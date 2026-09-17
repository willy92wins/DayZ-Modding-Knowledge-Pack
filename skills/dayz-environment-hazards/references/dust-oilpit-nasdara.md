# Polvo por superficie, pozos de petróleo y Nasdara

El detalle de `.ptc` / `ParticleParamsOverrideData` / headless es de `dayz-particles`. Aquí solo el contrato de peligro y mundo.

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

`DustEffectCeilingHandlerBase.OnStepUpdate` (`DustEffectCeilingHandler.c:25-40`): si `GetCeilingDustParticleId() > 0`, cada N pasos (4–8 default) baja `pos.y` por `GetThickness()` (default 0.4 si -1) y spawnea. Local: `SEffectManager.PlayInWorld`. Synced: `SEffectManager.CreateParticleServer(..., ParticleEffecterParameters("CeilingDustEffecter", ...))` (`:91-99`).

## Ambiente y disparo

`DustEffectManager` lee `WorldData.GetDustEffectsSettings()` (`DustEffectsManager.c:73+`, `WorldData.c:548-551`). Nasdara enciende ground+cloud (`Nasdara.c:152-170`): viento mínimo 8 / 5, distancias 30 / 16. Kickup: `DustKickupEffects` + `KickupDustEffect_SoundSet` (`DustKickupEffects.c:43-45`).

## Vehículos

`VehicleVFXComponent.PlayEffectData` detecta suelo con `g_Game.GetSurface` y pasa `SurfaceInfo` (`VehicleVFXComponent.c:177-186`). `EffVehicleDust.SelectFromSurface` usa `GetVehicleDustParticleId()`; override LIFETIME/REPEAT/WIND/VELOCITY/SIZE/AIR_RESISTANCE por speed×weight (`VehicleDust.c:5-35`). `Transport.GetWeightCoef()` default 1.0 (`Transport.c:475-478`); `Offroad_02` 1.5 (`Offroad_02.c:133-136`). Digest M: camión 2.0, moto 0.25 — no reabiertos aquí, citar `dayz-vehicles` / `dayz-motorbikes`.

`EffWheelContact` (`:25-57`): `GetWheelContactParticleId` + `GetWheelContactSoundSetName`.

## Oil pit

Enum de área (`EffectArea.c:10-16`): `EEffectAreaType.OIL_PIT = 8` (digest I escribió `EOffsetDataAreaType` — nombre falso).

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

Cliente: luz `BonfireLight` a +2.5 m; fuego `OIL_FIRE1`+`BONFIRE_SMOKE` o `OIL_FIRE2`+`SMOKE_GENERIC_WRECK`; sonido `oil_pit_burn_SoundSet`, rango 200 m, check 2 s (`OilPitTrigger.c:3-5, 90-116, 201-223`). Posición ajustada con `SurfaceRoadY` (`:128-133`).

[DESIGN] Área custom: hereda `OilPitArea` o copia el patrón trigger+netsync. Overridea `OnCEIterate`, no `OnCEUpdate`.

## Nasdara (DLC Badlands) — stub de build

`CfgMods.nasdara` `appId = 3816030` (`exp\nasdara__data_nasdara\DZ\data_takistan\config.cpp:32-50`). Prefijo interno `DZ\data_takistan`. Listing: **6 ficheros** (`work\pbo-listing-diff.txt:487`): `aiconfigs\config.bin`, `basicdefines.hpp`, `config.bin`, plus `.p3d` / `.bisurf` / `.rvmat` de test de impacto (`config.cpp:52-59`).

Skinning (`basicDefines.hpp:5-32`): muflón 10 steaks / 2 guts / 1 lard / 1 bones; perro + head; lagarto 1 de cada. Digest I `config.cpp:214-239` no existe: el `config.cpp` Nasdara acaba ~línea 60.

AI (`aiconfigs\config.cpp:16-70`): `DZMouflonGroupBeh` type `DomesticHerbivores`; `DZDogGroupBeh` type `Predators` con `siegeAttackCountdownMin/Max` 10–15 (`:94-95`).

Clima: ver [sandstorm-shelter.md](sandstorm-shelter.md). Temperaturas max julio 38.4 (`Nasdara.c:49`). Dust ground/cloud ON (`:152-170`).

[CHANGELOG] Navmesh 1.30 no es backwards compatible: cuando exista terreno, regenerar.

## Ruido IA (puntero)

`AIParams.sandstormToNoiseMultiplier = 10.0` (`exp\dz\DZ\data\aiconfigs\config.cpp:19-27`). No lo reconfigures desde script `GetNoiseReductionByWeather`. Ver `dayz-ai-patterns`.
