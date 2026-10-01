# Vehicle rider IK pose — extrapolate body pose from .p3d anchors (Layer 1 + 2 hybrid)

A route that produces the seated body pose of a vehicle driver or passenger by **solving IK from a handful of fixed anchors in the `.p3d`** instead of keyframing the body bone-by-bone. Useful when the vanilla shared driver pose looks wrong on a vehicle whose geometry differs (quad/motorbike with handlebar vs car with steering wheel, unusual grip/footpeg positions, atypical seat height).

## When this route applies

- The vehicle's geometry breaks the vanilla shared driver/passenger pose (hands floating off the wheel, feet off the floor, torso clipped).
- You don't have an animator to author 4 hand-keyed clips and don't want to.
- You can place 5 memory points in the `.p3d` Memory LOD precisely (this is the prerequisite).

## When it does NOT apply

- You're authoring expressive action animations (combat, reload-while-driving) — that's keyframe work in `references/skeletal-anm-enfusion.md`.
- The vanilla pose already looks acceptable — don't pay the rest-pose calibration cost (see Caveat below) just to fix a minor offset.
- You haven't accepted **anchor 3** (the one-anim-mod wall): this route still produces a character/creature animation mod and conflicts with every other anim-mod on the server. (scoped 2026-09-28) That holds when the clips ship through a graph replacement; the child-`.asi` route (§Per-vehicle pose without a graph change) replaces no graph file.

## The 5 anchors

Place these as Memory LOD points in the vehicle `.p3d`. Names are conventions used by the LFQuad reference case — adapt to your project as long as your `ik_pose_to_seanim.py` config matches.

| Memory point | Drives | Notes |
|---|---|---|
| `crewdriver` | pelvis (sit position) | already used by vanilla for `pos_driver`; reuse the same point |
| `pos_grip_L` / `pos_grip_R` | left/right hand IK target | for steering wheels: place at the rim; for handlebars: at the grips |
| `pos_footpeg_L` / `pos_footpeg_R` | left/right foot IK target | for cars: floor pedal area; for bikes: footpegs |

For copilot/passenger you place the same 6 anchors under a different name prefix (e.g. `crewcodriver`, `pos_co_grip_L`...).

## The 21 joints of `OFP2_ManSkeleton` that get solved

This skill ships `references/player-skeleton.md` with the full bone catalog. For seated IK the solver writes only these 21:

- **Spine chain (7)**: `Pelvis`, `Spine`, `Spine1`, `Spine2`, `Spine3`, `Neck`, `Head`
- **Arms (4 per side, mirrored)**: `LeftShoulder`, `LeftArm`, `LeftForeArm`, `LeftHand` (+ `Right*`) — 8 joints across both arms
- **Legs (3 per side, mirrored)**: `LeftUpLeg`, `LeftLeg`, `LeftFoot` (+ `Right*`) — 6 joints across both legs

Total: 7 (spine) + 8 (arms) + 6 (legs) = 21 joints.

The hand IK helpers (`LeftHandIK`, `RightHandIK`, `LeftHandIKTarget`) are NOT written by this solver — they are driven by the `OFP2_ManSkeleton` overlay at runtime when the engine plays the resulting `.anm`. Authoring them would over-constrain the pose.

## The solver — 2-bone analytic IK per limb + straight spine

Empirically validated in the LFQuad case (`LFQuad_dev/handoff_2026-05-28.md`, LL-pose-from-anchors): **FABRIK and CCD are not needed**. A 2-bone analytic IK per arm and per leg, plus a straight-chain spine with a single `lean` parameter, produces hand→grip error 0.0000 in the validated cases.

```
ARM solver (per side):
  Inputs:
    shoulder_pos     # from spine chain
    grip_target_pos  # from anchor
    upper_arm_length, fore_arm_length  # from rest pose
    pole_hint        # forward + slightly down, prevents elbow flip
  Outputs:
    LeftShoulder.rotation
    LeftArm.rotation
    LeftForeArm.rotation
    LeftHand.rotation = look_at(grip_axis, world_up_blended)

LEG solver (per side):
  Identical shape, with hip→knee→ankle and pole hint forward.

SPINE chain:
  Pelvis at anchor (height + small forward tilt = lean * spine_length)
  Spine .. Spine3 distributed evenly along straight line from Pelvis to base of Neck
  Neck/Head: aligned to the same vector, with optional small look-ahead
```

The `lean` parameter is the only torso degree of freedom this solver exposes: `0` = vertical torso (sport-bike rider over the tank), `0.2` = slight forward lean (typical car driver), `0.5` = aggressive forward lean (sport-car / scooter passenger holding rider). Above ~0.6 the spine clips, so cap it.

Optional refinement: subtle **torso twist** with handlebar yaw. When `steerMax` is non-zero, the spine chain twists `0.2 * steerMax` between Pelvis and Spine3 to keep elbows naturally angled. Disable for cars where the body should stay neutral.

## Pipeline (start to finish)

1. **Place anchors in the `.p3d` Memory LOD.** Use `dayz-p3d-inspector` to extract → Recipe JSON → add the 5 memory points → rebuild. Or `dayz-model-pipeline` (py3d) if you are assembling from scratch.
2. **Author or validate the pose interactively** (optional but strongly recommended for the first vehicle). The LFQuad reference case used a Three.js viewer (`LFQuad_pose_viewer.html`) with sliders for `lean`, `steerMax`, and per-anchor positions; the viewer ran the same solver and exported the canonical pose JSON. Building one yourself takes about a day; reusing the LFQuad viewer pattern is faster — the baked-viewer-reuse trick (decode the existing viewer's `const DATA` block instead of re-parsing the `.p3d` with py3d) is documented in SKILL.md anchor 5 (LL-baked-viewer-reuse) and applied in `selection-painter-for-actions.md` for the painter case.
3. **Generate the SEAnim variants** with `scripts/ik_pose_to_seanim.py` (this skill). One SEAnim per variant: idle, steer-left, steer-right, plus copilot idle if applicable.
4. **User runs DayZATool** (`--generate-anim file.seanim`) on Windows → `.anm`.
5. **Wire in the vehicle graph** — point the appropriate transition or state at the new `.anm`. Up to 1.29 the vehicle sub-graph was `Vehicles.agr`, a text file in the old `$AnimGraph 7` format (corrected 2026-09-28: this step used to call it a binary `vehicles.agr` and the step Workbench-only; evidence in `anim-graph.md` §Vehicles.agf). (added 2026-09-16, DayZ 1.30 Exp) [EXACT] In 1.30 the graph is Enfusion Config text (`DZ\anims\workspaces\player\player_main\Vehicles.agf`, `MotorBikeSTM` at `Vehicles.agf:1582-1751` (closing brace at `:1751`) [EXACT]) and the vanilla rider sets are bound through `player_main.ast:1119-1120` (`Jawa_05`, `Jawa_Bitrak`) and `player_main.asi:5088` (`Vehicle.Jawa_05.*`). [UNVERIFIED] Editing the `.agf` by hand and having the engine accept it has not been tried; the Workbench Animation Editor (2021 Enfusion, live editing) remains the measured path. However it is edited, the graph sits at vanilla paths, so shipping it makes this a graph-replacing mod (the wall below). A route that leaves the graph alone, measured while the vehicle stands, is in §Per-vehicle pose without a graph change.
6. **Test in-game.** RPT must show no bone-name errors. Verify pose visually from inside the vehicle (1st person) and outside (3rd person, both sides).

## The wall this route does NOT escape

**The one-anim-mod wall (anchor 3 of SKILL.md) still applies.** Loading two mods that ship character/creature animations crashes client/server, Enfusion engine limit. This route just produces better-quality animations in the slot that wall allows — it does not give you more slots. Every plan that ships these SEAnims MUST tell the user about the conflict. (scoped 2026-09-28) This applies when the clips reach the engine by replacing the graph or adding a column of your own; the child-`.asi` route below replaces no graph file, like the weapon ASI route (anchor 3 correction in SKILL.md). Loading it next to a graph-replacing mod has not been tested, and it can still collide with another mod that swaps the player's animation instance.

For Layer 1 cosmetics that are NOT character animation (the handlebar/steering wheel rotation itself, hide-on-attach for accessories), see `handlebar-and-steering-config.md` and `item-ik-and-hide.md` — those do not hit the wall.

## Per-vehicle pose without a graph change (added 2026-09-28, DayZ 1.30 Exp; measured while standing the same day)

Where the hands come from decides what any route has to ship. [EXACT][CLAIM-ANIM-HAND-IK-FROM-CLIP-130] None of the ten IK nodes in `Vehicles.agf` reads a vehicle memory point, bone or config value. Each `AnimSrcNodeIK2Target` takes a child pose and the `LHandIKTarget`/`RHandIKTarget` chain bindings, and each `AnimSrcNodeIK2` re-solves those chains: `AnimNodeIK2Target0` over `SteeringBlend` (`Vehicles.agf:17-30`), `AnimNodeIK2hands` (`:31-46`), with `SteeringBlend` picking the `Vehicle.DriverSteeringExtreme` or `Vehicle.DriverSteeringMain` pose (`:2614-2626`). The file has no foot IK (`FootIK`: 0 hits). [INFERRED] The hand targets are wherever the steering-pose clip leaves the hands. The `pos_grip_*`/`pos_footpeg_*` anchors above only feed the offline solver; the engine never reads them, and another grip or footpeg position needs new clips, not a model or config change.

[EXACT][CLAIM-ANIM-CHILD-ASI-SWAP-130] Vanilla 1.30 already swaps the player's animation instance at run time, for surrender. It turns off the hands-driven switch and loads a child `.asi`: `GetItemAccessor().EnableAutoAnimInstUpdateOnHandsChange(false)`, then `SetAnimationInstanceByName("dz/anims/workspaces/player/player_main/player_main_surrender.asi", 1)` (`4_World/Entities/ManBase/PlayerBase.c:2087-2088`); on the way out it turns the switch back on and returns to `player_main.asi` (`:2104-2107`). That child is an `AnimSetInstanceSource` whose `ParentTemplates` names `player_main.asi` (`player_main_surrender.asi:1-5`). Both switch targets are registered as item-in-hands profiles: the child on a dummy item, and the base as `"Empty"`, whose comment says it exists so the character can switch back to it by name (`4_World/Entities/ManBase/DayZPlayer/DayZPlayerCfgBase.c:1532-1537`). A mod can register its own profiles by overriding `ModItemRegisterCallbacks.RegisterCustom(DayZPlayerType pType)` (`:305`, `:329`), which vanilla calls at `:1559`. The native's own comment warns that it can desync if misused (`3_Game/human.c:1383-1384`).

[EXACT][CLAIM-ANIM-CHILD-ASI-RUNTIME-130] The route works while the vehicle stands, for the one player tested (DayZDiag 1.30.164014, dedicated server and the owning client, 2026-09-28). A child `.asi` of `player_main.asi` that overrides only the column the vehicle rides on (for `MOTO2`, the `Vehicle.Jawa_Bitrak.*` lines), registered through `RegisterCustom` and swapped in while the player rode one vehicle class, changed that player's pose on that class only, with `Vehicles.agf`, `player_main.ast` and `player_main.agr` untouched. Like the weapon ASI route (anchor 3 correction in SKILL.md), it does not hit the one-graph-mod wall; it can still collide with any other mod that swaps the player's instance. What was run:
- The file: a text `.asi` in the vanilla format, header copied from `player_main_surrender.asi:1-6`, holding only the two `Vehicle.Jawa_Bitrak.DriverSteering*` lines, pointed at the CivilianSedan's steering poses (`player_main.asi:4785-4790`; the lines replaced are `:5175-5180`). Vanilla stores its `.asi` files the same way in `anims_workspaces.pbo` (uncompressed text, LF, no `.meta`). Packed as a plain file of the mod PBO, it loaded by path with no Workbench step and no `.aw` entry.
- Registration: `AddItemInHandsProfileIK("<no such item>", "<pboprefix>/anims/<name>.asi", cfg, "")` with an empty-handed `DayzPlayerItemBehaviorCfg`, inside `RegisterCustom`, which runs before the preload at `DayZPlayerCfgBase.c:1642`. It returned 913 on both machines. `DayZPlayerTypeRegisterItems` runs twice per machine (`:12`, `:21`).
- The swap, run on the dedicated server and on the owning client (the two machines tested): on in `PlayerBase.OnCommandVehicleStart` (`PlayerBase.c:4342`) when the vehicle command's transport `IsKindOf` the class, with surrender's two calls; off as soon as `IsGettingOut()` is true and again in `OnCommandVehicleFinish` before `super`, with `EnableAutoAnimInstUpdateOnHandsChange(true)`, the base `player_main.asi` by path and `OnItemInHandsChanged(true)`, so that vanilla's `RefreshHandAnimationState` (`PlayerBase.c:4384`) runs after it.
- Measured: both machines received `OnCommandVehicleStart`/`OnCommandVehicleFinish` and ran `CommandHandler`; their switch-on calls were logged 24 ms apart, and their switch-off calls at the start of the get-out 5 ms apart. Stopped, on the owning client's samples, the probe rider's left hand, pelvis and head sat 0.84, 1.01 and 1.01 m from the same player on the same model without the swap (the server logged too few control samples for its own comparison). The same player stayed unswapped on the other classes of the row. On exit both machines logged the switch back with `auto=1`; the instance itself was not read back (the debug instance fields came out empty), but the same player's stopped pose on three `MOTO2` variants ridden afterwards matched the control's on both machines (pelvis 1.098 m high in the bike's model space, against 0.093 m with the swap), so the override was gone. Other riders, restoring a held item, remote observers and late join were not tested.
- Traps: after the get-out clip the command read as seated, not getting out, until `OnCommandVehicleFinish`, and a per-frame check switched the rider back on for 32 ms on the server and 28 ms on the client; latch it off from the get-out until the command is gone. [EXACT][CLAIM-ANIM-POSE-PROBE-TRAPS-130] (corrected 2026-09-28, LL-535) `Human.GetBoneIndexByName` (`3_Game/human.c:1417`) returns hash-like ids, and several are negative: `RightHand` -1405358722, `RightFoot`, `RightToeBase`, `LeftForeArm`, `RightHandRing1`. The B1 probe treated every negative id as missing, and this line used to say they returned -1; only -1 means missing, and tested that way every one of them resolved (the right hand mirrored the left). And the server's hands are not the client's: for the same stopped pose the dedicated server put the left hand 0.35 m (vanilla pose) and 0.55 m (swapped pose) from where the client did, while pelvis and head agreed within a few millimetres; measure hand placement on the client.

Still open, each needing its own in-game gate (the riding pose and the switch back at the get-out were measured later the same day, next subsection): remote observers and late join (`OnCommandVehicleStart`/`OnCommandVehicleFinish` are engine callbacks, `3_Game/human.c:1691-1692`, and nothing yet shows that they reach remote proxies); a weapon in hand; an item change or the delayed hand refresh while riding (`OnItemInHandsChanged(bool pInstant = false, bool pChangeAnimationInstance = true)`, `3_Game/humanitems.c:112`; `PlayerBase.c:6197-6200`); the unconscious restart, ejection and death. Survivor Animations' current graph is in the 1.29 format and has no `Jawa_*` lines, so on a server that loads it the route has nothing to override; whether another graph replacement still consumes the `Vehicle.Jawa_Bitrak.*` bindings has to be checked per mod.

[EXACT][CLAIM-ANIM-MOTO-STOP-RIDE-SPLIT-130] A custom rider pose comes in four pieces, because the motorbike graph already splits standing from riding. `SteeringBlend` (`Vehicles.agf:2614-2626`) blends `Vehicle.DriverSteeringExtreme` and `Vehicle.DriverSteeringMain` on `!VehicleWalking && VehicleSpeed >= 0.5`, and `Idle_MotorBikeSTM` plays `Vehicle.IdleToDrive` when that turns true (`:1248-1251`, source `:1169-1171`) and `Vehicle.DriveToIdle` when it turns false (`:1267-1270`, source `:610-612`). [INFERRED from the clip names] `DriverSteeringExtreme` is the stopped pose: its MOTO2 clip is `p_motorbike_02_driver_idle_steering_pose.anm` (`player_main.asi:5175-5177`). [DESIGN] For a sport bike: stopped, stand with the feet down and lean further to the clip-ons; `IdleToDrive` lifts the feet onto the pegs and tucks; riding, the full tuck; `DriveToIdle` puts the feet down. The comparison with Survivor Animations' own motorcycle type is in the `dayz-motorbikes` skill (`references/rider-animation.md` §5).

### Own clips on the rider, measured end to end (added 2026-09-28, DayZ 1.30 Exp, LFRider on the Kawasaki H2R)

The same child-`.asi` route with clips we generate, riding included (DayZDiag 1.30.164014, dedicated server and the owning client, one player; LFRider runs P1, P4, P5 and P6, 2026-09-28, LL-533 to LL-535). The shared mod keeps a config table (`CfgLFRider >> Poses`, one class per pose with `vehicle` and `asi`), registers every `.asi` in `RegisterCustom`, switches in `OnCommandVehicleStart`, `CommandHandler` and a per-frame client poll, and latches off from the start of the get-out.

- [EXACT][CLAIM-ANIM-OWN-ANM-PLAYS-130] A clip made with `DayZATool --generate-anim <file>.seanim 100` plays. DayZATool writes `ANIMSET5`, and 1.30 ships player clips in three versions (`anims_anm_player.pbo`: 10 `ANIMSET4`, 2,398 `ANIMSET5`, 4,980 `ANIMSET6`). A vanilla `MOTO2` steering pose with `Spine1` bent 20 degrees put the stopped rider's head 0.4 mm (median of 129 client samples) from the clip's FK and 19 cm from the vanilla one. The `.asi` `Resource` loaded both as a bare path and with an invented `{GUID}` in front; vanilla ships no `.meta` for its clips.
- [EXACT][CLAIM-ANIM-MOTO-STEER-SCALE-130] The motorbike steering poses are read at `Time = clamp((VehicleSteering + 0.785) * 0.63694, 0, 1)` (`Vehicles.agf:50` for `DriverSteeringMain`, `:1466` for `DriverSteeringExtreme`), `VehicleSteering` being the wheel angle in radians: the clip always spans -45 to +45 degrees of wheel angle, whatever the bike's lock. Author frame `i` of `N` at `(2i/(N-1) - 1) * 45` degrees, clamped to the lock. Measured on the H2R (20-degree lock): with the frames spread over the lock, both hands sat 44 mm from where that clip puts them at full lock (the engine was reading it at s = 0.45); with the frames at 45 degrees, the frame that best explains the measured hands (mean fit residual 0.3 mm per hand) sat at the bars' measured angle (probe below): 20.0 degrees stopped at full lock, and riding at 11-27 km/h with the bars between -16.0 and +17.4 degrees, within 1.2 degrees of the bars (0.1 or less in 29 of 39 samples; fit residual median 0.3 mm, max 0.6 mm per hand). That shows the hands following the clip frame of the bars' angle; the clip puts them on the grips by construction of the solver (LL-531). No hand-to-grip distance was measured in game. The node reads normalized time, so the frame count is free: 37 frames put a 20-degree lock exactly on a frame.
- [EXACT][CLAIM-ANIM-TRANSITIONS-ABSOLUTE-130] Write the transitions as absolute, whole-body poses. The vanilla `IdleToDrive` and `DriveToIdle` clips hold differences: per bone, pose = base * add in local space with the translations added; `IdleToDrive` goes over the riding pose (its frame 0 rebuilds the stopped pose within 0.19 degrees and it ends at identity) and `DriveToIdle` over the stopped one. The engine plays them as `Idle_MotorBikeSTM` states (`Vehicles.agf:1204-1220`) under the `Steerinng` blend (`:2720`). A DayZATool clip holding the same kind of data played as an absolute pose: during the transitions the pelvis, spine, neck and head collapsed onto one point near the rider's root (P4: 8 of 209 client and 9 of 218 server samples; the hands and some leg bones stayed apart). Exported as absolute poses keying every bone of the steering pose, arms included: no collapse in P6 (210 client and 218 server samples), and while stopping the measured hands sat 0.1-1.5 mm from our clips' hands at the measured bar angle (3 client samples). Keep the vanilla notes (`Sound` at frame 10 of `IdleToDrive`, `Step` at 7 and 15 of `DriveToIdle`); an SEAnim with notes needs presence flag 64.
- [EXACT][CLAIM-ANIM-BARS-ANGLE-PROBE-130] The bars' real angle, for a probe: `GetBonePivotsForAnimationSource(GetViewGeometryLevel(), "turnfront", pivots)` (`3_Game/Entities/Object.c:233`, `:220`; vanilla does the same for its sounds at `4_World/Entities/Vehicles/MotorbikeScript.c:287-292`) and `GetBoneRotationMS(pivots[0], q)` (`Object.c:242`); the angle is `2 * atan2(|q.xyz|, |q.w|)`, signed along the steering axis. `Motorbike.WheelGetDirection(0)` (`3_Game/Vehicles/Motorbike.c:247`) gives the front wheel's direction.
- A scripted get-out, for a test that must see the pose switch back: `ActionGetOutTransport` needs no target (`HasTarget` returns false, `4_World/Classes/UserActionsComponent/Actions/Interact/ActionGetOutTransport.c:220`; its condition reads only the vehicle command, `:70`) and its `OnStart` calls `GetOutVehicle` (`:183`), so `PerformActionStart` with any target gets the rider off. Measured: the switch-off fired at the start of the get-out on both machines; the get-out took 2 s.
- Stopped, the per-bone medians sat 0.1-0.5 mm from the clip's FK (single samples up to 37 cm during the blend after getting on); riding, pelvis medians 1.1-1.7 cm and head medians 2.1-2.6 cm (P4-P6, owning client; the graph's lean and acceleration layers). Getting on and off still play the vanilla clips (the leg over the tail) and blend into the new pose in about 0.3 s. One sample while pulling away had both hands 4 cm wider than the grips during the state blend.
- Still open: remote observers and late join (needs a second client), a held item, the unconscious restart, ejection and death, get-in and get-out clips of our own.
- Grip hole first (measured on the skinned body mesh, DayZ 1.30.164014 Exp) [EXACT]: vanilla vehicle-clip hands close on a thin bar — the vanilla fist-hole center sat ~23 mm from the memory-point center used, and the hole is 9.9 mm radius on the left hand and 11.5 on the right (Jawa bar) against a 20.1 mm custom grip that cut up to 19-20 mm into the hand. Before reusing vanilla clip hands on another vehicle, measure the clip's fist hole against the new grip or wheel radius; vehicle memory points (`accelerator`, `clutchlever` axes) are NOT fist centers; and a "hands at 0 mm" reading that the solver satisfies by construction is not contact evidence — measure wrap degrees and penetration on the mesh, and wrap by rotating each finger and thumb phalanx tangent to the grip (330-360 degrees covered with 5-6 mm of overlap at every piece and through the whole steering range).

## Critical caveat — rest pose calibration

SEAnim stores bone rotations **relative to the skeleton's rest pose**, NOT absolute world rotations. The solver in `ik_pose_to_seanim.py` produces world-space joint positions and converts to local rotations by composing against an assumed rest pose. **If the assumed rest pose differs from the real `OFP2_ManSkeleton` rest pose, the in-game pose will be subtly wrong** (rotated shoulders, twisted spine) even when the viewer looks perfect.

Mitigation (the only one that works reliably):

1. Pick a vanilla driver-idle `.anm` close to your target (e.g. `dz/anims/anm/player/vehicles/sedan_01/p_sedan_01_driver_idle.anm`).
2. User runs `DayZATool --extract-anim <file>.anm` on Windows → SEAnim text file.
3. Read frame 0 (or the actual rest reference frame the file declares) and use it as the bind pose for the solver: `python ik_pose_to_seanim.py --rest-pose extracted_bind.seanim ...`.
4. Without `--rest-pose`, the script produces "positionally approximate" output flagged in the SEAnim metadata — usable for offline review, NOT for final in-game.

This is the standard Bohemia animation pipeline; there is no shortcut. Plan for the rest-pose extraction round-trip from day one.

## Frame-of-reference caveat (LL-frame-of-reference)

If your project has two coordinate frames for the same model (a viewer/authoring frame and a production `.p3d` frame), all anchor coordinates must be expressed in the SAME frame as the `.p3d` they get baked into. The LFQuad reference case has a `+Z front` authoring frame and a `-Z front` production frame; baking anchors from the authoring frame to the production `.p3d` requires negating Z first.

The dual-entry detection in `dual-entry-action-pattern.md` is robust to this because `WorldToModel` returns local coords in whatever frame the `.p3d` uses, so the `localP[0] >= 0` side check works regardless. But the anchor coords you place via `dayz-p3d-inspector` Recipe edits DO need to be in the right frame — verify by reopening the `.p3d` in a viewer aligned to the production frame and confirming `crewdriver` sits where the pelvis should sit.

## Single-track vehicles: directional boarding and stability ejection (added 2026-09-16, DayZ 1.30 Exp) [EXACT]

When authoring poses for motorbikes or other single-track vehicles in 1.30:
1. **Directional get-in / get-out**: the side is chosen at runtime by a dot product in `ActionGetInTransport.c:81-100` when `Transport.HasDirectionalInOutAction()` (`Transport.c:677`) is true. The graph has separate states `GetIn_L` (`CMD_Vehicle_GetIn == 0`) and `GetIn_R` (`== 1`), plus `GetOut_L/R` and `JumpOut_L/R` (`Vehicles.agf:1592-1658`). A custom vehicle with its own mounting animations needs both left and right variants.
2. **Handlebar IK lock**: vanilla uses `AnimNodeIK2hands` (`AnimSrcNodeIK2`, `Vehicles.agf:31-46`) with `SnapRotation 1` to hold the wrists on the grips; the steering pose `DriverSteeringMain` is driven by `VehicleSteering` normalised over [-0.785, +0.785] rad (about +/-45 deg) (`Vehicles.agf:47-51`). That is the wheel angle, not a fraction of the bike's lock: author the steering-pose frames over +/-45 degrees (`CLAIM-ANIM-MOTO-STEER-SCALE-130` above; two solvers missed this line until the hands were measured 44 mm off, LL-533).
3. **Stability ejection**: `CrewShouldEject(seatPos)` on the motorbike returns `IsFallen()` (`MotorbikeScript.c:466`); when the bike is down, `DayZPlayerImplement.c:2458` activates `eModifiers.MDF_UNCONSCIOUSNESS` to get the rider off (Bohemia's own comment at `:2454-2455` calls this temporary until a ragdoll command exists). When the driver dies, `motorbike.FallOver()` (`DayZPlayerImplement.c:731`) tips the bike over.
Rider-side detail, anim list (`Jawa_05` = `Motorbike_01`, `Jawa_Bitrak` = `Motorbike_02`) and the vehicle config side live in the `dayz-motorbikes` skill (`references/rider-animation.md`).

## Cross-contract with handlebar/wheel rotation (LL-handlebar-rotation-sync)

If the steering geometry rotates by `model.cfg` (`handlebar-and-steering-config.md`) AND the rider's hands track its grips by IK, the angular range of the two MUST match:

- `model.cfg` block: `angle0 = "rad -0.39"; angle1 = "rad 0.39";`
- Solver config: `T.steerMax = 0.39`

Stale note: the `model.cfg` example above still uses the pre-2026-06-07 `rad 0.39` throw; cross-check `handlebar-and-steering-config.md:64` before shipping visible steering, because model.cfg `angle*` uses the empirical degrees scale while `T.steerMax` remains solver radians.

If they drift, hands lose contact with the grips at full lock — visible immediately in-game.

(added 2026-09-28) On the 1.30 motorbike graph the contract is a different one: the clip's frames are read over +/-45 degrees of wheel angle whatever the `model.cfg` throw (`CLAIM-ANIM-MOTO-STEER-SCALE-130`), so the solver maps frames to 45 degrees and clamps at the lock, and the model's `TurnFront` must follow the physics angle one to one (the H2R's does) for the bars and the hands to agree. Document the shared constant in your project (`verified-apis.md` or `assumptions.md`) so a later edit to one side updates the other.

## Reference case

`LFQuad_dev/handoff_2026-05-28.md` (Yamaha Banshee quad). All concrete numbers in this reference (anchor names, joint list, validated pose JSON, viewer pattern) come from that case. Promote to `references/case-studies/` if a second case validates the same pattern with different vehicle proportions.
