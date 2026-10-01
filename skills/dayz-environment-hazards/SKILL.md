---
name: dayz-environment-hazards
description: >
  Use when: sandstorm, sandstormFrequency, ScriptedSandstormController, shelter
  fade, ThermalBias, heat stroke, HeatStroke, IsInShadow, oil pit, OilPitArea,
  silicosis, irritated eyes, DEF_DUST_PARTICLE, AGT_AIRBOURNE_SOLID, Nasdara,
  Badlands, WashHead, solar exposure, environmental hazard. Not particle .ptc/.emat
  authoring: dayz-particles. Not worn-model clothing: dayz-clothing. Not character
  import: dayz-characters. Not player stream layout: dayz-persistence. Not AI noise
  multipliers: dayz-ai-patterns. Not vehicle VFX components: dayz-vehicles.
---

# DayZ Environment Hazards (1.30 Exp)

DayZ 1.30 Experimental (build 1.30.164014) adds native environmental hazards: hybrid engine+script sandstorm (`Weather.GetSandstorm()`, `exp\scripts\scripts\3_Game\Weather.c:210` and `exp\scripts\scripts\3_Game\Sandstorm.c:6-135`), exposure with shelter fade in `ScriptedSandstormController`, heatstroke via `ThermalBiasHandler` accumulator (high heat no longer kills from `HeatComfortMdfr`), eye irritation and silicosis via `AGT_AIRBOURNE_SOLID`, `OilPitArea` oil pits, dust via `SurfaceInfo`, and sunstroke with `IsInShadow`. The Nasdara world (DLC Badlands, `appId = 3816030`) brings sand weather and solar tables, but the PBO in this build is a 6-file stub.

All evidence is `source_verified` against extracted text. No behavior is declared `runtime_verified`.

## Family selector

| Case | Skill / reference | Files |
|---|---|---|
| Activate or balance sandstorm in custom world | **This skill** | [references/sandstorm-shelter.md](references/sandstorm-shelter.md) |
| Heatstroke, shadow, WashHead, motorbike/boat in wind | **This skill** | [references/thermal-heatstroke.md](references/thermal-heatstroke.md) |
| Masks, glasses, silicosis, eye irritation | **This skill** + `dayz-clothing` for item | [references/ppe-agents.md](references/ppe-agents.md) |
| Ceiling dust, kickup, wheel `.ptc` | `dayz-particles` (VFX detail) + link here | [references/dust-oilpit-nasdara.md](references/dust-oilpit-nasdara.md) |
| Oil pit / `EffectArea` 1.30 | **This skill** | [references/dust-oilpit-nasdara.md](references/dust-oilpit-nasdara.md) |
| Nasdara / Badlands / mouflon-dog-lizard | **This skill** (map stub) | [references/dust-oilpit-nasdara.md](references/dust-oilpit-nasdara.md) |
| `PlayerBase` + `ThermalBiasHandler` stream | `dayz-persistence` | `ThermalBiasHandler.c:67-78` |
| `AIParams.sandstormToNoiseMultiplier` | `dayz-ai-patterns` | `exp\dz\DZ\data\aiconfigs\config.cpp:19-27` |

Recommendation: a new environmental hazard inherits the vanilla pattern (`EffectArea` + synced trigger, or `Weather.GetSandstorm().Start` in `WorldData`). Do not reuse direct damage from `HeatComfortMdfr` for extreme heat: that path no longer exists in 1.30.

## Day-0 critical path for sandstorm + heat in a custom world

1. [EXACT] **Access to phenomenon**: controller is not instantiated in script. On server: `GetGame().GetWeather().GetSandstorm().Start(duration, false)` / `.Stop(duration, false)` (`Sandstorm.c:12-27`, `Weather.c:210`).
   ```c
   // [EXACT] exp\scripts\scripts\3_Game\Weather.c:210
   	proto native Sandstorm GetSandstorm();
   ```
2. [EXACT] **World config**: `class Sandstorm` block with SoundSets and `particlePath` in `cfgWorlds` (`exp\dz\DZ\data\config.cpp:968-972`).
3. [EXACT] **JSON frequency**: `"SandstormData": { "sandstormFrequency": 1.0 }` (`CfgGameplayDataJson.c:433-451`). `0` disables weather-triggered storms; `2` doubles probability on Nasdara (`WorldData.c:427-442`, `Nasdara.c:563-575`).
4. [DESIGN] **WorldData**: if you want automatic storms like Nasdara, copy the `CalculateWind` + `StartSandstorm` pattern (`Nasdara.c:318-322, 561-575`). ChernarusPlus does not start sandstorm in its `WeatherOnBeforeChange`.
5. [EXACT] **Shelter**: intensity per player is `GetIntensity(head)` attenuated over 1.5 s if underground, interior (roof **and** `IsSoundInsideBuilding`) or `Car` (`ScriptedSandstormController.c:15, 142-178, 213-248, 250-282`). Motorbike and boat do **not** count as shelter.
6. [EXACT] **PPE**: mask `DEF_DUST_PARTICLE_BREATH` against silicosis; eyewear/mask/NVG `DEF_DUST_PARTICLE_EYES` against irritation (`constants.c:545-550`, `PluginTransmissionAgents.c:414-437`).
7. [EXACT] **Heat**: `HeatComfortMdfr` feeds `ThermalBiasHandler.Add` above comfort thresholds (`HeatComfortMdfr.c:74-111`). The 4 phases of `HeatStroke` read `GetThermalBiasHandler().Get()` (`HeatStroke.c:4, 58-61`).
8. [DESIGN] **Shadow and sunstroke**: `CheckShadowPresence` every `ENVIRO_TICK_SHADOW_RC_CHECK` (30 s, not 5) (`constants.c:760`, `Environment.c:406-415, 665-720`). The +2/+6/+8 °C table is in `NasdaraData.Init`, not ChernarusPlus.
9. [DESIGN] **Economy / CE**: register `OilPitArea` zones via `cfgeffectarea.json` like any `EffectArea`. Detail in [references/dust-oilpit-nasdara.md](references/dust-oilpit-nasdara.md).

## The ten invariants that break an environmental hazard

### 1. Only `Car` (closed) cancels sandstorm; motorbike and boat do not
- **Symptom**: motorbike rider keeps squinting and accumulating silicosis inside storm.
- **Cause**: `ApplyVehicleModifier` requires `transport.IsAnyInherited({Car})` (`ScriptedSandstormController.c:265`).
- **Remedy**: do not assume generic vehicular shelter. For a custom closed vehicle, inherit from `Car` or override `GetIntensityForPlayer`.

### 2. Interior = roof **and** building sound
- **Symptom**: being under an eave or a `CrashBase` does not turn off the storm.
- **Cause**: `isCurrentlyInside = (isUnderRoof && isInInterior)` and `EXCLUDED_SHELTER_TYPES = {CrashBase, Plant}` (`ScriptedSandstormController.c:20, 222-228`).
- **Remedy**: modded buildings must trigger `IsSoundInsideBuilding()` and have `ObjIntersectIFire` geometry for `IsUnder`.

### 3. Lethal heat no longer lives in `HeatComfortMdfr`
- **Symptom**: a 1.29 mod trimming heat damage in `HeatComfortMdfr` stops doing anything (player still dies from `HeatStrokePhase4`).
- **Cause**: high heat tick calls `thermalBiasHandler.Add(...)` (`HeatComfortMdfr.c:74-111`). Health damage is in `HeatStrokePhase4Mdfr.OnTick` (`HeatStroke.c:308-310`).
- **Remedy**: balance `PlayerConstants.THERMAL_BIAS_*` (`PlayerConstants.c:203-210`) or `HeatStroke` phases. Cold still subtracts health in same modifier (`HeatComfortMdfr.c:62-71`).

### 4. `HeatStrokePhase1` breaks sickness badge
- **Symptom** [CHANGELOG / confirmed in script]: sickness icons do not reappear.
- **Cause**: empty `OnActivate` and `OnDeactivate` calls `DecreaseDiseaseCount()` (`HeatStroke.c:68-75`). `ImmuneSystemMdfr` only refreshes `NTF_SICK` when `HasDisease()` changes (`ImmuneSystem.c:44-55`, `PlayerBase.c:1119-1122`).
- **Remedy**: if modding phase 1, increment counter in activate or do not decrement in deactivate.

### 5. Respiratory PPE ≠ Eye PPE
- **Symptom**: eyewear prevents silicosis, or a mask without `DEF_DUST_PARTICLE_EYES` does not prevent squinting.
- **Cause**: `AGT_AIRBOURNE_SOLID` uses MASK for `SILICOSIS` and EYEWEAR|MASK|NVG for `EYES_IRRITATION` (`PluginTransmissionAgents.c:414-437`). Squint checks `DEF_DUST_PARTICLE_EYES` (`SquintState.c:25-39`).
- **Remedy**: declare both defenses in item config. Cache depth = 2 (`GetProtectionLevelCachedEquipment` `:577-582`).

### 6. `OnCEUpdate` is no longer the `EffectArea` tick
- **Symptom**: custom area does not resize particles / does not iterate.
- **Cause**: `EffectArea` overrides `OnCEIterate(float currentTime, float elapsedTime)` (`EffectArea.c:191-195`). Changelog: `OnCEUpdate` obsolete.
- **Remedy**: override `OnCEIterate`. `SpawnParticles` anchors to `SurfaceRoadY` (`EffectArea.c:414-417`).

### 7. `Surface.GetStepsParticleID` / `EffWheelSmoke.SetSurface` are obsolete
- **Cause**: `Surface.c:64-73`, `WheelSmoke.c:32-35`. The 1.30 pipeline passes `SurfaceInfo` (`VehicleVFXComponent.c:177-186`, `VehicleDust.c:25-35`).
- **Remedy**: `SurfaceInfo.GetByName(...).GetStepParticleId()` and `SelectFromSurface`. VFX detail in `dayz-particles`.

### 8. Oil pit only deals damage in `BURNING` state
- **Cause**: random delay 3–10 s (`OilPitArea.c:10-11, 52-60`). `HeatDamage` 20.0 damage every 1 s (`OilPitTrigger.c:7-8, 53-70`).
- **Remedy**: wait for `AddState(EOilPitState.BURNING)` or trigger seems inert.

### 9. Shadow is not a raycast every 5 s
- **Cause**: `ENVIRO_TICK_SHADOW_RC_CHECK = 30` (`constants.c:760`). Capsule 50 m × 0.05 m towards `-GetSunOrMoonDirection()` (`Environment.c:679-719`). Interior, roof or `Car` force shadow true (`:667-676`).
- **Remedy**: do not copy "5 seconds" from digests; measure with 30 s timer.

### 10. `Weather.GetNoiseReductionByWeather()` does not govern AI
- **Causa**: marcado `[Obsolete]`; el nativo usa `AIParams` incluyendo `sandstormToNoiseMultiplier = 10.0` (`Weather.c:407-467`, `aiconfigs\config.cpp:19-27`).
- **Remedio**: HUD/mods → `GetNoiseReductionByWeatherEx(object)`. Infectados → config `AIParams`. Skill hermana: `dayz-ai-patterns`.

## How to verify

1. **Offline linter**: `python <KNOWLEDGE_PACK>/tools/dayz-script-validator/scripts/script_validator.py <addon_root>`. Gate `len(errors) == 0`.
2. **In-game ladder** (DayZ-MCP or Diag `-filePatching`):
   - **Weather spawn**: on server, `GetGame().GetWeather().GetSandstorm().Start(5, false)`. Client must receive PPE `REQ_SANDSTORMEFFECT` (`ScriptedSandstormController.c:310-327`).
   - **Shelter**: enter a building with `IsSoundInsideBuilding`; intensity → 0 in 1.5 s. Mount a motorbike: intensity must NOT go to 0. Enter a `Car`: yes.
   - **PPE**: with dust mask, no cough or silicosis; with glasses, no squint.
   - **Heat**: sustained high heatcomfort must raise `ThermalBias` and activate `MDF_HEAT_STROKE1..4`.
   - **WashHead**: reduces 10 `EYES_IRRITATION` (1.6 from bottle) and applies resistance for 30 s (`ActionWashHeadWettingClothesBase.c:46-55`, `ActionWashHeadItemContinuous.c:41`).
   - **Oil pit**: wait 3–10 s; then 20 HeatDamage/s and `OIL_FIRE1`/`OIL_FIRE2` particles.
3. **RPT** [UNVERIFIED texts]: search for `ThermalBiasHandler`, `Sandstorm`, `Could not get players sandstorm data`.

## Status of this build (WIP Experimental 1.30.164014)

1. **Nasdara is not playable**: `data_nasdara.pbo` has 6 files (`work\pbo-listing-diff.txt:487`). There is no `.wrp` or navmesh.
2. **Wash Head with frozen bottle**: `ActionWashHeadItemContinuous` only rejects gasoline (`:32-38`). Matches KNOWN ISSUES from changelog.
3. **Sickness icons**: bug in `HeatStrokePhase1` + `HasDisease` (invariant 4).
4. **ChernarusPlus** does not populate `m_TemperatureUnderSunModifier` in `Init` (`ChernarusPlus.c:31-80`); +2/+6/+8 solar table belongs to `NasdaraData` (`Nasdara.c:67-73`). Solar effect in Chernarus stays 0 if map lacks key [DESIGN: empty map lookup].
5. **Fire particles in OilPitTrigger.UpdateState** are `PlayInWorld` without headless guard on ignition branch (`OilPitTrigger.c:105-116`); stop does use `IsHeadlessOrDedicatedServer` in `DeferredInit`.

## Cite-then-verify

Citations relative to `E:\DayZ-Exp-Extract\1.30.164014\`. Open file at the line. Digests I/M shifted dozens of citations (e.g. "5 s" shadow, `PluginTransmissionAgents.c:377`, `PlayerBase.c:941`). NEVER copy an `[EXACT]` block from a digest: open it in `exp\`.

## References index

- [references/sandstorm-shelter.md](references/sandstorm-shelter.md): native API, `ScriptedSandstormController`, cfgWorlds, JSON, Nasdara `CalculateWind`.
- [references/thermal-heatstroke.md](references/thermal-heatstroke.md): `ThermalBiasHandler`, `HeatComfortMdfr`, 4 phases, WashHead, shadow, motorbike/boat.
- [references/ppe-agents.md](references/ppe-agents.md): agents, modifiers, symptoms, PPE, cough.
- [references/dust-oilpit-nasdara.md](references/dust-oilpit-nasdara.md): `SurfaceInfo`, roofs, oil pit, Nasdara stub, animals.
- [references/sources.md](references/sources.md): inventory of reopened files and digest line errors.

## WHAT THIS DRAFT COULD NOT VERIFY

1. **`SandstormController` C++**: progression, magnitude, and `GetPointOnEdge` live in exe.
2. **Nasdara terrain**: no `.wrp` in this build.
3. **`.p3d` / `.ptc` / `.edds` binaries**: existence via listings; emitter curves [UNVERIFIED].
4. **`PlayerBase.OnStoreSave` caller of `m_ThermalBiasHandler`**: handler writes `m_TemporaryResistanceTime` (`ThermalBiasHandler.c:67-78`) and is constructed in `PlayerBase.c:426`; digest citation `PlayerBase.c:941-950` is volcanic `OnUpdateEffectAreaServer`, not stream. Did not locate player's `OnStoreSave` in open ranges.
5. **Runtime**: no tick was measured in-game.

FIN-SKILL-DRAFT
