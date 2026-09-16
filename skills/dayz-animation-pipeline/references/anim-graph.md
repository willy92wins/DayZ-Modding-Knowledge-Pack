# Anim graph, state machines, commands & ASI structure (sprint 2026-05-28)

The animation **graph** is the layer DayZ uses to drive characters and creatures: state machines, transitions, commands fired by the engine/AI/script, variables that conduct blending, and the **ASI** (animsetinstance) catalog that maps state names to `.anm` files. This reference covers the parts of that system that you can read in plain text from vanilla unpacked data — and refuses the parts that don't exist.

All `[VERIFIED-vanilla]` items below were greped directly against the unpacked vanilla in `DZ/` + `SurvivorAnims/` (sprint 2026-05-28). Cross-ref vault: `20_Knowledge/dayz-animations-creatures-weapons.md`.

## Where the source of truth lives in vanilla

| Topic | Vanilla path | Format |
|---|---|---|
| Player master graph index (1.30 Exp) | `DZ/anims/workspaces/player/player_main/player_main.agr` (added 2026-09-16, DayZ 1.30 Exp) [EXACT] | text (`AnimSrcGraph` with `GraphFilesResourceNames` at `player_main.agr:1587`) |
| Player sub-graphs (Locomotion, Vehicles, Actions, Combat...) | `DZ/anims/workspaces/player/player_main/*.agf` (added 2026-09-16, DayZ 1.30 Exp) [EXACT] | text Enfusion Config (`AnimSrcGraphFile`); in 1.29 these were binary `.agr` |
| Player commands + transitions (pre-1.30 source) | `SurvivorAnims/animgraph/player_main/*.agr` | text |
| Animal/infected/predator graphs | `DZ/animals/animations/!graph_files/<species>/*_graph.agr` | text |
| Skeleton LOD and missing bones | `DZ/anims/cfg/skeletons.anim.xml` (added 2026-09-16, DayZ 1.30 Exp) [CHANGELOG] | XML (`lod` attribute only; 250 bone limit removed) |
| ASIs (player + props + weapons) | `DZ/anims/workspaces/player/player_main/` | text (`$animsetinstance`) |
| Event table | `DZ/anims/workspaces/player/Player_EventTable.ae` | text |
| Workspaces | `DZ/anims/workspaces/player/player_main/*.aw` (compiled), `SurvivorAnims/animgraph/player_main/*.aw` (source) | text |

You can `grep` all of these in-sandbox if the vanilla data is unpacked on the user's `P:\`. The `.anm` files themselves are binary — leave them to DayZATool / Workbench.

## Commands — `CMD_*` UPPER_SNAKE [VERIFIED-vanilla]

Casing is real and exact: prefix `CMD_`, `UpperCamel` suffix. Community tutorials and video transcripts often render these as `cmd death` or `cmd_death` — **wrong**, use the column from the table.

### Animal commands

Source: `DZ/animals/animations/!graph_files/ambientlife/ambientlife_graph.agr`. Same set appears in herbivores/predators/wolf graphs.

| Command | Triggers |
|---|---|
| `CMD_Death` | death state |
| `CMD_LookAt` | head/look tracking towards target |
| `CMD_LookAtXChange` | sub-command for look-at axis change |
| `CMD_Attack` | enter attack state |
| `CMD_AttackSuccess` | attack connected → apply damage. **There is no `CMD_Success` alone** — community tutorials get this wrong |
| `CMD_Hit` | recv hit |
| `CMD_AnimCallBack` | generic event callback |

### Player commands

Source: `SurvivorAnims/animgraph/player_main/{combat,locomotion,player_main}.agr`.

| Command | Triggers |
|---|---|
| `CMD_WeaponFire` | weapon fire (value 2 = fire while cocked-empty, see `combat.agr:850`) |
| `CMD_Reload_Magazine` | full magazine reload |
| `CMD_Reload_BoltAction` | bolt-action reload |
| `CMD_Reload_Chambering` | chamber a round |
| `CMD_Reload_ChamberingFast` | fast chambering variant |
| `CMD_Reload_Clip` | clip reload |
| `CMD_Modifier_Additive` | **state modifier** for sickness/cough/sneeze (`locomotion.agr:3959-3976`). **NOT for reload** — see the refutation below |

## Variables — `#Var` declarations [VERIFIED-vanilla]

Animal graphs declare variables with `#Var <name> <type> <default> <min> <max> ""`. Examples from `herbivores_graph.agr`:

- `#Var speed float 0.0 0.0 5.0 ""` — used by the locomotion blend tree.
- `#Var SlopeAngleX float 0.0 -90.0 90.0 ""` — provided by the engine, drives terrain alignment.
- `#Var SlopeAngleZ float 0.0 -90.0 90.0 ""` — same.

`swimming` is **NOT** a `#Var` in any animal graph. In the player it appears as a state tag (`TagSwimming`, `SwimmingMaster` in `locomotion.agr`), not as a numeric variable. Community tutorials that treat `swimming` as a creature variable are inventing it.

## Terrain alignment [VERIFIED-vanilla]

There is no special "terrain alignment node". It's an `AnimNodeRot` that consumes `SlopeAngleX/Z` multiplied by `0.01745329` (= π/180, degrees → radians):

- Wolf: `wolf_maingraph.agr:3` — `"AlignToTerrain_Rot" "" "Master_SM" "SlopeAngleX * 0.01745329..."`
- Herbivores: `TerrainRot_Deers`, `TerrainRot_CowAndBull`, `TerrainRot_BoarAndPig`, `TerrainRot_SheepAndGoat` — same shape.

For a new creature, **copy the formula from the vanilla animal closest in proportions** (large quadruped → cow, medium → boar, small → sheep). Don't reinvent.

## ASI — `$animsetinstance` structure [VERIFIED-vanilla]

ASIs map `StateName.SubName.Phase` → `{GUID}path.anm`. They form a parent chain (one base `.asi` + children that override). Example from `DZ/anims/workspaces/player/player_main/player_main_rifle.asi:1-6`:

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

- `#template` → the `.ast` (animset template) that defines which states this instance can populate.
- `#parent` → another `.asi` to inherit from. `player_main.asi` is the root of the player chain.
- `$animations` → the state-to-anm mapping. State path is dotted: `Category.SubCategory.StateName`.

### Player ASI catalog [VERIFIED-vanilla `DZ/anims/workspaces/player/player_main/`]

| ASI | Purpose |
|---|---|
| `player_main.asi` | base / root parent for all |
| `player_main_1h.asi` | one-handed items/weapons |
| `player_main_1h_restrained.asi` | one-handed + restrained |
| `player_main_2h.asi` | two-handed items/weapons |
| `player_main_heavy.asi` | heavy items (wheel/door/barrel) — target of `AddItemInHandsProfileIK` for heavy |
| `player_main_pistol.asi` | pistols |
| `player_main_rifle.asi` | rifles |
| `player_main_bow.asi` | bow (partial, see vol.3 caveat — additive locomotion unfinished) |
| `player_main_surrender.asi` | hands up |
| `menu_rifle.asi` | rifle in menu/preview |
| `props/*.asi` | 30+ ASIs, one per prop |
| `weapons/*.asi` | one per specific weapon (`player_main_akm.asi`, `player_main_1911.asi`, ...) |

### Weapon state path convention [VERIFIED-vanilla]

Weapon-specific ASIs use `WeaponOperations.<RigKey>.<StateName>` where `<RigKey>` encodes pose + rail accessory system (e.g. `ErcRas` = erected + rail-accessory).

Example (`weapons/player_main_1911.asi`):

| State path | Maps to |
|---|---|
| `WeaponOperations.ErcRas.FireCocked` | `p_erc_empty_cocked_1911_ras.anm` |
| `WeaponOperations.ErcRas.ReloadMagazineDetach` | `p_erc_reload_mag_remove_1911_ras.anm` |

Real state names corrected from community/video tutorial naming:

| Tutorials call it | Real state | Notes |
|---|---|---|
| "weapon cocked" | `FireCocked` | fired while cocked-empty |
| "mag remove" | `ReloadMagazineDetach` | the `.anm` filename has `_mag_remove_` but the state name is `ReloadMagazineDetach` |
| "bullet in chamber" | **no such state** | chambering uses commands (`CMD_Reload_Chambering`, `CMD_Reload_ChamberingFast`), not a state name |

## Vehicles.agf & Enfusion .agf format (added 2026-09-16, DayZ 1.30 Exp) [EXACT]

Starting with DayZ 1.30 Exp, the player sub-graphs live in `.agf` text files (`AnimSrcGraphFile`) referenced by `GraphFilesResourceNames` in `player_main.agr:1587`. The vehicle graph `DZ/anims/workspaces/player/player_main/Vehicles.agf` (3654 lines) is the reference implementation. Extraction root for the citations below: `E:\DayZ-Exp-Extract\1.30.164014\exp\anims_workspaces\DZ\anims\workspaces\player\player_main\`.

```
// Vehicles.agf:1564-1576
AnimSrcNodeBlendT MotorBikeB {
 EditorPos 4 -18.3
 BlendTime "0.3"
 BlendFn S
 Condition "VehicleType == 10 || VehicleType == 11"
 Child0 "VehicleSTM"
 Child1 "MotorBikeSTM"
 OptimizeMin 1
 OptimizeMax 1
 SelectMainPath 0
}
```

Node types seen in the file (each with the line where the first instance starts):
- `AnimSrcNodeBlendN`: multi-input threshold blend (`BlendWeight "VehicleSpeed"`, `Thresholds { 3.5 8 }`, `Vehicles.agf:5-16`).
- `AnimSrcNodeBlendT`: conditional transition selector (`Condition`, `BlendTime`, `Child0`/`Child1`, `Vehicles.agf:1564`).
- `AnimSrcNodeBlend`: continuous 2-input formula blend (`MotoYIntertiaB`, `Vehicles.agf:1556`).
- `AnimSrcNodePose`: 1D static pose evaluated along its timeline by a variable (`Vehicles.agf:47-51`).
- `AnimSrcNodeStateMachine`: hierarchical state machine with `states { AnimSrcNodeState ... }` and `transitions { AnimSrcNodeTransition ... }` (`MotorBikeSTM`, `Vehicles.agf:1582-1750`).
- `AnimSrcNodeIK2Target` and `AnimSrcNodeIK2`: two-bone IK pinning the driver's hands to the handlebar (`AnimNodeIK2Target0` at `Vehicles.agf:17`, `AnimNodeIK2hands` at `:31`).
- `AnimSrcNodeSourceSync`: clip playback bound to a sync line (`Vehicles.agf:69-80`).

`MotorBikeSTM` rider states: `Idle`, `GetIn_L`, `GetIn_R`, `GetOut_L`, `GetOut_R`, `JumpOut_L`, `JumpOut_R`, `Death`, `GettingInDeath` (`Vehicles.agf:1582-1750`); transitions test integer direction flags (`GetCommandI(CMD_Vehicle_GetIn) == 0` left, `== 1` right). The `.agr` of 1.29 was binary; diffing a 1.30 `.agf` against a 1.29 graph is therefore not possible in text.

## Reload is NOT additive in vanilla [REFUTED-vanilla]

Some community tutorials say "reload is an additive animation: only torso/shoulders, the rest is handled by another layer". Vanilla does not confirm this:

- `CMD_Modifier_Additive` (in `player_main.agr:47` and applied in `locomotion.agr:3959-3976`) drives **sickness/cough/sneeze** state modifiers (`SickSneezeStanceSTM`, `SickCoughStanceSTM`). Nothing about reload.
- Reloads use dedicated commands without an additive flag: `CMD_Reload_Magazine`, `CMD_Reload_BoltAction`, `CMD_Reload_Chambering`, `CMD_Reload_ChamberingFast`, `CMD_Reload_Clip`.
- There is no `AnimNodeAdditive` or `TagAdditive` for reload in the player animgraph.

The tutorial may be describing authoring convention in Blender (only animate torso/arms during reload, leave legs to locomotion) — not a runtime additive system. When you author a custom reload, look at the vanilla weapon graph closest in feel and copy how it transitions in/out of the state; don't assume the engine will mix layers for you.

## Workbench Animation Editor — the `#eventtable` line [VERIFIED-vanilla]

Tutorials say "to load the Player Animation Editor in Workbench you have to edit the player graph and remove an event table line". Mechanism confirmed:

- **Compiled workspace** `DZ/anims/workspaces/player/player_main/player_main.aw:136` contains:
  ```
  #eventtable "{3037156104937B91}DZ/anims/workspaces/player/Player_EventTable.ae"
  ```
- **Source workspace** `SurvivorAnims/animgraph/player_main/player_main.aw` does NOT have that line.

To edit the player graph in Workbench Animation Editor: take a `.aw` that has `#eventtable`, delete that line, and the editor will open. Workbench/Workshop re-binds the `.ae` on export/compile.

(added 2026-09-16, DayZ 1.30 Exp) [CHANGELOG] In 1.30 the Workbench Animation Editor moved to the 2021 Enfusion editor with live editing of a running graph and a "Show In Explorer" context action; `Buffer Save` / `Buffer Use` nodes and the default unnamed group of animation set templates were removed. [EXACT] The 1.30 `player_main.aw:15` declares its event table directly: `EventTable "{3037156104937B91}DZ/anims/workspaces/player/Player_EventTable.ae"`. [UNVERIFIED] Whether the `#eventtable` deletion trick is still needed with the 2021 editor has not been tried on this host.

## Building a creature anim graph — minimal-first workflow

1. Create the graph + state machine with **one state** (idle) and **one anim source** (one `.anm`).
2. Set up the creature in-game with a minimal `model.cfg` (geometry, mass, basic FireGeo). Cross-ref `dayz-p3d-audit` and `dayz-model-pipeline`.
3. Confirm the creature spawns, plays idle, does not crash. **Only then** add walk → run blending by `speed`, terrain alignment, hit, death, attack/success.

Building the whole graph offline and discovering the bug on first spawn is the recurring failure mode — incremental validation is the only protection.

## Creature special bones [VERIFIED-vanilla]

See `references/player-skeleton.md` for the full bone catalog. The two creature-critical bones referenced by anim graphs:

- `EntityPosition` (`skeletons.anim.xml:4`, `movement="true"`) — the bone the engine reads for predicted entity displacement. Animal graphs reference it explicitly, e.g. wolf uses `"PredictionTurn" "EntityPosition"`.
- `LookAt` (`skeletons.anim.xml:18`) — head/look tracking. The name is literally `LookAt`, not `Pin Look At` or `PinLookAt`.

## Animation tags and HumanAnimInterface.IsTag (added 2026-09-16, DayZ 1.30 Exp) [EXACT]

DayZ 1.30 lets script query the active animation-graph tags on the fixed tick via `HumanAnimInterface.IsTag` (`3_Game/human.c:318-319`):
```c
// E:\DayZ-Exp-Extract\1.30.164014\exp\scripts\scripts\3_Game\human.c:318-319
proto native TAnimGraphTag 			BindTag(string pTagName);
proto native bool                   IsTag(TAnimGraphTag iTag);
```

In the graph, states declare tags with a `Tags { "TagName" }` block. In `Vehicles.agf`: `TagVehicleGetIn` in `GetIn_L` / `GetIn_R` (`Vehicles.agf:1594, 1614`) and `TagVehicleGetOut` in the get-out / jump-out states (`:1604, 1624, 1634, 1651`). Transitions consume them, e.g. the driver death animation is blocked while boarding is in progress: `Condition "IsCommand(CMD_Death) && !IsTag(\"TagVehicleGetIn\")"` (`Vehicles.agf:1719`). [DESIGN] Script can cache the handle with `BindTag("TagVehicleGetIn")` and poll `IsTag(handle)` on the fixed tick to sync gameplay with an animation phase; no vanilla script caller was found in this extraction, so treat the usage pattern as a proposal.

## What this reference does NOT cover

- The exact `.ast` template grammar — vanilla `.ast` files exist but the dialect is not fully documented; treat them as schemas to be copy-edited from the closest vanilla example.
- Player animation **FPS** — not declared in any text file under `SurvivorAnims/animgraph/` or `DZ/anims/workspaces/`. Probably baked into the `.anm` binary or set by the exporter. Convention reported by tutorials is 30 fps; assume that and round-trip-test before committing a full set.
- Binary `.anm` / `.xob` internals — out of scope; route via DayZATool / Workbench.

## [2026-06-28] Weapon-anim corrections (verified vs dayzplayer.c / human.c)

### The one-anim-mod wall does NOT apply to weapon anims via the ASI route [VERIFIED-vanilla]

The "only one mod modifying player/creature animations at a time" wall (in this skill's anchor 3, `tooling-and-walls.md` wall #1, and `skeletal-anm-enfusion.md`) applies ONLY to mods that REPLACE the player animation graph (`player_main.aw`/`.agr`, e.g. Expansion-Animations). A custom-weapon animation authored via the ASI route does **NOT** touch the graph and is therefore **conflict-free across mods** — multiple weapon-anim mods coexist.

Why: a player weapon animation reaches the engine through three decoupled layers, none of which edits `.agr`/`.aw`:
1. Author `.txa` → Workbench `.anm`.
2. A per-weapon `.asi` (`$animsetinstance`) maps `WeaponOperations.<RigKey>.<State>` → your `.anm`, inheriting the parent chain (`your.asi` → `player_main_rifle.asi` → `player_main.asi`).
3. Enforce Script `AddItemInHandsProfileIK(itemClass, asi, behavior, ikPose.anm, weaponStates.anm)` binds the weapon classname to the `.asi` + a one-time IK pose + a weapon-states `.anm`; `AddItemBoneRemap(itemClass, pairs[])` maps the weapon's part selections to the player's `Weapon_*` bones.

Because binding is per-item via these script calls (not a graph replacement), each weapon mod registers its own items independently. (`dayzplayer.c:243` `AddItemInHandsProfileIK` 5-arg; `dayzplayercfgbase.c:382,411`; refuted the "needs a full player-anim mod" pessimism. Vehicles are the unsupported exception.) When the user's plan is a custom WEAPON animation, do NOT warn about the one-anim-mod wall — it is a false blocker here.

### Weapon-states `.anm` is 2–4 keys/channel, not "exactly 3 frames" [VERIFIED-vanilla]

The 3-frame closed/open/jammed is the AUTHORING intent (one frame per init state); Workbench TRIMS near-identical consecutive keys, so the stored per-channel keycount across 47 vanilla `w_*_states.anm` is 2, 3 or 4. `w_akm_states.anm` = 2 distinct frames @30fps (`Weapon_Bolt` slides f0→f1, `Weapon_Bullet` ejects). All player weapon reload/fire/jam/state/ikpose anims are authored at framerate 30.0; `frame_count = last-key-index + 1`. See `references/weapon-anim-blender-complete.md` for the full AKM frame budget.

### ikpose_* keys live in the WeaponIK graph node, not player_main.ast [VERIFIED-vanilla]

The `ikpose_chainoffset`/`ikpose_weaponoffset`/`ikpose_secchainoffset`/`ikpose_chainmiddledir`/`ikpose_secchainmiddledir` keys (plus two omitted by community sources: `ikpose_chainmiddlediro`, `ikpose_secchainmiddlediro`) are parameters of the `AnimNodeWeaponIK` node in the `.agr`/compiled `.aw` graph — `DZ/anims/workspaces/player/player_main/combat.agr:24-30`, 14× across 6 `.agr` files. They are NOT in `player_main.ast`/`.aw` top-level (a grep there returns 0) and NOT in config.cpp/model.cfg. They are explicit IK-role→bone mappings, identical in every vanilla occurrence. Full block in `references/weapon-anim-blender-complete.md`.
