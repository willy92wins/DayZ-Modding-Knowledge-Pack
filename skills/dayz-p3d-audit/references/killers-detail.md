# The 13 Silent P3D Killers — full detail

> Extracted from dayz-p3d-audit/SKILL.md 2026-07-07 (F3). The core SKILL.md keeps the index/summary and points here.


These produce ZERO engine errors but break functionality completely. The core SKILL.md carries the one-line index of all 13; this file holds the full body of each killer (root cause, detection snippet, fix, caveats).


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

**Where**: Named property on ALL collision LODs — Geometry (1e13), LandContact (2e15), ViewGeometry (6e15), FireGeometry (7e15), plus Roadway/Hitpoints when present. GeoPhys 2e13 and FireGeo 3e13 are Arma 3 resolutions that DO NOT apply to DayZ — the engine ignores LODs at those values. DayZ canon (matches `audit_p3d.py` and `dayz-model-pipeline`): Geometry 1e13, Memory 1e15, LandContact 2e15, ViewGeo 6e15, FireGeo 7e15.
In py3d: `lod.properties['autocenter'] = '0'`

### 4. Missing Memory LOD or Geometry LOD (CRITICAL)

A P3D without a Memory LOD (res ~1e15) will have no animation, no bounding data, and
potentially crash the engine. A P3D without a Geometry LOD (res ~1e13) will have zero
collision and zero action targeting.

**Required LODs for any interactive DayZ object:**
- LOD 0: Visual (res=0.0) — rendering
- Memory (res ~1e15) — animation axes, bounding, interaction points
- Geometry (res ~1e13) — collision and cursor raycasting

**Recommended additional LODs (DayZ canon — GeoPhys 2e13 / FireGeo 3e13 are Arma 3 values that do NOT apply to DayZ):**
- LandContact (res 2e15) — ground placement contact points
- ViewGeometry (res 6e15) — action cursor + occlusion raycasts
- FireGeometry (res 7e15) — ballistic raycast (bullets)

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
