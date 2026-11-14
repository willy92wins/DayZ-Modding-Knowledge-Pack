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
- **Forward slashes in every path**, including `CfgMods` `files[]`: with backslashes a 1.30 server compiles none of
  the mod's scripts and reports no error.
- **Every PBO sits in `@Mod/addons/`.** A PBO at the mod folder root is silently ignored.
- **Load order follows `requiredAddons`, not the `-mod` list.** Never build a fix on a position in the `modded class`
  chain; hook an event that runs after the behaviour you counteract.
- **A `modded class` lives in the script module of the class it modifies** (`Transport` is `3_Game`).
- **A compile error can crash the server** right after `Can't compile ... script module!`: read `script_*.log`
  before anything else when a server dies at boot.
- **`FindFile` works on 1.30 stable and later**; `CF.FindFileEx` and copied `FindFile` path helpers are leftovers to remove.
- **Never write into Steam's directories** (server, client, workshop). Test servers run from a tree of their own.
  The one exception is a symlink to the test mod in the client's install folder, which a client needs to load it;
  remove it after the run (`dayz-test-ingame/references/linux-headless-client.md`, section 2).
- **Uploading to the Workshop is the user's call**; prepare the commands, never run them unprompted.
- On Linux, build and sign with **dayzmake >= 1.0.0**, never upstream armake2: that is built for Arma, leaves `*.c` out
  of the signature and lacks the DayZ-only functions dayzmake adds (`_shared/linux-proton.md`, section 1).

Details and evidence: `dayz-mod-workflow/references/dayz-1-30-server-measured.md`.

## Look it up before you use it

In this order:

1. **The Pack.** `enforce-script-reference` (`references/verified-api-catalog.md`, `references/dayz-1-30-enforce-script.md`)
   and the domain skill's `references/dayz-1-30-*.md`.
2. **A local index of the vanilla scripts** (offline, exact for the installed build). Build it once per game update:
   ```sh
   S=skills/_shared/scripts
   bash $S/extract-dayz-sources.sh "<DayZ install>" /var/tmp/dz-src         # scripts + derapified configs, ~90 s
   python3 $S/build-api-index.py /var/tmp/dz-src/scripts ~/.cache/dayz-api   # or set DAYZ_API_DIR
   python3 $S/dayz-api.py class CarScript --inherited    # members incl. every base class
   python3 $S/dayz-api.py find 'OnCEIterate'             # member lines matching a regex
   python3 $S/dayz-api.py chain PlayerBase               # base class chain
   python3 $S/dayz-api.py sub Weapon_Base                # subclasses;  enum X / src X likewise
   ```
   `src X` names the declaring file; read the body in `/var/tmp/dz-src/scripts/...` and cite `path:line`. The index holds
   Bohemia's declarations, so it is built locally and never committed to a mod or to this Pack.
3. **Online**: `https://diff.yadz.app/api/classes/<Name>.json` (latest build, one class as JSON) and
   BohemiaInteractive/DayZ-Script-Diff for exact bodies. Remote mirrors can lag a release; the local index cannot.

CF and Expansion classes: read their public sources at a pinned commit (Arkensor/DayZ-CommunityFramework,
salutesh/DayZ-Expansion-Scripts), or index an extracted Workshop copy with `build-api-index.py --mod <name>`.

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
  it without a hard dependency. Changing whether a test tree runs CF means wiping its `storage_1` first.
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
- Either way: one server per tree and one at a time, never default ports, a vanilla boot as the baseline, the
  `Module: ...; loaded` counts as the proof that scripts loaded, and a deliberate syntax error as the probe when an
  override silently does nothing.

## Building, signing, publishing

`dayz-pbo-build`. On Windows: AddonBuilder, DsUtils and the Publisher or SteamCMD (`references/workshop-publish.md`).
On Linux: `skills/_shared/scripts/dayz-mod-pack.sh` (`init`, `keygen`, `build [--binarize-models]`, `check`,
`publish-hint`) over dayzmake, and the `workshop` uploader (`references/dayzmake-linux.md`). Keep the private key out
of git and out of the upload folder; one key per mod family; sign after the final build.
