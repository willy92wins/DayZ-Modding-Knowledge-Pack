# DayZ 1.30 Exp — Particles, dust, vehicle VFX, sandstorm

Verified against extracted 1.30 Exp scripts (`exp\scripts\scripts\`) and `exp\graphics\graphics\Materials\postprocess\sandstorm.emat`. Binary `.ptc` bodies are not in `exp\`; file existence is from `work\pbo-listings\exp__dta__graphics.txt`.

## Client gate: `IsHeadlessOrDedicatedServer`

(until 1.29: wrecks and FireplaceBase used `!g_Game.IsDedicatedServer()`.) (since 1.30 Exp: vanilla PlayOnObject / PlayInWorld / GetInstance skip **headless clients as well as dedicated servers**.)

`Game.IsHeadlessOrDedicatedServer` is proto native (`exp\scripts\scripts\3_Game\Global\Game.c:1136`). Comment at `:1132-1135`: combines `IsDedicatedServer` and `IsHeadless`, and includes headed servers (`-headlessMode=0`).

```
// [EXACT] exp\scripts\scripts\4_World\Entities\Building\Wrecks\Wreck_MI8.c:1
//New russian helicopter crash site
class Wreck_Mi8_Crashed extends CrashBase
{
	void Wreck_Mi8_Crashed()
	{
		if ( !g_Game.IsHeadlessOrDedicatedServer() )
		{
			m_ParticleEfx = ParticleManager.GetInstance().PlayOnObject(ParticleList.SMOKING_HELI_WRECK, this, Vector(2, 0, -5));
		}
	}
}
```

`ParticleManager.GetInstance()` only constructs the global pool when `!g_Game.IsHeadlessOrDedicatedServer()` (`ParticleManager.c:65`). FireplaceBase `PlayParticle` uses the same check (`FireplaceBase.c:1112`).

[DESIGN] Mods that still gate with `IsDedicatedServer()` will spawn particles on headless roboclients. Prefer `IsHeadlessOrDedicatedServer()` for VFX.

## Synced spawn: `CreateParticleServer`

`SEffectManager.CreateParticleServer` existed in 1.29 (trees, fishing, traps). 1.30 adds ceiling-dust as a first-class caller.

```
// [EXACT] exp\scripts\scripts\4_World\Classes\Dust\DustEffectCeilingHandler.c:91
//! Generic synced solution
class DustEffectCeilingHandlerSynced : DustEffectCeilingHandlerBase
{
	//! Request from server, effecter handles the rest
	override protected void CreateEffects(int ceilingParticleID, vector position)
	{
		//'spam' variant of effecters solution
		SEffectManager.CreateParticleServer(position, new ParticleEffecterParameters("CeilingDustEffecter", 2.0, ceilingParticleID));
	}
}
```

The local path (`DustEffectCeilingHandlerLocal`) still uses `SEffectManager.PlayInWorld` on the client (`:77-88`). Particle ID comes from `surfaceInfo.GetCeilingDustParticleId()` (`:27`).

```
// [EXACT] exp\scripts\scripts\3_Game\EffectManager.c:585
	//! returns unique effecter ID
	static int CreateParticleServer(vector pos, EffecterParameters parameters)
	{
		EffecterBase eff;
		eff = EffecterBase.Cast(g_Game.CreateObjectEx(parameters.m_EffecterType, pos, ECE_PLACE_ON_SURFACE));
		
		if (eff)
		{
			int id = GetFreeEffecterID();
			m_EffectersMap.Insert(id, eff);
		}
		
		eff.Init(id, parameters);
		return id;
	}
```

[DESIGN] PlayOnObject remains client-only. Use `CreateParticleServer` when every nearby client must see the same short-lived effecter.

## SurfaceInfo particle IDs

(until 1.29: `Surface.GetStepsParticleID(string)` / `GetWheelParticleID(string)` were the documented lookups.) (since 1.30 Exp: those wrappers are `[Obsolete]`.)

```
// [EXACT] exp\scripts\scripts\4_World\Static\Surface.c:64
	[Obsolete("1.30: use SurfaceInfo.GetStepParticleId directly")]
	static int GetStepsParticleID(string surface_name) 
	{
		return SurfaceInfo.GetByName(surface_name).GetStepParticleId();
	}
	
	[Obsolete("1.30: use SurfaceInfo.GetWheelParticleId directly")]
	static int GetWheelParticleID(string surface_name) 
	{
		return SurfaceInfo.GetByName(surface_name).GetWheelParticleId();
	}
```

`SurfaceInfo` proto getters (`exp\scripts\scripts\3_Game\SurfaceInfo.c:47-70`): `GetStepParticleId`, `GetStepSoundSetName`, `GetWheelParticleId`, `GetWheelSoundSetName`, `GetWheelContactParticleId`, `GetWheelContactSoundSetName`, `GetVehicleDustParticleId`, `GetVehicleDustSoundSetName`, `GetDustKickupEffectId` / `Small` / `Big`, `GetCloudEffectParticleId`, `GetGroundEffectParticleId`, `GetCeilingDustParticleId`. Missing config entry → `ParticleList.NONE`; bad entry → `ParticleList.INVALID`.

## `ParticleParamsOverrideData` and vehicle VFX

New in 1.30 (absent from 1.29 scripts). `EffectParticle` declares:

```
// [EXACT] exp\scripts\scripts\3_Game\Effects\EffectParticle.c:611
	void SelectFromSurface(string surface);
	void SelectFromSurface(SurfaceInfo surfaceInfo);
	
	void SetParticleState(int state);

	/**
	\brief Callback for overriding effect's particle attributes
	*/
	void ParticleParamsOverride(notnull ParticleParamsOverrideData data);
```

```
// [EXACT] exp\scripts\scripts\3_Game\Effects\EffectParticle.c:651
class ParticleParamsOverrideData
{
	ref TFloatArray m_FloatModifiers = new TFloatArray();
	
	void ClearAll()
	{
		m_FloatModifiers.Clear();
	}
}
```

`EffVehicleDust` (`VehicleDust.c:5-23`) reads `m_FloatModifiers[0]` as speed and `[1]` as weight, then `SetParticleParam` on `LIFETIME` (`2.5 * weight`), `REPEAT`, `WIND`, `VELOCITY` (`speed * weight`), `SIZE` (`speed * weight`), `AIR_RESISTANCE` (`1.0 * weight`). Threshold `WHEEL_DUST_THRESHOLD = 3.0`. Surface ID: `surfaceInfo.GetVehicleDustParticleId()`.

`EffWheelContact` (`EffWheelContact.c:5-23`) scales `LIFETIME` by `1.0 * weight`, sets `SPRING 15`, `REPEAT false`, `WIND false`. Surface ID: `GetWheelContactParticleId()`.

`EffExhaustSmoke` (`ExhaustSmoke.c:3-28`) scales `LIFETIME` / `BIRTH_RATE` from speed (`speed < 100` → `1 + speed * 0.1`, else `0.1`) and sets `SIZE` / `VELOCITY` to `speed * 2`.

`EffWheelSmoke.SetSurface(string)` is `[Obsolete("1.30: use SelectFromSurface instead")]` (`WheelSmoke.c:32-48`). The live path is `SelectFromSurface(SurfaceInfo)` → `GetWheelParticleId()`.

`VehicleVFXComponent` (`VehicleVFXComponent.c:96`) registers single effects (`EVehicleVFXEffect`: `DUST_BEHIND`, `ENGINE_SMOKE`, `COOLANT_STEAM`, `EXHAUST_SMOKE`) and groups (`EVehicleVFXEffectGroup`: `WHEEL_SMOKE`, `WHEEL_CONTACT`) (`EVehicleVFXTypes.c:2-17`). `GetParticleParamsOverrideData` / `GetEffectGroupParticleParamsOverrideData` feed CarScript / MotorbikeScript.

## EffectArea tick and snap

(until 1.29: `EffectArea.OnCEUpdate()` and `partPos[1] = g_Game.SurfaceY(...)`.) (since 1.30 Exp:)

```
// [EXACT] exp\scripts\scripts\4_World\Classes\ContaminatedArea\EffectArea.c:190
	// Through this we will evaluate the resize of particles
	override void OnCEIterate(float currentTime, float elapsedTime)
	{
		super.OnCEIterate(currentTime, elapsedTime);
		Tick();
	}
```

```
// [EXACT] exp\scripts\scripts\4_World\Classes\ContaminatedArea\EffectArea.c:412
	protected void SpawnParticles(ParticlePropertiesArray props, vector centerPos, vector partPos, inout int count)
	{
		float roadY = g_Game.SurfaceRoadY(partPos[0], partPos[2]);	// Snap particles to ground
		
		if (partPos[1] > roadY)
			partPos[1] = roadY;
```

[DESIGN] Custom areas that still override `OnCEUpdate` will not tick. Road snap keeps gas on bridge decks instead of the terrain under the road.

## Sandstorm: postprocess `.emat` vs `.ptc`

Weather `class Sandstorm` (`exp\dz\DZ\data\config.cpp:968-972`) sets `soundSets[] = {"SandStorm_Debris_SoundSet","SandStorm_Close_SoundSet","SandStorm_Dist_SoundSet"}` and `particlePath = "Graphics/Particles/sandstorm/sandstorm"`.

`sandstorm.emat` is **not** a `Particle` / `ParticleSprite` material. It starts with shader `SnowEffect` (`exp\graphics\graphics\Materials\postprocess\sandstorm.emat:1`). Tint is `ParticlesColor 0.69 0.49 0.29 1` (`:29`). Texture `SnowFlakesSheets_BCA.edds` (`:13`). Nasdara rain uses a separate postprocess shader `RainEffect` (`rainnasdara.emat:1`).

`Particles\sandstorm\sandstorm.ptc` is listed in `work\pbo-listings\exp__dta__graphics.txt` (the `.ptc` body is not extracted). [UNVERIFIED] emitter count / curves inside that `.ptc`.

## Oil pits

`OilPitTrigger.UpdateState` (`OilPitTrigger.c:90-116`) randomly plays `ParticleList.OIL_FIRE1` + `BONFIRE_SMOKE` or `OIL_FIRE2` + `SMOKE_GENERIC_WRECK`. Light is `BonfireLight` at `GetPosition() + "0 2.5 0"`. Stop path uses `IsHeadlessOrDedicatedServer` (`:37`, `:190`).

## Dust kickup (footstep / projectile)

`DustKickupEffects` (`exp\scripts\scripts\3_Game\DustKickupEffects.c`) maps surface → particle class/id and distance bands. SurfaceInfo supplies `GetDustKickupEffectId` / `Small` / `Big`. [DESIGN] Custom `CfgSurfaces` that want kickup, wheel dust, or ceiling dust must fill those config entries or the getters return `NONE`.

## New ParticleList constants (1.30 vs this catalog)

Verified in `exp\scripts\scripts\3_Game\Particles\ParticleList.c` and absent from 1.29 `ParticleList.c` (except `STEP_DESERT` / `STEP_SOIL`, which 1.29 already had but the catalog omitted):

| Constant | .ptc | Lines |
|---|---|---|
| `TANDOOR_HOUSE_SMALL_FIRE` … `TANDOOR_HOUSE_FIRE_STEAM_2END` | tandoor_fire_* / tandoor_smoke_* / tandoor_steam_* | 48-54 |
| `EXPLOSION_GRENADE_SAND` / `EXPLOSION_GRENADE_DESERT_SAND` | explosion_grenade_sand, explosion_grenade_desert_sand | 145-146 |
| `IMPACT_DESERT_SAND_*` / `IMPACT_MUD_BRICK_*` | impacts/hit_desert_sand_*, hit_mud_brick_* | 266-271 |
| `CEILING_WOOD` | `RegisterParticleByFullPath("graphics/particles/dust/dust_ceiling_wood")` | 378 |
| `BUILDNG_DESTRUCT_WOOD` / `BRICK` / `METAL` | building_destruction_* | 381-383 |
| `VEHICLE_WHEEL_SOIL` / `VEHICLE_WHEEL_DESERT` | vehicle_wheel_soil / vehicle_wheel_desert | 390-391 |
| `DUST_GROUND` / `DUST_CLOUD` / `DUST_VEHICLE` / `DUST_VEHICLE_SOFT` | dust/dust_grnd_01, dust/dust_effect_01, dust_vehicle, dust_vehicle_soft | 405-409 |
| `OIL_FIRE1` / `OIL_FIRE2` | fire_oil1, fire_oil2 | 411-412 |

Catalog tables: `references/vanilla-particle-catalog.md`.
