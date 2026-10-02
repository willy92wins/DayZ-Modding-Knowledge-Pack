# Worked examples

## Contents

- [Where these examples come from](#where-these-examples-come-from)
- [Simple Door](#simple-door-door-plus-handle)
- [Door with Button](#door-with-button-static-controller)
- [Expert Mode](#expert-mode-door-plus-handle-plus-lever)
- [Cross-pattern diff](#cross-pattern-diff)
- [Source discrepancies](#source-discrepancies)
- [Building locks (DayZ 1.30 Exp)](#building-locks-dayz-130-exp)

## Where these examples come from

The three doors on this page are the examples of novoGOD's door tutorial *Doors_Buttons_Lesson*: three models, each with its model.cfg and config.cpp, and four tutorial texts, files dated 2025-04-23. The tutorial's archive holds no license or permission text, so the Pack does not ship its files. This page describes each example in its own words and tables, and cites the tutorial's files by path and line, such as `Doors_Buttons_Lesson/Door/Simple_Door.cfg:29-40`. Pack v1.3.0 to v1.5.0 shipped those files under `assets/`, wrongly labelled as the Pack author's MIT work; they were removed on 2026-10-02.

Read each example as a pair. model.cfg declares the bones, the selections that move and the source that drives them; config.cpp binds that source to a **class Doors** entry and sets its timing, sounds and damage. The three share their scaffolding (a CfgPatches entry requiring **"DZ_Data"**, an empty **Default** model class, **skeletonInherit = ""**, **isDiscrete = 0**, **scope = 1** on a **HouseNoDestruct** child) and one DamageSystem, the same lines in all three files; [door-model-cfg-and-config.md](door-model-cfg-and-config.md) describes those once, with line citations. The tables below keep to what each pattern adds.

## Simple Door: door plus handle

A door that swings on its hinge, and a handle that turns first and then rides along with the door. One source, **door1**, drives both.

### Side-by-side mapping

| Tutorial model.cfg | Tutorial config.cpp |
|---|---|
| **door1 -> ""**, **handle -> door1**. | One Doors entry **Door1**. |
| Door and handle source **door1**. | **component = "door1"**. |
| Handle **0..0.15**; door **0.15..1**. | **animPeriod = 1.3**; init values **0.0**. |

The handle follows the door transform. It reaches angle1 **-1.4** by phase **0.15**; then the door begins its rotation to **1.9**.

### Bones (`Doors_Buttons_Lesson/Door/Simple_Door.cfg:1-14`)

| Bone | Parent | Effect |
|---|---|---|
| **door1** | none (**""**) | Turns about its own axis. |
| **handle** | **door1** | Carried by the door's rotation, on top of its own turn. |

The skeleton class is **Simple_DoorSkeleton**; the model class **Simple_Door**, named after the P3D, points at it through **skeletonName** (`:23-25`).

### Animations (`Doors_Buttons_Lesson/Door/Simple_Door.cfg:27-53`)

| Class | selection | source | axis | Phase window | Turn, radians |
|---|---|---|---|---|---|
| **Door1** | **door1** | **door1** | **door1_axis** | 0.15 to 1 | 0 to 1.9 |
| **handle** | **handle** | **door1** | **handle_axis** | 0 to 0.15 | 0 to -1.4 |

Both are rotations about a Memory LOD axis (**type = "rotation"**, **memory = 1**). The windows do not overlap: the handle turns during the first 15 % of the action, and the door swings during the rest.

### Doors entry (`Doors_Buttons_Lesson/Door/config.cpp:16-31`)

| Doors class | component | soundPos | animPeriod | initPhase | initOpened | Sounds |
|---|---|---|---|---|---|---|
| **Door1** | **door1** | **door1_action** | 1.3 s | 0.0 | 0.0 | **doorMetalSmall** Open, Close, Rattle (locked), OpenABit |

The entity class is **land_Simple_Door** (`:12`); its **model** points at the addon's `Door\Simple_Door.p3d` (`:15`).

## Door with Button: static controller

A door opened from a button next to it. The button never moves, so it is not a bone: it only carries the interaction selection **door1_open**, and that name is the source of the door's rotation.

### Side-by-side mapping

| Tutorial model.cfg | Tutorial config.cpp |
|---|---|
| Only bone **door1 -> ""**; no button bone. | One Doors entry **Door1_Open**. |
| Moving **door1**; source **door1_open**. | **component = "door1_open"**. |
| Door phase **0..1**. | **soundPos = "door1_action"**, period **1.0**. |

The button is static. The tutorial places View Geometry selection and interaction point at the button as **door1_open**; interacting there drives moving selection **door1**.

### Bones (`Doors_Buttons_Lesson/Door_w_Button/Door_w_Button.cfg:1-12`)

| Bone | Parent | Effect |
|---|---|---|
| **door1** | none (**""**) | The only bone; the button is not listed. |

### Animations (`Doors_Buttons_Lesson/Door_w_Button/Door_w_Button.cfg:25-39`)

| Class | selection | source | axis | Phase window | Turn, radians |
|---|---|---|---|---|---|
| **Door1** | **door1** | **door1_open** | **door1_axis** | 0 to 1 | 0 to 1.9 |

The selection that moves (**door1**) and the source that drives it (**door1_open**) have different names; that split is the whole pattern.

### Doors entry (`Doors_Buttons_Lesson/Door_w_Button/config.cpp:16-31`)

| Doors class | component | soundPos | animPeriod | initPhase | initOpened | Sounds |
|---|---|---|---|---|---|---|
| **Door1_Open** | **door1_open** | **door1_action** | 1.0 s | 0.0 | 0.0 | the same four **doorMetalSmall** sounds |

The DamageZone still names the moving part, **componentNames[] = {"door1"}** (`:65`), not the button's **door1_open**.

## Expert Mode: door plus handle plus lever

A door with a handle, opened from a separate lever. All three parts move from one source, **door1_open**, which the lever carries as its interaction selection.

### Side-by-side mapping

| Tutorial model.cfg | Tutorial config.cpp |
|---|---|
| door root, handle child, lever root. | Main **Door1_Open**, secondary **Lever**. |
| All source **door1_open**. | Both component **door1_open**. |
| Door starts **0.10**; lever ends **0.5**. | Main **initOpened = 0.5**; Lever period **0.50**. |

The handle follows the moving door. The lever is an independent root at the controller. All three animations share one source.

? The tutorial's config has two Doors entries for one source/component, contradicting a universal one-entry-per-source rule. The secondary Lever also omits **soundPos** and all sounds. Ask before reusing that duplicate mapping.

### Bones (`Doors_Buttons_Lesson/Expert_Mode/Expert_Mode.cfg:1-14`)

| Bone | Parent | Effect |
|---|---|---|
| **door1** | none (**""**) | Turns about its own axis. |
| **handle** | **door1** | Carried by the door's rotation, on top of its own turn. |
| **lever** | none (**""**) | Turns about its own axis, independent of the door. |

### Animations (`Doors_Buttons_Lesson/Expert_Mode/Expert_Mode.cfg:27-65`)

| Class | selection | source | axis | Phase window | Turn, radians |
|---|---|---|---|---|---|
| **Door1** | **door1** | **door1_open** | **door1_axis** | 0.10 to 1 | 0 to 1.9 |
| **Handle** | **handle** | **door1_open** | **handle_axis** | 0 to 1 | 0 to -1.7 |
| **Lever** | **lever** | **door1_open** | **lever_axis** | 0 to 0.5 | 0 to -0.88 |

Here the windows overlap: the lever finishes its throw by mid-action, the handle turns over the whole action, and the door starts at 10 %.

### Doors entries (`Doors_Buttons_Lesson/Expert_Mode/config.cpp:16-39`)

| Doors class | component | soundPos | animPeriod | initPhase | initOpened | Sounds |
|---|---|---|---|---|---|---|
| **Door1_Open** | **door1_open** | **door1_action** | 1.0 s | 0.0 | 0.5 | the four **doorMetalSmall** sounds |
| **Lever** | **door1_open** | none | 0.50 s | 0.0 | 0.0 | none |

With **initOpened = 0.5** the main door spawns open about half the time (the **initOpened** note in [door-model-cfg-and-config.md](door-model-cfg-and-config.md)). Its DamageZone names **door1** (`:73`).

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

- Where the tutorial's texts and its files disagree, the files are authoritative.
- Expert prose at **Welcome to novoGODs Expert_Mode Door mod.txt:128-137** shows **switchOpen/switchClose**.
- The tutorial's **Doors_Buttons_Lesson/Expert_Mode/config.cpp:31-38** has neither sound.
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
