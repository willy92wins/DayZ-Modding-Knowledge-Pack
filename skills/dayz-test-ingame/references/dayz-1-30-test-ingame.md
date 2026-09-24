# DayZ 1.30 Exp — launch / session-test deltas (build 1.30.164014)

Companion to `SKILL.md` § DayZ 1.30 Exp. Diag-only managed lifecycle, absolute
`-mod` paths, and the filepatching-vs-PBO caveats still hold. This file is the
1.30 launch-flag and action-injection delta.

Line numbers are from files opened under `exp\` and the changelog
transcription. Runtime behaviour of the new exe flags is [CHANGELOG] /
[UNVERIFIED] (no DayZ 1.30 Tools binary in this extract).

## Unpacked `-mod` folder (configs without packing)

(until 1.29: this skill's loop was "re-pack the PBO, deploy it where the
engine reads mods, and launch DayZDiag".) (since 1.30 Exp [CHANGELOG],
`work\changelog-1.30-exp-modding.md:25-28`):

> Changed: Mods now have their own named filesystem
> Changed: Improved unpacked mod workflow; -mod can now point to a physical folder
> Changed: RV configs can now be read when loaded as an unpacked mod

[DESIGN] For **config.cpp / script** iteration, `-mod` may name the addon
**source folder** (still prefer absolute paths; the silent-no-mount gotcha of
bare `@Name` is unchanged). `.p3d` / `.paa` still follow the existing
filepatching-does-not-reload-binaries rule. A shipping test still packs.

## New launch flags

(since 1.30 Exp [CHANGELOG], `work\changelog-1.30-exp-modding.md:10-11`):

> Added: '-resolveFilePatchingUsingEnfusion=0/1' for file patching to
> prioritize looking through named enfusion filesystems before checking
> launched directory (requires -filepatching, always enabled in Workbench)
> Added: '-cacheP3D=0/1' command line launch option, creates .p3dcache files
> next to .p3d files to allow for quicker subsequent launches of the
> Game/Buldozer when working with unbinarized assets

[DESIGN] Append to Diag argv when iterating unpacked / MLOD assets, for
example:

`-filePatching -resolveFilePatchingUsingEnfusion=1 -cacheP3D=1`

Requires `-filePatching`. Workbench always enables the resolve flag.
`.p3dcache` siblings are local caches — do not commit them as product.

## Headless roboclients vs `Mode=all`

(since 1.30 Exp) `CGame.IsHeadless()` and `IsHeadlessOrDedicatedServer()` —
see `dayz-mod-workflow/references/dayz-1-30-mod-workflow.md`. This skill's
MCP composition still requires `-Mode all` for a **rendered** client
(`dayz-mcp-verify`: headless has no window to grab).

[DESIGN] A load-test roboclient is `IsHeadless()==true` and must not be used
as the capture peer. Script that skips VFX should use
`IsHeadlessOrDedicatedServer()` so roboclients match dedicated.

`IsHeadless` is absent from `stable-1.29\scripts\scripts\3_Game\Global\Game.c`.

## `PerformActionStart` in SP — pending guard + `UA_AM_INIT`

(until 1.29: this skill cited `actionmanagerclient.c:762`.) (since 1.30 Exp:
the method is at `:804`. Singleplayer no longer overwrites an in-flight
pending/current action.)

```
// [EXACT] exp\scripts\scripts\4_World\Classes\UserActionsComponent\ActionManagerClient.c:804-827
	void PerformActionStart(ActionBase action, ActionTarget target, ItemBase item, Param extra_data = NULL)
	{
		if (!g_Game.IsMultiplayer())
		{
			if (!m_PendingActionData && !m_CurrentActionData)
			{
				m_PendingActionData = new ActionData;
	
				if (!action.SetupAction(m_Player, target, item, m_PendingActionData, extra_data))
					m_PendingActionData = null;
			}
		}
		else
		{
			ActionStart(action, target, item, extra_data);
		}
	}
	
	override int GetActionState()
	{
		if (m_PendingActionData)
			return UA_AM_INIT;
		
		return super.GetActionState();
	}
```

1.29 contrast: `stable-1.29\scripts\scripts\4_World\Classes\UserActionsComponent\ActionManagerClient.c:762` is the old
`PerformActionStart` line.

`UA_AM_INIT = 14` was inserted; later `UA_AM_*` values shifted:

```
// [EXACT] exp\scripts\scripts\3_Game\constants.c:506-511
	const int 		UA_INITIALIZE = 12;
	const int		UA_CHECK_CON = 13;
	const int		UA_AM_INIT = 14;
	const int		UA_AM_PENDING = 15;
	const int		UA_AM_ACCEPTED = 16;
	const int		UA_AM_REJECTED = 17;
```

[DESIGN] Autotest that injects a second `PerformActionStart` in SP without
waiting for idle will silently no-op. Wait until `GetActionState()` is not
`UA_AM_INIT` / not pending. Never hardcode the integer `14` — use the
constant (Digest O §4.6).

MP path is unchanged: `PerformActionStart` still calls `ActionStart` directly
(`:816-819`).

## Navmesh / Tools (session awareness)

Custom terrains: regenerate `.nm` (no backwards compatibility —
changelog `:21`). Workbench 1.30 is not on disk in this extract; treat Tools
UI claims as [CHANGELOG].
