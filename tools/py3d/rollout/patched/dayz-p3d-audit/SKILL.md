---
name: dayz-p3d-audit
description: >
  Audit and fix DayZ .p3d model files for collision, action targeting, physics, animation,
  path, and structural issues. Runs py3d-based validation against known-working reference
  patterns. Also validates config.cpp and .rvmat files for path and property issues.
  Use this skill whenever: a DayZ mod object has no collision, actions don't appear,
  the player walks through placed objects, CCTObject raycasts miss, Geometry LOD seems
  ignored, a model was exported from Blender and doesn't work in-game, textures are
  missing, animations don't play, or the user says "review the p3d", "check the model",
  "audit collision", "why no actions", "flag/object has no collision", "audit the mod",
  "check paths", "validate the model". Also trigger when debugging any placed
  Inventory_Base item. This is the GO-TO skill for P3D and mod structure debugging.
---

# DayZ P3D Audit — Complete Model & Mod Validator

Validates .p3d model files, config.cpp, model.cfg, and .rvmat materials against
DayZ engine requirements. Built from production debugging where models rendered
correctly but had zero collision, missing animations, or broken textures.

## Preflight gate

Per the L2 rule (`.claude/skills/_shared/dayz-conventions.md`), every DayZ skill that does work gates on `/dayz-preflight` first. The audit reads `.p3d` files which can live anywhere, but the moment you point it at `P:\` paths or a built mod, an unmounted P-drive silently produces wrong results. Run `/dayz-preflight` before this skill.

## Quick Start

```bash
python <skill-path>/scripts/audit_p3d.py path/to/model.p3d [more.p3d ...]
```

For full mod audit including config and materials, also check sections below manually.

---

## PART 1: The 10 Silent P3D Killers

These produce ZERO engine errors but break functionality completely.

### 1. Inverted Face Winding (CRITICAL — Most Common from Blender)

Geometry LOD faces have normals pointing INWARD. Raycasts from outside pass through
without detecting collision — no collision, no action targeting, no physics.

**Root cause**: Blender Z-up → DayZ Y-up axis conversion flips triangle winding on
collision LODs while leaving the Visual LOD correct. The model looks perfect but is
physically invisible.

**Detection**: Cross-product of edge vectors must point AWAY from mesh center.

> **AUTOMATED CHECK (added 2026-05-21)**: `audit_p3d.py` now runs a RELATIVE winding
> check — it compares each collision LOD's winding orientation against the **Visual LOD**
> (which renders correctly in-game and therefore defines this model's correct convention)
> and emits a CRITICAL if they are opposite. This replaces the old absolute centroid
> heuristic, which false-positived on every Blender export (left-handed transform) and so
> was disabled — that disablement is exactly why an inverted collision sphere could pass a
> full audit with "ALL PASSED". The relative check is coordinate-system-agnostic.
>
> **MANDATORY when you GENERATE or EDIT a collision LOD** (procedural sphere, py3d round-trip,
> Blender import, inspector rebuild): re-run `audit_p3d.py` and confirm there is no
> "winding is INVERTED relative to the Visual LOD" CRITICAL **before deploying**. A
> separately-created dynamic physics body (`dBodyCreateDynamicEx`) can still make the object
> move, which masks inverted collision winding — the object rolls but the player walks
> through it and no action cursor registers. If the CRITICAL fires, swap `vertices[1]`/`[2]`
> on every face of that LOD so it matches the Visual LOD convention.

**Fix**: Swap `vertices[1]` and `vertices[2]` of each inverted face.

**Why Visual LOD isn't affected**: Visual and Geometry LODs have independent face data.
The renderer draws both sides; collision only detects the "front" face.

### 2. Component Selection Case Sensitivity (CRITICAL)

Geometry LOD component MUST be `Component01` (uppercase C). The engine string-matches
exactly. `component01`, `COMPONENT01`, or any variation silently fails — engine finds
zero components and ignores ALL collision geometry.

**Verified against**: LFPowerGrid production models (fridge, furnace, battery_adapter)
all use `Component01`.

### 3. Missing `autocenter=0` LOD Property (CRITICAL for Inventory_Base)

For items with `autocenter=0` in config.cpp, the Geometry LOD MUST ALSO carry
`autocenter=0` as a named property. Config property controls the visual mesh;
LOD property controls the collision mesh. Without both, collision is displaced.

**Where**: Named property on Geometry (1e13), GeoPhys (2e13), FireGeo (3e13) LODs.
In py3d: `lod.properties['autocenter'] = '0'`

### 4. Missing Memory LOD or Geometry LOD (CRITICAL)

A P3D without a Memory LOD (res ~1e15) will have no animation, no bounding data, and
potentially crash the engine. A P3D without a Geometry LOD (res ~1e13) will have zero
collision and zero action targeting.

**Required LODs for any interactive DayZ object:**
- LOD 0: Visual (res=0.0) — rendering
- Memory (res ~1e15) — animation axes, bounding, interaction points
- Geometry (res ~1e13) — collision and cursor raycasting

**Recommended additional LODs:**
- GeoPhys (res ~2e13) — physics collision (player walking, vehicles)
- FireGeo (res ~3e13) — ballistic damage zones

### 5. Missing `pos center` Memory Point

Without `pos center`, the engine calculates bounding center from vertex distribution.
For tall/asymmetric objects (flagpoles where most vertices are in cloth at top), the
calculated center is far from the base — breaking the action targeting pre-filter.

**Fix**: Add `pos center` at `(0.0, 0.0, 0.0)` in Memory LOD for `autocenter=0` items.

### 6. Missing Animation Selections & Axes

If model.cfg defines an animation (like `flag_mast`), the P3D MUST have:
- **Visual LOD**: Named selection matching the animation selection name (e.g. `flag_mast`)
  covering all vertices/faces that should animate
- **Memory LOD**: Named selection matching the axis name (e.g. `flag_mast_axis`) with
  EXACTLY 2 points defining the animation axis (start and end of translation/rotation)

If either is missing, the animation silently does nothing.

> **Caveat — vehicles: the axis↔selection binding lives in `model.cfg`, so this check
> false-positives on a valid decoupled rig (added 2026-06-05, LL-027).** `audit_p3d.py`
> cross-references Memory↔Visual by a NAME heuristic — it assumes `wheel_X_X_axis` implies
> a visual selection literally named `wheel_X_X`. A clone-Croco / vanilla wheel rig
> legitimately DECOUPLES the names: the selection is `wheelfrontleft` while the rotation
> axis is `wheel_1_1_axis`, and the two are tied in `model.cfg`
> (`class wheel_1_1 { source="wheelfrontleft"; selection="wheelfrontleft"; axis="wheel_1_1_axis"; }`,
> see `dayz-model-pipeline/references/vehicle-config-and-modelcfg.md` §12). The audit then
> reports the selection as "missing" when it exists under a different name. Real LFQuad case:
> 12 spurious CRITICALs on the C.6 body, all false positives. **Rule:** for ANIMATED AXES on a
> vehicle, treat these CRITICALs as WARNING until you cross-check `model.cfg` — read the
> `selection=`/`axis=` of each animation class and confirm BOTH names exist in the `.p3d`
> (axis as a 2-point Memory selection, the named `selection=` in the Visual LOD). A rig that
> decouples axis-name from selection-name is valid (Croco/vanilla pattern). The deep fix
> (parse `model.cfg` in `audit_p3d.py`) is tracked as PB-010.

### 7. Missing `box_placing_min` / `box_placing_max` Memory Points

For deployable objects using the hologram placement system, the Memory LOD needs:
- `box_placing_min` — single point at the minimum corner of the placement bounding box
- `box_placing_max` — single point at the maximum corner

Without these, the hologram collision check may malfunction (permanently block placement
or never detect terrain collision).

**Note (empirical, vanilla 1.x)**: This memory-point pair is a *fallback*. Vanilla
`hologram.c::GetProjectionCollisionBox` first calls `m_Projection.GetCollisionBox(min_max)`,
which returns the bbox derived from the Geometry LOD; only if that fails does it fall
back to `box_placing_*`. Vanilla deployables (`55galdrum`, `wooden_case`, `sea_chest`,
`MilitaryCrate` from a6_base_storage) ship `boundingbox_min/max` as Memory LOD selection
names — NOT `box_placing_*` — and rely on the Geometry LOD bbox. So this rule fires only
for items without a proper Geometry LOD or with broken `GetCollisionBox()` data.

### 8. Incomplete Component01 Coverage

`Component01` must include ALL vertices AND ALL faces of the Geometry LOD with weight=1.
Partial coverage means partial collision — some faces won't register raycasts.

### 9. Non-Watertight Collision Mesh

The Geometry LOD mesh must be closed (watertight) — every edge shared by exactly 2 faces.
Open meshes (with boundary edges/holes) cause unreliable collision where raycasts can
pass through gaps.

### 10. Missing Surface/Material Assignment on Collision LODs (CRITICAL)

Every face in the collision LODs (Geometry / GeoPhys / FireGeometry / ViewGeometry /
HitPoints) MUST have a `material` assigned, pointing to a penetration `.rvmat` that in
turn references a `.bisurf` file. Without this assignment, the engine raycasts hit the
geometry but cannot resolve a surface to consult — bullets pass through, footstep sound
is missing, and action cursor may not register.

Vanilla items always ship this — verifiable via `strings <p3d> | grep penetration`:

| Vanilla object   | Penetration material assigned             |
|------------------|-------------------------------------------|
| `55galdrum`      | `dz\data\data\penetration\metalplate.rvmat` + `metalPlate.bisurf` |
| `wooden_case`    | `dz\data\data\penetration\wood_desk.rvmat` + `wood_desk.bisurf` |
| `sea_chest`      | `dz\data\data\penetration\wood_desk.rvmat` + `wood_desk.bisurf` |
| `MilitaryCrate` (a6_base_storage) | `dz\data\data\penetration\plastic.rvmat` + `plastic.bisurf` |

Detection (py3d):
```python
for lod in p.lods:
    if lod.resolution in collision_lod_ranges:
        for face in lod.faces:
            assert (face.material or '') != '', f"face missing material in {lod_label}"
```

Fix: in Object Builder OR programmatically via py3d, set `face.material =
"dz\\data\\data\\penetration\\<surface>.rvmat"` for every face in every collision LOD
and write back. Visual LOD keeps its complex multi-stage `.rvmat` (e.g. `wooden_case.rvmat`)
unchanged — the penetration `.rvmat` is a SEPARATE simpler material used only by
collision LODs. Symptoms persist after binarization (ODOL preserves the empty
material), so this can be missed until in-game ballistic test.

### 11. Wheel Proxy `.p3d` Memory LOD has only `ce_center` (CRITICAL for wheeled vehicles) (added 2026-05-29)

If you audit a wheel proxy `.p3d` (the separate file referenced by `ProxyVehiclePart`
in `CfgNonAIVehicles`, atached to the body via `inventorySlot`) and its Memory LOD
contains only `ce_center` — the wheel is **anatomically incomplete**. The vanilla
pattern (Croco `quadbike_wheel.p3d` v53, verified 2026-05-29) ships 5 mem-points:
`ce_center`, `ce_radius`, `boundingbox_min`, `boundingbox_max`, `invview`. PhysX uses
those 4 missing ones to construct the wheel collider geometry; without them it falls
back to the Geometry LOD of the proxy (typically a small 8-vertex cube on procedural
wheels generated by `dayz-model-pipeline`).

**Symptom in-game (silent — no RPT error)**: `wheelCount=N wheelPresent=N anyLocked=0`
(attachment / config / FireGeo slot all OK) but `contact=0` permanent on every wheel
every frame. The vehicle spawns, the suspension engages once at frame 0 (penetration
contact via Geometry hub), then the body lifts more than ~10 cm and **the wheel raycast
can no longer reach ground** because the effective collider is the size of the hub cube
(~0.10 m) rather than the wheel diameter (~0.34 m). Body falls free, chassis Geometry
hits terrain, bounce divergente, `speedo` oscillates between large magnitudes, eventually
exceeds finite range and the engine logs `Will delete object with !finite or outside
world coords`. Symptom triplet:

- `wheelPresent` = full count (not the older `wheelPresent=0` blocker)
- `contact` = 0 across all wheels in EVERY frame
- Body Y oscillates with amplitude growing per bounce (energy never dissipates because
  there is no wheel-ground contact to apply friction)

**Detection (py3d)**:

```python
WHEEL_REQUIRED = {"ce_center", "ce_radius", "boundingbox_min",
                  "boundingbox_max", "invview"}
for lod in p.lods:
    if abs(lod.resolution - 1e15) > 1e12: continue  # Memory only
    if not (path.endswith("wheel_front.p3d") or
            path.endswith("wheel_rear.p3d") or
            "wheel" in path.lower()):
        # Heuristic: this proxy is a wheel if its Geometry LOD bbox Y span
        # matches a wheel-shaped aspect (Y span ≈ Z span ≈ 2× radius from config).
        pass
    have = set(lod.selections.keys())
    missing = WHEEL_REQUIRED - have
    if missing:
        flag_critical(f"wheel proxy Memory missing {missing}")
```

**Fix**: bake the 4 missing mem-points using the Croco-vanilla convention (Y vertical,
X axial, Z with intentional min/max inversion). Reference values + scaling rules in
`dayz-model-pipeline/references/vehicle-structural-parity.md` §"Addendum (2026-05-29)
— Wheel proxy `.p3d` Memory anatomy (T1-D)". Bake with py3d 1.0.0 — observe the
6 quirks in `dayz-animation-pipeline/references/py3d-1.0.0-quirks.md` (constructor
with args, weight `int` not `float`, rebind after grow, etc.). The 5 mem-points
do NOT carry weight — each is its own one-vertex Selection.

**Caveat (Visual LOD diameter vs collider size)**: PhysX uses the **Memory mem-points
to construct the wheel collider**, NOT the Geometry LOD of the proxy. A wheel proxy
can have a perfectly sized Visual LOD (Ø0.68) AND a tiny Geometry hub cube (~0.20)
AND `contact=0` because the Memory anatomy is incomplete. Visual size is not what
PhysX measures.

**Why this is silent until 2026-05-29**: `audit_p3d.py` checks Component01, autocenter,
winding, surface materials — but not selection-name presence per proxy class. The
wheel proxy passed ALL PASSED with only `ce_center`, and the bug surfaced 4 sessions
later as a bounce blocker (LL-057 — gap TIER 1 diferido sin gate). Until the audit
script is updated, surface this proactively when the symptom is "vehicle bounces on
spawn / contact=0 / speedo diverges to ±inf / delete-outside-world".

Origin: LFQuad bounce diagnostic 2026-05-29; LL-057 (process); cross-ref
`dayz-model-pipeline` Rule 19.

---

### 12. Wheel-vertical-placement: tire bottom below model origin / chassis floor below wheel-center line (CRITICAL for wheeled vehicles) (added 2026-05-29)

A wheeled vehicle whose wheels sit too LOW relative to the body rides with its belly too close to the ground. **Symptom:** `wheelCount=N wheelPresent=N` OK but `contact=0` permanently on all wheels even at rest; chassis bounces elastically on terrain; vehicle falls unbalanced / rotates. No RPT error -- silent killer.

3 working references (Croco quad, vanilla `offroadhatchback`, `civiliansedan`) all place the **tire bottom ~ at/above the model origin** (never negative) and the **chassis floor ~ at/above the wheel-center line**. Anti-example: LFQuad shipped with tire bottom Y=-0.114, chassis floor Y=0.120 (0.107 BELOW the wheel center 0.227) -- 4+ iterations of geometry fixes never measured this because the invariant lived in the skill only as prose (LL-062).

**Check** (measure, don't eyeball; compare to a debinarized working reference):
```python
geo = next(l for l in p3d.lods if abs(l.resolution - 1e13) < 1e11)
wheel_center_Y = ...   # Memory wheel_X_X centroid Y (or hub damper_land)
radius = ...           # config Axles -> Wheels.radius
tire_bottom   = wheel_center_Y - radius
chassis_floor = component01_bbox_min_Y(geo)
if tire_bottom < -0.02:
    flag_critical(f"tire bottom {tire_bottom:.3f} below model origin (working refs ~+0.01/+0.05)")
if chassis_floor < wheel_center_Y - 0.05:
    flag_critical(f"chassis floor {chassis_floor:.3f} below wheel-center line {wheel_center_Y:.3f}")
```

**Coupling (do not create a new anomaly):** the fix raises BOTH the wheel/hub system AND the chassis floor to the reference triple -- raising only the wheels worsens resting clearance. See `dayz-model-pipeline/references/vehicle-structural-parity.md` "Addendum 2026-05-29 -- ride-height triple" + LL-062. Causal link to `contact=0` is `[verify in-game]` (R31); the parity divergence itself is verified vs 3 references.


### 13. Vehicle Geometry built as ONE monolithic component / mass concentrated / missing per-component `autocenter=0` (CRITICAL for wheeled vehicles) (added 2026-05-30)

A working DayZ car's Geometry LOD is a **compound of several closed convex components**, each with mass and `autocenter=0` — never a single monolithic hull holding all the mass. Building it as one component is the silent root of the classic **launch/bounce at spawn**: the chassis explodes upward the instant it's created, tumbles, gains energy, and the engine deletes it (`Will delete object with !finite or outside world coords`). No RPT error.

Mechanism (documented): PhysX resolves spawn interpenetration in a single step → large separating impulse (NVIDIA PhysX Best Practices, "Overlapping objects explode"); sharp edges of a tight monolithic hull "impart a large moment … sending it up into the air" (Arma Anti-Bounce community). Mass concentrated in one component → low/pathological inertia tensor → the impulse becomes a runaway tumble (LOD wiki: "the Mass distribution is critically important … Inertia/Moment of Inertia"). Anti-example: LFQuad shipped with **1** chassis component (`component01`) holding ~90% of mass, Izz 128.5 vs the Croco reference 350.7 (37%); the working Croco quad has **23 chassis components + 4 hubs**.

Working references converge: Bohemia `DayZ:Vehicle_Configuration` ("convex components. Every component's vertex should have weight assigned. From these weights the total mass of vehicle and its center of mass is computed. Wheel hubs should have their own components"); the Tyson89/Landrover tutorial Object-Builder checklist ("Convex Components / autocenter value 0 / Applied a Mass on **ALL** components / Wheel hubs present / Center of Mass"). See `dayz-model-pipeline/references/vehicle-structural-parity.md` Addendum 2026-05-30 + external refs there.

**Check** (measure, don't eyeball; compare to a debinarized working reference):
```python
geo = next(l for l in p3d.lods if abs(l.resolution - 1e13) < 1e11)   # Geometry LOD
comps = components_in(geo)                          # named selections componentNN (chassis) + hubs
chassis = [c for c in comps if c.name.startswith("component")]
if len(chassis) <= 1:
    flag_critical(f"Geometry chassis is {len(chassis)} component (monolith); working cars use many "
                  f"convex components (Croco ~23). Single hull → spawn-launch + low inertia.")
for c in comps:                                     # mass on ALL components, none ~0, none dominant
    if c.mass <= 0:
        flag_critical(f"component {c.name} has no mass; CoM/inertia will be wrong")
    if c.mass > 0.6 * total_mass:
        flag_critical(f"component {c.name} holds {c.mass/total_mass:.0%} of mass (concentrated → low inertia)")
    if c.named_property("autocenter") != "0":       # extends Killer #3 to per-component on vehicles
        flag_critical(f"component {c.name} missing autocenter=0 (engine may recompute CoM)")
com = center_of_mass(geo)
if abs(com.x) > 0.05:
    flag_critical(f"center of mass X={com.x:.3f} not laterally centered (vehicle will lean/launch)")
```

Note `autocenter=0` is already Killer #3 but only for `Inventory_Base`; on a **vehicle** it must be present on **every** Geometry component (per the Landrover checklist), or the engine recomputes the origin and shifts the CoM relative to the mass you assigned. The fix couples with Killer #12 (ride-height): rebuild the chassis as multiple convex components with distributed mass AND correct vertical placement together — raising one without the other creates a new anomaly (LL-030). Causal link to the launch is `[verify in-game]` (R31); the construction divergence vs 3 references is verified.

> **Correction (2026-06-02, verified in-game):** the `[verify in-game]` above was settled and the causal attribution did NOT hold. The CONFIRMED root cause of the LFQuad spawn-launch/bounce was a spurious `#Mass#` tagg (all zeros) on a non-Geometry LOD (FireGeometry) → AddonBuilder/binarize baked the mass of THAT LOD → deployed ODOL with `CoM=(0,0,0)` and zero inertia → `ECE_PLACE_ON_SURFACE` spawned the vehicle ~0.48 m below ground → PhysX ejection. It was **not** the monolithic Geometry nor the low inertia tensor. Multi-component Geometry with distributed mass remains **best-practice** (ride-height, collision, convex-component correctness per the Landrover/Bohemia checklist), but it is NOT the cause of the spawn-launch — keep this Killer as a recommended construction practice, not as the spawn-launch diagnosis. Fix = strip `#Mass#` from every LOD that is not the Geometry LOD (set `point.mass = None`, not `0.0`). See this skill's **"#Mass# debe vivir solo en Geometry LOD"** section + LL-079/LL-080/LL-081 + the worked example, and the mirrored correction in `dayz-model-pipeline/references/vehicle-structural-parity.md` Addendum (2026-05-30). First diagnose with the mass-only-Geometry check (it catches the real cause in seconds) before suspecting the chassis-component count.

## PART 2: Config.cpp Validation

### Baked-in P:\ Drive Paths (CRITICAL)

Absolute paths like `P:\DZ\gear\consumables\data\rag_co.paa` only exist on the
developer's machine. These MUST be converted to game-relative paths:

```cpp
// WRONG — breaks on any other machine:
hiddenSelectionsTextures[] = {"P:\DZ\gear\consumables\data\rag_co.paa"};

// CORRECT — works everywhere:
hiddenSelectionsTextures[] = {"DZ\gear\consumables\data\rag_co.paa"};
```

**Where to check**: `hiddenSelectionsTextures[]`, `hiddenSelectionsMaterials[]`,
and any texture/material path in config.cpp.

**Exception**: Paths starting with `P:\` are valid ONLY during development on a
workbench with P: drive mounted. They must be stripped for distribution/PBO packing.

### Required Properties for Placed Objects

```cpp
class MyPlacedObject: Inventory_Base
{
    autocenter = 0;        // MANDATORY — prevents visual mesh burial
    model = "\ModName\data\model.p3d";  // Backslash prefix = addon root
    // For kits (handheld items): do NOT set autocenter=0
};
```

### AnimationSources Must Match model.cfg

If model.cfg defines animation `flag_mast` with `source = "flag_mast"`, config.cpp
MUST have a matching AnimationSources entry:

```cpp
class AnimationSources
{
    class flag_mast
    {
        source = "user";    // "user" = script-controlled
        animPeriod = 0.5;
        initPhase = 1;      // 0=up, 1=down for vanilla flag convention
    };
};
```

### hiddenSelections Must Match P3D

Every entry in `hiddenSelections[]` MUST have a matching named selection in the
Visual LOD of the P3D. Missing selections silently fail (no texture swap occurs).

---

## PART 3: Material (.rvmat) Validation

### P:\ Drive Paths in .rvmat Files

Same rule as config.cpp — `P:\` paths break on distribution:

```
// WRONG:
texture="P:\dz\gear\camping\data\flag_generic_nohq.paa";

// CORRECT (vanilla reference):
texture="dz\gear\camping\data\flag_generic_nohq.paa";
```

### Required Texture Stages

Standard DayZ .rvmat needs at minimum:
- Stage 0: Diffuse color texture (`_co.paa`)
- Stage 1: Normal map (`_nohq.paa`)
- Stage 2: Specular/detail map (`_smdi.paa`)

Missing stages produce engine warnings but don't crash.

---

## PART 4: Diagnostic Decision Tree

```
1. Can you SEE the object in-game?
   NO  → Check model path in config.cpp (backslash prefix, case)
   YES ↓

2. Is the object buried/floating?
   BURIED → Missing autocenter=0 in config.cpp AND/OR LOD property
   FLOATING → autocenter=0 on a kit class (only placed objects need it)
   CORRECT ↓

3. Does floating text (item name) appear near it?
   NO  → Entity not spawned. Check CreateObjectEx, server logs
   YES ↓

4. Do debug Print() in ActionCondition appear in script log?
   YES → ActionCondition rejecting. Read prints to find which check fails
   NO  ↓ (P3D Geometry LOD issue — engine can't raycast)

5. Run audit_p3d.py and check:
   a. Face winding outward?      → If inward: swap verts[1]/verts[2]
   b. Component01 uppercase C?   → If wrong case: rename
   c. autocenter=0 LOD property? → If missing: add
   d. pos center in Memory?      → If missing: add at (0,0,0)
   e. Component01 covers all?    → If partial: extend selection
   f. Mesh watertight?           → If open: close gaps
   g. Geometry LOD exists?       → If missing: create one

6. Animations not playing?
   → Check flag_mast selection in Visual LOD
   → Check flag_mast_axis (2 points) in Memory LOD
   → Check AnimationSources in config.cpp matches model.cfg

7. Textures missing/white?
   → Check P:\ paths in config.cpp hiddenSelectionsTextures
   → Check P:\ paths in .rvmat files
   → Verify .paa files exist at referenced paths
```

---

## PART 5: Common Blender Export Pitfalls

1. **Z-up → Y-up flips collision winding but not visual** — always verify Geometry LOD
   normals independently from Visual LOD
2. **Blender Geometry LOD may inherit `class=house`** from Object Builder templates
3. **py3d read-write cycles** preserve validity but change file size (~800 bytes per
   property change). This is normal.
4. **Addon Builder binarizes MLOD → ODOL** — all MLOD issues persist into builds
5. **Named selections are case-sensitive** in MLOD format. `Component01` ≠ `component01`
6. **Memory LOD must have zero faces** — only single-vertex points. Faces in Memory LOD
   may confuse the engine.
7. **Animation axis points must be in the SAME named selection** — both points of
   `flag_mast_axis` must be in one selection, not split across two.

---

## PART 6: Script-Side Gotchas

These aren't P3D issues but commonly co-occur during debugging:

- `IsTakeable()` MUST return `true` for `ActionManagerClient` to include the entity
  in the action targeting pipeline. Use `CanPutInCargo()=false` +
  `CanPutIntoHands()=false` + `RemoveAction(ActionTakeItem)` for non-pickup items.
- `SetFullyRaised()` in group creation → flags start at progress=1.0 → only
  `LowerFlag` appears initially, not `RaiseFlag` (checks `< 1.0`).
- SyncVar timing vs RPC cache timing can deadlock ActionConditions.
- `autocenter=0` on FlagKit (handheld) causes it to float when dropped — only set
  on placed objects, not kits.

---



---

## WINDING DIAGNOSTICS — Deep Methodology

Movido desde `DayZ Projects/CLAUDE.md` 2026-05-04. Es el detalle de validación
de winding aprendido en producción con Crate_Wooden y WallLamp. Complementa la
sección 1 ("Inverted Face Winding") con metodología de validación, trampas y
checklist completo de importación.

#### Cómo NO verificar — heurísticas que engañan

⚠️ **Check centroid-based (`cross(e1, e2) · (face_centroid - LOD_centroid) > 0`):**
- Es **right-handed** (convención Three.js / OpenGL). DayZ es **left-handed**. Un modelo CORRECTO post-flip aparecerá como "winding inward" en ese check pero con normales declaradas outward — no es incoherencia, es el signo opuesto del cross product entre sistemas.
- Asume **geometría convexa** (compara contra el centroide del LOD). Para cajas huecas con paredes gruesas, caras interiores correctas se marcan como "invertidas".
- **Conclusión: NO SIRVE para validar winding DayZ absoluto.** El skill `dayz-p3d-audit` lo tuvo durante meses y producía hasta 100% de falsos positivos en modelos correctos. Solo vale para consistencia relativa antes/después de la MISMA operación, o comparado contra un vanilla de referencia.

⚠️ **Comparar `face.vertices[i].normal` con la cross product directamente NO funciona.** Las normales del pool `lod.facenormals` son per-vertex-corner suavizadas (smoothing groups): en faces planas coinciden con la flat normal; en faces suavizadas no. Para usarlas como referencia de "intent" hay que **promediar las normales de los 3-4 corners de UNA face** y compararlo con `cross(e1, e2)`. Ver Check A en `audit_p3d.py`.

⚠️ **Asumir que `lod.facenormals[i]` es el normal de `lod.faces[i]`.** Falso. `lod.facenormals` es un POOL global (tamaño = `num_facenormals` del header MLOD, **independiente** de `len(lod.faces)`); cada Vertex apunta a él vía `normal_index`. Confundirlos lleva a checks que nunca corren (length mismatch) o checks que comparan cosas incorrectas.

#### Cómo SÍ verificar

1. **Check A — winding-vs-normal-promediada por face (DIAGNÓSTICO).** Para cada face, calcular `n_winding = normalize(cross(v1-v0, v2-v0))` y compararlo con el promedio normalizado de `face.vertices[i].normal` sobre los corners. El % de faces con `dot < -0.5` indica el estado de handedness:
   - **~100% UNIFORM_FLIPPED** → estado ESPERADO en DayZ (left-handed) tras export desde Blender (right-handed Z-up). El cambio de handedness invierte el cross product. **Verificado empíricamente con Crate_Wooden 2026-04-25 in-game: render/balas/cursor/colisión todo OK.** No action needed. → severity NOTE.
   - **~0% UNIFORM_NON_FLIPPED** → o no hay handedness transform o las normales se re-alinearon post-transform. Verificar in-game. → severity NOTE.
   - **5-95% MIXED** → bug real, render/colisión inconsistente entre faces. → severity CRITICAL.
   Coordinate-system-agnostic.

2. **Check B — topología edge-pair (LA MÁS FIABLE).** Dos caras manifold que comparten una edge deben recorrerla en direcciones opuestas. Si `face1` recorre `(A→B)` y `face2` también recorre `(A→B)` ⇒ una de las dos está flipped. Coordinate-system-agnostic. Independiente de la intención del modelador. **Mejor herramienta para detectar winding mixto post-flip.**

3. **Check C — comparación vs vanilla.** Matchear faces entre el target y un vanilla equivalente (ej. `DZ/gear/camping/wooden_case.p3d`) por proximidad de centroides, comparar winding-derived normals. Solo aplicable cuando hay un equivalente vanilla cercano en geometría.

4. **Test in-game directo.** Rebuild PBO → servidor de test → inspeccionar visual + collision + actions + ballistic. Es el último filtro y el único 100% definitivo. Cuando todo lo anterior diga "OK", igualmente probar in-game.

#### Trampas conocidas (lessons learned)
- **`flip_winding.py` aplicado dos veces** vuelve al estado original (idempotente módulo 2). Si no recuerdas si lo aplicaste, mira si hay backup `.p3d.bak_v4_pre_winding_flip` — si existe, ya se aplicó al menos una vez.
- **`renegate_normals.py` es DEPRECATED** y basado en un malentendido. Si se aplicó, las normales del pool están negadas erróneamente; revertir negando otra vez. Ver "Scripts reutilizables".
- **Crate_Wooden tiene winding mixto en Visual LOD** (38.6% bad edges en Check B, 2026-04-25) pero **DayZ lo tolera en render** (verificado in-game: visual / balas / cursor / colisión OK). Los collision LODs (Geometry/LandContact/ViewGeo/FireGeo) son internamente consistentes. **El skill marca esto como CRITICAL en Check B**, lo cual está bien como señal preventiva, aunque el motor lo aguante en este caso particular. No re-flipar este modelo a menos que aparezca un síntoma in-game concreto.
- **`face.flags |= 0x20000`** (NoBackfaceCulling) — alternativa a duplicar caras para hacer faces doble-cara. Más barato que doblar el polycount; aún no verificado in-game al 100%. Si funciona, válido para piezas planas sin grosor.

---

## #Mass# debe vivir solo en Geometry LOD (added 2026-06-02)

**Origen**: LFQuad N1.5 cerrado 2026-06-02 (handoff `30_Sessions/2026-06-02-LFQuad-placement-fix-firegeo-mass-CLOSED.md`). Un `#Mass#` espurio (todos los valores en 0) en el FireGeo LOD del LFQuad hizo que AddonBuilder/binarize horneara la masa de ESE LOD → ODOL desplegado con `CoM=(0,0,0)` e inercia 0. `ECE_PLACE_ON_SURFACE` colocó el vehículo a la altura del CoM = 0 → spawn 0.48 m bajo tierra → eyección.

### Check añadido (mass-only-geometry)

Per-LOD validation: iterar TODOS los LODs del `.p3d` (Visual <1000, Geometry 1e13, Memory 1e15, LandContact 2e15, ViewGeo 6e15, FireGeo 7e15, Shadow) y comprobar:

- `Geometry LOD` (res 1e13): DEBE tener tagg `#Mass#` con valores no-cero y `lod.mass != None`.
- **TODOS los demás LODs**: NO deben tener tagg `#Mass#`. Si lo tienen (aunque sea con todos 0s), severidad **CRITICAL**.

Mensaje del check al fallar (FireGeo):
> *`FireGeometry LOD (res 7e15) contains a `#Mass#` tagg with N points. AddonBuilder/binarize will bake the mass of THIS LOD (not the Geometry LOD), producing CoM=(0,0,0) and inv_inertia=0 in the deployed ODOL → ECE_PLACE_ON_SURFACE will spawn the vehicle below ground. FIX: clear the mass from this LOD (set `point.mass = None` in the assemble, not `0.0`). py3d emits `#Mass#` if ANY point.mass is not None.*`

### Trampa de py3d (sutil)

py3d **emite el tagg `#Mass#` si ALGUNA `point.mass` del LOD es ≠ None**, aunque sea exactamente `0.0`. Por eso `point.mass = 0.0` deja el tagg con ceros → binarize lo usa → CoM=0. La forma correcta en los LODs no-Geometry es `point.mass = None` (Python None, no `0.0`).

### Detección headless (sin tocar el modelo)

```python
import py3d  # fork DayZ >= 1.2.0 (py3d.read_p3d NO existe: API confabulada)
with open(path, "rb") as f:
    m = py3d.P3D(f)
for lod in m.lods:
    if lod.resolution != 1e13:  # Anything but Geometry
        has_mass_tagg = any(
            p.mass is not None for p in (lod.points if hasattr(lod, "points") else [])
        )
        if has_mass_tagg:
            print(f"CRITICAL: LOD res={lod.resolution:.0e} has #Mass# tagg (must be Geometry-only)")
```

### Tool de fix headless

Para .p3d ya ensamblados con el bug, ver `LFQuad_dev/tools/fix_firegeo_mass.py` (LFQuad-specific pero el patrón generaliza: cargar p3d, iterar LOD ≠ Geometry, setear `point.mass = None`, reescribir). Verificación post-fix: `binarize.exe -always -addon=<dir> <src> <dst> <wildcard>` y leer `ModelInfo CoM` del ODOL (debe ser ≠ (0,0,0)).

### Cross-ref
LL-079 (bisección de LODs aisló el bug), LL-080 (la lección durable), R26 (criterios verificables), R35.1 (bisección antes de ensayo-error).

---

## Wheel-well clearance: medir contra RADIO de rueda, no contra HUB (added 2026-06-02, SP-024)

**Origen**: LFQuad sesión 2026-06-01 (handoff `30_Sessions/2026-06-01-LFQuad-spawn-launch-rootcause.md`, FASE 2). El R21 AC-7 del bake ROUND-2 validó "hubs fuera del hull" usando cajas de hub de 8 puntos. Pero la rueda real (radio 0.34) penetraba el chasis: mín 0.16-0.19 m del centro de rueda al chasis. PhysX-depenetración eyectó al vehículo; el Croco con despeje 0.43-0.46 m asienta limpio.

### Check añadido (wheel-well radius-aware)

Para cada rueda del modelo (proxy `wheel_*_*`):

1. Leer el radio efectivo del config: `wheel_radius` del `class Wheels { ... }` o el del `.p3d` de la rueda (cilindro BoundingBox.Y/2).
2. Computar `min_distance(chassis_geometry_hull, wheel_proxy_center)` con py3d (proyectar el centro del proxy sobre el hull del Geometry LOD del chasis).
3. Si `min_distance < wheel_radius` → **CRITICAL**: collider de rueda penetra chasis → PhysX-depenetración eyectará el vehículo al spawn.
4. Si `min_distance < wheel_radius * 1.20` → **WARNING**: margen mínimo (vibración / contacto intermitente). Croco-equivalent es ratio ~1.27.

Mensaje del check al fallar:
> *`Wheel '<wheel_proxy_name>': chassis-to-wheel-center distance = X.XX m < wheel_radius (Y.YY m). PhysX will treat this as self-penetration on spawn and eject the vehicle. FIX: reshape the chassis Geometry LOD to open wheel-wells (target clearance ≥ wheel_radius * 1.25-1.30, Croco-parity). NOT a hub-vs-hull check — must measure against the wheel volume (cylinder of `wheel_radius`).*`

### Anti-patrón cazado

El audit "hubs fuera del hull" mide contra la **caja del hub** (8 vértices pequeños), que pasa aun cuando la **rueda completa** (cilindro de radio efectivo) penetre. Es un falso PASS reproducible en cualquier vehículo donde el hub esté centrado pero el wheel-well sea estrecho.

### Cross-ref
LL-082 (la lección durable), `vehicle-structural-parity.md` Addendum 2026-05-26/29, `dayz-model-pipeline` sección wheel rigging.

---

## Crew check (get-in / copiloto) (added 2026-06-05)

Two new checks for any vehicle that declares a `Crew` (driver + co-driver / passengers).
Both are silent in-game (no RPT error) and cost days of churn when missed. Origin:
LFQuad 2026-06-05 (~7 days of churn diagnosing exactly these two).

### Check A — `seat_driver` / `seat_codriver` spread across the collision grid

Flag (probable broken get-in / co-driver never appears) if, in the **ViewGeo LOD**, the
selections `seat_driver` / `seat_codriver` are **spread over more than 1-2 components**.
Each seat should live in its **own dedicated component** (the Croco pattern). The engine
resolves which seat a get-in raycast hit via `CrewPositionIndex(component)`
(`transport.c:116`) on the component the raycast strikes. If seats are smeared over the
collision grid, the crew components are chaotic and the co-driver position never resolves.

### Check B — crew proxies are 90/45/45 isosceles triangles

Flag (player sits sideways / rotates on get-in) if the `crewdriver` / `crewcodriver`
proxies are isosceles 90/45/45 triangles → ambiguous angle-sort frame. They must be
**canonical** (three distinct angles). Cross-ref **dayz-proxy-align** "Crew proxies de
vehículos" for the frame convention (+Y → vehicle forward) and the canonical-triangle fix.
