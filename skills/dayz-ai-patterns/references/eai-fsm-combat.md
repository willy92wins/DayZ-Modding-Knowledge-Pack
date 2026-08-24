# eAI FSM & Combat Patterns

Source: salutesh/DayZ-Expansion-Scripts @ 8f75d554

---

## PC-5 — eAIState_Dormant: DisableSimulation from FSM state

`Scripts/4_World/DayZExpansion_AI/Classes/FSM/states/eaistate_dormant.c:1-17`

`DisableSimulation(true)` on enter, `DisableSimulation(false)` on exit. Conditions for entry: no combat, no nearby players, no pending waypoints, no movement, leader is AI. Master.xml lists Dormant as an explicit state.

Pattern: use an FSM state — not a flag or inline `if` — to gate physics/animation. Exit the state to restore simulation; don't spread the enable/disable calls across callers.

---

## PC-11 — eAIState_Fighting: combat FSM with hysteresis (0.4 / 0.2) and guard clauses

`Scripts/4_World/DayZExpansion_AI/Classes/FSM/states/eaistate_fighting.c:18-38`
`Scripts/4_World/DayZExpansion_AI/Classes/FSM/states/eaistate_fighting_fireweapon.c:78`

```
// enter when GetThreatToSelf() >= 0.4
// exit  when GetThreatToSelf() <  0.2
```

Entry guards: `IsRestrained`, `IsUnconscious`, `IsInTransport`, `GetRunningAction` checked before activating. `IsFightingFSM` flag synchronizes with external systems. The fire-weapon sub-FSM has its own guard chain: `IsRestrained -> GetTarget -> IsFighting`.

Hysteresis rule: enter threshold > exit threshold to prevent rapid oscillation when threat hovers near a single value.

---

## PC-13 — FSM loaded from XML + code; composition via sub-FSMs

`Scripts/4_World/DayZExpansion_AI/Entities/AI/eAIBase.c:661-666`
`Scripts/FSM/Master.xml:3-8`

LoadFSM pattern in eAIBase:
  ExpansionFSMType.LoadXML(...)
  Spawn(...)
  StartDefault()

Master.xml composes sub-FSMs: Vehicles, Fighting, Reloading. Dormant is a state in the master. Changing state composition requires editing XML, not Enforce code — decouples behavior definition from implementation.

---

## PC-9 (Codex angle) — FOV pre-filter before LOS raycast

`Scripts/4_World/DayZExpansion_AI/Entities/AI/eAIBase.c:8156-8168`

`eAI_CalculateFOVHalfAngleH` computes half-angle. Stance reduces effective FOV. If `angleDiffH > threshAngleH`, the target is discarded before the raycast fires. Raycasts are expensive; FOV is a cheap angle comparison that eliminates most candidates.
