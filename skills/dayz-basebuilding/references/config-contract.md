# Config contract — declaring a buildable BaseBuildingBase entity

Authored 2026-07-07 (F4) from vanilla P:\scripts — see citations.

Every field below is read live at runtime by `construction.c` / `basebuildingbase.c` via `g_Game.ConfigGet*`
— nothing is precomputed. Roots: `P:\scripts\` = `<dayz-projects>\scripts\`;
config root `DZ\gear\camping\config.cpp`. Line numbers are for the Fence entity unless noted.
(until 1.29: that live-on-instance read). (since 1.30 Exp: `ConstructionPartTypeData.InitPartTypeData` caches
the same `g_Game.ConfigGet*` keys once per `EntityType` (`ConstructionPartTyped.c:42-67`); instances only
hold `m_PartTypeData` + built/sync state. Field names in the `Construction{}` block did not change.)

## 1. The entity class

Base class (`config.cpp:25`):

```cpp
class BaseBuildingBase: Inventory_Base { weight=100000; itemSize[]={50,50}; disallowSwapCollisions="true"; };
```

A concrete entity, e.g. `class Fence: BaseBuildingBase` (`config.cpp:3252-3282`):

- `scope=2; model="\DZ\gear\camping\fence.p3d"; carveNavmesh=1; physLayer="item_large";`
- `createProxyPhysicsOnInit="false";` + `createdProxiesOnInit[]={"Deployed"};` — the `Deployed` proxy is
  the base collision, toggled by animation (see §5 of the SKILL and `entity-lifecycle.md`).

## 2. Attachment / material slots on the entity class

| Field | Meaning | Reader |
|---|---|---|
| `attachments[]` | every material and attachment slot the entity accepts | `GetAttachmentSlots()` reads `CfgVehicles <type> attachments` — `basebuildingbase.c:940-947`; declared `config.cpp:4362-4373` |
| `hybridAttachments[]` | attachments whose health mirrors a damage zone of the same name | `CheckForHybridAttachments` `basebuildingbase.c:1226-1236`; read in ctor `:54-58`; declared `config.cpp:3270` |
| `mountables[]` | attachments that get proxy physics toggled (barbed wire) | read in ctor `:59-63`; `UpdateAttachmentPhysics` early-returns if a slot is NOT in `mountables` `:878-879`; declared `config.cpp:3277` |

## 3. The `Construction{}` block field-by-field

Two-level nesting: `Construction { class <main_part> { class <part> {...} } }`. Example
`Construction > wall > base` (`config.cpp:4527-4551`) and `wall > wall_base_down` (`:4553-4585`).

| Field | Type / meaning | Reader `path:line` |
|---|---|---|
| `name` | localized display name (`$STR_...`) | `UpdateConstructionParts` `construction.c:256-264` |
| `id` | UNIQUE sync/persistence bit index, 1..93 | same reader; used by `RegisterPartForSync` `basebuildingbase.c:148-175` |
| `is_base` | 1 = foundation part; dismantling it destroys the whole entity | `construction.c:256-264`; destroy path `basebuildingbase.c:653-657` |
| `is_gate` | 1 = this part is a gate (Fence) | `construction.c:256-264` |
| `show_on_init` | read by the reader, but `[UNVERIFIED]` — no runtime effect was observed in the traced show/hide paths (parts show via sync) | `construction.c:256-264` |
| `required_parts[]` | parts that must be built first | `HasRequiredPart` `construction.c:415-418, 546-553` |
| `conflicted_parts[]` | parts that block this one if already built | `HasConflictPart` `construction.c:441-443` |
| `collision_data[]` | two memory-point names `{min, max}` for the build collision box | `construction.c:1128-1141` |
| `build_action_type` | bitmask AND-matched against the tool's own `build_action_type` | `construction.c:959, 966-1003` |
| `dismantle_action_type` | same, for dismantle | `construction.c:989` |
| `material_type` | `ConstructionMaterialType` enum — drives build/dismantle SFX | `construction.c:1005-1015`; enum `construction.c:1-9` |

### `ConstructionMaterialType` enum (`construction.c:1-9`)

`NONE=0`, `LOG=1`, `WOOD=2`, `STAIRS=3`, `METAL=4`, `WIRE=5`. Selects the build/dismantle sound set.
(until 1.29: enum on `construction.c:1-9` with those five values). (since 1.30 Exp: enum moved to
`ConstructionBase.c:2-12` as `MATERIAL_NONE`..`MATERIAL_WIRE` plus `MATERIAL_BRICK = 6` and
`MATERIAL_RUBBLE = 7`. SFX switch on `BaseBuildingBase` still only handles log/wood/stairs/metal/wire
(`basebuildingbase.c:1089-1101`).)

### `Materials` sub-block

Each `Material1..N` child under a part (`construction.c:632-693, 758-766`):

| Field | Meaning |
|---|---|
| `type` | item classname — used when refunding piles on dismantle |
| `slot_name` | attachment slot the material sits in; `HasMaterials` requires the attachment here with `GetQuantity() >= quantity` (`construction.c:617-655`) |
| `quantity` | amount consumed; `-1` = delete the whole object; `0` = ignore quantity |
| `lockable` | `1` = lock the material in its slot (stays attached, visually part of the wall) instead of consuming it (`TakeMaterialsServer` `construction.c:671-723`) |

If the `Materials` block is absent, `HasMaterials` returns true (no material required).

## 4. `GUIInventoryAttachmentsProps` (`config.cpp:4374-4415`)

Groups attachment slots into inventory categories (Base / Attachments / Material). Each child has
`attachmentSlots[]`, `selection` (the model selection the category maps to), `icon`, `name`. Read by
`GetAttachmentSlotFromSelection` / `GetAttachmentsFromSelection` (`constructionactiondata.c:250-336`) to
resolve which slot an attach action targets, and by `DropNonUsableMaterialsServer` via `platform_support`
(`construction.c:788-908`).

## 5. Tool contract

A tool participates by declaring `build_action_type` / `dismantle_action_type` in its own CfgVehicles
entry (`construction.c:966, 989`). Build is allowed when `(part_type & tool_type) > 0`. Shovel / Pickaxe /
Pliers / SledgeHammer also switch the player animation command (`actionbuildpart.c:161-181`).
(since 1.30 Exp: part masks are `EConstructionTools` including `TOOL_BRICKLAYING = 256`
(`ConstructionConstants.c:13-26`). `BrickTrowel` uses `CMD_ACTIONFB_BRICKTROWEL` (`actionbuildpart.c:260-262`).
Readers: `ConstructionPartTypeData.InitActionMasks` (`ConstructionPartTyped.c:92-104`) and
`ConstructionBase` tool cfg path `cfgVehicles <type> build_action_type` (`ConstructionBase.c:1407-1413`).)

## 6. DamageZones ↔ part mapping

The entity's `class DamageSystem { class GlobalHealth ...; class DamageZones {...} }` (`config.cpp:3283+`).
**Damage-zone names MUST match part names lowercased** — `EEHealthLevelChanged` lowercases the zone name and
looks up the part by it (`basebuildingbase.c:507-517`). A zone whose name does not match a part will not
trigger that part's destruction on ruin.

## 7. What the readers verify (cross-check before shipping)

- Base uses the `"Deployed"` proxy; every other part uses a per-part proxy via `AddProxyPhysics(part_name)`
  (`construction.c:591-599`). Missing memory point / selection → no collision on that part.
- `show/hide` a part = `SetAnimationPhase(part_name, 0/1)` (`construction.c:578-588`, phase 0 = visible).
  Every `part_name` must be an AnimationSource in config AND a selection in the `.p3d`.

## 8. DayZ 1.30 Exp — type cache, `IsCollidingEx`, obsolete trigger API

Digest J §3 told this file to "purge" `CreateCollisionTrigger` / `DestroyCollisionTrigger` / `IsTriggerColliding`.
Those names were **not** in this 1.29 reference. In 1.30 they still exist on `ConstructionBase`, tagged
`[Obsolete("no replacement")]` (`ConstructionBase.c:1742-1787`). Do not call them from new code.

Collision for a build now goes through `IsCollidingEx(CollisionCheckData)` (`ConstructionBase.c:1471`).
Fill `m_PartName` and optional `m_AdditionalExcludes` (vanilla inserts the player — `actionbuildpart.c:157-160`).

Config field readers moved:

| Field | 1.29 reader (kept as map) | 1.30 Exp reader (verified) |
|---|---|---|
| `name` / `id` / `is_base` / `is_gate` | `UpdateConstructionParts` `construction.c:256-264` | `ConstructionPartTypeData.InitBasicStrings` `ConstructionPartTyped.c:72-83` |
| `required_parts[]` | `HasRequiredPart` `construction.c:415-418` | still `HasRequiredPart` but on `ConstructionBase.c:668`; data from `InitRequiredParts` `:85-90` |
| `conflicted_parts[]` | `HasConflictPart` `construction.c:441-443` | `ConstructionBase.c:690`; data from `InitConflictedParts` |
| `build_action_type` | `construction.c:959, 966-1003` | `InitActionMasks` `ConstructionPartTyped.c:92-104` |
| `Materials` | `construction.c:632-693` | `InitPartMaterials` `ConstructionPartTyped.c:106+` |

`UpdateConstructionParts` on `ConstructionBase.c:495-532` no longer walks config children; it iterates
`ConstructionDataTypeHolder.GetConstructionPartTypeDataArray()` (`ConstructionPartTypedHolder.c:8-58`).

New optional config keys consumed by type data (rebuild-oriented, unused by vanilla Fence): `custom_part_type`,
`StaticsSupportData`, `can_decay` / `can_decay_general` (`ConstructionPartTyped.c:32-66`). [DESIGN] A player
`BaseBuildingBase` can ignore those unless you are authoring a rebuildable `BuildingBase`.
