---
name: blender-assembly
description: "Use this skill whenever building, assembling, or creating any 3D model in Blender via MCP tools (mcp__blender__execute_blender_code). Covers all object types: furniture, vehicles, architecture, props, mechanical parts, scenes. Trigger any time Blender Python code will create geometry with primitives, bmesh, curves, modifiers, or booleans. It prevents the most common geometry bugs (exploded models, silent scale errors, broken boolean meshes) AND enforces a detail pass so models don't ship as bare boxes — beveled edges, panel recesses, hardware, cables, lofted grips/stocks, baked normal maps. Includes a mesh-integrity gate (non-manifold, duplicate verts, degenerate faces) that runs after every boolean or modifier apply. Always invoke before writing any Blender geometry code, including 'simple' objects."
---

# Blender Assembly Skill

This skill prevents geometry errors when building 3D models in Blender via MCP, and enforces a detail pass so models come out looking like objects, not boxes. The recurring failure modes it addresses:

1. **Cube size math** — `primitive_cube_add(size=1)` creates vertices at ±0.5, so `scale=0.4` gives half-extent 0.2, not 0.4. This silently halves every dimension, misplacing all connected parts.
2. **Euler rotation on cylinders** — rotating a cylinder to point in a direction using Euler angles frequently points it along the wrong axis due to XYZ rotation order.
3. **Invisible gaps** — parts placed "near" each other with no geometric overlap look exploded when rendered. Even a 5mm gap is visible at model scale.
4. **Bare-box output** — nothing in the workflow asked for detail, so none was built. Phase 1.5 and Rules 6–11 fix this.
5. **Broken meshes** — booleans and joins leave non-manifold edges, duplicate verts, and degenerate faces that bounding-box checks never see. The integrity gate (Phase 3) fixes this.

## Helper library

All helper functions live in `references/blender_helpers.py`, versioned. At session start, read that file and execute it whole via the Blender MCP instead of re-pasting individual functions — this eliminates drift between copies. A new helper enters the library only after surviving its fixtures (library-learning convention). The v2 helpers are marked PENDING FIXTURES in the file header until validated.

## Routing: build it, or generate it?

This skill covers **parametric hard-surface modeling** — anything definable by dimensions, joints, and repeated features (furniture, machines, crates, frames, pipes, electrical devices, weapons). For **organic or densely decorative geometry** (statues, creatures, irregular props, sculpted surfaces), hand-building in Blender is the expensive path: route to `hunyuan3d-local` (canonical image→3D ladder: local → fal → paid) instead (AI base mesh → optimize/remesh → this pipeline for cleanup and export). Decide before writing any geometry code; a half-sculpted bmesh blob is the worst of both worlds.

## Phase 1: Connection Planning (before any code)

Create a **connection map** listing every joint before writing any geometry. This forces correct thinking about where parts touch.

For each joint, write:
- The two parts that connect
- Which face/edge of each meets the other
- The target overlap (minimum 0.005m / 5mm)

```
Connection Map:
  tabletop_bottom (Z=0.73) <-> leg_top (Z=0.74)     overlap: 0.01m on Z
  leg_bottom (Z=0.01)      <-> floor (Z=0.00)        sits on floor
  drawer_back              <-> desk_body_front        overlap: 0.01m on Y
```

Write this as a comment block in your first code cell, before any bpy calls.

## Phase 1.5: Detail Planning (before any code)

The connection map guarantees the model holds together; it does not stop the model from shipping as a set of bare boxes. A model with zero detail features is unfinished by default — nothing in the real world has perfect 90° edges.

Next to the connection map, write a **detail list**: for each visible part, enumerate the features the real object has, the technique that produces each, and its approximate size. Think like the reference photo, not like the primitive.

```
Detail List:
  housing      edge chamfer        bevel 3mm/2seg      all exterior edges
  housing      side vent recess    inset+sink          0.12 x 0.06m, depth 5mm
  housing      corner bolts        place_copies        4 per corner plate
  front panel  panel line          inset+sink          2mm wide, 1mm deep
  frame        cable run           make_cable r=6mm    junction box to motor
  grip         compound shape      loft_profile        palm swell + taper
  grip         stippling           bake (Rule 11)      normal map, not geometry
```

Floors (a model below these is not done):
- Every exterior edge of every visible part gets a bevel — Rule 6. No exceptions for "background" parts; un-beveled edges read as CGI from any distance.
- A hero object carries at least 3 distinct detail feature types (e.g. bevel + recess + hardware). If the detail list has fewer, go back to the reference before coding.
- Budget by LOD: full list on LOD0; drop hardware/recesses progressively on lower LODs (poly budgets live in `dayz-model-pipeline`).
- Fine surface detail (knurling, threads, stippling, stamped text) goes to the bake (Rule 11), never to LOD0 geometry.

If no reference image exists, get one first — `blender-visual-review` §C compares against it later, and a detail list invented from memory produces generic detail.

### Detail scan protocol (added 2026-07-30, adapted from img2threejs v1.4.3, Apache-2.0 — provenance in `blender-visual-review/references/NOTICE-img2threejs.md`)

An eyeballed detail list misses small identity-defining marks — a bevel highlight, a row of rivets, a stain — because the whole reference gets one glance. Scan zone by zone and record the scan alongside the list:

- **Scan method** — `component-zones` when part boundaries are already planned (walk each part's region of the reference), else `grid-3x3` (inspect every cell, no skipping). Write which method was used at the top of the detail list.
- **Count floor by complexity** — simple 3, moderate 6, complex 10, ultra-complex 16 details. A list below its floor means the scan stopped early — go back to the reference, not to memory. (The "≥3 distinct feature types on a hero object" floor above still applies; this one is about count.)
- **Per-detail record** — each row also carries: where on the reference (zone / grid cell), evidence (`seen` in a specific crop vs `inferred` from symmetry or occlusion), and confidence 0–1. Inferred and occluded details score low and MUST NOT be counted toward the floor.
- **Maps-to gate** — every row names the technique that builds it (Rules 6–11) or the texture channel that carries it (table below). A detail that maps to nothing is a planning failure: nothing reads prose, so it never reaches the model.

Texture-side detail kinds — the technique column above covers geometry; these kinds are details too and belong in the same list, with their destination in the DayZ texture pipeline (recipes in `dayz-texture-pipeline`):

| Kind | Reads as | DayZ destination |
|---|---|---|
| local gloss | low-roughness zone / specular hotspot on one region | `_smdi` gloss zone or rvmat |
| stain / patina / fade | darker cavity-biased dirt, gravity streaks, oxidation hue, sun-bleach | `_co` composite layer |
| scratch / chip | thin bright/dark line, may expose underlayer color at edges | `_co` + detail in the `_nohq` bake |
| decal / painted line | flat printed graphic or stripe — color contrast, zero relief | `_co` (or `_ca` when alpha) |
| emissive | self-lit region (LED, screen, ember) | rvmat emissive semantics |

Linework is three different techniques that read differently — pick the one the evidence supports, never default to geometry: an engraved groove is real negative relief that catches shadow (`panel_recess` / boolean); a painted line is color only (`_co`); a panel-line is a soft dark AO seam with no depth (bake / `_co` darkening). A hard groove where the reference shows a soft dark line is a wrong detail even though "a line" exists.

## Phase 2: Geometry Creation Rules

### Rule 1: Always Use size=2 for Cube Primitives

A cube with `size=S` has vertices at `±S/2`. After `scale=K`, the half-extent is `K * S/2` — **not** `K`.

**Always use `size=2`.** With `size=2`, vertices are at ±1, so after `scale=K` the half-extent equals `K` directly. The math is transparent and the factor-of-2 error disappears.

```python
# CORRECT — size=2, scale = desired half-extent
bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 0.75))
obj.scale = (0.60, 0.30, 0.02)   # box is 1.2m wide, 0.6m deep, 0.04m tall

# WRONG — size=1, scale misread as full extent
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.75))
obj.scale = (0.60, 0.30, 0.02)   # box is only 0.6m wide — half of intended!
```

Cylinders and spheres use `radius` which is already the actual radius — no conversion needed.

### Rule 2: Use bmesh for Directional Geometry — Never Rotate Cylinders

Never create a cylinder and rotate it to point in a direction. Euler rotation order (XYZ) makes this fail silently — the cylinder often ends up on the wrong axis.

For any geometry that must span from point A to point B (legs, beams, axles, supports, pipes, rails), build it with explicit vertex positions: `make_beam(name, start, end, hw, hh)` from the helper library.

Use for: chair/table legs, beams, axles, frame members, railings, any angled strut.
Skip for: vertical posts, wheels, hubs — anything aligned with a world axis where no rotation is needed.
For round cross-sections (pipes, cables, trigger guards): `make_cable` (Rule 8). For varying cross-sections (grips, stocks): `loft_profile` (Rule 10).

### Rule 3: Always Call transform_apply Immediately After Setting Scale

When creating objects in a loop, `bpy.context.active_object` can silently reference the wrong object by the end of the loop, causing a scale assignment to fail or apply to the wrong mesh. Call `transform_apply` immediately after every scale assignment — inside the loop, before anything else:

```python
# CORRECT
bpy.ops.mesh.primitive_cube_add(size=2, location=(x, y, z))
obj = bpy.context.active_object
obj.name = name
obj.scale = (sx, sy, sz)
bpy.ops.object.transform_apply(scale=True)   # ← immediately, inside the loop

# WRONG — scale may silently not apply
obj.scale = (sx, sy, sz)
# ... more operations ...
bpy.ops.object.transform_apply(scale=True)   # too late; active_object may have changed
```

### Rule 4: Derive Spanning Dimensions from Verified Neighbour Bounds

Never hardcode a dimension for a part that must reach between two existing parts. Hardcoded values drift from actual geometry. Instead, call `verify_bounds()` on both neighbours and compute the required size from their real extents:

```python
# CORRECT — measure first, then size the new part
b_a = verify_bounds("Part_A")
b_b = verify_bounds("Part_B")
half_span = (b_b['x'][1] - b_a['x'][0]) / 2   # actual half-width needed to bridge A and B

# WRONG — dimension set independently of actual neighbour positions
half_span = 0.28   # guessed; will be wrong if neighbours shifted even slightly
```

Apply this rule whenever one part must cover, fill, or connect two others on any axis. Always measure the gap from real bounds; never guess.

### Rule 5: Compensate for Subsurf Shrinkage

Subdivision surface modifiers pull geometry inward. A box spanning 0.0–0.30m may only reach 0.26m after level-2 subsurf.

**Extend geometry 10–15% past the target boundary** before applying subsurf, then verify:

```python
target_reach = 0.28
build_to     = target_reach * 1.13   # 13% longer to compensate for shrinkage
```

Alternative: use bevel modifier instead of subsurf for structural parts — it adds smooth edges without shrinking the shape.

### Rule 6: Bevel Every Exterior Edge (the box-to-object rule)

80% of the visual difference between "primitive" and "object" is edge bevels. Add an angle-limited bevel to every visible part as the last step of its construction, after all booleans: `add_bevel(obj, width=0.003, segments=2, angle_deg=40)` — width in meters, 2–4mm reads right at prop scale.

Apply (don't leave live) so LOD decimation and export see real geometry. Scale must already be applied (Rule 3) — a live scale makes bevel width anisotropic. Run `verify_mesh_integrity` after applying (Phase 3).

### Rule 7: Panel Recesses and Insets via bmesh

Panel lines, vents, screens, and recessed faces come from inset + sink: `panel_recess(obj, near_point, inset, depth)`. The face is picked by its world-space center — never by index, which changes with any earlier edit. For a raised panel instead of a recess, translate along `+face.normal` (edit the helper call). Chain two insets (frame + sink) for vent-style detail.

### Rule 8: Repeated Hardware and Cables

**Hardware (bolts, rivets, handles):** model one low-poly instance (cylinder, 8 segments is plenty at bolt scale), then place copies by explicit loop with `place_copies(src, positions)` — consistent with this skill's explicit-math philosophy and easier to verify than an Array modifier. Each copy must overlap its mount surface by ≥1mm (the connection map applies to hardware too).

**Cables / pipes / hoses / trigger guards:** never chain rotated cylinders. `make_cable(name, points, radius)` builds a Bezier curve through explicit points, bevels it, and converts to mesh. Endpoints come from `verify_bounds()` of the parts being connected (Rule 4), with ≥5mm penetration into each.

### Rule 9: Boolean Protocol

Booleans are the main source of broken meshes. Three rules, then mandatory cleanup:

1. Apply scale on both operands first (Rule 3) — booleans on live scale produce garbage intersections.
2. NEVER leave coplanar faces between operands. The cutter must overshoot every surface it cuts through by ≥1mm. Flush == coplanar == the #1 boolean failure (degenerate slivers, open holes).
3. Solver is always `'EXACT'`.

`boolean_cut(target, cutter, op)` enforces all three plus cleanup (remove_doubles + dissolve_degenerate). After every boolean, run `verify_mesh_integrity` before building anything on top. A broken mesh discovered three parts later costs the whole session.

> **(adjusted 2026-06-10, fixture F3)** Point 2's "NEVER" is downgraded to a strong recommendation: Blender 5.1 EXACT handled an exactly-flush, axis-aligned cutter without breaking the mesh (identical open pocket and volume vs the overshoot cut, clean hard counters; only the ring-ngon layout differs — LL-119). Keep the ≥1mm overshoot as the default for robustness (float drift, oblique cuts), but a flush cut that passes the integrity gate plus the visual checkpoint is acceptable, not an automatic fail. The gate reports ngons as warnings, never failures (LL-120).

### Rule 10: Loft Cross-Sections for Compound Shapes

Boxes and beams cannot make a pistol grip, a stock, a bottle, or an ergonomic handle. The technique for those is **cross-section lofting**: define a 2D profile, sweep it through a 3D path, scale it per section. This is the standard parametric approach for weapon grips and receivers.

Helpers: `ellipse_profile(rx, ry, n)`, `rounded_rect_profile(hw, hh, r, seg)`, `loft_profile(name, profile, path, scales, close_caps)`.

Usage pattern for a grip: `rounded_rect_profile` swept down a slightly curved path with scales like `[1.0, 1.05, 0.95, 0.9]` (palm swell → taper). Path points come from the connection map; the top ring must overlap the receiver by ≥5mm. The helper recalculates face normals, so winding is verified rather than assumed — but degenerate rings (duplicate path points) still produce zero-area faces, so run `verify_mesh_integrity` after every loft. If the result looks faceted in review, raise the profile's `n`.

### Rule 11: Fine Detail Goes to the Normal Map, Not to LOD0

Knurling, grip stippling, screw threads, stamped text, fine panel seams — modeling these as geometry blows the poly budget and still reads worse than a bake. The game-industry standard is the high→low pass, and it slots directly into the DayZ texture pipeline (`_nohq` normal map, AO multiplied into `_co`):

1. Build the part twice from the same build script: **high** (bevel segments 4–6, knurl/thread geometry, deep panel lines) and **low** (game budget, Rules 1–10 only). Same script, two parameter sets — never two divergent scripts.
2. UV-unwrap the low: `smart_uv(obj)` (Smart UV Project is acceptable for hard surface; islands need margin or the bake bleeds).
   Smart UV Project atomizes: median 2-4 faces/island is the classic failure — an unusable atlas for detail texturing. For DayZ
   visual assets unwrap by logical SECTIONS with contiguous islands and a human-readable atlas; the gate is a human reading the
   atlas. Full reference: `<vault>\AI\20_Knowledge\uv-mapping-dayz.md` + audit tool
   `<dayz-projects>\LFQuad_dev\tools\uv_audit.py`.
3. Bake from high to low with `bake_map(high, low, 'NORMAL', ...)` and `bake_map(high, low, 'AO', ...)` (Cycles, selected-to-active).

Known pitfalls (all reproduced in community reports, all controllable):
- No UVs on the low → hard error. `smart_uv` first, always.
- High and low not occupying the same space, or `ray` too small/large → patchy garbage in the map. Tune `max_ray_distance` to slightly more than the largest high/low surface gap; use a cage for parts with deep recesses.
- Blender bakes **OpenGL-convention (Y+)** tangent normals; DirectX-convention engines need the green channel inverted. Which convention DayZ's `_nohq` expects MUST be verified empirically against a vanilla `_nohq` (fixture F7) before shipping — do not guess and do not assume.

Output feeds `dayz-model-pipeline`: normal PNG → `_nohq.paa`, AO PNG → multiply layer in the `_co` composite.

> **(resolved 2026-06-10, fixture F7)** DayZ `_nohq` is DirectX-convention (Y−): invert the green channel (G' = 255−G) on every Cycles bake before export — Cycles emits OpenGL (Y+), verified by calibration. Full verdict, the DXT5nm swizzle caveat (the .paa stores X in alpha) and the reproducible calibration chain live in `dayz-model-pipeline` §"Convención _nohq" and LL-123/LL-125. The `ray=0.01` default was validated by fixture F6 (clean 1024px NORMAL+AO bakes at a ~4mm high/low gap).

## Phase 3: Verify After Every Part

Call these after creating each part. Catching a defect immediately is far cheaper than debugging an exploded or broken model later. All three live in the helper library.

**`verify_bounds(name)`** — print and return the world-space bounding box of a part.

**`verify_overlap(name_a, name_b, axis, min_overlap)`** — confirm two parts physically overlap on the given axis. Run for **every joint** in your connection map before moving to the next part. If it shows a gap, fix the position before continuing.

**`verify_mesh_integrity(name, require_closed, allow_ngons)`** — the broken-geometry gate. `verify_bounds` proves position; it passes happily on a non-manifold mess. This gate proves the mesh itself is sound. Run it after every boolean, every modifier apply, every loft, and once per part at finalization. Reading the result:

- `non_manifold_edges > 0` — an edge shared by 3+ faces: almost always a boolean leftover or two parts joined without merging. Fix at the operation that caused it; don't patch around it.
- `duplicate_verts > 0` — run `remove_doubles` on the real mesh (the gate's pass is on a throwaway copy).
- `boundary_edges > 0` with `require_closed=True` — a hole. Collision geometry MUST be closed; for visual meshes with intentional openings, call with `require_closed=False` and record why in the build script comment.
- `ngons` on curved surfaces shade badly and decimate badly — triangulate or re-inset; on large flat faces they're tolerable (hence warn, not hard fail).

The gate failing means stop and fix before the next part — same discipline as `verify_overlap`, same reason: broken geometry compounds.

**Component checkpoint:** for complex parts (lofts, boolean-heavy pieces), also take one quick visual capture of the part alone before building on top — see `blender-visual-review`. Numbers verify topology; only eyes verify intent.

## Phase 4: Finalization

Apply to every mesh object: `finalize(name)` (transforms applied, origin set, shade smooth), then `audit_all()` to confirm rotation=(0,0,0) and scale=(1,1,1) across the whole scene. Both in the helper library.

## Workflow Checklist

Every Blender model, every time:

1. **Route first** — parametric hard-surface stays here; organic/sculpted goes to `hunyuan3d-local` (canonical image→3D ladder: local → fal → paid)
2. **Connection map** — every joint, written before any bpy code
3. **Detail list** — zone-scanned (`grid-3x3` / `component-zones`), count floor by complexity, every row maps to a technique or texture channel; ≥3 feature types on a hero object; reference image in hand
4. **`size=2`** for all cube primitives — scale = actual half-extent
5. **`make_beam()` / `make_cable()` / `loft_profile()`** for A-to-B and compound shapes — no Euler rotations, ever
6. **`transform_apply(scale=True)` immediately** after every scale assignment, inside the loop
7. **Spanning dimensions from `verify_bounds()`** — measured, never guessed
8. **Booleans by protocol** — scale applied, cutter overshoots ≥1mm, EXACT, cleanup, gate
9. **Bevel every visible part** — angle-limited, applied, after all booleans
10. **Fine detail to the bake** — high/low twins from one script, `smart_uv` + `bake_map` (NORMAL + AO), never knurl on LOD0
11. **`verify_bounds()` + `verify_overlap()`** after every part, every joint
12. **`verify_mesh_integrity()`** after every boolean/modifier apply, every loft, and at finalization
13. **Component checkpoint** — one quick `vr_capture` of each complex part (lofts, boolean-heavy) before building on top
14. **`finalize()` + `audit_all()`** — transforms clean across the scene
15. **Hand off to `blender-visual-review`** — numbers verify topology; only eyes verify intent


## MCP render-depsgraph stale after in-place mesh edits (added 2026-06-11, verified 2026-06-10)

When driving the HOST Blender via MCP, `obj.data.transform()` (and other low-level in-place
datablock writes) update the data — verifiable by reading vertices — but the RENDER depsgraph
keeps serving a FROZEN copy of that datablock: every `render.render()` shows the pre-edit mesh.
`data.update()`, `update_tag()`, `view_layer.update()` and `evaluated_depsgraph_get().update()`
do NOT clear it, and a `mesh.copy()` INHERITS the stale cache. NEW objects render fine.

- Fix: write edited geometry to a **new mesh datablock via `bm.to_mesh(new_mesh)` and link it
  on a NEW object**; remove the old object+mesh. Cost of not knowing: phantom renders that
  contradict your measurements (nearly mis-diagnosed a correct orientation on A6_MK47).
- Diagnose with the **marker-sphere test**: add primitive spheres at known coords and render —
  markers correct + mesh stale = this cache, not your math.
- Also: `bpy.context.scene` can silently revert to the USER's scene between MCP calls — pin
  `bpy.context.window.scene` and pass `scene=` to `render.render()` on EVERY call, or you
  render (and screenshot) the wrong scene.

## Reglas promovidas del corpus de lecciones (added 2026-07-27)

Promovidas desde `AI/20_Knowledge/lessons-learned.md` para que lleguen por trigger en vez
de depender de que alguien recuerde buscarlas. Cada regla cita su `LL-NNN` de origen;
la entrada completa (síntoma, origen, evidencia) vive allí. No quites la cita: el índice
`lessons-index.md` detecta la promoción buscando esa referencia dentro de las skills.

- **LL-065** — No uses booleanos para tallar mallas orgánicas abiertas o no-watertight; prefiere extruir el boundary loop o hacer bridge manual. Si usas boolean, opera entre sólidos cerrados y valida raycast, boundary y non-manifold antes de continuar.
- **LL-121** — Tras modificar `location`, `rotation` o `scale` por API, ejecuta `bpy.context.view_layer.update()` antes de leer `matrix_world`. Coloca el update en el helper lector y usa fixtures que varíen todos los ejes.
- **LL-122** — Para tubos cerrados, activa `use_fill_caps`, convierte a malla y suelda con `remove_doubles(1e-5)`. Mantén el gate `require_closed`; no lo rebajes ante boundary edges.
- **LL-126** — Llama siempre `transform_apply(location=False, rotation=<bool>, scale=<bool>)` con los tres argumentos explícitos. Crea los sources de copias en el origen mundial antes de hornear transforms.
- **LL-127** — Llama `finalize()` inmediatamente sobre el objeto activo recién creado; no recorras nombres esperando que el helper haga lookup. Verifica el contrato real del helper y confirma nombre→bbox tras renombrar.
- **LL-128** — Para piezas curvadas en un plano, construye un loft 2.5D con ancho en eje mundial fijo y profundidad derivada de la tangente planar. Ejecuta `remove_doubles` y `dissolve_degenerate` tras cada loft.
- **LL-129** — En piezas huecas, dimensiona cada cutter para cruzar solo la pared objetivo, con overshoot hacia el hueco sin alcanzar la pared opuesta. Ejecuta el gate de integridad tras cada boolean.
- **LL-132** — Mantén disjuntos los componentes de cada cutter y aplica círculos/ranuras en pasadas separadas. Haz fallar el gate si la malla queda con cero vértices y alerta si operaciones sucesivas producen firmas idénticas.
- **LL-133** — No uses `panel_recess` sobre caps/ngons de loft; usa un boolean orientado o difiere el detalle al bake. Posiciona cutters desde path, escalas y perfil analíticos, nunca muestreando bandas de la malla resultante.
