# Authoring keyframes in Blender headless (Layer 2)

How Claude authors or edits animation keyframes in-sandbox before handing an intermediate to a closed converter. This is the programmatic-authoring half of Layer 2; the converters live in `tooling-and-walls.md` and run on the user's Windows machine.

## What is in-sandbox vs not

- In-sandbox (Claude): `blender --background --python script.py` to build/edit keyframes on an armature, export to a format Claude or the user can convert. SEAnim export via `scripts/seanim_writer.py` (no Blender needed for SEAnim itself). FBX export via Blender's built-in exporter.
- Not in-sandbox: the DayZ/Arma Blender plugins (Arma3ObjectBuilder, DayZAnimationPluginDemo, SE2Dev) are interactive-Blender addons on Windows; do not assume they run in headless sandbox without verifying. The reliable in-sandbox exports are FBX (built-in) and SEAnim (this skill's writer).

## Recommended in-sandbox path

1. Build an armature in Blender headless whose bone names match `OFP2_ManSkeleton` (or the target skeleton). Get the exact bone list from `BohemiaInteractive/DayZ-Misc` or the user's vanilla rig — never guess.
2. Set keyframes (pose per frame). Keep FPS explicit and consistent.
3. Export:
   - **SEAnim** (preferred bridge to `.anm`): collect per-bone per-frame transforms and write with `scripts/seanim_writer.py`. The user runs `DayZATool --generate-anim` to get `.anm`.
   - **FBX** (bridge to RTM): Blender built-in `bpy.ops.export_scene.fbx(...)`. The user runs `FBXToRTMGui.exe`.

## Bone-name discipline (the recurring wall)

Bone names must match the target skeleton exactly. A mismatch logs `Error: Bone X doesn't exist in skeleton OFP2_ManSkeleton` and that bone silently does not animate. Before authoring:
- pull the authoritative bone list,
- map your Blender armature names 1:1 to it,
- verify no extra/renamed bones (you cannot restructure the vanilla skeleton — overlay only, [TBD-verify]).

## FPS and scale

- Set the scene FPS and pass the same value to whatever converter the user runs; mismatches drift the playback speed.
- Scale: Blender meters; the exact factor into BI space for DayZ is [TBD-verify] — round-trip one known clip and compare before trusting a custom factor.

## Coordinate handling

DayZ/Arma differ from Blender in up-axis AND handedness: Blender is right-handed with Z up, DayZ left-handed with Y up. For geometry the model pipeline maps `(x, y, z) → (x, z, y)`, det −1 (`dayz-model-pipeline` Rule 12, in-game test 2026-10-01). *Corrected 2026-10-01: this line used to give `x'=x, y'=z, z'=-y`, a det +1 map that mirrors.* For animation, the calibrated viewer → SEAnim conversion already carries that reflection: rotation `(x,y,z,w) → (−y,−z,x,w)`, rest position `(x,y,z) → (y,z,−x)`, det −1, calibrated exactly against a DayZATool-extracted reference (`blender-animation/references/dayz-handoff.md`, Route C). Do not add a second reflection on top. `scripts/seanim_export.py` in this skill predates that calibration and writes the viewer frame as it is. [TBD-verify whether SEAnim/FBX export needs manual axis fix for DayZ skeletons.] A mirrored clip raises no error; it plays with left and right swapped. Chiral check for any new route: key one side only (raise `LeftArm`, the arm at +X in the official rig in Blender), export, play it in game on a player holding an item. The arm that rises must be the one opposite the item hand (items sit on `RightHand_Dummy`). [Run 2026-10-02, DayZDiag 1.29.163709: Route C's script fed from the official FBX rig.] Only `LeftArm` keyed, 70° above horizontal, on `animation_rig_character.fbx` in Blender 5.1 (its rest local rotations equal the viewer rig's on all 114 bones), exported to SEAnim with the calibrated Route C script, spliced as the one changed rotation track into the SEAnim that `DayZATool --extract-anim` gives for the vanilla 1H standing idle `p_1hd_erc_idle_low.anm`, built with `DayZATool --generate-anim`, and played through a child `.asi` of `player_main_1h_fruit.asi` (its `Locomotion.Erc.Idle*` lines) on an `Apple` subclass: the arm opposite the apple rose. The same Blender pose through this skill's uncalibrated `scripts/seanim_export.py` (as of `eca85e6`) left that arm at shoulder height, and the vanilla idle round-tripped through DayZATool showed the vanilla standing pose. (claim: CLAIM-ANIM-ROUTEC-CHIRAL-INGAME) Scope: the run shows that this route keeps the keyed track on `LeftArm` and raises that arm as keyed. It says nothing about the handedness of the frame change: the bone offsets came from the vanilla clip, and a rotation map reads the same whether that change is a reflection or not. Nor does it show that the formula fits the FBX rig's bone frames: the 2026-06-29 calibration ran on the JD rig (`--rig data/jd_dayz.json`), whose bone frames are the FBX rig's turned 90° about Z (105 of 113 bones within 0.5°), and this raise turns mostly about the bone's own Z, so both maps raise the arm (offline FK on the idle: +61.8° with Route C's map, +73.1° with the rig-aware one).

## Verify before shipping

Author → export → (user converts) → reference in config → in-game. The only real acceptance is in-game playback with no RPT bone errors. For a quick offline sanity check, re-read the SEAnim/FBX you wrote and confirm bone count, frame count, and FPS are what you intended (round-trip read). Do not treat a written intermediate as correct just because the writer did not error.
