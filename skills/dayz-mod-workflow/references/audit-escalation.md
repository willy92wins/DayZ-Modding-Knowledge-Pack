# Audit escalation — severity discipline + multi-agent isolation

> Extracted from dayz-mod-workflow/SKILL.md 2026-07-07 (F3).
>
> Sectioned §8 (severity inflation in audit reports) and §9 (multi-agent audit context isolation) from the core SKILL.md. These OVERLAP the `rigorous-data-audit` skill (the operational 7-step, multi-auditor workflow) — use that skill to RUN a data-critical audit; this file is the workflow-protocol note on labelling severity and keeping parallel auditors independent.

---

<!-- [merged 2026-06-05 from .claude\skills user copy during plugin-canonical migration] -->
## 8. SEVERITY INFLATION IN AUDIT REPORTS (added 2026-05-15)

Pattern observed in LFPowerGrid audits: labeling as `P1 — crash`
findings that in reality are `P2 — recoverable VM exception, server keeps
running`. Cause: extrapolation from log message (`String CORRUPTED`) to
actual behavior (process dies) without verification.

### Operational antidote before drafting audit findings

1. Reproduce bug on local server (`dayz-launch-test` if available).
2. Log complete bug cycle (load -> execute -> autosave -> reload).
3. Distinguish:
   - `crash` <-> process dies, server drops, requires restart.
   - `VM exception` <-> Enforce VM exception, log spam, execution continues.
   - `corruption` <-> bad data persists, code runs with it.
   - `degradation` <-> feature functions worse but runs.
   - `cosmetic` <-> visual only / no functional effect.
4. Finding label uses concrete term from step 3, not "crash"
   as generic.

### Caso real

Session `Review audit findings and create remediation plan` 2026-05-14
(`local_daee0706`): "Server boots: NO" in `before vs after` table was
deflated to "server does boot, it just throws an error" after correction by
user.

### Referencia cruzada

R4 + R30 del `CLAUDE.md` global.

---

<!-- [merged 2026-06-05 from .claude\skills user copy during plugin-canonical migration] -->
## 9. MULTI-AGENT AUDITS: MANDATORY CONTEXT ISOLATION (added 2026-05-16)

Post-mortem documented in `LF_VStorage_dev/skills/rigorous-data-audit/postmortem.md`
(session `Evaluate GitHub project` 2026-05-14): 4 auditor agents
"converged" on confabulated findings because they read same conventions
doc and inherited same bias. Convergence was interpreted as rigor;
it was coupling.

### Operational rule for future multi-agent audits on DayZ code

- Each agent verifies from independent vanilla source / `path:line`.
- Prohibited for two agents to cite "X says same thing" as cross-evidence
  when both read the same doc.
- At least one agent must run **adversarial** — without access to conventions
  doc, only to actual code, checking findings of others.
- **Random sampling (≥20%) of findings before applying them**: if they fail
  adversarial recheck, discard entire audit, not just suspicious
  items. Confabulation is systemic, not per-item.

### Symptoms of confabulated audit triggering re-check

- Large absolute metrics ("47 issues found") without `path:line` per
  item.
- Defensive OR branches labeled as bug when they are designed tolerance.
  Case: `classify_lod()` with Arma 3 + DayZ bands — the OR branch IS the design,
  not a bug.
- Inflated severity (P1 on items that are P2-P3). Cross-check with section 8.
- Anomalous convergence among agents that should be independent — if 4
  agents "find" the same thing and read same conventions doc, it is
  shared bias, not triangulation.

### Operational definition of VERIFIED

For a finding to be applied:

1. Has concrete `path:line` in real code (not in doc).
2. Snippet of code violating rule is pasted.
3. Snippet of fix with applicable diff is pasted.
4. At least one agent without shared context verified it separately.

Without these four, finding is marked `❓ possible confabulation` and is NOT
applied.

### Referencia cruzada

R8 (verification during, not only at the end) + R22 (honest verification in
output) + R31 (pitch language prohibited without evidence) of global
CLAUDE.md.
