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
- Every component MUST be named `ComponentXX` (e.g., Component01, Component02, up to Component2048)
- Every component MUST be **convex** — use Structure > Convexity > Component Convex Hull
- Every component MUST be **closed** (watertight mesh, no holes)
- Every component MUST have **mass assigned** (Alt-M in Object Builder, minimum 10 for character collision)
- Always run "Find Components" (Structure > Topology > Find Components) to validate
- Named property `class` = `house` is required for buildings

**In Blender:**
- Name objects as `ComponentXX_LODGeometry` for auto-assignment on FBX import
- Use Mesh > Convex Hull in edit mode to ensure convexity
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

**Common cause:** Axis rotation without compensating winding reversal.
Blender uses Z-up; DayZ uses Y-up. The -90° rotation around X
(`x'=x, y'=z, z'=-y`) changes face handedness. After applying this
rotation, ALL faces in ALL LODs must have their vertex order reversed.

**Fix in py3d:**
```python
for lod in model.lods:
    for face in lod.faces:
        face.vertices.reverse()
```

**Fix in Blender:**
- Select all faces → Mesh → Normals → Flip
- Or: Mesh → Normals → Recalculate Outside

**Applies to ALL LODs** — Geometry, Fire Geometry, View Geometry, and Shadow
LODs are affected too. Flipped Geometry faces cause physics pass-through;
flipped Fire Geometry faces cause bullets to pass through.

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
