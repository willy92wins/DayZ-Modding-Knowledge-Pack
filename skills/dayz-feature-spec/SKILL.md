---
name: dayz-feature-spec
description: >
  Define and quality-gate a non-trivial DayZ feature before implementation.
  Produces measurable Success Criteria, Given/When/Then scenarios with in-game
  repro, resolved ASSUMED markers, and a Forward Contract for every classname,
  model.cfg selection, .p3d proxy, stringtable/layout key or injected object the
  next phase consumes. Then runs a spec checklist and a read-only
  spec↔plan↔tasks/HANDOFF↔code consistency gate for coverage gaps,
  contradictions, terminology drift and unverified references. Use for "spec
  de la feature", "definición de done", "criterios de aceptación", "antes de
  implementar", acceptance criteria, consistency/analyze gate, spec checklist
  or "¿está listo para codear?". Run after planning and before
  dayz-mod-workflow; compose with rigorous-data-audit for data-critical work.
---

# DayZ Feature Spec

The DayZ-adapted spine of spec-driven development: define *what done means* and *how it will be verified* before touching code, then gate the artifacts for consistency before spending an in-game test cycle.

This is the local adaptation of GitHub's [spec-kit](https://github.com/github/spec-kit) `specify → clarify → analyze → implement` flow. The generic app scaffolding (TDD red-green, contract tests, user-story-as-independent-MVP slicing, the `specify` CLI, GitHub-issue export, extension marketplace) is intentionally dropped — see "What this drops" below. What is kept is the discipline that already maps to R7/R8/R8-extended and G1–G3, plus one thing they lack: an explicit **artifact-level** consistency gate.

## When to use / when to skip

Use before implementing:

- a new mod feature, or any change touching >1 file (aligns with R3),
- anything data-critical (persistence, progression) — then also invoke `rigorous-data-audit`,
- anything where "done" is not self-evident, or where a later phase/consumer reads this phase's output (R8-extended forward contract).

Skip for: 1-line typos, trivial reversible tweaks (default keybind, stringtable key, path slash). R3's small-reversible-changes-go-direct rule wins — a spec here would be ceremony.

## The flow

```
Plan mode ─► dayz-feature-spec                       ─► [code] ─► dayz-feature-spec        ─► dayz-mod-workflow ─► R5 batched
            Step 1 spec + Step 2 checklist  (GATE)              Step 3 analyze gate (GATE)     (implement)          in-game test
```

The two gates are where this skill earns its place: nothing goes to the expensive in-game cycle (R5) with an unmeasurable criterion, an unverified cross-file reference, or a spec↔code contradiction.

## Step 1 — Write the feature spec

Fill `references/spec-template.md`. It is deliberately short. Four sections carry the DayZ-specific weight:

- **Acceptance Scenarios** — Given/When/Then, each with concrete **in-game repro steps** (spawn what, do what, observe what). "It works" is not a scenario.
- **Success Criteria** — measurable and, where possible, technology-agnostic. DayZ examples: "cerrojo se desplaza al disparar", "0 `Error` lines in `script_*.log` post-test", "manos a <0.5 cm del grip", "coche alcanza ≥X km/h en llano". Vague adjectives ("se ve bien", "funciona") are not criteria.
- **Assumptions** — every guess marked `ASSUMED`. If an assumption decides whether the work is correct (path, classname, version, format), resolve it with `AskUserQuestion` **now**, not after coding (G1: verbalizing a risk is not managing it).
- **Forward Contract** (R8-extended) — list every symbol the *next* phase or consumer reads: `config.cpp` classnames, `model.cfg` selections/bones, `.p3d` proxy paths, `hiddenSelections`, stringtable keys, layout names. Each MUST carry a verify status — `path:line` (verified per G2/R2) or `[UNVERIFIED]`. An `[UNVERIFIED]` ref is a coverage gap the analyze gate treats as CRITICAL. This is exactly the LFQuad Fase B P1 class of bug (proxy path to a non-existent file, missing selections model.cfg needs).

## Step 2 — Spec quality checklist ("unit tests for English")

Before writing any code, run `references/spec-checklist.md` against the spec. It checks the spec itself the way tests check code: is every criterion measurable, every scenario reproducible, every `ASSUMED` resolved-or-flagged, every cross-file ref verified, scope boundary explicit. A spec that fails the checklist is not ready to implement. This is a gate on the *English*, complementary to `rigorous-data-audit`, which is a gate on the *code*.

## Step 3 — Analyze gate (after code/tasks, before the in-game test)

Run `references/analyze-gate.md` — a **read-only** cross-artifact pass over spec ↔ plan ↔ HANDOFF/tasks ↔ code ↔ `CLAUDE.md`. It reports coverage gaps, contradictions, terminology drift, duplicate/near-duplicate requirements, unverified forward-contract refs, and constitution (R1–R9 / G1–G6) violations, each with a severity (CRITICAL/HIGH/MEDIUM/LOW). The gate MUST NOT modify files; it produces a report and offers remediation for explicit approval.

Key DayZ adaptation: coverage means **every acceptance criterion has a verification path** — either an offline check (grep / python / py3d / RPT scan) or an assignment to the batched in-game session (R5). A criterion with no verification path is a CRITICAL coverage gap. CRITICAL findings block the in-game cycle.

This is the artifact-level complement to R7 (trace invariants to all call-sites, code-level) and R8 (end-to-end mental walk).

## What this drops from spec-kit (and why)

- **TDD / red-green / contract tests** — DayZ has no unit-test harness; the acceptance test is the in-game gate (R5). The verification-path concept replaces test-first.
- **User-story-as-independent-MVP slicing** — DayZ features are often monolithic (a vehicle drives or it does not; a grip pose is right or wrong). Priorities/scenarios are kept; the MVP-per-story ceremony is not.
- **The `specify` CLI, uv scaffolding, tech-stack research phase** — the stack is fixed (Enforce Script, config.cpp, model.cfg, .p3d) with a fixed toolchain (AddonBuilder, DayZDiag). No scaffolding needed.
- **`/taskstoissues`, extensions/presets/bundles marketplace** — solo dev; overkill.

If a future task tempts you to re-add generic app cruft here, don't — that was the reason to adapt rather than adopt.

## Relationship to existing rules and skills

- **Plan mode** produces the plan this spec references; run this skill right after.
- **G1 / R3** — clarify before assuming; plan+approval for big changes. Step 1's ASSUMED-resolution is G1 applied at spec time.
- **G2 / R2** — cite-then-verify. Every forward-contract ref and cross-file symbol is verified `path:line`.
- **G3** — honest verification. Success Criteria say what will be checked and how.
- **R7 / R8 / R8-extended** — the analyze gate is the artifact-level layer above R7's code-level invariant tracing and R8's end-to-end walk; the Forward Contract section is R8-extended made explicit.
- **rigorous-data-audit** — for data-critical mods, this skill precedes it; the spec's crash-recovery/admin scenarios feed that audit.
- **dayz-mod-workflow** — consumes the approved spec and implements.
- **pre-output-discipline** — the discovery→generation gate; writing the spec is a generation step, so validate discovery first.
- **Pre-code ceremony routing (SP-050)** — which gate applies when is fixed by the single source: `<system-notes>\workflow.md` §Árbol de decisión pre-código. This skill is Step 2 of that tree; Grill A precedes it, Grill B and `dayz-mod-workflow` follow.

## Provenance

Adapted from github/spec-kit, reviewed 2026-07-01. Sources: `templates/spec-template.md`, `templates/commands/analyze.md`, `templates/commands/clarify.md`, `templates/checklist-template.md`. Generic scaffolding excluded by design.

## Forward Contract for injected objects

[EXACT][CLAIM-R21-FEATURE-INJECTED-CONTRACT] When a plan injects an object
that replaces another implementation (planner, bridge, transport, repository),
the Forward Contract MUST enumerate every field and method the consumer reads,
not only the field that motivates the test double. Grep all accesses on the
injected value and prefer the existing result type over a partial look-alike.

The failure mode is concrete: a consumer can read `.status.value`, `.proposal`
and `.source` even when a plan mentions only `.proposal`; the partial object
then fails at runtime despite satisfying the prose spec. Verified example:
`GameMaster/tools/gm/service.py:209-218`; the complete existing result contract
is `GameMaster/tools/gm/ollama_planner.py:43-50`.
