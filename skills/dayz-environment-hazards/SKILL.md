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

DayZ 1.30 Experimental (build 1.30.164014) añade peligros ambientales nativos: tormenta de arena híbrida engine+script (`Weather.GetSandstorm()`, `exp\scripts\scripts\3_Game\Weather.c:210` y `exp\scripts\scripts\3_Game\Sandstorm.c:6-135`), exposición con fade de refugio en `ScriptedSandstormController`, golpe de calor por acumulador `ThermalBiasHandler` (el calor alto ya no mata desde `HeatComfortMdfr`), irritación ocular y silicosis por `AGT_AIRBOURNE_SOLID`, pozos de petróleo `OilPitArea`, polvo por `SurfaceInfo`, e insolación con `IsInShadow`. El mundo Nasdara (DLC Badlands, `appId = 3816030`) trae clima de arena y tablas solares, pero el PBO de esta build es un stub de 6 ficheros.

Toda la evidencia es `source_verified` sobre texto extraído. Ningún comportamiento se declara `runtime_verified`.

## Selector de familia

| Caso | Skill / reference | Ficheros |
|---|---|---|
| Activar o balancear sandstorm en mundo custom | **Esta skill** | [references/sandstorm-shelter.md](references/sandstorm-shelter.md) |
| Golpe de calor, sombra, WashHead, moto/lancha al viento | **Esta skill** | [references/thermal-heatstroke.md](references/thermal-heatstroke.md) |
| Máscaras, gafas, silicosis, irritación ocular | **Esta skill** + `dayz-clothing` para el ítem | [references/ppe-agents.md](references/ppe-agents.md) |
| Polvo de techo, kickup, `.ptc` de rueda | `dayz-particles` (detalle VFX) + enlace aquí | [references/dust-oilpit-nasdara.md](references/dust-oilpit-nasdara.md) |
| Pozo de petróleo / `EffectArea` 1.30 | **Esta skill** | [references/dust-oilpit-nasdara.md](references/dust-oilpit-nasdara.md) |
| Nasdara / Badlands / muflón-perro-lagarto | **Esta skill** (stub de mapa) | [references/dust-oilpit-nasdara.md](references/dust-oilpit-nasdara.md) |
| Stream `PlayerBase` + `ThermalBiasHandler` | `dayz-persistence` | `ThermalBiasHandler.c:67-78` |
| `AIParams.sandstormToNoiseMultiplier` | `dayz-ai-patterns` | `exp\dz\DZ\data\aiconfigs\config.cpp:19-27` |

Recomendación: un peligro ambiental nuevo hereda el patrón vanilla (`EffectArea` + trigger sincronizado, o `Weather.GetSandstorm().Start` en `WorldData`). No reutilices el daño directo de `HeatComfortMdfr` para calor extremo: ese camino ya no existe en 1.30.

## Ruta crítica day-0 para sandstorm + calor en un mundo custom

1. [EXACT] **Acceso al fenómeno**: el controller no se instancia en script. En servidor: `GetGame().GetWeather().GetSandstorm().Start(duration, false)` / `.Stop(duration, false)` (`Sandstorm.c:12-27`, `Weather.c:210`).
   ```c
   // [EXACT] exp\scripts\scripts\3_Game\Weather.c:210
   	proto native Sandstorm GetSandstorm();
   ```
2. [EXACT] **Config de mundo**: bloque `class Sandstorm` con SoundSets y `particlePath` en `cfgWorlds` (`exp\dz\DZ\data\config.cpp:968-972`).
3. [EXACT] **Frecuencia JSON**: `"SandstormData": { "sandstormFrequency": 1.0 }` (`CfgGameplayDataJson.c:433-451`). `0` anula tormentas disparadas por clima; `2` duplica la probabilidad en Nasdara (`WorldData.c:427-442`, `Nasdara.c:563-575`).
4. [DESIGN] **WorldData**: si quieres tormentas automáticas como Nasdara, copia el patrón `CalculateWind` + `StartSandstorm` (`Nasdara.c:318-322, 561-575`). ChernarusPlus no arranca sandstorm en su `WeatherOnBeforeChange`.
5. [EXACT] **Refugio**: la intensidad por jugador es `GetIntensity(head)` atenuada en 1,5 s si subterráneo, interior (techo **y** `IsSoundInsideBuilding`) o `Car` (`ScriptedSandstormController.c:15, 142-178, 213-248, 250-282`). Moto y lancha **no** cuentan como cobijo.
6. [EXACT] **PPE**: máscara `DEF_DUST_PARTICLE_BREATH` contra silicosis; gafas/máscara/NVG `DEF_DUST_PARTICLE_EYES` contra irritación (`constants.c:545-550`, `PluginTransmissionAgents.c:414-437`).
7. [EXACT] **Calor**: `HeatComfortMdfr` alimenta `ThermalBiasHandler.Add` por encima de umbrales de comfort (`HeatComfortMdfr.c:74-111`). Las 4 fases de `HeatStroke` leen `GetThermalBiasHandler().Get()` (`HeatStroke.c:4, 58-61`).
8. [DESIGN] **Sombra e insolación**: `CheckShadowPresence` cada `ENVIRO_TICK_SHADOW_RC_CHECK` (30 s, no 5) (`constants.c:760`, `Environment.c:406-415, 665-720`). La tabla +2/+6/+8 °C está en `NasdaraData.Init`, no en ChernarusPlus.
9. [DESIGN] **Economía / CE**: registra zonas `OilPitArea` vía `cfgeffectarea.json` como cualquier `EffectArea`. Detalle en [references/dust-oilpit-nasdara.md](references/dust-oilpit-nasdara.md).

## Los diez invariantes que rompen un peligro ambiental

### 1. Solo `Car` (cerrado) cancela sandstorm; moto y lancha no
- **Síntoma**: el piloto de moto sigue entrecerrando y acumulando silicosis dentro de la tormenta.
- **Causa**: `ApplyVehicleModifier` exige `transport.IsAnyInherited({Car})` (`ScriptedSandstormController.c:265`).
- **Remedio**: no asumas cobijo vehicular genérico. Para un vehículo cerrado custom, hereda de `Car` o overridea `GetIntensityForPlayer`.

### 2. Interior = techo **y** sonido de edificio
- **Síntoma**: estar bajo un alero o un `CrashBase` no apaga la tormenta.
- **Causa**: `isCurrentlyInside = (isUnderRoof && isInInterior)` y `EXCLUDED_SHELTER_TYPES = {CrashBase, Plant}` (`ScriptedSandstormController.c:20, 222-228`).
- **Remedio**: edificios modded deben disparar `IsSoundInsideBuilding()` y tener geometría `ObjIntersectIFire` para `IsUnder`.

### 3. El calor letal ya no vive en `HeatComfortMdfr`
- **Síntoma**: un mod 1.29 que recortaba el daño por calor en `HeatComfortMdfr` deja de hacer nada (el jugador sigue muriendo por `HeatStrokePhase4`).
- **Causa**: el tick de calor alto llama `thermalBiasHandler.Add(...)` (`HeatComfortMdfr.c:74-111`). El daño a salud está en `HeatStrokePhase4Mdfr.OnTick` (`HeatStroke.c:308-310`).
- **Remedio**: balancea `PlayerConstants.THERMAL_BIAS_*` (`PlayerConstants.c:203-210`) o las fases `HeatStroke`. El frío sigue restando salud en el mismo modificador (`HeatComfortMdfr.c:62-71`).

### 4. `HeatStrokePhase1` rompe el badge de enfermedad
- **Síntoma** [CHANGELOG / confirmado en script]: iconos de enfermedad no reaparecen.
- **Causa**: `OnActivate` vacío y `OnDeactivate` llama `DecreaseDiseaseCount()` (`HeatStroke.c:68-75`). `ImmuneSystemMdfr` solo refresca `NTF_SICK` cuando cambia `HasDisease()` (`ImmuneSystem.c:44-55`, `PlayerBase.c:1119-1122`).
- **Remedio**: si modeas fase 1, incrementa el contador en activate o no decrementar en deactivate.

### 5. PPE de respiración ≠ PPE de ojos
- **Síntoma**: gafas evitan silicosis, o una máscara sin `DEF_DUST_PARTICLE_EYES` no evita el entrecerrar.
- **Causa**: `AGT_AIRBOURNE_SOLID` usa MASK para `SILICOSIS` y EYEWEAR|MASK|NVG para `EYES_IRRITATION` (`PluginTransmissionAgents.c:414-437`). El squint mira `DEF_DUST_PARTICLE_EYES` (`SquintState.c:25-39`).
- **Remedio**: declara ambas defensas en config del ítem. Profundidad de caché = 2 (`GetProtectionLevelCachedEquipment` `:577-582`).

### 6. `OnCEUpdate` ya no es el tick de `EffectArea`
- **Síntoma**: área custom no redimensiona partículas / no itera.
- **Causa**: `EffectArea` overridea `OnCEIterate(float currentTime, float elapsedTime)` (`EffectArea.c:191-195`). Changelog: `OnCEUpdate` obsoleto.
- **Remedio**: overridea `OnCEIterate`. `SpawnParticles` ancla a `SurfaceRoadY` (`EffectArea.c:414-417`).

### 7. `Surface.GetStepsParticleID` / `EffWheelSmoke.SetSurface` están obsoletos
- **Causa**: `Surface.c:64-73`, `WheelSmoke.c:32-35`. El pipeline 1.30 pasa `SurfaceInfo` (`VehicleVFXComponent.c:177-186`, `VehicleDust.c:25-35`).
- **Remedio**: `SurfaceInfo.GetByName(...).GetStepParticleId()` y `SelectFromSurface`. Detalle VFX en `dayz-particles`.

### 8. Pozo de petróleo solo hace daño en estado `BURNING`
- **Causa**: delay aleatorio 3–10 s (`OilPitArea.c:10-11, 52-60`). Daño `HeatDamage` 20.0 cada 1 s (`OilPitTrigger.c:7-8, 53-70`).
- **Remedio**: espera `AddState(EOilPitState.BURNING)` o el trigger parece inerte.

### 9. Sombra no es un raycast cada 5 s
- **Causa**: `ENVIRO_TICK_SHADOW_RC_CHECK = 30` (`constants.c:760`). Cápsula 50 m × 0,05 m hacia `-GetSunOrMoonDirection()` (`Environment.c:679-719`). Interior, techo o `Car` fuerzan sombra true (`:667-676`).
- **Remedio**: no copies el "5 segundos" de resúmenes; mide con el timer de 30 s.

### 10. `Weather.GetNoiseReductionByWeather()` no gobierna la IA
- **Causa**: marcado `[Obsolete]`; el nativo usa `AIParams` incluyendo `sandstormToNoiseMultiplier = 10.0` (`Weather.c:407-467`, `aiconfigs\config.cpp:19-27`).
- **Remedio**: HUD/mods → `GetNoiseReductionByWeatherEx(object)`. Infectados → config `AIParams`. Skill hermana: `dayz-ai-patterns`.

## Cómo verificar

1. **Linter offline**: `python <KNOWLEDGE_PACK>/tools/dayz-script-validator/scripts/script_validator.py <addon_root>`. Gatea `len(errors) == 0`.
2. **Escalera in-game** (DayZ-MCP o Diag `-filePatching`):
   - **Spawn clima**: en servidor, `GetGame().GetWeather().GetSandstorm().Start(5, false)`. Cliente debe recibir PPE `REQ_SANDSTORMEFFECT` (`ScriptedSandstormController.c:310-327`).
   - **Refugio**: entra a un edificio con `IsSoundInsideBuilding`; intensidad → 0 en 1,5 s. Sube a una moto: la intensidad NO debe ir a 0. Sube a un coche `Car`: sí.
   - **PPE**: con máscara de dust, no tos ni silicosis; con gafas, no squint.
   - **Calor**: heatcomfort alto sostenido debe subir `ThermalBias` y activar `MDF_HEAT_STROKE1..4`.
   - **WashHead**: reduce 10 de `EYES_IRRITATION` (1.6 desde botella) y aplica resistencia 30 s (`ActionWashHeadWettingClothesBase.c:46-55`, `ActionWashHeadItemContinuous.c:41`).
   - **Oil pit**: espera 3–10 s; entonces 20 HeatDamage/s y partículas `OIL_FIRE1`/`OIL_FIRE2`.
3. **RPT** [UNVERIFIED textos]: busca `ThermalBiasHandler`, `Sandstorm`, `Could not get players sandstorm data`.

## Estado de esta build (WIP Experimental 1.30.164014)

1. **Nasdara no es jugable**: `data_nasdara.pbo` tiene 6 ficheros (`work\pbo-listing-diff.txt:487`). No hay `.wrp` ni navmesh.
2. **Wash Head con botella congelada**: `ActionWashHeadItemContinuous` solo rechaza gasolina (`:32-38`). Coincide con KNOWN ISSUES del changelog.
3. **Iconos de enfermedad**: bug de `HeatStrokePhase1` + `HasDisease` (invariante 4).
4. **ChernarusPlus** no rellena `m_TemperatureUnderSunModifier` en `Init` (`ChernarusPlus.c:31-80`); la tabla solar +2/+6/+8 es de `NasdaraData` (`Nasdara.c:67-73`). El efecto solar en Chernarus queda a 0 si el mapa no tiene clave [DESIGN: lookup de map vacío].
5. **Partículas de fire en OilPitTrigger.UpdateState** se `PlayInWorld` sin guard headless en el branch de encendido (`OilPitTrigger.c:105-116`); el stop sí usa `IsHeadlessOrDedicatedServer` en `DeferredInit`.

## Cite-then-verify

Citas relativas a `E:\DayZ-Exp-Extract\1.30.164014\`. Abre el fichero en la línea. Los digests I/M desplazaron decenas de citas (p. ej. "5 s" de sombra, `PluginTransmissionAgents.c:377`, `PlayerBase.c:941`). NEVER copies un bloque `[EXACT]` desde un digest: ábrelo en `exp\`.

## Índice de references

- [references/sandstorm-shelter.md](references/sandstorm-shelter.md): API nativa, `ScriptedSandstormController`, cfgWorlds, JSON, Nasdara `CalculateWind`.
- [references/thermal-heatstroke.md](references/thermal-heatstroke.md): `ThermalBiasHandler`, `HeatComfortMdfr`, 4 fases, WashHead, sombra, moto/lancha.
- [references/ppe-agents.md](references/ppe-agents.md): agentes, modificadores, síntomas, PPE, tos.
- [references/dust-oilpit-nasdara.md](references/dust-oilpit-nasdara.md): `SurfaceInfo`, techos, oil pit, stub Nasdara, animales.
- [references/sources.md](references/sources.md): inventario de ficheros reabiertos y errores de línea del digest.

## LO QUE ESTE BORRADOR NO PUDO VERIFICAR

1. **C++ de `SandstormController`**: avance, magnitud y `GetPointOnEdge` viven en el exe.
2. **Terreno Nasdara**: no hay `.wrp` en esta build.
3. **Binarios `.p3d` / `.ptc` / `.edds`**: existencia vía listings; curvas de emisor [UNVERIFIED].
4. **Caller `PlayerBase.OnStoreSave` de `m_ThermalBiasHandler`**: el handler escribe `m_TemporaryResistanceTime` (`ThermalBiasHandler.c:67-78`) y se construye en `PlayerBase.c:426`; la cita digest `PlayerBase.c:941-950` es `OnUpdateEffectAreaServer` volcánico, no el stream. No localicé el `OnStoreSave` del jugador en los rangos abiertos.
5. **Runtime**: ningún tick se midió in-game.

FIN-SKILL-DRAFT
