# DayZ 1.30 on a running server: what was measured, not only diffed

`dayz-1-30-mod-workflow.md` and the other `dayz-1-30-*.md` references come from vanilla script diffs. This page
holds what was observed by booting test mods on a dedicated server: things a diff cannot show (a function that
silently does the wrong thing, a path rule, a crash), plus the community-framework facts a 1.30 server needs.

Source: bzed's own measurements, contributed to this Pack under its MIT licence by the author, from
`bzed/dayz-dev-plugin@6112ac5`: `compatibility/version-130.md` (cited as `V:<line>`),
`frameworks/community-framework.md` (`CF:<line>`), `frameworks/expansion.md` (`EX:<line>`) and
`scripting/client-server.md` (`CS:<line>`); only the author's own sections of the last three were taken. Platform:
the native **Linux** `DayZServer`. 1.30 is the stable release; the author re-tested the whole plugin on DayZ 1.30 stable (the author's report, 2026-11-13; build not recorded here). An entry's build says where it was first measured: the 1.30.164014
pre-release (`1.30.164014.27`, 2026-10-02, then on Experimental) unless it names 1.30.164200 (`1.30.164200.56`, build
25963285, 2026-10-23), 1.30.164078.38 or 1.30.164289. Windows servers
were not tested; where a Windows rule differs, `dayz-test-ingame` says so. The rig to repeat any of it:
`dayz-test-ingame/references/linux-native-server.md`.

## 1. The version define

- The engine defines only the current version: the `defines:` of a 1.30 server's `Module:` lines contain
  `DAYZ_1_30`, and 1.30 does **not** define `DAYZ_1_29` (1.29 did not define `DAYZ_1_28`) (`V:30-34`).
- So write plain 1.30 code without a version `#ifdef`. A mod that must still load on 1.29 puts the **old** code
  under `#ifdef DAYZ_1_29` and the new code in `#else`, so the new code stays the default on 1.31+;
  `#ifdef DAYZ_1_30` would drop the code again on 1.31 (`V:36-39`).
- `string v; g_Game.GetVersion(v);` gives the full runtime build, e.g. `"1.30.164014.27"`; use it for logging. It
  cannot select code that would not compile; only a define can (`V:40-41`).
- A mod's own `defines[] = {"MYMOD"};` in `CfgMods` works with `#ifdef MYMOD` (`V:42`). The mod name of a loaded
  mod is a define too (`#ifdef AutoTest`; `dayz-test-ingame/references/linux-headless-client.md`).
- `BUILD_EXPERIMENTAL` and `DIAG_DEVELOPER` exist only on diag/experimental builds; never use them to mean
  "1.30" (`V:43-44`).

## 2. `FindFile` and file paths (DZEXP-134)

**Current state: fixed in 1.30.164200.** On build 25963285 `FindFile` resolves `$profile:`, `$mission:`, `$saves:`
and `$storage:` again, and backslash patterns work too. The script declarations of `FindFile`, `FindNextFile`,
`CloseFindFile`, `FindFileHandle`, `FileAttr` and `FindFileFlags` in `1_Core/proto/EnSystem.c` are byte-identical to
1.29: BI fixed the native binding only, so nothing needs a new signature (`V:48-56`). Measured matrix on 25963285,
with `-profiles=profiles` inside the server folder and with an absolute `-profiles=/var/tmp/<dir>` outside it, both
the same (`V:58-72`):

| Pattern | Result |
|---|---|
| `$profile:*`, `$profile:fftest/*.json` (also with `\`), with `FindFileFlags.DIRECTORIES` | the profile folder's entries; files and the `sub` dir |
| `$mission:fftest/*.json`, `$mission:*` | `m.json`; the mission's `cfg*.xml` |
| `$saves:*` | `DayZ.cfg` |
| `$storage:*` | `data`, `backup`, `players.db`, `spawnpoints.bin` once the mission runs; nothing in `main()` or on a first boot |
| relative `profiles/fftest/*.json` (either slash) | found |
| `FindFile(..., -1)` | same as `ALL` |
| `CF.FindFileEx` (Workshop CF 1.5.9 of 2026-10-12) | passes through to `FindFile` |

**Removing the workarounds** (every 1.30 stable server is on 164200 or later, since clients must match)
(`V:74-93`):

- `CF.FindFileEx(...)` → `FindFile(...)`, same arguments. Leaving it costs only a test file
  `$profile:cf_findfile_dz130_test`, so it is cleanup, not a fix; a mod that needed CF only for it can drop CF.
- A copied `YOURMOD_FindFilePath(p)` wrapper → plain `p`, then delete the helper and the leftover
  `$profile:yourmod_findfile_dz130_test` / `cf_findfile_dz130_test` files. (The helper is not shipped here: it only
  served 1.30 builds before 164200.)
- The profile folder no longer has to sit inside the server executable's folder; an absolute `-profiles=` works with
  plain `FindFile` and with `CF.FindFileEx`. A mission folder or `-storage=` outside it was not tested.
- Keep the loop shape: the first match arrives in `fileName`, then `FindNextFile`, then `CloseFindFile`; results are
  bare names, so open each by the placeholder path (`"$profile:MyMod/" + fileName`). Enforce has no `do { } while`
  (`Can't find variable 'do'`), so loop with `bool found = fileName != ""; while (found) { ...; found = FindNextFile(h, fileName, attr); }`
  (`V:165-177`).
- Before removing anything on an unknown server, check `g_Game.GetVersion(v)`: there is no define for the point release.

**History, 1.30.164014 and the 1.30 release (25956772):** `FindFile` ignored the placeholders and, with no error,
listed the server's working directory instead (`FindFile("$profile:*")` returned `DayZServer`, `addons`, `keys`, ...);
backslash paths found nothing. BI tracked it as DZEXP-134 (per the ticket, the binding passed the `FindFileFlags`
value where the reworked native expects a file system index). The workarounds were `CF.FindFileEx` (CF 1.5.9+), or a
port of it for mods without CF, and both reduced an absolute `-profiles=` to its last component, which is where the
announced "profile folder must be inside the server folder" rule came from (`V:98-115`, `CF:179-206`). Every other
file function worked with the placeholders on those builds (`V:117-128`).

**Still true on 25963285** (`V:90-91`, `V:129-137`, `V:202-204`):

- **`$storage:` is not available during mission start.** `FileExist`, `MakeDirectory` and `OpenFile` on it returned
  false in the `MissionServer` constructor, `OnInit()` and both sides of `OnMissionStart()`, and true from the first
  `MissionServer.OnUpdate()` / `CallLater` tick, 7-10 s later. On the very first boot of an instance (no
  `storage_1` yet) it stayed unavailable for the whole 60 s run: fall back to `<mission folder>/storage_<instanceId>/`.
  The 1.30 build ignored a relative `-storage=<dir>`; do not combine `-storage` with `$storage:`.
- **`g_Game.GetMissionFolderPath()` returns `""` on 1.30 servers**, while `GetMissionPath()` is
  `mpmissions/dayzOffline.chernarusplus/mission.c`: vanilla's `SetMissionPath` only splits on `\`. Derive the folder
  from `GetMissionPath()`.
- Write forward slashes in every path you build (`dir + "/" + name`); they work everywhere.

## 3. Script module paths in `CfgMods` need forward slashes

With `files[] = {"MyMod\scripts\4_World"};` a 1.30.164014 server loads the mod's config and shows its `CfgMods`
defines, but compiles **none** of its scripts and prints no error: the World module count stays at vanilla (2321).
`files[] = {"MyMod/scripts/4_World"};` fixes it; 1.29 loaded the backslash form. The folder name's case made no
difference. Found in Haralds Armory (Workshop 3325200572), whose five PBOs all used backslashes. Check every
`worldScriptModule`/`gameScriptModule`/`missionScriptModule`, also in a debinarized `config.bin`. Not re-tested on
25963285 and not tested on Windows (`V:140-146`, `V:88-89`).

## 4. Compile failures, measured

- On the 1.30 pre-release a script compile failure was followed by a **segfault** of the server, right after
  `Can't compile "World" script module!`. A crash at boot is often a compile error: read `script_*.log` first
  (`V:215-217`, `V:422`).
- Override signatures confirmed by a failing boot ("marked as override, but there is no function with this name"):
  `EntityAI/ItemBase.ProcessVariables()` → `ProcessVariables(float elapsedTime)`;
  `Construction.SetParent(BaseBuildingBase)` → `SetParent(EntityAI)` (`Construction` now extends
  `ConstructionBase : ConstructionBasic`); `CarScript.ToggleHeadlights()` is gone, use `LightToggle()` on `Transport`
  (`V:219-242`). Adding a parameter, even with a default, changes the signature.
- `Settings`/`GameSettings`/`SettingsMenu` (2_GameLib) were always under `#ifdef GAME_TEMPLATE`: unknown type (`V:253`).
- `modded class` must live in the **same script module as the class it modifies**: `Transport` is a `3_Game` class,
  so `modded class Transport` in `4_World` fails with `Unknown type 'Transport'`; hook `CarScript`/`BoatScript`/
  `MotorbikeScript` instead (`EX:73-74`).
- A string built with `"x" + (bool expression)` crashed a 1.29 server during World compile, with no script error,
  only a crash dump. Use `bool.ToString()` (`EX:75`).

## 5. Silent breakers, measured

- **`OnCEUpdate()` is never called on 1.30.** It is still declared `[Obsolete]` with no body, so an override compiles
  with a warning and never runs: over 2 minutes with 20 spawned items, `OnCEUpdate` 0 calls, `OnCEIterate` 446k
  (`V:295-306`). Port to `OnCEIterate(float currentTime, float elapsedTime)`.
- Obsolete members compile with `SCRIPT (W): '...' is obsolete` (`V:356`).
- **`ERPCs` values shifted**: `RPC_SYMPTOM_PARAM_SYNC` and others were inserted near the top, so every vanilla id after
  `RPC_PLAYER_SYMPTOM_OFF` changed. Mods that send or store vanilla RPC ids as raw ints, or count from one, break. Use
  the enum names and keep mod ids in your own range (`V:266-269`).
- `GAME_STORAGE_VERSION` 142 → 144: back up `storage_1` before the first 1.30 boot; older servers cannot read it back
  (`V:348-349`; the stream itself is in `dayz-persistence`).

## 6. The 1.30.164200 update (25956772 → 25963285)

From diffing the shipped API index of both builds; only the Workbench row was run on a server (`V:271-289`):

| Before | Now | Effect |
|---|---|---|
| `ConstructionPart.GetSupportProvided(int)` / `GetSupportRequirement(int)` returning `int` | `bool GetSupportProvided(int category, out int providedStrength)` / `bool GetSupportRequirement(int category, out int requiredStrength)` | same on `ConstructionPartStaticsSupportData` and `ConstructionPartTypeData.GetPartTypeSupport*`; callers and overrides break |
| `ConstructionPart.TryHandleUtilityParts(EntityAI)` | `TryQueueUtilityPartsUpdate(ConstructionBase)` | utility parts update through a queue (`QueueUpdateUtilityParts`, `UpdateUtilityParts`) |
| `ConstructionPartTypeData.m_UtilityAutomaticBuild`, `GetPartTypeUtilityAutobuildPartsList()` | removed | `TriggersUtilityPartsUpdate()` instead |
| — | `InvertSupportBehavior()`, `ConstructionPartRebuildInvertedSupport`, `ConstructionBase.IgnoreHouseCollisions()` | new |
| `CarScript.IsMoving()` | declared on `Transport`; new `Transport.HasCrew()` | calls keep working |
| `ActionBase` | adds `IsLockTargetOnUse()` | clashes only with a same-named method of another signature |
| `MiscGameplayFunctions.FilterObstructedObjectsByGrouping` | removed | |
| `NavmeshTest*` | `Land_NavmeshTest*` | |
| `Workbench`, `WorldEditor`, `WBModuleDef`, ... callable from game scripts | every Workbench class inside `#ifdef WORKBENCH`; `ResourceBrowser`, `WorldEditor*` gone | **measured**: DabsFramework 1.51 (`SampleMVC.c:33`, `Workbench.Dialog(...)`) fails with `Can't find variable 'Workbench'`, then `Can't compile "Mission" script module!` and a crash at boot. Wrap such calls in `#ifdef WORKBENCH`. An API index that ignores `#ifdef` still lists the classes |

The guard itself is mapped from the sources in `knowledge/workbench-scripting-api.md`.

## 7. Mod load order is not the `-mod` order

`modded class` blocks from several addons stack in addon **compile** order, and that order follows `requiredAddons`
resolution, not the `-mod=`/`-servermod=` string. Measured: a servermod whose `requiredAddons` names
`DayZExpansion_Vehicles_Scripts` compiled right after that addon, at a position unrelated to its place in the
`-servermod` string. A `-servermod` addon does not compile after every `-mod` addon (`CS:22-31`). So no position in the
chain can be relied on; never build a fix on being first or "outermost". Make it order-independent:

- hook an event that provably runs **after** the behaviour you counteract: `EEInit()` runs after the constructor chain,
  so re-enabling damage there beats a constructor-time `SetAllowDamage(false)` from any position;
- identify targets by data (class-name prefix, config flags), not by which mod you assume ran first.

## 8. Community Framework and Expansion on 1.30

**CF** (`CF:2-31`, `CF:53-64`, `CF:285-290`, `CF:320-327`):

- Use the regular Workshop **CF 1.5.9 or newer** (1559212036). CF-Test (1625463737) is obsolete: the 1.5.9 PBOs are
  byte-identical to its last build (checked 2026-10-14). Load only one of them (both declare `JM_CF_Scripts`). The
  current COT (1564026768) needs no COT-Test either. CF's `config.cpp` still says `version = "1.5.8"`; do not test for
  the string.
- CF 1.5.9 compiled unmodified on 1.30.164014 with no `SCRIPT (E)` of its own; 1.30-only code in it is behind
  `#ifndef DAYZ_1_29`. Against 1.5.8 (19 files): `CF.ResolvePath`/`CF.FindFileEx`; ModStorage on `MotorbikeScript`;
  `AdvancedCommunication`, `AnimalBase`, `BuildingBase`, `ZombieBase` create their `CF_ModStorageObject` lazily; a corrupt
  header (CF too new, or more than 256 mods) is rejected with `Corrupt modstorage header, unsupported CF version ... or
  too many mods` and `false` from the load; input bindings keep a persistent `UAIDWrapper` (`CF_InputBinding.m_InputID`
  gone, use `m_InputWrapper`); `JMAnimRegister.Register(pType)` deprecated and empty; `CF_String.LastIndexOf`
  `[Obsolete]`. Storage written by CF 1.5.9 on 1.30 is not loadable by older servers. Hooks and layout:
  `dayz-persistence/references/cf-modstorage.md`.
- Start a CF server with `-profiles=<dir>` **and** `-mission=mpmissions/<mission>`. CF resolves paths from both;
  without `-mission` it falls back to the `serverDZ.cfg` template, which is only the folder name, so `$mission:` and
  `$storage:` pointed nowhere and the diag build printed a `Virtual Machine Exception`. On the native Linux server the
  mission path must be relative anyway (`dayz-test-ingame`). CF needs a writable `$profile:`.
- On diag/experimental builds any `Error()` inside CF ("Could not determine mission folder") shows as a
  `Virtual Machine Exception`.
- A CF module only receives the events it enables: call `EnableUpdate()`, `EnableMissionStart()`,
  `EnableClientReady()`, ... in `OnInit()`; an override without its `Enable...` call is never invoked. Networked
  module variables: at most 256 per module, sync through RPC id 435022, only the dedicated server sends.
- Adding CF to, or removing it from, a server whose storage already exists breaks that storage, and adding it can
  look like a version conflict: `dayz-test-ingame/references/linux-native-server.md`, "Wipe the storage".

**Expansion** (`EX:10-27`, `EX:53-76`):

- DayZ-Expansion-Bundle does not run on its own. Load, in this order: CF (1559212036), **Dabs Framework** (2545327648;
  not pulled in by the Bundle or CF and not in Expansion's own mod list), **DayZ-Expansion-Licensed** (2116157322),
  the Bundle (2572331007), then your mod. The Bundle contains every module, so do not add single-module items such as
  Spawn-Selection. DayZ-Expansion-Animations (2918418331) is needed to drive Expansion cars and helicopters.
- **Without Dabs** the Game module fails with `Undefined function 'Math.Exp'`, followed by hundreds of
  `Bad type 'JsonFileLoader'` / `'array'` cascade errors: fix the first error, not the cascade.
- Measured on 1.30.164078.38 with CF, Dabs, Licensed and Bundle: 1081 Game-module files, no `SCRIPT (E)`, and a
  headless client joined into the world. On 1.30 stable the Workshop Dabs build runs unpatched, and no
  `-newErrorsAreWarnings=1` is needed; the patched Dabs fork and the `-experimental` items were 1.30.164014
  pre-release workarounds only.
- `#ifdef EXPANSIONMODNAVIGATION` / `EXPANSIONMODVEHICLE` detect the modules whatever the mod order (the preload
  scripts define them).

## 9. Read from the sources, not measured

The author's notes from reading CF 1.5.8/1.5.9 and the vanilla 1.30 scripts; no boot behind them. Cited as above,
plus `bzed/dayz-dev-plugin@6112ac5` `systems/vehicles.md` (`VH:<line>`) and `systems/inventory.md` (`IN:<line>`).

- **CF RPCs**: `GetRPCManager().AddRPC(mod, func, this, SingleplayerExecutionType.Server|Client|Both)` (default
  `Server`; the old misspelling `SingeplayerExecutionType` is still declared); the handler is a method of `this` named
  exactly like the RPC, and `AddRPC` returns `bool`. `SendRPC(string modName, string funcName, Param params = NULL,
  bool guaranteed = false, PlayerIdentity sendToIdentity = NULL, Object sendToTarget = NULL)`; a `null` identity from the
  server broadcasts. `SendRPCs(..., array<ref Param> params, ...)` sends several params at once (no `Both`). There is no
  `VSendRPC` in CF 1.5.8 (`CF:115-147`).
- **CF modules**: `CF_Modules<MyModule>.Get()`; `CF_ModuleGame` (3_Game: RPCs, input bindings, networked variables;
  `CF_Module` is a typedef of it), `CF_ModuleWorld` (4_World, client lifecycle events), `CF_ModuleCore`. Remember the
  `Enable...()` calls (section 8) (`CF:187-195`).
- **CF notifications**: `NotificationSystem.Create(StringLocaliser title, StringLocaliser text, string icon, int color,
  float time = 3, PlayerIdentity sendTo = NULL)` (`CreateNotification` is the same); on the server `sendTo` null means
  everyone, on the client it shows locally (`CF:330-341`). `CF_TypeConverter.Get(typename)` returns the converter CF's
  config/XML code uses; there are no `IntToString`/`StringToInt` helpers, use `ToString()`/`ToInt()` (`CF:345-347`).
- **Detecting CF without a dependency**: its `CfgMods` exports `CF_MODULES`, `CF_MODSTORAGE`, `CF_SURFACES`,
  `CF_EXPRESSION`, ...; `#ifdef CF_MODULES` (`CF:400-401`).
- **`EntityAI.SetRequiredSimulation(bool)` / `IsRequiredSimulation()`** control the active state of a custom
  `Transport`; a sleeping body no longer ticks `EOnSimulate`/`EOnPostSimulate` (`VH:288-289`).
- **`InventoryLocationType.TEMP`**: a client-side limbo location during an inventory desync. The values come from C++,
  so use the names, and a `switch` over the type should tolerate `TEMP` (`IN:9-17`).
