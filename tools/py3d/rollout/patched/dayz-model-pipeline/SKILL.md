---
name: dayz-model-pipeline
description: >
  Skill for generating complete DayZ mod objects autonomously — from 3D models to game-ready
  .p3d files with LODs, memory points, named selections, procedural textures, .rvmat materials,
  animations (model.cfg), and config.cpp. Primary path: Blender headless for pro geometry
  (bevel, subdiv, booleans, Smart UV, AO bake, auto LOD decimate) + py3d for .p3d assembly.
  Textures use OpenSimplex FBM multi-layer compositing. Use when user mentions: Object Builder,
  p3d files, LODs, memory points, named selections, model.cfg, PBO packing, 3D models for DayZ,
  animated objects, procedural textures, .rvmat materials, or LF_PowerGrid electrical mod objects.
  Also trigger for Blender-to-DayZ workflow or generating models from scratch.
---

# DayZ Model Pipeline — Complete Autonomous Object Generation

This skill enables generating complete DayZ mod objects from scratch — 3D model, textures,
materials, animations, and all config files — using Python and Blender headless.
Primary path uses Blender for pro-grade geometry (bevel, subdiv, booleans, Smart UV,
AO baking, auto LODs via decimate) + py3d for .p3d assembly. Fallback path uses
py3d only for quick prototyping without Blender.

## Capabilities

1. **Blender headless geometry** (bevel, subdivision, boolean cutouts, shade smooth)
2. **Automatic LOD generation** via Blender Decimate modifier (LOD0 → LOD3)
3. **Smart UV projection** and AO baking from real 3D geometry
4. **Procedural texture generation** via Pillow + OpenSimplex (coherent noise FBM, multi-layer compositing)
5. **Direct .p3d assembly** via py3d library (LOD packaging, named selections, memory points)
6. **Full LOD pipeline** (Resolution, Geometry, Fire Geometry, View Geometry, Shadow, Memory)
7. **Animation setup** (model.cfg with skeletons, bones, rotation/translation animations)
8. **Config generation** (config.cpp with AnimationSources, DamageSystem, hiddenSelections)
9. **Material generation** (.rvmat files with emissive support for LEDs/indicators)
10. **Complete addon packaging** ($PBOPREFIX$, folder structure ready for AddonBuilder)
11. **Interactive 3D preview** via Three.js HTML artifacts for visual validation before generating

## Quick Reference

Before doing anything, read the relevant reference file:

- **Wheeled vehicle? READ FIRST, before baking** → `references/vehicle-structural-parity.md`. A from-scratch vehicle reveals the pieces a real DayZ vehicle has of stock (Geometry wheel hubs, crew proxies in ViewGeometry, FireGeometry damage zones, lights, AnimationSources) one error at a time in-game unless you extract the full anatomy up front. Debinarize the civiliansedan once, diff against it, build every missing piece in one pass — that is the anatomy a project's readiness gate expects in hand before the spec is written (LL-030).
- **Wheeled vehicle config.cpp + model.cfg (complete, worked example)** → `references/vehicle-config-and-modelcfg.md`. The full car class: SimulationModule (engine/gearbox/drive/differential/suspension), Crew, lights, DamageZones, cargo, wheel/door items + slots + proxies, sound, AnimationSources, plus the matching model.cfg (CfgSkeletons bone hierarchy + wheel/steering/damper animations). Reproduces a verified working car (Tyson89/Landrover). Read AFTER vehicle-structural-parity.md.
- **Wheeled vehicle per-LOD content, memory points & proxies** → `references/vehicle-structural-parity.md` Addendum 2026-05-30b (what each LOD carries for a car, the full memory-point catalog, and proxy placement per LOD).
- **Blender headless pipeline (PRIMARY)** → `references/blender-headless.md`
- **Procedural texture generation (OpenSimplex)** → `references/procedural-textures.md`
- **Direct P3D assembly (for LOD packaging)** → `references/py3d-direct-generation.md`
- **LODs & geometry rules** → `references/lods-and-geometry.md`
- **Memory points & named selections** → `references/memory-and-selections.md`
- **Animations (model.cfg)** → `references/animations.md`
- **Config.cpp & addon structure** → `references/config-and-packing.md`
- **Blender manual workflow (ALTERNATIVE)** → `references/blender-workflow.md`
- **LF_PowerGrid object recipes** → `references/lfpg-recipes.md`
- **AnswerOverflow community findings (mined 2026-05-17)** → `references/answeroverflow-2026-05-17.md` (binarize misalignment on personality meshes, nested proxy disappearance on binarized models, Maya Object Builder alternative)

## Pipeline Overview

### Path A: Blender Headless + py3d Assembly (PRIMARY)

This is the PRIMARY path. Blender generates pro-grade geometry; py3d assembles the .p3d.
Install: `apt-get install -y blender && pip install opensimplex --break-system-packages` + py3d fork DayZ (bloque CRITICAL abajo).

> **CRITICAL: py3d installation** — Do NOT use `pip install py3d` (different
> point-cloud library) and do NOT install upstream from GitHub anymore. Use the
> **py3d DayZ fork >= 1.2.0** (codec KoffeinFlummi + guards anti-corrupcion,
> constantes LOD DayZ, `validate()`, proxies, recipe y CLI `python -m py3d`),
> vendorizado como wheel en `wheels/` de esta skill (D2=B):
>
> ```bash
> SKILL_DIR=<dir de esta skill>
> # py3d DayZ fork >= 1.2.0 (wheel vendorizada en esta skill - D2=B).
> # NUNCA `pip install py3d` (PyPI = point-cloud lib) NI git+upstream (sin guards).
> pip install --break-system-packages "$SKILL_DIR"/wheels/py3d-*-py3-none-any.whl 2>/dev/null \
>   || pip install --break-system-packages $(ls /sessions/*/mnt/*/_tools/py3d/dist/py3d-*-py3-none-any.whl 2>/dev/null | sort -V | tail -1)
> python3 -c "import py3d; assert getattr(py3d,'IS_DAYZ_FORK',False) and tuple(map(int,py3d.__version__.split('.')))>=(1,2,0), (py3d.__version__, py3d.__file__)"
> ```

**Step 1: Define the Object**
- User describes what the object does, how it looks, what moves
- Identify: static parts, animated parts, interaction points, electrical connections
- Select recipe from `lfpg-recipes.md` or define a new one

**Step 2: Create Interactive Preview (Optional but Recommended)**
- Generate a Three.js HTML artifact showing the object in 3D
- Include state toggles (on/off/disconnected, open/closed, etc.)
- Let the user validate the design before generating the real model

**Step 3: Generate Geometry in Blender Headless**
- See `references/blender-headless.md` for complete API reference
- Create geometry using primitives + modifiers (bevel, subdiv, boolean)
- Apply shade smooth for curved surfaces
- Run Smart UV Project for automatic UV mapping
- Export LOD0 as OBJ (full detail, ~1500-2000 verts for small objects)
- Auto-generate LOD1/2/3 via Decimate modifier (ratios: 0.50, 0.25, 0.12)
- Optionally bake AO map from real geometry (Cycles, 64+ samples)
- Save .blend reference file

**Step 4: Generate Procedural Textures (Coherent Noise Pipeline)**
- See `references/procedural-textures.md` for complete API reference
- Use OpenSimplex coherent noise + FBM for organic detail
- Multi-layer compositing: base + flow + grain + micro + wear + sparse detail
- If AO was baked in Step 3, composite it into diffuse (multiply blend)
- Generate _co, _nohq, _smdi maps per surface at 512x512
- Output as .png (user converts to .paa with TexView/Pal2PacE)
- NEVER use random()-per-pixel for surface patterns

**Step 5: Assemble .p3d (py3d library)**
- See `references/py3d-direct-generation.md` for py3d API
- Read Blender OBJ exports → build visual LODs (0.0, 1.0, 4.0, 8.0)
- Generate Geometry/Fire/View LODs as convex boxes (py3d primitives — these don't need Blender quality)
- Generate Memory LOD with animation axes, port points, actionPos, CE center
- Add named selections across all LODs
- Assign texture/material paths (.paa, .rvmat)
- Write .p3d binary, verify by reading back

**Step 6: Generate Materials (.rvmat)**
- Standard materials per surface type
- Emissive materials for LEDs (green, red, off)
- Penetration materials for Fire Geometry

**Step 7: Generate model.cfg + config.cpp**
- CfgSkeletons, CfgModels, animations
- CfgVehicles with AnimationSources, hiddenSelections, DamageSystem
- Class name MUST match .p3d filename

**Step 8: Package**
- $PBOPREFIX$, folder structure, output .zip

**User's only remaining steps:**
1. Convert .png → .paa (TexView or Pal2PacE)
2. Pack with AddonBuilder → .pbo
3. Test in-game

### Path B: py3d Only (Fallback — Quick Prototyping)

Use when Blender is unavailable or for very simple geometry (cubes, basic cylinders).
Generates everything in pure Python. Lower quality but zero dependencies beyond pip.
Follow Steps 1-8 above but skip Step 3 (Blender) and generate geometry directly
in Step 5 using py3d primitives. See `references/py3d-direct-generation.md`.

### Path C: Blender Manual Workflow (Alternative)

Use when the user already has a complex mesh from an external source (.fbx, .obj, .glb)
that cannot be generated procedurally. See `references/blender-workflow.md`.

### Path C: 3D Model Viewer/Tagger (For External Models)

For cases where the user imports a model and needs to tag parts interactively:
- Build a Three.js artifact that loads .glb files
- User clicks parts to label them (animated, static, axis location)
- Claude generates the configuration from the labels
- Requires the model in .glb format (export from Blender if needed)

## Critical Rules (Common Mistakes)

1. **Geometry LOD components MUST be convex** — non-convex geometry causes collision failures
2. **All Geometry/Fire/View LOD components MUST have mass** — minimum 10 for character collision
3. **Fire Geometry thickness matters** — too thick glass becomes bulletproof
4. **Shadow LOD must be slightly smaller than visual LOD** — otherwise object appears fully shaded
5. **Memory points are single vertices** — not edges, not faces
6. **Animation axes need exactly 2 points** — defining a line in 3D space
7. **Named selections must be consistent across LODs** — same name in Resolution, Geometry, Fire, View
8. **Texture paths in p3d must use .paa** — not .png or .tga (but generate as .png, user converts)
9. **model.cfg class names must match p3d filenames** — e.g., class MyObject for MyObject.p3d
10. **LOD resolution values matter** — wrong values = engine doesn't recognize the LOD type
11. **Always verify the .p3d** — read it back with py3d after writing to confirm integrity
12. **Blender Z-up → DayZ Y-up rotation is MANDATORY** — Blender exports with Z as up-axis; DayZ uses Y-up. Apply `x'=x, y'=z, z'=-y` to ALL vertices AND face normals in ALL LODs. Failing to do this makes models spawn sideways or upside-down. See `py3d-direct-generation.md`.
13. **Rotation MUST be paired with winding-order reversal** — the axis swap changes face handedness. After rotating, reverse the vertex order of every face (`face.vertices.reverse()`) or textures will render on the inside of faces (invisible exterior). This applies to ALL LODs, including Geometry/Fire/View/Shadow.
14. **Attachments require proxy system (3 parts)** — for items to render visually when attached: (a) proxy face + selection in visual LODs of the parent p3d, (b) a proxy p3d referenced by the selection, (c) `CfgNonAIVehicles` entry mapping `inventorySlot` to the proxy model. Missing any part = attachment is logically present but invisible. See `memory-and-selections.md` and `config-and-packing.md`.
15. **Proxy selections use special naming** — `proxy:addon_path\proxy_model.p3d.NNN` where NNN is a 3-digit index starting at 001. The face assigned to this selection defines position and orientation of the rendered attachment.
16. **`autocenter=0` named property required on EVERY collision LOD** — not just Geometry. Without it on FireGeometry / ViewGeometry / Roadway / Hitpoints / LandContact, the engine recenters that LOD's mesh based on its bbox center, displacing the collision mesh from the visual mesh by half-height (typically 20-25cm Y). Empirical symptoms: bullets pass through, hologram raycast falls through to ground when stacking, action cursor doesn't register the object. Detection: `lod.properties.get("autocenter") != "0"` on any collision LOD. Fix: `lod.properties["autocenter"] = "0"` on all collision LODs, then write back. Vanilla reference: LFPG `gate_and.p3d` has `autocenter=0` on Geometry, ViewGeometry, FireGeometry uniformly.
17. **Every face in collision LODs needs a penetration `.rvmat`** — assign `face.material = "dz\\data\\data\\penetration\\<surface>.rvmat"` (e.g. `wood_desk` for wood, `metalplate` for metal, `plastic` for plastic). The .rvmat references a `.bisurf` that defines ballistic properties (penetration thickness, deflection, damage). Without this assignment, ObjIntersectFire raycasts hit the geometry but the engine cannot resolve a surface — bullets pass through, no footstep sound. Vanilla: `wooden_case` has every collision-LOD face assigned to `wood_desk.rvmat`. Detection: `(face.material or "").strip() == ""` on any collision LOD face is a fail.
18. **Post-export winding verification (Check C) — Check A is INSUFFICIENT** — Rule 13 (winding reverse after Z→Y rotation) can be silently skipped without Check A noticing, because Check A (`cross(e1,e2)` vs declared normal) returns UNIFORM_NON_FLIPPED in BOTH the broken and rotated-but-not-flipped states. The reliable check is **Check C: per-component-centroid outward direction**. For each face in each collision LOD, compute `outward = face_centroid - component_centroid` and `cross_n = normalize(cross(v1-v0, v2-v0))`. If `dot(outward, cross_n) > 0` for most faces, the cross-product is OUTWARD — engine raycast `ObjIntersectFire` treats faces as back-facing, raycast misses. Expected DayZ state: `dot(outward, cross_n) < 0` (cross product INWARD), matching vanilla LFPG `gate_and` and DayZ engine's expected face orientation. Symptom triplet of Rule 13 not applied: bullets pass through + hologram falls to ground when stacking + items can't be placed on top — all three simultaneously means cross-product is OUTWARD on collision LODs. Fix: `for face in lod.faces: face.vertices.reverse()` on every collision LOD (NOT Visual — Visual renders fine in either state thanks to per-vertex declared normals). Implementation: see `flip_collision_winding.py` pattern in `references/py3d-direct-generation.md`.

19. **Wheel proxy `.p3d` Memory LOD MUST contain the 5 anatomical mem-points** — `ce_center`, `ce_radius`, `boundingbox_min`, `boundingbox_max`, `invview`. PhysX uses them to build the wheel collider; without them the engine defaults to the Geometry LOD of the proxy (typically a cube ~0.20³ on procedural wheels) as the collider. Result: wheel collider the size of the hub cube instead of the wheel diameter → `wheelPresent=N` but `contact=0` permanent → suspension raycast misses ground when body lifts more than ~10 cm → bounce divergente, eventually `Will delete object with !finite or outside world coords`. The 5 mem-points follow Croco-vanilla convention (Y vertical/radial, X axial/width, Z radial with INTENTIONAL min/max inversion) — copy literal and scale, do not normalize Z inversion. Full anatomy + scaling rules in `references/vehicle-structural-parity.md` §"Addendum (2026-05-29) — Wheel proxy `.p3d` Memory anatomy (T1-D)". Bake them with py3d using the 6 quirks in `dayz-animation-pipeline/references/py3d-1.0.0-quirks.md`. This invariant is silent in `dayz-p3d-audit` until 2026-05-29 (Silent Killer #11) — older audits may pass a wheel proxy with only `ce_center` as ALL PASSED. Origin: LFQuad bounce 2026-05-29; LL-057 (process — gap diferido sin gate).

## LOD Resolution Values Quick Reference

**DayZ-modern values** (verified against Mikero DeP3d docs and vanilla items
55galdrum, wooden_case, sea_chest, MilitaryCrate, gate_and). Old Arma 3
values (FireGeo=2e13, ViewGeo=3e13, GeoPhys=4e13) DO NOT work in DayZ —
the engine ignores LODs at those resolutions.

| LOD Type | DayZ Resolution Value | Notes |
|----------|-----------------------|-------|
| Resolution 0 (full detail) | 0.0 | Visual |
| Resolution 1 | 1.0 | Visual |
| Resolution 2 | 4.0 | Visual |
| Resolution 3 | 8.0 | Visual |
| Shadow Volume (close) | 10000.0 (1.0e4) | optional |
| Shadow Volume (far) | 11000.0 (1.1e4) | optional |
| Geometry | 1.0e13 | physics + cursor raycast |
| Memory | 1.0e15 | named points, animation axes |
| LandContact | 2.0e15 | ground placement contact points |
| Roadway | 3.0e15 | walkable surface (stack base) |
| Hitpoints | 5.0e15 | named hit zones for damage |
| ViewGeometry | 6.0e15 | action cursor + occlusion |
| FireGeometry | 7.0e15 | ballistic raycast (bullets) |

## Proven Reference Implementation: LFPG Push Button

A complete working example exists as the LFPG Push Button (worn industrial style):
- 9 LODs, 218KB .p3d file, generated entirely in Python
- 328 vertices at LOD 0 (32-segment cylinders + dome)
- Animated button (translation, 3mm travel)
- LED with 3 material states (green/red/off via hiddenSelections)
- 12 procedural textures (rust, wear, dirt, fingerprints, brushed metal)
- 7 .rvmat files including 3 emissive LED states
- Complete model.cfg, config.cpp, $PBOPREFIX$
- See `references/lfpg-recipes.md` for the full recipe

## Troubleshooting — Common Failures & Quick Fixes

| Symptom | Root Cause | Fix |
|---------|-----------|-----|
| Model spawns sideways/upside-down | Z-up → Y-up rotation not applied | Apply `x'=x, y'=z, z'=-y` to all vertices (Rule 12) |
| Textures render on inside of faces (invisible exterior) | Face winding not reversed after axis rotation | Reverse vertex order of every face after rotation (Rule 13) |
| Textures look like TV static | Using `random()` per pixel instead of coherent noise | Use OpenSimplex FBM with multi-layer compositing |
| Textures look flat/artificial | Single noise layer, no wear/variation | Add 5-6 layers: base + flow + grain + micro + wear + sparse details |
| Textures appear stretched/misaligned | UVs not generated or exported incorrectly | Run Smart UV Project in Blender before export, verify UV layer exists |
| Model too polygonal/angular | No modifiers applied (bevel, subsurf) | Add Bevel (width 0.002, segments 3) + SubSurf (level 2) before export |
| Collision doesn't work | Geometry LOD is non-convex | Geometry LOD components MUST be convex hulls (Rule 1) |
| Character walks through object | Geometry LOD components have no mass | Set mass ≥ 10 on all Geometry/Fire/View components (Rule 2) |
| Animation doesn't play | Axis memory points missing or misnamed | Verify 2 memory points exist in Memory LOD matching axis name |
| Attachment appears in inventory but invisible on model | Missing one of 3 proxy parts | Need: proxy face+selection in parent, proxy .p3d, CfgNonAIVehicles entry (Rule 14) |
| .p3d file corrupt or crashes Object Builder | Vertex/face data inconsistency | Always read back .p3d with py3d after writing to verify (Rule 11) |
| LOD not recognized by engine | Wrong resolution value | Check LOD resolution table — values must be exact |
| Normal map looks inverted | DirectX vs OpenGL convention | DayZ uses OpenGL convention (green channel = Y-up). Flip green channel if needed |
| Bullets pass through object | Penetration `.rvmat` not assigned to collision LOD faces | Set `face.material = "dz\\data\\data\\penetration\\wood_desk.rvmat"` (or appropriate) on every face in Geometry/FireGeometry/ViewGeometry/HitPoints/Roadway. Verify with `strings <p3d> | grep penetration` (Rule 17) |
| Hologram falls to ground when stacking on object, items can't be placed on top | `autocenter=0` named property missing on collision LODs | Add `lod.properties["autocenter"] = "0"` to ALL collision LODs (FireGeo, ViewGeo, Roadway, Hitpoints, LandContact), not just Geometry. Engine recenters LODs by bbox without it, displacing collision mesh ~20-25cm from visual (Rule 16) |
| Cross-product UNIFORM_NON_FLIPPED in collision LODs | Rule 13 (winding reverse) not applied after Z→Y rotation | Run `for lod in model.lods: for face in lod.faces: face.vertices.reverse()` once on all LODs. Verify expected state post-fix is UNIFORM_FLIPPED (cross-product opposite to declared normals) |
| Bullets pass through + hologram falls to ground when stacking + items can't be placed on top — all three simultaneously | Rule 18: cross-product OUTWARD on collision LODs (Rule 13 was skipped). Check A is insufficient to detect this — must use Check C (per-component-centroid). | Run `flip_collision_winding.py` pattern: reverse vertex order on Geometry/Roadway/ViewGeometry/FireGeometry. Visual LOD untouched. Verify Check C reports cross-product INWARD per component (matches vanilla LFPG gate_and). |
| Damage shows only as color tint, not visible cracks/wear | `_damage.rvmat` Stage3 uses procedural `color()` instead of vanilla overlay texture | Replace Stage3 texture with `dz\\weapons\\data\\weapons_damage_<wood\|metal>_mc.paa` (and `weapons_destruct_<wood\|metal>_mc.paa` for `_destruct.rvmat`). UV transform: `aside={0,4,0}, up={4,0,0}` for 4x tiling. Vanilla pattern: `dz/gear/camping/data/wooden_case_damage.rvmat`. |
| Vehicle launches/bounces at spawn, then deleted (`!finite or outside world coords`) | Geometry built as ONE monolithic component / mass concentrated → low inertia | Rebuild Geometry as many closed convex components + mass on ALL + per-component `autocenter=0` (`vehicle-structural-parity.md` Addendum 2026-05-30; `dayz-p3d-audit` #13) |
| Vehicle doesn't roll / sinks (steers but no roll, `contact=0`) | Wheel hub inside chassis hull, or wheel-proxy Memory anatomy incomplete | Wheel-wells in Geometry so hubs sit OUTSIDE the hull; wheel proxy `.p3d` needs its 5 Memory mem-points (`vehicle-structural-parity.md` Addenda 2026-05-26/29; `dayz-p3d-audit` #11/#12) |
| Vehicle floats / rides too low / belly scrapes | Wheel vertical placement (tire bottom below origin, chassis floor below wheel-center) | Raise wheels AND chassis floor to the ride-height triple together (`dayz-p3d-audit` #12; parity Addendum 2026-05-29) |
| Engine won't start / drowns at spawn | Missing `CarBattery`/`SparkPlug` attachments, or missing `drown_engine` memory point | `vehicle-config-and-modelcfg.md` §15 (won't-start) + in-game Diag menu (Win+Alt → Game→Vehicles→Simulation) |
| `unknown animation source damper` / wheels don't spin or steer | model.cfg ↔ config wiring broken (AnimationSources, animRotation/animTurn/animDamper sources) | `vehicle-config-and-modelcfg.md` §10–13 (the wiring chain) |

## Winding on axis-change + collision LODs + flat-color (added 2026-05-23)

### Rule 13 nuance: only REFLECTIONS (det<0) flip winding (LL-020)
The "always reverse winding after rotating" guidance assumes a reflection. A PROPER rotation
(determinant = +1) PRESERVES handedness/winding → do NOT reverse. E.g. Blender Z-up → DayZ Y-up
via `(x,y,z)->(x,z,-y)` (or its 180°-about-Y sibling `(-x,z,y)`) is det=+1 → no reverse. Reverse
ONLY applies to transforms with a reflection (negating a single axis, det<0). Never assume:
verify with `check_face_winding` (cross(e1,e2)·normal) after assembling — must read ~0% flipped.
(Reversing on a det=+1 transform gives 100% flipped: model only visible from inside / black
outside.)

### Collision LOD winding must match the Visual LOD (SP-003)
When you GENERATE/EDIT a collision LOD (Geometry/Fire/View), compare its winding against the
Visual LOD of the same model (centroid method) BEFORE deploying — they must agree in sign
(~100% INWARD in DayZ left-handed). `audit_p3d.py` does NOT validate this (centroid check
disabled for false positives). Surface this proactively when the symptom is "walks through /
no action / bullets pass".

### Flat-color models: per-material .rvmat, NOT a UV-atlas bake (LL-021)
For monochrome / flat-color-per-piece models, use one .rvmat per material with `diffuse[]` =
base color and `texture=""` (zero UV, zero gaps). A UV-atlas bake of many flat materials yields
black holes/smudges. Atlas baking is for models with real texture detail.

---

## Mass assembly: `point.mass = None`, NEVER `point.mass = 0.0` (added 2026-06-02)

**Origen**: LFQuad N1.5 cerrado 2026-06-02 (handoff `30_Sessions/2026-06-02-LFQuad-placement-fix-firegeo-mass-CLOSED.md`).

### Regla

Cuando ensambles **LODs no-Geometry** (FireGeo 7e15, ViewGeo 6e15, LandContact 2e15, Memory 1e15, Shadow, Visual <1000) por py3d, usa explícitamente `point.mass = None` para cada punto. **NUNCA** uses `point.mass = 0.0`.

Razón: py3d emite el tagg `#Mass#` si **ALGUNA** `point.mass` del LOD es ≠ None, **aunque sea exactamente `0.0`**. Resultado: el `.p3d` lleva un `#Mass#` espurio en el LOD no-Geometry. AddonBuilder/binarize hornea la masa de ESE LOD (suma = 0) → ODOL desplegado con `CoM=(0,0,0)` e inercia 0 → `ECE_PLACE_ON_SURFACE` posiciona el vehículo a la altura del CoM = 0 → spawn bajo tierra → eyección por PhysX-depenetración.

### Antipattern (productor de bug LFQuad N1.5)

```python
# WRONG — produces #Mass# tagg in FireGeo LOD with all zeros
for face in firegeo_lod.faces:
    for v in face.vertices:
        v.point.mass = 0.0      # ← py3d emits #Mass#, binarize uses it, CoM=0
```

### Pattern correcto

```python
# RIGHT — no #Mass# tagg emitted; binarize uses Geometry LOD's #Mass#
for face in firegeo_lod.faces:
    for v in face.vertices:
        v.point.mass = None     # ← py3d skips #Mass# emission for this LOD
```

### Verificación post-assemble

Iterar todos los LODs y asegurar que **solo el Geometry LOD (res 1e13)** tiene `lod.mass != None` y tagg `#Mass#`:

```python
for lod in model.lods:
    has_mass = any(p.mass is not None for p in (lod.points if hasattr(lod, "points") else []))
    if lod.resolution == 1e13:
        assert has_mass, "Geometry LOD must have #Mass#"
    else:
        assert not has_mass, f"LOD res={lod.resolution:.0e} must NOT have #Mass#"
```

Verificación end-to-end (post-binarize): `binarize.exe -always -addon=<dir> <src> <dst> <wildcard>` + leer `ModelInfo CoM` del ODOL → debe ser ≠ (0,0,0) y coincidir con el CoM del Geometry MLOD.

### Cross-ref

LL-079 (bisección de LODs aisló el bug), LL-080 (la lección durable), check añadido a `dayz-p3d-audit` (Mass-only-Geometry, added 2026-06-02), tool de referencia `LFQuad_dev/tools/fix_firegeo_mass.py` (patch headless para .p3d con el bug).

<!-- [merged 2026-06-05 from .claude\skills user copy during plugin-canonical migration] -->
## Llama Mod Extraction Patterns (rvmat)

Patterns extracted from LM_Planes mod (workshop 3730564764, Llama+Itspete-Here). Aviation-applied but generally reusable.

### Toggle rvmat pattern (lights on/off without duplicating material)

For dashboards, control panels, displays that have an "on" and "off" state, create **two near-identical rvmats** with minimal diff:

```
Controls.rvmat (lights off)           Controls_on.rvmat (lights on)
ambient[]      = {0.9999992,...}     ambient[]      = {0.9999992,...}    SAME
diffuse[]      = {0.9999992,...}     diffuse[]      = {0.9999992,...}    SAME
forcedDiffuse[] = {0,0,0,1}      →   forcedDiffuse[] = {0.1,0.1,0.1,1}   DIFFERS (slight emissive boost)
specular[]     = {0.882,...}         specular[]     = {0.882,...}         SAME
specularPower  = 55                  specularPower  = 55                  SAME

Stage5 SMDI:
  texture = "...controls_SMDI.paa"   texture = "...controls_on_SMDI.paa"  DIFFERS

Everything else identical.
```

**Pattern**: only `forcedDiffuse` (controls overall brightness) + Stage5 SMDI texture (specular/material mask with glowing elements) differ. Toggle via script using vehicle-level `dashboardMatOn`/`dashboardMatOff` properties in CfgVehicles:

```cpp
class LM_Catalina: CarScript {
    dashboardMatOn  = "LM_Planes\LM_Tigermoth\data\Controls_on.rvmat";
    dashboardMatOff = "LM_Planes\LM_Tigermoth\data\Controls.rvmat";
    ...
};
```

(Plus: cross-aircraft material sharing — Catalina references Tigermoth's rvmats directly. DRY across related entities.)

### Glass rvmat distinctives

Transparency requires specific flags + values:

```cpp
ambient[]      = {0.55,0.55,0.55,1};
diffuse[]      = {0.45,0.45,0.45,1};
forcedDiffuse[] = {0,0,0,1};
emmisive[]     = {0,0,0,1};
specular[]     = {0.25,0.25,0.25,1};
specularPower  = 1320;                      // HIGH — glassy reflection
renderFlags[]  = {"noZwrite"};              // MANDATORY for transparency
PixelShaderID  = "Super";
VertexShaderID = "Super";

class Stage1 { texture = "#(argb,8,8,3)color(0.5,0.5,1,1,NOHQ)"; ... };  // procedural normal
class Stage4 { texture = "#(argb,8,8,3)color(1,1,1,1,AS)"; ... };          // procedural AS
class Stage5 { texture = "#(argb,8,8,3)color(1,1,1,1,SMDI)"; ... };        // procedural SMDI
class Stage6 { texture = "#(ai,64,64,1)fresnel(1,0)"; uvSource = "tex1"; ... };  // softer fresnel for glass
class Stage7 { texture = "dz\data\data\env_land_chrome_co.paa"; ... };     // CHROME env map, not env_land
```

Key points:
- `renderFlags[] = {"noZwrite"}` — without this, glass fails to render transparent or causes z-fighting
- `specularPower = 1320` — much higher than opaque materials (typical 50-200)
- Glass usually omits real textures for Stage4/5 (uses procedural `color(...)` placeholders)
- Stage7 uses `env_land_chrome_co.paa` for reflective chrome look, not the regular `env_land_co.paa`
- Stage6 fresnel `(1,0)` softer than standard `(1.1,0.3)` — glass has subtle edge fall-off

### Damage variant rvmat pattern

For materials that should look damaged/scratched/burnt at higher damage levels, create a damage variant with same texture base + overlay:

```cpp
// engine.rvmat (normal)                    engine_scratch_damagex1.rvmat (damaged)
ambient[]    = {0.9999,...};                 ambient[]    = {0.634,...};         REDUCED
diffuse[]    = {0.9999,...};                 diffuse[]    = {0.634,...};         REDUCED
specular[]   = {0.882,...};                  specular[]   = {0.392,...};         REDUCED
specularPower = 55;                          specularPower = 85;                  HIGHER (worn = sharper specular)

// Stage1-2: same base textures
// Stage3 (Macro Color) is the KEY:
Stage3 normal:  "#(argb,8,8,3)color(0,0,0,0,mc)"
Stage3 damaged: "<mod>\<aircraft>\data\damage_layer_mc.paa"   // CUSTOM damage overlay

// Stage2 detail (worn material reuses vanilla DZ texture):
Stage2 damaged: "DZ\data\data\detail_maps\plastic1_512_dt.paa"   // Reuse vanilla
```

**Pattern**: damage variants share base texture set, swap Stage3 (Macro Color) for a damage overlay texture, reduce color values to simulate burn/wear. The damage overlay is a single `damage_layer_mc.paa` per aircraft that overlays scratches/blackening on top of the base diffuse.

Tied to `DamageSystem` zones via `healthLevels[]`:

```cpp
healthLevels[] = {
    {1.0, {}},                                     // pristine: base rvmat
    {0.7, {}},
    {0.5, {}},
    {0.3, {"<path>/engine_scratch.rvmat"}},        // damaged level 1
    {0.0, {"<path>/engine_scratch_damagex1.rvmat"}} // damaged level 2 / destroyed
};
```

### 6-stage rvmat variant (omit env stage)

Standard rvmat has 7 stages (NOHQ, DT, MC, AS, SMDI, Fresnel, env). For cosmetic materials that don't need world environment reflection, omit Stage7 — fits in 6 stages + StageTI:

```
Stage1=NOHQ, Stage2=DT, Stage3=MC, Stage4=SMDI, Stage5=Fresnel, Stage6=env (combined), StageTI=thermal
```

The Pickle.rvmat (Patty_Wagon car body) uses this. Slightly cheaper, valid for simple opaque materials. **Don't use for aircraft canopies, mirrors, or anything reflective** — those need the full env Stage7.

### HDR emissive trick (super-bright lights)

For materials that simulate fluorescent lamps / bright LEDs glowing visibly even in daylight, use values **>1.0** across all stages — engine accepts HDR-range values:

```cpp
ambient[]       = {10,10,10,10};
diffuse[]       = {10,10,10,10};
forcedDiffuse[] = {10,10,10,10};
emmisive[]      = {10,10,10,10};
specular[]      = {10,10,10,10};
specularPower   = 100;
// Plus Stage5 SMDI uvTransform aside/up = {5,0,0}/{0,5,0} (texture scale 5x for finer detail)
```

This produces a glowing material WITHOUT needing PointLight engine objects — purely material-based. Used in `houselightmat.rvmat` (Llama Hangar1 fluorescent lamps). Tradeoff: no actual illumination on nearby surfaces (no dynamic light cast), just the material itself appears very bright. Combine with a real `CarLightBase` / `PointLightBase` if you need surfaces lit too.

For LED screens that need both visible-from-far glow + dynamic light, use this trick + a `PointLightBase` script-controlled to match.

<!-- llama-mod-extraction: findings f_055, f_056, f_057, f_059, f_082 | pbo: LM_Planes | pass: 1 | date: 2026-05-23 | source: workshop 3730564764 LM_Tigermoth/data + LM_Catalina/data + LM_Patty_Wagon/data + LM_Z37_Bumblebee/data + LM_Plane_Assets/LM_Hangar1/data -->
