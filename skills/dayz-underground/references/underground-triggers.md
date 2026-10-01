# Underground triggers: schema and recipes (DayZ 1.30.164014 Exp)

Citations from `exp\scripts\scripts\…`, opened on 2026-09-24. `source_verified` except what is
marked `[DESIGN]` or unverified.

## Schema of `cfgundergroundtriggers.json`

[EXACT][CLAIM-UG-TRIGGER-JSON-130] Root `{ "Triggers": [ … ] }`
(`3_Game\UndergroundAreaLoader.c:1-3`). Each trigger (`JsonUndergroundAreaTriggerData`,
`:69-99`):

| Field | Type | Purpose |
|---|---|---|
| `Comment` | string | freeform note (new in 1.30) |
| `CustomSpawn` | bool | not spawned at boot: created by parent object (see §Triggers parented to an object) |
| `Tag` | string | link to Object Spawner entry or manual spawn |
| `ParentNetworkId` | int[2] | link to map object by its network id |
| `Position`, `Orientation`, `Size` | float[3] | trigger box |
| `EyeAccommodation` | float | eye adaptation; `1.0` without breadcrumbs gives `OUTER` type |
| `InterpolationSpeed` | float | transition speed |
| `UseLinePointFade` | bool | simple fade between `Breadcrumbs` points |
| `AmbientSoundType` | string | ambient type for sound controller |
| `AmbientSoundSet` | string | manual ambient (Livonia uses `Underground_SoundSet`) |
| `Breadcrumbs` | array | transition points; if any present, type is `TRANSITIONING` (up to 32) |

Each breadcrumb (`JsonUndergroundAreaBreadcrumb`, `:36-51`): `Position` (float[3]),
`EyeAccommodation` (float), `UseRaycast` (bool), `Radius` (float; Livonia uses `-1`),
`LightLerp` (bool, only with `UseLinePointFade`), `Comment` and `ExternalValueController`
(`Type` + `Params`; for example `BreadcrumbDoorStateController`, taking selection
name of a door, `:53-67`).

Trigger type is decided by `UndergroundTrigger.c:97-116`:

- with breadcrumbs, `TRANSITIONING`;
- without them, `EyeAccommodation == 1.0` gives `OUTER`;
- any other value gives `INNER`.

Player presence comes from type (`TranslateTriggerTypeToPresence`, `:190-203`).

## Loading and synchronization

1. **File.** `UndergroundAreaLoader.GetData` first searches
   `$mission:cfgundergroundtriggers.json`; if missing, warns in RPT and tries
   `dz/worlds/<world>/ce/cfgundergroundtriggers.json` (`:105-125`).
2. **Startup.** Server creates an `UndergroundTriggerCarrier` per trigger without
   `CustomSpawn` (`SpawnAllTriggerCarriers`, `:135-154`, called in
   `5_Mission\mission\missionServer.c:91`).
3. **Synchronization.** Upon player connection, server sends entire JSON via
   `RPC_UNDERGROUND_SYNC` (`:174-177`; `missionServer.c:342,363`) and client stores it
   (`:181-193`). Client does not need file locally.
4. **Local.** In local game with `DIAG_DEVELOPER`, client loads and creates triggers
   itself (`5_Mission\mission\missionGameplay.c:112-117`).

Cap: `m_TriggerIndex` synchronizes in `-1..4095` (`UndergroundTrigger.c:10`), so
a JSON supports up to 4096 triggers. In 1.29 it was 256.

## Triggers ligados a un objeto

Two ways, both with `CustomSpawn = true`:

- **Map object.** `ParentNetworkId` with network id of object; object itself
  calls `JsonUndergroundTriggers.SpawnParentedTriggers(this)` (`:5-22`). Done by
  `Land_WarheadStorage_Main` (`:72`) and `Land_WarheadStorage_Bunker_Facility` (`:16`).
- **Object placed by Object Spawner.**
  - Spawner entry (`ITEM_SpawnerObject`: `name`, `pos`, `ypr`, `scale`,
    `enableCEPersistency`, `customString`; `3_Game\ObjectSpawner.c:100-108`) carries
    `"customString": "undergroundTriggerTag=TAG"`.
  - Spawner calls `object.OnSpawnByObjectSpawner(item)` (`ObjectSpawner.c:63`).
  - Class iterates `CustomSpawn` triggers and creates those matching that `Tag`
    (`Land_WarheadStorage_Bunker_Facility.c:62-94`); `customString` accepts multiple
    pairs separated by `;`.
  - That logic lives in Sakhal classes, not in a common base: a mod class
    must write it.

Unverified: whether `Position` of parented trigger is world or relative to parent. The
code creates carrier at `data.GetPosition()` and then calls `SetParent(parent)`
(`UndergroundAreaLoader.c:24-33`); how that transforms position has not been measured.

## Recipe [DESIGN]: mod bunker placed with Object Spawner

Untested. Follows vanilla Sakhal pattern.

1. **Trigger in mission JSON**, with `"CustomSpawn": true`, a unique `Tag` and the
   interior box. For a dark zone without transition: no breadcrumbs and
   `EyeAccommodation` other than `1`, which yields `INNER`.
2. **Object Spawner entry** with `"customString": "undergroundTriggerTag=<Tag>"`.
3. **Bunker script class.** Override `OnSpawnByObjectSpawner(ITEM_SpawnerObject item)`
   with same iteration as `Land_WarheadStorage_Bunker_Facility.c:62-94`, calling
   `JsonUndergroundTriggers.SpawnTriggerCarrier(this, index, triggerData)`.
4. **Hole.** If bunker opens to terrain, hole is also needed
   (`CfgWorlds >> <world> >> Holes`, see `SKILL.md`).

A mod cannot add its own triggers file without touching loader: `GetData`
reads a single file. A `modded class UndergroundAreaLoader` adding mod
triggers to `m_JsonData` before `SyncDataSend` is the obvious path; not tested.

## Presence and restrictions

See `SKILL.md` §Underground presence. In summary: client calculates presence, in 1.30
sends it to server (`INPUT_UDT_UNDERGROUND_SYNC`), and inside a trigger `CanPlaceItem`
blocks `disallowedTypesInUnderground`.
