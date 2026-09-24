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

## Action injection vs 1.30 SP pending

MCP `action_use` / `PerformActionStart` in singleplayer now no-ops if
pending/current is set (`ActionManagerClient.c:804-814`). Continuous actions
already do not complete via MCP (existing SKILL.md limitation). Instant
actions: if a second inject returns `setup_failed` / no-op, wait for
`GetActionState()` to leave `UA_AM_INIT`. Detail:
`dayz-test-ingame/references/dayz-1-30-test-ingame.md`.
