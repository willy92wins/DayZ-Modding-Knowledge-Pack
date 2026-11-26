# Why this skill exists — the LF_VStorage 1.4.6 retrospective

## What happened

LF_VStorage 1.4.6 went through a multi-round audit before the user asked for
a "release-safe?" verdict:

1. External auditor handed in 6 P1 findings (lost-items class). Fixed.
2. User requested re-audit with multiple Opus agents to catch what was
   missed. Spawned 6 parallel Opus agents from independent angles
   (persistence, state machine, async, hooks, admin, recovery). Each agent
   produced a coherent report. None found anything new.
3. Declared "release-safe pending in-game test".
4. User then handed in `AUDIT_HARDENING_IMPLEMENTER.md` from an external
   implementer-grade auditor. **12 VULNs (P0–P3) the agents had missed.**

## The 12 VULNs

Listed here so the patterns are concrete:

| ID | Severity | Class |
|---|---|---|
| VULN-001 | P0 | External VS kill-switch not durable across mission entry points |
| VULN-002 | P1 | `m_HasItems` not hydrated from disk on TrackContainer |
| VULN-003 | P0 | Path-helper inconsistency: `.tmp` vs `.lfv.tmp` between writer and recovery |
| VULN-004 | P0 | Pre-super gate runs after vanilla super in EE hooks |
| VULN-005 | P1 | Shutdown queue iteration mutation |
| VULN-006 | P1 | `migrate-all` admin command blocked by its own restore queue |
| VULN-007 | P1 | Degraded recovery deletes `.lfv` after partial — destroys recoverable data |
| VULN-008 | P0 | `DeleteContainerFiles` missing `.restoring` and `.manifest.json` |
| VULN-009 | P1 | `VirtualizeSynchronous` leaves stale `.virtualizing` marker |
| VULN-010 | P0 | Admin recovery flags in-memory only while sidecar removed |
| VULN-011 | P1 | LFV2 count fields lack sanity caps |
| VULN-012 | P2 | Non-authoritative JSON writes still best-effort |

## Why the agents missed each one

| VULN | Class | Why six agents missed it |
|---|---|---|
| VULN-003 | Path-helper inconsistency | Each helper looked correct in isolation. Bug is the **inconsistency**, not any one site. Reasoning agents trace happy paths. |
| VULN-008 | Sidecar cleanup missing | `DeleteContainerFiles` looked thorough — it deleted 6 of 8 file types. Reasoning agents check what is present, not what is missing. |
| VULN-009 | Sync entry-point divergence | The async path had been audited heavily. The sync path was "obviously similar". Was not. |
| VULN-001 | Mission entry-point divergence | OnMissionStart + OnMissionLoaded looked correct as a pair. The third entry point (server reload) was not in the agent's mental model. |
| VULN-010 | Two-store divergence | Admin recovery flags lived in `m_AdminRecoveryFlags`, separate from `m_QuarantineMap`. Each map looked consistent internally. |
| VULN-004 | Pre-super gate placement | Gate was present. Order within the EE hook was not visible from "is the gate there?". |
| VULN-011 | Threat model out of scope | Agents prompted "audit persistence" did not ask "what if disk is hostile?". |
| VULN-002 | Initial-state hydration | Agent saw the field set on save, did not check that load restored it from disk. |
| VULN-005 | Iteration-during-mutation | The shutdown drain code was short and "obvious". Agents skipped the careful read. |
| VULN-006 | Self-blocking queue | Admin command queued itself behind work it was supposed to flush. Required cross-actor tracing (admin → queue → admin). |
| VULN-007 | Wrong cleanup action | "Delete after partial recovery" looked like cleanup; was actually data destruction. Required understanding intent, not just code. |
| VULN-012 | Best-effort write | Easy to miss because "best-effort" feels like a reasonable error mode. Audit asks "is this state critical?" — yes, then best-effort is wrong. |

## The five lessons that drove this skill's design

### 1. Reasoning is bad at enumeration

Five of twelve VULNs (003, 008, 009, 010, 011) were **mechanically
enumerable** — a grep + table walk finds them in under a minute each.
Reasoning agents underweight bookkeeping. The skill fixes this by running
mechanical pre-checks **before** spawning reasoning agents (workflow step 1).

### 2. Cross-actor tracing is the agent's weak spot

Three of twelve VULNs (006, 008, 010) required tracing across modules:
admin command → queue → state machine, or writer → cleanup → boot scan. A
reasoning agent prompted "audit module X" looks within X. The skill fixes
this by adding a dedicated **implementer-grade pass** in step 4 that
explicitly demands cross-actor tracing.

### 3. Alternative entry points always diverge

Two of twelve VULNs (001, 009) were alternative-entry-point bugs. Sync
shortcuts, admin commands, mission-reload paths — they always skip
something. The skill fixes this by adding a dedicated angle (entry-point
audit) and a dedicated angle prompt (action layer).

### 4. Confidence in good-looking code propagates between agents

Once one agent said "this module is fine", subsequent agents implicitly
trusted that read. The skill fixes this by prompting agents to **not trust
prior reports** (implementer-grade pass) and by spawning agents in
parallel so they cannot read each other's output.

### 5. Severity self-reporting is unreliable

Agents reported many P2/P3 findings and zero P0. The implementer-grade
auditor reported 6 P0/P1. Agents systematically under-rate severity. The
skill fixes this by having the user (or main thread) assign severity
during step 3 consolidation, not the agent.

## What the skill is and is not

**This skill is not a guarantee.** Twelve VULNs is a snapshot of one
auditor's findings. A more thorough auditor on the same code would find
more. The skill makes the audit phase more rigorous, but in-game testing
on real save data remains the final filter.

**This skill is a forcing function.** It exists because the user and the
agent both know that "audit" is easy to perform shallowly and hard to
perform deeply. The 7-step workflow makes the deep version the default.

## Reading list

- `audit-prompts.md` — the eight angle prompts and implementer-grade pass
- `path-naming-matrix.md` — finds VULN-003 class
- `sidecar-cleanup-symmetry.md` — finds VULN-008 class
- `entry-point-audit.md` — finds VULN-001, VULN-009 classes
- `flag-lifecycle-audit.md` — finds VULN-010 class
- `state-machine-matrix.md` — structural state-transition check
