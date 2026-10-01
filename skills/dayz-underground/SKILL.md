---
name: dayz-underground
description: >
  Use when: terrain holes, terrain hole, SurfaceIsHole, CfgWorlds Holes, tiles[],
  holes.cfg, hole in the terrain, agujero o hueco en el terreno, underground area,
  zona subterránea, bunker, búnker, tunnel, túnel, trench, trinchera, cave,
  irrigation tunnel, cfgundergroundtriggers.json, UndergroundTrigger, breadcrumbs,
  EyeAccommodation, EUndergroundPresence, INPUT_UDT_UNDERGROUND_SYNC, underground
  trigger editor, disallowedTypesInUnderground, bunker broadcast,
  cfgbunkerbroadcast.json, Buldozer MarkUnderground or CopyTileCoord. DayZ 1.30 Exp
  (1.30.164014). Not construction parts, rebuilding or code locks: dayz-basebuilding.
  Not the bunker-broadcast storage file: dayz-persistence. Not sandstorm or heat:
  dayz-environment-hazards.
---

# DayZ Underground (1.30 Exp)

Underground areas in DayZ 1.30 Experimental (build 1.30.164014): the hole in the
terrain (*terrain holes*, new in 1.30), the underground triggers that darken and
change the environment, the player's "underground" state, and what Badlands builds on top
(radio-announced bunkers, irrigation tunnel entrance).

Citations `exp\scripts\scripts\…` are from `dta\scripts.pbo` of 1.30.164014, compared
with 1.29. Everything marked `source_verified` was opened in those files. **Nothing in
this skill has been tested in game yet**: §Verification Status states the level
of each claim and §Before designing with holes, how to raise it.

## The model: three pieces

| Piece | What it is | Where defined | Who uses it |
|---|---|---|---|
| Hole | heightmap cells without terrain | `CfgWorlds >> <world> >> Holes` (map config) | the engine, upon loading the world |
| Geometry | tunnel or bunker placed below the surface | `.wrp` (Terrain Builder), Object Spawner or script | the engine |
| Triggers | boxes that darken, alter sound, and flag "underground" | `cfgundergroundtriggers.json` | the server creates them, the client applies the effects |

The hole only removes terrain: it does not create any space. What happens if something falls through a
hole without geometry underneath is not measured; design as if there were no ground. Without
triggers, it does not darken inside.

## Terrain holes

### Formato

Among readable vanilla maps in 1.30.164014, only Livonia has holes (Chernarus does not;
Sakhal is encrypted): seven cells in two groups, next to the two entrances of the Dambog
bunker. The 1.29 config of the same map does not have them.

```cpp
// [EXACT][CLAIM-UG-HOLES-SCHEMA-130] Addons\worlds_enoch.pbo > config.bin > CfgWorlds > Enoch (1.30.164014, pasado a texto con CfgConvert)
class Holes
{
	class Dambog            // one group = one subclass; the name is arbitrary
	{
		tiles[]=
		{
			{118,195},{118,196},{118,197},
			{94,180},{95,180},{94,181},{95,181}
		};
	};
};
```

- Each entry in `tiles[]` is `{x, z}`: heightmap cell indices, not meters.
- The engine validates the range: code reading `tiles` uses the messages
  `x (%d) out of range <0, %d)` and `y (%d) …` (strings from `DayZDiag_x64.exe` 1.30;
  details in `references/terrain-holes-evidence.md`).
- Each group is a subclass, so a mod could add its own without overriding Bohemia's.
  **Unverified**: that a mod config patch on
  `CfgWorlds >> ChernarusPlus` opens holes is the first hypothesis that must be measured.

### Unit: heightmap cell

In Livonia the grid is 2048 cells of 6.25 m (12,800 m). With that size, both
groups fall over the vanilla underground triggers of Dambog; with 5 m or 10 m neither
falls within range (calculations in the reference):

- `{118, 195–197}` → X 737.5–743.75, Z 1218.75–1237.5: main entrance.
- `{94–95, 180–181}` → 12.5 m square at X 587.5–600, Z 1125–1137.5: second entrance.

It is `cross_checked` by that fit: the cell size was not read in the header of the
`.wrp` (OPRW v32) and the other maps are not measured. Always calculate
`celda = floor(coordenada / tamaño_de_celda)` with the size of your terrain.

### Script API

```c
// [EXACT][CLAIM-UG-SURFACEISHOLE-130] exp\scripts\scripts\3_Game\Global\Game.c:1203-1204
//! Returns whether tile at provided world coordinates is a hole.
proto native bool		SurfaceIsHole(float x, float z);
```

- It is the only new holes API and is read-only: there is no way to open or close
  holes from script at runtime.
- No vanilla 1.30 script calls it.
- Useful to avoid placing anything where there is no terrain: custom loot, spawn points,
  custom holograms.

### Where data lives

- `enoch.wrp` and `chernarusplus.wrp` go from OPRW v29 to v32 in 1.30 and both grow by 5%;
  Chernarus has no `Holes`. That change is format-related, not hole-related: holes
  reside in the world config (`cross_checked`).
- `exp\scripts\scripts\4_World\Classes\Hologram.c` is identical in 1.29 and 1.30: no
  kit placement check is aware of holes.

## Authoring workflow

- Buldozer 1.30 brings four new inputs: `UABuldLinkCamToTerrain`,
  `UABuldCopyTileCoord`, `UABuldMarkUnderground`, and `UABuldRemoveUnderground`
  (`exp\bin\bin\constants.xml:282-285`, cited in `enforce-script-reference`; the last
  two also appear in `DayZDiag_x64.exe` 1.30).
- Changelog 1.30, Terrain Builder section: the Buldozer camera can be unlinked from
  terrain height to edit below the surface (key 8 by default), and each object
  has an "underground" flag preventing a static object below terrain from being hidden
  by occlusion when it should be visible.
- That flag belongs to Terrain Builder. There is no script equivalent for objects created by
  Object Spawner or `CreateObject`, and whether those objects are occluded under terrain
  is unmeasured.
- A stable DayZ Tools from April 2026 contains no hole strings or flag strings
  (measured 2026-09-24): a later Terrain Builder is required.
- Third-party tool: Flynn's Terrain Tools (FTT, released 2026-09-19).
  - Marks cells and writes `holes.cfg` next to `layers.cfg`, where according to its guide
    Terrain Builder and Buldozer read it.
  - Adds the `#include` to the terrain's `config.cpp`.
  - Buldozer re-reads it on each alt-tab.
  - Matches the `\holes.cfg` string that the engine uses in its world-loading function,
    but the exact path and reload behavior are not verified here.

## Underground triggers

- File: `$mission:cfgundergroundtriggers.json`; if not present,
  `dz/worlds/<mundo>/ce/cfgundergroundtriggers.json`
  (`exp\scripts\scripts\3_Game\UndergroundAreaLoader.c:105-125`).
- Server creates boxes (`UndergroundTriggerCarrier`) on mission startup
  (`5_Mission\mission\missionServer.c:91`) and sends the entire JSON to each client upon
  connecting (`UndergroundAreaLoader.c:174-177`; `missionServer.c:342,363`). A custom mission
  JSON works without the client having the file.
- Trigger type (`4_World\Entities\ScriptedEntities\Triggers\UndergroundTrigger.c:97-116`):
  - with `Breadcrumbs` it is `TRANSITIONING` (maximum 32);
  - without them, `EyeAccommodation == 1.0` yields `OUTER`;
  - any other value yields `INNER`.
- [EXACT][CLAIM-UG-TRIGGER-LIMIT-130] Cap of 4096 triggers per JSON: `m_TriggerIndex` is
  synchronized in `-1..4095` (`UndergroundTrigger.c:10`); in 1.29 it was `-1..255`.
- Triggers bound to an object (`CustomSpawn`): via `ParentNetworkId` for map
  objects, or via `Tag`.
  - Vanilla pattern for a structure placed by Object Spawner: its spawner entry
    contains `"customString": "undergroundTriggerTag=TAG"`.
  - The class, in `OnSpawnByObjectSpawner`, creates triggers whose `Tag` matches
    (`4_World\Entities\Building\Underground\Land_WarheadStorage_Bunker_Facility.c:62-94`;
    `3_Game\ObjectSpawner.c:63,107`).
  - That logic lives in Sakhal classes, not in a common base: a mod class
    must implement it.
- In-game editor, new in 1.30: `LCTRL+/`, only in DayZDiag and in local game.
  - Double-click creates a trigger; edits boxes and breadcrumbs.
  - Exports to `$mission:cfgundergroundtriggers.json` and leaves a backup copy
    `…json.backup-<date>`.
  - Citations: `4_World\Plugins\PluginBase\PluginUndergroundTriggerManager.c:1,360,821,922`;
    `PluginKeyBinding.c:55`. More details in `dayz-mod-workflow`.
- Full JSON schema and trigger recipe with `Tag`: `references/underground-triggers.md`.

## Presencia bajo tierra

- `EUndergroundPresence`: `NONE`, `OUTER`, `TRANSITIONING`, `FULL`
  (`4_World\Classes\UndergroundHandlerClient.c:1-7`). Calculated by the client based on the
  trigger it is in (`:470-475`).
- [EXACT][CLAIM-UG-PRESENCE-SYNC-130] In 1.30 the client sends it to the server.
  - `SetUnderground` sends `INPUT_UDT_UNDERGROUND_SYNC`
    (`4_World\Entities\ManBase\PlayerBase.c:2853-2865`).
  - The server accepts it in `OnInputUserDataProcess` with only a range check
    (`:6531`, `:6557-6563`).
  - In 1.29 the value only existed on the client.
- Consequence: the server now knows presence. Previously, any server-side
  check reading it saw `NONE`.
- One such check is `CanPlaceItem` (`PlayerBase.c:2834-2846`, called from
  `Hologram.c:438`): inside a trigger it blocks types from
  `disallowedTypesInUnderground`.
  - By default: `FenceKit`, `TerritoryFlagKit`, and `WatchtowerKit`
    (`3_Game\CfgGameplayDataJson.c:229-232`).
  - Configured in `cfggameplay.json` > `BaseBuildingData` > `HologramData`.
- The value is decided by the client: the server does not recalculate it.

## Badlands in 1.30 scripts

- **Radio-announced bunkers.**
  - Classes `Land_Bunker_Basement_*` and `Land_Bunker_Shelter_*`
    (`4_World\Entities\Building\Bunker.c:289-294`), with code lock.
  - The radio broadcasts coordinates and code in Morse.
  - Configured in `cfgbunkerbroadcast.json`, in `$mission:` or in
    `dz/worlds/<mundo>/ce/` (`3_Game\CfgBunkerBroadcastHandler.c:5,23-27`), plus
    `bunkerBroadcastEnabled` in `cfggameplay.json` (`CfgGameplayDataJson.c:193`).
  - State file is covered by `dayz-persistence`.
- **Irrigation tunnel.** `Land_IrrigationTunnel_Entrance_01` is in
  `4_World\Entities\Building\Rebuildable\` (`IrrigationTunnel_Entrance.c:1-11`): the
  entrance is rebuildable, and its debug spawn populates it with sticks and rope.
  Rebuilding is covered by `dayz-basebuilding`.
- Nasdara configs and models are not included in 1.30 Exp: only its scripts (measured
  2026-09-24 on unencrypted PBOs).
- Bohemia (Dev Blog Recap 2, Steam, 2026-09-22): Badlands underground facilities
  use the terrain holes system, which will be available for other maps and
  for the modding community.

## Verification status

| Claim | Level |
|---|---|
| Format `Holes`/`tiles[]`, `SurfaceIsHole`, presence synchronization, trigger cap, JSON schema | `source_verified` |
| One entry in `tiles[]` is a heightmap cell; 6.25 m in Livonia | `cross_checked` (fit with triggers) |
| Holes reside in config, not in `.wrp` | `cross_checked` (`.wrp` grows identically with and without holes) |
| How a hole renders and collides, what happens when falling through it, AI and navmesh | `unverified` |
| A config-only mod opens holes in a vanilla map | `unverified` (hypothesis) |
| `holes.cfg` next to `layers.cfg` and reload on alt-tab | `unverified` (third parties: FTT) |
| Effect of `ECE_OBJECT_SPAWNER` | `unverified` |

## Before designing with holes

Each test advances one row of §Verification status. Together they fit in a single session of
DayZDiag 1.30 (`dayz-test-ingame`, `dayz-mcp-verify`):

1. **Livonia vanilla.** `g_Game.SurfaceIsHole(740, 1225)` must return `true` (cell
   `{118,196}`) and `g_Game.SurfaceIsHole(1000, 1000)` `false`. One screenshot from outside and
   another from inside the hole.
2. **Config-only mod.** Add a custom group in `CfgWorlds >> ChernarusPlus >> Holes`
   and repeat the check on its cell.
3. **Mod geometry.** Place an object with Object Spawner under that hole and
   verify that it is visible from inside and outside, and that it collides.
4. **Falling.** Drop an object and enter with a character into a hole without geometry.

## Delegaciones

| Topic | Skill |
|---|---|
| Base building parts, reconstruction, locks | `dayz-basebuilding` |
| Bunker broadcast state file | `dayz-persistence` |
| Trigger editor within general mod workflow | `dayz-mod-workflow` |
| Buldozer inputs and Enforce 1.30 API | `enforce-script-reference` |
| Launch game and verify with screenshots | `dayz-test-ingame` + `dayz-mcp-verify` |
| Sandstorm and heat of Nasdara | `dayz-environment-hazards` |

## Referencias

- `references/terrain-holes-evidence.md`: new engine strings and their references in
  code, Livonia config diff, cell size calculations, `.wrp` v29→v32, and official
  and third-party sources.
- `references/underground-triggers.md`: full schema of `cfgundergroundtriggers.json`,
  trigger recipe with `Tag` and underground presence.

## WHAT THIS SKILL COULD NOT VERIFY

- Any in-game behavior: rendering, collision, occlusion, falling, AI, and navmesh.
- Cell size of any map other than Livonia, and Livonia's read from the
  header of `.wrp`.
- Sakhal: its world is stored in an encrypted `.ebo` and could not be read.
- Exactly where the engine looks for `holes.cfg` and whether a config-only mod opens holes.
- What the engine does with `ECE_OBJECT_SPAWNER`.
