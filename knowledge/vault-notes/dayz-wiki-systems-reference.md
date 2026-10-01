# DayZ — official wiki systems (gameplay / environment / server) — reference

> From "Wiki Sweep #2" (research 2026-07). Covers DayZ configuration systems documented on
> `community.bistudio.com`. **`[TBD-verify]` by default**: wiki-sourced, NOT verified against local
> vanilla (except where noted). DZ-R2.1: treat each data point as hint until confirmed against vanilla
> `cfggameplay.json`/`.xml` or `BohemiaInteractive/DayZ-Central-Economy` repo. Low reuse for
> 3D/vehicle modding, but captured at user request to avoid re-investigating.
>
> **Guardrail**: for any Enforce/config identifier, require a `community.bistudio.com` URL
> before stating it as fact. `dayzexplorer.zeroy.com` / `dayz-scripts.yadz.app` / fandom = "plausible,
> unverified" — label as such.

## ⚠️ ERRATA permanente (CORRECTED / DOWNGRADED) — no reintroducir

- **`CfgStamina` is NOT a vanilla class.** Verified 2026-07-06: NOTHING in user skills/vault/repo
  asserts it (grep empty); `enforce-script-reference` cites actual vanilla `staminahandler.c:797`
  (legitimate, distinct). Stamina/temperature/wetness are configured via **`cfggameplay.json` keys** +
  `globals.xml WorldWetTempUpdate`, not via a `CfgStamina` class.
- `Stamina.c` / `StaminaHandler.c` / `environment.c` / `m_HeatComfort` / `UniversalTemperatureSource`
  as "documented in wiki" = **false**: they only appear on third-party mirrors. (Note: they are REAL
  vanilla APIs in decompiled code — what is false is attributing them to the wiki, not their existence.)
- `vonCodecQuality` range **0–20** (not 0–10 as some host-docs claim).

## 1. Entorno / hazard

- **Contaminated areas — `cfgEffectArea.json`** (mission folder; static NOT persistent,
  added/removed between restarts WITHOUT wipe). Structure: `"Areas"[]` with `AreaName`, `Type`
  (`ContaminatedArea_Static`), `TriggerType` (`ContaminatedTrigger`), `Data` (`Pos[x,y,z]` — Y≠0 = floating
  gas; `Radius`, `PosHeight`, `NegHeight`, `InnerRingCount`, `InnerPartDist`, `OuterRingToggle`,
  `ParticleName` e.g. `contaminated_area_gas_bigass`), `PlayerData` (`PPERequesterType`
  `PPERequester_ContaminatedAreaTint`). Many `Data` accept `-1`=default. **v1.28**: helper
  `FillWithParticles(pos, areaRadius, outwardsBleed, partSize, partId)` + **clamp 1000 emitters/zone**.
  Empty `{ }` = disables. URL: `/wiki/DayZ:Contaminated_Areas_Configuration`. (Particles → skill
  `dayz-particles`.)
- **Weather — `cfgweather.xml`** (mission folder; **XML not JSON**, see DAYZ_INFRA errata). Root
  `<weather reset="0" enable="1">`. Elements `<overcast>/<fog>/<rain>/<wind>/<storm>` with children
  `<current actual= time= duration=>`, `<limits min= max=>` (0..1), `<timelimits>`, `<changelimits>`.
  `<rain>` + `<thresholds min= max= end=>`; `<wind><maxspeed>` m/s; `<storm density= threshold= timeout=>`.
  Mirrors `3_Game\Weather.c` API. 3 weather avenues: scripted state machine
  (`WorldData::WeatherOnBeforeChange` in `Enoch.c`), `MissionWeather(true)`+API, or XML.
  Known limitation (Feedback T162322, NOT official): with active file weather tends toward extremes;
  reliable mainly to DISABLE weather. URL: `/wiki/DayZ:Weather_Configuration`.
- **Underground darkness — `cfgundergroundtriggers.json`** ("eye accommodation" 0=dark,1=normal).
  Outer/Transitional/Inner triggers + Breadcrumbs (points with radius and weight by proximity). Trigger:
  `Position`, `Orientation`, `Size`, `EyeAccommodation`, `Breadcrumbs[]`, `InterpolationSpeed`. Diag
  (v1.20+): `Script > Underground Areas > Show Breadcrumbs / Disable Darkening`. Ref working file:
  `dayzOffline.enoch`. URL: `/wiki/DayZ:Underground_Areas_Configuration`. (Namalsk/underground niche.)

## 2. Wildlife / animal AI
- Ambient animal spawner = CE dynamic event (`db/events.xml`, events starting with `Animal`/
  `Infected`; `<child type="Animal_VulpesVulpes"/>`, `<territory>`, `<zone>`). Toggleable.
  URL: `/wiki/DayZ:CE:_Ambient_Spawner`.
- Footstep sounds: macros `ANIMAL_STEP_SOUNDTABLE(Bird,Walk)` in Surfaces config.
- Fishing: **no official modding page** (fan wikis only) → non-authoritative. Fish/bait items in CE
  (`cfgspawnabletypes.xml`).

## 3. Player systems
- **Stamina** (`cfggameplay.json`, verified verbatim in CE repo): `staminaMax=100.0`,
  `staminaWeightLimitThreshold=6000.0`, `staminaKgToStaminaPercentPenalty=1.75`, `staminaMinCap=5.0`;
  modifiers (float, default 1.0): `sprintStaminaModifierErc/Cro`, `sprintSwimmingStaminaModifier`,
  `sprintLadderStaminaModifier`, `meleeStaminaModifier`, `obstacleTraversalStaminaModifier`,
  `holdBreathStaminaModifier`; `staminaDepletionSpeed=10.0`; `allowStaminaAffectInertia` (bool).
- **Temp/wetness** (`cfggameplay.json` + `globals.xml`): `environmentMinTemps[12]`,
  `environmentMaxTemps[12]` (monthly arrays), `wetnessWeightModifiers[1.0,1.0,1.33,1.66,2.0]` (5
  states DRY..DRENCHED). `WorldWetTempUpdate` (globals.xml, master toggle). Enable:
  `enableCfgGameplayFile=1` in serverDZ.cfg. URL: `/wiki/DayZ:Gameplay_Settings`.
- **VOIP** (serverDZ.cfg): `disableVoN` (0/1), `vonCodecQuality` (0–**20**).

## 4. Surfaces / clutter / projection (terrain authoring — low reuse)
- **CfgSurfaces** derives `DZ_SurfacesInt`/`DZ_SurfacesExt` (`DZ_Surfaces` addon). Params: `files`,
  `friction`, `restitution`, `soundEnviron` (hard_ground/metal/wood/concrete/tyre/water…), `soundHit`,
  `character` (→`CfgSurfaceCharacters`, terrain only), `footDamage`, `audibility`, `isDigable`,
  `isFertile`, `impact`, `deflection`. Roadway flattens clutter except `DZ\data\data\surfaces\clutter.rvmat`.
  URL: `/wiki/DayZ:Surfaces`. (`isDigable`/`isFertile` already in `dayz-physics-engine`.)
- **Grass-clutter**: single-sided model res LODs; wind via rvmat `plantWind[]={speed,stiffness,
  smoothness,light}` (stiffness 0 = static). Config `class Clutter` in `CfgWorlds` (model/scaleMin/
  scaleMax/noSatColor) + `clutterGrid`/`clutterDist`. NOT previewable in Buldozer with grass shader.
  URLs: `/wiki/DayZ:Grass-clutter_modelling` + `_configuration`.
- **Projection Layer** (directional snow/moss, Sakhal): Supershader/Multishader params
  `multiTopProjectionLayer`, `degAngleTopProjectionStart/End`, `multiTopProjectionBlend`,
  `multiTopProjectionLayerNormal`; alpha of a `_CA` masks. URL: `/wiki/DayZ:Projection_Layer`.
  (→ skill `dayz-texture-pipeline` if touched.)

## 5. Server — launch params and config (see also `DAYZ_INFRA.md`)
- Core: `-config=`, `-port=` (2302 UDP), `-profiles=`, `-mission=` (absolute), `-mod=` (client+server,
  `;`-sep, absolute), `-serverMod=` (server only).
- `steamQueryPort = 2305;` in serverDZ.cfg — fix for "server not visible in browser" (wiki uses explicit
  key, NOT the myth "game port +1"). Does not contradict "2302 is UDP" (it is the game port, another thing).
- **`-par=<file>`** — reads params from a file (one option/line; supports C++ comments/#define). Fix for
  Windows **8192-char command-line limit** when stacking many mods (Feedback T180950).
  ⭐ Useful for user (stacks `@CF;@Dabs;@VPP;@<Mod>_deps;@DayZ_MCP…` with absolute paths). `[TBD-verify]`: 
  source traces to T180950, not wiki body → test a `.par` before relying on it.
  Generic URL: `/wiki/Startup_Parameters_Config_File`.
- Diag/logging: `-doLogs`, `-adminLog`, `-netLog`, `-freezeCheck`, `-filePatching`, `-cpuCount=`
  (≤ logical cores), `-limitFPS=` (cap, max 200). `priority.txt` (SteamIDs `;`-sep, login queue).
- BattlEye: `BEServer_x64.cfg` next to `BEServer_x64.dll`; `-bePath`; `RConPassword`, `RestrictRCon 1`.
- Linux server: `./DayZServer` binary (SteamCMD app 223350; client 221100; Tools 1042420); mods by
  workshop ID via symlinks; NOT as root; systemd unit. Discrepancy: wiki documents native Linux
  binary, but independent host-docs state stable runs Windows-under-compat → flag.
  URL: `/wiki/DayZ:Server_Configuration`, `/wiki/DayZ:Hosting_a_Linux_Server`.

## 6. Diag menu / spawners (DayZDiag_x64)
- Diag: Win+Alt (or Ctrl+Win, conflicts with Win11). Categories: Statistics (Script Profiler flags
  SPF_RECURSIVE/RESET/NONE, modules CORE/GAMELIB/GAME/WORLD/MISSION; `-profile` forces), Enfusion
  Renderer/World, DayZ render, Game (Weather, Free Camera, Vehicles, Combat DE*, **Central Economy**
  debug: Loot Spawn Edit, Force Save, Dynamic Events…), AI (NavMesh/Pathgraph), Sounds.
  ⚠️ **DO NOT capture `-debugweather`** — research saw it in snippet but NOT confirmed in body of
  page (G2/DZ-R2.1). URL: `/wiki/DayZ:Diag_Menu`.
- **Object Spawner** (`spawnerData.json`, mission folder; requires cfgGameplay): static objects
  (pos+orient) at startup. Missing class → "Object spawner failed to spawn" in RPT.
  URL: `/wiki/DayZ:Object_Spawner`.
- **Spawning Gear** (`cfgGameplay.json` → `PlayerData.spawnGearPresetFiles`): server-side override of
  spawn; presets with `spawnWeight`, `characterTypes` (`SurvivorM_Mirek`), `attachmentSlotItemSets`,
  `discreteUnsortedItemSets`. Total override of `StartingEquipSetup()`. URL:
  `/wiki/DayZ:Spawning_Gear_Configuration`.

## 7. Licencia / EULA (guardrail)
Assets built with **DayZ Tools are non-commercial** (DayZ Tools EULA); reuse of BI game
data falls under the "Arma & DayZ Only, Noncommercial" license; content cannot be behind a paywall
(voluntary donations, free content). Relevant because user generates source-game rips + AI
assets. URLs: `/wiki/DayZ:End_User_License_Agreement_for_DayZ_Tools`, `bohemia.net/monetization`.

## Cross-ref
- [[dayz-objectbuilder-lod-conventions]] — doors/ladders/LOD (MODELING part, verified vanilla).
- `DAYZ_INFRA.md` — user operational server infra (launch, ports, BattlEye, allowFilePatching).
- Skills: `enforce-script-reference` (config.cpp, vanilla stamina APIs), `dayz-particles`,
  `dayz-texture-pipeline`, `dayz-physics-engine`.
- Origin: session 2026-07-06 (deep-research Wiki Sweep #2).
