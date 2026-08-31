---
name: dayz-test-ingame
description: >
  Build, deploy and launch a DayZ mod locally to test it in-game with filepatching,
  using DayZDiag_x64.exe — server+client on one box, or single-exe offline. Operationalizes
  DAYZ_INFRA.md: AddonBuilder PBO build, deploy to the P:\Mods junction (to DayZ\!Workshop),
  serverDZ.cfg allowFilePatching, diag launch flags, mission resolution. Generates a
  parametrized dayz-test.ps1 orchestrator plus server/client/offline .bat wrappers in
  the mod's _dev\tools\ folder. Use when the user wants to: "lanzar el juego con el mod", "probar el mod
  in-game", "test the mod in-game", "arrancar server local", "launch DayZ with my mod",
  "filepatching", "iterar scripts sin re-empaquetar", "probar HiddenBase/LFPowerGrid en local",
  "DayZ offline mode", run/start/launch the
  mod, connect to 127.0.0.1, the build-deploy-launch loop. Also for BattlEye filePatching
  kicks (0x00020005), stuck DayZDiag/DayZServer processes, "the mod doesn't load in-game".
  Pairs with dayz-pbo-build (packaging) and dayz-mod-workflow (debug).
---

# DayZ test in-game (filepatching launch)

## WHAT THIS DOES

Closes the dev loop for a DayZ mod on a single Windows box: re-pack the PBO, deploy it
where the engine reads mods, and launch `DayZDiag_x64.exe` with `-filePatching` so script
and config edits are picked up without re-binarizing. Three launch modes (offline / server /
client / all) driven by one orchestrator script and double-click `.bat` wrappers, generated
per mod into `<Mod>_dev\tools\`.

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
default to the diag exe. Retail es manual-only y externo a este launcher.

## PROTOCOLO DE SESIÓN COMPARTIDA

Leer antes de lanzar:
`<runbooks>\dayz-mcp-agent-session-protocol.md`.
El launcher oficial es Diag-only y aplica esta matriz:

| Ruta | Ejecutable / rol | Contrato |
|---|---|---|
| Diag gestionado | `DayZDiag_x64.exe`, incluido el rol `-server` | `managed_lifecycle=true`; `dayz_test_run` posee lease/heartbeat/release y devuelve `run_id`. |
| Servidor dedicado | `DayZServer_x64.exe` | `managed_lifecycle=false`; probe-gated y no lo inicia el launcher oficial. |
| Retail manual externo | Sesión abierta por el usuario fuera del launcher | Sin lifecycle de agente; activa cuarentena. |

1. Ejecuta `bridge_status`; con cuarentena retail solo se permiten lecturas.
2. [EXACT][CLAIM-R21-TEST-PUBLIC-LIFECYCLE] Usa `dayz_test_run` para el
   server/client gestionado y `dayz_test_stop` para el `run_id` exacto. Esas
   herramientas poseen la cola FIFO, lease, heartbeat y liberación; NO
   pre-adquieras otro lease alrededor de ellas.
3. `session_acquire`/`session_wait`/`session_heartbeat`/`session_release` quedan
   para mutaciones de bajo nivel que no estén encapsuladas por las herramientas
   públicas.
4. [EXACT][CLAIM-R21-TEST-CREDENTIAL-SCOPE] El launcher aprobado recibe
   `DAYZ_MCP_CLIENT_ID_JSON` y `DAYZ_MCP_LEASE_TOKEN` solo en el entorno de
   proceso. La plantilla los captura, los retira del entorno padre y los
   restaura únicamente alrededor del proceso hijo; nunca copies sus valores a
   shell, argv, logs o handoff ni invoques el launcher aprobado directamente.
5. Conserva el `run_id` devuelto. El mismo mod no concede ownership: stop/adopt
   requieren el run exacto. `-Kill` sin `-RunId` queda fail-closed.
6. Verifica estado terminal después del stop. NUNCA sustituyas el lifecycle
   guard por un kill o por atribución basada en nombre, mod, cmdline o perfil.

Retail manual-only activa cuarentena retail: el usuario que lo abrió lo cierra por la UI y
después ejecuta doctor/rescan. Sin acceso a esa UI, declarar `manual_cleanup_required`; otro
agente no mata ni adopta el proceso.

## PREREQUISITES (preflight — runs automatically)

The orchestrator checks these every run and fixes what it safely can. Verified on this box
2026-05-30: missions present in DayZServer, AddonBuilder present, `P:\` mounted, but
`P:\Mods` junction NOT yet created and `DAYZ_*` env vars unset (fallbacks used).

- **Diag exe** — `DayZDiag_x64.exe`. Client AND server MUST be the diag binary; retail blocks
  past the loading screen with `-filePatching`. [EXACT — DAYZ_INFRA.md §Diag binary obligatorio para iteración]
- **`P:\Mods` junction** -> `<DayZ>\!Workshop` so deployed PBOs land where the engine looks.
  The script creates it via `mklink /J` if missing (no admin needed). [EXACT — DAYZ_INFRA.md §Layout de drives y mods]
- **`allowFilePatching = 1`** in the server's `serverDZ.cfg`, else BattlEye kicks the client
  with `0x00020005`. The script generates a dev `serverDZ.cfg` with it set. [EXACT — DAYZ_INFRA.md §serverDZ.cfg — allowFilePatching = 1; obligatorio]
- **Mission template** — absolute path; the server loads an empty mission otherwise.
  [EXACT — DAYZ_INFRA.md §Comandos de invocación canónicos — Server diag]. Aliases:
  `chernarus`/`livonia`/`sakhal`. [EXACT — DAYZ_INFRA.md §Mission templates — aliases canónicos]
- **AddonBuilder** — only when `-Build`. [EXACT — DAYZ_INFRA.md §Comandos de invocación canónicos — AddonBuilder]
- **Steam client session** — for CLIENT-launching modes only (`offline`, `client`, `all`),
  `HKCU\Software\Valve\Steam\ActiveProcess` must have both `pid != 0` and
  `ActiveUser != 0`. The script warns without aborting; run `steam.exe -shutdown`, then relaunch
  Steam (the login is preserved, no re-login is required, and the key repopulates in ~20 s).
  See `SKILL.md:362-366` for the measured failure signature and details. [EXACT — SKILL.md:362-366]

Path resolution is env-var-first, Steam-default fallback (`DAYZ_GAME_PATH`, `DAYZ_DIAG_PATH`,
`DAYZ_TOOLS_PATH`, `DAYZ_WORK_DRIVE`). [EXACT — DAYZ_INFRA.md §Variables de entorno opcionales (resolvers)]

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
| `all` (default) | server, wait for UDP bind, then client | [EXACT — DAYZ_INFRA.md §Comandos de invocación canónicos — Server diag + Cliente diag] |
| `server` | `DayZDiag_x64.exe` gestionado con `-server` | `managed_lifecycle=true`; [EXACT — DAYZ_INFRA.md §Comandos de invocación canónicos — Server diag] |
| `client` | diag `-connect=127.0.0.1` (server already up) | [EXACT — DAYZ_INFRA.md §Comandos de invocación canónicos — Cliente diag] |
| `offline` | single diag with `-mission`, no network | **[DESIGN]** validate in-game |

## RETAIL EXTERNO MANUAL PARA MODSETS DE TERCEROS (histórico verificado 2026-06-11)

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
   name (the CfgPatches identifier — no dashes; `Mi_Mod`, not `Mi-Mod`). [EXACT — DAYZ_INFRA.md §Layout de drives y mods — Naming de mods]
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

### Mission `init.c`: no extender tipos de módulos anteriores desde el fixture (SP-140)

[IN-GAME CONFIRMED, DayZ 1.29 server diag, 2026-07-30] En este compilador una
misión generada que añadió `modded class` sobre tipos de `4_World` falló con
`Unknown type` tanto para una clase concreta (`SmallStone`) como para una base
(`BuildingBase`). Un incidente anterior reprodujo lo mismo con
`LFPG_NetworkManager`. Los tests offline del texto no detectaron la frontera.

Regla para oráculos de misión: usa un receptor ya compilado que exponga el
contrato bajo prueba. Si necesitas añadir un método, el puente debe vivir en el
mismo módulo/PBO que el tipo y requiere su propio candidato/enmienda; no lo
inyectes como `modded class` desde `init.c`. Mantén llamadas y expresiones
booleanas del fixture en formas vanilla de una línea: el operador `&&` al
comienzo de la línea siguiente produjo `Incompatible parameter` + `Syntax
error`. Antes de gastar pares, ejecuta un único control que exija Module
Game/World/Mission, OnInit y el marcador del oráculo.

Evidencia: `P:\LFPowerGrid_dev\_validation\server-footprint-a9p1-20260730\v1-oracle\a7-attempt3-f02-unknown-type\script-final.log`,
`...\a7-attempt4-f03-cross-module-modded\script-final.log` y
`...\a7-attempt5-f04-boolean-linebreak\script-final.log`. El receptor existente
cerró el control en `...\a7-control\script-final.log`.

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
| Client kicked `0x00020005` | filePatching mismatch | `allowFilePatching = 1;` in serverDZ.cfg [DAYZ_INFRA.md §serverDZ.cfg — allowFilePatching = 1; obligatorio + §BattlEye — códigos de kick más comunes] |
| VPP asks for a password despite a `SuperAdmins.txt` superadmin | `serverDZ.cfg` predates the `vppDisablePassword = 1;` default (generated before 2026-06-09); the existing-cfg path only re-checked `allowFilePatching` | launch now self-heals (appends `vppDisablePassword = 1;` if absent) + restart; or add it manually [session 2026-06-15] |
| Kicked `0x00010002` | mismatched signatures | rebuild PBO; or `verifySignatures=0` (dev cfg already does) [DAYZ_INFRA.md §BattlEye — códigos de kick más comunes] |
| "PlayerConnect will stay disabled" | mission empty / `-mission` not absolute | pass an absolute mission path [DAYZ_INFRA.md §Comandos de invocación canónicos — Server diag] |
| Stuck past loading screen | retail exe + filePatching | use `DayZDiag_x64.exe` [DAYZ_INFRA.md §Diag binary obligatorio para iteración] |
| Server/client no termina | run gestionado aún activo | detener solo el `run_id` exacto con `-Kill -RunId <run_id>`; si falta el ID, declarar `manual_cleanup_required` y no buscar otro proceso que matar |
| Mod not visible in-game | PBO landed outside `!Workshop` | ensure `P:\Mods` is a junction [DAYZ_INFRA.md §Layout de drives y mods] |
| Server boots then dies before UDP bind; RPT/log shows `!!! Serious stream damage detected during load` | half-written CE storage after an unclean server kill — masquerades as a mod bug | wipe (or rename) `<mission>\storage_1` before the next test; the server regenerates a fresh one. SOP: after ANY unclean server kill, wipe it preemptively |
| Mod class missing / `CreateObjectEx` returns null, no RPT error | relative `-mod=@Name` didn't mount | use absolute `!Workshop` paths — `Get-ModString` now does this (see "MOD PATHS MUST BE ABSOLUTE") |
| Mod mounts (CfgPatches in `defines:`) but no script/hook runs | AddonBuilder binarize dropped the `.c` → config-only PBO | build scripts mods with `-packonly` (Invoke-Build auto-detects when no `.p3d`/`.paa`); grep the deployed PBO for a known classname to confirm. [verified 2026-06-03] |
| Script edit doesn't take effect — the same compile error persists across rebuilds even though the source is fixed on disk | AddonBuilder's incremental sync to `P:\temp\<Mod>` served stale source (a changed `.c` not re-copied); filePatching also did not override the PBO's scripts with the loose work-drive copies | Invoke-Build now wipes `P:\temp\<Mod>` before every build; building AddonBuilder by hand, pass `-clear` or delete the temp first. Canonical tell: a compile error citing a line you already fixed and verified. [verified 2026-06-18] |
| `-Build` ran but the deployed car is UNCHANGED in-game (old config/.p3d) | the deployed PBO was **LOCKED** by the running server, so AddonBuilder failed to COPY it — a SILENT `[ERROR] Build failed` at the *copy* step while the script CONTINUES and the gates run on the OLD pbo | detener el run gestionado exacto antes de reconstruir, verificar estado `EXITED`, luego build y relaunch; sin `run_id`, declarar cleanup manual en vez de inferir ownership. SUB_BRZ s28 |
| Kicked `240 ("Game restart required")` 20-60 s after connect | server BE active + client launched bare (`DayZ_x64.exe` never inits BE); `BattlEye = 0;` stops masking it after a BE service hot-update (check mtimes in `Common Files\BattlEye`) | diagnóstico histórico: `DayZ_BE.exe` inicializó correctamente BE en la sesión 2026-06-11; el usuario decide si abre retail externamente y el agente permanece en cuarentena, sin iniciarlo |
| Retail server binds, then dies ~1 min later; `BattlEye initialization failed`, RPT ends "Termination successfully completed" | `BEServer_x64.dll` missing/renamed | Historical observation: the 1.29 dedicated server shut down when BE initialization lacked that DLL. The external owner/user decides and performs any restoration outside the agent workflow; the agent remains in quarantine/read-only [session 2026-06-11] |
| Modal "Compile error … Missing function scope" citing a third-party file at boot | diag exe strict-compiles third-party packs | reportar la incompatibilidad; si el usuario abre retail externamente, aplicar cuarentena y no perseguir el "bug" del tercero |

Logs (where to look): `script.log` = script compile/runtime errors; `*.RPT` = engine errors
(missing assets, malformed configs); `crash_*.log` = handled exceptions, not hard segfaults.
[EXACT — DAYZ_INFRA.md §Cuándo cita el RPT que un script falla]. All under the `_server\profiles\` and `_client\profiles\`
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

## `-ExecutionPolicy Bypass` — quirk intermitente de Codex, NO un bloqueo del host (corregido 2026-07-22)

`[corregido por el usuario 2026-07-22]` La versión previa de esta sección (2026-07-21, escrita por
Codex) afirmaba que la policy de PowerShell del host era `Restricted` y que Microsoft Defender
interrumpía los wrappers con `-ExecutionPolicy Bypass`, y de ahí derivaba un régimen "BLOCKED-
SECURITY / solo managed Python lifecycle". **Era un MALENTENDIDO de Codex sobre lo que dijo el
usuario.** Lo real:

- **Codex (ChatGPT CLI) A VECES dispara SU PROPIA política de seguridad cuando el comando contiene
  `-ExecutionPolicy Bypass`.** Es un rechazo intermitente del AGENTE Codex, no un fallo del host: la
  policy de PowerShell del host NO está en `Restricted` por esto, y Defender NO interrumpe los
  launches.
- Por tanto los lanzadores `.ps1`/`.bat` de este skill **NO están host-bloqueados**: Claude y el
  usuario los ejecutan con normalidad. **No hay "BLOCKED-SECURITY"** por este motivo, ni requisito de
  pasar por un "managed Python lifecycle" para poder lanzar.
- **Única implicación, y SOLO al delegar un launch a Codex**: `-ExecutionPolicy Bypass` puede ser
  rechazado de forma intermitente por Codex → evita ese flag en el comando que le pasas a Codex, o
  deja que el launch lo haga Claude o el usuario.
- **Independiente y vigente**: el protocolo de sesión compartida (lease FIFO + `run_id`,
  §PROTOCOLO DE SESIÓN COMPARTIDA) sigue aplicando para coordinar launch/stop; no tiene relación con
  esto.

(El reporte `P:\Utopia_PC_Suite\reports\2026-07-21-powershell-defender-diagnosis.md` arrastra el
mismo malentendido de Codex — reconciliar o marcar si se cita. No deshabilites Defender ni añadas
exclusiones como "workaround": no procede, porque no era Defender.)

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

## Reglas promovidas del corpus de lecciones (added 2026-07-27)

Promovidas desde `AI/20_Knowledge/lessons-learned.md` para que lleguen por trigger en vez
de depender de que alguien recuerde buscarlas. Cada regla cita su `LL-NNN` de origen;
la entrada completa (síntoma, origen, evidencia) vive allí.

- **LL-118** — Ante una regresión, compara primero el comando de launch, argumentos `-mod`, rutas y entorno con el último run que pasó. Verifica un invariante medible entre ambos runs y consulta los ledgers antes de formular una hipótesis de código.

## Reglas promovidas del corpus de lecciones (added 2026-07-27)

Promovidas desde `AI/20_Knowledge/lessons-learned.md` para que lleguen por trigger en vez
de depender de que alguien recuerde buscarlas. Cada regla cita su `LL-NNN` de origen;
la entrada completa (síntoma, origen, evidencia) vive allí. No quites la cita: el índice
`lessons-index.md` detecta la promoción buscando esa referencia dentro de las skills.

- **LL-196** — Busca `Print()` y `DbgLog` del mod en el `script_*.log` más reciente del profiles correspondiente. Usa el RPT para engine, CE, red, compilación y fallos nativos; no concluyas “el código no corrió” por ausencia de prints en el RPT.
- **LL-197** — Prepara comando, rutas y argumentos antes de adquirir un lease corto; adquiere y usa el token en llamadas adyacentes. Si hubo análisis prolongado, vuelve a adquirir justo antes de la operación bloqueante.
- **LL-198** — En ciclos gestionados, ejecuta `adopt → stop` mientras server y client sigan vivos; pide mantener ambos abiertos entre iteraciones. Si un peer ya murió, usa el cierre degradado documentado y espera el auto-heal antes de relanzar.

## `dayz_test_run` con `build:true` NO construye — y el error que devuelve no lo dice (SP-139, added 2026-07-29)

En esta caja DayZDiag solo arranca por el launcher nativo registrado (SP-085), asi que
`dayz_test_run` es el unico camino. **Su `build:true` esta ROTO**: devuelve el generico
`dayz_test_failed` y **NO escribe el PBO** (hash y mtime del desplegado quedan intactos).
Medido 2026-07-29 en DayZ_MCP, reproducido 2 veces, siempre a los ~16 s.

Por que engana: `dayz_test_failed` es el `except Exception` de `server.py:1101`, que **traga la
causa real** — no es un codigo de error del tool, es "algo lanzo y no se que". Leer el audit
(`%LOCALAPPDATA%\DayZ_MCP\audit\events.jsonl`) tampoco basta aqui: el lease se concede y se
libera limpio, con `runs_released: []` y ningun evento de run. Parece un fallo de build y no
dice donde.

**Biseccion que lo aisla en 3 llamadas** (hazla antes de tocar nada):

| Llamada | Resultado medido | Que descarta |
|---|---|---|
| `preflight: true` | `succeeded` en 1,5 s | launcher, PE, bundle, request y lifecycle estan SANOS |
| `mode: server` sin `build` | `succeeded` en 5,1 s | el launch funciona |
| AddonBuilder a mano | `Build Successful`, exit 0, ~3,4 s | **AddonBuilder tampoco es el culpable** |

Con esas tres, el fallo queda acotado a la ruta de build DEL LIFECYCLE, que es plataforma.

**Workaround verificado y repetible** (build fuera del path publicado, que ademas es lo que pide
el §RELEASE-GRADE BUILD BOUNDARY de esta misma skill):

```powershell
# 1. construir a staging, NUNCA directo al path publicado
AddonBuilder.exe P:\<Mod> <staging> -prefix=<Mod> -temp=P:\temp\<Mod> -clear -packonly
# 2. validar por CONTENIDO antes de publicar (contar anclas, no Contains -- SP-065)
# 3. publicar y verificar por SHA-256, no por mtime
Copy-Item <staging>\<Mod>.pbo P:\Mods\@<Mod>\Addons\<Mod>.pbo -Force
(Get-FileHash 'P:\Mods\@<Mod>\Addons\<Mod>.pbo' -Algorithm SHA256).Hash
# 4. arrancar con dayz_test_run SIN build
```

Dos precondiciones que ya estaban documentadas y aqui son load-bearing: el PBO desplegado queda
**LOCKED mientras el run corre** (para el run antes de publicar), y por SP-078 **los scripts no
hot-loadean en esta instalacion**, asi que cada iteracion de Enforce necesita este ciclo entero.

Origen: DayZ_MCP, gate agrupado de `query_all_players` (2026-07-29). Coste real: ~20 min de
biseccion sobre un error opaco que no nombraba ni el build ni el launch.

**Leccion de metodo asociada**: `LL-224` — el error opaco se acoto bisecando CAPACIDADES (preflight / sin la feature / la herramienta a mano), no leyendo el codigo que lo lanzo. La tabla de arriba ES esa biseccion; reutiliza el patron ante cualquier error de wrapper que no describa nada.

## `dayz_test_run` `extra_mods` REEMPLAZA la lista de extras, no la amplia (SP-323, added 2026-08-22)

Pasar `extra_mods=["@MiMod"]` a `dayz_test_run` **sustituye** los mods extra por esa
lista en vez de anadirse a los que el proyecto trae. Si el bridge `@DayZ_MCP` viajaba
ahi, se cae fuera y **todos los verbos del MCP dejan de funcionar aunque el par
arranque perfectamente**: los dos procesos vivos, respondiendo, con la mision cargada,
y `bridge_status.ready.reason = server_poll_stale` con `last_poll_age_s` congelado en
el valor de la corrida ANTERIOR. Sintoma que despista porque todo lo demas esta sano.

**Comprobacion barata en 5 s**: grepear el script log del servidor por `DayZ_MCP` en la lista de
`defines:` de cualquier modulo, o por la linea `[DayZ-MCP] config loaded ... poll_hz=`; si no esta,
el mod no se cargo. Nombrar SIEMPRE `@DayZ_MCP` explicitamente en `extra_mods`.

Segundo apunte del mismo lanzamiento: **`mode="pair"` no existe** y devuelve
`bad_dayz_test_request` sin decir cuales son validos. Los modos son `server`, `client`
y `all`. El camino fiable sigue siendo `server` -> esperar -> `client` con el mismo
`run_id` (T9-HARNESS-046), no `all`.

Origen: sesion 2026-08-22; un ciclo de arranque completo perdido por esto.

## (added 2026-08-01, HH-60G v19) El RPT del diag BUFFERIZA ~52 KB, y el lifecycle necesita su ventana tras run_not_adoptable

Dos hechos operativos de la nocturna de 6 boots (todos reproducidos varias veces):

1. **Un RPT congelado NO discrimina proceso muerto de buffer sin flush.** El diag escribe el
   RPT a buffer de ~52 KB (esta noche: 5 boots distintos, SIEMPRE ~464 lineas / ~52 KB en el
   momento del fallo, con contenidos distintos). El discriminante real es el **delta de CPU
   del proceso en 30 s** (`Get-Process` dos veces): plano = parado de verdad; creciendo =
   vivo con el log retenido. Ademas `Get-Item`/stat sobre P:\ (OneDrive) puede mentir el
   tamano (927 b reportados con 52 KB reales): leer con `Get-Content` (share-read) y contar.
2. **Tras un `run_not_adoptable` del `dayz_test_stop`, el lifecycle tiene una ventana de
   reconciliacion**: el siguiente `dayz_test_run` devuelve `active_run_exists` aunque los
   procesos esten muertos. Patron que funciono (x3): cerrar los DayZDiag huerfanos por
   proceso, reintentar el stop hasta que devuelva `run_not_active`, y SOLO entonces lanzar
   el run nuevo.

## Estrenar CF sobre una misión con persistencia escrita SIN CF = crash duro del servidor (added 2026-08-02)

Si un proyecto añade **Community Framework** (y con él Dabs/VPP) a una misión cuyo `storage_*` se
escribió en corridas **sin** CF, el servidor arranca, carga la misión y **muere** al leer la
persistencia. Firma exacta (MercedesAMGLF 2026-08-02, `crash_*.log` del server):

```
SCRIPT (E): Virtual Machine Exception
Reason: Failed to read modstorage for entity Type=Rangefinder, Position=<...>
Class: 'CF_ModStorageObject<ItemBase>'
  JM/CF/.../modstorage\cf_modstorageobject.c:142  Function OnStoreLoad_CF
  .../mpmissions/dayzOffline.chernarusplus/init.c:6  Function main
```

**Lo que más despista**: la entidad citada es **vanilla y aleatoria** (aquí un `Rangefinder`), así
que el mensaje apunta a cualquier sitio menos al mod que acabas de añadir. Y el cliente NO falla —
carga bien (`PlayerBase OnStoreLoad SUCCESS`) y se cierra limpio detrás del servidor, lo que refuerza
la lectura equivocada de «problema del cliente».

**Causa**: las misiones `dayzOffline.*` del DayZServer se COMPARTEN entre proyectos. Un proyecto que
corre sin CF persiste entidades sin los datos de `modstorage` de CF; el siguiente que sí lleva CF los
lee y revienta.

**Remedio** (convención ya establecida en la propia carpeta de la misión, con 4 ocurrencias:
`storage_1_corrupt-modstorage-20260720 / 0728 / 0729 / 0802`): con los procesos parados, **renombrar**
`storage_1` → `storage_1_corrupt-modstorage-<YYYYMMDD>` y dejar que el server regenere. Es rename, no
borrado, así que es reversible — pero **volver a arrancar con CF sobre ese storage vuelve a crashear**:
lo que se conserva es la evidencia, no un estado al que puedas volver con CF puesto.

**Consecuencia que hay que decirle al usuario ANTES**: mundo y personaje se resetean.

Cross-ref `SP-062` (misma acción — renombrar `storage_1` — por un motivo distinto: entidades
persistidas que re-disparan `EEInit`). Regla combinada: **cualquier cambio en el conjunto de mods
que altere quién escribe `modstorage` exige storage limpio**, igual que un boot de medición.

### La trampa es BIDIRECCIONAL y la regla se decide al LANZAR (medido 2026-08-21)

La direccion inversa tambien muerde, y mas rapido: un server **sin** CF que arranca sobre un
`storage_1` escrito **con** CF entra en tormenta de VME — `!!! Scripted variables corrupted upon
"<entidad>"` por CADA entidad persistida (medido: **15.688 en ~3 min**, `-mod=@DayZ_MCP` a secas
sobre un storage recien guardado por un server con CF) — y puede morir a mitad de escritura
dejando el storage PEOR: las entidades reescritas pierden su modstorage de CF, y el siguiente
server que SI lleva CF crashea con la firma de arriba. Asi se encadenan los cruces:
server-sin-CF reescribe -> server-con-CF crashea -> rotacion.

**Regla al lanzar sobre la mision compartida**: o el `-mod=` lleva CF, o se rota `storage_1`
ANTES de levantar. No hay tercera opcion estable — el storage queda "CF-flavored" en cuanto un
server con CF guarda una vez. Rotar = renombrar con motivo
(`storage_1.bak-<YYYYMMDD>-<HHMM>-<motivo>`, con los procesos parados; ocurrencias 2026-08-21:
`-1605-modstorage-corrupt`, `-1610-cfless-storm`). Que storage toca rotar lo dice el propio RPT
del server: linea `[StorageDirs] :: Selected storage directory:`.

## (added 2026-08-12, LFHeli celda COM/pivot) Celda in-game AUTOMATIZADA sin piloto: los 4 muros medidos y sus salidas

Once celdas de iteración en un día para dejar una celda automatizada verde (stack + get-in +
motor + sondas + parser, ~5 min). Los cuatro muros, medidos con discriminantes, para no volver
a pagarlos:

1. **DayZDiag NO define DEVELOPER para scripts (SÍ define DIAG y DIAG_DEVELOPER)** — medido con
   telemetría de defines en cliente conectado. Todo mecanismo vanilla bajo `#ifdef DEVELOPER`
   (p.ej. `SetGetInVehicleDebug`/`TryGetInVehicleDebug`, playerbase.c:3270-3295) NO EXISTE en
   diag. Gatea el código de test por parámetro de línea de comandos (`CommandlineGetParam`,
   game.c:660) o por `#ifdef DIAG`, nunca por DEVELOPER.
2. **Get-in automatizado en MP: `StartCommand_Vehicle` directo desde el cliente sienta un
   FANTASMA local** (own=true, HUD activa) pero el server NUNCA registra el crew (crew0=false,
   consumed=0, ObtainState mudo). La vía que funciona: inyectar la ACCIÓN real —
   `ActionManagerClient.PerformActionStart(GetAction(ActionGetInTransport), target, null)`
   (actionmanagerclient.c:762; en MP entra por ActionStart, el flujo sincronizado que el server
   espeja). El componentIndex del target se obtiene iterando `CrewPositionIndex(c)` hasta que
   devuelva el asiento buscado (transport.c:116). El éxito se observa con `GetCommand_Vehicle()`
   al tick siguiente (con retry), no marcando done al inyectar. OJO: `ActionCondition` es
   protected — no se puede pre-validar desde fuera; el manager valida en ambos lados.

   **El marco que reconcilia esto con SP-295** (medido contra el arbol vanilla, 2026-08-18):
   la pertenencia al crew y el comando de vehiculo son DOS cosas distintas, y solo la accion
   real produce las dos. El crew es estado NATIVO del engine, no un netsync de script:
   `Transport` registra una sola variable (`m_EngineZoneReceivedHit`, transport.c:73) y
   `CrewMember`/`CrewDriver` son `proto native` (transport.c:111-128), legibles desde cualquier
   cliente — por eso el cliente que quiere subir puede rechazar un asiento ya ocupado
   (actiongetintransport.c:57-60). El `HumanCommandVehicle`, en cambio, lo crea
   `StartCommand_Vehicle` en LA MAQUINA que lo llama, y en los 2.805 ficheros del arbol hay
   exactamente tres call-sites: la propia accion (actiongetintransport.c:91), la reanudacion
   tras inconsciente via `m_TransportCache` (dayzplayerimplement.c:2376) y un debug bajo
   `#ifdef DEVELOPER` (playerbase.c:3287). **Ninguno arranca el comando al enterarse por red de
   que uno ya va sentado.** De ahi salen las dos caras del mismo hecho: llamar
   `StartCommand_Vehicle` a pelo desde el cliente da comando SIN crew de server (el fantasma de
   arriba); sentar a alguien por script desde el servidor da crew SIN comando local, y entonces
   cualquier `ActionCondition` que exija ir sentado NUNCA se cumple, porque piden
   `GetCommand_Vehicle()` y no `CrewMember` — asi lo hacen get-out
   (actiongetouttransport.c:68-74) y arrancar/parar motor (actionstartengine.c:26-37). Ojo con
   `IsInVehicle()`: acepta las dos vias (comando O parent Transport,
   dayzplayerimplement.c:465-468), asi que no sirve para distinguirlas.
3. **Un body DORMIDO rechaza la acción get-in inyectada** (sleep gate de PARKED). Si el mod
   duerme el vehículo en reposo, la celda debe DESPERTARLO antes del get-in — lo más simple:
   arrancar el motor server-side desde la misión de test (`EngineStart`, car.c:244) NADA MÁS
   spawnear, no al detectar crew. Además, sin motor/simulación el canal OwnerState no fluye
   (ObtainState/RewindState callados) aunque el player esté sentado.
4. **El compile gate real de Enforce es el ARRANQUE del stack** (ningún check offline ve
   visibilidad de métodos, p.ej. protected). La celda debe buscar `Compile error` / `Can't
   compile` en el script log del server ANTES de esperar fases posteriores, y tratar el
   message-box del cliente como cuelgue (timeout de fase).

Patrón de orquestador que funcionó: wrapper con FASES nombradas (BOOT-spawn / BOOT-log /
COMPILE / CONNECT / GETIN / sondas / SETTLE / teardown / PARSE), cada una con veredicto
PASS/FAIL y timeout propio; los logs se copian a evidence AUNQUE una fase falle; el teardown
mata SOLO los PIDs que la celda lanzó. Referencia completa:
`LFHeli_dev\tools\run_celda_compivot.ps1` + `evidence-2026-08-12-offset\` (11 celdas con la
causa de cada fallo). Cross-ref: sesión 2026-08-12-lfheli-oh1-com-pivot-medido-recenter-verde.

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

## Validez de una corrida automatizada: preflight, ciclo y evidencia

Una celda solo emite `PASS` si demuestra que arrancó en el modo previsto, cubrió la transición completa y produjo la evidencia que el veredicto consume. Aplica este contrato antes de gastar una tanda:

1. **Preflight por mecanismo y modo (LL-284, LL-307).** Documenta cada guard como `mecanismo protegido → modos afectados` y codifica la rama: un guard exclusivo de cliente aborta con cliente y solo avisa en `-NoClient`, sin bypass manual. En una caja con varios stacks, una celda desatendida con cliente tampoco está aislada del teclado: censa los otros `DayZDiag` y mods activos, registra PID/mods y riesgo de foco, y usa un guard DIAG exclusivo de test para rechazar las acciones humanas que cambiarían el estado mientras el guion esté activo. La automatización conserva una ruta programática separada. Si no puedes demostrar el aislamiento, el resultado es `SETUP_FAIL`.

2. **Identidad y separación de boots (LL-258, LL-260).** En una tanda que relanza el cliente, deja un cooldown conservador de 60 s desde el cierre anterior hasta el siguiente arranque; una muerte nativa durante ese arranque es `SETUP_FAIL`, no una regresión del mod. El cooldown no aplica a un one-shot realmente aislado porque no encadena otro cliente. Al empaquetar evidencia, no elijas el fichero por mtime aparente: los artefactos de producto se nombran en UTC y los RPT/mtimes usan hora local. Cruza el boot-id o marcador interno con el incidente del ledger; su timestamp manda sobre el mtime. Si faltan los marcadores esperados del boot, rechaza el bundle.

3. **Recorrido completo y compile gate bilateral (LL-310, LL-312).** Dibuja cada transición crítica como `entrada → estado observable → salida → postestado` y ejecútala por software. Un autotest que solo entra tiene cobertura incompleta; busca primero el disparador de cierre entre watchers, cancelaciones y timeouts ya existentes. Extiende el gate de :811-814 (server) al log del cliente: escanea los logs de script de ambos peers por `Compile error` / `Can't compile` antes de esperar marcadores funcionales. `Cliente muerto / servidor vivo + Can't compile` es un fallo de compilación de código solo-cliente, no un timeout ni una regresión de runtime. El lint offline no acredita visibilidad `private`/`protected`; la compilación real de ambos peers es la autoridad.

4. **Cierre acorde con la medida (LL-277).** SP-237 ("copiar/verificar antes de matar") conserva evidencia ya emitida, pero no acredita métricas que nacen al salir. Para informes de fugas, flushes, destructores o hooks finales, solicita cierre ordenado, espera un marcador explícito de que el informe o hook ejecutó y solo entonces recoge el resultado. Un kill forzado produce `SETUP_FAIL` para toda métrica de salida y también impide verificar un arreglo que vive en ese hook. "No apareció el problema" nunca equivale a `PASS` si la comprobación no llegó a ejecutarse.


## Tres trampas medidas en el ciclo LFPG S2-B (added 2026-08-29)

Las tres costaron tiempo la misma noche, con el puente MCP v10 sano. Ninguna era del mod.

1. **`action_use` empareja por NOMBRE DE CLASE, no por el texto de la accion.** El bridge recorre
   `ActionManagerBase.m_ActionsArray` y compara `candidate.Type().ToString() == wantedAction`
   (`DayZ_MCP/scripts/5_Mission/MCPClientBridge.c:1806`). Pasar el texto visible -el que resuelve
   `m_Text` desde el stringtable- devuelve `action_not_found` aunque la accion este disponible en
   pantalla. La trampa se agrava con el cliente en otro idioma, porque invita a probar la traduccion:
   el idioma es irrelevante, la llave es la clase. Saca el nombre del `class X : ActionInteractBase`
   del propio mod, nunca del stringtable.

2. **El gate de Steam de :99-103 solo AVISA, y ademas no corre por la via del MCP.** Esta
   implementado en `templates/dayz-test.ps1:478-484`, que es el lanzador de ESTA skill;
   `dayz_test_run` del MCP no pasa por ahi, asi que en la ruta que usan las sesiones con MCP el
   check sencillamente no existe. Variante nueva observada 2026-08-29: `pid=0` **y** `ActiveUser=0`
   con **cero procesos de Steam vivos** (la firma ya documentada era pid poblado / ActiveUser=0).
   Mismo desenlace: RPT del cliente cortado justo tras el argv, sin una sola linea de script, y
   servidor intacto porque no usa Steam. Comprobar la clave antes de lanzar cliente cuesta 10 s.

3. **La CUENTA de Steam activa decide QUE PERSONAJE carga.** (Corregido el mismo dia: ver la
   refutacion al final del punto — el estado del MOD no depende de la cuenta.) Reiniciar
   Steam puede devolver OTRA cuenta sin avisar. Medido 2026-08-29: el cliente de las 03:55 entro
   como `76561197995575711`, con su personaje persistido en el sitio de pruebas; el de las 04:17,
   tras el reinicio, como `76561198141021937`, con personaje fresco en la costa. El sitio aparecia
   sin sus dispositivos y **parecia un fallo de persistencia del mod**. La clave del registro lo
   dice sin abrir el juego: `ActiveUser = steamID64 - 76561197960265728`. Corroborable desde fuera:
   AddonBuilder imprime `Steam_SetMinidumpSteamID:  Caching Steam ID:  <steamID64>` en su salida.
   Si el ciclo depende del personaje persistido, fija la CUENTA en el pre-flight, no solo el pid.

   **REFUTACION MEDIDA EL MISMO DIA, y la distincion es fina y cara.** Volver a la cuenta correcta
   devuelve el PERSONAJE (spawn en el sitio exacto, sin teleport) pero NO el estado del mod. Con
   `...711` el server seguia diciendo `[VanillaWires] Loaded 0 entries from 0` y
   `RebuildTrackedDevices: tracking 0 wired devices`: cero cables en las DOS cuentas. O sea que un
   sitio de pruebas vacio NO se explica por la cuenta, y quien lo asuma perdera el tiempo cambiando
   de login en vez de montar la fixture. La regla util es: la cuenta explica DONDE aparece tu
   personaje; el estado del mod se monta o no esta.


## El aviso de `modstorage` lleva 12 fallos: conviertelo en preflight, no en parrafo (added 2026-08-29)

La seccion "Estrenar CF sobre una mision con persistencia escrita SIN CF = crash duro del
servidor" (added 2026-08-02) es correcta y **ha vuelto a fallar**. Contado hoy host-direct en la
carpeta de la mision compartida `DayZServer\mpmissions\dayzOffline.chernarusplus`:

    12 carpetas storage_1*corrupt-modstorage*, del 2026-07-20 al 2026-08-29,
    de al menos 5 proyectos distintos (subbrz, amglf, gunracks, nocf-gate, lfquad2).

12 ocurrencias en 40 dias. Una nota que se ha saltado 12 veces no se arregla leyendola con mas
cuidado la 13a: la precondicion es MECANICA y se esta pidiendo a mano.

**Regla operativa: la persistencia pertenece al juego de mods que la escribio.** Antes de lanzar
con un `-mod=` distinto al de la corrida anterior sobre esa misma mision, rota. No es "si
sospechas": es **siempre que cambie la lista**, y anadir UN mod ya la cambia.

    # con los procesos parados
    $m = "<mision>"
    Rename-Item -LiteralPath "$m\storage_1" -NewName "storage_1_corrupt-modstorage-$(Get-Date -f yyyyMMdd)_<proyecto>"

Rename, no borrado: es reversible. Pero volver a arrancar con CF sobre ese storage vuelve a
crashear, asi que lo que se conserva es la evidencia, no un estado al que puedas volver.

**Aviso que hay que dar ANTES de rotar**: mundo y personaje de esa mision se resetean.

Y el modo de fallo de proceso que lo dejo pasar esta vez, que es el que hay que saber reconocer:
**la precondicion se comprobo contra el plan A, y el plan cambio.** Iba a usar una copia nueva y
propia de la mision, asi que "mision limpia, sin storage" era CIERTO cuando lo despache. Entonces
el tool rechazo la ruta absoluta --`dayz_test_run` valida el campo `mission` contra
`_MISSION_ALIASES` y solo acepta `chernarus|livonia|sakhal`, ver `dayz_mcp\dayz_test_tool.py:135`--
y me empujo a la mision COMPARTIDA. El descarte viajo con el plan viejo y nadie lo reevaluo.

**Un descarte se apellida con el plan que lo justifico: si cambia la ruta, las precondiciones que
despejaste vuelven a estar sin comprobar.** Vale para cualquier caveat de esta skill, no solo
para este.


## Tras un reinicio, `P:` NO existe -- y FileBank empaqueta el vacio con exit 0 (added 2026-08-29)

`P:` es un `subst`, no un enlace en disco: **no sobrevive a un reinicio**, y menos a una caida
dura. Todo lo que las herramientas BI y el launcher sellado tocan cuelga de ahi
(`P:\Mods`, `P:\<Mod>`, `P:\<Mod>_dev\_server\profiles`, `P:\scripts`, `P:\DZ`).

Lo caro no es que falte: es **como falla**. Medido hoy, con `P:` ausente:

    FileBank.exe -property prefix=<Mod> -exclude <lst> -dst <staging> P:\<Mod>
    exit=0
    <staging>\<Mod>.pbo   ->   79 bytes

**Exit 0 y un PBO de 79 bytes.** Ni un mensaje. Es el mismo modo de fallo que el
`Build failed` con exit 0 de AddonBuilder que ya documenta esta skill: la herramienta BI
considera que empaquetar cero ficheros es un exito.

**Preflight, dos lineas, antes de cualquier build o launch:**

    Test-Path -LiteralPath "P:\"          # si False:
    subst P: "<dayz-projects>"

Y comprueba las anclas, no solo la raiz: `P:\<Mod>\config.cpp`, `P:\Mods\@<Mod>\Addons`,
`P:\scripts`, `P:\DZ`. **Valida el PBO por TAMANO y por numero de entradas** antes de
publicarlo; un paquete de tres cifras de bytes es la firma de esto.

## El `pid` de Steam en el registro puede estar MUERTO, y la comprobacion de esta skill no lo veia (added 2026-08-29)

Esta skill ya pide que `HKCU\Software\Valve\Steam\ActiveProcess` tenga `pid != 0` y
`ActiveUser != 0`. **Necesario, pero NO suficiente: un `pid` distinto de cero puede ser un pid
muerto.** Tras una caida dura del PC la clave conserva el pid del Steam anterior; Steam
arranca de nuevo con OTRO pid y **no siempre reescribe la clave a tiempo**. DayZ lee ese pid,
va a buscar ese proceso, no lo encuentra, y muere.

Medido hoy: registro `pid=25484`, `steam.exe` vivo `pid=13856`. La comprobacion "no es cero"
daba VERDE sobre un sistema roto. La pregunta correcta no es "¿es cero?" sino **"¿existe ese
proceso?"**:

    $k  = Get-ItemProperty 'HKCU:\Software\Valve\Steam\ActiveProcess'
    $st = Get-Process -Name steam -ErrorAction SilentlyContinue
    $ok = $st -and ($st.Id -contains [int]$k.pid) -and $k.ActiveUser -ne 0

**Firma del fallo, para reconocerla sin adivinar** (tres reproducciones identicas):

| senal | valor |
|---|---|
| dialogo modal | `unable to locate running instance of Steam` |
| excepcion del volcado | `0x80000003` **BREAKPOINT**, misma direccion exacta cada vez |
| CPU del proceso cliente | **0 s** -- vivo pero parado en seco |
| RPT del cliente | congelado en **847 B**, solo la cabecera |
| modulos cargados | ~69, ultimos los de Steam (`gameoverlayrenderer64.dll`, `tier0_s64.dll`) |

`0x80000003` **no es un crash**: es un `int 3` deliberado del exe diag al sacar su dialogo. Por
eso el proceso queda vivo con 0 CPU en vez de desaparecer, y por eso no hay evento de fallo en
el visor de sucesos de Windows: DayZ escribe su propio `.mdmp` y se planta.

**Remedio** (conserva el login, ~20 s): `steam.exe -shutdown`, esperar a que el proceso muera,
relanzar, y **esperar a que la clave vuelva a casar con un proceso vivo** antes de lanzar el
cliente. No basta con que Steam "este abierto".

**Como leer el volcado sin depurador**, que es lo que corto el bucle de hipotesis: un minidump
trae `MINIDUMP_EXCEPTION_STREAM` (tipo 6) y `MODULE_LIST` (tipo 4); con ~60 lineas de Python se
saca el codigo de excepcion y el modulo que contiene `ExceptionAddress`. Antes de teorizar
sobre drivers o sobre el mod, **lee el instrumento**: aqui `0x80000003` descarto de un golpe
"crash de render" y "mod corrupto", que eran las dos hipotesis en las que ya se habian gastado
dos ciclos de arranque.

**Y el corolario de metodo, que vale para cualquier fallo tras tocar el mod:** antes de buscar
la causa en tu cambio, **despliega el artefacto ANTERIOR y reproduce**. Aqui el PBO
pre-cirugia fallaba identico, lo que exonero el trabajo en un solo ciclo y mando a buscar en
el entorno. Un A/B con el binario viejo cuesta lo mismo que una hipotesis, y a diferencia de
ella, decide.


## Parches medidos del ciclo de test promovidos el 2026-08-31

Las reglas siguientes se aplican sobre el estado posterior a la cosecha del 2026-08-29. Cuando
corrigen una sección histórica, la corrección de este bloque manda; la sección anterior se conserva
como evidencia de la evolución medida.

### Build mixto: `-include` filtra el sync, no define el PBO (SP-083 / SP-168, corregidos por SP-177)

Las afirmaciones históricas de :125-155 necesitan dos límites. AddonBuilder usa una ruta nativa
para `config.cpp`, `.p3d` y los `.rvmat` descubiertos desde caras, y otra ruta de sincronización
ordinaria para `.c`, `.paa`, `.ogg`, `.layout` y `.csv`. `-include` gobierna esta segunda ruta; no
es el manifiesto final. Un `.rvmat` citado solo desde `config.cpp` todavía puede faltar.

El template publicado de esta skill no pasa hoy una lista en
`templates/dayz-test.ps1:531-534`. Por tanto, para un mod mixto no acredites el `-Build` genérico:
usa un build que pase una lista adecuada para el payload ordinario y valida después las entradas
reales del PBO. Exige al menos igualdad de rutas y conteos para los `.c` del fuente, y comprueba por
separado los materiales citados por config. No añadas `*.rvmat` a una lista y lo tomes como prueba.
La semántica de build autoritativa y el gate completo viven en
`skills/dayz-pbo-build/SKILL.md`, sección SP-177.

### Logs vivos y cierre de un run liberado (SP-077)

DayZDiag mantiene abiertos el RPT y `script_*.log`. `Get-Content` o `ReadAllText` pueden fallar con
`IOException` durante todo un waiter. Para monitorizar un peer vivo, abre con compartición explícita:

```powershell
$fs = [IO.File]::Open($path, [IO.FileMode]::Open, [IO.FileAccess]::Read,
                     [IO.FileShare]::ReadWrite)
try { $text = [IO.StreamReader]::new($fs).ReadToEnd() } finally { $fs.Dispose() }
```

En lifecycle gestionado, conserva el `run_id` y usa las herramientas públicas. Si una operación de
bajo nivel encuentra un run `released`, la secuencia es `adopt` y después `stop`; `stop` solo puede
devolver `run_not_adopted`. Si otra sesión ya lo limpió, `run_not_adoptable` + cero procesos del run
+ RPT terminado en `Termination successfully completed` describe cierre ordenado, no crash.

### Binarize antes de gastar un boot (SP-125)

Todo `.p3d` candidato necesita un veredicto PASS de binarize antes de entrar en un PBO, incluso si
el empaquetado final usa `-packonly`: packonly conserva el MLOD, pero no hace que el motor acepte un
modelo que binarize rechaza. Agrupa los modelos del cambio y paga este gate una vez antes del build;
el censo post-build sigue siendo obligatorio y prueba otra frontera.

### Identidad offline entre fuente y PBO desplegado (SP-144)

Antes de planificar por citas `path:line` o gastar un ciclo in-game, prueba qué bytes va a compilar
el juego:

1. Extrae el PBO desplegado a un scratch con un extractor que expanda correctamente las entradas
   `Cprs`; valida primero el extractor contra una baseline conocida.
2. Calcula SHA-256 del fichero dentro del PBO y del fichero fuente citado por el plan.
3. Exige igualdad para cada fichero que sostiene el cambio. Un mtime reciente del contenedor no
   acredita sus entradas.

Si los hashes difieren, el plan está citando un árbol distinto del runtime. Reconstruye y repite el
gate antes de diagnosticar lógica. Este control offline es el discriminador barato que complementa
el `srcprobe` de SP-078.

### El guard de deploy protege el destino, no congela toda la caja (SP-150)

En una caja compartida, «cero procesos DayZ» es demasiado amplio. Antes de reemplazar un PBO exige
las dos condiciones que protegen ese destino:

1. Ningún proceso vivo referencia el mod objetivo en su `CommandLine`/modline, medido con
   `Win32_Process`; el nombre del ejecutable no basta.
2. El PBO destino admite apertura exclusiva con `FileShare.None`.

Registra el hash baseline justo antes de copiar y verifica el hash publicado después. Si una
condición falla, no despliegues. Si ambas pasan, no cierres procesos de otras líneas que cargan otros
mods.

### Quoting y triage de un Diag que no llega a escribir logs (SP-167)

Para argumentos `name=value` con espacios, entrecomilla el token entero:

```text
-profiles="<profiles-path>"      # NO: comillas solo alrededor del valor
"-profiles=<profiles-path>"      # SÍ: un token completo
```

Aplica el mismo patrón a `-config=`, `-mission=` y `-mod=`. En Windows PowerShell 5.1, pasar un
array a `Start-Process -ArgumentList` no garantiza el quoting de cada elemento; no uses ese
resultado como prueba del argv recibido. La ruta gestionada de esta skill transporta un array
estructurado y sigue siendo la vía normal.

Para un cuelgue con 0 CPU y sin RPT, ejecuta primero el control mínimo autorizado
`DayZDiag_x64.exe -server`, sin otros argumentos, y añade uno por uno. En la medida que fundó esta
regla, ~53 módulos era «aún no llegó a UI» y 69-78 era arranque real; usa el delta como firma del
build medido, no como constante universal. Obtén el argv real con `Win32_Process`: la línea truncada
de cabecera del RPT no lo representa de forma fiable.

### Cliente pelado: separar argumento, ruta nativa y mod (SP-174)

Ante un cliente que no arranca, decide por forma antes de tocar el mod:

- **Vivo, 0 CPU, sin RPT ni dump:** aplica el control mínimo y la bisección de argumentos anterior.
- **Muere con RPT de solo cabecera + `ErrorMessage_*.mdmp`, sin `crash_*.log`, incluso sin mods:**
  lanza el servidor del mismo build. Servidor estable con RPT grande y cliente pelado que cae apunta
  a la ruta nativa/gráfica del cliente. Confirma con el perfil de otro proyecto en la misma ventana.
- **Solo falla al añadir `-mod`:** entonces sí abre la investigación del mod y su orden de carga.

«Se reinició» también se mide: compara `Win32_OperatingSystem.LastBootUpTime` y comprueba que no
sobreviva un proceso anterior al instante declarado. Fast Startup puede conservar el kernel después
de apagar; un reinicio completo cambia ese dato.

### Spawn diagnóstico sin depender de la UI de VPP (SP-210, alcance de un solo uso)

Si la UI administrativa bloquea un diagnóstico, una misión privada puede usar
`CustomMission.InvokeOnConnect` para crear una fixture una vez por boot, a distancia fija del
jugador, con `CreateObjectEx(..., ECE_PLACE_ON_SURFACE)`. Usa un booleano one-shot y storage limpio.

Es un fallback desechable, no infraestructura de celda. La regla portable de :383-392 sigue
mandando: cualquier spawner, watcher o control que deba sobrevivir al proyecto vive dentro del mod,
gated por DIAG y por un parámetro explícito.

### Parsers: primero extraer el payload real de `Print` (SP-234)

Una variable string llega al script log con una forma equivalente a:

```text
SCRIPT       : string <var> = '<payload>'
```

La comilla simple de cierre queda pegada al último campo. Extrae primero lo comprendido entre
`= '` y la última comilla; solo después tokeniza números y campos. Un gate de logs incluye siempre
fixtures literales copiadas de un log real, además de casos sintéticos, y contrafixtures con wrapper
truncado. Un self-test que nunca consumió una línea real solo valida el parser imaginado.

### Teleport y readiness antes de inyectar una acción (SP-235)

Para teletransportar al jugador en un harness usa X/Z del punto censado y
`Y = GetGame().SurfaceY(x, z)`. La Y de un memory point puede dejarlo en
`ACID_Human_Fall`; durante Fall, una acción inyectada puede abortar sin error mientras el servidor ya
reservó el asiento.

Antes de gastar un intento, exige un command ID admitido, ninguna acción en curso,
`CanStoreInputUserData()` y `ActionBase.Can(...)`. Después observa la transición real; no marques
éxito al enviar la acción. Un desync `server=Move, client=Fall` apunta primero al placement.

### Servidor retail headless como término de paridad (SP-242)

La obligación de `DayZDiag_x64.exe` en :89-90 está acotada a la iteración con `-filePatching` y al
launcher oficial de esta skill. Un `DayZServer_x64.exe` retail headless puede cargar PBOs con
`-mod`, compilar Enforce y ejecutar `RestApi` saliente sin ocupar la sesión Steam del cliente.
La medida observó defines `RELEASE, SERVER, NO_GUI, SERVER_FOR_WINDOWS` y polling HTTP real.

Úsalo como segundo término de un gate diag↔retail cuando el comportamiento server-side pueda
depender de `RELEASE` o de APIs developer-only. No sustituye al cliente para captura visual ni para
verbos que requieren un jugador conectado. Este servidor queda fuera del lifecycle oficial: solo
un runner probe-gated que posea su PID exacto puede iniciarlo y cerrarlo.

### Celdas multi-peer: reloj, replay y sondas bilaterales (SP-276 / SP-278)

Para un fallo de salida o desync, instrumenta el callback equivalente a `OnDriverExit` en ambos
peers y emite en una sola ventana `playerPos`, `vehiclePos`, `crewEntryWS` y sus distancias. Alinea
los relojes cliente/servidor con pares del mismo evento; no compares timestamps crudos de peers.

En una serie del owner con rewind/replay, varias muestras pueden compartir el mismo `t`. Conserva la
primera muestra por tick —o colapsa un intervalo documentado menor de 20 ms— antes de evaluar los
flancos. Convierte los eventos del servidor al reloj del owner, usa la serie autoritativa como
oráculo principal y el owner como secundaria, y re-ejecuta el histórico después de cambiar el
parser.

El bridge no inyecta valores arbitrarios en `UAInput`. Si el mod neutraliza `CarController` y
consume ejes propios, una celda necesita un guion DIAG en el owner antes de `WriteToMove`; esta rama
solo se promueve para el mod cuando una corrida in-game demuestre que pilota.

### Contrato de una celda scriptada repetible (SP-279)

- Spawnea la fixture en un sitio fijo conocido y coloca al jugador en un offset fijo sobre
  `SurfaceY`; un spawn aleatorio convierte obstáculos y puertas en ruido de entorno.
- Después de una salida, rearma server-side el placement tras un cooldown con el jugador a pie.
  La reentrada forma parte del test: una pose fantasma en cliente invalida reach y `Can()`.
- `forces-off`, `clamp-abort`, `no-probes`, `no-pilot` y `not-owner` son **INCONCLUSO** y admiten
  retries acotados. Un timeout después de satisfacer las precondiciones es **FAIL**.
- El guion ejecuta; no adjudica. Sus gates son los mismos del preregistro. Detecta «posado» por AGL
  sostenido o, mejor, por estado autoritativo, no por una velocidad owner aislada.

### Aislamiento, settle y sondas de efecto en celdas (SP-285)

Mientras el piloto scriptado está activo, un guard DIAG debe rechazar en `ActionCondition` las
acciones humanas que rompen la celda, pero conservar una ruta programática separada. El settle se
decide por estado autoritativo espejado (`GROUND_READY`/`PARKED`) y usa AGL solo como respaldo; el
owner puede seguir rebotando después de que la autoridad esté posada.

Instrumenta el callback del síntoma en ambos peers con una sonda gated y pila. En cliente imprime la
pila línea a línea para evitar truncado y no llames APIs cuya validez sea solo server-side. Al
arrancar, el runner censa otros DayZDiag vivos con PID, modline y puerto; si 2302 pertenece a otra
sesión, elige un puerto acreditado distinto. Esto extiende el preflight de :976 sin tocar los peers
ajenos.

### Quien abre un proceso manual también lo cierra (SP-344)

Los runs gestionados se cierran por su `run_id`. Para un proceso manual autorizado fuera del MCP,
el agente que lo abrió conserva PID y `CommandLine`, solicita cierre ordenado con
`CloseMainWindow()`, espera 8-10 s y usa `Stop-Process -Id <pid>` solo como fallback exacto. Nunca
selecciona por nombre de ejecutable ni toca un peer de otra sesión.

Si la ventana la abrió el usuario y está jugando, el cierre sigue siendo suyo por la UI. Si la abrió
el agente, no se convierte al usuario en operador de limpieza; pedir continuar el ciclo autoriza a
cerrar solo esos procesos propios.


## Dos trampas del ciclo build-deploy-test que ponen verde una corrida inútil (added 2026-08-31)

Las dos medidas el 2026-08-31 cerrando un gate de motor. Ninguna da error; las dos dejan que
saques conclusiones de una corrida que no probó lo que crees.

### 1. `DSSignFile` devuelve 0 después de un build fallido — y firma el PBO VIEJO

`dayz_test_run` (y cualquier cliente/servidor vivo) deja el PBO **bloqueado**. Reconstruir con
AddonBuilder mientras la corrida está en pie da `[ERROR]: Build failed`, y si el script encadena
la firma, `DSSignFile` sale con **`EXIT=0`** tan contento: ha firmado el binario anterior.

Encadenado en un `.ps1`, el resultado es un `SIGN=0` que parece confirmar el despliegue.

**Parar la corrida antes de reconstruir**, y verificar el resultado por **la tabla del PBO contra
el tamaño del fuente**, nunca por exit codes:

```
scripts\4_World\LFG10_Probe.c    3579     <- y en disco: 3579
scripts\5_Mission\LFG10_Driver.c 4756     <- y en disco: 4756
```

Es la misma doctrina que ya está en `DAYZ_INFRA.md` («el veredicto de un build es la tabla de
ficheros del PBO, no el exit code»), extendida a la firma: **el exit code de `DSSignFile` no dice
nada sobre si el build entró.**

### 2. La persistencia devuelve el sujeto como lo dejó la corrida anterior

Un experimento que mide el estado de una entidad (salud, humedad, cantidad, temperatura) **no
puede fiarse del loadout de spawn**. Medido: el personaje volvió con la prenda en `wetlevel=4
hplevel=2`, exactamente donde la había dejado la corrida anterior, así que el control de la corrida
nueva arrancaba **ya pasado el umbral que tenía que cruzar** — y habría dado «el control no
dispara» siendo falso.

El probe **normaliza el sujeto** antes de medir nada (`SetWet(0)`, `SetHealthLevel(0)`, lo que
aplique) y lo registra en el log. Y si hay una parte cliente que depende de ese estado, se ata a
**la condición, no a un temporizador**: esperar a observar el sujeto ya normalizado, porque la
propia normalización es un cambio de estado que puede pisar lo que ibas a medir.

### Bonus: un probe desechable no necesita darse de alta como proyecto del MCP

`P:\Mods` es `mod_root` de los diez proyectos aprobados en `request-policy.json`, y
`dayz_test_tool._valid_public_mod` acepta cualquier carpeta relativa dentro de esos roots. Así que:

```
dayz_test_run(project="DayZ_MCP", mode="all", extra_mods=["@MiProbe"])
```

sale con el bridge entero (`capture_screenshot`, `camera_set`, `query_player_state`, `wait_for`
sobre `log_matches`) **más** tu probe, sin tocar la política sellada ni reconstruirla con
`build_native_launcher.py`.
