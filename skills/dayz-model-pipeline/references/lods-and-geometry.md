# LODs & Geometry Rules for DayZ Models

## LOD Types and Their Purposes

### Resolution LODs (Visual)
These are what the player sees. Multiple LODs at increasing distances reduce rendering cost.

| LOD | Resolution Value | Purpose |
|-----|-----------------|---------|
| LOD 0 | 0.000 | Full detail — closest view |
| LOD 1 | 1.000 | ~50% of LOD 0 polygon count |
| LOD 2 | 2.000 | ~25% of LOD 0 |
| LOD 3+ | 4.000, 8.000... | Progressive simplification down to a box |

**Rules:**
- Do NOT make identical copies of LOD 0 for other levels — this wastes memory and gains nothing
- Each lower LOD should meaningfully reduce polygon count
- All resolution LODs need textures assigned (.paa paths)
- UV mapping must be consistent across LODs for the same texture

### LOD reduction method: planar dissolve is NOT a reducer on curved surfaces (added 2026-05-23)

DECIMATE type=DISSOLVE merges coplanar faces into n-gons, but a `.p3d` only stores tris/quads, so the n-gons must be triangulated. On a CURVED body (few coplanar faces) the dissolve barely merges, and triangulating the resulting n-gons RE-INFLATES the count — measured on LFQuad: LOD1 via planar = 122k tris > LOD0 = 60k. Planar dissolve does not reduce LOD triangle count for curved bodywork.

To reduce a LOD while PRESERVING a specific feature (radiator grille, logo, badge), use **DECIMATE COLLAPSE with a protected vertex group**: build a vertex group from the feature (often identifiable by material) and set `vertex_group=<group>`, `invert_vertex_group=True`, `vertex_group_factor=1.0`. This reduces exactly like plain collapse but keeps the feature intact. Measured on LFQuad at ratio 0.5/0.25/0.1 -> 78k/39k/15.6k tris with the grille (B_GRAY, 37 faces) preserved 37/37/37, whereas plain collapse gutted it to 26->9->3. Always re-check per-LOD triangle counts after decimating. (origin: LFQuad Fase B, LL-024)

### Geometry LOD (Collision)
Defines physical collision — what stops players and objects from passing through.

**Critical Requirements:**
- Every component MUST be named `ComponentXX` (e.g., Component01, Component02, up to Component2048).
  Far below 2048, a collision LOD with many pieces can make `binarize` fail with no message: 1,501
  pieces of a building failed, and 1,786 lighter ones passed ("Collision of a large building with an
  interior", below).
- Every component MUST be **convex** — use Structure > Convexity > Component Convex Hull
- Every component MUST be **closed** (watertight mesh, no holes)
- Every component MUST have **mass assigned** (Alt-M in Object Builder, minimum 10 for character collision)
- Always run "Find Components" (Structure > Topology > Find Components) to validate
- Named property `class` = `house` is required for buildings

**In Blender:**
- Name objects as `ComponentXX_LODGeometry` for auto-assignment on FBX import
- Use Mesh > Convex Hull in edit mode to ensure convexity. Check the result: hulls built by script
  with `bmesh.ops.convex_hull` came out folded by a few mm, and recomputed with Qhull they passed
  the convexity check (`dayz-p3d-audit` SKILL.md, "Source meshes for collision")
- Assign mass via the Arma 3 Object Builder addon's vertex mass tools

### Fire Geometry LOD (Ballistics/Damage)
Defines where bullets hit and what happens when they do.

**Critical Requirements:**
- Same component naming rules as Geometry LOD (ComponentXX)
- Components must be found (Find Components)
- **Materials define penetration** — assign penetration .rvmat files from `CA\Data\Penetration\`
  - `penetration\metal_plate.rvmat` — for metal objects
  - `penetration\wood.rvmat` — for wooden objects  
  - `penetration\glass.rvmat` — for glass
  - `penetration\concrete.rvmat` — for concrete
- **Thickness matters** — component thickness determines how bullet-resistant it is
  - Too-thick glass becomes bulletproof (unintended)
  - Model realistic thicknesses
- If two armor plates overlap, model them as ONE piece — overlapping fire geometry may cause bullet simulation errors

### View Geometry LOD (Occlusion)
Used by the rendering engine to determine what is visible and what is hidden behind objects.

**Requirements:**
- Components must be found
- Should be simpler than resolution LOD but accurate enough to occlude properly
- Poor view geometry causes performance issues AND gameplay issues (players visible when they shouldn't be)

### Shadow Volume LOD(s)
Casts shadows on ground, objects, and the object itself.

**Requirements:**
- Should be simplified compared to resolution LOD
- **Must be slightly SMALLER than the resolution LOD** — otherwise the object appears fully dark/shaded in-game (use Push modifier in Blender to shrink slightly)
- No textures applied
- ALL faces must be CLOSED
- Usually create two: one detailed (close range) and one very simple (far range)
- Shadow Volume 0.000 = detailed, Shadow Volume 10.000 = simple

### Memory LOD
Contains no visible geometry — only single vertices (memory points) that define:
- Animation axes (bone pivots)
- Interaction widget positions
- Sound emission points
- Bounding sphere overrides
- Central economy points (ce_center, ce_radius for loot spawning)

See `memory-and-selections.md` for detailed memory point documentation.

### Roadway LOD
Defines where characters can walk and what sound their footsteps make.

**Requirements:**
- Flat plane(s) where walkable surfaces are
- **All faces MUST face UP** — faces pointing down cause characters to fall through
- Can assign textures to define footstep sounds (wood, metal, concrete, etc.)
- Must be present below ladder memory points for ladders to work
- Must NOT overlap with Geometry LOD or characters will wobble
- If animated elements (bones) exist in roadway, max 255 points (127 in older versions)
- Max ~36m from center of origin — limits bridge length to ~72m per p3d

### Geometry PhysX LOD (Arma 3 / DayZ SA)
Copy of Geometry or Fire Geometry for PhysX physics interactions.
- Thrown objects (grenades etc.) interact with this LOD and Roadway LOD
- Should be as simple as possible — PhysX collisions are expensive

## Vertex Normal Limits
- DayZ (RV engine with DX9): max 32,768 vertex normals per LOD
- Exceeding this crashes the game or makes the LOD invisible
- Check with Bulldozer — if LOD doesn't display, you're over the limit

### Budget on the RESOLVED LOD0 (proxies summed - DX9 16-bit indices)

The 32,768-normal ceiling above is per LOD, but for a vehicle/attachment host the
figure that actually crashes the game is the **resolved LOD0**: the body mesh PLUS
every wheel/light/attachment proxy resolved and counted once per INSTANCE (4x wheel,
2x headlight, ...), not per source file. DX9 uses 16-bit indices, so the hard ceilings
on that resolved sum are **~32768 normals** and **~65536 vertices**. Cross either and
DayZ crashes on load or renders the LOD invisible - expensive to diagnose because each
part's own `.p3d` looks fine in isolation. Budget against both ceilings BEFORE
generating proxies/LODs.

Traps when trimming to fit:
- **Orphan normals** - cutting faces with py3d without reindexing leaves unreferenced
  entries in the normal pool, so the count does not drop. Measure *referenced* normals,
  not pool length.
- **Merge-by-distance before decimating** - a triangle-soup mesh has verts = 3x faces;
  welding coincident verts first collapses the count for free before any decimate.
- **Duplicate-resolution LOD ladder** - two LODs at the same resolution value is an
  invalid LOD set; each lower LOD must be a strictly coarser (larger) resolution value.

(origin: SP-009, LL-026, kt_roadkill_armed bug-011)

## Face Normals & Winding Order (Texture Visibility)

The RV engine uses face winding order to determine which side of a face is
"outward" (textured/visible) vs "inward" (invisible/backface-culled).

**Symptoms of wrong winding order:**
- Textures render on the interior of the model instead of the exterior
- Object appears transparent or invisible from outside
- Object appears solid black from outside (shadow-only)

**Rule (source: [`SKILL.md`](../SKILL.md), Rule 12):** Blender-authored geometry and
GLB/glTF-sourced geometry brought through Blender take the same det=-1 map, and
neither is reversed (a glTF read without Blender: SKILL.md "GLB/glTF imports"):
- **Blender-authored geometry** via the reflection `x'=x, y'=z, z'=y` (det=-1):
  apply it to ALL vertices and normals in ALL LODs, keep the vertex order (it comes
  out INWARD, the MLOD convention) and negate the normals. The old det=+1 rotation
  `z'=-y` ships a MIRRORED model (measured in game 2026-10-01).
- **GLB/glTF-sourced geometry** brought through Blender is Blender geometry: glTF
  front faces are CCW like Blender's, and Blender's glTF importer keeps them so. The
  same map, order and normals apply. Reversing the faces after the det=-1 map turns
  them OUTWARD, which rendered inside-out in game (MercedesAMGLF, 2026-06-24; SKILL.md
  "GLB/glTF imports").
Never assume: `check_face_winding` must read ~0% flipped, but it only shows that the
vertex order and the normals agree, and an inside-out export with both outward reads
the same.

**In py3d:** `py3d.blender_to_dayz(model)` (py3d 1.8.0 and later) maps a model in
Blender space; call it before adding anything built in DayZ space. With
`P3D.transform(((1, 0, 0), (0, 0, 1), (0, 1, 0)))` instead, det<0 makes it reverse
every face, proxy triangles included: reverse them all back and negate every normal,
which leaves the original order (`references/py3d-direct-generation.md`, "Blender
Z-up → DayZ Y-up Rotation").

**In Blender:** a GLB/glTF import needs no flip. Before export, faces should show
blue from outside in the Face Orientation overlay (`blender-visual-review`). If some
show red, select all of the mesh's faces (not the proxy triangles), use Mesh →
Normals → Recalculate Outside and check the overlay again: on an open mesh it can
guess wrong. Mesh → Normals → Flip turns the selected faces inward, and Rule 12's map
then turns them OUTWARD.

**Apply the map to ALL LODs** — Geometry, Fire Geometry, View Geometry, Shadow and
Memory LODs included — so that they all land in one convention. A collision LOD left
OUTWARD lets the LOD raycasts through, the `view` and `fire` rays that actions and
ballistic hits rely on (`dayz-p3d-audit` killer #1, measured in game 2026-10-02). On
the 2 m boxes measured there, physics still stopped a walking player; a walk alone
does not diagnose winding, since the 0.49 m `item_small` kit let the player through
with either winding.

*(Aligned 2026-10-03 with SKILL.md Rule 12 and "GLB/glTF imports". The rule opened "The
winding decision is conditional on the asset source (Blender-authored vs GLB/glTF) — both
maps below are det=-1 — with two cases:"; its GLB case read "**GLB/glTF-sourced geometry**
via the pure swap `(x,y,z)->(x,z,y)` (det=-1): ALWAYS reverse the vertex order of every face
in every LOD, except proxy triangles, whose vertex order encodes the attachment frame."; and
it closed "Never assume either case: verify post-assembly with `check_face_winding`; it must
read ~0% flipped." The py3d fix, titled "Fix in py3d for the GLB/glTF source case:", ran, since #68
(2026-10-03), `import py3d # After the swap, applied to points and normals with every face's
vertex order kept. # A proxy triangle, the only face of a 'proxy:<path>.<index>' selection when
it is a # triangle, keeps its order. A selection under a proxy name with more faces, or a quad, #
holds geometry: its faces are reversed with the rest. Weight 0 is not membership. keep, faces,
lists = set(), set(), set() for lod in model.lods: for name, sel in lod.selections.items():
sel_faces = [face for face, weight in sel.faces.items() if weight > 0] if
(py3d.PROXY_NAME_RE.match(name) and len(sel_faces) == 1 and len(sel_faces[0].vertices) == 3):
keep.add(sel_faces[0]) for face in lod.faces: # A Face listed twice, or two faces sharing one
vertex list, would be reversed # twice: refuse before anything changes. if id(face.vertices) in
lists: raise ValueError("a vertex list is listed twice: give each face its own")
lists.add(id(face.vertices)) faces.add(face) for face in faces - keep: face.vertices.reverse()`
on 22 lines, followed by "`P3D.transform()` with the swap matrix reverses every face itself,
proxy triangles included, because det<0: after it, reverse only the proxy triangles back. The
loop above, run after `transform()`, undoes the reversal of every other face and leaves the
proxies reversed (measured offline, py3d 1.9.0)." and by the note "(Fixed 2026-10-03: the block
read `for lod in model.lods: for face in lod.faces: face.vertices.reverse()`, on three lines,
which reversed the proxy triangles too, against the rule above.)"; the
Blender fix, titled "Fix in Blender for the GLB/glTF source case:", read "Select all faces →
Mesh → Normals → Flip" and "Or: Mesh → Normals → Recalculate Outside"; and the last paragraph
read "**When Rule 12 requires reversal, it applies to ALL LODs except proxy triangles** —
Geometry, Fire Geometry, View Geometry, and Shadow LODs are affected too. Flipped Geometry
faces cause physics pass-through; flipped Fire Geometry faces cause bullets to pass
through." Killer #1 measured outward 2 m collision boxes that still stopped the player.)*

<!-- [repaired 2026-06-05: plugin file was truncated at "## Nami" (Edit >5KB bug); full section restored from <claude-home>\skills user copy] -->
## Naming Convention in Blender for FBX Export

Objects in Blender must follow this naming scheme to auto-assign LODs on import to Object Builder:

```
{selectionName}_LOD__{resolution}     → Resolution LOD (note: double underscore)
{selectionName}_LODGeometry           → Geometry LOD
{selectionName}_LODFireGeometry       → Fire Geometry LOD
{selectionName}_LODViewGeometry       → View Geometry LOD
{selectionName}_LODShadowVolume       → Shadow Volume LOD
{selectionName}_LODMemory             → Memory LOD
{selectionName}_LODRoadway            → Roadway LOD
```

**Example for a simple box:**
```
LOD0_LOD__0.000          → Resolution LOD 0
LOD0_LOD__1.000          → Resolution LOD 1
Component01_LODGeometry  → Geometry LOD component
Component01_LODFireGeometry → Fire Geometry component
```

**FBX Import Settings in Object Builder:**
- Check the "LODs" checkbox in the import dialog
- Set Master Scale to **0.01** (Blender exports 100x too large)
- After import: Structure > Squarize All LODs to clean up triangulation
- After import: Structure > Convexity > Component Convex Hull on Geometry LOD


### Total LOD count ceiling (added 2026-07-14)

Keep total LODs per model under ~30. The BI LOD wiki warns that **30 or more LODs in total
can crash the binarizer**. This counts ALL LOD types together (resolution + geometry + fire
+ view + shadow + memory + roadway...), not just resolution LODs. (Source: BI LOD wiki,
cited in YouTube tutorial BrW7V1lFbmQ 2026.) The rest of the resolution-LOD authoring those
tutorials show -- copy LOD0, decimate ~50%/25%/12%, set textures/sections BEFORE cutting
LODs so they carry over -- is already covered above and in `blender-headless.md`; this
ceiling is the one extra hard limit.

## Collision of a large building with an interior (SP-453, SP-457, SP-458, added 2026-10-03)

Measured on one project: a rock-shaped building generated from Blender, with a hangar, an attic,
a ground-floor room and a lift inside (SecretRock RocaHeli, rounds R7.1 to R7.3, 2026-10-01 to
2026-10-03). Its collision is hundreds of convex pieces per model. Every figure below comes from
that project; none was re-measured on another model.

### MLOD size grows with the square of the piece count

[OFFLINE MEASURED] An MLOD stores each named selection as one byte per point and one byte per
face of its LOD (py3d writes `len(all_points) + len(all_faces)` bytes per selection,
`tools/py3d/py3d/__init__.py:1968-1974`, py3d 1.10.1), and every `ComponentNN` is a selection.
N pieces of k points and f faces each make a LOD of about N·k points and N·f faces, so their
selections take about N²·(k + f) bytes in each collision LOD (arithmetic on that layout). With
1,150 pieces in Geometry, View and Fire, the rock's MLOD weighed 478 MB; with 827 to 997 pieces
of 6 points each and a separate, coarser View Geometry that kept the functional pieces (doors,
buttons), 55-75 MB. The binarized ODOL does not carry the cost (78.4 MB of MLOD became 2.1 MB of
ODOL); the MLOD does, and in a Git repository it needs LFS past GitHub's 100 MB. The separate
View did not last: in R7.3 its own set of pieces left 28 % of the skin open to the project's ray
test and went past 2,048 components, so the View went back to the Geometry's pieces.

Before assembling, clean the source meshes and check the hulls: zero-area faces, orphan points,
faces wound against their normals and `bmesh.ops.convex_hull` hulls that are not exactly convex
are in `dayz-p3d-audit` SKILL.md, "Source meshes for collision".

### Which room a point belongs to: no membership test on open meshes

[OFFLINE MEASURED] Interior surfaces are open meshes (floors and ceilings are other objects).
Near their edges, cross-sections of the lining, upward rays and the side of the nearest surface
all placed points in the wrong room. What worked (R7.1): each patch extruded behind its visible
side up to the next visible surface along a ray, minus 3 cm; analytic hard volumes for what
moves (platform travel, lift cabin, doors); and floor slabs by convex decomposition of the
outline, minus convex holes cut by half-planes.

### Collision that follows the visible face (R7.3)

1. [OFFLINE MEASURED] Patches from k-means clusters of random samples stand far behind a wall
   that curves tightly: the hull's chord enters the room, and the cut that removes it leaves the
   patch far back. On the hangar lining, 38 % of the wall had its collision more than 15 cm
   behind, and the corners up to 1 m, the probe's limit. Prisms built per region of near-flat
   faces, each extruded from 0.5 cm behind the region's deepest face to 3 cm short of the next
   visible surface behind it, gave a median of 1 cm and less than 2 % beyond 15 cm. That reading
   is of the prisms alone, before the generator's room and hard-volume test thins, splits or
   drops a prism that enters a room; the full model was not part of it.
2. [OFFLINE MEASURED] Extrude along the face's geometric normal turned toward its visible side,
   not along the mean of its corner normals: next to a crease the smoothed normal leans by up to
   ~45°, and prisms along it stood up to a face's width behind their far corner (median 10.5 cm);
   along the geometric normal, 1 cm.
3. [OFFLINE MEASURED] Grow the regions by position, not by topology. The room meshes, like the
   vanilla skin, are triangle soups: 1,872 faces gave 1,843 regions with neighbours by shared
   edge, and 652 with neighbours by corners closer than 2 cm (flatness tolerance 8 cm).
4. [OFFLINE MEASURED] A room test that only looks down and up (floor below, ceiling above) counts
   the rock of a door's lintel and jambs as room: the pieces there were rejected and a
   0.84 × 1.55 m gap opened (131 of 368,013 samples of the project's hole probe). A room's ceiling
   can also be another object, such as the slab of the room above: without it the vertical test
   missed the room almost everywhere, and pieces entered it by up to 0.40 m. Rule: floor below,
   ceiling above, and 3 of 4 horizontal rays that hit the visible side of the walls.
5. [OFFLINE MEASURED] Random samples miss the seams: four passes of 60,000 samples left 0.15 % of
   the skin open. Testing every exterior triangle at 7 points finds the triangles with a hole in
   one pass.

### Binarize: the visual budget

[OFFLINE MEASURED] Binarized with its Visual LOD 0 only, textures and materials on: R7.1 in one
model, with smooth normals, gave `CAPACITY_FAIL` at 92,430 resolved vertices (py3d
`(point, normal, uv)` count). Split into the rock (49,929) and the interior with smooth normals
on its inner face (42,501), both passed. The rock passed above the HH-60G's cliff of 46,133, so
that cliff does not carry over to another model (`dayz-vehicles`
`references/binarize-vertex-budget.md`, item 4). Split normals on a height-field face more than
triple its resolved vertices: the attic's inner face, 33,046 triangles, counted 56,743 with split
normals and 17,392 with smooth ones (a triple counter run in Blender, a lower bound).

### Binarize: a silent limit on the collision LODs

1. [OFFLINE MEASURED] With 1,843 convex pieces in Geometry, View and Fire, `binarize.exe` wrote
   no ODOL and printed no capacity line: the three-state bench read `OTHER_FAIL`, and no message
   explained it.
2. [OFFLINE MEASURED] It is not the file size: a 247.8 MB MLOD failed and a 264.4 MB one passed.
   Without its collision LODs, the same model passed.
3. [OFFLINE MEASURED, variable not isolated] The boundary over 9 variants, read per collision LOD
   (a variant without its View LOD failed like the full one):

   | Per collision LOD | Largest that passed | Smallest that failed |
   |---|---|---|
   | Faces | 28,124 | 32,766 |
   | Named selections × points | 31.5 M | 33.9 M |
   | Selection bytes | 81.7 M | 83.7 M |
   | Pieces | 1,786 | 1,501 |
   | Points | 22,281 | 22,281 |

   The first three separate the passes from the failures equally well (2^25 = 33.6 M lies between
   the two products); the piece count and the point count alone do not. A cap at 32,768 faces is
   ruled out: 32,766 already failed. A variant with few faces and many selections would decide it;
   it was not run.
4. [OFFLINE MEASURED] A truncated MLOD gives the same `OTHER_FAIL`: one variant was cut off while
   being written, inside its Geometry LOD. Before reading an `OTHER_FAIL` as this limit, walk the
   MLOD to the `#EndOfFile#` tagg of every LOD.
5. Rule (the project's, applied to the models it shipped): before binarizing, measure each
   collision LOD with a header reader. Points and faces are in each LOD's `P3DM` header, and the
   named selections and their bytes in its TAGG list, which a reader skips through by each tagg's
   size without loading the file (seconds for 350 MB). Where any of the three measures is above
   the largest value known to pass, move pieces to another model with the same transform, created
   and deleted with the main one. Do not merge or decimate pieces to fit.
6. [IN-GAME VERIFIED, DayZDiag 1.29, 2026-10-03] The separate model works: a collision-only
   `House` class of 602 pieces, spawned with the rock at its transform. A `geom` ray cast from
   30 m out toward the rock stopped on one of its pieces, and the project's battery of 1,188 rays
   per LOD from outside found 0 holes in Geometry, Fire and View.
