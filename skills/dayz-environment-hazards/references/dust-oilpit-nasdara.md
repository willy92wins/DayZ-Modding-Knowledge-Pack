# Surface dust, oil pits, and Nasdara

Detail for `.ptc` / `ParticleParamsOverrideData` / headless belongs to `dayz-particles`. Here only hazard and world contract.

## SurfaceInfo (1.30)

Protos nuevos (`exp\scripts\scripts\3_Game\SurfaceInfo.c:49-70`): step/wheel/wheel-contact/vehicle-dust (id + soundset), kickup (id / small / big), cloud y ground ambient, `GetCeilingDustParticleId()`. Grosor: `GetThickness()` (`:31`).

Wrappers obsoletos:

```c
// [EXACT] exp\scripts\scripts\4_World\Static\Surface.c:64
	[Obsolete("1.30: use SurfaceInfo.GetStepParticleId directly")]
	static int GetStepsParticleID(string surface_name) 
	{
		return SurfaceInfo.GetByName(surface_name).GetStepParticleId();
	}
```

`EffWheelSmoke.SetSurface` → `SelectFromSurface` (`WheelSmoke.c:4-35`).

## Techos

`DustEffectCeilingHandlerBase.OnStepUpdate` (`DustEffectCeilingHandler.c:25-40`): if `GetCeilingDustParticleId() > 0`, every N steps (4–8 default) lowers `pos.y` by `GetThickness()` (default 0.4 if -1) and spawns. Local: `SEffectManager.PlayInWorld`. Synced: `SEffectManager.CreateParticleServer(..., ParticleEffecterParameters("CeilingDustEffecter", ...))` (`:91-99`).

## Environment and triggering

`DustEffectManager` reads `WorldData.GetDustEffectsSettings()` (`DustEffectsManager.c:73+`, `WorldData.c:548-551`). Nasdara turns on ground+cloud (`Nasdara.c:152-170`): minimum wind 8 / 5, distances 30 / 16. Kickup: `DustKickupEffects` + `KickupDustEffect_SoundSet` (`DustKickupEffects.c:43-45`).

## Vehicles

`VehicleVFXComponent.PlayEffectData` detects ground with `g_Game.GetSurface` and passes `SurfaceInfo` (`VehicleVFXComponent.c:177-186`). `EffVehicleDust.SelectFromSurface` uses `GetVehicleDustParticleId()`; override LIFETIME/REPEAT/WIND/VELOCITY/SIZE/AIR_RESISTANCE by speed×weight (`VehicleDust.c:5-35`). `Transport.GetWeightCoef()` default 1.0 (`Transport.c:475-478`); `Offroad_02` 1.5 (`Offroad_02.c:133-136`). Digest M: truck 2.0, motorbike 0.25 — not reopened here, cite `dayz-vehicles` / `dayz-motorbikes`.

`EffWheelContact` (`:25-57`): `GetWheelContactParticleId` + `GetWheelContactSoundSetName`.

## Oil pit

Area enum (`EffectArea.c:10-16`): `EEffectAreaType.OIL_PIT = 8` (digest I wrote `EOffsetDataAreaType` — false name).

`OilPitArea` (`OilPitArea.c:7-61`): `PRE_BURNING_DURATION_MIN/MAX = 3/10`. `InitZoneServer` crea trigger y `CallLater(StartBurning, random * 1000)`. `StartBurning` → `AddState(BURNING)`.

Daño:

```c
// [EXACT] exp\scripts\scripts\4_World\Entities\ScriptedEntities\Triggers\OilPitTrigger.c:7
	protected const float 	DAMAGE_TICK_RATE 	= 1.0;	// seconds between fire damage ticks
	protected const float 	DAMAGE_MULTIPLIER	= 20.0;	// damage per tick
```

```c
// [EXACT] exp\scripts\scripts\4_World\Entities\ScriptedEntities\Triggers\OilPitTrigger.c:63
	override void OnStayServerEvent(TriggerInsider insider, float deltaTime)
	{
		if (!m_DealDamageFlag)
			return;

		EntityAI entity = EntityAI.Cast(insider.GetObject());
		if (entity)
			entity.ProcessDirectDamage(DamageType.CUSTOM, this, "", "HeatDamage", "0 0 0", DAMAGE_MULTIPLIER);
	}
```

Client: `BonfireLight` light at +2.5 m; fire `OIL_FIRE1`+`BONFIRE_SMOKE` or `OIL_FIRE2`+`SMOKE_GENERIC_WRECK`; sound `oil_pit_burn_SoundSet`, range 200 m, check 2 s (`OilPitTrigger.c:3-5, 90-116, 201-223`). Position adjusted with `SurfaceRoadY` (`:128-133`).

[DESIGN] Custom area: inherit `OilPitArea` or copy trigger+netsync pattern. Override `OnCEIterate`, not `OnCEUpdate`.

## Nasdara (DLC Badlands) — build stub

`CfgMods.nasdara` `appId = 3816030` (`exp\nasdara__data_nasdara\DZ\data_takistan\config.cpp:32-50`). Internal prefix `DZ\data_takistan`. Listing: **6 files** (`work\pbo-listing-diff.txt:487`): `aiconfigs\config.bin`, `basicdefines.hpp`, `config.bin`, plus `.p3d` / `.bisurf` / `.rvmat` impact test (`config.cpp:52-59`).

Skinning (`basicDefines.hpp:5-32`): mouflon 10 steaks / 2 guts / 1 lard / 1 bones; dog + head; lizard 1 of each. Digest I `config.cpp:214-239` does not exist: Nasdara `config.cpp` ends ~line 60.

AI (`aiconfigs\config.cpp:16-70`): `DZMouflonGroupBeh` type `DomesticHerbivores`; `DZDogGroupBeh` type `Predators` con `siegeAttackCountdownMin/Max` 10–15 (`:94-95`).

Clima: ver [sandstorm-shelter.md](sandstorm-shelter.md). Temperaturas max julio 38.4 (`Nasdara.c:49`). Dust ground/cloud ON (`:152-170`).

[CHANGELOG] 1.30 navmesh is not backwards compatible: when terrain exists, regenerate.

## Ruido IA (puntero)

`AIParams.sandstormToNoiseMultiplier = 10.0` (`exp\dz\DZ\data\aiconfigs\config.cpp:19-27`). Do not reconfigure it from script `GetNoiseReductionByWeather`. See `dayz-ai-patterns`.
