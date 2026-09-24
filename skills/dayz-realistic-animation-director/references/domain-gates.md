# Domain gates

Use only the sections relevant to the task, in addition to the common contract and the current `dayz-animation-pipeline` route.

## Player or humanoid action

- Verify the allowed body layer/export mask before authoring.
- Track centre-of-mass implication, shoulder/clavicle contribution and counter-motion.
- Preserve locomotion/root channels that the runtime layer owns.
- Test stance and camera variants that can change IK/blending.
- Review transitions into and out of the action, not only its central pose.
- **Surrender state (DayZ 1.30 [EXACT]):**
  *(Hasta 1.29: la rendición creaba físicamente en manos el ítem virtual `SurrenderDummyItem` para bloquear la recarga e interacción; desde 1.30 Exp: se elimina por completo `SurrenderDummyItem` y la rendición se gestiona nativamente con `PlayerBase.SetSurrenderState(bool)` y `Man.IsSurrendered()` [`exp\scripts\scripts\3_Game\Entities\Man.c:67`, `exp\scripts\scripts\4_World\Classes\EmoteManager.c:314, 1248-1250`]).*
  Do not author interactions assuming an invisible dummy weapon in hands during surrender.
- **Dynamic Animation Instance switching [EXACT]:**
  Script can now force transitions between `.asi` instances at runtime via `Human.SetAnimationInstanceByName(string animationInstanceName, float blendingTime)` (`// [EXACT] exp\scripts\scripts\3_Game\human.c:1384`). To reset back to unarmed base pose without an item, DayZ registers the `"Empty"` profile on `player_main.asi` (`// [EXACT] exp\scripts\scripts\4_World\Entities\ManBase\DayZPlayer\DayZPlayerCfgBase.c:1537`).
- **Stance-based speed and camera rotation limits [EXACT]:**
  `HumanInputController` can clamp movement speed and freeze horizontal camera rotation per stance:
  - `SetErectSpeedLimit(bool bShouldDisable, int pMaxErectSpeed)`, `SetCrouchSpeedLimit(...)`, `SetProneSpeedLimit(...)` (`// [EXACT] exp\scripts\scripts\3_Game\human.c:230-233`).
  - `DisableErectCameratHorizontalRotation(bool pDisable)`, `DisableCrouchCameratHorizontalRotation(...)`, `DisableProneCameraHorizontalRotation(...)` (`// [EXACT] exp\scripts\scripts\3_Game\human.c:240-243`).
  Author transitions knowing that extreme horizontal looking can be restricted natively during heavy or prone gestures.
- **Animation tag evaluation [EXACT]:**
  Active graph tags can be queried on fixed tick via `HumanAnimInterface.IsTag(TAnimGraphTag iTag)` (`// [EXACT] exp\scripts\scripts\3_Game\human.c:319`).
- **New Full-Body action constants (DayZ 1.30 [EXACT]):**
  DayZ 1.30 registers 11 new full-body actions in `DayZPlayerConstants` (`// [EXACT] exp\scripts\scripts\3_Game\dayzplayer.c:889-899`):
  - `CMD_ACTIONFB_COMBINATIONLOCK = 256` (prone combination lock manipulation, paired with `CMD_ACTIONMOD_COMBINATIONLOCK = 256` for erect/crouch)
  - `CMD_ACTIONFB_WASHFACEPOND = 257` (crouch face washing, paired with `CMD_ACTIONMOD_WASHFACE = 257`)
  - `CMD_ACTIONFB_BUILDROPELADDER = 258` (crouch crafting rope ladder)
  - `CMD_ACTIONFB_BRICKSTACK = 259` (erect/crouch brick stacking)
  - `CMD_ACTIONFB_BRICKTROWEL = 260` (erect/crouch trowel masonry)
  - `CMD_ACTIONFB_MIX_MORTAR = 261` (crouch bucket mortar mixing)
  - `CMD_ACTIONFB_DRINKWELL_BUCKET = 262` (erect drinking from well bucket)
  - `CMD_ACTIONFB_SHARPEN = 263` (crouch stone tool sharpening)
  - `CMD_ACTIONFB_WASHFACEWELL = 264` (erect well face washing)
  - `CMD_ACTIONFB_WETCLOTH = 265` (crouch cloth wetting at pond)
  - `CMD_ACTIONFB_WETCLOTHWELL = 266` (erect cloth wetting at well)

## Hand with weapon or object

- Apply every rule in `biomechanics-and-contact.md`.
- Identify the functional moving assembly before posing.
- Define jammed/closed/open or equivalent mechanical states from verified geometry/data.
- Keep contact lock until the declared release; after release enforce clearance.
- Validate regrip as approach → open hand → enclose target → close, rather than teleporting a closed fist.
- Compare start/end against the real runtime IK pose.
- **Hands item decoupling [EXACT]:**
  Changing the item in hands no longer automatically forces an animation instance change if `pChangeAnimationInstance = false` in `HumanItemAccessor.OnItemInHandsChanged(bool pInstant = false, bool pChangeAnimationInstance = true)` (`// [EXACT] exp\scripts\scripts\3_Game\humanitems.c:112`) and `EnableAutoAnimInstUpdateOnHandsChange(bool)` (`humanitems.c:115`).
- **Dedicated weapon and tool `.asi` profiles [EXACT]:**
  DayZ 1.30 splits generic 1H/2H instances into dedicated `.asi` files for specific tools and weapons (`DayZPlayerCfgBase.c:1540-1620`), including:
  - Bandage: `props/player_main_1h_bandage.asi`
  - Sickle: `props/player_main_1h_sickle.asi`
  - HayHook: `weapons/player_main_1h_hayhook.asi`
  - Hatchet: `weapons/player_main_1h_hatchet.asi`
  - Pitchfork: `weapons/player_main_2h_pitchfork.asi`
  - Sword: `weapons/player_main_2h_sword.asi`
  - Luger P08: `weapons/player_main_luger08.asi` (with `LugerBoneRemap` in `DayZPlayerCfgBase.c:1610`)
  - MP18: `weapons/player_main_mp18.asi`
  - Lee-Enfield: `weapons/player_main_leeEnfield.asi` (with `LeeEnfieldBoneRemap` in `DayZPlayerCfgBase.c:1594`)
  - SCAR-L: `weapons/player_main_SCARH.asi`
  Audit hand poses against the exact weapon/prop `.asi` profile rather than assuming generic `player_main_1h.asi` or `player_main_2h.asi`.

## Locomotion

- Define gait, stride, cadence, stance and root-motion ownership.
- Check foot locking, ground penetration, slip distance and support transitions.
- Track pelvis/COM arcs and upper-body counter-rotation.
- Match cycle pose and velocity at the seam.
- Test slopes/turning only if the DayZ graph or runtime consumer will exercise them.
- Audit transitions under posture speed limits (`SetErectSpeedLimit`, `SetCrouchSpeedLimit`, `SetProneSpeedLimit` in `human.c:230-233`). When speed limits are enforced, root motion scaling must not cause foot sliding.

## Creature

- Obtain the actual skeleton, rest pose and gait reference for that species/rig.
- **Skeleton bone index deregulation (DayZ 1.30 [EXACT]):**
  *(Hasta 1.29: skeletons.anim.xml definía índices fijos y limitaba el sistema a 250 huesos; desde 1.30 Exp: se elimina el límite de 250 huesos; los índices se calculan en runtime por hash del nombre del hueso y skeletons.anim.xml solo conserva index="0" en EntityPosition [`work\changelog-1.30-exp-modding.md:31, 43`, `exp\anims_cfg\DZ\anims\cfg\skeletons.anim.xml:986-988`]).*
  Four new animal skeletons are introduced in DayZ 1.30: `ovis_gmelini_skeleton.xob` (mouflon), `canis_familiaris_dobermann_skeleton.xob`, `canis_familiaris_german_shepherd_skeleton.xob`, and `varanus_griseus_skeleton.xob` (`skeletons.anim.xml:986-1150`).
- **Graph modularity (`.agf` files) [EXACT]:**
  Creature graphs migrate from monolithic binary `.agr` to modular Enfusion Config `.agf` files (`wolf_maingraph.agf`, `ambientlife_maingraph.agf`, `locomotion.agf`) referenced by master `AnimSrcGraph` `.agr` indexes (`wolf_graph.agr:157-159`).
- **Procedural terrain alignment (`AnimSrcNodeProcTransform`) [EXACT]:**
  Quadrupeds use procedural bone transforms driven by terrain slope:
  ```enfusion
  // [EXACT] exp\animals\DZ\animals\animations\!graph_files\wolf\wolf_maingraph.agf:5-18
  AnimSrcNodeProcTransform AlignToTerrain_Rot {
   EditorPos -1 -4.7
   Child "Master_SM"
   Expression "SlopeAngleX  * 0.01745329251994329576923690768489"
   Bones {
    AnimSrcNodeProcTrBoneItem "{6930A8DF8B23795C}" {
     Bone "scene_root"
     Axis X
     Space Model
     Op Rotate
     Amount 1
    }
  ```
  Validate that root and collarbone rotation compensations match the terrain slope angle (`SlopeAngleX`) to prevent feet penetrating slopes.
- **Prediction and 2D Look poses [EXACT]:**
  Creatures use `AnimSrcNodePrediction` on `EntityPosition` (`PercentTime 0.3`) for translational and rotational foot prediction, and `AnimSrcNodePose2` with `LookDirX` and `LookDirY` for head tracking.
- **Infected mental states [EXACT]:**
  DayZ 1.30 adds `MINDSTATE_COWER` (`// [EXACT] exp\scripts\scripts\3_Game\Entities\DayZInfected.c:18`), enabling cowering/fear behavior. Look blending uses `AnimSrcNodeBlendT AggroLookBlendT` conditioned on `Look` (`// [EXACT] exp\anims_workspaces\DZ\anims\workspaces\infected\infected_main\locomotion.agf:19-33`).

## Vehicle occupant

- Source seat, grip, pedal/footrest and steering anchors from actual model data.
- Keep hands/feet locked to moving controls through their travel.
- Audit elbow/knee solutions at steering extremes and animation transitions.
- Validate get-in/out approach side and clearance separately from the seated loop.
- Delegate anchor extraction and vehicle runtime behavior to their domain skills.
- **Motorcycles and 2-wheelers (DayZ 1.30 [EXACT]):**
  - **Animation instances:** `VehicleAnimInstances.c:13-14` registers `MOTO1 = 10` (Jawa 05 / 50cc) and `MOTO2 = 11` (Jawa Bitrak 3-wheeler).
  - **Camera:** 3rd person motorcycle camera with spring lag is registered as `DAYZCAMERA_3RD_VEHICLE_MOTORBIKE = 32` (`// [EXACT] exp\scripts\scripts\4_World\Entities\ManBase\DayZPlayer\DayZPlayerCameras.c:20`).
  - **Handlebar IK:** Hand grip choreography uses continuous two-bone IK solvers (`AnimSrcNodeIK2` / `AnimSrcNodeIK2Target` in `Vehicles.agf`) attached to vehicle steering pivots.
  - **Rider dynamics:** Rider torso, spine, and head lean curves are driven by dynamic inputs: `VehicleSteering`, `VehicleThrottle`, and `VehicleSuspension` (in `Vehicles.agf`).
  - **Transition queries:** Script queries transitions cleanly via `HumanCommandVehicle.IsTransitioning()` (`// [EXACT] exp\scripts\scripts\3_Game\human.c:735-738`), checking `IsGettingIn()`, `IsGettingOut()`, or `IsSwitchSeat()`.
  - **Crash and ejection:** Rider fall/crash ejection currently delegates to unconsciousness (`eModifiers.MDF_UNCONSCIOUSNESS` in `// [EXACT] exp\scripts\scripts\4_World\Entities\DayZPlayerImplement.c:2454`) pending full ragdoll command support.

## Mechanical object or prop

- Identify selection/hierarchy, pivot/axis, limits and all attached sub-pieces.
- Use physically plausible acceleration, hard-stop, overshoot and damping for the mechanism.
- Check travel envelope and object-object collisions.
- Confirm whether DayZ drives it through `model.cfg`, script, weapon bones or skeletal animation; this decision belongs to `dayz-animation-pipeline`.
- **Graph and Template constraints (DayZ 1.30 [EXACT]):**
  - **No Buffer nodes:** `Buffer Save` and `Buffer Use` nodes are completely removed from animation graphs (`work\changelog-1.30-exp-modding.md:41`). State persistence must use control variables (`AnimSrcGCTVar*`).
  - **Named AST groups:** Anonymous animation groups (`$groupType { #ngroupnames 0 ... }`) are forbidden in `.ast` templates (`work\changelog-1.30-exp-modding.md:42`). Every group must declare an explicit `Name` (e.g. `Name "Default"`, `Name ".unnamed"`).
  - **Enfusion Config ASI:** Instance files must use `AnimSetInstanceSource` syntax rather than legacy `$animsetinstance`.

## Physics simulation

- Use `blender-animation` for simulation setup and bake discipline.
- Bake once before sampling; repeated unbaked evaluation is not deterministic evidence.
- Validate contacts and energy/settling after bake.
- Confirm the export route can carry the baked result into DayZ; do not assume Blender-only deformation survives.
- **Ragdoll vs Simple Death separation (DayZ 1.30 [EXACT]):**
  Workbench now includes a native **Ragdoll Editor** for `.ragdoll` files (`work\changelog-1.30-exp-modding.md:47`).
  Scripts separate animated death from ragdoll simulation:
  - `PhysicsSetSimpleDeath(bool pEnable)` handles animated death (`// [EXACT] exp\scripts\scripts\3_Game\human.c:1448-1449`).
  - `PhysicsSetRagdoll(bool pEnable)` and `PhysicsIsRagdoll()` handle physical ragdoll simulation (`// [EXACT] exp\scripts\scripts\3_Game\human.c:1451-1452`).
  - `HumanCommandUnconscious.IsRagdoll()` queries whether an unconscious character is ragdolling (`exp\scripts\scripts\3_Game\human.c:646`).
  When authoring death animations, note that DayZ default deaths invoke `PhysicsSetSimpleDeath(true)` rather than pure ragdoll.
