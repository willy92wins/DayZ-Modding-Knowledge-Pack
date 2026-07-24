# UV-unwrap + normal/AO bake for a rigged character (high→low)

After the mesh is rigged (`character-rigging.md`) you UV-unwrap the low-poly and bake the high-poly's
surface detail into a tangent-space `_nohq` plus an AO map, in the **new UV**. Verified end-to-end in
Blender headless ([LFInfectedBig ✓] 2026-06-25). The gotchas below each cost an iteration; front-load them.

The decisive gate is not "the map looks purple" — it is a **lit preview of the low with the normal applied,
compared to the high**, plus numeric checks (UV stretch spread, % black pixels, AO surface mean). Render and
look (`blender-visual-review`); the raw map is not the test.

## 1. UV-unwrap — Smart UV on quads, then triangulate

Unwrap on the quad mesh (cleaner islands), pack to fill the square, **then triangulate** — triangulation
adds no verts so the rig weights are untouched, and it makes the bake tangents equal the shipped tangents
(no shading seams in-game). Ship the triangulated mesh.

```python
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=radians(66), island_margin=0.003)   # small margin
bpy.ops.uv.select_all(action='SELECT')
bpy.ops.uv.pack_islands(rotate=True, scale=True, margin=0.008)           # fill the 0..1 square
bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY')
```

`island_margin=0.02` packs row-by-row and wastes ~40% of the square (islands clump bottom-left). Use a small
smart-project margin + an explicit rotating `pack_islands` → bbox fill ~97%, bigger islands = more texels.

**Verify, don't eyeball:** per-tri `uv_area/world_area` normalized to its median should sit in a tight band
(p10–p90 ≈ 0.8–1.15× → uniform texel density), 0 zero-area UV faces. Render a `COLOR_GRID` flat-lit
(Workbench `light='FLAT'`, `color_type='TEXTURE'`) — checker squares stay square, no smearing, the cavity
hole is visible. Rasterize the UV layout (dump loop UVs → PIL) to confirm no clumping/overlap.

## 2. THE ALIGNMENT GOTCHA — bake from a pre-conform proxy

The rig step (`character-rigging.md §3`) **conforms the low's limbs** to the canonical bind (e.g. arms
opened ~8 cm). The high-poly was never conformed, so after rigging the **low and high no longer occupy the
same space in the conformed regions** (tell: `low.dims.x` ≠ `high.dims.x`). Baking high→low directly there
gives rainbow noise (rays hit the wrong surface) and flat misses.

A tangent-space normal map is **pose-invariant given identical topology + UV** — that is exactly why normal
maps survive skeletal animation. So bake in a pose where low and high DO align (the pre-conform retopo
pose), using the shipped low's topology + new UV, then apply the result to the conformed shipped low.

```python
# co3 = world positions of the PRE-conform retopo low (matches the high; verify dims match the high)
proxy = duplicate(shipped_low); proxy.matrix_world = Identity
for i,v in enumerate(proxy.data.vertices): v.co = co3[i]     # topology+UV of shipped low, aligned positions
# verify index correspondence first: median |co3[i]-shipped[i]| ~0 for the un-conformed region (torso/legs),
# large only in the conformed limbs. Confirm proxy.dims == high.dims before baking.
```

Bake high → **proxy**. The OGL/tangent result applies correctly to the conformed shipped low (same topo+UV).

## 3. Don't `make_consistent` a non-watertight AI high-poly

Recalculating normals "outside" on a non-manifold AI mesh (Rodin/Hunyuan output) can flip whole shells
inward → large coherent **black blotches** in the lit preview. AI generators output normals already
consistent for rendering. Use them as-is; only `shade_smooth()`. (Recalc IS safe on the clean retopo target
— see §5.)

## 4. Bake misses → neutral, never black

Cycles `use_clear=True` clears the target to black `(0,0,0)`. The Normal Map node decodes `(0,0,0)` as an
inward normal → that texel renders **black** under light. Where the low has no high counterpart within ray
distance (thin fingers, the cavity rim, a conformed limb the proxy didn't fully cover), you get black holes.

**Pre-fill the image with neutral and disable clear**, so misses stay flat (no detail) instead of black:

```python
nrm = bpy.data.images.new("normal_ogl", 2048, 2048, float_buffer=True)
nrm.colorspace_settings.name = 'Non-Color'
nrm.pixels.foreach_set(np.tile(np.float32([0.5,0.5,1.0,1.0]), 2048*2048))   # neutral tangent normal
bpy.ops.object.bake(type='NORMAL', normal_space='TANGENT', use_selected_to_active=True,
                    cage_extrusion=0.025, max_ray_distance=0.05,            # generous; body is thick
                    margin=16, margin_type='EXTEND', use_clear=False)       # <-- keep the neutral fill
```

Confirm `% pixels == (0,0,0)` is ~0 after baking. Save 16-bit raw (`view_transform='Raw'`, depth `'16'`,
`img.save_render`).

## 5. AO — isolate the target as sole occluder, and fix its normals

Two separate causes of a too-dark AO bake:
- **The high-poly occludes.** AO uses ALL scene geometry as occluders; the coincident high-poly self-shadows
  the low → everything dark. Hide every mesh except the target (`hide_render=True`) before the AO bake.
- **The target's own normals are inconsistent** (voxel-remesh / decimate / conform leave custom split
  normals or flipped faces) → AO rays go into the surface → dark/noisy. Clean them first:

```python
bpy.ops.mesh.customdata_custom_splitnormals_clear()
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.object.shade_smooth()
```

Bake AO on the **conformed shipped low** (its real pose → correct occlusion), low-only:
`bake(type='AO', use_selected_to_active=False, samples=256, margin=16, use_clear=True)`. Sanity: AO mean on
SURFACE pixels (mask out the black gaps) should be bright (~180–210); a convex-ish body is mostly unoccluded.

These cleaned normals are also REQUIRED on the shipped low for the normal map to apply correctly (same
consistent-outside convention the proxy was baked against) — bake them into the shipped mesh.

## 6. `_nohq` orientation — green-invert for DayZ

DayZ `_nohq` is DirectX / **Y-**. Blender bakes OpenGL / Y+. Invert the GREEN channel of the OGL result for
the DayZ source (`dayz-texture-pipeline` map-conventions). Keep the 16-bit OGL as the master; derive `_nohq`
from it (not from an 8-bit intermediate) when going to `.paa`.

```python
r,g,b = Image.open("normal_ogl.png").convert("RGB").split()
Image.merge("RGB",(r, ImageOps.invert(g), b)).save("nohq.png")
```

## 7. Internal decorative geometry (ribcage, organs) — bone-heat fails

Thin, self-intersecting internal meshes (a scripted ribcage) break Blender bone-heat (`ARMATURE_AUTO`)
entirely → all verts zero-weight. Two robust alternatives, in order:
- **Procedural weight by height to the spine chain** (used [LFInfectedBig ✓]): for each vert, the two nearest
  `Pelvis/Spine/Spine1/Spine2/Spine3/Neck/Neck1` bones by world-Z, blend inverse-distance. Ribs hang from
  the spine, not the arms.
- **`DATA_TRANSFER` weights from the body mesh** (`POLYINTERP_NEAREST`, `layers_vgroup_select_src='ALL'`):
  anatomically matches the overlying skin BUT a wide ribcage picks up shoulder/arm weights from the nearby
  chest-top skin → ribs swing with the arms. Only use if you then strip non-spine groups and renormalize.

Decimate first (`DECIMATE` collapse to ~15 k), parent `type='ARMATURE'` (modifier, no auto weights), assign
weights, `vertex_group_limit_total(4)` + `normalize_all`. Deform-test: pose the spine, confirm the ribs
follow the torso (displacement direction `dot` with the chest skin ≈ 1) and stay inside the cavity. Set
`arm.data.pose_position='POSE'` for the test (it ships REST=bind); `animation_data_clear()` if the FBX Action
overrides the pose (`character-rigging.md §5`).

## Failure → cause quick map

| Symptom | Cause | Fix |
|---|---|---|
| Rainbow/garbage normal | low conformed after retopo → low≠high in conformed regions | bake from pre-conform proxy (§2) |
| Large black blotches in lit preview | misses cleared to black, or high shells flipped by recalc | neutral prefill + `use_clear=False` (§4); don't recalc the AI high (§3) |
| AO dark/muddy everywhere | coincident high occludes, or target normals inconsistent | isolate target as sole occluder + clean its normals (§5) |
| `_nohq` lights inverted in-game | OpenGL Y+ shipped as DayZ Y- | green-invert (§6) |
| Shading seams along UV islands in-game | baked on quads, shipped triangulated | triangulate before the bake; ship triangulated (§1) |
| Internal mesh all zero-weight | bone-heat failed on thin self-intersecting geo | procedural spine-height weights (§7) |
| Wasted UV resolution | `island_margin` too big, no rotating pack | small smart-project margin + `pack_islands(rotate)` (§1) |
