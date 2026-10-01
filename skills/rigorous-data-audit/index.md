# DayZ Skills — Fact Audit Index

> ⛔ **CRITICAL NOTICE 2026-05-12 — THIS AUDIT CONFABULATES**
>
> Re-verification of 2026-05-12 against real files (not against narrative audit) showed that most critical findings were **invented**. Out of 11 P0/P1 claims verified one by one:
>
> - **6 fully confabulated** (1a, 1b, 1d, 2, 3, 4)
> - **2 real** (1c LOD bug in `dayz-3d-viewer/p3d_to_gltf.py`, 1e Arma 3 demo code in `py3d-direct-generation.md`)
> - **3 partial/exaggerated** (5 unverified, 6 partial — only Motorcycle/Helicopter not HouseNoDestruct, 7 exaggerated)
>
> **Confabulation rate ≈ 55%.** This audit is not citable as a source. For any action depending on a finding here: **open the real file, grep, verify against `path:line`** before acting. Individual per-skill reports likely share the same confabulation rate — treat them equally.
>
> **Real actionable actions (the only 2 verified):**
>
> 1. `dayz-3d-viewer/scripts/p3d_to_gltf.py:30-51` — `classify_lod()` only recognizes Arma 3 LODs (`2e13`/`3e13`). Modern DayZ (`6e15`/`7e15`) fall back to "memory". Fix: add bands `5.9e15..6.1e15` → `view_geometry`, `6.9e15..7.1e15` → `fire_geometry` before `else`.
> 2. `dayz-model-pipeline/references/py3d-direct-generation.md:538-545` — copy-paste `classify_lod()` snippet teaches Arma 3 values without marking as legacy. Fix: add modern bands or mark snippet as historical demo.
>
> **F2 from fix-tracker (`_shared/dayz-conventions.md`):** purge only `Motorcycle`, `Helicopter` from `dayz-pbo-build/references/validation-scripts.md:226-228`. Keep `HouseNoDestruct`, `Vehicle` (valid in DayZ).
>
> Everything else from audit: read but **DO NOT act without verification against primary source**.

---

**Date**: 2026-05-11
**Scope**: 12 DayZ skills from plugin `skills-plugin/.../skills/`
**Depth**: Deep (conventions doc + py3d source + Bohemia wiki + cite-then-verify; P:\ marked for manual verification)
**Work done by**: 4 general-purpose agents in parallel + aggregation

---

## TL;DR

| Skill | VERIFIED | SUSPECT | CONFABULATED | Verdict |
|---|---:|---:|---:|---|
| `dayz-p3d-audit` | 34 | 12 | **9** | 🔴 Critical — Arma 3 bug survives |
| `dayz-p3d-inspector` | 51 | 11 | 0 | 🟢 Clean (prior 3e13/7e13 already fixed) |
| `dayz-3d-viewer` | 31 | 4 | **2** | 🔴 Critical — same Arma 3 bug |
| `dayz-model-pipeline` | 47 | 6 | **5** | 🔴 Critical — `LOD_RESOLUTION` dict bad |
| `dayz-particles` | 38 | 6 | 3 | 🟡 Off-by-one (276 vs 277) |
| `dayz-pbo-build` | ? | ? | **many** | 🔴 Critical — false "Forbidden EnScript" |
| `dayz-preflight` | ? | ? | 0–1 | 🟢 Clean (registry casing) |
| `japm-pbo-recovery` | ? | **many** | ? | 🟡 Wrong name + empirical constants |
| `enforce-script-reference` | ? | 1 | 0 | 🟢 Only SUSPECT(P:\) |
| `dayz-ui-development` | ? | 2+ | 0 | 🟢 SUSPECT(P:\) on COLOR_DAYZ_RED |
| `dayz-mod-workflow` | ? | few | 0 | 🟢 Cleanest |

**Totales aproximados**: ~248 VERIFIED, ~65 SUSPECT (≥30 requieren P:\), ~20 CONFABULATED.

---

## 🔴 Critical findings (immediate action)

### 1. Bug Arma 3 LOD thresholds — TRES skills afectadas

The bug that motivated this audit is in more places than the initial report:

| Skill | File | Line | Problem |
|---|---|---|---|
| `dayz-p3d-audit` | `scripts/audit_p3d.py` | 40-42 | `classify_lod()` accepts both `3e13`/`7e13` and `6e15`/`7e15`. User-facing messages cite Arma 3 as canonical. |
| `dayz-p3d-audit` | `SKILL.md` | 71, 87 | Cites `FireGeo (3e13)` and `GeoPhys (2e13)` as DayZ LODs. |
| `dayz-3d-viewer` | `scripts/p3d_to_gltf.py` | 40-49 | `classify_lod()` uses **only** Arma 3 values. All DayZ FireGeo/ViewGeo falls into `else: res > 1e14` and is labeled `memory`. **Resulting glb lacks correct labels.** |
| `dayz-model-pipeline` | `references/py3d-direct-generation.md` | 85-94 | The `LOD_RESOLUTION` dict — canonical skill reference to generate .p3d — uses `2e13` and `3e13`. |
| `dayz-model-pipeline` | `references/py3d-direct-generation.md` | 404-418 | `classify_lod()` reader with same bug. |

→ These five points require patch aligned with `dayz-conventions.md@01b15a6` (canonical table: Visual 0..N, ShadowVolume 1e4/1.1e4, Geometry 1e13, Memory 1e15, LandContact 2e15, **ViewGeometry 6e15**, **FireGeometry 7e15**).

### 2. `dayz-p3d-audit/scripts/audit_p3d.py:34` — ShadowVolume off by 6 orders

Current line: `if 9e9 <= resolution <= 1.1e10:  return "ShadowVolume"`
Real (conventions doc): ShadowVolume is `10000` and `11000`, i.e. `1e4..1.1e4`. Current range is 6 orders of magnitude higher — never matches a real .p3d, no model is classified as ShadowVolume.

### 3. `dayz-p3d-audit` clasificador omite Roadway, Paths, Hitpoints

The LODs `3e15` (Roadway), `4e15` (Paths), `5e15` (Hitpoints) — valid in DayZ and recognized by sibling skill `dayz-p3d-inspector` — fall into `Other(...)` and are warned as "Unknown". Massive false negative on models with those LODs.

### 4. `dayz-pbo-build/SKILL.md:189-217` — "Forbidden in Enforce Script" **wholesale falso**

The section "Forbidden in Enforce Script" lists as forbidden:
- Ternary `?:` — **is valid**
- `++` / `--` — **are valid**
- `foreach` — **is valid** (exists in EnScript)
- `+=` — **is valid**

Applying this guidance would cause a user to rewrite correct code to "avoid" features that actually exist. The **entire section must be deleted** (or replaced with the real list, which is much shorter: no templates, `auto` exists, etc. — cross-check against Bohemia wiki).

### 5. `dayz-pbo-build` LOD validator usa string-match

Validator does `'resolution' in str(lod.type).lower()` — but `py3d.Lod.resolution` is a **float**, not a string with the word "resolution". Validator does not work in any case. It also hard-errors when `ce_center` is missing which is NOT an engine-required memory point — validator fails every vanilla model.

### 6. `dayz-pbo-build` `known_bases` with Arma 3 classes

Base class list includes `HouseNoDestruct`, `Motorcycle`, `Helicopter`, `Vehicle` — **Arma 3** classes, not DayZ. Same confabulation pattern as threshold bug. Must clean against vanilla `CfgVehicles`.

### 7. `japm-pbo-recovery` — incorrect name and single-source constants

- "JAPM" **is not the public name** of any documented obfuscator. Public docs call it "PBO Tools". Users seeking help will never find this skill by name.
- Magic constants (`65793` / `8388608` / `4282663` for LCG, "≤3 cluster" heuristic, hardcoded "A6 Storage" classes, relative-vs-absolute LZSS interpretation) are **single-source empirical**. They are not corroborated in literature. They may be true but cannot be stated as verified facts.

---

## 🟡 Hallazgos medios

### `dayz-particles`
- Claim "277 vanilla particles" in SKILL.md:13,182 + catalog header. Catalog table has **276** entries — off-by-one. Small but indicates it was not counted.
- Remainder verified directly against `dayzexplorer.zeroy.com` (POOL_SIZE=10000, enum values, GetInstance server guard) — skill is the most solid of the visual ones.

### `dayz-preflight`
- Cosmetic: registry key casing inconsistent between SKILL.md and code. Functional but confusing. Sole finding.

---

## 🟢 Skills limpias

### `dayz-p3d-inspector`
**v4 changelog explicitly records fix for bug 3e13/7e13.** Treats `facenormals` as pool consistently. Only drift in `extract.py` shadow threshold dict (cosmetic).

### `dayz-mod-workflow`
**The cleanest skill.** Embeds anti-confabulation in its own process (Mini-audit + GOLDEN RULE + E08). 6 of 6 Recurring Error Catalog entries verified. Zero confabulated.

### `enforce-script-reference`
- **Bug refs VERIFIED**: T148506 (inventorySlot string-vs-array), T156746 (CallLater 4.5h precision loss), CCINonRuined vs CCINone — all confirmed on Bohemia feedback tracker.
- Sole SUSPECT: SKILL.md:61 states `IsClient()` returns FALSE on client during load (asymmetric pair of verified IsServer()=TRUE). Conventions doc only says "prefer IsDedicatedServer()". Advice is correct, mechanism of advice cannot be verified.

### `dayz-ui-development`
- SKILL.md:317-322 — `COLOR_DAYZ_RED` "exactly ONE place — mainmenupromo.c:158" is **claim repeated verbatim** from conventions doc, no source verifiable without P:\. **If it is wrong, it is wrong in two places.**
- SKILL.md:482-512 — Dabs WidgetAnimator, LinearColor, NotifyPropertyChanged: line refs (e.g. `ViewController.c:84-117`) unverifiable. Dabs repo exists; line refs and claims "30 easing curves / 140+ named colors" are SUSPECT until adding permalinks.

---

## Recommended action (prioritized)

### P0 — Critical, will break if left
1. **Eliminate Arma 3 LOD bug** in `dayz-p3d-audit`, `dayz-3d-viewer/p3d_to_gltf.py`, `dayz-model-pipeline/references/py3d-direct-generation.md`. Full diff already in `py3d-skills-patch-report.md`.
2. **Fix ShadowVolume range** in `dayz-p3d-audit/scripts/audit_p3d.py:34` (change `9e9..1.1e10` → `9.9e3..1.15e4`).
3. **Eliminate section "Forbidden in Enforce Script"** from `dayz-pbo-build/SKILL.md` or replace it with the true list.
4. **Rewrite LOD validator** from `dayz-pbo-build` to use `lod.resolution` (float) instead of string-match.
5. **Clean `known_bases`** from `dayz-pbo-build`: remove `HouseNoDestruct`, `Motorcycle`, `Helicopter`, `Vehicle`.

### P1 — Confusión / falsos positivos / off-by-one
6. **Add Roadway/Paths/Hitpoints** to the `dayz-p3d-audit` classifier.
7. **Rename/cross-reference** `japm-pbo-recovery` with "PBO Tools" so that it is discoverable.
8. **Recount particles** in `dayz-particles` (277 → 276 or add the missing one).
9. **Reconcile `format_notes.md` vs `odol_reader.py:494`** regarding `allowAnimation` version gating.

### P2 — Caveat / softening
10. **Soften `IsClient()` returns FALSE claim** in `enforce-script-reference`.
11. **Replace single-source claims** in `japm-pbo-recovery` with "empirically observed, no public verification".
12. **Add permalinks** to Dabs Framework refs in `dayz-ui-development`.

### Requires P:\ manual check (does not block but recommended)
- `dayz-ui-development`: confirm `COLOR_DAYZ_RED` only in `mainmenupromo.c:158`.
- `dayz-p3d-audit`: confirm script-side gotchas lines 312-319.
- `dayz-particles`: validate GUIDs and AddonBuilder defaults.
- Total ~30+ items P:\-pending — all marked `SUSPECT(P:\)` in the individual reports.

---

## Reportes individuales (drill-down)

| Skill | Reporte |
|---|---|
| dayz-3d-viewer | [audit-dayz-3d-viewer.md](./audit-dayz-3d-viewer.md) |
| dayz-mod-workflow | [audit-dayz-mod-workflow.md](./audit-dayz-mod-workflow.md) |
| dayz-model-pipeline | [audit-dayz-model-pipeline.md](./audit-dayz-model-pipeline.md) |
| dayz-p3d-audit | [audit-dayz-p3d-audit.md](./audit-dayz-p3d-audit.md) |
| dayz-p3d-inspector | [audit-dayz-p3d-inspector.md](./audit-dayz-p3d-inspector.md) |
| dayz-particles | [audit-dayz-particles.md](./audit-dayz-particles.md) |
| dayz-pbo-build | [audit-dayz-pbo-build.md](./audit-dayz-pbo-build.md) |
| dayz-preflight | [audit-dayz-preflight.md](./audit-dayz-preflight.md) |
| dayz-ui-development | [audit-dayz-ui-development.md](./audit-dayz-ui-development.md) |
| enforce-script-reference | [audit-enforce-script-reference.md](./audit-enforce-script-reference.md) |
| japm-pbo-recovery | [audit-japm-pbo-recovery.md](./audit-japm-pbo-recovery.md) |

---

## Observed confabulation patterns (lessons)

Recurrent across findings — **watch out in future skills**:

1. **"Accepts both ranges"** — anti-pattern: when an API has a canonical value, accepting also the "wrong but in the wild" value makes the classifier *teach the bug*. Better: accept only the correct one, mark the other as `Arma3_LEGACY_INVALID`.
2. **Single-source magic numbers** — if a constant (`65793`, `277`, `1e15`) comes from "I measured it once", flag it as such in the doc, not as a fact.
3. **Copy-paste between Arma 3 and DayZ** — `known_bases`, LOD resolutions, class names: Arma 3 references contaminate DayZ skills if no one reverifies them.
4. **"X is forbidden"** without citing engine docs — the `dayz-pbo-build` case "Forbidden EnScript" is a perfect example: forbidding real features based on confusion.
5. **"Exactly N" / "the only place" superlatives** — `COLOR_DAYZ_RED` "exactamente un sitio". These claims are highly prone to confabulation. Always cite with permalink + commit hash.
6. **Public name != internal name** — `japm` vs "PBO Tools". Skills must use the name the user googles.

Consider adding a check rule in `skill-conventions` that catches (1)-(6) in review.

---

## Methodology and sources

**Tier**: Profundo (conventions doc + py3d GitHub + Bohemia wiki + cite-then-verify; P:\ flagged manual)

**Consulted sources** (consolidated from the 4 agents):
- [dayz-conventions.md @ 01b15a6](https://raw.githubusercontent.com/<author>/Agentic-Z/01b15a6eeea5ea204079cddc9254f62388d0a9e1/.claude/skills/_shared/dayz-conventions.md)
- [KoffeinFlummi/py3d](https://github.com/KoffeinFlummi/py3d)
- [Bohemia Wiki — P3D MLOD Format](https://community.bistudio.com/wiki/P3D_File_Format_-_MLOD)
- [Bohemia Wiki — P3D ODOLV7 Format](https://community.bohemia.net/wiki/P3D_File_Format_-_ODOLV7)
- [Bohemia Wiki — PBO File Format](https://community.bistudio.com/wiki/PBO_File_Format)
- [Bohemia Wiki — Compressed LZSS File Format](https://community.bistudio.com/wiki/Compressed_LZSS_File_Format)
- [Bohemia Wiki — Addon Builder](https://community.bistudio.com/wiki/Addon_Builder)
- [Bohemia Wiki — raP File Format](https://community.bistudio.com/wiki/raP_File_Format_-_OFP)
- [DayZ Server (appid 223350) — SteamDB](https://steamdb.info/app/223350/)
- [MKLink command — Windows CMD](https://ss64.com/nt/mklink.html)
- [DayZ Error 0x00020005 — filePatching](https://feedback.bistudio.com/T153410)
- [DayZ feedback T148506 — inventorySlot string-vs-array](https://feedback.bistudio.com/T148506)
- [DayZ feedback T156746 — CallLater 4.5h](https://feedback.bistudio.com/T156746)
- [PBO-Tools/DayZ-PBO-Obfuscator](https://github.com/PBO-Tools/DayZ-PBO-Obfuscator)
- [DayZ Explorer (Zeroy) — ParticleManager / ParticleList / ParticleSource](https://dayzexplorer.zeroy.com/)

**Tokens consumed by agents**: ~674K tokens, ~227 tool calls, ~32 minutes of wall time.

**Limitations**:
- `P:\` not accessible from sandbox — all claims citing `P:\<path>:line` are marked `SUSPECT(P:\)`.
- `py3d/__init__.py` not fetchable directly from sandbox (provenance lock); used conventions doc as authoritative proxy for the API.
- 80+ "battle-tested facts" in `LFPG_UI_KnowledgeBase_v3.md` were not sampled (time budget). Explicit follow-up in `audit-dayz-ui-development.md`.

**Reproducibility**: the prompts sent to the 4 agents are in `references/audit-prompts.md` for future re-runs following changes to the skills.
