---
name: dayz-realistic-animation-director
description: Dirige de principio a fin la creación, corrección, pulido, exportación, integración y verificación de animaciones realistas para DayZ. Úsala cuando el resultado deba sentirse físicamente creíble en jugador, manos y armas, recargas, unstuck/unjam, locomoción, criaturas, ocupantes de vehículos, mecanismos, props o simulaciones; especialmente ante clipping, dedos cruzados, articulaciones sobreextendidas, contacto falso, objetos que no siguen la mano, stutter, loops defectuosos o discrepancias Blender-vs-in-game. Orquesta `blender-animation` para autoría y `dayz-animation-pipeline` para contratos del motor; no sustituye consultas puramente técnicas sobre config, ASI, skeletons o exportación.
---

# DayZ Realistic Animation Director

Produce a credible animation and close its integration with honest evidence. This skill directs the work; Blender and DayZ skills retain technical authority.

## Authority boundary

Before acting, read [authority-and-routing.md](references/authority-and-routing.md).

- Invoke `blender-animation` before operating on Actions, rigs, constraints, curves, renders, or export from Blender.
- Invoke `dayz-animation-pipeline` before deciding format, skeleton, export mask, FPS/frame budget, notetracks, anim graph/ASI, compile, wiring, or DayZ integration.
- Invoke additional domain skill indicated in [authority-and-routing.md](references/authority-and-routing.md) for characters, creatures, vehicles, P3D, retargeting, or in-game test; then apply checks from [domain-gates.md](references/domain-gates.md).
- In case of conflict, specialized authority wins. Record divergence and stop affected gate; do not invent a third rule.

If the request is strictly technical —for example, choosing an `AnimationSource`, registering an `.anm`, or explaining an ASI state— let `dayz-animation-pipeline` be the primary skill. Use this skill when authoring, evaluating, or improving motion.

## Domain routing

| Animation | Skills added to director |
|---|---|
| Player, hands, custom human or infected | `dayz-characters`; for creatures verify first their actual bind/skeleton (in 1.30: no fixed index in skeletons.anim.xml, 250-bone limit removed) |
| Weapon, reload, unjam, or P3D mechanism | `dayz-weapons` if entity contract changes + relevant P3D/model skill (in 1.30: new bone remaps and dedicated ASI profiles) |
| Occupant, entry, or vehicle controls | `dayz-vehicles` (in 1.30: quad bikes + motorbikes `MOTO1`/`MOTO2`, 2-bone IK on handlebar) |
| Mocap/external donor | applicable retargeting skill; never without source→target map |
| Runtime test | active `dayz-test-ingame`/`dayz-mcp-verify`, with lease and lifecycle (in 1.30: Workbench Enfusion 2021 Live Editing) |

`blender-animation` and `dayz-animation-pipeline` remain mandatory for authoring and integration respectively; skills in the table do not replace them.

## Three checks that never substitute for each other

1. **Full chain:** measuring knuckles and tips does not validate intermediate phalanges. Sample all relevant segments and joints.
2. **Positive contact:** "no penetration" does not mean "gripping". Require a contact pair, target surface/landmark, and distance band.
3. **Relative locking:** sharing keyframes or a scalar curve does not prove two elements move together. Measure `T_actor^-1 * T_target` throughout the entire grip window.

A reproducible visual failure from user or in-game invalidates any offline `PASS`. Convert it into a fixture before authoring again.

## Mandatory gated workflow

### 0. Preserve and observe

- Inspect scene, Actions, current frame, selection, constraints, and windows before mutating.
- Always work from a versioned copy; do not overwrite source `.blend`.
- If fixing a defect, first reproduce failure with current scene and preserve that RED evidence.
- Read project contract (current `CLAUDE.md`, product spec, plan, and handoff) when existing.

### 1. Capture the DayZ technical contract

Ask `dayz-animation-pipeline` for applicable route and record:

- animation type and authoritative skeleton/rig;
- FPS, duration or frame budget, and loop rules;
- notetracks/events and runtime states;
- included/excluded bones and complete mobile objects/selections;
- artifacts for export, compile, wiring, build, and in-game test.

Do not hardcode 291 frames, 30 FPS, or SR2M notetracks for other animations. Each task obtains its active contract.

### 2. Define acceptance before posing

Read [motion-quality-contract.md](references/motion-quality-contract.md) and create a per-task contract declaring only applicable modules:

- key poses and beats;
- joints/chains and calibrated limits;
- contacts, surfaces, and `contact_on..release` windows;
- prohibited collision pairs and permitted contacts;
- objects that must preserve relative transformation;
- intentional impact, snap, or sliding exceptions;
- actual entry/exit pose and in-game states to test.

Tolerances must come from reference, geometry, or an explicit decision. Never adjust threshold to make current candidate pass.

Every contract declares exactly `contract_mode: "diagnostic"` or `contract_mode: "production"`; missing or unknown values are errors. A contract capable of granting `OFFLINE_PASS` uses `production`. Each check declares provenance (`source_kind`, `source`, `verified_date`, `method`) and any `segment_clearance` check requires shared geometric provenance for capsule radii. A `diagnostic` contract may reproduce a failure, but `eligible_for_offline_pass` will always be false.

For a continuous window of contact, collision, locking, order, joint range, or continuity use consecutive `frame_range` with `step: 1`; production requires it. A sparse list of golden poses does not prove what happens between them.

### 3. Blocking

With `blender-animation`, author only golden poses: start, anticipation, contact, maximum effort, release, recovery, and end.

- Render each pose in on-axis view and at least one oblique view.
- Validate anatomy, silhouette, contact, and collision before interpolating.
- For hands, read [biomechanics-and-contact.md](references/biomechanics-and-contact.md) and evaluate all five fingers, wrist, forearm, elbow, shoulder, and clavicle when part of the gesture.
- Do not advance to spline if a key pose already clips, is overextended, or misses target.

### 4. Motion and effort

- Apply blocking → spline → polish via `blender-animation`.
- Use timing, spacing, arcs, anticipation, overlap, moving holds, and settle according to physical intent.
- Validate position, rotation, velocity, acceleration, and jerk on relevant elements.
- Distinguish an intentional snap/impact via a declared window; outside of it, a spike is stutter.
- In mechanisms, move full hierarchy or functional selection, not only visual piece seen from a camera.

### 5. Offline audit

Run sampler and validator when Blender is available:

```powershell
& $env:BLENDER_EXE --background '<scene.blend>' --python '<skill>\scripts\sample_blender_motion.py' -- --contract '<contract.json>' --output '<report.json>'
python '<skill>\scripts\validate_motion_contract.py' --report '<report.json>' --contract '<contract.json>' --output '<audit.json>'
```

Interpret validator exit codes:

- `0`: all required checks pass;
- `1`: valid input, one or more required checks fail;
- `2`: invalid contract, sample, or execution; no quality verdict.

In addition to JSON:

- review full video at real speed;
- review multi-angle renders of contact, extremes, transitions, and recovery;
- look for clipping between keyframes, not only on key frames;
- check start/end against actual runtime entry pose.

### 6. Exporta e integra

- Hand off Blender export to `blender-animation` following its active contract.
- Hand off artifact to `dayz-animation-pipeline` for compile, ASI/config, build, and deploy.
- Verify artifact actually deployed, not only source. In DayZ 1.30, animation graphs are structured into modular Enfusion Config `.agf` files indexed from `AnimSrcGraph` `.agr`, and `.asi` files use `AnimSetInstanceSource`.
- Do not declare that Workbench, DayZATool, Blender MCP, or DayZ executed if no evidence of that execution exists in the session.

### 7. Gate in-game

Lee [evidence-and-integration.md](references/evidence-and-integration.md).

- Test stances, cameras, and states that might alter IK or blending. In 1.30, Workbench Animation Editor allows **Live Editing** on active clients for interactive visual debugging of transitions and graphs.
- Review RPT and compare timing, contact, clipping, and mechanical states against contract.
- If in-game contradicts Blender, in-game rules and the case becomes a regression.
- If environment does not allow testing, terminate in `MANUAL_REQUIRED`, not PASS.

## Output states

- `FAIL`: at least one mandatory gate fails.
- `OFFLINE_PASS`: contract, scene, audit, renders, and offline artifact approved; game test pending.
- `MANUAL_REQUIRED`: next gate requires an action or tool that is unavailable.
- `IN_GAME_PASS`: deployed build and DayZ behavior are verified with evidence.

Always report which gates were executed, what evidence exists, what was omitted, and why.

## Regression policy

When a new defect appears:

1. freeze failed scene as read-only input;
2. write a minimal fixture that fails for that reason;
3. demonstrate RED;
4. implement or tighten the check;
5. demonstrate GREEN with a corrected sample to avoid a tautological test;
6. only then modify production animation.

Run reusable suite with:

```powershell
python '<skill>\scripts\run_regression_tests.py'
```

To include the real SR2M fixture, define `SR2M_V44_BLEND` and add `--real-fixtures`. If variable is missing, correct result is `SKIP_REAL_FIXTURE`, not PASS.

## DayZ 1.30 Exp (build 1.30.164014)

### What changes in 1.30 for realistic animation direction

1. **Motorbike rider integration [EXACT]:**
   - Dedicated animation instances: `MOTO1 = 10` (Jawa 50cc) and `MOTO2 = 11` (Jawa Bitrak tricycle) in `exp\scripts\scripts\4_World\Entities\Vehicles\VehicleAnimInstances.c:13-14`.
   - Third-person vehicle camera with elastic lag: `DAYZCAMERA_3RD_VEHICLE_MOTORBIKE = 32` in `exp\scripts\scripts\4_World\Entities\ManBase\DayZPlayer\DayZPlayerCameras.c:20`.
   - Handlebar grip with continuous two-bone IK solvers (`AnimSrcNodeIK2` and `AnimSrcNodeIK2Target` in `Vehicles.agf`) modulated by physical lean and roll variables (`VehicleSteering`, `VehicleThrottle`, `VehicleSuspension`).
   - Unified transition query via `HumanCommandVehicle.IsTransitioning()` (`exp\scripts\scripts\3_Game\human.c:735-738`).
2. **Surrender refactoring [EXACT]:**
   - *(Up to 1.29: surrendering physically created invisible `SurrenderDummyItem` in hands; since 1.30 Exp: `SurrenderDummyItem` is completely eliminated and natively governed via `PlayerBase.SetSurrenderState(bool)` and `Man.IsSurrendered()` [`exp\scripts\scripts\3_Game\Entities\Man.c:67`, `exp\scripts\scripts\4_World\Classes\EmoteManager.c:314, 1248-1250`]).*
3. **Dynamic instance control and in-hands decoupling [EXACT]:**
   - Direct transition between animation instances at runtime with `Human.SetAnimationInstanceByName(string animationInstanceName, float blendingTime)` (`exp\scripts\scripts\3_Game\human.c:1384`), backed by `"Empty"` profile registered in `player_main.asi` (`DayZPlayerCfgBase.c:1537`).
   - Decoupling of in-hands item swapping: `HumanItemAccessor.OnItemInHandsChanged(bool pInstant, bool pChangeAnimationInstance)` (`exp\scripts\scripts\3_Game\humanitems.c:112`).
4. **Per-stance camera rotation and speed limits [EXACT]:**
   - `HumanInputController` exposes `SetErectSpeedLimit`, `SetCrouchSpeedLimit`, `SetProneSpeedLimit`, and `DisableErectCameratHorizontalRotation` [sic], etc. (`exp\scripts\scripts\3_Game\human.c:230-243`).
5. **Catalog of 11 new Full-Body actions [EXACT]:**
   - `CMD_ACTIONFB_COMBINATIONLOCK = 256` to `CMD_ACTIONFB_WETCLOTHWELL = 266` (`exp\scripts\scripts\3_Game\dayzplayer.c:889-899`), including combination lock, mortar, brick stacking, and rope ladder.
6. **Skeleton de-indexing and creature kinematics [EXACT]:**
   - Removal of 250-bone limit; global indices resolved at runtime by name hash. In `skeletons.anim.xml` only `EntityPosition` retains `index="0" movement="true" lod="0"` (`work\changelog-1.30-exp-modding.md:31`, `exp\anims_cfg\DZ\anims\cfg\skeletons.anim.xml:39, 986-988`).
   - Procedural rotation in quadrupeds for terrain alignment: `AnimSrcNodeProcTransform AlignToTerrain_Rot` with `SlopeAngleX * 0.0174532925...` (`exp\animals\DZ\animals\animations\!graph_files\wolf\wolf_maingraph.agf:5-18`).
   - New mental state for infected: `MINDSTATE_COWER` (`exp\scripts\scripts\3_Game\Entities\DayZInfected.c:18`).
7. **Integration tools and physics in Workbench [EXACT]:**
   - Workbench Animation Editor updated to Enfusion 2021 with **Live Editing** of graphs on running clients (`work\changelog-1.30-exp-modding.md:48, 62`).
   - Workbench Ragdoll Editor to configure and edit `.ragdoll` files (`work\changelog-1.30-exp-modding.md:47`).
   - Native separation between animated death and ragdoll in scripts: `PhysicsSetSimpleDeath(bool)` vs `PhysicsSetRagdoll(bool)` (`exp\scripts\scripts\3_Game\human.c:1448-1452`).

### What breaks in 1.29 contracts and assets and how to migrate

| Broken element | Cause in 1.30 | Required action |
|---|---|---|
| Monolithic proprietary `.agr` graphs | Format replaced by modular Enfusion Config `.agf` text files (`Locomotion.agf`, `Vehicles.agf`, etc.) [EXACT: `player_main.agr:1587`] | Re-export workspaces from Workbench Animation Editor 2021 or reconstruct modifications in text across corresponding `.agf` modules. |
| `.ast` templates with anonymous groups | Removed support for `$groupType { #ngroupnames 0 ... }` [EXACT: `changelog:42`] | Assign each group an explicit `Name` attribute (`Name "Default"`, `Name ".unnamed"`). |
| `.asi` files with `$animsetinstance` syntax | Migrated to `AnimSetInstanceSource` class [EXACT: `anims_cfg.diff:624`] | Convert `#template`/`#parent`/`$animations` directives to Enfusion Config structure. |
| `Buffer Save` / `Buffer Use` nodes | Eradicated completely from animation engine [EXACT: `changelog:41`] | Replace buffer logic with control variables in `ControlTemplate AnimSrcGCT` or direct state machine connections. |
| `SurrenderDummyItem` dependency | Dummy object removed [EXACT: `EmoteManager.c:1242`] | Replace item-in-hands checks with calls to `PlayerBase.SetSurrenderState(bool)` and `IsSurrendered()`. |
| Fixed indices in `skeletons.anim.xml` | Manual indices ignored except on `EntityPosition` [EXACT: `changelog:43`] | Remove `index` attributes from XML; ensure exact name match with `.xob` model. |

### Migration checklist for animation director

- [ ] **Weapon mappings:** Verify whether weapon or interactive prop uses new remaps (`LugerBoneRemap`, `LeeEnfieldBoneRemap`) or dedicated `.asi` (`bandage.asi`, `hayhook.asi`, etc.).
- [ ] **Vehicle occupants:** On motorcycles, audit relative locking of both hands to handlebars (`AnimSrcNodeIK2`) and feet to footrests across all phases of `HumanCommandVehicle.IsTransitioning()`.
- [ ] **Surrender:** Confirm no offline check or fixture assumes a virtual item in hands during surrender state.
- [ ] **Creature terrain:** Check that animal paw contacts include procedural angular offset of `AnimSrcNodeProcTransform` against slopes (`SlopeAngleX`).
- [ ] **Templates and Instances:** Audit that delivery `.ast` files declare `Name` on all groups and `.asi` files use `AnimSetInstanceSource` class.
- [ ] **Live validation:** Leverage Workbench Enfusion 2021 Live Editing to verify continuous blend parameters on active client before final packaging.

## Resource index

- [authority-and-routing.md](references/authority-and-routing.md) — authority, precedence, and skill selection.
- [motion-quality-contract.md](references/motion-quality-contract.md) — sample/contract format and catalog of checks.
- [biomechanics-and-contact.md](references/biomechanics-and-contact.md) — anatomy, contact, self-collision, and synchronization.
- [domain-gates.md](references/domain-gates.md) — checks by animation domain.
- [evidence-and-integration.md](references/evidence-and-integration.md) — offline evidence, export, deploy, and in-game.
- `scripts/sample_blender_motion.py` — Blender → neutral JSON report.
- `scripts/validate_motion_contract.py` — report + contract → deterministic audit.
- `scripts/run_regression_tests.py` — synthetic and optional real fixtures.

## Stop conditions

Stop progression and request missing decision or evidence when:

- no input/output reference exists and a choice would alter choreography;
- current pipeline and a reference disagree on skeleton, export mask, or runtime state;
- full mechanical part cannot be identified;
- a tolerance can only be chosen by looking at candidate intended to pass;
- offline gate passes but visual or in-game review fails;
- integration test requires an unavailable tool or permission.
