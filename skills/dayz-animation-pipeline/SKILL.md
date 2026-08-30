---
name: dayz-animation-pipeline
description: Produce and modify DayZ animations across the full spectrum — config-driven object animation (model.cfg Animations, AnimationSources, CfgSkeletons, SetAnimationPhase), item carry IK, hide-on-attach, skeletal animation (RTM + Enfusion txa/anm via SEAnim and Blender), anim graph / state machine work for creatures and player (CMD_ commands, ASI, weapon states, player skeleton bones), and vehicle-rider IK pose from .p3d anchors plus the steering-geometry and dual-entry patterns that ship with it. Use for DayZ animations, model.cfg animation, AnimationSources, SetAnimationPhase, hide-on-attach, item-in-hands IK, RTM, .anm, .txa, SEAnim, DayZATool, anim graph, CMD_Death, CMD_Attack, FireCocked, ReloadMagazineDetach, RightHand_Dummy, EntityPosition, LookAt, drivingWheel, handlebar rotation, ActionGetInTransport, get-in spin, vehicle rider pose, weapon grip in hands (usti hlavne, eye, grip parity, ADS line), or animating a character, creature, weapon, vehicle or prop in DayZ.
---

# DayZ Animation Pipeline

Produce and modify DayZ animations end to end. DayZ has **two parallel animation systems**, and the single most common failure is conflating them. This skill keeps them straight, tells you exactly which parts run where, and refuses to confabulate the reverse-engineered formats.

## Dependencies

```bash
# py3d = DayZ fork of the pack, >= 1.5.0 (sealed wheel vendored in this skill).
# NUNCA `pip install py3d` (PyPI = point-cloud lib) NI git+upstream (sin guards).
command -v python3 >/dev/null 2>&1 || { echo "ABORT: python3 is required to install the sealed DayZ py3d wheel" >&2; exit 1; }; python3 scripts/install_py3d.py
python3 -c "import py3d; assert getattr(py3d,'IS_DAYZ_FORK',False) and tuple(map(int,py3d.__version__.split('.')))>=(1,5,0), (py3d.__version__, py3d.__file__)"
```

Only the `.p3d` scripts need py3d; the SEAnim/RTM writers are pure Python. The assert
is not decoration: without it a wrong `py3d` installs silently and every geometry read
returns plausible garbage.

## The seam: what runs in the sandbox vs what needs Windows/GUI (anchor 1)

This matters more than any config detail. Claude runs in a Linux sandbox with no `P:\`, no DayZ Tools, no Workbench, no Object Builder. Be honest about the boundary in every plan — promising work Claude cannot run is the worst outcome.

- **Layer 1 — Claude produces directly (sandbox, text + Python):** `model.cfg` (CfgSkeletons, CfgModels, class Animations), `config.cpp` AnimationSources, the script wiring (SetAnimationPhase / GetAnimationPhase), item carry-IK registration, hide-on-attach. Fully deliverable here.
- **Layer 2 — Claude assists via interchange formats (sandbox Python + Blender headless):** generate or edit strict **SEAnim v1** (bridges to `.anm` via DayZATool) and unbinarized **RTM_0101/RTM_MDAT** with the Knowledge Pack's dependency-free `dayz-animation-formats` tool, plus keyframe authoring in Blender headless. `.anm`/BMTR remain unsupported here.
- **Layer 3 — user or computer-use only (Windows GUI):** Workbench compile (`.txa` to `.anm`), `FBXToRTMGui.exe`, Arma3ObjectBuilder export from interactive Blender, PBO signing, in-game test. Claude can drive these via computer-use when granted, or hand the user precise steps — but never claim to run them in-sandbox.
  A strict interchange round-trip is not evidence that DayZ accepts the converted animation; keep the DayZATool/Object Builder/DayZDiag gate.

Additional layer-specific notes from the LFQuad rider-pipeline sprint (2026-05-28):

- **Layer 1 — handlebar/steering-wheel rotation**: pure `model.cfg` with `source = "drivingWheel"` plus a two-memory-point axis. No `AnimationSources` entry. See `references/handlebar-and-steering-config.md`.
- **Layer 1.5 — scripted (Enforce Script)**: a `modded ActionGetInTransport` that snaps the player to the correct seat side using 4 memory points per seat (`pos_*_L/_R`) before `super.OnStartServer` runs. Fixes the >180° yaw spin from the wrong side. See `references/dual-entry-action-pattern.md`. Sandbox-deliverable.
- **Layer 2 — IK pose from .p3d anchors → SEAnim**: 2-bone analytic IK on `OFP2_ManSkeleton` from 6 anchors (`scripts/ik_pose_to_seanim.py`). Produces SEAnim variants without a per-bone keyframer. **Critical caveat**: SEAnim rotations are rest-pose-relative, so the script needs `--rest-pose` extracted from a vanilla `.anm` via DayZATool to produce in-game-ready output; without it the output is positionally approximate. See `references/vehicle-rider-ik-pose.md`.

**The `.p3d` geometry an animation needs is NOT Layer 3 — don't punt it to Object Builder.** A config-driven animation needs a named selection to drive and (for rotation/translation) an axis = a pair of memory points; a skeletal bone is also a named selection. Adding/editing those and rebuilding the `.p3d` is sandbox work via the sibling p3d skills: `dayz-p3d-inspector` (extract → Recipe JSON → edit memory points / axis endpoints / selections → rebuild `.p3d`) or `dayz-model-pipeline` (py3d assembly, or from scratch). Run an external ODOL→MLOD converter first if the model is binarized (ODOL, not editable), and `dayz-p3d-audit` to verify winding and `Component01` naming. Honest caveats: py3d edits an MLOD `.p3d`, and authoring a brand-new selection that groups specific geometry leans on the model-pipeline/inspector context (memory points and the axis pair are trivially addable). So when a plan needs a selection or an axis, offer to do it in-sandbox — interactive Object Builder is a *preference*, not a requirement. For Layer 1 work the only true Layer 3 remnants are PBO signing and the in-game test.

When you produce a deliverable, say where it sits on this seam and what the user must run next.

## The wall you must always flag (anchor 3)

**Only one mod that modifies player/creature animations can be loaded at a time.** Loading two crashes the client/server — this is an Enfusion engine limit, not a policy. Any plan that ships a character/creature animation mod MUST warn the user it will conflict with every other animation mod on their server. This does not apply to config-driven object animation (Layer 1) — doors and levers are per-model and do not hit this wall.

## Cite-then-verify, because half this domain is reverse-engineered (anchor 2)

The RTM format carries an explicit Bohemia notice that it is internal and undocumented; the `.anm` format is proprietary. Community wikis disagree on edge details. So this skill labels every fact:

- **[VERIFIED]** — confirmed against a primary source actually read (PMC wiki model.cfg, an official repo, a working mod in this vault). Safe to act on.
- **[TBD-verify]** — reported by a secondary source or a single community guide, not confirmed. Before relying on it, open the real file (the user's `P:\` vanilla config, a vanilla `model.cfg`) and confirm. Never silently promote a [TBD-verify] to a fact.

When you cite a property/type/source in output, give the source. If you cannot verify and cannot reach the file, say so and mark it [TBD-verify] — do not invent a plausible config key to make a list look complete. This domain has burned us before (see the vault's `verificacion-outputs-multi-agente.md`).

## Decide which route you are on

Ask first: is this **object/prop animation** or **skeletal animation**?

| If the user wants… | Route | Read |
|---|---|---|
| A door, lever, wheel, turret, hatch, gauge, or any moving part of an object driven by a controller or by script | Config-driven (Layer 1) | `references/config-driven-animation.md` |
| An attached item to appear/disappear, or a carried item held with the right hand pose | Item IK + hide (Layer 1) | `references/item-ik-and-hide.md` |
| A character/infected/animal body animation, or a weapon animation | Skeletal — Enfusion `.anm` | `references/skeletal-anm-enfusion.md` |
| A legacy prop/man RTM animation, or to use FBXToRTM / Arma3ObjectBuilder | Skeletal — RTM | `references/skeletal-rtm.md` |
| Strict SEAnim v1 or unbinarized RTM read/write/inspect, bounded parsing or deterministic JSON | Interchange tooling | Knowledge Pack `tools/dayz-animation-formats/README.md` |
| To author keyframes from scratch or retarget in Blender | Authoring | `references/blender-authoring.md` |
| To apply Mixamo (or any FBX) mocap onto a rig — auto bone mapping, retarget, NLA — as a keyframe SOURCE for Layer 2 | Sibling skill | invoke `mixamo-retarget` (runs via Blender MCP); output feeds the SEAnim path below. Mixamo FBX download is manual (no API) |
| To know which tool does what, the walls, and signing | Tooling | `references/tooling-and-walls.md` |
| Anim graph / state machine for a creature or for the player; CMD_* commands; ASI structure; weapon state names (`FireCocked`, `ReloadMagazineDetach`); Workbench Animation Editor `#eventtable` mechanism | Anim graph (Layer 2/3) | `references/anim-graph.md` |
| Player skeleton bone catalog by zone (core/legs/arms/IK helpers/weapon attachment); `RightHand_Dummy`, `LeftHand_Dummy`, `EntityPosition`, `LookAt` | Skeleton bones | `references/player-skeleton.md` |
| Body pose of a vehicle driver/passenger from data (seat + grips + footpegs anchors) without per-bone keyframing | Data-driven IK + SEAnim (Layer 1 + 2 hybrid) | `references/vehicle-rider-ik-pose.md` |
| Handlebar or steering-wheel rotation driven by `drivingWheel`; axis from two memory points; cross-contract with rider IK angular range | Layer 1 config | `references/handlebar-and-steering-config.md` |
| Get-in action that snaps the player to the correct side of the seat before the engine plays the climb-on animation, killing the >180° yaw spin from the wrong side | Layer 1.5 scripted | `references/dual-entry-action-pattern.md` |
| `.p3d` named selections that drive action raycasts (seat, handlebar grip, door handle) with interactive painter + adjacency-dilation refiner | Sandbox tooling pattern | `references/selection-painter-for-actions.md` |
| How a custom weapon sits in the hands / ADS: weapon-side memory-point pattern (`eye`, `usti/konec hlavne`, axes) validated vs a vanilla reference, bore/ADS lines, estimated hand zones, grip parity overlay | Weapon-in-hands (Layer 1 + sandbox tooling) | `references/weapon-in-hands.md` + `scripts/weapon_grip_viewer.py` |
| Author a weapon animation interactively: pose the vanilla skeleton + weapon with IK handles + a keyframe timeline, get an offline preview, export SEAnim | Weapon-anim authoring viewer (Layer 2 interactive) | `references/weapon-anim-authoring-viewer.md` |
| Author a complete custom PLAYER weapon animation end-to-end (Blender `.txa` → Workbench `.anm`; per-weapon `.asi` `WeaponOperations.<RigKey>.<State>` map; `AddItemInHandsProfileIK` + `AddItemBoneRemap` binding; ikpose vs weapon-states vs action-anim artifacts; vanilla AKM frame budget; conflict-free-across-mods ASI route; reloadAction is legacy; RPT failure catalog) | Weapon-anim complete (Layer 2/3) | `references/weapon-anim-blender-complete.md` |
| In-sandbox `.p3d` edit / rebake via py3d 1.0.0 (selections, memory points, frame flip) where Object Builder "cannot read" or selections silently empty are real risks | Sandbox tooling quirks | `references/py3d-1.0.0-quirks.md` |

Most requests that say "animate X in DayZ" where X is an object are Layer 1 and never touch RTM/anm. Confirm before reaching for the heavy skeletal path.

## Layer 1 workflow (the high-certainty core)

This is what Claude can fully deliver in-sandbox. Read `references/config-driven-animation.md` for the exact properties, then:

1. **Model the motion.** Which named selection in the `.p3d` moves, around/along which axis, driven by what. An axis is two memory points; a hide needs none. If the `.p3d` doesn't yet have that selection or the axis memory points, add them in-sandbox with `dayz-p3d-inspector` / `dayz-model-pipeline` — don't send the user to Object Builder for it.
2. **Declare the skeleton and animation** in `model.cfg`: a `CfgSkeletons` entry listing the bones (named selections), and a `CfgModels` entry with `skeletonName` and a `class Animations` block (type `rotation*`/`translation*`/`hide`, with `source`, `selection`, `axis`/`begin`+`end`, `minValue`/`maxValue`, `angle0/1` or `offset0/1`).
3. **Wire the source** in `config.cpp` `class AnimationSources`: `source = "user"` for script control (with `animPeriod`, `initPhase`), or an engine source (`wheel`, `reload`, …) that needs no AnimationSources entry.
4. **Drive it from script** with `SetAnimationPhase("<animClassName>", phase)` on the right server/client side and the right lifecycle event.
5. **Verify names match exactly** across `model.cfg`, `config.cpp`, and the script call — a typo is the most common silent failure. Generate the `model.cfg` with `scripts/gen_model_cfg.py` to avoid hand-typo drift.

Output `.cpp`/`.c` files to the project's compilable folder; never invent vanilla paths — double-backslash texture/model paths and confirm against the user's data.

## Layer 2 workflow (programmatic intermediate authoring)

`scripts/seanim_writer.py` remains a legacy project helper.
For new format work, prefer the Knowledge Pack's strict
`tools/dayz-animation-formats/` package. Its verified public API is:
`read_seanim[_bytes]`, `write_seanim[_bytes]`, `read_rtm[_bytes]` and
`write_rtm[_bytes]`; the CLI is
`python -m dayz_animation_formats inspect FILE`.

The strict tool supports complete SEAnim v1 channels, modifiers, notes and
float32/float64 precision, plus one unbinarized `RTM_0101` block optionally
preceded by `RTM_MDAT`. It rejects unknown flags/blocks, malformed counts,
truncation, invalid UTF-8/NUL fields, non-finite values, wrong RTM bone order
and trailing bytes. It does not read or write `.anm`/BMTR.

`references/weapon-anim-authoring-viewer.md` is the interactive viewer route
for weapon authoring (IK handles + timeline + offline preview + SEAnim
export). The viewer reads `bone.quaternion` directly, so the
`positions_to_local_rotations` stub is not on its path.

For skeletal work Claude can take you partway. Read `references/skeletal-anm-enfusion.md` and `references/blender-authoring.md`, then:

1. Author or edit keyframes — either Blender headless (`bpy`) against the DayZ skeleton, or by writing strict **SEAnim v1** / unbinarized **RTM_0101** through `dayz-animation-formats`. A third source: retarget Mixamo/FBX mocap onto the DayZ skeleton with the `mixamo-retarget` skill, then treat the baked action as the keyframe input here (mind its rest-pose caveat).
2. Hand the intermediate to the closed converter the user runs: SEAnim → `.anm` via **DayZATool** (`--generate-anim`), or FBX → `.rtm` via **FBXToRTMGui.exe**, or `.txa` → `.anm` via **Workbench**.
3. Bone names MUST match `OFP2_ManSkeleton` exactly or the RPT logs `Bone X doesn't exist`. Verify the target skeleton's bone list before authoring.

The pure-Python RTM writer was cross-read by external Arma3ObjectBuilder 2.5.1
with first-party motion, phases, metadata and transforms preserved. A3OB is a
GPL external oracle only; no A3OB source is imported or redistributed.

## Animating a sub-piece of a proxy requires separating it (added 2026-05-23)

`model.cfg` rotates/translates whole selections/proxies. To animate a SUB-PIECE of a proxy
(e.g. one moving part within a proxied attachment), separate it into its own proxy/selection —
you cannot animate part of a proxy's geometry in place. Also: a derived mod that inherits the
base's `.p3d`/`model.cfg` needs its OWN `.p3d` + `model.cfg` + `model=` entry to rig new
animations; inheriting the config alone won't bind a new skeleton/anim. (SP-004, LL-012)

## Sprint 2026-05-28: vanilla-verified anim graph + skeleton additions (anchor 4)

The two newest references (`anim-graph.md`, `player-skeleton.md`) are the result of a vanilla-verification sprint against unpacked `DZ/` + `SurvivorAnims/`. They cover the gap this skill had: the **anim graph / state machine** layer where creature behavior and player weapon states actually live. Read them when:

- The user wants to **animate a creature** (animal/infected/predator) and needs commands, variables, terrain alignment, or the special `EntityPosition`/`LookAt` bones → `references/anim-graph.md` first, `references/player-skeleton.md` for bone names.
- The user wants to **author or modify a weapon/item animation** and needs the real state path (e.g. `WeaponOperations.ErcRas.FireCocked`) or the right hand/left hand anchor bones → both references.
- The user wants to **open the player graph in Workbench Animation Editor** (`#eventtable` removal trick) → `references/anim-graph.md`.

### Things community tutorials get wrong (correct them on output)

These corrections come from the same sprint. State them when the user repeats the tutorial naming, so they don't ship the wrong identifier:

- "Entity Position" / "Pin Look At" → real bones are `EntityPosition` and `LookAt` (no `Pin`, no spaces).
- "right hand dummy" → `RightHand_Dummy` (PascalCase + underscore).
- "cmd death" / "cmd success" / "cmd attack" → `CMD_Death`, `CMD_AttackSuccess` (not `CMD_Success`), `CMD_Attack` — UPPER_SNAKE with `CMD_` prefix.
- `discrete = 1` / `discrete = 0` → the model.cfg property is `isDiscrete`.
- `skeletonAnims.xml` / `skeletonanim.xml` → the vanilla file is `skeletons.anim.xml` (literal, with the dots).
- "weapon cocked" / "mag remove" as state IDs → the real state names are `FireCocked` and `ReloadMagazineDetach`. `BulletChambered` is not a state name — chambering is done by command (`CMD_Reload_Chambering`, `CMD_Reload_ChamberingFast`).
- "reload is additive" → REFUTED by vanilla: `CMD_Modifier_Additive` is for sickness/cough/sneeze modifiers, not reload. Reloads use dedicated commands with no additive flag. Authoring convention in Blender may animate only torso/arms, but the engine does not blend it as an additive layer at runtime — verify how the vanilla weapon graph closest in feel transitions in/out of the state before assuming.

## Caveats from the LFQuad rider-pipeline sprint (anchor 5, added 2026-05-28)

Three operational gotchas that bit during the LFQuad work. Add to your context when authoring or extending this skill, or when writing sandbox tooling for animation work.

### LL-edit-tool-truncation (reproduced again)

The Edit tool truncates `new_string` silently around 5–8 KB when the target path lives on OneDrive or under `LocalCache\Packages\Claude_*\…\<skills>\` (plugin mount: `skills-plugin`). The file is written but the second half is cut off; no error is raised. Read-after-write looks normal in chat until you read the file from the host and see it ends mid-line.

Mitigation when patching this skill (or any skill in the plugin mount):

1. Write the new block to `/tmp/<name>.md` with a bash heredoc.
2. Validate with `py_compile` (for scripts) or `wc -lc` plus a manual check that the tail matches the intended end of the block.
3. Copy from `/tmp/` to the destination with `open(dst, 'w').write(src)` in a Python heredoc — NOT `bash cp` if the destination is OneDrive (LL-onedrive-write-safe).
4. Read the destination back with the Read tool (host-direct) and assert the tail matches what you wrote.

This skill prefers heredoc-bash + Python writes specifically because of this bug. If you find yourself reaching for `Edit` on a `references/` file that is more than ~5 KB, stop and use the bash route.

### LL-baked-viewer-reuse

Re-parsing a 10+ MB `.p3d` with py3d in the bash sandbox commonly exceeds the 45 s timeout. Building viewers / painters / pose tools on top of py3d from scratch is slow and fragile.

Faster pattern: if any HTML viewer for the same `.p3d` already exists (output of `dayz-3d-viewer` or `dayz-p3d-inspector`), it contains the geometry base64-encoded in a `const DATA = "..."` literal. Reuse that DATA block: decoding it takes ~1 s vs ~30 s of py3d parsing.

Tell users this when they ask "can you make a new viewer for this model?" — first check whether an existing viewer's DATA can be lifted, only fall back to py3d when no prior viewer exists or the geometry has changed.

### LL-overlay-vs-lighting

In Three.js viewers that use PBR + environment map for the base geometry, overlay meshes (selection brushes, anchor markers, axis visualizers) drawn with `MeshStandardMaterial` get dimmed enough to be effectively invisible against chrome or dark plastic.

Two fixes, both required:

- Use `MeshBasicMaterial` (unlit) for overlays, with saturated high-luminance colors (yellow `0xffe000`, green `0x00ff66`, blue `0x33bbff`).
- Inflate the overlay mesh's vertices 5 mm along their per-vertex normal so it wins the z-fight against the base. Without this the overlay flickers in/out as the camera moves.

Applies to any sandbox tooling this skill or its consumers produce. Cross-ref: `selection-painter-for-actions.md` covers this in the painter context.

## py3d 1.0.0 quirks for in-sandbox `.p3d` writes (anchor 6, added 2026-05-29)

(historical — the pack fork is py3d 1.5.0 which supersedes these quirks; see
`references/py3d-1.0.0-quirks.md` header.)

The Layer-1 scripts this skill ships (or this skill's consumers write on top
of) edit `.p3d` files in-sandbox via py3d 1.0.0. Five quirks of that version
silently corrupt the output unless handled; a sixth pattern (frame
auto-detect when re-baking) is required for any project that has more than
one coordinate frame for the same model. All six are extracted from the
LFQuad rider-pipeline sprint (2026-05-28, LL-055 + LL-056).

Full detail and reference implementations in `references/py3d-1.0.0-quirks.md`.
Summary so a plan can flag them without re-reading the ref:

1. `py3d.Selection()` constructor requires `(points, faces)` positional args
   — the no-arg form silently produces empty selections.
2. Weights are `int`, not `float` — `1.0` corrupts the byte stream and
   Object Builder reports "cannot read".
3. Material name lookup is case-sensitive in py3d but DayZ vanilla `.p3d` uses
   lowercase; normalize on lookup with `.lower()`.
4. Memory points must be **overwritten in place** when the name already exists
   in the LOD (very common when extending a vanilla model); appending duplicates
   silently degrades to the vanilla value (LL-056).
5. Selections must be rebound (`py3d.Selection(lod.points, lod.faces)` after the
   last grow) when the script adds memory points or vertices, otherwise the
   selection references go stale.
6. A rebake script that crosses authoring and production frames must accept
   an explicit `--frame {plusZ|minusZ|auto}` and auto-detect from the bounding
   box (LL-054). Hard-coding the flip silently mirrors output for the other
   frame.

When you produce a plan that writes a `.p3d` (selections, memory points,
properties), name these six explicitly as criteria the script must satisfy
(R26 fixtures). Validation gate after the write: round-trip the file with
`py3d.P3D(open(path, "rb"))` (there is no `py3d.read_p3d`) or `dayz-p3d-inspector`
`extract_recipe`, and assert non-empty
selections, exact memory-point coords, and unchanged material count. If any
check fails, restore from backup before iterating — the failure modes here
cannot be "tweaked out" of a corrupted file.

Cross-references already covered in this skill:

- `vehicle-rider-ik-pose.md` §"Frame-of-reference caveat" addresses Quirk 6
  from the pose side (the anchor placement step). The rebake step is what
  Quirk 6 covers; both must agree on the frame in use.
- `selection-painter-for-actions.md` §"Pipeline (start to finish)" step 6
  calls into a `p3d_update.py`-style writer that needs all five quirks. The
  LFQuad case (`LFQuad_dev/task4_handoff/p3d_update.py`) is the canonical
  reference.
- `dual-entry-action-pattern.md` §"Bail-out for non-LFQuad" relies on
  `crewdriver` / `crewcodriver` having been overwritten in place (Quirk 4).
  If the rebake step skipped that, the modded action silently sees vanilla
  positions and L/R routing degrades.
- `dayz-debinarizer-inspector-memory-selection-bugs.md` (vault knowledge note)
  covers an adjacent failure mode on the READ side: ODOL → MLOD round-trip can
  preserve selection names but lose membership (LL-018). py3d 1.0.0 Quirks 1,
  2 and 5 reproduce a *similar* symptom on the WRITE side: name present,
  body empty or corrupted. If you see name-present-body-empty after either
  step, check the matching skill before assuming the source `.p3d` is wrong.

## Locomoción en scripted commands: GetCurrentStance/GetCurrentMovement conducen el grafo (added 2026-06-11)

Origen: LFSlidingFloor POC-A4, verificado in-game 2026-06-10. `HumanCommandScript` expone los overrides `int GetCurrentStance()` / `int GetCurrentMovement()` (human.c:1238-1247, "Override this!") sin NINGÚN call-site en script vanilla: los consulta el ENGINE, y el grafo del player reproduce la locomoción reportada durante COMMANDID_SCRIPT. Override `GetCurrentMovement()` devolviendo `DayZPlayerConstants.MOVEMENT_RUN` (dayzplayer.c:647) hizo CORRER al personaje mientras un scripted command lo trasladaba (sin override mostraba la locomoción heredada del command anterior). Modulable por estado (IDLE/WALK/RUN/SPRINT, dayzplayer.c:645-648) sin IDs mágicos.

Vías DESCARTADAS para conducir el grafo vanilla del player desde un scripted command: `PreAnim_CallCommand` (0 call-sites en script vanilla, IDs de comandos del grafo no documentados) y `PreAnim_SetFloat/SetInt` (los IDs de variables del grafo vanilla no están expuestos a script). Esas APIs sí sirven con grafos CUSTOM que definen sus propias variables (el sample BI Test_ScriptCmdSwim trae el suyo).

## [2026-06-28] CORRECTION to anchor 3 — the wall is GRAPH-replacement, not weapon anims [VERIFIED-vanilla]

The wall in anchor 3 ("Only one mod that modifies player/creature animations can be loaded at a time") applies ONLY to mods that REPLACE the player/creature animation GRAPH (`player_main.aw`/`.agr`, e.g. Expansion-Animations). It does **NOT** apply to custom WEAPON animations authored via the ASI route.

A custom weapon animation reaches the engine through three decoupled, per-item layers, none of which edits the graph: author `.txa`→`.anm`; a per-weapon `.asi` (`$animsetinstance`) maps `WeaponOperations.<RigKey>.<State>`→`.anm` inheriting `player_main_rifle.asi`→`player_main.asi`; and Enforce Script binds it per item via `AddItemInHandsProfileIK(itemClass, asi, behavior, ikPose.anm, weaponStates.anm)` (`dayzplayer.c:243`) + `AddItemBoneRemap`. Because binding is per-item and never replaces `.agr`/`.aw`, **multiple weapon-anim mods are conflict-free across mods**. (Vehicles are the unsupported exception.)

Practical rule: when the user's plan is a custom WEAPON animation, do NOT warn about the one-anim-mod wall — it is a false blocker. Keep the wall warning for character/creature/player-GRAPH-replacing mods only. See `references/weapon-anim-blender-complete.md` for the full binding contract, frame budgets, and the `ikpose_*`/`reloadAction` verified facts.

## scripts/ index (added 2026-07-06 — previously unreferenced)

Viewer-pipeline scripts shipped in `scripts/` but not referenced elsewhere in this file:

- `scripts/fbx_extract.py` — Blender headless: dumps the BI rig FBX (`animation_rig_character.fbx`) to JSON — per-bone rest world matrices (Blender Z-up), parents, lengths, plus empties. First step of the viewer rig build.
- `scripts/build_rig_dayz.py` — converts the raw rig JSON to `rig_dayz.json` in DayZ Y-up space: uniform scale + translate alignment against the mesh, frame `Rf=[[1,0,0],[0,0,1],[0,-1,0]]`.
- `scripts/extract_weapon.py` — py3d: extracts a weapon `.p3d` LOD0 visual geometry (proxy faces excluded) + memory points to `weapon.json` for the viewer.
- `scripts/build_viewer.py` — generates the self-contained weapon-anim authoring viewer HTML (rig + weapon mesh, Three.js r128 UMD, SkinnedMesh + analytic 2-bone IK + FK controls + keyframe timeline + JSON export). See `references/weapon-anim-authoring-viewer.md`.
- `scripts/seanim_export.py` — converts a viewer anim JSON (per-frame per-bone LOCAL quaternions) to SEAnim via `seanim_writer`; `--rest-pose` rebases against a DayZATool-extracted vanilla SEAnim. NOT valid for full-body action anims — those go Route A (JD plugin → `.txa` → Workbench Register&Import → `.anm`); hand-rolled SEAnim export is for weapon-bone/partial tracks only.

## Reglas promovidas del corpus de lecciones (added 2026-07-27)

Promovidas desde `AI/20_Knowledge/lessons-learned.md` para que lleguen por trigger en vez
de depender de que alguien recuerde buscarlas. Cada regla cita su `LL-NNN` de origen;
la entrada completa vive allí. No quites la cita: el índice detecta la promoción por ella.

- **LL-052** — Define un único rango angular para la pieza animada y para el solver IK que mantiene el contacto. Propaga el mismo valor a `angle0/angle1` y `steerMax`, y verifica los dos extremos.
- **LL-053** — No añadas scripted snap ni puntos `pos_*_L/R` para get-in bilateral. Replica la estructura vanilla: proxies de crew y selecciones/componentes de asiento válidos en ViewGeometry y FireGeometry; conserva la acción vanilla.
- **LL-102** — Usa `source="steeringwheel"`; `DrivingWheel` es el nombre habitual de la clase, no el source. Replica la jerarquía estándar `damper → steering → wheel`; no intentes alimentar una segunda animación desde el source de una rueda.
- **LL-171** — Antes de ajustar una pose offline, enumera los determinantes reales del estado in-game: origen del arma, bone remap, ikpose, geometría y stance/aim-space. Construye el visor desde esos datos; no encadenes heurísticas visuales.
- **LL-189** — Para articulaciones resueltas por IK en runtime, vuelca posiciones de huesos model-space desde el cliente y reconstruye la pose offline desde posiciones. No adivines el swivel ni dependas de rotaciones raw con convención no verificada.
