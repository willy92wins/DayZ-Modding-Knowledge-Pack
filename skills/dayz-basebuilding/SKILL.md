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

## THE MODEL — kit → deploy → build → upgrade → dismantle

The four-class quartet and who owns what:

| Class | Role | Where |
|---|---|---|
| `BaseBuildingBase: ItemBase` | the persisted world entity; owns one `ref Construction`, the sync ints, events, physics, area damage | `basebuildingbase.c:2` |
| `Construction` | per-instance controller; holds `map<string, ref ConstructionPart>` keyed by part config-class name; does ALL config lookups live | `construction.c:11` |
| `ConstructionPart` | runtime record of one part (name, `m_Id` bit index, built/base/gate flags, required parts) | `constructionpart.c:1` |
| `ConstructionActionData` | per-player scratch state on `PlayerBase`; caches which parts are buildable under the cursor, drives radial action variants | `constructionactiondata.c:1` |

`Construction` is NOT itself persisted — it is rebuilt from config on every load and its part states are
restored from the sync bitmask (see PERSISTENCE). End-to-end flow:

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
5. **Upgrade** = building further parts whose `required_parts[]` are satisfied (`HasRequiredPart`
   `construction.c:412-435`) and whose `conflicted_parts[]` are not built (`HasConflictPart` `:438-455`).
6. **Dismantle.** `ActionDismantlePart` (`actiondismantlepart.c:26`) → `DismantlePartServer` (`:98-118`)
   refunds materials. Blocked if the part `HasDependentPart` (`construction.c:479-496`). Dismantling the
   **base** part destroys the whole construction (`basebuildingbase.c:653-657`).
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

Do NOT build new features on `ActionPlugIntoFence` — it is DEPRECATED (`actionplugintofence.c:1`).

## DELEGATIONS

| Concern | Skill |
|---|---|
| `.p3d` selections / memory points / the `Deployed` proxy / LODs / missing-collision or action-target bugs | `dayz-model-pipeline` (+ `dayz-p3d-audit`) |
| config.cpp + Enforce script — RPC, sync vars, `OnStoreSave/Load`, `modded class`, side checks | `enforce-script-reference` |
| Persistence / bitmask packing / recovery paths (data-critical, id ranges, save ordering) | `rigorous-data-audit` (R9) |
| Show/hide a part (`SetAnimationPhase`), gate open/close, AnimationSources | `dayz-animation-pipeline` |
| Build / deploy / launch to test; smoke it in-game | `dayz-pbo-build` + `dayz-test-ingame` (+ `dayz-mcp-verify`) |

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
