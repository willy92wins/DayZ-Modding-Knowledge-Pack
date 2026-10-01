---
name: rigorous-data-audit
description: "Use when: audit X, revisa a fondo, release-safe?, esto puede romper progresión, data loss, OnStoreSave/OnStoreLoad. Persistence/state-machine pre-release audit. Not cosmetic/UI: dayz-ui-development; not output-discipline: pre-output-discipline."
---

# Rigorous Data Audit

Procedure for auditing mods where a bug equals lost player progression. Built
from a real failure: six parallel Opus reasoning agents reviewed LF_VStorage
1.4.6 from independent angles and signed off as "release-safe" — an external
implementer-grade audit then found 12 VULNs (P0–P3) the agents missed. This
skill encodes the lessons.

A second failure refined it further: a loose application of this skill's
"parallel agents + consolidation" shape — pointed at fact-checking a corpus —
produced an audit that was **~55% confabulated**, because there was no
adversarial verification step between "agents reported it" and "acting on it".
Step 3 below exists because of that. See `postmortem.md` for the case.

Read `references/why-this-skill-exists.md` for the full retrospective if you
want the original case study.

## When to invoke

Trigger automatically when any of these are true:

- Mod touches persistence, save files, state machines, or async work queues
- A bug would cause **silent data loss** (lost items, wrong sids, money loss)
- User asks for "audit", "revisa a fondo", "release-safe?", "puede romper progresión"
- User just applied multiple fixes and wants verification before rebuild/test
- User hands you findings from an external auditor and asks you to verify

If the change is cosmetic or UI-only, this skill is overkill — skip it.

## Why reasoning alone is insufficient

The reasoning agents that signed off on LF_VStorage 1.4.6 were not lazy. Each
read the relevant code and produced a coherent argument. They missed bugs
anyway. Looking at the 12 VULNs the implementer-grade audit caught:

| Failure mode | VULN examples | Why reasoning misses it |
|---|---|---|
| Path-helper inconsistency | VULN-003 (`.tmp` vs `.lfv.tmp`) | Bug is enumerable, not deducible — reasoning agents trace happy paths and see helpers used in isolation |
| Sidecar/marker not cleaned | VULN-008 (`.restoring`/`.manifest.json` survive `DeleteContainerFiles`) | Symmetric obligation — every Write needs a Delete. Reasoning agents check the writer side, not the cleanup side |
| Alternative entry point skips invariant | VULN-009 (sync path leaves stale marker), VULN-001 (kill-switch not durable) | Agent fixates on the canonical async path; the synchronous shortcut is "obviously similar" so gets a glance |
| Flag lifecycle asymmetry | VULN-010 (admin clears flag while sidecar still references stale state) | Two state stores must move together; reasoning agents check each store internally |
| Pre-super gate placement | VULN-004 (gate runs after vanilla super) | Order of operations within an EE hook is invisible from "is the gate present?" |
| Sanity caps missing | VULN-011 (LFV2 count fields uncapped) | Threat model not in scope of the agent's prompt |

Five of those are **enumerable mechanically** — a script + grep finds them in
under a minute. Three are **cross-actor** — one writer + a different deleter +
admin override. Reasoning across 3+ files is where Opus agents thin out.

And separately: agents *report* findings convincingly whether or not the
findings are real. The fix is three-pronged: cheap mechanical pre-checks
first, then reasoning agents specifically prompted on the gaps reasoning is
bad at, then an adversarial verification pass before any finding is trusted.

## Workflow

Seven steps in two phases.

- **Phase A (steps 1–6)** is the audit. It runs entirely from the codebase
  and ends with a verified findings list and fixes applied.
- **Phase B (step 7)** is in-game validation. A clean audit is necessary but
  not sufficient for "release-safe".

Skipping early steps makes later ones less effective — do not skip. Each step
below carries two annotations in a quote block: **Model** (the model tier the
step's work should run on) and **Done when** (the explicit exit criterion —
do not advance until it holds).

## Phase A — Audit (steps 1–6)

### Step 1 — Mechanical pre-checks (cheap, deterministic, fast)

> **Assignment** — run deterministic checks directly; delegate only if assigned and useful.
> **Done when** — a written list of mechanical findings exists (zero items if
> clean), each citing `path:line_start-line_end`, ready to paste into step 2.

Run before spawning any agents. Each check is a grep + table walk; together
they take ~10 minutes and catch the bookkeeping-style bugs reasoning misses.

The four reference docs give the procedures. Read them before running:

- `references/path-naming-matrix.md` — catches path-helper drift (VULN-003 class)
- `references/sidecar-cleanup-symmetry.md` — catches missing cleanup on delete/reset (VULN-008 class)
- `references/entry-point-audit.md` — catches alternative entry points skipping invariants (VULN-009, VULN-001 class)
- `references/flag-lifecycle-audit.md` — catches flag/sidecar state-store divergence (VULN-010 class)
- `references/crash-safe-evidence-and-bundles.md` — authoritative evidence indexes and multi-root publication
- `references/authority-and-loopback.md` — durable authority publication and authenticated-localhost provenance
- `references/incremental-rebuild-traps.md` — atomic-to-phased conversion hazards

Plus the existing structural check:

- `references/state-machine-matrix.md` — catches illegal transitions and double-counted state
- **Full-ancestry super-chain walk** (added 2026-07-05): whenever an invariant depends
  on "leaf class chains super" (physical Open/Close failsafes, EE* hook propagation,
  modded-base overrides), grep the override in EVERY class of the inheritance chain up
  to the modded base — never just the leaf. See dated section at end of this file.

This list goes into step 2's agent prompts as known-context so agents do not
waste cycles re-finding.

### Step 2 — Cover the relevant audit angles

> **Assignment** — the orchestrator chooses reviewer family, effort and lane count
> from risk and available budget; this skill does not authorize extra agents.
> **Done when** — relevant angles are covered; every finding pastes the literal
> code snippet it is about (not just a line citation) plus severity. A
> "finding" that only describes code without pasting it is bounced back as
> SUSPECT, not accepted.

The eight angles below are coverage dimensions, not eight required agents or reports.
Use one reviewer for a bounded audit; distribute independent angles only when delegated
and useful. Bound delegated reports (≤700 words, no narrative).

**Show, don't tell.** A claim of the form "this code has bug X" must include a
copy-paste of the actual code, with `path:line`. A description without the
snippet is a hypothesis, not a finding — the next step cannot verify it and it
will be dropped. This requirement is what makes "verified" something grep-able
rather than narrative.

Coverage dimensions; mark non-applicable angles with a reason:

1. **Persistence & atomic flow** — write barriers, fsync semantics, `.tmp`/`.bak1`/`.bak2` rotation, header/footer verification, partial-write recovery
2. **State machine** — every transition, every gate, every "should never happen" branch
3. **Async queues & cross-tick safety** — re-entry on the same sid, cancellation, queue-during-iteration, shutdown drain
4. **Engine hooks (EE*)** — entry-point gating placement, super-call ordering, EEDelete vs EEKilled symmetry, OnStoreSave/OnStoreLoad cadence
5. **Admin commands** — input validation, path traversal, race with running queues, sidecar ↔ in-memory consistency
6. **Recovery paths** — what crash leaves on disk, what boot consumes, degraded modes, partial-state quarantine
7. **Action layer (pre-super gates)** — every action handler that might fire while a container is virtualized; gates run **before** vanilla super
8. **Threat model & input bounds** — sanity caps on counts, sizes, lengths from disk; bound check before allocation

Full prompts are in `references/audit-prompts.md`. The implementer-grade
prompt for step 4 is also there.

### Step 3 — Adversarial verification + consolidate

> **Assignment** — follow the orchestrator's review budget. Citation checking and
> judging whether an inference follows are different checks; neither model brand proves them.
> **Done when** — every row in the deduped table has been confirmed against
> the real file (by the independent verifier or by you); the 20% self-sample
> passed (<10% confabulation); each row is labelled defect vs improvement.

This is the step that turns "agents reported it" into "it is real". It exists
because skipping it once produced a ~55%-confabulated audit (`postmortem.md`).
Three sub-steps, in order:

**3a — Verify every cited snippet against the real file.** Open the file at
the cited range and confirm it says what the agent's pasted snippet claims.
Reasoning agents drift on line numbers, copy citations from sibling files, and
occasionally invent plausible ranges wholesale. A finding whose snippet does
not match the file is not a finding — re-derive it or drop it. Every cause in durable
memory brings file+pattern+number of matches with n>0 (LL-414); without the trio it is a
hypothesis, and adjudication between rival mechanisms requires a prediction that only
the new mechanism compels.

**3b — Independent verifier pass.** When an independent pass is assigned, use a
reviewer from another family with a **fresh context that has not seen the angle reports**.
If it is unavailable, declare that limitation; do not silently claim independence. Hand it only the bare list of claims
(claim + location, no reasoning, no severity). Its task: for each
claim, open the cited file and return TWO separate verdicts — "does the
file actually say this" (`snippet_matches_file`) and "does the conclusion
follow from that code" (`inference_holds`, judged without seeing the
auditor's reasoning) — pasting the relevant lines (LL-270). A claim the
independent verifier cannot confirm on either verdict is NOT actionable
until the orchestrator re-reads it — dropping it silently is how a real
finding disappears. And a refutation rate of 0% is a reason to distrust the
verifier, not to trust the batch: the run that produced this rule refuted
0 of 67 claims, and TERR-2 arrived `CONFIRMED` on a false inheritance
premise. This is adversarial on purpose — convergence between
agents that *shared* context (the same spec, the same conventions doc) is
contagion, not confirmation. The verifier must not share that context.

**3c — 20% self-sample gate.** Before trusting the consolidated table, pick
20% of the findings at random and verify them yourself by opening the files.
If more than 10% of the sample is confabulated, the audit is not trustworthy —
re-run step 2 with stricter prompts, or discard it. Do not act on an audit
that fails this gate.

Then build the single deduped table:

| ID | Severity | Title | File:Lines | Found by | Verified by | Defect/Improvement | Status |
|---|---|---|---|---|---|---|---|

- Severity is yours to assign — do not trust the agent's self-reported
  severity. P0 = data-loss possible. P1 = recovery required. P2 = degraded
  behavior. P3 = code smell.
- **Defect vs improvement.** Defensive coding is not a bug. An `OR` branch
  that accepts two input formats, a tolerant parser, a redundant guard — those
  are robustness, not defects. Label them "improvement" at most; do not file
  them as findings or inflate their severity. The 55%-confabulated audit's
  single biggest error class was calling tolerance a bug.

### Step 4 — Implementer-grade cross-actor pass

> **Assignment** — an independently assigned reviewer capable of cross-actor reasoning.
> **Done when** — the agreed product checks and review budget are satisfied. A new
> finding needs executable evidence to block. The single stop-rule owner is
> `gates-ledger` §Cuándo para un bucle; do not create an until-clean loop here.

This is the step that, in retrospect, would have caught the 12 VULNs.

Give the assigned reviewer a fresh context — no audit history, no agent output,
no priors. Hand it the codebase, the README/spec, and this single
prompt: *"Find every way this code can lose, corrupt, or silently misroute
player data. Trace each writer to every reader, each sidecar to every cleanup
site, each admin flag to every consumer. Where any of those triples is
incomplete, that is a bug."*

Full prompt: `references/audit-prompts.md` § "Implementer-grade pass".

The cross-actor framing matters. Reasoning agents prompted "audit this layer"
look within the layer; they do not chase across actors. The implementer-grade
prompt explicitly says "trace across actors".

If this agent finds nothing, that is the signal that the audit is converging.
If it finds a defect, reproduce it, classify its impact, and recheck the affected
path within the agreed budget. Escalate remaining work when that budget is exhausted.

### Step 5 — Apply fixes

> **Assignment** — use the execution route authorized by the orchestrator.
> **Done when** — every applied fix names the check or angle that caught it;
> a re-grep confirms the pattern is gone everywhere; no fix exceeds the
> minimum verified change.

Standard editing flow, with four specifics:

- For every fix, write down which mechanical check or which agent angle caught
  it. If a fix has no source, it is a hunch — re-verify before shipping.
- After each fix, re-grep to confirm the bug pattern is gone everywhere (not
  just at the cited line). VULN-003-class bugs often have siblings.
- **Minimum verifiable patch.** Apply only what step 3 verified. When the
  verified instruction is "add bands X before the else", add bands X — do not
  also add Y, Z, W because a sibling (unverified) finding suggested them.
  "While I'm here" is exactly how a patch gets bloated with
  confabulation-derived changes.
- **Do not ship artifacts from an un-reverified audit.** Packaging a `.skill`,
  cutting a release, or handing the user a patch file based on findings that
  did not pass step 3 is how false confidence propagates. Applying a patch
  costs minutes; the bad release it enables costs hours.

### Step 6 — Re-audit subset

> **Assignment** — mechanical checks directly; targeted reasoning under the
> same review budget and family-independence contract.
> **Done when** — mechanical pre-checks plus the two most-changed angles run
> clean. A new finding loops back to step 5 **once**; a second reappearance stops
> the loop (ORCHESTRATOR_NEEDED with backlog).

Re-run mechanical pre-checks (cheap) plus the two angles whose code changed
most. If a new finding appears, loop back to step 5 once. If a finding of the same
family reappears, the defect is design, not patching: stop, file the remainder as
numbered backlog and escalate. Stop rule (owner): `gates-ledger` §Cuándo para un
bucle — the product gate closes the loop, a finding blocks only with an executable
repro, the budget is two rounds (rev. 2026-09-02; replaces «until zero critical/major»).
For each value crossing N layers, a test executes the two layers of each joint WITHOUT test doubles
(LL-473); the mutation to test deletes the COUPLING, and the fix is only accepted when
the RECEIVER repeats the exact mutation and sees the control die.

## Phase B — In-game validation (step 7)

### Step 7 — In-game test gate

> **Model** — n/a. The user runs these; the skill cannot.
> **Done when** — all four scenarios below pass in-game. Only then is
> "release-safe" earned.

Audit clean ≠ release-safe. Before declaring release-safe:

- Player connects with a virtualized container, server restart, container
  intact (basic round-trip)
- Crash mid-virtualize (kill server) → reboot → recovery completes, no data
  loss, no orphan markers
- Admin reset on a virtualizing container → stable state after reset
- All sids on disk after a long session match player intent (no orphans, no
  ghosts)

The skill cannot run these tests for the user. The skill's contribution is to
make the audit phase trustworthy enough that the in-game test phase is short.

## Anti-patterns

Watching for these saves rounds:

- **Declaring "release-safe" after step 2.** Steps 3–7 are not optional.
  Phase A alone is never "release-safe" — Phase B is the gate.
- **Using eight identical agents instead of eight different angles.** Eight
  reasoning agents prompted "audit this code" produce eight redundant reports.
  The angles must differ.
- **Skipping step 1 because "the agents will catch it".** They demonstrably
  do not.
- **Treating defensive coding as a bug.** A tolerant `OR` branch, a redundant
  guard, a parser that accepts two formats — robustness, not defects. Calling
  tolerance a bug was the 55%-confabulated audit's biggest error class.
- **Trusting consolidated metrics without drill-down.** "34 VERIFIED, 9
  CONFABULATED" is smoke if it is a summed number with no per-finding
  click-through. Metrics without traceable findings are sums of guesses.
- **Acting on an audit that has not passed step 3.** The agents' report is a
  set of hypotheses. Adversarial verification (independent verifier + 20%
  self-sample) is what makes it a set of facts. No verification = do not act.
- **Trusting "convergence" between agents that shared context.** Four agents
  citing the same bug because they all read the same conventions doc is
  contagion, not confirmation. The step 3 verifier must have fresh context.
- **Re-running the same audit after fixes.** Step 6 changes the cheap checks
  plus the two layers most edited — full 8-angle re-runs waste budget.
- **Serializing independent work after parallel delegation was authorized.** If multiple lanes are assigned, dispatch them together
  so they run concurrently.
- **Shipping a `.skill` / release / patch file from un-reverified findings.**
  Cheap to apply, expensive to walk back.
- **Reading a short-circuit finding as green (LL-481).** A gate skipped on PRECONDITION
  (dirty tree, unreadable config) wears the same face as a pass: verify the gate evaluated
  what changed, and count exit codes, not findings. Verification on a dirty tree is not
  verification.

## References

- `references/why-this-skill-exists.md` — full retrospective on the LF_VStorage 1.4.6 case
- `postmortem.md` — the ~55%-confabulated audit and the eight lessons that hardened step 3 and step 5
- `references/audit-prompts.md` — eight angle prompts + implementer-grade pass prompt
- `references/path-naming-matrix.md` — mechanical check #1
- `references/sidecar-cleanup-symmetry.md` — mechanical check #2
- `references/entry-point-audit.md` — mechanical check #3
- `references/flag-lifecycle-audit.md` — mechanical check #4
- `references/state-machine-matrix.md` — structural state-transition check
- `references/crash-safe-evidence-and-bundles.md` — crash-safe evidence and multi-root bundle publication
- `references/authority-and-loopback.md` — authority/WAL and authenticated loopback audit
- `references/incremental-rebuild-traps.md` — lost updates, non-idempotent retries and stuck flags

## (added 2026-06-10) Engine event semantics + remediation plan completeness

Origin: LFGungame GG-01 (2026-06-10) — a respawn wiring on the wrong event passed this skill's entire pass (8 auditors + cross-actor) and 2 external reviews because everyone verified the hook's SIGNATURE and no one its SEMANTICS. And F-25 fell out of the remediation plan unclassified (groups covered 26/27 findings).

- **Add to auditor prompts (all dimensions touching hooks)**: for each engine event override (`OnClient*Event`, `EE*`, `On*`), verifying that the signature exists in vanilla is NOT enough. Verify parameter CONTRACT: (1) read the body of vanilla event handler — its internal usage reveals what it delivers (canonical example: `OnClientRespawnEvent` kills the unconscious "choosing to respawn" → player is the OLD character; new one is born in `OnClientNewEvent`); (2) grep prior art across real tree mods: who hooks that event and for what purpose. If the audited mod uses an event that no prior art uses for that purpose, it is a finding (Medium confidence minimum).

- **Vanilla call-sites for each CONSUMED parameter (added 2026-08-15, SP-369)**: the handler body does not tell what caller chooses not to pass. For each parameter of an engine hook that override CONSUMES, grep vanilla call-sites of that method and verify they actually pass it. A parameter with a default value in signature is a promise caller might not keep. If any call-site omits it, override must derive the data on its own (`GetPosition()`, `GetOrientation()`) instead of trusting the argument — or at least detect default and not make destructive decisions with it. **Severity corollary**: when action upon validation failure is destructive (`ObjectDelete`, deleting a file, dissolving a record), an unreliable parameter turns a gate into a shredder. Gates that delete must fail **closed toward inaction**, not toward destruction. Origin: SimpleGroup 2026-08-15 — an `OnPlacementComplete` override validated territory with `position`; vanilla call-site digging garden plot with shovel computed position and called hook with only player, override received `(0,0,0)` and called `ObjectDelete`.
- **Plan completeness checklist (step 2, when processing findings)**: if audit produced N findings and plan classifies them into groups, mechanically verify that |union of groups| == N (list of IDs, not from memory). A finding without group = lost finding (real case: F-25).

## (added 2026-06-11) Production triage: deployed artifact, path attribution, lying-named gates, auditor spawn

Origin: LF_VStorage 2026-06-11 (5 production bugs; dual Claude+Codex audit; see LL-143/LL-144).

- **Deployed artifact ≠ source (prelude to Step 1 when trigger is a PRODUCTION bug)**: if audited code is distributed packaged (PBO/build), compare artifact mtime vs relevant fix files mtime AND probe INSIDE artifact (string-probe classnames on binary, without unpacking) BEFORE root-causing against source. Declare drift as its own finding. Case: PBO 28-May without 01-Jun CodeLockBridge — 2 of 5 bugs were partially deployment drift.
- **Path attribution in log evidence**: a log line that "proves X works" is attributed to emitting path (synchronous shutdown vs action hook vs periodic scan) before classifying partial-vs-broken. Case: "MMG virtualizes" came ONLY from OnMissionFinish; zero runtime path activity in entire session.
- **Lying-named gates (add to auditor prompts)**: for each trigger gate function (HasX/CanY/IsZ), paste and read BODY — do not accept name as evidence of coverage. Case: `HasCargoOrAttachments` without any attachments check → all slot storage invisible to all 4 triggers; missed by 9 auditors + cross-actor and uncovered by user pushback.
- **Auditor spawn (Step 2, operational)**: background agents auto-deny permission prompts outside cwd → launch auditors in FOREGROUND, all in a single turn (parallel). Case: mechanical checks agent bounced in background with PERMISSION-FAIL.

## (added 2026-07-05) Super-chain verification is a FULL-ANCESTRY walk, not a leaf check

Origin: LF_VStorage F-NEW-1 (review 2026-07-05). The mod's physical Open/Close
failsafe (`modded class ItemBase`) only fires if every class between the leaf and
ItemBase chains `super`. Verification pass A-F5 checked the leaf
(`rag_baseitems_container_base.Open()` — chains super) and declared the invariant
satisfied. The break was one level up: `RaG_ContainerBase.Open()/Close()`
(RaG_Core, `RaG_ContainerBase.c:142-154`) set state and return WITHOUT `super` —
the failsafe never fires for the entire family. The miss survived TWO independent
verification passes (a prior session and a search agent) because both stopped at
the leaf.

Procedure (mechanical, ~5 min per family):
1. Resolve the full chain: leaf → parents → vanilla base (`class X : Y` headers;
   third-party mods' extracted sources or PBO string-grep).
2. For EACH class in the chain, grep `override void <Method>` — if present,
   confirm it calls `super.<Method>()`. One missing link voids the invariant for
   every descendant.
3. Record the verdict per FAMILY (base class), not per leaf classname.
4. If any link is broken: the failsafe does not cover that family — a dedicated
   wrapper hook on the family base (with super + explicit notify) is required.

Corollary: a bridge/failsafe decision justified by "handled when the leaf chains
super" is UNVERIFIED until the full walk is on record. Treat such comments as
claims to audit, not facts.


## (added 2026-07-08) Delta-contract propagation — a Step-1 check when the trigger is "make it fail-closed"

Origin: LF_VStorage 1.5.0 pre-release audit. The change under review hardened durability
contracts (signature -> bool + gate on it; "verify sidecar before declaring persisted").
5 of ~9 real findings — including BOTH release blockers — were not the fix being wrong but
the fix MISSING at a sibling call-site: `HandleRestoreFailure` didn't clear the flag+sidecar
its 3 sibling terminal paths cleared; `MigrateLegacyTmp` got the `isCanonicalTmp` filter but
`PromoteOrphanTmp` didn't; retry/recover got the checked `ClearFor` gate but `reset` didn't;
DropQueue's success branch untracked but its 2 fail-closed branches didn't. The 8 structural
angle-auditors under-weight this — each reads its own layer's canonical path — yet the whole
point of a fail-closed delta is that it touches MANY sites.

Add to Step 1 (mechanical pre-checks) whenever the delta changes a signature to bool,
introduces a "verify-before-durable" contract, or propagates a fail-closed gate:
- Grep EVERY call-site of the changed symbol AND its sibling/opposite operation that should
  now share the contract: the success path, EVERY failure/early-return branch, the
  sync/shutdown shortcut, the admin variant, the boot-reconcile variant.
- For each, confirm it consumes the new contract (checks the bool / clears the same
  flag+sidecar / runs the same gate). Dominant failure mode is asymmetry: N-1 of N branches
  updated, one missed. Enumerate the branches mechanically — do not eyeball.
- This is a DELTA check (enumerate the changed symbol's fan-out), complementary to the 5
  structural checks; run it FIRST when the audit trigger is "someone hardened contracts".

Corollary (contradiction resolution): when two auditors disagree whether an orphaned on-disk
artifact (stale sidecar/marker) is dangerous or inert, the decisive question is whether the
boot/recovery scan ENUMERATES it. A sidecar whose primary enumerator glob (e.g. `*.lfv`) is
gone is inert even though it survives on disk — check the enumerator before rating severity.

Caveat when APPLYING the propagation (added 2026-07-08b, Step 5): if the missing call-site
transitions to a terminal/admin-blocking state (QUARANTINE, quarantine-orphaned) and its
failure branch contains a HARD-GATE (marker/payload preservation that prevents data loss), do
NOT reorder the flow to gate the durable write on the newly-checked contract. Reordering can
route the fail path into a marker-deleting / payload-purging branch and CREATE a worse
data-loss than the one you were closing. Prefer consume+retry of the contract with the durable
write kept in its ORIGINAL position. Verify the ENTIRE `else`/failure branch of the site you
touch, not just the happy path. Origin: a reorder of a degraded-partial handler introduced an
`.lfv`-deleting path at MAX failures; the adversarial reviewer caught it on the round after the
"fix" — the first apply attempt did not. Corollary: after a propagation fix, re-run the
adversarial verify pass (Step 3/4) on the CHANGED handler, because an apply can regress worse
than the finding.

## Rules promoted from lessons corpus (added 2026-07-27)

Promoted from `AI/20_Knowledge/lessons-learned.md` so they arrive via trigger instead
of relying on someone remembering to look for them. Each rule cites its originating `LL-NNN`;
the complete entry (symptom, origin, evidence) lives there.

- **LL-045** — Bound every claim of non-causality to the size, version, fixture, and conditions where verified. Do not promote "X does not matter" as a universal conclusion if the corpus does not cover other regimes.
- **LL-139** — Make every remote fake/stub emit the same types as the real wire, not just equivalent values. Do not use `is True`/`is False` with serialized data; explicitly test `0/1`, bool, and missing values according to contract. The fixture composes request as producer composes it, never the most complete one "for convenience" (LL-469): facing in-game defect with green suite, first look for test that already covered case and compare inputs field by field.
- **LL-140** — Verify every resource exclusion with two real acquisitions on target OS and require the second to fail. Inspect socket, file-sharing, and stdlib mutex defaults; configure lock fail-closed.
- **LL-190** — For every verifier asserting deleted/moved/repaired/restored, require an affected count greater than zero or an independent pre-check proving there was no work. Do not accept `{ok:true, count:0}` as proof on its own.


## (added 2026-07-29) Two things the audit must check and no single dimension covers alone

Origin: GameMaster IG-1 (R21 dual + this skill, 2026-07-29). The code entered with two independent
UNSOUND verdicts and emerged with 19 fixes. The two most severe findings of the day **were not
in the code being audited**: they were in the fixes written that very day. None of the
8 angles would have found them, because all 8 angles look at the system, not the patch.

### 1. A reused identifier is verified by its LIFECYCLE, not by its equality

`G2` requires verifying that the symbol exists. `LL-222` extended it to the semantics of a helper you
reuse. Missing is the third step, which is the one that bites in two-process systems: when a fix
uses an identifier emitted by ANOTHER actor, verifying that equality exists **is not enough**; one must
verify **how long** that equality lives and **who resets the counter**.

Real case: to delete an orphaned entity, `command_id` returned by enqueue was reused,
after verifying in server code that `object_id == command.id` — true, cited, with
`path:line`. What was not verified: issuer of those IDs **resets its counter on every startup**
(`self._next_id = 1`) and auto-reaps on idle at 30 min, while map indexing them on other
side **is never cleared** as long as host process lives. Recycled IDs ⇒ "compensatory" deletion
points to an entity from another session. A fix intended to leave no garbage could destroy work in progress.

**Mandatory questions before accepting a foreign ID as key for a destructive operation**:
who generates it and with which counter · does that counter reset (process, session, mission, reboot) ·
who maintains map resolving it and when is it cleared · can those two lifecycles get
desynchronized · what happens if ID no longer means what it meant. If any lacks a cited answer,
**the destructive operation is not performed**: log and report, never delete blindly.
A fixture never assigns ownership fields (LL-446): grep for assignments to `owner_*` in
helpers must yield zero; the only path to owner in tests is product operation with
real lease.

Corollary of same case: also verify **execution order** on other actor. There, a
`spawn` is always deferred to a queue and a `delete` of a batch without spawn is dispatched immediately, so
compensation could outrun spawn it intended to undo and create the permanent orphan
it came to prevent.

### 2. Step 6 looks for INTERACTIONS between fixes, not just defects in each fix

Step 6 says "re-run angles whose code changed most". Insufficient as it sounds: it invites
re-auditing each fix separately, and defect appears in the **product** of two correct fixes.

Real case, two fixes both correct and both with proven failing test: (a) "in dry-run do not call
sweep" — correct, sweep mutated the world in a mode advertised as safe; (b) "on startup,
guarantee trailing newline on ledger" — correct, a merged append caused loss of contract
for a live entity. Together: only broken-tail repair lived INSIDE sweep, which (a) had just
disabled in dry-run, and (b) closed broken line without discarding it, so next append
fell behind it and that line ceased being last. Result: `replay()` always raised and
ledger remained **permanently unreadable**. No subsequent startup could even sweep.

**Add to Step 6, explicitly**: for each pair of fixes in batch, ask if one **disables
a path that the other depends on**. Especially when one fix adds a guard (`if not X: ...`) and another
touches the resource that path repaired or cleaned. Enumerate pairs mechanically if batch exceeds
four fixes; guilty pair is rarely the one suspected.

**And use mutants in Step 6, not just green tests.** In this case re-audit with mutants
killed 12 of 14 and the 2 survivors were precisely tests that "tested" a fix without being
able to distinguish it from its absence. A test that passes with and without fix is not coverage: it is decoration.
The positive control of an oracle is the REAL artifact along full load→evaluate path,
with mutants as files (LL-438); synthetic in-memory mocks only measure author consistency.
## (SP-367, added 2026-08-07) When audited tree is OUTPUT of a generator, Step 5 does not edit the tree

Origin: LFPowerGrid F4-S2 (2026-08-07). Audit produced 3 fixes of 3 lines within a
delta of 24. Applying them seemed trivial. It was not: candidate tree was output of a
fail-closed transformer with tree manifest and contract pinned by SHA-256, and lines to
touch were its Python literals, gated by exact counts (`count('"key"') != 2 -> fail`).
Editing tree would have broken manifest and made fix irreproducible.

**Add to Step 1 (mechanical pre-checks), as question zero**: first of all, determine if
audited tree is output of a tool (transformer, codegen, build, migration) with
manifest, contract, or pinned hashes. Look for `*-receipt.json`, `contract*.json`,
`*manifest*.json` alongside tree, and a `--verify` in tool that produced it. If present, the
tree is NOT the edit surface.

**Consecuencias, en orden**:

1. **The fix is applied to generator literal**, not artifact. Next: regenerate contract
   and its SHA, re-run `analyze -> apply -> verify` from clean tree, and re-seal
   artifact (PBO/package). Previous artifact is preserved separately as evidence.
2. **Re-anchoring gates is the failure mode this skill exists to prevent.** A gate that is
   touched so it accepts your fix is a loosened gate. Rule: ALWAYS re-anchor stricter (two
   exact counts of 1 instead of count of 2), add a non-regression gate for each
   check the fix removes, and **test every touched gate in red on the same day** — tamper
   the literal, run tool, require exit != 0 with expected token, restore, and
   verify that restore is byte-identical.
3. **State cost BEFORE user approves scope of fixes.** Real cost is not
   "editing N lines": it is contract + SHA + re-run + re-sealing + possible re-measurement. It changes
   which findings are worth fixing. In origin case, two of four approved fixes changed
   shape once cost became known, and one became inapplicable.
4. **A finding whose fix would require touching a hash-pinned region in contract is not fixed.**
   It is documented, or turned into a procedural note. In origin case, relocated body
   was byte-identical by design and pinned: finding "debug hook was left duplicated in
   two files and tester may edit the one that does not compile" was closed with a line in
   test procedure, not code.

### Corollary for Step 3a: a correct citation may not prove what is asked of it

An auditor cited an official vanilla test as proof that an API was synchronous: test measured
a counter before and after call and asserted `== 1` on next statement. The citation was
literal and exact. But sibling of that API, **documented as asynchronous**, passed the same
assert a few lines down. Test did not discriminate, so it proved nothing about synchrony.

**Rule**: before accepting a third-party test, assert, or invariant as proof of property
P, locate case that DOES NOT have P and verify that same assert fails. If negative control
passes, evidence does not discriminate — it is compatible with conclusion, does not support it. It is same
axis as "a gate that cannot be turned red is not a gate", applied to third-party evidence instead of
own gates. Verifying citation exists (`G2`) is first rung; verifying citation
DISCRIMINATES is second, and is the one skipped.

### Sibling corollary: control is calibrated to WORST real case, not a convenient one (LL-348)

Previous corollary covers control that does not discriminate. This one covers one that discriminates but in
the wrong range.

A sweep of 18 files searched for a known defect — a rewritten line left alongside the
old one — measuring common prefix `>= 55` characters between neighboring lines. It yielded **0**. It carried positive
control, and control was planted on a pair sharing **77**: passed green. The only
difficult real case shared **~32** before diverging, so probe would not have found it
ever. It was fixed because external reviewer named it, not because sweep detected it.

Lowering threshold was not answer either: at 25 there were 27 hits, nearly all legitimate repetition.
**Threshold was not problem; measured magnitude was.** The good probe measures *similarity* over
neighbors of lines that change ADDED — defect only exists where something landed — and its
control is planted in real cases.

**Rule**: a positive control answers "can it find something?", and that is not the question; the
question is "can it find THIS?". Plant it in worst known real case. If there is none
yet, declare up to what toughness coverage is demonstrated — "0 remaining, verified up to
similarity 0.60" — instead of saying "0 remaining" point-blank. And if moving threshold causes result
to jump from 0 to dozens of false positives without passing through useful range, stop: you are measuring
the wrong magnitude.

**Cheap signal**: if you wrote positive control and someone else found defect,
check whether your control would have caught theirs.

### Third corollary: a control that inherits the instrument's convention is born blind (LL-347)

Previous two cover control that does not discriminate and one discriminating out of range. This one
covers one that discriminates perfectly **inside the blind spot intended to be measured**.

A gate checked that proxies were rotated 180 degrees around vertical axis. It had
negative control and was well thought out: generated a model rotated 180 degrees around a
*horizontal* axis and required gate to flag it in red. It did. Gate GREEN on good
artifact, negative RED, and result in game was **wrong** — weapons had rotated around
horizontal.

Cause: control generator applied `R_new = Ry(180) * R_old`, multiplying from the
LEFT, and function deriving frame returns axes as rows in world coordinates.
Multiplying from left negates rows, meaning it rotates around proxy's **own axis**, not around
world's. Measured: local Y axis of those proxies pointed to `(1.0, -0.001, 0.006)` — world's X.
**The control used the same mistaken convention as the gate**, so it confirmed
convention instead of testing it.

**Rule**: when what might be wrong is a CONVENTION (multiplication order, rows versus
columns, local frame versus world, axis order, endianness, 0-based versus 1-based), control cannot
be built with same code or same convention as instrument. It is built
from outside: an artifact whose expected value is known via another means — a manual measurement, an external
reference file, a visible asymmetrical marker — and compared against that. A control that
shares gate apparatus only proves that apparatus is self-consistent.

**Cheap signal**: if control and instrument share function, module, or formula, it is not an
independent control. And if gate comes out green and observable result comes out wrong, suspect
convention before threshold.

## (added 2026-07-28) Two DayZ persistence facts a Step-1 check must assume, not discover

Both were re-read against the pinned build 1.29.0.163451 during the r21 Phase 03
audit. They are engine properties, not project quirks, so any DayZ mod that
persists data inherits them.

- **DayZ exposes no rename and no move, so "temp -> verify -> replace" is NOT
  atomic.** The file primitives stop at `FileExist`, `OpenFile`, `ReadFile`,
  `CloseFile`, `FPrint`, `FGets`, `MakeDirectory`, `DeleteFile` and `CopyFile`
  (`VANILLA/1_core/proto/ensystem.c:397-531`); a grep for `Rename|MoveFile` over
  `1_core` returns zero. The real replace is `DeleteFile(dest)` followed by
  `CopyFile(tmp, dest)`, leaving a window in which the destination does not
  exist. Audit consequence: back up BEFORE that window, verify AFTER the copy,
  and delete the `.tmp` only once the post-copy verify passes. Treat any code or
  comment claiming an atomic replace as a finding, not as documentation.

- **`EntityAI.OnStoreSave` writes a runtime-dependent NUMBER of fields.** With an
  energy component it writes nine, without it none
  (`VANILLA/3_game/entities/entityai.c:2928-2959`). Reading by fixed offset after
  `super.OnStoreLoad` therefore desynchronises only for the configurations that
  lack the component -- it will pass every test written against the configuration
  that has it. Audit consequence: any subclass that reads after `super` must read
  sequentially and check each read's return; a fixed offset is a latent defect
  even when the current tests are green.

Both belong in the Step 1 mechanical sweep, because both are grep-able and
neither is deducible by reading the happy path.

**And the entry-point instance they combine into**, found by this skill's own
check #3 on the Phase 03 simulator: the normal save path deleted a destination
that failed its post-copy verify, while the recovery path left the corrupt bytes
in place as the live file. Same invariant, two entry points, one of them silently
weaker -- the VULN-009 shape. When a codebase has a `save` and a `recover`, diff
their verify branches line by line; do not assume the recovery path inherited the
discipline.

## (added 2026-08-14, SP-238 + SP-240) A CORRECTIVE is unaudited input: re-audit its NEW code, never delta-only

**Step 3 says "re-audit until zero critical/major". It did not say that the
corrective's own code must be audited as if it were a fresh round.** It must.

**Evidence.** A corrective bundle passed its receiver, an R8 walk and the compile
gate, and closed the findings of six review lanes. Re-running the multi-angle
audit against **its own new code** then found two new criticals and one blocker,
all of them **defects in the corrective's design rather than its implementation**:
a clear-after-reapply that broke the guarantee of an alternate path, and an alias
in the canonical buy/withdraw/restart flow that left the in-game ATM permanently
blocked. Four of five independently re-launched auditors converged on the same
alias without contact. It was the fourth instance of the same shape in one
campaign, which is what makes it a rule rather than an anecdote.

**Apply, appended to Step 3:**

1. **Re-launch every applicable angle over the NEW code**, not "check that the
   fixes landed". The round-two findings were in the corrective's design, so a
   delta-only check could not have seen them. Resumed agents work here and cost
   roughly 30% of a fresh run, provided they are told explicitly that their
   cached content is STALE.
2. **The corrective's prompt carries its own counter-scenarios** -- the scenarios
   that would refute its design -- and the implementer verifies and documents
   them as part of RED->GREEN. Treat the arbitration's design as unaudited input.
   In the case above, the counter-scenarios that were embedded got verified; the
   one that was not embedded is the one the re-audit had to catch.
3. **Use the single loop budget established before review.** Follow `gates-ledger`
   §Cuándo para un bucle: executable product criteria, bounded rounds and an explicit
   escalation outcome. Do not substitute a zero-new-findings requirement.


## (added 2026-08-31, SP-196 + SP-200) Repair-on-load constructors turn every reader into a writer

A store constructor that prunes, migrates, compacts, normalizes, or repairs while loading is
not read-only. Every call site that constructs it can write the same file, even when the
caller's help text or docstring says "read-only". Treat that claim as unverified until the
constructor and its callees have been read.

**Step-1 caller census:**

1. Grep every construction of the store class, including tests and alternate entry points.
2. Classify each caller as intentional writer, required reader, or test. For each required
   reader, trace constructor side effects through the persistence choke point.
3. Check the lock's scope. `threading.RLock` excludes threads in one process; it does not
   serialize two processes writing the same file. A shared file needs an inter-process lock
   or a design that gives only one process write authority.
4. Look for readers that discard exactly the records the loader repairs or prunes. That is a
   mechanical signal that maintenance is an unwanted side effect, not part of the read.

**Read-only must be structural.** A read-only mode loads without repair or checkpointing, and
the persistence choke point plus every public mutator must raise if a future caller attempts
to write. Pin the contract with a file that contains material the normal loader would repair,
then compare its bytes before and after the read-only operation; an unchanged mtime is not
enough evidence.

**A pre-operation backup is not fail-closed merely because it uses `O_EXCL`.** The path
`FileExistsError -> success` can reuse a stale, empty, or crash-truncated backup, and one fixed
backup name protects only the first destructive operation. Use a fresh numbered slot per
operation (`.bak`, `.bak.2`, ...), create it with `O_EXCL`, validate its bytes and size, never
reuse it, and fail closed when the bounded slots are exhausted.

A permanent fail-closed state must also be observable. Whenever a repair or destructive
operation can stop because no valid backup slot remains, require the existing diagnostic
surface to emit a finding. Always ask: **how does a human learn that this brake is engaged?**

## (added 2026-08-31, SP-369) The super-chain walk also goes downward from a modded base

The full-ancestry walk above protects an invariant while moving from a leaf toward its bases.
A `modded class <Base>` needs the opposite walk too: inheriting from the base does not execute
the modded hook when a descendant overrides that method without chaining `super`.

Procedure:

1. Enumerate every vanilla descendant of `<Base>`; include indirect descendants rather than
   stopping at the first level.
2. For each method modified on `<Base>`, inspect every descendant override and record whether
   it calls `super.<Method>()` on every applicable path.
3. Treat an override without that chain as a family-sized coverage hole. Add a dedicated hook
   at the correct family boundary or document that the invariant does not cover that family.
4. Treat comments such as "X and Y inherit this gate" as claims to audit, not evidence.

Record both directions separately: leaf-to-base proves that a leaf reaches the hook, while
base-to-descendants proves that no overriding child bypasses it.

## (added 2026-09-29, SP-447) Census the inventory before handing it to auditors; deployed ≠ source via the PBO

1. [EXACT] A regex-generated inventory is closed with an independent census before auditors see it: the LFPowerGrid save/load-body table listed 11 files while 25 contained `ctx.Read` or `ctx.Write`, missing an entire hook family (`LFPG_OnStore*Device`, 10 classes). Auditors treat the handed table as complete.
2. [DESIGN] "Deployed artifact ≠ source" is checked in DayZ by extracting the PBO and comparing by content (EOL-normalized) against each candidate tag: a release tag differed from the published PBO in 51 of 144 scripts.
3. [EXACT] Do not count entities by searching class names in `storage_1\data\*.bin` (nor in `types.bin`): the positive control returns 0 matches in a world that does contain those classes. Count them in game.
