# Prompt conventions

Why agent and skill files in this repo look the way they do. Read this before writing or editing anything in `.claude/agents/` or `.claude/skills/`.

## TL;DR

- **Uppercase section headers** (`## NAME`, `## ROLE`, `## CONSTRAINTS`) are structural — for tooling and scannability, not for the model.
- **Inline caps directives** (`MUST`, `NEVER`, `ALWAYS`, `DO NOT`, `CRITICAL`) are behavioral — they measurably increase model compliance, but only when used sparingly.
- **Lowercase prose for everything else.** Caps are a finite signal; spending them on decoration burns the budget you need for real rules.

## Why caps directives work

Capitalized directives like `MUST`, `MUST NOT`, `SHALL`, `SHOULD`, and `MAY` come from **RFC 2119**, the IETF's "Key words for use in RFCs to Indicate Requirement Levels." That convention is everywhere in the training data: protocol specs, security standards, API contracts, compliance docs. Whenever a document needed an unambiguous rule that a reader couldn't talk themselves out of, the author capitalized the verb.

LLMs have absorbed that pattern. Anthropic's own prompting guide explicitly recommends using caps for critical instructions, and in practice:

- *"you must not delete files"* — gets rationalized away ("the user clearly wants this resolved, deleting seems necessary…")
- *"you MUST NOT delete files"* — held to as a hard rule

Same words, measurably different compliance rates. This is real, not folklore.

## Why caps work *only when rare*

Caps function as a salience boost. The boost exists **because most surrounding text is lowercase** — caps stand out against the baseline. If a file is wall-to-wall `EVERY AGENT MUST ALWAYS DO X AND NEVER DO Y`, the model treats that as the author's normal voice and the emphasis evaporates. You end up with noisy prose AND no compliance lift — worst of both.

The signal is finite. Spend it on rules that, if violated, would mean the agent failed its job.

## How to decide whether to cap something

Apply this test to any directive you're tempted to capitalize:

> If I remove the caps and read the sentence aloud, does it still feel like an absolute rule?

- **Yes** → leave it lowercase. The grammar already carries the weight.
- **No, removing the caps would let the model rationalize an exception** → keep it capped.

Examples from the existing agents that pass the test:

- `DO NOT write fixes yourself` (mod-reviewer's whole identity is "audit, don't fix" — without caps the model would slip into fixing)
- `NEVER on params/returns/locals/typedefs` (a hard EnScript rule with no exceptions)
- `MUST conform to the style guide` (non-negotiable, blocks the work otherwise)

Examples that would *fail* the test (and should stay lowercase):

- `you must read the file before editing` — already enforced by tooling, no rationalization risk
- `you should always be helpful` — vague, not actionable, no specific failure mode
- `IMPORTANT: this is a tip about formatting` — decoration; the word "tip" already framed it

## Section headers — different rule

Section headers (`## NAME`, `## ROLE`, `## CAPABILITIES`, `## CONSTRAINTS`, `## EXAMPLES`) are uppercase by convention but for a different reason: the `agent-creator` skill validates the template structure, and consistent caps make sections greppable and visually distinct from inline content. Doesn't change model behavior — could be lowercase and nothing would break.

If you're authoring a new agent, follow the existing template exactly (uppercase headers, no trailing colons, blank line after each heading). The structural rules are enforced by `agent-creator`; deviating from them just makes the file fail validation.

## Quick checklist for writing a new agent or skill

1. Section headers: uppercase `## NAME`, `## ROLE`, etc. — match the existing template.
2. Inline caps: reserve `MUST` / `NEVER` / `ALWAYS` / `DO NOT` for actual hard rules. Apply the "remove the caps and re-read" test.
3. Default to lowercase prose. Trust the grammar.
4. If half the bullets in a section are capped, you've over-spent the signal — demote some to lowercase.

---

## CROSS-ENGINE / CROSS-LANGUAGE CONTAMINATION (added 2026-05-12)

When a skill documents a system sharing a family with another better documented online — Arma 3 ↔ DayZ, SQF ↔ EnScript, Python 2 ↔ 3, Vue 2 ↔ 3, React class ↔ hooks — dominant risk is **transferring knowledge from the better-documented version to the worse without re-verifying**. Author assumes they share values when they only share lineage.

Anti-patterns detected on 2026-05-12 (verified against actual files, NOT against narrative audit):

- In `dayz-p3d-audit/scripts/audit_p3d.py` and `dayz-p3d-inspector` there is a historical trail of contamination: comments "Earlier versions used 2e13 / 3e13 / 7e13 — those values were wrong for modern DayZ" indicate Arma 3 ranges WERE there and were corrected. The bug is NOT in current code.
- In `dayz-pbo-build/references/validation-scripts.md:226-228` `known_bases` mixes valid DayZ bases (`Inventory_Base`, `Container_Base`, `HouseNoDestruct`) with pure Arma 3 tags (`Motorcycle`, `Helicopter`) — a user inheriting from `Motorcycle` in DayZ cannot find class. Recommended verification: filter against vanilla `P:\dz\`.
- Paradoxical case (meta): the audit intended to detect this contamination asserted concrete findings (ShadowVolume `9e9..1.1e10`, `dayz-p3d-audit:34`) that **DO NOT EXIST in current code**. The bug cited by audit belonged to a previous version already fixed. Lesson: even audits confabulate — verify against PRIMARY source (the file) before believing audit.

Operational rule before writing a magic number, base class list, or language restriction in a skill for poorly documented system:

1. Does this information come from native source (vanilla P:\, BI repo, Enfusion docs, vanilla scripts of game itself)? Cite `path:line` or URL.
2. Or does it come from a cousin engine (Arma3/SQF/legacy) assumed to apply? If yes, mark `[NEEDS DAYZ VERIFICATION]` until confirmed.
3. For languages (EnScript, etc.): authoritative source = binary or game vanilla scripts. Cite it. Do not trust community blogs without cross-check against actual `.c`.

DEBUNKED-and-then-corrected case (2026-05-12 audit; updated 2026-07-06): audit claimed `?:`, `++`, `foreach`, `+=` "are valid EnScript features". Verification of 2026-05-12 against skills back then concluded "all four NOT supported". Final verdict split:

- `?:` (ternary) — debunking HOLDS: does not compile in EnScript. Remains prohibited (enforce-script-reference, hard rules).
- `++`, `foreach`, `+=` — audit WAS RIGHT: verified later in production (LBmaster) and in game vanilla scripts (`P:\scripts\3_game\billboardset.c:108` uses foreach, among many). Skills listing them as prohibited were mistaken and got corrected (enforce-script-reference rules 2-4).

Meta lesson REVISED (stronger than original): on 2026-05-12 the claim was "refuted" citing 4-5 matching skills — but N skills repeating the same claim are NOT N independent sources if they share lineage (all inherited same legacy note). Multi-skill consensus ≠ verification. Sole primary source for language restrictions is compiler / vanilla game scripts; a single vanilla `.c` using `foreach` outweighs 5 skills saying it does not exist.

## DISCOVERABILITY THROUGH USER VOCABULARY (added 2026-05-12)

The `name:` and `description:` of a skill decide whether Claude autoinvokes it when user asks about the domain. If skill is named with internal jargon or technical name user would never say, it will not autoinvoke — it exists but nobody finds it.

Anti-pattern: skill `japm-pbo-recovery`. "JAPM" is the identifier of tool author; actual trade name is "PBO Tools". A user googling "decompile PBO Tools" / "recover PBO source" / "obfuscated PBO" does not find the skill.

Regla: en `description:` incluir:

1. Technical system name (for precision).
2. Associated commercial name(s) or public product(s) (what user would google).
3. User verbs in present imperative: "decompile", "recover", "fix", "audit" — what user types.
4. Problem symptoms: "lost my source", "no source available", "obfuscated" — how user describes it before knowing solution.

Ejemplo correcto (parche aplicable a `japm-pbo-recovery`):

> Recover source code from DayZ PBO files obfuscated with JAPM **(also known as "PBO Tools")**. Use whenever: user mentions "PBO Tools", "JAPM", "obfuscated PBO", "lost my source", "recover PBO source", "decompile PBO", ...

## DEPTH OF RESPONSE (added 2026-05-12, recalibrated 2026-08-05)

The model already tends to broaden scope and lengthen response on its own, and its
harness already instructs to "deliver what was requested, at requested scope". Previous version of this
section instructed the opposite —bump by default **one level deeper**— and pushed precisely
the failure that today must be reined in. Correct default is **the requested scope**.

- Scoped task ("look up X for me", "what do you think of Y") → respond at that level. If domain
  is complex and something substantial remains to be said, ONE sentence at the end offering it: "I can
  drill down to alternatives + criteria + risks if you want".
- Do not inflate first turn with sections nobody asked for (matrices, 5+ options, lateral
  audits) unless cost of not doing so is irreversible (`G1`, persistent format).
- Recommending before enumerating still rules (`G4`): max 3 options and recommendation
  first, not a catalog.

Keywords with which user sets level:

| Keyword | Depth |
|---|---|
| "fast" / "brief" | 2-4 sentences maximum |
| (no word) | requested scope, without leveling up |
| "deep" / "in depth" / "with math" / "audit" | exhaustive |

Once level is established, maintain it throughout entire session unless user changes it.

Origin and nuance (2026-05-12 session "Optimize legendary reanimation deck"): case creating
this rule was too superficial an analysis to "look up clive's hideaway for me", with
user insisting on *"do a broader search... do a mathematical analysis"*. That failure is
real, but correct response is not raising default across board: it is **reading the accumulated
context of the session**. Complex domain + prior iteration history calls for depth;
a scoped cold prompt does not.

## DELIVERY PROTOCOL — session edits directly; guardrail is root CENSUS (rewritten 2026-09-01)

**Replaces instruction of 2026-07-30** ("a skill edit is packaged, not applied;
he installs it"). Since 2026-08-31 skills **are updated directly by sessions**, without
packaging and without asking permission for each edit. What does NOT disappear are mechanical
guardrails: they shift place, from permission to census.

### Guardrail replacing permission: census roots BEFORE editing

Writing to ONE root leaves **invisible drift**: the copy edited by this session and copy served to
agent may differ, and nobody sees it until someone reads the old one. Before touching a
skill, enumerate where it lives and **classify links before counting** (junction rule):

```
~\.claude\skills\<name>                          <- lo lee Claude Code (CLI)
~\.agents\skills\<name>                          <- muchas entradas son junction a la de .claude
…\skills-plugin\<guid>\<guid>\skills\<name>      <- read by app; there are N GUIDs and they are DISTINCT plugins
~\.grok\skills\<name>                            <- projection; measured 2026-09-01: junction to plugin
```

Write to **all real copies**; those that are links are already covered. Verify upon
finishing by **sha256**, not by mtime. Example measured on 2026-09-01: `codex-handoff-template` and
`grok-handoff-template` existed in a single real copy (plugin) and `~\.grok\skills` was junction to
it, so a single write covered both views — but that **is verified, not assumed**.

### What decides what governs you: manifest, not folder

A folder does not state what governs it. `<plugin>\manifest.json` does: includes per skill its `skillId`,
`enabled`, `creatorType`, and `updatedAt`. Before concluding a skill is orphaned, open it.
On 2026-09-01 six skills were assumed orphaned that were **registered and enabled**, and the
"rescue" ended up leaving the fix in ungoverned copy while served copy remained broken.

**Measured caveat:** editing plugin projection **persists** (host-direct, stable sha within
minutes), but **does not** bump registry `updatedAt`. Edit lives locally; if app
resyncs from server, it is lost. If change must survive that, tell user.

### Mechanical guardrails that remain standing

1. **In plugin tree, write host-direct with PowerShell**, never with harness
   Edit/Write: there they go to an overlay view diverging from real disk. Read to package, yes.
2. **Backup before**, and **read-after-write** always.
3. **Sweep with positive control.** If your final check yields zero, run it across pre-fix
   version: if it also yields zero there, what is broken is your detector, not file declared clean.
4. **In PowerShell, text you write goes in SINGLE quotes** (`'...'` or here-string
   `@'...'@`), never in double. In `"..."` and `@"..."@` backtick is escape and `$`
   interpolates, so a markdown code span whose text begins with `0`, `a`, `b`, `e`, `f`,
   `n`, `r`, `t` or `v` gets corrupted without throwing error: `` "see `references/x.md` and" `` writes a CR
   followed by `eferences/x.md`, and closing backtick disappears. Measured 2026-09-15 with
   PowerShell 7.6.5: `` "[`0][`a][`b][`e][`f][`n][`r][`t][`v]" `` gives bracketed codes
   0, 7, 8, 27, 12, 10, 13, 9 and 11; `` "`q" `` gives only `q`; `` 'x`ry' `` outputs literal. Happened already:
   a section written host-direct on 2026-09-02 in plugin copy of `delegar/SKILL.md`
   carried two loose CRs where source text said `` `references/routing.md` ``, and survived
   13 days. For whole files, `Copy-Item` from a verified copy. And watch out for
   read-after-write: sha only proves disk has what you sent, not that you sent it
   right; also look for loose CRs (`\r(?!\n)`).

### When a `.skill` IS packaged

No longer default delivery route. Remains for bringing a skill to a machine or storage
lacking a copy. If packaging:

1. `python C:\Users\<you>\.claude\skills\_shared\pack_skill.py <folder> <destination DIRECTORY>` — the
   second argument is a **directory**; passing a `.skill` dies with `FileExistsError`.
   DO NOT use `skill-creator/scripts/package_skill.py`: reads `SKILL.md` without `encoding`, falls back to cp1252 on
   Windows and dies with `UnicodeDecodeError` on any em-dash, arrow, or accent (3 of 8 skills
   died there on 2026-07-27).
2. **Installing REPLACES the whole folder, does not merge.** Package from the **most complete** copy
   —normally plugin copy, which may vendor `scripts/` or `wheels/`— or installing deletes them.
   With `dayz-3d-viewer` it would have dropped 6 scripts that its own `SKILL.md:51` invokes.
3. Package the **entire** skill: `SKILL.md` + `references/` + `scripts/` + `assets/`. A
   standalone `SKILL.md` installs it mutilated, and a `.md` snippet will not even install
   (`SKILL.md must start with YAML frontmatter (---)`).
4. The script excludes `__pycache__`, `.git`, `.pyc`, and `.pyo` (`pack_skill.py:22-23`) but **not**
   `SKILL.md.bak*`: if folder has backups, package from scratchpad copy with
   same folder name and delete them there.

`pack_skill.py` already validates presence of frontmatter and `name`, that `description` does not exceed 1024
characters (trim by moving non-triggering material to body, never by truncating), and reopens zip to
check that entries use `/` and not `\` — PowerShell 5.1 `CreateFromDirectory` writes them
with backslash and then installer cannot find `<name>/SKILL.md`.
