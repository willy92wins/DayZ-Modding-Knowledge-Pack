# Linux / Proton findings (2026-11-03) — notes for making the pack and dayz-mcp work on Linux

Status: **raw findings**; sections 1–4 are the first pass, section 5 records what was built from them. Nothing here is registered in
`sources/claims.json`; promote individual items through the normal workflow once they are re-checked.

Machine: Debian testing, Python 3.14, Steam native, GE-Proton11-1, native Linux `DayZServer`
(app 223350), DayZ client (app 221100) under Proton. dayz-mcp at commit `0107c0c` (2026-11-03).

## 1. Structural facts about the Linux setup

- **DayZ Tools (830640) and DayZ (221100) are different Steam apps, so each gets its own Proton prefix.**
  The DayZ Tools themselves run fine under Proton, AddonBuilder included. What breaks is every tool step
  that needs **game data**: the tools prefix does not know where the game is, so that data has to be
  linked into it. Observed on this machine: the game prefix has
  `HKLM\Software\Wow6432Node\Bohemia Interactive\DayZ` `"main"="S:\steamapps\common\DayZ"`, while in the
  tools prefix (`compatdata/830640`) the same key exists but is **empty**. The tools prefix has an `s:`
  drive pointing at the Steam root, and no `P:`. So the link is the `main` value in the tools prefix,
  plus a `P:` with the game data the tool resolves (`dz\...`). This repair is not tested here; see the
  dayz-dev skill (`systems/mod-packaging.md`). dayz-mcp's `dayz_tools_paths.py` and `pack-addon.ps1` need that
  linked prefix. For these tests the addon was packed with bzed's armake2 fork (`armake2 build`, `keygen`,
  `sign`), and the game was started by hand.
- The **native Linux `DayZServer`** runs mods and the dayz-mcp bridge unchanged (see 3). Its defines
  include `SERVER_FOR_WINDOWS` and `PLATFORM_LINUX`.
- The **client runs under Proton** (Steam Linux Runtime → Proton → `DayZ_x64.exe`). It accepts
  `-profiles=Z:\<linux path>`, and `$profile:` resolves there. It loads an `@Mod` that is a
  symlink in the client's DayZ folder pointing at a Linux path. Started headless in sway; the
  dayz-dev skill's `dayz-client-headless.sh` does this.
- **Client and server builds must match.** The Steam client auto-updated to 1.30.164289 while the
  DayZ Server app was still 1.30.164200 (`StateFlags=6`, update pending): the client is refused with
  `CONNECTING FAILED (0x00020013) Client is a newer build than the server`. Check both
  `appmanifest_221100.acf` and `appmanifest_223350.acf` (`buildid`, `StateFlags` 4) before a
  client/server run.

## 2. dayz-mcp Python side on Linux

`tools/` does not import on Linux. Each blocker below was worked around with a throwaway shim (a
`sitecustomize.py` plus a launcher script) to see how far it gets; the list is what a real port needs.

| # | Where | Problem on Linux | Shim used / proper fix |
|---|---|---|---|
| 1 | `win32_fileinfo.bind_common_kernel32` (called at import by `pinned_keyfile`, and more) | `ctypes.WinDLL` does not exist → `AttributeError` at import | fake `WinDLL` whose functions raise when called. Fix: bind lazily, POSIX branches |
| 2 | `dayz_test_worker.py:1250` (module level) | `stat.IO_REPARSE_TAG_MOUNT_POINT` / `_SYMLINK` exist only on Windows | define the constants. Fix: guard with `getattr` or `os.name` |
| 3 | `inbox.py:23` (module level) | `os.environ["LOCALAPPDATA"]` → `KeyError` | set `LOCALAPPDATA`. Fix: XDG state dir (`$XDG_STATE_HOME/dayz_mcp`) on POSIX |
| 4 | `daemon_policy.py:8` | `import msvcrt` at module level | stub module. **Pitfall:** a `msvcrt` module on `sys.path` makes CPython's `subprocess` think it is on Windows (`import _winapi` fails); the stub must be put in `sys.modules` only after `subprocess`/`asyncio` are imported. Fix: `fcntl.flock` on POSIX |
| 5 | `pinned_keyfile.read_pinned_keyfile` (`loopback.read_key`) | Win32 handle-based reader → always `invalid_daemon_keyfile` | plain read. Fix: POSIX reader (`O_NOFOLLOW`, `fstat`: regular file, `st_nlink == 1`, size cap) |
| 6 | `--daemon` mode, `instance_context.try_acquire` → `_open_shared_lock` | `OSError: root_writer_lock_open_failed` (Windows byte-range lock) | used `--embedded` instead. Fix: `fcntl.lockf` on POSIX |
| 7 | `loopback.ExclusiveThreadingHTTPServer.allow_reuse_address = False` | correct on Windows (there SO_REUSEADDR allows a second LISTEN), wrong on Linux: a restarted daemon cannot bind while the game's polls left the port in TIME_WAIT (`Errno 98`) | set `True` on POSIX. On Linux SO_REUSEADDR does not allow a second listener |
| 8 | `session_*` tools | `session_tools_require_client_mode`: leases only exist in `--client` mode, which needs the daemon (#6) | blocks every lease-gated tool until #6 is ported |
| 9 | run binding | a game started by hand polls as `LEGACY_UNBOUND`: reads only, every mutation and most reads refused with `game_not_ready:reason=legacy_unbound`. Binding comes only from the managed launcher (Windows process identity, native launcher bundle) | bound by hand with `ServerState.install_bound_peer(instance=<uuid4>, role="server", pid=<enfMain pid>)` (the test helper), and wrote `"instance": "<uuid4>"` into `dayz_mcp.json` **before** the game starts (the bridge reads `instance` only at init; `ReloadKeyAfterFailure` re-reads the key only). After that the polls show `bind=BOUND`. Fix: a supported "bring your own game" binding (CLI or MCP verb that takes a PID + token and writes the config) |

Not reached (needs a matching client): `bridge_status` readiness also requires the **client** peer to poll
(`client_not_polling`), so even the server-side reads (`surface_query`, `scene_raycast`) were refused with only
the server bound. A server-only mode (useful for terrain checks on a dedicated server) would need that gate relaxed
for server-peer tools.

Platform-specific code to review for a port: `grep -l -E 'winreg|windll|WinDLL|msvcrt|win32|_winapi|
LOCALAPPDATA|IO_REPARSE' tools/dayz_mcp/*.py` hits about 25 modules (`wmi_host`, `window_*`,
`foreground_lock`, `steam_preflight`, `registry_lock`, `launcher_registry*`, `identity_migration`,
`native_*`, `orphan_guard` with `netstat.exe`, `authenticode`, ...). Most are launcher/desktop features that a
Linux port can leave out. The minimal Linux set is: loopback daemon + client mode + leases + a manual binding
(#1–#9).

## 3. dayz-mcp addon (Enforce side) on Linux — works

- `addon/` packed with `armake2 build addon <out>/addons/DayZ_MCP.pbo` (prefix `DayZ_MCP` from
  `$PBOPREFIX$`) and signed with `armake2 keygen`/`sign`. It loads on the native Linux server with
  `-mod=@DayZ_MCP`: the Mission module compiled; warnings only (`IsVitalCarBattery`, `IsVitalTruckBattery`,
  `ForceUpdateLightsStart` obsolete in 1.30).
- `RestApi` polling from the Linux server to the Linux daemon on `127.0.0.1` works at about 1.1 Hz
  (`pollHz 5` configured, measured interval 0.9 s while idle).
- After the daemon restarts, the bridge logs `poll error=7` with backoff up to 30 s and recovers by itself
  once the port is back.
- Under Proton the client loaded the same PBO from a symlinked `@DayZ_MCP` and `$profile:` from
  `-profiles=Z:\...`. Whether its `RestApi` reaches the Linux loopback was **not reached**: the bridge starts
  in-mission and the join failed on the build mismatch (section 1).

## 4. Next steps to finish the test

1. Let Steam finish updating the DayZ Server (223350) to the client's build.
2. Run again: Linux server + Proton client, both with `instance` tokens in their `dayz_mcp.json`, bind both
   peers (`role` `server`/`client`, client PID = the Linux PID of the `DayZ_x64.exe` wine process), and
   check `bridge_status` → `ready`, then `surface_query` / `scene_raycast` / `player_teleport`.
3. Port #6/#8 so leases work. Until then only the embedded, lease-free subset can be tested.

## 5. Follow-up, same day: what changed after these notes

- **DayZ Tools under Proton** were measured tool by tool and turned into
  `skills/_shared/linux-proton.md` (guide) and `skills/_shared/scripts/dayz-proton.sh` (runner). Short
  version: the cross-app problem is the missing `P:` and the empty game key in the tools prefix, plus
  what Steam does on a first launch (install-script registry, VC++ runtime) that a private prefix
  lacks. ImageToPAA, CfgConvert, the DS tools, AddonBuilder, binarize, TexView, Object Builder,
  Workbench and DayZDiag (client and `-server`) all ran.
- **armake2 `--proton-binarize` alpha bug**: fixed in bzed's fork by `0a0ce3b`; a build from HEAD
  `7dcb3cf` gives output byte-identical to BI's binarize run from a `P:` root. An older installed build
  still showed the 20-byte difference (texture not found); `--version` prints `v0.3.0` for both.
- **Build match**: by the evening both client and server reported 1.30.164289 (`doctor` in the runner
  compares the game versions; Steam `buildid`s differ per app by design). The Experimental server
  (1042420) was still on 1.30.164200 with an update pending.
- **dayz-mcp Python side**: branch `linux-port` (commit `ac5578d`) fixes #1–#5 and #7 properly
  (no shims): every module imports except `native_launcher_backend`, the POSIX keyfile reader, OFD
  byte locks, `SO_REUSEADDR` on Linux, XDG state dir. `--embedded` answers MCP `initialize` and
  `tools/list` (107 tools) and serves the loopback. #6/#8 got further: the daemon passes the instance
  lock, startup election, interpreter check and process scan, then stops at the runs.json identity
  migration (`runs_backup_transaction_publish_failed`), which is built on Windows handle semantics
  (no-clobber rename, delete through a pinned handle, file-ID identity) and needs a POSIX design.
  The modules sealed into the native launcher (`tools/packaged-modules.lock.json`) are left
  byte-identical: the Linux code lives in the unsealed `linux_compat.py` (its `install()` runs first
  in `python -m dayz_mcp` and swaps Linux implementations in) and `byte_lock.py`, so no launcher
  rebuild is needed. #9 (binding a hand-started game) is unchanged; attaching to a game under Proton
  is a poor fit (its Linux PID is a Wine process), so the intended route is a Linux launch path in
  which the daemon starts the native server and the Proton client itself and binds them by per-run
  token. The Windows test suite was not run.
