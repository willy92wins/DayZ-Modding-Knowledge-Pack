# py3d 1.0.0 quirks — HISTORICO (superado por el fork DayZ >= 1.4.0)

> **Estado 2026-06-06 (rollout py3d-fork S2):** este documento queda como
> HISTORICO. La verificacion R22 (plan py3d-fork, R22-P1-01) demostro que
> varios de estos "quirks" describian APIs de WRAPPERS de proyecto
> (`set_face_weight`, `add_memory_point`, `lod.materials`), NO la superficie
> real de upstream 1.0.0. El **fork DayZ de py3d (>= 1.6.0, `pip install -e tools/py3d`)**
> (plugin projection: wheel vendorizada por skill)
> resuelve o supera cada caso:
>
> | Quirk historico | En el fork |
> |---|---|
> | 1 `Selection()` sin args | TypeError accionable; usar `lod.new_selection(name)` o `lod.set_selection(name, ...)` (F1-01/F2-04) |
> | 2 weights int vs float | guard en write: int-like coercionado, invalido -> `ValueError` temprano con nombre de la selection (F1-02) |
> | 3 materiales lowercase | `lod.faces_by_material()` / `faces_for_material()` case-insensitive (F1-03) |
> | 4 memory points duplicados | `lod.set_memory_point(name, xyz)` upsert idempotente, NUNCA duplica (F1-04) |
> | 5 rebind tras crecer el LOD | invariantes de membership en write: stale/foreign -> raise; ademas `P3D.save(verify=True)` re-lee y verifica (F1-05/F1-08) |
>
> Validacion integral: `python -m py3d validate modelo.p3d` o
> `P3D.validate()` (v1.2.0). El texto original se conserva abajo para
> contexto de sesiones antiguas (LFQuad D30, LL-055/056).

---

# py3d 1.0.0 quirks for in-sandbox `.p3d` updates (sandbox-deliverable)

The animation-pipeline ships scripts that touch `.p3d` files in-sandbox via
**py3d 1.0.0** (`ik_pose_to_seanim.py`, project-side `p3d_update.py`,
`rebake_selections.py`, viewer/painter pipelines). Five quirks of py3d 1.0.0
silently corrupt the output unless you handle them. They are NOT documented in
the py3d README; they were extracted from the LFQuad rider-pipeline sprint
(`LFQuad_dev/handoff_2026-05-28.md` D30, LL-055, LL-056).

If your script writes selections, memory points, or rebakes a production `.p3d`,
walk this checklist before treating the output as "round-tripped".

## Quirk 1 — `py3d.Selection()` constructor needs `(points, faces)` args

```python
# WRONG (silently produces empty Selection):
sel = py3d.Selection()

# RIGHT:
sel = py3d.Selection(lod.points, lod.faces)
```

py3d 1.0.0 made the `Selection` constructor positional-argument-required.
Calling the no-arg form returns an object whose `.set_face_weight(idx, w)` calls
appear to succeed but write nothing into the LOD's stream. The selection ends
up in the output `.p3d` with **zero membership**, same failure mode as the
debinarizer Memory-LOD bug (cross-ref LL-018, `dayz-debinarizer-inspector-memory-selection-bugs.md`):
the name shows up, the body is empty.

Apply once per LOD per selection. If you grow `lod.points` or `lod.faces`
later, see Quirk 5.

## Quirk 2 — weights are `int`, not `float`

```python
# WRONG (corrupted .p3d, Object Builder error "cannot read"):
sel.set_face_weight(face_idx, 1.0)

# RIGHT:
sel.set_face_weight(face_idx, 1)
```

py3d 1.0.0 stores weight in a byte stream and treats the value as a Python int.
A float `1.0` writes `b'\x00\x00\x80\x3f'` into a byte slot, shifting every
subsequent byte by 3 — the rest of the LOD is garbage. The .p3d looks the right
size on disk but Object Builder reports "cannot read" the LOD.

Same fix for point weights, vertex weights, anything `weight`-typed. Default
to `int(1)` unless you're explicitly skinning.

## Quirk 3 — material names are matched lowercase

```python
# WRONG (selection silently empty when JSON has UPPER names):
explicit = json.load(...)            # {"B_BLACK_1": [...], "B_CHROME_2": [...]}
for mat_name, face_indices in explicit.items():
    target = next(m for m in lod.materials if m.name == mat_name)   # NEVER MATCHES

# RIGHT:
for mat_name, face_indices in explicit.items():
    target = next(m for m in lod.materials if m.name.lower() == mat_name.lower())
```

py3d 1.0.0 reads material names from the `.p3d` as the binary stores them.
DayZ vanilla `.p3d` files use **lowercase** material names; tooling on top
(Blender exporters, `.mtl` libraries, OBJ writers) commonly write **UPPER** or
**MixedCase**. JSON config files inherit whatever the tool emitted. The
exact-name match silently fails and the selection's face-set ends up empty.

Normalize on lookup, not on storage — your JSON is allowed to use whatever
casing the source pipeline used. The lower() lookup is one line; rewriting the
JSON is many.

## Quirk 4 — memory points overwrite-in-place, do NOT append

```python
# WRONG (duplicates vanilla crewdriver/crewcodriver):
mem_lod.add_memory_point("crewdriver", pos)

# RIGHT:
existing = next((p for p in mem_lod.points if p.name == "crewdriver"), None)
if existing:
    existing.set_position(pos)         # overwrite in place
else:
    mem_lod.add_memory_point("crewdriver", pos)
```

If the `.p3d` you are editing already inherits or contains a memory point with
the same name (very common when extending a vanilla model — the body p3d
already ships `crewdriver` / `crewcodriver`), appending a new point with the
same name produces **two** entries. The engine resolves to one of them
non-deterministically — usually the first, which is the vanilla one, so your
edit silently has no effect.

The right pattern is overwrite-in-place. The reference implementation lives in
`LFQuad_dev/task4_handoff/p3d_update.py` (search `existing = next`).

Cross-cuts the dual-entry pattern (`references/dual-entry-action-pattern.md`):
the modded action's distance check against `crewdriver` / `crewcodriver` relies
on these being the points YOU wrote, not the vanilla originals. If the
overwrite-in-place step is skipped, the dual-entry action silently sees the
wrong positions and the L/R routing degrades.

## Quirk 5 — rebind point references after growing the LOD

```python
# WRONG (corrupted MLOD stream after adding new memory points):
mem_lod.add_memory_point("pos_driver_L", pos_L)
mem_lod.add_memory_point("pos_driver_R", pos_R)
# ... 10+ adds ...
# Now write a selection that references the OLD point indices:
sel = py3d.Selection(mem_lod.points, mem_lod.faces)   # WRONG — old reference

# RIGHT:
mem_lod.add_memory_point("pos_driver_L", pos_L)
# ... all the adds ...
mem_lod.rebind()                                       # or:
sel = py3d.Selection(mem_lod.points, mem_lod.faces)    # AFTER the growth
```

py3d 1.0.0 keeps an internal cursor into `lod.points` / `lod.faces`. Adding
points grows the underlying array, which can reallocate; references taken
before the grow point to **freed memory or the wrong index range**.

If your script grows the Memory LOD (adds N new points) and then writes a
selection that references the LOD, take the reference **after** the last add.
Same for any selection that was attached to the LOD before the growth — call
`Selection(lod.points, lod.faces)` again to refresh, do not reuse the old one.

This bug shows up as a `.p3d` that reads fine for the new memory points but
whose selections list garbled face/point indices — Object Builder displays the
selection covering random faces of the wrong material.

## Frame auto-detect when re-baking (LL-frame-of-reference, expanded)

A `.p3d` rebake script (one that takes JSON describing selections + memory
points in some authoring frame and writes them into the production `.p3d`)
**must accept** an explicit frame flag AND verify the frame from the model's
bounding box. Hard-coding `flip_z` to True or False is the most common source
of "the script runs, the .p3d updates, but the points are mirrored" bugs.

```python
# Pattern (reference: LFQuad_dev/task4_handoff/rebake_selections.py):

def detect_frame(p3d) -> str:
    # Front of vehicle in DayZ convention: the long axis with the most surface
    # area at the FAR end (engine bay) vs the seat end.
    bbox = p3d.lod0.bbox()
    z_min, z_max = bbox.z_min, bbox.z_max
    # Sample face centroids at z_max and z_min, count faces in each band.
    fwd_zPos = count_faces_in_band(p3d.lod0, axis='z', range=(z_max - 0.5, z_max))
    fwd_zNeg = count_faces_in_band(p3d.lod0, axis='z', range=(z_min, z_min + 0.5))
    return 'plusZ' if fwd_zPos > fwd_zNeg else 'minusZ'

parser.add_argument('--frame', choices=['plusZ', 'minusZ', 'auto'], default='auto')
frame = args.frame if args.frame != 'auto' else detect_frame(p3d)
flip_z = (frame == 'minusZ')

for memname, src_pos in canonical_points.items():
    pos = src_pos[:]
    if flip_z:
        pos[2] = -pos[2]
    # Now apply via Quirk 4 (overwrite-in-place):
    ...
```

The LFQuad reference case has `+Z front` in the authoring viewer/JSON and
`-Z front` in the production `.p3d` (D1 — the rotation to align with Croco's
naming convention). Without the explicit flag + auto-detect, baking the same
JSON against either frame produces mirrored output for one of them.

## Validation — assert the round-trip before treating output as done

After any py3d-based `.p3d` write:

1. Re-open the output with `py3d.P3D(open(output, "rb"))` (or
   `dayz-p3d-inspector`'s `extract_recipe`). `py3d.read_p3d` does not exist.
2. For each selection you wrote: assert `len(sel.faces) > 0` AND the count
   matches the JSON source ±N (small drift from refiner steps is OK, zero
   drift is not — that means the write didn't take).
3. For each memory point you wrote: assert the position matches the source
   (tolerance < 1e-4 m). If overwrite-in-place was skipped, you'll see a
   duplicate with the OLD value at the front; this catches it.
4. Material count and `Component01` casing unchanged (`dayz-p3d-audit` covers
   this; cross-ref).

If any check fails, the production `.p3d` was corrupted by one of the five
quirks above. Do NOT ship; restore from backup and re-run with the fix.

## Reference case

`LFQuad_dev/task4_handoff/p3d_update.py` and `rebake_selections.py` — both
applied all five quirks in-flight during the LFQuad sprint 2026-05-28 (D30).
The corrupted-output failure modes here are the ones those scripts had to
discover; if you base a new script on them, the quirks are already handled.
The auto-detect frame logic in `rebake_selections.py` is the canonical
implementation of LL-frame-of-reference.

## Cross-references

- `references/vehicle-rider-ik-pose.md` §"Frame-of-reference caveat" — pose
  side of the same frame issue.
- `references/dual-entry-action-pattern.md` §"Bail-out for non-LFQuad" — the
  modded action needs `crewdriver` / `crewcodriver` written via Quirk 4.
- `references/selection-painter-for-actions.md` §"Pipeline (start to finish)"
  step 6 — calls into a `p3d_update.py`-style script; that script needs all
  five quirks.
- `dayz-p3d-audit` — its winding/Component01 checks run AFTER this write;
  pass the round-trip first.
- `dayz-debinarizer-inspector-memory-selection-bugs.md` (vault) — adjacent
  failure mode (LL-018) where selection names survive but membership is lost.
  py3d 1.0.0 Quirks 1, 2, 5 reproduce a *similar* symptom on the write side.
