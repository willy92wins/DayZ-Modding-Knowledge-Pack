# Server-Side Performance Patterns

Canonical write-up of the server-tick performance techniques used across DayZ mods
and vanilla-adjacent code. Consolidated 2026-07-07 from two source clusters:

1. **Expansion eAI** (`salutesh/DayZ-Expansion-Scripts @ 8f75d554`) — the
   budget-per-frame scheduler, backoff, staggered scan, FPS-adaptive throttling and
   rolling-average patterns, verified in `dayz-ai-patterns` (PC-2 / PC-7 / PC-9b) and
   its `references/eai-pathfinding-groups.md`. Those PC-* entries are the eAI-specific
   instances of the generic principles written up here.
2. **LFPowerGrid perf/simplification audit** (`LFPowerGrid_dev/LFPowerGrid_Audit_Report_2026-06-17.md`,
   read-only static pass, every finding cite-verified at `file:line`) — the server-side
   budget/backoff/staggered-scan and side-check (`#ifdef SERVER` vs `IsServer`) evidence
   in a real production mod, plus the ScriptInvoker-vs-polling bus contrast.

The generic `#ifdef SERVER` / `IsServer()` / `IsDedicatedServer()` side-check rules and
the ScriptInvoker lifecycle rule live in the core SKILL.md as **hard rules 17-20 and 28**;
section (f)/(g) below cross-reference them rather than restating them.

`[EXACT]` = the snippet is copied from a source file verified at the cited `path:line`.
`[DESIGN]` = the snippet is a distilled/parameterized pattern, not a byte-for-byte quote.

---

## (a) The problem — the server tick has a fixed budget

A DayZ dedicated server advances the world on a single simulation thread. Every entity
that wants periodic work (self-heal, target scans, LOS, visual sync, wire propagation)
competes for the **same tick**. Two failure shapes dominate, and both are server-side and
event/tick-shaped, **not** per-frame UI:

- **O(n²)-per-event work that fires often.** LFPowerGrid's `ValidateAllWiresAndPropagate`
  ran **5 `GetAll()` passes per self-heal**, each O(n²) in registry size, reached via
  `DoGlobalSelfHeal` on a 500 ms debounce after any device move/cut
  (`LFPG_NetworkManager.c:2605,2631` + `LFPG_DeviceRegistry.c:81-104`, audit §B row 1).
  The fix is structural: fetch the device list **once** and pass it by-ref into the rebuild
  helpers (kills 3 of 5 passes), and replace `outArr.Find(ent)` O(n²) dedup with a seen-map.

- **Ungated always-on diagnostics.** Per-node `SetPowered` diagnostic string builds
  (`LFPG_MemoryCell.c:188-208`, `LFPG_ElectronicCounter.c:286-300`, `LFPG_LogicGate.c:178-191`)
  and a per-validation-tick charger log (`LFPG_ElecGraph.c:2844-2854`) built and `Print`ed a
  multi-part string on every dirty node at production `LFPG_LOG_LEVEL=2` — always-on RPT spam
  with zero LoC payoff to remove but real per-tick cost (audit §B rows 3-4). Rule of thumb:
  a log string that is **concatenated unconditionally** costs even when the log level would
  discard it — gate the *concat*, not just the print.

The techniques below are the vocabulary for keeping many entities inside one tick budget.

---

## (b) Budget-per-frame scheduler — cap work per tick, resume next tick

Instead of "every entity does its full work every tick", a central scheduler gives each
tick a **budget** and advances only as many entities as fit, resuming where it left off on
the next tick. Expansion eAI runs exactly this: a global `s_eAI_FTO` (frame-time-offset /
scheduler mode) flag flips the whole AI population from "update every entity every frame"
into scheduler mode once the population crosses a threshold.

`ExpansionWorld.c:247-250` (`Scripts/4_World/DayZExpansion_AI/Classes/ExpansionWorld.c`) —
the scheduler is the thing that reads `s_eAI_FTO >= 2` to decide each AI's per-tick interval
(see backoff in (e)). Vanilla mirrors the "one central tick manager, register/unregister"
shape in **core hard rule 23** (centralize all periodic ticks in a single manager) — a
budget scheduler is that manager plus a per-tick work cap.

```c
// [DESIGN] Budget scheduler skeleton — one manager owns the tick, caps work/tick.
class LFPG_TickScheduler
{
    protected ref array<EntityAI> m_Registered;   // hard rule 8: reuse, never `new` in tick
    protected int m_Cursor;                        // resume point across ticks
    protected const int WORK_BUDGET_PER_TICK = 32; // tune to measured frame time

    void OnTick(float dt)
    {
        int n = m_Registered.Count();
        if (n == 0) return;
        int processed = 0;
        while (processed < WORK_BUDGET_PER_TICK && processed < n)
        {
            if (m_Cursor >= n) m_Cursor = 0;       // wrap
            EntityAI e = m_Registered[m_Cursor];
            if (e) DoWork(e, dt);                  // the actual per-entity work
            m_Cursor++;
            processed++;
        }
        // remaining entities are picked up next tick — work spread, not dropped
    }
}
```

The scheduler's payoff is that the **worst-case tick cost is bounded by `WORK_BUDGET_PER_TICK`**,
independent of population. It trades latency (an entity may wait a few ticks for its turn)
for a flat frame time.

---

## (c) FPS-adaptive interval + rolling average — scale work rate to headroom

When the server has headroom, do work at the base rate; when it's under load (frame time /
`pDt` grows), stretch the interval so the *per-real-second* work stays constant. Expansion
eAI does this for LOS checks: this is **PC-9b**.

`eAIBase.c:8089-8097` (`Scripts/4_World/DayZExpansion_AI/Entities/AI/eAIBase.c`) — [EXACT]:

```c
if (s_eAI_FTO < 2)
    interval = LOS_CHECK_INTERVAL;
else
    interval = LOS_CHECK_INTERVAL * (pDt / ExpansionWorld.AI_UPDATE_INTERVAL);
if (m_eAI_LOSCheckDT >= interval)
    m_eAI_LOSCheckDT = 0;
m_eAI_LOSCheckDT += pDt;
if (m_eAI_LOSCheckDT < interval && !m_eAI_TargetChanged)
    return state.m_LOS;   // return cached LOS; skip the raycast this tick
```

The key line is `interval = LOS_CHECK_INTERVAL * (pDt / AI_UPDATE_INTERVAL)`: when the
scheduler stretches `pDt` to 5× the base interval, the LOS interval also stretches 5×, so an
AI updated at one-fifth the rate does **not** get five times the LOS-check frequency. The
effective LOS rate stays constant regardless of how loaded the scheduler is. Setting
`m_eAI_TargetChanged` forces a fresh check, bypassing the cache — the escape hatch for
correctness-critical transitions.

**Rolling average** feeds this: to decide "is the server loaded", average `pDt` over a
window instead of reacting to a single spike. Expansion's `pDt` is already the scheduler's
smoothed step; the pattern generalizes to any adaptive interval:

```c
// [DESIGN] Rolling average of frame time to drive an adaptive interval.
protected float m_DtAvg;
protected const float DT_SMOOTH = 0.1;   // EMA weight; smaller = smoother/slower
void AccumulateDt(float dt) { m_DtAvg = m_DtAvg * (1.0 - DT_SMOOTH) + dt * DT_SMOOTH; }
float AdaptiveInterval(float baseInterval, float refDt)
{
    return baseInterval * (m_DtAvg / refInterval > 1.0 ? m_DtAvg / refDt : 1.0);
}
```

Same shape appears mod-side as a fixed (non-adaptive) throttle for cosmetic work — the
"adaptive update rate" pattern in `references/llama-extraction-patterns.md` (LM_Planes):
physics runs every tick, dials/HUD throttle to 10 Hz (`DIAL_UPDATE_INTERVAL = 0.1`) because
the human eye doesn't perceive UI refresh above ~10-15 Hz. FPS-adaptive is that same throttle
with the interval *driven by measured load* instead of a constant.

---

## (d) Staggered / modulo-gated scan — spread work across ticks, de-sync the herd

Two distinct sub-techniques, both aimed at never letting the whole population do the same
expensive thing on the same tick.

**Persistent-index staggered scan** — advance one item per tick, full refresh only when the
index is exhausted. Expansion eAI's target scan is **PC-7**:

`eAIBase.c:2962-2966` (`Scripts/4_World/DayZExpansion_AI/Entities/AI/eAIBase.c`) — [EXACT]:

```c
m_eAI_UpdateTargetsTick += pDt;
if (m_eAI_CurrentPotentialTargetIndex >= m_eAI_PotentialTargetEntities.Count()
    && m_eAI_UpdateTargetsTick > Math.RandomFloat(0.1, 0.2))
{
    m_eAI_UpdateTargetsTick = 0;
    m_eAI_CurrentPotentialTargetIndex = 0;
```

`UpdateTargets` advances **one index per tick** rather than scanning the whole list; a full
refresh happens only when the index is exhausted **and** the random interval elapsed. The
`Math.RandomFloat(0.1, 0.2)` jitter is the de-sync: without it, every AI that spawned on the
same frame would finish its scan on the same later frame, re-clustering the cost. The same
jitter idea recurs at `eAITargetInformationState.c:58-67` (PC-14, threat cache,
`Math.RandomIntInclusive(250, 300)`) and `eAIGroup.c:822-830` (PC-18, formation cache,
`Math.RandomFloat(2.0, 4.0)`).

**Modulo-gated scan** — process `entity[i]` only when `(tick + i) % N == 0`, so 1/N of the
population runs each tick, and offsets by index so they don't all land together:

```c
// [DESIGN] Modulo-gating: each entity runs once every N ticks, staggered by index.
protected int m_TickCounter;
void OnTick()
{
    m_TickCounter++;
    for (int i = 0; i < m_Registered.Count(); i++)
        if ((m_TickCounter + i) % SCAN_STRIDE == 0)   // +i staggers the herd
            DoScan(m_Registered[i]);
}
```

Modulo-gating gives a deterministic 1/N spread (good when you want a guaranteed cadence);
random jitter gives a statistical spread (good when deterministic phase would still cluster,
e.g. entities that all register on server boot). LFPowerGrid uses the *event-driven* variant
of "don't do it every tick" — its self-heal is **500 ms debounced** on the triggering event
(`DoGlobalSelfHeal`) rather than polled, which is the strongest form of staggering: do the
work zero times until something actually changes (see (g)).

---

## (e) Exponential / multiplicative backoff — degrade frequency by relevance

When an entity has nothing nearby worth reacting to, **stretch its interval** instead of
disabling it — logic still runs, just less often, and re-arms instantly when relevance
returns. Expansion eAI's is **PC-2**, a flat 5× backoff gated on player proximity:

`ExpansionWorld.c:247-250` (`Scripts/4_World/DayZExpansion_AI/Classes/ExpansionWorld.c`) — [EXACT]:

```c
if (eAIBase.s_eAI_FTO >= 2 && ai.m_eAI_PlayersWithinVisibilityDistanceLimit.Count() == 0)
    updateIntervalCurrent = AI_UPDATE_INTERVAL * 5;   // 50 ms -> 250 ms
else
    updateIntervalCurrent = updateInterval;
```

When no player is within the AI's visibility range, its interval degrades from ~50 ms to
~250 ms. The condition is **AI-local** — each unit decides its own backoff independently, so
a server with 200 idle bots and 3 engaged bots pays full rate for 3 and one-fifth rate for
200. This is the multiplicative-backoff principle (degrade frequency by relevance); the eAI
case uses a fixed 5× factor rather than a growing exponential, but the shape generalizes:

```c
// [DESIGN] Exponential backoff with a cap — grows while idle, snaps back on activity.
protected float m_Backoff = 1.0;
protected const float BACKOFF_MAX = 8.0;
float NextInterval(float baseInterval, bool sawSomethingRelevant)
{
    if (sawSomethingRelevant) m_Backoff = 1.0;                        // snap back
    else                      m_Backoff = Math.Min(m_Backoff * 2.0, BACKOFF_MAX); // double, capped
    return baseInterval * m_Backoff;
}
```

Cap the growth (`BACKOFF_MAX`) so an idle entity still checks often enough to notice when it
becomes relevant. Fixed-factor (eAI's ×5) is simpler and adequate when the "idle" and "busy"
states are binary and cheap to test; growing-exponential is worth it only when the idle test
itself is expensive and idleness is long-tailed.

---

## (f) `#ifdef SERVER` (compile-time) vs `IsServer()` / `IsDedicatedServer()` (runtime)

Cross-references core **hard rules 17-20**. Both mean "do this only on the server", but they
resolve at different times and have different failure modes — picking wrong is a perf **and**
a correctness bug.

- **`#ifdef SERVER` — compile-time.** The block is *not compiled into* the client build at
  all. Use it to keep server-only work (SyncVar writes per rule 17, heavy propagation, disk
  I/O, diagnostics) out of the client binary entirely — zero runtime cost on the client
  because the code doesn't exist there. This is the right tool for **whole subsystems** that
  never run client-side. LFPowerGrid gates its self-heal/propagation and per-node diagnostics
  this way; the audit's recommended fix for the ungated diagnostic strings (§B rows 3-4) is
  precisely to `#ifdef`-guard or delete them so they never build on either side at ship level.

- **`IsServer()` / `IsDedicatedServer()` — runtime.** A branch taken at execution time in a
  build that contains *both* paths. Use it inside code that legitimately runs on both sides
  and must fork behavior per-call (e.g. an `OnRPC` handler that validates on server and
  applies on client). **The load-time trap (hard rules 19-20):** `GetGame().IsServer()`
  returns TRUE on a client *during load*, and `IsClient()` is not reliably true on a client during
  load — so at constructor / module-init / `OnInit` time you must use `IsDedicatedServer()` /
  `!IsDedicatedServer()`, not `IsServer()`/`IsClient()`. After load (post-load callbacks:
  `OnRPC`, `EEContact`, per-tick), `IsServer()`/`IsClient()` are safe and are the standard
  vanilla pattern (rule 20 scope note). The LM_Planes client-only-resource guard in
  `references/llama-extraction-patterns.md` (`!IsClient() && IsMultiplayer()` called *lazily*,
  never at load) is the concrete "skip if MP server" instance of this.

**Perf decision rule:** if the work is server-only for an entire subsystem, prefer
`#ifdef SERVER` — it removes the cost from the client build outright. If the work is one
branch of a both-sides method, use the runtime check, and if it runs at load time use
`IsDedicatedServer()`. Do not wrap a per-tick hot path in a runtime `IsServer()` when a
compile-time gate on the enclosing subsystem would remove the branch entirely.

---

## (g) ScriptInvoker bus vs polling — react to events, don't scan for them

The cheapest scan is the one you never run. Polling asks "did anything change?" every tick;
an event bus (`ScriptInvoker`) is *told* when something changed and does zero work otherwise.
LFPowerGrid's self-heal is the canonical win: it is **500 ms-debounced on the device
move/cut event** (`DoGlobalSelfHeal`) rather than polled every tick — the expensive
O(n²) validation runs only in response to an actual topology change (audit §B row 1).

`ScriptInvoker` is the DayZ event-bus primitive: an entity/manager exposes an invoker,
consumers `Insert(callback)`, and the producer `Invoke(...)` fans out on the event. This
replaces "N consumers each polling the producer's state every tick" with "producer notifies
N consumers once, when the state changes".

```c
// [DESIGN] Event bus instead of per-tick polling.
// Producer:
static ref ScriptInvoker Event_TopologyChanged = new ScriptInvoker();
void OnDeviceMovedOrCut() { Event_TopologyChanged.Invoke(this); }   // fire once, on change

// Consumer:
void Init()   { Event_TopologyChanged.Insert(OnTopologyChanged); }
void OnTopologyChanged(EntityAI src) { /* validate only the affected subgraph */ }
```

**Lifecycle — core hard rule 28 (mandatory):** every `ScriptInvoker.Insert(cb)` **must** be
matched by a `Remove(cb)` in the consumer's destructor, null-checking the invoker first:
`if (Producer.Event_X) Producer.Event_X.Remove(OnTopologyChanged);`. A dangling subscription
keeps a dead consumer reachable (leak) and can crash on shutdown when `Remove` is called on a
freed invoker (see the "ScriptInvoker crash on shutdown" TROUBLESHOOTING row in the core
SKILL.md).

**When polling still wins:** an event bus is worth it when changes are *sparse relative to
ticks* (topology edits, power transitions, player join/leave). If a value changes *every*
tick anyway (a moving position you sample each frame), a direct read is simpler than firing
an invoker every tick — the bus adds fan-out overhead without saving a scan. Choose the bus
when `event_rate << tick_rate`; keep the poll when `event_rate ≈ tick_rate`.

---

## Provenance

- **Expansion eAI patterns** (budget scheduler, FPS-adaptive interval + rolling average,
  staggered/jittered scan, multiplicative backoff): `salutesh/DayZ-Expansion-Scripts @
  8f75d554`, dual-arm research (Claude + Codex), adversarially verified. Snippets marked
  `[EXACT]` are quoted from `dayz-ai-patterns/references/eai-pathfinding-groups.md`, which
  cites full repo paths (`Scripts/4_World/DayZExpansion_AI/...`) at that SHA. The eAI-specific
  instances are PC-2 / PC-7 / PC-9b (+ PC-14 / PC-18 jitter) in `dayz-ai-patterns/SKILL.md`.
- **Production server-side evidence** (5× `GetAll()` self-heal, event-debounced self-heal,
  ungated diagnostic-string cost, `#ifdef SERVER` gating): `LFPowerGrid_dev/
  LFPowerGrid_Audit_Report_2026-06-17.md` §A/§B, read-only static pass, every finding
  cite-verified at `file:line`. Corroborated by the `[VERIFIED LFPowerGrid 2026-06-18]`
  TROUBLESHOOTING row (SP-047) in the core SKILL.md — same audit window.
- **Fixed-rate throttle contrast** (adaptive update rate, dial/HUD 10 Hz): LM_Planes,
  `references/llama-extraction-patterns.md` (workshop 3730564764).
- **Side-check + ScriptInvoker lifecycle rules**: core SKILL.md hard rules 17-20, 23, 28.
