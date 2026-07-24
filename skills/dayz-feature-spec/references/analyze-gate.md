# Analyze Gate — cross-artifact consistency (read-only)

A non-destructive pass over the feature's artifacts before spending an in-game test cycle. Adapted from spec-kit `templates/commands/analyze.md`, wired to DayZ (in-game test = acceptance; forward-contract refs must exist).

Run AFTER the code and task list exist, BEFORE the R5 batched in-game test.

## Operating constraints

- **READ-ONLY**: MUST NOT modify any file. Produce a report; offer remediation only on explicit approval.
- **Constitution authority**: `CLAUDE.md` (global G1–G6 + project R1–R9) is non-negotiable in this scope. A conflict with a MUST-level rule is automatically CRITICAL and requires changing the spec/plan/code, not reinterpreting the rule.

## Inputs

- Spec (`references/spec-template.md` instance for this feature)
- Plan (Plan-mode output / HANDOFF section)
- Task list / HANDOFF pending items
- The code produced so far
- `CLAUDE.md` (global + project)

## Detection passes

Focus on high-signal findings. Do not dump raw artifacts into the report.

### A. Coverage (the DayZ core)

- Every acceptance criterion / SC has a **verification path** (offline check or R5 in-game assignment). Missing path → CRITICAL.
- Every requirement maps to ≥1 task/code change; every task maps to ≥1 requirement. Orphans both ways → HIGH.
- Every Forward-Contract symbol is verified to exist (`path:line`). Any `[UNVERIFIED]` the code depends on → CRITICAL (this is the LFQuad Fase B P1 class: consumer references a symbol that isn't there).

### B. Contradiction & drift

- Spec ↔ code contradictions (spec says bolt→-Z, code ejects +Z) → HIGH.
- Terminology drift (same concept, different name across spec/plan/code) → MEDIUM.
- Duplicate / near-duplicate requirements → MEDIUM (consolidate).

### C. Ambiguity

- Vague criteria that survived the spec checklist (should be zero) → HIGH.
- Unresolved `ASSUMED` that decides correctness → CRITICAL.

### D. Constitution alignment

- Any spec/plan/code element conflicting with a CLAUDE.md MUST rule (e.g. R2 unverified API, R7 invariant not traced to all call-sites, R6 comment style) → CRITICAL for correctness rules, HIGH for style.
- Missing mandated gate (e.g. data-critical change without rigorous-data-audit queued) → CRITICAL.

## Severity heuristic

- **CRITICAL**: constitution MUST violation; criterion with no verification path; `[UNVERIFIED]` dependency; unresolved correctness-deciding ASSUMED; missing mandated audit.
- **HIGH**: spec↔code contradiction; requirement with zero coverage; untestable acceptance criterion; orphan task/requirement.
- **MEDIUM**: terminology drift; duplicate requirement; underspecified edge case.
- **LOW**: wording/style not affecting execution.

## Report format

```
## Analyze Report — [feature]

| ID | Category | Severity | Location | Summary | Recommendation |
|----|----------|----------|----------|---------|----------------|
| C1 | Coverage | CRITICAL | spec SC-002 | no verification path | add offline py3d check or R5 assignment |

### Coverage summary
| Criterion / Requirement | Verified/Task? | Where | Notes |

### Forward-contract refs
| Symbol | Exists? | path:line or [UNVERIFIED] |

### Metrics
- Requirements / criteria total
- Coverage % (criteria with a verification path)
- CRITICAL / HIGH / MEDIUM / LOW counts
```

## Next actions

- If any CRITICAL: resolve before the in-game cycle. Do not build/deploy.
- If only MEDIUM/LOW: may proceed; note improvements.
- Offer: "Suggest concrete remediation edits for the top N?" — do NOT apply automatically (R3).

## Guidelines

- NEVER modify files (read-only).
- NEVER hallucinate a missing section — report it as absent.
- Prioritize constitution violations.
- Cite specific instances (`path:line`, SC-###), not generic patterns.
- Report zero issues gracefully with the coverage metrics.
