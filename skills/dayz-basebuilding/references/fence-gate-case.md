# Fence gate — the worked example

Authored 2026-07-07 (F4) from vanilla P:\scripts — see citations.

`Fence: BaseBuildingBase` (`fence.c`, 904 ln) is the richest concrete entity: it adds a gate state machine,
an open/close animation, a combo lock, barbed-wire area damage, and a persisted gate field. Use it as the
template when adding any stateful sub-behaviour on top of the base part system. Roots: `P:\scripts\` =
`<dayz-projects>\scripts\`.

## 1. Gate state

The gate has its own state field `m_GateState` plus `m_IsOpened`, separate from the part bitmask. A part
declares itself a gate with `is_gate=1` in the `Construction{}` block (read in
`UpdateConstructionParts` `construction.c:256-264`). The gate's open/close animation and combo lock are
driven off `m_IsOpened` / the combolock, and the barbed-wire area damage is rotated with the gate.

The open/close actions are `interact\actionopenfence.c` and `interact\actionclosefence.c`. Opening/closing
plays the gate animation and toggles `m_IsOpened`.

## 2. Barbed-wire area damage

`CreateAreaDamage` (`basebuildingbase.c:1086-1131`) builds an `AreaDamageLoopedDeferred_NoVehicle` from the
`<slot>_min` / `<slot>_max` memory points, ammo `"BarbedWireHit"`, hitting Torso / hands / legs / feet.
Fence rotates that area damage with the gate (`fence.c:558-566`) so the damage volume follows the gate leaf
as it swings.

Barbed wire is a `mountables[]` attachment (proxy physics toggled — see `config-contract.md §2`); its damage
zone also unmounts the wire when destroyed.

## 3. Gate persistence and the version bump

The gate state is persisted AFTER the base three sync ints, following the strict `OnStoreSave`/`OnStoreLoad`
ordering invariant (this is the canonical example of the subclass-after-super rule in `persistence-audit.md`):

- `Fence.OnStoreSave` (`fence.c:212-220`): calls `super.OnStoreSave` FIRST (which writes `m_SyncParts01/02/03`
  then `m_HasBase`), THEN writes `m_GateState`, `m_IsOpened`.
- `Fence.OnStoreLoad` (`fence.c:222-255`): calls `super.OnStoreLoad` FIRST, then handles a legacy branch — for
  `version < 110` it reads and DISCARDS a bool, then reads the gate state + opened for current versions.

**Version note:** Fence gate persistence was bumped at **v110**. The base damage-system version is
`GetDamageSystemVersionChange()→111` (`basebuildingbase.c:1238-1241`). When you add a persisted field to a
subclass, you bump the version and add a legacy branch exactly like this — read the old layout for old saves,
the new layout for new ones, so existing bases don't corrupt on the first load after the update. Getting this
wrong loses every fence on the server → treat as data-critical (R9, `persistence-audit.md`).

## 4. Repair

`Fence.CanBeRepairedToPristine()→true` (`fence.c:421-424`). Repair scales the material requirement by
`REPAIR_MATERIAL_PERCENTAGE=0.15` (`construction.c:13, 640-644`), floor min 1. The repair action itself is the
generic `ActionRepairPart` / kit path (not in `fence.c`).

## 5. What to copy when authoring your own stateful entity

1. Add the state field(s) and register them for netsync in the ctor, alongside the base `m_SyncParts*`.
2. Persist them in `OnStoreSave`/`OnStoreLoad` AFTER `super`, in the exact same order both ways.
3. Bump the version and add a legacy read branch for old saves.
4. If the behaviour has a physical volume (area damage, a moving leaf), rotate/relocate it in the same
   handler that mutates the state (`fence.c:558-566` pattern).
5. Gate the whole thing behind server authority — the state mutation runs server-side and syncs to clients.

## 6. DayZ 1.30 Exp — `DigitalCodeLock` and combo-lock unlock

(until 1.29: Fence lock attachment was `CombinationLock` on `Att_CombinationLock` only; finishing the
dial unlocked/detached the lock). (since 1.30 Exp: Fence also declares `DigitalCodeLock` on `Att_CodeLock`.)

```c
// [EXACT] exp/scripts/scripts/4_World/Entities/ItemBase/BaseBuildingBase/Fence.c:19-26
	typename ATTACHMENT_COMBINATION_LOCK	= CombinationLock;
	typename ATTACHMENT_CODE_LOCK			= DigitalCodeLock;
	
	const string ATTACHMENT_SLOT_CAMONET			= "Wall_Camonet";
	const string ATTACHMENT_SLOT_BARBEDWIRE_DOWN	= "Wall_Barbedwire_1";
	const string ATTACHMENT_SLOT_BARBEDWIRE_UP		= "Wall_Barbedwire_2";
	const string ATTACHMENT_SLOT_COMBINATION_LOCK 	= "Att_CombinationLock";
	const string ATTACHMENT_SLOT_CODE_LOCK 			= "Att_CodeLock";
```

`GetCodeLock()` finds the slot (`fence.c:161-165`). `GetCombinationLock()` is unchanged (`:155-159`). Gate
open checks in 1.30 also reject a mounted code lock (`fence.c:208,440`).

`CombinationLock.SetActions` now includes `ActionCombinationLockUnlock` (`CombinationLock.c:686`). Dialing
the right combination is not enough. Persist: `OnStoreSave` writes `m_Combination`, `m_CombinationLocked`,
then `m_CombinationInside`; `OnStoreLoad` reads the third int only when `version >= 143`
(`CombinationLock.c:128-136,169-177`). Fence gate fields themselves still follow the v110 branch
(`fence.c:246-279` in 1.30; the 1.29 citations `:212-255` above are the same methods, shifted).

Building-door lock slots on `BuildingBase` (`Building.c:10-11`) are documented for `dayz-doors`. This
file only covers the Fence attachment.

`Fence.OnStoreSave` in 1.30:

```c
// [EXACT] exp/scripts/scripts/4_World/Entities/ItemBase/BaseBuildingBase/Fence.c:246-254
	override void OnStoreSave( ParamsWriteContext ctx )
	{   
		super.OnStoreSave( ctx );
		
		//write
		ctx.Write( m_GateState );
		ctx.Write( m_IsOpened );
		if (LogManager.IsBaseBuildingLogEnable()) bsbDebugPrint("[bsb] OnStoreSave - build=" + m_GateState + " opened=" + m_IsOpened);
	}
```
