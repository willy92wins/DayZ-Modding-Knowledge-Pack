> ## VERIFIED CORRECTIONS (added 2026-06-28 after the completeness-critic pass, checked against vanilla primary source)
>
> 1. **{GUID} keys: DO NOT strip them.** The body of this doc says ~4x to remove the {GUID} serial keys from copied .asi files ("DayZ does not need them"). That is WRONG - verified against vanilla DZ/anims/workspaces/player/player_main/weapons/player_main_akm.asi: every line carries a {GUID} prefix (#template, #parent, #ikpose, and all 27 .anm value lines). Keep them / let Workbench generate them. Hand-authoring bare paths risks silent resolution failure. [VERIFIED vanilla]
> 2. The companion *-CRITIC.md lists the remaining must-verify items (ikpose_* config keys, the 3-frame weapon-states convention, the "filepatching does not reload .anm" claim, the reloadAction legacy class) - each with the exact primary source to check before relying on it.
> 3. Verified-correct and safe to rely on: the conflict-free-across-mods finding for weapon anims via the ASI route (the one-anim-mod wall applies only to player-GRAPH-replacing mods), the AddItemInHandsProfileIK 5-arg signature (dayzplayer.c:243), and the 42 WeaponOperations.* names (player_main.ast:1236-1280).

---

# Authoring DayZ Playable-Character Weapon Animations in Blender — Complete End-to-End Workflow

> Definitive, no-gaps reference for the Enfusion `.txa` → Workbench `.anm` route (DayZAnimationPlugin / OFP2_ManSkeleton). Audience: an engineer or AI skill that must execute the entire pipeline with zero prior gaps. Every load-bearing fact carries an inline source. Facts that are video/forum-only or `verified=false` in the research are marked `[verify]`. A consolidated **Open gaps** section is at the end.

---

## 0. Overview and the two routes

### 0.1 What "a custom player weapon animation" actually is

A playable-character weapon animation in DayZ is **not** wired through `config.cpp` animation keys. It reaches the player through **three decoupled layers**, and crucially does **not** edit the player animation graph (`.agr`):

1. **Authoring** — keyframe the `OFP2_ManSkeleton` rig in Blender, export `.txa` (human-readable text) with the DayZAnimationPlugin. Workbench compiles `.txa → .anm` (binary).
2. **Mapping** — a per-weapon `.asi` (`$animsetinstance`) text file maps dotted engine state paths `WeaponOperations.<RigKey>.<State>` to your `.anm` files, inheriting a parent chain (your `weapon.asi` → `player_main_rifle.asi` → `player_main.asi`).
3. **Binding** — an Enforce Script call `AddItemInHandsProfileIK(itemClass, asi, behavior, ikPose.anm, weaponStates.anm)` binds your weapon classname to the `.asi` + a one-time IK pose + a separate weapon-states `.anm`; a second call `AddItemBoneRemap(itemClass, pairs[])` maps your p3d/model.cfg part selections to the player skeleton's `Weapon_*` bones.

Because this ASI route does **not** modify `player_main.aw`/`.agr`, it is **conflict-free across mods** (multiple weapon-anim mods coexist; vehicles are the unsupported exception). The "only one animation mod at a time" wall applies only to mods that replace the **player animation graph** itself (e.g. Expansion-Animations). (`dayzplayer.c:243`; `dayzplayercfgbase.c:382,411`; release transcript Yrh2ZIqAaOs; `answeroverflow.com/m/1090534919182233642`.)

Three distinct artifact kinds exist per weapon (do not conflate):

| Artifact | What it is | Where referenced |
|---|---|---|
| **IK pose** (`#ikpose`) | One-frame hand/finger placement on the gun | `.asi` `#ikpose`; 4th arg of `AddItemInHandsProfileIK` |
| **Weapon-states** (`w_*_states.anm`) | 3-frame additive anim of only the `Weapon_*` bones (bolt closed/open/jammed) | 5th arg of `AddItemInHandsProfileIK`; `SetInitState` reads it |
| **Action anims** (reload/fire/chamber/jam) | Additive deltas (≈ shoulders-down) blended on the idle | `.asi` `$animations` map |

The `.asi` animations **blend on top of** the weapon-states `.anm` and override those bone transforms. (`answeroverflow.com/m/906540004170432552`, MarioE; `human.c:1081-1088`.)

### 0.2 The two routes (and when to use which)

| | **Route A — `.txa` / Workbench (canonical)** | **Route B — SEAnim / DayZATool** |
|---|---|---|
| Authoring file | `.txa` (text) via DayZAnimationPlugin in Blender | SEAnim (open format) |
| To `.anm` | Workbench "Register resource and import" / "Reimport Resource" | `DayZATool --generate-anim file.seanim` |
| Maintained tooling | Yes — Sanitoeter05 MAINTAINED fork of MrTea/HunterZ plugin, local clone present | DTZxPorter closed `.NET` binary, requires .NET 4.5 |
| Rig quality | Correct (uses the master rig + IK helpers) | Community reports extracted rigs are **"always wrong"** for anything using empties (the IK helper bones used by weapon reload/state anims); inverts local bone axes | 
| Recommended for | **Player weapon anims** (this document) | Extracting reference meshes/anims only |

**Decision:** For a playable-character weapon animation, use **Route A**. This is what the canonical demo (`JDsAnimationDemo`) and the community use. Route B is a fallback for when Route A is blocked, and is fully compatible with the same `.asi` wiring + AddonBuilder packaging — but its extracted rig is a reference, not a clean round-trip. (Steam Workshop MRTsBackflip id 2510405063; `answeroverflow.com/m/824986169522520064` MarioE; `dtzxporter.com/tools/dayzatool`.)

**Do NOT** use RTM (Real Virtuality, Arma-era config-driven prop animation) for a player weapon animation — it is the #1 wrong turn. RTM is for legacy config-driven props; characters and weapons are Enfusion `.txa → .anm`. (`skeletal-rtm.md:5-17`.)

---

## 1. Tools + environment setup

### 1.1 Blender version — resolve this FIRST (the stale-README trap)

The plugin README and the official release video both say **"Requires Atleast Blender 3.6.8"** and recommend exactly 3.6.8. That is correct **for the original jdfnc24/MrTea plugin**. (`README.md:4`; Yrh2ZIqAaOs transcript.)

**BUT** the locally-cloned **Sanitoeter05 MAINTAINED fork** has been ported to newer APIs and will **NOT** run on 3.6.8:
- `Import/ImportTxa.py` calls `action.fcurve_ensure_for_datablock(...)` (a Blender **4.4+** slotted-actions API) and a helper `generate_fcurves_bl51` (bl51 = Blender **5.1**). (`ImportTxa.py:378-384,227,234`.)
- `bl_info` in `__init__.py` **falsely** declares `'blender': (2, 80, 0)` — this is meaningless; do **not** trust it. (`__init__.py:8`.)

**Rule:** Always check the import code's API calls against your Blender version before choosing.
- **Maintained (Sanitoeter05) fork → Blender 4.4+ / 5.x.**
- Original jdfnc24/MrTea plugin → Blender 3.6.8.

Note: Blender 5.x `.blend` files won't open in 4.2, and the bundled sample `.blend` files were saved in 3.6.8 (won't open in older). At least one user hit an enable error on 4.1 with the original plugin. (`answeroverflow.com/m/1512103128257007667`; Yrh2ZIqAaOs transcript.)

### 1.2 Install the addon (manual folder copy — NOT a zip)

The download is a **plain folder**, not a zip, so Blender's "Install from file" will **not** work.

1. Copy the folder `BlenderPlugin/DayzAnimationTools` into Blender's addons dir:
   `%AppData%\Roaming\Blender Foundation\Blender\<version>\scripts\addons\DayzAnimationTools`
2. Blender → **Edit > Preferences > Add-ons**, search **"DayZ"**, tick **"Dayz Animation Tools"** to enable.

(`README.md:18`.)

### 1.3 Where the tools live in the UI

After enabling:
- A top editor-menu **"DayZ Animation Tools"** appears (registered via `VIEW3D_MT_editor_menus`) with submenus **Import / Export / Tools**.
- Import/Export also surface in **File > Import** and **File > Export** as **"DayZ Animation (.txa)"** and **"DayZ Object (.txo)"**.
- The **Event Manager** is a 3D-viewport sidebar (N-panel) tab: **"Dayz Animation Tools" > "Events"** (`EventManager.py`: `bl_category='Dayz Animation Tools'`, `bl_region_type='UI'`).

### 1.4 DayZ Tools / Workbench + the P:\ work drive

- **Work drive:** Launch DayZ Tools → Settings → uncheck "Default" → pick a drive (recommended **P:\**, 20 GB+ free) → Apply. Then **Tools → Extract Game Data** to unpack vanilla into `P:\DZ\...`, `P:\scripts\...`.
- In this repo, **`P:\` is a junction to `<dayz-projects>\`** (Bohemia tools require the work drive at `P:\`). For Read/Write/Edit/Grep use the real OneDrive path; for BI tools use `P:\`.
- `SetupWorkdrive.bat` creates junctions `P:\<ModName>` for any folder containing `Workbench\dayz.gproj`. (`SetupWorkdrive.bat:12-20`.)
- Set Workbench as the default app to enable fast **F6 launch / F10 kill** from the resource browser.

### 1.5 The vanilla animation source tree (read-only reference)

- Player workspace: `DZ/anims/workspaces/player/player_main/` (`.asi`, `.ast`, `.aw`, `.agr` files).
- Compiled anim tree: `DZ/anims/anm/player/...` (IK: `ik/weapons/<wpn>.anm`; reloads/states: `reloads/<wpn>/w_<wpn>_states.anm`).
- Player skeleton config: `DZ/Anims/cfg/skeletons.anim.xml` (referenced by `dayz.gproj` `skeletonDefinitions`).

### 1.6 Optional: DayZATool (Route B fallback)

DTZxPorter DayZATool: `--extract-anim` (ANM→SEAnim), `--extract-model` (XOB→SEModel), `--generate-anim file.seanim` (SEAnim→.anm). Requires .NET Framework 4.5; expect manual scale tuning. Blender importers: `io_scene_seanim`, `io_model_semodel`. (`dtzxporter.com/tools/dayzatool`.)

---

## 2. The rig (OFP2_ManSkeleton / JD master rig)

### 2.1 Open the master rig

Open `_AssetSamples/JD_Master_Rig (No IK Bones).blend`. This armature **is** `OFP2_ManSkeleton` with vanilla bone names. The rig ships custom display shapes on focal bones (hand, forearm, knee, foot) for grabbing in Pose Mode.

**Hard wall:** Bone names must match `OFP2_ManSkeleton` **exactly** (PascalCase + underscores), case- and spelling-precise, or the RPT logs `Error: Bone X doesn't exist in skeleton OFP2_ManSkeleton` and that bone silently does **not** animate. The skeleton **cannot be restructured** — overlay only; adding/removing bones breaks vanilla anim compatibility. (`tooling-and-walls.md:34`; `skeletal-anm-enfusion.md:33`.)

### 2.2 Bone roster (inferred from sample `.txa` + plugin code — `[verify]` full ordered list by opening the rig or running GenerateModelCfg)

| Group | Bones |
|---|---|
| Root | `Scene_Root`, `EntityPosition`, `Collision` |
| Spine | `Pelvis`, `Spine`, `Spine1`, `Spine2`, `Spine3` |
| Head | `Neck`, `Neck1`, `Head` |
| Left arm | `LeftShoulder`, `LeftArm`, `LeftArmRoll`, `LeftForeArm`, `LeftForeArmRoll`, `LeftHand` (mirror `Right*`) |
| Fingers | `LeftHand{Thumb,Index,Middle,Ring,Pinky}1..4` (mirror `Right*`) + `*Roll`/`*Extra` helpers |
| Legs | `LeftUpLeg`, `LeftUpLegRoll`, `LeftLeg`, `LeftLegRoll`, `LeftFoot`, `LeftToeBase` (mirror `Right*`) |
| Dummies | `RightHand_Dummy`, `LeftHand_Dummy` |
| Weapon | `Weapon_Bolt`, `Weapon_Trigger`, `Weapon_Magazine`, `Weapon_Bullet`, `Weapon_Bone_01..06`, legacy `Weapon_Root` |

(`ImportTxa.py`; sample `.txa`; `player-skeleton.md`.)

### 2.3 Weapon bones and the right-hand parenting

- An item held in the right hand is parented to bone **`RightHand_Dummy`** (the weapon is a child of the right hand).
- **Modern DayZ anims use `RightHand_Dummy` (NOT `Weapon_Root`)** to move the gun; `Weapon_Root` is legacy and unused by modern anims. (`AddSurvivorIK.py:59`; `ImportTxa.py:257,284`; Yrh2ZIqAaOs transcript.)
- The player skeleton drives weapon sub-bones: `Weapon_Bolt`, `Weapon_Trigger`, `Weapon_Magazine`, `Weapon_Bullet`, and **six configurable slots `Weapon_Bone_01..Weapon_Bone_06`** for arbitrary moving parts. (`player-skeleton.md:55-61`.)
- **Do NOT** use the legacy bones `Bullet/Trigger/Magazine/Bolt/Universal1/2` (marked To-Be-Removed in `player_testing.xob`). (`player-skeleton.md`.)
- **There are no dedicated magazine-in-hand bones.** The engine tracks mag position via `LeftHand_Dummy`. (`player-skeleton.md:39`.)

### 2.4 Add Survivor IK Bones — required ONLY for IK/hand-placement anims

Run **Tools > "Add Survivor IK Bones"** (operator `import_scene.addsurvivorik`) with the armature selected. It creates:
- `LeftHandOrigin` (parent `RightHand_Dummy`)
- `RightHandOrigin` (parent `RightShoulder`)
- `RightForeArmDirection` / `LeftForeArmDirection` (parents `RightShoulder` / `LeftShoulder`)

and adds Blender IK constraints on `LeftHand`/`RightHand`: `chain_count=5`, pole targets = the `*ForeArmDirection` bones, `pole_angle` baked at **-127.9° (Left)** / **+45.3° (Right)**. (`AddSurvivorIK.py:52-129`.)

**When/why:** These bones do **not** exist in the vanilla skeleton; `ImportTxa.py`/`ExportTxa.py` reference them. Run it **BEFORE** importing/authoring any IK pose. If you import an IK `.txa` onto a rig without first running this tool, the importer prints `Ignoring survivor IK bone ... because Tools > Add Survivor IK Bones is required first!` and silently drops those bone tracks. **Do NOT** keyframe (or even add) these helpers for non-IK (full-body/additive) anims — stray keys corrupt full-body/additive exports, and both the exporter and `GenerateModelCfg` explicitly skip them. (`ImportTxa.py:201-207`.)

The engine's `ikpose_*` config keys (single-source, sysrover Discord — **`[verify]` against `player_main.ast`**):
`ikpose_chainoffset=RightHandOrigin`, `ikpose_weaponoffset=RightHand_Dummy`, `ikpose_secchainoffset=LeftHandIKTarget`, `ikpose_chainmiddledir=RightForeArmDirection`, `ikpose_secchainmiddledir=LeftForeArmDirection`. (`answeroverflow.com/m/1079941206152319006`.)

The plugin exports `LeftHandIKTarget` as a copy of `LeftHandOrigin` (extrapolated, not keyed in Blender). (`ExportTxa.py:444-448`.)

---

## 3. Importing a vanilla pose / anim as a base

### 3.1 Import procedure

1. **Select the armature first** (operator errors `Select an armature first!` otherwise).
2. **File > Import > DayZ Animation (.txa)** (operator `import_scene.txa`).
3. Options: **Scale Factor** (`fUnitScale`, default 1.0); **Translation/Rotation Keys** (default on); **Scale Keys** (default off — DayZ ignores scale).

The importer forces all bones to QUATERNION rotation, sets scene FPS and frame range from the file, disables IK constraints during import then re-enables, and stores the action with `use_fake_user`. Multiple selected files import as separate actions (previous action pushed to an NLA strip). (`ImportTxa.py`.)

### 3.2 Choose the closest vanilla base ("copy the anim closest in feel")

This is the **explicit recommended starting method**.

- **IK grip:** start from the bundled idle pose nearest the target, e.g. `Poses/Rifle/Rifle_Erect_Idle_Ras (Soft_Aim).txa` (soft-aim = the natural reload start), `Pistol_Erect_Idle_Ras` for pistols.
- **Reload/fire:** base timing/feel on the nearest vanilla action.

Bundled IK base poses cover **Rifle / Pistol / 1-Handed / 2-Handed / Heavy / Ladder / Spear / Unarmed / Surrender_Restrained**, each with Erect/Crouched/Prone Idle, `Idle_Low` and `Idle_Ras (Soft_Aim)` variants. IK sample blends: `Poses/Rifle/M4 Rifle IK.blend`, `Poses/Pistol/Pistol_IK.blend`, `Poses/2_Handed/Shovel_IK.blend`, `Poses/Heavy/SeaChest_IK.blend`, `Poses/1_Handed/Apple_IK.blend`. (`_AssetSamples/Poses/**`; Yrh2ZIqAaOs transcript.)

### 3.3 Attach the weapon model for visual reference (standard, optional)

To author against the actual gun:
1. In **Object Builder**, split the p3d's moving parts (body, bolt, trigger, magazine, mag_release, bullet) each into its own blank LOD; export each as **FBX** with **"export current LOD only"**, **UNCHECK** normals, **Master Scale 100**.
2. Import each FBX into Blender. Before constraining, set object rotation **X=0, Z=90** (the part default rotation X is 90).
3. For each part add an **Object > Child Of** constraint targeting the armature, **subtarget = the matching weapon bone** (`Weapon_Bolt`, `Weapon_Trigger`, …).

The weapon bones float in front of the right chest by default; the whole weapon is a child of `RightHand_Dummy`. (Yrh2ZIqAaOs transcript; corroborated 1n0vGup-QlM.)

---

## 4. The authoring craft, per animation type

General invariants:
- **Default FPS = 30** (engine default). Set **"Override Fps" = 30** in the exporter (0 = use scene FPS); use **20-25** for a slower deliberate feel; 60 is also valid. (`ExportTxa.py:102-107,308-311`; transcript.)
- **DayZ ignores bone SCALE** — never key scale; Scale Keys default off on both import and export. (`ExportTxa.py:97-101`.)
- Legs/feet are left to **locomotion**: idle/aim poses key the leg chain only as the static idle; reload/fire/state additives key **shoulders-down** (the Survivor reload bone list `SURVIVOR_RL_ANIM_BONES` contains **zero** leg bones). (`Txa.py:33-105`.)

### 4.1 The IK / grip pose (ikpose)

Keyframe **four** controls (insert keys with `I > "Only Selected Channels"`):

| Control | Role |
|---|---|
| `LeftHandOrigin` | support-hand position (child of `RightHand_Dummy`, so it tracks the weapon) |
| `RightHandOrigin` | whole-grip position/rotation relative to the shoulder |
| `LeftForeArmDirection` | LEFT elbow / pole direction (the "elbow control") |
| `RightForeArmDirection` | RIGHT elbow / pole direction |

**Geometric grip truth (VERIFIED, SR-2M 2026-06-17):** rotating `LeftHand` / the IK helpers does **NOT** reorient the support wrist in-game — the IK realigns the hand to the weapon, absorbing wrist rotation. The ikpose visibly drives **finger curl**, not wrist orientation. To truly change support-hand **orientation** (e.g. horizontal → vertical foregrip), rotate the **raw `LeftHand` bone + finger bones**, or pursue **weapon geometry parity** (the grip is positioned by the weapon's bore/handguard relation to the model origin). (`weapon-in-hands.md:90-105`.)

**Export type:** `Survivor IK 2h` (`IK2H`) or `Survivor IK 1h` (`IK1H`). The plugin auto-restricts to the survivor-IK bone list, writes a **single-keyframe pose**, and clamps `frameEnd` to 1 — do **not** pre-select bones and do **not** treat it like a multi-frame anim. (`ExportTxa.py:11-18,174-189,390-404`.)

### 4.2 The eye / ADS (aim-down-sights) line

The ADS camera is anchored by the **weapon p3d's `eye` memory point** (AKM ~5.2 cm above bore on the bore Z). ADS alignment is driven by **weapon geometry + the ikpose**, **not** by leg/locomotion bones.

Critical p3d invariants (VERIFIED-vanilla AKM):
- `usti hlavne` and `konec hlavne` share Y/Z (level bore line).
- `bolt_axis` parallel to bore.

If iron sights look canted, fix the weapon's frame/buttstock angle and eye/bore line — **not** the leg bones. (`weapon-in-hands.md:23-56`.)

### 4.3 Fire anim (additive, ~7 frames @ 30 fps)

- Keyframe **only what moves** — typically the **right index finger** and **`Weapon_Bolt`**.
- **ALWAYS start with the trigger already depressed on frame 0.**
- Drive `Weapon_Bolt` translation out-and-back over the frames (SVD sample: `0, 0.031, 0.090, 0.121, 0.081, 0.040` along X).
- Add the **bullet-eject event** (`#event 1 "Weapon_BulletEject"` in the SVD sample).
- Belt-fed (M249) belt motion goes here too.

(`JD_SVD_Fire.txa`, 7 frames; transcript.)

### 4.4 Weapon states (`w_<name>_states`, exactly 3 frames, additive)

The three weapon conditions — the **only** ones — are:

| Frame | State |
|---|---|
| 0 | bolt **closed** |
| 1 | bolt **open** |
| 2 | **jammed** |

- Only `Weapon_*` bones matter; the rest of the body is irrelevant. Use the **"weapon bones" preselection** group.
- In Blender set **end-on-frame 2** (NOT frame 1) or you only get 2 frames and the jammed/open states break.
- Export **Type = `ADD` (Additive) + "Selected Bones Only" + 30 fps**.
- Each frame = one weapon init state, set at runtime via `proto native void SetInitState(int pFrameIndex)`. (`human.c:1081-1088`.)

(`w_JD_SVD_states.txa` = 3 frames: `Weapon_Bolt` frame0 closed / frame1 t=0.121 open / frame2 t=0.035 jammed; transcript.)

> `[verify]` Whether the states `.anm` must always be exactly 3 frames or can have more init states per weapon is not exhaustively verified against every vanilla binary `w_*_states.anm`; `human.c` only says "each frame = one init state". The 3-frame convention is from the transcript + SVD sample.

### 4.5 Reload / charge / chamber / jam (additive, shoulders-down)

- Keyframe `Spine`/`Spine1-3`/`Neck`/`Head` micro-rotations + both arms + hands + the relevant `Weapon_*` parts. Don't neglect the spine/neck/head micro-rotations — they add humanlike fluidity.
- The `ADD` export writes **only** bones that have keyframes (true additive); unkeyed bones are omitted. (`ExportTxa.py:427`.)
- Use **"visual location/rotation"** keying when a bone is constraint-driven.
- **The "additive" framing is an AUTHORING convention, not a graph node.** Reloads in vanilla use dedicated `CMD_Reload_*` commands without an additive flag (`CMD_Modifier_Additive` drives sickness/cough/sneeze, not reload). "Reload is additive (shoulders down)" means *only animate torso/arms and export selected-bones-only additive*. (`anim-graph.md:127-135`.)

**Naming caveat:** `ReloadMagazineDetach` maps to a `*_mag_remove_*.anm`, but that vanilla anim does **NOT** actually remove a magazine — it is the **hand-from-hip return motion** (`[verify]`, transcript single-source). `FireCocked` = fire while cocked. "Bullet in chamber" is not a state; chambering is command-driven. (`player_main_1911.asi:21`; transcript.)

### 4.6 Magazine attach/detach tracking (no mag bone)

There are no dedicated magazine bones; fake the tracking:
1. Duplicate `LeftHand` in edit mode (e.g. `LeftHandMagTrack`), parent it to `LeftHand`, position it where the hand grips the mag.
2. On `Weapon_Magazine` add bone-constraints **Copy Location + Copy Rotation** of that tracker.
3. Key the constraints on/off across the reach frames using **"visual location/rotation"** (not plain Loc/Rot, or it snaps when constraints toggle).
4. **Bake** (Pose > Animation > Bake Action, **Visual Keying + Clean Curves**) to de-jitter.

The engine itself tracks mag position via `LeftHand_Dummy`. (`player-skeleton.md:39`; transcript.)

### 4.7 The "Survivor Reload" (RL) export type

`RL` exists in code (`SURVIVOR_RL_ANIM_BONES`) but the plugin author cannot tell its in-engine effect apart from plain `ADD` and uses `ADD`. **`[verify]`** — treat reloads as plain Additive until a discrepancy appears.

### 4.8 Aim-space (raise-while-aiming, bow draw)

**Unsolved by the plugin.** Editing aim-space (the additive look-direction grid used by bows/repeaters) turns the character into a floating meatball. Do **not** attempt aim-space authoring with this tool yet. (transcript; gotchas.)

### 4.9 Per-grip animation swap (foregrip)

The ikpose is registered **once** at register-callback time and cannot be re-evaluated per-attachment at runtime. To swap pose for a foregrip, register a **different `.asi`/IK conditionally** in the callback, e.g. branch on `weapon.withGrip` with two `AddItemInHandsProfileIK` calls. (`answeroverflow.com/m/917810289293029407` — **`[verify]`**, community technique.)

---

## 5. Export `.txa` + Events

### 5.1 Export the animation

**File > Export > DayZ Animation (.txa)** (operator `export_scene.txa`). Set the **Type** (`eAnimType`):

| Type | Code | Use |
|---|---|---|
| Full Body | `FB` | emotes only (injects a `Scene_Root` root bone) |
| Survivor IK 1h | `IK1H` | one-handed grip ikpose |
| Survivor IK 2h | `IK2H` | two-handed grip ikpose |
| Survivor Reload | `RL` | rarely — author treats reloads as `ADD` |
| Additive | `ADD` | reload/charge/fire/w_states |

(`ExportTxa.py:11-18`.)

**Workflow rules (hard):**
- **IK export:** use `IK1H`/`IK2H` and **do NOT** pre-select bones (the IK type auto-restricts to the survivor-IK bone list).
- **Reload/fire/states export:** use `ADD` + **"Selected Bones Only"** with only the relevant bones selected.
- Exporting **ALL** bones on a reload makes the character **"turn into a meatball"** in-game (head gone, body distorted). Full-body is only for emotes. (transcript; `ExportTxa.py:163-169`.)
- Bones ending in **`ik_helper`** are always skipped on export. (`ExportTxa.py:160-161`.)

### 5.2 Edit Events (N-panel Event Manager)

3D viewport sidebar (**N**) → **"Dayz Animation Tools" > "Events"**:
- **Load** reads existing events (stored as Blender pose markers named `Type|Args|ID`).
- **Add/Remove**; set **Frame, Type, Args, ID**; **Save** writes them back as pose markers.
- Events carry **sound IDs** (mapped to `AnimEvents > SoundWeapon` class ids in the weapon `config.cpp`) and — **critically — weapon-state changes** (bullet in chamber, weapon cocked). The state-change events are **mandatory even if all sound events are absent**.
- On export, markers become `$events { #event <frame> "Name" "Args" <ID> }` in the `.txa`. (`EventManager.py:99-156`; `ImportTxa.py:356-359`; transcript.)

### 5.3 The `.txa` text format (verified, for round-trip understanding)

```
$animation "name" {
  #fps 30
  #numFrames N
  $node "BoneName" {
    $keys t q s {
      $frame start [end] { #t x y z  #q x y z w }
    }
    $node ...nested by hierarchy...
  }
  $events { #event <frame> "EventName" "userStr" <int> }
}
```

Player arm/finger bones and weapon bones both appear as `$node` entries. (`JD_SVD_Fire.txa:1-389`; `w_JD_SVD_states.txa`.)

### 5.4 Coordinate conventions baked into the plugin (two distinct transforms — do not conflate)

1. **Axis fix (`mtxFix`)** — `Matrix(((0,1,0,0),(-1,0,0,0),(0,0,1,0),(0,0,0,1)))` = a **+90° rotation about Z that swaps Blender's X/Y axes** (NOT a Y-Z swap). Applied identically in `ImportTxa.py`, `ExportTxa.py`, `ExportTxo.py`. (`ImportTxa.py:141`; `ExportTxa.py:194,228`.)
2. **`.txa` text-level component swap** — translation/scale write as **X Z Y** (`FVector.GetSwapYZ`); quaternion writes as **(x, z, y, -w)** (`TxaKeyframe.Write`); reads mirror this (W negated). The export also applies a final `FQuaternion(-w,-x,-y,-z)`. (`Txa.py:480-496,550-566`; `DayzAnimUtils.py:35-39`; `ExportTxa.py:250`.)

Conflating these (or assuming a simple Y-Z swap) produces wrong rotations. Round-tripping outside the plugin needs both. **Unit scale:** `fUnitScale` default 1.0; the demo uses 1.0 — assume 1.0 until a discrepancy appears (**`[verify]`** against vanilla).

### 5.5 Export `.txo` (skeleton/object — for custom skeletons, usually NOT needed for player weapons)

**File > Export > DayZ Object (.txo)** (operator `export_scene.txo`). Used for a custom skeleton (creatures/zombies) plus optional mesh+weights. Options: Scale Factor; Selection/Showing Only; **"Auto Create EntityPosition"**; **"Auto Create HeadLook"** (HeadLook Bone default `pin_lookat`, use `lookat` for vanilla infected; HeadLook Parent default `head`; offset default `0, 0.25, 0`). Warns on >4 weights/vertex (DayZ max 4). Registered in Workbench as a `.xob`. Player-weapon anims reuse the vanilla `OFP2_ManSkeleton`, so this step is normally skipped. (`ExportTxo.py`.)

---

## 6. Workbench compile `.txa → .anm`

### 6.1 Compile procedure

In the Workbench **Resource Browser**, navigate to the `.txa`, **right-click** it:
- **First time:** **"Register resource and import"** (a.k.a. "Register Resource & Import").
- **Subsequent edits:** **"Reimport Resource"**.

This produces the binary **`.anm`** next to the `.txa` plus a **`.anm.meta`** sidecar — a `MetaFileClass` with a `{GUID}` Name and per-platform `TXAResourceClass` entries (PC / XBOX_ONE / PS4 / LINUX) referencing `SourceFile`. (`JD_SVD_Fire.anm.meta:1-16`; transcript; `answeroverflow.com/m/1079842895571456101`.)

For a `.txo`: same mechanism — right-click → "Register resource and import", choose **"As Model"** (vs "As Animation"); for a custom skeleton tick **"Export Skinning"** in the right panel, reimport, and paste the generated entry into `DZ/Anims/cfg/skeletons.anim.xml`. (`answeroverflow.com/m/910458080960086047`.)

### 6.2 Compile-time gotchas (silent data loss)

- **Workbench silently TRIMS near-identical consecutive keyframes** (frames whose delta is small are dropped) — your `.anm` can have fewer frames than authored, and "hold" poses can collapse. No documented "force all frames" option. Author with meaningful keyframe deltas. (`answeroverflow.com/m/1262609766635802705`, sysrover — **`[verify]`**, single-source; corroborated by `ExportTxa.py:358-385` skip-when-NearlyEquals.)
- **Scale is IGNORED on binarize** — appears in `.txa`, dropped in `.anm`. (`answeroverflow.com/m/1027718061819699222`, MarioE — **`[verify]`**.)
- After registering a **brand-new** resource type/path, **RESTART Workbench** if it doesn't appear. (`answeroverflow.com/m/582179174588874752`.)
- **ALWAYS keep the source `.txa` next to every `.anm`.** Workbench can only re-edit an `.anm` if its `.txa` is present; otherwise you need Mikero's DeAnm just to touch events. (`answeroverflow.com/m/781549585607950388`, MarioE.)
- File patching does **NOT** pick up `.anm` changes — you **must repack the PBO** (see §8).
- The "Enable net API (for communication with external applications)" Workbench setting is the **Enfusion Blender Tools** live bridge and is **NOT** used by this plugin (a pure on-disk file writer; grep of the plugin found zero socket/http usage). Do not conflate the two. (`ExportTxa.py:464-467`; `community.bohemia.net/wiki/Arma_Reforger:Enfusion_Blender_Tools`.)

### 6.3 Inspecting the player graph (read-only, local only)

The Workbench Animation Editor was historically crash-prone (`status access violation` on new group; `Error openning workspace`; `no TXA file found` editing vanilla `DZ\Anims`). Budget for editor instability. (`feedback.bistudio.com/T134639`.)

To inspect (never ship) vanilla states: open a **copy** of `player_main.aw`, delete the `#eventtable` line (`player_main.aw:136` of 138), open in the editor, double-click Master Control in Sheets, right-click → set node default running / run master control, Play; use Debug Controls to fire `fire`, `chambering`, `reloads`. **Never ship a debinarized/edited vanilla `.aw`/`.p3d`/`.anm`** — that is against BI Workshop rules and gets you removed. (`player_main.aw:136`; transcript; `anim-graph.md:137-147`.)

---

## 7. `config.cpp` / `model.cfg` / ASI wiring into the anim graph

### 7.1 The single biggest trap

**`config.cpp` does NOT carry the player-character weapon-animation association.** Newcomers expect a config key; the wiring is **100% in Enforce Script** (`AddItemInHandsProfileIK` in `ModItemRegisterCallbacks.RegisterFireArms`). The weapon `config.cpp` only defines the item. (`ModItemRegisterCallbacks.c:3-7`.)

### 7.2 The `.asi` (AnimSetInstance) — the hub

A **text** file, one per weapon. Author/point it like `JD_Demo_SVD.asi`:

```
$animsetinstance {
  #template "DZ/anims/workspaces/player/player_main/player_main.ast"
  #nparents 1
  #parent "DZ/anims/workspaces/player/player_main/player_main_rifle.asi"
  #ikpose "<Mod>/Animations/<Wpn>/JD_SVD_IK.anm"
  $animations {
    "WeaponOperations.ErcRas.Fire"               "<...>/p_erc_fire_SVD_ras.anm"
    "WeaponOperations.ErcRas.ReloadMagazineDetach" "<...>/p_erc_reload_mag_remove_SVD_ras.anm"
    "WeaponOperations.ErcRas.Chambering_Closed"  "<...>.anm"
    ... (the PneRas prone set too)
  }
}
```

- `#parent` chain: your `weapon.asi` → `player_main_rifle.asi` (or `_pistol`/`_2h`/`_1h`/`_heavy`) → `player_main.asi` (root, `#nparents 0`). (`JD_Demo_SVD.asi:1-62`; `player_main_akm.asi:1-6`.)
- **Copy the closest vanilla weapon's `.asi`** (rifle: clone an akm/m4a1-style; pistol: clone 1911-style). Different weapons declare **different state subsets** — the `.ast` lists the union of 42 legal slots; each `.asi` uses a subset. (`player_main_akm.asi:7-28` vs `player_main_1911.asi:6-39`.)
- **Strip the auto-generated `{GUID}` serial-number keys** from any copied vanilla `.asi`. DayZ does **not** need them (only Arma Reforger does); they cause problems and break editing in the Animation Editor. Workbench regenerates them on import. (transcript; gotchas.)

### 7.3 State vocabulary

State paths are `WeaponOperations.<RigKey>.<StateName>`. Only **TWO RigKeys** exist in vanilla: **`ErcRas`** (erect) and **`PneRas`** (prone), both carrying the `Ras` (rail-accessory / raised soft-aim) suffix. **There is no crouch RigKey** — crouch reuses `ErcRas`; stance is handled by the graph stance STM. Do not invent `WeaponOperations.CroRas`. (`player_main.ast:1228-1235`; grep over 80 weapon ASIs: 642 `ErcRas` / 638 `PneRas`, no others.)

The complete vanilla `WeaponOperations` set is the **42 `$anims`** in `player_main.ast:1236-1280`:
`ChamberingBulletL/R`, `ChamberingCancel`, `ChamberingFast_Closed/Open`, `ChamberingIn`, `ChamberingLook`, `ChamberingLoop(+1/_Closed_Bullet/_Closed_NoBullet/_Open_Bullet/_Open_NoBullet)`, `ChamberingOut`, `Chambering_Closed(_Uncocked)`, `Chambering_NoBulletL/R`, `Chambering_Open`, `Fire`, `FireCocked`, `FireEmptyAutomatic`, `FireJam`, `FireLast`, `FireUncocked`, `Jamming`, `'Jamming Cancel'` (literal space), `'Jamming Check'`, `Obstruction`, `ReloadAction_Closed(_Uncocked)/_Open`, `ReloadBoltAction2`, `ReloadClipInBullet/InNoBullet/Out/Pose`, `ReloadMagBullet`, `ReloadMagNoBullet`, `ReloadMagazineDetach`, `ReloadNoMagBullet`, `ReloadNoMagNoBullet`.

Keys are **exact, dotted, case-sensitive, stance-segmented**. A typo/missing key silently falls back to the vanilla anim (or breaks that operation). Note the literal space in `'Jamming Cancel'`. (`player_main.ast:1236-1280`; `JD_Demo_SVD.asi:23,32`.)

### 7.4 The `.ast` template (schema — copy, don't hand-author)

The `.ast` declares **27 `$groupType` blocks**; `WeaponOperations` is groupType #27 with `#ngroupnames 2` (`ErcRas,PneRas`) / `#nanims 42`. It is the schema that **legalizes** which state names an `.asi` may populate. The full grammar is undocumented — **copy-edit from the closest vanilla `.ast`**. (`player_main.ast:1-2,1228-1281`.)

### 7.5 Enforce Script registration (REQUIRED)

`Scripts/4_World/.../ModItemRegisterCallbacks.c`:

```c
modded class ModItemRegisterCallbacks {
  override void RegisterFireArms(DayZPlayerType pType, DayzPlayerItemBehaviorCfg pBehavior) {
    super.RegisterFireArms(pType, pBehavior);
    pType.AddItemInHandsProfileIK(
      "JD_SVD_Base",                                 // weapon *_Base class
      "JDsAnimationDemo/Animations/SVD/JD_Demo_SVD.asi",
      pBehavior,
      "JDsAnimationDemo/Animations/SVD/JD_SVD_IK.anm",
      "JDsAnimationDemo/Animations/SVD/w_JD_SVD_states.anm");
  }
  override void CustomBoneRemapping(DayZPlayerType pType) {
    super.CustomBoneRemapping(pType);
    pType.AddItemBoneRemap("JD_SVD_Base", {
      "bolt","Weapon_Bolt",
      "magazine","Weapon_Magazine",
      "trigger","Weapon_Trigger",
      "charging","Weapon_Bone_01",
      "bullet","Weapon_Bullet",
      "mag_release","Weapon_Bone_02",
      "boltrelease","Weapon_Bone_03"
    });
  }
}
```

Verified proto signatures (vanilla `dayzplayer.c`):
- `proto native int AddItemInHandsProfileIK(string pItemClass, string pAnimInstanceName, HumanItemBehaviorCfg pBehaviorCfg, string pIkPoseAnim, string pWeaponStates = "")` — `dayzplayer.c:243`. The 5th arg (weapon states) is present only for weapons; items use the 4-arg form with the generic `player_main_1h.asi`/`_2h.asi`/`_heavy.asi`.
- `proto native int AddItemBoneRemap(string pItemClass, array<string> pBoneRemap)` — `dayzplayer.c:245-252`; pairs are 2×N: "bone in item's P3D first, bone in Character skeleton second".

Register against the **`*_Base`** class so all variants inherit and the call count stays low. (`ModItemRegisterCallbacks.c:7,12-33`; `dayzplayercfgbase.c:382,411`.)

**Bone-remap contract:** first column = the **p3d/model.cfg selection name**, second column = the **player-skeleton `Weapon_*` bone**. Standard slots: `Weapon_Bolt`, `Weapon_Magazine`, `Weapon_Trigger`, `Weapon_Bullet`; non-standard parts use `Weapon_Bone_01..06`. **Skipping the remap is why bolt/mag/trigger don't animate.** A mismatch silently drops that part's motion.

**Limitation:** `AddItemBoneRemap` works for **WEAPON** base classes only — **not** for non-weapon items (medical etc.), even pointing at a free `Weapon_Bone`. The only non-weapon hand anchors are `RightHand_Dummy` (item) and possibly `LeftHand_Dummy` via constraints. (transcript; open BI ticket.)

Alternate (older) registration: `GetDayZPlayerType().AddItemInHandsProfileIK(...)` inside a modded `PlayerBase.Init()`, guarded by `if (!GetGame().IsServer() || !GetGame().IsMultiplayer())` so it runs client-side. The `ModItemRegisterCallbacks` override is the cleaner/canonical route. (`answeroverflow.com/m/574191434396073985,/m/925299889469018112`.)

**Full item-in-hands API catalogue — all by classname, zero per-instance [VERIFIED-vanilla `dayzplayer.c:225-252`]:**
`SetDefaultItemInHandsProfile(asi, behavior)` (:225, global default), `ResetItemInHandsProfiles()` (:229,
global reset), `AddItemInHandsProfile(itemClass, asi, behavior)` (:240, no IK),
`AddItemInHandsProfileIK(itemClass, asi, behavior, ikpose, weaponStates="")` (:243),
`AddItemBoneRemap(itemClass, pairs[])` (:252). Every signature takes a `string pItemClass` or is global —
none takes a weapon instance or a `DayZPlayer`. Registration runs in `DayZPlayerTypeRegisterItems()` →
`RegisterFireArms()` ONCE when the `DayZPlayerType` initializes (`dayzplayercfgbase.c:334,382`), not per
equipped weapon nor reactive to attach/detach. Consequence: there is no supported "based on the attachment
in the slot → pose A/B/fallback". The "fallback" that DOES exist is by CLASS HIERARCHY (register on
`*_Base`, override in the subclass), root `Inventory_Base`→`apple.anm` (`dayzplayercfgbase.c:373`) — the
condition is the classname, not attachment presence. `ResetItemInHandsProfiles()`+re-add is global to the
player type (affects all), not per-instance.

### 7.6 How the engine selects which state/RigKey plays

Driven by the player combat/weapons graph, not by you:
- RigKey: `'WeaponStanceErc'` → `WeaponFireSTM("WeaponOperations","ErcRas")`; `'WeaponStancePne'` → `("WeaponOperations","PneRas")`. (`combat.agr:850,881,909`.)
- Fire dispatch: `CMD_WeaponFire == 2` selects `FireCocked`. (`combat.agr:787-827`.)
- Weapon-operation `CMD_*` commands: from `weapons.agr` — `CMD_Reload_Magazine`, `CMD_Reload_BoltAction`, `CMD_Reload_Chambering`, `CMD_Reload_ChamberingFast`, `CMD_Reload_Clip`, `CMD_Reload_Exit`, `CMD_Weapon_Jam`; from `combat.agr` — `CMD_WeaponFire`. Casing is exactly `CMD_` + Mixed_Snake. (`weapons.agr`, `combat.agr`.)

> `[verify]` The precise runtime trigger for each individual `WeaponOperations.<State>` (which `CMD_`/FSM transition fires `ReloadAction_Closed` vs `_Open` vs `ReloadMagBullet`) lives in `weapons.agr` but was not traced state-by-state. **Copy the transition wiring from the closest vanilla weapon graph.**

### 7.7 The weapon's own `model.cfg` (separate from the player skeleton)

The weapon `model.cfg`/`.cfg` defines the **weapon's own small skeleton** (the selections the bone-remap first column points at). Two different "skeleton" worlds — **do not confuse them**: (a) the WEAPON's tiny skeleton (`bolt/trigger/magazine` in `SVD.cfg`); (b) the PLAYER skeleton `OFP2_ManSkeleton` (in `DZ/Anims/cfg/skeletons.anim.xml`). The `.anm` animates PLAYER bones; `AddItemBoneRemap` bridges weapon selections → player bones.

```
class CfgSkeletons {
  class svd {
    skeletonInherit="";
    isDiscrete=1;
    SkeletonBones[]={ "magazine","", "trigger","", "bolt","", "firemode","", "bullet","", "mag_release","" };
  };
};
class CfgModels {
  class svd : Default {
    skeletonName="svd";
    sections[]={ "magazine", "camo...", "zbytek", "bullet", ... };
  };
};
```

(`SVD.cfg:1-39`; community sample `Thurston00/.../sample_shotgun/model.cfg`.)

The plugin's **Tools > "Generate DayZ Model Config (model.cfg)"** (`export_scene.modelcfg`) emits exactly this `CfgSkeletons` + `CfgModels` stub from a selected armature (`isDiscrete=0`, `skeletonInherit=""`, per-bone name+parent; a `CfgModels` `P3dFilenameNoExtension` class to rename). It **skips** helper bones (`scene_root`, `entityposition`, `righthandorigin`, `righthand_dummy`, `rightforearmdirection`, `lefthandorigin`, `lefthand_dummy`, `leftforearmdirection`, case-insensitive). Primarily for custom skeletons (creatures), **not** for player weapon anims (which reuse vanilla `OFP2_ManSkeleton`). Note the `*_Dummy`/`Direction` bones are **skipped in `CfgSkeletons`** yet **DO** appear as animated `$node` entries in the `.txa` — "skip in CfgSkeletons" ≠ "don't animate". (`GenerateModelCfg.py:40-116`.)

### 7.8 The weapon's `config.cpp` item class (does NOT reference the anim)

`Firearms/<Wpn>/config.cpp` carries `model`, `magazines[]`, `chamberableFrom[]`, `modes[]`, `reloadAction`, `class AnimEvents { class SoundWeapon {…} }`, `class OpticsInfo` — but **NO** reference to the `.anm`/`.asi`. The `*_Base` extends `Rifle_Base`; the script class extends `RifleBoltLock_Base` for engine behavior. (`Firearms/SVD/config.cpp:18-364`; `SVD.c:1-2`.)

**`reloadAction` is the LEGACY gesture system** (`CfgMovesMaleSdr` → `CfgGesturesMale`), distinct from the new `.asi`/`AddItemInHandsProfileIK` path. The demo sets `reloadAction="ReloadSVD"` yet its real reload anims come through the `.asi`. Do **not** assume `reloadAction` drives your custom `.anm`. (`[verify]` whether `reloadAction` must be a real class when the `.asi` system is in use.) (`community.bistudio.com/wiki/CfgMoves_Config_Reference` — **`[verify]`**, 403 to fetch.)

### 7.9 Mod scaffolding (CfgMods + per-PBO CfgPatches)

Folder layout (one top-level folder per PBO; the demo has three):

```
<Mod>/
  Animations/   <- .asi + .txa/.anm/.anm.meta per weapon; config.cpp (CfgPatches <Mod>_Animations)
  Firearms/     <- weapon .p3d, .cfg (weapon skeleton), textures, config.cpp (CfgPatches <Mod>_Firearms)
  Scripts/      <- config.cpp (CfgPatches <Mod>_Scripts + CfgMods) + the .c callback files
  Workbench/    <- dayz.gproj, project.cfg, build.bin, launch.bin, server.cfg
```

No `$PBOPREFIX$` files exist in the gproj source tree — the prefix is the folder name at pack time. If packing manually with AddonBuilder you must add a `$PBOPREFIX$` per folder. (`Animations/config.cpp`, `Firearms/config.cpp`, `Scripts/config.cpp`.)

**`Scripts/config.cpp`** (mod entry point):
```
class CfgPatches { class <Mod>_Scripts { requiredVersion=0.1; requiredAddons[]={"DZ_Scripts"}; }; };
class CfgMods {
  class DZ_<Mod> {
    type="mod"; dir="<Mod>"; dependencies[]={"Game","World","Mission"};
    class defs {
      class worldScriptModule  { files[]={"<Mod>/Scripts/4_World"}; };
      // + engineScriptModule (1_core), gameScriptModule (3_Game), missionScriptModule (5_Mission)
    };
  };
};
```
(`Scripts/config.cpp:1-69`.)

**Per-PBO `CfgPatches` requiredAddons:**
- `<Mod>_Animations` → `DZ_Anims_Anm_Player`, `DZ_Anims_Cfg`, `DZ_Data`, `DZ_Scripts` (so the vanilla anm tree/configs are available). (`Animations/config.cpp:1-16`.)
- `<Mod>_Firearms` → `DZ_Weapons_Firearms` (+ magazines/muzzles/optics/launchers). 
- `<Mod>_Scripts` → `DZ_Scripts`.

**`inputs.xml` (OPTIONAL):** the demo ships an **empty** `<modded_inputs>` stub — reload/fire/chamber reuse vanilla operations, so **no** new inputs are needed. Required **only** for a brand-new bindable action (e.g. a custom "inspect" action; **`[verify]`** — unverified path). (`Scripts/Inputs.xml:1-12`.)

**`stringtable.csv` (OPTIONAL):** demo ships only the header row; used only for localized `displayName`/`description`. (`Scripts/stringtable.csv:1`.)

### 7.10 The Workbench project (`dayz.gproj`)

Declares: Workdrive FileSystem `Directory "P:/"`; `skeletonDefinitions "DZ/Anims/cfg/skeletons.anim.xml"` (where the player skeleton lives for Workbench); `imageSets`, `widgetStyles`; the 5 ScriptModules (1_Core..5_Mission) + a workbench ToolAddons module. `project.cfg` lists client/server Mods loaded for the run (demo: `@Dabs Framework;@CF;@Community-Online-Tools`). Build/launch from Workbench so `.txa → .anm` compilation happens. (`dayz.gproj:1-105`; `project.cfg:1-2`.)

---

## 8. Build / sign / deploy / in-game test

### 8.1 Build the PBO

**GUI (Addon Builder):**
- "Addon source directory" = the mod subfolder; "Destination directory" = `...\@Mod\addons\`.
- Options: "Path to project folder" = `P:\` (so cross-addon paths resolve); choose **Binarize** for config/p3d-bearing addons, leave **packonly** for script/anm/paa-only; "List of files to exclude" (demo ships an empty `exclude.lst`); Pack.
- Ensure a `$PBOPREFIX$` at the addon root declares the internal prefix.

**CLI / Workbench Build button:**
`AddonBuilder.exe <source> <dest> -prefix=<Prefix> -project=P:\ [-binarize | -packonly] [-clear] [-sign=<key.biprivatekey>] [-include=<list>]`. The Workbench `build.bin` invokes `...\DayZ Tools\Bin\AddonBuilder\AddonBuilder.exe`. (`build.bin` xxd; `community.bohemia.net/wiki/Addon_Builder`.)

**`-packonly` vs binarize:** use `-packonly` for `.c`/`.layout`/`.anm`/`.paa`/`.ogg`; binarize when `CfgVehicles`/p3d/TGA→PAA need conversion. Binarizing a script/anm-only addon is unnecessary and binarize can drop config-only-referenced textures; packonly on a p3d/config mod leaves MLOD/TGA unconverted. **Match the flag to the addon contents.** (`stardz-team.github.io/.../06-pbo-packing`.)

### 8.2 Sign (optional for local filepatching tests)

DSUtils chain:
1. `Bin\DsUtils\DSCreateKey.exe MyModKey` → `MyModKey.biprivatekey` (secret) + `MyModKey.bikey` (public).
2. Sign via Addon Builder ("Create signature" / `-sign=...biprivatekey`) or `DSSignFile.exe` → `<Mod>.pbo.MyModKey.bisign`.
3. Optionally verify with `DSCheckSignatures.exe`.

Use **lowercase** `addons/` and `keys/` folder + file names for Linux-server compatibility. Server admins drop the public `.bikey` into the server `keys\` folder when `verifySignatures` is on. (`dayz-launcher.com/dayz-tools-modder-knowledge-base.php` — **`[verify]`** exact CLI args.)

### 8.3 Deploy

Place `@Mod\addons\*.pbo` + `@Mod\keys\MyModKey.bikey` under the DayZ install (or the local harness `P:\Mods` junction → `DayZ\!Workshop`). (`launch.bin` references `P:\Profiles`, `P:\Missions`, `P:\Mods`, `ChernarusPlus`.)

### 8.4 In-game test loop

- Local server `serverDZ.cfg`: **`allowFilePatching=1`**, **`verifySignatures=0`**, BattlEye off. (`server.cfg:11-12`.)
- Launch with `DayZDiag_x64.exe -mod=@Mod` (+ the Mods from `project.cfg`); from Workbench use **F6** to launch / **F10** to kill.
- **Critical:** filepatching loads loose `.c`/`.layout` but **does NOT reload `.anm` changes** — you must **repack the PBO** and Reimport in Workbench. Forgetting this makes edits appear to do nothing. The loop is: edit in Blender → export `.txa` → Workbench "Reimport Resource" → **repack PBO** → reconnect → trigger the weapon state.
- Test sequence: spawn weapon + mag + ammo; chamber a bullet (no parts move when chambering); attach optic/suppressor (they stay put); look down sights (iron-sight level); reload (mag tracks); fire (bolt cycles); then the **elbow stress tests** below.

### 8.5 The elbow tuning gate (the only true gate)

The Blender IK constraint `pole_angle` on `LeftHand`/`RightHand` is a **Blender-preview-only** tuning value — it is **NOT exported**; only the resulting pose exports. Elbow correctness can **only** be confirmed **in-game**. The `ForeArmDirection` bone **position** dictates elbow pop-out. Tune `pole_angle` + ForeArmDirection position, re-export, Reimport, **repack**, retest. Failure tests (elbow error is angle-dependent — looks fine head-on but collapses inside the ribcage otherwise):
1. **Lean-left + look-down** (left elbow must stay out of the ribcage),
2. **Crouch**,
3. **Throw** (tap **G**).

The plugin's IK is reverse-engineered and only ~90-95% accurate vs the engine; expect iteration. (transcript; gotchas.)

---

## 9. Walls, gotchas, and failure-mode catalog

### 9.1 Hard walls (architectural)

| Wall | Detail | Source |
|---|---|---|
| **Bone names exact** | Mismatch → RPT `Bone X doesn't exist in skeleton OFP2_ManSkeleton`, bone silently dead. Skeleton overlay-only, cannot restructure. | `tooling-and-walls.md:34` |
| **One graph-mod at a time** | Two mods that modify the player/creature anim **graph** (`.agr`, e.g. Expansion-Animations) cannot coexist — crash. **Does NOT apply** to the ASI/weapon route. | `answeroverflow.com/m/1090534919182233642` |
| **ASI route is conflict-free** | Multiple weapon-anim mods coexist (doesn't touch the main graph). **Vehicles are the exception** — ASI for vehicle rider/driver anims is not yet available (**`[verify]`**). | transcript |
| **No Python `.anm` writer** | `.anm` is proprietary — only Workbench or DayZATool write it. RTM has no open Python writer either. Sandbox can produce `.txa` (text) or SEAnim (open), never the binary `.anm`. | `tooling-and-walls.md:11-12` |
| **No bone-remap for non-weapons** | `AddItemBoneRemap` works for weapons only; medical/other items can't drive a `Weapon_Bone`. | transcript |
| **Dual-wielding infeasible** | Only one weapon is assigned to the player; other anims fight it. | gotchas |
| **Aim-space unsolved** | Editing aim-space (bows/repeaters) → floating meatball. | transcript |

### 9.2 Silent-data-loss / "looks done but isn't" failures

- **All-bones export → "meatball"** (head gone, body distorted). Always "Selected Bones Only" for IK/additives; full-body only for emotes.
- **Weapon-states not ending on frame 2** → only 2 of 3 frames, jammed/open break.
- **Workbench trims near-identical keyframes** (`[verify]`) — author meaningful deltas; "hold" poses can collapse.
- **Scale silently dropped on binarize** (`[verify]`) — never animate via bone scale.
- **`pole_angle` not exported** — Blender preview lies; verify elbow in-game.
- **Rotating `LeftHand`/IK helpers to fix wrist orientation is inert in-game** (IK realigns) — fix grip by weapon geometry parity.
- **Typo'd `.asi` state key silently falls back to vanilla** — exact, case-sensitive, stance-segmented; mind the literal space in `'Jamming Cancel'`.
- **Missing `AddItemBoneRemap`** → hand anim plays but bolt/mag/trigger dead.
- **Lost `.txa`** → can't re-edit the `.anm` (only DeAnm recovers events). Keep the `.txa` next to every `.anm`.
- **Filepatching doesn't reload `.anm`** → must repack the PBO.

### 9.3 Tooling traps

- **Stale README Blender version** — maintained fork needs 4.4+/5.x despite README's 3.6.8; `bl_info` says 2.80 (meaningless).
- **DayZATool rig is "always wrong"** for empties (IK helpers) and inverts local bone axes — use the Blender plugin for authoring, DayZATool only to extract references.
- **Do NOT round-trip FBX out of DayZATool back into XOB/ANM/TXA** in Workbench — it breaks.
- **`{GUID}` serials in copied `.asi`** must be stripped for DayZ.
- **Don't ship debinarized/edited vanilla `.aw`/`.p3d`/`.anm`** — Workshop-rule violation; the `#eventtable` trick is local-only.
- **Workbench Animation Editor historically crash-prone** (T134639) — budget for editor instability.
- **`magazine` tracking** needs "visual location/rotation" keying + bake, or it snaps.
- **Confusing the two "model.cfg/skeleton" worlds** (weapon skeleton vs player skeleton).
- **Confusing RTM vs `.txa`/.anm** — RTM is for legacy props, never for player weapons.
- **Confusing the Workbench "Enable net API" setting** — it's the Reforger Blender-Tools bridge, unused by this plugin.

### 9.4 Stacking / runtime

- **Stacking many `AddItemInHandsProfileIK` overrides can trigger a `ModItemRegisterCallbacks` stack overflow** on heavily-modded servers (`feedback.bistudio.com/T182404` — **`[verify]`**). Register on `*_Base` classes to minimize calls.
- **Registration must run in the right context** — guard `PlayerBase.Init` patterns with `if (!IsServer() || !IsMultiplayer())`, or use the `RegisterFireArms` override; wrong place silently no-ops.

### 9.5 Shipping artifacts (real, from JD's Animated Weapons)

Documented imperfections to expect/budget for: prone anims reusing standing/crouched poses (gun clips into ground); Serbu Super Shorty left-hand glitch when empty; M249 finger "noodle" at end of chamber. (Steam Workshop id 3297234994.)

---

## 10. End-to-end checklist

**Setup**
- [ ] Blender version matches the plugin fork (maintained = 4.4+/5.x; original = 3.6.8) — checked against `ImportTxa.py` API calls, not `bl_info`.
- [ ] `DayzAnimationTools` folder copied into `scripts/addons`, enabled in Preferences.
- [ ] DayZ Tools work drive = `P:\`; vanilla extracted; `SetupWorkdrive.bat` run.
- [ ] `dayz.gproj` opens in Workbench; `project.cfg` lists dependency mods.

**Author**
- [ ] Opened `JD_Master_Rig (No IK Bones).blend` (or an IK sample for grip work).
- [ ] For IK: ran **Tools > Add Survivor IK Bones** BEFORE importing/authoring.
- [ ] Imported the closest vanilla base pose/anim; attached weapon FBX via Child Of (optional).
- [ ] IK pose: keyed `LeftHandOrigin`, `RightHandOrigin`, `LeftForeArmDirection`, `RightForeArmDirection` only.
- [ ] Fire: ~7 frames, trigger depressed on frame 0, `Weapon_Bolt` cycle + eject event.
- [ ] Weapon-states: 3 frames (closed/open/jammed), end-on-frame 2, weapon bones only.
- [ ] Reload/charge/chamber/jam: shoulders-down, keyed bones only, spine micro-motion.
- [ ] HOLD-type action anim (unjam/continuous) -> `LoopStart`/`LoopEnd` notetracks present (SP-046 below).
- [ ] No keys on IK helpers for non-IK anims; no scale keys anywhere.
- [ ] Events set in the N-panel Event Manager (state-change events mandatory).

**Export + compile**
- [ ] `.txa` exported with the correct Type (IK1H/IK2H for grip; ADD + Selected Bones Only for the rest); FPS 30.
- [ ] Workbench: right-click `.txa` → Register/Reimport → `.anm` + `.anm.meta` produced (restart Workbench if a new resource doesn't appear).
- [ ] `.txa` kept next to every `.anm`.

**Wire**
- [ ] Per-weapon `.asi`: `#template player_main.ast`, `#parent player_main_rifle.asi`, `#ikpose`, `$animations` map (ErcRas + PneRas), `{GUID}` serials stripped.
- [ ] State keys exact/case-sensitive (mind `'Jamming Cancel'`).
- [ ] `ModItemRegisterCallbacks.RegisterFireArms` → `AddItemInHandsProfileIK(<Base>, asi, behavior, ik.anm, w_states.anm)`.
- [ ] `CustomBoneRemapping` → `AddItemBoneRemap(<Base>, {selection,Weapon_*,...})`.
- [ ] Weapon `.cfg`/model.cfg `CfgSkeletons` selections match the remap first column.
- [ ] `CfgMods` `worldScriptModule` → `4_World`; per-PBO `CfgPatches` requiredAddons set (Animations needs `DZ_Anims_Anm_Player`+`DZ_Anims_Cfg`+`DZ_Data`+`DZ_Scripts`).

**Build + test**
- [ ] PBO packed (`-packonly` for script/anm; binarize for p3d/config); `$PBOPREFIX$` present if manual.
- [ ] (Optional) signed; `.bikey` in `keys/`; lowercase folders for Linux.
- [ ] Deployed to `@Mod`; server `allowFilePatching=1`, `verifySignatures=0`, BE off.
- [ ] In-game: chamber / attach optic / ADS / reload / fire all correct.
- [ ] Elbow stress tests pass: lean-left+look-down, crouch, throw (G).
- [ ] After each `.anm` edit: Reimport + **repack PBO** before retest.

**Compatibility**
- [ ] If only adding per-weapon anims via `AddItemInHandsProfileIK` → conflict-free.
- [ ] If modifying the player anim graph (`.agr`) → mutually exclusive with all other graph mods.

---

## Open gaps / must verify against primary source

Aggregated from all seven dimensions. Every item below is **unverified or single-source** and must be confirmed against primary data before being relied on:

1. **Full ordered `OFP2_ManSkeleton` bone roster** — inferred from sample `.txa` + plugin code, not from opening the rig. Confirm by opening `JD_Master_Rig` or running `GenerateModelCfg` on it; also read the complete `Weapon_*` set from vanilla skeleton config (demo shows only `Weapon_Bolt/Magazine/Trigger/Bullet/Bone_01..03`).
2. **`ikpose_*` config keys** (`ikpose_chainoffset` etc.) — single Discord message (sysrover). Confirm against `DZ/anims/workspaces/player/player_main/player_main.ast` (or `.aw`) in unpacked vanilla.
3. **`AddItemInHandsProfileIK` / `AddItemBoneRemap` signatures** — verified in `dayzplayer.c:243,245-252`; cross-check still recommended for the exact param order across Tools versions.
4. **".txa must be packed in a PBO; filepatching doesn't work for anims"** — release-video only; not independently verified against BI docs or a repro.
5. **Minimum Blender for the maintained fork** — inferred from API calls (4.4+/5.1), not run on 3.6.8 to confirm failure.
6. **`Ras` == raised/soft-aim exactly** — inferred from filename + ASI state conventions; engine semantics of Ras vs non-Ras not read from BI docs.
7. **No BI primary page** for the DayZ `.asi`/`.ast`/`.anm` player weapon-animation workflow or `$animsetinstance` grammar was fetched (BI wiki 403s; only the Reforger tutorial surfaced). The `.ast`/`.asi` directive grammar and the **complete** legal `WeaponOperations.*` vocabulary are taken from the working demo + vanilla data only — additional valid operations (e.g. modeswitch) may exist.
8. **Player anim FPS** — not declared in any text file under `workspaces/`; engine default assumed 30. Round-trip test; confirm fpsOverride mismatches don't cause speed/scale issues.
9. **"Conflict-free ASI / vehicles-unsupported"** — release-stream + Workshop wording, not BI primary. (The complementary "graph mods conflict" wall IS corroborated.)
10. **`feedback.bistudio.com` tickets** T150316 (official IK/anim-instance API request), T134639 (Animation Editor bugs), T182404 (stack overflow), HunterZ vehicle-ASI ticket — all 403/unauthenticated; current resolution states unconfirmed.
11. **Weapon-states `.anm` always exactly 3 frames?** — convention from transcript/SVD only; not verified against every vanilla binary `w_*_states.anm`. `human.c` only says "each frame = one init state".
12. **Per-state runtime trigger mapping** (which `CMD_`/FSM transition fires `ReloadAction_Closed` vs `_Open` vs `ReloadMagBullet`) — lives in `weapons.agr` but not traced state-by-state. Copy the closest vanilla weapon graph.
13. **Workbench keyframe-trimming + "force all frames" option** — single-contributor Discord claim (sysrover), no maintainer reply.
14. **Scale ignored on binarize** — single-author Discord (MarioE), not a BI repro (though plugin default `bExportScaleKeys=False` corroborates intent).
15. **`.asi` blends on top of `w_states.anm`** — Discord (MarioE), not a BI primary doc (corroborated by demo structure).
16. **`reloadAction` semantics under the `.asi` system** — whether it must be a real `CfgMovesMaleSdr` class or can be a dummy/inherited value is unconfirmed against vanilla.
17. **"Since 0.63 all weapon animation is character-side, not model.cfg"** — single 2020 Discord message.
18. **`DZ_Anims_Anm_Player` / `DZ_Anims_Cfg` as vanilla `CfgPatches`** — corroborated only by web summary + the demo's requiredAddons, not by reading vanilla `config.bin`.
19. **"Survivor Reload" (RL) vs plain Additive** — the plugin author can't tell them apart; in-engine difference untested.
20. **`ReloadMagazineDetach` is the hand-from-hip return (not an actual mag removal)** — transcript single-source.
21. **Per-grip ASI swap (foregrip branch)** — community technique (`answeroverflow.com/m/917810289293029407`), not verified.
22. **Reload/charge/chamber/jam frame-range conventions** — the demo ships those as `.anm` only (no `.txa`), so per-state frame counts beyond fire(7)/states(3) are not primary-verified.
23. **`Weapon_Bone_01..06` semantics per weapon family** — configurable, not standardized; only the SVD mapping (`charging`/`mag_release`/`boltrelease`) is confirmed.
24. **Whether a new `inputs.xml` action is ever needed for a weapon-only anim** (e.g. custom "inspect") — demo proves NOT needed for reload/fire/chamber; the inspect path is untested.
25. **Blender→DayZ unit/scale factor for translations** — `fUnitScale` default 1.0; demo uses 1.0; not independently confirmed against vanilla.
26. **Whether ADD additive player anims escape the "one graph mod" wall** — unconfirmed; needs in-game test.
27. **Exact current Workbench Resource-Browser menu wording** ("Register resource and import" vs "Register & Import") — from 2019-2023 community posts; confirm the live label per Tools version.
28. **No quantified perf/FPS data** on custom weapon anims (keyframe budgets, cost of many `AddItemInHandsProfileIK` registrations) — inferred, not measured.
29. **No confirmed RPT error-string catalog** for a bad weapon `.anm` (missing remapped bone, 404 `.anm`/`.asi` path) — needs a DayZDiag repro.
30. **DSUtils signing CLI exact argument syntax** — not run here; confirm against installed `Bin\DsUtils` binaries' `--help`.

---

## [2026-06-28] Verified gap resolutions (weapon-anim pipeline)

Resolved from the WeaponAnimPipeline gap pass against vanilla primary data + the JD demo + the maintained plugin. Confidence markers: [VERIFIED-vanilla] = file read in `DZ/`; [verify] = in-game-gated or single-source.

### Vanilla AKM player weapon-anim frame budget [VERIFIED-vanilla]

All 8 vanilla AKM `.anm` files extracted to SEAnim via DayZATool v1.3 and read with `seanim_writer.read_seanim`. **Every one runs at framerate = 30.000 fps** (FPS chunk `u32le = 0x1e = 30`, also baked in the binary — confirmed by parsing `DZ/anims/anm/player/reloads/akm/w_akm_states.anm` FORM>ANIMSET6>FPS). `frame_count = last-key-index + 1`. Use these counts as the canonical timing reference for a custom rifle so its graph timings match vanilla:

| Anim (`.anm`) | Frames | Duration @30fps | Bones | Purpose |
|---|---|---|---|---|
| `p_erc_reload_mag_remove_akm_ras` | 22 | 0.700 s | 69 | mag DETACH (remove portion) |
| `p_erc_reload_mag_nobullet_akm_ras` | 55 | 1.800 s | 69 | full mag swap (remove+insert, no chamber) |
| `p_erc_reloadaction_closed_akm_ras` | 44 | 1.433 s | 73 | reloadAction (charging-handle pull, closed bolt) |
| `p_erc_chambering_closed_akm_ras` | 107 | 3.533 s | 73 | chamber a loose round, closed bolt |
| `p_erc_fire_akm_ras` | 11 | 0.333 s | 45 | single fire cycle |
| `p_erc_jam_akm_ras` | 230 | 7.633 s | 73 | jam-clearing sequence (long) |
| `w_akm_states.anm` | 2 | 0.033 s | 10 (weapon bones) | bolt/bullet state driver |
| `ik/weapons/akm.anm` (ikpose) | 2 | 0.033 s | 43 | left-hand grip IK pose |

Source: `DayZATool.exe --extract-anim` on each vanilla `.anm` under `DZ/anims/anm/player/reloads/AKM` + `DZ/anims/anm/player/ik/weapons/akm.anm`, then `read_seanim` (`A6_SR2M_dev/tools/anim-pipeline/seanim_writer.py`); cross-checked vs raw SEAnim header struct `=6BfII4BI`. The `AKM` and `akm` reload subdirs are the same directory (Windows case-insensitive) — identical listings.

### CORRECTION — weapon-states frame count (the "exactly 3 frames" claim) [VERIFIED-vanilla]

`w_<wpn>_states.anm` is **NOT a fixed 3 frames**. The 3-frame "closed/open/jammed" is the AUTHORING intent (one frame per init state, per `human.c`); Workbench TRIMS near-identical consecutive keys, so the STORED per-channel keycount across 47 vanilla `w_*_states.anm` is **2, 3, or 4** — not uniformly 3. The exact per-weapon init-state count is engine-read, not cleanly extractable from the binary offline.

`w_akm_states.anm` specifically = **2 frames @30fps with two DISTINCT poses** (closed vs open bolt): `Weapon_Bolt` pos f0=(0,0,0)→f1=(5.61,0,0); `Weapon_Bullet` pos f0≈0→f1=(−17.38,−4.02,4.03) (ejected). Source: `dupcheck.py` on `w_akm_states.seanim`; RAW header `frame_count=2`.

### CORRECTION — ikpose frame count ("ikpose = 1 frame") [VERIFIED-vanilla]

The weapon IK grip pose (`ik/weapons/<wpn>.anm`) is **ONE distinct static pose**. The vanilla file ships `frame_count=2` @30fps, but **frame 1 is a byte-exact duplicate of frame 0 for every bone/channel** (verified by `dupcheck.py` on `ik_akm.seanim`). So "1 frame" is correct in intent; the literal file carries 2 (write a duplicate if the tool requires ≥2). IK poses are shared/registered once and reused across weapons — the AKM `.asi` reuses izh18's pose (`player_main_akm.asi:5` → `.../ik/weapons/izh18.anm`).

### ikpose_* config keys — VERIFIED and LOCATION CORRECTED [VERIFIED-vanilla]

The `ikpose_*` keys are REAL and exact, but they live in the **AnimGraph `.agr` (compiled `.aw`) WeaponIK node**, NOT in `player_main.ast`/`.aw` top-level, and NOT in `config.cpp`/`model.cfg`. That is why a prior grep of `.ast`/`.aw` for `ikpose_` returned 0 — they are plain-text params of the `AnimNodeWeaponIK` node string. They occur **14× across 6 `.agr` files** (actions 7, combat 2, gestures 1, locomotion 2, master 1, vehicles 1). Canonical block at `DZ/anims/workspaces/player/player_main/combat.agr:24-30` (node starts `combat.agr:3-4`, `$Node AnimNodeWeaponIK "DamageFullBodyIK"`):

```
ikpose_chainoffset        = RightHandOrigin
ikpose_weaponoffset       = RightHand_Dummy
ikpose_secchainoffset     = LeftHandIKTarget
ikpose_chainmiddledir     = RightForeArmDirection
ikpose_chainmiddlediro    = RightHandOrigin,RightForeArmDirectionOrigin
ikpose_secchainmiddledir  = LeftForeArmDirection
ikpose_secchainmiddlediro = LeftHandOrigin,LeftForeArmDirectionOrigin
```

The Discord source was INCOMPLETE — it omitted the two `*_diro` keys (`ikpose_chainmiddlediro`, `ikpose_secchainmiddlediro`). These are NOT optional keys with defaults: each is an explicit IK-role→bone/helper mapping, identical across all vanilla occurrences. The same node also carries the non-ikpose IK config at `combat.agr:14-22` (`hand=RightHand`, `weapon=RightHand_Dummy`, `weaponrotator=RightArm`, `weaponaxis=-x`, `chain/chainaxis`, `secchain/secchainaxis`) and a comment block (`combat.agr:4-9`) documenting the hierarchy: root `RightHand` (not exported) | `RightHand_Dummy` (where the weapon is) | `LeftHandIKTarget` (where the left hand sits on the weapon) | `RightHandOrigin` (inverse transform of where the hand originally was). The IK-pose chain is configured in this graph node, not in any config file. Drop the "single-Discord-source, UNVERIFIED" caveat. Source: `combat.agr:3-30` (Read); `actions.agr:1648-1654`; grep count over `DZ/anims/workspaces/player/player_main`.

### reloadAction — LEGACY/obsolete, not required [partial: offline-verified non-fatal, in-game-gated for the RPT]

`reloadAction` is a LEGACY `CfgWeapons` property (Arma/old-DayZ lineage) that named a reload action in `CfgMovesMaleSdr`. In DayZ Standalone it is **NOT** the mechanism that drives reloads: the `.asi`/`.ast` graph binds clips by graph-node names (`WeaponOperations.ErcRas.ReloadMagBullet`, `ReloadMagazineDetach`, `Chambering_Closed`, …), independent of `reloadAction`.

- Not required: ALL vanilla rifles omit it. AK74 (`DZ/weapons/firearms/ak74/config.cpp`, full read) and vanilla SVD (`DZ/weapons/firearms/svd/config.cpp`) define neither `reloadAction` nor `shotAction`. [VERIFIED-vanilla]
- It survives in exactly TWO vanilla configs: a crossbow (`reloadAction="ReloadBow"`) and the AT launcher (`reloadAction="ManActReloadAT"`) at `DZ/data/config.cpp:4574` and `:4738`. [VERIFIED-vanilla]
- No vanilla Enforce `.c` reads `reloadAction`/`GetReloadAction` (grep over the tree, *.c → 0). [VERIFIED-vanilla]
- The JD demo SVD still SETS `reloadAction="ReloadSVD"` (`JDsAnimationDemo/Firearms/SVD/config.cpp:41`), but that string resolves to NO class in unpacked vanilla and the demo animates fine via its `.asi`. [VERIFIED]
- Community searches (DayZ Wiki Changelog) report `reloadAction`/`shotAction`/`drySound`/`disarmAction` etc. were removed as obsolete ~1.25-1.26. [verify — Fandom/wobo 403, exact line/version not read]

Guidance: do NOT spend effort making `reloadAction` resolve to a real `CfgMovesMaleSdr` class. Either omit it (recommended, matches vanilla rifles) or leave a harmless free-text value. Open in-game item: confirm an INVALID value emits at most a benign RPT warning, not a load error (offline evidence says non-fatal; not checked against an RPT). [verify]

### RPT / failure catalog for custom weapon anims [primary-source entries VERIFIED]

| # | RPT / symptom | Cause | Fix |
|---|---|---|---|
| E1 | `Error: Bone <name> doesn't exist in skeleton OFP2_ManSkeleton` (per bone; that bone won't animate, rest plays) | `.anm`/model.cfg/p3d selection names a bone absent from OFP2_ManSkeleton (typo, wrong case, foreign Arma/face/proxy bone, or a remapped weapon bone never tied to a character bone) | Match the authoritative OFP2_ManSkeleton list exactly (BohemiaInteractive/DayZ-Misc rig); remove/rename foreign bones. (`skeletal-anm-enfusion.md:33` + RHS/Epoch RPT dumps) |
| E2 | `ANIMATION (E): Can't load <Mod>/Anims/cfg/skeletons.anim.xml` then `ANIMATION (E): Failed to open file, line 0, column 0` | Animation/skeleton config path not packed / wrong `$PBOPREFIX$` / case mismatch (404). Same shape for a missing `.anm` referenced by an `.asi` state | Verify the exact path is packed and case-correct. (verbatim from a real DayZ server RPT, pastebin sFwd21nZ) |
| E3 | Blender export `AttributeError: 'Mesh' object has no attribute 'calc_normals_split'` (`ExportTxo.py`) | Running the ORIGINAL jdfnc24/MrTea plugin on Blender ≥4.1 (`calc_normals_split` removed) | Use Blender 3.6.8–4.0 for the original plugin. (NOTE: the MAINTAINED Sanitoeter05 fork is the OPPOSITE — it needs Blender 4.4+/5.x; see plugin-version note.) (plugin GitHub issue #1 + README) |
| E4 | Two animation mods crash the game / one silently wins | (Applies ONLY to player-GRAPH-replacing mods.) Enfusion allows one player/creature animation-graph mod at a time. **Does NOT apply to weapon anims via the ASI route — those are conflict-free.** See the wall correction. | Merge graph mods into one. ASI-route weapon mods coexist. (Workshop 2918418331 desc + Discord) |
| E5 | Limbs snap to default / T-pose / partial freeze during the anim | Not every skeleton bone has a keyframe; un-keyed bones fall back to a default transform | Key every bone in the skeleton. (Discord m/740228592830513234, m/1246221883976716288) |
| E6 | Arms/weapon grossly wrong after a 2H anim where 1H is expected | Wrong handedness state | Assign the anim to the matching handed ASI (1h/2h/rifle/pistol). (Discord m/850646042878017636) |
| E7 | Looks right in Blender, bones twist/roll wrong in-game | Blender bone +Y follows bone length; DayZ uses +X bone frame — offset not derivable offline | Account for the Blender→DayZ bone-axis remap via the official rig/exporter; verify in-game. (Discord m/1042818007908503612 + project MEMORY) |
| E8 | Extracted rig "always incorrect" | DayZATool/Mikero DeAnm extraction is a reference, not a clean round-trip (worst for empties/IK-helper bones) | Treat extraction as a starting point only. (`skeletal-anm-enfusion.md:41`) |

Two failure modes are visual-only with no catalogued RPT string [verify — capture during the in-game gate]: the exact DayZ `.anm` "not found" wording for an `.asi`-referenced clip, and any RPT for an un-run "Add Survivor IK Bones" Blender step or a dead-bolt weapon.

### Filepatching of `.anm` — repack-each-iteration [in-game-gated]

Claim "filepatching does NOT reload `.anm` → repack the PBO each iteration" is plausible but NOT closed by a primary source — keep it, marked [in-game-gated], not asserted. Rationale: DayZ filepatching loose-loads only non-binarized text-read file types (`.c` scripts loaded as text, `.layout`, `.json`, `.paa`, `.ogg`); `config.cpp`/`.p3d`-MLOD/`.tga`/`.rvmat`/`.wrp` are binarized (stardz DayZ-Modding-Wiki 04-file-formats/06-pbo-packing). `.anm` is a Workbench-COMPILED binary resource (FORM>ANIMSET6 IFF container, verified by parsing `w_akm_states.anm`) reached via `.asi` resource refs at `AddItemInHandsProfileIK` register time, NOT via the loose-text loader — so "no loose reload" is mechanistically likely. BUT one unverified web summary claims loose `.p3d`/`.paa` DO filepatch in the diag exe, so the boundary for binary resources is genuinely undocumented (BI wiki 403s; stardz wiki does not enumerate `.anm`). Repro to close it: edit a loose `.anm`, launch DayZDiag `-filePatching`, observe whether the weapon state changes without a repack.

### Other gap items moved to VERIFIED [VERIFIED-vanilla]

- **WeaponOperations group**: exactly `#ngroupnames 2` (`ErcRas`, `PneRas`) and `#nanims 42`; 42 names match incl. literal-space `Jamming Cancel`/`Jamming Check`. **No `CroRas` in WeaponOperations** (CroRas lives only in OTHER groupTypes, lines 401-780); no modeswitch op. Do NOT invent `WeaponOperations.CroRas`. (`player_main.ast:1228-1281`)
- **Weapon bone set**: `Weapon_Root` (legacy), `Weapon_Bullet`, `Weapon_Trigger`, `Weapon_Magazine`, `Weapon_Bolt`, `Weapon_Bone_01..06` (exactly 6 configurable), plus `RightHand_Dummy`/`LeftHand_Dummy`. (`DZ/Anims/cfg/skeletons.anim.xml:74-116,254-264`)
- **CfgPatches**: `DZ_Anims_Anm_Player` and `DZ_Anims_Cfg` are real vanilla classes; the demo's `Animations/config.cpp` `requiredAddons[]` includes `DZ_Anims_Anm_Player`. (`DZ/anims/anm/player/config.cpp:3`; `DZ/anims/cfg/config.cpp:3`; `JDsAnimationDemo/Animations/config.cpp:8-10`)
- **{GUID} keys — DO NOT strip**: vanilla `.asi` carry `{GUID}` prefixes on `#template`/`#parent`/`#ikpose` and every `.anm` value (`player_main_akm.asi:2-5`, `player_main.asi:2`); only the hand-authored demo `.asi` omit them — Workbench regenerates GUIDs on import. Hand-authoring bare paths risks silent resolution failure. Keep them / let Workbench generate them.
## [2026-07-06] VERIFIED CORRECTIONS — action anims (SP-042..SP-046, A6_SR2M) + headless .txa import (SP-035)

### SP-042 — §4.9 "per-grip animation swap" cites an UNANSWERED question; the suggested code is invalid [VERIFIED-vanilla `dayzplayer.c:225-252`]

The thread `answeroverflow.com/m/917810289293029407` cited in §4.9 is NOT a "community technique": it is a
2021 question (Wayward son) nobody answered; the same ask reappears unsolved in 2026
(`/m/1515447189676097556`, Egzo, "I have like 50 attachments"). The snippet
`if(weapon.withGrip) pType.AddItemInHandsProfileIK(...)` does not compile where implied:
`RegisterFireArms(DayZPlayerType pType, …)` runs ONCE when the `DayZPlayerType` loads and only receives
CLASSNAMES — there is no `weapon` instance in that callback. Verdict: the ikpose/asi is bound by classname,
once; the engine does NOT re-evaluate it on attach/detach, and there is NO per-instance API. The only
marginally viable way to vary pose by attachment is two classnames + hot-swapping the weapon entity in
`EEItemAttached`/`EEItemDetached` (a binary axis, fragile, combinatorially explosive) — NOT a branch in
the callback. Author one pose that reads OK with and without the attachment (what vanilla does).

### SP-043 — EXCLUDE `Weapon_*` bones from full-body action anims [VERIFIED in-game A6_SR2M 2026-06-30]

Weapon action anims: EXCLUDE the `Weapon_*` bones from the `.anm` unless animating them with correct
bind values. A full-body action anim authored in a pipeline that treats the weapon as a RIGID object
following the hand exports `Weapon_*` bones (`Weapon_Bolt`/`Trigger`/`Magazine`/`Bullet`/`Bone_01..06`)
at the export rig's rest — garbage values (typically collapsed to `(0,0,0)`; measured: `Weapon_Bone_01..06`
at `(0,0,0)` vs `(-11.43,0.79,-2.48)` in vanilla `p_erc_jam_cancel_pm73_ras` ≈ 11.7 cm). The engine
overwrites those bones with that garbage and DEFORMS/STRETCHES the weapon mesh. Fix: filter `Weapon_*`
out of the SEAnim bridge — `DayZATool --extract-anim <anm> 100` → drop `Weapon_*` bones with
`seanim_writer` → `--generate-anim 100`; the weapon stays in base pose held by the grip ikpose. Include
`Weapon_*` ONLY when animating them with correct values (e.g. bolt slide copied from the vanilla
equivalent). Detection: extract the `.anm`, compare `Weapon_Bone_*` frame-0 vs the weapon's vanilla;
several cm off = garbage → exclude. Same principle as excluding `RightHand_Dummy` (the weapon anchor):
remove what the export got wrong, let ikpose/base state place it — do NOT try to "fix the value" in the
export.

### Spine-up invariants for full-body weapon action anims [A6_SR2M 2026-06-30]

Full-body weapon action anims are SPINE-UP: exclude `EntityPosition`, `Pelvis` and leg bones at the
`.seanim` level (the action must not fight locomotion). Never animate `RightHand_Dummy` — it is the
weapon anchor; animating it makes the ikpose lose the weapon.

### SP-044 — Pose-preservation gate: PER-COMPONENT quat delta, NOT angle

Verify pose preservation with PER-COMPONENT quat delta, NOT angle. Align sign first (double-cover: if
sum(qa·qb) < 0 → qb = −qb), then max|qa−qb| per component, threshold ~5e-6 (benign 6-decimal rounding).
Do NOT use `2·acos(sum(qa·qb))`: near rest it amplifies rounding to ~0.1–0.2°, and with non-unit-norm
quats it invents an angle where the components are identical (seen: 0.18° reported with true delta
0.00). The `seanim_writer` round-trip gate already uses the correct pattern.

### SP-045 — Bolt idle state comes from `w_<wpn>_states.anm`, NOT the action anim [VERIFIED A6_SR2M 2026-07-01]

The bolt's idle state (closed/open/jammed) is fixed by `w_<wpn>_states.anm`, NOT by the action anim.
The 3 weapon-states frames are the ONLY rest values of the bolt (0 closed, 1 open, 2 jammed); on jam
the engine puts `Weapon_Bolt` at frame 2 via `SetInitState`. An unjam action anim blends on top and
overrides `Weapon_Bolt` ONLY while playing → its frame 0 must equal the jammed frame or the bolt JUMPS
at gesture start. Extract real values with `DayZATool --extract-anim w_<wpn>_states.anm 100` and use
them as the bolt markers in the authoring tool; do NOT eyeball them. (SR-2M: closed 0 / jammed −2.2 cm /
open −4.3 cm, 51% of travel, X-bone.)

### SP-046 — HOLD/continuous action anims MUST carry `LoopStart`/`LoopEnd` notetracks [root cause traced in the vanilla FSM; in-game gate pending 2026-07-01]

Every HOLD/continuous weapon action anim (unjam is the canonical case) MUST carry `LoopStart`/`LoopEnd`
notetracks, or the gesture loops forever and the operation never completes. The operation is
TIMER-driven: `WeaponUnjamming_Start.OnUpdate` (`weaponunjamming.c`) accumulates hold time and at ~5 s
does `SetJammed(false)`; neither anim length nor any notetrack completes it. For the timer to
accumulate, the anim command must be LOOPING (`HumanCommandWeapons.IsActionFinished()` stays false) —
that is what `LoopStart`/`LoopEnd` provide. Without them the anim plays once, `IsActionFinished()`→true,
the FSM posts `_abt_` and returns to jammed; with continuous input it re-fires → visible loop, never
unjams. Adding `Weapon_CanUnjam_*`/`Weapon_Unjammed` does NOT fix it (not consumed by the unjam FSM).
Correct structure (copy from vanilla, extracted with `DayZATool --extract-anim p_erc_jam_<sim>_ras.anm
100`): intro (f0→LoopStart) · loop (LoopStart→LoopEnd = the struggle; repeats while held) · outro
(LoopEnd→end, contains `Weapon_Unjammed` = rechamber). `LoopEnd` goes BEFORE `Weapon_Unjammed`.
Notetrack format that DayZATool round-trips: `LoopStart||-1` / `LoopEnd||-1`. No re-authoring needed:
extract the `.anm`, add the 2 notetracks with `seanim_writer`, `--generate-anim` (verified: bones
preserved <1e-3, notetracks survive). Unjam is a ~5 s HOLD: when testing in-game, HOLD the key; a tap
plays the jam_cancel and the weapon stays jammed (that is vanilla). Checklist line added under §10
"Author": HOLD-type action anim → `LoopStart`/`LoopEnd` present.

### SP-035 — Headless `.txa` import via DayzAnimationPlugin (Blender background)

Recipe for importing a `.txa` without the Blender UI (plugin repo `BlenderPlugin` folder), for
programmatic pose extraction — complements §3.1 (interactive import):

1. `sys.path.append(<repo>\BlenderPlugin)`; `import DayzAnimationTools`;
   `DayzAnimationTools.register()`; then with the armature active:
   `bpy.ops.import_scene.txa(filepath=..., files=[{"name": basename}])`.
2. GOTCHA `NameError`: `ImportTxa.py:202` references `SURVIVOR_IK_ANIM_BONES`, which does NOT exist
   (`Txa.py` defines the `_L` and `_R` variants); monkeypatch BEFORE importing:
   `import DayzAnimationTools.Import.ImportTxa as IT`, then
   `from DayzAnimationTools.Types.Txa import SURVIVOR_IK_ANIM_BONES_L, SURVIVOR_IK_ANIM_BONES_R` and
   `IT.SURVIVOR_IK_ANIM_BONES = list(SURVIVOR_IK_ANIM_BONES_L) + list(SURVIVOR_IK_ANIM_BONES_R)`.
3. FK-pure pose (= the `.anm`/in-game content): the plugin re-enables constraints after import —
   disable pose-bone constraints AFTER import, `frame_set(0)`, read `arm.matrix_world @ pb.matrix`.
4. Rotation AND translation are applied; arm-bone translation ≈ rest offset, but ROOT (`Pelvis`)
   translation is real (soft-aim crouches ~3.5 cm) — keep it.
5. Reusable scripts: `WeaponAnimPipeline_dev/tools/txa/apply_txa_plugin.py` + `txa_plugin_to_pose.py`
   (transform `Rf=[[1,0,0],[0,0,1],[0,-1,0]]`); `apply_txa_jd.py`/`pose_convert.py`/`pose_from_txa.py`
   are DEPRECATED (hardcoded scratchpad paths + dropped root translation).
