---
name: dayz-proxy-align
description: "Use when: align proxy, clothing shows at the floor, dressable mannequin, proxy orientation, ropa al suelo, worn vs ground (_m vs _g). Proxy triangles on a host. Not general LOD/memory edit: dayz-p3d-inspector; not clothing mesh/weights: dayz-clothing."
---

# DayZ Proxy Align — visual proxy positioning + lossless write-back

A DayZ proxy is a named selection `proxy:\path\to\model.NNN` over ONE tiny triangle in
a Visual LOD. That triangle encodes the attachment frame, but the engine derives it by
**angle-sort**, not by vertex order (see "The proxy frame convention" below): the widest-angle
corner is the anchor/position and the other two corners give the orientation. When the
triangle is degenerate or mis-oriented, the attached clothing/item renders at the floor,
floating, or rotated.

This skill is the visual, fast alternative to blind FORWARD/UP-knob iteration: it loads
the host model + every proxy, lets you drag/rotate each anchor with a TransformControls
gizmo against the real worn clothing, and writes the edited triangles straight back into
the MLOD with py3d — losslessly.

## When to reach for it

Misplaced/mis-oriented proxies on any host model — most often a **dressable static
object** (mannequin, Armor-Rack pattern: `Inventory_Base`/`Container_Base` that embeds
vanilla `\dz\characters\proxies\*_dz` proxies and declares clothing `attachments[]`).
Symptoms: equipped clothing shows at the floor, floats, clips, or is rotated.

## Pipeline

```
.p3d --extract--> recipe.json --worn_overlay(optional)--> recipe+worn
   --viewer--> drag/rotate gizmo --export--> edits.json --apply--> aligned .p3d
```

## Dependencies

```bash
# py3d DayZ fork >= 1.6.0 (`pip install -e tools/py3d`).
# NUNCA `pip install py3d` (PyPI = point-cloud lib) NI git+upstream (sin guards).
pip install -e tools/py3d
python3 -c "import py3d; assert getattr(py3d,'IS_DAYZ_FORK',False) and tuple(map(int,py3d.__version__.split('.')))>=(1,6,0), (py3d.__version__, py3d.__file__)"
pip install numpy --break-system-packages
```

Worn-mesh preview of vanilla clothing also needs an **external ODOL→MLOD backend**
(vanilla `*_m.p3d` are ODOL); pass its scripts dir to `worn_overlay.py --odol-backend`
or set `DAYZ_ODOL_BACKEND_ROOT`. The host model itself must be **MLOD** (binarized hosts:
convert them externally first).

## py3d lifecycle (pack fork >= 1.6.0, batch / non-visual)

For deterministic automation, the pack py3d fork (>= 1.6.0) owns the complete
add/inspect/align/remove lifecycle:

```python
import py3d

with open("host.p3d", "rb") as handle:
    model = py3d.P3D(handle)
lod = model.lods[0]

name = lod.add_proxy(
    r"\dz\characters\proxies\vests", 1,
    origin=(0.0, 1.1, 0.0),
    rotation=((1, 0, 0), (0, 1, 0), (0, 0, 1)),
    space="engine",
)
descriptor = {
    item["name"]: item for item in lod.get_proxies(strict=True)
}[name]
lod.align_proxy(
    name,
    origin=(0.0, 1.15, 0.02),
    rotation=descriptor["engine_frame"],
    space="engine",
)
# lod.remove_proxy(name)
model.save("host_aligned.p3d")
```

The legacy default remains `space="raw"`. In 1.4.0 the explicit conversion is
`engine_frame = P' × raw_frame`, with
`P' = ((-1,0,0),(0,0,1),(0,1,0))`; the same involutive matrix converts back.
Use `space="engine"` when the matrix describes the pose expected in DayZ.

All mutators are fail-closed: path, index, anchor, rotation, scale, canonical
proxy anatomy and exclusive ownership are validated before mutation.
`get_proxies(strict=True)` rejects malformed proxy selections. `align_proxy`
preserves point/face/selection identities; `remove_proxy` deletes exactly its
selection, face and three points, remaps surviving point indices and sharp
edges, and intentionally leaves the normal pool unchanged.

## py3d 1.4.0 lifecycle (plugin projection, historical)

The Cowork plugin projection vendored py3d 1.4.0 as a wheel and documented the
same add/inspect/align/remove API under this heading. This pack uses the fork
`>= 1.6.0` via `pip install -e tools/py3d` — see the lifecycle section above.
The 1.4.0 conversion `engine_frame = P' × raw_frame` with
`P' = ((-1,0,0),(0,0,1),(0,1,0))` is unchanged.

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/proxy_frame.py`   | the source-verified proxy-frame convention (angle-sort -> anchor + orientation matrix; canonical-triangle builder). shared by extract/canon |
| `scripts/proxy_extract.py` | host .p3d -> `recipe.json` (body mesh + every proxy's triangle, **derived frame + `ambiguous` flag**, ref model path) |
| `scripts/worn_overlay.py`  | resolve the worn-on-male model per slot (a default item is seeded for every slot; override any with `--map`), debinarize ODOL, inject LOD0 geometry as `proxies[i].worn` |
| `scripts/proxy_canon.py`   | rewrite every proxy as a **canonical unambiguous** triangle -> `edits.json` (identity by default = worn upright, or per-slot `--rot`) |
| `scripts/proxy_viewer.py`  | `recipe.json` -> standalone HTML editor (move/rotate gizmo, worn ref + assembled "final result" overlays; export bakes canonical triangles) |
| `scripts/proxy_apply.py`   | `edits.json` + src .p3d -> aligned .p3d (edits the MLOD in place; lossless) |

## Quick start

```bash
python3 scripts/proxy_extract.py maniqui.p3d recipe.json
# worn reference: every slot gets a sensible default _m item out of the box.
python3 scripts/worn_overlay.py recipe.json recipe.json --dz "/path/DZ" \
    --odol-backend "/path/to/odol-backend/scripts"
#   --map Vest=vests/press_vez Legs=pants/cargopants   # test specific items per slot
#   --dry-run                                          # just print the resolved mapping
#   --no-defaults                                      # start empty, map only what you pass
# FAST PATH — fix the common "worn but rotated" case in one shot (no GUI):
python3 scripts/proxy_canon.py recipe.json edits.json          # identity frame for every slot
#   --rot Headgear=Y:90 Mask=Y:90                              # per-slot rotation only where needed
python3 scripts/proxy_apply.py maniqui.p3d edits.json maniqui_aligned.p3d --verify

# INTERACTIVE PATH — dial orientation in by eye:
python3 scripts/proxy_viewer.py recipe.json proxy_align_viewer.html
# open the HTML, align each proxy, click "Exportar edits", save as edits.json
python3 scripts/proxy_apply.py maniqui.p3d edits.json maniqui_aligned.p3d --verify
```

## Using the editor

Click a proxy (sidebar or its sphere) to attach the gizmo. **W** = move, **E** = rotate;
drag the arrows/rings. Two clothing overlays help you align:

- **Resultado final** — every slot's worn mesh attached to its proxy, rigidly following
  your edits. This is the assembled "dressed mannequin" preview: align the proxies, toggle
  it on, and see the whole result at the current alignment.
- **Worn ref** — the selected proxy's worn mesh in its native character-space position, as
  a fixed target to align the anchor against.

"Reset proxy" restores a proxy to its loaded position. "Exportar edits" opens a modal;
Select-All + Ctrl+C (clipboard is blocked on `file://`) and save as `edits.json`.

The gizmo sets the anchor position and the frame rotation; on export the skill writes a
**canonical** (unambiguous) triangle encoding exactly that, so the engine re-derives the
frame you set. Scale is fixed (proxies are a tiny triangle); only position + rotation matter.

## The model-variant rule (clothing has MORE THAN ONE model)

DayZ clothing ships as variants distinguished by suffix:

- `<item>_m` — worn on the **male** player. **Use this** for a male host.
- `<item>_f` — worn on the female player.
- `<item>_g` — **ground/dropped** model (the "default"/floor one). **Not** this.

`worn_overlay.py` seeds one default `_m` item per slot and always prefers `_m` when
resolving. If a slot has several plausible candidates (e.g. `plate_carrier_m`,
`plate_carrier_holster_g`), it reports them and you should pick one explicitly with `--map`
— **do not silently guess; surface the choice to the user**. Picking the `_g`/ground model
is the classic cause of "it shows the floor model".

Note the scope boundary: the *engine swap* that replaces a slot's default `*_dz` proxy
with the equipped item's worn model is config/skeleton behaviour (e.g. the F2.3 problem on
a static `Inventory_Base`), separate from anchor position. This skill aligns the anchor and
previews the correct worn variant; it does not by itself force the engine swap.

## Why write-back is safe (the viability gate)

The dayz-p3d-inspector Recipe->build path does NOT write proxies and can drop Memory
selections, so this skill never uses it. Instead `proxy_apply.py` loads the MLOD with py3d,
mutates ONLY the listed proxy points, and re-writes. py3d round-trips a real DayZ MLOD
byte-for-byte, so the host geometry, the host's own selections (e.g. `woodup1`/`zbytek`),
the Geometry/Memory LODs and `#UVSet#` are preserved. Before trusting an edit, re-extract
the output and confirm the proxy count and non-proxy selections are unchanged
(`proxy_apply.py --verify`).

## The proxy frame convention (orientation is deterministic)

Coords are raw MLOD (Y-up), rendered directly (matches dayz-p3d-inspector). The engine reads a
proxy triangle by **angle-sort**, verified against Arma3ObjectBuilder (`utilities/proxy.py`
`find_axis_vertices` / `get_transform_rotation` / `create_proxy`; doc
https://mrcmodding.gitbook.io/home/documents/proxy-coordinates):

- sort the three corners by interior angle, descending;
- widest-angle corner = **anchor** (position);
- middle-angle corner direction = local **+Y**; smallest-angle corner direction = local **+Z**;
- **+X** = Y x Z, then Z re-orthogonalized.

It is pure geometry, so orientation is **fully reproducible offline** — `proxy_frame.py` computes
the same matrix the engine does. The old "confirm rotation in-game by trial" caveat came from not
knowing this rule (`scripts/test_proxy_frame.py` checks it offline: canonical -> identity, the 90/45/45 tie -> ambiguous, rotation round-trips).

**The degenerate-triangle gotcha (the usual cause of "worn but rotated").** If the two edges from
the anchor are equal length — the 90/45/45 isosceles triangle hand-rolled proxy builders tend to
emit — the middle and smallest angles **tie**, so +Y/+Z get assigned by raw vertex order and the
engine picks a rotated, unintended frame. `proxy_extract.py` reports this as `ambiguous`. Fix it
with a **canonical** triangle that has three distinct angles (90/63.4/26.6): `proxy_canon.py`
rewrites every proxy to a canonical frame (identity by default, or per-slot `--rot`), and the
viewer's export bakes canonical triangles too. Any rotation of a canonical triangle stays canonical
(rotation preserves angles), so an exact orientation survives the lossless write-back.

Worn-mesh overlays are shown in native character-space coords (a robust positional reference); with
canonical frames the "Resultado final" preview matches the engine's orientation rather than only
approximating it. Engine-exactness for DayZ vs Arma3 MLOD is [verify in-game] but high-confidence —
same MLOD format.

## Sibling skills

- **dayz-p3d-inspector** — general MLOD viewer/editor + Recipe round-trip (this skill is the
  proxy-specialized, write-safe counterpart).
- **External ODOL→MLOD backend** — required for vanilla worn meshes and binarized hosts; not distributed with this pack (`--odol-backend` / `DAYZ_ODOL_BACKEND_ROOT`).
- **dayz-p3d-audit** / **dayz-pbo-build** — audit the aligned .p3d and validate before packing.

## Crew proxies de vehículos (added 2026-06-05)

The angle-sort frame convention above (widest-angle corner = anchor; middle = +Y;
smallest = +Z) and the 90/45/45 isosceles gotcha are NOT clothing/mannequin-only. They
apply identically to **vehicle crew proxies** — `crewdriver` / `crewcodriver`, i.e.
`proxy:\dz\vehicles\wheeled\proxies\crew_driver`. A crew proxy is the same tiny triangle
in a LOD and is read by the same angle-sort.

**Real case — LFQuad 2026-06-05.** `crewdriver` / `crewcodriver` were 1 mm 90/45/45
triangles → ambiguous frame → driver and co-driver sat **sideways** and the player
rotated on get-in. The tie resolved differently per seat (one had +Y mapping to "up",
wrong; the other +Y to "forward", correct), so the same bug looked different on each
seat. Fix: canonical triangles (three distinct angles) with **+Y → vehicle forward,
+Z → up** (use `proxy_canon.py` / canonical_triangle).

**The crew proxy ANCHOR sets the seated player's POSITION/HEIGHT.** The config `proxyPos`
resolves the seat from the proxy in the ViewGeo LOD — NOT from a memory point or a bone.
An anchor placed too high seats the player in the air. LFQuad evidence: anchors at
Y=1.46 / 1.70 left the rider elevated; corrected down to actual seat height.

**Do not copy a frame raw from another sub-model's proxy.** Croco `bus_*` proxies are
not vanilla `crew_*`; the correct frame depends on the sub-model. For vanilla crew
proxies the rule is **+Y → forward**.

## Pure-geometry proxies: MODEL-SPACE geometry + the engine-identity frame P' (added 2026-06-24; in-game VERIFIED 2026-06-24)

For a **pure-geometry proxy** (a body region split off to beat the 65535 vertex ceiling —
`proxy:\<mod>\proxy\chassis.NNN`, 1 visual LOD, no config class), TWO things must be right:

1. **Geometry authored in MODEL-SPACE** (its real position on the car, NOT centered at its own origin).
   Measured by debinarizing vanilla proxies (`prox_int` Y[0.36,1.56] cabin, `sedan_engine` Z[-2.30,-1.12]
   front) + Star_Audi_R8 + kt_roadkill `_body`. Centering each chunk at its own origin piles them all at the
   host origin.
2. **Triangle FRAME = the engine-identity `P' = [[-1,0,0],[0,0,1],[0,1,0]]`, NOT this skill's `derive_frame`
   identity.** Same `P'` as the weapon-proxy section below: the skill/py3d "identity" renders the geometry
   LAID ~90 deg to the side; `canonical_triangle(anchor, P')` (i.e. `add_proxy(path, rotation=P')`) renders it
   as authored. **VALIDATED IN-GAME on MercedesAMGLF body-proxys 2026-06-24 (AC1.4 PASS)**, independently of the
   A6_SR2M weapon-proxy validation. This SUPERSEDES the earlier note here ("origin anchor + skill-identity is
   mandatory") — that was offline-only and rendered the MercedesAMGLF body rotated ~90 deg in-game (the offline
   frame/render gave green-in-false twice).

Path carries NO `.p3d` extension (engine appends it; a doubled `.p3d.p3d` = proxy silently absent in-game).
**Attachment proxies (wheel/crew/door) are NOT a placement reference** — physics/config place them (`proxyPos`,
axles); their non-zero `pos` misleads. **Gate**: for proxies the offline frame/render is NOT valid — the gate is
the in-game spawn+render. Vehicle case + the three rules (path / frame P' / model-space): skill `dayz-vehicles`
(body-proxy convention, CONFIRMED in-game).

## Weapon attachment proxies + the engine-vs-skill convention map (added 2026-06-24, A6_SR2M)

A weapon's `proxy:` selections (`suppressor_45acp`, `optic_*`, `*_mag`, a custom rail mount) orient the
ATTACHED item exactly like clothing proxies. Hard-won lessons from the A6_SR2M comp/rail/optic:

- **The engine reads the triangle as `h(R) = P'·R`, with `P' = [[-1,0,0],[0,0,1],[0,1,0]]`** (a 180°
  rotation about the Y+Z diagonal) relative to this skill's `derive_frame`. So `derive_frame` is the
  skill frame, the *rendered* frame is `P'·derive_frame`. Validated in-game: a rail baked with the
  skill-IDENTITY frame rendered "laid 90° to the side"; a frame of `P'` renders upright. Therefore
  `canonical_triangle(anchor, P')` makes the engine render IDENTITY. (Resolves the old WARNING in
  `proxy_frame.py`: the skill `derive_frame` ≠ engine; they differ by `P'`.)
- **Matching a vanilla item's frame value works only if your model is authored like the vanilla one.**
  optic_reflex (vanilla model) + mag worked by copying the vanilla frame bit-for-bit. A CUSTOM
  muzzle/comp model authored on different local axes does NOT — it renders rotated even at the
  "correct" vanilla frame.
- **Find the bore by the HOLE, not by bbox/hollow heuristics.** A custom comp had a circular bore hole
  AND an oval vent hole, plus a perpendicular tab longer than the bore. `bbox`-longest and
  central-void/hollow detection both pointed at the wrong axis. The reliable method: render the
  **MUZZLE VIEW** (orthographic projection looking down world X = the barrel, at the current proxy
  frame) and locate the round (circular = bore) vs elongated (oval) holes. The barrel must pass
  through the CIRCULAR hole.
- **Fix = shift + roll, verified against the user's in-game photo.** Detect the circular hole's Y-Z
  center; translate the proxy triangle so that center lands on the barrel line (anchor Y/Z); apply the
  needed roll about world X (e.g. 180°: `p -> (p.x, 2*Yb - p.y, -p.z)`). Re-render the muzzle view to
  confirm the barrel `+` is centered in the circular hole before building.
- **The inventory PREVIEW does NOT use the proxy** — it renders the raw MODEL. Fixing the proxy fixes
  in-game but the icon still shows the model's authored (wrong) orientation. To make the preview match
  in-game, bake the proxy's orientation `M = engM(proxy)` into the MODEL (rotate every LOD's points +
  the normal pool + memory points by `M`) and reset the proxy to `canonical_triangle(anchor, P')`
  (engine-identity). In-game is unchanged (`anchor + I·(M·v) == anchor + M·v`); the preview now shows
  the in-game orientation.

Session tooling not preserved (the muzzle-view render, hole detection, shift+roll bake and
weapon+attachment overlay scripts lived in a session TEMP dir); the method described above is
sufficient to re-derive them.
