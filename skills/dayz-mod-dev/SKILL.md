---
name: dayz-mod-dev
description: "Entry point for DayZ mod development on 1.30 or later, for a mod as a whole: writing, reviewing or porting a mod in Enforce Script (vanilla, Community Framework, Expansion) and taking it through build, local server boot, in-game check and Workshop release, on Windows or Linux. Use it for 'write/fix/review my mod', 'port this mod to 1.30 or later', 'set up a new mod', 'my mod builds but does not work', a mod that spans several domains, CF or Expansion dependencies and load order, or 'what is the workflow from code to Workshop'. It routes to the domain skills (vehicles, weapons, UI, persistence, models, testing, packaging, ...) and carries the rules every mod task needs; invoke it alongside them whenever the work has to end in a mod that loads."
---

# DayZ mod development: the entry point

This skill is the way into the Pack for mod work. It does not repeat the domain skills: it says which one
to read, carries the rules every mod task needs, and runs the loop that turns code into a mod that loads.
Use it **alongside** the domain skill, and alongside `dayz-mod-workflow` (how to implement and debug) once
code is being written.

Target: **DayZ 1.30 or later** (written against 1.30.164289). Builds before 1.30 are not covered; do not write
`#ifdef` branches for them unless the user asks for a mod that must still load on an older server. On a newer build,
re-check a fact against that build's sources before relying on it (next sections).

## The loop

1. **Scope.** A non-trivial feature first gets `dayz-feature-spec` (success criteria, forward contract).
2. **Write.** Read the domain skill (router below) and `dayz-mod-workflow`; look up every API before using it
   (next section).
3. **Build.** `dayz-pbo-build`: validate, pack, sign.
4. **Boot it.** A PBO that builds is not a tested mod. Boot it on a local server, compare the script module counts
   with a vanilla boot, read `script_*.log`. `dayz-test-ingame`.
5. **Verify in game** when the change is visible or player-driven: `dayz-test-ingame`, `dayz-mcp-verify`.
6. **Publish** only when the user says so: `dayz-pbo-build` (`references/workshop-publish.md` on Windows,
   `references/dayzmake-linux.md` on Linux).

## Rules for every task

- **Look it up before you use it.** Every class, method, enum value and config token is checked against the target build's
  sources before it goes into code (below). Unverified names are the most common cause of a mod that does not compile.
- **The engine defines only the current version** (`DAYZ_1_30` on 1.30, the next one's define on the next release).
  Plain current code needs no version `#ifdef`, and `#ifdef DAYZ_1_30` would drop the code on the next release; never
  use `DIAG_DEVELOPER`/`BUILD_EXPERIMENTAL` to mean a version.
- **Forward slashes in every path**, including `CfgMods` `files[]`: on the measured Linux build 164014, with backslashes a 1.30 server compiles none of
  the mod's scripts and reports no error (not retested on 25963285 or Windows); keep forward slashes as the safe habit.
- **Every PBO sits in `@Mod/addons/`.** A PBO at the mod folder root is silently ignored.
- **Load order follows `requiredAddons`, not the `-mod` list** (the measured loading order; launching in dependency order is a conservative recipe, not a guarantee). Never build a fix on a position in the `modded class`
  chain; hook an event that runs after the behaviour you counteract.
- **A `modded class` lives in the script module of the class it modifies** (`Transport` is `3_Game`).
- **A compile error can crash the server** right after `Can't compile ... script module!`: read `script_*.log`
  before anything else when a server dies at boot.
- **`FindFile` works from 1.30.164200**: its signature in `1_core/proto/ensystem.c:520-522` (`FindFile`, `FindNextFile`, `CloseFindFile`) is unchanged [EXACT][CLAIM-130-FINDFILE-PROTO], and on Linux build 25963285 the author measured `$profile:`/`$mission:`/`$saves:`/`$storage:` working again (the first stable release was broken, see `dayz-1-30-server-measured.md`); `CF.FindFileEx` and copied `FindFile` path helpers are leftovers to remove on that build or later.
- **Never write into Steam's directories for test servers or Workshop folders.** Test servers run from a tree of their own.
  The exceptions are the client's own prefix and mod symlink, which `dayz-client-headless.sh` uses
  (`compatdata/<appid>` of the real prefix and a symlink to the test mod in the client's install folder,
  removed after the run; `dayz-test-ingame/references/linux-headless-client.md`, section 2). This does not
  contradict the Windows `P:\Mods -> !Workshop` deploy in `_shared/dayz-conventions.md`.
- **Uploading to the Workshop is the user's call**; prepare the commands, never run them unprompted.
- On Linux, build and sign with **dayzmake >= 3.1.0**, never upstream armake2: that is built for Arma, leaves `*.c` out
  of the signature and lacks the DayZ-only functions dayzmake adds (`_shared/linux-proton.md`, section 1). dayzmake 3.x fixes a lot of security and file-handling issues of the earlier releases,
  so do not use an older build; download it only with its GPG-signed checksums verified
  (`dayz-pbo-build/references/dayzmake-linux.md`, "Get the right dayzmake").

Details and evidence: `dayz-mod-workflow/references/dayz-1-30-server-measured.md`.

## Look it up before you use it

In this order:

1. **The Pack.** `enforce-script-reference` (`references/verified-api-catalog.md`, `references/dayz-1-30-enforce-script.md`)
   and the domain skill's `references/dayz-1-30-*.md`.
2. **dayzmake's script-API index** (dayzmake >= 3.1.0; offline, exact for the installed build, read straight from
   the game's PBOs and cached, nothing to extract or commit):
   ```sh
   dayzmake api class CarScript --inherited        # members incl. every base class
   dayzmake api find 'OnCEIterate'                 # member lines matching a regex
   dayzmake api chain PlayerBase                   # base class chain
   dayzmake api sub Weapon_Base                    # subclasses;  enum X / defines likewise
   dayzmake api src CarScript --context 5          # file:line of each declaration, 5 lines around it
   dayzmake api grep 'GetGame\(\)\.GetMission\(\)'  # call sites: a regex over every script body
   dayzmake api config CfgVehicles/Hatchback_02    # config class: chain, resolved properties, subclasses
   ```
   Cite the `path:line` that `src` and `grep` print (`--lines <a-b>` prints a range, `--cat` the whole file).
   `--dayz <dir>` picks an install, `--experimental` the experimental branch, `-m cf,expansion` (or a workshop id,
   `all`) adds installed mods. For a tree to read or grep with your own tools, extract only scripts and configs:
   `dayzmake extract --derapify --only '*.c' --only 'config.*' "<DayZ install>" /var/tmp/dz-src` (about 40 MB, a
   few seconds; `pbo-map.tsv` maps each prefix to its PBO). `-f` replaces only an empty folder or an earlier extract
   (one with a `pbo-map.tsv`), never an unrelated one. Both hold Bohemia's code, so they stay local and are never
   committed to a mod or to this Pack.
3. **Online**: `https://diff.yadz.app/api/classes/<Name>.json` (latest build, one class as JSON) and
   BohemiaInteractive/DayZ-Script-Diff for exact bodies. Remote mirrors can lag a release; the local index cannot.

CF and Expansion classes: read their public sources at a pinned commit (Arkensor/DayZ-CommunityFramework,
salutesh/DayZ-Expansion-Scripts), or query the installed Workshop copy with `dayzmake api ... -m cf` / `-m expansion`.

## Router

Match the request, read that skill first; read more than one when the request spans domains.

| Request mentions | Skill |
|---|---|
| Enforce Script, `modded class`, `config.cpp`/`CfgPatches`/`CfgMods`, `ScriptRPC`, sync variables, `CallLater`, inputs | `enforce-script-reference` |
| How to implement or debug, "it doesn't work", client/server split, error catalog | `dayz-mod-workflow` (+ `systematic-debugging`) |
| Spec, acceptance criteria, "ready to code?" | `dayz-feature-spec` |
| `OnStoreSave`/`OnStoreLoad`, CF ModStorage, storage versions, `types.xml`, `events.xml`, Central Economy files | `dayz-persistence` (`references/central-economy-files.md`); audits: `rigorous-data-audit` |
| `serverDZ.cfg`, `cfggameplay.json`, mission files, starting a local server, the mod does not load | `dayz-test-ingame` (`references/server-and-mission-config.md`) |
| PBO, prefix, signing, keys, Workshop | `dayz-pbo-build` |
| Environment check: `P:`, DayZ Tools, workshop folder | `dayz-preflight` |
| UI, `.layout`, widgets, HUD, Dabs | `dayz-ui-development` |
| Cars, trucks, boats / motorbikes (read both) / aircraft | `dayz-vehicles` / `dayz-motorbikes` + `dayz-vehicles` / `dayz-aviation` |
| Firearms / clothing / doors and locks / base building | `dayz-weapons` / `dayz-clothing` / `dayz-doors` / `dayz-basebuilding` |
| Characters and infected / AI (Expansion eAI) | `dayz-characters` / `dayz-ai-patterns` |
| Physics, collisions, ragdoll / sound / particles | `dayz-physics-engine` / `dayz-sound-system` / `dayz-particles` |
| Sandstorm, heat, oil pits / terrain holes, bunkers | `dayz-environment-hazards` / `dayz-underground` |
| Models `.p3d`, LODs, memory points / textures `.paa`, `.rvmat` / animations | `dayz-model-pipeline`, `dayz-p3d-audit`, `dayz-p3d-inspector` / `dayz-texture-pipeline` / `dayz-animation-pipeline` |
| Proxies on a host model / previewing `.p3d`, `.paa`, `.rvmat` / UV atlases | `dayz-proxy-align` / `dayz-3d-viewer` / `uv-clean-atlas` |
| Assets from AI generation or a ripped vehicle | `ai-3d-to-dayz` / `rip-vehicle-import` |
| Animation authoring in Blender, Mixamo retargeting, realistic motion | `blender-animation`, `mixamo-retarget`, `dayz-realistic-animation-director` |
| Blender geometry, render review | `blender-assembly`, `blender-visual-review` |
| Reading a third-party mod | `dayz-pbo-reverse-engineering` |
| Verifying in game through dayz-mcp | `dayz-mcp-verify` |

## Porting or reviewing a mod for 1.30 or later

1. Boot it unchanged on a server of the target build and read `script_*.log` for `(E)` and `(W)`; the first error matters, the rest
   are often a cascade.
2. Walk the 1.30 references of every domain the mod touches (`*/references/dayz-1-30-*.md`) and
   `dayz-mod-workflow/references/dayz-1-30-server-measured.md`. Quick greps over the mod's scripts:
   `ProcessVariables`, `OnCEUpdate`, `m_ElapsedSinceLastUpdate`, `CreateFrontLight`, `ToggleHeadlights`,
   `TakeEntityToCargo`, `TakeEntityAsAttachment`, `CombinationLock`, `GetSupportProvided`, `Is3rdPersonDisabled`,
   `CCTWaterSurface`, raw `ERPCs` integers, `files[]` with backslashes, `Workbench.` outside `#ifdef WORKBENCH`,
   `FindFileEx`, `GetMissionFolderPath`, `$storage:` before the first `OnUpdate`.
3. Report each finding with `file:line` and the replacement, then fix, rebuild and boot again until the log is
   clean and the module counts are above vanilla.
4. Back up `storage_1` before a server's first boot on a new release; older servers cannot read it back.

## Community Framework and Expansion

- CF: the regular Workshop CF 1.5.9 or newer (1559212036), one dependency `JM_CF_Scripts`; `#ifdef CF_MODULES` detects
  it without a hard dependency. Removing CF from a tree whose storage was written with CF is an observed breakage; whether adding CF needs a wipe is a hypothesis that was not isolated — isolate first (rebuild with the same storage kept, or copy the storage aside) before rotating `storage_1`.
- Expansion needs CF, Dabs Framework and DayZ-Expansion-Licensed before the Bundle; the ids, the order and the
  failure without Dabs are in section 8 of the reference below (the one copy to keep current).
- Details: `dayz-mod-workflow/references/dayz-1-30-server-measured.md` sections 8-9; CF storage:
  `dayz-persistence/references/cf-modstorage.md`; Expansion AI: `dayz-ai-patterns`; Expansion market UI:
  `dayz-ui-development`.

## Testing a mod or a server

- **Windows:** the managed cycle through dayz-mcp and `dayz-test.ps1`, in `dayz-test-ingame`.
- **Linux:** the native `DayZServer` from a private tree, the retail client headless under Proton, and the
  self-reporting AutoTest mod: `dayz-test-ingame/references/linux-native-server.md` and
  `references/linux-headless-client.md`; DayZ Tools and DayZDiag under Proton: `_shared/linux-proton.md`.
- Either way: one server per tree, never default ports, a vanilla boot as the baseline, and a deliberate syntax error as the probe when an
  override silently does nothing. One server at a time is a limit for hosts with limited RAM (about 7.5 GB RSS each with the Expansion bundle, measured on Linux), not an engine rule; parallel servers are allowed (`dayz-client-headless.sh` and `linux-headless-client.md`). Compare each script module the mod contributes files to against the vanilla baseline count; an unchanged count in such a module is the signal that its scripts did not load.

## Building, signing, publishing

`dayz-pbo-build`. On Windows: AddonBuilder, DsUtils and the Publisher or SteamCMD (`references/workshop-publish.md`). On
Linux: `"$S/dayz-mod-pack.sh"` (`S` set in the look-up block above) (`init`, `keygen`, `build [--binarize-models]`,
`check`, `publish-hint`) over dayzmake, and the `workshop` uploader (`references/dayzmake-linux.md`). Keep
the private key out of git and out of the upload folder; one key per mod family; sign after the final build.
