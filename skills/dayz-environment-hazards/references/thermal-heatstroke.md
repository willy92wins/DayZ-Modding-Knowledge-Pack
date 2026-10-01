# ThermalBias, heat stroke, shadow, and cooling

## ThermalBiasHandler

Server instance in `PlayerBase` (`exp\scripts\scripts\4_World\Entities\ManBase\PlayerBase.c:339, 426`). Stat `EPlayerStats_current.THERMAL_BIAS`. `Add` does nothing while `m_TemporaryResistanceTime > 0` (`ThermalBiasHandler.c:21-47`). Handler persistence:

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

If a `modded class PlayerBase` touches the native stream, it MUST invoke `super.OnStoreSave` / `super.OnStoreLoad` in the same order. Exact caller in `PlayerBase.OnStoreSave` was not located (digest I cited `:941-950`, which is volcano). Contract skill: `dayz-persistence`.

## HeatComfortMdfr → bias (1.30)

Until 1.29 extreme heat could damage health from this modifier. Since 1.30 Exp the **high** heat tick feeds bias; **cold** continues deducting health:

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

| Symbol | Value |
|---|---|
| `THERMAL_BIAS_WASH_HEAD_DECREMENT` | 0.175 |
| `THERMAL_BIAS_WASH_HEAD_TEMPORARY_RESISTANCE_TIME` | 30.0 s |
| `THERMAL_BIAS_POSITIVE_HC_DECREMENT` | 0.0001 |
| `THERMAL_BIAS_POSITIVE_HC_LOW_INCREMENT` | 0.00022 |
| `THERMAL_BIAS_POSITIVE_HC_MEDIUM_INCREMENT` | 0.00032 |
| `THERMAL_BIAS_POSITIVE_HC_HIGH_INCREMENT` | 0.00050 |

## HeatStroke — 4 simultaneous phases per threshold

```c
// [EXACT] exp\scripts\scripts\4_World\Classes\PlayerModifiers\Modifiers\diseases\HeatStroke.c:3
	const int NUMBER_OF_STAGES = 4;
	const float STAGE_THRESHOLDS[NUMBER_OF_STAGES] = {0.0, 0.4, 0.6, 0.85};
```

IDs: `MDF_HEAT_STROKE1..4` (`eModifiers.c:66-69`). Sync: `MODIFIER_SYNC_HEAT_STROKE` (`ModifiersManager.c:12`).

| Phase | Active if bias | Verified effects |
|---|---|---|
| 1 | `> 0.0` | Drains water 0.35/tick (`:77-81`). `OnActivate` empty; `OnDeactivate` → `DecreaseDiseaseCount()` (`:68-75`). |
| 2 | `> 0.4` | `SYMPTOM_FEVERBLUR`, stamina `DISEASE_PNEUMONIA`, `IncreaseDiseaseCount`, water 0.5, complaints `SYMPTOM_HOT` (`:110-137`). |
| 3 | `> 0.6` | Vanilla comment: stays active alongside phase 4 (`:140`). Water 0.75, cyclic vomiting 70 water / 55 energy, `VOMIT_EXHAUSTION` (`:187-230`). Deactivate uses `<` not `<=` (`:165-167`). |
| 4 | `> 0.85` | Health damage remap 0.01–0.35/tick (`:26-28, 308-310`), `SYMPTOM_FAINT`, uncon 5–10 s every 60–120 s, shock 25 (`:18-22, 266-387`). Extra uncon if `thermalBias > 0.75` (`:371`). |

## WashHead and wet clothing

`ActionWashHeadWettingClothesBase.OnFinishProgressServer` (`:49-56`):

- `ReduceAgent(EYES_IRRITATION, 10)` (bottle override 1.6 in `ActionWashHeadItemContinuous.c:41`).
- `ThermalBiasHandler.Add(-THERMAL_BIAS_WASH_HEAD_DECREMENT)`.
- `SetTemporaryResistance(30 s)`.
- Wets slots according to container vs surface map (`:10-43`).

`ActionWashHeadItemContinuous.ActionCondition` accepts any liquid ≠ gasoline (`:32-38`). No `IsFrozen()`. [CHANGELOG] KNOWN ISSUES: frozen bottles.

`ActionWetClothingInHandsBase` wets item in hands and subtracts bias proportional to wet gain (`:44-45`).

## Shadow and sunstroke

Timer: `GameConstants.ENVIRO_TICK_SHADOW_RC_CHECK = 30` (`constants.c:760`). **No** 5 s.

`IsInShadow()` → `m_ShadowPresence` (`Environment.c:519-522`). Update (`:406-415`): if `IsInsideBuilding()` → true; otherwise, `CheckShadowPresence`.

`CheckShadowPresence` (`:665-720`): interior/roof/`Car` → true. Otherwise, capsule 50 m × radius 0.05 toward `-g_Game.GetWorld().GetSunOrMoonDirection()`, layers ITEM_LARGE|BUILDING|VEHICLE|TERRAIN|ROADWAY, `DayZPhysics.CapsuleOverlapBullet`.

If `!IsInShadow()`, temperature += `GetSunEffectOnTemperature(m_DayTime) * HeadGearProtectionAgainstSun()` (`Environment.c:868-872`). `GetSunEffectOnTemperature` scales by overcast (`WorldData.c:355-360`).

Tabla solar **Nasdara** (`Nasdara.c:67-73`): DAWN 2, MORNING 6, NOON 8, AFTERNOON 4, EVENING 2, DUSK 0, NIGHT 0. ChernarusPlus `Init` no escribe el mapa (`ChernarusPlus.c:31-80`).

`HeadGearProtectionAgainstSun` (`Environment.c:2037-2065`): if `HEADGEAR` present, isolation * `HC_EXPOSED_HEAD_TO_SUN` + 0.4; if first clothing attachment is not headgear, return exposed. [DESIGN] loop exits on first clothing that is not HEADGEAR.

## Motorbike and boat (wind)

`DetermineHeatcomfortBehavior` (`Environment.c:575-627`): `Car` with engine on → comfort 0; `Motorbike` if speed > 20; `Boat` if speed > 15 (`constants.c:792-798`). `SetHeatcomfortDirectly` subtracts comfort with `Easing.EaseInCubic` (`:1369-1444`). `BoatScript.GetHeatComfortOverride` exists (digest M); full file was not reopened here — [UNVERIFIED] default value 0.0 cited by digest M `BoatScript.c:112`.

Digest I cited `Environment.c:371-402` and `:884-942` for this wind: those lines are cargo cache and `GetWetDelta`, not motorbike behavior.
