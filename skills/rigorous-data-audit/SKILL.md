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

> **Model** — Sonnet; Haiku is fine for the pure grep + table-walk checks.
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

### Step 2 — Eight parallel reasoning auditors

> **Model** — Opus. Sonnet is tolerable per-angle for cost, but the step 4
> cross-actor pass must stay Opus.
> **Done when** — eight angle reports are in; every finding pastes the literal
> code snippet it is about (not just a line citation) plus severity. A
> "finding" that only describes code without pasting it is bounced back as
> SUSPECT, not accepted.

Eight angles, one subagent per angle, all spawned in the same turn so they run
concurrently. Bound each agent's report (≤700 words, no narrative).

**Show, don't tell.** A claim of the form "this code has bug X" must include a
copy-paste of the actual code, with `path:line`. A description without the
snippet is a hypothesis, not a finding — the next step cannot verify it and it
will be dropped. This requirement is what makes "verified" something grep-able
rather than narrative.

The angles, in the order they should appear in the parallel batch:

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

> **Model** — Sonnet. The independent verifier subagent and the citation
> checks are file-reading work, not deep reasoning.
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
not match the file is not a finding — re-derive it or drop it.

**3b — Independent verifier pass.** Spawn one subagent with a **fresh context
that has not seen the angle reports**. Hand it only the bare list of claims
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

> **Model** — Opus, no substitution. The cross-actor reasoning is exactly
> where smaller models drop bugs.
> **Done when** — the fresh-context agent returns clean. If it found
> something, fix it and re-run step 4 with fresh context; repeat until clean.

This is the step that, in retrospect, would have caught the 12 VULNs.

Spawn **one** Opus agent with a fresh context — no audit history, no agent
output, no priors. Hand it the codebase, the README/spec, and this single
prompt: *"Find every way this code can lose, corrupt, or silently misroute
player data. Trace each writer to every reader, each sidecar to every cleanup
site, each admin flag to every consumer. Where any of those triples is
incomplete, that is a bug."*

Full prompt: `references/audit-prompts.md` § "Implementer-grade pass".

The cross-actor framing matters. Reasoning agents prompted "audit this layer"
look within the layer; they do not chase across actors. The implementer-grade
prompt explicitly says "trace across actors".

If this agent finds nothing, that is the signal that the audit is converging.
If it finds one thing, fix it and re-run step 4 with fresh context (it may
unblock a chain of further findings).

### Step 5 — Apply fixes

> **Model** — Opus. This is code editing.
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

> **Model** — Sonnet for the mechanical re-checks; Opus for the two re-run
> angles.
> **Done when** — mechanical pre-checks plus the two most-changed angles run
> clean. A new finding loops back to step 5.

Re-run mechanical pre-checks (cheap) plus the two angles whose code changed
most. If a new finding appears, loop back to step 5.

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
- **Spawning step 2 agents serially.** They are independent; spawn in one turn
  so they run concurrently.
- **Shipping a `.skill` / release / patch file from un-reverified findings.**
  Cheap to apply, expensive to walk back.

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

## (added 2026-06-10) Semántica de eventos engine + completitud del plan de remediación

Origen: LFGungame GG-01 (2026-06-10) — un wiring de respawn sobre el evento equivocado pasó la pasada completa de esta skill (8 auditores + cross-actor) y 2 reviews externos porque todos verificaron la FIRMA del hook y nadie su SEMÁNTICA. Y F-25 se cayó del plan de remediación sin clasificar (los grupos cubrían 26/27 findings).

- **Añadir a los prompts de los auditores (todas las dimensiones que toquen hooks)**: para cada override de evento engine (`OnClient*Event`, `EE*`, `On*`), NO basta verificar que la firma existe en vanilla. Verificar el CONTRATO de los parámetros: (1) leer el cuerpo del handler vanilla del evento — su uso interno revela qué entrega (ejemplo canónico: `OnClientRespawnEvent` mata al unconscious "choosing to respawn" → el player es el personaje VIEJO; el nuevo nace en `OnClientNewEvent`); (2) grep de prior art en mods reales del árbol: quién hookea ese evento y para qué. Si el mod auditado usa un evento que ningún prior art usa para ese propósito, es finding (mínimo confianza Media).

- **Call-sites vanilla de cada parámetro CONSUMIDO (added 2026-08-15, SP-369)**: el cuerpo del handler no dice lo que el llamante decide no pasar. Para cada parámetro de un hook engine que el override CONSUMA, hacer grep de los call-sites vanilla de ese método y comprobar que realmente lo pasan. Un parámetro con valor por defecto en la firma es una promesa que el llamante puede no cumplir. Si algún call-site lo omite, el override debe derivar el dato por su cuenta (`GetPosition()`, `GetOrientation()`) en vez de fiarse del argumento — o al menos detectar el default y no tomar decisiones destructivas con él. **Corolario de severidad**: cuando la acción ante un fallo de validación es destructiva (`ObjectDelete`, borrar un fichero, disolver un registro), un parámetro no fiable convierte un gate en una trituradora. Los gates que borran deben fallar **cerrados hacia la inacción**, no hacia la destrucción. Origen: SimpleGroup 2026-08-15 — un override de `OnPlacementComplete` validaba territorio con `position`; el call-site vanilla que cava el huerto con pala calculaba la posición y llamaba al hook solo con el player, el override recibía `(0,0,0)` y hacía `ObjectDelete`.
- **Checklist de completitud del plan (step 2, al procesar findings)**: si la auditoría produjo N findings y el plan los clasifica en grupos, verificar mecánicamente que |unión de grupos| == N (lista de IDs, no de memoria). Un finding sin grupo = finding perdido (caso real: F-25).

## (added 2026-06-11) Triage de producción: artefacto desplegado, atribución de camino, gates con nombre mentiroso, spawn de auditores

Origen: LF_VStorage 2026-06-11 (5 bugs de producción; auditoría dual Claude+Codex; ver LL-143/LL-144).

- **Artefacto desplegado ≠ source (preludio de Step 1 cuando el trigger es un bug de PRODUCCIÓN)**: si el código auditado se distribuye empaquetado (PBO/build), comparar mtime del artefacto vs mtime de los archivos de los fixes relevantes Y sondear el INTERIOR del artefacto (string-probe de classnames sobre el binario, sin desempaquetar) ANTES de root-causear contra source. Declarar la deriva como finding propio. Caso: PBO 28-may sin el CodeLockBridge del 01-jun — 2 de 5 bugs eran parcialmente deployment drift.
- **Atribución de camino en evidencia de logs**: una línea de log que "prueba que X funciona" se atribuye al camino emisor (shutdown síncrono vs hook de acción vs scan periódico) antes de clasificar parcial-vs-roto. Caso: "MMG virtualiza" venía SOLO de OnMissionFinish; cero actividad del camino de runtime en toda la sesión.
- **Gates con nombre mentiroso (añadir a los prompts de los auditores)**: para cada función-gate de un trigger (HasX/CanY/IsZ), pegar y leer el CUERPO — no aceptar el nombre como evidencia de cobertura. Caso: `HasCargoOrAttachments` sin ningún chequeo de attachments → todo el almacenamiento por slots invisible para los 4 triggers; lo pasaron por alto 9 auditores + cross-actor y lo destapó el pushback del usuario.
- **Spawn de auditores (Step 2, operativo)**: los agentes background auto-deniegan permission prompts fuera del cwd → lanzar los auditores en FOREGROUND, todos en un solo turno (paralelos). Caso: el agente de checks mecánicos rebotó en background con PERMISSION-FAIL.

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

## Reglas promovidas del corpus de lecciones (added 2026-07-27)

Promovidas desde `AI/20_Knowledge/lessons-learned.md` para que lleguen por trigger en vez
de depender de que alguien recuerde buscarlas. Cada regla cita su `LL-NNN` de origen;
la entrada completa (síntoma, origen, evidencia) vive allí.

- **LL-045** — Acota toda afirmación de no-causalidad al tamaño, versión, fixture y condiciones donde se verificó. No promociones «X no importa» como conclusión universal si el corpus no cubre otros regímenes.
- **LL-139** — Haz que todo fake/stub remoto emita los mismos tipos que el wire real, no solo valores equivalentes. No uses `is True`/`is False` con datos serializados; prueba explícitamente `0/1`, bool y valores ausentes según contrato.
- **LL-140** — Verifica toda exclusión de recurso con dos adquisiciones reales en el SO objetivo y exige que la segunda falle. Inspecciona defaults de socket, file-sharing y mutex de la stdlib; configura el lock fail-closed.
- **LL-190** — Para todo verificador que afirme deleted/moved/repaired/restored, exige un count afectado mayor que cero o un pre-check independiente que demuestre que no había trabajo. No aceptes `{ok:true, count:0}` como prueba por sí sola.


## (added 2026-07-29) Dos cosas que la auditoria debe mirar y que ninguna dimension cubre sola

Origen: GameMaster IG-1 (R21 dual + esta skill, 2026-07-29). El codigo entro con dos veredictos
UNSOUND independientes y salio con 19 fixes. Los dos hallazgos mas graves de la jornada **no estaban
en el codigo que se venia a auditar**: estaban en los fixes escritos ese mismo dia. Ninguno de los
8 angulos los habria encontrado, porque los 8 angulos miran el sistema, no el parche.

### 1. Un identificador reutilizado se verifica por su CICLO DE VIDA, no por su igualdad

`G2` obliga a verificar que el simbolo existe. `LL-222` lo extendio a la semantica de un helper que
reutilizas. Falta el tercer escalon, que es el que muerde en sistemas con dos procesos: cuando un fix
usa un identificador emitido por OTRO actor, verificar que existe la igualdad **no basta**; hay que
verificar **cuanto vive** esa igualdad y **quien reinicia el contador**.

Caso real: para borrar una entidad huerfana se reutilizo el `command_id` que devuelve el enqueue,
tras verificar en el codigo del servidor que `object_id == command.id` — cierto, citado, con
`path:line`. Lo que no se verifico: el emisor de esos ids **reinicia su contador en cada arranque**
(`self._next_id = 1`) y se auto-reapea por idle a los 30 min, mientras el mapa que los indexa al otro
lado **no se limpia nunca** mientras viva el proceso host. Ids reciclados ⇒ el borrado "compensatorio"
apunta a una entidad de otra sesion. Un fix pensado para no dejar basura podia destruir trabajo en curso.

**Preguntas obligatorias antes de aceptar un id ajeno como clave de una operacion destructiva**:
quien lo genera y con que contador · ese contador se reinicia (proceso, sesion, mision, reboot) ·
quien mantiene el mapa que lo resuelve y cuando lo limpia · pueden desincronizarse esos dos ciclos de
vida · que pasa si el id ya no significa lo que significaba. Si alguna no tiene respuesta citada,
**la operacion destructiva no se hace**: registrar y reportar, nunca borrar a ciegas.

Corolario del mismo caso: comprobar tambien el **orden de ejecucion** en el otro actor. Alli, un
`spawn` siempre se difiere a una cola y un `delete` de un lote sin spawn se despacha inmediato, asi
que la compensacion podia adelantar al spawn que pretendia deshacer y crear el huerfano permanente
que venia a evitar.

### 2. El Step 6 busca INTERACCIONES entre fixes, no solo defectos en cada fix

El Step 6 dice "re-run los angulos cuyo codigo cambio mas". Insuficiente tal como suena: invita a
re-auditar cada fix por separado, y el defecto aparece en el **producto** de dos fixes correctos.

Caso real, dos fixes ambos correctos y ambos con test en rojo probado: (a) "en dry-run no llames al
sweep" — correcto, el sweep mutaba el mundo en un modo que se anuncia como seguro; (b) "al arrancar,
garantiza el salto de linea final del ledger" — correcto, un append fusionado hacia perder el contrato
de una entidad viva. Juntos: la unica reparacion de cola rota vivia DENTRO del sweep, que (a) acababa
de desactivar en dry-run, y (b) cerraba la linea rota sin descartarla, de modo que el siguiente append
caia detras de ella y esa linea dejaba de ser la ultima. Resultado: `replay()` lanzaba siempre y el
ledger quedaba **permanentemente ilegible**. Ningun arranque posterior podia siquiera barrer.

**Anadir al Step 6, explicitamente**: por cada par de fixes de la tanda, preguntar si uno **desactiva
un camino del que el otro depende**. Sobre todo cuando un fix anade un guard (`if not X: ...`) y otro
toca el recurso que ese camino reparaba o limpiaba. Enumerar los pares mecanicamente si la tanda pasa
de cuatro fixes; el par culpable rara vez es el que uno sospecha.

**Y usar mutantes en el Step 6, no solo tests verdes.** En este caso la re-auditoria con mutantes
mato 12 de 14 y los 2 supervivientes eran precisamente tests que "probaban" un fix sin poder
distinguirlo de su ausencia. Un test que pasa con y sin el fix no es cobertura: es decorado.
## (SP-367, added 2026-08-07) Cuando el arbol auditado es OUTPUT de un generador, el Step 5 no edita el arbol

Origen: LFPowerGrid F4-S2 (2026-08-07). La auditoria produjo 3 fixes de 3 lineas dentro de un
delta de 24. Aplicarlos parecia trivial. No lo era: el arbol candidato era el output de un
transformer fail-closed con manifiesto de arbol y contrato pineado por SHA-256, y las lineas a
tocar eran literales Python suyos, gateados por conteos exactos (`count('"key"') != 2 -> fail`).
Editar el arbol habria roto el manifiesto y hecho el fix irreproducible.

**Anadir al Step 1 (pre-checks mecanicos), como pregunta cero**: antes de nada, determinar si el
arbol auditado es output de una herramienta (transformer, codegen, build, migracion) con
manifiesto, contrato o hashes pineados. Buscar `*-receipt.json`, `contract*.json`,
`*manifest*.json` junto al arbol, y un `--verify` en la herramienta que lo produjo. Si lo hay, el
arbol NO es la superficie de edicion.

**Consecuencias, en orden**:

1. **El fix se aplica al literal del generador**, no al artefacto. Despues: regenerar el contrato
   y su SHA, re-correr `analyze -> apply -> verify` desde un arbol limpio, y re-sellar el
   artefacto (PBO/paquete). El artefacto anterior se conserva aparte como evidencia.
2. **Re-anclar los gates es el modo de fallo que esta skill existe para evitar.** Un gate que se
   toca para que acepte tu fix es un gate aflojado. Regla: re-anclar SIEMPRE mas estricto (dos
   conteos exactos de 1 en vez de un conteo de 2), anadir un gate de no-regresion por cada
   comprobacion que el fix elimina, y **probar en rojo cada gate tocado el mismo dia** — tamperar
   el literal, correr la herramienta, exigir exit != 0 con el token esperado, restaurar y
   verificar que el restore es byte-identico.
3. **Decir el coste ANTES de que el usuario apruebe el alcance de fixes.** El coste real no es
   "editar N lineas": es contrato + SHA + re-corrida + re-sellado + posible re-medicion. Cambia
   que findings merecen arreglarse. En el caso origen, dos de los cuatro fixes aprobados cambiaron
   de forma al conocerse el coste, y uno resulto inaplicable.
4. **Un finding cuyo fix exigiria tocar una region pineada por hash en el contrato no se arregla.**
   Se documenta, o se convierte en nota de procedimiento. En el caso origen, el cuerpo reubicado
   era byte-identico por diseno y estaba pineado: el hallazgo "el hook de debug quedo duplicado en
   dos ficheros y el tester puede editar el que no compila" se cerro con una linea en el
   procedimiento de test, no con codigo.

### Corolario para el Step 3a: una cita correcta puede no probar lo que se le pide

Un auditor cito un test oficial de vanilla como prueba de que una API era sincrona: el test medi­a
un contador antes y despues de la llamada y afirmaba `== 1` en la sentencia siguiente. La cita era
literal y exacta. Pero el hermano de esa API, **documentado como asincrono**, pasaba el mismo
assert unas lineas mas abajo. El test no discriminaba, asi que no probaba nada sobre sincronia.

**Regla**: antes de aceptar un test, assert o invariante de terceros como prueba de la propiedad
P, localizar el caso que NO tiene P y comprobar que falla ese mismo assert. Si el control negativo
pasa, la evidencia no discrimina — es compatible con la conclusion, no la sostiene. Es el mismo
eje que "un gate que no puede ponerse en rojo no es un gate", aplicado a evidencia ajena en vez de
a gates propios. Verificar que la cita existe (`G2`) es el primer escalon; verificar que la cita
DISCRIMINA es el segundo, y es el que se salta.

### Corolario hermano: el control se calibra al PEOR caso real, no a uno comodo (LL-348)

El corolario anterior cubre el control que no discrimina. Este cubre el que discrimina pero en
el rango equivocado.

Un barrido de 18 ficheros buscaba un defecto conocido —una linea reescrita dejada al lado de la
vieja— midiendo prefijo comun `>= 55` caracteres entre lineas vecinas. Dio **0**. Llevaba control
positivo, y el control estaba plantado en un par que compartia **77**: paso en verde. El unico
caso real dificil compartia **~32** antes de divergir, asi que la sonda no lo habria encontrado
jamas. Se arreglo porque un revisor externo lo nombro, no porque el barrido lo detectara.

Bajar el umbral tampoco era la respuesta: a 25 salieron 27 hits, casi todos repeticion legitima.
**El umbral no era el problema; la magnitud medida lo era.** La sonda buena mide *similitud* sobre
los vecinos de las lineas que el cambio ANADIO —el defecto solo existe donde aterrizo algo— y su
control se planta en los casos reales.

**Regla**: un control positivo responde «¿sabe encontrar algo?», y esa no es la pregunta; la
pregunta es «¿sabe encontrar ESTO?». Plantalo en el peor caso real conocido. Si aun no hay
ninguno, declara hasta que dureza esta demostrada la cobertura —«0 restantes, verificado hasta
similitud 0,60»— en vez de decir «0 restantes» a secas. Y si al mover el umbral el resultado
salta de 0 a decenas de falsos positivos sin pasar por un rango util, para: estas midiendo la
magnitud equivocada.

**Senal barata**: si el control positivo lo escribiste tu y el defecto lo encontro otro,
comprueba si tu control habria cazado el suyo.

### Corolario tercero: un control que hereda la convencion del instrumento nace ciego (LL-347)

Los dos anteriores cubren el control que no discrimina y el que discrimina fuera de rango. Este
cubre el que discrimina perfectamente **dentro del punto ciego que se pretende medir**.

Un gate comprobaba que unos proxies estuvieran rotados 180 grados sobre el eje vertical. Tenia
control negativo y estaba bien pensado: generaba un modelo rotado 180 grados sobre un eje
*horizontal* y exigia que el gate lo marcase en rojo. Lo marcaba. Gate VERDE sobre el artefacto
bueno, negativo ROJO, y el resultado en juego estaba **mal** — las armas habian girado sobre la
horizontal.

La causa: el generador del control aplicaba `R_new = Ry(180) * R_old`, multiplicando por la
IZQUIERDA, y la funcion que deriva el frame devuelve los ejes como filas en coordenadas de mundo.
Multiplicar por la izquierda niega filas, o sea rota sobre el eje **propio del proxy**, no sobre el
del mundo. Medido: el eje local Y de esos proxies apuntaba a `(1.0, -0.001, 0.006)` — la X del
mundo. **El control usaba la misma convencion equivocada que el gate**, asi que confirmaba la
convencion en vez de ponerla a prueba.

**Regla**: cuando lo que puede estar mal es una CONVENCION (orden de multiplicacion, filas contra
columnas, marco local contra mundo, orden de ejes, endianness, base 0 contra base 1), el control no
puede construirse con el mismo codigo ni la misma convencion que el instrumento. Se construye
desde fuera: un artefacto cuyo valor esperado se conoce por otra via —una medida a mano, un fichero
de referencia ajeno, un marcador asimetrico visible— y se compara contra eso. Un control que
comparte el aparato del gate solo demuestra que el aparato es consistente consigo mismo.

**Senal barata**: si el control y el instrumento comparten funcion, modulo o formula, no es un
control independiente. Y si el gate sale verde y el resultado observable sale mal, sospecha de la
convencion antes que del umbral.

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
3. **Budget 2-4 rounds for integrity bundles.** The closing signal is "a round
   with zero NEW critical/major", not "the old findings are closed".


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
