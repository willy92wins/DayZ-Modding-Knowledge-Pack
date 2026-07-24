# Spec Quality Checklist ("unit tests for English")

Run against the feature spec BEFORE writing code. This checks the spec the way tests check code. A spec that fails is not Ready-to-implement. This is a gate on the English; `rigorous-data-audit` is the gate on the code.

Mark each `[x]` pass / `[ ]` fail. Any fail → fix the spec, do not proceed to code.

## Measurability

- [ ] CHK001 Every Success Criterion is measurable (a check could pass/fail it deterministically).
- [ ] CHK002 No vague adjectives as criteria ("se ve bien", "funciona", "robusto", "fluido") — each is replaced by a metric or an observable state.
- [ ] CHK003 Numeric criteria have units and a threshold (km/h, cm, ms, count), not "fast" / "close".

## Testability / verification path

- [ ] CHK004 Every acceptance scenario is Given/When/Then with concrete in-game repro steps.
- [ ] CHK005 Every criterion and scenario has a verification path in the plan — offline (grep/python/py3d/RPT) or assigned to the R5 batched in-game session.
- [ ] CHK006 Offline-verifiable criteria are marked offline (not sent to an in-game cycle unnecessarily — R5).

## Assumptions & clarity

- [ ] CHK007 Every guess is marked `ASSUMED`.
- [ ] CHK008 Every assumption that decides correctness (path, classname, version, format) is resolved (AskUserQuestion) or explicitly deferred with a reason (G1).
- [ ] CHK009 No unresolved placeholders left in the spec (TODO, `???`, `[...]`, template guidance comments).

## Cross-file references (G2/R2)

- [ ] CHK010 Every Forward-Contract symbol is verified `path:line` OR explicitly marked `[UNVERIFIED]`.
- [ ] CHK011 Every classname / selection / bone / proxy path / stringtable key the code will emit or the next phase will read actually exists (opened the file, not from memory).
- [ ] CHK012 No `[UNVERIFIED]` ref remains that the code depends on for correctness. API-index evidence distinguishes `active|commented|missing`, records source `path:line` and compile guards; a zero-record v1 result is not treated as proof of absence.

## Scope & consistency

- [ ] CHK013 Out-of-scope section is explicit (non-goals listed).
- [ ] CHK014 One canonical term per concept — no synonym drift across sections.
- [ ] CHK015 No two criteria/scenarios contradict each other.

## Data-critical escalation

- [ ] CHK016 If the feature touches persistence / progression / async queues / admin commands: crash-recovery and admin-intervention scenarios (R8) are present, AND `rigorous-data-audit` is queued before release.

## Result

- Pass count: __ / 16
- If <16: list failing IDs and fix the spec before implement.
