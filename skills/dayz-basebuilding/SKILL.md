---
name: dayz-basebuilding
description: >
  Author, extend and debug DayZ buildable structures on BaseBuildingBase:
  fences, watchtowers, gates, walls, shelters, tents, flag poles and barbed
  wire. Covers kit recipe/deploy/hologram flow, Construction{} fields,
  BaseBuildingBase/Construction/ConstructionPart/ConstructionActionData,
  required/conflicted parts, build/dismantle/destroy actions, synced-bitmask
  persistence, damage-zone mapping and the Fence gate state machine. Use for
  "base won't save", parts reset/disappear after restart, construction part or
  action missing, CanBuild/CanBuildPart, RegisterPartForSync, blocked
  dismantle, missing collision or hologram placement. Always invoke before
  authoring/debugging a buildable structure or its persistence. Delegate
  geometry to dayz-model-pipeline, script APIs to enforce-script-reference,
  persistence audit to rigorous-data-audit and packaging to dayz-pbo-build.
  Also 1.30 Exp: ConstructionBase/Rebuilding, BuildPartServerEx, bricks/mortar, fence code lock.
  Not terrain holes: dayz-underground.
---

# DayZ Base Building

Buildable player structures in DayZ — fences, watchtowers, gates, shelters, flag poles — are built by
**extending the vanilla `BaseBuildingBase` chain**, not from `EntityAI`. Inheriting `BaseBuildingBase`
gives you the whole system for free: the per-part build/dismantle/destroy action set, the synced-bitmask
persistence, the hologram deploy flow, and the damage-driven part destruction. The only things you author
are a `.p3d` with the right selections + memory points and a config `Construction{}` block that declares
each buildable part.

This skill owns the base-building-specific layer. Generic geometry, config-script mechanics, packaging and
data-critical audit are delegated to the skills in the table below.

The whole system is ~6 script files + 1 config block. All `path:line` citations here point at real vanilla
source under `P:\scripts\` (= `<dayz-projects>\scripts\`) and
`DZ\gear\camping\config.cpp`. Verify against those before writing any class name or field.
(until 1.29: that ~6-file count). (since 1.30 Exp: `ConstructionBasic` in `3_Game`, `ConstructionBase` /
`Construction` / `Rebuilding` in `4_World`, plus `ConstructionPartTypeData` on `EntityType`. Full map in
`references/dayz-1-30-construction-rebuilding.md`.)

## THE MODEL — kit → deploy → build → upgrade → dismantle

The four-class quartet and who owns what:

| Class | Role | Where |
|---|---|---|
| `BaseBuildingBase: ItemBase` | the persisted world entity; owns one `ref Construction`, the sync ints, events, physics, area damage | `basebuildingbase.c:2` |
| `Construction` | per-instance controller; holds `map<string, ref ConstructionPart>` keyed by part config-class name; does ALL config lookups live | `construction.c:11` |
| `ConstructionPart` | runtime record of one part (name, `m_Id` bit index, built/base/gate flags, required parts) | `constructionpart.c:1` |
| `ConstructionActionData` | per-player scratch state on `PlayerBase`; caches which parts are buildable under the cursor, drives radial action variants | `constructionactiondata.c:1` |
| `ConstructionBasic` | (since 1.30 Exp:) 3_Game stub + `EntityAI` hooks `CreateConstructionComponent()` / `GetConstructionBasic()` | `Construction_Basic.c:2`; `EntityAI.c:3441-3479` |
| `ConstructionBase : ConstructionBasic` | (since 1.30 Exp:) shared 4_World controller; `BuildPartServerEx` / `DismantlePartServerEx` / `IsCollidingEx` | `ConstructionBase.c:30,174,185,1471` |
| `Rebuilding : ConstructionBase` | (since 1.30 Exp:) map-building restoration on `BuildingBase`; ten `m_SyncParts*` ints | `Rebuilding.c:1`; `Building.c:23-26` |
| `ConstructionPartTypeData` | (since 1.30 Exp:) type-level cached `Construction{}` fields; instance `ConstructionPart` holds mutable state | `ConstructionPartTyped.c:2` |

`Construction` is NOT itself persisted — it is rebuilt from config on every load and its part states are
restored from the sync bitmask (see PERSISTENCE). End-to-end flow:
(until 1.29: `BaseBuildingBase` owned `ref Construction m_Construction` and `ConstructionPart` stored config
fields per instance). (since 1.30 Exp: the field is `protected ref ConstructionBasic m_Construction`
(`basebuildingbase.c:15`); `CreateConstructionComponent()` does `new Construction(this)` (`:871-875`);
`GetConstruction()` is `Construction.Cast(m_Construction)` (`:883-886`). Config is cached once per
`EntityType` in `ConstructionPartTypeData` and attached via `SetPartTypeData` (`ConstructionPart.c:383-389`;
`ConstructionBase.UpdateConstructionParts` `:495-532`).)

1. **Craft the kit.** A `RecipeBase` (`craftfencekit.c:1`) consumes materials → a `KitBase: ItemBase`
   (`kitbase.c:1`, `IsBasebuildingKit()→true` `:5`).
2. **Deploy (hologram).** Kit `SetActions()` adds `ActionTogglePlaceObject` + `ActionDeployObject`
   (`kitbase.c:146-152`); `ActionDeployObject.ActionUsesHologram()→true` (`actiondeployobject.c:15`). On
   finish the SERVER spawns the real entity — `FenceKit.OnPlacementComplete` (`fencekit.c:19-34`)
   `CreateObjectEx("Fence", …)` + `HideAllSelections()` — and the kit self-deletes on `OnEndServer`
   (`actiondeployobject.c:230-234`).
3. **Base part.** The spawned entity has NO parts built. Player attaches the base material then builds the
   `base` part (`is_base=1`). Building it sets `HasBase()=true`, spawns a construction kit back, and toggles
   the `"Deployed"` proxy/animation (`OnPartBuiltServer` `basebuildingbase.c:592-598`; `InitVisuals` `:770-784`).
4. **Build part.** `ActionBuildPart` (`actionbuildpart.c:25`) with a tool in hand → `OnFinishProgressServer`
   (`:112-130`) re-checks collision + `CanBuildPart` → `construction.BuildPartServer(...)` (`construction.c:75-95`):
   reset damage-zone health, `TakeMaterialsServer`, register the part in the sync bitmask, show physics+visual,
   regen navmesh.
   (until 1.29: `BuildPartServer(player, part_name, action_id)`). (since 1.30 Exp: `ActionBuildPart` calls
   `BuildPartServerEx` (`actionbuildpart.c:170`); the old method is `[Obsolete("call BuildPartServerEx instead")]`
   and forwards (`ConstructionBase.c:1688-1694`). Override `BuildPartServerEx`, not the obsolete wrapper.)
5. **Upgrade** = building further parts whose `required_parts[]` are satisfied (`HasRequiredPart`
   `construction.c:412-435`) and whose `conflicted_parts[]` are not built (`HasConflictPart` `:438-455`).
6. **Dismantle.** `ActionDismantlePart` (`actiondismantlepart.c:26`) → `DismantlePartServer` (`:98-118`)
   refunds materials. Blocked if the part `HasDependentPart` (`construction.c:479-496`). Dismantling the
   **base** part destroys the whole construction (`basebuildingbase.c:653-657`).
   (until 1.29: `DismantlePartServer`). (since 1.30 Exp: `DismantlePartServerEx` (`ConstructionBase.c:185`);
   obsolete wrapper `:1696-1702`. `HasDependentPart` now lives on `ConstructionBase` `:758`.)
7. **Fold.** With no base and no attachments (`CanFoldBaseBuildingObject` `:1067-1075`),
   `ActionFoldBaseBuildingObject` converts back to a kit in hands (`FoldBaseBuildingObject` `:1077-1083`).

## THE Construction{} CONFIG BLOCK (the single most-reused artifact)

Two-level nesting: `Construction { class <main_part> { class <part> {...} } }`. Annotated from the Fence
block (`config.cpp:4527-4585`). Full field-by-field in `references/config-contract.md`.

```cpp
class Construction {
  class wall {                          // main_part_name (m_MainPartName)
    class base {                        // part_name — config class == m_PartName AND the p3d selection
      name="$STR_..._Part_Base";        // localized display name
      is_base=1;                        // foundation part; dismantling it destroys the whole entity
      id=1;                             // UNIQUE sync/persistence bit index, 1..93 (see PERSISTENCE)
      required_parts[]={};              // parts that must be built first
      conflicted_parts[]={};            // parts that block this one if already built
      collision_data[]={};              // {min_memorypoint, max_memorypoint} for the build collision box
      build_action_type=4;             // bitmask AND-matched against the tool's build_action_type
      dismantle_action_type=4;
      material_type=1;                  // ConstructionMaterialType — drives build/dismantle SFX
      class Materials {
        class Material1 {
          type="WoodenLog";             // item classname (used when refunding piles)
          slot_name="Material_WoodenLogs"; // attachment slot the material sits in
          quantity=2;                   // consumed; -1 = delete whole object; 0 = ignore qty
          lockable=1;                   // 1 = lock material in slot instead of consuming it
        };
      };
    };
  }
}
```

Every field's reader lives in `construction.c` — cited in `references/config-contract.md`. The entity class
itself declares `attachments[]` (material/attachment slots), `hybridAttachments[]` (health mirrors a damage
zone), `mountables[]` (proxy-physics toggled, e.g. barbed wire), and a `DamageSystem { class DamageZones }`.

## PREFLIGHT — the hard invariants

Gate real build work on `/dayz-preflight` (P:\ mounted, AddonBuilder, P:\Mods junction) per
`_shared/dayz-conventions.md`. Authoring config offline does not need it; packing does. Before declaring a
base-building entity done, verify ALL of these — each is a silent-corruption source:

- **`id` MUST be unique and in 1..93** across the whole `Construction{}` block. The id is a bit index into
  three 31-bit sync ints; a duplicate or out-of-range id collides in the bitmask and corrupts part state
  (`RegisterPartForSync` `basebuildingbase.c:148-175`). This caps a single entity at 93 distinct parts.
  (until 1.29: that 93-part cap was the only packing). (since 1.30 Exp: it still holds for every
  `BaseBuildingBase` — `RegisterPartForSync` is unchanged (`basebuildingbase.c:137-164`) and `OnStoreSave`
  still writes `m_SyncParts01/02/03` then `m_HasBase` (`:420-430`). `Rebuilding` on `BuildingBase` is a
  different stream: ten ints `m_SyncParts1`..`10`, 2 bits per part, `REBUILDING_STORAGE_VERSION = 1`
  (`Rebuilding.c:3,7-16,502-515`). Do not mix the two caps.)
- **Damage-zone name MUST equal the part name, lowercased.** `EEHealthLevelChanged` lowercases the zone and
  looks up the part by that name (`basebuildingbase.c:507-517`); a mismatch means damage never destroys the part.
- **`OnStoreSave`/`OnStoreLoad` order is strict.** Save writes `m_SyncParts01`, `02`, `03`, then `m_HasBase`
  (`basebuildingbase.c:420-430`); load reads them in the same order (`:432-464`). A subclass writes/reads its
  extra fields AFTER calling `super`, in the exact same order both ways (Fence appends gate state after the
  three ints — `fence.c:212-220` / `:222-255`). Reordering silently corrupts every saved base.
- **Every `part_name` MUST be both an AnimationSource in config AND a selection in the `.p3d`.** Show/hide is
  `SetAnimationPhase(part_name, 0/1)` (`construction.c:578-588`, phase 0 = visible); the base uses the
  `"Deployed"` proxy instead. A missing selection/memory point → the part builds but has no visual or no collision.
- **Action-type ints** (`_constants.c:6-8`): `AT_BUILD_PART=193`, `AT_DISMANTLE_PART=195`, `AT_DESTROY_PART=209`.
  Passed into `BuildPartServer`/`DismantlePartServer`/`DestroyPartServer` and synced so clients play the right SFX.
  (since 1.30 Exp: pass them into `BuildPartServerEx` / `DismantlePartServerEx`. Tool masks now include
  `EConstructionTools.TOOL_BRICKLAYING = 256` (`ConstructionConstants.c:25`).)
- **How much of a material fits in one slot is decided by the SLOT's `stackMax`, NOT by the item's
  `varQuantityMax`.** For a splitable item, `GetTargetQuantityMax` asks `InventorySlots.GetStackMaxForSlotId`
  first and only falls back to `varStackMax`, then to `varQuantityMax` (`itembase.c:3473-3490`). Vanilla
  declares the cap per slot in `scripts\config.cpp`: `Material_WoodenPlanks` and `Material_MetalSheets` are
  `stackMax=20` (`:2266-2281`), `Material_Nails` is `99` (`:2260-2264`). A NON-splitable item skips that
  branch entirely and lands on `varQuantityMax` — `MetalWire` declares no quantity and neither of its slots
  declares `stackMax` (`:2290-2296`, `:2349-2355`), so it is one wire per slot. Reading the item class instead
  overstates plank capacity 5× (100 vs 20) and makes any recipe above the slot cap silently unbuildable: the
  player fills the slot and never reaches the threshold, so the build action simply never appears. Derive
  slots per material as `ceil(default_qty / slot stackMax)` and get that number from `CfgSlots`, not from the
  item. Any design promising a uniform configurable range ("1..100 of each material") is broken before it is
  written. Origin: caught by an independent plan review after the item-class reading had already been written
  into a spec — the item's ceiling exists, it just is not the one that governs.
- **A green/red placement hologram needs TWO declarations, and neither is the one the name
  suggests.** `Hologram.RefreshVisual` tints by calling `SetObjectTexture`/`SetObjectMaterial` on a
  **hidden-selection index** (`hologram.c:1546-1565`). That index comes from `GetHiddenSelection`,
  which **falls back to 0 when the name is absent** (`:1523-1531`) — so a model with no
  `hiddenSelections[]` in config silently renders the ghost in its normal material, with no error
  anywhere. And the config entry alone is not enough: the model must expose that selection as
  retexturable via `sections[]` in `model.cfg`, or the swap has nothing to bind to. Declare
  `hiddenSelections[]` + `hiddenSelectionsTextures[]` + `hiddenSelectionsMaterials[]` with the values
  the model **already uses** (so normal rendering is unchanged), and put the same selection in
  `sections[]`. Note the hologram never looks the name up: it asks for `placing`/`inventory`
  (`:40-43,178-194`) and lands on index 0 regardless, so the name only maps index 0 to a real
  section. Also declare `hologramMaterial` + `hologramMaterialPath`; the engine appends
  `_deployable.rvmat` / `_undeployable.rvmat` (`:14-16`). Cost of learning this the hard way: one
  in-game cycle, plus a review finding that was raised, retired as a likely false positive, and
  turned out to be true.
- **`itemBehaviour` does NOT choose the in-hands carry pose.** The int drives behaviour rules and the
  deploy command (`itembase.c:65`: `0 = heavy, 1 = onehanded, 2 = twohanded`), but the pose comes
  from **class registration in the anim graph**. Vanilla registers every heavy object explicitly —
  barrel at `dayzplayercfgbase.c:817`, wooden crate at `:830` — through
  `ModItemRegisterCallbacks.RegisterHeavy` (`:305,:317`) calling `AddItemInHandsProfileIK(class, …
  player_main_heavy.asi, pBehavior, … .anm)`. With no registration the item falls back to the
  `Inventory_Base` one-handed default and is carried in one hand no matter what `itemBehaviour` says.
  The `.anm` is an IK pose, not a class binding, so reusing a vanilla one for a different class is
  fine and needs no new animation. Pick the value from the object family you are imitating, not from
  a mod that ships a different shape: a cabinet is `0` like the barrel, not `2` like a small kit box. `SetActions` adds
  `ActionTogglePlaceObject` + `ActionPlaceObject` only in the deployable subclass (`container_base.c:32,48-54`),
  which is what `Barrel_ColorBase` inherits from (`barrel_colorbase.c:1`). A storage entity extending
  `Container_Base` gets no placement at all, and `IsDeployable()` is `false` by default (`itembase.c:4380-4383`).
  Adding the two actions to the single class that needs them is cheaper than reparenting a shared base and
  cannot regress its siblings. The ghost material comes from `hologramMaterial` + `hologramMaterialPath`
  (`hologram.c:1554-1557`) plus the suffixes `_deployable.rvmat` / `_undeployable.rvmat` (`:14-16`); declare
  both keys or the hologram renders untextured.
- **A custom wall-placement hologram (modded `Hologram.UpdateHologram`) needs four things vanilla does not
  hand you.** (1) The wall normal: neither `RaycastRVProxy.dir` nor `RaycastRV.contactDir` is a face normal for
  object hits — both are the ray direction, so a yaw taken from them faces the camera and the ghost's box
  collides with the wall at any angle. Take it from `DayZPhysics.RayCastBullet` on
  `PhxInteractionLayers.BUILDING` and keep the fire-geometry ray for identity (`enforce-script-reference`
  SP-LFS-2). (2) The ground: pick the nearest support at or BELOW the aimed point (Y ≤ aimY + 2 mm); a ray
  started 2 m above the point selects sills, ledges and the floor above. (3) The collision box: lift its
  bottom 5 cm like `IsCollidingBBox` (`hologram.c:547,556`) or every building floor blocks placement, and trim
  the back so the support wall does not count. (4) One diagnostic line per cause bit (wall/ground/spacing/
  player/water/box), emitted on change and rate-limited, each line under 255 chars, with the unlifted box
  queried only when logging — that is what turned "the hologram is grey" into a named cause in one cycle.
  Origin: LFSecure, 2026-09-09, three in-game cycles and two Codex rounds
  (`LFSecure_dev/plans/2026-09-09-colocacion-fix-diag.md`); (1) shipped but not yet exercised in-game.

## PERSISTENCE — one synced bitmask is BOTH netsync AND save (data-critical)

Part-built state is NOT stored per part; it is packed into three 31-bit ints `m_SyncParts01/02/03`
(`basebuildingbase.c:12-14`), which serve as both the netsync representation and the persistence format.
Part `id` 1..31 → SyncParts01, 32..62 → SyncParts02, 63..93 → SyncParts03. On load,
`SetPartsFromSyncData` rebuilds each part's built flag from the bitmask and reconciles physics/visuals
(`SetPartFromSyncData` `:276-315`, which also failsafe-relocks attached materials against corrupted data).

**R9 gate:** any mod that adds parts, changes the bitmask packing or the `id` ranges, or touches
`OnStoreSave`/`OnStoreLoad` ordering is modifying player progression — a bug means lost bases after a
restart. Delegate to `rigorous-data-audit` (R9) BEFORE declaring release-safe. Full detail, the 93-part
cap, the version bumps (`GetDamageSystemVersionChange()→111`; Fence gate persistence bumped at v110) and
the hand-off checklist are in `references/persistence-audit.md`.
(since 1.30 Exp: `BaseBuildingBase` packing is unchanged. `Rebuilding` is a second, versioned stream on
map buildings — see `references/persistence-audit.md` §8 and `references/dayz-1-30-construction-rebuilding.md`.
`CombinationLock` on a Fence now also writes `m_CombinationInside` at vanilla stream **v143**
(`CombinationLock.c:128-136,169-177`) — a subclass `OnStoreLoad` that skips that branch desyncs the item.)

## QUICK TRIAGE

| Symptom | Likely cause | Where |
|---|---|---|
| **Base won't save / parts reset on server restart** | `OnStoreSave`/`OnStoreLoad` order broke, or a subclass wrote fields before `super` / in a different order | PERSISTENCE; `references/persistence-audit.md` |
| **A built part doesn't show (visual missing)** | `part_name` is not an AnimationSource in config or not a selection in the `.p3d` | PREFLIGHT show/hide; `dayz-animation-pipeline`, `dayz-model-pipeline` |
| **A built part has no collision** | missing per-part proxy memory/selection, or (base) missing `"Deployed"` proxy | `dayz-model-pipeline` (+ `dayz-p3d-audit`) |
| **Part state corrupts / two parts toggle together** | duplicate or out-of-range `id` in `Construction{}` (bitmask collision) | PREFLIGHT id≤93; `RegisterPartForSync` `basebuildingbase.c:148-175` |
| **Damage never destroys a part** | damage-zone name ≠ part name lowercased | PREFLIGHT zone==part; `basebuildingbase.c:507-517` |
| **The build action never appears** | tool's `build_action_type` doesn't AND-match the part's, or `CanBuildPart` fails (missing/ruined material, required part, conflict) | `construction.c:296-304, 959-1003` |
| **Dismantle is blocked** | the part `HasDependentPart` (something built depends on it) | `construction.c:479-496` |
| **"built but not shown until sync" in single-player** | `ConstructionPart.SetRequestBuiltState` skips the local set in SP and waits for sync | `constructionpart.c:56-63` |
| **Placement / hologram won't confirm** | height check or collision fails on the hologram | `actiondeployobject.c:42-75`; `references/entity-lifecycle.md` |
| **Perf hitch when building** | `UpdatePhysics()` is a "massive performance hit" per the code's own warning | `basebuildingbase.c:838` — avoid frequent calls |
| **Override of `BuildPartServer` never runs (1.30)** | vanilla actions now call `BuildPartServerEx` | `actionbuildpart.c:170`; `ConstructionBase.c:1688-1694` |
| **Compile error on `CreateCollisionTrigger` (1.30)** | methods still exist but are `[Obsolete("no replacement")]`; collision is `IsCollidingEx(CollisionCheckData)` | `ConstructionBase.c:1471,1742-1787` |
| **Rebuilt house / well part resets** | mixed up `BaseBuildingBase` 3-int save with `Rebuilding` 10-int `HandleStoreSave` | `Rebuilding.c:474-515`; `Building.c:23-45` |
| **Fence code lock ignored** | slot is `Att_CodeLock`; getter is `Fence.GetCodeLock()` | `fence.c:20,26,161-165` |

Do NOT build new features on `ActionPlugIntoFence` — it is DEPRECATED (`actionplugintofence.c:1`).

## DELEGATIONS

| Concern | Skill |
|---|---|
| `.p3d` selections / memory points / the `Deployed` proxy / LODs / missing-collision or action-target bugs | `dayz-model-pipeline` (+ `dayz-p3d-audit`) |
| config.cpp + Enforce script — RPC, sync vars, `OnStoreSave/Load`, `modded class`, side checks | `enforce-script-reference` |
| Persistence / bitmask packing / recovery paths (data-critical, id ranges, save ordering) | `rigorous-data-audit` (R9) |
| Show/hide a part (`SetAnimationPhase`), gate open/close, AnimationSources | `dayz-animation-pipeline` |
| Build / deploy / launch to test; smoke it in-game | `dayz-pbo-build` + `dayz-test-ingame` (+ `dayz-mcp-verify`) |
| Terrain holes, underground triggers, `disallowedTypesInUnderground`, bunkers under the terrain | `dayz-underground` |

## CITE-THEN-VERIFY

Base-building class and field names are easy to half-remember. Before writing a class name, base, config
field or named selection, grep vanilla (`P:\scripts\4_world\`, `DZ\gear\camping\config.cpp`) or the cited
reference. The `id`/damage-zone/selection invariants above corrupt data silently when wrong — verify them
against the real `.c` and `.p3d`, never from memory.

## REFERENCES

- `references/config-contract.md` — the `Construction{}` block, `Materials`, `GUIInventoryAttachmentsProps`,
  `attachments[]`/`hybridAttachments[]`/`mountables[]`, tool `build_action_type`, DamageZones↔part mapping,
  every field with its reader `path:line`.
- `references/entity-lifecycle.md` — the deploy→build→sync→persist→load call chain hop by hop with `path:line`
  (hologram, `OnPlacementComplete`, `OnPartBuiltServer`, `SetPartFromSyncData`, `AfterStoreLoad`), plus the
  action set and `AT_*` ints.
- `references/fence-gate-case.md` — the Fence worked example: gate state machine, open/close animation,
  combolock, barbed-wire area damage, and the v110 gate-persistence version bump.
- `references/persistence-audit.md` — the three-int bitmask packing, the 93-part cap, `OnStoreSave/Load`
  ordering, the version bumps, and the R9 hand-off checklist.
- `references/dayz-1-30-construction-rebuilding.md` — 1.30 Exp hierarchy (`ConstructionBasic` /
  `ConstructionBase` / `Rebuilding`), `ConstructionPartTypeData`, `*ServerEx` / `IsCollidingEx`,
  obsolete collision-trigger wrappers, brick/mortar/trowel loop, Fence `DigitalCodeLock`.

## Reglas promovidas del corpus de lecciones (added 2026-07-27)

Promovidas desde `AI/20_Knowledge/lessons-learned.md` para que lleguen por trigger en vez
de depender de que alguien recuerde buscarlas. Cada regla cita su `LL-NNN` de origen;
la entrada completa (síntoma, origen, evidencia) vive allí. No quites la cita: el índice
`lessons-index.md` detecta la promoción buscando esa referencia dentro de las skills.

- **LL-042** — Crea una clase de script homónima para cada clase config placeable y hereda del kit/static base que aporta `SetActions`, `IsDeployable` y el enlace kit↔static. Verifica ambas mitades antes de diagnosticar holograma o texturas.

## DayZ 1.30 Exp (build 1.30.164014)

Digest J (`work/out2/digest-J-construction-locks-bunker.md` §§1,3–5). Every class/method below was re-opened under `exp\scripts\scripts\`. Digest line numbers were often wrong; citations here are from the files.

### What changes

- **Hierarchy.** `EntityAI.CreateConstructionComponent()` (`EntityAI.c:3451`) returns null by default. `BaseBuildingBase` overrides it to `new Construction(this)` (`basebuildingbase.c:871-875`). `BuildingBase` overrides it to `new Rebuilding(this)` (`Building.c:23-26`). Field type on both is `protected ref ConstructionBasic m_Construction`.
- **Static vs instance.** `ConstructionPartTypeData` caches `Construction{}` on `EntityType` (`ConstructionPartTyped.c:2-67`). `ConstructionPart` keeps `m_PartTypeData`, `m_LocalSyncBitMask`, `m_IsBuilt` (`ConstructionPart.c:9-12`). The old multi-arg constructor is empty (`:14-16`); instances are `ToType().Spawn()` then `SetPartTypeData` (`ConstructionBase.c:514-520`).
- **`*ServerEx`.** `BuildPartServer` / `DismantlePartServer` / `IsColliding` are `[Obsolete]` wrappers on `ConstructionBase` (`:1688-1740`). Live path: `BuildPartServerEx` / `DismantlePartServerEx` / `IsCollidingEx(CollisionCheckData)` (`:174,185,1471`). Digest J's `IsCollidingEx(string, Object, bool, bool)` signature is **not** in the file.
- **Collision triggers.** `CreateCollisionTrigger` / `DestroyCollisionTrigger` / `IsTriggerColliding` are **not deleted**. They are `[Obsolete("no replacement")]` (`ConstructionBase.c:1742-1787`). Calling them still compiles; do not build new code on them.
- **`ConstructionActionData.SetSlotId` / `GetSlotId`.** Not deleted. `[Obsolete("1.30: Unsafe, overridden ActionData used in-system instead")]` (`constructionactiondata.c:617-627`).
- **Rebuilding (map buildings, not player fences).** `BuildingBase` registers `m_Construction.m_SyncParts1`..`10` (`Building.c:29-45`). Packing: `BIT_INT_SIZE = 32` (`BitArray.c:4`) × 10 ints / `BITWISE_SYNCINFO_SIZE_BASE = 2` (`ConstructionPart.c:6`) = **160 part ids**. Persist via `HandleStoreSave` → `SerializeConstructionData` (`Rebuilding.c:474-515`). Default build mask sets bit 0; `ConstructionPartRebuild` also stores facing in bit 1 (`:985-991`). Digest J's 00/01/10 "ruined" table was **not** found in those methods.
- **Masonry loop.** `PileOfBricks` + `ActionPickUpBricks.YIELD = 3` (`ActionPickUpBricks.c:16-18`). `MortarMix` mixes at water/well (`MortarMix.c:6-7`) into `MortarMix_Opened`. `BrickTrowel` adds `ActionBuildPart` (`BrickTrowel.c:1-7`); build anim `CMD_ACTIONFB_BRICKTROWEL` (`actionbuildpart.c:260-262`). Tool mask enum `TOOL_BRICKLAYING = 256` (`ConstructionConstants.c:25`). `[UNVERIFIED]` `CfgVehicles BrickTrowel build_action_type` — class not in extracted configs.
- **Fence locks.** `Fence` has `ATTACHMENT_CODE_LOCK = "Att_CodeLock"` and `GetCodeLock()` (`fence.c:20,26,161-165`) beside the existing combination lock. Dialing a combo lock no longer unlocks it: `ActionCombinationLockUnlock` (`CombinationLock.c:686`).
- **Material enum moved.** `ConstructionMaterialType` now lives on `ConstructionBase.c:2-12` and adds `MATERIAL_BRICK = 6`, `MATERIAL_RUBBLE = 7`.
- **`disableSimulation`.** `[CHANGELOG]` house entities may set `disableSimulation` to skip ticking (`changelog-1.30-exp-modding.md:13`; native `Entity.c:3-6`). Not a `BaseBuildingBase` field.
- **Activation.** Any `CfgVehicles` class with a `Construction` subclass gets the component at init (`EntityAI.c:248-249`). Rebuilding parts read new keys: per-part decay (`can_part_decay`, `part_decay_threshold`, `part_decay_rate`, global `disableBaseDecay`), `StaticsSupportData`, `EffectsData`, `custom_part_type`, `skipOnRepair`/`skipOnDismantle`. Table with readers: `references/dayz-1-30-construction-rebuilding.md` §9.2.
- **Rebuildable map buildings are scripts only in 1.30 Exp.** The Nasdara houses and `Land_IrrigationTunnel_Entrance_01` have script classes but no configs or models in the Exp install (§9.4). Terrain holes and underground areas: `dayz-underground`.

### What breaks (1.29 mods)

1. Override of `BuildPartServer` / `DismantlePartServer` is skipped if vanilla calls `*Ex`. Migrate the override.
2. New code that called `CreateCollisionTrigger` still compiles but is obsolete with **no replacement** — use `IsCollidingEx(CollisionCheckData)` (`ConstructionBase.c:1471,1896-1910`).
3. Direct typed access to `m_Construction` as `Construction` fails: field is `ConstructionBasic` and `protected`. Use `GetConstruction()` or `GetConstructionBasic()`.
4. Instantiating `ConstructionPart` with the old constructor does not fill type data. Spawn + `SetPartTypeData`.
5. Fence combo-lock automation that assumed "last dial = unlocked" needs `ActionCombinationLockUnlock`.
6. Custom `CombinationLock.OnStoreLoad` must read `m_CombinationInside` when `version >= 143`.

### Migration checklist

- [ ] Replace overrides of `BuildPartServer` / `DismantlePartServer` / `IsColliding` with `*Ex`.
- [ ] Stop using construction-box triggers; build `CollisionCheckData` and call `IsCollidingEx`.
- [ ] Access construction via `GetConstruction()` / `GetConstructionBasic()`, never the raw field from outside.
- [ ] Keep `BaseBuildingBase` `id` in 1..93 and the `OnStoreSave` order `01,02,03,m_HasBase`.
- [ ] Do not write Rebuilding's 10-int stream into a `BaseBuildingBase` subclass.
- [ ] If attaching a code lock to a Fence, use slot `Att_CodeLock` and `DigitalCodeLock`.
- [ ] If subclassing `CombinationLock`, handle stream v143.
- [ ] R9-audit any bitmask / `OnStoreSave` change (`references/persistence-audit.md`).

### Detail

`references/dayz-1-30-construction-rebuilding.md` (EXACT blocks), `references/persistence-audit.md` §8, `references/config-contract.md` §8, `references/entity-lifecycle.md` §2/§4, `references/fence-gate-case.md` §6.
