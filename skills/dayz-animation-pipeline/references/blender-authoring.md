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

DayZ/Arma differ from Blender in up-axis AND handedness: Blender is right-handed with Z up, DayZ left-handed with Y up. For geometry the model pipeline maps `(x, y, z) → (x, z, y)`, det −1 (`dayz-model-pipeline` Rule 12, in-game test 2026-10-01). *Corrected 2026-10-01: this line used to give `x'=x, y'=z, z'=-y`, a det +1 map that mirrors.* For animation, `scripts/seanim_export.py` (Route C) carries that reflection, with one map per rig because the two rigs' bone frames differ by a 90° turn about Z: the JD Master Rig (`jd_dayz.json`) takes the map calibrated 2026-06-29 against a DayZATool-extracted reference, rotation `(x,y,z,w) → (−y,−z,x,w)`, rest position `(x,y,z) → (y,z,−x)`; the BI FBX rig that `scripts/build_rig_dayz.py` builds (`rig_dayz.json`) takes `(x,y,z,w) → (−x,−z,−y,w)` and `(x,y,z) → (x,z,y)`, derived offline 2026-10-02 (`weapon-anim-authoring-viewer.md`, "Route C bone-frame maps, per rig"). Both are det −1; do not add a second reflection on top. *Corrected 2026-10-02: this line said the script predated the calibration and wrote the viewer frame as it is, and gave the JD map without naming its rig; applied to the FBX rig, that map puts every bone's frame 90° off.* [TBD-verify whether other exporters (Blender FBX, third-party SEAnim tools) need the same reflection for DayZ skeletons.] A mirrored clip raises no error; it plays with left and right swapped. Chiral check for any new route [DESIGN, not yet run]: key one side only (raise `LeftArm`, the arm at +X in the official rig in Blender), export, play it in game on a player holding an item. The arm that rises must be the one opposite the item hand (items sit on `RightHand_Dummy`).

## Verify before shipping

Author → export → (user converts) → reference in config → in-game. The only real acceptance is in-game playback with no RPT bone errors. For a quick offline sanity check, re-read the SEAnim/FBX you wrote and confirm bone count, frame count, and FPS are what you intended (round-trip read). Do not treat a written intermediate as correct just because the writer did not error.
