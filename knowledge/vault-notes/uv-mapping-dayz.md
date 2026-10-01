# UV mapping — diagnostic reference for DayZ (RV engine)

> Created 2026-07-05 (LFQuad session "thorough UV review"). Consolidates: direct
> verification from py3d + quantitative audit of LFQuad, vault sweep (LL-021/123/125/
> 159/167, SUB_BRZ, LFInfectedBig), skills/scripts sweep, and external research
> (biki, PMC, armake, polycount, DayZ-Samples). External claims include URL; local
> ones include `path:line`. Unconfirmed items are marked [UNVERIFIED] or [derivation].
> Executable tool: `LFQuad_dev\tools\uv_audit.py` (§7).

## 0. TL;DR operativo

- A UV is a (u,v) pair **per face-vertex** (loop), not per 3D point: the same point
  can have different UVs on different faces → seams and islands are born there.
- UV overlap: OK to **read** texture (mirroring, tiling, trim sheets); FATAL
  to **bake** (bake AO/albedo/normal writes two surfaces into the same texels).
- Flat textures (solid `_co`, procedural glass) are **UV-invariant**: they work
  with garbage UVs or (0,0). Per-part detail is the only thing that requires good UVs
  ([`30_Sessions/2026-06-28-SUB_BRZ-fase5-texturas.md:50-52`](../30_Sessions/2026-06-28-SUB_BRZ-fase5-texturas.md)). Diagnostic corollary:
  a flat texture MASKS broken UVs; the problem surfaces when adding detail.
- Binarizing quantizes UVs to int16 over the min/max of the ENTIRE LOD → a single face
  with huge tiling degrades precision across the entire LOD (§2.2).
- `_nohq` is DirectX (Y−/green-down): G'=255−G ALWAYS when exporting from Cycles (LL-123).
- Each UV split (seam) duplicates vertices when binarizing (unique point×normal×UV) →
  more seams = more resolved vertices = earlier reaching "Too many vertices"
  (`dayz-binarize-vertex-limit` memory).

## 0.5 GATE #0 — mesh health BEFORE unwrap (added 2026-07-06, Banshee/LFQuad v2 case)

UV work rests on mesh health: unwrapping/baking on broken mesh
produces false diagnoses (e.g. "double wall" that was mirrored mapping on single
wall). Translation from artist-language to measurable:

| What the artist says | Measurable | Banshee case (measured) |
|---|---|---|
| "open/unwelded vertices" | verts that would merge at <0.5mm (KDTree) + coincident duplicate faces | 190-715 verts/part in mechanical buckets; ~1.9k duplicate faces in 2 parts |
| "convexity issue" / "does not close" | boundary edges (1 face), non-watertight shells | 65-3,674 open edges/part (majority = single-wall design, NOT breakage) |
| "weird normals" | edges with inconsistent winding, non-manifold (>2 faces/edge) | 28 winding + 264 NM on the grill (stacked-strip design) |

**Recipe (tools in `LFQuad_dev\tools\mesh_health.py` + `mesh_sanitize.py`):**
1. Audit first (mesh_health): boundary/NM/dup-verts/dup-faces/zero-area/winding per part.
2. **ADAPTIVE weld** — central pitfall: a blind weld at 0.5mm MERGES legitimately
   touching parts and CREATES non-manifold (Banshee: SEAT.009 0→168 NM). Ladder
   [0.5, 0.2, 0.1, 0.05, 0.01 mm]: per mesh, the greatest distance whose result does NOT
   increase NM and preserves UVs (automatic gates). The weld preserves loop
   UVs (100% verified on 15 meshes).
3. Delete coincident duplicate, degenerate, loose faces; recalc normals.
4. Exit gates: NM(after) ≤ NM(before), UV nonzero% equal, visual render
   (black patches = flipped normals).
5. DESIGN open edges (single walls, strips) STAY: DayZ renders them;
   they only matter for watertight/interior AO bake.

bpy gotcha (bit 2×): cached refs to `me.loop_triangles` become STALE after
any edit-mode round-trip → silent corruption or IndexError. Rebuild
the cache after each `mode_set`. Symptom of corruption: two UV layers ended up
byte-for-byte identical (G3's "identical numbers = artifact" caught it).

bpy gotcha #2 (bit 3×, different root, added 2026-07-06): building MULTIPLE UV
layers with operators (smart_project/unwrap/pack) in ONE headless session can contaminate
a pair of layers (ended up ≡ byte-for-byte despite different pipelines) even without
stale caches. Mandatory defenses: (a) **byte-for-byte equality probe between all
layers at the end of any multi-layer build** (numpy foreach_get + array_equal);
(b) the affected candidate is rebuilt STANDALONE (clean bpy session, one layer).
Anti-false-positive nuance: equal metrics between methods ≠ equal data — density
normalization + global pack push any re-projected field to the
same statistical equilibrium (~same islands/px-m); only DATA equality is a bug.

bpy gotcha #3 (added 2026-07-06, the most severe): **`bpy.ops.uv.smart_project` in
headless IGNORES face selection and unwraps the ENTIRE mesh**. Measured: 4
different pipelines that "re-projected only N selected faces" converged
all into layouts of exactly the same ~2043 islands (= smart45 of everything). Symptom:
identical island counts between supposedly different methods. Defense: for
LOCAL re-projection of concrete faces, do NOT use the operator — manual planar
projection (orthonormal basis of the cluster's dominant normal, direct UV writing),
100% scoped by construction. `uv.unwrap`/`pack_islands` do respect selection
(measured indirectly: packs by section worked).

EXACT overlap verification (production gate, e.g. for Substance Painter):
Monte-Carlo has a noise floor (~0.05-0.1%) and cannot assert "zero". Exact
test = 2D triangle-triangle SAT on candidate pairs from a spatial grid
(intersecting interiors; touching at boundary does NOT count, eps 1e-9). ~74k tris →
~10⁵ pairs, seconds in Python. "No overlap" is only declared with SAT=0
(implementation: `uv_g3.py §sat_tri_overlap/exact_pairs`).

Small island stitch (reduce fragmentation, "larger groups"): island S
is stitched to neighbor N with most shared mesh boundary, via SIMILARITY transform
(complex: s=(b2-b1)/(a2-a1)) that aligns the shared edge — conformal, cannot
wrinkle. Final recipe (v4, LFQuad G8): normalize density BEFORE (correct stitch
→ |s|≈1, guard [0.75,1.33]) + **ABSOLUTE post-stitch density guard [0.6,1.6]**
(without it, stitch chains accumulate compound drift: p5 0.027 measured) +
sampled non-overlap vs N (8 pts/tri) + top-3 neighbors + sweeps until converged.
865 clean merges, islands 2054→544, p5 0.245. RULED OUT with data: rigid weld
of the entire boundary (wrinkles the seam faces, p5 0.031) . Local folds
between ADJACENT faces are not fixed by translating (they travel together): local
planar projection per cluster.

Gotchas of `pack_islands` (measured 2026-07-06): (1) **does NOT normalize selection to
tile [0,1]** — leaves content near its current scale/tile (CLOSEST_UDIM);
any post-pack remap must measure the real bbox (blind remap crushed buckets ~40×);
(2) packing by zones (dust in separate band) costs ~30-36% global density:
dust acts as FILLER for gaps between large islands in global pack —
reserving a zone for it leaves those gaps empty (LFQuad: 703 vs 449 px/m). Visual order
of the atlas has a measurable price; let the consumer (artist) decide it.

Injective split of folded islands (method G, LFQuad v2): to separate stacked
regions WITHIN an island without re-projecting it (preserves authored unwrap): BFS by
mesh adjacency within the island, accepting faces into the sub-region as long as the
mapping remains injective (overlap test by sampling against region grid);
blocked face opens a new sub-region; sub-regions 1..n are moved outside (+2k in U)
to break loop continuity → the pack treats them as their own islands.
Measured result: 16 folded islands → 2-5 sub-regions each; density of A preserved
(690 px/m@2048) with overlap 88%→0.2%. Implementation: `LFQuad_dev\...\uv_methods_all.py §injective_split`.

## 0.6 FEW ISLANDS artist-style — TOPOLOGICAL cut, not by angle (added 2026-07-06, LFQuad v2 G13)

User feedback with real example: an entire object (wheel) = **4-5 islands**, not
hundreds. Rule that cost ~12 dead-end iterations:

**Fragmentation does NOT come from geometry — it comes from the algorithm cutting at every
sharp edge.** First measure SHELLS (edge-connected components): Banshee
wheel = 15 shells, bodywork = 13 shells. The **island floor = number of shells**
(an unwrapper cannot merge disconnected shells). If the model has 13 shells,
the target is ~13-30 islands, NOT 500-2000.

Methods that FRAGMENT (measured on tire, 7056 faces/1 shell):
`smart_project` any angle → **1115 islands** (splits at each tread); working
on authored UVs (already pre-fragmented) → 500-2000; sliver stitch → 544
(better, but still terrible). All attack the symptom.

**Method that WORKS — topological cut + anti-fold LSCM** (`uv_topological_unwrap.py`):
1. **Open closed shells**: a genus-0 closed shell (sphere/box/cap) has
   trivial homology → tree-cotree gives 0 cuts → remains closed → LSCM FAILS
   ("Unwrap failed to solve"). Mark the edges of ONE seed-face per closed
   shell as seam (slit) → each shell becomes a disk-with-boundary, always solvable.
2. **Tree-cotree** (minimal homological cut): primal spanning forest on
   VERTICES (short edges first → clean cuts); dual forest on FACES with
   non-primal manifold edges; edges in neither tree = cut graph
   (homology generators) → seams. Opens each shell into a disk with MINIMUM
   cuts (2·genus per handle).
3. **`unwrap(method="MINIMUM_STRETCH")`** = SLIM solver, anti-fold (much better
   than ANGLE_BASED/CONFORMAL to close without overlap).
4. PCA bisection of the few poorly-folded islands (8% threshold, **1 single pass** — the
   loop CASCADES: 26→508 islands if iterated).
5. normalize density → CONCAVE pack.

Measured result: **wheel 29 islands (3261 px/m@2048), bodywork 22 islands (857 px/m,
13 SAT pairs = almost clean)** — vs 508-2000 for all previous methods. The
layout is LEGIBLE (tire caps = 2 disks, rim = cross, tread = sweep).

Honest residual: closed CURVED shells (tire carcass, domed caps)
retain minor self-overlap after LSCM. Planar reprojection FOLDS them worse (they are
not developable); more cuts fragment. An artist relaxes or adds 1 seam per shell in
seconds. Perfect-zero-overlap automatic on closed curved surface = genuinely
hard problem (what RizomUV/auto-seams only half-solve).

bpy gotcha #4: `bm.to_mesh(me)` invalidates previous RNA refs (`me.uv_layers[..].data`)
→ recapture after each `to_mesh`.

## 1. Fundamentos orientados a diagnóstico

| Concept | What it is | Why it matters when diagnosing |
|---|---|---|
| Loop storage | UV lives in face-vertex, not in the point | Seams = points with >1 UV; runtime formats split the vertex |
| Seams / islands | Cuts to flatten the surface | Each island edge is a mip bleed point; tiny islands = unreadable bake |
| Overlap | Multiple faces over the same UV space | Legitimate for reading; breaks any bake |
| Mirrored islands | UV area with negative sign | Inverts tangent/bitangent → lighting seam with normal maps ([polycount](https://polycount.com/discussion/118218/the-dreaded-mirrored-seam-problem)) |
| Texel density | Texture px per surface meter | Uneven → sharp and blurry areas with the same file; see numbers §9 |
| Padding / mip bleed | Margin between islands | Without padding, mips average outside texels → seams that are only seen AT A DISTANCE ([polycount edge_padding](http://wiki.polycount.com/wiki/Edge_padding)) |
| Tiling outside 0..1 | Valid with sampler wrap | In RV it also triggers ODOL quantization (§2.2) |
| Degenerate UVs | Island collapsed to line/point | Texture stretched along an axis or single color; breaks tangent calculation (RPT "Error while trying to generate ST for points") |
| Multi UV sets | Extra channels | RV supports them (§2.1) and uses them for `_mc`/`_as`/Multi shader (§3) |

## 2. Where UVs live across formats

### 2.1 MLOD (editable, py3d)
- Per face-vertex: `point_index (u32) + normal_index (u32) + uv (2×float32)` —
  [`py3d/__init__.py:1012-1015`](../../tools/py3d/py3d/__init__.py) (site-packages, verified). Uncompressed. Default (0,0) `:992`.
- Face = 3-4 vertices + texture/material ASCIIZ per face (`:1044-1045`).
- TAGG `#UVSet#`: py3d WRITES it on save (`:1614-1619`, duplicating face
  UVs) and IGNORES it on read (`:1542`). The format supports **up to 8 UV sets** per LOD;
  set ID=0 is mandatory and duplicates that of the faces
  ([biki MLOD](https://community.bistudio.com/wiki/P3D_File_Format_-_MLOD)).
- py3d does NOT read/write sets >0 → any custom pipeline loses the 2nd set. The
  ODOL→MLOD converter likewise: "UV coordinates use the first UV set only; additional UV sets
  are dropped" (external converter doc, verified).

### 2.2 ODOL (binarized) — quantization
- Per UV set stores `float UVScale[4]` (minU,minV,maxU,maxV) + compressed pairs
  ([biki ODOLV4x](https://community.bistudio.com/wiki/P3D_File_Format_-_ODOLV4x)).
- Mechanism (armake `src/p3d.c`, [github](https://github.com/KoffeinFlummi/armake/blob/master/src/p3d.c)):
  normalizes each axis against the min/max of the ENTIRE LOD and quantizes to **int16** (~65534 steps).
  → **A single face with huge UV degrades the UV precision of the entire LOD.**
- Real binarize warning (RPT): "UV coordinate on point N is too big UV(153.36, 0.99) —
  the UV compression may produce inaccurate results"
  ([PMC arma.rpt](https://pmc.editing.wiki/doku.php?id=arma:arma.rpt)).
- Recommended limit [derivation, not official figure]: error < 0.5 texel if total LOD UV
  range ≤ ~64 (tex 1024) / **~32 (tex 2048)** / ~16 (tex 4096).
- armake also wraps per vertex and sets tileU/tileV flags depending on whether UVs go outside
  0..1 [inference from its code; BI binarize may differ].
- Custom parser: the `n_uv_sets` field exists in ODOL and a previous off-by-3 corrupted it
  (external converter doc, `SKILL.md:192-196`).

### 2.3 V-flip conventions between formats (#1 source of bugs in imports)
| Route | Flip | Citation |
|---|---|---|
| OBJ → p3d | `v_dayz = 1 − v_obj` | `LFQuad_dev\assemble_p3d.py:35` (`vt.uv=(u,1.0-vv)`) |
| p3d → glTF (viewer/inspector) | `1 − v` on export, un-flip on reconstruction | [`py3d/__init__.py:349,555`](../../tools/py3d/py3d/__init__.py); `dayz-3d-viewer/SKILL.md:151` |
| Blender internal | V=0 bottom (OpenGL) | The OBJ exporter already leaves it in OBJ convention |
- Rule: each converter must declare its convention; verify with an asymmetric checker,
  not with a flat texture (which is UV-invariant and hides the flip).
- source-game (.modelbin): brings **5 layers TEXCOORD0-4**; TEXCOORD2 = [0,1] per-part
  channel (swatch/AO), TEXCOORD0/1/4 = tiling absmax~30. `uv.active` picks the wrong layer →
  capture explicit: `bm.loops.layers.uv.get("TEXCOORD2")`
  ([`30_Sessions/2026-06-28-SUB_BRZ-fase5-texturas.md:25-33`](../30_Sessions/2026-06-28-SUB_BRZ-fase5-texturas.md); `<vehicle-import>\scripts\rip_p2_group.py:129-156`).
  On mirrored faces UV corners are inverted along with winding (`rip_p2_group.py:203`).

## 3. RVMAT, shaders and UVs

- `uvSource` per stage: `none, tex, tex1 (2º UV set), pos, norm, worldPos, worldNorm,
  texShoreAnim, texCollimator, texCollimatorInv`; default `tex`
  ([RVMAT basics](https://community.bistudio.com/wiki/RVMAT_basics), [Rvmat File Format](https://community.bistudio.com/wiki/Rvmat_File_Format)).
- `class uvTransform` (aside/up/dir/pos) = offset/deformation/repetition of the UV set;
  `aside.x`/`up.y` act as tiling U/V multipliers [semantics inferred from
  examples]: ACE Stage2 `_dt` with `aside={6,0,0} up={0,3,0}` = 6×3
  ([ace_vmh3.rvmat](https://github.com/acemod/ACE3/blob/master/addons/minedetector/data/ace_vmh3.rvmat));
  FC_Uaz body Stage2 `aside={16,0,0}` (LFQuad research 2026-06-14). `texGen=N` reuses.
- Super shader: Stage1 `_nohq`, Stage2 `_dt`, Stage3 `_mc`, Stage4 `_as`, Stage5 `_smdi`,
  Stage6 fresnel, Stage7 env. Flag "**use texture coords 2**": `_mc`/`_as` can read the
  2nd UV set ([Super shader](https://community.bistudio.com/wiki/Super_shader)) — the use
  case is baked AO without overlap on a tiled/mirrored base. The Multi shader also
  uses set 1 for its mask ([Mondkalb tutorial](https://community.bistudio.com/wiki/Mondkalb%27s_MultiMaterial_Tutorial)).
  ⚠ Our toolchain loses sets >0 (§2.1) → this path requires Object Builder.
- **UV-invariants** (work with broken UVs): solid color `_co`, procedural
  glass, flat-color rvmat with `texture=""` (LL-021). `hiddenSelectionsTextures[]/
  Materials[]` change texture/material WITHOUT touching UVs — that is why color variants
  of LFQuad work on bad UVs (`LFQuad\config.cpp:739-788`).
- **Damage/destruct**: `_destruct` rvmats use THE SAME UVs (all stages
  `uvSource="tex"`, identity transform) — verified in the official sample
  ([DayZ-Samples gorka destruct](https://github.com/BohemiaInteractive/DayZ-Samples/blob/master/Test_ClothingRetexture/data/gorka_normal_g_destruct.rvmat)).
  A re-unwrap breaks vanilla destructs; a retexture must respect the UV layout.

## 4. Normal maps and UVs

- `_nohq` = DirectX **Y− (green down)**: verified in-house against vanilla (LL-123,
  [`lessons-learned.md:2113-2127`](lessons-learned.md)) and triangulated in community
  ([PMC normal_maps](https://pmc.editing.wiki/doku.php?id=arma:texturing:normal_maps)).
  Cycles bake (Y+) → **G'=255−G ALWAYS** before exporting. The `.paa` swizzles X→alpha
  (DXT5nm); to audit a `_nohq` converted to PNG, un-swizzle first.
- Mirrored islands + `_nohq` → lighting seam on mirror axis and sunken relief
  on the mirrored side. Vanilla vehicles mirror entire sides and accept it
  ([retexture guide](https://steamcommunity.com/sharedfiles/filedetails/?id=238437456));
  cost: logos/text impossible on mirrored sides.
- Verify G polarity: zenithal light + feature with HORIZONTAL relief that only exists in
  the map; full-frame correlations are noise (LL-125, [`lessons-learned.md:2145-2157`](lessons-learned.md)).
- The UV-vs-texture IoU metric is CONFOUNDED by mirrored islands and partial coverage
  (0.28-0.81 even aligned) → the reliable gate is a render, not the metric
  ([`30_Sessions/2026-06-28-SUB_BRZ-fase5-texturas.md:32-33`](../30_Sessions/2026-06-28-SUB_BRZ-fase5-texturas.md)).

## 5. Bake Blender → DayZ (receta verificada in-house)

- **HARD ORDER — retopology invalidates previous UV** (P3D research 2026-07, Polycount): any
  retopo (`tencent/topology`, QuadriFlow, Voxel Remesh, Quad Remesher, AI auto-retopo) DISCARDS the UV of the
  source mesh. The sequence is fixed: generate → retopo → **re-unwrap** → finalize UV → bake → LODs.
  NEVER bake against a pre-retopo UV (maps end up poorly projected). The `bake-texture` (transfer
  high→low of 3d-ai-studio) thus goes from "optional tool" to mandatory step in any chain with
  retopo. Associated trade rule: a hard-edge/smoothing-split almost always needs a UV seam in
  the same place (seam-without-hard-edge OK; hard-edge-without-seam = #1 cause of seams in bake).

- **Unwrap BY SECTIONS, not by parts** (user feedback 2026-07-05 — "that is where
  the fault usually lies"): UV layout is organized by logical sections of the model
  (tank, chassis, seat, mudguards… — ideally aligned with named
  selections/materials), each section with its contiguous and recognizable islands, so
  that looking at the atlas one understands what part goes where. An auto-unwrap by loose
  parts/faces (Smart UV without manual seams) atomizes the model into thousands of anonymous islands →
  illegible atlas, impossible to paint or debug (measured case: LFQuad body §8, median
  2-4 faces/island). Smart UV Project works for AO/normal of already sectioned
  organic meshes (LFInfectedBig), NOT as authoring unwrap for a multi-part vehicle.
- Unwrap (parameters that worked): seams in hidden areas; Smart UV Project margin
  0.003 + `pack_islands(rotate=True, margin=0.008)` → bbox_fill 96.8%, stretch p10-p90
  0.82-1.13× (LFInfectedBig, [`30_Sessions/2026-06-25-LFInfectedBig-uv-bake.md`](../30_Sessions/2026-06-25-LFInfectedBig-uv-bake.md)).
- Normal bake high→low: selected→active, Cycles, extrusion+ray distance according to gap,
  margin ≥8px, Non-Color image. **Neutral prefill (128,128,255) + `use_clear=False`**
  (raycast misses stay neutral, not black/inverted).
- If the low was re-posed after retopo: **BakeProxy** = topo+UV of final low with
  pre-conform positions; tangent-space is pose-invariant (LL-159).
- AO: hide the high and everything except the low (self-occlusion) — mean 64→202 when doing so.
- Monochromatic models WITHOUT real texture: do NOT bake atlas; flat-color rvmat per material
  with `diffuse[]` and `texture=""` (LL-021 — origin of this doc: the Banshee/LFQuad).
- Padding for atlas: 2048→16px, gutter ≥2× ([polycount](http://wiki.polycount.com/wiki/Edge_padding)).

## 6. Catalog symptom → cause → diagnosis → fix

| In-game symptom | Probable cause | Diagnosis | Fix |
|---|---|---|---|
| Single flat color face | Missing/(0,0) UVs or collapsed island | `uv_audit.py` zero-uv%; OB Structure→Check Faces | Map; OB "neighbour mapping" for loose faces |
| "Wrong" texture repeated on different parts; AO with double spots | Bake over UVs with overlap | `uv_audit.py` OVERLAP MC per group and cross-group | Re-unwrap without overlap for bake, or AO to 2nd UV set ("use texture coords 2") |
| Lighting seam on central axis; sunken detail on one side | Mirrored islands + `_nohq` | `uv_audit.py` mirrored% (negative UV area) | Offset mirroring; re-bake with engine tangent basis |
| Sharp texture in OB but distorted/shimmer after binarizing | int16 quantization with huge UV range in LOD | RPT "UV coordinate on point N is too big"; bounds in `uv_audit.py` | Re-center tiling near 0; move tiling to rvmat (`uvTransform`); split materials |
| Swept/stretched texture on one axis | Degenerate UVs (planar map with bad view, broken import) | `uv_audit.py` degenerate%; RPT "generate ST for points" | Re-unwrap affected faces |
| Blurry despite large texture | Low or uneven texel density | `uv_audit.py` px/m; checker grid in-game | Re-scale islands to uniform density |
| Seams that only appear at distance | Mip bleed from short padding | View `.paa` mips; island padding | Edge padding §5/§9; atlas background similar to islands |
| Bake comes out black / holes / circles | Tiny islands on black background + UV drift | `uv_audit.py` islands (median faces/island) + density | LL-021: flat-color rvmat if model is monochromatic; otherwise, re-unwrap with larger islands |
| "Too many vertices" when binarizing | Excess UV/normal splits (resolved vertices) | Count seams; `dayz-binarize-vertex-limit` memory | Share normals/UVs where possible; fewer islands |
| Everything correct offline, wrong in-game | V-flip convention lost in a converter | Asymmetric checker through full pipeline | Apply/remove `1−v` at culprit step (§2.3) |
| Illegible atlas: unknown which island is which part; wrong part painted/baked | Automatic unwrap by loose PARTS/faces (Smart UV atomizes) instead of logical SECTIONS | `uv_audit.py` islands: low median faces/island (2-4) = atomized; open atlas and see if human reads it | Re-unwrap **by sections** (§5): a contiguous and recognizable UV area per section (tank, chassis, seat…), seams marked by hand |

## 7. Tool: `uv_audit.py` (LFQuad_dev\tools\)

MLOD auditor over py3d. Per visual LOD and texture|material group: zero-uv%, NaN,
bounds, degenerates, mirrored (signed UV area), **Monte-Carlo overlap** (robust
with subpixel islands), islands (union-find over shared UVs), texel density
(sqrt(uvA/3dA) → px/m at 2048), and cross-group overlap at LOD level.

Gotchas of the tool itself (learned while building it):
- Classic raster FAILS with subpixel islands (tris <1 texel do not cover any sample
  center) → hence Monte-Carlo with index grid.
- **Whitelist proxy faces** (selection `proxy:...`): they carry degenerate UV by design.
- **Exclude "full-frame" tris** (UV area >0.2) from cross-group overlap: a single face
  mapped to entire [0,1] (e.g. headlight lens) overlaps with everything and gives false 100%.
- Numbers "exactly 100%/0.000" = suspicion of tool artifact, not of model (G3).

## 8. LFQuad case (measured 2026-07-05, deployed p3ds)

- **Wheels (healthy reference, work in-game with real `_co`)**: zero-uv 0%, bounds
  [0.01,0.99], overlap 0.2-0.4%, mirrored ≤0.6%, density p50 ≈ **292 px/m** (2048).
- **Body**: UVs from Smart-UV-project of 2026-05-23 DID travel to p3d (0% zero-uv,
  0 NaN, bounds [0,1]) — "imported without UVs" = without texture using them, not without UVs.
  Real problems: **fragmentation** (b_black_1: 1859 islands/9732 faces, median 4;
  b_metal_2: 2154 islands, median 2), **density p50 ≈ 27 px/m** (10× worse than wheels;
  10cm part ≈ 2.7px → quantitative cause of LL-021 bake artifacts),
  overlap per group 0-2% with peak **b_white 18.7%** (the `color` selection), cross-group
  4.4%. Headlight face (`b_lights_fc_nolight`) maps full [0,1].
- The "87.5% overlap" from 2026-06-14 research **was not from the deployed p3d**: RESOLVED
  2026-07-06 — corresponds to ORIGINAL authored UVs of model (FBX
  `YAMAHA_BANSHEE_1987_BLEND_DIEZMADO.fbx`: bodywork B_WHITE MC overlap 88.3%,
  buckets 57-88%). Originals have good density (349-1900 px/m@2048) but
  massive overlap due to stacking of instanced parts → unusable for bake, usable
  for tiling/flat. Two different UV lineages: originals (dense+overlapped) vs
  smart-project of p3d (unique+atomized+27 px/m). Neither works for texture with
  detail.
- If detailed texture is ever wanted on body: current UVs do NOT work
  (density+fragmentation); re-unwrap (§5) + re-bake would be needed, respecting that
  current color variants (flat, UV-invariants) would continue working.

## 9. Reference numbers

| Metric | Value | Source |
|---|---|---|
| Edge padding | 1024→8px, 2048→16px; gutter ≥2× | polycount edge_padding |
| Props texel density | ~512 px/m | [Beyond Extent](https://www.beyondextent.com/deep-dives/deepdive-texeldensity) |
| FP weapons texel density | ~1024 px/m or more | Beyond Extent + polycount |
| Healthy internal reference | LFQuad wheels ≈ 292 px/m (2048) | audit 2026-07-05 |
| Max UV range per LOD (ODOL) | ~32 in tex 2048 [derivation] | armake p3d.c + PMC arma.rpt |
| Acceptable stretch (Blender) | p10-p90 within 0.8-1.2× | LFInfectedBig 2026-06-25 |
| Smart UV / pack | margin 0.003 / pack margin 0.008, rotate=True | LFInfectedBig 2026-06-25 |

## 10. Fuentes principales

Biki P3D [MLOD](https://community.bistudio.com/wiki/P3D_File_Format_-_MLOD) /
[ODOLV4x](https://community.bistudio.com/wiki/P3D_File_Format_-_ODOLV4x) ·
[armake p3d.c](https://github.com/KoffeinFlummi/armake/blob/master/src/p3d.c) ·
[Super shader](https://community.bistudio.com/wiki/Super_shader) +
[RVMAT basics](https://community.bistudio.com/wiki/RVMAT_basics) ·
[PMC arma.rpt](https://pmc.editing.wiki/doku.php?id=arma:arma.rpt) ·
[DayZ-Samples](https://github.com/BohemiaInteractive/DayZ-Samples) ·
py3d site-packages (verified in code) · vault: LL-021/123/125/159,
30_Sessions SUB_BRZ phase 5 + LFInfectedBig uv-bake.

Open UV pending items in projects: MercedesAMGLF B5 (interior "UV scrambled");
A6_Mk47 cosmetic V-flip unconfirmed in-game; source-game `--flip-green` if `_nohq`
comes out inverted in-game.
