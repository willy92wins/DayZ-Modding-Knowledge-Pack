# DayZ 1.30 Exp — ragdoll data-driven and fall damage

Lane P04 overflow for `dayz-physics-engine`. SKILL.md keeps the 90% working set; this file holds
1.30 physics-engine detail that would blow the 500-line cap. Character bind path (`ragdoll =` on
`SurvivorBase`) is `dayz-characters`. Animation-graph / surrender ASI is `dayz-animation-pipeline`.

Citations are under `exp/` unless marked `stable-1.29/`. `[EXACT]` blocks were copied from the
opened file. `[UNVERIFIED]` = no script call-site or no in-game test.

## 1. `.ragdoll` / `RagdollDef`

(hasta 1.29: player ragdoll collision/mass lived in native code; scripts only saw `PhysicsSetRagdoll`.)
(desde 1.30 Exp: vanilla ships a text `RagdollDef` next to the body.)

Workbench added a ragdoll editor for `.ragdoll` files. [CHANGELOG] `work/changelog-1.30-exp-modding.md:47`.

There is **no** `LoadRagdollFile` (or similar) in extracted 1.30 scripts. [UNVERIFIED] whether a
custom creature auto-loads a same-named `.ragdoll` via the `.xob` GUID. `dayz-characters` documents
the `SurvivorBase` config bind.

```c
// [EXACT] exp/characters_bodies/DZ/characters/bodies/human.ragdoll:1
RagdollDef {
 Object "{D470A4E7581CCE23}DZ/anims/workspaces/player/Models/player_m_editorpreview.xob"
 {
  RagdollBone pelvis {
   Mass 17
   Offset -0.008 -0.011 0
   Geometries {
    PhysicsCapsuleGeometry Spine1 {
     SurfaceProperties "DZ/data/data/penetration/flesh.bisurf"
     Offset 0 0.914 0.015
     Orientation 0 0 90
     Radius 0.1
     Height 0.2
    }
    PhysicsCapsuleGeometry Spine2 {
     Offset 0 1.061 0
     Radius 0.1
     Height 0.1
    }
   }
   {
```

Head is a sphere, not a capsule:

```c
// [EXACT] exp/characters_bodies/DZ/characters/bodies/human.ragdoll:38
      RagdollBone head {
       Mass 6.1
       Offset 0.094 0 0
       Geometries {
        PhysicsSphereGeometry Head {
         SurfaceProperties "DZ/data/data/penetration/flesh.bisurf"
         Offset 0 1.672 -0.009
         Radius 0.1
        }
       }
       JointMinLimits -70 -35 -40
       JointMaxLimits 70 35 45
       JointStiffness 0.8
       JointDamper 0.3
      }
```

[DESIGN] Author a custom humanoid ragdoll by copying this tree, matching `RagdollBone` names to
the skeleton, and keeping `SurfaceProperties` on a penetration `.bisurf`. Joint limits are degrees
relative to the parent. Masses in vanilla `human.ragdoll` (kg): pelvis 17 (`:5`), spine3 15 (`:23`),
head 6.1 (`:39`), leftarm 2.1 (`:54`), leftforearm 1.7 (`:69`), rightarm 2.1 (`:85`),
rightforearm 1.7 (`:100`), leftupleg 7.5 (`:118`), leftleg 6.6 (`:134`), rightupleg 7.5 (`:159`),
rightleg 6.6 (`:175`). Sum = 73.8 kg. (The 2026-06-11 live-player `dBodyGetMass` reading of 87.5 kg
is a different body — the CCT/player body, not this ragdoll def.)

## 2. `PhysicsSetSimpleDeath` vs `PhysicsSetRagdoll`

(hasta 1.29: `PhysicsSetRagdoll` comment was at `stable-1.29/scripts/scripts/3_Game/human.c:1417-1418`.
Death used `PhysicsSetRagdoll(true)` at `stable-1.29/scripts/scripts/4_World/Entities/DayZPlayerImplement.c:736`.)

```c
// [EXACT] exp/scripts/scripts/3_Game/human.c:1448
	//! Old system for handling player death state, was previously handled by PhysicsSetRagdoll
	proto native	void		PhysicsSetSimpleDeath(bool pEnable);
	
	proto native	void		PhysicsSetRagdoll(bool pEnable);
	proto native	bool		PhysicsIsRagdoll();
```

`PhysicsIsFalling` also documents ragdoll motion:

```c
// [EXACT] exp/scripts/scripts/3_Game/human.c:1426
	//! returns true if physics controller is falling 
	//! returns true if the ragdoll is moving greater than 1m/s
	proto native 	bool		PhysicsIsFalling(bool pValidate);
```

Non-command death branch (desde 1.30 Exp):

```c
// [EXACT] exp/scripts/scripts/4_World/Entities/DayZPlayerImplement.c:743
			else
			{
				PhysicsSetSimpleDeath(true);
			}
```

Unconscious ragdoll query lives on the command, not only on `Human`:

```c
// [EXACT] exp/scripts/scripts/3_Game/human.c:644
	proto native void 	WakeUp(int targetStance = -1);
	proto native bool	IsWakingUp();

	proto native bool   IsRagdoll();
```

Vanilla clears vehicle re-attach while that ragdoll is active:

```c
// [EXACT] exp/scripts/scripts/4_World/Entities/ManBase/PlayerBase.c:3346
			if (hcu && hcu.IsRagdoll())
			{
				// Don't attach us back to the vehicle once we wake up
				m_TransportCache = null;
			}
```

## 3. Wake-up while falling

(hasta 1.29: only `m_UnconsciousTime > 2` at `stable-1.29/scripts/scripts/4_World/Entities/ManBase/PlayerBase.c:3184`, then `hcu.WakeUp`.
The 2026-06-11 0.5 s wake test buried the player 40 m under terrain.)

```c
// [EXACT] exp/scripts/scripts/4_World/Entities/ManBase/PlayerBase.c:3419
						//! protection for a player being broken when attempting to wake them up too early into unconsciousness
						if (m_UnconsciousTime > 2)
						{
							// If the player is falling then prevent waking up
							if (false == PhysicsIsFalling(false))
							{
								int wakeUpStance = DayZPlayerConstants.STANCEIDX_PRONE;
	
								//! Don't set the stance if we are swimming or in a vehicle, stance change animation could play
								if (m_Swimming.m_bWasSwimming || m_LastCommandBeforeUnconscious == DayZPlayerConstants.COMMANDID_VEHICLE)
									wakeUpStance = -1;
	
								hcu.WakeUp(wakeUpStance);
```

[DESIGN] Custom uncon/ragdoll get-up MUST keep both guards. `PhysicsIsFalling(false)` is true while
the ragdoll moves greater than 1 m/s (`exp/scripts/scripts/3_Game/human.c:1426-1428`), so a still-tumbling ragdoll will not wake.

## 4. Fall damage `CurveExp`

(hasta 1.29: linear `Math.InverseLerp`. `HEALTH_HEIGHT_LOW = 5`, `HEALTH_HEIGHT_HIGH = 14`,
`SHOCK_HEIGHT_LOW = 3`, `SHOCK_HEIGHT_HIGH = 12`, `BROKENLEGS_HEIGHT_LOW = 5`,
`BROKENLEGS_HEIGHT_HIGH = 9` — `stable-1.29/scripts/scripts/4_World/Entities/DayZPlayerImplementFallDamage.c:26-32`.
`HandleFallDamage` used `Math.InverseLerp` at `:97`.)

```c
// [EXACT] exp/scripts/scripts/4_World/Entities/DayZPlayerImplementFallDamage.c:26
	const float		HEALTH_HEIGHT_LOW 		= 2;
	const float		HEALTH_HEIGHT_HIGH 		= 12;

	private const float		SHOCK_HEIGHT_LOW 		= 0;
	private const float		SHOCK_HEIGHT_HIGH 		= 8;
	private const float		BROKENLEGS_HEIGHT_LOW 	= 3;
	private const float		BROKENLEGS_HEIGHT_HIGH 	= 8;
```

```c
// [EXACT] exp/scripts/scripts/4_World/Entities/DayZPlayerImplementFallDamage.c:92
	float CurveExp(float low, float high, float value, float power)
	{
	    float t = Math.InverseLerp(low, high, value);
	    t = Math.Clamp(t, 0, 1);
	    return Math.Pow(t, power);
	}
```

Powers used in `HandleFallDamage` (`exp/scripts/scripts/4_World/Entities/DayZPlayerImplementFallDamage.c:104-139`): health 2.0, shock 2.0, broken legs 2.5, bleeding
hands/feet 1.8, bleeding legs 2.0, gloves 2.0, shoes 2.2, pants 2.0, bleeding chance 2.0.

```c
// [EXACT] exp/scripts/scripts/4_World/Entities/DayZPlayerImplementFallDamage.c:160
	private float Randomize(int pType, float pValue)
	{
		if (pValue == 1)
			return pValue;
```

Ammo names unchanged: `FallDamageHealth` / `FallDamageShock` (`:20-21`), applied via
`ProcessDirectDamage` at `:155-156`.

[DESIGN] A 1.29 `modded` class that re-lists `HEALTH_HEIGHT_LOW = 5` and `InverseLerp` will compile
and then silently restore the old (weaker) curve. Replace the body with `CurveExp` or do not
override the constants.

## 5. Action cursor (View Geometry) + liquid surfaces

Truth #2 is still true. Line drift only:

- `RaycastRVProxy` (desde 1.30 Exp): `exp/scripts/scripts/4_World/Classes/UserActionsComponent/ActionTargets.c:255` (`RaycastRVParams` still defaults
  `ObjIntersectView` at `exp/scripts/scripts/3_Game/global/dayzphysics.c:88`).
- Ground fallback `RayCastBullet` + `ROADWAY|TERRAIN|WATERLAYER`: `:383-384`.
- Liquid surface with no object: utility 0.01 at `:532-534`. `ActionTarget` ctor
  `surfaceName` / `GetSurfaceLiquidType()` at `:125-138` and `:184-187`.

```c
// [EXACT] exp/scripts/scripts/4_World/Classes/UserActionsComponent/ActionTargets.c:255
		if (DayZPhysics.RaycastRVProxy(rayInput, results))
```

```c
// [EXACT] exp/scripts/scripts/4_World/Classes/UserActionsComponent/ActionTargets.c:383
			PhxInteractionLayers collisionLayerMask = PhxInteractionLayers.ROADWAY|PhxInteractionLayers.TERRAIN|PhxInteractionLayers.WATERLAYER;
			DayZPhysics.RayCastBullet(m_RayStart,m_RayEnd,collisionLayerMask,null,hitObject,contact_pos,hitNormal,hitFraction);
```

```c
// [EXACT] exp/scripts/scripts/4_World/Classes/UserActionsComponent/ActionTargets.c:532
		//! surfaces with liquid source
		if (m_SurfaceInfo && m_SurfaceInfo.GetLiquidType() != LIQUID_NONE)
			return 0.01;
```

## 6. Related 1.30 notes (physics-adjacent, not this skill's job)

- `disableSimulation` on house-based entities + `Entity.DisableSimulation` /
  `GetIsSimulationDisabled` — `dayz-model-pipeline`. [CHANGELOG] `work/changelog-1.30-exp-modding.md:13`.
  Script API: `exp/scripts/scripts/3_Game/Entities/Entity.c:3-6`.
- `SurfaceInfo.GetSoundHitType` / `SoundHitType` — listed in the official changelog
  (`work/changelog-1.30-exp-modding.md:9`) but **not present** in extracted `exp/scripts/scripts/3_Game/surfaceinfo.c`. [CHANGELOG]
  [UNVERIFIED] in this extract.
- Motorbike branch inside `RegisterTransportHit` (`exp/scripts/scripts/3_Game/Entities/EntityAI.c:4143-4160`) — see
  `dano-transporthit.md`. Vehicle authoring is `dayz-vehicles` / `dayz-motorbikes`.
- `DayZPlayer.IsFirstRenderFrame` (`exp/scripts/scripts/3_Game/dayzplayer.c:1186-1189`) — catchup skip, not rigid-body API.
