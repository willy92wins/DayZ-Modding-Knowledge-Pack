# eAI Pathfinding, Groups & Perception Patterns

Source: salutesh/DayZ-Expansion-Scripts @ 8f75d554

---

## PC-15 — Pathfinding with recalculation thresholds and measured cost

`Scripts/4_World/DayZExpansion_AI/Classes/PathFinding/ExpansionPathHandler.c:581-592`

`ExpansionPathHandler` does not recalculate on every target update. Guards:
- `PATH_RECALCULATE_THRESHOLD` — minimum delta before path is considered stale
- `simulationPrecision` — controls step resolution
- `m_MinTimeUntilNextUpdate` — cooldown between recalcs
- `m_TimeIt.GetElapsed()` — actual cost measurement per recalc

Legacy alternative: `eAIPathFinding` (activated via `#define EAI_USE_LEGACY_PATHFINDING`). Default system is `ExpansionPathHandler`.

---

## PC-16 — Path filters with navmesh costs: open door = 10 000 (prohibitive)

`Scripts/4_World/DayZExpansion_AI/Classes/PathFinding/expansionpathfilters.c:131-147`

`SetFilterCost` assigns weights per area type:
- CRAWL, CROUCH, JUMP, DEEP_WATER: cost 10
- DOOR_OPENED: cost 10 000 (forces AI to route around, avoiding door physics collisions)

Filters are not just include/exclude flags — they encode behavioral cost. A cost of 10 000 is effectively a prohibition without a hard block.

---

## PC-17 — Group target distribution: prevents over-concentration

`Scripts/4_World/DayZExpansion_AI/Classes/eAIGroup.c:726`
`Scripts/4_World/DayZExpansion_AI/Entities/AI/eAIBase.c:3497-3505`

`eAIGroup.AddTarget` distributes target info to members. Before assignment, `eAIBase` checks `num_ai_in_group_not_tracking`: if it reaches 0 (all members already tracking this target), returns false. Prevents the whole squad from focusing one enemy.

Practical implication: if every bot is already chasing target X, the next call to assign X to a new member is rejected. Spread happens automatically.

---

## PC-18 — Formation positions cached with per-AI jitter 2-4 s

`Scripts/4_World/DayZExpansion_AI/Classes/eAIGroup.c:822-830`

`GetFormationPosition` uses `m_eAI_FormationPositionUpdateTime` with `Math.RandomFloat(2.0, 4.0)` per AI. Position recalculation is deferred per-member, not synchronized across the group. Prevents all members from recalculating simultaneously when the leader moves.

---

## PC-14 — Threat cache with jitter 250-300 ms

`Scripts/4_World/DayZExpansion_AI/Classes/Targets/eAITargetInformationState.c:58-67`

```
if (force || diff > Math.RandomIntInclusive(250, 300))
{
    m_ThreatLevelUpdateTimestamp = time;
    m_ThreatLevel = m_Info.CalculateThreat(m_AI, this);
```

Threat is not recalculated every tick. Each target information state carries its own timestamp and a random cooldown window. The jitter prevents simultaneous threat recalcs across many targets.

---

## PC-7 — Staggered target scan: persistent index + jitter 0.1-0.2 s

`Scripts/4_World/DayZExpansion_AI/Entities/AI/eAIBase.c:2962-2966`

```
m_eAI_UpdateTargetsTick += pDt;
if (m_eAI_CurrentPotentialTargetIndex >= m_eAI_PotentialTargetEntities.Count()
    && m_eAI_UpdateTargetsTick > Math.RandomFloat(0.1, 0.2))
{
    m_eAI_UpdateTargetsTick = 0;
    m_eAI_CurrentPotentialTargetIndex = 0;
```

`UpdateTargets` advances one index per tick. Full list refresh only when index is exhausted AND the random interval has elapsed. Jitter prevents all AIs from completing their scan on the same tick.

---

## PC-2 — Backoff 5x when no players within visibility distance

`Scripts/4_World/DayZExpansion_AI/Classes/ExpansionWorld.c:247-250`

```
if (eAIBase.s_eAI_FTO >= 2 && ai.m_eAI_PlayersWithinVisibilityDistanceLimit.Count() == 0)
    updateIntervalCurrent = AI_UPDATE_INTERVAL * 5;
else
    updateIntervalCurrent = updateInterval;
```

AI-specific implementation: backoff is gated on `s_eAI_FTO` (scheduler mode) and the AI's own player-visibility list. Does not disable logic — degrades frequency from 50 ms to 250 ms.

---

## PC-9 (Claude angle) — LOS throttle adaptive to current update interval

`Scripts/4_World/DayZExpansion_AI/Entities/AI/eAIBase.c:8089-8097`

```
if (s_eAI_FTO < 2)
    interval = LOS_CHECK_INTERVAL;
else
    interval = LOS_CHECK_INTERVAL * (pDt / ExpansionWorld.AI_UPDATE_INTERVAL);
if (m_eAI_LOSCheckDT >= interval)
    m_eAI_LOSCheckDT = 0;
m_eAI_LOSCheckDT += pDt;
if (m_eAI_LOSCheckDT < interval && !m_eAI_TargetChanged)
    return state.m_LOS;
```

In scheduler mode, LOS interval scales proportionally to `pDt`. An AI updated at 5x the base interval does not do LOS checks 5x faster — the effective LOS rate stays constant. Ignoring `m_eAI_TargetChanged` returns cached LOS.
