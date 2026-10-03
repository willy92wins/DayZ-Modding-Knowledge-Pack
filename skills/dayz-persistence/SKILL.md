---
name: dayz-persistence
description: Use when designing, implementing, debugging, or auditing DayZ persistence — OnStoreSave/OnStoreLoad entity streams, CF ModStorage and storageVersion, persistent-format migration or rollback, sidecar JSON, recoverable file replacement or atomic-save claims, player-data corruption after save or restart, and placed objects that vanish after a restart (central-economy lifetime, types.xml entries). Invoke for deprecated JSON loading APIs, future or truncated versions, uninstall-safe mod data, CombinationLock stream v143, code lock, ThermalBiasHandler, GAME_STORAGE_VERSION, and BunkerBroadcastPersistenceStorage.bin.
---

# DayZ Persistence

## Router: choose one contract first

Answer all four questions before choosing a mechanism. Each matching rule adds a
candidate; exactly one candidate is required. Zero or multiple candidates return
`needs_clarification`. Never resolve conflicting signals by silently preferring a
contract.

| Observable input | Candidate |
|---|---|
| Data is not attached to an entity, or an administrator must inspect or repair it outside the game | Sidecar file |
| The mod does not own the entity, or the data must survive uninstall and reinstall | CF ModStorage |
| Data is attached to an entity the mod owns, need not survive uninstall, and need not be inspected outside the game | Vanilla entity stream |

This is a routing decision, not a ranking. For example, data outside an entity
that must also survive uninstall matches two rules and needs clarification about
ownership and the required recovery surface.

## Contract 1: vanilla entity stream

Use the stream for data owned by the entity's own mod when uninstall survival is
not required. `EntityAI.OnStoreSave(ParamsWriteContext)` and
`EntityAI.OnStoreLoad(ParamsReadContext, int)` are the hooks
(`VANILLA/3_game/entities/entityai.c:2925`; `VANILLA/3_game/entities/entityai.c:2989`). Save and load fields in the same
order and type, propagate `super`, stage reads, and return `false` on any failed
`ctx.Read`; partial state is never valid
(`VANILLA/3_game/entities/entityai.c:2969-2985`).

The hook version is the DayZ build from `g_Game.SaveVersion()`, not the mod's
schema version (`VANILLA/3_game/global/game.c:434`). The base stream has variable
width: the optional energy component writes nine fields or none, so a fixed
offset after `super` is a latent alignment bug
(`VANILLA/3_game/entities/entityai.c:2928-2959`). If the mod is removed, no
remaining code re-emits its appended bytes.
(hasta 1.29: that EntityAI prefix was energy-or-nothing plus `SaveVariables`;
`GAME_STORAGE_VERSION` was 142.)
(desde 1.30 Exp: energy is still optional, but `HandleStoreSave` runs first and
`PlayerBase` appends `ThermalBiasHandler` with no version gate. See
[references/dayz-1-30-persistence.md](references/dayz-1-30-persistence.md).)

Read the complete contract in
[references/vanilla-stream.md](references/vanilla-stream.md).

## Contract 2: CF ModStorage

Use CF ModStorage for data attached to another mod's entity or data that must
survive uninstall and reinstall. CF frames a framework version, a mod count, and
one stream per mod
(`CF_ROOT/ModStorage/CF_ModStorageObject.c:46,62,64-71`). Its version unit is the
mod: `CfgMods storageVersion` feeds `GetStorageVersion()`, then
`CF_ModStorage.GetVersion()`
(`CF_ROOT/Mods/ModStructure.c:61-63,307`;
`CF_ROOT/ModStorage/CF_ModStorage.c:274`; `CF_ROOT/ModStorage/CF_ModStorage.c:41-44`).

CF's differential property is byte-preserving re-emission of data for an
unloaded mod (`CF_ROOT/ModStorage/CF_ModStorageObject.c:73-77`). It does not
define the payload's migrations, validate the mod's staged state, provide
administrator-editable files, or make file replacement atomic.

Read the complete contract in
[references/cf-modstorage.md](references/cf-modstorage.md).

## Contract 3: sidecar files

Use a sidecar when data is not entity-owned or must be inspected and repaired
outside the game. The file owns its version header. Prefer
`JsonFileLoader<T>.LoadFile(string, out T, out string)` and check both its `bool`
return and `errorMessage`
(`VANILLA/3_game/tools/jsonfileloader.c:7-40`); `JsonLoadFile` is deprecated and
has no return channel (`VANILLA/3_game/tools/jsonfileloader.c:99-131`).

DayZ exposes `DeleteFile` and `CopyFile`, but no rename or move primitive
(`VANILLA/1_core/proto/ensystem.c:528,531`;
`VANILLA/1_core/proto/ensystem.c`). Therefore temp -> verify -> replace is not
atomic. The real replace deletes the destination and then copies the verified
temporary file, leaving a window in which the destination does not exist.
Back up before that window, verify after the copy, and retain the completed
`.tmp` until post-copy verification succeeds.

Read the full flow and all nine I/O boundaries in
[references/sidecar-files.md](references/sidecar-files.md).

### Restore order: build what stored entities rest on inside `OnMissionStart` (added 2026-10-03, measured in game, DayZDiag 1.29.163709)

[EXACT][CLAIM-PERS-RESTORE-BEFORE-STORED] A mod rebuilt its placed structures from a
sidecar with a `CallLater` of 2 s from `MissionServer.OnMissionStart`, and each
structure created its floor and platform parts 0.5 s after its own `EEInit`. A
helicopter (a `CarScript` kept by the game's own storage) parked on one structure's
lowered platform came back after an orderly restart before those parts existed: its
`EEInit` print, at the parked height (y 14.13), came before the parts line in the
server script log, and it fell 6.9 m to the terrain and lay rolled -54.3°. With the
restore called directly in `OnMissionStart` and the parts created in that call, the
parts line came before the helicopter's `EEInit` after two orderly restarts, and the
helicopter stayed where it was parked (0.010 and 0.014 mm from its parked height,
level within 0.07°) and later rose with the platform. The 2 s pass was kept to bind
what already exists and created nothing twice. The builds before and after differed in
other ways too; what ties the fall to the timing is the order of those two log lines.
This matches `enforce-script-reference` SP-LFS-3: stored entities are created after
`OnMissionStart` returns. Rule: a structure the mod rebuilds from its own sidecar, if
stored entities can rest on it (a floor, a platform, a hangar), is created
synchronously in `OnMissionStart`, as long as nothing it needs comes from the game's
storage, which loads later; a later pass may only bind, idempotently. Not measured: a
crash restart, stored entities other than this one vehicle, and freezing the vehicles
until the structure exists, the alternative the project did not take.

## Migration gate

Any format change must classify fresh, legacy, known, future, truncated,
same-build/new-mod-version, and old-reader rollback inputs. Each result declares
verdict, bytes consumed, preserved state, and action. Rejecting a record is
read-only. Run a mutation check; a perfect `0.000` result against an unmodified
fixture is suspicious, not evidence.

Use [references/migration-matrix.md](references/migration-matrix.md) as the
normative table.

### Declarative existence is part of compatibility (LL-268)

A persistence-compatibility audit is incomplete if it only compares
`OnStoreSave`/`OnStoreLoad` streams or script fields. Compare the declarative identity that
decides whether the entity can still exist: classname, declared parent, `scope`, and
membership in `CfgPatches.units[]`. A byte-identical stream cannot preserve an entity the
engine no longer instantiates.

Diff the authoritative deployed configuration against both the prior release and the current
source. If `config.bin` and `config.cpp` coexist, derapify and audit the `config.bin` from
the PBO the engine consumes; resolve any date or content divergence before release. Several
script-only audits are not independent confirmation when they share this same blind spot.

### Storage-copy census: without the CE anchor files nothing loads (SP-399, added 2026-09-14, measured in game, DayZDiag 1.29.163709)

[EXACT] A copy of `storage_1` carrying only `animals.bin`, `building.*` and `dynamic_*` (without `types.*`, `events.*`, `vehicles.*`, `zombies.bin`) loads NOTHING: the RPT reports every file `ver:0 stamp:0, valid:NO` — even files that are present — and ends with `[CE][Hive] :: Empty storage folder, reinitializing ...`; zero items restored, zero mod load lines. The `dynamic_000.bin` header bytes match a working world's, so it is not corruption: the CE files anchor the stamp that validates the rest. Control on the same machine, full world: `dynamic_000.bin ... valid:yes` and `Restoring file ... 812 items.`

Rules: (1) before censusing a storage copy, check that `data/` brings `types.bin` and `events.bin` with their generations besides the `dynamic_*`; (2) a boot census counts only if the RPT shows `Restoring file ... N items` with N > 0 — without that signal a zero count of load lines is vacuous, not "zero"; (3) do not count entities by grepping class names in the `.bin` files — the byte-grep returns 0 even in a world that contains them.

### A class with no `types.xml` entry lives 30 to 60 minutes of server time (SP-459, added 2026-10-04, measured in game, DayZDiag 1.29.163709)

[EXACT][CLAIM-PERS-CE-DEFAULT-LIFETIME] The central economy keeps a lifetime, in seconds, on every
entity it persists: `GetLifetime`/`SetLifetime` read and set what remains, `GetLifetimeMax`/`SetLifetimeMax`
the maximum (`VANILLA/3_game/entities/entityai.c:3378-3387`), and `GetEconomyProfile` returns the class's
economy profile (`VANILLA/3_game/entities/entityai.c:883`). A probe in the LFPowerGrid mod logged them for
classes that have no entry in any `types.xml`:

- the profile's lifetime and `GetLifetimeMax()` are both 1800;
- a new entity starts above that: 1857.19 and 2883.18 (six creations, with and without an entry, started at
  1.03 to 1.98 times `lifeMax`);
- the lifetime falls in real time with a player 10 m away (49 s in 49 s): being near does not pause it;
- a restart saves and restores what remains (1808.19 before, 1783.69 after), and server downtime does not count;
- in `EEInit` of a restored entity `GetLifetime()` is 0: the stored value is not loaded yet;
- restored entities whose lifetime had run out are deleted during startup, before any player connects: four
  `delete ... life=-1 lifeMax=1800` lines come before the first `EOnClientPrepare`.

So an object placed from a class without an entry runs out 30 to 60 minutes of server time after it is created,
and the next restart deletes it. While the server runs, the economy's cleanup is expected to delete it once no
player is within `CleanupAvoidance` (100 m in the mission's `db/globals.xml`); this probe did not measure that. A
persistence test with objects younger than that proves nothing. Not shown: that 1800 is a fixed engine value, and
a dedicated server.

[EXACT][CLAIM-PERS-CE-ENTRY-LATE] Adding the entry (lifetime 3888000) to a world that already holds such objects:

- new entities start at 5.02e6 and 6.68e6;
- existing ones take the new `lifeMax` but keep what remained of their short lifetime (created at 2059.67 and
  2124.49 without the entry, 2008.97 and 2073.79 after the restart with it);
- restored entities that had run out are deleted at startup anyway;
- removing the entry from the XML after it has loaded changes nothing: new entities still start at 4.63e6 and
  7.72e6, and that run restores the types from the storage's `types.bin`.

Rule: ship every class that a player places, or that otherwise persists in the world, in the mod's own
`types.xml` with an explicit lifetime (3888000 for placed structures, as vanilla gives `Fence` and `Watchtower`
in Chernarus' `db/types.xml`), and check the file mechanically against the public classes of `config.cpp`. A
server that installs the file late keeps its existing objects on the short lifetime: tell admins to dismantle
them and place them again after the restart. A territory flag might also rescue them: its refresh calls
`GetCEApi().RadiusLifetimeReset` (`VANILLA/4_world/entities/itembase/basebuildingbase/totem.c:168` and `:207`),
documented as a reset "to default value from DB within radius" (`VANILLA/3_game/ce/centraleconomy.c:562-569`),
which with the entry is 3888000. Read in the code, not measured.

[EXACT][CLAIM-PERS-CE-UNTAGGED-LOOT] An entry with `nominal` above 0 and no `category`, `usage` or `value` tags
still spawns as loot. On a fresh storage (`Empty storage folder, reinitializing`) with `log_ce_lootspawn` on, the
economy placed 202 of the mod's objects (kits, items and generators) across the map in its first pass. The RPT's
`Adding <class> at [x,z]` lines also record what a script creates: nine more lines were the test scene. Tags
restrict where an entry spawns; they are not needed for it to spawn.

### `OnStoreLoad` returning false keeps the entity (SP-460, added 2026-10-04, measured in game, DayZDiag 1.29.163709)

[EXACT][CLAIM-PERS-ONSTORELOAD-FALSE-KEEPS] When an entity's `OnStoreLoad`
(`VANILLA/3_game/entities/entityai.c:2989`) returns false, the engine does not delete the entity. The RPT prints
`!!! Scripted variables corrupted upon "<class>"` with `Reason: [EntityAI::OnStoreLoad] :: [WARNING]`, and the
entity stays in the world with its script variables at their defaults, except what the load had already assigned
before it returned. Measured with three batteries of the LFPowerGrid mod whose load read their wires and then
rejected the battery's own record as an old version: all three stayed, with their wires (the generator kept its
four outputs and each lamp its input), and their stored energy started at 0 (about 90 s later they read 116, 116
and 182, from charging). The same RPT line is the one listed for a save and load order mismatch
(`enforce-script-reference/references/pitfalls-advanced.md`), so the line alone does not tell a deliberate
rejection from a desync.

- A version rejection in `OnStoreLoad` loses the script state, not the entity. To remove the entity, delete it
  explicitly. An audit that writes "the entity is discarded" has to measure it.
- Not measured: the next save. The entity is still in the world, so expect it to be saved again with the state it
  holds, which would replace the rejected record. Until that is measured, do not count on `return false` to keep
  the original bytes (the read-only rejection of the migration gate above).

## Hard stops

Stop and resolve the violation before recommending or shipping persistence work:

1. An API, method, hook, field, or signature is written without a verified
   `path:line`.
2. A persistent-format change omits legacy behavior or old-reader rollback
   behavior. Present an equivalent no-format-change alternative first when one
   exists.
3. A migration auto-saves rewritten data without a backup and verification.
4. A future version is accepted silently instead of rejected read-only with a
   rate-limited diagnostic.
5. A failed `ctx.Read` leaves partially applied state that is treated as valid.
6. A test covers only the happy path; future, truncated, rollback, and injected
   I/O failures remain unexercised.
7. Promotion reports `PROMOTION-UNROUTED` or `PROMOTION-DRIFT`.
8. Live `CargoBase` is walked by frozen index across ticks while items can be removed mid-walk (SP-418).
9. An entry of the mod's own registry of world entities is removed by proximity, bound on
   restore to an entity that does not carry its id, or given a new entity while one it already
   had may still live; no rule for that restore has come out of review sound (SP-456).

### Live cargo capture across ticks (SP-418, added 2026-09-21, measured in game, DayZ 1.30.164014 Exp)

[EXACT] `GetItemCount()` is frozen when the capture begins; a batched walk over `cargo.GetItem(i)` silently loses items if the player removes one mid-capture: the cargo compacts, the shifted item lands on an already-visited index, never enters the snapshot, and a later `ClearPhantomItems` destroys it unwritten. The guard `i < GetItemCount()` hides the out-of-range access. Invariant: walking live cargo across ticks requires either a fail-closed abort when the count changes, or capture by entity identity at a single instant. A range guard that skips the hole is silent loss. Do not improvise a smarter walk on a data path without an explicit decision: the minimum correct behaviour is to abort without writing world or disk.

### A registry entry leaves by its id, never by proximity (SP-456, added 2026-10-03; read in the code, point 1 also in game, DayZDiag 1.29.163709)

A mod that keeps its own registry of the world entities it placed (a sidecar JSON with class,
position and id per entry; Contract 3) binds each entry to one entity. An audit of the SecretRock
mod's code (DZ-R9, 2026-10-03: Codex read the code, Claude checked each finding against it) found
three ways to cross that binding.

1. **Unregister by proximity deletes another entity's entry.** `EEDelete` called an unregister that
   looked the entity up by id and, failing that, took the nearest entry of the same class within
   0.75 m and saved the file without it. Two paths create and then delete an entity that never got
   an id: a placement that creates the entity, checks the site and deletes it on refusal, and an
   entity an admin spawns from the console and deletes. Either way a registered neighbour of the
   same class inside the radius loses its entry and does not come back after the next restart. Rule:
   an unregister needs a matching id, and an entity without one never touches the file; an id that
   two entries share identifies neither of them. In the degraded case (ids assigned in memory that
   could not be saved) a deleted entity then comes back after a restart, which is preferred to
   deleting another entity's entry. In game, with that rule, a console entity created 0.3 m from a
   registered one horizontally (0.37 m apart, inside the radius) and then deleted left the registry
   byte-identical (same SHA-256), and the registered one came back after the restart
   [EXACT][CLAIM-PERS-UNREGISTER-BY-ID]; the failure itself was read in the code, not reproduced.
2. **Restore: only the id can bind an entity to the entry, a position match proves nothing, and how
   to restore is an open problem.** `GetObjectsAtPosition3D` returns the objects in a sphere and
   promises no order (`VANILLA/3_game/global/game.c:924-929`)
   [EXACT][CLAIM-PERS-RESTORE-BIND-BY-ID], so taking the first unclaimed candidate of the class
   inside the radius can swap ids and states between two nearby entities of that class, and a
   second restore pass (one 2 s after start, to bind what the mission created) runs that code on
   every boot. SecretRock's fix takes the entity already bound to the entry's id, else the nearest
   one not yet claimed in the pass; it keeps the id in a script member, so no entity carries it
   across a restart. A position match proves nothing: an entity near the entry's position, or of its
   class, is not shown to be the entry's, and finding none there does not show the entry's entity
   gone. An id that two entries, or two live entities, carry identifies neither.

   No automatic restore rule has come out of review sound. Six rounds of cross-family review (Codex,
   2026-10-03), one on each restore rule this section gave in #97 and #99, traced every one of them,
   through SecretRock's fixed code or through the rule's own text, into an entry that takes the
   wrong entity or gets a second one:
   - **the wrong entity**: an entry left in the registry by an unregister whose save failed takes
     the nearest unclaimed entity of the class although it carries another entry's id (R21-01), or
     an admin's console entity that carries no id (R21-03); of two loaded entities that carry one
     id, the second to load takes the binding (R21-07);
   - **a second entity**: a rule that refuses every entity with another id creates again for an
     entry whose id was regenerated after a failed save (`I1` given to the entity in memory, the
     save fails, a later pass saves `I2`) (R21-04); a rule that reads an empty radius as absence
     creates while the entity sits outside the radius, under another class name or not yet loaded
     by the engine (R21-05); a list of the restore's own creations, cleared when the mission ends,
     misses the previous mission's entities if they still live (R21-06); a list of every live
     entity kept by the entities' own `EEInit` and `EEDelete` misses a creation in flight, which
     joins it from its `EEInit` before it carries the id, so a pass started from that `EEInit`
     creates a second one (R21-08); and a reservation of the entry during that creation does not
     stop a pass that reloads the registry and gets a copy of the entry without the reservation
     (R21-09).

   Where later passes do see the reservation, a creation that fails keeps the entry from ever
   getting its entity (R21-10). These are traces, not observations: none was reproduced in game,
   and several need conditions not shown to occur in SecretRock: a pass started from an entity's
   `EEInit` (SecretRock starts its restore passes only from `MissionServer`), two loaded entities
   with one id, entities that live through a mission change. Whether the engine persists
   SecretRock's rocks is not established. The Pack gives no rule for this restore; Hard stops item 9
   names what it must not do.
3. **A restore pass still queued can reopen saving at shutdown.** If the restore clears the
   shutdown flag (for a mission restart in the same process), a restore `CallLater` still in
   `CALL_CATEGORY_SYSTEM`, which is processed "without any restrictions"
   (`VANILLA/3_game/global/game.c:1515`), clears it again after `OnMissionFinish`, and the
   `EEDelete` calls of the shutdown then unregister entries. Rule: remove the pending passes
   (`ScriptCallQueue.Remove`, `VANILLA/2_gamelib/tools.c:65`) before setting the flag
   [EXACT][CLAIM-PERS-SHUTDOWN-QUEUE]. Read in the code; the shutdown order in game is not confirmed.

Every entry point that creates or deletes such an entity has to honour the first rule; the
inventory to walk is in `rigorous-data-audit`, `references/entry-point-audit.md`.

## DayZ 1.30 Exp (build 1.30.164014)

Verified against `exp\scripts\scripts\` (1.30.164014) vs `stable-1.29`. Full
`[EXACT]` bodies live in
[references/dayz-1-30-persistence.md](references/dayz-1-30-persistence.md).
Worked 1.30 cells for CombinationLock, ThermalBiasHandler, Rebuilding, and
BunkerBroadcast are in
[references/migration-matrix.md](references/migration-matrix.md).
Mission-file exception: [references/sidecar-files.md](references/sidecar-files.md).

### What changes

- `GAME_STORAGE_VERSION` is 144 (`3_Game\Global\Game.c:5`). `SaveVersion()` is
  at `:435`. CombinationLock and EntityAI construction load branch on
  `version >= 143`; a 1.29 record (`142`) skips those new fields.
- `EntityAI.OnStoreSave` calls `ConstructionBasic.HandleStoreSave` before
  energy (`3_Game\Entities\EntityAI.c:2887-2891`). Load of that block is
  `version >= 143` (`:2955-2961`). Empty for `BaseBuildingBase`; `Rebuilding`
  writes `REBUILDING_STORAGE_VERSION` plus ten ints.
- `PlayerBase` MP save appends `m_ThermalBiasHandler.OnStoreSave` after the
  arrow manager (`4_World\Entities\ManBase\PlayerBase.c:7395`). Load has **no**
  version gate (`:7520-7524`). Payload is `float m_TemporaryResistanceTime`
  (`4_World\Classes\ThermalBiasHandler.c:67-77`).
- `CombinationLock` writes `m_CombinationInside` and reads it at
  `version >= 143` (`4_World\Entities\ItemBase\CombinationLock.c:128-177`).
- New `DigitalCodeLock` streams PIN / locked / door index through
  `CodeLockComponent` (`ItemBase\CodeLock.c:469-482`;
  `Classes\CodeLockComponent.c:257-277`).
- New `$mission:BunkerBroadcastPersistenceStorage.bin` via `FileSerializer`
  (`Classes\BunkerBroadcastHandler.c:16-82`). Not the character/world bin.

### What breaks

- A `PlayerBase` override that copies the 1.29 MP suffix or skips `super`
  fails with `---- failed to load ThermalBiasHandler, read fail  ----`.
- A `CombinationLock` `OnStoreLoad` that assumes two ints after `super`
  desyncs from v143 onward.
- Seeking a fixed offset past `super` on a `Rebuilding` house: construction
  bytes now sit in front of energy.
- Treating the bunker `.bin` as `JsonFileLoader` or as an atomic replace.
  `DeleteFile`/`CopyFile` only work on `$profile:` and `$saves:`
  (`1_Core\proto\EnSystem.c:527-531`).

`JsonFileLoader` and CF ModStorage line numbers in this extract still match
the 1.29 skill. Digest I's `PlayerBase.c:941-950` cite was volcanic-area ticks,
not persistence.

### Migration checklist

- [ ] Keep `super.OnStoreSave` / `super.OnStoreLoad` on PlayerBase,
      CombinationLock, DigitalCodeLock, and any EntityAI with a construction
      component.
- [ ] CombinationLock: `if (version >= 143) ctx.Read(m_CombinationInside)`
      (or rely on `super`).
- [ ] Do not treat a 1.29 `player.bin` on 1.30 as a successful thermal
      legacy migrate — vanilla always reads the new float on MP load.
- [ ] Do not apply `Rebuilding`'s ten ints to `BaseBuildingBase` (still three
      ints + `m_HasBase` at `BaseBuildingBase.c:420-429`).
- [ ] Do not clone vanilla's unchecked `$mission:` `FileSerializer` overwrite.
- [ ] Classify CombinationLock 142→144 as gated known/legacy; classify
      ThermalBias 142→144 as failed/truncated unless Bohemia wipes characters.
