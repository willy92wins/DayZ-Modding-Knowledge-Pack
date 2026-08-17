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

DayZ/Arma use a different up-axis than Blender (the model pipeline applies `x'=x, y'=z, z'=-y` for geometry — see `dayz-model-pipeline`). For animation, the converter/plugin generally handles axis conversion, but verify on a round-trip rather than assuming. [TBD-verify whether SEAnim/FBX export needs manual axis fix for DayZ skeletons.]

## Verify before shipping

Author → export → (user converts) → reference in config → in-game. The only real acceptance is in-game playback with no RPT bone errors. For a quick offline sanity check, re-read the SEAnim/FBX you wrote and confirm bone count, frame count, and FPS are what you intended (round-trip read). Do not treat a written intermediate as correct just because the writer did not error.
