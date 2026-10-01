# DayZ vehicles — invariantes cross-proyecto

> Domain hub: the invariants that **every** DayZ vehicle (car/quad/truck/bike) will
> encounter, along with which project earned each one. Exists because the actual cost of NOT having this
> was re-deriving crew get-in across dozens of iterations in three projects in a row.
>
> Executable detail lives in skill `dayz-vehicles` ("INVARIANTS YOU WILL HIT" checklist at
> beginning of `SKILL.md` + `references/vehicle-structural-parity.md`). This note is the cross-project
> durable record + graph. Promotion rule: `[[evidence-led-memory]]` §"Cross-project
> promotion".

## Vehicle projects (chronological order)

- `[[10_Projects/LFQuad/project-brief|LFQuad]]` — quad (Banshee + Croco physics). **First** to resolve
  get-in, wheel-sim, structural parity. The source of invariants 1, 3, 4.
- **SUB_BRZ** (rip→DayZ pipeline; no vault folder, lives in `<vehicle-import>\` + auto-memory
  `rip-vehicle-import-pipeline`) — re-suffered get-in + componentNN dual-tag + winding. Proved that invariant 1
  is the SAME in an imported car, not something specific to the quad.
- `[[10_Projects/MercedesAMGLF/project-brief|MercedesAMGLF]]` — Mercedes-AMG GT3 via proxies. Closed the
  engine body-proxies convention (invariant 5) and re-confirmed get-in in-game.

## The invariants (which project earned it · where detail is located)

| # | Invariant | Earned in | Detail in skill |
|---|---|---|---|
| 1 | Radial get-in needs **script class** `extends CarScript` overriding `CrewCanGetThrough` (a bare `class X: CarScript` inherits `Transport.CrewCanGetThrough()=false`, `transport.c:493` → action is filtered out and never appears) | LFQuad D34 → re-suffered SUB_BRZ + Mercedes | `vehicle-structural-parity.md` "Crew get-in" |
| 2 | Script module must **load** (`CfgMods files[]` without backslash / without `.p3d` path yielding `*.p3d.p3d`) or class never binds — silent failure | SUB_BRZ / Mercedes | SKILL §"Script binding" |
| 3 | Geometry LOD needs named property **`class=vehicle`** or wheels do not simulate (`WheelCountPresent()==0`, no RPT error) | LFQuad 2026-05-27 (SP-027) | `vehicle-structural-parity.md` |
| 4 | Seats and hubs must have **`componentNN` (dual-tag)** or they are invisible collision islands → spawn blocker / no seat | SUB_BRZ s7 | "componentNN DUAL-TAG" |
| 5 | Crew/wheel proxies in **ViewGeo AND FireGeo**; proxy triangle = engine identity frame `R=((-1,0,0),(0,0,1),(0,1,0))` model-space (NOT `rotation=None` from py3d) | Mercedes (body-proxys) | parity + `rip-import.md` |
| 6 | Wheel `angle1` sign: **measure axis in `.p3d` BEFORE** setting it (offline check predicts inverted rotation without in-game) | LFQuad shipping | `build-packaging-and-debug.md` §2-3 |
| 7 | **One vital plug per car**: vanilla makes SparkPlug AND GlowPlug vital by default (bare `CarScript` requires both, `carscript.c:2004/2011`); petrol overrides `IsVitalGlowPlug()->false` (`civiliansedan.c:363`), diesel `IsVitalSparkPlug()->false` (`offroad_02.c:389`); declare only the vital one in `attachments[]` + attach in `OnDebugSpawn`. "Does not start" with SparkPlug inserted = GlowPlug not overridden, NOT a removed requirement | SUB_BRZ 2026-06-28 | SKILL #8 + `vehicle-config-and-modelcfg.md` sec 15 |

## Why this note exists (the process lesson)

Knowledge of get-in **was captured** in the skill (SP-007 pose, SP-017 wheelPresent), but
arrived **late**: LFQuad victory was not promoted to domain invariant when won, so each
subsequent project re-derived it. Fix was not "more memory" or "more links" — it was **promoting the
invariant the day it is won** and placing it where next project reads it **at startup** (preflight
checklist), not as triage after failure. Rule codified in `[[evidence-led-memory]]` §"Cross-project
promotion"; patch queue for read-only skills in `[[skill-patches-pending]]`.

## 2026-06-29 — Skills audit vs LFQuad/Mercedes/Subaru (consolidation)

Comparison of knowledge from 3 cars vs skills. Confirmed: not a capture failure but findability/timing + wrong destination (May promotions to `dayz-model-pipeline`, later retired). Actions applied to `dayz-vehicles/SKILL.md`: co-driver ViewGeo inward+flags `0x02000000` → **preflight #4**; **METHOD** block (parity-first / in-game-is-the-gate / crew-probe-FIRST); ownership completed with `OnInput` actuator; +LL-103/LL-104/OnDebugSpawn/fitting editor in `references/vehicle-config-and-modelcfg.md`. Vault: LL-166 + LL-175 written; `skill-patches-pending` reconciled (SP-032/036 → applied; SP-041 closed no-issue; SP-040(b) `GetSteering` applied to `dayz-animation-pipeline` plugin via Codex). Reaffirmed (already in §Related): **`dayz-vehicles` is editable user-skill, NOT plugin** — SP-032/036 were wrongly parked as "read-only plugin". Detail: [`30_Sessions/2026-06-29-dayz-vehicles-skill-audit-consolidation.md`](../30_Sessions/2026-06-29-dayz-vehicles-skill-audit-consolidation.md).

## Relacionado

- `[[dayz-capacidades-verificadas]]` — DayZ feasibility verdicts + Enforce/config gotchas.
- Skill `dayz-vehicles` (directly writable in `~/.claude/skills/`, NOT read-only plugin) — destination for
  promotion of every new vehicle invariant.
- [[dayz-model-pipeline]] — LOD/proxy/named-property assembly where invariants 3-5 originate.
- [[evidence-led-memory]] — §"Cross-project promotion", the process rule embodied by this note.
- [[skill-patches-pending]] — patch queue for read-only skills (SP-017/SP-027 are vehicle-related).
- [[20_Knowledge/lessons-learned|lessons-learned]] — durable lessons from LFQuad/SUB_BRZ/Mercedes projects cited above.
- [[10_Projects/MercedesAMGLF/project-brief|MercedesAMGLF]] — project that closed invariant 5 (body-proxies).
