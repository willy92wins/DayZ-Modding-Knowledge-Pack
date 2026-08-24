# Entry-point audit — mechanical check #3

Catches the bug class where the canonical path enforces an invariant but an
alternative entry point (synchronous shortcut, admin command, early-mission
hook) skips it.

Reasoning agents miss this because they fixate on the canonical async flow
and treat the shortcut as "obviously similar". The shortcut is rarely
similar enough.

## Worked examples

### VULN-009: synchronous virtualize leaves stale marker

`Virtualize_Async` wrote `.virtualizing`, did the work across ticks, then
removed the marker. `VirtualizeSynchronous` (used during shutdown) wrote
`.virtualizing` but never removed it because the shutdown path skipped the
post-completion cleanup branch. Next boot saw the marker, treated the
container as crashed-during-virtualize, and entered recovery on a
fully-virtualized container. Recovery merged duplicates.

### VULN-001: kill-switch not durable across mission entry points

`OnMissionStart` set the in-memory `m_ExternalVSDetected` flag.
`OnMissionLoaded` read it and gated work. Looked correct. Bug: a separate
boot path (server reload after admin command) skipped `OnMissionStart` and
went straight to `OnMissionLoaded` — flag still false, gate did not fire.
The fix was to persist the detection result on disk so any entry point
could re-read it.

### VULN-004: pre-super gate runs after vanilla super

`EEItemAttached` called `super.EEItemAttached(item, slot)` first, then
checked `IsVirtualized()`. Vanilla super already mutated cargo before the
gate fired, leaving inconsistent state.

## Procedure

### Step 1 — Inventory entry points per invariant

For each invariant the mod enforces, list every entry point that should
honor it. Common invariants and their entry points:

**Invariant: container must end virtualize with no marker on disk**

- `Virtualize_Async` (canonical, multi-tick)
- `VirtualizeSynchronous` (shutdown)
- `Virtualize_FromAdminCommand` (`migrate-all`)
- `Virtualize_FromMigrationStub` (legacy / one-shot)

**Invariant: external-VS detection must gate work on every boot**

- `OnMissionStart`
- `OnMissionLoaded`
- Server reload after admin command
- World load after rare crash recovery

**Invariant: pre-super gate must precede vanilla super in EE hooks**

- `EEInit`
- `EEDelete`
- `EEKilled`
- `EECargoIn` / `EECargoOut`
- `EEItemAttached` / `EEItemDetached`
- `EEItemLocationChanged`
- `OnStoreSave` / `OnStoreLoad`

### Step 2 — For each invariant, walk every entry point

Grep the entry-point name; open each match; verify the invariant is
enforced. Build table:

| Invariant | Entry point | File:Line | Honored? | Notes |
|---|---|---|---|---|
| End virt without marker | `Virtualize_Async` | persistence.c:340 | yes | Removes `.virtualizing` on success |
| End virt without marker | `VirtualizeSynchronous` | persistence.c:480 | **no — VULN-009** | Skips cleanup branch |
| End virt without marker | `Virtualize_FromAdminCommand` | admin.c:120 | yes | Calls async path |
| Pre-super gate | `EEItemAttached` | events.c:88 | **no — VULN-004** | Gate after super |
| Pre-super gate | `EECargoIn` | events.c:102 | yes | |

### Step 3 — Specific patterns to search

**Synchronous shortcuts of an async operation**:

```powershell
Grep "Synchronous|_Sync\b|Force\w+|_Now\b|ImmediateMode" --type c --output_mode content -n true
```

For each hit, find the corresponding async function and diff the two by
hand. The diff should be limited to scheduling/yielding — not invariants.

**Admin command handlers**:

```powershell
Grep "OnAdminCommand|HandleAdmin|RegisterCommand|admin_|Cmd_" --type c --output_mode content -n true
```

For each handler, ask: does this short-circuit the async queue? If yes, does
it acquire the same gates and clean up the same markers as the queue would?

**Mission entry points**:

```powershell
Grep "OnMissionStart|OnMissionLoaded|OnMissionFinish|OnUpdate" --type c --output_mode content -n true
```

For state set in OnMissionStart and read in OnMissionLoaded: is there a path
that hits OnMissionLoaded without OnMissionStart? Server reload, world
reload, mission script reload. If yes, the state must be **on disk**, not
in memory.

**EE hook ordering**:

```powershell
Grep "override\s+void\s+EE" --type c --output_mode content -n true
```

For each EE override: read the body. The first 3 lines must be either
gate-then-super or super-then-gate consistently. Mixed order = bug.

### Step 4 — Output

Findings table with three columns: invariant, offending entry point, fix
sketch. Group by invariant so the user sees "this invariant is honored in
3 of 4 entry points" — that is a P0 even if only one entry point is wrong.

## Heuristics

- An entry-point inventory of fewer than 4 items per invariant is suspicious — go look harder, you missed one
- "Synchronous", "Sync", "Force", "Immediate", "Now" in a function name = shortcut = high suspicion
- Admin commands almost always skip something. Default to "untrusted, audit individually"
- Server-reload / mission-reload paths are easy to forget; ask the user explicitly which entry points exist if unsure

## Time budget

~3–5 minutes per invariant. LF_VStorage has ~6 invariants of this shape =
~30 minutes. Slow but cheap relative to a P0 escape.
