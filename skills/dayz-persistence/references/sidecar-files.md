# Sidecar File Contract

## Scope and available primitives

Use a sidecar for state that is not owned by one entity, must be inspected or
repaired outside the game, or needs an explicit file-level recovery surface. The
file owns its format header and mod version.

DayZ exposes these relevant primitives:

- `FileExist`, `OpenFile`, `ReadFile`, and `CloseFile`
  (`VANILLA/1_core/proto/ensystem.c:397,417,425,443`).
- `FPrint`, `FGets`, and `MakeDirectory`
  (`VANILLA/1_core/proto/ensystem.c:462,501,525`).
- `DeleteFile` and `CopyFile`
  (`VANILLA/1_core/proto/ensystem.c:528,531`).

There is no DayZ rename or move primitive; a search for `Rename` or `MoveFile`
in the cited `1_core` surface returns no match
(`VANILLA/1_core/proto/ensystem.c`). A design that says rename, move, or atomic
replace is using an API DayZ does not provide.

For JSON, use
`JsonFileLoader<T>.LoadFile(string, out T, out string)` and check its `bool`
return before accepting the output; preserve or report `errorMessage` without
private paths or player identifiers
(`VANILLA/3_game/tools/jsonfileloader.c:7-40`). Do not use `JsonLoadFile`: it is
deprecated and returns no success signal
(`VANILLA/3_game/tools/jsonfileloader.c:99-131`).

## Load contract

1. If the destination cannot be opened, return failure with the original
   untouched and create nothing.
2. Read into staged bytes. A failed or short read returns failure and applies no
   state.
3. Parse and validate magic/header, version, schema, declared lengths, and the
   complete payload before applying state.
4. Invalid JSON, a foreign schema, trailing data, or truncation preserves the
   original as evidence and applies no partial values.

## Recoverable save flow

Use deterministic sibling names: `<dest>.tmp`, `<dest>.bak`, and
`<dest>.sha256`.

1. Serialize the complete new record in memory, including its own version
   header and lengths.
2. Write it to `<dest>.tmp` and close the handle. If writing fails, discard the
   incomplete fragment; the original remains intact.
3. Reopen `<dest>.tmp`, read it fully, parse it, and verify it reproduces the
   intended record. A completed candidate that fails this verification is kept
   as evidence.
4. If `<dest>` exists, copy it to `<dest>.bak`. If backup fails, stop before
   replacement; keep the original and verified temporary file.
5. Delete `<dest>`, then copy the verified `<dest>.tmp` to `<dest>`. If deletion
   fails, stop with the original, temporary file, and backup available. If the
   process stops after deletion or the copy fails, the destination is absent but
   the temporary file and backup make recovery deterministic.
6. Reopen and fully verify the copied destination against the intended bytes and
   schema. If it is truncated or invalid, delete the bad destination and retain
   `<dest>.tmp` and `<dest>.bak`.
7. Write the verified destination digest to `<dest>.sha256`. If this fails, keep
   the destination, temporary file, and backup as evidence; do not claim a clean
   save.
8. Delete `<dest>.tmp` only after destination verification and sidecar creation
   succeed. A completed candidate is never deleted on a verification failure.

The production sequence is temp -> verify -> backup -> delete -> copy -> verify
-> hash sidecar -> delete temp
(`LFVS_SOURCE/Scripts/4_World/LFV_FileStorage.c:28-45`). Post-copy verification
exists because `CopyFile` can produce an incomplete destination; compare the
copied bytes before removing the temporary source
(`LFVS_SOURCE/Scripts/4_World/LFV_FileStorage.c:998-1009,1281-1282`).

An incomplete fragment from a failed temp write is discardable. That is distinct
from a completed `.tmp` that reached verification: once complete, it is retained
until the post-copy verify and digest sidecar succeed.

## Atomicity honesty

Temp -> verify -> replace is not atomic in DayZ. The actual replace operation is
`DeleteFile(dest)` followed by `CopyFile(tmp, dest)`. Between those calls the
destination does not exist. A backup and retained temporary file make the window
recoverable; they do not make it atomic. Document the window and every recovery
artifact explicitly.

## Nine I/O boundaries

| Boundary | Injected failure | Required invariant |
|---|---|---|
| open (read) | Handle is `0` | Original intact; no new file is created. |
| read | Input is cut halfway | No partial state is applied. |
| parse | Invalid JSON or foreign schema | Original intact and preserved as evidence. |
| backup / rotate | Backup copy fails | Stop before replacement; original and `.tmp` remain. |
| temp-write | `FPrint` fails or storage is full | Incomplete temp is discardable; original remains intact. |
| temp-verify | Header or payload does not reproduce | Preserve the completed `.tmp`; original remains intact. |
| replace | Failure between destination delete and temp copy | Destination may be absent; `.tmp` and `.bak` are present and recoverable. |
| post-copy verify | Destination copy is truncated | Delete the bad destination; do not delete `.tmp`; retain backup. |
| orphan `.tmp` | Candidate is valid or truncated | Promote only verified content; never decide from mtime. |

Every boundary preserves either the original bytes or deterministic recovery
evidence. Returning failure without identifying which artifacts remain is not a
complete result.

## Orphan policy

Evaluate `<dest>.tmp` by content, never by modification time.

- If the candidate cannot be opened/read fully, has an invalid header, declares
  a length it does not contain, or otherwise fails schema verification, do not
  promote it. Preserve it as truncated evidence and leave the destination
  untouched.
- If the candidate verifies, back up an existing destination, perform the same
  delete-and-copy replacement, verify the copied destination, create the digest
  sidecar, and only then delete the orphan temporary file.
- If orphan promotion fails after destination deletion, retain the temporary
  file and backup. The same non-atomic window applies.

mtime says when a directory entry changed, not whether its bytes form a complete
record. It is never a promotion or deletion criterion.

## Verification checklist

- The file has an independent mod-format header.
- Every loader result and `errorMessage` is checked before state is applied.
- Reads are staged; parse or length failure applies nothing.
- Temp data is reopened and verified before backup or replacement.
- Backup failure stops before deleting the destination.
- The delete-copy window is documented as non-atomic.
- Post-copy verification compares complete bytes and schema.
- A bad copied destination is removed while `.tmp` and `.bak` remain.
- The digest sidecar is created before `.tmp` cleanup.
- Valid and truncated orphan candidates take different deterministic actions.
- No orphan decision uses mtime.
