---
name: dayz-doors
description: "Use when working on a DayZ door, animated door, class Doors, doors on buildings, a door with button, a door with lever, hatch/lid animation, model.cfg door, CfgSkeletons door, code lock, combination lock, DoorManipulationParams, CanDoorBeOpened, or diagnosing 'door won't open/animate' on buildings and static props."
---

# DayZ Doors

## Scope

Use this skill for the **class Doors** subsystem on DayZ buildings and static props: doors, hatches, lids, and the buttons or levers that drive them.

Do not use it as a general animation guide. For **AnimationSources**, **SetAnimationPhase**, character or creature animation graphs, vehicle-rider IK, weapons, RTM, ANM, or TXA work, use the **dayz-animation-pipeline** skill.

## Core contract

A door action crosses five name domains:

1. Visible and physical named selections in the P3D LODs.
2. Bones in **CfgSkeletons**.
3. Rotation classes in **CfgModels > class Animations**.
4. Each animation's **source**, normally the View Geometry interaction selection.
5. A **CfgVehicles > HouseNoDestruct child > class Doors** entry whose **component** matches that source.

The moving **selection** and interactive **source** may differ. This is the key to a door controlled by an adjacent button or lever.

Read [door-model-cfg-and-config.md](references/door-model-cfg-and-config.md) before editing model.cfg or config.cpp. Read [lods-and-object-builder.md](references/lods-and-object-builder.md) before editing the P3D. Read [worked-examples.md](references/worked-examples.md) when choosing a pattern. Exact source folders are in **assets/**.

(until 1.29: a building door's lock state was the engine native pair `LockDoor` / `UnlockDoor`, operated with a lockpick through `ActionLockDoors` / `ActionUnlockDoors` and `CanDoorBeOpened(int doorIndex, bool checkIfLocked = false)`.) (since 1.30 Exp: that native path still exists, but `BuildingBase` also accepts inventory locks on slots `Att_CombinationLock` and `Att_CodeLock`, bound per door by `AdditionalDoorInfo`. Vanilla `ActionOpenDoors` now calls `CanDoorBeOpened(notnull DoorManipulationParams params)` and `DoorsDirectionalCheck`. See [Door open conditions and locks](references/door-model-cfg-and-config.md#door-open-conditions-and-locks-dayz-130-exp) and [Building locks](references/worked-examples.md#building-locks-dayz-130-exp).)

## Workflow

1. **Model the object.** Decide what moves, what follows another bone, where the action appears, and where the sound originates.
2. **Build the LOD contract.** Name visible parts in Resolution LOD; add only space-occupying parts to Geometry; add interaction and occlusion shapes to View Geometry; add penetration-material components to Fire Geometry; add axes, action/sound, and interaction points to Memory.
3. **Write model.cfg.** Give the model a unique skeleton, list (child,parent) pairs, then add one rotation class per animated selection. Reuse a source when several parts move from one action.
4. **Write config.cpp.** Inherit from **HouseNoDestruct**, set **scope** and **model**, map the model source through **class Doors**, then define **DamageSystem**.
5. **Validate names.** Compare exact spelling and case across every LOD, skeleton bone, animation **selection**, **source**, **axis**, Doors **component**, **soundPos**, and DamageZone **componentNames**.
6. **Test in game.** Verify action location, closed/open motion, child motion, sub-ranges, collision, occlusion, penetration, sounds, world-spawn state, and server/client RPT logs.

Follow the debug order: config load -> entity spawn -> action location -> animation -> collision/occlusion -> audio/damage. Do not debug a later layer before the earlier layer is proven.

## Pick a worked pattern

| Need | Pattern | Defining mapping |
|---|---|---|
| Door plus moving handle | Simple Door | Door and handle share source **door1**; handle is a child of **door1** and finishes at phase **0.15**. |
| Door controlled by a static button | Door with Button | Only **door1** is a bone; animation source and Doors component are **door1_open** at the button. |
| Door plus moving handle and lever | Expert Mode | Door, handle, and lever share **door1_open**; handle follows door, lever follows nothing. |
| Building door that accepts a combination lock or code lock (since 1.30 Exp) | Building lock attachments | Keep the **class Doors** mapping above; add per-door `relatedInventorySlots[]` / `lockCompatibilityBitMask` plus entity slots `Att_CombinationLock` / `Att_CodeLock`. |

## New door from scratch checklist

- [ ] P3D basename, CfgModels class, model path, and vehicle class are chosen.
- [ ] Skeleton name is unique to this P3D.
- [ ] Every animated selection is a skeleton bone.
- [ ] Every (child,parent) pair matches the intended transform hierarchy.
- [ ] Resolution LOD names every visible component.
- [ ] Geometry/View/Fire shapes are closed and convex.
- [ ] View Geometry contains the intended interaction selection/source.
- [ ] Memory contains each rotation axis, the sound/action point, and the interaction point.
- [ ] Every animation has verified type, selection, source, axis, memory, phase range, and angles.
- [ ] **CfgPatches.requiredAddons[]** includes **"DZ_Data"**.
- [ ] The object inherits from **HouseNoDestruct**.
- [ ] **class Doors** maps each intended source through **component**.
- [ ] (since 1.30 Exp, if the door should take a padlock or code lock) entity `attachments[]` include `Att_CombinationLock` and/or `Att_CodeLock`; the matching **class Doors** entry sets `relatedInventorySlots[]`; Memory has slot selections `att_combinationlock` / `att_codelock` and any `interactPositionPoint` / `interactDirPoint` pair.
- [ ] (since 1.30 Exp) any script override of door-open conditions targets `CanDoorBeOpened(notnull DoorManipulationParams params)`, not only the `int` wrapper.
- [ ] Door sound names are verified in **DZ\sounds\hpp\config.cpp**.
- [ ] **DamageSystem** has GlobalHealth, GlobalArmor, and appropriate DamageZones.
- [ ] In-game tests cover action position, motion, sounds, physical LODs, damage, spawn state, and RPT logs.

## Common gotchas

- A button can be the source without being animated or listed in the skeleton.
- A child handle must name the door bone as its parent or it will not follow the door transform.
- Only sources need a normal Doors mapping; animated selections sharing one source do not each need one.
- **DamageZones.componentNames[]** can target moving geometry (**door1**) even when the action source is **door1_open**.
- Use phase sub-ranges to sequence motion: Simple Door handle runs **0..0.15**, then the door runs **0.15..1**.
- **initOpened** is a spawn probability: `rand < initOpened` spawns the door opened (0 = always closed, 0.5 ~= half). Verified vs BI Doors_on_buildings wiki.
- Keep skeleton names unique. The tutorial warns that duplicate skeleton names can crash a server.
- The shipped Expert Mode example has a source-to-Doors anomaly; read its warning before copying it.
- (until 1.29: `LockDoor` / `UnlockDoor` plus lockpick was the only building-door lock path.) (since 1.30 Exp: a locked `DigitalCodeLock` or `CombinationLock` on a related slot also makes `BuildingBase.CanDoorBeOpened` return false. Lockpick is skipped when an external lock is already on that door. Combination unlock is a separate action `ActionCombinationLockUnlock` after the dials match.)
- (since 1.30 Exp) `EBuildingLockType` is still lockpick / ship-container keys. Combination and code locks are **inventory attachments**, not extra enum bits. Do not invent `COMBINATION_LOCK = 2` / `CODE_LOCK = 4`.

## Stop and ask

STOP and ask the user when a source, interaction selection, axis, component, LOD membership, or duplicate **class Doors** mapping cannot be proven from the real P3D/config files. Do not invent a plausible name. Prefix any unresolved technical claim with **?**.

## References

- [Model/config contract](references/door-model-cfg-and-config.md)
- [LODs and Object Builder](references/lods-and-object-builder.md)
- [Verified worked examples](references/worked-examples.md)
- [Official DayZ doors reference](https://community.bistudio.com/wiki/DayZ:Doors_on_buildings)
- [Official DayZ Samples](https://github.com/BohemiaInteractive/DayZ-Samples)
- [Official LOD reference](https://community.bistudio.com/wiki/LOD)

## Vehicle doors are out of scope (added 2026-08-31)

Vehicle doors do **not** use the building `class Doors` contract documented here.

- A detachable car door is a `CarDoor` attachment. `ActionCarDoorsOutside` resolves its target by
  raycast against the **item's ViewGeometry**.
- A door that stays part of the vehicle shell needs vehicle actions around
  `SetDoorOpen`/`IsDoorOpen` plus `model.cfg` `AnimationSources`.

Route vehicle work through `dayz-vehicles`: invariant #21 redirects to the public
`rip-vehicle-import/cookbooks/family-b/radial-puerta-ausente.md` **DOOR MECHANISM SELECTOR**, and
invariant #22 carries the attachment ViewGeometry rule. Applying building `class Doors` to a
vehicle will not produce a working radial, even though both mechanisms use names such as `source`,
`component`, and `axis`.

## DayZ 1.30 Exp (build 1.30.164014)

### What changes

- **Open API.** `DoorManipulationParams` carries `m_DoorIndex`, `m_CheckIfLocked`, and `m_Caller`. `Building.CanDoorBeOpened(notnull DoorManipulationParams params)` is the real check; the old `CanDoorBeOpened(int doorIndex, bool checkIfLocked = false)` still exists as a wrapper that does not set `m_Caller`. Vanilla `ActionOpenDoors` now fills the params object and also calls `BuildingBase.DoorsDirectionalCheck`. (`exp/scripts/scripts/3_Game/Entities/Building.c:5-10,141-167`, `exp/scripts/scripts/4_World/Classes/UserActionsComponent/Actions/Interact/ActionOpenDoors.c:36-52`)
- **Per-door extra info.** `AdditionalDoorInfo` is parsed from each **class Doors** child: `relatedInventorySlots[]`, `lockCompatibilityBitMask`, `interactPositionPoint`, `interactDirPoint`, `doorConstructionPart`, `doorConstructionPhysicsSource`. Default mask if the bitmask is omitted: `1 << EBuildingLockType.LOCKPICK`. (`exp/scripts/scripts/3_Game/Entities/AdditionalDoorsInfo.c:1-45`)
- **Attachment locks.** `BuildingBase` defines `Att_CombinationLock` and `Att_CodeLock`. A locked `DigitalCodeLock` or `CombinationLock` on a related slot blocks `CanDoorBeOpened`. Conflicting twin slots are rejected. A locked lock cannot be released. (`exp/scripts/scripts/4_World/Entities/Game/Super/Building.c:8-11,192-333`)
- **New item `DigitalCodeLock`.** Script class in `CodeLock.c`; logic in `CodeLockComponent`; UI layout `gui/layouts/day_z_digital_lock.layout`. Needs `Battery9V` in slot `BatteryD`. PIN length 4–6. Two brute-force stages via `CfgGameplayHandler.GetExternalLockProtectionCountStageOne/Two` and `GetExternalLockProtectionTime` / `GetExternalLockProtectionResetTime`. (`exp/scripts/scripts/4_World/Entities/ItemBase/CodeLock.c:1-41`, `exp/scripts/scripts/4_World/Classes/CodeLockComponent.c:4-73,468-479`)
- **`CombinationLock` two-sided + unlock action.** Dials no longer drop the lock by themselves; `ActionCombinationLockUnlock` runs after the combination matches. Persistence writes `m_CombinationInside` at vanilla stream **version 143**. (`exp/scripts/scripts/4_World/Entities/ItemBase/CombinationLock.c:32-65,128-177`, `exp/scripts/scripts/4_World/Classes/UserActionsComponent/Actions/SingleUse/ActionCombinationLockUnlock.c:1-7`)
- **Bunker doors.** `Bunker.CanDoorBeOpened` uses `MemPointDirectionalCheck` on `{doorType}_action` / `{doorType}_inside`. Main door auto-closes after `DOOR_AUTOCLOSE_TIME = 12` and re-locks the `DigitalCodeLock_Bunker`. (`exp/scripts/scripts/4_World/Entities/Building/Bunker.c:3,47-61,73-89`)
- **Rebuildable house doors.** `Rebuilding` drives `doorConstructionPhysicsSource` on open/close start. (`exp/scripts/scripts/4_World/Classes/Rebuilding/Rebuilding.c:440-464`)
- **[CHANGELOG]** House-based `disableSimulation` (natives `DisableSimulation` / `GetIsSimulationDisabled` on `Entity`) and a fix for inventory attachments on buildings created at load time. (`exp/scripts/scripts/3_Game/Entities/Entity.c:3-6`, `work/changelog-1.30-exp-modding.md:13,36`)

### What breaks for a 1.29 door mod

| Break | Severity | Migration |
|---|---|---|
| Override of `CanDoorBeOpened(int, bool)` is skipped by vanilla Open | **HIGH** | Override `CanDoorBeOpened(notnull DoorManipulationParams params)` and call `super`. The `int` wrapper still exists (`Building.c:160-167`) but `ActionOpenDoors` no longer calls it (`ActionOpenDoors.c:39-52`). Vanilla `Land_WarheadStorage_Main` still overrides the `int` form (`Land_WarheadStorage_Main.c:352`) — do not copy that as the 1.30 pattern. |
| Door opens from the wrong side, or Open never appears | **MEDIUM** | Add Memory points named in `interactPositionPoint` / `interactDirPoint`, or omit both (empty names make `MemPointDirectionalCheck` return true). (`MiscGameplayFunctions.c:911-936`, `Building.c` 4_World `:335-342`) |
| Lockpick still offered on a padlocked door | **MEDIUM** | Set `relatedInventorySlots[]` on that Doors entry so `ActionLockDoors` / `ActionUnlockDoors` see the external lock. (`ActionLockDoors.c:40-57`) |
| Custom combination-lock auto-unlock on last dial | **MEDIUM** | Fire `ActionCombinationLockUnlock` after the dials match. Persist `m_CombinationInside` when `version >= 143`. |
| Code lock / combination lock never attaches to a custom building | **HIGH** | Declare the slots on the entity, proxy selections `att_codelock` / `att_combinationlock`, and `relatedInventorySlots[]` on the door. `ActionAttachToConstruction` looks up the slot from `AdditionalDoorInfo`. (`ActionAttachToConstruction.c:151-174`) |

### 1.30 migration checklist (building doors)

- [ ] Search the mod for `CanDoorBeOpened(` and convert building overrides to the `DoorManipulationParams` signature.
- [ ] If the door should take a lock, add `attachments[]` + `relatedInventorySlots[]` + Memory slot selections.
- [ ] Do not treat `EBuildingLockType` as the combination/code-lock API; those are attachments.
- [ ] Combination-lock mods: add `ActionCombinationLockUnlock` and the v143 `m_CombinationInside` read.
- [ ] Rebuildable doors: set `doorConstructionPart` and `doorConstructionPhysicsSource` on the Doors entry.
- [ ] Optional: `disableSimulation = 1` on static house classes that must not tick (`[CHANGELOG]`; no extracted `config.cpp` example in this dump).

### 1.30 references in this skill

- [Door open conditions and locks](references/door-model-cfg-and-config.md#door-open-conditions-and-locks-dayz-130-exp)
- [Building lock integration examples](references/worked-examples.md#building-locks-dayz-130-exp)
- [1.30 Memory points and lock slot selections](references/lods-and-object-builder.md#dayz-130-exp-memory-points-and-lock-slots)
