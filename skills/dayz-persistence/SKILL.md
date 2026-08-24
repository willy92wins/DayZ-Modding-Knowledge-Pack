---
name: dayz-persistence
description: Use when designing, implementing, debugging, or auditing DayZ persistence — OnStoreSave/OnStoreLoad entity streams, CF ModStorage and storageVersion, persistent-format migration or rollback, sidecar JSON, recoverable file replacement or atomic-save claims, and player-data corruption after save or restart. Invoke for deprecated JSON loading APIs, future or truncated versions, and uninstall-safe mod data.
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
