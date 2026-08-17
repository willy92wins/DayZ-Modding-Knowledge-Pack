---
name: dayz-ai-patterns
description: >
  Use this skill when working with DayZ Expansion AI (eAI module): FSM states (Dormant, Fighting),
  combat hysteresis, threat/targeting, LOS/FOV, pathfinding, group formation, squad target
  distribution, or the NoiseSystem. Also trigger when a user asks why AI bots are not
  attacking, not patrolling, walking through doors, ignoring sounds, all focusing the same
  enemy, not spreading into formation, or when debugging eAIBase, eAIGroup, eAIState, or
  ExpansionPathHandler. Trigger on: eAI, DayZ AI, AI FSM, FSM pathfinding, group AI,
  squad AI, threat targeting, LOS FOV AI, Expansion AI, AI bots.
---

# DayZ Expansion AI Patterns (eAI)

> Material source: salutesh/DayZ-Expansion-Scripts @ 8f75d554fda209b257c00deb8f01c181e67c980a
> Research: dual-arm (Claude + Codex), adversarially verified. All path:line cites are confirmed.

## Overview

12 patterns covering the irreducible AI architecture of Expansion eAI:

| ID   | Pattern                                  | File reference                          |
|------|------------------------------------------|-----------------------------------------|
| PC-5 | Dormant state: DisableSimulation via FSM | `eaistate_dormant.c:1-17`               |
| PC-11| Fighting FSM: hysteresis + guard clauses | `eaistate_fighting.c:18-38`             |
| PC-13| FSM loaded from XML + sub-FSM composition| `eAIBase.c:661-666`, `Master.xml:3-8`   |
| PC-9a| FOV pre-filter before LOS raycast        | `eAIBase.c:8156-8168`                   |
| PC-9b| LOS throttle adaptive to update interval | `eAIBase.c:8089-8097`                   |
| PC-14| Threat cache with jitter 250-300 ms      | `eAITargetInformationState.c:58-67`     |
| PC-7 | Staggered target scan + jitter 0.1-0.2 s | `eAIBase.c:2962-2966`                   |
| PC-2 | Backoff 5x: no players in visibility     | `ExpansionWorld.c:247-250`              |
| PC-15| Pathfinding: recalc thresholds + cost    | `ExpansionPathHandler.c:581-592`        |
| PC-16| Path filters: navmesh costs (door=10000) | `expansionpathfilters.c:131-147`        |
| PC-17| Group targets: distribution by tracking  | `eAIGroup.c:726`, `eAIBase.c:3497-3505` |
| PC-18| Formation positions: cached + jitter 2-4s| `eAIGroup.c:822-830`                    |

Server-side scheduling/throttling principles (budget-per-frame, FPS-adaptive interval, rolling average, modulo-gating): canonical server-perf write-up: `enforce-script-reference/references/server-performance.md` (PC-2/PC-7/PC-9b in THIS skill are the eAI-specific instances). For `#ifdef SERVER` vs `IsServer()` side checks and ScriptInvoker lifecycle, `enforce-script-reference` does apply (hard rules 17-20, 28).

---

## FSM Architecture

### PC-13 — FSM loaded from XML; sub-FSM composition

`eAIBase.c:661-666` + `Scripts/FSM/Master.xml:3-8`

`LoadFSM()` calls `ExpansionFSMType.LoadXML(...)`, then `Spawn(...)` and `StartDefault()`. Master.xml includes sub-FSMs for Vehicles, Fighting, and Reloading. Dormant is a state in the master.

Key implication: state composition changes via XML, not Enforce code. Adding or removing states does not require a code recompile.

Full detail: `references/eai-fsm-combat.md` — PC-13.

### PC-5 — Dormant state: DisableSimulation managed by FSM

`eaistate_dormant.c:1-17`

On enter: `unit.DisableSimulation(true)`. On exit: `unit.DisableSimulation(false)`. Entry conditions checked by FSM transitions: no combat, no players within visibility range, no pending waypoints, no active movement, leader is an AI unit.

Do not scatter `DisableSimulation` calls across logic — let the FSM state own that toggle. The FSM exit restores simulation; no caller needs to remember to re-enable it.

Full detail: `references/eai-fsm-combat.md` — PC-5.

---

## Combat FSM

### PC-11 — Fighting FSM: hysteresis thresholds and guard clause chain

`eaistate_fighting.c:18-38` (enter/exit logic)
`eaistate_fighting_fireweapon.c:78` (fire sub-FSM guards)

Enter combat when `GetThreatToSelf() >= 0.4`. Exit when it drops below `0.2`. The gap prevents oscillation when threat hovers around a single value.

Guard clauses before enter: `IsRestrained`, `IsUnconscious`, `IsInTransport`, `GetRunningAction`. The fire-weapon sub-FSM has its own chain: `IsRestrained -> GetTarget -> IsFighting`. `IsFightingFSM` flag is set so external systems can query combat state without inspecting the FSM directly.

Hysteresis rule: always set enter > exit. A single threshold creates a flip-flop bug in practice.

Full detail: `references/eai-fsm-combat.md` — PC-11.

---

## Threat & Targeting

### PC-14 — Threat cache with jitter 250-300 ms

`eAITargetInformationState.c:58-67`

```
if (force || diff > Math.RandomIntInclusive(250, 300))
{
    m_ThreatLevelUpdateTimestamp = time;
    m_ThreatLevel = m_Info.CalculateThreat(m_AI, this);
```

Each target information state carries its own timestamp and a per-call random cooldown. `CalculateThreat` runs at most once per ~275 ms on average. The jitter means AIs do not all recalculate threat on the same server tick.

Full detail: `references/eai-pathfinding-groups.md` — PC-14.

### PC-7 — Staggered target scan: persistent index + jitter 0.1-0.2 s

`eAIBase.c:2962-2966`

```
m_eAI_UpdateTargetsTick += pDt;
if (m_eAI_CurrentPotentialTargetIndex >= m_eAI_PotentialTargetEntities.Count()
    && m_eAI_UpdateTargetsTick > Math.RandomFloat(0.1, 0.2))
{
    m_eAI_UpdateTargetsTick = 0;
    m_eAI_CurrentPotentialTargetIndex = 0;
```

`UpdateTargets` advances one index per tick rather than scanning the entire list. A full refresh only happens when the index is exhausted AND the random interval has passed. Prevents all AIs from finishing their scan simultaneously.

Full detail: `references/eai-pathfinding-groups.md` — PC-7.

---

## LOS / FOV

### PC-9a — FOV pre-filter before LOS raycast

`eAIBase.c:8156-8168`

`eAI_CalculateFOVHalfAngleH` produces the effective half-angle (stance-adjusted). If `angleDiffH > threshAngleH`, the candidate is discarded before a raycast is issued. Angle comparison costs nanoseconds; a raycast costs microseconds to milliseconds depending on scene complexity.

Apply cheap spatial tests (angle, range band) before expensive ones (raycast, physics query).

Full detail: `references/eai-fsm-combat.md` — PC-9 (Codex angle).

### PC-9b — LOS throttle adaptive to current update interval

`eAIBase.c:8089-8097`

```
if (s_eAI_FTO < 2)
    interval = LOS_CHECK_INTERVAL;
else
    interval = LOS_CHECK_INTERVAL * (pDt / ExpansionWorld.AI_UPDATE_INTERVAL);
if (m_eAI_LOSCheckDT < interval && !m_eAI_TargetChanged)
    return state.m_LOS;
```

In scheduler mode (`s_eAI_FTO >= 2`) the LOS interval scales with `pDt`. An AI updated at 5x the base interval does not get 5x the LOS check rate — the effective check frequency remains constant. Setting `m_eAI_TargetChanged = true` forces a fresh check, bypassing the cache.

Full detail: `references/eai-pathfinding-groups.md` — PC-9 (Claude angle).

### PC-2 — Backoff 5x when no players within visibility distance (AI-specific)

`ExpansionWorld.c:247-250`

```
if (eAIBase.s_eAI_FTO >= 2 && ai.m_eAI_PlayersWithinVisibilityDistanceLimit.Count() == 0)
    updateIntervalCurrent = AI_UPDATE_INTERVAL * 5;
else
    updateIntervalCurrent = updateInterval;
```

When no player is within the AI's visibility range, its update interval degrades from ~50 ms to ~250 ms. Logic is not disabled — it runs at one-fifth frequency. Condition is AI-local: each unit decides its own backoff independently.

This is the AI-specific implementation of the backoff principle (degrade frequency by relevance). Canonical server-perf write-up: `enforce-script-reference/references/server-performance.md` (PC-2/PC-7/PC-9b are the eAI-specific instances).

---

## Pathfinding

### PC-15 — Path recalculation with thresholds and measured cost

`ExpansionPathHandler.c:581-592`

`ExpansionPathHandler` does not recalculate on every target update. Three guards:
- `PATH_RECALCULATE_THRESHOLD`: minimum positional delta before path is stale
- `m_MinTimeUntilNextUpdate`: cooldown between recalcs
- `m_TimeIt.GetElapsed()`: actual cost measurement per recalc (feedback for adaptive scheduling)

Legacy path: `eAIPathFinding`, activated with `#define EAI_USE_LEGACY_PATHFINDING`. Default is `ExpansionPathHandler`.

Full detail: `references/eai-pathfinding-groups.md` — PC-15.

### PC-16 — Path filters with navmesh costs; DOOR_OPENED = 10 000

`expansionpathfilters.c:131-147`

`SetFilterCost` per area type: CRAWL, CROUCH, JUMP, DEEP_WATER = 10. DOOR_OPENED = 10 000. Cost 10 000 is effectively prohibitive — the pathfinder routes around an open door rather than through it (avoids collision with door physics geometry).

Filters encode behavioral preferences, not just include/exclude flags. A cost of 10 000 is a soft prohibition without a hard constraint.

Full detail: `references/eai-pathfinding-groups.md` — PC-16.

---

## Group & Formation

### PC-17 — Group target distribution: prevents squad over-concentration

`eAIGroup.c:726` + `eAIBase.c:3497-3505`

`eAIGroup.AddTarget` distributes target data to members. Before assigning target X to a member, `eAIBase` checks `num_ai_in_group_not_tracking`: if it reaches 0 (everyone already tracks X), returns false. The squad naturally distributes across multiple enemies without explicit assignment logic.

If all bots are chasing the same player, check whether `num_ai_in_group_not_tracking` logic is intact and `AddTarget` is being called rather than bypassed.

Full detail: `references/eai-pathfinding-groups.md` — PC-17.

### PC-18 — Formation positions cached with per-AI jitter 2-4 s

`eAIGroup.c:822-830`

`GetFormationPosition` checks `m_eAI_FormationPositionUpdateTime` with `Math.RandomFloat(2.0, 4.0)`. Each member has its own jitter window. When the leader moves, members do not all recalculate simultaneously — they spread the recalc over a 2 s window.

Formation recalc is per-AI, not per-group. The group does not broadcast "recalculate now" to all members.

Full detail: `references/eai-pathfinding-groups.md` — PC-18.

---

## References

- `references/eai-fsm-combat.md` — PC-5, PC-11, PC-13, PC-9a
- `references/eai-pathfinding-groups.md` — PC-14, PC-7, PC-2, PC-9b, PC-15, PC-16, PC-17, PC-18


## NoiseSystem — feeding noise the AI can hear (added 2026-06-06)

Source-verified vs vanilla v1.24 (`3_game/noise.c:1-23`):

- Server-side API: `g_Game.GetNoiseSystem().AddNoise(entity, params, mult)` /
  `AddNoisePos(entity, pos, params, mult)` / `AddNoiseTarget(pos, lifetimeSec, params, mult)`.
- `AddNoiseTarget` creates a positional **decoy with a duration** — infected/AI investigate a
  position with no entity attached (distraction devices, impacts).
- `NoiseParams.Load("CfgNoises_entry")` or `LoadFromPath(path)`.
- Rain/wind reduce effective noise: `NoiseAIEvaluate.GetNoiseReduction(g_Game.GetWeather())`
  (player steps use it, `dayzplayerimplement.c:3204-3208`).
- Weapon shots are config-side: `class NoiseShoot { strength = 82; type = "shot"; }` in the weapon
  config (real mod example: IMPWMODPart2 MCXSpear `config.cpp:73-77`).
