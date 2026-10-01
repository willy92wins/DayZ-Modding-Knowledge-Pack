# DayZ tooling — loss of Memory LOD selection membership (ODOL→MLOD converter + inspector)

> Cross-cutting note (any DayZ mod debinarizing or editing .p3d with these skills).
> Origin: session 2026-05-21 kt_roadkill_armed (weapon rig). Two distinct bugs in
> two skills that, combined, cause a debinarized car/object to silently
> lose its Memory LOD selections (animation axes, dmgzones,
> crew positions, proxies).

## TL;DR

A Memory LOD selection in MLOD is a **membership set** (which points/faces
belong). In ODOL that membership lives in `NamedSelection.selected_vertices` /
`selected_faces`. Two tools lose it:

1. **External ODOL→MLOD converter** (reading→conversion side): transfers it only if there are
   `vertex_weights`. Memory selections are NOT skinned bones → no weights →
   discarded. Result: MLOD with NAMES of all 79 selections but **0 points** each.
2. **dayz-p3d-inspector** (writing side): on rebuild reconstructs Memory LOD from
   `recipe.memory_points[].selections` (which extractor leaves empty) and **ignores**
   `recipe.lods[memory].selections`. Result: rebuilding deletes memory selections.

Common and dangerous symptom: the `.p3d` looks "fine" (names present, geometry intact),
but in-game the car loses door/wheel/suspension axes, dmgzones, seats. The
backup does not save you: the rebuild remains structurally broken.

## Bug 1 — ODOL→MLOD converter: weight-gate discards selections without weights

**Location**: `odol_to_mlod.py` of external converter (~line 136, `convert_lod`).

```python
# ROTO:
if ns.selected_vertices and ns.vertex_weights:   # exige weights
    for idx_pos, vi in enumerate(ns.selected_vertices):
        ...
        if w > 0:
            sel.points[dst.points[vi]] = 1
```

Memory selections (`*_axis`, `dmgzone_*`, `pos_*`, `crew*`) provide
`selected_vertices` (e.g. an axis = 2 points) but empty `vertex_weights` → condition is
false → empty selection. (Also, heads up: in BI weight byte 0 can mean 1.0 — the
filter `if w > 0` is also suspicious for skinned selections.)

**Verified fix (minimum)**: map all `selected_vertices` as membership 1.

```python
if ns.selected_vertices:
    for vi in ns.selected_vertices:
        if vi < len(dst.points):
            sel.points[dst.points[vi]] = 1
```

Result on kt_roadkill_scum: 79/79 memory selections with points
(`doors_driver_axis`=2, wheel axes=2, dmgzones=1, `pos_driver`=1). The reader (v55patch)
already read membership properly — `NamedSelection.read` parses `selected_faces`/`selected_vertices`/
`vertex_weights` (`odol_reader_v55patch.py:250-261`). The bug was solely in the conversion.

**Conversor parcheado reproducible**:
`OneDrive\…\kt_roadkill_armed_dev\model-rig\odol_to_mlod_v55patch.py` (junto a `odol_reader_v55patch.py`).

## Bug 2 — inspector: build reconstructs memory from empty source

**Location**: `dayz-p3d-inspector/scripts/p3d_inspector_build.py` `build_memory_lod()`.
Reconstructs Memory LOD by grouping `recipe.memory_points[].selections` + `recipe.axes`.
BUT the extractor (`p3d_inspector_extract.py`) leaves `memory_points[].selections` empty and
`axes` empty on real models; actual membership is in `recipe.lods[memory].selections`,
which builder **ignores**. → rebuilding wipes 79 selections (and 132 faces) from memory.

**Status**: NOT fixed. **Mitigation**: to edit a `.p3d` that has critical memory
selections, **edit the MLOD object directly with py3d and write with py3d**, without going
through inspector recipe→build round-trip. (Inspector remains valid for inspection/viewer.)

## Gate operativo (defensa)

- After debinarizing, **verify membership, not just names**: read MLOD with py3d and check
  `len(sel.points)`/`len(sel.faces)` > 0 on memory selections (especially `*_axis`).
- Before any irreversible rebuild: **test round-trip** extract→build→re-extract and
  compare selection counts (this is what caught both bugs here). R26 in action.

## Propuesta upstream (backlog)

Apply both fixes to corresponding SKILL.md / scripts. skills-plugin is **read-only from
sandbox** → candidate for `introspection` task (APPEND to SKILL.md with fix section) or
for a pipeline maintenance session. Converter fix is already validated; inspector
fix requires rewriting `build_memory_lod` to rebuild from `lods[memory].selections`.

Cross-ref: handoff [`30_Sessions/2026-05-21-kt-roadkill-armed-faithful-mlod-stepB-unblock.md`](../30_Sessions/2026-05-21-kt-roadkill-armed-faithful-mlod-stepB-unblock.md),
lesson `LL-006`, project bug-ledger `bug-tool-001/002`.

## Related

- [[dayz-model-pipeline]] — `.p3d` assembly/editing with py3d; Memory LOD selections are authored here.
- [[dayz-p3d-inspector]] — inspector runbook (Bug 2: recipe→build round-trip wipes memory).
- [[dayz-p3d-audit]] — membership/winding/Component01 verification closing operational gate.
- [[dayz-capacidades-verificadas]] — cross-cutting limitation: ODOL v55 reader does not parse anims section.
- [[dayz-animations-creatures-weapons]] — why `*_axis` matter: animation axes for doors/wheels/suspension.
