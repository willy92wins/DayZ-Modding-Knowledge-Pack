# A5 — Exact handoff contract between a new "blender-animation" skill and the existing DayZ animation pipeline

Research date: 2026-07-09. Scope: read-only extraction from existing skills + project handoffs. No files outside this report were modified.

**Path aliases used throughout** (to keep citations readable — substitute before use):
- `[SKILLS]` = `<claude-appdata>\local-agent-mode-sessions\skills-plugin\<plugin-id>\<install-id>\skills`
- `[PROJ]` = `<dayz-projects>`

All facts below were read directly from the cited `path:line` — none inferred from search snippets alone (R2.1 discipline).

---

## Pipeline routes (A/C)

The existing pipeline is `dayz-animation-pipeline`'s Layer 2 (skeletal `.anm` authoring), concretely instantiated by the sibling project `WeaponAnimPipeline_dev/` (an interactive Three.js viewer) and validated end-to-end on `A6_SR2M_dev/` (a real weapon mod). Two export routes exist from "posed skeleton" to the binary `.anm` DayZ actually loads. The skill file names them **Route A** / **Route C** (English); the project handoffs call the same things **"Via A"** / **"Ruta C"** (Spanish) — identical mechanisms.

### Route A — `.txa` (DayZAnimationPlugin) → Workbench → `.anm` — THE CANONICAL ROUTE

- Definition: `[SKILLS]\dayz-animation-pipeline\references\weapon-anim-authoring-viewer.md:147-150` — "Route A (canonical): `tools/txa/dump_viewer_world.py` + `viewer_to_txa_via_plugin.py` -> `.txa` -> Workbench -> `.anm`. Handles root motion. USE THIS FOR THE GRIP."
- Confirmed as the ONLY validated route for full-body/action anims: `weapon-anim-authoring-viewer.md:154-156` — "Route C is also NOT valid for full-body action anims (jam/unjam/melee): the A6_SR2M golpe (2026-06-30) confirmed full-body goes Route A."
- Full end-to-end recipe actually executed and confirmed in-game, `[PROJ]\A6_SR2M_dev\reviews\2026-06-30-handoff-golpe-pipeline-CLOSE.md:20-26` ("EL PIPELINE CORRECTO"):
  1. Author in the viewer → anim JSON (e.g. `golpe_retimed.json`).
  2. `python tools/txa/dump_viewer_world.py golpe_retimed.json <scratch>/golpe_world.json` — converts per-frame per-bone viewer state to FK **world**-space.
  3. `blender --background --python tools/txa/viewer_to_txa_via_plugin.py -- <world.json> <out.txa> ADD <spine_up_bones.json>` → poses the plugin's own rig and calls the plugin's real Blender **export operator** to emit `.txa` — "maneja TODA la convención" (`[PROJ]\...\2026-06-29-handoff-pipeline-ingame-test.md:118`).
  4. **Workbench (GUI, human-only step)**: Resource Manager → right-click the `.txa` → "Register & Import" (first time) / "Reimport Resource" (subsequent) → produces `.anm` + `.anm.meta`.
  5. Optional CLI post-process for corrections the plugin doesn't expose (bone exclusion, notetracks): `DayZATool --extract-anim` → `.seanim` → Python (`seanim_writer.py`) edits → `DayZATool --generate-anim` → final `.anm`. This step is CLI/sandbox-doable.
  6. Deploy `.anm` to `<Mod>/animations/`; rebuild PBO (filepatching does NOT reload `.anm`).
- Used for: full-body action anims (jam/unjam "golpe"), and per the flow doc, the weapon **grip** authoring itself (`[PROJ]\WeaponAnimPipeline_dev\reviews\2026-07-05-flujo-agarre-con-visor.md:43-48`, "Export — RUTA A obligatoria para el agarre").
- Status: **CLOSED, in-game confirmed** for golpe body+head+weapon-in-hand-not-flying-off (`2026-06-30-handoff-golpe-pipeline-CLOSE.md:10`). Loop/unjam fixes (below) fully built and deployed via this route; **final in-game re-confirm of the last polish pass (loop+microjerk+thumb) was still pending** as of the last handoff read — the user interrupted the test (`[PROJ]\A6_SR2M_dev\reviews\2026-07-02-handoff-unjam-DONE-viewer-guion-next.md:6-13,46-53`).
- Tool/version pin: DayZAnimationPlugin_MAINTAINED (Sanitoeter05 fork) cloned at `<downloads>\DayZAnimationPlugin_MAINTAINED\`, requires **Blender 4.4+/5.x** (session used Blender 5.1) — see Blender-side conventions below.
- Alternative pure-Python `.txa` writer `pose_to_txa.py` exists but does **NOT** close the root frame correctly (body lies down) — verified broken, use Route A's plugin-based script instead (`[PROJ]\WeaponAnimPipeline_dev\reviews\2026-06-29-handoff-pipeline-ingame-test.md:124-125`).

### Route C — `.seanim` (CLI) → DayZATool → `.anm` — weapon-bone/partial tracks ONLY

- Definition: `weapon-anim-authoring-viewer.md:150-156` — "Route C (CLI): `tools/seanim_export.py` -> `.seanim` -> `DayZATool --generate-anim <f>.seanim 100` -> `.anm`. Rotations + rest only. The viewer->seanim quat convention `(-vy,-vz,vx,vw)` is exact on fingers but `LeftHand` does NOT obey it (separate wrist process) -> do not use Route C for the support-hand wrist. ... Use Route C only for weapon-bone/partial tracks."
- Script header states the same caveat directly in code: `[PROJ]\WeaponAnimPipeline_dev\tools\seanim_export.py:1-14` (docstring: viewer quats are rig-local/+Y-pointing vs DayZ's +X-pointing bone-local frame; "NOT guaranteed to be in DayZ's exact convention. The in-game test is the gate").
- DayZATool does NOT read `.txa` at all — only `--extract-anim` / `--generate-anim` / `--extract-mdl`, all on `.seanim` (`[PROJ]\WeaponAnimPipeline_dev\reviews\2026-06-29-handoff-pipeline-ingame-test.md:121-123`).
- Status: used to deploy a first test "unjam" anim directly onto A6_SR2M production for a manual in-game test (`[PROJ]\WeaponAnimPipeline_dev\reviews\2026-06-29-handoff-pipeline-ingame-test.md:78-93`); superseded by Route A once full-body work (the golpe) proved Route C insufficient for anything beyond isolated weapon-bone channels.
- Still the right tool for: baking hand-authored finger/thumb corrections directly into an already-exported `.anm` without re-running Workbench (used for the final thumb-curl fix on `golpe.anm`, `[PROJ]\A6_SR2M_dev\reviews\2026-07-02-handoff-unjam-DONE-viewer-guion-next.md:35-37,62-63`).

---

## Interface point for the new skill

**This is the section that matters most: exactly what the new "blender-animation" skill must produce, so it plugs into Route A without re-deriving anything.**

### The recommended artifact: pose the plugin's own rig, export via the plugin's own operator

Every verified, in-game-confirmed animation in this pipeline was produced by loading the DayZAnimationPlugin_MAINTAINED's rig (`_AssetSamples\JD_Master_Rig (No IK Bones).blend`, armature object `_DayZ_Character`, 151 bones — `[SKILLS]\dayz-animation-pipeline\references\weapon-anim-blender-complete.md:107-111`; `[PROJ]\WeaponAnimPipeline_dev\tools\txa\viewer_to_txa_via_plugin.py:7-8,20` confirms the exact path constants `PLUGDIR`/`BLEND` and `arm=bpy.data.objects['_DayZ_Character']`), keyframing it, and letting the plugin's OWN export operator (`export_scene.txa`, `ExportTxa.py`) write the `.txa` — because that operator is what "handles ALL the convention" (mtxFix, root frame, per-component swaps, quaternion negation) correctly (`[PROJ]\WeaponAnimPipeline_dev\reviews\2026-06-29-handoff-pipeline-ingame-test.md:117-120`, "operador EXPORT del plugin (maneja TODA la convención ... Round-trip plugin real mediana 0.0°").

**Because the existing `WeaponAnimPipeline_dev/tools/txa/*.py` scripts exist ONLY to bridge a non-Blender tool (a bespoke Three.js viewer) into Blender, a skill that drives Blender directly (via the Blender MCP) does not need that bridge at all.** It can pose `_DayZ_Character` with `bpy` calls (via `mcp__Blender__execute_blender_code`) and call the plugin's `bpy.ops.export_scene.txa(...)` directly. That is a strictly shorter path to the exact same artifact Route A already produces and that Workbench/the rest of the pipeline already consumes. This is the single biggest actionable finding of this research: **do not reinvent a JSON interchange format — pose the plugin's rig and call its export operator.**

### The concrete deliverable, in priority order

1. **Primary/preferred**: a Blender scene where `_DayZ_Character` (or the vanilla-named equivalent from `DZ/Anims/cfg/skeletons.anim.xml`) has a keyframed Action, produced with the DayZAnimationPlugin_MAINTAINED add-on registered, then exported through **File > Export > DayZ Animation (.txa)** (`export_scene.txa`) with the correct **Type** for the anim kind (`FB`/`IK1H`/`IK2H`/`ADD` — see Blender-side conventions). Handoff artifact = the `.txa` file + a note of which `.anm` it should become. The user's remaining step is Workbench "Register & Import" (or "Reimport Resource") — a 2-click GUI action — then wiring (owned by `dayz-animation-pipeline`, see below).
2. **Fallback / when Blender MCP posing is impractical for a given track**: emit the same **world-space JSON** the existing bridge script consumes, so the user's already-working `viewer_to_txa_via_plugin.py` can run unmodified. Exact schema, read directly from code (`[PROJ]\WeaponAnimPipeline_dev\tools\txa\viewer_to_txa_via_plugin.py:24,53-59`):
   ```
   {
     "fps": 30,
     "order": ["Bone1", "Bone2", ...],       // bone names, any order (script depth-sorts parent-first)
     "parent": {"Bone2": "Bone1", ...},       // bone -> parent bone name map
     "frames": [
       { "Bone1": {"q": [x,y,z,w], "p": [px,py,pz]}, ... },   // per-frame, per-bone WORLD-space quat+pos
       ...
     ]
   }
   ```
   Quaternion field order is **[x,y,z,w]**; the script itself converts to Blender's `Quaternion(w,x,y,z)` constructor order internally (`viewer_to_txa_via_plugin.py:58`: `Quaternion((q[3],q[0],q[1],q[2]))`) — do not pass Blender-order quats into this JSON.
3. **Only for isolated weapon-bone/partial tracks (never full body, never the support-hand wrist)**: the "viewer anim JSON" Route C consumes, schema read directly from `[PROJ]\WeaponAnimPipeline_dev\tools\seanim_export.py:37-43`:
   ```
   {
     "fps": 30,
     "bone_order": ["Bone1", ...],
     "keyframes": [0, 15, 40, ...],           // frame indices that are authored keyframes
     "frames": [
       { "bones": { "Bone1": [x,y,z,w], ... } },   // per-frame, per-bone LOCAL (rig-frame) quaternion
       ...
     ]
   }
   ```
   This feeds `seanim_export.py --anim <json> --rig data/jd_dayz.json --out out.seanim`, then the user runs `DayZATool --generate-anim out.seanim 100` (Windows CLI, not a GUI step, but still outside the sandbox — DayZATool is a closed `.NET` binary).

### What the new skill must NEVER do (already owned downstream)

- Never write `.asi` wiring, `AddItemInHandsProfileIK`/`AddItemBoneRemap` Enforce Script, `config.cpp`/`model.cfg` — that is `dayz-animation-pipeline` Layer 1/3 territory (see "do-not-duplicate" below).
- Never claim to run Workbench, DayZATool, or the in-game test itself — those remain the user's GUI/Windows steps (`[SKILLS]\dayz-animation-pipeline\references\tooling-and-walls.md:41-49`, "Never imply Claude ran Workbench / FBXToRTM / DayZATool in-sandbox — it cannot").
- Never re-derive the mtxFix / quaternion-swap math from scratch — it is already calibrated (see Coordinate conventions) and re-deriving it caused multiple wasted sessions in this project history.

---

## Skeleton & exclusion rules

- **Target skeleton is always `OFP2_ManSkeleton`**; bone names must match **exactly** (PascalCase + underscores) or the RPT logs `Error: Bone X doesn't exist in skeleton OFP2_ManSkeleton` and that bone silently does not animate. Repeated verbatim in three independent files: `[SKILLS]\dayz-animation-pipeline\references\player-skeleton.md:1-5`, `references\skeletal-anm-enfusion.md:33`, `references\weapon-anim-blender-complete.md:111`.
- **`RightHand_Dummy`** is the weapon anchor (child of it = the whole weapon). For a **full-body action anim**, animating `RightHand_Dummy` is a bug: it overrides the ikpose's grip and the weapon visually flies to the character's back. Root-caused and fixed in production: `[PROJ]\A6_SR2M_dev\reviews\2026-06-30-handoff-golpe-pipeline-CLOSE.md:15` ("Arma-a-la-espalda = `RightHand_Dummy` ... FIX: excluir `RightHand_Dummy` del `.anm` -> la ikpose sujeta el arma"). Cross-ref `player-skeleton.md:44-49` (what the dummy is / does).
- **Spine-up exclusion rule (action anims only)**: vanilla action anims (reload/fire/chamber/jam) exclude `EntityPosition`, `Pelvis`, and the leg chain — the idle/locomotion layer supplies those; including them makes the character "flop" (lie down / clip underground in-game). Root-caused in production: `2026-06-30-handoff-golpe-pipeline-CLOSE.md:16` ("Flop ... = incluir EntityPosition/Pelvis/piernas ... spine-UP"). Independently confirmed directly in code (not just a handoff claim): `[PROJ]\WeaponAnimPipeline_dev\tools\seanim_export.py:50-58` — the `--rest-pose` bone-mask logic filters the emitted bone list down to exactly the bones present in a vanilla reference SEAnim, with the comment "vanilla action anims are spine-UP — they exclude EntityPosition/Pelvis/legs; the idle provides the lower body. Including the rig's absolute root/pelvis orientation makes the player flop in-game."
- **`Weapon_*` bones need CORRECT values or must be dropped, never garbage values**: `Weapon_Bolt`, `Weapon_Trigger`, `Weapon_Magazine`, `Weapon_Bullet`, `Weapon_Bone_01..06` are legitimate skeleton bones the player rig drives, but if a viewer/tool exports them with placeholder/default values (not the real vanilla-derived transform), the weapon mesh visibly stretches. Root cause measured with DayZATool extraction (not guessed): `2026-06-30-handoff-golpe-pipeline-CLOSE.md:29` — `Weapon_Bone_01..06` collapsed to `(0,0,0)` vs vanilla `(-11.43,0.79,-2.48)` = ~11.7 cm displacement = stretched weapon mesh. Fix was to drop all 10 `Weapon_*` bones from that anim entirely (72→62 bones), accepting the bolt doesn't move during that specific action as a scoped trade-off.
- **IK helper bones must NOT be keyframed for non-IK (full-body/additive) anims.** `LeftHandOrigin`/`RightHandOrigin`/`*ForeArmDirection`/`LeftHandIKTarget` etc. do not exist in the vanilla skeleton; the plugin's importer silently drops their tracks if "Tools > Add Survivor IK Bones" wasn't run first, and stray keys on these "corrupt full-body/additive exports" per the plugin author (`[SKILLS]\dayz-animation-pipeline\references\weapon-anim-blender-complete.md:145`).
- **Hands are parented to the twist/roll bone, not the raw forearm** — `RightHand`'s real Blender parent is `RightForeArmRoll` (not `RightForeArm`); skipping the roll bone when computing a wrist's local-from-world quaternion leaks rotation into the wrist and can drop fingers up to ~11 cm. Verified by rendering in-game bone positions as an overlay, not by quaternion theory: `[SKILLS]\dayz-animation-pipeline\references\player-skeleton.md:34-42` (SP-039). Independently reproduced and root-caused the same way in the viewer tooling: `[PROJ]\WeaponAnimPipeline_dev\reviews\2026-06-29-handoff-pipeline-ingame-test.md:100-104`.
- **IK helpers do NOT roll the wrist** — rotating `LeftHandIKTarget`/`LeftHandOrigin`/etc. does not change hand/wrist orientation in-game; only the raw `LeftHand` + finger bones do that (proven with 4 ikpose variants, RMS pixel-diff). `[SKILLS]\dayz-animation-pipeline\references\player-skeleton.md:63`; corroborated `references\weapon-in-hands.md:90-105`.
- **Weapon-states `.anm` is 2-4 keys/channel, not a fixed "exactly 3 frames"** — an earlier draft of the pipeline reference claimed exactly 3 (closed/open/jammed); the vanilla-verified correction is 2-4 keys, Workbench trims near-duplicates: `[SKILLS]\dayz-animation-pipeline\references\anim-graph.md:183` header (content read as grep header only, not full body — flag if exact wording matters) and `references\weapon-in-hands.md:200-204` (verified table: AKM weapon-states = 2 distinct frames, not 3).

---

## Coordinate conventions

### Route A (`.txa` via plugin) — the mtxFix + component swap

- Axis fix (`mtxFix`): a **+90° rotation about Z that swaps Blender's X/Y axes**, matrix `[[0,1,0],[-1,0,0],[0,0,1]]`, applied identically in the plugin's `ImportTxa.py`, `ExportTxa.py`, `ExportTxo.py`. `[SKILLS]\dayz-animation-pipeline\references\weapon-anim-blender-complete.md:328` (`ImportTxa.py:141`, `ExportTxa.py:194,228` cited therein).
- `.txa` text-level component swap (a SEPARATE transform from the axis fix — do not conflate): translation/scale write as **X Z Y**; quaternion writes as **(x, z, y, -w)**; a final `FQuaternion(-w,-x,-y,-z)` is also applied on export. `weapon-anim-blender-complete.md:329` (`Txa.py:480-496,550-566`; `DayzAnimUtils.py:35-39`; `ExportTxa.py:250`).
- The same formula, independently re-derived and confirmed against a real calibration pair in this project (not just quoted from the plugin source): `[PROJ]\WeaponAnimPipeline_dev\reviews\2026-06-29-handoff-pipeline-ingame-test.md:135-137` — `rot_txa = mtxFix·viewer_local·mtxFixᵀ`, `#q file = (x,z,y,−w)`, and the note that **the root frame does NOT close correctly in a pure-Python re-implementation** (`jd EntityPosition→Pelvis` vs `.txa Scene_Root→{EntityPosition,Pelvis}`) — this is exactly why Route A must go through the real plugin/Blender, not a hand-rolled `.txa` writer.
- Unit scale: `fUnitScale` defaults to 1.0 in the plugin; assume 1.0 until a discrepancy appears (`weapon-anim-blender-complete.md:331`, marked `[verify]`).

### Route C (viewer JSON → `.seanim`) — CALIBRATED, exact

- Rotation: viewer-local quaternion `(x,y,z,w)` → SEAnim `(−y,−z,x,w)`. Position (rest-offset): `(x,y,z)` → `(y,z,−x)`, in **centimeters** (rig meters × 100). Calibrated against a real `.anm` (JD_SVD_Fire, `.txa`-via-plugin vs DayZATool-extracted `.anm`), **73 bone/frame pairs, exact to 0.00° globally**, DayZATool round-trip error 0.0007°: `[PROJ]\WeaponAnimPipeline_dev\tools\seanim_export.py:62-64` (in-code comment, the primary source) and `[PROJ]\WeaponAnimPipeline_dev\reviews\2026-06-29-handoff-pipeline-ingame-test.md:138-140` (independent confirmation). Also stated in skill form as `(-vy,-vz,vx,vw)` (same formula, "v" = viewer-prefixed): `[SKILLS]\dayz-animation-pipeline\references\weapon-anim-authoring-viewer.md:151-152`.
- This formula is verified **exact on fingers** but **`LeftHand` (the raw wrist bone) does NOT obey it** — a separate, not-yet-solved wrist process — so Route C must never be used to author the support-hand wrist orientation (`weapon-anim-authoring-viewer.md:152-153`).
- `UNIT_CM = 100.0` is hard-coded as "rig meters -> SEAnim cm (verified vs aks74u_reference finger offsets)": `[PROJ]\WeaponAnimPipeline_dev\tools\seanim_export.py:25`.

### General Blender ↔ DayZ axis convention (geometry and rig import, not just anim export)

- Blender Z-up → DayZ Y-up: `(x', y', z') = (x, z, −y)`. Stated for the animation-viewer rig-alignment case: `[SKILLS]\dayz-animation-pipeline\references\weapon-anim-authoring-viewer.md:53`. The general model-pipeline geometry equivalent (`x'=x, y'=z, z'=-y`) is referenced from `blender-authoring.md:31-32` (cross-referencing `dayz-model-pipeline`, not independently re-verified in this pass).
- **FBX rig scale trap** (bit this project twice — LFInfectedBig and this pipeline): the official BI rig FBX imports with the **mesh at object-scale 0.01** and the **armature at scale 1**, i.e. they live in disjoint spaces (armature cm/T-pose/pelvis-origin, mesh meters/feet-origin). Naively reading bone world positions puts the skeleton ~35x off the mesh. Fix = re-bind in a self-consistent space (derive a uniform scale from a known correspondence, e.g. wrist-bone-X vs mesh-half-width ⇒ `s≈0.0101`, translate to align bbox centers, then apply the Y-up axis fix). Full recipe: `weapon-anim-authoring-viewer.md:37-58`. **This FBX-rig bug is why the pipeline switched to the plugin's own `JD_Master_Rig` (no scale bug) as the authoring rig instead of the raw BI FBX** (`weapon-anim-authoring-viewer.md:129-136`).
- Game model-space (MS) → viewer/Three.js: position `(x, y, −z)` (z-flip, Enfusion is left-handed, Three.js is right-handed); the naive quaternion z-flip `(−x,−y,z,w)` renders **mirrored** — reconstruct the pose from measured **positions**, not from a flipped quaternion. `[SKILLS]\dayz-animation-pipeline\references\weapon-in-hands.md:240`.
- **FPS**: engine default and universal assumption throughout this pipeline = **30 fps**. Exporter option "Override Fps" should be set to 30 (0 = use scene fps); 20-25 fps for a slower/deliberate feel is also valid; 60 also valid. `weapon-anim-blender-complete.md:187`.
- **Scale is never keyed / is ignored** — DayZ ignores bone scale entirely; the plugin's Scale Keys export option defaults OFF and scale is dropped at binarize time even if present in the `.txa`. `weapon-anim-blender-complete.md:188,354`.

---

## Loop metadata

This is a fully-solved, non-obvious, and expensive-to-discover mechanism (3 rebuild cycles before the root cause was found) — the new skill must apply it correctly the first time for any hold/timer-driven action (unjam being the concrete case, but the mechanism is generic to any `HumanCommandActionContinuous`-style action).

- **Root cause chain when `LoopStart`/`LoopEnd` are missing** (traced against vanilla scripts, not guessed): the unjam action is **timer-driven**, not notetrack-driven — `WeaponUnjamming_Start.OnUpdate` accumulates `dt` and only calls `SetJammed(false)` at **5.0 s** (`m_jamTime`). The FSM exits only when `HumanCommandActionFinished` posts, which happens when `hcw.IsActionFinished()` is true. A `.anm` with no loop section **ends** at its last frame (e.g. ~1.7 s for a 51-frame anim), `IsActionFinished()` flips true, and because the unjam state isn't waiting for that (`IsWaitingForActionFinish()=false`) the FSM posts `_abt_` and transitions right back to the jammed state — the continuous action re-fires, and the 5 s timer **literally never accumulates** because the anim never stays "in progress" long enough. Vanilla avoids this because its jam anim HAS `LoopStart`/`LoopEnd` (frames 22/200 in `p_erc_jam_pm73`), so the command loops and `IsActionFinished()` stays false until the timer resolves it. Full trace with vanilla script file references: `[PROJ]\A6_SR2M_dev\reviews\2026-07-02-handoff-unjam-DONE-viewer-guion-next.md:15-26`.
- **Notetrack format**: `LoopStart` / `LoopEnd`, written as `Name||-1` — "idéntico al que extrae la vanilla" (identical to what vanilla extraction produces). Same handoff, line 30, and repeated in the re-authoring script: `[PROJ]\A6_SR2M_dev\reviews\2026-07-02-guion-golpe-reautor.md:98`.
- **Loop duration rule**: must last **≥ the engine timer (5 s for unjam), recommended ~6 s**, so the timer fires before the loop completes a full cycle and the wrap-around is simply never seen — this is literally what vanilla does (observed vanilla loop lengths: 5.9-6.9 s, always > the 5 s timer). This means the loop does NOT need to be a perfectly hand-closed cycle if it's long enough; the alternative (shorter, closed-loop) also works but is harder to author cleanly. `[PROJ]\A6_SR2M_dev\reviews\2026-07-02-guion-golpe-reautor.md:15-17`; same conclusion first reached in `2026-07-02-handoff-unjam-DONE-viewer-guion-next.md:114-118` ("una anim de unjam sin LoopStart/LoopEnd aborta a mitad y el arma nunca desatasca; el loop debe durar ≥ el timer de 5 s o cerrar seamless").
- **Outro after `LoopEnd`** carries the actual state-resolving notetrack (e.g. `Weapon_Unjammed`), timed near its end; vanilla outro is ~2.5-3.2 s. `2026-07-02-guion-golpe-reautor.md:18,38`.
- **The "micro-jerk" lesson (non-obvious, cost a full session)**: the engine exits the loop from **whatever pose is current at the moment the timer fires**, not necessarily the pose authored at `LoopEnd`'s frame — if the outro's start pose differs from the loop's late-cycle pose there is a visible snap. Practical fix: from some frame well before `LoopEnd` (e.g. "from ~f140" in a ~195-frame loop), settle the moving part into the "ready" pose and hold it through `LoopEnd`, so wherever the timer actually fires the pose is already consistent with the outro's start. `[PROJ]\A6_SR2M_dev\reviews\2026-07-02-handoff-unjam-DONE-viewer-guion-next.md:` §2 (lines ~31-34); restated as an authoring rule in `2026-07-02-guion-golpe-reautor.md:23-26`.
- **First attempt that did NOT fix the loop** (negative result worth keeping so it isn't retried): adding only mid-anim notetracks (`Weapon_CanUnjam_Start`, `Weapon_CanUnjam_End`, `Weapon_Unjammed`) without `LoopStart`/`LoopEnd` — verified to survive the `.anm` round-trip but the loop persisted unchanged. `[PROJ]\A6_SR2M_dev\reviews\2026-07-01-handoff-unjam-loop.md:15,18`. Confirms `CanUnjam_Start`/`CanUnjam_End` are not consumed by the unjam transitions at all (`2026-07-02-handoff-unjam-DONE-viewer-guion-next.md:39`).
- fps convention for loop-frame math throughout is the same 30 fps default noted above.

---

## What dayz-animation-pipeline already covers (do-not-duplicate list)

The new skill must treat all of the following as already-owned and reference them, not re-author them. File inventory of `[SKILLS]\dayz-animation-pipeline\`:

| Reference file | Owns | Why the new skill must not duplicate it |
|---|---|---|
| `SKILL.md` | Top-level routing table (object vs skeletal vs vehicle-rider vs anim-graph), the Layer 1/2/3 seam definition, the one-anim-mod wall + its 2026-06-28 correction (graph-replacement only, weapon anims are conflict-free) | This is the front door; the new skill should be reachable FROM this routing table (a new row pointing at it), not replace it. `SKILL.md:41-65` is the decision table; `SKILL.md:10-26` is the seam. |
| `references/config-driven-animation.md` | Full `model.cfg` `class Animations` property reference (type, source, selection, axis, begin/end, minValue/maxValue, sourceAddress, angle0/1, offset0/1, hideValue), `class AnimationSources` in config.cpp, the full engine `source` value list, `SetAnimationPhase`/`GetAnimationPhase` script interface | This is Layer 1 (config-driven object/door/lever animation) — entirely orthogonal to skeletal character/weapon animation. A Blender-authoring skill for skeletal anims should never touch this. Read in full: `config-driven-animation.md:1-115` (file continues past what was read; core tables captured). |
| `references/item-ik-and-hide.md` | Pattern A (reuse a vanilla `.anm` for carry-IK on heavy items via `AddItemInHandsProfileIK` with a 4-arg / no-weapon-states call) and Pattern B (hide-on-attach via a `hide`-type animation) | Both patterns are "reuse vanilla, zero new authoring" — explicitly the opposite of what a Blender-authoring skill does. Read: `item-ik-and-hide.md:1-40`. |
| `references/skeletal-rtm.md` | The legacy RTM route (Arma-era, FBXToRTMGui.exe / Arma3ObjectBuilder) | Not read in full this pass, but `SKILL.md:50` and `tooling-and-walls.md:22-27,32` establish it is legacy/reverse-engineered and explicitly NOT the route for player/weapon anims — "RTM is the #1 wrong turn" (`weapon-anim-blender-complete.md:49`). The new skill should actively warn against it, not implement it. |
| `references/skeletal-anm-enfusion.md` | The Enfusion `.txa`/SEAnim/`.anm` pipeline overview, the two-route framing, source-of-truth repo URLs | This is the file the new skill's Route A/C summary above was cross-checked against; it is the conceptual owner of "which route for what." Read in full: `skeletal-anm-enfusion.md:1-63`. |
| `references/player-skeleton.md` | The full bone catalog by zone (core/spine, legs, arms, fingers, IK helpers, weapon bones, face, misc/legacy) | The new skill should reference this catalog rather than re-list bone names; it already carries the SP-039 twist-bone-parent gotcha and the `RightHand_Dummy` facts cited above. Read in full: `player-skeleton.md:1-110`. |
| `references/anim-graph.md` | State machine / `CMD_*` command catalog, `#Var` declarations, ASI `$animsetinstance` structure, player ASI catalog, weapon-state-path convention, "reload is not additive" correction, Workbench Animation Editor `#eventtable` trick, creature-graph minimal workflow | This is the wiring/graph layer downstream of any `.anm` the new skill produces — headers confirmed via grep: `anim-graph.md:1,20,52,62,71,91,108,127,137,149,157,164,170,172,183,187`. Not fully read this pass (headers only) — the new skill should point here for anything about HOW an `.anm` gets selected at runtime. |
| `references/weapon-in-hands.md` | The full grip/ADS memory-point contract (`eye`, `usti/konec hlavne`, `bolt_axis`, etc.), the grip validator tool, the "geometric parity is the grip fix" doctrine, the ikpose/wrist-inertness finding, the live bone-dump technique for engine-IK-resolved poses | This is the definitive answer to "why does the weapon look wrong in the hand" — a Blender-authoring skill must defer to this rather than re-deriving grip fixes. Read in full: `weapon-in-hands.md:1-247`. |
| `references/weapon-anim-authoring-viewer.md` | **The existing Layer-2 interactive authoring pipeline itself** (viewer, IK, keyframe timeline, both export routes, current viewer feature set as of 2026-07-05) | **Highest-overlap-risk file.** This IS "a blender-animation skill" in spirit, just implemented as a bespoke Three.js viewer instead of live Blender. The new skill's pitch must be "the same outcome, driven inside real Blender via MCP" — not a second, parallel viewer. Read in full: `weapon-anim-authoring-viewer.md:1-175`. |
| `references/weapon-anim-blender-complete.md` (906 lines; read 1-516 of 906 this pass) | The single most complete reference: Blender version matrix, addon install, rig roster, IK-helper setup, per-anim-type authoring craft (ikpose/fire/weapon-states/reload/aim-space/magazine-tracking), `.txa` export types and text format, Workbench compile gotchas, the full `config.cpp`/`.asi`/Enforce Script wiring contract (`AddItemInHandsProfileIK`, `AddItemBoneRemap`, the 42 `WeaponOperations.*` state names), mod folder scaffolding | This is the master reference the new skill should point to for anything Blender-plugin-mechanical (export types, event markers, `.txo`) rather than re-explain. Sections not read (517-906) likely cover deploy/packaging/troubleshooting — check before assuming a gap. |
| `references/vehicle-rider-ik-pose.md` | IK-from-anchors solver for seated vehicle poses (2-bone analytic IK + straight-spine, 21 solved joints), rest-pose calibration requirement, frame-of-reference caveat | Different domain (vehicle seating, not weapon/action anims) but same rest-pose-calibration and coordinate-frame caveats apply; reference rather than duplicate the solver math. Read in full: `vehicle-rider-ik-pose.md:1-118`. |
| `references/handlebar-and-steering-config.md`, `references/dual-entry-action-pattern.md` | Layer 1 config-driven vehicle-part rotation, and a scripted get-in seat-side-snap pattern | Not read this pass; out of scope for a Blender-animation skill (config/script layer, not authoring). |
| `references/selection-painter-for-actions.md`, `references/py3d-1.0.0-quirks.md` | `.p3d` named-selection painting/writing quirks for action raycasts | Model-editing side (adding the selections/axes an animation drives), owned by `dayz-p3d-inspector`/`dayz-model-pipeline`, not by an animation-authoring skill. |
| `references/blender-authoring.md` | **The existing "Layer 2 programmatic Blender authoring" stub** — headless `bpy` keyframing recommendation, bone-name discipline, FPS/scale, coordinate-handling caveats | **Second highest-overlap-risk file.** This is explicitly the sandbox/headless-Blender authoring guidance the new skill would supersede or extend. It currently marks several things `[TBD-verify]` (exact axis conversion, whether SEAnim/FBX export needs manual axis fix) that this research's other citations above have since resolved empirically (mtxFix, Y-up fix, Route A/C formulas) — the new skill (or a patch to this file) should close those TBDs rather than re-open them. Read in full: `blender-authoring.md:1-36`. |
| `references/tooling-and-walls.md` | Canonical tool inventory table, the two-format (RTM vs `.anm`) split, the walls (one-anim-mod, RTM/`.anm` closed-format caveats), signing/deploy pointer, "what to hand the user" checklist | The new skill's handoff message should follow the exact checklist here (`tooling-and-walls.md:41-49`) rather than invent its own handoff format. |
| Sibling skill `mixamo-retarget` | Retargeting Mixamo/FBX mocap onto an arbitrary armature (incl. DayZ skeleton) via Blender MCP already, fuzzy bone-matching, rest-pose-mismatch caveat | **Note**: this sibling skill ALREADY drives Blender via the same MCP (`execute_blender_code`) the new skill would use — it is the closest existing precedent for "live Blender MCP session touching the DayZ skeleton." Its output feeds Layer 2 as a keyframe SOURCE, explicitly not a shortcut around the rest of the pipeline (`[SKILLS]\mixamo-retarget\SKILL.md:49-51`). Status: EXPERIMENTAL, fixture-unvalidated (`SKILL.md:10`, `53-55`). |
| `dayz-model-pipeline/references/animations.md` | An independent, fairly complete restatement of the SAME `model.cfg`/`CfgSkeletons`/`CfgModels`/`class Animations` syntax as `dayz-animation-pipeline/references/config-driven-animation.md` (rotation/translation/hide types, axis, minValue/maxValue, angle0/1) | **Overlap between two existing skills**, not something the new skill should add a third copy of. `dayz-model-pipeline/SKILL.md:50` points here for "Animations (model.cfg)"; content cross-checked at `references/animations.md:1-79` and it duplicates config-driven-animation.md's core tables almost exactly. If the new skill ever needs to mention config-driven animation in passing, point at `dayz-animation-pipeline` (the animation-specialist skill) as canonical, not `dayz-model-pipeline`. |

---

## Blender-side conventions

- **Blender version is plugin-fork-dependent and the metadata lies — always check the code, not `bl_info`.** Original `jdfnc24/DayZAnimationPluginDemo` needs **Blender 3.6.8-4.0** (breaks on ≥4.1 with `AttributeError: 'Mesh' object has no attribute 'calc_normals_split'`). The **maintained Sanitoeter05 fork** (the one actually in use in this pipeline) needs **Blender 4.4+/5.x** (calls `action.fcurve_ensure_for_datablock`, a 4.4+ API, and a helper literally named `generate_fcurves_bl51`) — yet its own `bl_info` falsely declares `'blender': (2, 80, 0)`. `[SKILLS]\dayz-animation-pipeline\references\weapon-anim-blender-complete.md:56-67`; same correction in `references\tooling-and-walls.md:57-59`. This project's actual working environment used **Blender 5.1** (`[PROJ]\A6_SR2M_dev\reviews\2026-06-30-handoff-golpe-pipeline-CLOSE.md:23`).
- **Install is a manual folder copy, not a zip**: copy `BlenderPlugin/DayzAnimationTools` into `%AppData%\Roaming\Blender Foundation\Blender\<version>\scripts\addons\DayzAnimationTools`, then enable "DayZ Animation Tools" in Preferences > Add-ons. Blender's "Install from file" does NOT work on this download. `weapon-anim-blender-complete.md:69-77`.
- **Actual local install path used in this environment**: `<downloads>\DayZAnimationPlugin_MAINTAINED\` (both the addon and its `_AssetSamples` rig/pose blends live under here) — confirmed as literal path constants in working code: `[PROJ]\WeaponAnimPipeline_dev\tools\txa\viewer_to_txa_via_plugin.py:7-8` (`PLUGDIR`, `BLEND`).
- **Rig source of truth**: `_AssetSamples\JD_Master_Rig (No IK Bones).blend` = `OFP2_ManSkeleton` with correct vanilla bone names and custom display shapes on focal bones; this IS the rig to pose. `weapon-anim-blender-complete.md:107-111`. A second candidate rig source (the raw BI FBX `animation_rig_character.fbx`, 114 bones) has the scale-space bug documented in Coordinate conventions above and should be avoided in favor of the JD rig (`weapon-anim-authoring-viewer.md:129-136`).
- **"Add Survivor IK Bones" (`import_scene.addsurvivorik`) must run BEFORE authoring any IK/grip pose.** It creates `LeftHandOrigin`/`RightHandOrigin`/`*ForeArmDirection` and adds Blender IK constraints on `LeftHand`/`RightHand` with baked pole angles **−127.9° (Left) / +45.3° (Right)**. Importing/authoring an IK `.txa` without this first silently drops those bone tracks (the importer prints a warning). Conversely, these helper bones must NEVER be keyed for non-IK anims. `weapon-anim-blender-complete.md:136-145`.
- **Export Type discipline is load-bearing, not cosmetic**: `FB` (Full Body — emotes only, injects a `Scene_Root`), `IK1H`/`IK2H` (grip ikpose, single keyframe, plugin auto-restricts to the IK bone list — do not pre-select bones), `RL` (rarely used, treated as `ADD` in practice), `ADD` (reload/fire/chamber/jam/weapon-states — use "Selected Bones Only"). Exporting **ALL** bones on a reload/action anim makes the character "turn into a meatball" in-game. `weapon-anim-blender-complete.md:282-297`.
- **Never key scale** (engine ignores it entirely) — see Coordinate conventions.
- **Workbench silently trims near-identical consecutive keyframes** — an authored "hold" can collapse to fewer frames than intended; author with meaningful keyframe deltas, and always keep the source `.txa` next to its `.anm` since Workbench can only re-edit an `.anm` if the `.txa` is present. `weapon-anim-blender-complete.md:351-356`.
- **Never assume rig facing direction — measure it.** A hardcoded assumption that the character faces `+X` was wrong; the JD rig actually faces **−Z** when aimed (measured via hip/shoulder forward vectors: `fwdHip=(0.75,0,-0.66)`, `fwdShoulder=(0.57,0,-0.82)`), and the bug was mis-diagnosed as "roll" for a full session before being correctly identified as "yaw." `[PROJ]\WeaponAnimPipeline_dev\reviews\2026-06-29-handoff-pipeline-ingame-test.md:30-37`. Generalizable lesson: measure rig-forward empirically before writing any orientation-fix code.
- **Character import scale (`f=0.7901`) is NOT part of this pipeline** — it is tagged in this user's cross-session memory to a *different* project ("LF Big Infected," a custom zombie/character mesh import), not to weapon/action-animation authoring. It was not found in any file searched this session (see Open questions). Do not apply it here without separately verifying its source.

---

## Open questions

Things the available files do not answer, or that this session could not verify — flag to the user / re-check at skill-authoring time rather than guessing:

1. **`dayz-characters` skill could not be located.** Searched `[SKILLS]\..\skills-plugin\` (the same mount that has `dayz-animation-pipeline`, `mixamo-retarget`, `dayz-model-pipeline`, etc.) with a targeted Glob for `**/dayz-characters/SKILL.md` and a broader `**/dayz-characters/**` under `C:\Users\<you>` (the latter timed out after 20 s / returned nothing conclusive). It is listed as an available skill name in this session's system reminders, but no backing `SKILL.md` was found on disk in the locations checked. Possibilities: it lives under a different plugin registration not covered by these Globs, or the skill-name list includes entries without a locally-readable file. The new skill's authors should re-verify with `ToolSearch`/direct invocation rather than assuming its content matches this report's inferences about character work.
2. **The `f=0.7901` / `T2=(−x,z,y)` scale-orientation convention** (mentioned in this user's persistent memory index for the "LF Big Infected" project) was not found in any file searched under `[PROJ]` this session (a Glob for `*Infected*` under the DayZ Projects root returned only unrelated `<tmp>` script files). It appears to be a **mesh-import/rig-binding scale fact for one specific character model**, not a general animation-authoring convention — likely irrelevant to a Blender-animation-authoring skill, but flagged since the task explicitly asked about it. Would need `<claude-home>\projects\...\memory\lf-big-infected-project.md` or the actual project handoff (path unknown, not located this session) to confirm.
3. **No verified use of the Blender-side SEAnim plugin (SE2Dev `io_anim_seanim`) in this project's history** — all concrete, in-game-tested work went through the DayZAnimationPlugin_MAINTAINED (`.txa`) route or the Python `seanim_writer.py` (which is a standalone reader/writer, not a Blender plugin/importer). If the new skill wants a Blender-native SEAnim import/export path as an alternative to Route A, `io_anim_seanim` is cited only as existing (`tooling-and-walls.md:19`) — not exercised or validated in this environment.
4. **Route C's calibration formula (`(-vy,-vz,vx,vw)` / cm scale) was calibrated against exactly one weapon/anim pair** (JD_SVD_Fire, 73 bone/frame samples). It is described as "GLOBAL" (not per-bone) and "exact," but re-verify if the maintained plugin fork or Blender version changes, since the formula is tied to the plugin's own mtxFix/component-swap internals.
5. **Final in-game confirmation of the fully-fixed `golpe.anm`** (loop + seamless ping-pong + micro-jerk fix + thumb curl) was still pending as of the last handoff read (`2026-07-02-handoff-unjam-DONE-viewer-guion-next.md:6-13,46-53` — user interrupted the test). This report's "Route A: CLOSED, in-game confirmed" status is scoped to the earlier golpe body/head/weapon-grip fix (2026-06-30) specifically, not to the loop/unjam polish pass. Check `A6_SR2M_dev\HANDOFF.md` (not opened this session) for whatever happened after 2026-07-02 before assuming full closure.
6. **The viewer's "build 2026-07-05" feature set** (per-finger+thumb absolute sliders, live hyperextension guard, keyframe auto-update) is described only secondhand via handoff prose in this report (`2026-07-02-...` and `2026-07-05-flujo-agarre-con-visor.md`) — `tools/build_viewer.py` itself was not opened in full this session. If the new skill needs to match or extend this UX inside Blender, read that script directly rather than relying on this report's paraphrase.
7. **`anim-graph.md` was only grepped for section headers, not read in full** (to conserve budget given its content was already well-covered by `skeletal-anm-enfusion.md` and `weapon-anim-blender-complete.md`'s ASI section for this report's purposes). If the new skill needs the exact `CMD_*`/ASI grammar, read `anim-graph.md` in full rather than relying on the header list in the do-not-duplicate table.

---

## Citations index

All paths below were opened directly with the Read/Grep tool this session (not inferred from search snippets). Alias definitions repeated here for standalone use of this section.

`[SKILLS]` = `<claude-appdata>\local-agent-mode-sessions\skills-plugin\<plugin-id>\<install-id>\skills`
`[PROJ]` = `<dayz-projects>`

**Skill files read (full or substantial partial read):**
- `[SKILLS]\dayz-animation-pipeline\SKILL.md` (238 lines, read in full)
- `[SKILLS]\dayz-animation-pipeline\references\skeletal-anm-enfusion.md` (63 lines, full)
- `[SKILLS]\dayz-animation-pipeline\references\player-skeleton.md` (110 lines, full)
- `[SKILLS]\dayz-animation-pipeline\references\weapon-anim-blender-complete.md` (906 lines total; read lines 1-516)
- `[SKILLS]\dayz-animation-pipeline\references\weapon-anim-authoring-viewer.md` (175 lines, full)
- `[SKILLS]\dayz-animation-pipeline\references\tooling-and-walls.md` (64 lines, full)
- `[SKILLS]\dayz-animation-pipeline\references\blender-authoring.md` (36 lines, full)
- `[SKILLS]\dayz-animation-pipeline\references\vehicle-rider-ik-pose.md` (118 lines, full)
- `[SKILLS]\dayz-animation-pipeline\references\config-driven-animation.md` (read lines 1-115 of a longer file)
- `[SKILLS]\dayz-animation-pipeline\references\weapon-in-hands.md` (247 lines, full)
- `[SKILLS]\dayz-animation-pipeline\references\item-ik-and-hide.md` (read lines 1-40)
- `[SKILLS]\dayz-animation-pipeline\references\anim-graph.md` (headers only, via Grep `^#{1,3} `)
- `[SKILLS]\mixamo-retarget\SKILL.md` (59 lines, full)
- `[SKILLS]\dayz-model-pipeline\references\animations.md` (read lines 1-79 of a longer file)
- `[SKILLS]\dayz-model-pipeline\SKILL.md` (grepped for `class Animations|AnimationSources|CfgSkeletons|model\.cfg`, not read in full)

**Project files read (full):**
- `[PROJ]\WeaponAnimPipeline_dev\README.md` (129 lines)
- `[PROJ]\WeaponAnimPipeline_dev\reviews\2026-06-28-handoff-next-session.md` (74 lines)
- `[PROJ]\WeaponAnimPipeline_dev\reviews\2026-06-29-handoff-pipeline-ingame-test.md` (184 lines)
- `[PROJ]\WeaponAnimPipeline_dev\reviews\2026-06-29-handoff-weapon-part-animation.md` (41 lines)
- `[PROJ]\WeaponAnimPipeline_dev\reviews\2026-07-05-flujo-agarre-con-visor.md` (77 lines)
- `[PROJ]\A6_SR2M_dev\reviews\2026-06-30-handoff-golpe-pipeline-CLOSE.md` (49 lines + embedded project CLAUDE.md)
- `[PROJ]\A6_SR2M_dev\reviews\2026-07-01-handoff-unjam-loop.md` (51 lines)
- `[PROJ]\A6_SR2M_dev\reviews\2026-07-02-handoff-unjam-DONE-viewer-guion-next.md` (125 lines)
- `[PROJ]\A6_SR2M_dev\reviews\2026-07-02-guion-golpe-reautor.md` (117 lines)

**Source code read directly (primary source, not doc-mediated):**
- `[PROJ]\WeaponAnimPipeline_dev\tools\seanim_export.py` (lines 1-70 of the file read)
- `[PROJ]\WeaponAnimPipeline_dev\tools\txa\viewer_to_txa_via_plugin.py` (lines 1-60 of the file read)

**Searches that returned no result (documented for the Open questions section, not fabricated):**
- Glob `**/dayz-characters/SKILL.md` under `<claude-appdata>` — no files found.
- Glob `**/dayz-characters/**` under `C:\Users\<you>` — ripgrep timeout after 20 s, no conclusive result.
- Grep `0\.7901` under `[PROJ]` — 36 matches, all in unrelated binary/XML/OBJ files (`mapgroupcluster*.xml`, `cherno2.obj`), none textually relevant.
- Glob `*Infected*` under `[PROJ]` — only `<tmp>\DayZ-Expansion-Scripts\...` unrelated script files.
- Glob `**/*eaponAnim*` and `**/*SR2M*` under `<project-notes>` — no files found (these two projects are not mirrored into the Obsidian vault; their handoffs live only under `[PROJ]` and the user's `.claude/projects` auto-memory).


## Addendum — eval-run findings (2026-07-10, verified during benchmark runs)

- **Ring/Pinky finger chains of the JD rig must be excluded from exports.** In
  `JD_Master_Rig (No IK Bones).blend` they hang from carpal bones (`RightHandRing`,
  `RightHandPinky`) that do NOT exist in the vanilla `OFP2_ManSkeleton`
  (`DZ\Anims\cfg\skeletons.anim.xml`) — their local transforms would reference a parent
  the engine does not have. Thumb/Index/Middle chains parent directly to `RightHand` and
  export safely (verified during the wave-action eval run).
- **Palm-orientation gate for gestures**: see SKILL.md section 7 — measure character
  forward from bone geometry and assert the palm normal numerically; judge stills only
  from an on-axis camera.
