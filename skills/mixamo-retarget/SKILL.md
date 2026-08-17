---
name: mixamo-retarget
description: "(EXPERIMENTAL — extracted and syntax-checked, fixture validation pending) Retarget Mixamo (or any FBX/DAE) animations onto a custom Blender rig — including the DayZ skeleton — with fuzzy bone matching, preset mappings (mixamo_to_rigify), persistent per-pair bone maps, NLA stacking and playback. Use whenever the user wants to apply Mixamo mocap to a character, retarget an animation between skeletons, auto-map bones between two armatures, import an animation FBX onto an existing rig, or source motion-capture keyframes for the DayZ SEAnim pipeline (dayz-animation-pipeline Layer 2). Triggers: retarget, Mixamo, mocap a mi rig, pasar animación entre esqueletos, bone mapping, aplicar animación FBX. Runs through the existing Blender MCP (execute_blender_code) — no extra addon, no WebSocket server."
---

# Mixamo Retarget (via Blender MCP)

Retargets skeletal animations between armatures inside Blender, driven entirely through the already-connected Blender MCP. The engine is the retargeting module extracted from Dev-GOM's `blender-toolkit` (Apache-2.0; attribution below) — the valuable 700 lines, without the plugin's WebSocket server, CLI build, hooks, or second Blender addon.

**Status: EXPERIMENTAL — extracted and syntax-checked, not yet fixture-validated.** Before first production use, run the fixture at the bottom and record the result.

## What it does

- `auto_map_bones(source, target)` — fuzzy bone matching with a Mixamo alias table (works on `mixamorig:`-prefixed and bare names).
- `get_preset_bone_mapping("mixamo_to_rigify")` — known-good preset.
- `store_bone_mapping` / `load_bone_mapping` — persist a reviewed map per armature pair (scene-level), so the fuzzy pass runs once and the corrected map is reused.
- `retarget_animation(source, target, bone_map, action_name)` — bakes the retargeted action onto the target rig.
- `import_fbx` / `import_dae`, `list_armatures`, `get_bones`, `list_animations`, `play_animation`, `add_to_nla`.

## How to run it (through the Blender MCP)

The two modules in `scripts/` are plain Blender-Python. Load them once per session by exec-ing them in Blender's interpreter, in dependency order:

1. Read `scripts/bone_matching.py` and `scripts/retargeting.py` from this skill.
2. Send each through `execute_blender_code` (bone_matching first — retargeting imports `fuzzy_match_bones` from it; when exec'd into the same namespace, replace its `from bone_matching import …` line with nothing, or exec bone_matching's source first so the names already exist).
3. Then drive the workflow:

```python
# inside execute_blender_code, after both modules are loaded
import_fbx(r"C:\path\to\Walking.fbx")          # brings in the Mixamo armature + action
print(list_armatures())                          # e.g. ['Armature', 'MyDayZRig']
bm = auto_map_bones("Armature", "MyDayZRig")    # fuzzy pass — REVIEW THIS DICT
print(bm)
```

4. **Two-phase discipline (kept from the original design):** never retarget straight off the fuzzy map. Print it, review/correct it (the human or a reasoned pass), `store_bone_mapping` the corrected version, then:

```python
retarget_animation("Armature", "MyDayZRig", bone_map=bm, action_name="Walking_retarget")
play_animation("MyDayZRig", "Walking_retarget")
```

`references/bone-mapping-guide.md` (653 lines, from the original project) covers alias logic, naming conventions, and fixing bad matches — read it when the fuzzy map comes back with gaps.

## Rest-pose caveat (the classic failure)

Mixamo rigs are T-pose; many targets (including game rigs) are A-pose or custom. A retarget across mismatched rest poses bakes a permanent offset into every frame. Align rest poses first (apply rotation on the Mixamo armature; or pose-match the target's rest to the source) before judging the result. Symptom: arms floating ~45° off on every frame.

## DayZ integration note

For LFPG work, the output of a retarget onto the DayZ skeleton is **source keyframes**, not a game-ready animation: it feeds `dayz-animation-pipeline` Layer 2 (Blender keyframes → SEAnim → DayZATool → `.anm`), and the player/creature anim-graph wall still applies (one animation mod per server). Use it to harvest mocap for creatures, poses, and reference motion — not as a shortcut around the pipeline.

## Fixture before first real use (AGENTS-R26)

Positive: import any Mixamo FBX, retarget onto a copy of its own armature with the identity map — the result must visually match the original (render 3 frames via `blender-visual-review`). Negative: retarget with an empty bone map must raise/return an error, not silently produce a frozen action. Record both outcomes; only then drop the EXPERIMENTAL label.

## Attribution

Retargeting engine: `retargeting.py` + `bone_matching.py` from [Dev-GOM/claude-code-marketplace](https://github.com/Dev-GOM/claude-code-marketplace) `plugins/blender-toolkit`, Apache License 2.0. Modified: relative imports flattened, logger replaced with stdlib logging. The original project additionally offers a WebSocket CLI control plane and UI confirmation panel not included here.

## Assets

This skill redistributes **no** Mixamo or Adobe mocap, FBX, or character assets — only the retargeting workflow. Download Mixamo clips yourself; they stay on your machine and are not part of this pack.
