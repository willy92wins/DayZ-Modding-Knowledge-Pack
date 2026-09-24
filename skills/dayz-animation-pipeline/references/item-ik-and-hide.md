# Item carry-IK and hide-on-attach (Layer 1)

Two production-proven patterns, both Layer 1 (Claude produces in-sandbox), both sourced from working mods in this vault (`AI/10_Projects/DayZ_Vehicle_Skill/patterns/` — specifically `vanilla-ik-anim-reuse.md` and `slot-attached-item-hide-animation.md`). They reuse the vanilla animation system instead of authoring new clips — zero animator work, accepted visual debt.

## Pattern A — carry IK by reusing vanilla `.anm`

When the player picks up a large item (wheel, door, barrel), DayZ needs an IK animation describing how to hold it across poses. Authoring custom `.anm` is animator work; instead point the item at a similar vanilla `.anm`.

```c
modded class ModItemRegisterCallbacks
{
    override void RegisterHeavy(DayZPlayerType pType, DayzPlayerItemBehaviorCfg pBehavior)
    {
        super.RegisterHeavy(pType, pBehavior);
        pType.AddItemInHandsProfileIK(
            "my_Wheel",                                                       // my item class
            "dz/anims/workspaces/player/player_main/player_main_heavy.asi",   // workspace
            pBehavior,
            "dz/anims/anm/player/ik/vehicles/hatchback_02/Hatchback_02_Wheel.anm" // vanilla anm
        );
    }
};
```

Vanilla `.anm` catalog (observed in kt_roadkill — [TBD-verify] against `P:\dz\anims\anm\player\ik\vehicles\` before relying):

| item type | anm path |
|---|---|
| wheel (medium) | `dz/anims/anm/player/ik/vehicles/hatchback_02/Hatchback_02_Wheel.anm` |
| wheel (large/truck) | `dz/anims/anm/player/ik/vehicles/sedan_02/Sedan_02_Wheel.anm` |
| door | `.../hatchback_02/Hatchback_02_Door_PassengerL.anm` (L/R, Driver/Passenger variants) |
| hood / trunk | `.../hatchback_02/Hatchback_02_Hood.anm` / `..._Trunk.anm` |

Gotchas: the workspace (`player_main_heavy.asi`) is fixed per item weight class — pick the vanilla item closest to yours. IK can clip through the player if your item's proportions differ a lot from the vanilla reference — Layer 3 in-game test required. Using `PassengerL` for both door sides looks mirrored/odd; accepted compromise.

When to use: early-stage mod, no animator, item proportions close to a vanilla equivalent. When not: strong visual identity, or a wildly different shape (a 1.5 m tractor wheel on Hatchback IK looks wrong).

## Pattern B — hide-on-attach (animation source of type `hide`)

An item that lives in the `.p3d` (geometry + texture already there) appears/disappears based on whether it is attached to its slot. Visibility is a `hide` animation driven by a `user` source, toggled in the attach/detach lifecycle events.

`config.cpp`:
```cpp
class AnimationSources
{
    class hide_barrel1 { source="user"; animPeriod=0.1; initPhase=1; }; // start HIDDEN
};
```

`model.cfg` `class Animations`:
```cpp
class hide_barrel1 { type="hide"; source="hide_barrel1"; selection="barrel_1"; minValue=0; maxValue=1; hideValue=0.5; }; // hideValue: [TBD-verify], see note
```

> **`hideValue` is [TBD-verify], not a settled constant.** The `0.5` above is the working default observed in kt_roadkill, but the exact threshold and the comparison direction (selection hidden when phase ≥ or ≤ `hideValue`) are not in the PMC wiki type table. Whenever you emit a `hideValue` in output, label it `[TBD-verify]` and tell the user to confirm it against a vanilla `hide` config on `P:\` before shipping — do not present the number as verified just to make the block look complete. This is anchor 2 applied to the one key most easily copied as if it were fact.

script `4_World/MyVehicle.c`:
```c
override void EEItemAttached(EntityAI item, string slot_name)
{
    super.EEItemAttached(item, slot_name);
    if (slot_name == "my_barrel1") SetAnimationPhase("hide_barrel1", 0); // phase 0 = VISIBLE
}
override void EEItemDetached(EntityAI item, string slot_name)
{
    super.EEItemDetached(item, slot_name);
    if (slot_name == "my_barrel1") SetAnimationPhase("hide_barrel1", 1); // phase 1 = HIDDEN
}
```

Key points: `initPhase=1` starts hidden (object spawns without the attachment); `_attached` sets phase 0 (visible), `_detached` sets phase 1 (hidden). DayZ fires `EEItemAttached` during `CreateInInventory`, so OnDebugSpawn-created items update automatically. The attached item is still a real inventory item — the hide only affects its representation on the host.
When to use: vehicles/objects with visible exterior cargo (jerry cans, barrels, spare wheels), modular elements where you do not want N `.p3d` variants. When not: if the item affects the collision (Geometry LOD) — then you need real `.p3d` variants, not a hide.

## Pattern C -- model swap by attach-state (two selections, item-side)

A cousin of Pattern B. Instead of hiding one selection, the item carries TWO full
selections -- a detailed `not_attached` model and a lighter `attached` model -- and swaps
which one renders when the item is attached to its slot (performance: show the cheap model
while attached/proxied). Driven from the ITEM's attach hooks, not the parent's.

Difference vs Pattern B:
- Pattern B: one selection, hidden/shown via a `hide` animation, toggled on the PARENT
  (`EEItemAttached`/`EEItemDetached`).
- Pattern C: two selections (two models), toggled on the ITEM
  (`OnWasAttached`/`OnWasDetached`) with `Show/HideSelection`.

`model.cfg` (own skeleton, both selections as bones; mirrors the vanilla flag's
folded/opened selections):
```cpp
class CfgSkeletons { class MyItemSkeleton { skeletonInherit=""; isDiscrete=0;
    SkeletonBones[]={ "attached","", "not_attached","" }; }; };
// class Animations: a hide-type anim per selection, source-driven; initPhase sets default.
```
`config.cpp`: an `AnimationSources` entry drives the swap; `hiddenSelections` still lists
only the texture selections.

script (item side) -- APIs verified vs vanilla (see `enforce-script-reference` ->
`verified-api-catalog.md`; entityai.c:3356/3365, inventoryitem.c OnWasAttached):
```c
void MyItem()  // constructor: default to the ground model
{
    ShowSelection("not_attached");
    HideSelection("attached");
}
override void OnWasAttached(EntityAI parent, int slot_id)
{
    super.OnWasAttached(parent, slot_id);
    HideSelection("not_attached");
    ShowSelection("attached");
}
override void OnWasDetached(EntityAI parent, int slot_id)
{
    super.OnWasDetached(parent, slot_id);
    ShowSelection("not_attached");
    HideSelection("attached");
}
```
Source: community technique (YouTube "How to change the model of a proxy attachment",
RXIFoFo5stY, 2026); author credits the vanilla flag (folded/opened) as the reference. The
script APIs are verified; the exact `AnimationSource`/`initPhase` wiring is `[verify]`
against the vanilla flag config before shipping. Selections must exist in Resolution + View
Geometry (and Geometry if the attached model needs collision).

## Pattern D — Dynamic Animation Instance Switching (DayZ 1.30 Exp) [EXACT]

In DayZ 1.30 Exp, Bohemia introduced native Enforce Script methods to dynamically switch the player character's animation instance (`.asi`) at runtime without needing to swap physical items in hands.

### Native `Human.SetAnimationInstanceByName`
```c
// [EXACT] exp\scripts\scripts\3_Game\human.c:1383-1384
	//! sets the animation instance of the player character - careful when using, could create desync if not used properly
	proto native	void		SetAnimationInstanceByName(string animationInstanceName, float blendingTime);
```

### Decoupling Hand Item Changes from Animation Instances
`HumanItemAccessor` allows mods to decouple item-in-hands changes from automatic animation instance transitions:
```c
// [EXACT] exp\scripts\scripts\3_Game\humanitems.c:111-118
	//! signalization from script to engine that item in hands changed
	proto native void	OnItemInHandsChanged(bool pInstant = false, bool pChangeAnimationInstance = true);
	
	//! enable whether the animation instance should change when switching the item in hand
	proto native void	EnableAutoAnimInstUpdateOnHandsChange(bool pNewValue);
	
	//! get whether the animation instance should change when switching the item in hand
	proto native bool	IsAutoAnimInstUpdateOnHandsChangeEnabled();
```

### Resetting to Unarmed Hands via "Empty" Profile
To return the player character cleanly to the default unarmed state, DayZ 1.30 Exp registers an `"Empty"` hands profile in `DayZPlayerCfgBase.c`:
```c
// [EXACT] exp\scripts\scripts\4_World\Entities\ManBase\DayZPlayer\DayZPlayerCfgBase.c:1535-1538
	//! Empty profile to be able to switch back to this using SetAnimationInstanceByName
	{
		pType.AddItemInHandsProfileIK("Empty", "dz/anims/workspaces/player/player_main/player_main.asi", emptyHanded, "");
	}
```
Invoking `SetAnimationInstanceByName("Empty", 0.2)` restores the base `player_main.asi` animation instance.

### Native Surrender System (No Dummy Item)
In 1.29 and earlier, the surrender emote (`HandsUp`) required spawning an invisible `SurrenderDummyItem` in hands. In 1.30 Exp, this hack is eradicated; `PlayerBase` uses `SetAnimationInstanceByName` directly:
```c
// [EXACT] exp\scripts\scripts\4_World\Entities\ManBase\PlayerBase.c:2081-2090
	protected void OnStartTransitionToSurrender()
	{		
		m_StartedSurrenderTransition = true;
		HumanInputController hic = GetInputController();
		hic.DisableProneCameraHorizontalRotation(true);
		g_Game.GetMission().AddActiveInputRestriction(EInputRestrictors.SURRENDER_TRANSITION);
		GetItemAccessor().EnableAutoAnimInstUpdateOnHandsChange(false);
		SetAnimationInstanceByName("dz/anims/workspaces/player/player_main/player_main_surrender.asi", 1);	
		m_SurrenderTransitionTimer = m_SurrenderAnimationTransitionTime;
	}
```
State is controlled via `player.SetSurrenderState(bool)` (`PlayerBase.c:2116`) and queried via `player.IsSurrendered()` (`Man.c:66`), completely eliminating dummy item desyncs.
