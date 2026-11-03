# DayZ modding on Linux: native tools and Proton

The skills in this pack are written for Windows, and on Windows they apply unchanged. This note is
the Linux supplement they point to: which Windows step has a native Linux equivalent, which one runs
under Proton and how, and what was not checked. Read it when a skill names a DayZ Tools program,
`P:\`, PowerShell, `%LOCALAPPDATA%` or `DayZDiag_x64.exe` and the machine is Linux.

Measured on 2026-11-03: Debian testing, Steam native, Proton Hotfix and GE-Proton11-1, DayZ and
DayZ Server 1.30.164289, DayZ Tools build 26405911 (binarize 1.30.164289.70). Everything below marked
**not verified** was not run.

## 1. Pick the route per step

| Windows step in a skill | On Linux | Status |
|---|---|---|
| Pack / sign a PBO (AddonBuilder, DSSignFile) | `armake2 build` / `keygen` / `sign` (bzed's fork, https://github.com/bzed/armake2; the `dayz-dev` skill's `dayz-mod-pack.sh` drives it) | native, **use this** |
| Binarize models (`.p3d`/`.rtm` MLOD → ODOL) | `armake2 build --proton-binarize` (runs BI's binarize.exe under Proton itself) | works; needs a fork build with commit `0a0ce3b` (section 4) |
| Publish to the Workshop (Publisher) | `workshop` uploader (https://github.com/nozwock/steam-workshop-uploader; `dayz-mod-pack.sh publish-hint`) | native, **use this** |
| Cross-check armake2 against BI's own tools | `dayz-proton.sh tool AddonBuilder P:\<Mod> <out> -prefix=<Mod>`; `tool DSCreateKey` / `DSSignFile` / `DSCheckSignatures`; `dayz-proton.sh binarize <P-root> <addon> <out> [files]` | works (section 4); for comparisons, not the build |
| `config.cpp` → `config.bin` (CfgConvert) | `armake2 rapify`, or `dayz-proton.sh tool CfgConvert -bin -dst <bin> <cpp>` | both work |
| PNG/TGA → PAA (ImageToPAA) | `armake2 img2paa`, or `dayz-proton.sh tool ImageToPAA <in> <out.paa>` | both work |
| View a PAA (TexView) | `armake2 paa2img`, the pack's `dayz-3d-viewer`, or `dayz-proton.sh gui TexView <paa>` | all work |
| Object Builder | `dayz-proton.sh gui ObjectBuilder [model.p3d]` | starts, loads a model; editing not exercised |
| Workbench | `dayz-proton.sh gui Workbench` | starts and compiles the bundled scripts; game config needs `P:\dz` (section 3) |
| Terrain Builder, DSUtils GUI, ImageToPAA GUI | `dayz-proton.sh gui <Tool>` | **not verified** |
| Dedicated server (`DayZServer_x64.exe`) | native `DayZServer` (Steam app 223350); `dayz-dev` skill, `testing/local-server.md` | native, preferred |
| Client (`DayZ_x64.exe`) | Proton; `dayz-dev`'s `dayz-client-headless.sh` / `dayz-client-test.sh` | works |
| `DayZDiag_x64.exe` (client or `-server`) | `dayz-proton.sh headless start <state> DayZDiag <args>` | client reaches the main menu; `-server` loads the mission and Central Economy |
| `P:` drive (WorkDrive, `subst`) | a plain directory, mapped by `dayz-proton.sh init <dir>` | works (section 3) |
| PowerShell scripts (`*.ps1`) | rewrite the steps in sh; `pwsh` exists on Linux but the scripts call Windows programs, the registry and `subst` | translate, do not run |
| `%LOCALAPPDATA%\DayZ` logs | `<prefix>/pfx/drive_c/users/steamuser/AppData/Local/DayZ` (section 5) | |
| dayz-mcp in-game bridge | addon works on the Linux server; the Python side needs the Linux port | see `knowledge/linux-proton-findings-2026-11.md` |

Build, sign, binarize and publish with armake2 and `workshop`; they are what this pack's Linux route
is built on. AddonBuilder and Publisher are not needed on Linux. Use the Proton route when the question
is "what do BI's own tools produce", or for the GUI editors that have no native equivalent (Object
Builder, TexView, Workbench, Terrain Builder) and for DayZDiag.

## 2. The cross-app quirk: why DayZ Tools under Proton needs setup

DayZ (221100), DayZ Server (223350) and DayZ Tools (830640) are separate Steam apps. Proton gives each
app its own Wine prefix (`steamapps/compatdata/<appid>`), and nothing crosses between them:

- On Windows the game installer writes `HKLM\SOFTWARE\(WOW6432Node\)Bohemia Interactive\DayZ`, value
  `main` = game folder, and the tools read it (the Launcher, WorkDrive and Workbench binaries carry
  that key name). In the tools prefix that key exists but is empty: the game was installed into
  another prefix.
- `P:` is a `subst` drive on Windows, shared by every program. Wine has no `subst`, and a drive
  letter is a symlink in one prefix's `dosdevices/`, so `P:` exists nowhere unless you create it, and
  it must be created in each prefix that needs it (tools and game).
- A prefix Steam never launched misses what Steam does on a first launch: the registry entries of
  DayZ Tools' `installscript.vdf` (TexView stops at "Missing registry entry
  HKEY_LOCAL_MACHINE/Software\BIStudio\TextureConvert" without them) and the VC++ runtime from
  `Steamworks Shared/_CommonRedist` (Object Builder does not load without `mfc140.dll`).

`skills/_shared/scripts/dayz-proton.sh init <P-root>` handles all of it in private prefixes under
`~/.local/share/dayz-proton` (Steam's own prefixes are not touched): it replays the install-script
registry, adds the game `main` key, installs the VC++ runtime, spends the first .NET start (below),
and links `P:` in the tools and the game prefix. It takes about two minutes once. `doctor` prints what
is installed, the game version of each app, update state and whether armake2 is the right fork.

## 3. `P:` on Linux

`P:` is just a directory. Pick one (for example `~/dayz/P`), put each addon at `P/<prefix path>`
(`P/MyMod/config.cpp` for prefix `MyMod`) and run `dayz-proton.sh init ~/dayz/P`. `winpath` shows the
mapping (`P:\MyMod\config.cpp`), and `tool`/`gui` rewrite absolute Linux paths in arguments to `P:\…`
inside the root and `Z:\…` elsewhere.

Keep the `P:` root small. Binarize scans the folder above the addon it converts (`-addon=` is the
parent of the source folder; `dayz-pbo-build` documents this); from `P:\MyMod` that is the `P:` root.
From a `Z:` path it is a Linux directory, possibly your home, and binarize then burns CPU for minutes
(`dayz-dev` measured it walking `~/.cargo` and a network mount).

Vanilla data under `P:\dz` (what WorkDrive's "extract game data" does on Windows): unpack the game's
PBOs with `armake2 unpack` into `P/` at their prefix paths, or only scripts and configs with
`dayz-dev`'s `extract-dayz-sources.sh`. Workbench run without it compiled its bundled scripts but
logged `No entry 'config.bin/CfgVehicles/…'` for every vanilla class. Whether an extracted `P:\dz`
removes those errors is **not verified**, and neither is a model that references vanilla textures.

## 4. DayZ Tools under Proton: what was measured

All through `dayz-proton.sh` in a fresh private prefix after `init`.

| Tool | Result | Notes |
|---|---|---|
| ImageToPAA | PNG → DXT5 PAA in 3–6 s; read back by `armake2 paa2img` and TexView | paths with spaces work |
| CfgConvert | `-bin` output decodes with `armake2 derapify`; a syntax error exits 1 with the message | a **missing input exits 0** and writes a 26-byte empty `config.bin`: check the input exists |
| DSCreateKey / DSSignFile / DSCheckSignatures | key pair, `.bisign`, "Signature … is OK" | they print nothing on Proton's console; `tool` runs them through `cmd` with output redirected |
| AddonBuilder | `-packonly` and full builds (config.bin, binarized `.p3d`, `texHeaders.bin`), 3–5 s | exits 0 on failure; `tool` reads `[ResultCode]` from `DayZ Tools/Bin/Logs/AddonBuilder.rpt` and returns it |
| binarize (`binarize` subcommand) | MLOD → ODOL v8 | identical bytes to AddonBuilder's binarized model; textures resolved |
| TexView | opens a DXT5 PAA, shows format, size, average colour | |
| Object Builder | opens a `.p3d` (points, faces, LOD, selections shown) | first start shows BI's licence: run it once on your desktop and answer it yourself |
| Workbench | starts, compiles the vanilla script modules from its bundled `dta/`, shows its script-authorization prompt | game config missing without `P:\dz` |
| DayZDiag_x64 client | main menu, v1.30.164289.70, ~20 s | a diag build reports `Error()` as VM exceptions (`crash_*.log`), as on Windows |
| DayZDiag_x64 `-server` | mission loaded from a Linux server tree via `Z:` paths, Central Economy ran, listening on the given UDP port | |

armake2 `--proton-binarize` against BI's binarize run from the `P:` root (same textured cube, alpha
`_ca.paa`): a fork build from HEAD `7dcb3cf` (contains `0a0ce3b`, "run binarize.exe from a P: root with
the addon mapped, so texture alpha is detected") gives **byte-identical** output. An older fork build
differed in 20 bytes: the face's average colour (`00 00 00 FF` instead of `70 83 83 C8`) and its flag
bits, the texture-not-found defaults — the alpha bug the `dayz-dev` skill describes for fork
`782396e`. `armake2 --version` prints `v0.3.0` for both, so the version string does not tell them
apart: if in doubt, build the fork from source, or binarize one textured model both ways and `cmp`.

## 5. Pitfalls

- **One display per prefix.** A prefix's wineserver is bound to the display its first program used.
  A program started later on another display — or after that display is gone, e.g. a stopped headless
  sway — dies with `X Error … BadWindow … X_UnmapWindow`. Run one session per prefix, and stop the
  wineserver when it ends (`headless stop` does; by hand:
  `WINEPREFIX=<prefix>/pfx <proton dir>/files/bin/wineserver -k`).
- **32-bit tools need WoW64 here.** TexView, Object Builder, Terrain Builder, ImageToPAA and
  AddonBuilder are 32-bit. Run bare and without WoW64, Proton uses the host's i386 libraries; without an
  i386 FreeType ("Wine cannot find the FreeType font library") their dialogs show no text.
  `PROTON_USE_WOW64=1` (the script's default) fixed it. Inside the Steam Linux Runtime container
  (`DAYZ_PROTON_RUNTIME=1`) GDI tools crashed on this host (fontconfig error, X error).
- **The first .NET start in a fresh prefix fails**: AddonBuilder crashed (DXVK error) without WoW64
  and hung after its constructor with it; every later start worked. `init` spends that start.
- **Never `pkill -f <tool>`** from a shell whose command line contains that name: it kills the shell.
  Kill by PID, or stop the prefix's wineserver.
- **Client and server versions must match**, or the client is refused with `0x00020013 Client is a
  newer build than the server`. Steam `buildid`s differ per app by design; compare the game version
  (`dayz-proton.sh doctor` prints it) and check `StateFlags` 4 (fully updated) in both
  `appmanifest_*.acf`.
- **Logs**: a Proton program's `%LOCALAPPDATA%` is
  `<prefix>/pfx/drive_c/users/steamuser/AppData/Local` (the Steam client's prefix is
  `steamapps/compatdata/221100`, the script's game prefix `~/.local/share/dayz-proton/game`); pass
  `-profiles=<linux dir>` (rewritten to `Z:\…`) to get them where you want. DayZ Tools write their own
  logs into `DayZ Tools/Bin/Logs`, as on Windows.
- **Case sensitivity**: Linux file systems are case-sensitive and Wine's `Z:` hides that from the
  tools, but native tools (armake2, the Linux server reading loose files) do not. Keep path case in
  `config.cpp`, `.rvmat` and model texture references identical to the files on disk.

## 6. What this note does not cover

Terrain Builder, Publisher, BinMake and the GUI front-ends were not started. Object Builder was
opened, not used to edit. An ODOL produced under Proton was not loaded in game here (the
`dayz-dev` note on `--proton-binarize` says the same of its own output).
