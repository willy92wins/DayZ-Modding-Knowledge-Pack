# Sidecar cleanup symmetry — mechanical check #2

Catches the bug class where a writer creates a sidecar/marker file and the
matching cleanup site fails to remove it. The file persists, future boots
misinterpret the container's state, and recovery silently misroutes.

Reasoning agents miss this because each writer looks correct in isolation —
the bug is the missing entry on the deleter side, which is a different file.

## Worked example: VULN-008 (LF_VStorage 1.4.6)

`StartRestore` wrote `.restoring`. `WriteManifest` wrote `.manifest.json`.
Both writers were correct. `DeleteContainerFiles(sid)` removed `.lfv`,
`.lfv.bak1`, `.lfv.bak2`, `.tmp`, `.virtualizing`, `.quarantine.json` — but
not `.restoring` and not `.manifest.json`. After admin-resetting a
mid-restore container, the marker survived. Next boot, recovery saw a
`.restoring` with no `.lfv` and treated the container as crashed-during-
restore, blocking the slot.

## Procedure

### Step 1 — Inventory all sidecar/marker writers

Grep every site that writes a recognized sidecar/marker extension:

```powershell
Grep "FileWrite|FileSave|JsonFileLoader\.SaveFile|JsonSaveFile|MakeDirectory" --type c --output_mode content -n true
Grep "\.virtualizing|\.restoring|\.manifest\.json|\.quarantine\.json|\.partial|\.locked" --type c --output_mode content -n true
```

Build table:

| Sidecar | Writer site | File:Line | Lifecycle owner |
|---|---|---|---|
| `.virtualizing` | `Virtualize_BeginBatch` | persistence.c:340 | virtualize state |
| `.restoring` | `StartRestore` | restore.c:88 | restore state |
| `.manifest.json` | `WriteManifest` | manifest.c:42 | per-container |
| `.quarantine.json` | `WriteQuarantineSidecar` | quarantine.c:66 | per-failure |

### Step 2 — Inventory all consumer sites

For each sidecar, three obligations exist downstream:

1. **Successful completion path** — the success branch must remove or rotate the marker
2. **`DeleteContainerFiles(sid)` (or equivalent reset)** — admin reset / `.lfv` purge must remove the sidecar
3. **Boot orphan cleanup** — first-boot scan that handles "marker exists, owner state unknown"

For each row in the writer table, walk these three:

```powershell
Grep "DeleteFile|RemoveFile" --type c --output_mode content -n true
```

Find the success-path delete and `DeleteContainerFiles` (or your project's
equivalent). Confirm the boot scan in the recovery module enumerates this
sidecar.

### Step 3 — Cross table

| Sidecar | Success-path delete? | DeleteContainerFiles? | Boot orphan scan? |
|---|---|---|---|
| `.virtualizing` | yes (persistence.c:412) | yes (cleanup.c:55) | yes (recovery.c:140) |
| `.restoring` | yes (restore.c:188) | **no — VULN-008** | yes (recovery.c:155) |
| `.manifest.json` | n/a (overwrite-in-place) | **no — VULN-008** | n/a |
| `.quarantine.json` | n/a (admin-only) | yes (cleanup.c:60) | yes (recovery.c:170) |

Any "no" in any column is a finding. Severity:

- Boot scan missing → P0 (orphans accumulate forever, slot wedged)
- DeleteContainerFiles missing → P0/P1 (admin reset leaves stale state)
- Success-path delete missing → P1 (next operation sees stale marker)

### Step 4 — The "n/a" trap

`.manifest.json` shows `n/a` for success-path delete because manifests are
overwrite-in-place. That is fine for the success path — but the
`DeleteContainerFiles` column still requires a yes. A purged container must
not leave a `.manifest.json` behind that points to nothing. Do not let
"n/a" leak into the reset/cleanup column.

## Heuristics

- A writer that produces a file with a fixed suffix has a cleanup obligation in three places. Always.
- "Marker" (state-bearing) and "sidecar" (data-bearing) follow the same rules. Do not skip sidecars on the assumption that "the data is just metadata".
- Watch for sidecars written by **alternative entry points** (admin commands, sync paths). Often the canonical path cleans up; the shortcut does not. See `entry-point-audit.md`.

## Time budget

~5 minutes per sidecar (4 sidecars in LF_VStorage = ~20 minutes). Worth it —
this is the single highest-leverage check by bug-found-per-minute.
