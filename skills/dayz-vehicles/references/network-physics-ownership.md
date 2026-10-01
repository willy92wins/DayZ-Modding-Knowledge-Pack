# Network, physics, and ownership: who controls the pose

Extracted from `SKILL.md` (cut 3, 2026-08-15). The DETAILS live here; the short
statement and when to read this are in the `## LESSONS ARCHIVE` index of SKILL.md.
Nothing in this file is repealed: these are active lessons, ordered by topic
instead of date.

---

## (added 2026-06-28) Network ownership: server-side forced seat != client ownership; PHYSICS is driven by owner

Verified invariant (source + in-game, DayZ-MCP Phase 5 S0). PREFLIGHT before any attempt to
drive/automate a car from a client peer or reason about "who drives":

- The car is a **Pawn** (`Transport extends Pawn` under `FEATURE_NETWORK_RECONCILIATION`,
  transport.c:53 -> Car car.c:98 -> CarScript carscript.c:170). The `IsOwner()` of `IsServerOrOwner()`
  (carscript.c:3222-3231) is the **car's network OWNERSHIP**, not the player's (glossary pawn.c:5-8:
  Owner = client controlling the pawn).
- **`IsServerOrOwner()` DOES NOT gate throttle.** Its only consumers are teardown/fluids
  (carscript.c:822/850/986). Throttle->physics is **proto native** (`SetThrottle` car.c:202, "future
  throttle value") and is applied by **body simulator = the OWNER**. The only script `SetThrottle`
  (carscript.c:1377) is dead in production (`#ifdef DIAG_DEVELOPER`).
- A car **without client-owner = `IsAuthorityOwner`** (authority without owner, pawn.c:199-200) -> simulated
  by server -> a server-side `SetThrottle` **DOES move it**. This is a **single-box/SP
  artifact**, NOT proof that server drives cars owned by a client. (DayZ-MCP S0 F2:
  server moved a PHYSICS car pos_delta=2.29 because no client owned it.)
- A server-side **`StartCommand_Vehicle`** (e.g. MCP's `vehicle_enter`) seats the player ONLY
  server-side: the client **never gets `GetGame().GetPlayer().GetCommand_Vehicle()` nor car
  ownership** (measured in-game x6, yields `not_seated` on client peer). Real get-in
  (`ActionGetInTransport.Start()`, shared client+server method, actiongetintransport.c:82-98) runs
  `StartCommand_Vehicle` on the **CLIENT'S** Human + reserves seat via juncture
  (`AddInventoryJunctureEx`/`SetVehicle`, :141-161). Ownership transfer is proto-native (no
  `SetNetworkOwner` exists in script).
- **Practical consequence:** to drive/measure **owner-side** from a client, client must
  **take ownership itself** (client-side get-in), not rely on server-side forced seat. And an
  owner-authority test in **single-box** is **confounded** (client never truly owns) ->
  clean discriminator is a 2-machine dedicated setup with remote client performing get-in.
- Diagnostic readings: `IsOwner()` (pawn.c:194), `IsAuthorityOwner()` (pawn.c:199-200),
  `GetOwnerIdentity()` (pawn.c:209), `GetNetworkID()` (object.c:815). Extends get-in/radial case
  (LL-164) to network dimension. Origin: DayZ-MCP S0 (2026-06-28).
- **Driving owner-side from script (the actuator — verified in-game 0→39 km/h):** `Car.SetThrottle/SetSteering/
  SetBrake` called from MISSION (`OnUpdate` / a job) DO NOT move owner-sim PHYSICS — **`super` of
  `CarScript.OnInput(dt)` (`carscript.c:1303`) OVERWRITES them every frame** with local driver input=0. Fix: apply
  throttle INSIDE a `modded class CarScript.OnInput`, **AFTER `super.OnInput(dt)`** (where vanilla debug autopilot
  `carscript.c:1377` does it). NO injection via `HumanInputController` (vehicle input is native,
  no override API). Symptom: "car belongs to owner but `SetThrottle` does not move it". Origin: DayZ-MCP Phase 5 (SP-032).

## Angular velocity is NOT yaw/pitch/roll; derive omega from the pose delta (SP-170, origen LFHeli 2026-08-05)

`dBodySetAngularVelocity` takes angular velocity as rotation around x, y and z, **not
yaw/pitch/roll** — vanilla spells it at `enphysics.c:163`: *"Angular velocity,
rotation around x, y and z axis (not yaw/pitch/roll)"*. The Enfusion axis map is
yaw → Y, pitch → Z, roll → X (right-hand rule). Cross-checked on two independent
vanilla sources: `YawPitchRollMatrix("70 15 45", mat)` at `enmath3d.c:125-131`
matches the COLUMNS of `Rz(pitch) . Ry(yaw) . Rx(roll)` to 4e-7;
`dayzplayercameravehicles.c:137-139` reads `dBodyGetAngularVelocity(vehicle)` and
routes Y to yaw, Z to pitch, X to roll for camera lag. Corollary: `mat[i]` from
`GetTransform` (`enentity.c:288`) and from `YawPitchRollMatrix` are world-space
BASIS VECTORS (columns), not rows — mixing them up flips the sign of any rotation
derived from those matrices.

The trap that bites: if the solver keeps rate accumulators in deg/s (`m_PitchRate` /
`m_RollRate` / `m_YawRate`), those rates are NOT the derivative of the orientation
that gets written once a later step moves the pose without touching them (a
levelling stabilizer, a cosmetic pendulum adding a roll delta, a takeoff
level-assist). Feeding them as omega commands a rotation that the next
`SetOrientation` contradicts — that is the "body fighting the pose" judder.

Recipe: derive omega from the REAL pose delta, never from the accumulators.

    GetTransform(before);
    SetOrientation(target);
    GetTransform(after);
    // w*dt = 1/2 * sum_i (b_i x a_i) over the three basis vectors
    dBodySetAngularVelocity(this, sum * (0.5 / dt));

Exact to O(theta^3) (the per-tick delta does not reach 6 deg), immune to the
pendulum or stabilizer moving the pose on their own, and automatically ZERO at
call-sites that command the sampled pose (transition holds, ground clamp) with no
extra branch. Benign failure: if `SetOrientation` does not refresh the transform
on the same tick, `after == before`, omega = 0, behaviour identical to before.

## PHYSICS = owner prediction with reconciliation: writing pose fights it (SP-180, added 2026-08-06, LFHeli F-01)

Extends the ownership section above. Verified invariant (runtime + file, LFHeli 2026-08-06).
PREFLIGHT upon ANY symptom of "input lag" / "rubberbanding" / "client reverts transforms" in a
server-authoritative CarScript:

- **Measure the strategy BEFORE theorizing** (1 line, either side): `Print(GetNetworkMoveStrategy().ToString())`
  — NONE=0, LATEST=1, PHYSICS=2 (`pawn.c:138-148`; getter proto native `pawn.c:218` — YES it is exposed to script;
  a previous note stating the opposite cost a 3-week diversion in LFHeli). In DayZ 1.29 CarScript runs
  **PHYSICS by default** (measured `str=2 own=true` on the pilot client); no config flag exists to select it
  (verified vanilla + Expansion): the engine sets it by native class. `FEATURE_NETWORK_RECONCILIATION` is
  unconditional (`defines.c:64`).
- **Under PHYSICS the owner ALREADY simulates predictively** (full Pawn contract in vanilla: `pawn.c:256-329`
  ObtainMove/ConsumeMove/ReplayMove/RewindState; `CarScriptMove/OwnerState` `carscript.c:3198-3218`;
  `IsServerOrOwner()` `carscript.c:3222-3231`). Consequences:
  1. A server that writes pose/velocity per tick (`SetOrientation`/`SetVelocity`) DOES NOT cooperate: it causes
     continuous owner<-authority correction = **structural round-trip lag + snap-backs**. The symptom is
     felt even on loopback (RTT is not the only latency: server tick + replication + rewind).
  2. Writing TRANSFORM from the owner client REVERTS in ~0.3 s (measured LFHeli D1). It is not a bug to
     debug: it is reconciliation working. Do not waste cycles there.
  3. The compatible path is that of Expansion 1.28+: **symmetric owner/server forces** (`dBodyApplyForce`
     `enphysics.c:146`, world space; commit gated by `dBodyIsActive && dBodyIsDynamic`,
     `ExpansionPhysicsState.c:209-218`) + input inside native `PawnMove` (its legacy RPC is TURNED OFF under
     PHYSICS, `DayZExpansion CarScript.c:1014-1051`) + custom Move/OwnerState contract with `super` first
     (`ExpansionHelicopterScript.c:164-213`). The engine integrates; nobody writes pose.
- **Cheap spike before committing to that architecture** (ForceSpike E pattern, LFHeli
  `plans/2026-08-06-forcespike-e.md`): default-off tuning flag + 1.5 s window in which both sides
  apply the SAME force (anti-gravity + lateral pulse on an axis untouched by anything in the model) and the server
  suspends its kinematic actuator; per-tick traces on both sides; offline parser decrees YES/NO/INCONCLUSIVE
  (`LFHeli_dev/tools/spike_verdict.py`). Harness traps already paid for: the abort must be SYMMETRIC
  (engine/seat/flight state exit), hijacked key suppression goes UPSTREAM of all
  channel consumers, and any exit from flight state clears the window.
- Evidence status: ALL MEASURED. Verdict flight 2026-08-06: **YES** — 3 clean pulses on the
  owner (local slope ~1.6 m/s2 vs 1.5 theoretical, retained gain, transient reversal <=30% due to
  owner->server offset); snap-back upon window EXPIRING is the kinematic actuator reabsorbing
  (the reason for removing pose writing in the full path); an owner-only pulse near the ground
  (unarmed server by AGL) reverted 91% = the live F4 limitation. Pilot perception: null
  (0.15 g lateral during a climb at 7-11 m/s) — the gate is telemetric, not feel-based.

## Custom Pawn framework (Move/OwnerState): the type ladder and its hard rules (SP-188, added 2026-08-06, LFHeli D3-1)

Continuation of SP-180: when the approach is "forces + owner prediction", the FIRST step of
construction is an INERT Pawn framework (custom types + log-only hooks, flight intact) — validates engine
wiring before migrating any solver (lowest-risk ordering verified against the
Expansion corpus). Recipe verified by vanilla source + compile gate (LFHeli 2026-08-06):

- **Type ladder** (derive from the last rung, not from Pawn*): `PawnMove -> TransportMove ->
  CarMove -> CarScriptMove` and `PawnOwnerState -> TransportOwnerState -> CarOwnerState ->
  CarScriptOwnerState` (`transport.c:11-50`, `car.c:89-93`, `carscript.c:135-152`).
  `TransportOwnerState/TransportMove` carry NATIVE transform + linear + angular velocity
  (`transport.c:13-23,:35-42`): **DO NOT duplicate them in custom state**.
- **Hooks** (`pawn.c:238-311`, all `protected event`): `GetMoveType`/`GetOwnerStateType` (the
  engine instantiates the types AT CONSTRUCTION, `pawn.c:235,:244` — overrides must exist on the
  class, not activate late), `ObtainMove`, `ConsumeMove`, `ReplayMove` (bool: honor super's
  rejection before processing), `ObtainState`, `RewindState(state, move, inout NetworkRewindType)`.
  CarScript already implements Get*Type/ObtainState/RewindState (`carscript.c:3198-3218`) — super
  ALWAYS and exactly once (super's ObtainState/RewindState carry `m_fTime`).
- **Serialization**: `Write/Read` with super FIRST; NEVER serialize `vector` (expand to
  floats); `EstimateMaximumSize()` = super + 4 bytes per scalar (bool counts as 4, conservative).
  The Move carries RAW axes pre-authority-scale (attenuation/FSM are recomputed per solve
  tick; baking them breaks replay determinism). Solver latch/stateful memory goes
  in OwnerState (server -> owner), not in Move.
- **`ReadRawLocal` INSIDE `ObtainMove`** (R22 that cost a round: the native order
  ObtainMove<->EOnSimulate is NOT exposed to script; relying on tick's last read can
  serialize zeroes/stale and your round-trip gates validate EMPTY wiring). Require also that the
  payload gate rejects the run if all samples are neutral.
- **Inert framework instrumentation**: match owner<->authority by EXACT `GetMoveId()`
  (deterministic sampling `id % 64 == 0` on BOTH sides), never by clock; `rewind` is always
  logged (rare), `replay` only sampled (a rewind storm re-runs all pending moves and
  floods client log, truncated to ~255 chars/line); counters aggregated at 1 Hz.
- **"Inert" applies to FLIGHT, not to NETWORK**: custom types add payload per
  move/correction and a Write/Read asymmetry desyncs the owner — the payload gate exists
  for that.
- Evidence status: ALL CONFIRMED IN RUNTIME (LFHeli flight D3-1, 2026-08-06): engine
  instantiates custom types and transports them (G1), 94 sampled moves with exact 5 axes on
  both sides and 48 with non-zero payload (G2), 477 rewinds + 47 replays visible on owner (G3).
  Receiver trap: DayZ script log wraps each Print in single quotes — a log
  parser must strip the quote attached to the LAST token on the line or the payload gate
  gives a false FAIL on that field.
- CAVEAT measured on the same flight: CONTACT script chain received NOT A SINGLE callback from
  skid-ground seating (0 OnContact across entire flight, with real touchdown via AGL) — overriding
  Car.OnContact DOES NOT guarantee gentle settling contacts. Before building logic on
  vehicle contacts, first measure that the callback fires for YOUR case (a one-shot print);
  candidate robust path is EntityEvent.CONTACT + EOnContact, pending validation.

## Attack/release state must read raw input (SP-201, added 2026-08-31)

**[CODE-VERIFIED; in-game A/B pending]** A first-order command filter such as
`cmd += (raw - cmd) * k` decays asymptotically and does not reach exact zero. A
boolean derived from the filtered working value (`cmd != 0`) therefore remains
active after release: attack constants stay selected and idle-only levelling or
damping never starts. Capture `m_<axis>Raw` when the input is read, keep the
filtered command separate, and derive activity only from the raw field on every
simulation side. Owner and server must use the same source; mixing raw owner
state with filtered server state creates a second disagreement.

## Forced sleep needs registration warm-up and a settled-state gate (SP-153, added 2026-08-31)

- **[IN-GAME VERIFIED]** Do not call `dBodyActive(this,
  ActiveState.INACTIVE)` in the `EEInit` tick. The collider may not finish
  registration, leaving visual and physical position split. Keep the body active
  for a measured warm-up (about 3 s in the verified case) before the first sleep.
- **[DESIGN REVIEWED; partial in-game gate]** Sleep only when speed is near zero
  and AGL is at the local surface. Do not impose a lower AGL bound: a settled
  pivot measured `-0.02 m`. Explicitly request `ACTIVE` while the body is not
  settled; merely stopping the repeated `INACTIVE` call does not wake a body.
- `ClampMinValue(name, value, minimum, fallback)` does not impose an upper cap;
  the fourth argument handles non-finite input. Apply a safety maximum at the
  consumer with `Math.Min(tuned, cap)`.
