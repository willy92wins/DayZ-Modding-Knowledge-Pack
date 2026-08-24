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

`BaseBuildingBase` owns one `ref Construction m_Construction` (`basebuildingbase.c:8`), created in
`ConstructionInit()` (`:965-973`) — called from the constructor (`:52`) and again in `OnCreatePhysics()`
(`:489-494`). `GetConstruction()` (`:975`). `Construction.UpdateConstructionParts()` (`construction.c:235-270`)
reads the `Construction{}` config block and populates `map<string, ref ConstructionPart> m_ConstructionParts`
(`construction.c:15`), keyed by part config-class name.

## 3. Base part

The freshly-spawned entity has NO parts built. The player attaches the base material (e.g. WoodenLogs) then
builds the `base` part (`is_base=1`). Building the base sets `HasBase()=true`, spawns a construction kit back
(`OnPartBuiltServer` `basebuildingbase.c:592-598`), and toggles the `"Deployed"` animation/proxy
(`InitVisuals` `:770-784`).

## 4. Build a part

1. `ActionBuildPart` (`actionbuildpart.c:25`) with a tool in hand. Collision is re-checked server-side in
   `ActionConditionContinue` / `OnFinishProgressServer` via `IsCollidingEx` (`actionbuildpart.c:90-110, 112-130`).
2. `OnFinishProgressServer` (`:112-130`) re-validates `CanBuildPart` (the "redundant at this point?" comment
   at `:123`) then calls `construction.BuildPartServer(player, part_name, AT_BUILD_PART)` (`construction.c:75-95`).
3. `BuildPartServer`: reset the part's damage-zone health, `TakeMaterialsServer` (`construction.c:671-723` —
   `lockable=1` locks the slot; else subtract `quantity`, or delete on `quantity==-1`), destroy the build
   collision trigger, call `GetParent().OnPartBuiltServer` (`basebuildingbase.c:587-618`).
4. `OnPartBuiltServer` → `RegisterPartForSync` (sets the part's `id` bit in `m_SyncParts01/02/03`
   `basebuildingbase.c:148-175`), sync, show part physics + visual, regen navmesh.

### CanBuildPart / CanDismantlePart / CanDestroyPart gates

- `CanBuildPart` (`construction.c:296-304`): `!IsPartConstructed && HasRequiredPart && !HasConflictPart &&
  HasMaterials && (!use_tool || CanUseToolToBuildPart) && !MaterialIsRuined`.
- `CanDismantlePart` (`:468-476`): `IsPartConstructed && !HasDependentPart && CanUseToolToDismantlePart`.
- `CanDestroyPart` (`:566-574`): `IsPartConstructed && !HasDependentPart` (no tool/material gate — triggered
  by damage, `basebuildingbase.c:510-518`).

## 5. Upgrade

Just building further parts whose `required_parts[]` are satisfied (`HasRequiredPart` `construction.c:412-435`)
and whose `conflicted_parts[]` are not built (`HasConflictPart` `:438-455`). E.g. `wall_wood_down` requires
`wall_base_down` and conflicts with `wall_metal_down`. Radial variants: multiple buildable parts under one
selection produce N action variants — `ActionBuildPart` uses `m_VariantID`; `ConstructionActionData.OnUpdateActions`
sets the variant count (`constructionactiondata.c:139`), and its `OnUpdateActions` (`:129-155`) calls
`Construction.GetConstructionPartsToBuild(...)` each cursor update.

## 6. Dismantle / destroy / fold

- `ActionDismantlePart` (`actiondismantlepart.c:26`) → `DismantlePartServer` (`construction.c:98-118`):
  refunds materials (`ReceiveMaterialsServer` → `StaticConstructionMethods.SpawnConstructionMaterialPiles`),
  drops non-usable materials, calls `OnPartDismantledServer`. Blocked if the part `HasDependentPart`
  (`construction.c:479-496`). Dismantling the **base** destroys the whole construction (`basebuildingbase.c:653-657`).
- Destroy on ruin: `EEHealthLevelChanged` (`basebuildingbase.c:496-528`) — when a zone hits `STATE_RUINED`,
  `DestroyPartServer` that part + `DestroyConnectedParts` (`construction.c:141-154`, dependents, with a gate
  exception `ExceptionCheck` `:157-167`).
- Fold: with no base and no attachments (`CanFoldBaseBuildingObject` `basebuildingbase.c:1067-1075`),
  `ActionFoldBaseBuildingObject` → `FoldBaseBuildingObject` (`:1077-1083`) converts back to a kit in hands.

## 7. Persist → load reconciliation

- `OnStoreSave` (`basebuildingbase.c:420-430`): writes `m_SyncParts01`, `02`, `03`, then `m_HasBase`.
  A subclass appends its extra fields AFTER `super` (Fence adds `m_GateState`, `m_IsOpened` — `fence.c:212-220`).
- `OnStoreLoad` (`:432-464`): reads the three ints then `m_HasBase`, each with a `return false` on read
  failure (default-then-abort). Subclass reads AFTER `super` in the same order (`fence.c:222-255`, with a
  `version<110` legacy branch).
- `AfterStoreLoad` (`:466-474`) → `SetPartsAfterStoreLoad()` (`:476-487`) → `SetPartsFromSyncData()`: rebuilds
  each part's built flag from the bitmask, sets base state from the base part, re-syncs. Guarded by
  `m_FixDamageSystemInit` (the damage-system migration path uses `EEOnAfterLoad` + a 500ms deferred call
  instead, `:530-538`).
- `SetPartFromSyncData` (`:276-315`) — the reconciliation core: per part, compares "built in sync bitmask"
  vs "built flag", adds/removes constructed parts, shows/hides physics, toggles the `Deployed` proxy for the
  base, and **failsafe-relocks attached materials** (`:314`, "failsafe for corrupted sync/storage data").

## 8. Action-type ints and the action set

`_constants.c:6-8`: `AT_BUILD_PART=193`, `AT_DISMANTLE_PART=195`, `AT_DESTROY_PART=209`. Also
`m_InteractedPartId` / `m_PerformedActionId` (`basebuildingbase.c:15-16`, registered `:47-48`) sync the last
action so clients play the right SFX (`SetActionFromSyncData` `:259-273`).

Action classes (`scripts\4_world\classes\useractionscomponent\actions\`): `continuous\actionbuildpart.c`,
`continuous\actiondismantlepart.c`, `continuous\actiondestroypart.c`, `continuous\deployactions\actiondeployobject.c`,
`continuous\actionfoldbasebuildingobject.c`, `interact\actionbuildshelter.c` (no-tool build),
`interact\actionopenfence.c`, `interact\actionclosefence.c`, `singleuse\actionattachtoconstruction.c`,
`singleuse\actionplugintofence.c` (DEPRECATED — do not build on it).

`[UNVERIFIED]` The no-tool shelter path (`ActionBuildShelter` / `ActionActionBuildPartNoTool`,
`UseMainItem()→false`, `actionbuildpart.c:224-245` + `interact\actionbuildshelter.c`) exists but its
shelter-specific config was not fully traced in this pass.
