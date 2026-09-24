# Verified worked examples

## Contents

- [How to use these examples](#how-to-use-these-examples)
- [Simple Door](#simple-door-door-plus-handle)
- [Door with Button](#door-with-button-static-controller)
- [Expert Mode](#expert-mode-door-plus-handle-plus-lever)
- [Cross-pattern diff](#cross-pattern-diff)
- [Source discrepancies](#source-discrepancies)
- [Building locks (DayZ 1.30 Exp)](#building-locks-dayz-130-exp)

## How to use these examples

Each block is **[EXACT]** content from the supplied .cfg/config.cpp, with line endings normalized for Markdown. Originals are copied byte-for-byte under **assets/**.

Treat each pair side by side: model.cfg defines bones, selections, and sources; config.cpp binds Doors components, timing, sounds, and damage.

## Simple Door: door plus handle

### Side-by-side mapping

| Real model.cfg | Real config.cpp |
|---|---|
| **door1 -> ""**, **handle -> door1**. | One Doors entry **Door1**. |
| Door and handle source **door1**. | **component = "door1"**. |
| Handle **0..0.15**; door **0.15..1**. | **animPeriod = 1.3**; init values **0.0**. |

The handle follows the door transform. It reaches angle1 **-1.4** by phase **0.15**; then the door begins its rotation to **1.9**.

### [EXACT] model.cfg - assets/Door/Simple_Door.cfg

<!-- BEGIN VERBATIM: assets/Door/Simple_Door.cfg -->
~~~cpp
class cfgSkeletons
{
	class Simple_DoorSkeleton
	{
		skeletonInherit = "";
		isDiscrete = 0;
		SkeletonBones[]=
		{
			
			"door1","",
			"handle","door1",
		};
	};
};
class CfgModels
{
	class Default
	{
		sections[] = {};
		sectionsInherit="";
		skeletonName = "";
	};
	class Simple_Door:Default
	{
		skeletonName="Simple_DoorSkeleton";
		sections[]={};
		class Animations
		{
			class Door1
			{
				type = "rotation";
				selection = "door1";
				source = "door1";
				axis = "door1_axis";
				memory = 1; 
				minValue = 0.15; 
				maxValue = 1; 
				angle0 = 0; 
				angle1 = 1.9;
			};
			class handle
			{
				type = "rotation";
				selection = "handle";
				source = "door1";
				axis = "handle_axis";
				memory = 1; 
				minValue = 0; 
				maxValue = 0.15; 
				angle0 = 0; 
				angle1 = -1.4; 
			};
		};
	};
};
~~~
<!-- END VERBATIM: assets/Door/Simple_Door.cfg -->

### [EXACT] config.cpp - assets/Door/config.cpp

<!-- BEGIN VERBATIM: assets/Door/config.cpp -->
~~~cpp
class CfgPatches
{
	class Doors_Buttons_Lesson_Simple_Door
	{
		requiredAddons[] = {"DZ_Data"};
	};
};

class CfgVehicles
{
	class HouseNoDestruct;
	class land_Simple_Door: HouseNoDestruct
	{
		scope = 1;
		model = "Doors_Buttons_Lesson\Door\Simple_Door.p3d";
		class Doors
		{
			class Door1
			{
				displayName = "Door 1";
				component = "door1";
				soundPos = "door1_action";
				animPeriod = 1.3;
				initPhase = 0.0;
				initOpened = 0.0;
				soundOpen = "doorMetalSmallOpen";
				soundClose = "doorMetalSmallClose";
				soundLocked = "doorMetalSmallRattle";
				soundOpenABit = "doorMetalSmallOpenABit";
			};
		};
		class DamageSystem
		{
			class GlobalHealth
			{
				class Health
				{
					hitpoints = 1000;
				};
			};
			class GlobalArmor
			{
				class Projectile
				{
					class Health { damage = 0; };
					class Blood { damage = 0; };
					class Shock { damage = 0; };
				};
				class Melee
				{
					class Health { damage = 0; };
					class Blood { damage = 0; };
					class Shock { damage = 0; };
				};
			};
			class DamageZones
			{
				class Door1
				{
					class Health
					{
						hitpoints = 1000;
						transferToGlobalCoef = 0;
					};
					componentNames[] = {"door1"};
					fatalInjuryCoef = -1;
					class ArmorType
					{
						class Projectile
						{
							class Health { damage = 2; };
							class Blood { damage = 0; };
							class Shock { damage = 0; };
						};
						class Melee
						{
							class Health { damage = 2.5; };
							class Blood { damage = 0; };
							class Shock { damage = 0; };
						};
					};
				};
			};
		};
	};
};
~~~
<!-- END VERBATIM: assets/Door/config.cpp -->

## Door with Button: static controller

### Side-by-side mapping

| Real model.cfg | Real config.cpp |
|---|---|
| Only bone **door1 -> ""**; no button bone. | One Doors entry **Door1_Open**. |
| Moving **door1**; source **door1_open**. | **component = "door1_open"**. |
| Door phase **0..1**. | **soundPos = "door1_action"**, period **1.0**. |

The button is static. The tutorial places View Geometry selection and interaction point at the button as **door1_open**; interacting there drives moving selection **door1**.

### [EXACT] model.cfg - assets/Door_w_Button/Door_w_Button.cfg

<!-- BEGIN VERBATIM: assets/Door_w_Button/Door_w_Button.cfg -->
~~~cpp
class cfgSkeletons
{
	class Door_w_ButtonSkeleton
	{
		skeletonInherit = "";
		isDiscrete = 0;
		SkeletonBones[]=
		{
			"door1"	,""
		};
	};
};
class CfgModels
{
	class Default
	{
		Sections[] ={};
		sectionsInherit="";
		skeletonName = "";
	};
	class Door_w_Button:Default
	{
		skeletonName="Door_w_ButtonSkeleton";
		sections[]={};
		class Animations
		{
			class Door1
			{
				type = "rotation";
				selection = "door1";
				source = "door1_open";
				axis = "door1_axis";
				memory = 1; 
				minValue = 0.0; 
				maxValue = 1; 
				angle0 = 0; 
				angle1 = 1.9;
			};
		};
	};
};
~~~
<!-- END VERBATIM: assets/Door_w_Button/Door_w_Button.cfg -->

### [EXACT] config.cpp - assets/Door_w_Button/config.cpp

<!-- BEGIN VERBATIM: assets/Door_w_Button/config.cpp -->
~~~cpp
class CfgPatches
{
	class Doors_Buttons_Lesson_Door_w_Button
	{
		requiredAddons[] = {"DZ_Data"};
	};
};

class CfgVehicles
{
	class HouseNoDestruct;
	class land_Door_w_Button: HouseNoDestruct
	{
		scope = 1;
		model = "Doors_Buttons_Lesson\Door_w_Button\Door_w_Button.p3d";
		class Doors
		{
			class Door1_Open
			{
				displayName = "Door 1";
				component = "door1_open";
				soundPos = "door1_action";
				animPeriod = 1.0;
				initPhase = 0.0;
				initOpened = 0.0;
				soundOpen = "doorMetalSmallOpen";
				soundClose = "doorMetalSmallClose";
				soundLocked = "doorMetalSmallRattle";
				soundOpenABit = "doorMetalSmallOpenABit";
			};
		};
		class DamageSystem
		{
			class GlobalHealth
			{
				class Health
				{
					hitpoints = 1000;
				};
			};
			class GlobalArmor
			{
				class Projectile
				{
					class Health { damage = 0; };
					class Blood { damage = 0; };
					class Shock { damage = 0; };
				};
				class Melee
				{
					class Health { damage = 0; };
					class Blood { damage = 0; };
					class Shock { damage = 0; };
				};
			};
			class DamageZones
			{
				class Door1
				{
					class Health
					{
						hitpoints = 1000;
						transferToGlobalCoef = 0;
					};
					componentNames[] = {"door1"};
					fatalInjuryCoef = -1;
					class ArmorType
					{
						class Projectile
						{
							class Health { damage = 2; };
							class Blood { damage = 0; };
							class Shock { damage = 0; };
						};
						class Melee
						{
							class Health { damage = 2.5; };
							class Blood { damage = 0; };
							class Shock { damage = 0; };
						};
					};
				};
			};
		};
	};
};
~~~
<!-- END VERBATIM: assets/Door_w_Button/config.cpp -->

## Expert Mode: door plus handle plus lever

### Side-by-side mapping

| Real model.cfg | Real config.cpp |
|---|---|
| door root, handle child, lever root. | Main **Door1_Open**, secondary **Lever**. |
| All source **door1_open**. | Both component **door1_open**. |
| Door starts **0.10**; lever ends **0.5**. | Main **initOpened = 0.5**; Lever period **0.50**. |

The handle follows the moving door. The lever is an independent root at the controller. All three animations share one source.

? The real config has two Doors entries for one source/component, contradicting a universal one-entry-per-source rule. The secondary Lever also omits **soundPos** and all sounds. Preserve it; ask before reusing that duplicate mapping.

### [EXACT] model.cfg - assets/Expert_Mode/Expert_Mode.cfg

<!-- BEGIN VERBATIM: assets/Expert_Mode/Expert_Mode.cfg -->
~~~cpp
class cfgSkeletons
{
	class Expert_ModeSkeleton
	{
		skeletonInherit = "";
		isDiscrete = 0;
		SkeletonBones[]=
		{
			"door1"	,"",
			"handle","door1",
			"lever",""
		};
	};
};
class CfgModels
{
	class Default
	{
		Sections[] ={};
		sectionsInherit="";
		skeletonName = "";
	};
	class Expert_Mode:Default
	{
		skeletonName="Expert_ModeSkeleton";
		sections[]={};
		class Animations
		{
			class Door1
			{
				type = "rotation";
				selection = "door1";
				source = "door1_open";
				axis = "door1_axis";
				memory = 1; 
				minValue = 0.10; 
				maxValue = 1; 
				angle0 = 0; 
				angle1 = 1.9;
			};
			class Handle
			{
				type = "rotation";
				selection = "handle";
				source = "door1_open";
				axis = "handle_axis";
				memory = 1; 
				minValue = 0.0; 
				maxValue = 1.0; 
				angle0 = 0; 
				angle1 = -1.7;
			};
			class Lever
			{
				type = "rotation";
				selection = "lever";
				source = "door1_open";
				axis = "lever_axis";
				memory = 1; 
				minValue = 0.0; 
				maxValue = 0.5; 
				angle0 = 0; 
				angle1 = -0.88;
			};
		};
	};
};
~~~
<!-- END VERBATIM: assets/Expert_Mode/Expert_Mode.cfg -->

### [EXACT] config.cpp - assets/Expert_Mode/config.cpp

<!-- BEGIN VERBATIM: assets/Expert_Mode/config.cpp -->
~~~cpp
class CfgPatches
{
	class Doors_Buttons_Lesson_Expert_Mode
	{
		requiredAddons[] = {"DZ_Data"};
	};
};

class CfgVehicles
{
	class HouseNoDestruct;
	class land_Expert_Mode: HouseNoDestruct
	{
		scope = 1;
		model = "Doors_Buttons_Lesson\Expert_Mode\Expert_Mode.p3d";
		class Doors
		{
			class Door1_Open
			{
				displayName = "Door 1";
				component = "door1_open";
				soundPos = "door1_action";
				animPeriod = 1.0;
				initPhase = 0.0;
				initOpened = 0.5;
				soundOpen = "doorMetalSmallOpen";
				soundClose = "doorMetalSmallClose";
				soundLocked = "doorMetalSmallRattle";
				soundOpenABit = "doorMetalSmallOpenABit";
			};
			class Lever
			{
				displayName = "Lever";
				component = "door1_open";
				animPeriod = 0.50;
				initPhase = 0.0;
				initOpened = 0.0;
			};
		};
		class DamageSystem
		{
			class GlobalHealth
			{
				class Health
				{
					hitpoints = 1000;
				};
			};
			class GlobalArmor
			{
				class Projectile
				{
					class Health { damage = 0; };
					class Blood { damage = 0; };
					class Shock { damage = 0; };
				};
				class Melee
				{
					class Health { damage = 0; };
					class Blood { damage = 0; };
					class Shock { damage = 0; };
				};
			};
			class DamageZones
			{
				class Door1
				{
					class Health
					{
						hitpoints = 1000;
						transferToGlobalCoef = 0;
					};
					componentNames[] = {"door1"};
					fatalInjuryCoef = -1;
					class ArmorType
					{
						class Projectile
						{
							class Health { damage = 2; };
							class Blood { damage = 0; };
							class Shock { damage = 0; };
						};
						class Melee
						{
							class Health { damage = 2.5; };
							class Blood { damage = 0; };
							class Shock { damage = 0; };
						};
					};
				};
			};
		};
	};
};
~~~
<!-- END VERBATIM: assets/Expert_Mode/config.cpp -->

## Cross-pattern diff

| Concern | Simple Door | Door with Button | Expert Mode |
|---|---|---|---|
| Moving bones | Door + handle | Door only | Door + handle + lever |
| Parent graph | Handle follows door | Door root | Handle follows door; lever root |
| Interactive source | **door1** | **door1_open** at button | **door1_open** at lever |
| Static controller bone | N/A | Button omitted | N/A; lever animates |
| Phase sequencing | Handle 0..0.15; door 0.15..1 | Door 0..1 | Door 0.10..1; handle 0..1; lever 0..0.5 |
| Doors components | **door1** | **door1_open** | **door1_open** twice |
| DamageZone component | **door1** | **door1** | **door1** |

No pattern introduces **AnimationSources** or script calls; those belong to **dayz-animation-pipeline**.

## Source discrepancies

- Real files above are authoritative for packaged examples.
- Expert prose at **Welcome to novoGODs Expert_Mode Door mod.txt:128-137** shows **switchOpen/switchClose**.
- Real **assets/Expert_Mode/config.cpp:31-38** has neither sound.
- ? No in-game test established the exact purpose/behavior of the duplicate Expert Lever Doors entry.

## Building locks (DayZ 1.30 Exp)

The three tutorial buildings above have no lock slots. (until 1.29: a world-building door locked only through engine `LockDoor` / `UnlockDoor` and lockpick.) (since 1.30 Exp: `House` is `BuildingBase`, which accepts `CombinationLock` and `DigitalCodeLock` as attachments and binds them per door through `AdditionalDoorInfo`.)

Player-built fence (gate) already lists both slots at **entity** level — not inside **class Doors** — in extracted camping config:

```cpp
// [EXACT] exp/gear_camping/DZ/gear/camping/config.cpp:2683
		attachments[] = {"Wall_Barbedwire_1","Wall_Barbedwire_2","Wall_Camonet","Att_CombinationLock","Att_CodeLock","Material_Nails","Material_WoodenPlanks","Material_MetalSheets","Material_WoodenLogs","Material_MetalWire"};
```

`BuildingBase` slot name constants:

```c
// [EXACT] exp/scripts/scripts/4_World/Entities/Game/Super/Building.c:8
class BuildingBase : Building
{
	const string ATTACHMENT_SLOT_COMBINATION_LOCK = "Att_CombinationLock";
	const string ATTACHMENT_SLOT_CODE_LOCK 	= "Att_CodeLock";
```

`CfgSlots` selections the P3D Memory/proxy must match:

```cpp
// [EXACT] exp/scripts/scripts/config.cpp:2325
	class Slot_Att_CombinationLock
	{
		name = "Att_CombinationLock";
		displayName = "#STR_CombinationLock0";
		selection = "att_combinationlock";
		ghostIcon = "set:dayz_inventory image:combolock";
	};
```

```cpp
// [EXACT] exp/scripts/scripts/config.cpp:2777
	class Slot_Att_CodeLock
	{
		name = "Att_CodeLock";
		displayName = "#STR_CodeLock0";
		selection = "att_codelock";
		ghostIcon = "set:dayz_inventory image:digitallock";
	};
```

### `AdditionalDoorInfo` on each `class Doors` child

Parsed once per building type in `Building.InitializeDoorInfos` (`exp/scripts/scripts/3_Game/Entities/Building.c:302-309`). Config keys (not the C++ member names):

```c
// [EXACT] exp/scripts/scripts/3_Game/Entities/AdditionalDoorsInfo.c:1
//! Single door info
class AdditionalDoorInfo
{
	protected string m_DoorPath;
	
	string m_DoorType;
	string m_InteractLimitingPositionPoint; //! memory point name for limiting open/close actions on the door/window
	string m_InteractLimitingDirPoint; //! memory point name for limiting open/close actions on the door/window
	string m_DoorConstructionPartName; //! Name of the construction part linked to the doors, if any (empty default)
	string m_DoorConstructionPhysicsSource; //! Name of the AnimationSource controlling door physics (required for rebuildable doors, empty default)
	int m_LockCompatibilityBitMask; //! Lock compatibility type, now in door config. Lockpick enabled by default if undefined.
	ref TStringArray m_RelatedInventorySlotNames; //! Inventory slots that have something to do with this door. Mostly external locks?
```

```c
// [EXACT] exp/scripts/scripts/3_Game/Entities/AdditionalDoorsInfo.c:21
	void Init()
	{
		if (g_Game.ConfigIsExisting(m_DoorPath + " relatedInventorySlots"))
		{
			m_RelatedInventorySlotNames = new TStringArray();
			g_Game.ConfigGetTextArray(m_DoorPath + " relatedInventorySlots", m_RelatedInventorySlotNames);
		}
		
		if (g_Game.ConfigIsExisting(m_DoorPath + " lockCompatibilityBitMask"))
			m_LockCompatibilityBitMask = g_Game.ConfigGetInt(m_DoorPath + " lockCompatibilityBitMask");
		else
			m_LockCompatibilityBitMask = 1 << EBuildingLockType.LOCKPICK; //default behavior if not configured
		
		if (g_Game.ConfigIsExisting(m_DoorPath + " interactPositionPoint"))
			m_InteractLimitingPositionPoint = g_Game.ConfigGetTextOut(m_DoorPath + " interactPositionPoint");
		
		if (g_Game.ConfigIsExisting(m_DoorPath + " interactDirPoint"))
			m_InteractLimitingDirPoint = g_Game.ConfigGetTextOut(m_DoorPath + " interactDirPoint");
		
		if (g_Game.ConfigIsExisting(m_DoorPath + " doorConstructionPart"))
			m_DoorConstructionPartName = g_Game.ConfigGetTextOut(m_DoorPath + " doorConstructionPart");
		
		if (g_Game.ConfigIsExisting(m_DoorPath + " doorConstructionPhysicsSource"))
			m_DoorConstructionPhysicsSource = g_Game.ConfigGetTextOut(m_DoorPath + " doorConstructionPhysicsSource");
	}
```

**[DESIGN]** A lockable custom house door therefore needs, in addition to the tutorial **class Doors** block:

1. Entity `attachments[]` containing `Att_CombinationLock` and/or `Att_CodeLock` (and numbered wood/metal variants if you copy rebuildable-house slot naming).
2. On that door's Doors subclass: `relatedInventorySlots[] = {"Att_CombinationLock","Att_CodeLock"};` so Open, lockpick, and attach-to-construction know which slots belong to which door.
3. Optional `lockCompatibilityBitMask` if lockpick / ship-container keys should differ from the default.
4. Memory selections `att_combinationlock` / `att_codelock`.
5. Optional `interactPositionPoint` / `interactDirPoint` for one-sided operation.

**[UNVERIFIED]** No extracted vanilla `config.cpp` **class Doors** child in this dump actually contains `relatedInventorySlots[]`. The parser and `BuildingBase` / `ActionAttachToConstruction` consumers are verified; a shipped Chernarus house block with those keys is not in the text extract.

### Attaching a lock to a building door

`ActionAttachToConstruction` (building branch) resolves the slot from `relatedInventorySlots[]` only when the door is closed and not engine-locked:

```c
// [EXACT] exp/scripts/scripts/4_World/Classes/UserActionsComponent/Actions/SingleUse/ActionAttachToConstruction.c:151
		else if (Class.CastTo(building, targetEntity) && building.CanUseConstruction())	// Building entities
		{
			if (item.IsExternalLockType()) // External lock handling of building objects with doors and lock attachments and internal locks
			{
				int doorIndex = building.GetDoorIndex(target.GetComponentIndex());
				if (doorIndex > -1 && !building.IsDoorLocked(doorIndex) && !building.IsDoorOpen(doorIndex))
				{
					AdditionalDoorInfo doorInfo = building.GetDoorInfo(doorIndex);
					if (!doorInfo || !doorInfo.m_RelatedInventorySlotNames)
						return InventorySlots.INVALID;
					
					foreach (string slotName: doorInfo.m_RelatedInventorySlotNames)
					{
						EntityAI slotEntity = building.FindAttachmentBySlotName(slotName);
						if (slotEntity)
							continue;
						
						slotId = InventorySlots.GetSlotIdFromString(slotName);
						GameInventory inventory = building.GetInventory();
						if (inventory && inventory.CanAddAttachmentEx(item, slotId))
							break;
```

`BuildingBase.CanReceiveAttachment` refuses a second lock on the twin slot (`HasConflictingDoorAttachment` swaps `Att_CodeLock` ↔ `Att_CombinationLock` suffixes) and refuses any external lock while that door is open (`Building.c:192-249`). `CanReleaseAttachment` refuses while `DigitalCodeLock.IsLocked()` or `CombinationLock.IsLocked()` (`Building.c:267-280`).

### Combination lock: two faces and explicit unlock

(until 1.29: matching the last dial unlocked/detached the lock.) (since 1.30 Exp: matching dials is not enough; `ActionCombinationLockUnlock` must run. Inside and outside combinations are separate.)

```c
// [EXACT] exp/scripts/scripts/4_World/Entities/ItemBase/CombinationLock.c:25
class CombinationLock extends ItemBase
{
	static const string LOCK_SELECTION_OUTSIDE = "lock_attached_outside";
	static const string LOCK_SELECTION_INSIDE = "lock_attached_inside";
	static const int FACING_OUTSIDE = 0;
	static const int FACING_INSIDE = 1;
```

```c
// [EXACT] exp/scripts/scripts/4_World/Classes/UserActionsComponent/Actions/SingleUse/ActionCombinationLockUnlock.c:1
class ActionCombinationLockUnlock: ActionInteractBase
{
	void ActionCombinationLockUnlock()
	{
		m_CommandUID 	= DayZPlayerConstants.CMD_ACTIONMOD_OPENDOORFW;
		m_Text = "#detach_combination_lock";
	}
```

Vanilla stream v143 adds `m_CombinationInside`:

```c
// [EXACT] exp/scripts/scripts/4_World/Entities/ItemBase/CombinationLock.c:128
override void OnStoreSave( ParamsWriteContext ctx )
{   
	super.OnStoreSave(ctx);
	
	//write data
	ctx.Write( m_Combination );
	ctx.Write( m_CombinationLocked );
	ctx.Write( m_CombinationInside );
}
```

```c
// [EXACT] exp/scripts/scripts/4_World/Entities/ItemBase/CombinationLock.c:169
		if (version >= 143)						//added with 143
		{
			//combination two (inside lock)
			if (!ctx.Read(m_CombinationInside))
			{
				m_CombinationInside = 0;
				return false;
			}
		}
```

### Digital code lock

Script item class is `DigitalCodeLock` (`CodeLock.c:1`), not a `CfgVehicles` class found in this extract (**[UNVERIFIED]** config classname). It owns `CodeLockComponent` and `CodeLockVisualManager`. Battery slot `BatteryD`. PIN 4–6 digits (`CodeLockComponent.c:23-24`). UI: `DigitalCodeLockUI.GetLayout()` returns `"gui/layouts/day_z_digital_lock.layout"` (`DigitalCodeLockUI.c:127-129`; layout listed in `work/pbo-listings/exp__dta__gui.txt`). Memory on the **item**: `ce_center`, `inside` (`CodeLock.c:3-4`).

```c
// [EXACT] exp/scripts/scripts/4_World/Classes/CodeLockComponent.c:4
enum CodeLockStage
{
	NONE,
	NORMAL,
	SETTING,
	PROTECTION_STAGE_ONE,
	PROTECTION_STAGE_TWO
}
```

Brute-force thresholds: `CfgGameplayHandler.GetExternalLockProtectionCountStageOne`, `GetExternalLockProtectionCountStageTwo`, `GetExternalLockProtectionTime`, `GetExternalLockProtectionResetTime` (`CfgGameplayHandler.c:498-515`, `CodeLockComponent.c:66-67,468-479`). There is **no** `GetExternalLockProtectionTimeStageOne` in this dump.

Component persist order: `m_LockPIN` (string), `m_IsLocked` (bool), `m_DoorIndex` (int) (`CodeLockComponent.c:257-262`).

### Bunker door (broadcast)

`Bunker` overrides `CanDoorBeOpened(DoorManipulationParams)`: inside + inactive uses `MemPointDirectionalCheck` on `{m_DoorType}_action` / `{m_DoorType}_inside`; outside requires `m_IsActive` and an unlocked `DigitalCodeLock_Bunker`. Main door auto-closes at 12 s and re-locks on close start.

```c
// [EXACT] exp/scripts/scripts/4_World/Entities/Building/Bunker.c:47
	override bool CanDoorBeOpened(notnull DoorManipulationParams params)
	{
		if (IsMainDoor(params.m_DoorIndex))
		{
			AdditionalDoorInfo doorInfo = GetDoorInfo(params.m_DoorIndex);
			string memPointStartName = string.Format("%1_action", doorInfo.m_DoorType);
			string memPointEndName = string.Format("%1_inside", doorInfo.m_DoorType);
			
			bool insideAndInactive = MiscGameplayFunctions.MemPointDirectionalCheck(PlayerBase.Cast(params.m_Caller), this, memPointStartName, memPointEndName) && super.CanDoorBeOpened(params);
			bool outside = m_IsActive && !GetCodeLock().IsLocked() && super.CanDoorBeOpened(params);

			return insideAndInactive || outside;
		}
		
		return super.CanDoorBeOpened(params);
	}
```

`BroadcastedBunker` binds `DigitalCodeLock_Bunker` on slot string `"att_codelock"` (`Bunker.c:174,192-204`).

### Rebuildable house doors

`Rebuilding.OnConstructionDoorOpenStart` / `OnConstructionDoorCloseStart` set `doorConstructionPhysicsSource` phase 1.0 / 0.0 (`Rebuilding.c:440-464`). Put `doorConstructionPart` and `doorConstructionPhysicsSource` on the Doors child if the door is a rebuildable construction part.

### Script override trap

Vanilla Open no longer calls `CanDoorBeOpened(int, bool)`. Override `CanDoorBeOpened(notnull DoorManipulationParams params)`. `Land_WarheadStorage_Main.CanDoorBeOpened(int doorIndex, bool checkIfLocked = false)` (`Land_WarheadStorage_Main.c:352`) is the old signature still present in 1.30 — do not treat it as the current Open path.
