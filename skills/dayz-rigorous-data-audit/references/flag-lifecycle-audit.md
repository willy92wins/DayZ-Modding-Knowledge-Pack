# Flag-lifecycle audit — mechanical check #4

Catches the bug class where two state stores must move together but one
moves without the other. Most common shape: an in-memory flag flips while
the on-disk sidecar still holds the previous truth, or vice versa.

Reasoning agents miss this because each state store looks consistent
internally — the bug is the asymmetry between stores.

## Worked example: VULN-010 (LF_VStorage 1.4.6)

Quarantined containers had two state stores: a `.quarantine.json` sidecar
on disk, and an `m_AdminRecoveryFlags` map in memory. Admin command
`recover-quarantine <sid>` cleared the sidecar from disk but only set a
flag in memory. On next boot, the in-memory flag was lost; the sidecar was
gone. The container appeared healthy. The actual data file was still
quarantined-format. Loading produced corrupt state.

The fix needed to keep two stores in sync: clear sidecar **after** the
recovery write succeeded, and persist the recovery flag if the recovery
needed multiple boots.

## Procedure

### Step 1 — Inventory state stores per concept

For each concept the mod tracks (quarantine status, virtualization status,
external-VS detection, etc.), list every place it lives:

| Concept | In-memory store | On-disk store | Sidecar | Other |
|---|---|---|---|---|
| Quarantine status | `m_QuarantineMap` | none | `.quarantine.json` | none |
| Admin recovery flag | `m_AdminRecoveryFlags` | none — VULN-010 | n/a | n/a |
| Virtualize state | `m_StateMachine[sid]` | header byte | `.virtualizing` | n/a |
| External VS detected | `m_ExternalVSDetected` | none — VULN-001 | n/a | n/a |

If the same concept lives in 2+ stores, it has a flag-lifecycle obligation.
If it lives in 1 store but should survive crashes/restarts, **it should be
2 stores** — flag the missing on-disk store as a finding.

### Step 2 — For each concept with 2+ stores, build a transition matrix

For every operation that touches the concept, record which stores it
mutates:

| Operation | Mutates m_QuarantineMap | Mutates `.quarantine.json` | Atomic? |
|---|---|---|---|
| `Quarantine(sid)` | set | write | no — write first, then set |
| `Recover(sid, success)` | clear | delete | no — delete first, then clear |
| `OnBoot` (load sidecar) | set | read | n/a |
| `recover-quarantine` admin | set flag in **other map** | delete sidecar | **stores diverge** |

The "stores diverge" row is the finding. Either:

1. The admin command must update both stores, or
2. The admin command must use the same store as `Recover` (no separate flag map)

### Step 3 — Verify ordering invariants

Two stores moving together still need order. Two valid patterns:

**Disk-first** (durable truth on disk, memory is cache):

```
1. Write sidecar with new state, fsync
2. Update in-memory map
3. If crash between 1 and 2: next boot reads sidecar, restores memory — safe
```

**Memory-first** (writes coalesced, sidecar is checkpoint):

```
1. Update in-memory map
2. Schedule sidecar write
3. If crash between 1 and 2: state lost — only safe if state can be recomputed
```

For data-critical stores (quarantine, persistence flags, money), use
disk-first. Memory-first is acceptable only for stores where loss is
recoverable (e.g., per-tick caches).

### Step 4 — Verify reset/cleanup symmetry

For each concept, the reset path must clear all stores:

```powershell
Grep "Reset|Clear|Purge|Wipe" --type c --output_mode content -n true
```

Find the reset functions. For each, walk down: which stores does it touch?
If concept X has stores A, B, C and Reset touches only A and B, that is a
finding.

### Step 5 — Output

Findings table:

| Concept | Issue | Stores affected | File:Line |
|---|---|---|---|
| Admin recovery flag | Memory-only — lost on restart | `m_AdminRecoveryFlags` only | admin.c:88 |
| External VS detected | Memory-only — lost on world reload | `m_ExternalVSDetected` only | mission.c:42 |
| Quarantine | Reset clears sidecar but not memory | `m_QuarantineMap` not cleared in `DeleteContainerFiles` | cleanup.c:55 |

Severity:

- Memory-only on a data-critical concept → P0
- Reset asymmetry where memory holds stale data after disk wipe → P1
- Ordering wrong (memory-first on critical) → P0/P1 depending on recoverability

## Heuristics for spotting concepts that need 2 stores

- Crosses a reboot? Must be on disk
- Crosses a world reload? Must be on disk
- Crosses only ticks? In-memory is fine
- Admin can override? Both stores must update consistently
- Recovery path reads it? Must be on disk

## Common false positives

- Per-session UI state (no need to persist)
- Per-tick computation caches (recomputable)
- Constants computed from on-disk state (the disk store is authoritative)

## Time budget

~5 minutes per 2-store concept. LF_VStorage had ~4 such concepts = 20 minutes.
The catch rate on this check is lower than path-naming or sidecar-symmetry,
but the bugs it finds are typically P0 (memory-only data-critical state).
