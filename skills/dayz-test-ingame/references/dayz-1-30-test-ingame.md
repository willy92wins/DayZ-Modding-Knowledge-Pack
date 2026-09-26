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

Measured 2026-09-26 on build 1.30.164014: the headless client (`-headlessMode=1`)
crashes before loading `World`, so there is no headless load-test roboclient in
this build yet. Server-side dummy bots do the job instead; details and numbers in
`dayz-mcp-verify/references/dayz-1-30-mcp-verify.md` § Roboclients vs server-side
dummy bots.

## Launching the 1.30 Exp DayZDiag directly (outside the managed lifecycle)

The managed launcher runs the 1.29 install. Probing the Exp install by hand
(measured 2026-09-26, evidence in `VAULT/AI/10_Projects/DayZ_MCP/lanes/2026-09-26-roboclient-130/`)
hit five traps, each costing a run:

1. **The script log is the define oracle.** Each module logs
   `Module: <name>; …; defines: "…"`. Reading that line after a launch to the main
   menu (~20 s) answers "is X defined in this exe?" without writing a probe mod.
   It also shows the version define, `DAYZ_1_30`.
2. **From the Claude desktop app the game can read a dead Steam PID.** The app sees a
   private, frozen copy of `HKCU\Software\Valve\Steam\ActiveProcess` (MSIX registry
   virtualization, LL-516). After Steam restarts, a game launched from the app reads a
   dead PID, logs `Unable to locate a running instance of Steam` and shows an error
   dialog while `steam.exe` runs. Compare the app's view with the real value (WMI
   `StdRegProv`) and the live `steam.exe`; then launch through WMI
   (`Win32_Process.Create`) or sync the copy right before launching. Writing the
   value from a shell inside the app only fixes the private copy, and only until the
   next Steam restart.
3. **A very long `-profiles=` path is a crash suspect.** A ~245-character profiles
   path ended in `0xC0000005` after 1 s with no log written; a short path did not
   repeat it. Steam was broken at the same time, so the cause is probable, not
   isolated. Keep profiles paths short.
4. **Launch DayZ with a whitelisted environment (LL-525).** A DayZ `ErrorMessage_*.mdmp` or
   crash minidump embeds the parent's whole environment block, and an agent shell
   usually carries API keys and passwords. On every crash the DayZ CrashReporter
   also sends "analytical data" before offering the dump. Start DayZ with
   `ProcessStartInfo.UseShellExecute = $false` and remove every variable not on a
   short whitelist (`SystemRoot`, `Path`, `TEMP`, `USERPROFILE`, `APPDATA`,
   `LOCALAPPDATA`, `ProgramFiles*`, processor/OS variables, `ComSpec`), and delete
   dumps you do not need.
5. **Own the PID.** Out-of-lifecycle probes start and stop only the process they
   launched, and hold the MCP lease while they run so no managed run lands on top.

## Measuring server load

What worked on 2026-09-26 (dummy-bot load, same evidence folder):

- **Cap the server.** Uncapped, the Diag server ran at ~1958 FPS and FPS was no load
  signal (10 moving dummies: 1900; 25 idle: 1908). `-limitFPS=60` (the 1.30 exe
  carries a `limitfps` switch) turns frame drops into the saturation point and makes
  process CPU per window comparable across load steps.
- **Meter frames inside the server.** Count `timeslice` in an `override void OnUpdate(float timeslice)`
  of the server mission (`5_Mission\mission\missionServer.c:108`) and log per
  window: frames, seconds, FPS, max frame time. Sample the process
  `TotalProcessorTime` every second from outside and join by timestamp.
- **Skip the first minutes after a fresh CE start.** The first three windows of a
  fresh storage ran at 36-84 % machine CPU; a final baseline after deleting all
  load returned to 0.007 cores. Warm up two minutes, and end with a baseline.
- **Separate spawn transients.** With a 15 s settle, the idle window right after
  spawning 25 or 50 dummies cost more than the moving window that followed it
  (0.201 vs 0.010 and 0.179 vs 0.032 cores). Settle longer (45 s) before
  measuring idle.
- **Write CSV numbers with the invariant culture (LL-524).** On an es-ES host,
  `'{0:F3}' -f` writes decimal commas and silently splits every CSV row into
  extra columns. Use `[string]::Format([Globalization.CultureInfo]::InvariantCulture, …)`.

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
