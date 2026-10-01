# Sandstorm: architecture and shelter

Source 1.30 Exp `1.30.164014`. Citations reopened in `exp\`. Native controller is not inspected (exe).

## How to obtain and trigger the phenomenon

`SandstormController` has private constructors (`exp\scripts\scripts\3_Game\Sandstorm.c:12-13`). Alias: `typedef SandstormController Sandstorm` (`:135`). Engine instantiates scripted type:

```c
// [EXACT] exp\scripts\scripts\3_Game\Sandstorm.c:124
	private static event typename GetScriptedType()
	{
		//
		// The following class is present in module 4_World and
		// hence its typename cannot be used directly in 3_Game.
		//
		string className = "ScriptedSandstormController";
		return className.ToType();
	}
```

`Start` / `Stop` are server-only (`Sandstorm.c:20-27`). Server `OnStart`/`OnStop` callbacks forward to `WorldData.WeatherSandstormStart/Stop` (`Sandstorm.c:90-116`). `WorldData.StartSandstorm` sets `m_IsSandstormStartedByWeather` flag and calls `GetSandstorm().Start(timeToGather, true)` (`WorldData.c:477-489`).

Useful native API (all require active storm except `IsActive`/`GetMagnitude` per comments): `GetDirection`, `IsPositionAtEnd`, `GetPosition`, `GetSpeed`, `GetRemainingMovementDuration`, `GetPointOnEdge` (negative distance = interior), `GetIntensity(worldPosition)`, `GetMagnitude` (`Sandstorm.c:32-83`). `GetIntensityForPlayer` is script, not proto (`:78`).

## Intensidad percibida (cobijo)

`GetIntensityForPlayer` (`ScriptedSandstormController.c:142-178`):

1. Head position → `GetIntensity`. If ≤ 0, return 0.
2. `ApplyUndergroundModifier`: `EUndergroundPresence.TRANSITIONING` or `FULL`, fade 1.5 s; also if `playerPos[1] < SurfaceY` attenuates by depth (`MAX_SURFACE_DISTANCE = 2.0`) (`:180-210`). If `HumanCommandVehicle` is present, underground returns early (`:182-184`).
3. If still > 0: `ApplyBuildingCheckModifier` — `MiscGameplayFunctions.IsUnder(..., ObjIntersectIFire)` **and** `IsSoundInsideBuilding()` (`:222-228`).
4. If still > 0: `ApplyVehicleModifier` only if transport `IsAnyInherited({Car})` (`:265`).

Fade:

```c
// [EXACT] exp\scripts\scripts\4_World\Systems\Sandstorm\ScriptedSandstormController.c:15
	private static const float INTERIOR_TRANSITION_DURATION = 1.5; // 1.5 seconds transition
```

```c
// [EXACT] exp\scripts\scripts\4_World\Systems\Sandstorm\ScriptedSandstormController.c:129
	protected void ApplyShelterFade(inout float intensity, bool isCurrentlySheltered, float transitionProgress)
	{
		if (isCurrentlySheltered)
		{
			intensity = Math.Lerp(intensity, 0.0, transitionProgress);
		}
		else
		{
			intensity = Math.Lerp(0.0, intensity, transitionProgress);
		}
	}
```

State per player: `PlayerSandstormData` (`4_World\Systems\Sandstorm\PlayerSandstormData.c`). In MP key is UID; in SP `"-1"` (`ScriptedSandstormController.c:49-58`).

## Cliente: PPE

Client `OnStart` requests `PPERequesterBank.REQ_SANDSTORMEFFECT` and `SetTargetIntensity` (`:310-327`). Postprocess: `PPERequester_SandstormEffect` (`PPERSandstorm.c:1-36`, amber color, saturation, godrays). Material `exp\graphics\graphics\Materials\postprocess\sandstorm.emat:1` shader `SnowEffect`, `ParticlesColor 0.69 0.49 0.29 1` at `:29`.

## cfgWorlds

```cpp
// [EXACT] exp\dz\DZ\data\config.cpp:968
			class Sandstorm
			{
				soundSets[] = {"SandStorm_Debris_SoundSet","SandStorm_Close_SoundSet","SandStorm_Dist_SoundSet"};
				particlePath = "Graphics/Particles/sandstorm/sandstorm";
			};
```

## cfggameplay.json

```c
// [EXACT] exp\scripts\scripts\3_Game\CfgGameplayDataJson.c:433
class ITEM_SandstormData : ITEM_DataBase
{
	override void InitServer()
	{
	}
	
	override bool ValidateServer()
	{
		return true;
	}
	
	//-------------------------------------------------------------------------------------------------
	//!!! all member variables must correspond with the cfggameplay.json file contents !!!!
	
	/*!
	* \brief Rate at which the sandstorm should occur.
	* \note Example values: 0 => never occur, 1 => occur at normal rate, 2 => occur twice as frequently.
	*/ 
	float sandstormFrequency = 1.0;
};
```

`CfgGameplayHandler.GetSandstormFrequency()` (`CfgGameplayHandler.c:518-521`) is copied to `WorldDataWeatherSettings.m_sandstormFrequency` in `SetupWeatherSettings` (`WorldData.c:427-442`).

## Nasdara: weather trigger

In `CalculateWind` bad weather, `sandstormChance = Clamp(8 * m_sandstormFrequency, 0, 100)` (`Nasdara.c:561-575`). If sandstorm results: `m_IsSandstorm = true`, and in OVERCAST `StartSandstorm(phmnTime * WIND_MAGNITUDE_TIME_MULTIPLIER)` (`:318-322`). ChernarusPlus does not call `StartSandstorm`.

[DESIGN] On a custom map without `NasdaraData.CalculateWind`, `sandstormFrequency` does nothing until someone calls `Start` (mission or custom WorldData).
