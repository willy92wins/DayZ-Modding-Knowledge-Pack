# Entity lifecycle — deploy → build → sync → persist → load

Authored 2026-07-07 (F4) from vanilla P:\scripts — see citations.

The exact call chain from crafting a kit to a base surviving a server restart, hop by hop. Roots:
`P:\scripts\` = `<dayz-projects>\scripts\`. Server-authoritative: every
mutating hop runs through a `*Server` method gated by `g_Game.IsServer()`; the client only previews.

## 1. Deploy (hologram)

1. `RecipeBase` (`craftfencekit.c:1`) consumes materials → a `KitBase: ItemBase` (`kitbase.c:1`;
   `IsBasebuildingKit()→true` `:5`).
2. Kit `SetActions()` adds `ActionTogglePlaceObject` + `ActionDeployObject` (`kitbase.c:146-152`).
3. `ActionDeployObject` (`actiondeployobject.c:7`) is hologram-driven (`ActionUsesHologram()→true` `:15`).
   Placement validity is checked against `player.GetHologramLocal()/GetHologramServer()` — `IsColliding()`,
   `item.CanBePlaced(...)` (`actiondeployobject.c:42-75`). Kits declare `DoPlacingHeightCheck()→true` and a
   `HeightCheckOverride()` (FenceKit 2.54 `fencekit.c:36-44`; WatchtowerKit 2.83 `watchtowerkit.c:32-40`).
4. On finish the client calls `entity.OnPlacementComplete(...)` (`actiondeployobject.c:164`). The SERVER-only
   `FenceKit.OnPlacementComplete` (`fencekit.c:19-34`) does `g_Game.CreateObjectEx("Fence", …)` with
   `ECE_PLACE_ON_SURFACE`, sets pos/orient, `HideAllSelections()`.
5. The kit self-deletes on `OnEndServer` if it was placed (`actiondeployobject.c:230-234`).

## 2. Construction init

`BaseBuildingBase` owns one `ref Construction m_Construction` (1.29 `basebuildingbase.c:8`), created in
`ConstructionInit()` (`:965-973`) — called from the constructor (`:52`) and again in `OnCreatePhysics()`
(`:489-494`). `GetConstruction()` (`:975`). `Construction.UpdateConstructionParts()` (1.29 `construction.c:235-270`)
reads the `Construction{}` config block and populates `map<string, ref ConstructionPart> m_ConstructionParts`
(1.29 `construction.c:15`), keyed by part config-class name.
(until 1.29: that field type and those line numbers). (since 1.30: `protected ref ConstructionBasic
m_Construction` (`basebuildingbase.c:15`). `ConstructionInit()` is on `EntityAI` (`EntityAI.c:3464-3471`)
and calls `CreateConstructionComponent()` (`:3474`). `BaseBuildingBase` overrides that to
`m_Construction = new Construction(this)` (`basebuildingbase.c:871-875`). `UpdateConstructionParts` is on
`ConstructionBase.c:518-549` and fills parts from `ConstructionDataTypeHolder`, not by walking config on the
instance. `GetConstruction()` is `Construction.Cast(m_Construction)` (`basebuildingbase.c:883-886`).)

## 3. Base part

The freshly-spawned entity has NO parts built. The player attaches the base material (e.g. WoodenLogs) then
builds the `base` part (`is_base=1`). Building the base sets `HasBase()=true`, spawns a construction kit back
(`OnPartBuiltServer` `basebuildingbase.c:554-560`), and toggles the `"Deployed"` animation/proxy
(`InitVisuals` `:677-691`).

## 4. Build a part

1. `ActionBuildPart` (`actionbuildpart.c:33`) with a tool in hand. Collision is re-checked server-side in
   `ActionConditionContinue` / `OnFinishProgressServer` via `IsCollidingEx` (`actionbuildpart.c:123-148, 150-167`).
2. On 1.29, `OnFinishProgressServer` (`actionbuildpart.c:112-130`) re-validates `CanBuildPart` (the "redundant at this point" comment
   at `:123`) then calls `construction.BuildPartServer(player, part_name, AT_BUILD_PART)` (1.29 `construction.c:75-95`).
   (until 1.29: `BuildPartServer`). (since 1.30: `construction.BuildPartServerEx(action_data.m_Player, partName, AT_BUILD_PART)`
   after `IsCollidingEx(checkData)` (`actionbuildpart.c:157-170`). `Construction.BuildPartServerEx` still
   resets the damage zone and calls `OnPartBuiltServer` (`Construction.c:52-68`).)
3. `BuildPartServer`: reset the part's damage-zone health, `TakeMaterialsServer` (1.29 `construction.c:671-723` —
   `lockable=1` locks the slot; else subtract `quantity`, or delete on `quantity==-1`), destroy the build
   collision trigger, call `GetParent().OnPartBuiltServer` (`basebuildingbase.c:549-580`).
   (until 1.29: `BuildPartServer` destroyed a construction-box trigger). (since 1.30: `ConstructionBase.BuildPartServerEx`
   only `TakeMaterialsServer(part_name)` (`ConstructionBase.c:180-185`); `CreateCollisionTrigger` /
   `DestroyCollisionTrigger` / `IsTriggerColliding` remain as `[Obsolete("no replacement")]`
   (`ConstructionBase.c:1805-1850`). Do not write new trigger calls.)
4. `OnPartBuiltServer` → `RegisterPartForSync` (sets the part's `id` bit in `m_SyncParts01/02/03`
   `basebuildingbase.c:137-164`), sync, show part physics + visual, regen navmesh.

### CanBuildPart / CanDismantlePart / CanDestroyPart gates

- `CanBuildPart` (1.29 `construction.c:296-304`): `!IsPartConstructed && HasRequiredPart && !HasConflictPart &&
  HasMaterials && (!use_tool || CanUseToolToBuildPart) && !MaterialIsRuined`.
  (since 1.30: `CanBuildPart` / `CanBuildPartEx` on `ConstructionBase.c:584-601`; failure bits in
  `EConstructionInfoCategories` (`ConstructionConstants.c:1-11`).)
- `CanDismantlePart` (1.29 `construction.c:468-476`): `IsPartConstructed && !HasDependentPart && CanUseToolToDismantlePart`;
  since 1.30 it also requires `SupportRemovalCheck` (`ConstructionBase.c:780-810`).
- `CanDestroyPart` (1.29 `construction.c:566-574`; since 1.30 also `SupportRemovalCheck`,
  `ConstructionBase.c:1063-1069`): `IsPartConstructed && !HasDependentPart` (no tool/material gate — triggered
  by damage, 1.29 `basebuildingbase.c:510-518`; 1.30 `ConstructionBase.c:353-369`).

## 5. Upgrade

Just building further parts whose `required_parts[]` are satisfied (`HasRequiredPart` `ConstructionBase.c:723-736`)
and whose `conflicted_parts[]` are not built (`HasConflictPart` `:745-767`). E.g. `wall_wood_down` requires
`wall_base_down` and conflicts with `wall_metal_down`. Radial variants: multiple buildable parts under one
selection produce N action variants — `ActionBuildPart` uses `m_VariantID`; `ConstructionActionData.OnUpdateActions`
sets the variant count (`constructionactiondata.c:187`), and its `OnUpdateActions` (`:163-199`) calls
`Construction.GetConstructionPartsToBuild(...)` each cursor update.

## 6. Dismantle / destroy / fold

- `ActionDismantlePart` (`actiondismantlepart.c:23`) → `DismantlePartServer` (1.29 `construction.c:98-118`):
  refunds materials (`ReceiveMaterialsServer` → `StaticConstructionMethods.SpawnConstructionMaterialPiles`),
  drops non-usable materials, calls `OnPartDismantledServer`. Blocked if the part `HasDependentPart`
  (`ConstructionBase.c:813-824`). Dismantling the **base** destroys the whole construction (`basebuildingbase.c:615-619`).
  (since 1.30: `DismantlePartServerEx` (`ConstructionBase.c:191-207`, override `Construction.c:77-90`).
  `HasDependentPart` is `ConstructionBase.c:813`.)
- Destroy on ruin: `EEHealthLevelChanged` (1.29 `basebuildingbase.c:496-528`; 1.30 `ConstructionBase.OnHealthLevelChanged`, `ConstructionBase.c:353-369`) — when a zone hits `STATE_RUINED`,
  `DestroyPartServer` that part + `DestroyConnectedParts` (1.29 `construction.c:141-154`, dependents, with a gate
  exception `ExceptionCheck` `:157-167`).
- Fold: with no base and no attachments (`CanFoldBaseBuildingObject` `basebuildingbase.c:962-970`),
  `ActionFoldBaseBuildingObject` → `FoldBaseBuildingObject` (`:972-978`) converts back to a kit in hands.

## 7. Persist → load reconciliation

- `OnStoreSave` (`basebuildingbase.c:420-430`): writes `m_SyncParts01`, `02`, `03`, then `m_HasBase`.
  A subclass appends its extra fields AFTER `super` (Fence adds `m_GateState`, `m_IsOpened` — `fence.c:246-254`).
- `OnStoreLoad` (`basebuildingbase.c:432-464`): reads the three ints then `m_HasBase`, each with a `return false` on read
  failure (default-then-abort). Subclass reads AFTER `super` in the same order (`fence.c:256-289`, with a
  `version<110` legacy branch).
- `AfterStoreLoad` (`basebuildingbase.c:466-474`) → `SetPartsAfterStoreLoad()` (`:476-487`) → `SetPartsFromSyncData()`: rebuilds
  each part's built flag from the bitmask, sets base state from the base part, re-syncs. Guarded by
  `m_FixDamageSystemInit` (the damage-system migration path uses `EEOnAfterLoad` + a 500ms deferred call
  instead, `:505-513`).
- `SetPartFromSyncData` (`:265-304`) — the reconciliation core: per part, compares "built in sync bitmask"
  vs "built flag", adds/removes constructed parts, shows/hides physics, toggles the `Deployed` proxy for the
  base, and **failsafe-relocks attached materials** (`:303`, "failsafe for corrupted sync/storage data").

## 8. Action-type ints and the action set

`_constants.c:6-8`: `AT_BUILD_PART=193`, `AT_DISMANTLE_PART=195`, `AT_DESTROY_PART=209`. Also
`m_InteractedPartId` / `m_PerformedActionId` (`basebuildingbase.c:13-14`, registered `:46-47`) sync the last
action so clients play the right SFX (`SetActionFromSyncData` `:248-262`).

Action classes (`scripts\4_world\classes\useractionscomponent\actions\`): `continuous\actionbuildpart.c`,
`continuous\actiondismantlepart.c`, `continuous\actiondestroypart.c`, `continuous\deployactions\actiondeployobject.c`,
`continuous\actionfoldbasebuildingobject.c`, `interact\actionbuildshelter.c` (no-tool build),
`interact\actionopenfence.c`, `interact\actionclosefence.c`, `singleuse\actionattachtoconstruction.c`,
`singleuse\actionplugintofence.c` (DEPRECATED — do not build on it).

`[UNVERIFIED]` The no-tool shelter path (`ActionBuildShelter` / `ActionActionBuildPartNoTool`,
`UseMainItem()→false`, 1.29 `actionbuildpart.c:224-245` + `interact\actionbuildshelter.c`) exists but its
shelter-specific config was not fully traced in this pass.

## 9. DayZ 1.30 — hop notes

- `CreateConstructionComponent` / `GetConstructionBasic` are the hooks; see
  `references/dayz-1-30-construction-rebuilding.md` §1 for EXACT getters.
- `BuildingBase` uses the same hooks to install `Rebuilding` (`Building.c:23-50`). That path does **not**
  go through `FenceKit.OnPlacementComplete`.
- `SetRequestBuiltState` is obsolete (`ConstructionPart.c:510-518`); use `SetBuiltState`.
- Fence `OnStoreSave` in 1.30 is `fence.c:246-254` (still `super` then `m_GateState`, `m_IsOpened`).
