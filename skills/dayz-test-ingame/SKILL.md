---
name: dayz-test-ingame
description: "Use when: lanzar el juego con el mod, probar el mod in-game, filepatching, DayZDiag, arrancar server local, connect 127.0.0.1, the mod doesn't load. Not packaging-only: dayz-pbo-build; not env check: dayz-preflight."
---

# DayZ test in-game (filepatching launch)

## WHAT THIS DOES

Closes the dev loop for a DayZ mod on a single Windows box: re-pack the PBO, deploy it
where the engine reads mods, and launch `DayZDiag_x64.exe` with `-filePatching` so script
and config edits are picked up without re-binarizing. Three launch modes (offline / server /
client / all) driven by one orchestrator script and double-click `.bat` wrappers, generated
per mod into `<Mod>_dev\tools\`.
(until 1.29: the loop was pack PBO → deploy packed `@Mod` → DayZDiag `-filePatching`.) (since 1.30 Exp [CHANGELOG]: `-mod` may point at an **unpacked** source folder; RV configs load unpacked; new flags `-cacheP3D=0/1` and `-resolveFilePatchingUsingEnfusion=0/1`. Details: [dayz-1-30-test-ingame.md](references/dayz-1-30-test-ingame.md) and ## DayZ 1.30 Exp.)

## SOURCE OF TRUTH

`<dayz-projects>\DAYZ_INFRA.md` is the canonical record of
this user's DayZ paths, flags and gotchas, verified in-situ. This skill **operationalizes**
that doc — it does not re-derive the flags. If the two ever disagree, DAYZ_INFRA.md wins;
update the skill to match, never the reverse.

Cite-then-verify discipline:
- `[EXACT]` — flag/path verified against DAYZ_INFRA.md (section refs below; section names are
  stable, line numbers drift as the doc grows) and the user's RPTs.
- `[DESIGN]` — plausible but NOT in the user's infra. The single-exe **offline mode is
  `[DESIGN]`** — validate it in-game on first run before trusting it.

## WHEN TO USE / WHEN NOT

Use when the user wants to see a mod running in-game, iterate scripts/configs live, or stand
up a local server+client. Do NOT use to author the mod (that is `dayz-model-pipeline` /
`enforce-script-reference`), to validate/pack only (`dayz-pbo-build`), or to configure a
production server. The retail `DayZ_x64.exe` is for final pre-release validation only —
default to the diag exe. Retail is manual-only and external to this launcher.
On this box retail does not load mission (LL-479): B-4 accredits 3_Game+4_World and 5_Mission
only compiles in diag; coverage is written per module in the matrix, never "B-4 green".

## SHARED SESSION PROTOCOL

Read before launching:
`<runbooks>\dayz-mcp-agent-session-protocol.md`.
Official launcher is Diag-only and enforces this matrix:

| Route | Executable / role | Contract |
|---|---|---|
| Managed diag | `DayZDiag_x64.exe`, including `-server` role | `managed_lifecycle=true`; `dayz_test_run` possesses lease/heartbeat/release and returns `run_id`. |
| Dedicated server | `DayZServer_x64.exe` | `managed_lifecycle=false`; probe-gated and not started by official launcher. |
| External manual retail | Session opened by user outside launcher | No agent lifecycle; triggers quarantine. |

1. Run `bridge_status`; under retail quarantine only reads are allowed.
2. [EXACT][CLAIM-R21-TEST-PUBLIC-LIFECYCLE] Use `dayz_test_run` for
   managed server/client and `dayz_test_stop` for exact `run_id`. Those
   tools possess FIFO queue, lease, heartbeat, and release; DO NOT
   pre-acquire another lease around them.
3. `session_acquire`/`session_wait`/`session_heartbeat`/`session_release` remain
   for low-level mutations not encapsulated by public
   tools. (rev. 2026-09-06) And to ADOPT the run: upon completion, `dayz_test_run`
   releases its lease and run remains `RUNNING_IDLE` without owner; any bridge verb
   on it, reads included, is rejected with `run_not_owned` until
   `session_acquire_wait` adopts it (check `adopted_run`). Sequence and citations:
   `dayz-mcp-verify` §COMPOSITION, "Bridge startup sequence".
4. [EXACT][CLAIM-R21-TEST-CREDENTIAL-SCOPE] The approved launcher receives
   `DAYZ_MCP_CLIENT_ID_JSON` and `DAYZ_MCP_LEASE_TOKEN` only in the process
   environment. The template captures them, removes them from parent environment, and
   restores them solely around child process; never copy their values to
   shell, argv, logs, or handoff nor invoke approved launcher directly.
5. Retain returned `run_id`. Same mod does not grant ownership: stop/adopt
   require the exact run. `-Kill` without `-RunId` remains fail-closed.
6. Verify terminal state after stop. NEVER substitute lifecycle
   guard with a kill or with attribution based on name, mod, cmdline, or profile.
7. [EXACT] After adopting, keep the run owned yourself: the lease lasts 120 s and is not renewed internally, fresh client or not, so send `session_heartbeat` at least every ~90 s during the whole run, including while a human plays. Without heartbeats the run goes ownerless and the daemon stops it after the grace period (measured 2026-09-27, three runs; detail in `dayz-mcp-verify` §COMPOSICIÓN).

Manual-only retail triggers retail quarantine: user who opened it closes it via UI and
then runs doctor/rescan. Without access to that UI, declare `manual_cleanup_required`; another
agent neither kills nor adopts the process.

### Unmanaged fallback when managed is blocked (SP-084-unmanaged-fallback)

`dayz-test.ps1` and `dayz_test_run` are the managed path. If `approved-launchers.json` registry does not let the project pass and MCP daemon on documented port goes down (`session_status`=`daemon_unavailable`), that path does not launch.

With the box free of run DayZ processes and explicit user authorization, the path is UNMANAGED launch. It is not default.

- Do not launch exe from agent shell. [EXACT - this skill, cross-ref SP-085] DayZDiag launched outside registered launcher stays alive with 0 CPU and 0 RPT. Signature: alive + 0 CPU + 0 RPT => not args/mod, it is launch-from-agent.
- Do not use `Start-Process -ArgumentList` for DayZDiag. [EXACT - this skill, SP-167] In Windows PowerShell 5.1 array does not guarantee quoting of each element. [EXACT - SP-228, measured in LFPowerGrid P0.0, 6 A/B attempts 2026-08-12] `cmd /c start` with literal quotes on each value with spaces is the path that starts; `Start-Process -ArgumentList` starts and hangs at ~0.06 s CPU without writing EVEN the RPT header.
- [EXACT] When the command that `cmd /c start` launches is a `.bat`, the new window runs `cmd /K`: an `exit /b` at the end of the bat exits the script, not the interpreter, and the window stays at an idle prompt after the server closes — one leftover console window per launch (measured 2026-09-25, LFDucati T99, Windows 11 23H2: 9 idle `cmd.exe /K` wrappers after two days of server starts; 0 after the switch). Wrap the bat in a second `cmd /c`: `cmd /c start "<title>" cmd /c "<abs bat>"`. A preflight failure with `pause` inside the bat is still visible.
- Recipe: agent writes `.bat` (server/client argv, literal quotes on each value with spaces) and user double-clicks to execute them in interactive session. [EXACT - this skill, SP-077] Read script.log/RPT with `FileShare.ReadWrite`. UI closure, not by PID, except agent's own zombie (then exact `Stop-Process -Id`).
- [DESIGN] Server argv: `-server "-config=<serverDZ.cfg>" "-profiles=<server-profiles>" "-mission=<mission-abs>" "-mod=<mod-abs-semicolon-list>" -filePatching -port=2302`
- [DESIGN] Client argv: `"-mod=<mod-abs-semicolon-list>" -connect=127.0.0.1 -port=2302 "-profiles=<client-profiles>" -name=Dev -window -filePatching`
(since 1.30 Exp [CHANGELOG]) Optional on both: `-cacheP3D=1` (unbinarized `.p3d` sibling cache) and `-resolveFilePatchingUsingEnfusion=1` (requires `-filePatching`; always on in Workbench). `-mod=` may name an unpacked source folder, not only a packed `@Mod`. See `references/dayz-1-30-test-ingame.md`.

Three gotchas that bite along this same path and are not from argv (SP-228, measured):

- **Stuck Workshop.** `workshop_log.txt` with "No workshop depot defined, skipping non-legacy
  item" on each item (`NeedsDownload=1`) is unblocked with `steam://validate/221100`, which refreshes
  appinfo. Neither launcher nor download page unblocks it.
- **Default RPT.** If `-profiles` does not reach exe, DayZDiag writes RPT and script log to
  `%LOCALAPPDATA%\DayZ`. Search there before declaring nothing was written.
- **VPP superadmin.** Current versions read
  `<profiles>\VPPAdminTools\Permissions\SuperAdmins\SuperAdmins.txt` (IDs only, one per line);
  `SuperAdmins.json` is old format and ignored. With `vppDisablePassword=1` plus ID in `.txt`
  menu opens directly. Corrects hint that cited only the JSON.

## PREREQUISITES (preflight — runs automatically)

### Step 0 — offline linter, BEFORE wasting a startup

A startup cycle costs minutes; linter costs ~60 s and catches cold what you would otherwise
discover reading an RPT:

```
python <KNOWLEDGE_PACK>/tools/dayz-script-validator/scripts/script_validator.py <addon_root>
```

Gate on **`len(errors)`**, never on `status` (`WARN` with zero errors is valid).
 Path is **relative to Knowledge Pack root**, not your project: from a mod directory
you must give absolute path to YOUR checkout of the pack, or command dies with
`No such file or directory` and reads as "not installed".
 Compare against
base to know if error is yours. **Does not substitute startup** — Enforce only compiles on loading
the world, and this linter does not see that — but `errors > 0` means startup will fail and
there is no need to launch it to find out. Mandatory if change deletes classes, files, or
`config.cpp` entries.

⚠ **MEASURED blind spot, costing an entire startup: linter DOES NOT see an undeclared
variable.** An `obj.m_Campo` where type of `obj` does not declare `m_Campo` exits with **0 errors**
and zero delta, and upon world load module dies with `Cant compile "World" script module!` +
`ACCESS_VIOLATION`. Measured 2026-09-08 in LFPowerGrid: SAME tree passed this gate in **12
lanes** and again on merged `main`; an adversarial review from another family did not
catch it either, because read in a diff an incrementing counter looks reasonable. The case:
`tRnd.m_Projections` on a `LFPG_RenderMetrics`, field existing on `LFPG_PreviewMetrics`
— the adjacent class in same file. **Useful asymmetry**: SERVER started fine because
that code was on render path; a gate looking only at its log gives green to this.

Cheap sweep that catches it, before wasting startup when touching many files: for
each typed local `Type obj = ...` in diff, check that each `obj.m_Campo` is declared in
`Type` or its parents, resolving inheritance with regex census of `class X : BASE {...};`
across all `scripts/`. Measured: 145 classes and 32 files in ~2 s. Only covers locals with explicit
type — does not see member accesses, function returns, or `this` — but covers this pattern.

The orchestrator checks these every run and fixes what it safely can. Verified on this box
2026-05-30: missions present in DayZServer, AddonBuilder present, `P:\` mounted, but
`P:\Mods` junction NOT yet created and `DAYZ_*` env vars unset (fallbacks used).

- **Diag exe** — `DayZDiag_x64.exe`. Client AND server MUST be the diag binary; retail blocks
  past the loading screen with `-filePatching`. [EXACT — DAYZ_INFRA.md §Mandatory diag binary for iteration]
- **`P:\Mods` junction** -> `<DayZ>\!Workshop` so deployed PBOs land where the engine looks.
  The script creates it via `mklink /J` if missing (no admin needed). [EXACT — DAYZ_INFRA.md §Drive and mod layout]
- **`allowFilePatching = 1`** in the server's `serverDZ.cfg`, else BattlEye kicks the client
  with `0x00020005`. The script generates a dev `serverDZ.cfg` with it set. [EXACT — DAYZ_INFRA.md §serverDZ.cfg — allowFilePatching = 1; obligatorio]
- **Mission template** — absolute path; the server loads an empty mission otherwise.
  [EXACT — DAYZ_INFRA.md §Canonical invocation commands — Server diag]. Aliases:
  `chernarus`/`livonia`/`sakhal`. [EXACT — DAYZ_INFRA.md §Mission templates — canonical aliases]
- **`class Missions` in `serverDZ.cfg`** — a dedicated server with a `dayzOffline.*` mission self-terminates before the mission loads (RPT countdown `[Server] :: termination in: N`) unless the config declares `class Missions { class DayZ { template="<mission>"; }; };`. With it, the server stays up with no client, which is what a server-side probe in the mission `init.c` needs. [EXACT] (measured in game, DayZ 1.30.164014 Exp, SP-434]
- **AddonBuilder** — only when `-Build`. [EXACT — DAYZ_INFRA.md §Canonical invocation commands — AddonBuilder]
- **Steam client session** — for CLIENT-launching modes only (`offline`, `client`, `all`),
  `HKCU\Software\Valve\Steam\ActiveProcess` must have both `pid != 0` and
  `ActiveUser != 0`. The script warns without aborting; run `steam.exe -shutdown`, then relaunch
  Steam (the login is preserved). [DESIGN] Restart is NOT the reliable remedy: measured 2026-09-08/09, a restart can leave the key pointing at the old pid with the client still dead — the deterministic fix is to copy the live `steam.exe` pid into `ActiveProcess` from a shell OUTSIDE any sandboxed (MSIX) app — a write from inside one only reaches that app's private registry copy, see `references/dayz-1-30-test-ingame.md` — (guards and verification in the "El `pid` de Steam en el registro puede estar MUERTO" section below), and restart only as a fallback when there is no live Steam or `ActiveUser == 0`.

- **Mod set is SEALED, and changing it WIPES test world** (since 2026-09-06,
  measured in game). Each server startup seals its effective mod list in
  `<mission>\storage_1.modset.json` (`seal` field, sha256). If seal changes relative to previous
  startup, startup **archives `storage_1`** into `storage_1.modset-<ts>-<seal8>` (with its
  `.marker.json` and a `…rotation.<hash>.completed.json` receipt) and starts fresh: **world, bases, and
  test characters, gone**. Measured: repeating same set DOES NOT rotate and seal does not move;
  changing it rotates **exactly once**; repeating new one does not rotate; and `mode=client` on live run
  does not rotate either — rotation lives in SERVER startup.
  - **Consequence for anyone alternating stacks** (testing your mod, then next one, then yours):
    you lose test persistence on each hop. If you need to preserve it, **copy
    `storage_1` manually beforehand**; archived ones all remain as siblings in mission directory.
  - **Rotation DOES NOT leave a row in audit log** (known defect, emitter swallows its
    exceptions silently). If one day you lose the world and look for why, check via
    `storage_1.modset-*` folders and `seal` field, not audit log.
  - **It is deliberate and fixes something worse**: previously, that same stack hop corrupted savegame.
    Measured 2026-09-04 with previous bundle, an A→B hop produced **43,197** lines of
    `Scripted variables corrupted`; with seal, both signatures (`Failed to read modstorage` and
    `Scripted variables corrupted`) exit at **0**. Caution when diagnosing: in that repro the signature
    appearing was NOT the one incident entry proposed watching; watch **both**.
  - **Format trap**: `extra_mods` is a **list**, not a string with `;`. A
    `["@CF;@VPPAdminTools"]` passes validation and then does not exist as folder: silent red.
  - Via MCP route, expired Steam session from previous point manifests as
    `dayz_test_run` dying in `validating` phase at ~1.3 s with `error_code: "steam_session_stale"`;
    remedy is the same (restart Steam, login is preserved).

Path resolution is env-var-first, Steam-default fallback (`DAYZ_GAME_PATH`, `DAYZ_DIAG_PATH`,
`DAYZ_TOOLS_PATH`, `DAYZ_WORK_DRIVE`). [EXACT — DAYZ_INFRA.md §Optional environment variables (resolvers)]

## THE CYCLE

1. **Build + deploy** (`-Build`) — `AddonBuilder P:\<Mod> -> P:\Mods\@<Mod>\Addons\<Mod>.pbo`.
   Required whenever **assets** (`.p3d`, `.paa`, `.rvmat`) change — filepatching does not
   reliably hot-load binarized models/textures.
   **Scripts-only mods**: AddonBuilder's default binarize mode drops `.c` files (not in its
   include-list) → a config-only PBO where the mod mounts but no script runs. `Invoke-Build`
   now auto-adds `-packonly` when the source has no `.p3d`/`.paa` (force with `-PackOnly`), and
   warns if a mod with a `scripts\` folder packs suspiciously small. [verified 2026-06-03]
   **`.asi`/`.anm` (added 2026-06-24, A6_SR2M)**: binarize mode ALSO drops these unless the
   `-include` list has `*.asi;*.anm`. A weapon with a custom player anim graph
   (`AddItemInHandsProfileIK` 2nd arg = its own `.asi`) then builds WITHOUT the graph → the
   reference points at a missing file and the change (e.g. a fire-anim no-jump fix) is silently
   absent (the build still reports success). The generated include list must contain
   `*.asi;*.anm`. Verify the `.asi`/`.anm` shows up as a FILE ENTRY in the PBO header, not just
   as a string inside the compiled script.

   **Mixed mods (assets + scripts, SP-083, added 2026-07-22, LFPowerGrid)**: auto-`-packonly` does
   NOT apply when `.p3d`/`.paa` are present — `Invoke-Build` and `dayz-test.ps1 -Build` never pass
   `-include` (only -prefix/-temp/[-clear]/[-packonly]), so binarize still silently drops
   `.c`/`.paa`/`.ogg`/`.rvmat`/`.layout`/`.csv` — the PBO mounts with zero scripts running.
   The "packs suspiciously small" warning (<4096 B) misses it: binarized `.p3d` keep the PBO
   large (measured 95.1 MB / 170 files; with include-list 451 files / 106.8 MB). Production:
   AddonBuilder <src> <out> -prefix=<Mod> "-temp=<tmp>" "-include=<lst>" -clear with
   lst = `*.c;*.asi;*.anm;*.paa;*.rvmat;*.layout;*.ogg;*.ptc;*.csv`. Mandatory post-build gate:
   count PBO entries (PboViewer unpackFolder) or grep a known `.c` (170 vs 451 = drop).
   Complements SP-065. Cross-ref `dayz-pbo-build`.

   **Mixed mods, migration (SP-168, added 2026-08-04, GunRacks)**: the real failure mode
   is MIGRATION. Measured on GunRacks: **22 entries / 401.857 B without the include-list,
   25 entries / 411.786 B with it** — the gap is exactly the three `.c`. The project's
   documented hand command already passed `-include=...\tools\include.lst`
   (`PLAN.md:216`, `GunRacks_dev\HANDOFF.md:543`); that `include.lst` was created by
   hand. GENERATING THE SCRIPTS FOR A MOD copies only `dayz-test.ps1` plus the three
   `.bat` wrappers — it does not write `include.lst`. `Invoke-Build` still does not pass
   `-include`, so switching from the hand command to `server.bat` / `dayz-test.ps1 -Build`
   drops every script with no visible change (PBO still large; the <4096 B warning never
   fires). In-game the mod mounts but no action appears — indistinguishable from an
   unregistered ActionConstructor or a bad ActionCondition, so the wrong file gets
   debugged. Caught by listing the freshly built PBO before spending a test cycle.
   In `Invoke-Build`, pass the include-list when it exists and the build is not packonly:
       $incLst = Join-Path $PSScriptRoot 'include.lst'
       if (-not $usePackOnly -and (Test-Path $incLst)) { $abArgs += "-include=$incLst" }
   Replace the size check (`scripts\` present and PBO < 4096 B) with a CONTENT check:
   if the source has `scripts\`, list the PBO and require packed `.c` count == source
   `.c` count. `GunRacks_dev\tools\pbo_list.py` is the lister. Cross-ref
   `GunRacks_dev\tools\dayz-test.ps1` Invoke-Build (patched locally; the measurement
   is in the comment). Complements SP-083.
2. **Launch** — diag exe in the chosen mode. **Script/config** edits (`.c`, `.cpp`) are then
   picked up live by `-filePatching` without re-packing.

So: edit a model -> re-run with `-Build`. Edit a script -> just relaunch (or even keep the
client running, depending on what changed).

## RELEASE-GRADE BUILD BOUNDARY

[EXACT][CLAIM-R21-TEST-BUILD-POSTCONDITION] `exit_0_is_not_build_success`.
AddonBuilder can leave an old destination PBO in place after a later copy step
fails, so process exit and `Test-Path` alone do not prove that the requested
bytes were built or deployed. A release verdict requires evidence for a
`fresh_pbo`, the expected `header_prefix` and file entries, and a clean
`fatal_log` scan; require a valid `.bisign` too when signing is expected.

[DESIGN] The Phase 04 release workflow must stage the candidate outside the
published path, validate it, and publish only after every gate passes. On any
failure, require `previous_artifact_unchanged` and do not advance the build
manifest or cache. Its cache key must cover input bytes, build options, prefix,
DayZ build, tool versions/hashes and signing-key identity. Its preflight must
reject case/path conflicts, excluded-but-referenced files, absolute packaged
paths, stale or missing `.paa` dependencies, and unsupported ODOL inputs before
binarization.

The current generated dev launcher does not yet implement that complete
release contract. Use its PBO for iteration, but do not label the result
release-ready until the future `dayz-pbo-build` / `dayz-workshop-release`
pipeline supplies these postconditions.

## MODES

| Mode | What | Status |
|---|---|---|
| `all` (default) | server, wait for UDP bind, then client | [EXACT — DAYZ_INFRA.md §Canonical invocation commands — Server diag + Cliente diag] |
| `server` | `DayZDiag_x64.exe` managed with `-server` | `managed_lifecycle=true`; [EXACT — DAYZ_INFRA.md §Canonical invocation commands — Server diag] |
| `client` | diag `-connect=127.0.0.1` (server already up) | [EXACT — DAYZ_INFRA.md §Canonical invocation commands — Cliente diag] |
| `offline` | single diag with `-mission`, no network | **[DESIGN]** validate in-game |

## MANUAL EXTERNAL RETAIL FOR THIRD-PARTY MODSETS (historical verified 2026-06-11)

The diag exe compiled Enforce in STRICT mode; the retail chain compiled permissively.
Third-party packs were observed with syntax that retail tolerated as `FIX-ME` warnings but
diag rejected as fatal errors — verified live with the A6 weapons pack (braceless
one-liners: `override typename GetInputType() return X;` in OpticScripts/WeaponScripts,
"Missing function scope") and LBmaster_Core ("Unsafe down-casting"). This remained a
diagnostic fact, not an alternate launcher path. The agent's role is limited to reporting
the incompatibility; the user owns any decision to open retail manually outside this
orchestrator. While an external retail route is open, the agent remains in cuarentena
retail and read-only under the protocol.

Historical manual-route facts retained for diagnosis:

- **Retail server was `DayZServer_x64.exe` from the dedicated install.** In the observed
  session, the retail game exe with `-server` booted the CE and then terminated while
  loading GFX resources (`Water/*.edds`, "Termination successfully completed").
- **The dedicated binary already operated as a server.** Adding `-server` also triggered
  LBmaster's startup check (`Error: Remove Startup Parameter: -server`).
- **The historical LBmaster setup loaded server-only addons through `-serverMod=`.** Its
  `*_Server.pbo` files had been placed under `@SomeFolder\addons\*.pbo`, and their paths
  had resolved absolutely in the same way as `-mod` paths.
- The launcher's bind-wait produced a false negative ("exited before binding") while the
  server was still booting the CE. In that session, the first CE boot of the large pack
  took minutes and the later UDP 2302 observation showed that startup had continued.

**BattlEye on the retail pair — kick 240 "Game restart required"** (session 2026-06-11):

- The retail server loaded its BE module (`profiles\BattlEye\BEServer_x64.dll`,
  auto-downloaded on its first BE boot) and kicked clients that had not initialized BE,
  including the bare `DayZ_x64.exe` client from that session. `BattlEye = 0;` in
  serverDZ.cfg masked the behavior for several sessions, then stopped doing so after a
  system-wide BE service hot-update under `%ProgramFiles(x86)%\Common Files\BattlEye`.
  The recorded file times identified that update, after which kick 240 returned 20-60 s
  after each connection regardless of the cfg flag.
- When `BEServer_x64.dll` was removed or renamed in the 1.29 dedicated installation, the
  server bound UDP, printed `BattlEye initialization failed`, and shut down cleanly about
  a minute later ("Termination successfully completed" in the RPT). The sequence looked
  like a healthy boot followed by a silent death.
- In the historical external-manual setup, with server BE intact, `DayZ_BE.exe`
  initialized the client handshake and avoided the kick. The in-game session on
  2026-06-11 reached spawn, equip and inventory with zero kicks. This launcher did not
  invoke that route; the user owned its UI lifecycle and the agent remained in
  quarantine/read-only.

Historical load-order failures that cost a session:

- Removing `@CF` from BaseMods while `@VPPAdminTools` remained caused VPP's embedded CF
  sources to fail with `Unknown type 'RPCManager'`.
- LBmaster operated only when the observed setup included client PBOs (`LBmaster_Core`
  plus the matching client of every `*_Server.pbo`, such as `LBmaster_Groups` for
  `AdvancedGroups_Server`), the server-side PBOs and a per-IP license whitelist. Its
  error log contained the corresponding whitelist URL. In the historical local weapon
  sessions, VPP served as the admin/spawner and LBmaster appeared only in parity runs.
- The historical `@A6_TestPack` subset had been staged with filesystem hardlinks from
  `@LFTEST`; it represented 13 weapon PBOs without duplicate file copies.

## USAGE

Orchestrator (from `<Mod>_dev\tools\`):

```powershell
# build, deploy, run server+client on Chernarus
.\dayz-test.ps1 -Mod HiddenBase -Mode all -Build

# script-only change: relaunch client, no re-pack
.\dayz-test.ps1 -Mod HiddenBase -Mode client

# offline eyeball of a model [DESIGN]
.\dayz-test.ps1 -Mod HiddenBase -Mode offline -Build

# another map + an extra dependency on top of the defaults (CF/Dabs/VPP)
.\dayz-test.ps1 -Mod LFPowerGrid -Mode all -Build -Mission livonia -ExtraMods "@RaG_Liquid_Framework"

# preflight only / stop one exact managed run
.\dayz-test.ps1 -Mod HiddenBase -Preflight
.\dayz-test.ps1 -Mod HiddenBase -Kill -RunId <run_id>
```

Key params: `-Mod` (required), `-Mode`, `-Mission`, `-Build`/`-Clean`, `-ExtraMods`,
`-BaseMods`/`-NoBaseMods` (see below), `-Source` (default `P:\<Mod>`), `-RunId`,
`-NoFilePatching`, `-Port`, `-PlayerName`, `-ServerWait`. Double-click wrappers:
`server.bat` (all+build), `client.bat`, `offline.bat`.

## DEFAULT MODS & ADMIN TOOLS

Every launch prepends three base mods (load order, CF leftmost — folder names verified in this
user's `!Workshop`): `@CF;@Dabs Framework;@VPPAdminTools`. The mod under test and `-ExtraMods`
load after them. Override with `-BaseMods "..."`, or drop them entirely with `-NoBaseMods`.

`@VPPAdminTools` gives in-game admin tools (teleport, spawn, godmode, object editing) for
testing. Admin access is by **SteamID64**, not a server password — but the on-disk layout
differs across VPP versions, and the installed one uses the `Permissions\` folder, NOT the root
`SuperAdmins.json`. Because this script isolates `-profiles`, the preflight seeds **both** so
admin works regardless of version (idempotent; an already-hashed password is never clobbered):

- `<server profiles>\VPPAdminTools\Permissions\SuperAdmins\SuperAdmins.txt` — one SteamID64 per
  line; the file the installed VPP actually reads. (verified in-situ 2026-06-09)
- `<server profiles>\VPPAdminTools\Permissions\credentials.txt` — the **in-game login
  password** on line 1. VPP hashes it on first boot and the raw is then lost.
  [EXACT][CLAIM-R21-TEST-VPP-SECRET] There is no packaged default. It is seeded
  only when the operator explicitly supplies non-empty `-AdminPass`, and its
  value is never printed.
- `<server profiles>\VPPAdminTools\SuperAdmins.json` — `{ "SUPER_ADMINS": ["<SteamID64>"] }`,
  the legacy layout; still seeded for older VPP builds that read it.

SteamID source: `-AdminSteamId`, else reused from the retail config at
`%LOCALAPPDATA%\DayZ\VPPAdminTools\SuperAdmins.json`. In-game: open the VPP menu (key set under
Options → Controls; VPP's common default is Insert), then log in with the password. To change
admin or password later, edit the files above and restart the server.

**No-password dev default (verified vs VPP source 2026-06-09):** the generated `serverDZ.cfg`
sets `vppDisablePassword = 1;`, so VPP skips the login password entirely — a superadmin (SteamID
in `SuperAdmins.txt`) gets access with NO password (`missionServer.c:14` →
`DisablePasswordProtection(true)`; granted because `HasUserGroup`→`IsSuperAdmin`,
`PermissionManager.c:693`). This is the robust local-dev default: the `credentials.txt` password
path repeatedly failed across sessions (SHA256/version quirks), and disabling it removes that
whole failure class. An explicitly seeded `credentials.txt` password only matters if you remove
`vppDisablePassword` for password-gated testing. In-game keys: End = toggle admin, Home = open
menu (rebind under Options → Controls if a fresh client profile lost them).

Earlier this doc claimed VPP reads the root `SuperAdmins.json` — that was wrong for the installed
build (it reads `Permissions\`), which is why admin silently failed until 2026-06-09.

The dev `serverDZ.cfg` sets `verifySignatures = 0`, so VPP's signed PBO loads without registering
its `.bikey`.

## GENERATING THE SCRIPTS FOR A MOD

1. Create `<Mod>_dev\tools\` if absent (per the dev-split layout in workflow.md).
2. Copy `templates\dayz-test.ps1` there verbatim — it is fully generic (driven by `-Mod`).
3. Copy the three `.bat` wrappers and replace the `__MODNAME__` placeholder with the real mod
   name (the CfgPatches identifier — no dashes; `Mi_Mod`, not `Mi-Mod`). [EXACT — DAYZ_INFRA.md §Drive and mod layout — Naming de mods]
4. Confirm the mod **source** is reachable at `P:\<Mod>` (a junction to the editable folder)
   or pass `-Source`. Confirm `requiredAddons` in `config.cpp` map to the `-ExtraMods` you
   pass (CF, Expansion, etc.) — the client and server mod lists MUST match.

The `.ps1` is self-contained (no dependency on this skill at runtime) so it stays valid in the
mod repo even if the skill changes. `_server\` and `_client\` workspaces (serverDZ.cfg, RPT,
script.log) are created next to `tools\` under `<Mod>_dev\`.

## FILEPATCHING SCOPE — read before promising hot-reload

`-filePatching` hot-loads **scripts and configs** from raw source in the general case, not
binarized assets. Model/texture/material changes need a `-Build`. Do not tell the user "just
edit and it reloads" for a `.p3d` or `.paa` change — that is the most common false expectation
here. **On this install even scripts do NOT hot-load — the PBO wins** (measured 2026-07-20);
see the SP-078 section at the end of this file and use the `srcprobe` discriminator before
attributing anything to filepatching.

## MOD PATHS MUST BE ABSOLUTE — silent no-mount otherwise (verified 2026-06-01)

A bare `-mod=@Name` is resolved by the engine **relative to its working directory** (the game
dir), i.e. `<DayZ>\@Name`. Deployed mods live under `<DayZ>\!Workshop\@Name`, so that relative
path does not exist and the engine **silently fails to mount the addon** — its `CfgPatches` /
`CfgVehicles` classes never register, and `CreateObjectEx` later returns **null with no RPT
error**. This is a brutal failure mode: the server boots, the mission runs, nothing logs wrong,
but your mod's classes simply aren't there.

Verified via an in-mission `ConfigIsExisting("CfgPatches LFQuad")` probe on a headless `-server`:
- `-mod=@LFQuad` (relative, cwd=game) → `CfgPatches.LFQuad = 0` (absent).
- `-mod=C:\...\DayZ\!Workshop\@LFQuad` (absolute) → `CfgPatches.LFQuad = 1`, `LFQuad_base = 1`.

`Get-ModString` now rewrites every bare `@Name` to its absolute `!Workshop` path via
`Resolve-ModToken` (handles names with spaces like `@Dabs Framework`; passes through tokens that
are already rooted or not found under `!Workshop`). This applies to server, client and offline.

Caveats (honest scope — not yet verified):
- The probe only confirmed the **mod-under-test** mount. Whether base mods mount under relative
  names in the `all` mode (client present) was NOT isolated — the fix makes it moot by resolving
  all of them to absolute.
- Checking a dependency's mount needs its **real CfgPatches name**, not the folder name:
  `@CF` → `JM_CF_Scripts` (verified by extracting `@CF\addons\scripts.pbo`). A probe using `"CF"`
  yields a false negative.

### Headless autotest pattern (no client, scripted spawn)

For automated physics/spawn testing without a human client, a dedicated harness lives at
`LFQuad_dev\tools\dayz-autotest.ps1` (reuses this launcher's build+deploy). Five gotchas that
cost many iterations, recorded so the next headless harness works first try:
1. **Historical detached pattern — superseded 2026-07-15.** A direct `Start-Process` avoided
   waiting on the DayZDiag grandchild but left it outside the registered lifecycle. Launch now
   exclusively through the managed Diag launcher after acquiring the lease; retain its `run_id`
   and poll the RPT read-only. Do not recreate the old direct invocation.
2. **A test mission `init.c` should skip `CreateHive()`** (CE economy) for a physics test — it
   loads ~20k loot items and delays the mission loop by minutes.
3. **A `CarScript` vehicle only ticks `OnUpdate` / simulates with a player present.** A headless
   server with zero clients won't drive the vehicle's own script; spawn after a client connects
   (the harness has a `-WithClient` mode that connects a second diag instance to 127.0.0.1).
4. **Cell infrastructure (spawn-on-connect, engine watcher, auto-test hooks) belongs INSIDE the
   mod under `#ifdef DIAG` + a CLI param — never only in the mission `init.c`** (added 2026-08-17,
   LFHeli). The mission lives under Steam (`DayZServer\mpmissions\<mission>\init.c`), which no
   portable pack, backup or repo carries: the LFHeli cell infra written into `init.c` on
   2026-08-12 (`CreateObjectEx` on `InvokeOnConnect` + `EngineStart()` pre-crew watcher) was
   gone on the other machine five days later and had to be recovered from a transcript. In-tree
   it travels with the PBO, is versioned, and stays inert in retail by absence of the flag
   (pattern: `LFHeliCore\scripts\5_Mission\LFHeliFLIRMission.c` `modded class MissionServer`,
   `-lfheliAutoGetIn=1` in `LFHeliPlayerBase.c`). Corollary measured the same day: start the
   engine BEFORE the crew sits — a sleeping PARKED body rejects the injected get-in action.
5. **PowerShell orchestrator traps that hang a cell silently** (measured 2026-08-17, LFHeli
   `run_celda_scripted.ps1`): (a) never name a function parameter `$Args` — it is the automatic
   variable, `@Args` splats EMPTY and `& python` with no argv opens the interactive REPL that
   never returns (the cell sat at "flip DebugLog" for minutes with a `python.exe` child and no
   arguments); (b) `& native 2>&1` under `$ErrorActionPreference='Stop'` turns any stderr line into
   a terminating error (PS 5.1) — wrap native calls in a helper that switches to `Continue` and
   returns text + `$LASTEXITCODE`; (c) the DayZ CLIENT needs a usable Steam
   (`HKCU\Software\Valve\Steam\ActiveProcess` pid AND ActiveUser ≠ 0): a Steam restarted minutes
   earlier sits at pid populated / ActiveUser=0 and the client dies at bootstrap with a ~1 KB RPT
   and an `ErrorMessage_*.mdmp` while the SERVER (no Steam) boots fine — `steam.exe -shutdown` +
   relaunch repopulated the key in ~20 s. Check the key in the pre-flight of every cell.

### Mission `init.c`: do not extend previous module types from fixture (SP-140)

[IN-GAME CONFIRMED, DayZ 1.29 server diag, 2026-07-30] On this compiler a
generated mission adding `modded class` on `4_World` types failed with
`Unknown type` for both a concrete class (`SmallStone`) and a base
(`BuildingBase`). An earlier incident reproduced the same with
`LFPG_NetworkManager`. Offline text tests did not detect the boundary.

Rule for mission oracles: use an already compiled receiver exposing contract
under test. If you need to add a method, bridge must live in the
same module/PBO as the type and requires its own candidate/amendment; do not
inject it as `modded class` from `init.c`. Keep fixture calls and boolean
expressions in single-line vanilla forms: `&&` operator at the
start of next line produced `Incompatible parameter` + `Syntax
error`. Before expending pairs, run a single control requiring Module
Game/World/Mission, OnInit, and oracle marker.

Evidence: `P:\LFPowerGrid_dev\_validation\server-footprint-a9p1-20260730\v1-oracle\a7-attempt3-f02-unknown-type\script-final.log`,
`...\a7-attempt4-f03-cross-module-modded\script-final.log` and
`...\a7-attempt5-f04-boolean-linebreak\script-final.log`. Existing receiver
closed control in `...\a7-control\script-final.log`.

## WHEEL SIMULATION DIAGNOSIS (vehicle won't drive / bounces / sinks)

When a modded `CarScript` vehicle spawns but won't drive - wheels mount yet don't
spin, chassis bounces or sinks, engine revs with no speed - the failure is almost
always one of two MEASURABLE things, not mass/inertia. Instrument and read them
side-by-side against a known-good reference vehicle (e.g. the vanilla sedan or the
Croco quadbike) IN THE SAME RUN before touching geometry.

### 1. Is the wheel seated in PhysX, and does it touch ground?

- `WheelCountPresent()` - how many wheels the simulation actually seated (the gate).
  `0` while `WheelCount()` returns N means the slot/FireGeometry wiring is wrong; see
  the `enforce-script-reference` wheel-attachment rule and audit check SP-017.
- `WheelHasContact(i)` per wheel - `1` = touching ground, `0` = airborne. Print the
  four as a bitstring (`wc=1111` good; `wc=0000` = the whole vehicle is suspended off
  the ground, a placement/clearance problem, not a sim problem). Vanilla refs:
  `car.c:297,349,352`.

So: `WheelCountPresent()=0` is the silent wheel-binding blocker (FireGeometry slot
selection); `WheelCountPresent()=4` with `wc=0000` is geometry sitting too high or
buried, which step 2 isolates.

### 2. Did placement bury or launch the vehicle? (controlled-height probe)

Spawn with an explicit height flag instead of letting CE drop it:
- `ECE_KEEPHEIGHT` (`=524288`, "no surface trace") - places at the exact Y you pass,
  no terrain snap. Spawn a known clear height and watch whether it settles.
- `ECE_PLACE_ON_SURFACE` (`=1060`) - normal surface-trace placement.
Vanilla refs: `centraleconomy.c:37,27`. If the vehicle is stable under KEEPHEIGHT but
bounces/sinks under PLACE_ON_SURFACE, the bug is placement burying the hull (wheel-well
clearance vs tire radius - audit check SP-023), not the model.

### 3. Gotcha: parser/instrumentation drift before declaring the test failed

When the harness reports "ERROR / no data", first confirm the parser regex still
matches the CURRENT log-line format of the instrumentation. A log-format change
(renamed tag, reordered fields) reads as a test failure when the test actually ran
fine. Check the regex against a raw sample line before concluding the build is broken.

(origin: SP-023; LFQuad wheel-well/placement 2026-06-01; handoff 30_Sessions/2026-06-01-LFQuad-wheelwell-bake-placement.md)

## TROUBLESHOOTING

| Symptom | Cause | Fix |
|---|---|---|
| Client kicked `0x00020005` | filePatching mismatch | `allowFilePatching = 1;` in serverDZ.cfg [DAYZ_INFRA.md §serverDZ.cfg — allowFilePatching = 1; obligatorio + §BattlEye — most common kick codes] |
| VPP asks for a password despite a `SuperAdmins.txt` superadmin | `serverDZ.cfg` predates the `vppDisablePassword = 1;` default (generated before 2026-06-09); the existing-cfg path only re-checked `allowFilePatching` | launch now self-heals (appends `vppDisablePassword = 1;` if absent) + restart; or add it manually [session 2026-06-15] |
| Kicked `0x00010002` | mismatched signatures | rebuild PBO; or `verifySignatures=0` (dev cfg already does) [DAYZ_INFRA.md §BattlEye — most common kick codes] |
| "PlayerConnect will stay disabled" | mission empty / `-mission` not absolute | pass an absolute mission path [DAYZ_INFRA.md §Canonical invocation commands — Server diag] |
| Stuck past loading screen | retail exe + filePatching | use `DayZDiag_x64.exe` [DAYZ_INFRA.md §Mandatory diag binary for iteration] |
| Server/client does not exit | managed run still active | stop only the exact `run_id` with `-Kill -RunId <run_id>`; if ID is missing, declare `manual_cleanup_required` and do not look for another process to kill |
| Mod not visible in-game | PBO landed outside `!Workshop` | ensure `P:\Mods` is a junction [DAYZ_INFRA.md §Drive and mod layout] |
| Server boots then dies before UDP bind; RPT/log shows `!!! Serious stream damage detected during load` | half-written CE storage after an unclean server kill — masquerades as a mod bug | wipe (or rename) `<mission>\storage_1` before the next test; the server regenerates a fresh one. SOP: after ANY unclean server kill, wipe it preemptively |
| Mod class missing / `CreateObjectEx` returns null, no RPT error | relative `-mod=@Name` didn't mount | use absolute `!Workshop` paths — `Get-ModString` now does this (see "MOD PATHS MUST BE ABSOLUTE") |
| Mod mounts (CfgPatches in `defines:`) but no script/hook runs | AddonBuilder binarize dropped the `.c` → config-only PBO | build scripts mods with `-packonly` (Invoke-Build auto-detects when no `.p3d`/`.paa`); grep the deployed PBO for a known classname to confirm. [verified 2026-06-03] |
| Script edit doesn't take effect — the same compile error persists across rebuilds even though the source is fixed on disk | AddonBuilder's incremental sync to `P:\temp\<Mod>` served stale source (a changed `.c` not re-copied); filePatching also did not override the PBO's scripts with the loose work-drive copies | Invoke-Build now wipes `P:\temp\<Mod>` before every build; building AddonBuilder by hand, pass `-clear` or delete the temp first. Canonical tell: a compile error citing a line you already fixed and verified. [verified 2026-06-18] |
| `-Build` ran but the deployed car is UNCHANGED in-game (old config/.p3d) | the deployed PBO was **LOCKED** by the running server, so AddonBuilder failed to COPY it — a SILENT `[ERROR] Build failed` at the *copy* step while the script CONTINUES and the gates run on the OLD pbo | stop exact managed run before rebuilding, verify state `EXITED`, then build and relaunch; without `run_id`, declare manual cleanup instead of inferring ownership. SUB_BRZ s28 |
| Kicked `240 ("Game restart required")` 20-60 s after connect | server BE active + client launched bare (`DayZ_x64.exe` never inits BE); `BattlEye = 0;` stops masking it after a BE service hot-update (check mtimes in `Common Files\BattlEye`) | historical diagnosis: `DayZ_BE.exe` correctly initialized BE in session 2026-06-11; user decides whether to open retail externally and agent remains in quarantine, without launching it |
| Retail server binds, then dies ~1 min later; `BattlEye initialization failed`, RPT ends "Termination successfully completed" | `BEServer_x64.dll` missing/renamed | Historical observation: the 1.29 dedicated server shut down when BE initialization lacked that DLL. The external owner/user decides and performs any restoration outside the agent workflow; the agent remains in quarantine/read-only [session 2026-06-11] |
| Modal "Compile error … Missing function scope" citing a third-party file at boot | diag exe strict-compiles third-party packs | report incompatibility; if user opens retail externally, apply quarantine and do not pursue third-party "bug" |

Logs (where to look): `script.log` = script compile/runtime errors; `*.RPT` = engine errors
(missing assets, malformed configs); `crash_*.log` = handled exceptions, not hard segfaults.
[EXACT — DAYZ_INFRA.md §When the RPT cites that a script fails]. All under the `_server\profiles\` and `_client\profiles\`
folders. For a structured script-failure diagnosis, hand off to `dayz-mod-workflow`.

## OUT OF SCOPE

Authoring the mod, production server config, Central Economy / persistence tuning beyond the
minimal dev `serverDZ.cfg`, signing for Workshop release. PBO validation/packaging internals
are planned for `dayz-pbo-build` / `dayz-workshop-release` in r21 Phase 04 — this skill calls
AddonBuilder and records their required handoff contract; it does not re-implement the checks.

## REFERENCES

- `DayZ Projects\DAYZ_INFRA.md` — canonical paths/flags/gotchas (the source this skill serves).
- `dayz-pbo-build` — pre-build validation + packaging.
- `dayz-mod-workflow` — debug protocol when a launch surfaces script/engine errors.
- `templates\dayz-test.ps1`, `server.bat`, `client.bat`, `offline.bat` — the generated tooling.

## Session findings (dated appendices -> references/session-findings.md)

Per-session in-game gotchas moved to `references/session-findings.md`; load it when a launch hits one of these. One line each:

- **LFSlidingFloor (2026-06-11)** — `Print()`->script.log not RPT; `-filePatching` can compile WITHOUT the mod's scripts silently; VPP needs `@CF` first; 1 Steam acct = 1 client (kick 179); deployed PBO locked while server runs.
- **A6_SR2M grip (2026-06-17)** — visual capture on retail (brightness band, specular glint, exposure drift, multi-config desync, RPT error filter) + `Start-Process EPERM uv_spawn` in a backtick `foreach`.
- **MercedesAMGLF Fase 0 (2026-06-22)** — cheap mount-probe gate (CfgPatches existence) before physics autotest; retargeting the LFQuad physics harness (server-only no-spawn, phantom debug token, control-vehicle verdict, case-insensitive `-replace`).
- **Retargeting the harness to a new mod (2026-06-23)** — `dayz-test.ps1` is car-parametric (copy verbatim); only per-mod helpers need a case-sensitive token swap; retarget host-direct.
- **The box is a coordinated resource (2026-06-24, superseded 2026-07-15)** — one DayZ instance per box (UDP 2302); FIFO lease serializes mutations and `run_id` exacto identifica lifecycle; nombres de mod/perfil no conceden ownership.
- **`@<Mod>_deps` separate dep addon (2026-06-26)** — put deps in `-BaseMods` (loads first) or the client fails `Unknown type` at compile; replicate the last successful `-mod=` from the RPT.
- **Third-party "sloppy" scripts (2026-06-28)** — deps that only warn on retail but fatal-compile on diag require a user-owned external manual parity run; agent stays in quarantine.
- **Launching DayZDiag from the agent (2026-06-28, superseded 2026-07-15)** — background tool-jobs can lose their child; use the Diag-only managed launcher and its exact run instead of an unmanaged process.

## Backups (.bak_*) in scripts/ inflate the PBO and break grep-verify (SP-065, added 2026-07-14)

`Invoke-Build -packonly` copies the mod tree AS-IS, so any `<file>.c.bak_*` left next to the `.c` (the OneDrive rule: back up before editing) gets packed into the PBO. It does not break the game (Enforce compiles only `*.c`, ignores `.bak_*`), but it (a) inflates the PBO and (b) breaks PBO verification by grep-of-the-blob - an old anchor reads as PRESENT because it lives in a `.bak`, not the active `.c`. Measured (LFHeli 2026-07-14): 827,593 bytes with 29 `.bak` inside vs 115,609 bytes after moving them out (7x bloat + stale code shipped).

Rule: in `Invoke-Build`, before packing, move/exclude `*.bak*` from `$src` (or warn if `Get-ChildItem $src -Recurse -Include *.bak*` is non-empty). When verifying a PBO by text, COUNT occurrences (`Cnt`) instead of `Contains` - a `.bak` copy makes `Contains` lie. Cross-project convention: never leave `.bak_` in the mod's `scripts/`; put them in `<Mod>_dev\_backups\`. Cross-ref `dayz-pbo-build` (packaging). Origin: LFHeli feel-pass 2026-07-14 (cycle-16).

## Clean storage before any measurement boot - persisted entities re-fire EEInit (SP-062, added 2026-07-14)

Vehicles (and other persistent entities) saved in the mission's `storage_1` RE-RUN their `EEInit` on the next boot. Any logic ARMED there - a test `CallLater`, a JSON-driven spike/tuning mode, a countdown - re-fires on every persisted instance at once. Real case (LFHeli 2026-07-11): two helis from the day before re-armed their W0 spike at boot and flew off on their own after 60 s (two phantom CSV pairs contaminating the corpus, violating one-run-active-at-a-time; the user even saw them fly with no explanation).

Rule: before a boot meant for MEASUREMENT (cells, spikes, telemetry), the mission storage must be clean ALWAYS - rename `storage_1` -> `storage_1.bak_<date>_<reason>` (reversible), not only after a dirty kill. The current SOP only covers the dirty kill / stream-damage case (see `## TROUBLESHOOTING`). The rename also purges test entities accumulated from earlier sessions. Cross-ref `dayz-mcp-verify` (one-run-active protocol). Origin: LFHeli feel cells 2026-07-11 (storage renamed storage_1.bak_20260711_feelcells).

## DEVELOPER vs DIAG_DEVELOPER - the standard diag only defines DIAG_DEVELOPER (SP-033, added 2026-07-14)

The standard `DayZDiag_x64` defines `DIAG_DEVELOPER` but NOT `DEVELOPER` (bare). Verified in `script_*.log` of both peers: server/client defines include `DIAG,DIAG_DEVELOPER,...,FEATURE_NETWORK_RECONCILIATION` - no `DEVELOPER`. So every vanilla `#ifdef DEVELOPER` block (e.g. the debug get-in: `DayZPlayerSyncJunctures.SendGetInVehicle`, `SJ_DEBUG_GET_IN_VEHICLE`, `PlayerBase.TryGetInVehicleDebug`, much of `plugindeveloper.c`) does NOT exist in this build. `OnDebugSpawn` working (it is `#ifdef DIAG_DEVELOPER`) does NOT prove `DEVELOPER` is active - different macros.

Expensive trap: if a mod PBO EMITS a `#ifdef DEVELOPER` symbol (a call to `SendGetInVehicle`, etc.), the symbol does not exist -> HARD compile failure of the WHOLE PBO -> every tool/script of the mod drops. Not a silent no-op (unlike `ExecuteEnforceScript`, Developer-only, which returns false at runtime).

Rule before basing a design on a vanilla `#ifdef DEVELOPER` API: (1) grep the `#ifdef` guarding it (`DEVELOPER` or `DIAG_DEVELOPER`?); (2) if `DEVELOPER`, read the `defines:` line of a recent `script_*.log` for that build to confirm it is active; (3) if not, do NOT emit the symbol - wrapping it in `#ifdef DEVELOPER` is not "robustness" if the design DEPENDS on it; find a non-DEVELOPER path. Cross-ref `dayz-mod-workflow` (anti-confabulation). Origin: DayZ_MCP Fase 5 Tramo A (2026-06-28), compile logs of both profiles.

## Secure-launcher allow-list: the base_mods format is decided by junctions, not style (SP-089, added 2026-07-25)

On this box DayZDiag only launches through the registered native launcher (SP-085), so a mod that is not in the sealed allow-list of `dayz-test-v1` cannot be launched under a project entry of its own. It can still be TESTED without touching the launcher, by riding an approved project - see "Testing a mod that is not in the allow-list" below; reach for the rebuild only when the mod needs its own sealed entry. Adding the Nth mod is mechanical - copy a live project block in `DayZ_MCP_dev\tools\build_native_launcher.py` (`_build_request_policy()` AND `_build_worker_runtime()`, same order) - but the `default_base_mods` FORMAT is a correctness trap, not a style choice.

`request_path_authority._open_descendant` rejects any path component that is a reparse point (`item.reparse_tag != 0 -> _invalid()`). Therefore:

- A dep whose folder under `P:\Mods` is a JUNCTION (`@CF`, `@Dabs Framework`, `@VPPAdminTools` -> Steam workshop) MUST be listed as its ABSOLUTE workshop path, and that path must also be sealed in `mod_roots`.
- A dep that is a REAL directory under `P:\Mods` (a locally built mod, e.g. `@LFHeliCore`) can be a bare relative name: `dayz_test_worker._mod_path` joins it to `mods_root` and it accredits under the sealed `P:\Mods` root (exactly 1 match required).

Why it costs a session: the wrong format passes EVERY unit test (they only pin strings) and fails at accreditation time, when the server is launched. Check `Get-Item <path> | Select-Object LinkType` for each dep BEFORE choosing the format.

Two more gates in the same flow, both of which have already burned a session:

- `tests\test_secure_launcher.py` HARDCODES the launcher PE sha256. Every rebuild changes it (adding a mod changes the PE), so update it after `build_native_launcher.py --offline --verify-reproducible` or the suite stays red for a reason unrelated to the change.
- `launcher_registry_update install-dayz-test-v1 --expected-sha256 <X>` is a compare-and-swap on the BYTES of `approved-launchers.json` (NOT the PE hash), and it REFUSES to install while a `dayz-test-v1` entry exists -> run `rollback-last` first; it prints the restored registry sha, which is the CAS token the install needs.

Origin: LFHeli OH-1 (2026-07-25), authorizing the 6th mod, after the 2026-07-22 session was lost to this same flow.

### Testing a mod that is not in the allow-list, without rebuilding the launcher

Authorizing a project is the expensive path: edit `build_native_launcher.py`, rebuild
the PE, update the hardcoded sha256 in the test, roll back and re-install the registry
entry. Sessions have gone into it. It is only needed when the mod must have its OWN
sealed project entry.

To just run the mod in-game, mount it as an `extra_mods` entry on a project that is
already approved. `_mods` appends every `extra_mods` value to the launch list
(`dayz_test_worker.py:204-210`), and `_mod_path` joins a NON-absolute value to the
sealed `mods_root` (`:199-201`), so a bare `@Name` accredits under `P:\Mods`.

The name must be a plain relative one. `_valid_mod_entry`
(`dayz_test_request.py:137-148`) rejects anything containing `:`, `\` or `/`, rejects
`.` and `..`, and requires `ntpath.normpath(value) == value`. An absolute path is
accepted instead, but then it must fall inside a sealed root.

Two constraints that decide whether the run works:

- **The deployed directory must be REAL, not a reparse point.** Same rule as the
  `default_base_mods` format above: `_open_descendant` rejects any component whose
  `reparse_tag != 0`. A junction has to be listed by its absolute workshop path and
  sealed in `mod_roots`.
- **Pick a carrier project that compiles.** Script compilation aborts on the first mod
  that fails, so a broken carrier's error only surfaces once yours already compiles -
  which reads as "my mod broke it". `LFPowerGrid` is verified as a carrier
  (`Module: Mission; loaded 231x files`). `@DayZ_MCP` is not usable as one: its
  `5_Mission` fails with `CParser: quoted string not closed` attributed to
  `mcpclientbridge.c`.

Origin: SP-128 (2026-07-28), measured against the launcher source; supersedes the
"cannot be tested at all" reading of SP-089.
 Cross-ref SP-085 (diag hangs, 0 CPU / 0 RPT, when launched outside the registered launcher).

## `-ExecutionPolicy Bypass` — intermittent Codex quirk, NOT a host block (corrected 2026-07-22)

`[corrected by user 2026-07-22]` The previous version of this section (2026-07-21, written by
Codex) claimed that host PowerShell policy was `Restricted` and that Microsoft Defender
interrupted wrappers with `-ExecutionPolicy Bypass`, and from there derived a "BLOCKED-
SECURITY / only managed Python lifecycle" regime. **It was a MISUNDERSTANDING by Codex of what the
user said.** The reality:

- **Codex (ChatGPT CLI) SOMETIMES triggers ITS OWN security policy when the command contains
  `-ExecutionPolicy Bypass`.** It is an intermittent rejection by the Codex AGENT, not a host failure: the
  host PowerShell policy is NOT set to `Restricted` because of this, and Defender does NOT interrupt
  launches.
- Therefore `.ps1`/`.bat` launchers of this skill **are NOT host-blocked**: Claude and the
  user run them normally. **There is no "BLOCKED-SECURITY"** for this reason, nor requirement to
  go through a "managed Python lifecycle" to be able to launch.
- **Only implication, and ONLY when delegating a launch to Codex**: `-ExecutionPolicy Bypass` may be
  intermittently rejected by Codex → avoid that flag in the command you pass to Codex, or
  let Claude or the user handle the launch.
- **Independent and active**: the shared session protocol (FIFO lease + `run_id`,
  §SHARED SESSION PROTOCOL) still applies to coordinate launch/stop; it has no relation to
  this.

(The report `P:\Utopia_PC_Suite\reports\2026-07-21-powershell-defender-diagnosis.md` carries over the
same Codex misunderstanding — reconcile or mark if cited. Do not disable Defender or add
exclusions as a "workaround": not applicable, because it was not Defender.)

## Script changes NEVER hot-load from the work drive on this install - the PBO wins; rebuild the PBO for every script iteration (SP-078, added 2026-07-20)

Measured 2026-07-20 (LFHeli toggle diagnosis): with `-filePatching` on server AND client, `allowFilePatching=1`, work drive mounted and `P:\<prefix>\scripts\...` present, the engine still compiled the scripts FROM THE PBO. Probe prints existing only in the source tree never appeared over two boots; after `dayz-test.ps1 -Build` (packonly repack) the same prints appeared immediately. Consequences:

1. "Iterate scripts without repacking" does NOT work here. Every Enforce change needs a PBO rebuild (packonly, seconds) + relaunch. Treat the PBO as the only script source of truth.
2. Loose-file MODEL/texture shadowing is equally unproven on this install - do not attribute stale visuals to (or expect fresh visuals from) work-drive loose files; verify what the engine runs, do not assume filepatching semantics.
3. **The srcprobe discriminator** (cheap, definitive, one boot): change a LOG STRING in an already-printing line in the SOURCE only (e.g. `[TAG]` -> `[TAG srcprobe]`), relaunch WITHOUT rebuilding, grep the script log: token present = source served; absent (old string still printing) = PBO served. Use it before wasting cycles on "why doesn't my script change do anything".

Origin: 3 boots lost to probes that were "deployed" but never in the runtime; the PBO-wins fact then explained an earlier red herring the same day (a stale `P:\LFHeli\models` tree suspected of shadowing the deployed model - it never did).


## Secure-launcher runtime traps: daemon argv, staging dir, opaque errors (SP-092, added 2026-07-26)

Three infra traps cost most of a session on 2026-07-26. All three are cheap preflights.

**1. The daemon argv is derived from the client registrations - and the handoff documented it wrong.**
`host_config.resolve_daemon_provenance()` reads BOTH `~/.claude.json` (`mcpServers.dayz-mcp`) and
`~/.codex/config.toml` (`[mcp_servers.dayz-mcp]`), requires them to agree, and builds ONE canonical
daemon argv. Hand-starting the daemon with anything else is rejected with `daemon_identity_unverified`
- by design, so nothing can squat the port and impersonate the daemon. The session handoff said
`--idle-timeout 1800.0`; the registrations say `600`, so the canonical argv ends in `--idle-timeout 600.0`.
That single wrong number made every retry impossible.
Never guess the argv - ask the system:
`python -c "import sys; sys.path.insert(0,r'<tools>'); from dayz_mcp import host_config; print(host_config.resolve_daemon_provenance().argv)"`

**2. The CLI hides its own error code.** `secure_launcher` prints only
`secure launcher failed: ControlClientError` and swallows the code. Getting `daemon_identity_unverified`
required a wrapper script that caught the exception and read `.code`. If a launch fails, capture the
code first - do not retry blind.

**3. `oh1-build-deploy.ps1` fills the staging dir but never creates it.** `$Stage` under
`%LOCALAPPDATA%\Temp\LFHeli_OH1_stage` holds `$PBOPREFIX$`, so when Windows cleans `%TEMP%` the build
dies with `staging dir missing`. Rebuild it by copying the pack source (models/, proxies/,
`$PBOPREFIX$`, config.cpp) into it; the script overwrites the p3ds with the fresh ODOLs afterwards.

Also: the daemon self-terminates on its idle timeout (600 s), so a launch flow that worked hours
earlier will fail later with no change to the mod. Check port 8765 before blaming the build.

## Secure-launcher request grammar, the Steam prerequisite, and orphaned runs (SP-095, added 2026-07-27)

Four traps in one launch session on LFHeli OH-1. Each is cheap once known and expensive when not.

**1. The CLIENT needs Steam running. The SERVER does not.** A client launched with Steam down exits
immediately, writes a 793-byte RPT with only the header and an `ErrorMessage_*.mdmp` next to it, and
logs NOTHING useful. The real message is only inside the minidump: extract strings and look for
`Unable to locate a running instance of Steam`. There is no Windows "Application Error" event
because the engine handles it itself. Check `Get-Process steam` BEFORE launching a client, and start
it with `steam.exe -silent` if missing.

**1-bis. If that message appears while Steam IS running, stop reading the message and run the
discriminator.** Measured 2026-09-08 on SUB_BRZ: the client died on 5 consecutive launches with
exactly the string above, plus `[API loaded no]` in the same dump, while `Get-Process steam`
returned a live process, `HKCU\Software\Valve\Steam\ActiveProcess` held a non-zero `ActiveUser`
whose `pid` matched it, and steam.exe, DayZDiag_x64 and the daemon all ran as the same unelevated
user. Restarting Steam (`steam.exe -shutdown`, then relaunch) changed nothing, twice. Point 1's
advice ends at "check Steam is running"; when it IS, the reader has nowhere to go.

**The asymmetry is the clue: the server lives and the client dies.** Point 1 already says why - only
the client needs the Steam API - so the split names the suspect on its own, and the experiment that
separates the two causes is to launch the dead half YOURSELF, from your own user shell, with the
same command line (lift it from the RPT header or the dump). Two minutes, and it answers completely:

- **the hand-launched client dies too** -> the host or Steam really is broken, and that fix belongs
  to the user.
- **the hand-launched client lives** -> the DAEMON'S SPAWN CONTEXT is what breaks it, not the host.
  Different owner, different fix, and no amount of restarting Steam will touch it.

On that date it lived: it booted, connected, and reached the in-game HUD. `capture_screenshot` works
on it, because capture is host-side rather than a bridge verb. Filed as `fb-20260908-190943-5073`.

**Caveat that bounds the workaround**: a client you launched yourself is FOREIGN to the run record,
so the instance fence rejects its polls (`unaccredited_polls_by_class.instance_unknown` climbs) and
no client verb reaches it. Without `camera_set` there is no framing. It is good for putting a HUMAN
in front of the screen, not for automating a reading.

**The general rule, worth more than this case**: when one half of a client/server pair dies and the
other lives, their differing requirements already shortlist the cause. Run the by-hand launch of the
dead half BEFORE believing whatever subsystem the error message happens to name. Here the message
named Steam, and Steam was the one thing that could not help.

**And when it IS the daemon, re-measure before treating the wall as permanent.** Confirmed on
SUB_BRZ 2026-09-10, the day after: the same launch succeeded on the first try -- `client_alive=true`
at 17 s, player in game at 51 s, no Steam intervention, and `auto_remediate_steam` not even
requested. The only thing that had changed was `session_status.daemon_generation`. The wall was
daemon STATE, not the host, and a daemon restart cleared it. So record `daemon_generation` when you
file the finding, compare it when you retry, and give a freshly restarted daemon one clean launch
before spending a session on the workaround.

**2. The request JSON must not carry a UTF-8 BOM.** `Out-File -Encoding utf8` in Windows PowerShell
5.1 writes a BOM and the parser rejects the whole request with `invalid_dayz_test_request`. Write it
with `[IO.File]::WriteAllText($path, $json, (New-Object Text.UTF8Encoding($false)))`, or copy a
known-good request file and string-replace the fields.

**3. The request grammar has two coupled rules** (`dayz_test_request.py:336-344`), and violating
either returns the same opaque `invalid_dayz_test_request`:
- `kill: true` REQUIRES a `run_id`.
- With a `run_id`, `mode` may NOT be `server` or `all`; and `mode: "client"` REQUIRES a `run_id`.
So the valid shapes are: `server`/`all` without run_id (starts a run), `client` with run_id (joins
one), and kill as `mode: "client"` + `kill: true` + run_id (stops the run, not just the client).
`mode: "all"` in one request launches server AND client and avoids the run_id dance entirely - prefer
it when starting fresh.

**4. `run_not_adoptable` means the run is gone but its processes may not be.** The kill path tries
`adopt` then `stop` (`dayz_test_worker.py:496-507`); when both fail the lifecycle has lost the run
while a DayZ process may still hold port 2302, so every new run fails with `worker_failed` and the
audit trail shows `session_rejected reason=process_identity_mismatch`. Read
`%LOCALAPPDATA%\DayZ_MCP\audit\events.jsonl` (tail) - it names the real reason, which the CLI hides.
Recovery is a documented DEGRADED CLOSURE: close that specific process after verifying by
`CommandLine` that it is yours, then start a fresh run. This is the sanctioned exception to "never
kill DayZ processes directly": it applies only to a process you launched, under a run the guard has
already disowned, that is blocking the port.

**Also**: `lifecycle_cli.py` cannot be invoked standalone - it answers `missing_lifecycle_environment`
because the launcher chain sets its environment. Drive lifecycle operations through
`secure_launcher.run_secure_launcher` with a request on stdin.

**Method note that cost real time here**: `host_config.resolve_daemon_provenance()` raises
`daemon_provenance_conflict` if you call it with the SYSTEM python instead of the `.venv-mcp`
interpreter that both registrations declare - it compares `command` against the local launch
executable (`host_config.py:218-222`). That is a false alarm produced by the caller, not a
divergence between the Claude and Codex registrations. Always invoke with
`DayZ_MCP_dev\tools\.venv-mcp\Scripts\python.exe`.

Cross-ref SP-089 (allow-list format), SP-092 (daemon argv, staging dir, opaque errors), SP-085
(diag hangs outside the registered launcher).

## Rules promoted from lessons corpus (added 2026-07-27)

Promoted from `AI/20_Knowledge/lessons-learned.md` so they arrive via trigger instead
of depending on someone remembering to look them up. Each rule cites its originating `LL-NNN`;
the full entry (symptom, origin, evidence) lives there.

- **LL-118** — In the face of a regression, first compare launch command, `-mod` arguments, paths, and environment with the last passing run. Verify a measurable invariant between both runs and consult ledgers before formulating a code hypothesis.

## Rules promoted from lessons corpus (added 2026-07-27)

Promoted from `AI/20_Knowledge/lessons-learned.md` so they arrive via trigger instead
of depending on someone remembering to look them up. Each rule cites its originating `LL-NNN`;
the full entry (symptom, origin, evidence) lives there. Do not remove the citation: the
`lessons-index.md` index detects promotion by searching for that reference inside skills.

- **LL-196** — Search for mod's `Print()` and `DbgLog` in the most recent `script_*.log` of corresponding profiles. Use RPT for engine, CE, network, compilation, and native crashes; do not conclude “code did not run” from absence of prints in RPT.
- **LL-197** — Prepare command, paths, and arguments before acquiring a short lease; acquire and use the token in adjacent calls. If there was prolonged analysis, acquire again right before the blocking operation.
- **LL-198** — In managed cycles, execute `adopt → stop` while server and client remain alive; request keeping both open between iterations. If a peer already died, use documented degraded shutdown and wait for auto-heal before relaunching.

## `dayz_test_run` with `build:true` does NOT build — and the error it returns does not say so (SP-139, added 2026-07-29)

On this box DayZDiag only starts via registered native launcher (SP-085), so
`dayz_test_run` is the only way. **Its `build:true` is BROKEN**: returns generic
`dayz_test_failed` and **does NOT write the PBO** (hash and mtime of deployed remain intact).
Measured 2026-07-29 in DayZ_MCP, reproduced 2 times, always at ~16 s.

Why it is deceptive: `dayz_test_failed` is the `except Exception` of `server.py:1101`, which **swallows the
real cause** — it is not a tool error code, it is "something threw and I don't know what". Reading the audit
(`%LOCALAPPDATA%\DayZ_MCP\audit\events.jsonl`) is not enough here either: lease is granted and
released cleanly, with `runs_released: []` and no run event. Looks like a build failure and does
not say where.

**Bisection isolating it in 3 calls** (perform it before touching anything):

| Call | Measured result | What it rules out |
|---|---|---|
| `preflight: true` | `succeeded` in 1.5 s | launcher, PE, bundle, request, and lifecycle are HEALTHY |
| `mode: server` without `build` | `succeeded` in 5.1 s | launch works |
| AddonBuilder by hand | `Build Successful`, exit 0, ~3.4 s | **AddonBuilder is not the culprit either** |

With those three, the failure is isolated to the LIFECYCLE build path, which is platform.

**Verified and repeatable workaround** (build outside published path, which is also what
§RELEASE-GRADE BUILD BOUNDARY of this same skill requires):

```powershell
# 1. build to staging, NEVER directly to published path
AddonBuilder.exe P:\<Mod> <staging> -prefix=<Mod> -temp=P:\temp\<Mod> -clear -packonly
# 2. validate by CONTENT before publishing (count anchors, not Contains -- SP-065)
# 3. publish and verify by SHA-256, not by mtime
Copy-Item <staging>\<Mod>.pbo P:\Mods\@<Mod>\Addons\<Mod>.pbo -Force
(Get-FileHash 'P:\Mods\@<Mod>\Addons\<Mod>.pbo' -Algorithm SHA256).Hash
# 4. start with dayz_test_run WITHOUT build
```

Two preconditions that were already documented and are load-bearing here: deployed PBO remains
**LOCKED while the run is executing** (stop run before publishing), and per SP-078 **scripts do not
hot-load on this install**, so each Enforce iteration requires this entire cycle.

Origin: DayZ_MCP, grouped gate of `query_all_players` (2026-07-29). Real cost: ~20 min of
bisection on an opaque error naming neither build nor launch.

**Associated method lesson**: `LL-224` — the opaque error was narrowed down by bisecting CAPABILITIES (preflight / without feature / tool by hand), not reading the code that threw it. The table above IS that bisection; reuse the pattern for any wrapper error that describes nothing.

## `dayz_test_run` `extra_mods` REPLACES the extras list, does not extend it (SP-323, added 2026-08-22)

Passing `extra_mods=["@MiMod"]` to `dayz_test_run` **replaces** extra mods with that
list instead of appending to those the project brings. If the `@DayZ_MCP` bridge traveled
there, it drops out and **all MCP verbs stop working even though the pair
boots perfectly**: both processes alive, responding, with mission loaded,
and `bridge_status.ready.reason = server_poll_stale` with `last_poll_age_s` frozen at
the value from PREVIOUS run. Misleading symptom because everything else is healthy.

**Cheap 5 s check**: grep server script log for `DayZ_MCP` in the list of
`defines:` of any module, or for the line `[DayZ-MCP] config loaded ... poll_hz=`; if absent,
the mod was not loaded. ALWAYS name `@DayZ_MCP` explicitly in `extra_mods`.

Second note from same launch: **`mode="pair"` does not exist** and returns
`bad_dayz_test_request` without saying which are valid. Modes are `server`, `client`,
and `all`. Reliable path remains `server` -> wait -> `client` with same
`run_id` (T9-HARNESS-046), not `all`.

Origin: session 2026-08-22; one full boot cycle lost to this.

## (added 2026-08-01, HH-60G v19) Diag RPT BUFFERS ~52 KB, and lifecycle needs its window after run_not_adoptable

Two operational facts from 6-boot overnight run (all reproduced several times):

1. **A frozen RPT does NOT distinguish dead process from un-flushed buffer.** Diag writes the
   RPT to a buffer of ~52 KB (tonight: 5 distinct boots, ALWAYS ~464 lines / ~52 KB at the
   moment of failure, with different contents). Real discriminant is **CPU delta of
   the process in 30 s** (`Get-Process` twice): flat = truly stopped; growing =
   alive with log buffered. Additionally `Get-Item`/stat over P:\ (OneDrive) can lie about
   size (927 b reported with 52 KB real): read with `Get-Content` (share-read) and count.
2. **After a `run_not_adoptable` from `dayz_test_stop`, the lifecycle has a reconciliation
   window**: next `dayz_test_run` returns `active_run_exists` even if
   processes are dead. Pattern that worked (x3): close orphan DayZDiag by
   process, retry stop until it returns `run_not_active`, and ONLY then launch
   the new run.

## Introducing CF on a mission with persistence written WITHOUT CF = hard server crash (added 2026-08-02)

If a project adds **Community Framework** (and with it Dabs/VPP) to a mission whose `storage_*` was
written in runs **without** CF, the server starts, loads the mission and **dies** upon reading
persistence. Exact signature (MercedesAMGLF 2026-08-02, server `crash_*.log`):

```
SCRIPT (E): Virtual Machine Exception
Reason: Failed to read modstorage for entity Type=Rangefinder, Position=<...>
Class: 'CF_ModStorageObject<ItemBase>'
  JM/CF/.../modstorage\cf_modstorageobject.c:142  Function OnStoreLoad_CF
  .../mpmissions/dayzOffline.chernarusplus/init.c:6  Function main
```

**What is most misleading**: the cited entity is **vanilla and random** (here a `Rangefinder`), so
the message points anywhere except the mod you just added. And the client does NOT fail —
loads well (`PlayerBase OnStoreLoad SUCCESS`) and closes cleanly behind the server, reinforcing
the mistaken reading of "client issue".

**Cause**: DayZServer `dayzOffline.*` missions are SHARED between projects. A project running
without CF persists entities without CF's `modstorage` data; the next one that does include CF
reads them and crashes.

**Remedy** (convention already established in the mission folder itself, with 4 occurrences:
`storage_1_corrupt-modstorage-20260720 / 0728 / 0729 / 0802`): with processes stopped, **rename**
`storage_1` → `storage_1_corrupt-modstorage-<YYYYMMDD>` and let server regenerate. It is a rename, not
deletion, so it is reversible — but **starting again with CF on that storage crashes again**:
what is preserved is evidence, not a state you can return to with CF enabled.

**Consequence that must be told to user BEFOREHAND**: world and character are reset.

Cross-ref `SP-062` (same action — rename `storage_1` — for a different reason: persisted
entities that re-fire `EEInit`). Combined rule: **any change in mod set
altering who writes `modstorage` requires clean storage**, same as a measurement boot.

### The trap is BIDIRECTIONAL and the rule is decided at LAUNCH (measured 2026-08-21)

The reverse direction also bites, and faster: a server **without** CF starting on a
`storage_1` written **with** CF enters a VME storm — `!!! Scripted variables corrupted upon
"<entity>"` for EACH persisted entity (measured: **15,688 in ~3 min**, plain `-mod=@DayZ_MCP`
on a storage freshly saved by a server with CF) — and can die midway through writing
leaving the storage WORSE: rewritten entities lose their CF modstorage, and next
server that DOES include CF crashes with the signature above. Thus crossings chain together:
server-without-CF rewrites -> server-with-CF crashes -> rotation.

**Rule when launching on shared mission**: either `-mod=` includes CF, or `storage_1` is rotated
BEFORE starting. There is no third stable option — storage becomes "CF-flavored" as soon as a
server with CF saves once. Rotate = rename with reason
(`storage_1.bak-<YYYYMMDD>-<HHMM>-<reason>`, with processes stopped; occurrences 2026-08-21:
`-1605-modstorage-corrupt`, `-1610-cfless-storm`). Which storage needs rotation is told by server's
own RPT: line `[StorageDirs] :: Selected storage directory:`.

## (added 2026-08-12, LFHeli COM/pivot cell) AUTOMATED in-game cell without pilot: the 4 measured walls and workarounds

Eleven iteration cells in one day to get an automated cell green (stack + get-in +
engine + probes + parser, ~5 min). The four walls, measured with discriminants, so as not to pay
them again:

1. **DayZDiag does NOT define DEVELOPER for scripts (DOES define DIAG and DIAG_DEVELOPER)** — measured with
   defines telemetry on connected client. Any vanilla mechanism under `#ifdef DEVELOPER`
   (e.g. `SetGetInVehicleDebug`/`TryGetInVehicleDebug`, playerbase.c:3270-3295) DOES NOT EXIST in
   diag. Gate test code via command line parameter (`CommandlineGetParam`,
   game.c:660) or via `#ifdef DIAG`, never DEVELOPER.
2. **Automated get-in in MP: `StartCommand_Vehicle` directly from client seats a
   local GHOST** (own=true, HUD active) but server NEVER registers crew (crew0=false,
   consumed=0, ObtainState silent). The route that works: inject real ACTION —
   `ActionManagerClient.PerformActionStart(GetAction(ActionGetInTransport), target, null)`
   (actionmanagerclient.c:762; in MP enters through ActionStart, synchronized flow mirrored by
   server). Target componentIndex is obtained iterating `CrewPositionIndex(c)` until
   it returns desired seat (transport.c:116). Success is observed with `GetCommand_Vehicle()`
   on next tick (with retry), not marking done upon injecting. NOTE: `ActionCondition` is
   protected — cannot be pre-validated from outside; manager validates on both sides.

   **The framework reconciling this with SP-295** (measured against vanilla tree, 2026-08-18):
   crew membership and vehicle command are TWO distinct things, and only real action
   produces both. Crew is NATIVE engine state, not a script netsync:
   `Transport` registers a single variable (`m_EngineZoneReceivedHit`, transport.c:73) and
   `CrewMember`/`CrewDriver` are `proto native` (transport.c:111-128), readable from any
   client — that is why a client wanting to get in can reject an already occupied seat
   (actiongetintransport.c:57-60). `HumanCommandVehicle`, on the other hand, is created by
   `StartCommand_Vehicle` on THE MACHINE that calls it, and across the tree's 2,805 files there are
   exactly three call-sites: action itself (actiongetintransport.c:91), resumption
   after unconsciousness via `m_TransportCache` (dayzplayerimplement.c:2376) and a debug under
   `#ifdef DEVELOPER` (playerbase.c:3287). **None starts the command upon finding out via network
   that one is already seated.** From there arise both sides of the same fact: calling
   `StartCommand_Vehicle` directly from client gives command WITHOUT server crew (the ghost
   above); seating someone via script from server gives crew WITHOUT local command, and then
   any `ActionCondition` requiring being seated is NEVER satisfied, because they check
   `GetCommand_Vehicle()` and not `CrewMember` — as done by get-out
   (actiongetouttransport.c:68-74) and start/stop engine (actionstartengine.c:26-37). Beware of
   `IsInVehicle()`: accepts both routes (command OR parent Transport,
   dayzplayerimplement.c:465-468), so it is useless to distinguish them.
3. **A ASLEEP body rejects the injected get-in action** (PARKED sleep gate). If the mod
   sleeps the vehicle at rest, the cell must WAKE IT UP before get-in — simplest:
   start the engine server-side from test mission (`EngineStart`, car.c:244) AS SOON AS
   spawned, not upon detecting crew. Furthermore, without engine/simulation OwnerState channel does not flow
   (silent ObtainState/RewindState) even if player is seated.
4. **The real Enforce compile gate is stack STARTUP** (no offline check sees
   method visibility, e.g. protected). The cell must search `Compile error` / `Can't
   compile` in server script log BEFORE waiting for later phases, and treat client
   message-box as hang (phase timeout).

Orchestrator pattern that worked: wrapper with named PHASES (BOOT-spawn / BOOT-log /
COMPILE / CONNECT / GETIN / probes / SETTLE / teardown / PARSE), each with PASS/FAIL
verdict and its own timeout; logs are copied to evidence EVEN IF a phase fails; teardown
kills ONLY PIDs the cell launched. Full reference:
`LFHeli_dev\tools\run_celda_compivot.ps1` + `evidence-2026-08-12-offset\` (11 cells with the
cause of each failure). Cross-ref: session 2026-08-12-lfheli-oh1-com-pivot-medido-recenter-verde.

---

## Preflight: prove your celda's gates can go RED before you trust a single green run (added 2026-08-13, LFHeli council; LL-249)

A test-cell wrapper is only worth what its gates are worth, and two failure modes make a gate
**structurally incapable of failing** while it keeps printing green. Neither is visible by reading
the script in good faith. Both were live in a wrapper that had already gated ~12 in-game cells.

**1. A flag that turns your regex into a literal.** This line looks like a compile gate:

```powershell
Select-String -Path $slog.FullName -Pattern "Compile error|Can't compile" -SimpleMatch
```

`-SimpleMatch` makes PowerShell search for the whole string **verbatim, pipe included** — a
sequence that never occurs in a log. Measured against a synthetic log containing both real errors:
**0 hits with `-SimpleMatch`, 2 without it.** Every cell that "passed the compile gate" passed it
by construction. Same trap: `-Raw`, `-Literal*`, `[Regex]::Escape` on a pattern you meant as regex,
and `-match` vs `-like` mixups.

**1-bis. The symmetric one: a pattern that CANNOT come out green — `not closed` is a false red.**
(measured 2026-09-07, LFPowerGrid). If you add `not closed` to the gate thinking of Enforce's
`CParser: quoted string not closed` (§:626), you will find it in **healthy** boots:
CommunityFramework writes
`File "$mission:storage_1/communityframework/modstorageplayers.bin" was not closed. Always shut
down the server gracefully to prevent data loss.` every time previous server did not shut down
gracefully — which is ALWAYS if stopped via tool. Measured on same box: 1 occurrence in a
green boot and 0 in next, with `CParser` at 0 in both, meaning difference was shutdown
mode, not code. **Anchor pattern to `CParser`, not the loose phrase**, and if you really
want the phrase, also require `CParser` on the same line. A gate shouting red on
good boots deactivates itself: by the third time, someone ignores it.

**2. An analyzer whose input does not depend on the experiment.** Hardcoded log paths
(`$clientPath = ...client_script_2026-08-12_11-25-05.log`) mean every future A/B re-analyses the
same old flight and reports "no change" tautologically. Its sibling: a script that only prints
statistics and never sets an exit code — without one, nothing can fail, so it is a report, not a gate.

**Preflight before trusting any inherited gate** (cheap, and it is the only thing that separates a
gate from decoration):

1. Feed it a fixture that MUST fail, and confirm it fails. If you have never seen the gate red, you
   do not know it is a gate.
2. Grep the wrapper for `-SimpleMatch`/`-Raw`/`-Literal*` next to any pattern containing `|`, `.`,
   `*`, `\` or `(`.
3. Require parametrised inputs, and assert the analysed artifact is **newer than** the run that
   produced it (a stale-input check is one line and catches the whole class).
4. Require a non-zero exit code on failure, and check the caller actually propagates it.

Corollary for measurement campaigns: fix the gates BEFORE the campaign, not after. A campaign run
through a decorative gate produces greens that mean nothing, and you cannot tell afterwards which
of them were real.

## Teardown copies the logs BEFORE killing the client, and verifies the copy (SP-237, added 2026-08-13)

Killing the DayZ client immediately loses its last unflushed log buffer. A pilot
run's flight output was lost this way: the **client** log cut at `t=2118` while
the **server** recorded the dismount roughly 56 s later, so the interesting
window existed only in the buffer that the kill discarded.

The order is not "stop, then collect". It is:

1. **Copy** the script logs while the process is still alive;
2. **Verify the copy contains the stretch that matters** -- count the lines of the
   probe you expected to see, do not just check the file is non-empty;
3. **Only then** `Stop-Process`.

A teardown that kills first cannot be repaired afterwards: there is no second
copy of an unflushed buffer. This costs one line-count assertion and buys the
whole run.

## Validity of an automated run: preflight, cycle, and evidence

A cell only emits `PASS` if it demonstrates that it booted in the planned mode, covered the complete transition, and produced the evidence consumed by the verdict. Apply this contract before spending a batch:

1. **Preflight by mechanism and mode (LL-284, LL-307).** Document each guard as `protected mechanism → affected modes` and code the branch: a client-exclusive guard aborts with client and only warns in `-NoClient`, without manual bypass. On a box with multiple stacks, an unattended cell with client is not isolated from keyboard either: census other `DayZDiag` and active mods, record PID/mods and focus risk, and use a test-exclusive DIAG guard to reject human actions that would change state while script is active. Automation preserves a separate programmatic path. If you cannot demonstrate isolation, result is `SETUP_FAIL`.

2. **Boot identity and separation (LL-258, LL-260).** In a batch relaunching client, leave a conservative cooldown of 60 s from previous shutdown to next startup; a native crash during that startup is `SETUP_FAIL`, not a mod regression. Cooldown does not apply to a truly isolated one-shot because it does not chain another client. When packing evidence, do not select file by apparent mtime: product artifacts are named in UTC and RPT/mtimes use local time. Cross-check boot-id or internal marker against ledger incident; its timestamp rules over mtime. If expected boot markers are missing, reject bundle.

3. **Complete path and bilateral compile gate (LL-310, LL-312).** Draw each critical transition as `input → observable state → exit → poststate` and execute it via software. An autotest that only enters has incomplete coverage; first find the closing trigger among existing watchers, cancellations, and timeouts. Extend the gate from :811-814 (server) to client log: scan script logs of both peers for `Compile error` / `Can't compile` before waiting for functional markers. `Dead client / live server + Can't compile` is a client-only code compile failure, not a timeout nor runtime regression. Offline lint does not accredit `private`/`protected` visibility; real compilation of both peers is authoritative.

4. **Shutdown matching the measurement (LL-277).** SP-237 ("copy/verify before killing") preserves already emitted evidence, but does not accredit metrics born upon exiting. For leak reports, flushes, destructors, or final hooks, request graceful shutdown, wait for an explicit marker that the report or hook executed, and only then collect result. A forced kill produces `SETUP_FAIL` for all exit metrics and also prevents verifying a fix living in that hook. "Problem did not appear" never equals `PASS` if check never ran.


## Three pitfalls measured in LFPG S2-B cycle (added 2026-08-29)

All three cost time the same night, with healthy MCP bridge v10. None was from mod.

1. **`action_use` matches by CLASS NAME, not by action text.** The bridge iterates
   `ActionManagerBase.m_ActionsArray` and compares `candidate.Type().ToString() == wantedAction`
   (`DayZ_MCP/scripts/5_Mission/MCPClientBridge.c:1806`). Passing visible text -the one resolving
   `m_Text` from stringtable- returns `action_not_found` even if action is available on
   screen. Pitfall worsens with client in another language, inviting testing the translation:
   language is irrelevant, the key is the class. Take the name from `class X : ActionInteractBase`
   of the mod itself, never from stringtable.

2. **Steam gate from :99-103 only WARNS, and also does not run via MCP.** It is
   implemented in `templates/dayz-test.ps1:478-484`, which is THIS skill's launcher;
   MCP's `dayz_test_run` does not pass through there, so on the route used by MCP sessions the
   check simply does not exist. New variant observed 2026-08-29: `pid=0` **and** `ActiveUser=0`
   with **zero live Steam processes** (already documented signature was populated pid / ActiveUser=0).
   Same outcome: client RPT cut off right after argv, without a single script line, and
   server intact because it does not use Steam. Checking key before launching client takes 10 s.

3. **Active Steam ACCOUNT decides WHICH CHARACTER loads.** (Corrected the same day: see
   refutation at end of point — MOD state does not depend on account.) Restarting
   Steam can return ANOTHER account without warning. Measured 2026-08-29: 03:55 client entered
   as `76561197995575711`, with persisted character at test site; 04:17 client,
   after restart, as `76561198141021937`, with fresh character on coast. Site appeared
   without its devices and **looked like a mod persistence failure**. Registry key tells it
   without opening game: `ActiveUser = steamID64 - 76561197960265728`. Corroborated from outside:
   AddonBuilder prints `Steam_SetMinidumpSteamID:  Caching Steam ID:  <steamID64>` in its output.
   If cycle depends on persisted character, pin ACCOUNT in pre-flight, not just pid.

   **MEASURED REFUTATION THE SAME DAY, and the distinction is subtle and costly.** Returning to correct account
   returns CHARACTER (spawn at exact site, without teleport) but NOT mod state. With
   `...711` server still said `[VanillaWires] Loaded 0 entries from 0` and
   `RebuildTrackedDevices: tracking 0 wired devices`: zero wires across BOTH accounts. Meaning an
   empty test site is NOT explained by account, and whoever assumes so wastes time switching
   logins instead of mounting fixture. Useful rule is: account explains WHERE your
   character appears; mod state is either set up or absent.


## `modstorage` warning has 12 failures: turn it into preflight, not a paragraph (added 2026-08-29)

The section "Introducing CF on a mission with persistence written WITHOUT CF = hard server
crash" (added 2026-08-02) is correct and **has failed again**. Counted today host-direct in
the shared mission folder `DayZServer\mpmissions\dayzOffline.chernarusplus`:

    12 storage_1*corrupt-modstorage* folders, from 2026-07-20 to 2026-08-29,
    from at least 5 different projects (subbrz, amglf, gunracks, nocf-gate, lfquad2).

12 occurrences in 40 days. A note skipped 12 times is not fixed by reading it more
carefully the 13th time: precondition is MECHANICAL and is being asked by hand.

**Operational rule: persistence belongs to the mod set that wrote it.** Before launching
with a `-mod=` different from previous run on that same mission, rotate. It is not "if
you suspect": it is **whenever list changes**, and adding ONE mod already changes it.

    # with processes stopped
    $m = "<mision>"
    Rename-Item -LiteralPath "$m\storage_1" -NewName "storage_1_corrupt-modstorage-$(Get-Date -f yyyyMMdd)_<proyecto>"

Rename, not deletion: it is reversible. But starting again with CF on that storage crashes again,
so what is preserved is evidence, not a state you can return to.

**Warning to give BEFORE rotating**: world and character of that mission are reset.

And the process failure mode that let it slip this time, which is the one to recognize:
**precondition was verified against plan A, and plan changed.** I was going to use a new,
own copy of the mission, so "clean mission, no storage" was TRUE when dispatched. Then
the tool rejected the absolute path --`dayz_test_run` validates `mission` field against
`_MISSION_ALIASES` and only accepts `chernarus|livonia|sakhal`, see `dayz_mcp\dayz_test_tool.py:135`--
pushing me to SHARED mission. Discard traveled with old plan and no one re-evaluated it.

**A discard is surnamed with the plan that justified it: if path changes, preconditions you
cleared are unverified again.** Applies to any caveat in this skill, not just
this one.


## After a reboot, `P:` does NOT exist -- and FileBank packs emptiness with exit 0 (added 2026-08-29)

`P:` is a `subst`, not a disk link: **does not survive a reboot**, let alone a hard
crash. Everything that BI tools and sealed launcher touch hangs from there
(`P:\Mods`, `P:\<Mod>`, `P:\<Mod>_dev\_server\profiles`, `P:\scripts`, `P:\DZ`).

The expensive part is not that it is missing: it is **how it fails**. Measured today, with `P:` absent:

    FileBank.exe -property prefix=<Mod> -exclude <lst> -dst <staging> P:\<Mod>
    exit=0
    <staging>\<Mod>.pbo   ->   79 bytes

**Exit 0 and a 79-byte PBO.** Not a single message. Same failure mode as
AddonBuilder's `Build failed` with exit 0 already documented in this skill: BI tool
considers packing zero files a success.

**Preflight, two lines, before any build or launch:**

    Test-Path -LiteralPath "P:\"          # si False:
    subst P: "<dayz-projects>"

And check anchors, not just root: `P:\<Mod>\config.cpp`, `P:\Mods\@<Mod>\Addons`,
`P:\scripts`, `P:\DZ`. **Validate PBO by SIZE and entry count** before
publishing; a three-digit byte package is the signature of this.

## Steam `pid` in registry can be DEAD, and this skill's check was not seeing it (added 2026-08-29)

This skill already requires `HKCU\Software\Valve\Steam\ActiveProcess` to have `pid != 0` and
`ActiveUser != 0`. **Necessary, but NOT sufficient: a non-zero `pid` can be a dead
pid.** After a hard PC crash the key retains the previous Steam pid; Steam
starts again with ANOTHER pid and **does not always rewrite the key in time**. DayZ reads that pid,
looks for that process, does not find it, and dies.

Measured today: registry `pid=25484`, live `steam.exe` `pid=13856`. The "not zero" check
gave GREEN on a broken system. The right question is not "is it zero?" but **"does that
process exist?"**:

    $k  = Get-ItemProperty 'HKCU:\Software\Valve\Steam\ActiveProcess'
    $st = Get-Process -Name steam -ErrorAction SilentlyContinue
    $ok = $st -and ($st.Id -contains [int]$k.pid) -and $k.ActiveUser -ne 0

**Failure signature, to recognize it without guessing** (three identical reproductions):

| signal | value |
|---|---|
| modal dialog | `unable to locate running instance of Steam` |
| dump exception | `0x80000003` **BREAKPOINT**, same exact address each time |
| client process CPU | **0 s** -- alive but stopped cold |
| client RPT | frozen at **847 B**, header only |
| loaded modules | ~69, last ones from Steam (`gameoverlayrenderer64.dll`, `tier0_s64.dll`) |

`0x80000003` **is not a crash**: it is a deliberate `int 3` of diag exe when popping its dialog. That
is why process remains alive with 0 CPU instead of disappearing, and why there is no failure event
in Windows Event Viewer: DayZ writes its own `.mdmp` and halts.

**Remedy** (revised 2026-09-12): reliable approach is **copying live `steam.exe` pid to the key**,
with guards: stable key between two reads, valid `ActiveUser`, single live `steam.exe` in your
session and in its path, rechecked just before writing and verified after. Restarting Steam
(`steam.exe -shutdown` and relaunch) preserves login but **may not rewrite the key**: measured
that day, Steam started with pid 34316, key stayed at 50968 untouched since previous night
and new pid only appeared in `HKLM\SOFTWARE\Valve\Steam\SteamPID`. If you restart, **check that
key matches a live process** before launching client; it is not enough that Steam "is open".

**The discriminating probe is `SteamAPI_IsSteamRunning`, not `SteamAPI_Init`.** With stale key,
DayZ's own `steam_api64.dll` returned `Init` OK and `IsSteamRunning` FALSE, and client died
just the same; after copying pid both came back true and client entered. A gate that only calls
`Init` yields green on broken state.

**Two Steam facts the registry cannot answer (measured 2026-09-08, LFPowerGrid; SP-382).** (1) WHICH account is logged in: read `logs/connection_log.txt` under the Steam install for `[Logged On, ...] [U:1:<accountID>] RecvMsgClientLogOnResponse() : 'OK'` (`SteamID64 = accountID + 76561197960265728`). (2) Whether that account OWNS DayZ: `steamapps/appmanifest_221100.acf`, field `"LastOwner"`. If the logged-in account is not the LastOwner, the client dies about one second after launch with the same header-only RPT + `0x80000003` signature while every registry check passes green; the dump's `Caching Steam ID: <id>` vs `LastOwner` closes the case in a minute. [EXACT] (measured, SP-382]

**How to read the dump without a debugger**, which is what broke the hypothesis loop: a minidump
brings `MINIDUMP_EXCEPTION_STREAM` (type 6) and `MODULE_LIST` (type 4); with ~60 Python lines one
extracts exception code and the module containing `ExceptionAddress`. Before theorizing
about drivers or mod, **read the instrument**: here `0x80000003` ruled out in one blow
"render crash" and "corrupt mod", which were the two hypotheses on which two boot cycles had already
been spent.

**And the method corollary, valid for any failure after touching the mod:** before searching
for the cause in your change, **deploy PREVIOUS artifact and reproduce**. Here the
pre-surgery PBO failed identically, exonerating work in a single cycle and sending search into
the environment. An A/B with old binary costs same as a hypothesis, and unlike
it, decides.


## Measured test-cycle patches promoted on 2026-08-31

The following rules apply to state after 2026-08-29 harvest. When
they correct a historical section, this block's correction rules; previous section is preserved
as evidence of measured evolution.

### Mixed build: `-include` filters sync, does not define PBO (SP-083 / SP-168, corrected by SP-177)

Historical statements in :125-155 need two boundaries. AddonBuilder uses a native route
for `config.cpp`, `.p3d`, and `.rvmat` discovered from faces, and another ordinary sync
route for `.c`, `.paa`, `.ogg`, `.layout`, and `.csv`. `-include` governs this second route; it is
not the final manifest. An `.rvmat` cited only from `config.cpp` can still be missing.

The published template of this skill does not pass a list today in
`templates/dayz-test.ps1:531-534`. Therefore, for a mixed mod do not accredit generic `-Build`:
use a build passing an adequate list for ordinary payload and validate actual PBO entries
afterward. Require at least equality of paths and counts for source `.c`, and check
separately materials cited by config. Do not add `*.rvmat` to a list and take it as proof.
Authoritative build semantics and full gate live in
`skills/dayz-pbo-build/SKILL.md`, section SP-177.

### Live logs and shutdown of a released run (SP-077)

DayZDiag keeps RPT and `script_*.log` open. `Get-Content` or `ReadAllText` can fail with
`IOException` throughout a waiter. To monitor a live peer, open with explicit sharing:

```powershell
$fs = [IO.File]::Open($path, [IO.FileMode]::Open, [IO.FileAccess]::Read,
                     [IO.FileShare]::ReadWrite)
try { $text = [IO.StreamReader]::new($fs).ReadToEnd() } finally { $fs.Dispose() }
```

In managed lifecycle, retain `run_id` and use public tools. If a low-level
operation finds a `released` run, the sequence is `adopt` and then `stop`; `stop` can only
return `run_not_adopted`. If another session already cleaned it up, `run_not_adoptable` + zero run processes
+ RPT ending in `Termination successfully completed` describes orderly shutdown, not crash.

### Binarize before spending a boot (SP-125)

Every candidate `.p3d` needs a binarize PASS verdict before entering a PBO, even if
final packing uses `-packonly`: packonly preserves MLOD, but does not make engine accept a
model that binarize rejects. Group models in the change and pay this gate once before build;
post-build census remains mandatory and tests another boundary.

### Offline identity between source and deployed PBO (SP-144)

Before planning by `path:line` citations or spending an in-game cycle, test what bytes the
game will compile:

1. Extract deployed PBO to a scratch with an extractor that correctly expands `Cprs`
   entries; validate extractor first against a known baseline.
2. Compute SHA-256 of file inside PBO and of source file cited by plan.
3. Demand equality for each file underpinning the change. A recent container mtime does not
   accredit its entries.

If hashes differ, plan is citing a tree different from runtime. Rebuild and repeat the
gate before diagnosing logic. This offline check is the cheap discriminant complementing
the `srcprobe` of SP-078.

### Deploy guard protects destination, does not freeze entire box (SP-150)

On a shared box, "zero DayZ processes" is too broad. Before replacing a PBO require
the two conditions protecting that destination:

1. No live process references target mod in its `CommandLine`/modline, measured with
   `Win32_Process`; executable name is not enough.
2. Target PBO allows exclusive opening with `FileShare.None`.

Record baseline hash just before copying and verify published hash after. If either
condition fails, do not deploy. If both pass, do not close processes from other lanes loading other
mods.

### Quoting and triage of a Diag that does not manage to write logs (SP-167)

For `name=value` arguments with spaces, quote the entire token:

```text
-profiles="<profiles-path>"      # NO: quotes only around the value
"-profiles=<profiles-path>"      # YES: a complete token
```

Apply the same pattern to `-config=`, `-mission=`, and `-mod=`. In Windows PowerShell 5.1, passing an
array to `Start-Process -ArgumentList` does not guarantee quoting of each element; do not use that
result as proof of the received argv. The managed path of this skill transports a structured
array and remains the normal way.

For a hang with 0 CPU and no RPT, first run the authorized minimal control
`DayZDiag_x64.exe -server`, with no other arguments, and add one by one. In the measurement that founded this
rule, ~53 modules was "has not yet reached UI" and 69-78 was real startup; use the delta as signature of the
measured build, not as a universal constant. Obtain the real argv with `Win32_Process`: the truncated
RPT header line does not reliably represent it.

### Bare client: separate argument, native path, and mod (SP-174)

Faced with a client that does not start, decide by form before touching the mod:

- **Alive, 0 CPU, without RPT or dump:** apply the minimal control and the previous argument bisection.
- **Dies with header-only RPT + `ErrorMessage_*.mdmp`, without `crash_*.log`, even without mods:**
  launch server of the same build. Stable server with large RPT and bare client crashing points
  to client native/graphics path. Confirm with another project's profile in the same window.
- **Only fails upon adding `-mod`:** then do open mod investigation and its load order.

"It was rebooted" is also measured: compare `Win32_OperatingSystem.LastBootUpTime` and verify that no
process prior to the declared instant survives. Fast Startup can preserve kernel after
shutdown; a full reboot changes that datum.

### Diagnostic spawn without depending on VPP UI (SP-210, single-use scope)

If administrative UI blocks a diagnosis, a private mission can use
`CustomMission.InvokeOnConnect` to create a fixture once per boot, at fixed distance from
player, with `CreateObjectEx(..., ECE_PLACE_ON_SURFACE)`. Use a one-shot boolean and clean storage.

It is a disposable fallback, not cell infrastructure. The portable rule of :383-392 continues
to govern: any spawner, watcher, or control that must survive the project lives inside the mod,
gated by DIAG and by an explicit parameter.

### Parsers: first extract actual `Print` payload (SP-234)

A string variable arrives in script log with a form equivalent to:

```text
SCRIPT       : string <var> = '<payload>'
```

Closing single quote is stuck to the last field. First extract what is between
`= '` and the last quote; only then tokenize numbers and fields. A log gate always includes
literal fixtures copied from a real log, in addition to synthetic cases, and counter-fixtures with truncated
wrapper. A self-test that never consumed a real line only validates the imagined parser.

### Teleport and readiness before injecting an action (SP-235)

To teleport player in a harness use X/Z of probed point and
`Y = GetGame().SurfaceY(x, z)`. The Y of a memory point can leave them in
`ACID_Human_Fall`; during Fall, an injected action can abort without error while server already
reserved seat.

Before spending an attempt, require an accepted command ID, no action in progress,
`CanStoreInputUserData()`, and `ActionBase.Can(...)`. Then observe real transition; do not mark
success upon sending action. A desync `server=Move, client=Fall` points first to placement.

### Headless retail server as parity term (SP-242)

The requirement of `DayZDiag_x64.exe` in :89-90 is scoped to iteration with `-filePatching` and to
official launcher of this skill. A headless retail `DayZServer_x64.exe` can load PBOs with
`-mod`, compile Enforce, and execute outbound `RestApi` without occupying client Steam session.
Measurement observed defines `RELEASE, SERVER, NO_GUI, SERVER_FOR_WINDOWS` and real HTTP polling.

Use it as second term of a diag↔retail gate when server-side behavior may
depend on `RELEASE` or developer-only APIs. It does not replace client for visual capture or for
verbs requiring a connected player. This server remains outside official lifecycle: only
a probe-gated runner possessing its exact PID can start and stop it.

### Multi-peer cells: clock, replay, and bilateral probes (SP-276 / SP-278)

For an exit failure or desync, instrument the callback equivalent to `OnDriverExit` on both
peers and emit in a single window `playerPos`, `vehiclePos`, `crewEntryWS`, and their distances. Align
client/server clocks with pairs of the same event; do not compare raw peer timestamps.

In an owner series with rewind/replay, multiple samples can share the same `t`. Retain the
first sample per tick —or collapse a documented interval smaller than 20 ms— before evaluating
edges. Convert server events to owner clock, use authoritative series as
primary oracle and owner as secondary, and re-run history after changing
the parser.

The bridge does not inject arbitrary values into `UAInput`. If the mod neutralizes `CarController` and
consumes its own axes, a cell needs a DIAG script on the owner before `WriteToMove`; this branch
is only promoted for the mod when an in-game run demonstrates that it steers.

### Contract of a repeatable scripted cell (SP-279)

- Spawn fixture at a known fixed location and place player at a fixed offset on
  `SurfaceY`; random spawn turns obstacles and doors into environmental noise.
- After an exit, rearm placement server-side after cooldown with player on foot.
  Re-entry is part of the test: a ghost pose on client invalidates reach and `Can()`.
- `forces-off`, `clamp-abort`, `no-probes`, `no-pilot`, and `not-owner` are **INCONCLUSIVE** and accept
  bounded retries. A timeout after satisfying preconditions is **FAIL**.
- Script executes; it does not adjudicate. Its gates are the same as preregistration. Detects "settled" by
  sustained AGL or, better, by authoritative state, not by an isolated owner velocity.

### Isolation, settle, and effect probes in cells (SP-285)

While scripted pilot is active, a DIAG guard must reject in `ActionCondition`
human actions that break the cell, but preserve a separate programmatic route. Settle is
decided by mirrored authoritative state (`GROUND_READY`/`PARKED`) and uses AGL only as backup;
owner can keep bouncing after authority is settled.

Instrument symptom callback on both peers with a gated probe and stack. On client print
stack line by line to prevent truncation and do not call APIs whose validity is server-side only. Upon
startup, runner probes other running DayZDiag with PID, modline, and port; if 2302 belongs to another
session, choose a different accredited port. This extends preflight of :976 without touching foreign
peers.

### Whoever opens a manual process also closes it (SP-344)

Managed runs are closed by their `run_id`. For an authorized manual process outside MCP,
the agent that opened it retains PID and `CommandLine`, requests orderly shutdown with
`CloseMainWindow()`, waits 8-10 s and uses `Stop-Process -Id <pid>` only as exact fallback. Never
select by executable name or touch a peer from another session.

If the window was opened by the user and they are playing, closing remains theirs via UI. If opened
by the agent, the user is not turned into a cleanup operator; asking to continue the cycle authorizes
closing only those own processes.


## Two traps of the build-deploy-test cycle that make a useless run green (added 2026-08-31)

Both measured on 2026-08-31 closing an engine gate. Neither gives an error; both let
you draw conclusions from a run that did not test what you think.

### 1. `DSSignFile` returns 0 after a failed build — and signs the OLD PBO

`dayz_test_run` (and any live client/server) leaves the PBO **locked**. Rebuilding with
AddonBuilder while the run is up gives `[ERROR]: Build failed`, and if the script chains
signing, `DSSignFile` exits with **`EXIT=0`** quite happily: it has signed the previous binary.

Chained in a `.ps1`, the result is a `SIGN=0` that seems to confirm deployment.

**Stop the run before rebuilding**, and verify the result by **the PBO table against
source size**, never by exit codes:

```
scripts\4_World\LFG10_Probe.c    3579     <- y en disco: 3579
scripts\5_Mission\LFG10_Driver.c 4756     <- y en disco: 4756
```

It is the same doctrine that is already in `DAYZ_INFRA.md` ("the verdict of a build is the PBO
file table, not the exit code"), extended to signing: **the exit code of `DSSignFile` says
nothing about whether the build got in.**

### 2. Persistence returns the subject as the previous run left it

An experiment measuring entity state (health, wetness, quantity, temperature) **cannot
rely on spawn loadout**. Measured: character returned with garment at `wetlevel=4
hplevel=2`, exactly where previous run had left it, so control for new run
started **already past the threshold it had to cross** — and would have given "control does not
fire" falsely.

The probe **normalizes the subject** before measuring anything (`SetWet(0)`, `SetHealthLevel(0)`, whatever
applies) and records it in log. And if there is a client part depending on that state, it binds to
**the condition, not a timer**: wait to observe subject already normalized, because
normalization itself is a state change that can clobber what you were about to measure.

### Bonus: a disposable probe does not need to register as an MCP project

`P:\Mods` is `mod_root` of the ten approved projects in `request-policy.json`, and
`dayz_test_tool._valid_public_mod` accepts any relative folder inside those roots. Thus:

```
dayz_test_run(project="DayZ_MCP", mode="all", extra_mods=["@MiProbe"])
```

starts with the full bridge (`capture_screenshot`, `camera_set`, `query_player_state`, `wait_for`
on `log_matches`) **plus** your probe, without touching sealed policy or rebuilding it with
`build_native_launcher.py`.

## The post-build gate of generated `dayz-test.ps1` checks EXISTENCE, not freshness (added 2026-08-31)

Complements the previous section, does not repeat it: there lies the doctrine ("the verdict of a
build is the PBO file table, not the exit code"); here is **the instrument that
this very skill generates and that violates it**, with its exact line and the fix.

Origin: ticket `fb-20260830-011217-668f` from the pipeline inbox (`project: LFQuad2`,
2026-08-30 01:12), archived by another session. The phrasing "checks that PBO EXISTS,
not that it is the new one" is theirs.

### What the generated script does today

Verified on 2026-08-31 on **three independently generated copies**, not on one:

```
A6_MK47_dev\tools\dayz-test.ps1:422-429
ExpandedBuilding_dev\tools\dayz-test.ps1:403-408
LFGungame_dev\tools\dayz-test.ps1:353-354
```

The sequence, taken from `A6_MK47_dev\tools\dayz-test.ps1:422-429`:

```powershell
if ($p.ExitCode -ne 0) { Die "AddonBuilder failed (exit $($p.ExitCode)). ..." }
$pbo = Join-Path $target "$Mod.pbo"
if (-not (Test-Path $pbo)) { Die "Build reported success but $pbo is missing." }
# Sanity: ... -lt 4096 ...
Ok "deployed: $pbo ($((Get-Item $pbo).Length) b)"
```

Three checks, and **none of the three looks at whether the PBO is from THIS build**:

| Check | What it answers | What it does NOT answer |
|---|---|---|
| `$p.ExitCode -ne 0` | if AddonBuilder returned != 0 | nothing if it returns 0 **and still fails** — measured in the ticket: `[ERROR]: Build failed` in its log with exit 0 |
| `Test-Path $pbo` | if **a** PBO exists | if it is the new one. Previous one also exists |
| `Length -lt 4096` | if it came out ridiculously small | nothing: a full old PBO weighs megabytes and easily passes |

With game running target PBO is **locked**, AddonBuilder's final copy
fails, and wrapper prints `[ok] deployed` and exits with **exit 0** on previous binary.
It is the same lock from `DSSignFile` section, one step before: there old PBO is signed,
here it is declared deployed.

### The three levels, and why gate must be on the third

**Existence** ("there is a PBO") is satisfied by previous build. **Freshness** ("this PBO is
newer than build") is satisfied by a new empty PBO. Only **content** ("this PBO
contains these sources") answers the question asked by the one testing the mod.

The minimal fix, which costs two lines and closes the measured case:

```powershell
$before = if (Test-Path $pbo) { (Get-Item $pbo).LastWriteTimeUtc } else { [datetime]::MinValue }
# ... Start-Process AddonBuilder ...
if (-not (Test-Path $pbo)) { Die "Build reported success but $pbo is missing." }
if ((Get-Item $pbo).LastWriteTimeUtc -le $before) {
    Die "PBO no cambio: AddonBuilder no lo reescribio (destino bloqueado por una corrida viva?). El desplegado sigue siendo el anterior."
}
```

The good fix is the content gate, and is written in **complementary form**: not a
list of what could have been left behind, but the positive statement **"every current source
is in deployed PBO with its size/sha"**. The source list is short and you
traverse it; that of things that can stay stale has no end.

That gate is not theoretical: on 2026-08-31 two gates of that form —one of byte-for-byte identity
against a snapshot, another of "each source present in PBO with its sha256"— detected in
another mod a PBO that had appeared in the tree and was not deployed. A `Test-Path` would
not have seen anything.

### When this bites

Whenever rebuilt with game running, which is just what the filepatching
cycle invites you to do. Before rebuilding, **stop the run** (see `DSSignFile` section). And if
you are going to chain build → sign → deploy in an unattended batch or in parallel lanes,
put the freshness gate before signing: signing the previous binary and deploying it produces
an artifact that seems correct in all steps and does not contain the change.

**Cheap sign that it happened to you**: AddonBuilder log says `[ERROR]: Build failed` and
your wrapper says `[ok] deployed` next. If those two lines coexist in the same
run, the PBO you are going to test is the old one.

**Two more masks of the same trunk (af59 round 2, measured 2026-09-08).** (1) The generated launcher FABRICATES its own destination: `Invoke-Build` creates `<WorkDrive>\Mods\@<Mod>\Addons` with `New-Item -Force` if missing, and `-BuildOnly` / `-Mode none` reach `Invoke-Build` without passing through the preflight, so a missing `Mods` folder becomes a PLAIN folder that silently receives the PBO — the script prints `[ok] deployed` and the engine never reads it (reproduced literally: `exit=0; Mods created=True; junction=False`; the two lines are in 6 of 6 mod trees and in the template). The destination check — exists AND is a reparse point — must run from the build path itself before copying, not only in the interactive preflight. (2) Add the stdout text gate beside the byte gate: capture AddonBuilder stdout (`Start-Process -RedirectStandardOutput`) and require `Build Successful` while rejecting `[ERROR]: Build failed`. The pair discriminates: a false "Successful" with an untouched PBO dies on the mtime/hash gate; a touched-but-failed build dies on the text gate. A FIRST legit build has no previous PBO, so the byte comparison must be guarded (compare only when a previous PBO existed). [EXACT] (measured, SP-380]

### SP-124 — Free lease does NOT imply free box

`session_status` can return `owner: null`, empty queue, and `claimable: true` while a DayZ
server and client are alive, launched outside the managed lifecycle by another project
line and occupying port 2302. The lease speaks of the lease, not of the box.

Before considering the box free, read `-mod=` of living processes:

```powershell
Get-CimInstance Win32_Process -Filter "Name LIKE 'DayZ%'" |
  Select-Object ProcessId, CommandLine
```

The command line tells whose run it is and whether it loads your mod.

Corollary for build: the "no DayZ process" guard can be **narrowed** to the two
conditions it actually represents —no running process loads your mod, and target PBO opens
exclusively— instead of skipping it or waiting for the other line to finish.

Cross-ref: `dayz-mcp-verify` (same rule, bridge side).


## An in-game observation is worth whatever the `-mod=` line of ITS run is worth (added 2026-09-05)

Distinct from the previous section, which reads `-mod=` to know **whose box it is**. This one
reads it to know **if the observation serves as evidence**, and is done BEFORE using it, not at
launch.

Measured on 2026-09-04 on two mods at once. Of six runs with `@LFQuad3`, **one** carried
`@SurvivorAnims`; of the four of LFQuad2, **none**. `LFQuad3.c:86-88` (and its twin in
LFQuad2) does `GetAnimInstance` -> returns 22 only if `CfgPatches SurvivorAnims` exists, and otherwise
falls back to `VehicleAnimInstances.V3S`, which is TRUCK pose on a quad. With the wrong pose
**driver camera is not where it would really be**, and that moves both what is seen from
seat and which LOD engine chooses. LFQuad2 had diagnosed and "fixed" a LOD
symptom on those runs and had to withdraw the fix: cause was not verified.

The failure is silent by construction: missing mod gives no error, game starts,
observation seems normal and user reports it in good faith.

**Upon receiving an in-game observation that will decide code or geometry:**

1. Locate RPT of THAT run (server and client) and read its first `-mod=` line.
2. Check that mods on which observed behavior depends are present. The three most silent:
   - an **animations** mod queried by `ConfigIsExisting` from `GetAnimInstance` or
     other hook -> without it, pose and camera are different;
   - a **framework** (CF and company) that writes modstorage per entity;
   - the content mod itself whose objects must be seen.
3. If any is missing, observation is not discarded: **it is reclassified**. Whatever does not depend on
   pose or LOD remains valid (a mirrored texture is so from any angle); whatever
   depends on where the eye is, does not.

Name trap in this tree: `@Survivor Animations` **with space** splits the command
line (in RPT it is seen cut off at `-mod=...;P:\Mods\@Survivor`). The good junction is
`@SurvivorAnims`.

Cheap audit of a whole workday, to know which runs are valid:

```bash
for f in _server/profiles/*.RPT _client/profiles/*.RPT; do
  m=$(grep -m1 -oE '\-mod=[^ ]*' "$f")
  printf "%-52s %s\n" "$(basename $f)" "$m"
done
```

## (added 2026-09-08) Three walls of managed startup that do not name their cause

Measured in a verification startup of LFPowerGrid. All three return a code that does not
describe what happens, and all three are resolved in one minute if you know which it is.

### 1. `launcher_root_identity_drift` — the seal fixes the DIRECTORY, not just binary

Sealed registry pins NTFS identity **of the directory** containing launcher
(`launcher_registry.py` `_open_validated_entry`: compares `root_file_id` = `file_id` +
`volume_serial_number` against `os.stat(root)`). If that directory is **recreated** —and it is under
OneDrive, which does so— `file_id` changes and **the entire** managed path dies, `preflight`
included. Binary can be byte-identical and it makes no difference.

**Diagnosis before touching a security seal**, because it distinguishes benign drift from
tampering: compare the two fields of `root_file_id` separately and **the sha256 of the PE**.
Same volume + different `file_id` + **PE with pinned hash** = directory was recreated and
binary did not change.

**Remedy** (it is the owner's to authorize, not yours to decide):

    cd <DayZ_MCP_dev>\tools
    .venv-mcp\Scripts\python.exe -m dayz_mcp.launcher_registry_update         replace-dayz-test-v1 --expected-sha256 <REGISTRY SHA256, IN UPPERCASE>

- It is `replace-*`, not `install-*`: `install` refuses while entry exists.
- CAS token is the sha256 **of the bytes of `approved-launchers.json`**, not of the PE.
- ⚠ **MUST BE IN UPPERCASE.** `_HEX = frozenset("0123456789ABCDEF")`, so a lowercase sha
  —what `sha256sum` produces— fails with `invalid_launcher_registry_update`, which says nothing
  about the format and sends you looking for the problem where it is not.
- Returns sha of the NEW registry, which is the CAS token for next operation.

### 2. Occupation is of BOX, not port: `port=` does not dodge a foreign process

With a foreign DayZ running, `dayz_test_run` returns `active_run_exists` / `port_in_use_foreign`
**even if you pass another `port=`**, and keeps naming 2302 in the error. The first hint says
"pass another port="; the second, with the box already read as occupied, says "retry with
wait_for_box_s". **The one that works is the second**: `wait_for_box_s` puts request into FIFO.
`port=` is only valid to coexist when the box is ALREADY yours.

Before waiting, verify that occupant is alive and not a zombie: `Get-Process` on
`DayZ*` and check **CPU and start time**. Growing CPU = real run of another line, it is
respected. And look at its `-mod=`: tells you whose it is.

### 3. `mode=client` requires repeating `extra_mods`, or rejects reattach

Complement of SP-323 measured today: on client reattach, omitting `extra_mods` does not inherit those
from server start — fails with `bridge_mod_missing: add extra_mods=['@DayZ_MCP']`. Pass the
**same list** as in `mode=server`, or whole set's seal changes in addition to losing bridge.

### Bonus: `condition_failed` vs `action_not_found` is a discriminator, with its control

`action_use` distinguishes the two things, and that turns a cheap probe into proof: `action_not_found`
= action class is not in player array; `condition_failed` = **is present and resolved
against target**, and rejected by its `ActionCondition`. Serves to accredit that an action
reaches an entity type without setting up the fixture satisfying its guard. **With negative
control**: also launch an invented action name on the same object and verify that it gives
`action_not_found`; without that control you do not know if both codes are truly distinguished.

## An unfocused DayZDiag client runs at ~20 fps: what the client measures depends on who holds the foreground (SP-391, added 2026-09-13)

Measured on F1 bench of LFHeli (DayZDiag, windowed client and server on same machine),
**with manipulation**, not by correlation:

- With its window in foreground, client runs at **25.0 ms** per frame (40 fps); without focus, at
  **51-52 ms** (~20 fps). Within the same cell, toggling focus moved median
  26 <-> 53 ms.
- It is not shared GPU or CPU distribution: 0 of 10 slow cells coincided with
  local LLM inference, and pinning client to 2 cores with high priority left 4 of 4 cells at
  51-52 ms. Slow ones form a narrow ceiling (91% of frames within +-3 ms), not a contention
  tail.
- What it entails: heli idle bouncing **followed focus**. With focus held, 6 of 6
  still idles; with focus removed, it bounces. Any client-side measurement
  (presentation, owner physics, `vehicle_trace`) inherits focus state.
- On a machine with multiple sessions, foreground is stolen every few seconds by other
  applications: measured Discord, OpenCode, Cursor, another session's AddonBuilder, and explorer.

Reglas:

1. A bench measuring client **holds foreground during the entire run** (reaffirming it
   every 0.25 s suffices) and **records compliance** every second along with data.
2. If design requires removing focus, park it on a **visible and activatable window of an
   own process** (a Tk window works). Two measured destinations that fail: DayZ server
   console (Windows returns focus to client instantly: compliance 1.00 with ~430
   attempts per cell) and `Start-Process notepad.exe` on Windows 11 (returned PID is a
   launcher that exits immediately; window lives in another process).
3. A cell archive run with random focus mixes two frame regimes: before
   comparing variants, stratify by frame time or repeat with focus held.

Evidencia y recetas: `<vault>\30_Sessions\2026-09-13-LFHeli-el-bote-sigue-al-foco-del-cliente.md`.
