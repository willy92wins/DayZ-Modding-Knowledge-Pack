# Testing a mod on the native Linux DayZServer, without dayz-mcp

A mod is only proven to work once a server has loaded it. A syntax check and a clean PBO build do not
show that the scripts compile, that a `modded class` or `override` is legal, or that the engine loaded
the scripts at all. A local dedicated server answers all three in about a minute, with no client.

Source: bzed's own measurements, from `bzed/dayz-dev-plugin@6112ac5` `testing/local-server.md`
(cited below as `LS:<line>`), contributed to this Pack under its MIT licence by the author. Platform:
Debian, the native Linux `DayZServer` (Steam app 223350). 1.30 is the stable release. The author re-tested the whole plugin on DayZ 1.30 stable (the author's report, 2026-11-13; build not recorded here). Build numbers in
the text say where a detail was first measured: 1.29.163709, the 1.30.164014 pre-release (then on Experimental),
1.30.164200 or 1.30.164289. The Windows server
(`DayZServer_x64.exe`) takes the same parameters, but where Linux and Windows differ the Windows rules in
`../SKILL.md` win on Windows (mod paths, mission path). This is the route without dayz-mcp; the managed
route is the "On Linux" section of `../SKILL.md`.

Scripts: `skills/_shared/scripts/` (`find-dayzserver.sh`, `make-server-tree.sh`, `free-ports.sh`),
tested in `skills/_shared/tests/test_linux_helpers.py`.

## 1. Use the server Steam already installed

Use the "DayZ Server" tool (app 223350) the user's Steam client installed: it is authenticated and Steam
keeps it on the build a client must match. A separate `steamcmd` install cannot log in anonymously (223350
needs an account that owns DayZ, with password and Steam Guard) and drifts from the client build unless you
update it yourself (`LS:12-27`). Do not install it for the user; ask them to install **DayZ Server** from
the Library's Tools filter (or `steam steam://install/223350`) and wait until they confirm (`LS:57-66`).

```sh
S=skills/_shared/scripts
"$S/find-dayzserver.sh" -v     # install dir on stdout; buildid and StateFlags on stderr
"$S/find-dayzserver.sh" -w     # the DayZ client's workshop dir (content/221100)
"$S/find-dayzserver.sh" -e -v  # experimental server 1042420 ("DayZ Server Exp", note the space)
```

It reads `libraryfolders.vdf` of every known Steam root and trusts `appmanifest_223350.acf`, not the
`"apps"` list in `libraryfolders.vdf`, which was stale on the measuring machine (`LS:31-47`). Exit 0 =
found; `StateFlags` other than 4 means Steam is still installing or updating, and the script warns.

| | Server | Client | Workshop items |
|---|---|---|---|
| Stable | 223350, `DayZServer` | 221100, `DayZ` | `workshop/content/221100` |
| Experimental | 1042420, `DayZ Server Exp` | 1024020, `DayZ Exp` | `workshop/content/1024020` |

Stable (223350) is the default, since 1.30 is stable; Experimental carries the next build and is only for testing a
mod ahead of that release.

Experimental runs a diag build (`DEVELOPER`, `DIAG_DEVELOPER`, `BUILD_EXPERIMENTAL` in the `defines:` of
the `Module:` log lines): `Error()`/`ErrorEx()` print as `Virtual Machine Exception`, and some `SCRIPT (E)`
lines such as `Leaked 'BunkerBroadcastManager'` are vanilla noise, so compare against a vanilla run. On the
1.30.164014 pre-release a script compile error was followed by a **segfault** of the server: a crash right
after boot means read `script_*.log` for `Can't compile` first (`LS:86-96`).

## 2. Never write into the Steam install: build a tree

Steam owns the install: an update or "Verify integrity" overwrites what you put there, and a server run
from it writes `storage_1/` and core dumps into it. Run from a tree of your own that symlinks into Steam
(`LS:98-129`):

```sh
TREE=$("$S/make-server-tree.sh" /var/tmp/dzt)   # short path, outside Steam
```

| In the tree | What it is |
|---|---|
| `DayZServer`, `addons/`, `dta/`, ... | one symlink per top-level entry of the install |
| `serverDZ.cfg` | a copy, yours to edit |
| `mpmissions/<mission>/` | a real directory of per-file symlinks, so `storage_1/` lands in the tree |
| `keys/`, `battleye/` | real directories of per-file symlinks; add your `.bikey` here |
| `profiles/` | for `-profiles=profiles` |

- To edit a Steam-provided file, replace its symlink with a copy first:
  `cp --remove-destination "$(readlink "$TREE/mpmissions/<m>/init.c")" "$TREE/mpmissions/<m>/init.c"`.
- Re-run the script after a Steam update; it refreshes the links and keeps your real files.
- The tree is disposable. Keep its path short: a deep path broke persistence with
  `File path exceeds max filename length. (291 > 280)` and no `spawnpoints.bin` (measured with the client
  harness, `bzed/dayz-dev-plugin@6112ac5 testing/client-testing.md:276-278`).
- **One tree per running server.** A server locks its `profiles/` and the `storage_1/` of its mission;
  two servers on one tree collide, and the logs you read afterwards belong to neither (`LS:131-150`).
- **Run the trees one at a time anyway.** A 1.30 server with the Expansion bundle used about 7.5 GB RSS; an
  A/B pair plus unnoticed leftovers pushed a 60 GB machine to its limit. A boot takes about two minutes,
  so stop one server (by PID, section 3) before starting the next, and check `free -h` first if two must
  overlap (`LS:156-160`).
- Since 1.30.164200 an absolute `-profiles=` outside the tree works; keep `-profiles=profiles` anyway, so
  each run's logs stay in its tree (`LS:152-154`).

### Ports: never the defaults

Every server needs its own game, Steam query and RCon port. The defaults (2302, 2303, 2306) are what a real
server, a client on the same machine or the last test run still holds, and a collision may not error: the
server answers on the wrong socket or RCon silently stays down (`LS:162-187`).

```sh
set -- $("$S/free-ports.sh" 3); GAME=$1 QUERY=$2 RCON=$3   # free for UDP and TCP, 10 apart, no defaults
```

| Port | Where |
|---|---|
| game | `-port=$GAME` |
| Steam query | `steamQueryPort = $QUERY;` in the tree's `serverDZ.cfg` |
| RCon | `RConPort $RCON` in `$TREE/profiles/battleye/beserver_x64.cfg` |

- **Insert `steamQueryPort` at the top, never with `echo >>`.** The stock `serverDZ.cfg` ends with `};` and no
  newline, so an appended line becomes `};steamQueryPort = ...;`, a later `sed '/steamQueryPort/d'` deletes
  the brace too, and the server exits with `Missing '}'` (`LS:189-197`):
  ```sh
  grep -q '^steamQueryPort' "$TREE/serverDZ.cfg" || sed -i '1i steamQueryPort = 0;' "$TREE/serverDZ.cfg"
  sed -i "s/^steamQueryPort = .*/steamQueryPort = $QUERY;/" "$TREE/serverDZ.cfg"
  ```
- **The RCon seed lives in the profile directory.** With `-profiles=profiles` the server reads
  `profiles/battleye/beserver_x64.cfg` once, writes `beserver_x64_active_<hex>.cfg` beside it and uses only
  that copy afterwards, so delete stale active copies before seeding, and use a random password
  (`LS:199-213`):
  ```sh
  mkdir -p "$TREE/profiles/battleye"
  find "$TREE/profiles/battleye" -name 'beserver_x64_active_*.cfg' -delete
  printf 'RConPassword %s\nRestrictRCon 0\nRConPort %s\n' \
      "$(tr -dc 'A-Za-z0-9' </dev/urandom | head -c10)" "$RCON" > "$TREE/profiles/battleye/beserver_x64.cfg"
  ```

### Mods are symlinks in the tree

```sh
ln -sfn "$PWD/build/@MyMod" "$TREE/@MyMod"           # your build: rebuild, rerun, no copy step
W=$("$S/find-dayzserver.sh" -w)
grep -h '^name' "$W"/*/mod.cpp "$W"/*/meta.cpp        # find a mod's id by name
ln -sfn "$W/1559212036" "$TREE/@CF"                   # Community Framework
ln -sfn "$W/1559212036/keys/"*.bikey "$TREE/keys/"
```

Only subscribed items are in the workshop directory. If a mod is missing, ask the user to subscribe and start
the launcher once; never `steamcmd +workshop_download_item` into Steam's directories (`LS:215-229`).

### Wipe the storage whenever CF is added or removed

If a tree already ran (or an existing storage is reused) and CF enters or leaves the mod set, delete the
storage **before** the next boot. CF's ModStorage writes extra data into every saved entity, so storage
written with CF and read without it, or the reverse, fails (`LS:231-249`):

```sh
find "$TREE/mpmissions" -maxdepth 2 -name storage_1 -exec rm -rf {} +   # only in a tree you built
```

What each direction looks like, and why it misleads:

- **Removing CF** (1.30.164200.56): a tree booted once with `-mod=@CF` and then vanilla logged about 24,000
  `Virtual Machine Exception`s during the CE load, all
  `[EntityAI::OnStoreLoad] :: [WARNING] :: Scripted variables corrupted upon "PileOfWoodenPlanks". Entity will not be loaded correctly.`
  The server kept running, so a boot that "works" proves nothing: grep for `Scripted variables corrupted`
  (`LS:251-261`).
- **Adding CF** (1.30): the boot died with `Unknown type 'CF_Trace'` and `Can't compile "Engine" script module`.
  That reads like a CF/Expansion version conflict, not stale storage. Rebuilding the trees fresh with their
  final mod sets booted at once. When a CF change coincides with "version conflict" compile errors, wipe or
  rebuild before debugging versions. An attempt to reproduce it on 1.29.163709 (vanilla storage, one saved
  player, then CF) did not show it; mods that persist their own state remain the likely trigger
  (`LS:263-278`).

## 3. Run it headless

```sh
cd "$TREE" && ulimit -c 0 && timeout -k 15 60 ./DayZServer \
    -config=serverDZ.cfg -profiles=profiles \
    -servermod=@MyMod "-mod=@CF" -port=$GAME -nosplash -nopause -dologs
```

- **Mod paths relative to the tree.** Absolute `-servermod=`/`-mod=` paths are silently ignored: the engine
  probes the folder, loads no PBO, prints no error. Symlinks or `../` work; `-config` and `-profiles` take
  absolute paths (`LS:290-293`). This is the reverse of the Windows rule in `../SKILL.md`.
- **Relative `-mission=mpmissions/<name>`.** An absolute one leaves the 1.30 server without `init.c`'s
  `main` (`_shared/linux-proton.md`, section 5).
- **Run from the tree**: `addons/` and `mpmissions/` resolve against the working directory.
- **`ulimit -c 0`**: a crash writes a core file of up to about 5 GB into the working directory.
- **`timeout -k 15 60`**: the mission is up after about 10 s, then the server idles forever. A quiet log
  is not a slow server; it means your code did not run. Keep the `-k`: after `Termination successfully
  completed` the process can hang in Steam API threads until SIGKILL (`LS:296-302`).
- `-mod=` is for mods the client loads too; a headless run still only proves the server side.

### Listing and stopping test servers

`pkill -x DayZServer` and `pgrep -x DayZServer` do not match a running Linux server: it renames itself
(`enfMain` in the comm column), and their silent no-match looks exactly like "nothing running" while
several 7.5 GB servers keep going (1.30.164289; `LS:315-333`). List by command line and kill by PID:

```sh
ps aux | grep "[D]ayZServer"     # the [D] keeps grep itself out
kill <pid>
```

- Never `pkill -f DayZServer` in the same command line: the pattern matches the shell running it, which
  kills itself (exit 144).
- A server started as a background child of an agent's shell can be reaped when that shell ends. Start one
  that must outlive the tool call with `setsid nohup ./DayZServer ... >server.log 2>&1 &` and keep its PID.
- Other DayZ servers on the machine are not yours: check the `ps` arguments (tree, ports) first.

## 4. Read the result

`$TREE/profiles` gets `script_<date>.log`, `DayZServer_<date>.RPT` and `error.log`.

```sh
grep -h 'Module: Game; loaded' "$TREE"/profiles/script_*.log   # files per script module
grep -h 'SCRIPT.*(E)' "$TREE"/profiles/script_*.log            # compile errors
grep -h 'MyMod' "$TREE"/profiles/script_*.log                  # your own Print lines
```

1. **Did the scripts load at all?** Boot once without the mod for the vanilla baseline: 440 Game-module files
   on 1.30.164014 (416 on 1.29.163709). With the mod the count must rise by its script files in that module.
   **An unchanged count means the mod's scripts were not loaded**, though the server started and printed no
   error (`LS:349-352`). Silent causes seen (`LS:354-366`):
   - the PBO at the mod folder root (`@MyMod/MyMod.pbo`) instead of `@MyMod/addons/MyMod.pbo`: silently
     ignored, while the folder still shows in the `ANIMATION (E): Can't load @MyMod/...` pass, which is
     **not** loading (`dayz-pbo-build`, "PBO outside `addons/`");
   - an absolute mod path (section 3);
   - on 1.30, backslashes in the `CfgMods` script module paths (`files[] = {"MyMod\scripts\4_World"}`): the
     defines appear, no script compiles, no error (`dayz-mod-workflow`, `references/dayz-1-30-server-measured.md`);
   - a PBO without the prefix its `config.cpp` script paths expect, or inner names that repeat the prefix
     (`MyMod\MyMod\config.cpp`): pack from inside the addon folder.

   **Decisive probe** when a `modded class` or `override` silently does nothing: put a deliberate syntax error
   in one of the mod's scripts and boot once. A clean boot means the file was never compiled and the mod is not
   loading; a compile error means it is (`LS:368-370`). Prove the scripts are in the compile set before
   theorising about override order or API misuse.
2. **Did they compile?** `SCRIPT    (E)` lines are compile errors. The tag is space-padded, so grepping for
   the literal `SCRIPT (E)` never matches; use `SCRIPT.*(E)` (`LS:371-372`).
3. **Did your code run?** A `Print("MyMod: loaded ...")` in a mission or init hook is the cheapest proof.

Only a boot catches: engine classes that cannot be `modded` (for example `DayZPlayerInventory`), `proto native`
methods that cannot be overridden (for example `SendSyncJuncture`), and wrong override signatures
(`LS:376-380`). A server that "works" also proves nothing about load order: see "Mod load order" in
`dayz-mod-workflow`.

## 5. Code that needs players

Without a client, player-driven hooks (actions, inventory, damage, vitals) never fire. Drive them from a scratch
copy of the mod with a debug call: `g_Game.CreatePlayer(null, "SurvivorM_Mirek", pos, 0, "NONE")`, then
`CreateInHands`, then the method under test. Such a player has no `PlayerIdentity`, so code that filters on
`GetIdentity()` skips it; mark those runs partial (`LS:382-394`). For a real client (UI, replication, RPCs in
both directions) see `linux-headless-client.md`.

## Windows notes (not verified)

The Steam root is `HKCU\Software\Valve\Steam` `SteamPath`; `libraryfolders.vdf` and the manifests have the same
format; the binary is `DayZServer_x64.exe`; stop it with `Stop-Process`. `make-server-tree.sh` is POSIX sh; the
same tree on Windows would use `New-Item -ItemType SymbolicLink` or `mklink /J` (`LS:399-409`). On Windows the
managed route in `../SKILL.md` is the measured one.
