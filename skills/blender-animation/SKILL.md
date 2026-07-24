---
name: blender-animation
description: >-
  Author animations inside a live Blender instance via the Blender MCP (execute_blender_code)
  or headless bpy — objects and cameras, characters/armatures (IK, walk cycles, poses),
  physics sims (rigid body, cloth) baked to keyframes, materials/drivers — with a
  blocking-spline-polish workflow, programmatic realism audits, rendered previews, and
  direct DayZ handoff (.txa export by posing the JD rig). Use whenever the user asks to
  animate anything in Blender, even a single keyframe — anima esto, hazme una animacion,
  animate the camera, walk cycle, turntable, product shot, haz que caiga o rebote, simula
  la tela, bakea la simulacion, camera shake, fade in the material, animacion para DayZ,
  .txa, action anim, pose the rig — or on symptoms like se ve robotico, the animation
  looks stiff or linear, arcs look broken. For mocap retargeting use mixamo-retarget; for
  geometry use blender-assembly; for DayZ model.cfg config-driven animation use
  dayz-animation-pipeline.
---

# Blender Animation (via MCP)

Author animations in the user's live Blender through `mcp__Blender__execute_blender_code`.
Everything happens via the bpy data API — no UI, no mouse. The user's install is Blender
5.1.1 (a dead "Blender 4.3" folder exists in Program Files without an executable — do not
target it). All API claims in this skill were either executed live against 5.1.1
(2026-07-09) or carry a doc/source citation in the references.

## When NOT to use this skill

- Retarget Mixamo/FBX mocap onto a rig → `mixamo-retarget` (same MCP, different job).
- Build/modify geometry → `blender-assembly`; visual QA of a static model → `blender-visual-review`.
- DayZ config-driven object animation (doors, levers, `model.cfg class Animations`,
  `SetAnimationPhase`) → `dayz-animation-pipeline` Layer 1. This skill only AUTHORS motion
  in Blender; for DayZ it stops at the `.txa` (see DayZ handoff below).

## §0 Preflight (run before any animation work)

Run this probe first and adapt to what it returns — versions, scene state and enabled
addons decide which API paths are safe:

```python
import bpy
ims = bpy.context.scene.render.image_settings
result = {
    "version": list(bpy.app.version),                     # gates the Action data model
    "blend_file": bpy.data.filepath or "(unsaved)",
    "fps": bpy.context.scene.render.fps,
    "frame_range": [bpy.context.scene.frame_start, bpy.context.scene.frame_end],
    "autokey": bpy.context.scene.tool_settings.use_keyframe_insert_auto,
    "has_media_type": hasattr(ims, "media_type"),         # 5.x video-output gate
    "addons": [a for a in bpy.context.preferences.addons.keys()
               if any(k in a.lower() for k in ("anim", "rig", "dayz"))],
    "objects": len(bpy.data.objects), "armatures": len(bpy.data.armatures),
}
```

Rules derived from the probe:
- Autokey ON → turn it OFF for the session and restore at the end. Scripts must insert
  keyframes explicitly; autokey turns every scratch transform into a stray key.
- Version ≥ (4,4) → slotted Actions (see the version wall below). Version ≥ (5,0) →
  legacy `action.fcurves` is GONE, not just deprecated.
- Working on the user's open scene: prefix every scratch datablock `_anim_tmp_`, save
  nothing without asking, and restore scene render settings you touch (they are the
  user's, not yours). Delete scratch objects AND their meshes AND their actions when done.

## §1 The version wall — slotted Actions (4.4+) and the death of `action.fcurves` (5.0+)

The single biggest break in this domain. Nearly every tutorial and StackExchange answer
online uses `action.fcurves` — that API raises `AttributeError` on the user's 5.1.1
(verified live). The data model is now Action → layers → strips → channelbags (one per
slot) → fcurves.

Version-safe rules (all verified live on 5.1.1):
- WRITE keyframes with `obj.keyframe_insert(data_path, frame=N)` / `pose_bone.keyframe_insert(...)`
  and drivers with `id.driver_add(path)` — identical call shape on 4.3 and 5.x. Prefer
  these always; they never touch the action layout.
- READ/EDIT curves through the channelbag:
  ```python
  ad = obj.animation_data
  cb = ad.action.layers[0].strips[0].channelbag(ad.action_slot)
  fc = cb.fcurves.find("location", index=2)
  ```
  or version-portably: `from bpy_extras import anim_utils;
  cb = anim_utils.animdata_get_channelbag_for_assigned_slot(ad)` (both helpers exist on
  5.1.1: `animdata_get_channelbag_for_assigned_slot`, `action_get_channelbag_for_slot`).
  On 4.3 fall back to `action.fcurves` guarded by `hasattr`.
- `action.fcurve_ensure_for_datablock(...)` exists 4.4+ for creating curves directly.
- Assigning actions (`animation_data_create()`, `ad.action = ...`) still works everywhere.
- `Bone.select` is GONE on 5.x — bone selection (e.g. for the DayZ exporter's "Selected
  Bones Only" mask) is set through `PoseBone.select` (verified live 2026-07-10; the DayZ
  plugin's own exporter reads `pose.bones[name].select`, `ExportTxa.py:163-169`).
- NEVER probe plugin operators with `hasattr(bpy.ops.export_scene, "txa")` — `bpy.ops`
  resolves attribute access dynamically and returns truthy for ANY name; it only fails at
  call time. Probe with `bpy.ops.export_scene.txa.poll()` inside try/except (false
  positive reproduced live 2026-07-10 with the DayZ plugin unregistered).
- `mathutils`: `a.rotation_difference(b)` returns the RIGHT-composed local delta
  (`a @ d == b`, NOT `d @ a == b`) — for slerp/extrapolation scale the delta via
  axis-angle and compose on the right (verified live 2026-07-10).
- Reused/inherited poses can hide broken finger channels: a distal phalanx rotated
  ~90-110° about a NON-flexion axis reads fine in full-body stills and only shows in a
  hand close-up. Before reusing any hand pose, check per-phalanx rotation AXES against
  the finger's flexion axis (siblings of one finger share it), and always render at
  least one CLOSE-UP still per hand during review — full-body resolution cannot resolve
  distal phalanges (defect caught by the user in live Blender, 2026-07-10).

## §2 Hard runtime rules (each one cost a real failure)

1. **Stale references after mutation.** After `fcurve.update()` or inserting keys, any
   Python reference you kept to `keyframe_points[i]` silently reads garbage (verified
   live: wrote `BACK/EASE_OUT`, stale ref read `CONSTANT/''`). Re-fetch the fcurve and
   its keyframe_points after every mutation before reading or writing them again.
2. **Data API only for curve editing.** `bpy.ops.graph.*` operators fail without a Graph
   Editor context (poll error — verified). Set `kp.interpolation`, `kp.easing`,
   `fcurve.extrapolation`, modifiers, handles directly on the data.
3. **Video output on 5.x is gated by `media_type`.** Set
   `ims.media_type = 'VIDEO'` FIRST; only then does `ims.file_format = 'FFMPEG'` become a
   valid enum value (verified: without it the enum only lists image formats and raises
   TypeError). Then `render.ffmpeg.format='MPEG4'; render.ffmpeg.codec='H264'`. Probe by
   try/except — if FFMPEG is genuinely absent from the build, fall back to a PNG sequence.
   Static enum introspection lies across versions; probing by assignment is the only
   reliable check.
4. **Previews from script use the scene camera, not the viewport — and the GL path
   depends on WHERE you run.** In the live MCP/GUI session,
   `bpy.ops.render.opengl(write_still=True, view_context=False)` is the fast path
   (`view_context=True`, the default, renders the user's viewport WITH overlays — grid,
   selection outlines, gizmos; verified by rendering one). In `blender -b` (headless)
   `render.opengl` FAILS — no OpenGL context exists (reproduced independently by three
   eval runs) — so render previews there with the normal engine render
   (`bpy.ops.render.render(write_still=True)` / `(animation=True)` on Workbench or EEVEE)
   from the scene camera. Same look, slightly slower, works everywhere.
5. **Never rely on autokey; never key scale for DayZ** (engine drops it).
6. **Operators that need context get `bpy.context.temp_override(...)`** — it accepts
   selection/active-object keys too, and restores state automatically. Many tasks are
   better done with pure data API to avoid operator context entirely.
7. **Physics baking headless:** `bpy.ops.rigidbody.bake_to_keyframes` fails in background
   mode (known Blender bug — nested operator context). Use
   `bpy_extras.anim_utils.bake_action(obj, action=None, frames=range(...), bake_options=BakeOptions(...))`
   (pure data API, needs NO context; BakeOptions is a 12-field dataclass with zero
   defaults — construct it fully) or step frames manually inserting keys. `ptcache.bake`
   needs `temp_override(point_cache=scene.rigidbody_world.point_cache)`. Bake the point
   cache BEFORE sampling any frames for keyframing: each pass over an un-baked sim
   re-simulates and diverges (measured 3.56 m drift between two passes in a real run).
8. **Restore what you touch.** Frame range, `render.filepath`, `image_settings`,
   `resolution_percentage`, autokey — snapshot before, `finally:`-restore after.

## §3 The authoring workflow (blocking → spline → polish)

Animation quality comes from iterating in the right order, not from one perfect pass.
Full detail + timing tables: `references/realism-and-iteration.md`.

1. **Plan beats.** Write the beat sheet with frame budgets BEFORE posing (e.g. at 24fps:
   anticipation 8f, action 6f, overshoot 3f, settle 12f). Real-action anchors: walk step
   ~12f, head turn 10-14f, jump crouch slow/takeoff fast, hit-stop 2-6f. Weight lives in
   SPACING (acceleration contrast), not in poses.
2. **Blocking.** Key ALL channels of a control on each story pose, interpolation
   `CONSTANT` (stepped). Mark key types: `kp.type = 'EXTREME'` / `'BREAKDOWN'` /
   `'MOVING_HOLD'` — Blender's own blocking vocabulary, settable from script.
   Gate: render 3-6 golden-pose stills (`view_context=False`, 25-50% res — subsecond
   each) and LOOK at them (Read the PNGs) before splining.
3. **Spline.** Flip to `BEZIER`, set easing per intent (`EASE_OUT` + `BACK` for
   overshoot-and-settle — verified to produce real overshoot), fix what the flip broke.
4. **Offset & overlap.** The #1 robotic tell is every channel keyed on the same frames.
   Stagger follower channels/bones +1..3 frames; add follow-through keys past the stop.
5. **Moving holds.** A frozen hold reads as dead; add tiny drift keys (1-2% of the move)
   across any hold >6 frames.
6. **Polish + audit.** Run the programmatic audit (below), fix flags, render the MP4
   playblast, watch it (or read stills at contact/extreme frames), iterate. Expect 2-4
   rounds minimum; gates are per-stage, not one final check.

## §4 Programmatic realism audit

Calibrated on 5.1.1 (robotic rig scored 1.0/1.0/0.0 vs organic 0.0/0.0/0.25 — full
separation). Code and thresholds: `references/realism-and-iteration.md` §self-audit.

- `linear_ratio` — % of keys with LINEAR interpolation (post-spline target ≈ 0).
- `keyframe_unison_ratio` — % of channels sharing identical key frames (correct ≈ 1.0 in
  blocking, a DEFECT after offset pass — thresholds are stage-dependent).
- `overshoot_ratio` — sample `fcurve.evaluate()` between last two keys; does the value
  pass its final target before settling?
- Designed extras (arc jitter via `motion_path.points`, frozen-hold detector, L/R
  twinning correlation, velocity discontinuities) — see the reference.

## §5 Domain routing

| Task smells like | Read first |
|---|---|
| Bones, poses, IK, cycles, bake, NLA layers | `references/characters-armatures.md` |
| Object/camera moves, easing, noise/cycles modifiers, constraints, material keys, drivers, shape keys | `references/objects-camera-materials-drivers.md` |
| Falling, collisions, cloth, particles, bake-to-keyframes, Alembic export | `references/physics-sims.md` |
| "Make it feel alive/heavy/real", timing, audit, playblast recipes | `references/realism-and-iteration.md` |
| Anything destined for DayZ | `references/dayz-handoff.md` |

Load only what the task needs. High-value specifics living in those files: pose-bone
matrix spaces (`matrix_basis` vs `matrix` — armature space, NOT world; cross spaces with
`Object.convert_space`), rotation-mode changes never convert existing fcurves, material
animation lives on `material.node_tree.animation_data` (not the material), node-socket
keyframing (`node.inputs["X"].keyframe_insert("default_value")`), camera Track To needs
`TRACK_NEGATIVE_Z`/`UP_Y` (RNA defaults are wrong for cameras), parent-inverse jump fix,
wheel-roll-by-distance driver (verified numerically), NOISE modifier reworked in 4.4,
cloth presets with exact numbers, kinematic→dynamic throw handoff, FBX cannot carry cloth
deformation (Alembic can — verified).

## §6 DayZ handoff (.txa) — the default deliverable for DayZ requests

Contract extracted and verified 2026-07-09 (all citations in `references/dayz-handoff.md`).

- **Interface point**: pose the JD plugin's own rig and export with the plugin's own
  operator. Rig: `<downloads>\DayZAnimationPlugin_MAINTAINED\_AssetSamples\JD_Master_Rig (No IK Bones).blend`,
  armature object `_DayZ_Character` (151 bones = `OFP2_ManSkeleton`). Export operator:
  `bpy.ops.export_scene.txa` (verified `ExportTxa.py:69`); IK helpers:
  `bpy.ops.import_scene.addsurvivorik` (`AddSurvivorIK.py:10`); notetracks via the
  plugin's Event Manager (`eventmanager.additem/load/save`).
- The maintained plugin fork requires Blender 4.4+/5.x (its `bl_info` lies and says 2.80).
  If the addon is not enabled, register it from the folder (`sys.path.append` +
  `DayzAnimationTools.register()` — the pattern in
  `WeaponAnimPipeline_dev\tools\txa\viewer_to_txa_via_plugin.py:13-16`) or install by
  folder copy (NOT zip-install).
- Posing pattern from the proven bridge script: disable constraints while setting
  matrices, `rotation_mode='QUATERNION'` on all pose bones, autokey off, explicit
  `keyframe_insert` per bone per frame.
- **Hard rules that ruined real sessions** (do them right the FIRST time):
  - Action anims are spine-UP: never key `EntityPosition`, `Pelvis` or legs (character
    flops/clips underground) — and never `RightHand_Dummy` (weapon flies to the back).
  - Export Type is load-bearing: `FB` emotes / `IK1H`/`IK2H` grip ikpose / `ADD`
    reload-fire-jam with "Selected Bones Only". Exporting ALL bones on an action anim =
    "meatball" character.
  - Hold/timer-driven actions (unjam-style) need `LoopStart`/`LoopEnd` notetracks
    (`Name||-1` format), loop length ≥ the engine timer (~6 s for the 5 s unjam), settle
    the moving part into the outro pose well before LoopEnd (micro-jerk lesson).
  - `Weapon_*` bones: correct values or drop them entirely — placeholder values stretch
    the weapon mesh. Never key scale (dropped at binarize).
  - 30 fps is the pipeline default. Bone names must match `OFP2_ManSkeleton` exactly.
- **This skill STOPS at the `.txa` + a note of the target `.anm` name.** Workbench
  "Register & Import", `.asi`/config wiring, PBO build and the in-game test belong to
  `dayz-animation-pipeline` and the user. Never claim to run Workbench or DayZATool.

## §7 Self-verification before delivering (non-negotiable)

An animation is not "done" when the code ran — it is done when you have LOOKED at it:
1. Render golden stills at contact/extreme frames + the final MP4 preview
   (`media_type='VIDEO'` → FFMPEG → `render.opengl(animation=True)`), all with
   `view_context=False`.
2. Read the stills (Read tool) and check: silhouettes read, arcs unbroken, no
   interpenetration, holds alive. Camera discipline: judge orientation claims only from
   an ON-AXIS still — a 3/4 angle foreshortens and lies (a palm-forward wave read as
   palm-sideways from a 3/4 front-right still in a real review). At least one still must
   be rendered from the character's MEASURED forward axis (compute forward from bone
   geometry — shoulder cross spine, sign-locked by face bones — never assume it).
3. For hand-facing gestures (wave, salute, point, present): add the numeric palm gate —
   identify the palm-normal axis of the hand bone once against rest anatomy (knuckle-plane
   normal at frame 0; palms face inward/down at rest), then assert
   `angle(world_palm_normal, character_forward) <= 30°` across the gesture's key frames
   via the hand pose-bone's world matrix. A stills-only check cannot catch this class of
   defect; the numeric gate plus the on-axis still can.
4. Run the §4 audit numbers and report them with the delivery.
5. For DayZ: verify the `.txa` file exists and is non-trivial in size, and state which
   bones were excluded and which Export Type was used.
6. Leave the user's scene clean: scratch datablocks removed, their settings restored,
   playhead at frame 1.

## Environment notes

- Default execution: the user's live Blender via MCP (they see progress in real time).
  If the MCP is not connected, ask the user to open Blender with the addon, or fall back
  to headless `"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" -b --python script.py`
  for batch/deterministic work (evals, bakes) — same bpy code, but `bake_to_keyframes`
  and anything needing a window stays broken there (§2.7).
- Big outputs (MP4s, stills) go to the session scratchpad or a user-named folder — never
  into the skill tree.
