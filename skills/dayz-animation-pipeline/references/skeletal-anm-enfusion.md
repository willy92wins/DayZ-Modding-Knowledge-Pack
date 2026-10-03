# Skeletal animation — Enfusion `.anm` route (characters, infected, animals, weapons)

This is the route for body and weapon animation. DayZ characters run on the Enfusion animation engine, which uses `.txa` (text) compiled to `.anm` (binary). Sources from fase-0 research (2026-05-20), labelled [VERIFIED]/[TBD-verify].

## ⚠️ The wall, first

**Only one mod modifying player/creature animations can be loaded at a time** — two crash the client/server. Enfusion engine limit, not policy. [VERIFIED across multiple Workshop mod descriptions.] State this on every plan that ships a character/creature animation through a graph replacement (scoped 2026-09-28: the child-`.asi` routes, weapon and vehicle, replace no graph file; see the correction below and `vehicle-rider-ik-pose.md` §Per-vehicle pose without a graph change). If the user already runs an animation mod, yours will conflict with it.

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

[EXACT][CLAIM-ANIM-DAYZATOOL-ROUNDTRIP-130] (added 2026-09-28, LFRider) Measured on two vanilla 1.30 player clips (the `MOTO2` steering pose, 119 bones, and `stand2drive`, 27): extract then generate kept rotations within 0.005 degrees and positions within 0.0021 cm. The generated file is `ANIMSET5` (the originals are `ANIMSET6`) and plays in 1.30, but as an absolute pose: a clip holding differences, like the vanilla transitions, collapses the skeleton (`vehicle-rider-ik-pose.md` §Own clips on the rider). On a Windows host DayZATool runs headless from a script: `DayZATool.exe --generate-anim f.seanim 100` with stdin closed returned 0 and wrote the file (2026-09-29); an earlier session reported it throwing on `Console.ReadKey` after writing, so judge by the output file, not by the exit code.

[EXACT][CLAIM-ANIM-DAYZATOOL-NO-MODIFIERS] (added 2026-10-03) DayZATool 1.3 marks bones RELATIVE through SEAnim bone modifiers when it extracts a vanilla clip, and the `.anm` that `--generate-anim` builds does not keep them. Measured on `p_1hd_erc_idle_low.anm` (SHA-256 `6eb2b5a5…`): the extract has an ABSOLUTE header and 60 RELATIVE modifiers on its 65 bones; the five without one (`Scene_Root`, `EntityPosition`, `Collision`, `Pelvis`, `LeftHand_Dummy`) are the only bones with position keys. That SEAnim, unchanged, through `--generate-anim 100` gives an `.anm` (same 209,300 bytes as the vanilla file, different hash) that re-extracts with no modifier: same 65 bones, rotations within 0.0035 degrees, positions within 0.0015 cm. In game (DayZDiag 1.29.163709, 2026-10-02) the regenerated idle looked like the vanilla one, which this clip could not contradict: its RELATIVE bones carry no position keys. What the loss does to a clip whose RELATIVE bones do carry them was not measured; generated clips play as absolute poses (previous paragraph). Up to 2026-10-03 `scripts/seanim_writer.py` dropped the modifiers too, on read and on write. It now keeps them: that extract read and written back is byte-identical, and `tests/test_seanim_writer.py` checks the same on synthetic clips.

## Source-of-truth repos (with URLs)

- DayZATool: dtzxporter.com/tools/dayzatool
- SEAnim Blender plugin: github.com/SE2Dev/io_anim_seanim (also defines the open SEAnim spec used by `seanim_writer.py`)
- DayZ Blender txa plugin: github.com/jdfnc24/DayZAnimationPluginDemo
- Skeleton/rig reference: github.com/BohemiaInteractive/DayZ-Misc

## [2026-06-28] Weapon-anim corrections (verified)

### The wall (top of this file) is the GRAPH-replacement wall — weapon anims are conflict-free [VERIFIED-vanilla]

"Only one mod modifying player/creature animations at a time" applies ONLY to mods that REPLACE the player/creature animation GRAPH (`player_main.aw`/`.agr`). Custom WEAPON animations via the ASI route (`AddItemInHandsProfileIK` + per-weapon `.asi` parent chain + `AddItemBoneRemap`, `dayzplayer.c:243`) do NOT touch the graph and **coexist across mods**. Do not state the wall on a custom-weapon-anim plan. (Vehicles were written up here as the unsupported exception; corrected 2026-09-28: a per-vehicle rider pose through a child `.asi` works without touching the graph, `vehicle-rider-ik-pose.md` §Per-vehicle pose without a graph change and §Own clips on the rider.)

### `.txa` → Workbench is the canonical PLAYER weapon route; the maintained plugin needs Blender 4.4+/5.x [VERIFIED]

Pipeline step "1. `.txa` route (official-aligned)" is the recommended route for player weapon anims (JD demo + community). Tool note: the ORIGINAL jdfnc24/MrTea plugin needs Blender 3.6.8–4.0 (≥4.1 → `AttributeError: 'Mesh' object has no attribute 'calc_normals_split'`); the MAINTAINED Sanitoeter05 fork is the opposite — Blender 4.4+/5.x (its `bl_info (2,80,0)` is meaningless). Install = manual folder copy into `…/scripts/addons/DayzAnimationTools` (plain folder, not a zip).

### Extraction "always incorrect" — confirmed scope [VERIFIED]

The line 41 caveat is real: DayZATool/Mikero extraction is worst for empties / IK-helper bones (the ones weapon reload/state anims use) and inverts local bone axes. Treat Route B extraction as a reference only; use Route A (`.txa`) for authoring. Frame data + full weapon-anim binding contract in `references/weapon-anim-blender-complete.md`.

## DayZ 1.30 Exp Updates (build 1.30.164014) [EXACT]

### Modular Plain-Text Graph Files (.agf)
In DayZ 1.30 Exp, sub-graphs are distributed as plain-text Enfusion Config `.agf` files (`AnimSrcGraphFile`, e.g., `DZ/anims/workspaces/player/player_main/Locomotion.agf`, `Actions.agf`, `Combat.agf`, `Vehicles.agf`). Master `.agr` files (`AnimSrcGraph`) index these via `GraphFilesResourceNames`. (corrected 2026-09-28) This section used to say that before 1.30 the sub-graphs were opaque binaries compiled inside `.agr` monoliths. They were neither: 1.29 ships them as separate text `.agr` files in the old `$AnimGraph 7` format, listed by the root `player_main.agr` (`:540-547` in the 1.29 extraction). 1.30 changed the syntax and the extension; evidence in `anim-graph.md` §Vehicles.agf.

### Vehicles in the 1.30 graph
The vehicle sub-graph is `Vehicles.agf` (`DZ/anims/workspaces/player/player_main/Vehicles.agf`, 3654 lines), with the rider state machines (`MotorBikeSTM`) readable in it. (corrected 2026-09-28) The old heading here said vehicles were "no longer an unsupported binary exception"; they were never binary, since 1.29 ships the same sub-graph as the text `Vehicles.agr`. What 1.30 adds is the motorbike rider: the 1.29 graph caps `VehicleType` at 10 and has no `Jawa_*` column. Readable is not patchable: a new rider state or vehicle type still means replacing vanilla graph files (`tooling-and-walls.md` §Named Filesystems for Mods).

### Bone Limit & Indexing
The 250 global bone limit is completely eliminated (`changelog:31`). Bone indices are dynamically hashed at runtime from bone names, rendering index numbers in `skeletons.anim.xml` deprecated.

### Workbench Enfusion 2021 & Live Editing
Workbench updates to the Enfusion 2021 animation editor suite with native Live Editing on running game clients (`changelog:48, 62`) and native `.ae` event table support.
