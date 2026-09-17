# ThermalBias, golpe de calor, sombra y enfriamiento

## ThermalBiasHandler

Instancia servidor en `PlayerBase` (`exp\scripts\scripts\4_World\Entities\ManBase\PlayerBase.c:339, 426`). Stat `EPlayerStats_current.THERMAL_BIAS`. `Add` no hace nada mientras `m_TemporaryResistanceTime > 0` (`ThermalBiasHandler.c:21-47`). Persistencia del handler:

```c
// [EXACT] exp\scripts\scripts\4_World\Classes\ThermalBiasHandler.c:67
    void OnStoreSave(ParamsWriteContext ctx)
    {
        ctx.Write(m_TemporaryResistanceTime);
    }

    bool OnStoreLoad(ParamsReadContext ctx, int version)
    {
        if (!ctx.Read(m_TemporaryResistanceTime))
            return false;

        return true;
    }
```

Si un `modded class PlayerBase` toca el stream nativo, MUST invocar `super.OnStoreSave` / `super.OnStoreLoad` en el mismo orden. El caller exacto en `PlayerBase.OnStoreSave` no se localizó (digest I citó `:941-950`, que es volcán). Skill de contrato: `dayz-persistence`.

## HeatComfortMdfr → bias (1.30)

Hasta 1.29 el calor extremo podía dañar salud desde este modificador. Desde 1.30 Exp el tick de calor **alto** alimenta bias; el **frío** sigue restando salud:

```c
// [EXACT] exp\scripts\scripts\4_World\Classes\PlayerModifiers\Modifiers\HeatComfortMdfr.c:74
		//! Thermal Bias value feeding (based on HeatStroke stages)	
		if (heatComfortValue > PlayerConstants.THRESHOLD_HEAT_COMFORT_PLUS_EMPTY)
		{
			thermalBiasHandler.Add(PlayerConstants.THERMAL_BIAS_POSITIVE_HC_HIGH_INCREMENT * deltaT);
		}
		else if (heatComfortValue > PlayerConstants.THRESHOLD_HEAT_COMFORT_PLUS_CRITICAL)
		{
			thermalBiasHandler.Add(PlayerConstants.THERMAL_BIAS_POSITIVE_HC_MEDIUM_INCREMENT * deltaT);
		}
```

Constantes (`exp\scripts\scripts\3_Game\PlayerConstants.c:203-210`):

| Símbolo | Valor |
|---|---|
| `THERMAL_BIAS_WASH_HEAD_DECREMENT` | 0.175 |
| `THERMAL_BIAS_WASH_HEAD_TEMPORARY_RESISTANCE_TIME` | 30.0 s |
| `THERMAL_BIAS_POSITIVE_HC_DECREMENT` | 0.0001 |
| `THERMAL_BIAS_POSITIVE_HC_LOW_INCREMENT` | 0.00022 |
| `THERMAL_BIAS_POSITIVE_HC_MEDIUM_INCREMENT` | 0.00032 |
| `THERMAL_BIAS_POSITIVE_HC_HIGH_INCREMENT` | 0.00050 |

## HeatStroke — 4 fases simultáneas por umbral

```c
// [EXACT] exp\scripts\scripts\4_World\Classes\PlayerModifiers\Modifiers\diseases\HeatStroke.c:3
	const int NUMBER_OF_STAGES = 4;
	const float STAGE_THRESHOLDS[NUMBER_OF_STAGES] = {0.0, 0.4, 0.6, 0.85};
```

IDs: `MDF_HEAT_STROKE1..4` (`eModifiers.c:66-69`). Sync: `MODIFIER_SYNC_HEAT_STROKE` (`ModifiersManager.c:12`).

| Fase | Activa si bias | Efectos verificados |
|---|---|---|
| 1 | `> 0.0` | Drena agua 0.35/tick (`:77-81`). `OnActivate` vacío; `OnDeactivate` → `DecreaseDiseaseCount()` (`:68-75`). |
| 2 | `> 0.4` | `SYMPTOM_FEVERBLUR`, stamina `DISEASE_PNEUMONIA`, `IncreaseDiseaseCount`, agua 0.5, quejas `SYMPTOM_HOT` (`:110-137`). |
| 3 | `> 0.6` | Comentario vanilla: se queda activa junto a fase 4 (`:140`). Agua 0.75, vómito cíclico 70 agua / 55 energía, `VOMIT_EXHAUSTION` (`:187-230`). Deactivate usa `<` no `<=` (`:165-167`). |
| 4 | `> 0.85` | Daño salud remap 0.01–0.35/tick (`:26-28, 308-310`), `SYMPTOM_FAINT`, uncon 5–10 s cada 60–120 s, shock 25 (`:18-22, 266-387`). Uncon extra si `thermalBias > 0.75` (`:371`). |

## WashHead y ropa mojada

`ActionWashHeadWettingClothesBase.OnFinishProgressServer` (`:49-56`):

- `ReduceAgent(EYES_IRRITATION, 10)` (botella override 1.6 en `ActionWashHeadItemContinuous.c:41`).
- `ThermalBiasHandler.Add(-THERMAL_BIAS_WASH_HEAD_DECREMENT)`.
- `SetTemporaryResistance(30 s)`.
- Humedece slots según mapa contenedor vs superficie (`:10-43`).

`ActionWashHeadItemContinuous.ActionCondition` acepta cualquier líquido ≠ gasolina (`:32-38`). No hay `IsFrozen()`. [CHANGELOG] KNOWN ISSUES: botellas congeladas.

`ActionWetClothingInHandsBase` moja el ítem en manos y resta bias proporcional al wet gain (`:44-45`).

## Sombra e insolación

Timer: `GameConstants.ENVIRO_TICK_SHADOW_RC_CHECK = 30` (`constants.c:760`). **No** 5 s.

`IsInShadow()` → `m_ShadowPresence` (`Environment.c:519-522`). Update (`:406-415`): si `IsInsideBuilding()` → true; si no, `CheckShadowPresence`.

`CheckShadowPresence` (`:665-720`): interior/techo/`Car` → true. Si no, cápsula 50 m × radio 0.05 hacia `-g_Game.GetWorld().GetSunOrMoonDirection()`, capas ITEM_LARGE|BUILDING|VEHICLE|TERRAIN|ROADWAY, `DayZPhysics.CapsuleOverlapBullet`.

Si `!IsInShadow()`, temperatura += `GetSunEffectOnTemperature(m_DayTime) * HeadGearProtectionAgainstSun()` (`Environment.c:868-872`). `GetSunEffectOnTemperature` escala por overcast (`WorldData.c:355-360`).

Tabla solar **Nasdara** (`Nasdara.c:67-73`): DAWN 2, MORNING 6, NOON 8, AFTERNOON 4, EVENING 2, DUSK 0, NIGHT 0. ChernarusPlus `Init` no escribe el mapa (`ChernarusPlus.c:31-80`).

`HeadGearProtectionAgainstSun` (`Environment.c:2037-2065`): si hay `HEADGEAR`, isolation * `HC_EXPOSED_HEAD_TO_SUN` + 0.4; si el primer clothing attachment no es headgear, return expuesto. [DESIGN] el bucle sale en el primer clothing que no es HEADGEAR.

## Moto y lancha (viento)

`DetermineHeatcomfortBehavior` (`Environment.c:575-627`): `Car` con motor on → comfort 0; `Motorbike` si speed > 20; `Boat` si speed > 15 (`constants.c:792-798`). `SetHeatcomfortDirectly` resta comfort con `Easing.EaseInCubic` (`:1369-1444`). `BoatScript.GetHeatComfortOverride` existe (digest M); no se reabrió el fichero completo aquí — [UNVERIFIED] valor por defecto 0.0 citado por digest M `BoatScript.c:112`.

Digest I citó `Environment.c:371-402` y `:884-942` para este viento: esas líneas son caché de cargo y `GetWetDelta`, no el comportamiento de moto.
