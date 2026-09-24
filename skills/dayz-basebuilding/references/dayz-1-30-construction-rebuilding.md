# DayZ 1.30 Exp — Construction hierarchy, Rebuilding, masonry, Fence code lock

Authored 2026-09-16 (P08) from `exp\scripts\scripts\` (build 1.30.164014). Digest J is the map; every block below was copied from the file named in the `[EXACT]` header. Line numbers in the digest were frequently wrong.

## 1. Type hierarchy

`ConstructionBasic` in `3_Game` is a **stub** (`Construction_Basic.c:2-37`) — it does **not** contain `GetParent()` / `IsPartConstructed()` / `HasBase()`. Those live on `ConstructionBase` in `4_World`.

```c
// [EXACT] exp/scripts/scripts/4_World/Classes/ConstructionBase.c:30
class ConstructionBase : ConstructionBasic
```

```c
// [EXACT] exp/scripts/scripts/4_World/Classes/BaseBuilding/Construction.c:2
class Construction : ConstructionBase
```

```c
// [EXACT] exp/scripts/scripts/4_World/Classes/Rebuilding/Rebuilding.c:1
class Rebuilding : ConstructionBase
```

`EntityAI.CreateConstructionComponent()` returns null (`EntityAI.c:3451-3455`). `ConstructionInit()` (`:3441-3448`) only inits when the override returns a component.

```c
// [EXACT] exp/scripts/scripts/4_World/Entities/ItemBase/BaseBuildingBase.c:15
	protected ref ConstructionBasic 	m_Construction;
```

```c
// [EXACT] exp/scripts/scripts/4_World/Entities/ItemBase/BaseBuildingBase.c:872-886
	override protected ConstructionBasic CreateConstructionComponent()
	{
		m_Construction = new Construction(this);
		return m_Construction;
	}
	
	override ConstructionBasic GetConstructionBasic()
	{
		return m_Construction;
	}
	
	Construction GetConstruction()
	{
		return Construction.Cast(m_Construction);
	}
```

```c
// [EXACT] exp/scripts/scripts/4_World/Entities/Game/Super/Building.c:23-26
	override protected ConstructionBasic CreateConstructionComponent()
	{
		m_Construction = new Rebuilding(this);
		return m_Construction;
	}
```

[DESIGN] Mods that stored `Construction m_Construction` on a `BaseBuildingBase` subclass should switch to `GetConstruction()` (already a `Construction.Cast`) or `Construction.Cast(GetConstructionBasic())`. Direct field access from outside the class no longer compiles (`protected`).

## 2. `ConstructionPartTypeData` vs `ConstructionPart`

(until 1.29: each `ConstructionPart` stored config fields and `UpdateConstructionParts` re-read config on the instance). (since 1.30 Exp: type data is held on `EntityType` via `ConstructionDataTypeHolder`.)

`ConstructionDataTypeHolderBasic` in `3_Game` is also a stub (`ConstructionTypeData_Basic.c:2-5`). The real holder is `ConstructionDataTypeHolder` (`ConstructionPartTypedHolder.c:2`).

```c
// [EXACT] exp/scripts/scripts/4_World/Classes/BaseBuilding/ConstructionPart.c:2-16
//! Instanced construction part data classes for dynamic data, statics now stored on EntityType level in ConstructionPartTypeData
class ConstructionPart
{
	//TODO: start with 2 bits per part, and iterate into differentiated simple/complex part structure
	static const int BITWISE_SYNCINFO_SIZE_BASE = 2; //! no. of bits to store synced info, per part. System not ready for variable size parts yet.
	protected const int ANIMATION_EFFECT_DELAY_BUILD = 350; //ms
	
	protected ConstructionPartTypeData m_PartTypeData; //! Entity-type object storing non-instanced data
	protected int 	m_LocalSyncBitMask = 0;
	bool 	m_IsBuilt;			//defines part build state
	protected ref TConstructionPartInsiderBoxData m_InsiderBoxData; //Grouped modelspace positions of min/max insidebox points
	
	void ConstructionPart( string name, string part_name, string main_part_name, int id, bool is_built, bool is_base, bool is_gate, array<string> required_parts )
	{
	}
```

Digest J claimed a new ctor `ConstructionPart(notnull ConstructionPartTypeData)`. That ctor is **not** in the file. Type data is assigned after spawn:

```c
// [EXACT] exp/scripts/scripts/4_World/Classes/BaseBuilding/ConstructionPart.c:383-389
	void SetPartTypeData(ConstructionPartTypeData ptd)
	{
		if (!m_PartTypeData)
			m_PartTypeData = ptd;
		else
			ErrorEx("cannot override m_PartTypeData during runtime!");
	}
```

`UpdateConstructionParts` (`ConstructionBase.c:495-532`) reads `entityType.GetConstructionDataHolderBasic()`, spawns the part, then `part.SetPartTypeData(typeData)`. Config field readers (`name`, `id`, `is_base`, `is_gate`, `required_parts`, `build_action_type`, …) now live on `ConstructionPartTypeData.InitPartTypeData` (`ConstructionPartTyped.c:42-67,72-104`).

`SetRequestBuiltState` is `[Obsolete("1.30: Use 'SetBuiltState' directly")]` (`ConstructionPart.c:492-500`). The 1.29 SKILL triage row about SP skipping the local set still describes the obsolete body.

## 3. `*ServerEx` and collision

```c
// [EXACT] exp/scripts/scripts/4_World/Classes/ConstructionBase.c:1688-1702
	[Obsolete("call BuildPartServerEx instead")]
	void BuildPartServer(notnull Man player, string part_name, int action_id)
	{
		if (LogManager.IsBaseBuildingLogEnable()) bsbDebugPrint("[bsb] Construction BuildPartServer | " + part_name);
		
		BuildPartServerEx(player,part_name,action_id);
	}
	
	[Obsolete("call DismantlePartServerEx instead")]
	void DismantlePartServer(notnull Man player, string part_name, int action_id)
	{
		if (LogManager.IsBaseBuildingLogEnable()) bsbDebugPrint("[bsb] Construction DismantlePartServer | " + part_name);
		
		DismantlePartServerEx(player,part_name,action_id);
	}
```

```c
// [EXACT] exp/scripts/scripts/4_World/Classes/ConstructionBase.c:174-179
	void BuildPartServerEx(Man player, string part_name, int action_id)
	{
		if (LogManager.IsBaseBuildingLogEnable()) bsbDebugPrint("[bsb] Construction BuildPartServerEx | " + part_name);
		//on action
		TakeMaterialsServer(part_name);
	}
```

Note: `player` **can be null** (comment at `:172`). `Construction` then calls `m_Parent.OnPartBuiltServer` (`Construction.c:52-68`). Vanilla `ActionBuildPart` already calls Ex:

```c
// [EXACT] exp/scripts/scripts/4_World/Classes/UserActionsComponent/Actions/Continuous/ActionBuildPart.c:167-170
		if (!construction.IsCollidingEx(checkData) && canBuild)
		{
			//build
			construction.BuildPartServerEx(action_data.m_Player, partName, AT_BUILD_PART);
```

`IsCollidingEx` takes a `CollisionCheckData`, not a string:

```c
// [EXACT] exp/scripts/scripts/4_World/Classes/ConstructionBase.c:1471-1472
	bool IsCollidingEx(CollisionCheckData check_data)
	{
```

```c
// [EXACT] exp/scripts/scripts/4_World/Classes/ConstructionBase.c:1896-1910
class CollisionCheckData
{
	ref array<Object> m_AdditionalExcludes;
	string m_PartName;
	int m_PrimaryGeometry;
	int m_SecondaryGeometry;
	
	void CollisionCheckData()
	{
		m_AdditionalExcludes = new array<Object>();
		m_PartName = "";
		m_PrimaryGeometry = ObjIntersectGeom;
		m_SecondaryGeometry = ObjIntersectView;
	}
}
```

Collision-trigger helpers still exist, marked obsolete with **no replacement**:

```c
// [EXACT] exp/scripts/scripts/4_World/Classes/ConstructionBase.c:1742-1743
	[Obsolete("no replacement")]
	void CreateCollisionTrigger(string part_name, vector min_max[2], vector center)
```

```c
// [EXACT] exp/scripts/scripts/4_World/Classes/ConstructionBase.c:1770-1781
	[Obsolete("no replacement")]
	void DestroyCollisionTrigger()
	{
		if (!m_ConstructionBoxTrigger)
			return;
		
		g_Game.ObjectDelete(m_ConstructionBoxTrigger);
		m_ConstructionBoxTrigger = NULL;
	}
	
	[Obsolete("no replacement")]
	bool IsTriggerColliding()
```

`m_ConstructionBoxTrigger` is tagged `//! Deprecated` (`ConstructionBase.c:1789`).

## 4. Rebuilding persistence (map buildings only)

`BuildingBase` registers ten netsync ints on the component (`Building.c:29-45`). `Rebuilding` writes its own versioned blob — this is **not** `BaseBuildingBase.OnStoreSave`.

```c
// [EXACT] exp/scripts/scripts/4_World/Classes/Rebuilding/Rebuilding.c:1-16
class Rebuilding : ConstructionBase
{
	static int REBUILDING_STORAGE_VERSION = 1;
	
	protected int m_LastStorageVersion;
	
	protected int m_SyncParts1;
	protected int m_SyncParts2;
	protected int m_SyncParts3;
	protected int m_SyncParts4;
	protected int m_SyncParts5;
	protected int m_SyncParts6;
	protected int m_SyncParts7;
	protected int m_SyncParts8;
	protected int m_SyncParts9;
	protected int m_SyncParts10;
```

```c
// [EXACT] exp/scripts/scripts/4_World/Classes/Rebuilding/Rebuilding.c:502-515
	protected void SerializeConstructionData(ParamsWriteContext ctx)
	{
		ctx.Write(REBUILDING_STORAGE_VERSION);
		ctx.Write(m_SyncParts1);
		ctx.Write(m_SyncParts2);
		ctx.Write(m_SyncParts3);
		ctx.Write(m_SyncParts4);
		ctx.Write(m_SyncParts5);
		ctx.Write(m_SyncParts6);
		ctx.Write(m_SyncParts7);
		ctx.Write(m_SyncParts8);
		ctx.Write(m_SyncParts9);
		ctx.Write(m_SyncParts10);
	}
```

Packing math [DESIGN]:
- `BIT_INT_SIZE = 32` (`3_Game/tools/BitArray.c:4`)
- `GetSyncDataSize()` returns `BITWISE_SYNCINFO_SIZE_BASE = 2` (`ConstructionPart.c:6,65-68`)
- `adjustedID = (partId - 1) * GetSyncDataSize()`; `syncIntIdx = adjustedID / BIT_INT_SIZE` (`Rebuilding.c:147-149`)
- 10 ints × 32 bits / 2 bits/part = 160 part ids (1..160)

Default `CalculateBitMaskOnBuild` sets only bit 0 at `offset` (`ConstructionPart.c:111-117`). `ConstructionPartRebuild` also ORs facing into bit 1 (`:985-991`). Digest J's 00=ruin / 01=built / 10=destroyed mapping was not in those methods — [UNVERIFIED] as a three-state ruin encoding.

`BaseBuildingBase.OnStoreSave` is unchanged (still 1 bit per part, ids 1..93):

```c
// [EXACT] exp/scripts/scripts/4_World/Entities/ItemBase/BaseBuildingBase.c:420-430
	override void OnStoreSave( ParamsWriteContext ctx )
	{   
		super.OnStoreSave( ctx );
		
		//sync parts 01
		ctx.Write( m_SyncParts01 );
		ctx.Write( m_SyncParts02 );
		ctx.Write( m_SyncParts03 );
		
		ctx.Write( m_HasBase );
	}
```

Support graph: `ConstructionPartStaticsSupportData` parses `StaticsSupportData { SupportProviders / SupportRequirements }` (`ConstructionStatics.c:1-26`). `ConstructionBase.SupportRemovalCheck` defaults to true (`:771-775`); Rebuilding overrides it. [DESIGN] Do not treat `required_parts[]` as the only structural gate on rebuildable houses.

## 5. Masonry items and `TOOL_BRICKLAYING`

```c
// [EXACT] exp/scripts/scripts/4_World/Classes/BaseBuilding/ConstructionConstants.c:13-26
//has to mirror tool defines in configs!
enum EConstructionTools
{
	TOOL_NO_ACTION = 0,
	TOOL_MOUNT_WIRE = 1,
	TOOL_NAIL = 2,
	TOOL_DIG_BASE = 4,
	TOOL_MOUNT_LOG = 8,
	TOOL_HEAVY = 16,
	TOOL_EXCAVATION = 32,
	TOOL_WOODWORK = 64,
	TOOL_HANDS = 128,
	TOOL_BRICKLAYING = 256
}
```

```c
// [EXACT] exp/scripts/scripts/4_World/Entities/ItemBase/BrickTrowel.c:1-8
class BrickTrowel extends ToolBase
{
	override void SetActions()
	{
		super.SetActions();
		
		AddAction(ActionBuildPart);
		AddAction(ActionRepairPart);
```

```c
// [EXACT] exp/scripts/scripts/4_World/Classes/UserActionsComponent/Actions/Continuous/ActionPickUpBricks.c:16-18
class ActionPickUpBricks: ActionContinuousBase
{	
	static const int YIELD = 3;
```

```c
// [EXACT] exp/scripts/scripts/4_World/Entities/ItemBase/MortarMix.c:1-8
class MortarMix extends ItemBase
{	
	override void SetActions()
	{
		super.SetActions();
        AddAction(ActionMixMortarAtWater);
		AddAction(ActionMixMortarAtWell);
	}
```

`ActionMixMortarAtWater` uses `CCTLiquid` (`ActionMixMortarAtWater.c:23,47-50`). `MortarMix_Opened` only adds `ActionAttachToConstruction` (`MortarMix_Opened.c:1-8`). `CommonBrick` adds attach-to-construction (`CommonBrick.c:1-8`). Rebuildable house scripts live under `4_World/Entities/Building/Rebuildable/` (e.g. `House_1M1.c:1`).

`ConstructionMaterialType` moved to `ConstructionBase.c:2-12` and adds brick/rubble:

```c
// [EXACT] exp/scripts/scripts/4_World/Classes/ConstructionBase.c:2-12
enum ConstructionMaterialType
{
	MATERIAL_NONE	= 0,
	MATERIAL_LOG	= 1,
	MATERIAL_WOOD	= 2,
	MATERIAL_STAIRS	= 3,
	MATERIAL_METAL	= 4,
	MATERIAL_WIRE	= 5,
	MATERIAL_BRICK 	= 6,
	MATERIAL_RUBBLE = 7
}
```

`[UNVERIFIED]` `CfgVehicles` `build_action_type` for `BrickTrowel` — the class name appears in scripts and in character sound config, but no `class BrickTrowel` CfgVehicles block was in the extracted `exp\*\config.cpp` set.

## 6. Fence `DigitalCodeLock` and combo-lock unlock

```c
// [EXACT] exp/scripts/scripts/4_World/Entities/ItemBase/BaseBuildingBase/Fence.c:18-26
	typename ATTACHMENT_WOODEN_LOG			= WoodenLog;
	typename ATTACHMENT_COMBINATION_LOCK	= CombinationLock;
	typename ATTACHMENT_CODE_LOCK			= DigitalCodeLock;
	
	const string ATTACHMENT_SLOT_CAMONET			= "Wall_Camonet";
	const string ATTACHMENT_SLOT_BARBEDWIRE_DOWN	= "Wall_Barbedwire_1";
	const string ATTACHMENT_SLOT_BARBEDWIRE_UP		= "Wall_Barbedwire_2";
	const string ATTACHMENT_SLOT_COMBINATION_LOCK 	= "Att_CombinationLock";
	const string ATTACHMENT_SLOT_CODE_LOCK 			= "Att_CodeLock";
```

```c
// [EXACT] exp/scripts/scripts/4_World/Entities/ItemBase/BaseBuildingBase/Fence.c:161-165
	DigitalCodeLock GetCodeLock()
	{
		DigitalCodeLock codeLock = DigitalCodeLock.Cast(FindAttachmentBySlotName(ATTACHMENT_SLOT_CODE_LOCK));
		return codeLock;
	}
```

`DigitalCodeLock` owns a `CodeLockComponent` (`CodeLock.c:1,9,30`). PIN length 4..6 (`CodeLockComponent.c:23-24`). Persist order on the component: `m_LockPIN`, `m_IsLocked`, `m_DoorIndex` (`CodeLockComponent.c:257-262`). Building-door lock slots (`Att_CombinationLock` / `Att_CodeLock` on `BuildingBase` `:10-11`) are owned by `dayz-doors`; Fence is the base-building attachment point.

Combo lock: `AddAction(ActionCombinationLockUnlock)` (`CombinationLock.c:686`). Stream v143 adds `m_CombinationInside`:

```c
// [EXACT] exp/scripts/scripts/4_World/Entities/ItemBase/CombinationLock.c:128-136
	override void OnStoreSave( ParamsWriteContext ctx )
	{   
		super.OnStoreSave(ctx);
		
		//write data
		ctx.Write( m_Combination );
		ctx.Write( m_CombinationLocked );
		ctx.Write( m_CombinationInside );
	}
```

Fence gate save itself is still after `super` (`fence.c:246-254` in 1.30; the 1.29 skill cited `:212-220`).

## 7. `ConstructionActionData` slot helpers

Not removed. Marked obsolete:

```c
// [EXACT] exp/scripts/scripts/4_World/Classes/BaseBuilding/ConstructionActionData.c:617-627
	[Obsolete("1.30: Unsafe, overridden ActionData used in-system instead")]
	void SetSlotId( int slot_id )
	{
		m_SlotId = slot_id;
	}
	
	[Obsolete("1.30: Unsafe, overridden ActionData used in-system instead")]
	int GetSlotId()
	{
		return m_SlotId;
	}
```

## 8. `disableSimulation` (changelog only for houses)

```c
// [EXACT] exp/scripts/scripts/3_Game/Entities/Entity.c:3-6
	proto native void DisableSimulation(bool disable);

	//! Returns whether simulation is disabled
	proto native bool GetIsSimulationDisabled();
```

`[CHANGELOG]` `disableSimulation` config parameter on house-based entities (`work/changelog-1.30-exp-modding.md:13`). Not observed on `BaseBuildingBase`.

## 9. Activation, new per-part keys and rebuildable buildings (added 2026-09-24)

Re-opened on 2026-09-24 against the 1.30.164014 Exp `scripts.pbo`. Nothing in this section has been exercised in-game.

### 9.1 What turns construction on

```c
// [EXACT][CLAIM-BB-CONSTRUCTION-ACTIVATION-130] exp/scripts/scripts/3_Game/Entities/EntityAI.c:248-249
		if (g_Game.ConfigIsExisting("cfgVehicles" + " " + GetType() + " " + "Construction"))
			ConstructionInit();
```

Any `CfgVehicles` class with a `Construction` subclass gets its component when the entity is constructed. The concrete type comes from `CreateConstructionComponent()`: `new Rebuilding(this)` on `BuildingBase` (`4_World/Entities/Game/Super/Building.c:23-26`) and `new Construction(this)` on `BaseBuildingBase` (`basebuildingbase.c:871-875`). Inference from those two overrides, not measured: a modded building that inherits a `BuildingBase` descendant needs no script override to become rebuildable, only the config block and the model selections.

### 9.2 Per-part keys that 1.30 reads

[EXACT][CLAIM-BB-REBUILD-PART-KEYS-130] Readers are in `exp/scripts/scripts/4_World/Classes/BaseBuilding/TypeConstructionData/ConstructionPartTyped.c` unless another file is named. The paths are relative to `Construction <main_part> <part>`.

| Key | Reader | What the code shows |
|---|---|---|
| `custom_part_type` | `ConstructionPartTypedHolder.c:34` | script class for the part's type data (e.g. the `ConstructionPartRebuild*Typed` classes) |
| `can_part_decay`, `part_decay_threshold`, `part_decay_rate` | `:199`, `:205`, `:212` | per-part decay. Global switch `disableBaseDecay` (`3_Game/CfgGameplayDataJson.c:60`, `CfgGameplayHandler.c:172`, used by `ConstructionBasic.CanConstructionDecay`, `3_Game/Systems/Construction_Basic.c:31-34`) |
| `insider_minMaxs` | `:159` | inner box, next to `collision_data` (`:148`) |
| `item_falling_data` | `:188` | read; its effect was not traced |
| `essential_attachments` | `:228` | read; its effect was not traced |
| `related_GUI_categories` | `:239` | ties the part to inventory GUI categories |
| `damage_hands_on_build` | `:250` | read; its effect was not traced |
| `is_utility`, `utility_build` | `:259`, `:265` | read; their effect was not traced |
| `EffectsData` > `soundEffectPositions`, `particleEffectPositions` | `4_World/Classes/Rebuilding/ConstructionEffects.c:19,26-28,37` | memory points for build effects |
| `StaticsSupportData` > `SupportProviders` / `SupportRequirements` > `<child>` > `supportCategory` (string, hashed), `supportStrength` (int) | `4_World/Classes/Rebuilding/ConstructionStatics.c:13,26,37-38,45,56-57` | structural support: what a part provides and needs, by category |
| `Materials` > `<material>` > `skipOnRepair`, `skipOnDismantle` | `4_World/Classes/BaseBuilding/ConstructionMaterials.c:31-32` | material not needed to repair / not refunded on dismantle (next to `type`, `slot_name`, `quantity`, `lockable`, `:26-30`) |

### 9.3 Locks on rebuilt doors

`BuildingBase` declares the slots `Att_CombinationLock` and `Att_CodeLock` (`Building.c:10-11`). A door cannot hold both (`HasConflictingDoorAttachment`, `:224-228`, `:344`), and `CanDoorBeOpened` is overridden (`:307`). The per-door slot wiring was not traced further here.

### 9.4 What 1.30 Exp ships and what it does not

- **Script classes.** The Nasdara houses (`4_World/Entities/Building/Rebuildable/House_*.c`) and `Land_IrrigationTunnel_Entrance_01 : BuildingSuper` (`IrrigationTunnel_Entrance.c:1-11`, whose debug spawn puts a `WoodenStick` and a `Rope` in its inventory).
- **No configs or models.** On 2026-09-24, no unencrypted PBO config of the Exp install defined `Land_House_2M1`, `Land_IrrigationTunnel_Entrance_01`, `wall1_wood` or `rubble_rubble1`. `nasdara\addons\data_nasdara.pbo` carries only the DLC `CfgMods` entry and a `mud_brick` surface.
- **Example part names.** `Land_House_2M1_Dam2.OnDebugSpawn` builds `rubble_rubble1`, `rubble_rubble2`, `wall1_wood`, `wall2_wood`, `wall3_brick` and `roof1` with `BuildPartServerEx(null, <part>, -1)` (`House_2M1.c:13-20`).
- **`RebuildingSpawner` is diag-only** (`4_World/Classes/BaseBuilding/RebuildingSpawner.c:1`, `#ifdef DIAG_DEVELOPER`).

### 9.5 Object Spawner flag

- **The flag.** `ECE_OBJECT_SPAWNER = 256` (`3_Game/CE/CentralEconomy.c:15`) is now set by the Object Spawner (`3_Game/ObjectSpawner.c:44,48`).
- **New parameter.** `CreateObject` and `CreateStaticObjectUsingP3D` gained `bool objSpawner = false` (`3_Game/Global/Game.c:680,691`).
- **Unknowns.** Script does not say what the engine does with the flag. Whether a rebuildable building placed by the Object Spawner keeps its parts across a restart is unmeasured.

Terrain holes, underground triggers and the underground placement block are in `dayz-underground`.
