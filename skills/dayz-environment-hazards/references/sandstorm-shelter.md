# Sandstorm: arquitectura y refugio

Fuente 1.30 Exp `1.30.164014`. Citas reabiertas en `exp\`. El controller nativo no se inspecciona (exe).

## Cómo obtener y disparar el fenómeno

`SandstormController` tiene constructores privados (`exp\scripts\scripts\3_Game\Sandstorm.c:12-13`). Alias: `typedef SandstormController Sandstorm` (`:135`). El engine instancia el tipo scriptado:

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

`Start` / `Stop` son server-only (`Sandstorm.c:20-27`). Callbacks `OnStart`/`OnStop` en servidor reenvían a `WorldData.WeatherSandstormStart/Stop` (`Sandstorm.c:90-116`). `WorldData.StartSandstorm` pone el flag `m_IsSandstormStartedByWeather` y llama `GetSandstorm().Start(timeToGather, true)` (`WorldData.c:477-489`).

API nativa útil (todas requieren storm activo salvo `IsActive`/`GetMagnitude` según comentarios): `GetDirection`, `IsPositionAtEnd`, `GetPosition`, `GetSpeed`, `GetRemainingMovementDuration`, `GetPointOnEdge` (distancia negativa = interior), `GetIntensity(worldPosition)`, `GetMagnitude` (`Sandstorm.c:32-83`). `GetIntensityForPlayer` es script, no proto (`:78`).

## Intensidad percibida (cobijo)

`GetIntensityForPlayer` (`ScriptedSandstormController.c:142-178`):

1. Posición de cabeza → `GetIntensity`. Si ≤ 0, return 0.
2. `ApplyUndergroundModifier`: `EUndergroundPresence.TRANSITIONING` o `FULL`, fade 1,5 s; además si `playerPos[1] < SurfaceY` atenúa por profundidad (`MAX_SURFACE_DISTANCE = 2.0`) (`:180-210`). Si hay `HumanCommandVehicle`, el underground return early (`:182-184`).
3. Si sigue > 0: `ApplyBuildingCheckModifier` — `MiscGameplayFunctions.IsUnder(..., ObjIntersectIFire)` **y** `IsSoundInsideBuilding()` (`:222-228`).
4. Si sigue > 0: `ApplyVehicleModifier` solo si el transport `IsAnyInherited({Car})` (`:265`).

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

Estado por jugador: `PlayerSandstormData` (`4_World\Systems\Sandstorm\PlayerSandstormData.c`). En MP la clave es UID; en SP `"-1"` (`ScriptedSandstormController.c:49-58`).

## Cliente: PPE

`OnStart` cliente pide `PPERequesterBank.REQ_SANDSTORMEFFECT` y `SetTargetIntensity` (`:310-327`). Postproceso: `PPERequester_SandstormEffect` (`PPERSandstorm.c:1-36`, color ámbar, saturación, godrays). Material `exp\graphics\graphics\Materials\postprocess\sandstorm.emat:1` shader `SnowEffect`, `ParticlesColor 0.69 0.49 0.29 1` en `:29`.

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

`CfgGameplayHandler.GetSandstormFrequency()` (`CfgGameplayHandler.c:518-521`) se copia a `WorldDataWeatherSettings.m_sandstormFrequency` en `SetupWeatherSettings` (`WorldData.c:427-442`).

## Nasdara: disparo climático

En `CalculateWind` mal tiempo, `sandstormChance = Clamp(8 * m_sandstormFrequency, 0, 100)` (`Nasdara.c:561-575`). Si sale sandstorm: `m_IsSandstorm = true`, y en OVERCAST `StartSandstorm(phmnTime * WIND_MAGNITUDE_TIME_MULTIPLIER)` (`:318-322`). ChernarusPlus no llama `StartSandstorm`.

[DESIGN] En un mapa custom sin `NasdaraData.CalculateWind`, `sandstormFrequency` no hace nada hasta que alguien llame `Start` (misión o WorldData propio).
