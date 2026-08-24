# The `dayz-mcp` bridge — protocol and design notes

An MCP server that exposes a running **DayZDiag** session as typed tools, so an
agent can spawn an object, drive a car, raycast a surface, read telemetry and
take a screenshot without touching a keyboard, an OCR pass or a macro.

This note is the transferable part: the surface, the invariants that make it
safe, and the engine facts it cost sessions to learn. The knowledge here holds
whether or not you run this particular server.

## Why a pack about offline verification ships this

The pack's argument is that **green does not accredit**. Every offline tool here
— the preflight gate, the ODOL diff, the UI lab — narrows the gap between "it
compiles" and "it works", and none of them close it. Something has to run the
engine and report what actually happened.

That is what the bridge is for. It turns *"the config looks right"* into *"the
car reached 40 km/h over 36 m on one sustained throttle command"*, which is a
different kind of sentence. The `dayz-mcp-verify` skill is the procedure built
on top of it; this note is the contract underneath.

## Tool surface

39 tools are registered; **38 are advertised by default** — `exec_enforce` is an
escape hatch behind an off-by-default flag and an exact-match allowlist.

| Group | Tools |
|---|---|
| **Session lease** | `session_acquire`, `session_acquire_wait`, `session_wait`, `session_heartbeat`, `session_release`, `session_cancel`, `session_status` |
| **Queries** | `query_player_state`, `query_all_players`, `query_get_in_condition` |
| **World mutation** | `world_spawn`, `object_delete`, `object_anim`, `world_time_set`, `world_weather_set`, `notify_players`, `inventory_give`, `player_teleport` |
| **Scene reads** | `scene_raycast`, `surface_query`, `object_inspect`, `telemetry_read` |
| **Camera & capture** | `camera_set`, `camera_get`, `capture_screenshot` |
| **Vehicles** | `vehicle_enter`, `vehicle_get_in_client`, `engine_set`, `vehicle_control`, `vehicle_telemetry`, `vehicle_release`, `vehicle_trace`, `vehicle_prepare_fixture` |
| **Lifecycle** | `dayz_test_run`, `dayz_test_stop`, `logs_since`, `restore_gameplay`, `bridge_status` |
| **Escape hatch** | `exec_enforce` *(disabled unless explicitly enabled)* |

The split that matters is not by group but by **peer**: some verbs run on the
server peer and some on the client peer, and the difference is not cosmetic.
`vehicle_enter` seats a player server-side; `vehicle_get_in_client` makes the
*client* take ownership. Only the second one lets you drive. See §Engine facts.

## Design invariants worth copying

**Server-authoritative, always.** Every mutation goes through the server peer and
every read reports what the server believes. An agent that reads client state and
reports it as truth will confidently describe a world that does not exist for
anyone else.

**One exclusive lease, FIFO.** The game is a single shared box. Concurrent
sessions mutating it produce results that cannot be attributed to a cause, so
mutation requires a lease and the queue is first-in-first-out with an explicit
wait verb. Nothing about this is DayZ-specific; it applies to any agent-driven
singleton.

**A broker daemon owns the port; sessions are clients.** The game polls one fixed
URL. "Use more ports" is not available. So a standalone daemon owns the socket
and every agent session proxies through it — which is what lets more than one
session hold tools at once.

**Fail closed at the ingress, not at the tool.** The allowlist and audit live at
the enqueue chokepoint, so a verb that is not whitelisted cannot reach the game
even if a tool forgets to check. Duplicating the check inside each tool is how
one of them ends up out of date.

**Sustained control needs a deadman.** A driving command that must be re-sent
every frame is unusable from an agent loop with network latency in it. Commands
are *held* with a TTL instead: one call drives until released or until the
deadman expires. An agent that crashes mid-test leaves a car that stops, not a
car that drives into the sea.

**Screenshots are budgeted, not truncated.** Image payloads are sized against the
client's token budget *before* encoding. If the response would exceed the cap the
client rejects the whole response rather than delivering a truncated image — a
half-image that decodes is worse than an error, because it looks like evidence.

## Engine facts the bridge had to discover

These were each paid for with in-game cycles. All citations are vanilla DayZ
script under `P:\scripts\`.

**A server-side seat is not client ownership.** Seating a player from the server
leaves the client without `GetCommand_Vehicle()`. The client takes ownership by
calling `StartCommand_Vehicle` on *its own* player; the engine then hands control
over in `PlayerBase.OnVehicleSeatDriverEnter`, which casts the parent to a `Pawn`
and calls `identity.Possess(pawn)` — under `FEATURE_NETWORK_RECONCILIATION`
(`4_world/entities/manbase/playerbase.c:4266-4280`).

**A car with no client owner is driven by the server.** Under PHYSICS the
throttle is applied by whoever owns the vehicle. On a single-box test setup an
unowned car moves when the server pushes it, which looks like a working
actuator and is not one. Measuring drivability without first establishing
client ownership measures the wrong thing.

**`SetThrottle` and `SetSteering` set *future* input, and `super` overwrites
them.** The vanilla headers say so literally — "Sets the future throttle value"
(`3_game/vehicles/car.c:201-202`), same for steering at `:195-196`. Calling them
from a mission-side tick does nothing visible, because `CarScript.OnInput`
(`4_world/entities/vehicles/carscript.c:1303`) runs afterwards and re-reads the
local driver's input, which is zero. The working shape is to apply the values
**after** `super` inside a `modded class CarScript.OnInput`, mirroring how the
vanilla debug autopilot does it.

**`DEVELOPER` is not defined in DayZDiag; `DIAG_DEVELOPER` is.** Emitting code
under `#ifdef DEVELOPER` compiles to nothing, and worse, a broken assumption
about which defines exist can fail the whole PBO compile — which takes every
tool down with it, not just the new verb.

**Freecam kills the simulation.** Setting the camera to free mode stops the sim;
a look-at camera does not. Any acceptance ladder that screenshots from freecam
between two driving rungs is measuring a frozen world.

**`Print()` goes to `script_*.log`, not the RPT.** Measured, repeatedly, by
people grepping the wrong file.

## Limits

- **It is not a test framework.** It drives the engine and reports; deciding what
  counts as a pass is the caller's job. `dayz-mcp-verify` supplies one such
  ladder for drivable vehicles.
- **Headless execution is bounded by the engine.** Some operations only work with
  a real client attached; that is a DayZ limitation, not a design choice.
- **A live daemon caches its own modules.** A newly added verb does not exist
  until the daemon restarts — the running process serves the code it loaded at
  start. This has cost more debugging time than any bug in the verbs themselves.
- **Multi-client behaviour is under-tested.** One Steam account means one client;
  anything that depends on two simultaneous players is unverified.

## Availability

The bridge is published as its own repository, separate from this pack because it
is a running service with its own lifecycle rather than redistributable content:
**[https://github.com/willy92wins/dayz-mcp](https://github.com/willy92wins/dayz-mcp)** (MIT). Its README covers install, the three run
modes, the security model and how a clone generates the machine-local pieces
(launcher policy, built launcher, registry). This note remains the design record:
the surface and the invariants are what the implementation is held to, and the
engine facts above apply to any bridge of this shape.

`.mcp.example.json` in the pack root is the client wiring `install-mcp.ps1
-Register` writes for it.
