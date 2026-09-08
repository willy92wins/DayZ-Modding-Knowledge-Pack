# Public wiki / GitHub harvest (2026-09) — hubs + staging pointers

> MIT original prose (Pack-authored). **Does not vendor** Bohemia wiki HTML or third-party README bodies into the release zip.
> Harvest date: **2026-09-07**. Wiki facts from this batch are **`historical` until live-verified** against current `community.bohemia.net` / vanilla `P:\scripts` / CE samples.
>
> **Reconcile, do not duplicate:** gameplay/server systems already distilled live in
> [`knowledge/vault-notes/dayz-wiki-systems-reference.md`](vault-notes/dayz-wiki-systems-reference.md)
> (Wiki Sweep #2, 2026-07). Prefer that note for contaminated areas, stamina/`cfggameplay.json`,
> diag menu categories, object/gear spawners, surfaces, and related errata. This note is the
> **batch-1 harvest index** (hubs, paths, ingest posture) for the 2026-09 public corpus.

## Provenance (Pack `source_id`)

| `source_id` | Kind | Role |
|---|---|---|
| `bi-community-wiki-wayback` | archive | BI Community Wiki via Wayback (`id_` captures → staging markdown). Cite archive URL + harvest date; do not ship HTML. |
| `dayz-public-github-index-2026-09` | web | Public GitHub org/author index + README **pointers** (license clues only). Prefer link+summarize; promote durable facts only with claims evidence. |

Canonical hosts (live often Cloudflare-blocked from automation): `community.bohemia.net/wiki/…`, mirror `community.bistudio.com/wiki/…`.

## Staging corpus (local research inbox — not Pack payload)

Relative to the operator vault research tree (redacted user component):

`C:\Users\<you>\ObsidianVault\AI\30_Research\dayz-public-corpus-2026-09-07\`

| Path under staging | Contents |
|---|---|
| `BRIEF.md` / `SOURCE-MAP.md` | Pipeline goal, exclusions (no Discord, no sealed skill edits), source inventory |
| `harvested/wiki/` | 23 markdown pages + `INDEX.md` + `harvest-meta.json` (Wayback) |
| `harvested/github/` | `GITHUB-INDEX.md`, `user-*.json`, search snapshots, `readmes/` |
| `harvested/dayzmodding/` | Site **DOWN** (HTTP 525); Wayback homepage ~2021 — **historical only** |
| `distilled/PACK-INTEGRATION.md` | Integration checklist for Asistente (inbox → claims → note → source-map → validate) |

## Wiki hubs harvested (batch 1)

Category hubs: `Category:DayZ` and Editing / Tutorials / Official Tools / Scripting / Vehicles / Central Economy / Modelling / Modding Structure.

High-value pages (staging filenames):

- `DayZ_Modding_Basics.md` — P: project drive, Extract Game Data, script module order, `modded class` / `override` / `super`, filepatching → PBO
- `DayZ_Enforce_Script_Syntax.md` — Enforce OOP surface; modded chains; access rules
- `DayZ_Modding_Structure.md` — PBO / addon layout conventions
- `DayZ_Vehicle_Configuration.md` — mission/server vehicle config (**pair later with** skill `dayz-vehicles`; do not conflate)
- `DayZ_Diag_Menu.md` — diagnostic surface (cross-link `dayz-test-ingame` / MCP verify); detailed category list already in vault-notes wiki systems ref
- `DayZ_Central_Economy_mission_files_modding.md` — `cfgeconomycore.xml` append/override pattern
- Also: Server Configuration, Gameplay Settings, Spawning Gear, Object Spawner, Contaminated Areas, Player Spawning, Hosting Linux Server, Terrain sample

**Posture:** treat identifiers and defaults as hints until re-checked live. Honor errata in the vault-notes wiki systems reference (e.g. no vanilla `CfgStamina` class; `vonCodecQuality` 0–20).

## GitHub index (batch 1) — pointers only

Official-ish: `BohemiaInteractive/DayZ-Central-Economy`, `DayZ-Samples`, `DayZ-Misc`, `DayZ-Script-Diff` (+ Experimental).

Community lineage often cited in Pack work: InclementDab (CF / Dabs / Editor), Arkensor (CF / persistence / DB), Jacob-Mango (COT / samples), salutesh (Expansion / eAI / CF forks), first-party `willy92wins` (this Pack, `dayz-mcp`).

Full table: staging `harvested/github/GITHUB-INDEX.md` (46 README copies — **not** redistributed here).

## Next Pack steps (not done by this note)

1. Adjudicate 5–10 durable facts into `sources/claims.json` with Wayback URL + harvest date; `verification_level: historical` until live-verified.
2. Keep sealed `skills/*/SKILL.md` untouched; route skill updates through normal Pack contribution + `packctl`.
3. No Discord ingestion in this pipeline.

## Cross-ref

- [[dayz-wiki-systems-reference]] — prior systems distill (reconcile target)
- `knowledge/DAYZ_INFRA.md` — operator server/launch infra
- Staging `distilled/PACK-INTEGRATION.md` — integration recommendation for Asistente

---

## Batch 2 (2026-09-07) — maximize coverage append

Append-only. Does not rewrite batch-1 section above. Still: **no Discord**, **no sealed skill edits**, staging remains research inbox.

### Counts after batch 2

| Artifact | Batch 1 | After batch 2 | Net |
|---|---:|---:|---:|
| Wiki MD (excl. INDEX) | 23 | 51 | +28 |
| GitHub README copies | 46 | 133 | +87 |
| dayzmodding.dev Wayback MD | homepage stub | 15 | +15 |

Staging: `C:\Users\<you>\ObsidianVault\AI\30_Research\dayz-public-corpus-2026-09-07\`  
Distill index: staging `distilled/BATCH-2.md`

### New wiki hubs / pages (pointers only — bodies stay in staging)

Category hubs added: Server, Terrain Editing, Troubleshooting.

High-value new pages (staging filenames): Surfaces; Error_Codes; Projection_Layer; Central_Economy_setup_for_custom_terrains; Configuring_2D_Map; Workbench_Script_Debugging; Weather_Configuration; Underground_Areas_Configuration; Buldozer_for_Object_Builder / Buldozer_for_Terrain_Builder; CE__Ambient_Spawner; Doors_on_buildings; Ladders_on_buildings; Grass-clutter_*; Administration_Logs; Generating_navigation_mesh; Using_Road_Tool_in_Terrain_Builder; Tools_Launcher; Server_manager; Modding_Samples; Survival; Unusual_Process_Exit; A2-DZ_env_assets_lookup_table; DayZ Tools EULA.

**Posture unchanged:** Wayback/`historical` until live-verified. Reconcile with `knowledge/vault-notes/dayz-wiki-systems-reference.md` (esp. Surfaces).

### GitHub batch 2

+87 README pointers (ExpansionModTeam, DaemonForge UniversalApi/MapLink, enforce LSP/Workbench tooling, more CE schema/tools). Full list: staging `harvested/github/GITHUB-INDEX.md` + `readme-meta-batch2.json`.

### dayzmodding.dev

Live still **525**. Wayback captured Mod-Code-Bases + Enforce Syntax article under staging `harvested/dayzmodding/pages/` — **historical only**.

### Suggested future `source_id`s (not applied here)

- Keep using `bi-community-wiki-wayback` for new wiki pages
- Keep `dayz-public-github-index-2026-09` for README pointers
- Optional new: `dayzmodding-dev-wayback-historical` when promoting Mod-Code-Bases facts

---

## Batch 3 (2026-09-07) — remaining public sources squeeze

Append-only. Still: **no Discord**, **no sealed skill edits**, staging remains research inbox.

### Live wiki / forums

- Live BI wiki: Cloudflare **403**; **browserUse/computerUse not available** this harvest → skipped. Wayback BI wiki **~saturated** (~51 MD) — **do not recommend more wiki scrapes**.
- Bohemia DayZ Editing forums / feedback tracker: not publicly harvestable without login (403 / board not found). Status note in staging `harvested/forums/ACCESS-STATUS.md`.

### Counts after batch 3

| Artifact | After batch 2 | After batch 3 | Net |
|---|---:|---:|---:|
| BI wiki MD (excl. INDEX) | 51 | 51 | 0 |
| GitHub README copies | 133 | 203 | +70 |
| StarDZ chapters/pages | — | 18 | +18 |
| DZconfig wiki MD | — | ~40 | +40 |
| dayzexplorer + YADZ MD | — | ~16 | +16 |
| Steam guide MD | — | 13 | +13 |

Staging: `C:\Users\<you>\ObsidianVault\AI\30_Research\dayz-public-corpus-2026-09-07\`  
Distill: staging `distilled/BATCH-3.md`

### Highest-value new pointers (bodies stay in staging)

- **StarDZ** `DayZ-Modding-Wiki`: gotchas, five-layer script hierarchy, entity system, professional template, troubleshooting, first-mod tutorial (also github.io mirrors under staging `harvested/other/stardz/`).
- **DZconfig wiki**: Understanding CE, loot balancing, types/events/globals, cfggameplay, cfgeconomycore, serverDZ.cfg, init.c.
- **API explorers**: `dayzexplorer.zeroy.com` (1.29) + `dayz-scripts.yadz.app` — cite/browse; avoid vendoring giant class dumps into Pack zip.
- **GitHub +70 READMEs** via topics `dayz` / `enforce-script` / `dayz-mod` / `workbench` / `enfusion` + awesome/wiki searches (includes VPP, Epoch historical, WoozyMasta tooling, StarDZ, DayZGhost plugin, …).

### dayzmodding.dev / dayzmodding.com

- `.dev` still **525**.
- `.com` hub captured as directory of resources (Discord not harvested). Notion link present but low anonymous value.

### Suggested future `source_id`s (not applied here)

- `stardz-dayz-modding-wiki-2026-09`
- `dzconfig-wiki-2026-09`
- `yadz-dayz-scripts-docs` / `zeroy-dayzexplorer` (URL-cite preferred)
