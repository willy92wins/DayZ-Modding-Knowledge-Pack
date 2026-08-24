# State machine matrix — structural check

Catches illegal transitions, double-counted state, and "should never happen"
branches that can in fact happen.

## Procedure

### Step 1 — List every state

Read the state enum / constant table. Build column headers:

```
states = [IDLE, VIRTUALIZING, VIRTUALIZED, RESTORING, RESTORED, QUARANTINE, QUARANTINE_ORPHANED]
```

Adapt to your project's actual state names.

### Step 2 — List every transition function

```powershell
Grep "SetState|TransitionTo|m_State\s*=" --type c --output_mode content -n true
```

For each callsite, record (from_state, to_state, function, conditions).

### Step 3 — Build the matrix

Rows = from_state, columns = to_state, cells = list of functions that
perform that transition.

|  | IDLE | VIRTUALIZING | VIRTUALIZED | RESTORING | RESTORED | QUARANTINE | QO |
|---|---|---|---|---|---|---|---|
| IDLE | — | StartVirt | — | — | — | OnLoadCorrupt | OnLoadOrphan |
| VIRTUALIZING | OnVirtCancel | — | OnVirtComplete | — | — | OnVirtFail | — |
| VIRTUALIZED | — | — | — | StartRestore | — | OnVerifyFail | — |
| RESTORING | — | — | — | — | OnRestoreComplete | OnRestoreFail | — |
| RESTORED | OnRestoredAck | — | — | — | — | — | — |
| QUARANTINE | OnAdminRecover | — | — | — | — | — | — |
| QO | OnAdminRecover | — | — | — | — | — | — |

### Step 4 — Validate

For each cell:

- **Empty** = transition should not happen. Confirm no code path performs
  it. Search for `m_State = TARGET` and verify every site is covered by a
  transition function in the matrix.
- **Multiple functions** = audit each individually. Multiple functions
  performing the same transition is a smell — they should converge to one.
- **One function** = the canonical case. Confirm the function's
  preconditions match the spec.

### Step 5 — Identify illegal transitions

Diagonal cells (state X → state X) should be empty unless the spec
explicitly allows self-transitions. Re-entry on the same state means work
overlap.

Disconnected cells: if a state has no incoming transitions, no entity
ever reaches it. If it has no outgoing transitions, entities are stuck.

Both are findings.

### Step 6 — Validate "should never happen" branches

Grep:

```powershell
Grep "should not happen|should never|impossible|unreachable|TODO.*remove" --type c --output_mode content -n true
```

For each comment claiming impossibility: identify the precondition that
makes it impossible. If you cannot identify a precondition (and the comment
is just self-assurance), treat the branch as a finding — it can happen.

## Common findings

- A state reachable only by a fail-path with no recovery transition out
- Two functions performing the same transition with different
  preconditions (race window where both fire)
- An EE hook that writes m_State without going through a transition
  function (bypasses validation)
- An admin command that sets m_State directly (the canonical example: VULN-010)

## Time budget

~10 minutes for a 7-state machine. Re-run after each state machine change.
