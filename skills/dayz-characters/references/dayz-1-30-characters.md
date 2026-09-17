# DayZ 1.30 Exp — humanoid character delta (build 1.30.164014)

Companion to `dayz-characters` SKILL.md. Mesh/rig/LOD rules in the parent skill still hold. This file is the 1.30 overlay: new classes, graph format, PPE, skinning, surrender.

## Infected class additions

Hierarchy `DZ_LightAI → DayZInfected → ZombieBase → ZombieMaleBase / ZombieFemaleBase → variants` is still the inherit path.

(desde 1.30 Exp) Female military CfgVehicles (`exp/characters_zombies/DZ/characters/zombies/config.cpp`):

- `ZmbF_SoldierNormal_Base: ZombieFemaleBase` — `:10376` (`model = "\DZ\characters\zombies\ZmbF_SoldierNormal.p3d"`, `aiAgentTemplate = "InfectedMSoldier"`)
- `ZmbF_SoldierNormal: ZmbF_SoldierNormal_Base` — `:10600` (`scope = 2`)
- `ZmbF_ArmyOfficer: ZmbF_SoldierNormal_Base` — `:10605` (`ArmyOfficer_fat_f.p3d`, `InfectedSoldier_Officer`)
- `ZmbF_eastSoldier_Base: ZmbF_usSoldier_normal_Base` — `:10828` (config parent is the US female soldier base, not `ZombieFemaleBase` directly)
- `ZmbF_eastSoldier_Normal_Navy` / `ZmbF_eastSoldier_Heavy_Navy` — `:11050`, `:11055`

Script bases (`exp/scripts/scripts/4_World/Entities/Creatures/Infected/`):

- `ZmbF_SoldierNormal_Base` / `ZmbF_eastSoldier_Base` extend `ZombieFemaleBase` and `IsZombieMilitary()` (`ZombieFemaleBase.c:139-152`)
- Nasdara male: `ZmbM_takiCitizenUrbanA_Base` … (`ZombieMaleBase.c:160`)
- Nasdara female: `ZmbF_takiCitizenUrbanA_Base` … `ZmbF_takiOilRigWorker_Base` (`ZombieFemaleBase.c:163-188`) plus `Zmbf_IonSoldier_Normal_1` (`:155`)

[DESIGN] Inherit `ZombieFemaleBase` (or one of these 1.30 soldier bases) for a custom female military infected; do not invent a parallel AI driver.

## Infected animation graph: `.agr` index + `.agf` subgraphs

(hasta 1.29: `enfanimsys.graphname` pointed at a monolithic infected `.agr`.)

(desde 1.30 Exp: that path is still `dz\anims\workspaces\infected\infected_main\infected.agr` — re-verified `exp/characters_zombies/DZ/characters/zombies/config.cpp:50-57`. The `.agr` is now Enfusion `AnimSrcGraph` text. Subgraphs are `.agf` with root `AnimSrcGraphFile` (`exp/anims_workspaces/DZ/anims/workspaces/infected/infected_main/locomotion.agf:1`).)

```
// [EXACT] exp/anims_workspaces/DZ/anims/workspaces/infected/infected_main/infected.agr:430
 GraphFilesResourceNames {
  "{055B14354B447015}DZ/anims/workspaces/infected/infected_main/Locomotion.agf" "{809A284592397198}DZ/anims/workspaces/infected/infected_main/Combat.agf" "{A3A83C5CD5FE35F3}DZ/anims/workspaces/infected/infected_main/Interaction.agf"
 }
```

Listed as NEW in `work/pbo-listing-diff.txt:45`: `infected\infected_main\combat.agf`, `interaction.agf`, `locomotion.agf`.

**Migration:** a 1.29 custom infected workspace cannot be dropped in as-is. Official process ([CHANGELOG] tweet in `work/changelog-1.30-exp-modding.md:93`): open the old graph in Workbench 1.30 and re-save the workspace. Bohemia notes the converter was not tested.

**THE WALL** (one loaded anim-graph mod) still applies to *new* graphs. Inheriting vanilla `enfanimsys` still avoids it.

## `MINDSTATE_COWER`

`DayZInfectedConstants` adds `MINDSTATE_COWER` after `MINDSTATE_FIGHT` (`exp/scripts/scripts/3_Game/Entities/DayZInfected.c:12-18`). `ZombieBase` holds a calm idle pose when cowering (`ZombieBase.c:474-477`, comment: sandstorm cowering). [DESIGN] Custom infected AI that switches on mindstate must handle this new value or the infected will fall through the switch.

## New infected attack anims (binaries)

Not extracted under `exp\` (`.anm`). Existence only: `work/pbo-listings/exp__Addons__anims_anm_infected.txt:66,68`

- `attacks\erected\z_erc_run_attackL_Heavy.anm` (25534 bytes)
- `attacks\erected\z_erc_run_attackR_Heavy.anm` (25264 bytes)

[DESIGN] A custom infected that replaces the combat `.agf` should expect these heavy run-attack sources in vanilla 1.30.

## Human skinning: `Lard` removed

(hasta 1.29: `SurvivorBase` `class Skinning` included `class Lard { item = "Lard"; ... }` at `stable-1.29/characters_data/DZ/characters/data/config.cpp:133-138`.)

(desde 1.30 Exp: `Skinning` on `SurvivorBase` is Steaks / Guts / Bones / BloodInfectionSettings only — `exp/characters_data/DZ/characters/data/config.cpp:121-147`. No `Lard` class. Digest line `PlayerBase:337` is the pre-DeRap config.bin number; the extracted file puts this on `SurvivorBase`.)

## Surrender (no dummy item)

(desde 1.30 Exp: `Man.IsSurrendered()` at `exp/scripts/scripts/3_Game/Entities/Man.c:67`; `PlayerBase.SetSurrenderState(bool)` at `PlayerBase.c:2116`; `EmoteManager.ForceSurrenderState` is `[Obsolete("1.30: Use PlayerBase::SetSurrenderState instead")]` at `EmoteManager.c:1255-1258`.)

The parent skill never documented `SurrenderDummyItem`. Do not detect surrender by an item-in-hands classname.

## Sandstorm PPE and head-gear sun isolation

These sit on worn clothing, but they fire on the humanoid:

- `DEF_DUST_PARTICLE_BREATH = 3` and `DEF_DUST_PARTICLE_EYES = 4` (`exp/scripts/scripts/3_Game/constants.c:549-550`)
- Airborne solid agents: `eAgents.SILICOSIS = 512`, `eAgents.EYES_IRRITATION = 1024` (`EAgents.c:14-15`)
- `PluginTransmissionAgents` `AGT_AIRBOURNE_SOLID` uses `GetProtectionLevelCachedEquipment(DEF_DUST_PARTICLE_BREATH, MASK)` for silicosis and `DEF_DUST_PARTICLE_EYES` with `EYEWEAR|MASK|NVG` for eye irritation (`PluginTransmissionAgents.c:414-433`, helper `:577-594`)
- `Environment.HeadGearProtectionAgainstSun` reads `InventorySlots.HEADGEAR` heat isolation (`Environment.c:2037-2064`)
- Heat path: `HeatComfortMdfr` feeds `ThermalBiasHandler`; `HeatStrokeMdfr` has four stage thresholds `{0.0, 0.4, 0.6, 0.85}` (`HeatStroke.c:1-4`) plus `HeatStrokePhase1Mdfr`…`HeatStrokePhase4Mdfr`. Dust diseases: `SilicosisMdfr`, `IrritatedEyesMdfr`.

[DESIGN] A custom mask/helmet for a humanoid must set those protection types or sandstorm agents ignore the mesh. Full clothing slot rules live in `dayz-clothing`.

## Bone indices (rigging)

See `references/character-rigging.md` § DayZ 1.30 Exp. Short: 250-bone cap gone; XML `index` unused except `EntityPosition`; names must match the `.xob`.
