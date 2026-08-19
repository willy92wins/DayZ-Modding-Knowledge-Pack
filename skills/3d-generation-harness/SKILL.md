---
name: 3d-generation-harness
description: "End-to-end disciplined harness for generating a complete 3D item: research → plan → build → roast → ship, with hard gates between phases. Forces multi-view reference research before any code (nothing modeled from memory), a plan with verifiable pass/fail criteria per part, per-component build checkpoints, an adversarial self-review ('roast') whose output is a defect list with evidence, and a scored ship gate. Use whenever the user asks to create/generate/design a full 3D object end-to-end, wants it validated against real references, says 'roast it', 'no des nada por supuesto', 'hazlo con el harness', 'compruébalo todo', asks for a production-ready / vanilla-parity model, or wants a disciplined rebuild after an in-game failure. Orchestrates blender-assembly, blender-visual-review, dayz-model-pipeline and dayz-p3d-audit, and optionally hunyuan3d-local (AI-generation ladder) if installed — they own the HOW; this skill owns the gates. Triggers: harness 3D, genera un modelo 3D completo, roast del modelo, modelo desde referencias."
---

# 3D Generation Harness

This harness exists because the default failure mode of LLM-driven 3D generation is **confident garbage**: a model built from memory of what the item "probably" looks like, reviewed by the same process that built it, and declared done because nothing crashed. The harness inverts every one of those defaults:

- Nothing is modeled from memory — a research dossier with multi-view references comes first.
- Nothing is declared correct without a number or a render behind the claim.
- The review phase is adversarial by design: its output is a defect list, not a verdict.
- Every phase ends in a gate. A gate that doesn't pass stops the pipeline; it is never "noted and continued past."

The harness governs sequencing and gates. The construction techniques live in `blender-assembly`; the capture/diagnosis techniques in `blender-visual-review`; AI generation → optionally invoke the external `hunyuan3d-local` skill if installed (not shipped in this pack; it contains the canonical routing ladder: local → fal → paid APIs); DayZ export and audit in `dayz-model-pipeline` and `dayz-p3d-audit`. Read each at the phase that needs it.

## Pack surface

This pack ships `blender-assembly`, `blender-visual-review`, `dayz-model-pipeline`,
`dayz-p3d-audit`, `ai-3d-to-dayz` and `dayz-pbo-build`. Names such as
`hunyuan3d-local` are optional external skills and are **not** included here.
If they are absent, skip the AI-generation route and stay on the parametric
`blender-assembly` path. Do not invent those skills or their APIs.

## Pipeline overview

```
Phase 0  INTAKE      what / for what / route          → Gate I
Phase 1  RESEARCH    dossier: views, dims, parts      → Gate R
Phase 2  PLAN        breakdown + viability tests      → Gate P
Phase 3  BUILD       per-component, checkpointed      → (component gates)
Phase 4  ROAST       adversarial review, rubric       → Gate V
Phase 5  FIX LOOP    one diagnosis at a time          → re-roast
Phase 6  SHIP        full-evidence final gate         → Gate S
```

Every gate produces a written PASS/FAIL with the evidence that justifies it, appended to the evidence ledger (see Evidence convention). FAIL means fix or return to the previous phase — never proceed.

## Phase 0 — Intake & Routing (Gate I)

Answer these before anything else; ask the user only for what cannot be inferred:

1. **What item, exactly?** "A rifle" is not an answer; "an AKM-pattern rifle, wooden furniture, DayZ-era condition" is.
2. **Target use:** DayZ mod (which slot/behavior), generic game asset, render-only? This sets the poly budget, LOD plan, and which export/audit skills apply.
3. **Route:** parametric hard-surface → this harness with `blender-assembly`. Organic/sculpted → AI generation: optionally invoke the external `hunyuan3d-local` skill if it is installed on the machine (not shipped in this pack; it contains the canonical routing ladder: local → fal → paid APIs) for the base mesh, then this harness resumes at Phase 4 (the roast and ship gates apply to AI-generated meshes too — *especially* to them). For DayZ-bound AI-generated assets, the DayZ-specific pitfalls (retopo of non-manifold, _nohq bake, handoff) live in the skill `ai-3d-to-dayz` — this harness owns the generic gates/discipline.
4. **Budget:** LOD0 tri range (for DayZ, anchor to the vanilla equivalent's counts, not to taste).

Gate I passes when all four have explicit answers written down. An unanswered item is a question to the user, not an assumption.

## Phase 1 — Research Dossier (Gate R)

NEVER model from memory. Training-data recall of an object's shape is a hypothesis, not a reference. Build the dossier per `references/dossier-template.md`:

1. **Multi-view references:** image-search the item until you hold at least 4 distinct viewpoints (front, side, top, and a 3/4) plus close-ups of every detail zone (grip, latches, fasteners, seams). For DayZ items, also pull the vanilla equivalent's model as a 1:1 in-scene reference (`dayz-model-pipeline` import path).
2. **Dimension table:** overall L×W×H from **two independent sources**, plus ≥5 landmark measurements (e.g. barrel length, grip height, wheel diameter). Where no source exists, write `ESTIMATE ±X%` explicitly — an unlabeled estimate is a confabulation.
3. **Part inventory:** every visually distinct component, named. This becomes the build breakdown.
4. **Unknowns list:** everything you could not verify, stated as unknown, with the decision (resolve / accept with tolerance / ask user). The unknowns list is the anti-assumption mechanism: an empty unknowns list on a non-trivial item is itself a red flag.

Gate R passes when: ≥4 viewpoints on file, dimension table sourced or explicitly estimated, part inventory complete, unknowns explicit. The dossier is saved with the evidence ledger — the roast (Phase 4) will be scored *against it*, so a thin dossier makes the roast blind.

## Phase 2 — Plan with Viability Tests (Gate P)

Using the dossier, write the plan **and its tests before any code** (the AGENTS-R26 rule: a plan without verifiable criteria gets returned, not improvised around):

1. **Build breakdown:** ordered part list mapped to techniques (which `blender-assembly` rule builds each part).
2. **Connection map + detail list:** per `blender-assembly` Phases 1/1.5 — every joint, every detail feature with size.
3. **Viability tests (the contract):** a `TESTS` block stating, per part: expected dims ±5% vs the dossier table, expected joint overlaps, expected `verify_mesh_integrity` result (closed/open, ngon tolerance). And model-level: total tri range, the named landmarks the final render must match, and which downstream audits apply (DayZ: `dayz-p3d-audit` winding + structure).

Gate P passes when every part in the breakdown has at least one numeric or visual pass/fail criterion. A part with no criterion is a part that cannot fail — which means it cannot be verified either.

## Phase 3 — Build (per-component gates)

Execute the plan under `blender-assembly` discipline (load its helper library first). Per component:

1. Build → `verify_bounds` + `verify_overlap` against the connection map.
2. `verify_mesh_integrity` after every boolean/modifier/loft.
3. **Component checkpoint:** quick visual capture of complex parts before building on top (`blender-visual-review`, component checkpoint section). High-risk parts: two parameter variants, choose from renders.
4. Log each component's results in the evidence ledger. A component gate failing stops the build at that component.

Do not "improve" the plan mid-build. A discovered necessity goes to the ledger as a plan deviation with one line of justification; a discovered nicety is scope creep and gets dropped.

## Phase 4 — Roast (Gate V)

The roast is a separate pass with an inverted objective: **find what is wrong, with evidence**. It is not a summary of the build and not a victory lap. Protocol:

1. Fresh full captures via `blender-visual-review` (`vr_capture`, all four angles, scale cube in frame) plus close-ups of every detail zone listed in the dossier.
2. Walk `references/roast-rubric.md` — 8 categories, scored 0–2, each verdict citing its evidence (render filename + what in it, or measured number vs dossier number). "Looks fine" is not evidence; the banned-phrases rule below applies hardest here.
3. **Dimension audit:** table of measured dims (from `vr_capture`'s numeric output) vs dossier dims, with % deviation per landmark. Deviations >5% are defects unless the plan declared a tolerance.
4. **Detail audit:** every feature in the detail list, present or missing. A missing planned feature is automatically a defect.
5. Output: a ranked defect list (severity high/medium/low) plus the rubric score.

Anti-self-congratulation rule: if the first roast returns **zero defects**, that result is treated as suspect, not as success — re-roast with new camera angles and tighter close-ups. If the second pass also returns zero, accept it. (A first build that survives first contact intact is rare enough that the cheap second look is always worth it.)

Gate V passes when: no rubric category scores 0, total ≥ 13/16, and no high-severity defects remain open. Otherwise → Phase 5.

## Phase 5 — Fix Loop

Per `blender-visual-review` discipline: fix **one diagnosis at a time**, re-render the **same angles**, keep the before/after pair. After fixes, re-run only the affected rubric categories plus mesh integrity on touched parts; a full re-roast is required only when fixes touched ≥3 components. Loop until Gate V passes. If three loops fail on the same defect, stop and re-plan that component (the plan was wrong, not the execution).

## Phase 6 — Ship Gate (Gate S)

The final gate re-checks everything once, on the final state:

1. All numeric gates green: `audit_all`, `verify_mesh_integrity` on every part, tri count inside budget.
2. Gate V passed with the current geometry (not an earlier iteration's renders).
3. Target-specific audits: for DayZ, run `dayz-p3d-audit` after export (absolute winding is decided there, never from a Blender render — hard guardrail in `blender-visual-review`), ride-height/scale parity vs the vanilla reference.
4. Evidence ledger complete: dossier, plan+tests, per-component logs, roast reports with renders, fix before/afters, final rubric.

Only after Gate S does the item hand off to packaging (`dayz-pbo-build`) or delivery.

## Evidence convention

One folder per item: `_harness/<item>/` containing `dossier.md`, `plan.md` (with the TESTS block), `ledger.md` (append-only: every gate verdict with timestamp and evidence reference), `renders/` (named `<part>__<angle>__<iter>.png`), `roast_N.md`. The ledger is append-only on purpose: a gate verdict is never edited, only superseded by a later entry.

## Honesty rules (apply in every phase)

- Every claim about the real item traces to a dossier entry. Every claim that the model is correct traces to a render or a number in the ledger.
- Banned as evidence: "looks fine", "looks correct", "should be right", "as expected" without a comparison, "probably". If one of these is the only support for a verdict, the verdict is UNVERIFIED, and UNVERIFIED ≠ PASS.
- Unknown stays unknown until measured. Saying "no lo sé, lo mido" is always a valid intermediate answer; a confident guess is not.
- The roast reports defects to the user as found — including defects in the plan or in this harness itself. A harness that hides its misses teaches nothing.

## References

- `references/dossier-template.md` — the Phase 1 research dossier template.
- `references/roast-rubric.md` — the 8-category scored rubric with per-category evidence requirements.
