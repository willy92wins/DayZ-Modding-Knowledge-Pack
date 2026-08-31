---
name: dayz-p3d-inspector
description: >
  Interactive 3D inspector/editor AND builder for DayZ .p3d files. Full round-trip: extract .p3d to
  Recipe JSON, visualize in Three.js with drag & drop editing, then rebuild a new .p3d from the edited
  Recipe. Editor shows LOD wireframes, draggable memory points, animation axes, bounding boxes and
  selections with snap-to-grid; builder handles visual/collision/memory LODs, mass by material density
  and auto-fix for winding/UV issues. VISUAL and interactive work — for structural audits, path validation
  or collision-LOD correctness use dayz-p3d-audit instead. Use when: inspecting p3d contents visually,
  verifying or moving memory points, viewing collision LOD wireframes, building a .p3d from a Recipe,
  applying interactive edits to a model. Also trigger from dayz-p3d-audit or dayz-model-pipeline.
  Keywords: "inspect model", "show me the p3d", "view memory points", "move points", "check LODs visually",
  "recipe json", "build p3d", "round-trip p3d".
---

# DayZ P3D Inspector — Interactive 3D Model Viewer, Editor & Builder

Full round-trip pipeline for DayZ .p3d files:

```
.p3d  --extract-->  Recipe JSON  --viewer-->  Edit visually  --build-->  new .p3d
```

Extract model data, visualize everything in Three.js, drag memory points
interactively, export the edited Recipe, and rebuild a fresh .p3d from it.

## Scope (and what this skill delegates)

This skill **owns** three things:

1. The **Recipe JSON** as a single, complete data contract over a .p3d file
   (all LODs + memory points + axes + selections + properties + referenced paths
   + bounding box).
2. The **interactive editor** (Three.js, drag&drop memory points and axis
   endpoints, snap-to-grid, modal Recipe export).
3. The **Recipe -> .p3d builder** (the inverse of the extractor; closes the
   round-trip loop).

Anything else is delegated to a sibling skill — do **not** duplicate it here:

| Task                                      | Use this skill instead                  |
|-------------------------------------------|-----------------------------------------|
| ODOL (binarized) .p3d -> MLOD (editable)  | external ODOL->MLOD converter (pre-step) |
| Visual viewer with PAA textures / glTF    | `dayz-3d-viewer` (or invoke before)     |
| PAA <-> PNG conversion                    | `dayz-3d-viewer` (`paa_to_png.py`)      |
| Deep config / path / structure validation | `dayz-p3d-audit` (post-step)            |
| Generating a .p3d from scratch (Blender)  | `dayz-model-pipeline`                   |
| Editing / aligning proxies on a host model | `dayz-proxy-align`                     |

The viewer in this skill renders untextured flat-shaded geometry on purpose:
its job is to make memory points, axes, selections, collision LODs, and bounds
inspectable and editable. For texture-rich previews, generate the Recipe here
and feed the source .p3d through `dayz-3d-viewer` separately.

## Install Dependencies

```bash
# py3d DayZ fork >= 1.5.0. Pick ONE route; both end in the same assert below.
# NUNCA `pip install py3d` (PyPI = point-cloud lib) NI git+upstream (sin guards).
#
# Route A - this pack is checked out:
pip install -e tools/py3d
# Route B - a vendored wheel is present in this skill's wheels/ directory. That wheel
# is placed by the local py3d rollout and is NOT shipped in this pack; the installer
# fails closed when it is missing, and refuses to guess when legacy wheels sit beside it.
#   python3 scripts/install_py3d.py
python3 -c "import py3d; assert getattr(py3d,'IS_DAYZ_FORK',False) and tuple(map(int,py3d.__version__.split('.')))>=(1,5,0), (py3d.__version__, py3d.__file__)"
pip install numpy --break-system-packages
```

Only the extractor and builder need py3d — the viewer is pure Python that
emits a self-contained HTML file.

## Scripts

All in this skill's `scripts/` directory:

| Script | Purpose |
|--------|---------|
| `p3d_inspector_extract.py` | P3D -> Recipe JSON extractor (all LODs, memory, axes, selections) |
| `p3d_inspector_viewer.py`  | Recipe JSON -> Interactive HTML viewer generator (Phase 2 — drag & drop) |
| `p3d_inspector_build.py`   | Recipe JSON -> .p3d builder (MLOD) with mass policy + auto-fix |

## Quick Start

### From a real .p3d file

```python
import sys
sys.path.insert(0, '/path/to/skill/scripts')
from p3d_inspector_extract import extract_recipe
from p3d_inspector_viewer import generate_inspector_html

recipe = extract_recipe('model.p3d', verbose=True)
generate_inspector_html(recipe, output_path='inspector.html', model_name='My Model')
```

### Demo mode (no p3d needed)

```bash
python scripts/p3d_inspector_viewer.py --demo inspector_demo.html
```

### CLI

```bash
# Extract recipe from p3d
python scripts/p3d_inspector_extract.py model.p3d -v -o recipe.json

# Generate viewer from recipe
python scripts/p3d_inspector_viewer.py recipe.json inspector.html

# Build .p3d from an edited Recipe
python scripts/p3d_inspector_build.py recipe.json output.p3d -v
```

### Build Recipe -> .p3d (Python)

```python
import json
from p3d_inspector_build import build_p3d

with open('recipe_edited.json') as f:
    recipe = json.load(f)

result = build_p3d(recipe, 'model_rebuilt.p3d', auto_fix_enabled=True, verbose=True)
# result = { "output_path", "lods_written", "fixes_applied", "warnings" }
```

## Recipe JSON Format

The Recipe JSON is the central data contract between all pipeline stages:

```json
{
  "meta": {
    "source": "model.p3d",
    "version": 1,
    "mode": "audit|propose|demo"
  },
  "lods": [
    {
      "type": "visual_0|visual_1|visual_2|visual_3|geometry|fire_geometry|view_geometry|landcontact|roadway|paths|hitpoints|memory|shadow",
      "resolution": 0.0,
      "num_points": 328,
      "num_faces": 640,
      "geometry": { "positions": [], "normals": [], "uvs": [], "material_groups": {} },
      "wireframe": { "positions": [], "edges": [], "faces": [] },
      "selections": { "name": { "vertices": [], "faces": [], "vertex_count": 0, "face_count": 0 } },
      "properties": { "autocenter": "0" }
    }
  ],
  "memory_points": [
    { "index": 0, "position": [x,y,z], "selections": ["name"], "category": "center|interaction|axis|placing|port|proxy|other", "label": "name" }
  ],
  "axes": {
    "axis_name": { "points": [[x1,y1,z1],[x2,y2,z2]], "direction": [dx,dy,dz], "length": 0.015 }
  },
  "bounding_box": { "min": [], "max": [], "size": [], "center": [] },
  "referenced_paths": { "textures": [], "materials": [] }
}
```

`material_groups` keys use the format `"texture|material"` (pipe-separated; either side may
be empty). UVs are stored in glTF V-flipped convention so they render correctly in the
viewer; the builder un-flips them before writing back to the .p3d.

## LOD Types & Resolution Constants (BIS MLOD)

The classifier maps `lod.resolution` to a logical type:

| Resolution | Type | Has geometry/wireframe? | Notes |
|------------|------|-------------------------|-------|
| `0.0..10`        | `visual_0..3`     | full geometry  | rendered LODs |
| `1.0e3..1.5e4`   | `shadow`          | wireframe      | shadow volumes |
| `1.0e13`         | `geometry`        | wireframe      | physical collision; needs `Component01..` + mass |
| `1.0e15`         | `memory`          | points only    | memory points + animation axes |
| `2.0e15`         | `landcontact`     | wireframe      | per-vertex ground contact points |
| `3.0e15`         | `roadway`         | wireframe      | walkable surfaces |
| `4.0e15`         | `paths`           | wireframe      | AI navigation paths |
| `5.0e15`         | `hitpoints`       | wireframe      | named-selection destruction points |
| `6.0e15`         | `view_geometry`   | wireframe      | line-of-sight occlusion |
| `7.0e15`         | `fire_geometry`   | wireframe      | bullet/projectile collision |

Anything else falls back to `unknown_<resolution>` and the builder skips it
with a warning.

## Builder Behaviour

- **Visual LODs** — rebuilds tri faces from `geometry.material_groups`, re-inverts
  UVs back to DayZ convention (Recipe stores glTF V-flip), deduplicates per-vertex
  normals into a shared face-normal pool.
- **Wireframe LODs** (`geometry`, `fire_geometry`, `view_geometry`, `landcontact`,
  `roadway`, `paths`, `hitpoints`, `shadow`) — rebuilds faces from `wireframe.faces`
  (tris / quads; N-gons are fan-triangulated), preserves `properties`, auto-adds
  `autocenter=0` and `class=house` to the Geometry LOD only if absent.
- **Mass** is applied **only** to `geometry` and `fire_geometry`. ViewGeo,
  Shadow, LandContact, Roadway, Paths, HitPoints get no per-point mass.
- **Memory LOD** — ignores any `lod` entry of type `memory` in the Recipe and
  rebuilds from `memory_points` + `axes`, creating one Selection per unique
  selection name referenced in `memory_points[].selections[]`.
- **Mass policy** for Geometry/Fire LOD points (priority):
  1. `lod.properties["_point_mass"]` override (per-LOD float)
  2. `recipe.meta.point_mass_default` override (global float)
  3. Heuristic: scan `referenced_paths` for density keywords
     (metal/steel/iron=7800, wood=600, plastic=1200, default=2000 kg/m^3),
     then `per_point = (bbox_volume * density) / num_points`.
- **Auto-fix** (on by default; disable with `auto_fix_enabled=False` or `--no-autofix`):
  - Detects inverted face winding in Visual LOD 0 (>50% faces with normal pointing
    opposite to geometric cross-product) and reverses winding on **all** LODs.
  - Reports every fix applied in `result["fixes_applied"]`.
- **Deeper validation** (path existence, BB anchor, action targets, Component01
  coverage, etc.) is intentionally **not** in scope here. Pipe the freshly built
  .p3d through the `dayz-p3d-audit` skill for that.

## Viewer Features

### Layer Toggles
- **Visual**: Flat-shaded model mesh (no textures by design — see Scope above)
- **Geometry**: Green wireframe overlay showing collision LOD
- **Fire Geo**: Red wireframe showing ballistic geometry
- **View Geo**: Blue wireframe showing view culling geometry
- **LandContact**: Yellow-green wireframe showing ground contact points
- **Roadway**: Cyan wireframe showing walkable surfaces
- **Paths**: Magenta wireframe showing AI navigation paths
- **HitPoints**: Orange wireframe showing destruction hit points
- **Memory Pts**: Colored spheres at memory point positions
- **Axes**: Purple arrows showing animation axes
- **Bounds**: Bounding box (cyan) + box_placing bounds (orange)
- **Labels**: Floating text labels on memory points and axes
- **Grid**: Reference grid
- **Wireframe**: Visual mesh wireframe overlay
- **Export Recipe**: Opens modal with edited Recipe JSON for copy

The 7 wireframe LOD layers are off by default; enable them as needed.

### Memory Point Categories (Color-Coded)
- **Center** (cyan): `pos center`, `ce_center`
- **Interaction** (red): `actionPos`, action-related points
- **Axis** (purple): Animation axis endpoints (2 points per axis)
- **Placing** (orange): `box_placing_min`, `box_placing_max`
- **Port** (deep orange): `port_*`, `cable_*` (LFPG electrical)
- **Proxy** (gray): Proxy attachment points
- **Other** (light gray): Unclassified points

### Sidebar Panels
- **Points**: List of all memory points with live coordinates, click to focus
- **LODs**: Summary of all LODs with point/face counts and selections
- **Selections**: All named selections across all LODs
- **Paths**: Referenced texture/material paths with `P:\` drive warnings (UX hint;
  for full path/structure validation use `dayz-p3d-audit`)

### Interaction
- **Orbit**: Left mouse drag on empty space
- **Pan**: Right mouse button drag
- **Zoom**: Scroll wheel
- **Select point**: Click on a sphere -> shows info panel with coordinates
- **Drag point**: Click sphere + drag -> moves it in camera-perpendicular plane
- **Snap to grid**: Hold **Shift** while dragging to snap to grid
- **Grid size**: Press **1** for 0.01m (1cm), **2** for 0.05m (5cm)
- **Focus**: Click point in sidebar list -> camera flies to it
- **Export**: Click "Export Recipe" -> modal with JSON, use Select All + Ctrl+C

### Drag & Drop Details (Phase 2)

The drag system uses hover-based orbit disabling: when the cursor hovers over a memory
point sphere, OrbitControls is pre-emptively disabled so that pointerdown on the sphere
starts a drag instead of orbiting. Moving away from spheres re-enables orbit.

When dragging a memory point, the following are updated in real-time:
- Sphere position in 3D scene
- HTML overlay label position
- Axis line + arrow geometry (if the point is an axis endpoint)
- Placing bounding box (if the point is `box_placing_min` / `box_placing_max`)
- Sidebar coordinates text
- Recipe JSON data (R object in memory)
- Selection info panel coordinates

A floating coordinate display shows X/Y/Z during drag. The coordinate display also
shows the current snap grid size when Shift is held.

## Technical Notes

### Three.js Setup
- Three.js **r0.147.0** via classic UMD `<script>` from CDN (NOT ESM/importmap).
  This is intentional: when the HTML is opened from `file://` on Windows Chrome,
  ESM `<script type="module">` + import map + cross-origin CDN imports break
  with `net::ERR_BLOCKED_BY_ORB`. UMD works from `file://` without any flags.
- OrbitControls from `examples/js/controls/OrbitControls.js`. r0.147 is the
  last version that still ships UMD examples; r0.148+ removed `examples/js/`
  in favor of ESM-only. Don't bump above r0.147 without re-introducing an ESM
  module wrapper or a local OrbitControls fork.
- No CSS2DRenderer — labels use pure HTML overlay divs with `Vector3.project()`
- No Box3Helper — bounding boxes use manual LineSegments
- All materials are MeshStandardMaterial (not Basic) to support emissive on selection
- BufferAttribute with explicit Float32Array (not Float32BufferAttribute)

### Event Handling
- Hover detection via mousemove sets `ctrl.enabled=false` when over a sphere
- This prevents OrbitControls from capturing pointerdown on spheres
- pointerdown on sphere: selects + prepares drag state
- pointermove with >5px threshold: activates drag, creates camera-perpendicular plane
- pointerup: ends drag, re-enables orbit
- Drag plane created perpendicular to camera view direction through point position

### Recipe Export
- Export opens a modal with textarea containing the modified Recipe JSON
- User clicks "Select All" then Ctrl+C to copy
- Clipboard API is blocked on local file:// URLs, so textarea copy is the reliable path

## Pipeline Integration

```
+-------------+     +--------------+     +--------------+     +-------------+
| OBJ/FBX/GLB | --> | Claude       | --> | Inspector    | --> | p3d_inspect |
| (raw model) |     | proposes     |     | user adjusts |     | _build.py   |
|             |     | recipe       |     | via drag&drop|     |             |
+-------------+     +--------------+     +--------------+     +-------------+
       ^                [TODO]               ^                       |
       |                                     |                       v
       |            +--------------+         | Export Recipe   +-------------+
       |            | Existing     | ------> | (audit mode)    | model.p3d   |
       +------------| .p3d file    | -- extract --> Recipe     | (MLOD)      |
                    +--------------+                            +-------------+

Round-trip edit workflow (fully working):
   p3d ---> extract ---> Recipe ---> viewer (drag&drop) ---> export ---> build ---> p3d
```

If the input .p3d is binarized (ODOL), convert it with an external ODOL->MLOD converter first to get an
MLOD copy. After building, optionally run `dayz-p3d-audit` over the result for a
deep structural review.

Components status:
- **Extractor** (`p3d_inspector_extract.py`) — done (selection iteration fix applied)
- **Viewer + drag&drop** (`p3d_inspector_viewer.py`) — done (Phase 2)
- **Builder Recipe->p3d** (`p3d_inspector_build.py`) — done (round-trip verified)
- **Smart proposal** (raw mesh -> Recipe with inferred memory points/selections) — TODO

## Planned Features

### Phase 3: Selection Painting
- Color faces by selection membership
- Click faces to assign to selections
- Face winding validation (red=inverted, green=correct)
- Component01 coverage check

Existing tooling: the selection painter in `dayz-animation-pipeline`
(`references/selection-painter-for-actions.md`, used on A6_SR2M to repaint the
`bolt`/`trigger` selections with py3d write-back) already covers interactive
face painting — start from there instead of implementing this phase from scratch.

### Phase 4: Animation Preview
- Parse `model.cfg` animations
- Interactive sliders for animation phases
- Material state toggles (LED on/off/color)
- Live preview of animated selections

## Known Limitations

- Only MLOD .p3d files supported (not ODOL/binarized — pre-process via an
  external ODOL->MLOD converter).
- Viewer renders untextured flat-shaded geometry by design — for textured
  previews use `dayz-3d-viewer` separately.
- Clipboard API blocked on file:// URLs — use textarea Select All + Ctrl+C.
- Drag works on the camera-perpendicular plane (no axis-lock yet).
- Extractor does not capture per-point `mass` (Geometry/Fire LODs); the builder
  fills it via the material-density heuristic. To preserve exact masses from an
  existing .p3d, add them to the Recipe manually (via `lod.properties["_point_mass"]`)
  or pass a global `recipe.meta.point_mass_default`.
- Builder does not yet write proxies, sharp edges, or `#UVSet#` tags beyond
  what py3d emits automatically. For placing/orienting proxies on a host model
  use `dayz-proxy-align`.

## Changelog

### v4.1 — Viewer fix for `file://` (Windows Chrome ORB)

- **FIX** Viewer used `<script type="module">` + import map + ESM imports from
  `cdn.jsdelivr.net/npm/three@0.160.0`. When the HTML was opened from `file://`
  (typical case: user double-clicks the file on Windows), Chrome's Opaque
  Resource Blocking refused the OrbitControls cross-origin module fetch with
  `net::ERR_BLOCKED_BY_ORB`. The whole script tag failed silently — `window.TL`
  was undefined, no canvas appeared, no toolbar buttons worked.
- **NEW** Switched to Three.js **r0.147.0** UMD via classic `<script src>`
  loaders, which load from `file://` without any browser flags. Same scene,
  same drag&drop, same APIs (`T = THREE` alias keeps the rest of the code
  unchanged). r0.147 is the last version with UMD `examples/js/` shipped.

### v4 — Correct LOD classifier (BIS 1e15 family)

- **FIX** `classify_lod()` and the builder's `LOD_RESOLUTION` map were using
  the wrong constants for FireGeometry (was `2.0e13`, should be `7.0e15`) and
  ViewGeometry (was `3.0e13`, should be `6.0e15`), and a `resolution > 1.0e14`
  catch-all bucketed every special LOD as `memory`. On real .p3d files this
  collapsed Memory + LandContact + Roadway + Paths + HitPoints + ViewGeo +
  FireGeo into a single `memory` type, then sequentially overwrote
  `recipe.memory_points` from each — so the genuine memory points were lost.
- **NEW** Full BIS MLOD 1e15-family support: `memory` (1e15), `landcontact` (2e15),
  `roadway` (3e15), `paths` (4e15), `hitpoints` (5e15), `view_geometry` (6e15),
  `fire_geometry` (7e15). The extractor stores wireframe data for all of them;
  the builder rebuilds them with the correct resolution.
- **NEW** Mass policy clarified: only `geometry` and `fire_geometry` receive
  per-point mass; LandContact, Roadway, Paths, HitPoints, ViewGeo and Shadow
  do not.
- **NEW** Viewer toolbar: 4 new toggles (LandContact yellow-green, Roadway
  cyan, Paths magenta, HitPoints orange), off by default.
- **DOCS** New "LOD Types & Resolution Constants (BIS MLOD)" reference table.

### v3 — Scope realignment

- **NEW** "Scope" section — explicit list of what this skill owns vs. what it
  delegates to `dayz-3d-viewer`, `dayz-p3d-audit`, and
  `dayz-model-pipeline`. Removes documentation drift / overlap with sibling skills.
- **NEW** Pipeline integration note pointing at the external ODOL->MLOD converter (pre)
  and `dayz-p3d-audit` (post).
- **DOCS** "Texture rendering in viewer — TODO" reframed as a deliberate scope
  decision (delegated to `dayz-3d-viewer`).
- **DOCS** Builder validation policy explicitly delegates deep structural checks
  to `dayz-p3d-audit`.
- **DOCS** Aligned all documented signatures with the real code
  (`build_p3d(..., auto_fix_enabled=True, ...)`).

### v2 — Builder + Extractor fix

- **NEW** `p3d_inspector_build.py` — Recipe JSON -> .p3d (MLOD) builder.
  Supports all Recipe LOD types, mass-by-density, auto-fix winding. Round-trip
  verified against demo recipe (memory points, axes, selections, properties
  all preserved bit-for-bit — demo recipe only; real models: Memory-selection
  loss documented in SP-002).
- **FIX** `p3d_inspector_extract.py` — `extract_selections()` and
  `extract_memory_data()` iterated `lod.selections` as if the values were
  Selection objects with a `.name` attribute. In the current py3d API
  `lod.selections` is an `OrderedDict` that yields string keys on iteration,
  and each `Selection.points` / `.faces` is a `{Point|Face: weight}` dict
  (not indexable). The old code crashed with `AttributeError: 'str' object
  has no attribute 'name'` on any real .p3d file. Fixed by iterating
  `.items()` and mapping `Point` / `Face` object identities back to LOD-local
  indices via `id()` lookup tables.

## Memory selection round-trip + collision winding (added 2026-05-23)

### Round-trip is NOT lossless for Memory selections (SP-002)
The build path can lose/mis-write Memory-LOD selection membership: `build_memory_lod()`
reconstructs the Memory LOD from `recipe.memory_points[].selections` + `recipe.axes`, but the
extractor leaves those empty on real models — the real membership lives in
`recipe.lods[memory].selections`, which the builder IGNORES → a rebuild can wipe memory
selections (axes, dmgzones, crew, proxies) while names/geometry still look fine. Before any
irreversible rebuild, do a round-trip test (extract→build→re-extract) and compare selection
COUNTS, not just names. Mitigation for a .p3d with critical memory selections: edit the MLOD
with py3d directly and write with py3d, bypassing the recipe→build round-trip. (The inspector
remains fine for inspection/visualization.)

### Collision LOD winding must match Visual (SP-003)
When generating/editing a collision LOD, compare its winding sign against the Visual LOD
(centroid method) before deploying — they must match (~100% INWARD, DayZ left-handed).

## (added 2026-06-01) Recipe stale tras edits externos al .p3d (SP-022)

El recipe JSON puede quedar desincronizado del `.p3d` real si el `.p3d` fue editado
por otra herramienta (Object Builder, py3d directo, conversor ODOL->MLOD externo) sin re-extraer el
recipe. Antes de reportar un bug desde la vista del inspector:

1. Re-extraer el recipe con `extract_recipe.py` y comparar estructuralmente con la
   versión cacheada.
2. Si difieren, la fuente de verdad es el `.p3d`, no el recipe.
3. Si el recipe es idéntico pero el viewer muestra algo "raro", verificar el
   round-trip py3d directo antes de afirmar bug.

Origen: introspección 2026-06-01 §B-6; sesión kt_roadkill_armed Sprint G' 2026-05-31.

<!-- [merged 2026-06-05 from <claude-home>\skills user copy during plugin-canonical migration; almacen: .claude\skills] -->
## py3d `selections` API gotcha (OrderedDict, non-subscriptable points/faces)

`lod.selections` is an **OrderedDict** keyed by selection name. Iterating it
gives string keys, not Selection objects. Each `Selection.points` and
`.faces` is a **dict** `{Point | Face: weight}` — NOT index-subscriptable.
To find LOD-local indices you must build `id()` lookup tables.

The extractor handles this correctly. If you see `AttributeError: 'str'
object has no attribute 'name'` or `TypeError: 'Selection' object is not
subscriptable`, you're looking at old/stale code — use the version in
this skill.

## Recipe selection indexing - vertices = point-pool, NOT triangle-soup (SP-028, added 2026-07-14)

`selections[].vertices` in the Recipe indexes the LOD's UNIQUE POINT POOL (0..len(lod.points)-1). `geometry.positions` is TRIANGLE-SOUP (3 entries per face, len = num_faces*3). Indexing `positions` with selection vertices yields coherent-looking but WRONG coordinates (it lands on unrelated real geometry), producing false structural alarms ("selection points at the wrong mesh").

Before declaring any selection/structure bug from Recipe data, verify at the py3d object level: load the .p3d, take `lod.selections[name].faces`, read each face's `vertices[].point_index` coords, and bbox THOSE. That is engine truth. Origin: kt_roadkill_armed 2026-06-07 false P1 (turret_yaw "was" the car spikes; the model was correct all along). Cross-ref SP-002, LL-111.

## Reglas promovidas del corpus de lecciones (added 2026-07-27)

Promovidas desde `AI/20_Knowledge/lessons-learned.md` para que lleguen por trigger en vez
de depender de que alguien recuerde buscarlas. Cada regla cita su `LL-NNN` de origen;
la entrada completa (síntoma, origen, evidencia) vive allí. No quites la cita: el índice
`lessons-index.md` detecta la promoción buscando esa referencia dentro de las skills.

- **LL-109** — Para round-trips que normalizan, ordenan o deduplican, prueba `f(f(x)) == f(x)` y define aparte qué campos deben ser estables desde la primera vuelta. Documenta toda renormalización permitida.

## Round-trip caveat

Memory selections may not survive the extract → edit → rebuild cycle (SP-002). Verify selection
membership after a rebuild, not just selection names.
- **LL-010** — Antes de afirmar que falta una pieza, enumera los proxies del `.p3d`, inspecciona sus tamaños y abre los candidatos sustanciales. El config solo revela lo riggeado; debinariza y separa componentes conexos si la geometría vive en un proxy.
- **LL-177** — Antes de extraer selecciones o geometría corregida, localiza el archivo realmente editado —incluidos backups que marquen la intervención— y haz que el pipeline lea esa copia. No valides procedencia solo porque el bbox parezca coherente.


## Non-semantic MLOD face padding (SP-229, added 2026-08-31)

An MLOD face record always reserves four vertex slots. A triangular face leaves the fourth
slot unused, and Object Builder can leave non-zero bytes there after face reordering or
editing. Those bytes carry no face data and binarization discards them. Source:
`p3dtxt/README.md:11` and `p3dtxt/src/main.rs:38-42`.

A changed `.p3d` hash after a rewrite therefore does not by itself prove data loss. For an
MLOD round-trip, compare parsed fields while ignoring the unused fourth slot of triangles,
or binarize both versions and compare the resulting ODOL semantics. Keep byte identity only
for producers that explicitly promise canonical zero padding. This caveat is separate from
the Memory-selection loss described in SP-002.
