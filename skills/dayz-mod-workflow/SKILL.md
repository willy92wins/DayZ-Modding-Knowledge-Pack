---
name: dayz-mod-workflow
description: >
  DayZ mod implementation and debugging protocol. Governs HOW to implement and
  fix, not WHAT. Client/server data mapping (mandatory before each feature),
  anti-confabulation (verify every API), debug hierarchy (top-down 6-layer
  diagnosis), edge case checklists, error catalog of verified recurring mistakes,
  checkpoint/handoff system for context degradation. Use ALONGSIDE domain skills
  (enforce-script-reference, dayz-ui-development, dayz-particles, etc.), not
  instead of them. Triggers: "implement", "write the code", "build the mod",
  "fix the bug", "debug this", "it doesn't work", "actions not showing",
  sprint execution, or any transition from plan to code/fix. Concurrent
  sessions, skill snapshot, live promote during an open session.
  Also: CanBeStarted, CCTLiquid, MotorbikeScript, HouseDestructible, cfggameplay ExternalLockData/SandstormData, PluginUndergroundTriggerManager, NVTypes underground/sandstorm, IsHeadless.
---

# DayZ Mod Implementation & Debug Protocol

Process skill for implementing and fixing DayZ mods. Does not contain domain
knowledge (that lives in domain skills). Ensures domain knowledge is correctly
applied and gaps are detected before they become bugs.
(until 1.29: the six-layer debug hierarchy, SyncVar rules, and E01–E20 catalog below remain the 1.29 contract.) (since 1.30 Exp: client start also gates on `CanBeStarted()`; vanilla water uses `CCTLiquid`; CE adds `MotorbikeScript`/`HouseDestructible`; `cfggameplay.json` gained lock/sandstorm keys. Details: [dayz-1-30-mod-workflow.md](references/dayz-1-30-mod-workflow.md) and ## DayZ 1.30 Exp.)

---

## 1. ACTIVATION CHECK

Pre-code ceremony routing (which gate applies when — Grill A → `dayz-feature-spec` → Grill B → this skill) is fixed by the single source: `<vault>\AI\00_System\workflow.md` §Árbol de decisión pre-código. Do not self-declare this skill mandatory without that context. (SP-050)

Before writing or fixing ANY code:

- [ ] Is there an approved plan/design? If NO -> plan first.
- [ ] Which domain skills apply? Load them NOW (not from memory):
  - Enforce Script -> `enforce-script-reference`
  - UI/layout -> `dayz-ui-development`
  - Particles -> `dayz-particles`
  - 3D models -> `dayz-model-pipeline`
  - PBO packaging -> `dayz-pbo-build`
  - Physics/collision/raycast -> `dayz-physics-engine`
  - Sound/CfgSoundSets -> `dayz-sound-system`
  - AI/infected/creature behavior -> `dayz-ai-patterns`
  - Build+deploy+launch loop -> `dayz-test-ingame`
- [ ] Is vanilla/mod reference code available for key patterns? If NO -> ask user.
- [ ] List all files to implement/fix, in dependency order.
- [ ] Concurrent session: follow
      `references/concurrent-session-snapshot.md`.

---

## 2. PER-FILE PROTOCOL

For EACH file produced or modified:

### 2a. Write/edit the file

Follow all rules from `enforce-script-reference`. When in doubt about ANY
function, class, method, or parameter:

**GOLDEN RULE: If it's not in a loaded skill AND not in vanilla/mod code the
user has provided AND you haven't verified it -> STOP.**

Options when stopped:
1. Search the internet for the exact API/function
2. Check reference files in loaded skills
3. Ask user to provide a vanilla/mod example
4. Mark as ASSUMED in the mini-audit

NEVER use a function because "it makes sense that it would exist."

### 2b. Mini-audit

After each file, include:

```
## Mini-audit: [filename]
| API/Function         | Source                    | Status   |
|----------------------|---------------------------|----------|
| CreateObjectEx       | enforce-ref / vanilla     | VERIFIED |
| SomeWidget.SetColor  | dayz-ui-dev ref           | VERIFIED |
| entity.GetSomeMethod | not found                 | ASSUMED  |
```

**HARD RULE: If >2 items are ASSUMED -> do NOT advance. Resolve first.**

### 2b-linter. Offline Enforce/layout lint

Run the **mandatory structural gate** (`script_validator.py`, and `ui_reconcile.py` if UI present) — complete contract, exit codes, and limits in the "Offline gates" section below. Exit 1 blocks. It is the OFFLINE layer; in-game behavior is covered by DayZ-MCP.

### 2c. Run type-specific checklist (Section 4)

---

## 2.5 CLIENT/SERVER DATA MAP

**MANDATORY before writing ANY feature involving entity state, actions, or UI.**

### Step 1: Fill this table

```
| Data needed       | CLIENT? | SERVER? | Bridge mechanism         |
|-------------------|---------|---------|--------------------------|
| (fill per feature)|         |         | SyncVar / RPC / Cache    |
```

### Hard rules (verified against vanilla EntityAI.c):

- **SyncVar types**: Bool, BoolSignal, Int, Float, Object ONLY.
  `RegisterNetSyncVariableString` DOES NOT EXIST.
- **Bitstream alignment**: Client and server MUST register same SyncVars in
  same order. Mismatch corrupts ALL synced data silently.
- **ActionCondition()** runs on BOTH sides: on the CLIENT for action menu
  display AND on the SERVER as the action-start gate
  (`actionmanagerserver.c:142` calls `pickedAction.Can(...)`; `Can()` calls
  `ActionCondition(player, target, item)` at `actionbase.c:898`).
  ActionCondition must only rely on data available on BOTH sides; a
  client-only cache passes the menu but the server rejects the action
  start silently.
(until 1.29: a listed action was assumed startable once `Can()` passed.) (since 1.30 Exp: the widget can still **show** an action whose `CanBeStarted()` is false; `ActionManagerClient.c:336` does not call `ActionStart`. Info actions override to false — `ActionPartInfo.c:18-21`. See `references/dayz-1-30-mod-workflow.md`.)
- **OnStart/OnFinish/OnUpdate with "Server" suffix** runs on SERVER.
  Use server-only data here.
- Server DOES re-execute `Can()` (and therefore `ActionCondition()`) before
  starting the delivered action (`actionmanagerserver.c:142`) - it does NOT
  blindly trust client selection.
- If you need a string on client -> use ScriptRPC to populate a client
  cache, or encode as int hash via SyncVar. For data read inside
  ActionCondition, the SyncVar route is the only safe one (both sides).
- **If uncertain whether data is client-available -> treat as NOT available.**

---

## 3. CHECKPOINT PROTOCOL

### When to checkpoint:
- After every 2-3 files
- When generating code faster than thinking about it
- After >15 exchanges in implementation mode
- When uncertain about something written 5+ messages ago

### Format:

```
## CHECKPOINT
### Done:
  file1.c - status
  file2.c - status
### Pending:
  file3.c - what's needed
### New uncertainties:
  [things discovered not in the plan]
### Context: [low/medium/high/critical]
  Recommendation: [continue / finish current file / stop + handoff]
```

### Context rules:
- HIGH -> finish current file, checkpoint, recommend new session
- CRITICAL -> stop immediately, write handoff (Section 7)
- NEVER produce code past HIGH context. Quality WILL drop.

---

## 4. CHECKLISTS BY FILE TYPE

### 4.1 config.cpp

<!-- corpus-stardz-2026-09-07 -->

### Script compile order vs -mod= path order (historical)

Mod **script/config load order** is driven by `requiredAddons[]` in each PBO’s config.cpp CfgPatches dependency graph — not by -mod= path order alone. The engine compiles **all mods’** scripts for layer N (ordered by that graph) before layer N+1. Unrelated mods may fall back to ASCII order of CfgMods class names (community note in StarDZ — historical).

- [ ] `requiredAddons[]` lists the **CfgPatches class names** you actually depend on (scripts + config parents), not Steam folder names
- [ ] Soft deps: omit from `requiredAddons` and feature-detect at runtime when optional

Source: CLAIM-STARDZ-REQUIREDADDONS-ORDER — https://github.com/StarDZ-Team/DayZ-Modding-Wiki/blob/main/en/02-mod-structure/01-five-layers.md


### Professional mod scaffold patterns (StarDZ — historical; patterns only)

When starting a non-trivial script mod, prefer this layer split (do **not** vendor StarDZ file bodies into the Pack):

- **3_Game:** constants, config data class, RPC ID enums
- **4_World:** manager singleton, player/event handlers, entity logic
- **5_Mission only:** modded MissionServer / MissionGameplay, HUD/UI, boot hooks
- Ship mod.cpp, Scripts config.cpp with correct CfgMods.defs module keys, stringtable.csv, inputs.xml, build script
- Habit when expanding: RPC endpoint → config field → UI panel → keybind → stringtable entry

Source: https://github.com/StarDZ-Team/DayZ-Modding-Wiki/blob/main/en/08-tutorials/09-professional-template.md (CC BY-SA 4.0; Pack paraphrase).


- [ ] `CfgPatches` class name matches addon folder name
- [ ] `requiredAddons` uses CfgPatches class names:
  - CommunityFramework: `"JM_CF_Scripts"` (NOT `"CommunityFramework"`)
  - DabsFramework: `"DF_Scripts"` or `"DF_GUI"` (NOT `"DabsFramework"`)
  - Vanilla: `"DZ_Data"`, `"DZ_Scripts"`
- [ ] `hiddenSelections[]` count matches `hiddenSelectionsTextures[]` count
- [ ] `scope = 2` spawnable, `1` reference, `0` abstract
- [ ] Inheritance: verify parent exists or is in requiredAddons
- [ ] `inventorySlot` = string for single, `inventorySlot[]` = array for multiple
- [ ] `ghostIcon`: `"set:setname image:imagename"` - verify imageset exists
- [ ] `imageSets` inside `CfgMods > Mod > defs > imageSets`, NOT in root/CfgSlots

### 4.2 Enforce Script - General

Defer to `enforce-script-reference` for full rules. Key verified restrictions:

- [ ] No ternary operators (`? :` does not compile)
- [ ] `ref` only on member fields, never on locals/params/returns
- [ ] Never use `delete` keyword (segfault if references still exist)
- [ ] `foreach`: works, but NEVER directly on getter returns (NPE on 2nd item).
      Assign to local variable first, then iterate.
- [ ] `m_` prefix on all member fields
- [ ] No `new` allocations inside periodic ticks - use m_ fields + `.Clear()`
- [ ] Complex expressions in array assignments can segfault - break into local var first

### 4.3 Networking

- [ ] `RegisterNetSyncVariable*` called in CONSTRUCTOR (not Init)
- [ ] Types: Bool, Int, Float, Object only. NO strings.
- [ ] Same vars, same order on client AND server (bitstream alignment)
- [ ] `OnVariablesSynchronized` override for every registered SyncVar
- [ ] Server guard: `GetGame().IsDedicatedServer()` (NOT `IsServer()` - returns true on client during load!)
- [ ] Client guard: `!GetGame().IsDedicatedServer()` (NOT `IsClient()` - returns false on client during load!)
- [ ] `SetSynchDirty()` after every SyncVar write on server

### 4.4 UI / Layout

- [ ] `.layout` path matches `$PBOPREFIX$`
- [ ] Widget names match script references exactly (case sensitive)
- [ ] Dabs MVC: widget names = ViewController property names exactly
- [ ] `ScriptViewMenu` ghost menu guard: check `if (layoutRoot)` before ops
- [ ] Input lock: `ChangeGameFocus(1)` on open, reverse on close
- [ ] Cursor: `ShowUICursor(true)` on open, reverse on close
- [ ] Cleanup in destructor/OnHide: remove handlers, null refs

### 4.5 Actions

**DayZ Action Pipeline** (verified against vanilla ActionBase.c `Can()` method):

```
1. ConditionMask  - bitwise (vehicle, ladder, swimming, restrain, raised...)
2. Stance         - IsFullBody / IsPlayerInStance / IsRolling
3. Target owner   - if target belongs to another player -> reject
4. CCT.Can()      - ConditionTarget (CCTObject=range, CCTCursor, CCTNone)
5. CCI.Can()      - ConditionItem (CCINone, CCIDummy)
6. ActionCondition()  - custom override, runs CLIENT (menu) AND SERVER (start gate, actionmanagerserver.c:142)
7. FullBody stance    - if full body, verify stance transition
```
(until 1.29: steps 1–7 were treated as the full client start gate.) (since 1.30 Exp: after the widget lists the action, `CanBeStarted()` must be true or the client never calls `ActionStart` — `ActionManagerClient.c:336`. Vanilla pond wash/drink/fill uses `CCTLiquid`, not `CCTWaterSurfaceEx` — `ActionWashHandsWater.c:28`.)

- [ ] CreateConditionComponents overridden with correct CCT/CCI
- [ ] (since 1.30 Exp) `CanBeStarted()` returns true for performable actions; info-only overrides return false
- [ ] (since 1.30 Exp) Water/wash/fill on sea/pond: `CCTLiquid` unless you intentionally diverge
- [ ] ActionCondition uses ONLY data available on BOTH client and server (see 2.5)
- [ ] Target type: `GetType()` for exact, `IsKindOf()` for inheritance
- [ ] **Non-pickupable items**: Use `RemoveAction(ActionTakeItem)` +
      `RemoveAction(ActionTakeItemToHands)`. Keep IsTakeable=true.
      (IsTakeable=false hides item from vicinity panel but does NOT block custom actions)
- [ ] `CanPutInCargo()` / `CanPutIntoHands()` overrides if item shouldn't be stored
- [ ] Verify stringtable key exists or use hardcoded string for testing

### 4.6 .rvmat Materials

- [ ] Stage2 DT: `color(0.5,0.5,0.5,0.5,DT)` - alpha 0.5, not 1.0
- [ ] Stage4 AS: `color(0,1,1,1)` - NO "AS" suffix, R=0
- [ ] Stage6 fresnel: copy from vanilla ref of same shader type
- [ ] Damage/destruct: use vanilla `generic_damage_mc.paa` / `generic_destruct_mc.paa`
- [ ] `forcedDiffuse` alpha: `0,0,0,1` not `0,0,0,0`
- [ ] Compare EVERY stage against known working vanilla .rvmat

### 4.7 Persistence (OnStoreSave / OnStoreLoad)

- [ ] Version field managed by ENGINE - do NOT serialize manually.
      `OnStoreLoad(ctx, version)` receives version as parameter.
- [ ] Save and Load in EXACTLY same order (raw sequential binary stream)
- [ ] Every `ctx.Write()` has matching `ctx.Read()` in same position
- [ ] Always call `super.OnStoreSave(ctx)` / `super.OnStoreLoad(ctx, version)` FIRST
- [ ] Check return value of every `ctx.Read()` -> return false on failure
- [ ] `AfterStoreLoad` for post-load init (not OnStoreLoad)
- [ ] Test: delete persistence files -> verify clean start works

### 4.8 Edge Cases - Logic Patterns

Run for ANY feature with collections, state, or lifecycle:

- [ ] **Empty collection (count=0)**: Loop body never executes.
      Send notifications BEFORE clearing, not after.
- [ ] **Null/empty state**: No group, no flag, no items in slots.
      Guard every access with null check.
- [ ] **State transitions**: active->abandoned, raised->lowered, powered->unpowered.
      Does cache update on EACH transition? Does UI reflect new state?
- [ ] **Cache vs entity lifecycle**: If entity destroyed, is cache cleaned up?
- [ ] **Player reconnection**: Client cache lost on disconnect.
      How is it rebuilt? (RPC on connect? SyncVar re-sync?)
- [ ] **Concurrent ops**: Two players acting on same entity simultaneously.

---

<!-- corpus-stardz-2026-09-07 -->

### External symptom index (pointer only)

For “mod won’t load / works offline but not dedi / UI broken” flowcharts, see StarDZ troubleshooting (historical community guide). Prefer this skill’s error catalog + diagnostic hierarchy first.

https://github.com/StarDZ-Team/DayZ-Modding-Wiki/blob/main/en/troubleshooting.md


## 5. RECURRING ERROR CATALOG

Verified errors committed more than once. Check ACTIVELY during implementation. The full table (Error / Correct / Source) lives in **`references/error-catalog.md`**; the one-line index is here:

- **E01** — `requiredAddons[]={"DabsFramework"}`
- **E02** — `imageSets` in CfgSlots or root
- **E03** — Same variable name in sibling scopes
- **E04** — rvmat Stage4 with `AS` suffix
- **E05** — rvmat Stage2 DT alpha=1.0
- **E06** — rvmat fresnel values guessed
- **E07** — rvmat damage using procedural color
- **E08** — Assuming function exists because "makes sense"
- **E09** — Continuing past context saturation
- **E10** — `forcedDiffuse` alpha 0
- **E11** — string in ActionCondition — not syncable; use an int ID via SyncVar (readable on both sides), a client-only cache passes the menu but fails the server-side `Can()` gate
- **E12** — IsTakeable=false to prevent pickup
- **E13** — Notify AFTER clearing collection
- **E14** — Debug downstream without verifying upstream
- **E15** — Cache not cleaned on state transition
- **E16** — Fix without mapping client/server boundary
- **E17** — SyncVar bitstream client/server mismatch
- **E18** — `IsServer()`/`IsClient()` for server/client guard
- **E19** — Version field manually serialized in persistence
- **E20** — modded vehicle won't drive, `WheelCountPresent()=0` while `WheelCount()=N` — `CfgSlots.<wheel-slot>.selection` must exist in the body FireGeometry LOD with a wheel proxy
- **E21** — (since 1.30 Exp) custom-map `cfgeconomycore.xml` missing `MotorbikeScript` / `HouseDestructible` rootclasses — `exp\worlds_chernarusplus_ce\DZ\worlds\chernarusplus\ce\cfgeconomycore.xml:17-18`
- **E22** — (since 1.30 Exp) visible action widget but F does nothing, or custom pond drink never lists — `CanBeStarted()` / `CCTLiquid` (see E21/E22 in `references/error-catalog.md` and `references/dayz-1-30-mod-workflow.md`)

---

## 5.5 DEBUG/FIX PROTOCOL

When something "doesn't work" after implementation, diagnose TOP-DOWN.

### Diagnostic hierarchy (MANDATORY order):

**Layer 1 - Config/Engine:**
- [ ] `scope` value correct in config.cpp?
- [ ] Class inherits from correct parent?
- [ ] Config compiles without errors?

**Layer 2 - Entity setup:**
- [ ] Entity spawns in-game?
- [ ] IsTakeable setting correct? (true for items with actions)
- [ ] Base class provides expected functionality?

**Layer 3 - Action registration:**
- [ ] `AddAction(MyAction)` in entity's `SetActions()` override?
- [ ] Action class compiles?
- [ ] `CreateConditionComponents` sets correct CCT/CCI?

**Layer 4 - Client conditions:**
- [ ] `ActionCondition()` uses only data available on BOTH sides? (see 2.5 — the server re-runs it as the start gate)
- [ ] Target type check correct?
- [ ] CCT range/component matches expected interaction distance?

**Layer 5 - Server execution:**
- [ ] Server-side methods (`*Server()`) execute?
- [ ] Permissions/validation pass?
- [ ] Data writes succeed?

**Layer 6 - Response path:**
- [ ] RPC sent back to client?
- [ ] Client cache updated?
- [ ] UI refreshed?

### Rules:
- **Never debug layer N+1 until layer N is confirmed working.**
- **Propose fix + explain WHY before implementing.**
- **Confidence < 90% -> ask user before applying.**
- **After fix: re-run edge case checklist (4.8).**

### Measurement discipline before another hypothesis

After confirming static layers, do not automatically jump to another
reading or to a bisection. First prove what the instrument measured and whether
suspicious code could have executed before the symptom:

1. **Establish the question and the instrument (LL-287).** Before basing a
   decision on a measurement, write "this command answers X, not Y" and preserve
   three outputs: `PASS`, `FAIL`, and `INCONCLUSIVE/SETUP_FAIL`. Privacy sweeps
   are case-insensitive and look for variants; a sample ordered by
   path does not allow estimating proportions; a reproduction protocol is not valid
   until producing at least one red with the fix turned off; and a dependency
   error is repeated in the known-good environment before attributing it to the
   repo. If the first instrument concludes "it is clean", confirm with another
   independent instrument.

2. **Mute runtime: receiving probe (LL-261).** If static path is
   verified end to end and runtime remains silent, stop analysis
   by reading and place a minimal probe on the first line of the receiver on each
   relevant side. Every fail-closed guard records, with rate-limit, the reason for
   `DROP` by design. First distinguish "did not arrive" from "arrived and was rejected";
   only then continue through the hierarchy.

3. **Prove temporal reachability before bisecting (LL-304).** In an alleged
   regression, demonstrate that the diff executed before the symptom. If there is no prior
   marker, correlation with the build does not attribute causality: instrument the
   callback observing the effect and capture the full stack to name the
   caller. On client, emit the stack line by line because the logger cuts
   long messages around 255 characters. Only bisect the diff if its
   temporal reachability is proven and the cause remains open.

---

## 6. TESTING WITH FILEPATCHING (DayZDiag fast loop)

> Populated 2026-06-06 from source-verified deep-dive (vanilla v1.24; see
> LF_RollingStone_dev/research/deep-dive-2026-06-06/08-workbench-diagnostico.md). Line refs +-3.

### The fast loop (script-only iteration in seconds)

1. **DayZDiag_x64.exe** (ships with DayZ Tools) defines `DIAG_DEVELOPER`, has **no BattlEye** and
   does **not** require mod signatures (.bisign) — ideal dev runtime.
2. Launch: `-filePatching -dologs -noPause -mission=P:\<mission>` (+ `-connect/-port` for MP,
   `-profile` to boot with EnProfiler on).
3. Edit `.c` under `P:\<Mod>\scripts\...` -> **restart the mission** to reload. There is NO
   runtime hot-reload.
4. `config.cpp`/model/layout changes are NOT file-patched -> those still need the full PBO rebuild.
5. Logs: `%LOCALAPPDATA%\DayZ\*.RPT` (+ `.mdmp` crash dumps alongside; open with WinDbg/VS).

**When to use which cycle**: filePatching loop for script logic (fixes, prints, tuning);
full AddonBuilder+server cycle (R5 grouping still applies) for config.cpp, models, layouts and the
final validation gate.

**Hard stop — 2 cycles without convergence**: two in-game cycles of the SAME type
(patch→rebuild→test) without measurable progress → STOP, do not launch a 3rd. Before the 3rd
rebuild, do (a) offline pipeline-vs-data bisection (Layer 7) or (b) strategy change
(Print/Shape/DiagMenu instrumentation, or ask user). "One variable per cycle"
is the Layer 7 anti-pattern transferred to the in-game loop: illusion of progress, O(N)
rebuilds. Real case (SUB_BRZ s8, `30_Sessions/2026-06-25-introspeccion.md`): "4 patches
without clean test — should have stopped after 2". Hardens R5 "3+ rebuilds" to a cap of 2.


**Client stuck loading (~148 MB) — rotate `storage_1`**: diag client
boots, stays on mod warning screen and does not progress. Its `script_*.log`
freezes after `Module: World`, process responds, and memory stays at
**~148 MB** (a client that really loads exceeds 2,000 MB). It is not lack of
focus nor a process hang. Fix: rotate mission `storage_1`
(`...\DayZServer\mpmissions\dayzOffline.chernarusplus\storage_1` → rename,
never delete) and relaunch; server regenerates it clean. Verified 2026-08-22:
after rotating, the same pair started completely and player joined. The tree already accumulates
dozens of backups with that pattern (`storage_1_stuck-loading-*`,
`storage_1.bak_corrupt-modstorage-*`). Cost to declare: rotating storage erases
persistent world state — spawned vehicles disappear and must
be re-created.

### Debug tooling matrix

| Tool | Build | Use |
|---|---|---|
| `Shape.Create*` / `Debug.Draw*` | ALL builds (retail too) | 3D overlay: spheres/lines/bbox/matrix. `ShapeFlags.ONCE` auto-destroys — never keep that pointer (`endebug.c:133`) |
| `DbgUI.Begin/Text/Check/SliderFloat/Button/PlotLive` | all builds; call every frame in OnUpdate | live tuning panels (`1_core/proto/dbgui.c:59-126`) |
| `DiagMenu` (WIN+ALT in-game) | `DIAG_DEVELOPER` only | register via `modded class PluginDiagMenu` overriding `RegisterModdedDiagsIDs()` (ids via `GetModdedDiagID()`) + `RegisterModdedDiags()`; hard limit 512 IDs (`plugindiagmenumodding.c:52`); wrap mod code in `#ifdef DIAG_DEVELOPER` or it silently no-ops |
| `EnProfiler` | diag/developer builds | `SetModule(EnProfilerModule.WORLD)` -> `Enable(true)` -> `Dump()` to RPT (`1_core/proto/enprofiler.c`); proto natives are not tracked individually (:70) |
| `LogManager` CLI switches | all | `-doLogs -doSyncLog -doInvMoveLog -doActionLog -doWeaponLog -doWeatherLog ...` read at boot, zero recompile (`3_game/tools/debug.c:714-723`) |

### Logging discipline

- `Print/PrintFormat` -> RPT, cheap. `PrintToRPT` forces fflush per call — reserve for messages that
  must survive a crash (`endebug.c:98`).
- `ErrorEx(msg, severity)` auto-prefixes `[Class::Method] :: [SEVERITY]`.
- Server adminlog: `server.cfg` `adminLogPlayerHitsOnly/adminLogPlacement/adminLogBuildActions` +
  `g_Game.AdminLog(text)` (`game.c:668`).

### Known limits (verified)

- No script hot-reload; mission restart per change.
- Workbench ScriptEditor has **no verified breakpoint/step-debug API** — debugging is prints +
  shapes + DbgUI + DiagMenu.
- `GetDiagDrawMode` physics-view indices are engine-side enums, not exposed to script
  (`game.c:780-793`) — drive them from the native DiagMenu.

---

## Offline gates: structural vs behavioral (added 2026-06-29)

An offline gate that passes does NOT authorize declaring "done" if it validates STRUCTURE but the
success criterion is engine BEHAVIOR.

- **Structural gate** (offline, deterministic): class==filename, paths exist,
  topology/winding/UV, selection sums, braces, cited APIs (2b), skeleton/bind
  compared against vanilla. Predicts that asset LOADS, not that it BEHAVES.
- **Behavioral gate** (engine running only, or Buldozer): deform under
  animation, visible render/winding, mass/CoM/collision, get-in, applied proxy
  convention, elbow/wrist IK. NOT derivable offline nor by a sandbox other than the
  engine itself.

### MANDATORY structural gate before declaring anything done

It is not a recommendation or a "see also": **if you have not run it, it is not done.**

```
python tools/dayz-script-validator/scripts/script_validator.py <addon_root>
```

Exit `0` = PASS · `1` = FAIL · `2` = WARN. **Exit 1 blocks**: fixed or
justified in writing in the handoff, with rule id and reason. A WARN is read, not
silently ignored.

If the mod has UI, the gate also includes:

```
python tools/dayz-script-validator/scripts/ui_reconcile.py <addon_root>
```

which crosses `FindAnyWidget`/`FindWidget` against real widgets in `.layout` and
`#STR_` keys against the stringtable — two flaws that compile and only appear on
opening the menu.

Costs under one second on a full addon, so **there is no cost excuse**:
runs on every pass, not just at the end. Catches the family of errors that only
manifests when compiling the module at boot (`Unknown type`, local redeclaration,
missing method override, `delete`, empty `#ifdef`, item override in wrong
`CfgXxx`) and which otherwise is paid for with a multi-minute in-game cycle.

**What this gate does NOT authorize**, and is the whole point of this section: green here
predicts that module COMPILES and that asset LOADS. Says nothing about behavior
of the engine. Behavioral gate remains mandatory separately.

Known coverage: tables in `scripts/shared/vanilla_reference.py` are
deliberately small (linter does not parse `P:\scripts` at runtime), so there are
false negatives by design and never false positives through that path. Green is not proof
of absence.

**Rule**: before iterating on an offline metric, ask "does it correlate with the
behavioral criterion, or is it a proxy the engine can ignore?". Proxy without
demonstrated correlation → ONE behavioral test BEFORE continuing to polish the proxy;
if it does not correlate, stop polishing it.

**Anti-pattern (real cases, week of 2026-06-23)**:
- Character deform: deform-test in Blender reduced edge-stretch 34×→6-9× in ~12
  offline iterations with ZERO in-game improvement — engine skins against the
  REAL OFP2_ManSkeleton from `model.cfg`, not against the FBX armature → false gate
  (`30_Sessions/2026-06-24-LFInfectedBig-s8-offline-gate-false-green.md`).
- Vehicle proxy: `derive_proxy_frame`=identity gave offline "green" 2 times;
  engine applied another convention → body-proxy rotated ~90°
  (`30_Sessions/2026-06-24-MercedesAMGLF-fase2-smoke-FAIL-proxy-rotation.md`).

**Cross-ref**: G3 (honest verification: declare WHAT was verified and what was NOT), Layer 7
(bisection), R5 (do not waste cycles), SP-020 (real gate = compilable tree).

---

## 7. HANDOFF DOCUMENT TEMPLATE

When session ends mid-implementation:

```markdown
# Handoff: [Mod] - Session [N]

## Context
- Plan: [filename]
- Skills needed: [list]

## Done
1. path/file1.c - status, caveats
2. path/file2.c - status, caveats

## Pending
3. path/file3.c - what, dependencies, uncertainties
4. path/file4.c - what, dependencies, uncertainties

## Unresolved
- [ ] uncertainty 1
- [ ] uncertainty 2

## Errors found -> add to Error Catalog if recurring

## Notes for next session
```

## Pre-implementation grill — checklist obligatoria DayZ (added 2026-05-28, LL-043)

BEFORE writing config.cpp / model.cfg / scripts of a DayZ mod, go through this
checklist with the user. **It is opt-out, not opt-in**: generic Mode A Grill
from `workflow.md` does not capture DayZ-specific axes; skipping this regenerates
LL-043 (silent assumptions).

### Presentation rule for non-technical users
For each axis: offer **closed options with recommended default** via
`AskUserQuestion` (not open questions). If user does not understand question,
explain it with a concrete vanilla example, do NOT fill with silent default.
If an answer branches (subsequent changes accordingly), ask **one by one**
(legitimate exception to R18, as in workflow Mode B Grill).

### Ejes a cubrir (mínimo para CUALQUIER objeto colocable/usable)

1. **Crafting (if applicable)** — exact quantities, required tool (yes/no
   and which), animation time, sound. Reasonable default: 2-6 units of
   main material, without tool, 1-3 s.
2. **In-hands carry** — weight (g), `itemSize` (slots — warn if going to be
   "hands only" due to size), carry pose (default vs specific).
3. **Deploy / placement** — hologram sounds, valid surfaces
   (terrain / interior / water), initial orientation, horizontal snap vs follows
   slope, rotation during hologram.
4. **Placed state** — **pickup yes/no and how** (this is critical and is
   very easily silenced: clarify that NOT adding take action ≠ engine
   does not have it by default; if pickup is not wanted, one must
   `RemoveAction(ActionTakeItem)` + `RemoveAction(ActionTakeItemToHands)` +
   `CanPutInCargo()=false` + `IsTakeable()=false`). Damage: hitpoints, sources
   (bullets/melee/weather), behavior at 0 HP (ruin/destroy), drops on
   destruction. `carveNavmesh`. Persistence and lifetime.
5. **Internal cargo** — stores items inside? If wearable: attachment slots
   exposed (subset or all).
6. **Visual / UX** — inventory icon (`.paa`, generate or wait for user),
   `displayName`/`descriptionShort` (language, tone, stringtable.xml with
   `#STR_<PREFIX>_*`).
7. **Spawn / distribution** — crafting only / loot / trader / admin /
   combination. TraderPlus / Expansion Market compatibility if applicable.
8. **Umbrella mod (if it is)** — policy: same PBO for all future objects
   vs sub-mods. Class naming convention (`<PREFIX>_<Objeto>`).
9. **Compatibility with third-party mods** — Expansion / CF / Dabs /
   TraderPlus / territories (BBP, Expansion Territory). Ask what server
   runs.
10. **Advanced phases (if any)** — for wearable characters, vehicles,
    complex crafting: enumerate axes specific to that phase (slots, cargo in
    garments, decay, limits…).

### Anti-patrón a evitar
"User chose X — by implication they will also want Y / Z". NO. Each decision
is confirmed. If an option label contains multiple features ("is placed, has
health, can be picked up"), treat each feature as INDEPENDENT confirmation
before implementing it (in "Mannequin Phase 1" session the label "deployable
base-building" included "can be picked up", user had to cut it by hand
during implementation).

### Plantilla reusable
Real case with default + question per point, serves as template:
`<DayZ Projects>/Mannequin_dev/_grill-pendiente.md`.

### Cross-ref
LL-043, R18 (ask before assuming), R25 (do not add unrequested — extend
to "do not assume unrequested"), R26 (verifiable criteria), workflow.md Grill
Mode A.

---

## Debug hierarchy — Layer 7: Component bisection (added 2026-06-02)

**When to activate**: when the 6 previous top-down levels (logs/RPT/script.log → config → ScriptRPC → engine class hierarchy → client/server data → race conditions) have not isolated the cause and symptom is **binary** (PASS/FAIL, visible/invisible, action shows/does not show, CoM=0/CoM≠0).

**Procedure** (`.p3d` multi-LOD case; pattern generalizes to multi-module mods and multi-phase pipelines):

1. **List of separable components** of the system:
   - `.p3d`: each LOD (Visual, Geometry, FireGeo, ViewGeo, LandContact, Memory, Shadow).
   - Mod: each submodule (modded class, RPC, layout, animation, particle).
   - Pipeline: each phase (extract → assemble → bake → binarize → PBO → deploy).

2. **Build a control + test hybrid**: half-A of working one, half-B of failing one. For `.p3d`: copy .p3d-control, replace its FireGeo+ViewGeo LODs with those of .p3d-test (preserving half A = Visual+Geometry+rest). For mods: in `config.cpp`, inherit from control module and override only members of suspected test module.

3. **Reproduce symptom** in hybrid:
   - If it **fails** → bug is in half B (FireGeo+ViewGeo LODs of test); recurse.
   - If it **passes** → bug is in half A (Visual+Geometry+rest of test); recurse.

4. **Repeat bisecting** until isolating the concrete component. Converges in log₂(N) experiments for N components (3 LODs = 2 bisections; 8 submodules = 3 bisections).

5. **Only then** do you read mechanism (R31) within isolated component and name root cause `path:line`. Bisection isolates component; R31 requires reading code to name cause, not just "it is in component X".

**Anti-pattern to avoid**: varying parameters of suspected component ("what if mass is non-uniform?", "what if topology is tris?", "what if material is metalplate?") before bisecting components. Each variation is a concrete experiment giving the **illusion of progress**, but if initial suspicion is wrong, you spend O(N) variations without reaching the bug. Bisection refutes or confirms suspicion in log₂(N) experiments.

**Real case** (LFQuad N1.5 closed 2026-06-02): LFQuad `.p3d` was spawned with `CoM=(0,0,0)` in deployed ODOL. All initial evidence pointed to Geometry LOD (mass, topology, material). 5 trial-and-error binarizations refuted material/mass-distribution/topology/skeleton/writer; **2 bisection binarizations** (Croco+LFQuad-Geo hybrid + LFQuad-without-FireGeo) isolated cause to FireGeo LOD (a spurious `#Mass#` tagg with zeroes that binarize prioritized over that of Geometry). Handoff: `30_Sessions/2026-06-02-LFQuad-placement-fix-firegeo-mass-CLOSED.md`.

**Preventive (not just reactive)**: for a NEW PATH/PIPELINE (first skinned export,
first proxy convention, first crew-selection, fire mode scope in a
new `CfgWeapons`) run a known-good CONTROL through the same pipeline BEFORE the
1st iteration on your asset. Is there a vanilla one that already does it? Read it / round-trip it
first: debinarize vanilla `.p3d`, read `bin.pbo` of vanilla config, or pass a
vanilla model through your exporter. If the CONTROL fails as well, the bug is in the PIPELINE,
not in your asset. Cases from this week that this would cut short: scope of `Mode_FullAuto`
(eclipsed vanilla — visible by reading vanilla `bin.pbo`, not by theorizing about
model/anim; `30_Sessions/2026-06-28-A6_SR2M-bug10-fullauto-resolved.md`) and mirrored
L↔R mesh (caught when comparing debinarized vanilla skeleton, after ~8 sessions
iterating against FBX rig; `30_Sessions/2026-06-25-LFInfectedBig-mirror-fix-deform-solved.md`).

### Cross-ref
R35 (multi-dimensional differential diagnosis), R35.1 (bisection before trial-and-error, added 2026-06-02 in `codex-briefing.md`), R31 (`path:line` mechanism after isolating). LL-079 (the durable bisection lesson), LL-080 (spurious #Mass# in FireGeo, the concrete case).

## (added 2026-06-01) Dev tree vs compilable tree: cite-then-verify of tree before value (SP-020)

When a DayZ mod has two parallel trees (`<MOD>/` compilable + `<MOD>_dev/`
working tree), EVERY `config.cpp`/`model.cfg`/script value cited as ground truth
must identify the source tree. Before citing:

1. Confirm which tree is COMPILABLE (the one user builds/signs/deploys).
   Heuristic: the one having `$PBOPREFIX$` with canonical path, NOT suffixed `_dev`.
2. Read config from compilable tree, not from `_dev`.
3. If both diverge, REPORT divergence as finding (may be desync of
   `_dev` needing rebase), NEVER tacitly pick one as ground truth.

Recidiva docs: LL-073, LL-025 (R8 extendido), handoff 2026-05-29/05-30 LFQuad.

<!-- [merged 2026-06-05 from <claude-home>\skills user copy during plugin-canonical migration] -->
### 4.9 Refactor - state coherence (MANDATORY when consolidating logic across side-effecting calls)

A refactor that moves a guard / validation / rate-limit across an irreversible
engine call (`super.OnStartServer`, `super.OnExecuteServer`, `ObjectDelete`,
RPC send, `SetSynchDirty`, file write) can introduce **orphan state**: the
engine has done half the work, the guard rejects the rest, and the world is
left incoherent.

**For every `return` / early-exit in the refactored function**, list:
- What irreversible engine state has been mutated up to this point?
- If we return now, is the world in a coherent state?

If the answer to the second question is "no" -> the guard is in the wrong
position. Move it BEFORE the irreversible call.

**Verified orphan patterns:**

- **ORPHAN-1: Rate-limit / validation AFTER `super.OnStartServer` of an
  open/toggle action.** Super already flipped `IsOpen()`; rejecting the
  follow-up LFV restore leaves the container physically open with cargo still
  virtualized in `.lfv`. Symptoms: empty open container in-game, `.lfv` file
  not consumed.
  **Fix**: rate-limit pre-super, gated on inferred intent (preState == CLOSED
  for toggles; asserted CLOSED for split-open hooks). See `LFV_ActionProbe.RateLimitAllowsOpen`
  in LF_VStorage Capa 6 v3.1.
- **ORPHAN-2: SyncVar write between irrelevant `SetSynchDirty()` calls** without
  matching the constructor registration order. Bitstream desync on client;
  values appear stale-but-correctly-typed. Fix: register and write in same
  fixed order; one `SetSynchDirty()` after a coherent batch of writes.
- **ORPHAN-3: Entity destruction inside `foreach` over a registry**, then
  continuing the loop. Stale ref at next iteration -> NPE or crash. Fix:
  collect entities-to-delete in a temporary array, delete after the foreach.

**Process rules:**

- **"Preserves original behavior" is a NON-GOAL** when the original is buggy.
  Treat each "preserved" semantic as a hypothesis to verify, not a fact to
  defend. For every "preserved" line in your audit, ask: "should this be
  preserved?"
- **"Pre-existing / not introduced by the refactor" is not exemption.** If the
  audit notes a sketchy pattern with that label, STOP and get explicit user
  signoff (fix-now / flag-for-later). Quietly continuing is the worst option.
- **When auditor or user catches one orphan-state bug, immediately grep
  cross-codebase for the same pattern in sibling files.** The bug rarely
  lives in just one place. Verified: in LF_VStorage Capa 6, after the
  auditor caught ORPHAN-1 in `RunToggleAfterSuper`, sibling-grep
  revealed `LFV_ModdedActionOpenRaGItem` and `LFV_ModdedActionFurnitureOpen`
  carried the same pre-existing orphan pattern that should have been fixed
  in the same pass.

---

## 8-9. AUDIT ESCALATION (severity discipline + multi-agent isolation) -> `references/audit-escalation.md`

Severity-inflation discipline (crash vs VM exception vs corruption vs degradation vs cosmetic — verify before labelling) and multi-agent audit context isolation (independent `path:line` per agent, ≥1 adversarial agent, ≥20% random re-check) are in **`references/audit-escalation.md`**.

> These OVERLAP the **`rigorous-data-audit`** skill — invoke that skill to RUN a data-critical audit (its 7-step, 8-parallel-auditor workflow); the reference here is only the severity-labelling + auditor-independence protocol note.

## (added 2026-07-23) When changing a scheduler interval constant, update verification harnesses with hardcoded counts

Origin: LFPowerGrid T4 W4-F02 changed `LFPG_VANILLA_FLUSH_S` from 30s to 5s (write-behind).
The `verify_corrective` gate (16 checks on mod) FAILED on `PERF_SCHEDULE_MAP` because its
harness `verify_scheduler.py` had EXPECTED counts hardcoded with old value
(`FlushVanillaIfDirty: 2` in window of 60000ms = 30s; now `12` = 5s; and `10`→`60` in
300000ms). The only diff was that callback; fix was updating the 2 EXPECTED maps of
harness, NOT the mod.

Rule: when a code change touches a `*_MS` / `*_S` constant feeding a
periodic scheduler/timer, BEFORE declaring build/verify gate PASS:
1. Grep verification harnesses (`tools/verify_*.py`, `tests/`) for hardcoded
   counts/intervals of THAT callback (EXPECTED maps, frozen cadence snapshots).
2. Recalculate expected count = `window_ms / new_interval_ms` and update harness
   (APPEND-only or minimal edit, with traceable comment citing motivating finding).
3. Confirm that ONLY that callback differs — remaining map counts must match exact.
   If another callback differs, it is an UNINTENDED cadence change: investigate before touching
   harness.
4. A verify gate FAIL due to a LEGITIMATE interval change is NOT code failure:
   it is outdated harness. Updating it is part of closing batch. Do NOT mask: sole
   diff must be intentional one, verified item-by-item against expected map.

## Rules promoted from lessons corpus (added 2026-07-27)

Promoted from `AI/20_Knowledge/lessons-learned.md` to arrive via trigger instead
of depending on someone remembering to look them up. Each rule cites source `LL-NNN`;
complete entry (symptom, origin, evidence) lives there. Do not remove citation: the index
`lessons-index.md` detects promotion by looking for that reference inside skills.

- **LL-013** — Isolate physics, inheritance, and `SimulationModule` changes from features, and validate each structural block separately. Do not approve `modded`/`extends` classes until they pass CfgConvert, actual compilation, and in-game gate.
- **LL-061** — Before another bake on the same `.p3d`/`.pbo`, close the pending gate of previous bake or declare it blocked with explicit cause. Do not accumulate changes rendering the next verdict ambiguous.
- **LL-147** — For any synced state failure, instrument client and server from first cycle and confirm value on the side where symptom is observed. Treat every discrepancy between sides as first-class data before proposing fix.
- **LL-199** — In client-side probes, put `t`, position, and state first; leave raws and flags at end. Keep each useful payload below ~225 characters to absorb logger wrapper.
- **LL-200** — Emit `t=GetTickTime()` at beginning of each diagnostic line. Estimate server↔client offset with median of RPC REQUEST/ACK pairs, interpolate one series over the other, and discard samples with excessive gaps.


## Live bug-ledger closure protocol (SP-236, added 2026-08-31)

Every new pilot-visible symptom gets a row in `<Mod>_dev/bugs.md` before the next debug
cycle. Search the ledger's `alias` fields first. A regression of a known symptom updates the
existing row; it is never archived as a new bug.

A deployed fix records `F@<hash>`, but that token does **not** mean fixed. Close the row only
with a named gate result or the user's verdict on that exact hash. Silence can adjudicate a
previously reported symptom only when the relevant regime was exercised and the observation
window is recorded. This keeps build identity, exercised behavior, and closure evidence in
the same live ledger.

## Compile gates cover both runtime sides (SP-208, added 2026-08-31)

A server compile pass is not a build-wide script gate. Code below `#ifndef SERVER` can be
absent from the server compilation while still breaking the client module. Before accepting
a build, boot and inspect both server and client script compilation. Record a pass for each
side separately. Wrapping a failing declaration in a side guard is not a fix unless the side
that still compiles it also passes.

The language rule for where a `modded class` declaration must live belongs to
`enforce-script-reference`; this workflow section governs the two-sided compile gate.

## Script-module capacity is calibrated by family (SP-209, added 2026-08-31)

The `SCRIPT : Module: World; ... used X/33554 kB` line reports a shared roughly 32 MiB arena
for vanilla and all loaded mods. Physical source lines, file bytes, and file count are not a
capacity model. Comments can be free while declarations, generic materializations, and
compiled method bodies consume structure and bytecode.

Do not use a global `kB/class` constant. Measured generic specializations formed one
5.6-6.6 kB family, while small shell classes measured 0-1 kB and two heavy source classes
measured 139 kB. Size a reduction with same-family before/after engine pairs. Count class
declarations case-sensitively so a variable such as `Class x` is not mistaken for a
`class X` declaration.

When a module approaches capacity, remove or parameterize repeated script declarations
before minifying text. A public `config.cpp` classname does not require a homonymous script
class; it can bind to the nearest scripted ancestor. Keep public config names and
`types.xml` entries while collapsing redundant script subclasses, then remeasure the same
module log on both sides.

## Cross-process divergence shape (SP-215, added 2026-08-31)

LL-199 and LL-200 already govern client payload length, `t=GetTickTime()`, clock-offset
calibration, interpolation, and gap rejection. After that alignment, use the shape of the
divergence series as a diagnostic: a sawtooth means correction arrives and the system then
re-diverges, which points at replay determinism; a monotonic rise or plateau with no reset
means the transform is not receiving correction, which points at mechanism gating. Do not
interpret shape until both clocks and sample gaps have passed those existing gates.

## Fit the clock offset on the axis you are NOT investigating (SP-385, added 2026-09-09)

LL-200 says to estimate the server↔client offset and interpolate one series onto the
other. It does not say which components to fit on, and the obvious choice is wrong:
minimising the full 3-D distance **absorbs a real single-axis divergence into the
fitted offset** and removes it from the residual. The measurement then reports "the
two sides agree" for a defect that is present, with no symptom that anything failed.

Restrict the fit to the axes NOT under investigation, and leave the axis in question
as a measurement rather than a fit parameter.

Measured 2026-09-04 on LFHeli: fitting horizontal X/Z only gave a 6 mm median
residual over 405 cells and left a post-landing height divergence of 0.169 m p50,
0.833 m max, standing. A full 3-D fit would have spent that height on the offset.

Two corollaries:

- **Where the reference side is CONSTANT the residual is immune to offset error.**
  With the airframe resting and the server reporting `|vy| <= 0.05`, height on that
  side does not move, so any clock error contributes zero. Prefer that window when
  it exists: the result then does not depend on the fit at all.
- **Validate the fit with a second estimator that shares nothing with it.** A paired
  handshake line logged with `t=` on both sides is independent of the trajectory;
  agreement bounds the alignment error. Measured: the two estimators differed by a
  constant 0.180 s, with 356 of 405 cells within ±0.05 s of that median — which also
  identifies the residual as send→apply latency rather than error.

## Probe independence and time order (SP-357, added 2026-08-31)

Before adjudicating a bug with a runtime probe, prove that the measured quantity is
independent of the transform or constant against which it is compared. A world-space point
computed by applying the entity transform to a fixed model point is not an independent
observation of that transform.

Treat an exactly round ratio, a value equal to a model constant, or a field that is zero in
100% of samples as a probe-integrity alarm before using it as evidence. Verify selection and
memory-point names in the source artifact. Time-series analyzers must preserve order:
global minimum-to-maximum arithmetic can report a descent as an ascent when the maximum
occurred first. Report ordered intervals and unrounded values.

## Attribute engine-channel errors to their emitter (SP-135, added 2026-08-31)

An RPT line in `RESOURCES`, `MATERIAL`, or `PHYSICS` can be emitted by a diagnostic call in
the mod, not by the engine's original asset-load path. Before using such a line as root-cause
evidence:

1. Search the mod for every API that can open or inspect the named resource.
2. Correlate the RPT with `script_*.log` from the same run. Matching counts, inputs, and
   instance multiplicity are an emitter signature.
3. Compare the delay with the mod's own `CallLater` intervals.
4. Find a positive proof of load, such as a non-empty resolved `GetShapeName()` or a later
   warning that requires traversing the shape.

A probe that cannot complete must log an explicit inconclusive reason and its input. It must
not leave an unexplained engine-channel error that can be mistaken for a product symptom.

## Prove probe reachability before expanding it (SP-149, added 2026-08-31)

When a probe has never emitted, do not add fields first. Walk upward from its call site to the
function entry and evaluate every `return`, `continue`, side guard, and state guard in the
actual scenario. Then search the probe marker in both server and client logs; a probe can be
silent only on the side being inspected.

Only expand instrumentation after the existing probe is shown to execute and its current
fields fail to discriminate. If a guard exits first, fix the placement or exercise a state
that reaches the call. A probe behind an incompatible guard fails because of where it is,
not because of what it measures.


## A gate on a RANGE scores duration of observation (SP-387, added 2026-09-10)

`p2p` (max minus min), maximum, and any extreme grow monotonically with sample
count. A gate written on one of them scores, without stating it, **how long the
window lasted**, and a variant that simply shortens cells passes it without fixing anything.

Measured on 2026-09-10 on 405 archived LFHeli cells. Within a single group
—upright cells, a single process— the height `p2p` by sample count strata:

| muestras en reposo | p2p mediano |
|---|---|
| [0,5) | 0,0000 m |
| [5,8) | 0,0000 m |
| [8,12) | 0,0031 m |
| [12,18) | 0,1729 m |
| [18,25) | 0,2619 m |
| [25,+) | 0,4726 m |

**The artifact spread (0.0000 -> 0.4726 m) is greater than the effect being
measured with it.** The conclusion relying on it —"flipped cells bounce less",
0.0023 vs 0.2434— does not survive matching by sample count: within a stratum the
sign flips depending on stratum and in most populated one both groups match (0.2247 vs
0.2619). Flipped ones had 7 samples and upright ones 21, and that was whole difference.

**How the gate is written instead:**

1. **FIXED duration window** (e.g. first 3 s of rest), not "entire window".
   This way each cell contributes same observation length and range becomes comparable again.
2. **Statistics that do not grow with n**: a RATE (events per second), a quantile (p90),
   or RMS relative to window's own median.
3. If range is retained, it is retained **alongside its n**, and two ranges with
   different n are never compared.

**Generic signal:** before comparing two groups with a statistic, ask whether that
statistic is a function of sample size. If it is, the comparison measures sampling
design. Related to SP-357 (probe independence): there problem is two
instruments sharing origin, here a statistic sharing destination with clock.

## An aggregate defect rate over MUTATED variants describes the experiment (SP-388, added 2026-09-10)

A tuning campaign corpus contains, by design, deliberately
broken configurations. Averaging defect across entire corpus produces a number not describing
what product does, and that number ends up cited as if it did.

Measured on 2026-09-10, same run. LFHeli landing rollover:

| configuration | cells | upright | tilted | on its side |
|---|---|---|---|---|
| **incumbent (the one shipped)** | 114 | **95.6 %** | 2.6 % | **1.8 %** |
| mutated candidates | 291 | 49.1 % | 21.3 % | 29.6 % |
| **entire corpus (what was cited)** | 405 | 62.2 % | 16.0 % | **21.7 %** |

The 21.7 % was the figure in circulation. Shipped configuration rolls over **1.8 %**, and
broken down by date comes out 100 % upright in six of nine evidence roots. The corpus
measured, above all, how many bad candidates were tested.

And the generating effect deserves to be recorded: between incumbent and worst candidate
only **three fields** change, none by more than 13 % —`AttitudeAlphaMaxRadS2` -5.3 %,
`GroundEffectBonus` +12.6 %, `StabSoftDeg` -4.6 %— and rollover rate goes from 1.8 % to
66.7 %. All three moved at once, so **it cannot be attributed to one**: it is a list
of suspects for a one-field-at-a-time run, not a cause.

**How it is reported:** every defect rate carries attached the configuration on which it was
measured. "X % of cells" without stating which is a figure without a universe (SP-149 and rule
of declaring census). And before opening a redesign plan for a high rate, verify
that rate describes shipped configuration and not queue of experiments.

**Limit to state out loud:** that testbench does not reproduce it does not mean it will not
happen. These cells are scripted landings, in a single spot and **without touching cyclic**;
the only thing they authorize saying is testbench, as is, does not reproduce defect in
shipped configuration.
