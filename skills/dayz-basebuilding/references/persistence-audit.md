# Persistence audit — the synced bitmask (data-critical, R9)

Authored 2026-07-07 (F4) from vanilla P:\scripts — see citations.

**R9 gate.** Any mod that adds parts, changes the bitmask packing or the `id` ranges, or touches
`OnStoreSave`/`OnStoreLoad` ordering is modifying player progression — a bug here means players lose their
bases after a server restart. Invoke `rigorous-data-audit` (R9) BEFORE declaring release-safe. This file is
the hand-off checklist. Roots: `P:\scripts\` = `<dayz-projects>\scripts\`.

## 1. The representation — three 31-bit ints, netsync AND save at once

Part-built state is NOT stored per part. It is packed into three sync ints `m_SyncParts01/02/03`
(`basebuildingbase.c:12-14`), registered for netsync in the ctor (`:44-46`). This SAME representation is both
the network sync AND the persistence format — there is no separate per-part save record.

Part `id` → bit:

- `id` 1..31  → `m_SyncParts01`
- `id` 32..62 → `m_SyncParts02`
- `id` 63..93 → `m_SyncParts03`

Bit ops in `RegisterPartForSync` (`basebuildingbase.c:148-175`). Also `m_InteractedPartId` /
`m_PerformedActionId` (`:15-16`, registered `:47-48`) sync the last action so clients play the right SFX
(`SetActionFromSyncData` `:259-273`).

## 2. The 93-part cap

Three ints × 31 usable bits = **93 distinct parts maximum per BaseBuildingBase entity**. Every part's `id`
MUST be unique and in 1..93 across the whole `Construction{}` block. A duplicate id makes two parts share a
bit (they toggle together); an out-of-range id writes outside the three ints (silent corruption). There is
no runtime warning — verify by hand or with a script that every `id` in the config is unique and ≤93.

## 3. OnStoreSave / OnStoreLoad — strict ordering

- `OnStoreSave` (`basebuildingbase.c:420-430`): writes `m_SyncParts01`, `02`, `03`, then `m_HasBase`.
- `OnStoreLoad` (`:432-464`): reads the three ints then `m_HasBase`, each guarded with a `return false` on
  read failure (default-then-abort).

**Subclass-after-super invariant:** a subclass writes/reads its extra fields AFTER calling `super`, in the
exact same order in both methods. Fence appends `m_GateState`, `m_IsOpened` after the base three ints
(`fence.c:212-220` save / `:222-255` load). Reorder either side, or write in the subclass before `super`, and
every saved base corrupts on the next load.

## 4. Load reconciliation

- `AfterStoreLoad` (`:466-474`) → `SetPartsAfterStoreLoad()` (`:476-487`) → `SetPartsFromSyncData()`: rebuilds
  each part's built flag from the bitmask, sets base state from the base part, re-syncs.
- Guarded by `m_FixDamageSystemInit` — the damage-system migration path uses `EEOnAfterLoad` + a 500ms
  deferred call instead (`:530-538`).
- `SetPartFromSyncData` (`:276-315`) is the core: per part, compares "built in sync bitmask" vs "built flag",
  adds/removes constructed parts, shows/hides physics, toggles the `Deployed` proxy for the base, and
  **failsafe-relocks attached materials** (`:314`, "failsafe for corrupted sync/storage data").

## 5. Version bumps

- Base damage-system version: `GetDamageSystemVersionChange()→111` (`basebuildingbase.c:1238-1241`).
- Fence gate persistence bumped at **v110** — `Fence.OnStoreLoad` reads a discarded bool for `version < 110`,
  then the gate fields for current versions (`fence.c:222-255`).

When you add a persisted field, bump the version and add a legacy read branch so old saves load with the old
layout and new saves with the new one.

## 6. R9 hand-off checklist

Before declaring a base-building persistence change release-safe, confirm with `rigorous-data-audit`:

1. Every part `id` in the `Construction{}` block is unique and in 1..93.
2. `OnStoreSave` and `OnStoreLoad` write and read the same fields in the same order.
3. Every subclass writes/reads its fields AFTER `super`, same order both ways.
4. A new persisted field bumps the version and adds a legacy branch for old saves.
5. Crash-recovery walk: kill the server between each I/O hop of save/load — does the next boot recover the
   base or lose parts? (R8 mental walk.)
6. The failsafe relock path (`SetPartFromSyncData:314`) still runs for corrupted sync/storage data.
7. In-game gate: build parts, restart the server, confirm every part and the base survive (not just an
   offline audit — the R9 case history shows bases-lost bugs that only surface on a real restart).

## 7. Out of scope for this pass

`[UNVERIFIED]` `TerritoryFlag: BaseBuildingBase` exists at `config.cpp:12387` and `staticflagpole.c`
references `AddRefresherTime01` / `AnimateFlagEx`, but the territory system (radius, decay, flag-refresher
mechanics) was not opened here — do not assume its persistence follows the same bitmask model without
tracing it. `[UNVERIFIED]` the `show_on_init` config field is read by `UpdateConstructionParts` but had no
observed runtime effect in the traced show/hide paths.
