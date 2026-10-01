---
status: durable-knowledge
created: 2026-05-28
last_verified: 2026-05-28
sources:
  - "video-transcripts/dayz-modding/index.md (4 videos: Tree + hunterz688 x3)"
  - "skills-plugin: dayz-animation-pipeline (SKILL.md + 6 references)"
  - "skills-plugin: dayz-model-pipeline (references/animations.md)"
  - "vault: lessons-learned LL-012"
  - "vanilla DayZ data unpacked at P:\\ (DZ/ + SurvivorAnims/ + 0_SurvivorAnimsDefines/)"
topic: DayZ animations — creatures, weapons/items, anim graphs
confidence_legend:
  "[VERIFIED-vanilla]": "confirmed against unpacked vanilla DayZ data (path:line snippet)"
  "[VERIFIED-vault]": "confirmed against an installed skill, real mod code, or vanilla asset already read"
  "[VERIFIED-source]": "stated by an experienced modder (hunterz688/Tree workshop) — credible but not vanilla-grounded; safe as a design pointer, not as a copy-pasteable identifier"
  "[REFUTED-vanilla]": "video claim contradicted by vanilla data"
  "[TBD-verify-vanilla]": "must grep P:\\ vanilla data before using any exact name/path/value in code"
---

# DayZ animations — creatures, weapons/items, anim graphs

Cross-cutting knowledge that **complements** the `dayz-animation-pipeline` skill. The skill covers Layer 1 (config-driven) and Layer 2/3 (skeletal `.anm`/RTM, tooling). This note covers areas that the skill barely touches: custom creature pipeline with anim graph + state machine, weapon/item animations with ASI/TXA, and Workbench Animation Editor discipline. Every claim carries a verification tag; nothing with `[TBD-verify-vanilla]` must enter `verified-apis.md` or a diff before grepping it in actual `P:\`.

## When to read this note before the skill

- You are going to animate a **custom creature/animal/infected** (anything beyond a rigid door/lever): start here, then the skill for the sandbox/Windows seam.
- You are going to touch **player/weapon/item animations** (reload, fire IK, mag remove, state IDs): start here, the skill confirms the "only one anim mod at a time" wall and OFP2_ManSkeleton.
- You are going to build your own **anim graph / state machine**: only here. The skill does not enter this level.

If the job is a rigid door/lever, lever, gauge: use the skill directly ([`references/config-driven-animation.md`](skills-drafts/dayz-animation-pipeline/references/config-driven-animation.md)) — this note adds nothing.

## Corrections to names appearing in videos (2026-05-28 sprint)

Master table of actual spellings versus what the videos say. **Always use the right-hand column**.

| Video says | VERIFIED reality | Vanilla source |
|---|---|---|
| `discrete = 1` / `discrete = 0` | `isDiscrete = 1` / `isDiscrete = 0` | `BuildingModels/model.cfg`, `Crate/model.cfg` |
| "rigid body vs weight deformation" | Mechanical (no interpolation) vs organic/smooth | `dayz-model-pipeline/references/animations.md:16` |
| "Entity Position" (with space) | `EntityPosition` (PascalCase, one word) | `DZ/anims/cfg/skeletons.anim.xml:4` |
| "Pin Look At" / "Look At" | `LookAt` (PascalCase, one word). `Pin` does not exist in vanilla | `DZ/anims/cfg/skeletons.anim.xml:18` |
| "right hand dummy" | `RightHand_Dummy` (with underscore, helper in lod=2) | `DZ/anims/cfg/skeletons.anim.xml:100,115,525` |
| "left hand mag tracking" bones | `LeftHand_Dummy` exists; there are NO magazine bones in production skeleton | `DZ/anims/cfg/skeletons.anim.xml:74` + absence in player skeleton |
| `cmd death` (lowercase, with space) | `CMD_Death` (UPPER_SNAKE with `CMD_` prefix) | `DZ/animals/animations/!graph_files/ambientlife/ambientlife_graph.agr` |
| `cmd look at` | `CMD_LookAt` | same |
| `cmd attack` | `CMD_Attack` | same |
| `cmd success` | `CMD_AttackSuccess` (`CMD_Success` alone does NOT exist) | same |
| `skeletonAnims.xml` / `skeletonanim.xml` | `skeletons.anim.xml` (literal, with dots) | `DZ/anims/cfg/skeletons.anim.xml` |
| "weapon cocked" (state ID) | `FireCocked` (state) — state path is `WeaponOperations.<rig>.FireCocked` | `SurvivorAnims/animgraph/player_main/combat.agr:795` |
| "mag remove" (state ID) | `ReloadMagazineDetach` — state path `WeaponOperations.<rig>.ReloadMagazineDetach` | `.../weapons/player_main_1911.asi:21` |

**Any identifier from the video** that does not appear confirmed in this table or below with actual `path:line`, **must be grepped in `P:\` before being used**. The videos are a useful source but systematically imprecise in casing and separators.

---

## 1. Custom creature pipeline (animal / infected / predator)

### 1.1 Pipeline layers

```
Blender (rig + skeleton + animaciones)
  → FBX (export con custom properties, sin leaf bones, sin cámara/lámpara, bake animation)
  → Workbench / Object Builder (import, weight painting, validación)
  → model.cfg (CfgSkeletons + bone-parent pairs)
  → anim graph (state machine, commands, variables, events)  ← núcleo del trabajo creativo
  → config.cpp (CfgVehicles entry tipo animal vanilla)
  → scripts mínimos (inventory visible, skinning, hit components)
  → skeleton XML registrado en metadata del mod
  → in-game con AI agent template vanilla (hen / herbívoro / predator)
```

[VERIFIED-source] The video repeats: you must **start with a minimal animgraph (1 state, 1 anim source)** and validate it in-game **before** wiring states/variables/events. Building the entire graph offline and discovering failure at the end is the anti-pattern.

### 1.2 Special creature bones — [VERIFIED-vanilla]

Creatures (and the player) use two skeleton bones that the engine natively understands:

- **`EntityPosition`** [VERIFIED-vanilla `DZ/anims/cfg/skeletons.anim.xml:4`]
  - `<bone name="EntityPosition" index="0" movement="true" lod="0" />`
  - Bone that the engine uses for entity prediction/displacement. Appears in player skeleton and is referenced from animal animgraphs — wolf uses `"PredictionTurn" "EntityPosition"` (in `wolf_maingraph.agr`).
  - `movement="true"` is what marks the bone as actual movement driver.
  - For flying creatures tricks are used because DayZ does not natively support flight [VERIFIED-source, hunterz688 vol.1].

- **`LookAt`** [VERIFIED-vanilla `DZ/anims/cfg/skeletons.anim.xml:18`]
  - `<bone name="LookAt" index="18" lod="0" />`
  - **`Pin` does NOT exist in vanilla** — the video gets it wrong. The bone is just `LookAt`.
  - Used by AI / engine to aim look at target.

[VERIFIED-source] **EntityPosition orientation**: forward = +Y (green in Blender), up = +Z (blue). Misorientation = animal walks sideways / clips through ground. The video is not vanilla-grounded on this, but the principle is Bohemia standard.

[VERIFIED-source] **Workbench refresh**: changing bones/skeleton in `P:` may require restarting Workbench to detect changes. Not a bug, it is project caching.

[VERIFIED-source] **Spaces in bone names**: Workbench converts spaces to underscores; Object Builder does not necessarily. **Hard recommendation: bone names WITHOUT spaces from the start** (PascalCase `EntityPosition` or snake like `entity_position`).

### 1.3 Skeleton XML and registration — [VERIFIED-vanilla]

- **Actual file name**: `skeletons.anim.xml` (literal, with both dots). [VERIFIED-vanilla `DZ/anims/cfg/skeletons.anim.xml:1`: `<skeletons version="1.0">`]
- **How the engine finds it**: by **path convention in the pbo**, not by an explicit key in `config.cpp`. The vanilla module's `config.cpp` `DZ/anims/cfg/config.cpp` contains ONLY `CfgPatches { class DZ_Anims_Cfg {...} }`; there is no `skeletonFile = "..."` or similar. [VERIFIED-vanilla]
- **Implication for mods**: if you add a custom creature with its own skeleton, the XML must be packed in the correct path within the mod's pbo (same layout `<mod>/anims/cfg/<something>.anim.xml`) and depend on `DZ_Anims_Cfg` in `CfgPatches`. **It does not need to be pointed to from config.cpp**.
- **XML structure**: root `<skeletons version="1.0">`, children `<skeleton name="...xob">` listing `<bone name="..." index="N" lod="N" />` (some with `movement="true"`).
- **"Crash on first spawn" risk** that the video attributed to the missing XML: the actual mechanism is that the `.xob` (binary skeleton) or its bones are not accessible to the animgraph; the XML only exposes the catalog. Verify packing of the XML + referenced `.xob`.

### 1.4 FBX export from Blender — checklist [VERIFIED-source]

Before exporting the creature as FBX:

- **Export custom properties**: yes.
- **Leaf bones**: disable (DayZ does not need them and they are noise in the skeleton).
- **Camera/lamp**: out of the FBX.
- **Bake animation**: yes (necessary for Workbench to receive correct clips).
- **Creature rotation**: take care with the specific orientation DayZ expects; check after importing into Workbench before continuing.
- If you add the Entity Position / Look At bone after the initial rig, **move it to its canonical position before exporting** (center/root for Entity Position, child of head for Look At).

### 1.5 model.cfg for creature — references

The structure of the `CfgSkeletons` block + `"bone","parent"` pairs is [VERIFIED-vault] in:
- [`dayz-animation-pipeline/references/config-driven-animation.md`](skills-drafts/dayz-animation-pipeline/references/config-driven-animation.md) (Layer 1 base)
- `dayz-model-pipeline/references/animations.md` (complete examples)

For creature: inherit the `CfgSkeletons` of a vanilla animal (seagull, hen, generic herbivore) and add its own bones. The seagull example in the video shows that the `bone, parent` pairs are the backbone of the config.

Anatomical note: `isDiscrete = 0` for creatures (organic movement with interpolation). `= 1` only for mechanical.

---

## 2. Anim graph and state machine (for creatures)

The **anim graph** is the layer that the video calls "preview model / sheet master / state machine". It is where you define:

- **States**: idle, walk, trot, run, attack, hit, death (one or more depending on impact side/zone), swim, turn.
- **Anim sources**: which `.anm` each state plays.
- **Transitions**: conditions to pass between states (variable change, event, end-of-clip).
- **Variables**: numerical values that drive blending/selection (`speed`, `swimming`, `state`).
- **Commands**: engine-side names that trigger states from AI (death/attack/look at).
- **Events**: markers within a clip that trigger sound, damage, end of simulation, etc.

### 2.1 Canonical anim graph commands — [VERIFIED-vanilla]

Actual casing (UPPER_SNAKE with `CMD_` prefix). The video speaks them in lowercase with spaces; **incorrect** — always use the actual column.

**Animales** (de `DZ/animals/animations/!graph_files/ambientlife/ambientlife_graph.agr`):

| Real | Video said | Notes |
|---|---|---|
| `CMD_Death` | `cmd death` | death state trigger |
| `CMD_LookAt` | `cmd look at` | head/look tracking |
| `CMD_LookAtXChange` | (not mentioned) | look at sub-command |
| `CMD_Attack` | `cmd attack` | starts attack state |
| `CMD_AttackSuccess` | `cmd success` | the attack connected → applies damage. **`CMD_Success` does NOT exist standalone** |
| `CMD_Hit` | (not mentioned) | receives hit |
| `CMD_AnimCallBack` | (not mentioned) | generic event callback |

**Player** (de `SurvivorAnims/animgraph/player_main/`):

| Real | Usage |
|---|---|
| `CMD_WeaponFire` | fires weapon |
| `CMD_Reload_Magazine` | full magazine reload |
| `CMD_Reload_BoltAction` | bolt-action reload |
| `CMD_Reload_Chambering` | chambering bullet |
| `CMD_Reload_ChamberingFast` | fast chambering |
| `CMD_Reload_Clip` | clip reload |
| `CMD_Modifier_Additive` | modifier (sickness/cough/sneeze) — **NOT for reload** (see §3.1 refutation) |

### 2.2 Anim graph variables — [VERIFIED-vanilla partial]

- **`speed`** [VERIFIED-vanilla]: actual variable in herbivores and ambientlife.
  `DZ/animals/animations/!graph_files/herbivores/herbivores_graph.agr`: `#Var speed float 0.0 0.0 5.0 ""`
- **`SlopeAngleX`** and **`SlopeAngleZ`** [VERIFIED-vanilla]: provided by the engine, present in all animal graphs. `#Var SlopeAngleX float 0.0 -90.0 90.0 ""`. **This is the basis of terrain alignment** (§2.4).
- **`swimming`** [REFUTED-vanilla as standalone `#Var`]: does NOT exist as a variable in animal graphs. In the player graph it appears as a **state tag** (`TagSwimming`, `SwimmingMaster` in `locomotion.agr`), not as an exposed float/bool variable. The video treated it as a generic variable — incorrect for animals.

### 2.2 Minimal state machine — validation method [VERIFIED-source]

The video recommends this strict order:

1. Create graph + state machine with **a single idle state** and **a single anim source** (a single `.anm`).
2. Model in game with minimal `model.cfg` (geometry, mass, basic FireGeo). [Cross-ref `dayz-p3d-audit` and `dayz-model-pipeline`.]
3. Verify that the creature does not crash, is visible, plays the idle.
4. **Only then** add walk → run, blending by `speed`, terrain alignment, hit, death.

Building all states offline and discovering a bug in one of them = hours/days of bisection.

### 2.3 BlendT (blend tree) by speed — [VERIFIED-source]

For locomotion: blending node between walk / trot / run according to the value of the `speed` variable, with explicit **transition duration**. Turn animations must start and end in poses compatible with the walk/run loops; a turn that starts/ends in an arbitrary pose generates visible popping.

### 2.4 Terrain alignment — [VERIFIED-vanilla]

Actual mechanism: `AnimNodeRot` node that consumes the `SlopeAngleX` / `SlopeAngleZ` variables (provided by the engine) multiplied by **π/180 (= 0.01745329)** to convert degrees to radians.

- Wolf: `DZ/animals/animations/!graph_files/wolf/wolf_maingraph.agr:3`
  `"AlignToTerrain_Rot" "" "Master_SM" "SlopeAngleX * 0.01745329..."`
- Herbivores: nodes `TerrainRot_Deers`, `TerrainRot_CowAndBull`, `TerrainRot_BoarAndPig`, `TerrainRot_SheepAndGoat` with the same formula. [VERIFIED-vanilla]

**It is not a "special" node** called "terrain alignment"; it is an `AnimNodeRot` with a descriptive name. For a custom creature: copy the formula from the vanilla animal most similar in proportions (large quadruped → cow, medium → boar, small → sheep).

### 2.5 Death states — [VERIFIED-source]

Death can be multi-state according to hit parameter/direction. The vanilla predators state machine shows multiple death states (by impact side, by body zone). The video shows it as copyable reference.

### 2.6 Hit states and attack — [VERIFIED-source]

- **Hit**: works as a transition from multiple states (idle, walk, run). If the purchased asset only has "hit while standing still", you have to **recombine in Blender** (non-linear editor) hits from other base poses so the transition does not look broken.
- **Attack**: requires `attack` state + `success` state (damage is applied in `success`, not in `attack`). Events within the attack animation mark the impact frame and the sound.

### 2.7 Events in animations — [VERIFIED-source]

Animation events serve to:
- Trigger sound.
- End simulation (death simulation finished → entity can be cleaned up).
- Apply damage on the correct frame of the attack.

**Video gotcha**: adding events can break the graph if the event table does not match. If Workbench fails loading a copied vanilla graph, **adjust the event table** before touching the graph logic.

### 2.8 Animations of purchased assets — [VERIFIED-source]

Stock purchased models rarely come with animations that fit DayZ transitions (different start/end poses). You have to **recombine in Blender** blending clips so that walk → run, idle → attack, etc., match in pose.

---

## 3. Weapon / item animations (vol.3)

### 3.1 ASI and TXA — actual format [VERIFIED-vanilla]

- **`.txa`** = text, keyframe source that Workbench compiles to binary `.anm`. [VERIFIED-vault]
- **`.asi`** = `$animsetinstance` with table `"StateName.SubName.Phase" → "{GUID}path.anm"`. [VERIFIED-vanilla]

**Actual structure** of the `.asi` (from `DZ/anims/workspaces/player/player_main/player_main_rifle.asi:1-6`):

```
$animsetinstance {
  #template "{GUID}DZ/anims/workspaces/player/player_main/player_main.ast"
  #nparents 1
  #parent  "{GUID}DZ/anims/workspaces/player/player_main/player_main.asi"
  $animations {
    "ActionContinuous.BlowFireplaceCro.In" "{GUID}DZ/anims/anm/player/..."
    ...
  }
}
```

- `#template` points to the `.ast` (animset template — defines which states can be mapped).
- `#parent` points to another `.asi` from which it inherits (hierarchy: `player_main.asi` is the root, specific ones hang from it).
- `$animations` maps `StateName.Sub.Phase` → `{GUID}path.anm`.

**Complete catalog of player ASIs** [VERIFIED-vanilla `DZ/anims/workspaces/player/player_main/`]:

| ASI | Usage |
|---|---|
| `player_main.asi` | base / parent of all |
| `player_main_1h.asi` | one-handed weapons/items |
| `player_main_1h_restrained.asi` | one-handed + restrained |
| `player_main_2h.asi` | two-handed weapons/items |
| `player_main_heavy.asi` | heavy items (wheel/door/barrel) — the one for `AddItemInHandsProfileIK` |
| `player_main_pistol.asi` | pistols |
| `player_main_rifle.asi` | rifles |
| `player_main_bow.asi` | bow (partial state — see §3.8) |
| `player_main_surrender.asi` | hands up |
| `menu_rifle.asi` | rifle in menu/preview |
| `props/` | 30+ ASIs per prop |
| `weapons/` | one per specific weapon (`player_main_akm.asi`, `player_main_1911.asi`, etc.) |

**Implication**: for a custom item/weapon, inherit from the closest vanilla ASI and only add/override states. Do not rewrite the complete ASI (cross-ref §4).

### 3.2 Bones and Fire / Reload / IK workflow

- **`RightHand_Dummy`** [VERIFIED-vanilla `DZ/anims/cfg/skeletons.anim.xml:100,115,525`]
  - Actual casing: `RightHand_Dummy` (with underscore). The video said "right hand dummy" — that exact string does not exist.
  - It is a **helper bone in lod=2** (it is not the main `RightHand` bone which is in lod=1). It serves as an auxiliary anchor for the weapon/item — moving this bone moves the weapon.
  - Aligning buttstock vs collarbone and forearm angles is the most sensitive part of the rig [VERIFIED-source].

- **`LeftHand_Dummy`** [VERIFIED-vanilla `DZ/anims/cfg/skeletons.anim.xml:74`]
  - Symmetrical to the right, lod=2.

- **Magazine tracking — no mag bones in production skeleton** [VERIFIED-vanilla]
  - Bones `Magazine`, `Bullets_Magazine`, `Bullets_holder`, `Bullets_on_holder` exist ONLY in the testing skeleton `player_testing.xob` and are literally marked `<!--To Be removed-->` (`skeletons.anim.xml:296-300`).
  - **In production the engine tracks the magazine via `LeftHand` / `LeftHand_Dummy` directly** — it does not need a specific mag bone.
  - The video claim of "helper bones in Blender that are NOT exported to the game" is consistent with this: helpers live only in the author's `.blend` to visualize the trajectory; the exported `.txa` only tracks the hand.

- **Fire IK**: can look "confusing" in Animation Editor; the rig in Blender (with weapon model present) helps understand what is happening [VERIFIED-source].

- **Blender vs game**: constraints and numbers in Blender help pose, but **are not exported as-is** to the TXA. You have to export, load in-game/preview, look at elbow, shoulder, grip gaps, and iterate [VERIFIED-source].

### 3.3 Weapon states — [VERIFIED-vanilla]

The actual names (with paths). General pattern: `WeaponOperations.<RigKey>.<StateName>` where `<RigKey>` is the pose/rig combination (e.g. `ErcRas` = erected + rail accessory system, `Pst` = pistol, etc.).

| Video said | Actual | Example path | Source |
|---|---|---|---|
| "weapon cocked" / "Cocked" | `FireCocked` | `WeaponOperations.ErcRas.FireCocked` → `p_erc_empty_cocked_1911_ras.anm` | `.../weapons/player_main_1911.asi:10` |
| "mag remove" | `ReloadMagazineDetach` | `WeaponOperations.ErcRas.ReloadMagazineDetach` → `p_erc_reload_mag_remove_1911_ras.anm` | `.../weapons/player_main_1911.asi:21` |
| "bullet in chamber" | **DOES NOT exist as state name** | — | — |

**Chambering** is done via commands (not state names): `CMD_Reload_Chambering`, `CMD_Reload_ChamberingFast`. The video confused the command with a state.

**Trigger of the FireCocked state** from the player animgraph (`SurvivorAnims/animgraph/player_main/combat.agr`):
- Line 795: `"FireCockedAnim" "" "WeaponOperations.FireCocked" "noloop"`
- Line 850: transition condition `"GetCommandI(CMD_WeaponFire) == 2"` (fire with empty weapon cocked)

**`mag remove` is only the return pose** [VERIFIED-vanilla by the name of the `.anm`: `p_erc_reload_mag_remove_1911_ras.anm`]: the inventory script decides when the magazine actually leaves the slot; the animation only draws the hand moving away. The video was right on this nuance.

### 3.4 Animation Editor (Workbench) — [VERIFIED-vanilla, mecanismo aclarado]

Actual mechanism: the `#eventtable` line only exists in the **compiled** workspace (`DZ/anims/workspaces/player/player_main/player_main.aw:136`):

```
#eventtable "{3037156104937B91}DZ/anims/workspaces/player/Player_EventTable.ae"
```

The **source** workspace edited in Workbench (`SurvivorAnims/animgraph/player_main/player_main.aw`) **does not contain** that line. That is why the video says "remove the line": for Workbench to open the graph in the Animation Editor, the source `.aw` must NOT have `#eventtable` (the association with the `.ae` is made upon compiling/exporting, not upon editing).

**Practical action if you are going to edit the player graph in Workbench**:
1. If you receive a compiled `.aw` (extracted from `DZ/`), delete the `#eventtable` line.
2. Edit the graph in Animation Editor.
3. Upon re-exporting/packing, Workbench/Workshop regenerates the reference to the `.ae`.

Path of the events `.ae`: `DZ/anims/workspaces/player/Player_EventTable.ae`.

### 3.5 FPS — UNKNOWN (not detectable in text files)

[VERIFIED-vanilla negative] Exhaustive search in `SurvivorAnims/animgraph/` (all `.agr`, `.ast`, `.aw`) and in `DZ/anims/workspaces/` (all `.asi`, `.aw`, `.asy`) finds no `fps`, `FPS`, `frameRate`, `framerate` key nor the literal `30` in relevant context. The only `AnimFPS 30` that appears is in `SurvivorAnims/Particle/MoneyPtc.ptc` — irrelevant (particle effect).

**Conclusion**: the framerate of player animations is not declared in text files of the workspace or animgraph. Either:
- (a) It is embedded in the binary `.anm` (probable — Bohemia bake of the fps upon compiling).
- (b) It is an exporter convention (Blender plugin / Workbench compiler).

The video claim "30 fps default" remains **unconfirmed and unrefuted** without an `.anm` inspector. **Practical action**: if your Blender plugin exposes fps, set it to 30 (consistent with the convention reported by the video) and verify round-trip with a short animation before mass-producing the set.

### 3.5.bis Reload is NOT additive in vanilla — [REFUTED-vanilla]

The vol.3 video claims that "reload is additive animation: only torso/shoulders downward". **Vanilla does not back this up.**

What does exist [VERIFIED-vanilla]:
- `CMD_Modifier_Additive` (in `player_main.agr:47` and used in `locomotion.agr:3959-3976`) controls **character state modifiers**: `SickSneezeStanceSTM`, `SickCoughStanceSTM`. Cough, sneeze, fever. Nothing related to reload.
- Vanilla reloads use **dedicated commands without additive flag**: `CMD_Reload_Magazine`, `CMD_Reload_BoltAction`, `CMD_Reload_Chambering`, `CMD_Reload_ChamberingFast`, `CMD_Reload_Clip`.
- There is no `AnimNodeAdditive` node or `TagAdditive` tag for reloads in the player animgraph.

**Interpretation**: the video may be describing how it is *authored* in Blender (only torso/arms are animated, leaving legs to another layer by production convention), but the **system** does not mark reload as additive at runtime. Implementing your own custom reload assuming it is additive and will blend "automatically" → can break your pose. **Verify in the nearest vanilla animgraph how it enters/exits the state**.

### 3.6 Minimum frames per state — [VERIFIED-source]

Beware of states with few frames (the videos mention "end on frame 2"). If the state ends prematurely, the engine is left showing 2 unique frames. Review clip duration vs expected state duration.

### 3.7 Custom item animations without re-authoring the entire ASI [VERIFIED-source]

To add animations to a **custom item** (turn on/turn off, custom action):

- **Inherit/override an existing anim instance** instead of creating ASI from scratch.
- Modify only the new state and leave the rest of the hierarchy intact.
- Caution: locomotion and additive inherited from parent ASI are **delicate**; they can break when overwriting.

### 3.8 Known system limits [VERIFIED-source]

As of 2024-03-30 they were not resolved:
- **Dual wielding** (two weapons at once).
- **Bow** (the full bow mechanic).
- Customized **additive locomotion** (modifying the additive layer of walk/run easily breaks the character visually).

If your plan touches this, mark as high risk in `assumptions.md` from day 1.

### 3.9 Blender version — [VERIFIED-source unverified]

The video recommends **Blender 3.6.8** because the sample `.blend` files were made there; another person reported that **Blender 4.1** broke with the DayZ animation plugin. Vault has no independent confirmation. **If you are going to start seriously**: start with 3.6.8, leave a quick test in 4.x before closing.

### 3.10 Player skeleton — bone map [VERIFIED-vanilla]

From `DZ/anims/cfg/skeletons.anim.xml` (production skeleton + `player_testing.xob`). Organized by zone to use as reference when mapping Blender armatures → DayZ.

**Core / spine**
- `Scene_Root`, `EntityPosition`, `Pelvis`, `Spine`, `Spine1`, `Spine2`, `Spine3`, `Neck`, `Neck1`, `Head`, `LookAt`

**Legs** (symmetric left/right)
- `LeftUpLeg`, `LeftUpLegRoll`, `LeftKneeExtra`, `LeftLeg`, `LeftLegRoll`, `LeftFoot`, `LeftToeBase`
- + `Right*` equivalents
- Hip helpers: `LeftHipExtra`, `RightHipExtra`, `LeftHip_Helper`, `RightHip_Helper`

**Arms** (symmetric)
- `LeftShoulder`, `LeftArm`, `LeftArmRoll`, `LeftForeArm`, `LeftForeArmRoll`, `LeftHand`
- + `Right*` equivalents (+ `RightArmExtra`)
- Hand helpers: `LeftHand_Dummy`, `LeftWristExtra`, `LeftForeArmExtra`, `LeftElbowExtra`, `LeftArmExtra` (+ `Right*`)

**Fingers** (lod 2)
- `[Left/Right]Hand[Ring/Pinky/Middle/Index/Thumb]1..4`

**IK helpers** (critical for weapon authoring)
- `RightHandOrigin`, `LeftHandOrigin`, `LeftHandIKTarget`, `LeftHandIK`, `RightHandIK`
- `LeftForeArmDirection`, `RightForeArmDirection` (+ Origin variants)

**Weapon attachment / interaction**
- `Weapon_Root` (ancla principal del arma)
- `Weapon_Bullet`, `Weapon_Trigger`, `Weapon_Magazine`, `Weapon_Bolt`
- `Weapon_Bone_01..06` (slots configurables)
- `Weapon_Holster`, `Pistol_Holster`, `Weapon2hnd_Holster`
- `weapon` (lowercase, legacy compat)

**Face** (lod 2)
- `Face_Hub`, `Face_Jawbone`, `Face_Chin`, `Face_Eyelids`, `Face_Forehead`
- `Face_Brow*`, `Face_Lip*`, `Face_Cheek*`, `Face_Tongue`
- `EyeLeft`, `EyeRight`

**Misc / system**
- `Opponent`, `Camera3rd_Helper`, `Camera1st_lock_dummy`, `Marker`

**Legacy / to-be-removed** (DO NOT use — they are marked `<!--To Be removed-->` in `player_testing.xob`)
- `Bullet`, `Trigger`, `Magazine`, `Bolt`, `Bullets_Magazine`, `Bullets_holder`, `Bullets_on_holder`, `Universal1`, `Universal2`

---

## 4. Anim instances and the override pattern

[VERIFIED-source] The idiomatic way to add or change an animation in DayZ for a custom item is:

1. Find the vanilla anim instance closest to what you want.
2. **Inherit/override** that instance, do not create from scratch.
3. Change only what is necessary (state ID, anim file, transition).
4. Leave the rest of the ASI touching the minimum.

Cross-ref Layer 1 of the skill ([`item-ik-and-hide.md`](skills-drafts/dayz-animation-pipeline/references/item-ik-and-hide.md)): pattern A "carry IK reusing vanilla `.anm`" is the already-verified version of this same principle for heavy items (wheel/door/barrel).

---

## 5. AI behavior wiring (ambient creature without aggression)

[VERIFIED-source] For a seagull-type ambient animal (non-aggressive, does not waste CPU):

- Copy the hen or vanilla ambient life AI agent template.
- Configure team / friendliness so it does not fight.
- Give minimal inventory, skinning component, hit components.
- If the creature is a predator (aggressive) copy from vanilla wolf/bear, adjust attack range.

Much of this is **scantly documented officially**, according to the video. The strategy is: clone nearest vanilla, change the minimum, iterate.

---

## 6. Skill echo: what we do NOT repeat here

To avoid duplicating knowledge (R20 incidental anti-refactor, R25 simplicity), this is NOT duplicated from the skill — read it there:

- Wall "only one animation mod at a time (player/creature)": skill `SKILL.md` § anchor 3, [`references/tooling-and-walls.md`](skills-drafts/dayz-animation-pipeline/references/tooling-and-walls.md) § "The walls".
- Player bone names must match `OFP2_ManSkeleton` exact: skill [`references/skeletal-anm-enfusion.md`](skills-drafts/dayz-animation-pipeline/references/skeletal-anm-enfusion.md).
- Pipeline `.txa` → Workbench → `.anm`, `SEAnim` → DayZATool → `.anm`: skill same references.
- Complete `AddItemInHandsProfileIK` API for heavy items with reused IK: skill [`references/item-ik-and-hide.md`](skills-drafts/dayz-animation-pipeline/references/item-ik-and-hide.md).
- `model.cfg` structure (CfgSkeletons + CfgModels + class Animations + properties): skill [`references/config-driven-animation.md`](skills-drafts/dayz-animation-pipeline/references/config-driven-animation.md) and `dayz-model-pipeline/references/animations.md`.
- Hide-on-attach pattern (`type="hide"`, `hideValue`): skill same doc, with [TBD-verify] on the exact threshold.
- LL-012: animating proxy sub-piece requires separating it + derived mod needs its own `.p3d` + `model.cfg`.

---

## 7. Verification status and pending items

**Sprint 2026-05-28** promoted most claims from [TBD-verify-vanilla] to [VERIFIED-vanilla] using unpacked `DZ/`, `SurvivorAnims/`, and `0_SurvivorAnimsDefines/`.

**Verified (path:line in vanilla)**:
- §1.2 creature bones (`EntityPosition`, `LookAt` — without `Pin`)
- §1.3 skeleton XML (`skeletons.anim.xml`, without explicit entry in config.cpp)
- §2.1 commands (`CMD_*` UPPER_SNAKE, actual casing)
- §2.2 variables (`speed`, `SlopeAngle*` confirmed; `swimming` only as player tag, not animal var)
- §2.4 terrain alignment (`AnimNodeRot` with `SlopeAngleX * 0.01745329`)
- §3.1 ASI structure + complete catalog
- §3.2 `RightHand_Dummy` / `LeftHand_Dummy` (without mag bones in production)
- §3.3 weapon states (`FireCocked`, `ReloadMagazineDetach` — without `BulletChambered`)
- §3.4 Workbench Animation Editor (`#eventtable` mechanism)
- §3.10 player skeleton (complete bone map)

**Refuted by vanilla**:
- §3.5.bis reload is NOT additive (additive modifiers are for sickness, not reload)
- §2.2 `swimming` is not a standalone var in animal graphs
- "Pin Look At" — `Pin` does not exist in vanilla
- `cmd success` alone — actual command is `CMD_AttackSuccess`
- `BulletChambered` — does not exist as state, chambering is done by command

**Still UNKNOWN (not detectable in vanilla text files)**:
- §3.5 30 fps default for player anims — embedded in binary `.anm` or exporter convention. Assume 30 + round-trip test.
- §3.9 Blender 3.6.8 vs 4.1 — vault has no independent confirmation. Test.

**Operational pending items**:
1. **Pipeline roadmap**: this knowledge is already solid — consider proposing APPEND to skill `dayz-animation-pipeline` with a new `references/anim-graph.md` (covers `CMD_*` commands, graph variables, terrain alignment, ASI structure). Pass through R34 (proposal to user, do not auto-apply).
2. **Patch queue**: register in [`20_Knowledge/skill-patches-pending.md`](skill-patches-pending.md) the proposed patch to `dayz-animation-pipeline` if decided to do so.

---

## 8. Provenance and links

**Verification against vanilla (sprint 2026-05-28)** — primary source of promotions to [VERIFIED-vanilla]:
- `DZ/anims/cfg/skeletons.anim.xml` — all bones of §1.2, §3.2, §3.10
- `DZ/animals/animations/!graph_files/{ambientlife,herbivores,wolf}/*.agr` — commands §2.1, variables §2.2, terrain alignment §2.4
- `DZ/anims/workspaces/player/player_main/*.asi` + `weapons/*.asi` — ASI structure §3.1, weapon states §3.3
- `SurvivorAnims/animgraph/player_main/{combat,locomotion,player_main}.agr` — player commands §2.1, additive refutation §3.5.bis
- `DZ/anims/workspaces/player/player_main/player_main.aw` vs `SurvivorAnims/animgraph/player_main/player_main.aw` — diff `#eventtable` §3.4

**Procedencia original (videos procesados por Codex 2026-05-28)**

- Tree, "DayZ Basic Animations Tutorial", 2026-02-14, 22:31 — [`video-transcripts/dayz-modding/2026-02-14-tree-dayz-basic-animations-tutorial.md`](video-transcripts/dayz-modding/2026-02-14-tree-dayz-basic-animations-tutorial.md)
- hunterz688, "DayZ Custom Animations Introduction", 2023-06-02, 01:29:26 — [`video-transcripts/dayz-modding/2023-06-02-hunterz688-dayz-custom-animations-introduction.md`](video-transcripts/dayz-modding/2023-06-02-hunterz688-dayz-custom-animations-introduction.md)
- hunterz688, "DayZ Animation workshop vol.2", 2023-12-22, 01:46:07 — [`video-transcripts/dayz-modding/2023-12-22-hunterz688-dayz-animation-workshop-vol-2.md`](video-transcripts/dayz-modding/2023-12-22-hunterz688-dayz-animation-workshop-vol-2.md)
- hunterz688, "DayZ Animation Workshop vol.3", 2024-03-30, 01:34:18 — [`video-transcripts/dayz-modding/2024-03-30-hunterz688-dayz-animation-workshop-vol-3.md`](video-transcripts/dayz-modding/2024-03-30-hunterz688-dayz-animation-workshop-vol-3.md)
- handoff from the session that processed the videos: [`30_Sessions/2026-05-28-dayz-animation-video-notes.md`](../30_Sessions/2026-05-28-dayz-animation-video-notes.md)
- skill `dayz-animation-pipeline` (installed): covers Layer 1/2/3, the two walls, heavy ASI.
- skill `dayz-model-pipeline/references/animations.md`: complete `model.cfg` structure with `isDiscrete`.
- lessons-learned LL-012 (proxy sub-piece animation).

---

## Support hand orientation: GEOMETRIC, not wrist rotation of the ikpose [VERIFIED-ingame 2026-06-17, A6_SR2M]

Tested in-game (A6_SR2M, custom SMG without hand memory points, AKS74U anims; iter17–22 retail, orbit
capture): **rotating the `LeftHand` bone (wrist) in the ikpose does NOT reorient the support hand.** The ASI/IK
realigns the hand to the weapon and absorbs wrist rotation. 4 variants with `LeftHand` at 90° on different axes
(120–180° to each other) render EQUAL in-game; pixel-diff of the hand zone: 180° roll =
RMS 7.8, LESS than a finger curl change (RMS 11). The only thing from the ikpose that visibly applies
is the **finger curl** (`LeftHand{Thumb,Index,Middle,Ring,Pinky}*`), not wrist orientation.

Actual mechanism (cf. `skills-plugin: dayz-animation-pipeline/references/weapon-in-hands.md` — the vanilla
AKM has 0 hand memory points): the support hand is posed by the reference `.anm` anchored to the weapon origin
(`Weapon_Root`/`RightHand_Dummy`); what decides where/how it falls is the **geometric parity**
weapon↔reference-anim, not the ikpose. `weapon_grip_viewer.py` quantifies the gap (SR2M vs
`aks74u_vanilla_mlod`: bore aligned 0°, but weapon ~3 cm lower + shorter barrel → hand high/forward,
horizontal handguard palm, not vertical foregrip palm).

**Corrects an over-generalization:** a diff of two vanilla ikposes of the SAME weapon (OTS-14 `normal` vs
`barrelhandle`) shows a `LeftHand` delta (24.8°), but that delta exists because both poses were
authored against a weapon WITH parity — does NOT imply that rotating `LeftHand` on a weapon without parity reproduces
the orientation. For vertical palm on a custom foregrip: geometric parity with an anim whose hand already
falls vertically (verify with `weapon_grip_viewer.py`), or weapon geo/offset adjustment — not rotating the ikpose.

---

## RESOLVED 2026-06-23: the grip closes by RAISING the weapon (idle AND aim) [VERIFIED-ingame + gate]

Closing of the line above. The lever that works is NOT rotating the ikpose or wrist, but **raising/
translating the WEAPON up to where the anim poses the support hand**. Empirical RE of a working mod
(KarmaKrew, workshop 2864245850; Vikhr/SR-2M weapons) confirmed: they achieve grip with VANILLA IK-driven ikposes
(`vikhr.anm`, `pm73_ik.anm`) + behavior firearms + **geometry parity**, without player anim mod, without
base pose override, without scripted bones.

- **The number:** the SR2M bore was 2.4 cm lower above weapon origin than KK reference
  (Y0.066 vs 0.090) → the anim's hand fell ON TOP of the barrel. Translating the ENTIRE model +Y0.024 (global-offset
  pattern; bore 0.066→0.090) raises the weapon to the hand and closes the grip. Heuristic: if anim
  levers (ikpose pos/rot, behavior, LeftHand FK) turn out inert, **move the WEAPON, not the anim**.
- **Closes BOTH stances.** The ikpose is shared idle↔aim and it was feared that closing idle would leave aim
  open (aim-space additive opens the hand). Empirically it did not happen: the same raised weapon closed idle
  (validated in-game, shipped) AND aiming (gate iter37, 3rd person, comparable to KK). The `.asi`
  per-stance override remains as FALLBACK, not needed here.
- **Capturing the aim pose to validate (MCP tool):** force raise **CLIENT-side** (`modded
  MissionGameplay` on `GetGame().GetPlayer()` → `OverrideRaise(ENABLED,true)`), NOT in server
  `init.c` — the captured character is the client's local player and server overrides do not move its
  render (gate iter36: server `raised=1` but weapon lowered). `WeaponADS()` is input flag (without script
  override) → erroneous success metric; use `IsRaised()` / client log. Not `SetIronsights()` (fights with
  free-cam). 3rd person aim pose depends only on `IsRaised()` (`dayzplayerimplement.c:1726`,
  AimingModel).
- **Judge by the hand at NATIVE resolution**, never rescaled contact-sheet (the ~30px hand is deceptive; a
  good grip was declared "inert" from looking at thumbnail).

Detalle con citas: skill `dayz-animation-pipeline/references/weapon-in-hands.md` (§"Geometric parity IS the
grip fix") + skill `dayz-mcp-verify` (§"capturar arma alzada"). Proyecto A6_SR2M:
`research\2026-06-22-karmakrew-vikhr-RE-grip-mechanism.md`, `HANDOFF.md`.

## Related

- [[dayz-custom-infected]] — rigging a creature/zombie to OFP2_ManSkeleton; uses the bones and anim graph that this note details.
- [[dayz-capacidades-verificadas]] — feasibility verdict of the animation pipeline (two systems, walls, Windows tools).
- [[dayz-model-pipeline]] — the named selection + memory points that are animated are authored here (geometry side `.p3d`).
- [[dayz-p3d-inspector-memory-selection-bugs]] — ODOL reader loses Memory LOD selections (anim axes) upon debinarizing.
- [[dayz-mod-implementation-checklists]] — checklist of model.cfg / config.cpp for animated entities.
