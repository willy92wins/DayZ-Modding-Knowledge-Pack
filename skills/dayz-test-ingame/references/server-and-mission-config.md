# Server and mission configuration on DayZ 1.30

What the stock dedicated server ships and which script reads it. Everything here was read from the
DayZ Server install of 1.30.164289 (Steam app 223350, build 26220720; the binary reports `1.30.164289.70`
in its RPT) and from the vanilla scripts extracted from the 1.30.164289 client. `MISSION` below is
`mpmissions/dayzOffline.chernarusplus/` of that install; script paths are relative to the extracted
`scripts/` tree. The Central Economy files (`db/*.xml`, `cfgeconomycore.xml`, `cfgspawnabletypes.xml`, ...)
are in `dayz-persistence/references/central-economy-files.md`. Ports and the test-tree layout are in
`linux-native-server.md`.

## 1. Missions shipped

`mpmissions/` holds `dayzOffline.chernarusplus`, `dayzOffline.enoch` (Livonia), `dayzOffline.sakhal` and
`dayzOffline.nasdara`. The mission to load is `template` inside `class Missions { class DayZ { ... }; };` of
`serverDZ.cfg` (stock file, lines 40-48), in the form `<mission>.<terrain>`.

A mission folder (Chernarus) contains:

| File | Role |
|---|---|
| `init.c` | the mission script: `main()` creates the Hive and sets the date, and `CustomMission` sets up new characters |
| `db/types.xml`, `db/events.xml`, `db/globals.xml`, `db/economy.xml`, `db/messages.xml` | economy data and server messages |
| `cfgeconomycore.xml`, `cfglimitsdefinition.xml`, `cfglimitsdefinitionuser.xml`, `cfgspawnabletypes.xml`, `cfgrandompresets.xml`, `cfgignorelist.xml`, `cfgeventspawns.xml`, `cfgeventgroups.xml` | Central Economy setup |
| `cfggameplay.json` | gameplay overrides (section 3) |
| `cfgeffectarea.json` | static contaminated areas (section 4) |
| `cfgundergroundtriggers.json` | underground darkness triggers (skill `dayz-underground`) |
| `cfgenvironment.xml` + `env/*_territories.xml` | animal and infected territories |
| `cfgweather.xml` | weather override; shipped with `enable="0"`, so the file is off by default (line 5) |
| `cfgplayerspawnpoints.xml` | fresh-spawn positions |
| `areaflags.map`, `mapgroup*.xml`, `mapcluster*.xml` | loot positions of the map |

Nasdara adds `cfgbunkerbroadcast.json` and `cfgexternallocks.json`; Sakhal adds `build.xml`, `config.cpp`
and `pra/`.

## 2. `serverDZ.cfg` keys in the stock file

The shipped `serverDZ.cfg` documents each key in a comment. Beyond the ones the test skills already set:

| Key (stock value) | Meaning, from the stock comment | Line |
|---|---|---|
| `verifySignatures = 2` | checks PBOs against `.bisign`; "only 2 is supported" | 11 |
| `forceSameBuild = 1` | only clients with the server's exe revision may join | 12 |
| `disableVoN = 0`, `vonCodecQuality = 20` | voice on/off; codec quality 0-30 | 14-15 |
| `disable3rdPerson = 0`, `disableCrosshair = 0` | view and crosshair toggles | 19-20 |
| `disablePersonalLight = 1`, `lightingConfig = 0` | personal light off; 0 brighter / 1 darker nights | 22-23 |
| `serverTime = "SystemTime"` | start time: the machine's clock, or `"YYYY/MM/DD/HH/MM"` | 25 |
| `serverTimeAcceleration = 12` | in-game time multiplier, 0-24 | 26 |
| `serverNightTimeAcceleration = 1` | extra multiplier for the night, 0.1-64, applied on top of `serverTimeAcceleration` | 27 |
| `serverTimePersistent = 0` | save the time to storage and resume from it | 28 |
| `guaranteedUpdates = 1` | network protocol; "use only number 1" | 30 |
| `loginQueueConcurrentPlayers = 5`, `loginQueueMaxPlayers = 500` | players processed at once during login; queue length | 32-33 |
| `instanceId = 1` | server instance number; names the storage folder | 35 |
| `storageAutoFix = 1` | replace corrupted persistence files with empty ones | 37 |

Keys the scripts read with `ServerConfigGetInt` (so they work even though the stock file does not list all of
them):

- `enableCfgGameplayFile`: without it set to 1 a dedicated server ignores `cfggameplay.json` (section 3).
- `disableBaseDamage`, `disableContainerDamage`, `disableRespawnDialog`, `disablePersonalLight`, `lightingConfig`:
  the defaults that apply when `cfggameplay.json` is not used (`scripts/3_Game/CfgGameplayDataJson.c:47-50`,
  `:79`, `:176`).
- `adminLogPlayerHitsOnly`, `adminLogPlacement`, `adminLogBuildActions`, `adminLogPlayerList`: filters for the
  admin log (`scripts/4_World/Plugins/PluginBase/PluginAdminLog.c:44-47`).
- `enableDebugMonitor` (`scripts/5_Mission/mission/missionServer.c:164`).

## 3. `cfggameplay.json`

`CfgGameplayHandler.LoadData` reads `$mission:cfggameplay.json`, or `dz/worlds/<world>/ce/cfggameplay.json` when
the mission has none, and only when `enableCfgGameplayFile` is set in `serverDZ.cfg` (a diag build that is not a
dedicated server forces it on). Otherwise it keeps the defaults from section 2
(`scripts/3_Game/CfgGameplayHandler.c:3`, `:44-66`). The whole object is sent to clients on connect
(`scripts/3_Game/CfgGameplayDataJson.c:1`). Every member must match a field of `CfgGameplayJson` and its
`ITEM_*` classes (`CfgGameplayDataJson.c:14-23` and the classes at `:43-440`).

Stock sections (`MISSION/cfggameplay.json`; `version` is 123):

- `GeneralData` (lines 3-9): `disableBaseDamage`, `disableContainerDamage`, `disableRespawnDialog`,
  `disableRespawnInUnconsciousness`.
- `PlayerData` (10-53): `disablePersonalLight`; `StaminaData` (`staminaMax` 100, `staminaMinCap` 5,
  `staminaWeightLimitThreshold` 6000, `staminaKgToStaminaPercentPenalty` 1.75, `sprintStaminaModifierErc/Cro`
  and the swimming, ladder, melee, obstacle and hold-breath modifiers at 1.0); `ShockHandlingData`
  (`shockRefillSpeedConscious` 5, `shockRefillSpeedUnconscious` 1, `allowRefillSpeedModifier`);
  `MovementData`; `DrowningData`; `WeaponObstructionData` (`staticMode`, `dynamicMode`).
- `WorldsData` (54-61, note the plural): `lightingConfig`, `objectSpawnersArr`, `environmentMinTemps` /
  `environmentMaxTemps` (twelve monthly values), `wetnessWeightModifiers`.
- `BaseBuildingData` (62-88): `HologramData` with the `disable...Check` switches (`disableIsCollidingBBoxCheck`,
  `disableIsCollidingPlayerCheck`, `disableIsClippingRoofCheck`, `disableIsBaseViableCheck`,
  `disableIsCollidingGPlotCheck`, `disableIsCollidingAngleCheck`, `disableIsPlacementPermittedCheck`,
  `disableHeightPlacementCheck`, `disableIsUnderwaterCheck`, `disableIsInTerrainCheck`,
  `disableColdAreaBuildingCheck`) and `disallowedTypesInUnderground`; `ConstructionData` with
  `disablePerformRoofCheck`, `disableIsCollidingCheck`, `disableDistanceCheck`, `disableItemFalling`,
  `disableDropAttachmentsOnFall`, `disableRefundMaterialsOnFall`.
- `UIData` (89-103): `use3DMap`, `HitIndicationData` (`hitDirectionOverrideEnabled`, behaviour, style, colour,
  duration, scatter, `hitIndicationPostProcessEnabled`).
- `MapData` (104-110): `ignoreMapOwnership`, `ignoreNavItemsOwnership`, `displayPlayerPosition`,
  `displayNavInfo`.
- `VehicleData` (111-118): `boatDecayMultiplier` and the wheel detach/damage switches.

The script also knows `ExternalLockData` and `SandstormData`, which the Chernarus file does not carry
(`dayz-mod-workflow/references/dayz-1-30-mod-workflow.md`).

## 4. `cfgeffectarea.json`

Read by `ContaminatedAreaLoader` from `$mission:cfgeffectarea.json`, with the same `dz/worlds/<world>/ce/`
fallback (`scripts/4_World/Classes/ContaminatedArea/ContaminatedAreaLoader.c:4`, `:18`). The top level has two
arrays (`JsonDataContaminatedArea.c:1-6`):

- `Areas`: one object per zone with `AreaName`, `Type` (the entity class, e.g. `ContaminatedArea_Static`),
  `TriggerType` (e.g. `ContaminatedTrigger`), `Data` and `PlayerData`.
- `SafePositions`: `[x, z]` pairs (`MISSION/cfgeffectarea.json:167`).

`Data` holds `Pos`, `Radius`, `PosHeight`, `NegHeight`, `InnerRingCount`, `InnerPartDist`, `OuterRingToggle`,
`OuterPartDist`, `OuterOffset`, `VerticalLayers`, `VerticalOffset`, `ParticleName`, `EffectInterval`,
`EffectDuration`, `EffectModifier`; `PlayerData` holds `AroundPartName`, `TinyPartName`, `PPERequesterType`
(`JsonDataContaminatedArea.c:17-41`). A `Radius` of 0 or less is rejected with an error naming the area
(`ContaminatedAreaLoader.c:48`). Chernarus ships nine `ContaminatedArea_Static` zones.

## 5. `db/messages.xml`

Each `<message>` has child elements, not attributes: `<text>` (may use `#name` for the server name and `#tmin`
for the minutes left), `<delay>` (minutes after connect), `<repeat>` (minutes between repeats),
`<onconnect>1</onconnect>` (start counting at the player's connect), `<deadline>` (minutes until the end) and
`<shutdown>1</shutdown>` (shut the server down at the deadline, with a countdown message). The stock file holds
only commented examples (`MISSION/db/messages.xml:3-45`).

## 6. Logs in the profile folder

With `-profiles=<dir>` the server writes `DayZServer_<date>_<time>.RPT` (engine), `script_<date>_<time>.log`
and `error_<date>_<time>.log`. With `-adminlog` it also writes `DayZServer_<date>_<time>.ADM`, which starts with
an `AdminLog started on <date> at <time>` header; without the switch no `.ADM` file appears (both measured on the
native Linux server, 1.30.164289, 2026-11-13).
