# DayZ — sistemas de la wiki oficial (gameplay / entorno / server) — referencia

> Del "Wiki Sweep #2" (research 2026-07). Cubre sistemas de configuración DayZ documentados en
> `community.bistudio.com`. **`[TBD-verify]` por defecto**: es wiki-sourced, NO verificado contra vanilla
> local (salvo donde se indique). DZ-R2.1: tratar cada dato como hint hasta confirmar contra un
> `cfggameplay.json`/`.xml` vanilla o el repo `BohemiaInteractive/DayZ-Central-Economy`. Bajo reuso para
> modding 3D/vehículos, pero capturado a petición del usuario para no re-investigar.
>
> **Guardrail**: para cualquier identificador Enforce/config, exigir una URL `community.bistudio.com`
> antes de afirmarlo como fact. `dayzexplorer.zeroy.com` / `dayz-scripts.yadz.app` / fandom = "plausible,
> unverified" — etiquetar como tal.

## ⚠️ ERRATA permanente (CORRECTED / DOWNGRADED) — no reintroducir

- **`CfgStamina` NO es una clase vanilla.** Verificado 2026-07-06: NADA en las skills/vault/repo del
  usuario lo afirma (grep vacío); `enforce-script-reference` cita el `staminahandler.c:797` vanilla real
  (legítimo, distinto). Stamina/temperatura/wetness se configuran por **keys de `cfggameplay.json`** +
  `globals.xml WorldWetTempUpdate`, no por una clase `CfgStamina`.
- `Stamina.c` / `StaminaHandler.c` / `environment.c` / `m_HeatComfort` / `UniversalTemperatureSource`
  como "documentados en la wiki" = **falso**: solo aparecen en mirrors de terceros. (Ojo: son APIs
  vanilla REALES en el código descompilado — lo falso es atribuirlos a la wiki, no su existencia.)
- `vonCodecQuality` rango **0–20** (no 0–10 como dicen algunos host-docs).

## 1. Entorno / hazard

- **Contaminated areas — `cfgEffectArea.json`** (mission folder; estáticas NO persistentes, se
  añaden/quitan entre reinicios SIN wipe). Estructura: `"Areas"[]` con `AreaName`, `Type`
  (`ContaminatedArea_Static`), `TriggerType` (`ContaminatedTrigger`), `Data` (`Pos[x,y,z]` — Y≠0 = gas
  flotante; `Radius`, `PosHeight`, `NegHeight`, `InnerRingCount`, `InnerPartDist`, `OuterRingToggle`,
  `ParticleName` p.ej. `contaminated_area_gas_bigass`), `PlayerData` (`PPERequesterType`
  `PPERequester_ContaminatedAreaTint`). Muchos `Data` aceptan `-1`=default. **v1.28**: helper
  `FillWithParticles(pos, areaRadius, outwardsBleed, partSize, partId)` + **clamp 1000 emisores/zona**.
  Vacío `{ }` = desactiva. URL: `/wiki/DayZ:Contaminated_Areas_Configuration`. (Partículas → skill
  `dayz-particles`.)
- **Weather — `cfgweather.xml`** (mission folder; **XML no JSON**, ver errata DAYZ_INFRA). Root
  `<weather reset="0" enable="1">`. Elementos `<overcast>/<fog>/<rain>/<wind>/<storm>` con hijos
  `<current actual= time= duration=>`, `<limits min= max=>` (0..1), `<timelimits>`, `<changelimits>`.
  `<rain>` + `<thresholds min= max= end=>`; `<wind><maxspeed>` m/s; `<storm density= threshold= timeout=>`.
  Espeja la API de `3_Game\Weather.c`. 3 vías de weather: state machine scripted
  (`WorldData::WeatherOnBeforeChange` en `Enoch.c`), `MissionWeather(true)`+API, o el XML.
  Limitación conocida (Feedback T162322, NO oficial): con el file activo el clima tiende a extremos;
  fiable sobre todo para DESACTIVAR clima. URL: `/wiki/DayZ:Weather_Configuration`.
- **Underground darkness — `cfgundergroundtriggers.json`** ("eye accommodation" 0=oscuro,1=normal).
  Triggers Outer/Transitional/Inner + Breadcrumbs (puntos con radio y peso por proximidad). Trigger:
  `Position`, `Orientation`, `Size`, `EyeAccommodation`, `Breadcrumbs[]`, `InterpolationSpeed`. Diag
  (v1.20+): `Script > Underground Areas > Show Breadcrumbs / Disable Darkening`. Ref working file:
  `dayzOffline.enoch`. URL: `/wiki/DayZ:Underground_Areas_Configuration`. (Nicho Namalsk/underground.)

## 2. Wildlife / animal AI
- Ambient animal spawner = evento dinámico CE (`db/events.xml`, eventos que empiezan por `Animal`/
  `Infected`; `<child type="Animal_VulpesVulpes"/>`, `<territory>`, `<zone>`). Toggleable.
  URL: `/wiki/DayZ:CE:_Ambient_Spawner`.
- Sonidos de paso: macros `ANIMAL_STEP_SOUNDTABLE(Bird,Walk)` en la config de Surfaces.
- Fishing: **sin página oficial de modding** (solo fan wikis) → no-autoritativo. Items pez/cebo en CE
  (`cfgspawnabletypes.xml`).

## 3. Player systems
- **Stamina** (`cfggameplay.json`, verificado verbatim en el repo CE): `staminaMax=100.0`,
  `staminaWeightLimitThreshold=6000.0`, `staminaKgToStaminaPercentPenalty=1.75`, `staminaMinCap=5.0`;
  modificadores (float, default 1.0): `sprintStaminaModifierErc/Cro`, `sprintSwimmingStaminaModifier`,
  `sprintLadderStaminaModifier`, `meleeStaminaModifier`, `obstacleTraversalStaminaModifier`,
  `holdBreathStaminaModifier`; `staminaDepletionSpeed=10.0`; `allowStaminaAffectInertia` (bool).
- **Temp/wetness** (`cfggameplay.json` + `globals.xml`): `environmentMinTemps[12]`,
  `environmentMaxTemps[12]` (arrays mensuales), `wetnessWeightModifiers[1.0,1.0,1.33,1.66,2.0]` (5
  estados DRY..DRENCHED). `WorldWetTempUpdate` (globals.xml, master toggle). Habilitar:
  `enableCfgGameplayFile=1` en serverDZ.cfg. URL: `/wiki/DayZ:Gameplay_Settings`.
- **VOIP** (serverDZ.cfg): `disableVoN` (0/1), `vonCodecQuality` (0–**20**).

## 4. Surfaces / clutter / projection (autoría de terreno — bajo reuso)
- **CfgSurfaces** deriva `DZ_SurfacesInt`/`DZ_SurfacesExt` (addon `DZ_Surfaces`). Params: `files`,
  `friction`, `restitution`, `soundEnviron` (hard_ground/metal/wood/concrete/tyre/water…), `soundHit`,
  `character` (→`CfgSurfaceCharacters`, solo terreno), `footDamage`, `audibility`, `isDigable`,
  `isFertile`, `impact`, `deflection`. Roadway aplasta clutter salvo `DZ\data\data\surfaces\clutter.rvmat`.
  URL: `/wiki/DayZ:Surfaces`. (`isDigable`/`isFertile` ya en `dayz-physics-engine`.)
- **Grass-clutter**: modelo single-sided res LODs; viento por rvmat `plantWind[]={speed,stiffness,
  smoothness,light}` (stiffness 0 = estático). Config `class Clutter` en `CfgWorlds` (model/scaleMin/
  scaleMax/noSatColor) + `clutterGrid`/`clutterDist`. NO previewable en Buldozer con grass shader.
  URLs: `/wiki/DayZ:Grass-clutter_modelling` + `_configuration`.
- **Projection Layer** (nieve/musgo direccional, Sakhal): Supershader/Multishader params
  `multiTopProjectionLayer`, `degAngleTopProjectionStart/End`, `multiTopProjectionBlend`,
  `multiTopProjectionLayerNormal`; alpha de un `_CA` enmascara. URL: `/wiki/DayZ:Projection_Layer`.
  (→ skill `dayz-texture-pipeline` si se toca.)

## 5. Server — launch params y config (ver también `DAYZ_INFRA.md`)
- Core: `-config=`, `-port=` (2302 UDP), `-profiles=`, `-mission=` (absoluto), `-mod=` (client+server,
  `;`-sep, absolutos), `-serverMod=` (solo server).
- `steamQueryPort = 2305;` en serverDZ.cfg — fix de "server no visible en el browser" (la wiki usa la key
  explícita, NO el mito "game port +1"). No contradice "2302 es UDP" (es el puerto de juego, otra cosa).
- **`-par=<file>`** — lee params de un archivo (una opción/línea; admite comentarios C++/#define). Fix del
  **límite de 8192 chars de la línea de comandos** de Windows al apilar muchos mods (Feedback T180950).
  ⭐ Útil para el usuario (apila `@CF;@Dabs;@VPP;@<Mod>_deps;@DayZ_MCP…` con paths absolutos). `[TBD-verify]`:
  el source lo cuelga de T180950, no del cuerpo de la wiki → probar un `.par` antes de fiarse.
  URL genérica: `/wiki/Startup_Parameters_Config_File`.
- Diag/logging: `-doLogs`, `-adminLog`, `-netLog`, `-freezeCheck`, `-filePatching`, `-cpuCount=`
  (≤ cores lógicos), `-limitFPS=` (cap, máx 200). `priority.txt` (SteamIDs `;`-sep, cola de login).
- BattlEye: `BEServer_x64.cfg` junto a `BEServer_x64.dll`; `-bePath`; `RConPassword`, `RestrictRCon 1`.
- Linux server: binario `./DayZServer` (SteamCMD app 223350; cliente 221100; Tools 1042420); mods por
  workshop ID vía symlinks; NO como root; systemd unit. Discrepancia: la wiki documenta binario nativo
  Linux, pero host-docs independientes dicen que el estable corre Windows-bajo-compat → flag.
  URL: `/wiki/DayZ:Server_Configuration`, `/wiki/DayZ:Hosting_a_Linux_Server`.

## 6. Diag menu / spawners (DayZDiag_x64)
- Diag: Win+Alt (o Ctrl+Win, choca con Win11). Categorías: Statistics (Script Profiler flags
  SPF_RECURSIVE/RESET/NONE, módulos CORE/GAMELIB/GAME/WORLD/MISSION; `-profile` fuerza), Enfusion
  Renderer/World, DayZ render, Game (Weather, Free Camera, Vehicles, Combat DE*, **Central Economy**
  debug: Loot Spawn Edit, Force Save, Dynamic Events…), AI (NavMesh/Pathgraph), Sounds.
  ⚠️ **NO capturar `-debugweather`** — el research lo vio en snippet pero NO confirmado en el cuerpo de la
  página (G2/DZ-R2.1). URL: `/wiki/DayZ:Diag_Menu`.
- **Object Spawner** (`spawnerData.json`, mission folder; requiere cfgGameplay): objetos estáticos
  (pos+orient) al arrancar. Falta de clase → "Object spawner failed to spawn" en RPT.
  URL: `/wiki/DayZ:Object_Spawner`.
- **Spawning Gear** (`cfgGameplay.json` → `PlayerData.spawnGearPresetFiles`): override server-side del
  spawn; presets con `spawnWeight`, `characterTypes` (`SurvivorM_Mirek`), `attachmentSlotItemSets`,
  `discreteUnsortedItemSets`. Override total de `StartingEquipSetup()`. URL:
  `/wiki/DayZ:Spawning_Gear_Configuration`.

## 7. Licencia / EULA (guardrail)
Los assets construidos con **DayZ Tools son non-commercial** (DayZ Tools EULA); la reutilización de game
data de BI cae bajo la licencia "Arma & DayZ Only, Noncommercial"; el contenido no puede quedar tras
pago (donaciones voluntarias, contenido libre). Relevante porque el usuario genera rips source-game + assets
IA. URLs: `/wiki/DayZ:End_User_License_Agreement_for_DayZ_Tools`, `bohemia.net/monetization`.

## Cross-ref
- [[dayz-objectbuilder-lod-conventions]] — doors/ladders/LOD (parte MODELADO, verificado vanilla).
- `DAYZ_INFRA.md` — server infra operativa del usuario (launch, ports, BattlEye, allowFilePatching).
- Skills: `enforce-script-reference` (config.cpp, stamina APIs vanilla), `dayz-particles`,
  `dayz-texture-pipeline`, `dayz-physics-engine`.
- Origen: sesión 2026-07-06 (deep-research Wiki Sweep #2).
