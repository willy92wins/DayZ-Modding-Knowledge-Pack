# DayZ 1.30 Exp (build 1.30.164014) — Enforce Script contract

Consultation reference for `enforce-script-reference`. Facts re-opened under `exp\` (digests E / F / O as a map). `[EXACT]` copied from those files. `[DESIGN]` = migration advice.

Until 1.29: CE tick `OnCEUpdate()`, inventory hooked `ProcessInputData`, fill-bottle `ActionFillBottleBase`, 3rd-person `World.Is3rdPersonDisabled()`, storage `142`. Since 1.30 Exp: replacements below.

## 1. Central Economy tick: `OnCEUpdate` → `OnCEIterate`

Until 1.29: `EntityAI.OnCEUpdate()` had no time args (`stable-1.29\scripts\scripts\3_Game\Entities\EntityAI.c:3860`). Since 1.30 Exp it is empty `[Obsolete]`; the live tick is `OnCEIterate(float currentTime, float elapsedTime)`.

```c
// [EXACT] exp\scripts\scripts\3_Game\Entities\EntityAI.c:3881
	void OnCEIterate(float currentTime, float elapsedTime)
	{
		ProcessVariables(elapsedTime);
		
		ConstructionBasic constructionComponent = GetConstructionBasic();
		if (constructionComponent && ConstructionBasic.CanConstructionDecay() && GetAllowDamage()) //checks if server allows damage AND decay
			constructionComponent.ProcessConstructionDecay(elapsedTime);
	}
```

```c
// [EXACT] exp\scripts\scripts\3_Game\Entities\EntityAI.c:4893
	[Obsolete("1.30: Use OnCEIterate(float currentTime, float elapsedTime) instead")]
	void OnCEUpdate();
```

`[DESIGN]` Rename `override void OnCEUpdate()` to `OnCEIterate(float currentTime, float elapsedTime)` and `super.OnCEIterate(currentTime, elapsedTime)`.

## 2. `GAME_STORAGE_VERSION = 144`

Until 1.29: `static int GAME_STORAGE_VERSION = 142;` (`stable-1.29\scripts\scripts\3_Game\Global\Game.c:5`). Since 1.30 Exp:

```c
// [EXACT] exp\scripts\scripts\3_Game\Global\Game.c:5
static int GAME_STORAGE_VERSION = 144;
```

`CGame` still calls `StorageVersion(GAME_STORAGE_VERSION)` (`Game.c:50`). Stream layout = skill `dayz-persistence`. Do not hardcode `142` against `g_Game.SaveVersion()`.

## 3. Inventory command pipeline (retail no longer calls `ProcessInputData`)

Until 1.29: one `ProcessInputData(ParamsReadContext ctx, bool is_juncture, bool is_remote)`. Since 1.30 Exp that method still exists (`DayZPlayerInventory.c:3319`) but call sites are `#ifdef DIAG_DEVELOPER` **and** `PluginInventoryDebug.IsOldProcessInputDataEnable()`. Retail uses Validate / Execute*.

```c
// [EXACT] exp\scripts\scripts\4_World\Systems\Inventory\DayZPlayerInventory.c:668
#ifdef DIAG_DEVELOPER
		if (PluginInventoryDebug.Cast(GetPlugin(PluginInventoryDebug)).IsOldProcessInputDataEnable())
		{
			ProcessInputData(ctx, true, false);
		}
		else
		{
#endif
			if(g_Game.IsServer())
			{
				ExecuteInventoryCommandServer(ctx);
			}
			else
			{
				ExecuteInventoryCommandClient(ctx);
			}
#ifdef DIAG_DEVELOPER
		}
#endif
```

| Method | Cite | Role |
|---|---|---|
| `bool ValidateInventoryCommandServer(ParamsReadContext ctx)` | `DayZPlayerInventory.c:3410` | Server juncture validation |
| `bool ExecuteInventoryCommandServer(ParamsReadContext ctx)` | `:3501` | Server execute |
| `bool ExecuteInventoryCommandClient(ParamsReadContext ctx)` | `:3569` | Owner-client after juncture |
| `bool ExecuteInventoryCommandRemote(ParamsReadContext ctx)` | `:3633` | Remote-client execute |

Input-user-data uses the same DIAG gate (`:734-744`) then `ValidateInventoryCommandServer` on server. `[DESIGN]` A `modded DayZPlayerInventory` that only overrode `ProcessInputData` is silent in retail.

### 3.1 `INPUT_UDT_INVENTORY_CHECK` / `OnInventoryCheck`

```c
// [EXACT] exp\scripts\scripts\3_Game\tools\Component\_constants.c:19
const int INPUT_UDT_INVENTORY_CHECK					= 16;
```

Caps: `INVENTORY_REPAIR_MAX_DISTANCE = 500.0`, `INVENTORY_REPAIR_MAX_ITEMS = 5` (`DayZPlayerInventory.c:163-164`, comments misspelled in vanilla).

```c
// [EXACT] exp\scripts\scripts\4_World\Systems\Inventory\DayZPlayerInventory.c:5003
	override bool OnInventoryCheck(int userDataType, ParamsReadContext ctx)
	{
		if (userDataType == INPUT_UDT_INVENTORY_CHECK)
```

Mismatch → `InventoryInputUserData.SendServerInventoryCheck` (`:5052`), DIAG-gated by `IsDesyncRepairEnable` (`:5048-5055`).

---

## 4. `[Obsolete]` takes → Target* variants

Until 1.29: `TakeEntityToCargo` / `ToCargoEx` / `AsAttachment` / `AsAttachmentEx`. Since 1.30 Exp they are `[Obsolete]` wrappers (digest E said `:1388-1430`; real block is `:1345-1386`).

```c
// [EXACT] exp\scripts\scripts\3_Game\Systems\Inventory\Inventory.c:1345
	[Obsolete("1.30: Use TakeEntityToTargetCargo instead")]
	bool TakeEntityToCargo(InventoryMode mode, notnull EntityAI item)
```

Same file: `TakeEntityToCargoEx` `[Obsolete]` `:1357`; `TakeEntityAsAttachmentEx` `[Obsolete]` `:1374` (attribute line is extra-indented in vanilla); `TakeEntityAsAttachment` `[Obsolete]` `:1382`.

Replacements: `TakeEntityToTargetCargo(mode, target, item)` `:1077`; `TakeEntityToTargetCargoEx(mode, cargo, item, row, col)` `:1084`; `TakeEntityAsTargetAttachmentEx(mode, target, item, slot)` `:1100`; `TakeEntityAsTargetAttachment(mode, target, item)` `:1142`. SP-184 identity-gate (`FindAttachment(slot) == item`) still applies.

---

## 5. Hand FSM guards

Until 1.29: `HandGuardCanMove` / `CanSwap` / `CanForceSwap` auto-passed `e.m_IsJuncture || e.m_IsRemote` (`stable-1.29\scripts\scripts\3_Game\Systems\Inventory\Hand_Guards.c:299,325,351`). Since 1.30 Exp only `e.m_IsRemote`; else `LocationCanMoveEntity` / `CanSwapEntitiesEx` / `CanForceSwapEntitiesEx`.

```c
// [EXACT] exp\scripts\scripts\3_Game\Systems\Inventory\Hand_Guards.c:299
		bool result = e.m_IsRemote;
		if (result == false)
		{
			result = GameInventory.LocationCanMoveEntity(es.GetSrc(), es.GetDst());
		}
```

Same `m_IsRemote` test at `:325` and `:351`. New guard `HandGuardIsNotSurrendered` (`:405`) returns `!m_Player.IsSurrendered()` (`:412`). `[DESIGN]` Hand events on a surrendered player fail the FSM.

---

## 6. `GUIInventoryAttachmentsProps`, `TypeAttachmentGroupData`, `ItemBaseType`

```c
// [EXACT] exp\scripts\scripts\3_Game\Entities\TypeAttachmentGroupDataHolders.c:39
		m_PropsPath = "" + pathBase + " GUIInventoryAttachmentsProps";
		if (!g_Game.ConfigIsExisting(m_PropsPath) || m_AttachmentGroupMap != null)
			return;
```

Category reach is a 1.5 m dome, vertical leeway `-range/5` (`AttachmentCategoriesRow.c:764`, default `range = 1.5` → −0.3 m).

`ItemBaseType` (`typedef ItemBaseType Inventory_BaseType`, `ItemBaseType.c:1-4`) caches type config. Keys re-opened: `varWetMax` `:71`, `headSelectionsToHide` `:105-108`, `hideSelectionsByinventorySlot` `:111-113`, `quickBarBonus` `:115`, `itemModelLength` / `itemAttachOffset` `:86-92`, `temperaturePerQuantityWeight` `:117-119`, `EnvironmentWetnessIncrements` Soaking/Drying `:121-137`, `compatibleLocks` / `lockType` `:96-99`. Rebuilding slots `Slot_RB_LvL*` from `exp\scripts\scripts\config.cpp:2924` (`Slot_RB_LvL1_Log`, `stackMax = 15`).

---

## 7. Action system 1.30

### 7.1 `CanBeStarted`, `IsTargetInfoAction`, `SortActions`, `InitInfoData`

```c
// [EXACT] exp\scripts\scripts\4_World\Classes\UserActionsComponent\ActionBase.c:276
	//! Should we display additional info panel on ActionTargetsCursor
	bool IsTargetInfoAction()
	{
		return m_InfoData != null;
	}
```

```c
// [EXACT] exp\scripts\scripts\4_World\Classes\UserActionsComponent\ActionBase.c:287
	//! If for some reason we want a non-performable action (like pure info ones)
	bool CanBeStarted()
	{
		return true;
	}
```

`InitInfoData()` is the empty hook (`ActionBase.c:159-161`). Info-only construction: `ActionPartInfo.c:18-21` `override bool CanBeStarted() { return false; }`. Client does not `ActionStart` unless `CanBeStarted()` (`ActionManagerClient.c:336-337`).

```c
// [EXACT] exp\scripts\scripts\4_World\Classes\UserActionsComponent\ActionInput.c:464
	//! sorts in order: performable -> non-performable (usually info). Extend/override as needed
	protected void SortActions(array<ActionBase> allActions)
```

### 7.2 Line drift: `PerformAction` / `Can()` / `UA_AM_*`

Until 1.29: SKILL.md cited `PerformAction` `:756` inside `#ifdef BOT` `:754-760`, `PerformActionStart` `:762`, `ActionBase.Can` `:912`. Since 1.30 Exp:

```c
// [EXACT] exp\scripts\scripts\4_World\Classes\UserActionsComponent\ActionManagerClient.c:796
#ifdef BOT
	/// used for bots
	void PerformAction(int user_action_id, ActionTarget target, ItemBase item, Param extraData = NULL)
	{
		ActionStart(GetAction(user_action_id), target, item, extraData);
	}
#endif
	
	void PerformActionStart(ActionBase action, ActionTarget target, ItemBase item, Param extra_data = NULL)
```

SP `PerformActionStart` no-ops if pending/current (`:806-814`). `GetActionState()` returns `UA_AM_INIT` while pending (`:822-825`). `Can(PlayerBase, ActionTarget, ItemBase)` is at `ActionBase.c:968`. Using public `Can` not protected `ActionCondition` is still the rule.

```c
// [EXACT] exp\scripts\scripts\3_Game\constants.c:508
const int		UA_AM_INIT = 14;
const int		UA_AM_PENDING = 15;
const int		UA_AM_ACCEPTED = 16;
const int		UA_AM_REJECTED = 17;
```

Do not hardcode those integers (1.30 inserted `UA_AM_INIT`).

### 7.3 `ActionFillBottleBase` → `ActionObtainLiquidBase`

```c
// [EXACT] exp\scripts\scripts\4_World\Classes\UserActionsComponent\Actions\Continuous\ActionFillBottleBase.c:28
[Obsolete("1.30: replaced by class ActionObtainLiquidBase")]
class ActionFillBottleBase: ActionContinuousBase
```

`RegisterActions` inserts `ActionObtainLiquidBase` (`ActionConstructor.c:156`), not FillBottle. `Bottle_Base.c:364` `AddAction(ActionObtainLiquidBase)`. Fill CCT:

```c
// [EXACT] exp\scripts\scripts\4_World\Classes\UserActionsComponent\Actions\Continuous\ActionObtainLiquidBase.c:56
		m_ConditionItem 	= new CCINonRuined();
		m_ConditionTarget 	= new CCTLiquid(m_AllowedLiquidMask, UAMaxDistances.DEFAULT, UAMaxDistances.DEFAULT);
```

`[DESIGN]` `modded ActionFillBottleBase` never instantiates.

### 7.4 Animation overrides on `EntityAI`

`ActionOverrideData` is at `EntityAI.c:103-108`. Map:

```c
// [EXACT] exp\scripts\scripts\3_Game\Entities\EntityAI.c:117
	static ref map<typename, ref TActionAnimOverrideMap> m_EntityActionOverrides = new map<typename, ref TActionAnimOverrideMap>; 
```

`OverrideActionAnimation(typename action, int commandUID, int stanceMask = -1, int commandUIDProne = -1)` at `:4758`. `AnimatedActionBase.GetCommandOverride` looks up item type then **target object type** (`:284-290`). Until 1.29 this lived on `ItemBase.m_ItemActionOverrides` — that name is gone.

### 7.5 CCT: `CCTLiquid`, `CCTCursorInherited`, head distance

```c
// [EXACT] exp\scripts\scripts\4_World\Classes\UserActionsComponent\TargetConditionsComponents\CCTLiquid.c:37
	void CCTLiquid(int allowedLiquidSource, float maximalTargetDistance = UAMaxDistances.DEFAULT, float maxVerticalReach = UAMaxDistances.DEFAULT, SurfaceDetectionType surfaceDetectionType = SurfaceDetectionType.Roadway, bool allowSeaLevelCursorFallback = false)
```

```c
// [EXACT] exp\scripts\scripts\4_World\Classes\UserActionsComponent\TargetConditionsComponents\CCTCursorInherited.c:28
				vector cursorHitPos = target.GetCursorHitPos();
				bool fromPlayerRoot = vector.DistanceSq(cursorHitPos, player.GetPosition()) <= m_MaximalActionDistanceSq;
				bool fromPlayerHead = vector.DistanceSq(cursorHitPos, MiscGameplayFunctions.GetPlayerHeadPosition(player)) <= m_MaximalActionDistanceSq;
```

`CCTCursor.c:27-28` also uses `GetPlayerHeadPosition`. Stance height, not Head bone (`MiscGameplayFunctions.c:748-756`).

### 7.6 New inputs in `exp\bin\bin\constants.xml`

```xml
// [EXACT] exp\bin\bin\constants.xml:90
		<input name="UAToggleHeadlight" loc="TOGGLE_LIGHT_HEAD" />
		<input name="UAToggleVehicleLights" loc="TOGGLE_LIGHT_HEAD" />
```

Also `:282-285` `UABuldLinkCamToTerrain` / `UABuldCopyTileCoord` / `UABuldMarkUnderground` / `UABuldRemoveUnderground`; `:308-311` `UAUICodeLockLeft/Right/Up/Down`. `UACarHorn` remains `:203`. `[DESIGN]` Vehicle lights bind `UAToggleVehicleLights`, not `UAToggleHeadlight`.

### 7.7 Recipes

Until 1.29, `m_ResultReplacesIngredient` + `TransferItemProperties` could overwrite health from `m_ResultInheritsHealth`. Since 1.30 Exp 5th arg is `transfer_health = false`. Signature: `MiscGameplayFunctions.c:269`.

```c
// [EXACT] exp\scripts\scripts\4_World\Classes\Recipes\RecipeBase.c:353
						MiscGameplayFunctions.TransferItemProperties(ingr, res, true, true, false, false);
```

`GetRecipeClassName(int recipe_id)` is `PluginRecipesManager.c:84` (digest E said `:54`, which is the constructor).

---

## 8. Engine / proto API (`1_Core`, `3_Game`)

### 8.1 Third person

Digest O cited `World.c:49-50` (`GetMoonIntensity` / `GetSunOrMoon`). Real API:

```c
// [EXACT] exp\scripts\scripts\3_Game\Global\World.c:177
	proto native ThirdPersonMode GetThirdPersonViewMode();
```

```c
// [EXACT] exp\scripts\scripts\3_Game\Global\World.c:291
	[Obsolete("1.30: replaced by World::GetThirdPersonViewMode returning current thrid person mode")]
	proto native bool Is3rdPersonDisabled();
```

```c
// [EXACT] exp\scripts\scripts\3_Game\Global\World.c:301
enum ThirdPersonMode
{
	DISABLED,
	ENABLED,
	VEHICLES_ONLY
```

`[DESIGN]` Compare to `ThirdPersonMode.ENABLED` (or `VEHICLES_ONLY`). Vanilla typo `thrid` is in the `[Obsolete]` string.

### 8.2 Weather noise — not deleted

Digest O claimed `GetNoiseReductionByWeather` was removed. Both methods exist. No-Ex is `[Obsolete]` → Ex; Ex is `[Obsolete]` "Kept for HUD and old mods" because AI damping is native AIParams. Vanilla still calls Ex (`SensesAIEvaluate.c:23`, class `NoiseAIEvaluate`).

```c
// [EXACT] exp\scripts\scripts\3_Game\Weather.c:407
	[Obsolete("1.30: AI noise dampening is now done natively via AIParams config parameters. Kept for HUD and old mods.")]
	float GetNoiseReductionByWeatherEx(notnull Object object)
```

```c
// [EXACT] exp\scripts\scripts\3_Game\Weather.c:454
	[Obsolete("Use Weather.GetNoiseReductionByWeatherEx instead!")]
	float GetNoiseReductionByWeather()
```

### 8.3 `vector.Cross`, `array.Slice`, `EnumFlagsToString`

Digest O cited `EnConvert.c:29-36` (`int.MAX`/`MIN`) and `EnScript.c:33-40` (`ClassName` docs). Real bodies:

```c
// [EXACT] exp\scripts\scripts\1_Core\proto\EnConvert.c:239
	vector Cross(vector v)
	{
    	float x = value[1] * v[2] - value[2] * v[1];
    	float y = value[2] * v[0] - value[0] * v[2];
    	float z = value[0] * v[1] - value[1] * v[0];

    	return Vector(x, y, z);
	}
```

```c
// [EXACT] exp\scripts\scripts\1_Core\proto\EnScript.c:720
	array<T> Slice(int from, int to)
	{
	    array<T> result = new array<T>();
		for (int i = from; i <= to && i < Count(); ++i)
	        result.Insert(Get(i));

	    return result;
	}
```

`to` is inclusive. `typename.EnumFlagsToString` `EnConvert.c:614`; `Enum.EnumFlagsToString` `:704` forwards.

### 8.4 `DoOnce`, `IsFirstRenderFrame`, `DisableSimulation`

```c
// [EXACT] exp\scripts\scripts\3_Game\DoOnce.c:1
class DoOnce
{
    protected static ref map<string, bool> m_Done;
```

`DoOnce.Run(string key, Class target, string fnName, Param params = null)` (`:12`) calls `g_Game.GameScript.CallFunctionParams` once per key (`:21-27`).

```c
// [EXACT] exp\scripts\scripts\3_Game\dayzplayer.c:1186
	//! Returns true if this is the first tick of the render frame.
	//! If the client FPS is below 30fps, the player could tick multiple times in one render frame, some systems don't 
	//! need to be processed on the client again if it has no visible effect to the screen or server simulation.
	proto native bool IsFirstRenderFrame();
```

```c
// [EXACT] exp\scripts\scripts\3_Game\Entities\Entity.c:3
	proto native void DisableSimulation(bool disable);

	//! Returns whether simulation is disabled
	proto native bool GetIsSimulationDisabled();
```

---

## Qué se rompe para un mod 1.29

1. `override OnCEUpdate` — obsolete; CE work may never run → `OnCEIterate`.
2. `modded DayZPlayerInventory.ProcessInputData` — not called in retail → Validate / Execute*.
3. `TakeEntityToCargo*` / `TakeEntityAsAttachment*` — obsolete → Target*.
4. `ActionFillBottleBase` — obsolete and **absent** from `RegisterActions` → `ActionObtainLiquidBase`.
5. `ItemBase.m_ItemActionOverrides` — compile error → `EntityAI.OverrideActionAnimation`.
6. `World.Is3rdPersonDisabled()` — obsolete; `VEHICLES_ONLY` is not a bool.
7. Hardcoded `UA_AM_*` ints — `UA_AM_INIT=14` shifted later values.
8. Hand takes on surrendered players — `HandGuardIsNotSurrendered` rejects.
9. `GetNoiseReductionByWeather()` — still compiles (obsolete). AI damping is native; HUD uses `GetNoiseReductionByWeatherEx(object)`.
10. `GAME_STORAGE_VERSION` 142 → 144. Recipe replace no longer copies ingredient health. Drink/fill CCT is `CCTLiquid`, not `CCTWaterSurfaceEx`.

## Checklist de migración

- [ ] `OnCEIterate(currentTime, elapsedTime)` + `super`. Inventory: Validate + Execute* (not `ProcessInputData`).
- [ ] Target* takes. `AddAction(ActionObtainLiquidBase)`. `EntityAI.OverrideActionAnimation` (item and target).
- [ ] Info actions: `InitInfoData` + `CanBeStarted()==false`. `new CCTLiquid(mask, ...)`. `GetPlayerHeadPosition`.
- [ ] `GetThirdPersonViewMode() == ThirdPersonMode.ENABLED`. Weather HUD: `GetNoiseReductionByWeatherEx(object)`.
- [ ] `vector.Cross` / `array.Slice` / `EnumFlagsToString`. Client catch-up: `IsFirstRenderFrame()`. Storage `144`.
- [ ] Recipes with `m_ResultReplacesIngredient`: set `m_ResultInheritsHealth`. Bind `UAToggleVehicleLights` / `UAUICodeLock*`. Never hardcode `UA_AM_*`.
