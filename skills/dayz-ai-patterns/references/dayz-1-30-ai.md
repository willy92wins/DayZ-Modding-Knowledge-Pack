# DayZ 1.30 Exp — vanilla AI noise, infected cower, animal groups

Citations re-opened under `exp\` (build 1.30.164014). Expansion eAI scripts are **not** in this extract; this file is vanilla infected / animal / NoiseSystem.

## Native environment noise reduction

(hasta 1.29: `NoiseAIEvaluate.GetNoiseReduction(g_Game.GetWeather())` was multiplied into `AddNoise` from player steps and several other emitters.)

(desde 1.30 Exp: the engine applies weather/sandstorm/sea reduction natively. Script query:)

```c
// [EXACT] exp\scripts\scripts\3_Game\Noise.c:12
	//! Absolute noise-strength reduction the environment (weather/sandstorm/sea) applies at 'pos'. Single source of truth used by AI.
	proto native float GetEnvironmentNoiseReduction(vector pos);
```

HUD/debug (not AI itself) already reads that proto:

`PluginPresenceNotifier.c:155-158` — `noiseSys.GetEnvironmentNoiseReduction(m_pPlayer.GetPosition())`.

Player steps no longer fold weather into the multiplier:

```c
// [EXACT] exp\scripts\scripts\4_World\Entities\DayZPlayerImplement.c:3472
			noiseMultiplier = NoiseAIEvaluate.GetNoiseMultiplier(this);
									
			AddNoise(noiseParams, noiseMultiplier);
```

Infected voice events:

```c
// [EXACT] exp\scripts\scripts\4_World\Entities\Creatures\Infected\ZombieBase.c:597
		if (g_Game.IsServer())
		{
			if (sound_event.m_NoiseParams != NULL)
				GetGame().GetNoiseSystem().AddNoise(this, sound_event.m_NoiseParams);
		}
```

## Obsolete script weather helpers (kept for HUD / old mods)

`[CHANGELOG]` says `'Weather.GetNoiseReductionByWeather'` was removed. The method is still in script, marked obsolete:

```c
// [EXACT] exp\scripts\scripts\3_Game\Weather.c:454
	[Obsolete("Use Weather.GetNoiseReductionByWeatherEx instead!")]
	float GetNoiseReductionByWeather()
	{
		float rainReduction = GetRain().GetActual() * GameConstants.RAIN_NOISE_REDUCTION_WEIGHT;
		float snowfallReduction = GetSnowfall().GetActual() * GameConstants.SNOWFALL_NOISE_REDUCTION_WEIGHT;
		
		if (rainReduction == 0 && snowfallReduction == 0)
			return 1;
		
		if (rainReduction > snowfallReduction)	// combined phenomenons dont need to have multiplicative effects
			return 1 - rainReduction;
		else
			return 1 - snowfallReduction;
	}
```

Replacement that also sees sandstorm (still `[Obsolete]`, not the AI source of truth):

```c
// [EXACT] exp\scripts\scripts\3_Game\Weather.c:407
	[Obsolete("1.30: AI noise dampening is now done natively via AIParams config parameters. Kept for HUD and old mods.")]
	float GetNoiseReductionByWeatherEx(notnull Object object)
	{
		float rainReduction = GetRainNoiseReduction();
		float snowfallReduction = GetSnowfallNoiseReduction();
		float sandstormReduction = GetSandstormNoiseReduction(object);
```

```c
// [EXACT] exp\scripts\scripts\4_World\Static\SensesAIEvaluate.c:92
	[Obsolete("Use GetNoiseReductionEx instead!")]
	static float GetNoiseReduction(Weather weather)
	{
		if (weather)
			return weather.GetNoiseReductionByWeather();
		 
		return 0;
	}
```

`GetNoiseReductionEx` (`SensesAIEvaluate.c:18-26`) forwards to `GetNoiseReductionByWeatherEx`.

## `AIParams` climate multipliers

(hasta 1.29: `rainToNoiseMultiplier` and `seaToNoiseMultiplier` only — `stable-1.29\dz\DZ\data\aiconfigs\config.cpp:21-23`.)

(desde 1.30 Exp:)

```cpp
// [EXACT] exp\dz\DZ\data\aiconfigs\config.cpp:19
class AIParams
{
	maxNoiseRange = 300.0;
	rainToNoiseMultiplier = 10.0;
	snowfallToNoiseMultiplier = 5.0;
	seaToNoiseMultiplier = 15.0;
	fogToNoiseMultiplier = 10.0;
	windToNoiseMultiplier = 10.0;
	sandstormToNoiseMultiplier = 10.0;
	noiseDampeningMultiplier = 0.7;
```

`[DESIGN]` To make infected hear less in a sandstorm, raise `sandstormToNoiseMultiplier` (or the other `*ToNoiseMultiplier` keys). Do not override `GetNoiseReductionByWeather` expecting native AI to follow.

## Infected `MINDSTATE_COWER`

```c
// [EXACT] exp\scripts\scripts\3_Game\Entities\DayZInfected.c:12
	//! mind states
	MINDSTATE_CALM,
	MINDSTATE_DISTURBED,
	MINDSTATE_ALERTED,
	MINDSTATE_CHASE,
	MINDSTATE_FIGHT,
	MINDSTATE_COWER,
```

```c
// [EXACT] exp\scripts\scripts\4_World\Entities\Creatures\Infected\ZombieBase.c:54
		RegisterNetSyncVariableInt("m_MindState", -1, 5);
```

```c
// [EXACT] exp\scripts\scripts\4_World\Entities\Creatures\Infected\ZombieBase.c:474
			//! sandstorm cowering, movement is already stopped by the AI, hold the calm idle pose
			case DayZInfectedConstants.MINDSTATE_COWER:
				if ( moveCommand && !moveCommand.IsTurning() )
					moveCommand.SetIdleState(0);
				break;
```

`[UNVERIFIED]` Native C++ that **enters** `MINDSTATE_COWER` from sandstorm intensity is not in Enforce; only the script reaction is visible.

## Animal group templates (Nasdara)

```cpp
// [EXACT] exp\nasdara__data_nasdara\DZ\data_takistan\aiconfigs\config.cpp:16
	class DZMouflonGroupBeh
	{
		type = "DomesticHerbivores";
		alertDistributionSpeed = 20.0;
		groupMaxAlertedSpreadRadius = 40.0;
		catchUpTestDelay = 4.0;
		catchUpStartRadius = 30.0;
		catchUpTargetRadius = 12.0;
		groupRadius = 10.0;
```

```cpp
// [EXACT] exp\nasdara__data_nasdara\DZ\data_takistan\aiconfigs\config.cpp:68
	class DZDogGroupBeh
	{
		type = "Predators";
		alertDistributionSpeed = 10.0;
		catchUpTestDelay = 4.0;
		catchUpStartRadius = 60.0;
		catchUpTargetRadius = 7.0;
		groupRadius = 10.0;
```

Dog lifecycle uses `zoneType = "HuntingGround"` (`:114`) with `siegeAttackCountdownMin = 10` / `Max = 15` (`:94-95`) and `safeKeeperIntervalMin = 20` / `Max = 40` (`:92-93`).

## Navmesh (eAI pathfinding on custom maps)

`[CHANGELOG]` (`work\changelog-1.30-exp-modding.md:21-23`): navmesh file is a newer version with no backwards compatibility — regenerate for custom terrains. Navmesh can use a hide animation source if configured in EntityType Navmesh config. Not re-verified against binary `.nm` files (binaries are not in `exp\`).
