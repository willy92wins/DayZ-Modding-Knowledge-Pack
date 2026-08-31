---
name: dayz-pbo-reverse-engineering
description: >
  Reverse-engineer DayZ PBOs from another author to extract reusable patterns, learn techniques, or build understanding before forking/extending. Covers extraction (Mikero ExtractPbo), source-vs-deployable classification (config.bin emptiness), the dimensional sweep order (config.cpp → model.cfg → scripts → rvmats → particles → p3d), citation discipline (path:line before claiming an API exists in another mod), state tracking (findings.jsonl/seen.json/queue.md), p3d string-extraction fallback, and anti-confabulation rules. Use when: extracting patterns from another modder's PBO, studying a third-party DayZ mod, building understanding before forking, auditing a workshop mod, or cataloging available 3D assets. Triggers: extract patterns from mod, reverse engineer PBO, analyze third-party DayZ mod, study modder code, pattern extraction, mod archaeology, workshop study. Use alongside dayz-pbo-build (opposite direction: packing your own PBO).
---

# DayZ PBO Reverse-Engineering

Workflow for systematically extracting patterns from another author's DayZ mod(s). Distilled from the LM_Planes extraction project (workshop 3730564764, Llama+Itspete-Here) where 130 patterns were extracted across 2 passes / ~30 loop iterations.

**Sister skill**: [[dayz-pbo-build]] handles the opposite direction (packaging your own PBO for release).

## When to use this skill

- User wants to extract patterns from another author's mod (workshop PBOs)
- User wants to fork/extend another mod and needs to understand it first
- User wants to audit a third-party mod for security/compatibility/quality
- User wants to catalog 3D assets available from a workshop entry
- User wants to learn modding techniques from a prolific modder's catalog
- Obfuscated PBO (GUID/COM1/BOM filenames, encrypted strings) → japm-pbo-recovery (+kgb-deobfuscator for KGB_DF marker) FIRST, then return here for the sweep. Both are optional external skills and are **not** included in this pack; without them an obfuscated PBO cannot be swept — report that and stop, rather than sweeping obfuscated output.

**NOT for**:
- Building your own PBO (use [[dayz-pbo-build]])
- Auditing your own model files (use [[dayz-p3d-audit]])
- General implementation work (use [[dayz-mod-workflow]] + domain skills)

## Step 0: Setup verification

Before starting, verify these are available:

```powershell
# Mikero PBO extractor (required)
Test-Path "C:\Program Files (x86)\Mikero\DePboTools\bin\ExtractPbo.exe"

# Disk space for extraction (estimate 2-3× compressed PBO size if keeping binaries)
Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'" | Select FreeSpace
```

If Mikero missing: install from https://mikero.bytex.digital/Downloads. There's no usable open-source PBO extractor for DayZ — Mikero is the only option for current ODOL format.

## Step 1: Inventory pass (fast classification)

Before deep work, classify each PBO as **deployable mod** vs **source asset distribution**. Use `-LB` flag (list contents only, no extraction):

```powershell
$pbos = Get-ChildItem "<workshop_path>" -Filter *.pbo -Recurse
foreach ($pbo in $pbos) {
    $listing = & "C:\Program Files (x86)\Mikero\DePboTools\bin\ExtractPbo.exe" -LB -P $pbo.FullName 2>$null
    # Parse listing: check if config.bin / config.cpp present and non-empty
    # Check file types: .c/.layout/.p3d (mod) vs .rar/.zip/.fbx/.blend (asset distribution)
}
```

**Key marker**: PBO with `config.bin` present BUT extracts to **0-byte `config.cpp`** = source distribution (no compiled config = nothing to load as mod). PBO with substantial `config.cpp` (>1KB) + `.c` scripts + `.p3d` models = deployable mod.

**Cautionary tale**: In LM_Planes workshop, 42 of 43 PBOs turned out to be source-only distributions. Inventory pass saved weeks of misdirected work. **Always do this first.**

## Step 2: Extraction setup

```powershell
$workdir = "C:\Users\<you>\<ProjectName>Extraction"
New-Item -ItemType Directory -Force -Path "$workdir\_state","$workdir\_meta" | Out-Null

# Extract a single PBO
& "C:\Program Files (x86)\Mikero\DePboTools\bin\ExtractPbo.exe" -P "$pbo_path" "$workdir\<category>\"
```

**Flags**:
- `-P` — don't pause on completion (required for scripting). MANDATORY.
- DO NOT use `-W` — it means "warnings are errors", too strict for unfinished/legacy PBOs. Skip.
- `-LB` for listing only (inventory pass).

Mikero auto-creates subdirectory `<destination>\<pbo_basename>\` from PBO prefix.

**Note**: ExtractPbo prints to stderr by default. In PowerShell, this triggers `NativeCommandError` — that's a wrapper artifact, NOT a real failure. Don't redirect stderr with `2>&1` (CLAUDE.md warns about this).

## Step 3: State tracking ledger

Set up 4 state files in `_state\`:

### `queue.md`

Ordered list of work units. Each line: `- [ ] <unit-id> — <description>` or `- [x] <unit-id> — DONE: <summary>`.

Unit types:
- `dim/<dimension>` — pass 1 dimensional sweep
- `<entity>/<name>` — pass 2 per-entity deep dive  
- `APPLY skill_changes for <X>` — apply pending findings to skills
- `PASS_END_CHECK pass-<N>` — convergence check

### `seen.json`

Machine-readable state per PBO/entity: extraction status, files read, dimensions extracted, findings_added count per unit, sha1 cache for skip-on-re-read.

### `findings.jsonl`

Append-only one-line-per-finding. Schema:

```json
{
  "ts": "ISO-8601",
  "id": "f_001",
  "pbo": "<name>",
  "pass": 1,
  "unit": "dim/config-root",
  "dimension": "config.cpp|model.cfg|script|layout|rvmat|sounds|particles|persistence|other",
  "pattern": "<concise description>",
  "evidence": "<path>/<file>:<line_range>",
  "novelty": "new|variant|confirm|dup",
  "skill_target": "<existing-skill>|new:<slug>|vault:note|vault:style-fingerprints",
  "action_pending": "append|consider_new_skill|vault_note|skip|applied"
}
```

### `skill_changes.md`

Markdown log of every APPEND or CREATE applied. One entry per skill edit with findings list + diff +/- lines + marker.

## Step 4: Dimensional sweep (pass 1)

Process files in **dimensional order** for a single PBO:

1. `config.cpp` (root) — entity declarations, mod metadata
2. `config.cpp` (per-sub-entity) — vehicle/item per-class configs
3. `model.cfg` — skeleton, animations, sections
4. `Scripts/` `.c` files — Enforce Script logic
5. `.layout` files — UI widgets
6. `.rvmat` materials — sample 5-10 representatives
7. `.ptc` particles — current Enfusion format
8. Sounds (config + sample of .ogg names)
9. `.p3d` models — strings extraction sample (3 representative)
10. `LM_Plane_Assets/` or other shared subdirs
11. Misc (graphics/, Inputs.xml, residuos)

For each file read: emit findings to `findings.jsonl` with `path:line` evidence MANDATORY.

**Per file**:
1. Read the file
2. Identify patterns
3. For each pattern: classify novelty by grepping `~/.claude/skills/**/*.md` for existing coverage
   - Found and identical → `confirm`
   - Found but Llama's version is different → `variant`
   - Not found → `new`
   - Already in this file's findings → `dup`
4. Assign `skill_target` (existing skill, `new:<slug>`, or `vault:*`)
5. Write JSONL line

## Step 5: Per-entity deep dive (pass 2)

Process one entity at a time (e.g., one aircraft/vehicle/weapon per unit). Look for **per-entity quirks** not captured by dimensional sweep:

- Custom logic beyond parameter overrides
- Per-entity tuning preferences
- Inheritance variations
- Unique features (combat code, special physics, etc.)

Per-aircraft units typically yield ~3-10 findings each. Aircraft with custom code (combat, water physics) yield more (Catalina, Spitfire ≈ 9-11). Aircraft that are pure parameter overrides yield ~3.

## Step 6: Novelty classification rules

Use these to decide `novelty`:

| Novelty | When | Action |
|---|---|---|
| `new` | Pattern not documented in any current skill | Counts toward convergence threshold |
| `variant` | Same pattern as documented but in different application/context | Document with cross-ref to original |
| `confirm` | Pattern matches existing skill content exactly | Don't append; just track for stats |
| `dup` | Already in this run's findings.jsonl | Skip emission |

**Honest verification rule**: don't claim `new` without grepping existing skills first. Don't claim `confirm` without verifying the existing skill actually documents the exact pattern.

## Step 7: Cite-then-verify discipline

When emitting a finding about another author's code:
- **Evidence is MANDATORY** in form `<relative_path>:<line_range>` or `<path>:<line>,<line>,<line>` for multi-line
- Never write "X function does Y" without an evidence path
- Never extrapolate behavior; only document what's literally in the code
- If unsure: read the file again with offset/limit at specific lines

**Anti-confabulation rule when reading another author's code**: their code may use undocumented engine APIs, non-obvious patterns, or have bugs. Don't assume their patterns are correct — document the pattern AND note suspected issues separately.

Example finding entry (good):
```
"pattern": "DC_3 OnDebugSpawn crea 4 wheels pero attachments[] solo permite 3 slots. La 4ta queda en cargo player."
"evidence": "LM_DC_3.c:79-86 vs LM_DC_3/config.cpp:134"
```

Example finding entry (BAD — assumed instead of cited):
```
"pattern": "DC_3 spare wheel system"
"evidence": "LM_DC_3.c"  // line missing
```

## Step 8: Skill APPEND vs CREATE decision

For each cluster of findings by `skill_target`:

```
¿Existe skill cuyo scope cubre este dominio?
├─ Sí → ¿Los findings refinan/extienden lo existente?
│       ├─ Sí → APPEND a esa skill
│       └─ No (contradice/sustituye) → APPEND con marcador VARIANT + nota
└─ No → ¿≥7 findings new+variant del mismo dominio?
        ├─ Sí → CREATE skill nueva
        └─ No (<7) → APPEND a skill más cercana O vault note
```

**Threshold relaxation**: for genuinely orthogonal domains (no existing skill can plausibly contain the patterns), create the skill anyway even with <7 findings. Spec compliance vs domain coherence — domain coherence wins for unique formats.

Example: `dayz-particles` was created with only 6 findings because Enfusion .ptc format is orthogonal to everything else.

## Step 9: APPEND mechanics

When appending to an existing skill:

1. **Read full skill first** (verify current content, don't blindly append)
2. **Find appropriate section** OR create `## <ModName> Mod Extraction Patterns` at the end
3. **Sub-organize by topic** if many findings (e.g., "CfgMods patterns" / "Performance" / "Vehicles")
4. **Marker at end** with findings IDs:
   ```
   <!-- <modname>-mod-extraction: findings f_001, f_002, ... | pbo: <name> | pass: N | date: YYYY-MM-DD -->
   ```
5. **Read-after-write** to verify marker present and content consistent

## Step 10: Vault note structure

For findings that don't fit any skill:

```
<research-notes>\<ModAuthor>\notes\
├── <author>-style-fingerprints.md      # Naming conventions, code style, authorship identifiers
├── <author>-curiosities-and-quirks.md  # Anti-patterns, jokes, easter eggs, mistakes
├── <author>-3d-source-catalog.md       # Inventory of source asset PBOs
```

Always link findings to evidence paths. Vault notes serve as discoverable reference when user later asks "what did Llama do with X?".

## Step 11: /loop dynamic mode for autonomous iteration

For multi-day work, use `/loop` in dynamic mode. One unit per turn:

```
/loop Procesa siguiente unidad de <project> extraction.
Spec: <path>/<project>-design.md
Queue: <workdir>/_state/queue.md
State dir: <workdir>/_state/

Protocolo cada turno:
1. Lee queue.md y toma la PRIMERA línea con [ ]
2. Ejecuta la unidad (dimensional / per-entity / APPLY / PASS_END_CHECK)
3. Actualiza state, tick la línea
4. ScheduleWakeup 240s if más unidades; sin schedule si converged or flag raised

Reglas:
- UNA unidad por turno
- Antes de cada finding: grep en ~/.claude/skills/ para novelty honesta
- Evidence obligatorio path:linea
- Anti-runaway: >40 findings en una unidad → flag y stop
```

**Pacing**: 240s between turns keeps prompt cache warm (under 5-min window) for back-to-back iterations.

## Step 12: Convergence

Strict spec rule: **two consecutive passes with <2 novel findings** = converged.

In practice, **diminishing returns** is the real signal:
- Pass 1 (dimensional sweep): typically 50-100 novel findings
- Pass 2 (per-entity deep dive): typically 20-40 novel findings (~50% drop)
- Pass 3 (revisit with full context): typically <5 novel findings

If pass 2 drops <50% of pass 1 AND most novel findings are minor cross-entity synthesis, **pragmatic convergence is acceptable** — pause for user decision rather than burn iterations on confirms.

**Convergence outputs**:
- Write `_state/CONVERGED.md` with metrics
- Write `<project>-final-report.md` to vault (TL;DR, skills modified, patterns, recommendations)
- Update category consolidated report

## Step 13: Final report structure

```markdown
---
type: <project>-final-report
date: YYYY-MM-DD
passes_executed: N
findings_total: <N>
skills_created: [...]
skills_enriched: [...]
vault_notes: [...]
---

# <Project> — Final Report

## TL;DR (one page max)
What was done, key discoveries, status.

## Skills created
Per skill: scope, sections, finding count.

## Skills enriched
Per skill: diff +/- lines, sections added.

## Vault notes
Per note: purpose, findings.

## Patrones transversales
Cross-entity patterns appearing in 7+ of N entities.

## Decisiones / recomendaciones
For future mods in same domain.

## Métricas finales
Iterations, time, files inspected, knowledge added.

## Pendientes
If user opts to extend (pass 3, additional skills, etc.).
```

## Anti-patterns observed during reverse-engineering work

### Recover historical artifacts before declaring a companion missing

[EXACT][CLAIM-R21-PBO-HISTORICAL-RECOVERY] Before concluding that a referenced
PBO or archive is unrecoverable, search delivery history and metadata as well
as live files:

- Use cloud-sync metadata to recover the resource tree, names, sizes,
  timestamps, content hashes and deletion provenance. A live hydration mapping
  proves only that a mapping exists; it does not prove payload bytes remain.
- Inspect browser download history for stable attachment or channel
  identifiers, but never retain expiring signed query strings, cookies or
  credentials.
- Search the normal delivery UI, including linked announcement channels, and
  preserve each recovered revision separately with timestamp and SHA-256.
- Treat Jump Lists, Recycle Bin metadata, Steam manifests/caches and archive
  indexes as supporting evidence, not as the missing payload.

Hash and size metadata can prove identity if a copy later appears, but cannot
substitute for the bytes. A later revision is a historical reference, never an
unlabelled replacement for the missing exact version. This sequence recovered
a later companion revision after metadata first identified the exact deleted
artifact in a 2026-07-20 case study.

1. **Don't trust filenames as authoritative**: a PBO named `aviation_dials` may turn out to be a source-only distribution (verified case from LM_Planes).
2. **Don't conflate ZIP/RAR contents with PBO contents**: source PBOs often wrap asset zips, but those zips are NOT the mod itself.
3. **Don't assume parameter overrides are simple**: Llama's "simple" 99-line parameter file for an aircraft references custom base class with 60+ Get* methods and 1900 lines of logic.
4. **Don't claim convergence without honest grep**: confirm findings only after `grep ~/.claude/skills/` proves the pattern is actually documented.
5. **Don't apply skill changes without read-after-write**: appending to a skill that already has the section creates dupes; always re-read.
6. **Don't write apostrophes inside bash heredocs**: single quotes in 'EOF' blocks break parsing. Use Write tool for content with apostrophes.
7. **Don't escape backslashes in JSON evidence paths**: use forward slashes (`LM_Planes/Scripts/4_World/file.c`) — JSON parsers reject unescaped backslashes.
8. **A referenced-but-missing class means the extractor DROPPED it, not that it's absent**: if the code calls `new FooCommand(...)` but no recovered file defines `class FooCommand`, do NOT conclude it lives elsewhere or "wasn't recovered, re-derive from scratch". The recovery tools lose real blocks (JAPM: the `japm-pbo-recovery` extractor's size filter + name-by-`original_size` collisions — 133 extracted, 122 saved). **Brute-force decompress every entry in script size range and grep for the class name** before claiming it's unrecoverable. Verified: `HumanGunnerCommand` (a 626-byte block) was filtered out of the Gunner_SIB_NIC recovery; brute-force found it and it changed the mechanic's interpretation. (See `japm-pbo-recovery` Troubleshooting.)
9. **Don't infer RUNTIME BEHAVIOR from partial control-flow**: reading `key_Forward.ForceDisable(false)` and concluding "the player can walk" was wrong — the movement (`//tp`) was commented out AND a `HumanCommandScript` ignores locomotion input regardless. A behavior claim ("can move / can't move", "fires / doesn't") must be traced to the **entity that governs it** (the active `HumanCommand`, the state machine), not to input-gating or setup code that may be vestigial, disabled, or overridden downstream. `DZ-R2`/`G3` (honest verification) applies to runtime behavior, not just API signatures.

## Tooling fallbacks when py3d unavailable

For binary `.p3d` inspection without py3d:

```powershell
# Strings extraction (printable ASCII >= 4 chars)
$bytes = [System.IO.File]::ReadAllBytes($p3d)
$current = ""
$strings = New-Object System.Collections.Generic.HashSet[string]
foreach ($b in $bytes) {
    if ($b -ge 32 -and $b -le 126) { $current += [char]$b }
    else {
        if ($current.Length -ge 4) { [void]$strings.Add($current) }
        $current = ""
    }
}
$strings | Where-Object { $_ -match '^(axis_|pos_|light_|seat_|dmgzone_)' } | Sort-Object
```

Captures memory points, selection names, texture references. Not as complete as py3d (no geometry, no LODs), but enough to identify model structure.

## Examples of well-extracted findings

Good extraction (LM_Planes f_037):
```json
{
  "pattern": "Aerodinamica real en Enforce Script: lift coefficient cubic polynomial Cl=ClCoef3*aoaRad^3 + ClCoef2*aoaRad^2 + ClCoef1*aoaRad + ClCoef0 con stall transition smoothing. Drag coefficient parabolic + induced drag Cd_i = Cl^2/(pi*AR*Oswald). Dynamic pressure q = 0.5*density*v^2. Forces aplicados via SafeApplyForce / SafeApplyTorque. Lift direction calculada como (velocityNorm * up) * velocityNorm (perpendicular a velocidad).",
  "evidence": "LM_Planes_extracted/LM_Planes/Scripts/4_World/entities/LlamaPlaneScript.c:906-940,1020-1100",
  "novelty": "new",
  "skill_target": "new:dayz-aviation"
}
```

Specific algorithm cited, line ranges proven, novelty justified, skill destination chosen.

## Cross-references

- [[dayz-mod-workflow]] — implementation protocol (use AFTER extracting patterns, when applying them)
- [[enforce-script-reference]] — general Enforce Script patterns (likely target for many findings)
- [[dayz-pbo-build]] — opposite direction (packaging your own)
- [[dayz-aviation]] — example of skill created via this workflow
- [[dayz-particles]] — example of orthogonal-domain skill (created with <7 threshold relaxed)
- `japm-pbo-recovery` — recover source from JAPM/PBO-Tools-obfuscated PBOs BEFORE the sweep. Optional external skill, **not** included in this pack.
- `kgb-deobfuscator` — strip KGB_DF preprocessor cruft after JAPM recovery. Optional external skill, **not** included in this pack.

## Lessons-learned from LM_Planes project

- **Re-scope on Day 1 if inventory contradicts assumption**: 42/43 PBOs were source-only. Saved weeks.
- **Pass 1 dimensional sweep is 80/20 win**: catches all major patterns. Pass 2 per-entity catches custom code. Pass 3 is usually diminishing returns.
- **Template detection accelerates pass 2**: once you identify "all aircraft are clones of two templates (Tigermoth + Catalina)", you can confirm clone status quickly + focus on the customized ones (Catalina, Spitfire) for new patterns.
- **Author fingerprints emerge**: by pass 2 you'll see naming, code style, sound asset ownership patterns that let you predict next quirks.
- **Vault notes are essential**: 20% of findings don't fit any skill but are valuable reference (style fingerprints, anti-patterns, jokes, decisiones reveladoras). Don't lose them.

<!-- created from LM_Planes reverse-engineering project | 130 findings extracted | 2 passes | author: claude+the author | date: 2026-05-23 -->


## (added 2026-08-31, SP-128) Prove that extraction decoded the payload before measuring it

`ExtractPbo` is the required extractor in Steps 0-2. Do not substitute `PboViewer.exe` for an
automated sweep: it can report `Pbo successful unpack`, return exit 0, and write entries marked
`Cprs` under the correct filenames while leaving their payload bytes compressed. File existence
and a success string therefore do not prove extraction.

Use these checks before parsing the result:

1. Extract to an explicit scratch destination with `ExtractPbo`. A fallback that writes beside
   the input must never run against a read-only Workshop source; copy the PBO to scratch first.
2. Compare representative output sizes with a trusted extraction. A layout expected at 6,444
   bytes but emitted at 1,579 bytes is still compressed even though its name is correct.
3. Do not replace the extractor with hand-written LZSS. Bohemia's variant uses a 4,096-byte ring
   buffer preinitialized with spaces; a wrong decoder can produce text that starts plausibly and
   then degrades, which is more dangerous than a hard failure.
4. Run the existing parser against a known baseline before measuring improvements. In the
   measured TraderX case, reproducing the previous 42/46 layouts first was the control that made
   the later 46/46 result credible.

Treat a baseline mismatch as an extraction failure. Stop the sweep instead of drawing findings
from bytes whose decoding has not been proved.
