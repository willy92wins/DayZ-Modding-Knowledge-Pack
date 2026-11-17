# Talking to dayzmake through `dayzmake mcp`

dayzmake (https://github.com/bzed/dayzmake, >= `v3.1.0`) ships an MCP server, `dayzmake mcp`, that serves its
script-API index and all of its file commands as tools. **For an agent it is the one way to talk to dayzmake**:
look-ups, PBOs, configs, keys, signatures, textures and binarizing go through the same server, on Linux and
Windows alike. The CLI stays the fallback and the interface for scripts. Installing and verifying the binary:
`dayz-pbo-build/references/dayzmake-linux.md`, "Get the right dayzmake".

Do not confuse it with **dayz-mcp** (https://github.com/willy92wins/dayz-mcp, tools `mcp__dayz-mcp__*`, skill
`dayz-mcp-verify`), the bridge into a running game. dayzmake's server never starts DayZ: it reads and writes
files.

Source of the facts below: dayzmake v3.1.0 (tag `v3.1.0`, commit `83320f1`), `README.md` "MCP server",
`docs/book/src/reference/mcp.md` and `docs/book/src/guides/mcp.md`, and the tool list the v3.1.0 server returned
on 2026-11-17 (`tools/list`, 26 tools); the v3.0.2 server was measured the day before (23 tools). What was run is under "Measured".

## 1. Why the server and not the shell

- **Structured arguments.** Paths and PBO entry names (`scripts\4_World\x.c`) go in as JSON strings, so there is
  no shell quoting of backslashes, spaces or `$`, and no PowerShell-versus-sh translation on Windows.
- **Results an agent can read.** [EXACT][CLAIM-DAYZMAKE-MCP-RESULTS] Warnings come first (`warnings:` and one line each, then a blank line, then the
  output), so a cut never drops them. A failure is a result with `isError: true` and the message as its text; the
  server keeps running and the call can be corrected.
- **Bounded output.** A reply is capped at 200 000 bytes and ends with
  `[truncated: showing bytes A-B of N; call again with offset=B]`; `pbo_cat` and `api_source` take `offset` and
  `length` to fetch the rest.
- **No silent overwrite.** No tool overwrites a file unless `force` is true.
- **Same code as the CLI.** Each file tool takes the arguments of its CLI command, so everything the skills say
  about a dayzmake command (`dayz-pbo-build`, `dayz-pbo-reverse-engineering`) holds for its tool.

## 2. Is it available?

Look for tools whose names end in the server's tool names (`api_class`, `pbo_build`, ...). The prefix comes from
the name the server was registered under, for example:

- `mcp__dayzmake__api_class`: registered as `dayzmake` (`claude mcp add dayzmake -- dayzmake mcp`);
- `mcp__plugin_dayz-dev_dayzmake__api_class`: registered by bzed's `dayz-dev` Claude Code plugin.

In Claude Code they may be deferred: `ToolSearch` with `dayzmake` finds them. If no such tools exist, offer the
user the registration below (it is their call: the server acts with their permissions) and use the CLI meanwhile.

**Version.** [EXACT][CLAIM-DAYZMAKE-MCP-STALE-SERVER] No tool reports the version (the `initialize` reply carries it as `serverInfo.version`, but a
client need not show that to the agent). `dayzmake --version` checks the binary on `PATH`, and the running server
can be older: a client keeps the server process it started, so after an upgrade the old binary keeps answering
until the client restarts the server (in Claude Code: `/mcp` and reconnect it, or a new session). When the
version matters (it does for `pbo_unpack` of third-party PBOs and `pbo_verify`, see `dayz-pbo-build`), ask for that
restart after an upgrade.

## 3. Register it

Register the binary you verified (`dayz-pbo-build/references/dayzmake-linux.md` installs it as
`~/.local/bin/dayzmake`) by its absolute path, not by the name `dayzmake`: a name is looked up on the client's
`PATH`, which can hold another, older build. Check that binary first. Claude Code, for every project of this user:

```sh
"$HOME/.local/bin/dayzmake" --version      # must print v3.1.0 or later
claude mcp add -s user dayzmake -- "$HOME/.local/bin/dayzmake" mcp
```

[EXACT][CLAIM-DAYZMAKE-MCP-REGISTER] Without `-s` the scope is `local` (this project, for this user only); `-s project` writes a `.mcp.json`
into the project for everyone who opens it (`claude mcp add --help`, 2026-11-16); a project-scoped entry is
shared, so it names the path where everyone installs the verified binary. Any other MCP client: a `stdio` server
whose command is the absolute path of the verified binary and whose argument is `mcp`; JSON does not expand `~` or
`$HOME`, so write the path out. The shape most clients read is in the Pack's `.mcp.example.json`:

```json
{ "mcpServers": { "dayzmake": { "command": "/home/<you>/.local/bin/dayzmake", "args": ["mcp"] } } }
```

On Windows, the same with the full path of the verified `dayzmake.exe`.

The server needs no configuration and opens no network connection. `dayzmake mcp -v` lifts the limit of ten
warnings per name in each call.

## 4. Safety: paths and permissions

- [EXACT][CLAIM-DAYZMAKE-MCP-RELATIVE-PATHS] **Paths resolve against the server's working directory**, which is where the client started it, usually the
  project folder the session was opened in. That need not be where your shell is standing: **pass absolute
  paths.**
- The tools act with the permissions of the user who runs the server. They read any file that user can, create
  files, and overwrite them when `force` is set. Pass `force` only when the user asked for that file to be
  replaced.
- Untrusted PBOs (Workshop content, anything you did not build): `pbo_inspect` and `pbo_cat` read without
  writing; `pbo_unpack` and `extract` into a fresh, empty folder skip unsafe entry names (>= `v3.1.0`; check the version as in
  section 2).
- `pbo_cat` without `target` returns an entry only if it is UTF-8 text (a `config.bin` gives an error that says to
  pass `target`); `config_derapify` then reads the written file.

## 5. Tools and their CLI commands

[EXACT][CLAIM-DAYZMAKE-MCP-TOOLS] Argument names as the v3.1.0 server lists them; **bold** marks a required argument. Every tool that writes a file
also takes `force`.

| Tool | CLI | Arguments |
|---|---|---|
| `api_class` | `dayzmake api class` | **`name`**, `inherited`, `mods_only` |
| `api_find` | `dayzmake api find` | **`regex`**, `class` |
| `api_subclasses` | `dayzmake api sub` | **`name`**, `all` |
| `api_enum` | `dayzmake api enum` | **`name`** |
| `api_chain` | `dayzmake api chain` | **`name`** |
| `api_source` | `dayzmake api src` | **`name`**, `context` (n lines around each declaration), `lines` (`"a-b"`), `cat`, `target` (only with `cat`), `offset`, `length`; `cat`, `context` and `lines` exclude each other |
| `api_grep` | `dayzmake api grep` | **`regex`**, `ignore_case` (every `.c` line of vanilla and the selected mods, read from the PBOs; no `refresh`) |
| `api_config` | `dayzmake api config` | **`path`** (`CfgVehicles/Hatchback_02`: chain, resolved properties tagged with their class, subclasses, defining PBOs) |
| `api_defines` | `dayzmake api defines` | `regex` |
| `api_update` | `dayzmake api update` | (rebuilds the caches; with `mods=all` it warms them) |
| `api_mods` | `dayzmake api mods` | (installed mods: workshop id, name, folder, whether they have scripts) |
| `pbo_inspect` | `dayzmake inspect` | **`path`** (a PBO, or a P3D model: MLOD and ODOL v56), `json` (PBOs: the header with each name's raw bytes in hex) |
| `pbo_cat` | `dayzmake cat` | **`pbo`**, **`file`**, `target`, `offset`, `length` |
| `pbo_unpack` | `dayzmake unpack` | **`pbo`**, **`target`**, `use_prefix`, `only`, `exclude` (glob arrays; `exclude` wins) |
| `extract` | `dayzmake extract` | **`source`** (install, mod folder or one PBO), **`target`**, `derapify`, `only`, `exclude` (every PBO of `dta/` and `addons/` into `<target>/<prefix>/`, plus `pbo-map.tsv`; staged and swapped in) |
| `pbo_pack` | `dayzmake pack` | **`source`**, **`target`**, `exclude`, `headerext`, `key` |
| `pbo_build` | `dayzmake build` | **`source`**, **`target`**, `exclude`, `headerext`, `include`, `key`, `proton_binarize` |
| `config_rapify` | `dayzmake rapify` | **`source`**, **`target`**, `include` |
| `config_derapify` | `dayzmake derapify` | **`source`**, `target`, `indent` |
| `config_preprocess` | `dayzmake preprocess` | **`source`**, `target`, `include` |
| `paa_to_image` | `dayzmake paa2img` | **`source`**, **`target`** (the format follows the target's extension) |
| `image_to_paa` | `dayzmake img2paa` | **`source`**, **`target`**, `type` (`dxt1`, `dxt5`; default `dxt5`), `compress` (kept for compatibility: DXT mipmaps wider than 128 px are always LZO-compressed) |
| `key_generate` | `dayzmake keygen` | **`name`** (writes `<name>.biprivatekey` and `<name>.bikey`) |
| `pbo_sign` | `dayzmake sign` | **`pbo`**, **`private_key`**, `signature`, `v2` |
| `pbo_verify` | `dayzmake verify` | **`pbo`**, **`public_key`**, `signature` |
| `binarize` | `dayzmake binarize` | **`source`**, **`target`** (Windows; on Linux through Proton) |

The `api_*` tools also take `mods`, `experimental`, `dayz` (a DayZ client or server folder instead of the Steam
install) and, all but `api_grep` and `api_mods`, `refresh`; the queries take `json`, and all but `api_chain` take `max` (default 120). **Without `mods`
only vanilla is queried**: pass `mods=cf`, `expansion`, a workshop id, a mod name from `api_mods`, or `all`. The
first `mods=all` run indexes every installed mod and can take a while. `key` on `pbo_build`/`pbo_pack` signs the
PBO after packing with that `.biprivatekey`; `include` folders are searched, the working directory is only checked
directly. `exclude` and `headerext` are arrays (`["*.bak"]`, `["product=dayz"]`).

## 6. What stays on the CLI or with the Pack's scripts

- `skills/_shared/scripts/dayz-mod-pack.sh` (project layout, `keygen` refusals, one key for all addons, the
  upload folder, `check`, `publish-hint`) and the other helper scripts call the CLI; they are scripts, not agents.
  Inside such a project the server's `pbo_build` + `pbo_verify` cover a single addon.
- Nothing for look-ups any more: since `v3.1.0` `api_grep` searches the script bodies, `api_config` the config
  classes, and `extract` writes the tree of scripts and derapified configs that the Pack's own
  `extract-dayz-sources.sh` used to (`dayz-mod-dev`, "Look it up before you use it").
- Workshop upload (`workshop`), servers and the game (`dayz-test-ingame`, dayz-mcp).
- Install, upgrade and `dayzmake --version`.

## Measured

2026-11-17, Debian, dayzmake v3.1.0 release binary (verified as in `dayzmake-linux.md`), by hand over stdin:
`initialize` answered `serverInfo` `dayzmake` `3.1.0`; `tools/list` returned the 26 tools of section 5 with the
arguments listed there. `api_grep` for `GetGame\(\)\.GetMission\(\)\.GetWorldData` listed
`scripts\3_Game\Sandstorm.c:95: ...` and the other hits; `api_config` `CfgVehicles/Hatchback_02` answered
`chain: Hatchback_02 : CarScript : Car : Transport : All` and the defining PBOs; `extract` of the DayZ stable
install with `derapify` and `only: ["*.c", "config.*"]` into an absolute path answered
`extracted 3167 files from 125 PBOs` (3058 `.c` files, configs as `.cpp`, `pbo-map.tsv`); `pbo_inspect` of
`dta/scripts.pbo` with `json` returned the header with `key_hex`/`value_hex`; `api_source` with both `cat` and
`context` answered `isError: true`, `--cat excludes --context and --lines`.

2026-11-16, Debian, dayzmake v3.0.2 release binary (verified as in `dayzmake-linux.md`):

- By hand over stdin: `initialize` answered `serverInfo` `dayzmake` `3.0.2`; `tools/list` returned 23 tools (those of
  section 5 without `api_grep`, `api_config` and `extract`); `pbo_verify` of the AutoTest mod built with `dayz-mod-pack.sh`
  answered `signature is valid`, and of the same PBO with one byte flipped `isError: true` with
  `PBO checksum mismatch`; `api_chain PlayerBase` answered the chain; `pbo_inspect` with an argument `pbo`
  instead of `path` answered `isError: true`, `missing required argument "path"`; `pbo_cat` of `config.bin` without `target` answered `isError: true`,
  `the entry is not UTF-8 text (486 bytes); pass target to write it to a file`.
- Through a client (Claude Code, the server registered by the `dayz-dev` plugin): `api_chain CarScript` answered
  `CarScript > Car > Transport > Pawn > EntityAI > ...`; `pbo_inspect` with a path relative to the shell's
  folder failed with `No such file or directory` because the server's working directory was the session's
  project folder, and the same call with the absolute path listed the PBO's header extensions and five entries.
  That server process was still running a dayzmake binary that had since been replaced on disk by v3.0.2
  (`/proc/<pid>/exe --version`: `v2.0.0`), which is the version caveat of section 2.

Not measured: any other MCP client, Windows, `binarize`/`proton_binarize` through the server.
