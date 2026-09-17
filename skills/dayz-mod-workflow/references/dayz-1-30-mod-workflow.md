# DayZ 1.30 Exp — implementation-workflow deltas (build 1.30.164014)

Companion to `SKILL.md` § DayZ 1.30 Exp. The six-layer debug hierarchy, offline
gates, and SyncVar rules still hold. This file is the 1.30 contract delta for
actions, CE rootclasses, `cfggameplay.json`, the underground trigger editor,
and NV type switches.

Line numbers are from files opened under `exp\`.

## Action pipeline: `CanBeStarted` + `CCTLiquid`

(until 1.29: `Can()` → CCT → CCI → `ActionCondition` was treated as the full
client start gate; a listed action was assumed startable.) (since 1.30 Exp:
the widget can still **show** an action whose `CanBeStarted()` is false; the
client manager does not call `ActionStart`.)

```
// [EXACT] exp\scripts\scripts\4_World\Classes\UserActionsComponent\ActionBase.c:276-291
	//! Should we display additional info panel on ActionTargetsCursor
	bool IsTargetInfoAction()
	{
		return m_InfoData != null;
	}
	
	ActionInfoDataBase GetClientActionInfo()
	{
		return m_InfoData;
	}
	
	//! If for some reason we want a non-performable action (like pure info ones)
	bool CanBeStarted()
	{
		return true;
	}
```

Client start guard:

```
// [EXACT] exp\scripts\scripts\4_World\Classes\UserActionsComponent\ActionManagerClient.c:333-340
					if (ain.JustActivate())
					{
						ActionBase action = ain.GetAction();
						if (action && action.CanBeStarted())
						{
							ActionStart(action, ain.GetUsedActionTarget(), ain.GetUsedMainItem());
							break;
						}
```

Info-only override (widget shows, F does nothing):

```
// [EXACT] exp\scripts\scripts\4_World\Classes\UserActionsComponent\Actions\Continuous\ActionPartInfo.c:18-21
	override bool CanBeStarted()
	{
		return false;
	}
```

Vanilla water/wash/fill no longer uses `CCTWaterSurfaceEx` at the wash-hands
pond action. `ActionWashHandsWater` constructs `CCTLiquid`:

```
// [EXACT] exp\scripts\scripts\4_World\Classes\UserActionsComponent\Actions\Continuous\ActionWashHandsWater.c:25-29
	override void CreateConditionComponents()
	{		
		m_ConditionItem		= new CCINone();
		m_ConditionTarget 	= new CCTLiquid(LIQUID_GROUP_WATER - LIQUID_SNOW - LIQUID_HOTWATER, UAMaxDistances.DEFAULT, UAMaxDistances.DEFAULT);
	}
```

[DESIGN] Copy `CCTLiquid` for custom drink/wash/fill on sea/pond; keep
`CCTWaterSurfaceEx` only if you intentionally diverge from vanilla. A listed
action that never starts is often `CanBeStarted()==false`, not a broken CCT.

`ActionFillBottleBase` is `[Obsolete]` in 1.30 (replaced by
`ActionObtainLiquidBase`) — domain detail in `enforce-script-reference` /
`dayz-basebuilding`. Workflow implication: do not `modded` an obsolete
vanilla action that `ActionConstructor` no longer registers.

## CE rootclasses: `MotorbikeScript` and `HouseDestructible`

(since 1.30 Exp) `cfgeconomycore.xml` on Chernarus / Livonia / Sakhal adds two
rootclasses. Digest O cited `:8-9`; the opened file places them at `:17-18`:

```
// [EXACT] exp\worlds_chernarusplus_ce\DZ\worlds\chernarusplus\ce\cfgeconomycore.xml:15-18
		<rootclass name="CarScript" act="car" reportMemoryLOD="no" /> <!-- cars (sedan, hatchback, transitBus, V3S, ...) -->
		<rootclass name="BoatScript" act="car" reportMemoryLOD="no" /> <!-- boats -->
		<rootclass name="MotorbikeScript" act="car" reportMemoryLOD="no" /> <!-- Motorbike -->
		<rootclass name="HouseDestructible" reportMemoryLOD="no" /> <!-- houses, wrecks -->
```

Same pair: `exp\worlds_enoch_ce\DZ\worlds\enoch\ce\cfgeconomycore.xml:17-18`,
`exp\sakhal__worlds_sakhal_ce\DZ\worlds\sakhal\ce\cfgeconomycore.xml:17-18`.

[DESIGN] A custom map CE that omits `MotorbikeScript` will not economy-spawn
motorbikes; omitting `HouseDestructible` drops destructible-house CE coverage.
`act="car"` on MotorbikeScript matches boats/cars (moveable vehicles).

## `cfggameplay.json` new members

(since 1.30 Exp) `CfgGameplayJson` gained `ExternalLockData` and
`SandstormData`; `ITEM_GeneralData` gained `disableBaseDecay`;
`ITEM_VehicleData` gained wheel detach/damage flags.

```
// [EXACT] exp\scripts\scripts\3_Game\CfgGameplayDataJson.c:14-23
	//!!! all member variables must correspond with the cfggameplay.json file contents !!!!
	ref ITEM_GeneralData GeneralData			= new ITEM_GeneralData;
	ref ITEM_PlayerData PlayerData 				= new ITEM_PlayerData;
	ref ITEM_WorldData WorldsData 				= new ITEM_WorldData;
	ref ITEM_BaseBuildingData BaseBuildingData 	= new ITEM_BaseBuildingData;
	ref ITEM_UIData UIData 						= new ITEM_UIData;
	ref ITEM_MapData MapData 					= new ITEM_MapData;
	ref ITEM_VehicleData VehicleData 			= new ITEM_VehicleData;
	ref ITEM_ExternalLockData ExternalLockData 	= new ITEM_ExternalLockData;
	ref ITEM_SandstormData SandstormData        = new ITEM_SandstormData;
```

```
// [EXACT] exp\scripts\scripts\3_Game\CfgGameplayDataJson.c:58-63
	bool disableBaseDamage;
	bool disableBaseDecay;
	bool disableContainerDamage;
	bool disableRespawnDialog;
	bool disableRespawnInUnconsciousness;
```

```
// [EXACT] exp\scripts\scripts\3_Game\CfgGameplayDataJson.c:407-411
	float boatDecayMultiplier = 1;
	bool canDetachAttachedCarWheels = true;
	bool canDamageAttachedCarWheels = true;
	bool canDetachAttachedBikeWheels = true;
	bool canDamageAttachedBikeWheels = true;
```

`ITEM_ExternalLockData` (`:427-430`): `protectionCountStageOne`,
`protectionCountStageTwo`, `protectionTime`, plus `protectionResetTime` at
`:430`. `ITEM_SandstormData` (`:451`): `sandstormFrequency`.

Note: `InitServer` has `disableBaseDecay` **commented out**
(`CfgGameplayDataJson.c:48`) — the JSON member exists; the server.cfg int
bridge is not wired in this build.

## Underground trigger editor (`PluginUndergroundTriggerManager`)

(since 1.30 Exp) Diag-only in-game editor (`#ifdef DIAG_DEVELOPER`), class
starts at
`exp\scripts\scripts\4_World\Plugins\PluginBase\PluginUndergroundTriggerManager.c:1-3`.
Keybinds (verified):

```
// [EXACT] exp\scripts\scripts\4_World\Plugins\PluginBase\PluginKeyBinding.c:55-56
		RegisterKeyBind(	 MENU_NONE|MENU_UNDERGROUND_TRIGGER_EDITOR	,KeyCode.KC_LCONTROL	,KeyCode.KC_SLASH		,"PluginUndergroundTriggerManager"		,"EditorToggle"			,"[LCTRL]+[/]"			,"Show/Hide Underground Trigger Editor");
		RegisterKeyBind(	 MENU_NONE|MENU_UNDERGROUND_TRIGGER_EDITOR	,KeyCode.KC_F	,-1		,"PluginUndergroundTriggerManager"		,"FocusOnObject"		,"[F]"							,"Focus on selected object");
```

[DESIGN] Level-design of underground volumes: use this editor on Diag rather
than hand-editing trigger configs blindly. Not available in retail (the plugin
file is wrapped in `DIAG_DEVELOPER`).

## NVTypes environmental variants (custom cameras)

(until 1.29: `NVTypes` ended at optics/pumpkin night variants.) (since 1.30
Exp: underground + sandstorm variants; a `switch` over the enum that is not
exhaustive will miss them.)

```
// [EXACT] exp\scripts\scripts\4_World\Entities\ManBase\DayZPlayer\DayZPlayerCamera_Base.c:54-78
enum NVTypes
{
	NONE = 0,
	NV_GOGGLES,
	NV_GOGGLES_2D,
	NV_GOGGLES_OFF,
	NV_OPTICS_ON,
	NV_OPTICS_OFF,
	NV_PUMPKIN,
	NV_OPTICS_KAZUAR_DAY,
	NV_OPTICS_KAZUAR_NIGHT,
	NV_OPTICS_STARLIGHT_DAY,
	NV_OPTICS_STARLIGHT_NIGHT,
	
	// ---- Optics condition variants ----
	NV_OPTICS_UNDERGROUND,
	NV_OPTICS_SANDSTORM_DAY,
	NV_OPTICS_SANDSTORM_NIGHT,
	NV_OPTICS_UNDERGROUND_SANDSTORM,
	
	// ---- Glasses/goggles condition variants ----
	NV_GOGGLES_DAY,
	NV_GOGGLES_UNDERGROUND,
	NV_GOGGLES_SANDSTORM,
	NV_GOGGLES_UNDERGROUND_SANDSTORM,
```

[DESIGN] Custom NV cameras: handle the new values or call vanilla
`ResolveNVType` instead of applying `rawType` directly. Domain cameras:
`enforce-script-reference`.

## Headless vs dedicated guards

(since 1.30 Exp) `CGame` exposes `IsHeadless()` and
`IsHeadlessOrDedicatedServer()` — **not** in 1.29 `Game.c`.

```
// [EXACT] exp\scripts\scripts\3_Game\Global\Game.c:1125-1136
	proto native bool		IsDedicatedServer();
	
	/**
	 \brief Check whether the application is headless or not (applies to both server and headless roboclients or anything else that is headless)
	*/
	proto native bool		IsHeadless();
	
	/**
	 \brief Check whether the application is headless or a dedicated server (it combines IsDedicatedServer and IsHeadless)
		\note This includes servers with a head as well (-headlessMode=0)
	*/
	proto native bool		IsHeadlessOrDedicatedServer();
```

(until 1.29: server-only particle/sound skips used `IsDedicatedServer()` /
`IsServer()`.) (since 1.30 Exp: vanilla skips client FX with
`!g_Game.IsHeadlessOrDedicatedServer()` so roboclients are treated like
servers.) Workflow: E18 still forbids `IsServer()`/`IsClient()` as the
client/server **guard**; for "skip VFX" prefer the new combined helper so
headless roboclients do not run particles.

## Migration checklist (implementation)

1. Action mods: implement `CanBeStarted`; do not treat a visible widget as
   startable. Water actions: `CCTLiquid`.
2. Custom CE: add `MotorbikeScript` / `HouseDestructible` rootclasses.
3. Mission `cfggameplay.json`: merge new keys; do not assume
   `disableBaseDecay` is wired from server.cfg (commented `InitServer`).
4. Exhaustive `NVTypes` switches: add underground/sandstorm cases.
5. FX that must not run on roboclients: `IsHeadlessOrDedicatedServer()`.
