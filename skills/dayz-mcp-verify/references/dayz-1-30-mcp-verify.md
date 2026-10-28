# DayZ 1.30 — MCP / script-console tooling

Companion to the `since 1.30` note at the top of `SKILL.md`. The managed `dayz_test_run` /
`dayz_test_stop` lifecycle and Mode=all capture rule still hold.

## `ScriptConsoleTabRegistry` (inject a Diag console tab)

(until 1.29: adding a Script Console tab meant editing / replacing
`ScriptConsole.c`.) (since 1.30: tabs register through
`ScriptConsoleTabRegistry.Register`.)

```
// [EXACT] exp\scripts\scripts\5_Mission\GUI\ScriptConsole.c:33-43
class ScriptConsoleTabRegistry
{
	protected static ref array<ref ScriptConsoleTabRegistryEntry> s_Entries;
	
	static void Register(int id, string displayName, string widgetName, typename tabClass)
	{
		if (!s_Entries)
			s_Entries = new array<ref ScriptConsoleTabRegistryEntry>();
			
		s_Entries.Insert(new ScriptConsoleTabRegistryEntry(id, displayName, widgetName, tabClass));
	}
```

Vanilla `InitializeRegistry` (`:50-66`) registers GENERAL through WEATHER.
`ScriptConsole` ctor calls `InitializeRegistry()` then iterates `GetAll()`
(`:293-296`).

[DESIGN] A verification / debug tab for a mod: `modded` the registry
initializer or register from a mission module **after** vanilla init, with a
new `ScriptConsoleTabID` value **below** `COUNT`. Do not replace the whole
`ScriptConsole.c`. Tabs are Diag/developer UI, not MCP verbs — they do not
replace `bridge_status` / spawn / raycast.

[UNVERIFIED] Whether a mod can `Register` from `4_World` before
`InitializeRegistry` clears the array (`:52-53` Clear). Prefer registering
inside a `modded` `InitializeRegistry` after `super` (if super exists) or by
appending after vanilla Register calls via modded class. Confirm in-game
before treating the order as contract.

## Headless vs rendered MCP

(since 1.30) `IsHeadless()` / `IsHeadlessOrDedicatedServer()` exist on
`CGame` (`exp\scripts\scripts\3_Game\Global\Game.c:1130-1136`). This skill
already forbids `-Mode server` for capture (no window). Roboclients are
headless: they poll neither a client_peer suitable for `capture_screenshot`
nor a rendered HUD.

[DESIGN] Keep `-Mode all` + `@DayZ_MCP` for visual smokes. Do not treat a
headless roboclient as the MCP client_peer.

## Roboclients vs server-side dummy bots (measured 2026-09-26)

Build 1.30.164014 Exp, public DayZDiag, local server outside the managed
lifecycle. Evidence: `VAULT/AI/10_Projects/DayZ_MCP/lanes/2026-09-26-roboclient-130/`
(`evidence_extracts.txt`, `results/`). Source paths below are under
`exp\scripts\scripts\`.

[EXACT][CLAIM-DZ130-ROBOCLIENT-DEFINE-PUBLIC-DIAG] The public 1.30 Exp DayZDiag
compiles every script module with `ROBOCLIENT` and `INPUT_OVERRIDE` defined, as
client and as `-server` (script log: `Module: …; defines: "…,ROBOCLIENT,INPUT_OVERRIDE,…"`).
`-headlessMode=1` adds `NO_GUI,NO_GUI_INGAME`. The 1.29 executables carry no
`ROBOCLIENT` or `RoboclientUtils` strings.

What that switches on (source-read):
- Every `PlayerBase` builds a `Bot` in `Init()` (`4_World\Entities\ManBase\PlayerBase.c:607-613`),
  and so does a Script Console spawn through `OnSpawnedFromConsole` (`:5281-5296`,
  called from `4_World\Plugins\PluginBase\PluginDeveloper.c:350-362`).
- Without `-roboclient` the bot idles in a debug FSM whose states start on
  `EActions.PLAYER_BOT_*` (`4_World\Systems\Bot\Bot.c:344-383`, `:331-342`; enum
  `3_Game\Enums\EActions.c:92-107`): stance and movement randomizers, user-action
  spam, attach/drop cycle, item move back and forth, spawn/open/eat/destroy a can,
  hand swaps. The Diag debug-action menu lists them (`PlayerBase.c:8427-8456`) and
  `OnAction` forwards them to `m_Bot.StartAction` (`:8356-8363`).
- With `-roboclient` the FSM comes from config through
  `RoboclientUtils.ReadStateMachines` (`Bot.c:80-84`). Vanilla ships none that we
  found, so a rendered `-roboclient` connects and stands still.

[EXACT][CLAIM-DZ130-DUMMY-BOT-SERVER-MOVES] A server-side dummy moves with no client
connected. Recipe used (APIs: `3_Game\Global\Game.c:703`, `PlayerBase.c:5281`,
`Bot.c:205-215`):

```c
// [DESIGN] server mission script; m_Bot exists only under #ifdef ROBOCLIENT
PlayerBase d = PlayerBase.Cast(GetGame().CreateObjectEx("SurvivorM_Mirek", pos, ECE_PLACE_ON_SURFACE|ECE_INITAI|ECE_EQUIP_ATTACHMENTS));
d.OnSpawnedFromConsole();                                    // scheduler + Bot, as the console does
d.m_Bot.StartAction(EActions.PLAYER_BOT_RANDOMIZE_MOVEMENT); // start
d.m_Bot.StartAction(EActions.PLAYER_BOT_STOP_CURRENT);       // back to idle
```

Measured: ~33.7 m per 5 s (sprint, ~6.75 m/s) in a straight line north, ~1.7 m/s
once in water. Mean displacement: 169.2, 169.1, 168.1 and 158.9 m in 25 s for 10, 25,
50 and 100 dummies (run 2); 297.1 and 291.0 m in 45 s for 50 and 100 (run 3). The
"randomizer" is not random: it forces `OverrideMovementSpeed(ONE_FRAME, 3.0)`
and `OverrideMovementAngle(ONE_FRAME, 0.0)` every frame
(`4_World\Systems\Bot\Bot_MovementRandomizer.c:26-40`). Spawn inland; from the
coast the dummies run into the sea.

[EXACT][CLAIM-DZ130-HEADLESS-CLIENT-CRASH] The headless roboclient is unusable in
this build: `-headlessMode=1 -roboclient` crashes with
`Access violation. Illegal read … at 0x0` at the same instruction, standalone and
with `-connect` (3 of 3 on 2026-09-26), after compiling `Game` and before `World`.

Load: one server at `-limitFPS=60`, no client, Ryzen 7 7800X3D. Two runs on
2026-09-26, one sample per cell:

- Run 2 added dummies in steps of 10, 25, 50 and 100 with 15 s settles, and did not
  move them back between steps.
- Run 3 spawned 50 and then 100 on a 10-wide grid (6 m by 8 m), settled 45 s, and put
  every dummy back on the grid before each moving window.

| Moving dummies | Run 2 FPS | Run 2 server CPU (cores) | Run 2 machine CPU | Run 3 FPS | Run 3 server CPU (cores) | Run 3 machine CPU |
|---:|---:|---:|---:|---:|---:|---:|
| 0 (final baseline) | 60.0 | 0.007 | 0.6 % | 60.0 | 0.001 | 0.4 % |
| 25 | 60.0 | 0.010 | 0.4 % | not run | not run | not run |
| 50 | 60.0 | 0.032 | 2.0 % | 60.0 | 0.024 (32 of 45 s sampled) | 3.2 % |
| 100 | 54.7 | 0.384 | 34.2 % | 60.0 | 0.008 | 2.0 % |

FPS is the mean over each window (run 2: 25 s for moving windows and 30 s for the final
baseline; run 3: 45 s); machine CPU is the whole host. In run 3's setup the 100-dummy moving window averaged 60.0 FPS (33 ms
max frame) at 0.008 server cores. Run 2's averaged 54.7 FPS while the host ran at
34.2 % CPU, of which the server's 0.384 cores are about 2.4 %. The runs differ in
settles, placement, window length and host load, and none of them was isolated, so
neither run is a capacity figure. Other contamination seen that day:

- Post-spawn idle windows. In run 2 the idle window right after spawning 25 dummies
  used 0.201 server cores against 0.010 in the moving window after it, with the host
  nearly idle; the idle window after spawning 50 ran with the host at 49.2 %.
- Startup. Machine CPU was 36-84 % in the first three windows of run 2, and the run-3
  baseline after a 120 s warm-up still used 0.276 server cores against 0.001 at its
  final baseline.

Method and traps:
`dayz-test-ingame/references/dayz-1-30-test-ingame.md` § Measuring server load.

[DESIGN] For the MCP: server verbs `bot_dummy_spawn(n, pos)` plus `bot_start(action)`
and `bot_stop()` on this path would give N moving players on one machine for load
and soak tests. They need a 1.30 lane; the managed launcher runs 1.29 today. This
is not a way to offload simulation: dummies and roboclients alike run under server
authority.

## Action injection vs 1.30 SP pending

MCP `action_use` / `PerformActionStart` in singleplayer now no-ops if
pending/current is set (`ActionManagerClient.c:804-814`). Continuous actions
already do not complete via MCP (existing SKILL.md limitation). Instant
actions: if a second inject returns `setup_failed` / no-op, wait for
`GetActionState()` to leave `UA_AM_INIT`. Detail:
`dayz-test-ingame/references/dayz-1-30-test-ingame.md`.

## Vehicle tests on 1.30.164200: what the LFQuad port ran into (2026-10-26)

[EXACT][CLAIM-MCPV-VEHICLE-GAPS-130] Five behaviours of the bridge that shaped a car test,
on 1.30.164200 DayZDiag (Exp and stable installs), each with its way round:

- `vehicle_control` does not shift an automatic gearbox: the bridge changes gear only when
  `GearboxGetType()` is manual (`MCP_CarScript.c:790-810` of the deployed `@DayZ_MCP`), so an
  automatic car stays in neutral with the throttle open (pipeline ticket
  `fb-20261026-142708-3efe`). To drive one, test a copy of the build whose `Gearbox.type` is
  `GEARBOX_MANUAL` and every other entry byte-identical, and say so in the verdict.
- `vehicle_prepare_fixture` answered `fixture_not_ready` with `fuel_fraction=0.0` right after
  `OnDebugSpawn()`, in four runs on two boxes, although `OnDebugSpawn()` fills the tank:
  `telemetry_read object_at` read `fuel_fraction=1` afterwards, and the car started and drove.
  The bridge reads the tank in the tick of the `Fill()` (ticket `fb-20261026-150310-9582`).
  Confirm with `telemetry_read` before calling it a failure.
- `entities_query` returns the config class as `type` and the script class as `classname`:
  a mod wheel with no script class of its own reads `CarWheel`, its `_Ruined` twin with one
  reads its own name. That is a cheap check that a mod's script class binds.
- No tool sets an item's health (request `fb-20261026-150310-c703`), so health-level
  transitions such as the 1.30 ruined-wheel swap cannot be driven. An RGD5 dropped unpinned
  1.5 m from a loose wheel took it only to 0.971. A grenade unpinned in the hands
  (`action_use ActionUnpin`, target `hands`) arms only when it leaves them
  (`grenade_base.c:273-281`); `ActionDropItem`, target `hands`, drops it.
- With the player seated, `camera_set` failed with `camera_unmoved_cabin`, yet the next
  capture showed the requested outside view and carried the warning `camera_unverified`
  (ticket `fb-20261026-152109-2277`). The camera had moved: that is how the driver's pose
  was checked from outside. It stays mounted until `restore_gameplay`.

## Vehicle tests on 1.30.164200: what the Arma2Quad port added (2026-10-26)

[EXACT][CLAIM-MCPV-VEHICLE-GAPS-A2Q-130] Six more behaviours of the bridge, from the stable
box (DayZDiag 1.30.164200 of the stable install) with a second 1.29 quad, Arma2Quad:

- In-vehicle actions need `vehicle_get_in_client` as well as `vehicle_enter`. After
  `vehicle_enter` alone, `action_use ActionSwitchLights` (target `self`) answered
  `condition_failed`; after `vehicle_get_in_client` it started and the lights came on (ticket
  `fb-20261026-203150-6f62`). The client stays bound to that first car: after
  `ActionGetOutTransport`, `vehicle_enter` into a second car seated the server player, and the
  switch failed there twice. Plan one car per run.
- `vehicle_enter` with its default 15 s timeout answered `timeout` with the player already in
  the seat (`query_player_state`); with `timeout_s=30` it answered in 1.3 s.
- Parts that `OnDebugSpawn` mounts are not world objects: `object_resolve` on a mounted
  `HeadlightH7` gave `object_not_found` at 0.3 and 3 m. To remove a part during a test, mount it
  with `inventory_attach`, keep its `item_object_id` and `object_delete` that id; the detach
  path runs (the headlights went from the two-bulb to the one-bulb state in game).
- No bridge reader exposes the light state: `vehicle_telemetry` and `telemetry_read` have no
  light field. Log it from the mod under `#ifdef DIAG_DEVELOPER` (Arma2Quad prints it in
  `OnDriverExit`) or compare captures.
- With another box's DayZ server holding port 2302, `dayz_test_run` on the stable box answered
  `port_in_use_foreign` with a hint to pass another `port=`; with `port=2402` it answered
  `active_run_exists` and only queued until that server exited (ticket
  `fb-20261026-203149-88fe`).
- `wait_for(log_matches, role=server, lookback_from=launch)` returned the client's
  `Module: World` line and listed only `_client` files in `scanned` (ticket
  `fb-20261026-203149-33c3`). Check `scanned.files`, or the defines of the returned line
  (`SERVER`), before taking it for the server's.
