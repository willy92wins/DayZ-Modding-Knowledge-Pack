# Skeletal animation — Enfusion `.anm` route (characters, infected, animals, weapons)

This is the route for body and weapon animation. DayZ characters run on the Enfusion animation engine, which uses `.txa` (text) compiled to `.anm` (binary). Sources from fase-0 research (2026-05-20), labelled [VERIFIED]/[TBD-verify].

## ⚠️ The wall, first

**Only one mod modifying player/creature animations can be loaded at a time** — two crash the client/server. Enfusion engine limit, not policy. [VERIFIED across multiple Workshop mod descriptions.] State this on every plan that ships a character/creature animation. If the user already runs an animation mod, yours will conflict with it.

## The pipeline

```
Blender (author/edit keyframes against DayZ skeleton)
  → .txa (text)            [DayZAnimationPluginDemo Blender plugin]   — OR —
  → SEAnim (open format)   [scripts/seanim_writer.py, or SE2Dev plugin]
       → .anm (binary)     [DayZATool --generate-anim]                — OR —
  → Workbench compiles .txa → .anm
       → reference .anm in config → pack PBO → sign → in-game
```

Two ways to reach `.anm`:
1. **`.txa` route (official-aligned):** author in Blender, export `.txa` via `jdfnc24/DayZAnimationPluginDemo`, let **Workbench** auto-compile `.txa`→`.anm` on file change. [VERIFIED tool existence; exact Workbench UI step TBD-verify.]
2. **SEAnim route (Claude-assistable):** produce a **SEAnim** file — either with this skill's `scripts/seanim_writer.py` (Layer 2, sandbox) or the SE2Dev Blender plugin — then the user runs **DayZATool** `--generate-anim file.seanim` to emit `.anm`. [VERIFIED: DayZATool does both directions, dtzxporter.com/tools/dayzatool.]

SEAnim is the lever for programmatic authoring because it is an **open format** (SE2Dev spec). Claude can write/edit it in-sandbox; the closed `.anm` conversion is the user's one GUI/CLI step.

## What Claude does vs the user (seam)

- Claude (sandbox): author/edit keyframes in Blender headless; write/edit SEAnim with `seanim_writer.py`; map bone names to `OFP2_ManSkeleton`.
- User/computer-use (Windows): run DazZATool / Workbench, pack, sign, test.

## Skeleton and bones [VERIFIED]

Target skeleton is `OFP2_ManSkeleton`. Bone names must match exactly or RPT logs `Error: Bone X doesn't exist in skeleton OFP2_ManSkeleton` and that bone does not animate. Get the authoritative bone list from the official `BohemiaInteractive/DayZ-Misc` repo ("Rig and Animations") or the user's vanilla data — do not guess bone names. [TBD-verify: you cannot restructure the vanilla skeleton; overlay only — community consensus, confirm before relying.]

## Editing/retargeting an existing vanilla `.anm`

1. `DayZATool --extract-anim file.anm` → SEAnim. [VERIFIED]
2. Edit in Blender (SE2Dev SEAnim plugin) or programmatically (`seanim_writer.py` / a reader).
3. `DayZATool --generate-anim edited.seanim` → new `.anm`. [VERIFIED]

Caveat: a community note (MRTsBackflip mod) says DayZATool's extracted rigs are "always incorrect" — treat extraction as a starting point, verify the rig, do not assume a clean round-trip. [TBD-verify exact failure mode.]

## Source-of-truth repos (with URLs)

- DayZATool: dtzxporter.com/tools/dayzatool
- SEAnim Blender plugin: github.com/SE2Dev/io_anim_seanim (also defines the open SEAnim spec used by `seanim_writer.py`)
- DayZ Blender txa plugin: github.com/jdfnc24/DayZAnimationPluginDemo
- Skeleton/rig reference: github.com/BohemiaInteractive/DayZ-Misc

## [2026-06-28] Weapon-anim corrections (verified)

### The wall (top of this file) is the GRAPH-replacement wall — weapon anims are conflict-free [VERIFIED-vanilla]

"Only one mod modifying player/creature animations at a time" applies ONLY to mods that REPLACE the player/creature animation GRAPH (`player_main.aw`/`.agr`). Custom WEAPON animations via the ASI route (`AddItemInHandsProfileIK` + per-weapon `.asi` parent chain + `AddItemBoneRemap`, `dayzplayer.c:243`) do NOT touch the graph and **coexist across mods**. Do not state the wall on a custom-weapon-anim plan. (Vehicles are the unsupported exception.)

### `.txa` → Workbench is the canonical PLAYER weapon route; the maintained plugin needs Blender 4.4+/5.x [VERIFIED]

Pipeline step "1. `.txa` route (official-aligned)" is the recommended route for player weapon anims (JD demo + community). Tool note: the ORIGINAL jdfnc24/MrTea plugin needs Blender 3.6.8–4.0 (≥4.1 → `AttributeError: 'Mesh' object has no attribute 'calc_normals_split'`); the MAINTAINED Sanitoeter05 fork is the opposite — Blender 4.4+/5.x (its `bl_info (2,80,0)` is meaningless). Install = manual folder copy into `…/scripts/addons/DayzAnimationTools` (plain folder, not a zip).

### Extraction "always incorrect" — confirmed scope [VERIFIED]

The line 41 caveat is real: DayZATool/Mikero extraction is worst for empties / IK-helper bones (the ones weapon reload/state anims use) and inverts local bone axes. Treat Route B extraction as a reference only; use Route A (`.txa`) for authoring. Frame data + full weapon-anim binding contract in `references/weapon-anim-blender-complete.md`.
