# Expansion eAI: server cost per bot (measured 2026-11-27)

One measured session, DayZ 1.30 DayZDiag, Expansion AI loaded with the DayZ MCP
Expansion adapter. It answers one design question: when eAI loads the server, is it
the bot existing or the bot being simulated? Use the numbers as orders of magnitude,
not as a capacity figure. Raw data: `VAULT/AI/10_Projects/Expansion_Study/research/2026-11-27-eai-server-cost/evidence.md`.

## Setup

- `dayz_test_run(mode="all")`: DayZDiag server and client on the same PC, Chernarus,
  no `-limitFPS`. Mods: CF, Expansion Core, Expansion AI and the MCP Expansion adapter.
  The server compiled with 0 script errors.
- One player with godmode. Bots spawned with `ai_group_spawn`: faction `Passive`,
  formation `Column`, three groups of 8 (the adapter caps at 8 per group and 24 living).
- Two behaviours: `LOOP` (2 waypoints, the group keeps walking) and `HOLD`
  (Expansion `HALT`, no waypoints).
- Each sample is one `server_perf` window of 15-30 s. Cost is read as frame time
  (1000 / avg_fps), never as an FPS difference.
- The map already had 15 AI (`counts.ai`) before any spawn; their origin was not checked.

## Results

[EXACT][CLAIM-EAI-SERVER-COST-ACTIVE-VS-DORMANT] Each pair below was measured
back to back at the same player position.

| State (24 bots) | With bots | Without bots, same spot | Cost |
|---|---:|---:|---:|
| `LOOP`, player ~40 m away | ~7.0 ms (128-159 fps) | ~2.55 ms (376-409 fps) | ~0.18 ms per bot |
| `LOOP`, player ~3 km away | ~2.05 ms (371-607 fps) | 0.90 ms (1113 fps) | ~0.05 ms per bot |
| `HOLD`, player ~40 m away | ~2.1 ms (404-555 fps) | ~2.55 ms (376-409 fps) | not distinguishable from noise |

[EXACT][CLAIM-EAI-DORMANT-STATE-OBSERVED] `ai_group_state` showed which state each group was in:

- **`HOLD` groups went `Dormant` with the player ~40 m away.** All 8 members of the
  group sampled were in that state, with `formation_state NONE`. Dormant is the state
  that calls `DisableSimulation(true)` (PC-5 in `eai-fsm-combat.md`).
- **`LOOP` groups never went `Dormant`, even with the player ~3 km away.** The leader
  stayed in `TraversingWaypoints` and the rest in `FollowFormation`, and positions kept
  changing. Far away they only drop to the slower update rate (PC-2, 5x interval), and
  that is why they still cost about a quarter of their near cost.

## What it means for design

- **A Dormant eAI body is almost free.** It still exists and is replicated, but its cost
  stayed inside the noise. What costs is a bot being simulated while it moves:
  animation, physics, pathfinding and FSM together. This session did not separate
  those four parts.
- **A group with pending waypoints keeps paying wherever it is.** Making far groups
  Dormant, and moving them along their route as data, is where the saving is.
  `[DESIGN]` The simplest form needs no new AI:
  - a manager freezes every group with no player inside a radius;
  - every N seconds it teleports the frozen group along its route;
  - when a player enters the radius, it wakes the group up.
- **Headless clients are no offload path on 1.30.** A DayZ client simulates only its
  own character, and the headless roboclient crashes on this build (see
  `CLAIM-DZ130-HEADLESS-CLIENT-CRASH` in
  `skills/dayz-mcp-verify/references/dayz-1-30-mcp-verify.md`).
- **The vanilla dummy-bot measurements are a different setup.** That same file has
  them, taken with `-limitFPS=60` and no client. They measure vanilla `Bot` dummies,
  not eAI, so they are not directly comparable with the table above.

## Limits of this measurement

- **The baseline drifted.** Without bots at the starting spot the server ran at 851 fps
  at the start of the session and at 376-409 fps later; the cause was not identified.
  Only back-to-back pairs at the same spot are usable, and most cells have 1-2 samples.
- **The client competed for the same CPU.** It ran on the same PC, and there was human
  input on the PC during the 16-bot step. The 8 → 16 → 24 ramp (749 → 398-510 →
  128-449 fps) is too noisy for a per-bot slope.
- **There was no combat.** The `Passive` faction gave threat 0, so targeting, LOS and
  fire FSMs did not run. A hostile group will cost more; that is not measured here.
- **This is DayZDiag, not a retail `DayZServer_x64` with `-limitFPS`.**
