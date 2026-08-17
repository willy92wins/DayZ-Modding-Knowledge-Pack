# Vehicle rider IK pose — extrapolate body pose from .p3d anchors (Layer 1 + 2 hybrid)

A route that produces the seated body pose of a vehicle driver or passenger by **solving IK from a handful of fixed anchors in the `.p3d`** instead of keyframing the body bone-by-bone. Useful when the vanilla shared driver pose looks wrong on a vehicle whose geometry differs (quad/motorbike with handlebar vs car with steering wheel, unusual grip/footpeg positions, atypical seat height).

## When this route applies

- The vehicle's geometry breaks the vanilla shared driver/passenger pose (hands floating off the wheel, feet off the floor, torso clipped).
- You don't have an animator to author 4 hand-keyed clips and don't want to.
- You can place 5 memory points in the `.p3d` Memory LOD precisely (this is the prerequisite).

## When it does NOT apply

- You're authoring expressive action animations (combat, reload-while-driving) — that's keyframe work in `references/skeletal-anm-enfusion.md`.
- The vanilla pose already looks acceptable — don't pay the rest-pose calibration cost (see Caveat below) just to fix a minor offset.
- You haven't accepted **anchor 3** (the one-anim-mod wall): this route still produces a character/creature animation mod and conflicts with every other anim-mod on the server.

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
5. **Wire in `vehicles.agr`** (Layer 3 GUI in Workbench) — point the appropriate transition or state at the new `.anm`. This step is Workbench-only; Claude cannot run it in-sandbox.
6. **Test in-game.** RPT must show no bone-name errors. Verify pose visually from inside the vehicle (1st person) and outside (3rd person, both sides).

## The wall this route does NOT escape

**The one-anim-mod wall (anchor 3 of SKILL.md) still applies.** Loading two mods that ship character/creature animations crashes client/server, Enfusion engine limit. This route just produces better-quality animations in the slot that wall allows — it does not give you more slots. Every plan that ships these SEAnims MUST tell the user about the conflict.

For Layer 1 cosmetics that are NOT character animation (the handlebar/steering wheel rotation itself, hide-on-attach for accessories), see `handlebar-and-steering-config.md` and `item-ik-and-hide.md` — those do not hit the wall.

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

## Cross-contract with handlebar/wheel rotation (LL-handlebar-rotation-sync)

If the steering geometry rotates by `model.cfg` (`handlebar-and-steering-config.md`) AND the rider's hands track its grips by IK, the angular range of the two MUST match:

- `model.cfg` block: `angle0 = "rad -0.39"; angle1 = "rad 0.39";`
- Solver config: `T.steerMax = 0.39`

Stale note: the `model.cfg` example above still uses the pre-2026-06-07 `rad 0.39` throw; cross-check `handlebar-and-steering-config.md:64` before shipping visible steering, because model.cfg `angle*` uses the empirical degrees scale while `T.steerMax` remains solver radians.

If they drift, hands lose contact with the grips at full lock — visible immediately in-game. Document the shared constant in your project (`verified-apis.md` or `assumptions.md`) so a later edit to one side updates the other.

## Reference case

`LFQuad_dev/handoff_2026-05-28.md` (Yamaha Banshee quad). All concrete numbers in this reference (anchor names, joint list, validated pose JSON, viewer pattern) come from that case. Promote to `references/case-studies/` if a second case validates the same pattern with different vehicle proportions.
