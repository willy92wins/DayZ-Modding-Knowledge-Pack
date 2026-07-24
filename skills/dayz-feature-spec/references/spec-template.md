# Feature Spec: [FEATURE NAME]

**Mod / PBO**: [e.g. LFPowerGrid_Core.pbo]
**Date**: [YYYY-MM-DD]
**Status**: Draft | Ready-to-implement | Implemented | Verified-in-game
**Plan**: [link to the Plan-mode plan or HANDOFF section this derives from]

> Fill this before writing code. Keep it short. Delete guidance comments before marking Ready.
> Skip this template entirely for 1-line typos / trivial reversible tweaks (R3).

## Context / Why

[1–3 lines: what problem this solves and why now. No implementation detail.]

## Acceptance Scenarios *(mandatory)*

Each scenario is Given/When/Then with concrete in-game repro steps. "It works" is not a scenario.

1. **Given** [initial state, e.g. "player spawned next to a placed Crate_Wooden"],
   **When** [action, e.g. "player fires one round"],
   **Then** [observable outcome, e.g. "the bolt selection moves back and a casing ejects toward -Z"].
   - **Repro in-game**: [spawn what / do what / observe what — the exact steps for the R5 batched test]

2. **Given** … **When** … **Then** …
   - **Repro in-game**: …

## Success Criteria *(mandatory)*

Measurable, technology-agnostic where possible. No vague adjectives.

- **SC-001**: [e.g. "0 `Error` lines in `script_*.log` during the scenario"]
- **SC-002**: [e.g. "hands sit <0.5 cm from the grip memory point"]
- **SC-003**: [e.g. "vehicle reaches ≥X km/h on flat terrain within Y s"]

## Scope — Out of scope *(mandatory)*

- [Explicit non-goals. What this feature does NOT do, so the analyze gate and reviewers do not treat their absence as gaps.]

## Assumptions

Mark every guess. If an assumption decides correctness (path, classname, version, format), resolve it with AskUserQuestion now — do not defer to code (G1).

- **ASSUMED**: [e.g. "inherits from Inventory_Base, not Container_Base"] — [resolve / defer + why]
- **ASSUMED**: …

## Forward Contract (R8-extended)

Every symbol the next phase or consumer reads. Each MUST be verified `path:line` (G2/R2) or marked `[UNVERIFIED]`. An `[UNVERIFIED]` ref is treated as CRITICAL by the analyze gate.

| Consumer | Symbol it reads | Kind | Verify status |
|---|---|---|---|
| model.cfg | `bolt` | selection | `Model.p3d` LOD0 selection `[UNVERIFIED]` |
| config.cpp | `DamageZones.Engine` | class | `carscript.c:991` |
| config.cpp | `hiddenSelection[0]` | texture slot | `[UNVERIFIED]` |
| stringtable | `STR_MYMOD_ACTION` | key | `stringtable.csv:12` |

## Verification plan

Per criterion: how it will be checked. Offline checks are preferred (they avoid an in-game cycle, R5); in-game checks are batched into one session.

| Criterion | Verification | Where |
|---|---|---|
| SC-001 | grep `script_*.log` for `Error` | offline (post-test RPT scan) |
| SC-002 | py3d distance grip↔hand bone | offline |
| Scenario 1 | fire + observe bolt/casing | in-game (R5 batch) |

## Open questions / NEEDS CLARIFICATION

- [Anything blocking that must be answered before implement. Prefer AskUserQuestion over guessing.]
