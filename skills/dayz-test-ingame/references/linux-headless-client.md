# Testing the client side on Linux: a headless client and a self-reporting test mod

`linux-native-server.md` proves the server half of a mod. Anything a player drives (UI, input, what the client
sees after a server change, RPCs both ways) needs a real client. This page runs the retail client under Proton
without a monitor, joins it to a local native server, and lets a test mod report its own results.

Source: bzed's own measurements, from `bzed/dayz-dev-plugin@6112ac5` `testing/client-testing.md` (cited as
`CT:<line>`), contributed to this Pack under its MIT licence by the author. **Measured** on Linux with client and
server 1.29.163709 (app 221100) and, unless a line says otherwise, the 1.30.164014.27 pre-release, then on the
Experimental apps (1024020); GE-Proton11-1, an AMD GPU on Vulkan/RADV, sway 1.12 (`CT:8-11`). 1.30 is stable now.
The author re-tested the whole plugin on DayZ 1.30 stable (the author's report, 2026-11-13; build not recorded here).

Scripts: `skills/_shared/scripts/dayz-client-headless.sh`, `dayz-client-test.sh`, `dayz-mod-pack.sh`. Test mod:
`../assets/autotest-mod/`. This pairs the **retail** client with the **native** server. A `DayZDiag` client only
joins a `DayZDiag` server (`0x00020017`); that pairing, and the managed dayz-mcp cycle, are in
`_shared/linux-proton.md` and the "On Linux" section of `../SKILL.md`.

## What you need, and the ground rules

- A running, logged-in Steam that owns DayZ (the game talks to it), the client installed, a Proton tool,
  `sway` and `grim` (`CT:15-20`).
- A server tree (`linux-native-server.md`) with the mods and their `.bikey`s; wipe its `storage_1` first if CF
  entered or left the mod set since it last ran.
- **One game at a time.** A Steam account runs one game, and a second client would fight the first over GPU,
  Wine prefix and Steam connection, including the user's own game: if they are playing, wait or ask. Servers
  can run side by side (`CT:24-27`).
- `dayz-client-headless.sh status` lists running clients (exit 1 if there is one); `start` and
  `dayz-client-test.sh` refuse to start a second game. Never kill a game you did not start (`CT:28-30`).
- **Stop the game as soon as you are done**: it holds the GPU, several GB of RAM, and shows the account as
  "playing DayZ". `dayz-client-test.sh` stops its client itself, also on failure, timeout or Ctrl-C (`CT:31-34`).

## 1. The client without a display

```sh
S=skills/_shared/scripts/dayz-client-headless.sh
$S start /var/tmp/dzc -name=autotest "-mod=@9dd22c91;@MyMod" -connect=127.0.0.1 -port=$GAME
$S shot  /var/tmp/dzc /var/tmp/dzc/now.png
$S stop  /var/tmp/dzc                         # ends sway, which ends the game
```

It starts a headless sway (`WLR_BACKENDS=headless`, 1280x720) and runs inside it the chain Steam itself uses
(Steam Linux Runtime 4 `_v2-entry-point` → `proton run` → `DayZ_x64.exe`), so the game inherits that session's
display while the Steam API handshake still goes to the running Steam (measured). `steam -applaunch` would hand
the launch to the running Steam and land on your desktop (reasoned, not run) (`CT:36-55`). Also measured
(`CT:56-66`):

- `for_window [app_id="dayz_x64.exe"] fullscreen enable`, or the window is larger than the output and the
  screenshot is cropped;
- `-nolauncher -skipintro -window -nosplash -noPause`; `-connect=<ip> -port=<port>` joins with no clicks;
- `-name=<x>` shows in the server's admin log, the cheapest "client connected" check;
- DayZ's arguments go one per line into a file, because sway's parser would cut `-mod=@a;@b` at the `;`;
- `PROTON` (default `GE-Proton11-1`) and `STEAM_ROOT` select the Proton tool; `PROTON_ENABLE_WAYLAND=1` is set.

## 2. Mods on the client

The client loads mods by folder name from its install directory, so link them there (this writes a symlink
into the Steam directory; remove it when done) (`CT:68-79`):

```sh
ln -sfn "$PWD/build/@MyMod" "<library>/steamapps/common/DayZ/@MyMod"
```

- **Use the client-side names in the client's `-mod=`.** The server's `@CF` is the client's hashed
  `@9dd22c91 -> workshop/content/221100/1559212036` here (find yours with
  `ls -l <client dir> | grep <workshop id>`). A name that does not exist loads nothing, and the game still
  starts and even shows the "modded game" notice (`CT:81-84`).
- **A wrong or missing client mod** gets the player kicked with
  `Client is missing a mod which is on the server. (<mod names>) (Missing PBO.)` in the server's output and
  logs. Read that before suspecting the network (`CT:85-87`).
- Dependencies first (CF before the mods that need it); the reverse order was not tried.
- Keep `verifySignatures = 2` and every mod's `.bikey` in the tree's `keys/`; signed mods with their keys
  joined. An unsigned mod with signature checks on was not tried (`CT:90-93`).
- **BattlEye**: a client started this way does not start BattlEye, so set `BattlEye = 0;` in the tree's
  `serverDZ.cfg` (`CT:94-95`).

## 3. Tests that run on both sides and report back

Seeing the client connect proves little. `../assets/autotest-mod/` runs code on the server and on the client in
a known order and prints results an outside script can grep; it ran green on both builds above (`CT:132-165`).

```
 server (drives)                               client (executes)
 wait until the player is connected, godmode on
 test N: ServerSetup(player)
 RPC AUTOTEST_RPC_RUN(name) ----------------->  ClientCheck()  (retried for up to 5 s while it returns false)
                              <---------------  RPC AUTOTEST_RPC_RESULT(name, passed, message)
 ServerCheck(player)
 Print("[AUTOTEST] PASS|FAIL name message")
 ...
 Print("[AUTOTEST] DONE passed=P failed=F")    <- the line an outside script waits for
```

- The server is the only driver; both sides load the same PBO, so only the test name crosses the wire.
- One RPC out, one back per test; a 20 s timeout turns silence into `FAIL ... no answer from the client`, so a
  crashed or absent client fails the run instead of hanging it.
- Client checks retry every 500 ms for up to 5 s: replication lag does not flake, a state that never arrives
  still fails.
- Results go to the server's script log; the client prints `[AUTOTEST-CLIENT]` lines to its own.

**Adding a test.** A test is a class in `scripts/4_World/AutoTestCases.c` (`Name()`, `ServerSetup(player)`,
`ClientCheck(out msg)`, optional `ServerCheck(player, out msg)` and `NeedsDamage()`), registered in
`AutoTestRegistry.All()` in run order. To test your own mod, copy the addon into a separate test mod
(`@MyMod_Test`) that depends on yours, load it with `-mod=` on both sides, and keep it out of the release. The
mod name is also a script define (`#ifdef AutoTest`, visible in the `Module: ...; defines:` line) (`CT:167-203`).

**Godmode.** The runner sets `player.SetAllowDamage(false)` as soon as it is scheduled and between tests, so a
zombie or a fall does not fail an unrelated test. A server-side melee hit left health `100 -> 100`; a test that
overrides `NeedsDamage()` to `true` gets damage for itself only, and the same hit gave `100 -> 95` (both builds).
Only the harness's own `ProcessDirectDamage` with `MeleeZombie` was tried, not real zombies, animals, falls,
hunger, thirst or cold (`CT:205-223`).

**Pitfalls found building it** (`CT:225-235`):

- Do not `foreach` directly over a function's return value (`foreach (T t : Registry.All())`): on the client it
  worked once, then threw `NULL pointer to instance` on the second call (1.29). Assign it to a local first.
- Pick RPC ids no other mod uses (the example uses 74010 and 74011; there is no registry).
- The runner starts 20 s after `InvokeOnConnect`, because the client is still loading.
- Several players need several clients; this runs one.

## 4. One command: start, wait, report, stop

```sh
skills/_shared/scripts/dayz-client-test.sh -t "$TREE" -s "@AutoTest" -c "@AutoTest" -o /var/tmp/run1
# [AUTOTEST] PASS client_has_player local player SurvivorM_Rolf
# [AUTOTEST] PASS server_item_synced Chemlight_Red replicated to the client
# [AUTOTEST] PASS godmode_blocks_damage  | server: health 100 -> 100
# [AUTOTEST] PASS damage_when_needed  | server: health 100 -> 95
# [AUTOTEST] DONE passed=4 failed=0
```

Free ports, server, headless client, wait for `DONE`, collect `[AUTOTEST]` lines, final screenshot, teardown.
Exit 0 = `DONE` seen and no `FAIL`; 1 = a failure or the timeout (default 300 s; a cold client start alone takes
about 60 s), which saves `timeout.png` (`CT:237-253`). Build and sign the example first:
`dayz-mod-pack.sh -C <copy of assets/autotest-mod> keygen`, then `build`; link `build/@AutoTest` and
`keys/AutoTest.bikey` into the tree and `build/@AutoTest` into the client directory. The key is a test key: never
install it on a real server.

## 5. Reading what the client did

- Client script log: `<compatdata>/<221100|1024020>/pfx/drive_c/users/steamuser/AppData/Local/<DayZ|DayZ Exp>/script_<date>.log`
  (newest = current run): compile errors, `Print` output, `NULL pointer` traces (`CT:261-263`).
- `crash_<date>.log` beside it holds a client-side script exception with its stack, so a mod can be checked for
  client exceptions without looking at the screen (`CT:264-267`).
- Screenshots answer "is the HUD there", not pixel asserts.
- The server's `profiles/*.ADM` has `Player "<name>" is connecting` / `is connected` and the spawn position: the
  reliable join signal (`CT:269-270`).
- The game's main thread is `enfMain` in `ps`, like the server; find it through `swaymsg -t get_tree` (`pid`) or
  just `stop` the session. `pkill -f DayZ_x64.exe` kills the shell running it (exit 144) (`CT:274-280`).

## Experimental (the next build, optional)

1.30 is stable, so the stable apps above are the default. Experimental has its own client (1024020, `DayZ Exp`), server (1042420), Wine prefix (`compatdata/1024020`) and
log folder (`AppData/Local/DayZ Exp/`), and its script log lines carry a timestamp prefix. It has **no Workshop of
its own**: subscribe through stable, link the items from `workshop/content/221100` into `steamapps/common/DayZ Exp`,
build the server tree from `find-dayzserver.sh -e`, and pass `-e` to the client scripts. Without `-e` they start
the stable client against the experimental server, which `forceSameBuild = 1` should reject (not run). The same
AutoTest PBO passed unchanged on 1.30.164014.27 with the stable Workshop's CF (`DONE passed=2 failed=0`)
(`CT:97-130`).

## Expansion bundle: skip the spawn selector first

With the Expansion bundle (or DayZ-Expansion-Spawn-Selection, 2804241648) the client lands in the spawn selector,
where screenshots show the menu and item handling does not work. On a fresh server profile, before the client
joins (measured 1.30.164078.38: the client then joined straight into the world, HUD visible) (`CT:283-297`):

1. Start the server once, so Expansion writes its settings and the storage; stop it.
2. In `mpmissions/<mission>/expansion/settings/SpawnSettings.json` set `"EnableSpawnSelection": 0`.
3. Delete `mpmissions/<mission>/storage_1/players.db` (a stored character skips the fresh-spawn path).
4. Start the server again, then join.

Repeat it for every new server config that loads the bundle. The bundle already contains Spawn-Selection. The mod
set, in load order: CF 1559212036, Dabs Framework 2545327648, DayZ-Expansion-Licensed 2116157322,
DayZ-Expansion-Bundle 2572331007, plus DayZ-Expansion-Animations 2918418331 to drive Expansion cars or helicopters
(`CT:299-318`; the requirements behind that order are in `dayz-mod-workflow`, `references/dayz-1-30-server-measured.md`).

## Not covered

gamescope and Xvfb (Xvfb has no DRI3 path, so DXVK presentation is in doubt), input injection, BattlEye-enabled
servers, several clients, Windows and macOS were not run (`CT:320-326`).
