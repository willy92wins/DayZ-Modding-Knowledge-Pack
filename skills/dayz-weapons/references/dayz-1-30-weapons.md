# DayZ 1.30 Exp (build 1.30.164014) — firearm entity layer

Insertion-only companion to `dayz-weapons`. Digest K named this skill; every `[EXACT]` block below was
copied from `exp\` after opening the file (digest K reconstructed several paths and signatures — do not
copy digest snippets). `[VERIFIED-vanilla]` = read on disk in this extract. Anim motion stays with
`dayz-animation-pipeline`.

## W-STAGING1 — scripts without CfgWeapons / `.p3d` in this build

(until 1.29: any vanilla firearm with a script under `4_World/Entities/Firearms/` also shipped a
debinarizable `.p3d` + `CfgWeapons` class in the matching weapons PBO.)

(desde 1.30 Exp: four new firearm scripts plus a bayonet compile, register IK, and in two cases have
dedicated bone remaps, but their weapon PBOs do **not** contain the `.p3d` or a `CfgWeapons` /
`CfgMagazines` class. Debinarize a **shipped** peer instead — SCAR-H for a SCAR-L-shaped rifle, P1/Glock
for a pistol, CZ527/Mosin for a bolt gun, CZ61/PM73 for an open-bolt SMG.)

| Script class | Script path | Script parent | CfgWeapons / `.p3d` in this build |
|---|---|---|---|
| `SCARL_Base` | `exp\scripts\scripts\4_World\Entities\Firearms\AutomaticRifle\SCARL.c:1` | `SCARH_Base` (not `RifleBoltFree_Base`) | No `SCARL` class under `exp\weapons_firearms\`; no SCARL `.p3d` in `work\pbo-listings\exp__Addons__weapons_firearms.txt`. Shipped peer: `SCARH\ScarH.p3d` + `class SCARH_Base: Rifle_Base` in `exp\weapons_firearms\DZ\weapons\firearms\SCARH\config.cpp:40`. |
| `Luger_Base` | `...\Firearms\Pistol\Luger.c:1` | `Pistol_Base` | No Luger folder / class under `exp\weapons_pistols\`; no luger `.p3d` in `exp__Addons__weapons_pistols.txt`. |
| `LeeEnfield_Base` | `...\Firearms\Rifle\LeeEnfield.c:1` | `BoltActionRifle_ExternalMagazine_Base` | No LeeEnfield folder under `exp\weapons_firearms\`. |
| `MP18_Base` | `...\Firearms\SMG\MP18.c:1` | `OpenBolt_Base` | No MP18 folder under `exp\weapons_firearms\`. |
| `P1907_Bayonet` | `...\ItemBase\Inventory_Base\P1907_Bayonet.c:1` | `Inventory_Base` | Bayonet script only; no matching melee/attachment PBO class found in this extract. |

Magazine script stubs exist (`Mag_Luger_8Rnd`, `Mag_LeeEnfield_10Rnd`, `Mag_MP18_Drum32Rnd` in
`exp\scripts\scripts\4_World\Entities\ItemBase\Magazine\Magazines.c:65-67`) but
`exp\weapon_magazines\DZ\weapons\attachments\magazine\config.cpp` has **no** matching `CfgMagazines`
classes. Do not put these classnames in `types.xml` or trader lists for this build.

IK / reload `.anm` **are** packed (entity side only records the registration path; motion is anim-skill):

- `Luger_Base` IK: `DayZPlayerCfgBase.c:395` → `player_main_luger08.asi` + `lugerP08.anm` + `w_LugerP08_states.anm` (listing: `exp__Addons__anims_workspaces.txt` / `exp__Addons__anims_anm_player.txt`).
- `MP18_Base` IK: `:432` → `player_main_mp18.asi` + `mp18_IK.anm` + `MP18_states.anm`.
- `SCARL_Base` IK: `:445` — **same** ASI / IK / states as `SCARH_Base` (`player_main_SCARH.asi`, `SCAR_ik.anm`, `w_SCAR_states.anm`).
- `LeeEnfield_Base` IK: `:446` → `player_main_leeEnfield.asi` + `enfield.anm` + `w_enfield_states.anm`.

```
// [EXACT] exp\scripts\scripts\4_World\Entities\Firearms\AutomaticRifle\SCARL.c:1
class SCARL_Base : SCARH_Base
{
    
    override RecoilBase SpawnRecoilObject()
    {
        return new SCARLRecoil(this);
    }
	
	override void OnDebugSpawn()
    {
        GameInventory inventory = GetInventory();

        inventory.CreateInInventory( "SCAR_StockBttstck" );
        inventory.CreateInInventory( "M4_T3NRDSOptic" );
        inventory.CreateInInventory( "Battery9V" );

        SpawnAttachedMagazine("Mag_STANAG_30Rnd");
    }
};
```

`SCARH_Base` itself is `RifleBoltLock_Base` (`AutomaticRifle\SCARH.c` header) and config
`SCARH_Base: Rifle_Base` (`SCARH\config.cpp:40`). A 5.56 SCAR-L-shaped mod that wants this family
inherits **SCAR-H config + `RifleBoltLock_Base` script**, then overrides ammo/mags/recoil — it cannot
debinarize a SCAR-L body from this experimental PBO.

`P1907_Bayonet` is dual-use as attachment + melee tool: `CanPutAsAttachment` refuses the slot when
`suppressorImpro` or `weaponMuzzle` is reserved/occupied (`P1907_Bayonet.c:13-26`), and
`OnWasAttached` / `OnWasDetached` call `parent.SetBayonetAttached(...)` when `parent.IsWeapon()`
(`:28-46`). `[DESIGN]` treat it as a bayonet-slot pattern, not as a shipped item in 1.30.164014.

## Pistol FSM — virtual anim-state getters (do not duplicate the FSM)

(until 1.29: `Pistol_Base.InitStateMachine()` passed `PistolAnimState.*` constants into each stable
state constructor — `Pistol_Base.c:203-212` in `stable-1.29`.)

(desde 1.30 Exp: the same constructors take `GetDischargedPistolAnimState()` / `GetChargedPistolAnimState()`
/ `GetOpenPistolAnimState()` / `GetJammedPistolAnimState()`. Override those on the pistol class. The
stable-state classes still return `PistolStableStateID.*` from `GetCurrentStateID()` — they were not
rewritten into `PistolDischarged` helpers.)

`enum PistolAnimState` (`Pistol_Base.c:2-8`): `DEFAULT=0`, `OPENED_DISCHARGED=1`, `CLOSED_CHARGED=2`,
`JAMMED=3`. Base getters (`:611-629`): discharged → `DEFAULT`, charged → `CLOSED_CHARGED`, open →
`OPENED_DISCHARGED`, jammed → `JAMMED`.

```
// [EXACT] exp\scripts\scripts\4_World\Entities\Firearms\Pistol_Base.c:199
		// setup state machine
		// basic weapon states
		// open-closed | discharged-charged | nobullet-bullet | nomag-mag
		// regexp: [OC][CDJ][01][01]
		CD00 = new Pistol_CLO_DIS_BU0_MA0(this, NULL, GetDischargedPistolAnimState());
		CC00 = new Pistol_CLO_CHG_BU0_MA0(this, NULL, GetChargedPistolAnimState());
		CC10 = new Pistol_CLO_CHG_BU1_MA0(this, NULL, GetChargedPistolAnimState());
		CJF0 = new Pistol_CLO_JAM_BU1_MA0(this, NULL, GetJammedPistolAnimState());
		OD00 = new Pistol_OPE_DIS_BU0_MA0(this, NULL, GetOpenPistolAnimState());
		CD01 = new Pistol_CLO_DIS_BU0_MA1(this, NULL, GetDischargedPistolAnimState());
		CC01 = new Pistol_CLO_CHG_BU0_MA1(this, NULL, GetChargedPistolAnimState());
		CC11 = new Pistol_CLO_CHG_BU1_MA1(this, NULL, GetChargedPistolAnimState());
		CJF1 = new Pistol_CLO_JAM_BU1_MA1(this, NULL, GetJammedPistolAnimState());
		OD01 = new Pistol_OPE_DIS_BU0_MA1(this, NULL, GetOpenPistolAnimState());
```

Luger (toggle-lock) overrides **three** getters — not discharged, and not magic integers 1/2/3/4:

```
// [EXACT] exp\scripts\scripts\4_World\Entities\Firearms\Pistol\Luger.c:8
	override int GetChargedPistolAnimState()
	{
		return PistolAnimState.DEFAULT;
	}

	override int GetOpenPistolAnimState()
	{
		return PistolAnimState.OPENED_DISCHARGED;
	}
	
	override int GetJammedPistolAnimState()
	{
		return PistolAnimState.CLOSED_CHARGED;
	}
```

`[DESIGN]` a modded pistol with a non-Colt slide maps custom `PistolAnimState` (or a parallel enum the
weapon-states `.anm` understands) through these getters. Do not fork `Pistol_CLO_*` state classes unless
the FSM graph itself must change.

## OpenBolt magazine detach

(until 1.29: `OpenBolt_Base.SetActions()` only `RemoveAction(FirearmActionLoadBullet)` +
`FirearmActionLoadBulletQuick` — `stable-1.29` `OpenBolt_Base.c:382-388`.)

(desde 1.30 Exp: it also `AddAction(FirearmActionDetachMagazine)`.)

```
// [EXACT] exp\scripts\scripts\4_World\Entities\Firearms\OpenBolt_Base.c:382
	override void SetActions()
	{
		super.SetActions();
		
		RemoveAction(FirearmActionLoadBullet);
		RemoveAction(FirearmActionLoadBulletQuick); // Easy reload
		AddAction(FirearmActionDetachMagazine);
	}
```

`OpenBolt_Base extends Rifle_Base` at `OpenBolt_Base.c:122`. MP18 inherits this. Do not invent a
bolt-phase workaround to allow mag detach on open-bolt SMGs — the continuous detach action is registered
on the base.

`FirearmActionDetachMagazine` lives at
`exp\scripts\scripts\4_World\Classes\UserActionsComponent\Actions\Weapons\FirearmActionDetachMagazine.c:151`
(`ActionSequentialBase`). The old class is `[Obsolete("1.30: Use class FirearmActionDetachMagazine instead")]`
at `:13`. The new action returns `true` from `CanBePerformedFromInventory()` (`:262-265`).

Attach is stricter: `FirearmActionAttachMagazine` `ActionCondition` now requires
`weapon.TestAttachMagazine(weapon.GetCurrentMuzzle(), mag, false, true)` (`:256-257`). A 1.29 override of
`TestAttachMagazine` that returned true too early will now block the reload animation.

## Weapon_Base — mag detach validates FSM; `EEFired` is client FX

```
// [EXACT] exp\scripts\scripts\4_World\Entities\Firearms\Weapon_Base.c:1115
	override void EEItemDetached(EntityAI item, string slot_name)
	{
		super.EEItemDetached(item, slot_name);

		GetPropertyModifierObject().UpdateModifiers();

		if(item.IsMagazine()) {ValidateAndRepair();}
	}
```

(until 1.29: `EEItemDetached` stopped after `UpdateModifiers()` — `stable-1.29` `Weapon_Base.c:1123-1128`.)

`EEFired` is `override` and wraps muzzle-flash / overheat in `if ( !g_Game.IsHeadlessOrDedicatedServer() )`
(`Weapon_Base.c:341-346`).

Magazine drop orientation when a swap cannot fit inventory: 1.29 passed an uninitialized `float dir[4]`
into `SetGroundEx` (`stable-1.29` `WeaponManager.c:1362-1365`). 1.30 fills it from the player yaw:

```
// [EXACT] exp\scripts\scripts\4_World\Classes\Weapons\WeaponManager.c:1364
					vector rotationMatrix[3];
					float dir[4];
					Math3D.YawPitchRollMatrix(m_player.GetOrientation(), rotationMatrix);
					Math3D.MatrixToQuat(rotationMatrix, dir);
					new_il.SetGroundEx( old_mag,  m_player.GetPosition(), dir);
```

Cartridge pull in the FSM helper (until 1.29: `LocalAcquireCartridge`; desde 1.30 Exp:
`LocalAcquireCartridgeEx`):

```
// [EXACT] exp\scripts\scripts\4_World\Entities\Firearms\FSM\weapon_utils.c:7
		float damage;
		string type;
		if (mag && mag.LocalAcquireCartridgeEx(damage, type))
```

## Recoil profiles (script `RecoilBase`, not config `recoil=`)

All four new recoils subclass `RecoilBase` and fill `m_HandsCurvePoints` + mouse/cam offsets — they do
**not** use a `m_HandsOffsetRelativePoseModel` string. Path:
`exp\scripts\scripts\4_World\Classes\RecoilBase\Recoils\`.

| Class | Hands curve peak Y (point_1/2) | `m_MouseOffsetDistance` | `m_CamOffsetDistance` | Notes |
|---|---|---|---|---|
| `SCARLRecoil` | 1.3 / 1.6 | 1.5 | 0.01 | Curve values are identical to `SCARHRecoil.c` in this build. |
| `LugerRecoil` | 3 / 4 | 0.95 | 0.02 | Sharp vertical hands spline. |
| `LeeEnfieldRecoil` | 1.75 / 2 | 1.6 | 0.02 | Short relative times (`m_HandsOffsetRelativeTime = 0.125`). |
| `MP18Recoil` | 0.9 / 0.85 | 0.9 | 0.005 | Lowest cam kick of the four. |

```
// [EXACT] exp\scripts\scripts\4_World\Classes\RecoilBase\Recoils\LeeEnfieldRecoil.c:18
		m_HandsOffsetRelativeTime = 0.125;
		
		m_MouseOffsetRangeMin = 80;//in degrees min
		m_MouseOffsetRangeMax = 100;//in degrees max
		m_MouseOffsetDistance = 1.6;//how far should the mouse travel
		m_MouseOffsetRelativeTime = 0.0625;//[0..1] a time it takes to move the mouse the required distance relative to the reload time of the weapon(firing mode)
	
		m_CamOffsetDistance = 0.02;
		m_CamOffsetRelativeTime = 0.125;
```

Weapons spawn them via `SpawnRecoilObject()` (`SCARL.c:4-7`, `Luger.c:3-6`, `LeeEnfield.c:3-6`,
`MP18.c:7-10`). Config `recoil = "recoil_fal"` on `SCARH_Base` (`SCARH\config.cpp:73`) is a **different**
channel (CfgRecoils) from this script object.

## Ammo / explosion FX API (breaking)

(until 1.29: `AmmoTypesAPI.GetExplosionParticleID(string ammoName, string surfaceName)` returned `int`
— `stable-1.29` `AmmoTypes.c:57`. Callers: `DayZGame.c` explosion path.)

(desde 1.30 Exp: that method is gone. `ExplosiveEffectData` + `GetExplosiveEffectData(ammoName, surfaceName)`
return particle **and** optional sound set. Signature is **two strings in, object out** — not
`(ammoType, outData)`.)

```
// [EXACT] exp\scripts\scripts\3_Game\Global\AmmoTypes.c:1
class ExplosiveEffectData
{
	int m_ParticleID;
	string m_SoundSetName;
	
	void ExplosiveEffectData(int particleID, string soundSetName = "")
	{
		m_ParticleID = particleID;
		m_SoundSetName = soundSetName;
	}
}
```

```
// [EXACT] exp\scripts\scripts\3_Game\Global\AmmoTypes.c:90
	static ExplosiveEffectData GetExplosiveEffectData(string ammoName, string surfaceName)
	{
		ExplosiveEffectData result;
		
		#ifdef NO_GUI
		return result;
		#endif
```

Vanilla caller (`AmmoEffects.c:49-56`) gets `surfaceType` from `SurfaceGetType3D` then:

```
// [EXACT] exp\scripts\scripts\3_Game\AmmoEffects.c:49
		string surfaceType;
		g_Game.SurfaceGetType3D(pos[0], pos[1], pos[2], surfaceType);
		ExplosiveEffectData explosiveEffectData = AmmoTypesAPI.GetExplosiveEffectData(ammoType, surfaceType);
		//int particleID = GetAmmoParticleID(ammoType);
		
		if (ParticleList.IsValidId(explosiveEffectData.m_ParticleID))
		{
			return ParticleManager.GetInstance().PlayInWorld(explosiveEffectData.m_ParticleID, pos) != null;
		}
```

`DayZGame.c:3634-3638` also plays `explosiveEffectData.m_SoundSetName` via `SetStartSoundParams`.
`Init()` maps `Hit_Desert_Sand` / `Hit_Sand` (and snow/ice) per ammo; RGD5/M67 sand entries pass
`"ExplosionDustEffect_SoundSet"` (`AmmoTypes.c:66-72`).

`MagazineTypeToAmmoType` still exists — (hasta 1.29: `AmmoTypes.c:14`) (desde 1.30 Exp: `:26`) because
`ExplosiveEffectData` was prepended. Vanilla uses it in `Weapon_Base.c:840` (1.29 cited `:848`).

`ExplosivesBase`: `[Obsolete("1.30: Handled in AmmoTypes instead")]` on
`SetParticleExplosion(int particle)` (`ExplosivesBase.c:306-310`), both
`AddExplosionEffectForSurface` overloads (`:387`, `:433`), `m_TypeToSurfaceParticleIDMap` (`:40-41`),
and `InitSpecificsExplosionEffectForSurface` (`:380-384`). Put `particle = "..."` on `CfgAmmo` and
`ammoType` on the explosive vehicle; do not keep a script-side surface→particle map.

## MP18 drum magazine (script only)

`Mag_MP18_Drum32Rnd` is not an empty stub. It drives AnimationSource `"drum"`, stops the anim at 12
rounds (`m_AmmoOffset = 12`), plays `wpn_mp18_drum_mag_SoundSet` at memory point `"drum_sound"`, and
persists `m_LastAnimPhase` from save version `>= 144` (`Magazines.c:67-121`). Still no `CfgMagazines`
entry in this build — W-STAGING1 applies.

## Changelog T189758 vs scripts

`[CHANGELOG]` official 1.30 modding notes (`work\changelog-1.30-exp-modding.md:9`) claim
`enum SoundHitType` and `SurfaceInfo.GetSoundHitType()`. Grep of `exp\scripts` finds **neither**.
`SurfaceInfo.c:1-71` adds vehicle/dust particle proto natives, not hit-type. A weapon mod MUST NOT call
`GetSoundHitType()` in Enforce on this build (compile fail). Surfaces/impact particles belong to
`dayz-surfaces` if that skill is patched separately.

## Out of this skill (digest K §5)

- `GunCase` / `GunCaseKeys` / color recipes → `dayz-containers`.
- PoliceBaton health 18→13 / 40→30, `hitBricks` / `hitMudDry` melee sound arrays → `dayz-melee`.
- `Hit_Mud_Brick` / `Hit_Desert_Sand` registration → `dayz-surfaces`.
