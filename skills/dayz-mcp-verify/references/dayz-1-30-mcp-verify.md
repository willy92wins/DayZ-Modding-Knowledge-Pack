# DayZ 1.30 Exp — MCP / script-console tooling (build 1.30.164014)

Companion to `SKILL.md` § DayZ 1.30 Exp. The managed `dayz_test_run` /
`dayz_test_stop` lifecycle and Mode=all capture rule still hold.

## `ScriptConsoleTabRegistry` (inject a Diag console tab)

(until 1.29: adding a Script Console tab meant editing / replacing
`ScriptConsole.c`.) (since 1.30 Exp: tabs register through
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

(since 1.30 Exp) `IsHeadless()` / `IsHeadlessOrDedicatedServer()` exist on
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
once in water; 169 m mean displacement in 25 s for 10, 25 and 50 dummies, 158.9 m
for 100. The "randomizer" is not random: it forces `OverrideMovementSpeed(ONE_FRAME, 3.0)`
and `OverrideMovementAngle(ONE_FRAME, 0.0)` every frame
(`4_World\Systems\Bot\Bot_MovementRandomizer.c:26-40`). Spawn inland; from the
coast the dummies run into the sea.

[EXACT][CLAIM-DZ130-HEADLESS-CLIENT-CRASH] The headless roboclient is unusable in
this build: `-headlessMode=1 -roboclient` crashes with
`Access violation. Illegal read … at 0x0` at the same instruction, standalone and
with `-connect` (2 of 2), after compiling `Game` and before `World`.

Load, one server at `-limitFPS=60`, no client, Ryzen 7 7800X3D, one sample per cell:

| Moving dummies | Server FPS | Server CPU (cores) |
|---:|---:|---:|
| 0 (final baseline) | 60.0 | 0.007 |
| 25 | 60.0 | 0.010 |
| 50 | 60.0 | 0.032 |
| 100 | 54.7 | 0.384 |

Read it as "up to 50 moving dummies do not show at 60 FPS; 100 do". At 25 and 50
dummies the idle window right after a spawn cost more than the moving window after
it (spawn transients), and the first minutes after a fresh CE start are
contaminated (machine CPU 36-84 %). Method and traps:
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
