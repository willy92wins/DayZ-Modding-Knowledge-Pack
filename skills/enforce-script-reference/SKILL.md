---
name: enforce-script-reference
description: "Enforce Script reference for DayZ modding: memory (ref, autoptr, Managed, GC), networking (ScriptRPC, SyncVars, OnRPC, OnVariablesSynchronized, OnStoreSave/OnStoreLoad), timers (CallLater 4.5h bug, Timer), type system (typename, Cast, IsKindOf), pitfalls (IsDedicatedServer, segfaults, modded class), config.cpp (CfgVehicles, CfgPatches, custom CfgSlots, inventorySlot bug T148506, inputs.xml, hiddenSelections), action system (CCINonRuined vs CCINone, RemoveAction, IsTakeable), layout-path crash rules (full UI/layout/Dabs → skill dayz-ui-development). Also JsonFileLoader, EXTrace.Start, ScriptInvoker lifecycle, #ifdef SERVER vs IsServer/IsDedicatedServer side checks, custom RPC enums and server-authoritative input patterns, server-side performance patterns (budget scheduler, FPS-adaptive throttling, staggered scan, exponential backoff, ScriptInvoker bus vs polling). Use for ANY Enforce Script code, config.cpp, inputs.xml, or debugging crashes."
---

# Enforce Script Reference — Complete DayZ Modding Guide

Enforce Script is the OOP scripting language of the Enfusion engine used by DayZ.
It resembles C# but has critical differences that cause crashes if ignored.

This skill is organized as a quick-reference SKILL.md (rules, restrictions, checklist)
with detailed reference files for each domain.

---

## ENFORCE SCRIPT HARD RULES — ALWAYS APPLY

These restrictions apply to ALL Enforce Script code. Every rule has caused a real
crash, segfault, or silent failure in production.

### Syntax Restrictions (compiler enforced or runtime crash)

1. **NO ternary operators** — `condition ? a : b` does not compile
2. **`++` / `--` WORK** — both prefix and postfix: `++i`, `i++`, `--i` (verified LBmaster production)
3. **`foreach` WORKS** — `foreach (Type var : array)` and `foreach (key, value : map)`. Avoid foreach on expressions returning temporary collections (may NPE)
4. **`+=` / `-=` WORK** — `x += y;` is equivalent to `x = x + y;` (verified LBmaster production)
5. **String literals as function params WORK** — `MyFunc("hello", "world")` is fine (verified LBmaster production)
6. **Multiline expressions — SCOPE RESTRICTED** — production compiles HAVE broken on multi-line BOOLEAN operators (`&&`/`||` split across lines: LF_VStorage F-NEW-1, HUD_Mod) and on multi-line string `+` continuation (bone-dump Print, dayz-animation-pipeline `references/weapon-in-hands.md:239`). Keep boolean conditions and string builds on ONE line, or split into single-line statements (`ln = ln + ...;`) — this is legacy ENF-R11g (see rule map below). Multi-line function ARGUMENT lists appear in working code, but the exact safe scope is [UNRESOLVED — verify on next diag compile]
7. **NO same variable name in sibling `if`/`else` scopes** — hoist before conditionals
8. **NO `new array`/`map`/`Param` inside periodic ticks** — use `m_` fields, `.Clear()` each tick
9. **Explicit typing always; `m_` prefix on all member fields**
10. **Variables hoisted before loops and conditionals**
11. **Inline string concat WORKS** — `"Count: " + val + " items"` is valid (verified LBmaster production)

### Memory Management Rules

12. **`ref` ONLY on class member fields** — never on function params, local vars, or return types. DayZDiag STRICT compiler makes `ref` on a method param a FATAL compile error while retail tolerates it (see TROUBLESHOOTING, SP-047 row)
13. **Never combine `ref` and `autoptr`** on the same field — pick one
14. **Never use `delete` keyword** — GC handles everything; `delete` on live object = segfault
15. **Non-Managed class instances are weak refs by default** — destroyed when scope ends
16. **Break circular references in destructors** — refcount GC cannot collect cycles

### Networking Rules

17. **All SyncVar writes inside `#ifdef SERVER`** + `SetSynchDirty()`
18. **Every `ctx.Read()` must check return value** → `return false` on failure
19. **`GetGame().IsServer()` returns TRUE on client during load** — use `IsDedicatedServer()`
20. **`GetGame().IsClient()` is NOT reliably true on the client during load (inferred from rule 19, which is the primary-source-verified one; treat as unreliable, do not assume an exact value)** — use `!IsDedicatedServer()`
    - Scope of 19-20: LOAD/INIT time (constructors, module init, OnInit). In post-load callbacks (OnRPC, EOnContact, per-tick), `GetGame().IsServer()` / `IsClient()` are safe and are the standard vanilla pattern

### Timer Rules

21. **`CallLater` loses precision after ~4.5 hours** (32-bit float overflow) — known engine bug
22. **Per-device `CallLater` repeat timers fragment heap** → crash after hours
23. **Centralize all periodic ticks** in a single manager (Register/Unregister pattern)

### Override Rules

24. **`override` parameter names MUST match base class exactly** — mismatched names cause silent runtime failure
25. **`modded class` CAN add member variables** — verified: LBmaster's modded DayZGame adds 10+ member vars in production. Safe for DayZGame. For ItemBase/PlayerBase, external static maps keyed by entity ID is safest if uncertain. STATUS: CONFIRMED for DayZGame, PROBABLE for other classes
26. **Two `modded class` declarations for the same class CAN coexist** across different files

### Serialization Rules

27. **`[NonSerialized()]` attribute** excludes class fields from JSON serialization — use on runtime-only fields
28. **`ScriptInvoker` subscriptions MUST be removed in destructor** — null-check the invoker first: `if (MyClass.Event_X) MyClass.Event_X.Remove(callback);`
29. **`Widget.Unlink()` destroys widget + all children** — preferred over `delete` for UI cleanup

### Action System Rules

30. **`CCINonRuined` for actions requiring item in hand** — `CCINone` means "no item needed"; with `CCINone` + tool check in ActionCondition, the action may not appear when holding the tool
31. **Use `IsKindOf()` not `GetType() ==` for tool checks** — `GetType()` exact match fails on inherited/modded variants; `IsKindOf()` checks full inheritance chain
32. **Match client-side and server-side tool checks** — if ActionCondition uses `IsKindOf`, the server RPC handler must also use `IsKindOf`, not `GetType() !=`
33. **`RemoveAction(ActionTakeItem)` + `RemoveAction(ActionTakeItemToHands)`** — prevents item pickup/drag on placed objects; combine with `IsTakeable()` returning false and `CanPutInCargo()` returning false

### Layout & UI Path Rules

34. **Layout paths MUST match `$PBOPREFIX$`** — if prefix is `SimpleGroup`, paths must be `SimpleGroup/gui/layouts/...` not `LFPG_Territory/gui/...`; mismatch causes crash + ghost menu in UIManager
35. **Guard ScriptViewMenu construction** — check `GetLayoutRoot()` after `new`; if null, set singleton to null (don't `delete`); failed ScriptViewMenu leaves ghost entry in UIManager blocking all future menus

### Custom Input / Keybind Rules

36. **`inputs.xml` root tag must be `<modded_inputs>`** — NOT `<modinfo>` (common mistake); structure: `<actions>` declares input names, `<preset>` assigns default keys
37. **`config.cpp` must reference inputs file** — add `inputs = "ModName\\inputs.xml";` in CfgMods (backslash path)
38. **Three input detection patterns exist, all valid:**
    - Simple: `g_Game.GetInput().LocalPress("UAMyAction", false)` — one-line check
    - Direct: `GetUApi().GetInputByName("UAMyAction").LocalPress()` — per-frame
    - Persistent: `UAIDWrapper wrapper = input.GetPersistentWrapper()` then `wrapper.InputP().LocalPress()` — most robust for stored refs. All three verified in LBmaster production
39. **Avoid keybind conflicts** — check VPP (`kP`=CopyPosition, `kEnd`=Toggle, `kHome`=Menu), COT (`kHome`), LBGroups; choose uncommon keys like `kU`, `kO`

### ENF-R legacy rule map (old numbering cited by project docs)

Project files cite Enforce rules by an OLD numbering (`ENF-R` namespace: DayZ Projects\CLAUDE.md DZ-R5/DZ-R6; dayz-animation-pipeline `references/weapon-in-hands.md:239`) that predates the current 1-39 list. Mapping:

| Legacy ref | Meaning (as recorded at bite time) | Current equivalent |
|---|---|---|
| ENF-R8 | No `new` array/map/Param inside periodic ticks | Hard rule #8 (exact match) |
| ENF-R11b | `Print(string.Format(LOG_TAG + ...))` logging bite — build format strings in single-line statements | No numbered equivalent; nearest anchors: rule #11 + TROUBLESHOOTING row "String concatenation compiles but no output" [legacy — from production bites, see DZ-R5] |
| ENF-R11g | Multi-line boolean operators (`&&`/`||`) and multi-line string `+` continuation break the compile — keep conditions on one line | Hard rule #6 (scoped rewrite carries both evidences) |
| ENF-R10 | Definition not recoverable from any surviving file | [legacy — from production bites, see DZ-R6]; treat comment refs as bite markers, verify against rules 1-39 |
| ENF-R11f | Definition not recoverable from any surviving file | [legacy — from production bites, see DZ-R6] |
| ENF-R12 | Definition not recoverable from any surviving file (NOT the same as current rule #12) | [legacy — from production bites, see DZ-R6] |

---

## REFERENCE FILES — Read Before Building

Pick the reference file matching your need:

| Topic | File | When to read |
|---|---|---|
| Memory management | `references/memory-management.md` | Using ref/autoptr, debugging GC, preventing leaks |
| Networking & persistence | `references/networking.md` | ScriptRPC, SyncVars, OnStoreSave/Load, RPC patterns |
| Timers & performance | `references/timers-performance.md` | CallLater, Timer, EnProfiler, centralized tick |
| Advanced pitfalls | `references/pitfalls-advanced.md` | Compiler bugs (int.MIN, switch/default return, empty #ifdef segfault, wrong-file compile errors), runtime segfaults (map<Widget,T>, ScriptView from RPC, compound expression to array element), operator precedence, modded class rules, variable scoping traps, debugging tools (Print, script console, RPT), string/number gotchas |
| Dabs MVC advanced | `references/dabs-mvc-advanced.md` | ObservableCollection, auto-bind failures, Relay_Command |
| config.cpp patterns | `references/config-cpp.md` | CfgVehicles, CfgPatches, CfgSlots (custom attachment slots), inputs.xml keybinds, inventorySlot overrides (string vs array bug T148506), ghostIcon values, GUIInventoryAttachmentsProps, preventing item pickup, vanilla item parent classes |
| Production UI patterns | `references/production-patterns.md` | UI state management, hover caching, view binding, animation, memory, event handlers |
| Verified API catalog | `references/verified-api-catalog.md` | Reflection/introspection, verified global functions, string/math/config-lookup patterns (consultation catalog, not rules) |
| Llama extraction patterns | `references/llama-extraction-patterns.md` | LM_Planes-derived Enforce/DayZ patterns (CfgMods, custom inputs, **CfgSoundSets parameters**, buildings, custom RPC enums, server-authoritative input, parent/child mod architecture) |
| Vanilla deep-dive additions | `references/vanilla-deep-dive.md` | Source-verified v1.24 facts: recipes/crafting, ComponentEnergyManager, action system, damage pipeline, player internals/sync |
| Weapon fire modes | `references/weapon-firemodes.md` | Fire-mode inheritance (single/burst/full-auto), `Mode_*` root-scope forward-decl trap (SP-031) |
| Server-side performance | `references/server-performance.md` | Budget-per-frame scheduler, FPS-adaptive interval + rolling average, staggered/modulo-gated scan, exponential backoff, `#ifdef SERVER` vs `IsServer`/`IsDedicatedServer`, ScriptInvoker bus vs polling |
| UI / layout / Dabs / widgets | skill `dayz-ui-development` (canonical, HEAD-verified) | Full UI, layout and Dabs MVC work lives there; this skill keeps only hard rules 34-35 (layout-path crash, ScriptViewMenu guard) and CfgMods `inputs` |

---

## SCRIPT LAYER ARCHITECTURE — 3_Game / 4_World / 5_Mission

DayZ loads scripts in order: 3 → 4 → 5. Each layer can reference classes from
its own layer and ALL lower layers, but NEVER higher layers.

### Layer Rules

| Layer | Purpose | Has access to | Does NOT have |
|---|---|---|---|
| **3_Game** | Data, enums, configs, structs, utilities | Engine core, `GetGame()` basics | Entities, World, UI widgets, Mission |
| **4_World** | Entities, actions, items, world logic | Everything in 3_Game + `PlayerBase`, `ItemBase`, `EntityAI`, `Widget`, `UIManager`, `MissionBaseWorld`, Dabs MVC (ScriptView/ViewController via CF) | `MissionGameplay`, `IngameHud`, `Chat`, `InGameMenu` |
| **5_Mission** | Client presentation, HUD, menus, mission hooks | Everything in 3+4 + `MissionGameplay`, `MissionServer`, `IngameHud`, `Chat`, `ChatInputMenu`, `UIScriptedMenu`, `InGameMenu` | — (top layer) |

### What Goes Where

**3_Game** — shared data that both server and client need without world context:
- Enums, constants, defines
- Data classes (structs, configs, serialization helpers)
- Pure utility functions (string, math, file)
- RPC ID enums
- Telemetry/logging

**4_World** — anything that interacts with world entities:
- Device entities (ItemBase, Inventory_Base descendants)
- Actions (ActionBase descendants)
- Entity logic (electrical graph, networking, persistence)
- Kit classes, hologram overrides
- Device controllers (server-side logic)
- **ScriptView/ViewController** (Dabs MVC works here via CF)
- **Pure UI panels** that don't need IngameHud/MissionGameplay

**5_Mission** — client-side presentation that needs Mission-level access:
- `modded class MissionGameplay` / `modded class MissionServer`
- HUD overlays that check `IngameHud.IsHudVisible()`
- `modded class Chat` or chat integration
- Compass, GPS minimap, player list overlays
- Notification system tied to game state
- Phone/ATM HUD elements (persistent on-screen widgets)
- Any UI that needs to know if a menu is open via mission context

### The Bridge Pattern (recommended for LFPG)

Keep logic in 4_World, expose via singletons. Call from 5_Mission bridge:

```
// 4_World: singleton with static access
class LFPG_PhoneHUD {
    static ref LFPG_PhoneHUD s_Instance;
    protected Widget m_Root;
    
    static void Init() { s_Instance = new LFPG_PhoneHUD(); }
    static LFPG_PhoneHUD Get() { return s_Instance; }
    
    void Show(bool visible) { m_Root.Show(visible); }
    void UpdateFrame() { /* render logic */ }
}

// 5_Mission: bridge calls into 4_World singleton
modded class MissionGameplay {
    override void OnInit() {
        super.OnInit();
        LFPG_PhoneHUD.Init();
    }
    
    override void OnUpdate(float timeslice) {
        super.OnUpdate(timeslice);
        // HUD visibility needs IngameHud (5_Mission only):
        IngameHud hud = IngameHud.Cast(GetGame().GetMission().GetHud());
        bool hudVisible = hud && hud.LBIsHudVisible();
        LFPG_PhoneHUD.Get().Show(hudVisible && playerAlive);
        if (hudVisible)
            LFPG_PhoneHUD.Get().UpdateFrame();
    }
}
```

**Key**: The 5_Mission bridge does the `IngameHud` check and passes
the result (bool) down to 4_World. The 4_World class never references
`IngameHud` directly.

### Anti-Patterns (DO NOT)

- **DO NOT** reference `MissionGameplay` from 4_World — won't compile or will crash
- **DO NOT** reference `IngameHud` from 4_World — class not available at that layer
- **DO NOT** put entity logic in 5_Mission — server doesn't load 5_Mission scripts
- **DO NOT** put 109 files in 4_World and 1 in 5_Mission when 15 are pure UI (current LFPG state — works but limits future HUD features)
- **DO NOT** declare `modded class MissionServer` / `modded class MissionGameplay` / `modded class Chat` from 4_World — these are Mission-layer classes. The compile may succeed silently (depending on parse order), but the override is **never bound** to the live instance, so hooks like `OnInit`, `OnMissionStart`, `OnMissionLoaded`, `InvokeOnConnect` never fire from your code. Symptom: no log output, no error, total no-op.

  **Detection**: if you wrote `modded class MissionServer { override void OnInit() { Print("hooked"); ... } }` and the `Print` never appears in `script_*.log` despite the server reaching mission load, check the file's layer. The `config.cpp::CfgMods::missionScriptModule` only loads `Scripts/5_Mission/` — files anywhere else cannot mod `MissionServer`.

  **Fix**: place the file in `Scripts/5_Mission/` (e.g. `Scripts/5_Mission/MyMod_MissionServer.c`). Same applies to any class only available in the Mission module.

### Migration Guide for LFPG

Files that are **fine in 4_World** (entity-coupled or don't need Mission):
SorterView, BTCAtmView, SorterController, BTCAtmController, DeviceInspector,
CameraViewport, SearchlightController, DoorController, RemoteController

Files that **should move to 5_Mission** when HUD features are added:
- `LFPG_CableHUD.c` → if it needs IngameHud visibility checks
- `LFPG_TankHUD.c` → if it needs IngameHud visibility checks  
- Future: PhoneHUD, NotificationOverlay, CompassMarkers, MinimapWidget

**Rule of thumb**: If it renders on the HUD (always visible, not a menu popup)
and needs to hide when the HUD hides → 5_Mission.

---

## TYPE SYSTEM QUICK REFERENCE

```
// typename — the class itself (compile-time)
typename t = MyClass;              // class reference
typename t2 = inst.Type();         // get typename from instance

// ClassName() — script class name as string
string s = inst.ClassName();       // "MyClass"
// same as:
string s2 = inst.Type().ToString(); // "MyClass"

// GetType() — config.cpp entry name (for entities)
string cfgName = entity.GetType(); // config class name (preferred over ClassName for entities)

// Cast<> — safe downcast (returns null on failure)
PlayerBase player = PlayerBase.Cast(someEntity);
if (player) { /* safe */ }

// IsKindOf — inheritance check against config class name
string kWeapon = "Weapon_Base";
if (entity.IsKindOf(kWeapon)) { /* is a weapon */ }

// StaticType — get typename without instance
typename wt = ItemBase.StaticGetType(); // class, no instance needed
```

**Key distinction**: `GetType()` returns the config.cpp class name (what the entity IS in game data), `ClassName()` returns the script class name (what the script class IS in code). For modded items, these can differ. **Prefer `GetType()` for entity identification.**

---


---

## REFLECTION & INTROSPECTION

Moved to `references/verified-api-catalog.md` — reflection/introspection API (GetClassVar, CallFunction, typename introspection, ToType/Spawn, ScriptCaller, load-time attributes).

## ENTITY LIFECYCLE QUICK REFERENCE

```
Constructor      → Called on object creation (both client/server)
EEInit()         → Called after entity is fully initialized in world
SetActions()     → Register player actions (server)
OnStoreSave()    → Persistence: write SyncVars to storage (server)
OnStoreLoad()    → Persistence: read SyncVars from storage (server)
OnVariablesSynchronized() → SyncVar changed on client (client)
EEDelete()       → Entity being removed from world
Destructor       → Object being garbage collected
```

**Registration timing**: `RegisterNetSyncVariableInt/Bool/Float` MUST be called in the **constructor**, not in `EEInit`. SyncVar registration after construction is ignored.

---

## MANDATORY CODE REVIEW CHECKLIST

Before delivering ANY Enforce Script code, verify:

- [ ] No ternary operators (only confirmed syntax restriction)
- [ ] foreach used on stored collections (not temporary method returns)
- [ ] All variables hoisted before loops/conditionals
- [ ] `m_` prefix on all member fields
- [ ] `ref` only on class member fields (never params/locals/returns)
- [ ] No `new` allocations inside repeated timer callbacks
- [ ] `GetGame()` null-checked in all destructors
- [ ] All `Cast()` results null-checked before use
- [ ] All `ctx.Read()` return values checked
- [ ] SyncVar writes wrapped in `#ifdef SERVER` + `SetSynchDirty()`
- [ ] `RegisterNetSyncVariable*` called in constructor, not EEInit
- [ ] Circular references broken in destructors
- [ ] `override` methods contiguous (no custom methods between overrides)
- [ ] Periodic ticks centralized (no per-instance `CallLater` repeat)
- [ ] `IsDedicatedServer()` used instead of `IsServer()`/`IsClient()` for side checks
- [ ] Action tool checks use `IsKindOf()` not `GetType() ==`
- [ ] Actions requiring tool in hand use `CCINonRuined` not `CCINone`
- [ ] Server-side RPC handlers match client-side action condition checks
- [ ] Layout paths in `GetLayoutFile()` match `$PBOPREFIX$` exactly
- [ ] ScriptViewMenu construction guarded with `GetLayoutRoot()` null check
- [ ] Placed objects have `RemoveAction(ActionTakeItem)` + `RemoveAction(ActionTakeItemToHands)`
- [ ] `inputs.xml` uses `<modded_inputs>` root tag (not `<modinfo>`)
- [ ] `config.cpp` CfgMods has `inputs = "ModName\\inputs.xml"` (backslash)
- [ ] Vanilla inventorySlot overrides: use `=` for string-defined items, `+=` only for array-defined items

---

## COMMON API PATTERNS

### Safe Entity Creation
```
// Always check return from CreateObjectEx
Object obj = GetGame().CreateObjectEx(typeName, pos, flags);
EntityAI entity = EntityAI.Cast(obj);
if (!entity)
{
    // Creation failed — do NOT delete kit, do NOT proceed
    return;
}
```

### AI creature spawn — ECE flags (SP-048)

Production spawn of AI creatures = `GetGame().CreateObjectEx(type, pos, ECE_PLACE_ON_SURFACE|ECE_INITAI|ECE_EQUIP_ATTACHMENTS[|ECE_NOPERSISTENCY_WORLD])`. `ECE_INITAI` (=2048, `centraleconomy.c:17`) is what initializes the AI — without it the creature spawns inert. `ECE_NOPERSISTENCY_WORLD` (=8388608, `centraleconomy.c:30`) lets a restart clean it up. Vanilla patterns: `playerbase.c:6491` (SpawnAI), `plugindayzinfecteddebug.c:367`. ANTI-TRAP: the CEApi force-spawn methods (SpawnEntity/SpawnLoot/SpawnDE/SpawnSingleEntity, `centraleconomy.c:335-471`) are DEVELOPER/DIAG ONLY — not a contract on DayZServer_x64 release (same pattern as ExecuteEnforceScript, `game.c:776`). [VERIFIED in-game PRODUCTION 2026-07-02, GameMaster H0-SPIKE-1] Cross-ref: skill `dayz-characters` (custom infected runtime spawn).

### Safe Inventory Operations
```
PlayerBase player = PlayerBase.Cast(GetGame().GetPlayer());
if (!player)
    return;
EntityAI item = player.GetInventory().CreateInInventory(className);
if (!item)
    return;
// item created successfully
```

### Config Lookup / String / Math operations

Moved to `references/verified-api-catalog.md` — ConfigIsExisting/ConfigGet patterns, Enforce string ops (Substring/IndexOfFrom/Replace/ToLower), and Math/vector/world helpers.

## VERIFIED GLOBAL FUNCTIONS

Moved to `references/verified-api-catalog.md` — verified global functions (screen/mouse, profiling, CLI, FindFile, RestApi, sound, notifications, JSON, per-frame callbacks, full keybind API, clipboard/time, bones).

## ADDITIONAL PITFALLS — Style guide & performance

Moved to `references/pitfalls-advanced.md` (appended section) — EnScript style-guide and performance pitfalls: empty #ifdef segfault, int.MIN, switch/default return, bitwise precedence, GetType vs ClassName, notnull, EXTrace, CfgMods defines[], cross-mod #ifdef gates, DEVELOPER vs DIAG_DEVELOPER (SP-037), foreach-on-getter.

## TROUBLESHOOTING — Common Errors & Fixes

| Error | Cause | Fix |
|---|---|---|
| **Segfault on shutdown** | `delete` on live ref object | Replace `delete x;` with `x = null;` — let GC handle cleanup |
| **"Illegal write to memory"** | Allocating arrays/maps inside CallLater repeat callback | Move to member field, `.Clear()` each tick instead of `new` |
| **NPE (null pointer) in Cast** | Using result without null-check | Always: `if (Cast(obj)) { ... }` — never assume Cast succeeds |
| **ObservableCollection not updating UI** | Binding set up but NotifyPropertyChanged not called | Call `NotifyPropertyChanged("PropertyName")` when data changes |
| **Circular reference leak** | Collection holds view, view holds controller | Break in destructor: `m_Controller = null;` — call Clear() on close |
| **UI color flashes on hover exit** | Hover cache not updated when controls disabled | Update cache: `CacheColor(widget, newDisabledColor)` in SetControlsEnabled |
| **Hover state persists after drag** | m_HoveredWidget not cleared on drag start | In OnMouseButtonDown: reset `m_HoveredWidget = null;` |
| **Player stuck with input locked** | Input lock not released in destructor | Add unlock logic to `~ClassName()` destructor |
| **SyncVar not synchronizing to client** | RegisterNetSyncVariable called in EEInit instead of constructor | Move registration to **constructor only** — EEInit is too late |
| **Layout child counts don't match** | Mismatched braces or child block structure | Use `grep '{' layout_file | wc -l` vs `grep '}' layout_file | wc -l` — must be equal |
| **"Undefined variable" in if/else** | Variable declared in one branch, used in sibling branch | Hoist all variables BEFORE conditionals: `string result; if (...) { result = "a"; } else { result = "b"; }` |
| **CallLater loses precision after 4.5 hours** | 32-bit float overflow (known engine bug) | Use centralized Manager with Timer class instead, or resync after 4h |
| **IsKindOf returns false unexpectedly** | Comparing config class name with script class name | Always use GetType() for entities: `if (entity.GetType() == "MyItem")` not `if (entity.ClassName() == "MyItem")` |
| **String concatenation compiles but no output** | Rare edge case with very long concat chains | Break into multiple statements if >5 concatenations |
| **Foreach on temporary NPEs** | foreach on method return creating temporary | Store in local first: `TStringArray arr = GetItems(); foreach (string s : arr) { }` |
| **CONFIG\_NOT\_FOUND in logs** | Reading config path incorrectly | Format: `"CfgVehicles ClassName propertyName"` — space-separated, not dot-notation |
| **RPC executes on wrong side** | SyncVar write outside `#ifdef SERVER` | Wrap writes: `#ifdef SERVER` `SetSynchDirty();` `#endif` |
| **CreateObjectEx fails silently** | Not checking return value or entity cast | Check: `EntityAI e = EntityAI.Cast(obj); if (!e) return;` before using |
| **Modded class member vars unstable** | Some entity classes may have issues with added member vars | Safe for DayZGame. For ItemBase/PlayerBase use external static maps if uncertain |
| **Widget color stays black/invisible** | Widget not in scene tree or parent hidden | Call FindAnyWidget from root, verify all parents are Show(true) |
| **ScriptInvoker crash on shutdown** | Remove() called on null invoker during cleanup | Always null-check: `if (MyClass.Event_X) MyClass.Event_X.Remove(cb);` |
| **Math.Clamp not found** | Outdated reference — it EXISTS | Use `Math.Clamp(val, min, max)` directly. Also: Math.Min, Math.Max, Math.Sqrt |
| **IndexOfFrom not found** | Outdated reference — it EXISTS | Use `str.IndexOfFrom(startPos, searchStr)`. Also: LastIndexOf, Hash, Replace |
| **String copy not working** | ToLower mutates in place | Copy first: `string lower = original + ""; lower.ToLower();` The `+ ""` forces a copy |
| **RPC collision with other mods** | Using low RPC IDs | Use high unique base: `START_RPC = 25416533` then auto-increment enum values |
| **GetScreenPos marker behind camera** | Not checking z component | `GetGame().GetScreenPos(pos)[2] <= 0` means behind camera — hide the widget |
| **Layout path crash + ghost menu** | `GetLayoutFile()` returns path not matching `$PBOPREFIX$` | Path must use exact prefix: if `$PBOPREFIX$` is `SimpleGroup`, return `"SimpleGroup/gui/layouts/file.layout"` |
| **ScriptViewMenu blocks all other menus** | Layout failed but singleton set | Guard: `if (!dialog.GetLayoutRoot()) { s_Instance = null; dialog = null; return; }` |
| **Action not appearing when holding tool** | `CCINone` used with tool-in-hand check | Change to `CCINonRuined` — `CCINone` tells engine "no item needed" so engine may skip action when holding item |
| **Action appears on client but server rejects** | Client uses `IsKindOf()`, server uses `GetType() !=` | Make both sides use identical check (`IsKindOf` preferred) |
| **Keybind does nothing** | Wrong `inputs.xml` format or missing config reference | Must use `<modded_inputs>` root tag + `inputs = "Mod\\inputs.xml"` in CfgMods + `GetGame().GetInput().LocalPress()` |
| **Attachment slot not accepting items** | Vanilla inventorySlot is string, mod uses `+=` | Bohemia T148506: `+=` on string inventorySlot fails silently; redeclare as `inventorySlot[] = {"vanilla_slot", "custom_slot"}` |
| **Item fits in slot but quantity limited** | Vanilla `varQuantityMax` lower than needed | Override `varQuantityMax` in config.cpp: `class Stone: Inventory_Base { varQuantityMax = 16.0; }` |
| **Placed item can be picked up by dragging** | Only `IsTakeable()` overridden | Also need `RemoveAction(ActionTakeItem)` + `RemoveAction(ActionTakeItemToHands)` in SetActions + `CanPutInCargo()` returning false |
| **SetObjectTexture has no effect** | hiddenSelections not declared in config, or selection name mismatch with P3D model | Verify `hiddenSelections[]` in config matches named selections in P3D exactly (case sensitive). Check with `GetObjectTextures()` — empty = no selections |
| **SetObjectTexture wrong slot** | Using wrong index | Index = position in `hiddenSelections[]` array (0-based), NOT the selection name. Barrel has 1 selection at index 0 |
| **GetObjectTextures path differs from config** | Engine normalizes paths | Config: `"\dz\gear\..."` vs GetObjectTextures: `"dz\gear\..."` (no leading backslash). When saving/restoring textures, use GetObjectTextures result, not hardcoded config path |
| **Custom barrel/container missing functionality** | Script extends ItemBase instead of vanilla script class | Extend `Barrel_ColorBase` (not `ItemBase`) for barrels. Always extend the vanilla SCRIPT class that matches the config parent. Needs `requiredAddons` = addon of config parent (e.g. `DZ_Gear_Containers`) |
| **Procedural texture ignored** | Feature may not exist in DayZ SA | Check RPT: "unknown procedural" = stripped. "class/extension not found" = parser exists. color() most likely to work. text(), r2t(), ui(), extension() = test first |
| **SetObjectTextureGlobal may not compile** | Method may not exist in DayZ SA | Do NOT call `SetObjectTextureGlobal` without confirming it exists — if absent, entire script fails to compile. Use `SetObjectTexture` and verify sync in multiplayer instead |
| **Diag server crash: `SCRIPT (E): "Method argument can't be strong reference"` → `Can't compile "World" script module!` (SP-047)** | DayZDiag STRICT compiler rejects `ref` on method params as FATAL; retail compiler tolerates it, so a mod only tested on retail can carry latent ref-on-param bugs that surface only under diag | Drop the OUTER `ref` on the param: `ref array<ref X> p` → `array<ref X> p` (the inner `<ref X>` is legal). [VERIFIED LFPowerGrid 2026-06-18, LFPG_DeviceInspector.c:1100] |

---

## Quick Reference: Most Common Fixes

1. **Crash on close?** → Remove `delete`, check destructors, clear collections
2. **Memory leak?** → Break circular refs in destructors, Clear() on collections before close
3. **UI not updating?** → Call NotifyPropertyChanged when data changes; check binding syntax
4. **Input stuck?** → Unlock in destructor; check ChangeGameFocus(0) + SetDisabled(false)
5. **SyncVar not syncing?** → Move RegisterNetSyncVariable to constructor; check #ifdef SERVER wraps

## Vehicles — crew seated pose, soft-dep, get-in (added 2026-05-23)

### Driver seated pose = GetAnimInstance() int (SP-007)
The seated driver pose is chosen by `Transport.GetAnimInstance()` returning a
`VehicleAnimInstances` int (`scripts/4_world/entities/vehicles/vehicleaniminstances.c`); the
base `Error`s if not overridden, so every drivable vehicle must override it. Vanilla has no
quad pose (CIVVAN=0, V3S=1, SEDAN=2, HATCHBACK=3, BUS=4, S120=5, MULTICAR=6, GOLF=7, HMMWV=8,
ZODIAC=9); the Croco quad reuses V3S.

### Soft-dependency on another mod's anim pack (runtime, with fallback)
To prefer another mod's pose (e.g. survivorAnimations' `CustomVehicleAnimInstances.QUADBIKE=22`)
but fall back when absent: do NOT reference the other mod's enum name (hard compile dependency),
and do NOT use `#ifdef` (compile-time — bakes one behavior, no runtime fallback). Use a runtime
check + raw int:
`return GetGame().ConfigIsExisting("CfgPatches <Mod>") ? <raw_int> : VehicleAnimInstances.<vanilla>;`
This compiles without the mod and picks the pose per the server's modset. Trade-off: the raw int
couples to the upstream enum value — document the literal with a path:line to its definition.

### Get-in: single mount point per seat; bilateral via dual entry components
The seat is decided by the looked-at component (`Transport.CrewPositionIndex(componentIndex)`);
the action is gated by `CanReachSeatFromDoors(selection, fromPos)`, looped over multiple door
selections (`actiongetintransport.c:49-91`). The mount uses a SINGLE getInPos per seat
(`pos_driver`) + a one-sided get-in anim. For "enter from either side", give the seat two entry
components/door selections mapping to the same crew index → the action is reachable from both
sides; a truly mirrored mount, though, needs a mirrored get-in animation.

### Vital parts gate engine start — override IsVital* when cloning a reference vehicle (LL-026)
A drivable `CarScript` decides which parts are required to run via `IsVital*()` methods, all
`true` in the base (`carscript.c`: `IsVitalCarBattery/TruckBattery/GlowPlug/EngineBelt/Radiator/FuelTank`).
The start gate sets `NO_IGNITER` if a vital igniter part is missing (`carscript.c` ~2011-2015:
`IsVitalGlowPlug()` true + no GlowPlug attached → no start), and a vital-but-absent radiator
makes the running engine self-damage each tick (no coolant). So a vehicle that uses
CarBattery + SparkPlug (the common case) MUST override the parts it does not have, or it never
starts. Vanilla shows the pattern: `offroadhatchback.c` overrides `IsVitalTruckBattery()` and
`IsVitalGlowPlug()` to `false`; a quad with no radiator/belt also overrides
`IsVitalRadiator()`/`IsVitalEngineBelt()` to `false`.

### Cloning a binarized reference vehicle: the config is NOT the full contract (LL-026)
When porting a vehicle by copying the `config.cpp` of a workshop reference (Croco, etc.), the
behavioral overrides that make it work live in its **script (`.c`), which is binarized and not
visible** — `IsVital*`, `GetSeatAnimationType`, `CrewCanGetThrough`, the get-in mapping. Cloning
only the config compiles and looks complete, yet the vehicle won't start or won't let you in.
Verify the script side against an **open-source vanilla equivalent** in `scripts/` (e.g.
`offroadhatchback.c`), not against the binarized reference. Two checks that bite:
- **`IsVital*`**: match overrides to the actual attachment set (see previous subsection).
- **get-in action selection must exist in the `.p3d` geometry**: `config` `actionSel="seat_driver"`
  / `"seat_codriver"` and the chain `GetActionComponentNameList → CanReachSeatFromDoors`
  (`carscript.c` `GetDoorConditionPointFromSelection`: `seat_driver→seat_con_1_1`) need a NAMED
  selection `seat_driver`/`seat_codriver` painted on faces of the **Geometry LOD**. The
  `seat_con_*` memory point is only the mapping DESTINATION; the override maps the name, it does
  not create it. Read the `.p3d` back (py3d) and confirm the action selection exists in geometry —
  a vehicle can pass all internal model checks and still have get-in silently fail (this is the
  forward-contract trap of LL-025). Cross-ref `dayz-p3d-audit` for the geometry-side read-back.

### Wheel attachment to simulation: `CfgSlots.selection` ↔ FireGeometry proxy selection (added 2026-05-28)

For PhysX to actually simulate a wheel (`WheelCountPresent() > 0`, not merely `WheelCount() = N`),
the **selection that `CfgSlots…<Slot>.selection` names MUST exist in the FireGeometry LOD of the
body, and must contain the faces of a wheel proxy** (`proxy:\…`). Bohemia wiki
*DayZ:Vehicle_Configuration* states it directly: *"Inside the fire geometry LOD there must be a
proxy object placed with the correct name of the wheel slot so the simulation can attach a
wheel and suspension to that position."*

**Vanilla pattern (Croco quadbike, sedán, etc.):** one consistent name (typically `wheel_X_X`)
used for all three roles — `CfgSlots…<Slot>.selection`, the wheel proxy's selection in the
visual LODs (hide-when-detached), AND the wheel proxy's selection in the FireGeometry LOD. The
*consistency across LODs* is the invariant; the concrete name is free.

**Anti-pattern (silent killer):** hybrid naming — visual proxy in selection name `A` (so
`CfgSlots.selection = "A"` makes wheel-hide work), but the FireGeometry proxy face lives in a
different selection name `B`. `CfgSlots.selection = "A"` then points at a selection that exists
ONLY in visual LODs → the simulation LOD has no proxy in that selection → the wheel never
seats in PhysX. Compile clean, no warning, no RPT error.

**Symptoms (with NO RPT error — silent failure):**
- `WheelCountPresent() = 0` while `WheelCount() = 4` (config is fine).
- Wheels mount as inventory but never spin nor provide traction; engine RPM rises with throttle
  but `speedo ≈ 0`.
- Vehicle sinks slightly into terrain and bounces on its hull (hull collision is still valid).
- Steering animates the wheels (input source is the anim graph, separate from sim) even though
  they do not simulate.

**Detection (offline, py3d):**
1. From `config.cpp > CfgSlots > Slot_*` referenced by
   `…SimulationModule.Axles.<*>.Wheels.<Left|Right>.inventorySlot`, read each slot's
   `selection = "<name>"`.
2. In the body `.p3d`, verify the **FireGeometry LOD** contains a selection named `<name>`
   AND that selection contains the faces of a `proxy:\…` proxy.
3. If missing → P1: vehicle will not drive, will fail silently, every post-mortem will
   mislead you toward suspension/mass/geometry. **Fix this first.**

**Fix (additive, safe — preserves visual hide):** alias the FireGeometry proxy face into a new
selection named `<name>` (the slot's `selection`), without removing the original selection.
py3d: read the existing FireGeo selection that contains the proxy face; build a new
`Selection(lod.points, lod.faces)` with `points`/`faces` dicts copied from it; insert into
`lod.selections` under the slot's `selection` name. Read back and verify everything else
byte-identical (mass, properties, other selections).

**Origin / case study:** LFQuad 2026-05-27. Blocker `wheelPresent=0` cost ~12 failed iterations
over a month, all targeting suspension / mass / hub geometry / `class=vehicle` / etc., all of
which were red herrings. The actual cause was `CfgSlots.selection = "wheelfrontleft"` (which
existed only in Visual LOD0/1, where the visual proxy was authored for wheel-hide) vs the
FireGeometry proxy face living in `wheel_X_X` selection. Aliasing the FireGeo proxy face into
`wheelfrontleft` (additive, single py3d session) flipped `wheelPresent` 0→4 on the next deploy.

**Cross-ref:** LL-044 (parity audits must include cross-LOD wiring consistency, not only
geometry); bug-ledger LFQuad UPDATEs 1-16; handoff
`30_Sessions/2026-05-27-LFQuad-fixY-firegeo-wheelslot-selection.md`.

## Llama Mod Extraction Patterns

Moved to `references/llama-extraction-patterns.md` — LM_Planes-derived Enforce/DayZ patterns (pass 1 + pass 2), including the **CfgSoundSets parameters reference** table (`dayz-sound-system` cross-ref), custom inputs XML, buildings (Doors/damage isolation), custom RPC enums, server-authoritative input, and parent/child mod architecture.

## Deep-dive verified additions

Moved to `references/vanilla-deep-dive.md` — source-verified vanilla v1.24 facts: recipes/crafting, ComponentEnergyManager, action system, damage pipeline, player internals/sync.

## Fire modes (single / burst / full-auto)

Moved to `references/weapon-firemodes.md` — inherit-vs-redeclare fire-mode classes on derived weapons, and the `Mode_*` root-scope forward-declaration trap (SP-031). Cross-ref: SP-038 in `dayz-pbo-build`.

## Client preload lifecycle - native camera/world getters crash, not catchable (SP-064, added 2026-07-14)

Native getters that walk the world camera - `Game.GetCurrentCameraPosition/Direction`, `Camera.GetCurrentCamera/GetCurrentFOV/IsInterpolationComplete` - are NOT safe during the client's preload. The world camera is not built yet, the native getter derefs null, and the process takes a **native crash (minidump), not a VM exception**. An Enforce guard on the derived object (`if (!Camera.GetCurrentCamera())`) does NOT catch it: the deref happens inside the next native call. A client-side handler that processes async input (RPC, pulled command, tick-driven poll) can receive a command BEFORE the local player exists and trip this.

Rule: in any client-side handler that touches camera / world / player-derived APIs, gate fail-closed on readiness BEFORE the first native call - `GetGame() && GetGame().GetPlayer()` (local player null = preload / not in-game). Same discriminator the vehicle handlers already use (`ResolveOwnedCar`: `if (!GetGame().GetPlayer()) return null`). Prefer a single gate in the dispatcher (covers the whole command class, R7) plus a defensive guard at the getter site if it has call-sites that do not re-enter the dispatch (e.g. an async job's report).

Cross-ref: `## ENTITY LIFECYCLE QUICK REFERENCE`, IsServer/IsClient side-checks, and the CallLater 4.5h rule (Timer Rules) - same lifecycle-timing family. Origin: DayZ_MCP BUG-041, minidump in `MCPClientBridge::BuildCameraResult`, repro 2026-07-11; in-game gate PASSED 2026-07-12 (a `camera_get` reaching the client bridge during preload returns `client_not_in_game`, dump_delta=0). The cited signatures (`game.c:730-731`, `camera.c`) are from the DayZ_MCP project tree; the base-vanilla scripts bundled here predate those symbols, so the durable, version-independent part is the readiness gate, not the exact signature.

## Math has no Math.Exp - exponential idiom is Math.Pow(Math.EULER, x) (SP-058, added 2026-07-14)

Enforce has no `Math.Exp` (0 hits tree-wide in `P:\scripts`, verified 2026-07-10 and re-verified 2026-07-14). Write any exponential - dt-invariant smoothing, decay, half-life, easing - with the verified primitives `Math.Pow` (`enmath.c:183`) and `Math.EULER` (`enmath.c:11`). Vanilla precedent for the idiom is `Pow(EULER,-mean)` in the Poisson helper (`enmath.c:710`).

dt-invariant tick pattern (cheap, one `Pow` per channel per tick): when tuning loads, precompute per channel `K_PER_SEC = Math.Pow(Math.EULER, -1.0 / TAU_channel)`; per tick compute `decay = Math.Pow(K_PER_SEC, dt)` and `alpha = 1 - decay`. This equals `exp(-dt/TAU)` with no exp call. Never use a per-tick constant (multiply by 0.95 each tick = frame-rate dependence - the real bug in RFFS `FlightSimulation`).

Cross-ref: `## TROUBLESHOOTING` row "Math.Clamp not found" - same assumed-missing/assumed-present Math API family. Origin: LFHeli fase 1, caught by the independent R22 as FAIL R22-001 before coding; shipped in LFHeli (4 K_PER_SEC channels).

## `$profile:` resolves to the exe's -profiles= folder, not always %USERPROFILE% - probe it at runtime (SP-029, added 2026-07-14)

`$profile:` resolves to the folder given by the exe's `-profiles=` (DayZDiag_x64 / DayZServer_x64), NOT always `%USERPROFILE%\Documents\DayZ\...`. Resolution changes with server-vs-client, diag-vs-retail, and the exact `-profiles=` value (relative paths resolve against the launch cwd). Canonical probe from the mod on first boot (mission/init):

    string p = "$profile:dayz_mcp.json"; // or whatever file
    Print("[MOD] profile resolves to: " + p);

Check in the RPT that `p` matches the absolute path where the wrapper (PowerShell/batch) wrote the config. A mismatch explains "config_url_empty" / "JsonFileLoader returned empty" symptoms without touching the read code or rebuilding: the fix is the wrapper's `-profiles=` or an absolute path in the mod, NOT the read logic. Origin: DayZ_MCP step0-rerun 2026-06-07 (GATE=FAIL config_url_empty). Cross-ref LL-113, LL-097 (path is a HINT), LL-101 (proto != runtime).

## Scheduled callbacks: the callback IS the deadline; sleeping entities miss EOnSimulate; one DbgLog marker per fix (SP-060, added 2026-07-14)

Clock race in a scheduled one-shot: a `GetGame().GetCallQueue(...).CallLater(fn, delayMs, false)` whose `fn` RE-CHECKS the deadline with `GetTickTime() >= armTime` can miss by milliseconds right at the due instant (the CallQueue keeps its own clock; `GetTickTime()` can lag in the firing frame) - with a one-shot the action is lost forever. Rule: the callback IS the deadline - do not compare clocks inside it, re-check only state conditions (`armed && !started && state==X`). A path that runs on an awake tick may keep the clock comparison. Evidence: LFHeli c3 (`TrySpikeStart fired state=0` then `skipped`), fixed clockless (`IsArmedNotStarted()`) first try.

Sleeping entities miss `EOnSimulate`: an idle, still CarScript sleeps within a few ticks and anything living inside `EOnSimulate` (countdowns, polls) dies with it. `dBodyActive(this, ActiveState.ALWAYS_ACTIVE)` alone did NOT guarantee the tick here - the robust path for timed logic on a possibly-sleeping entity is the CallQueue (immune to body sleep).

Process pattern: one DbgLog marker per fix. Each in-game-cycle fix adds its own log marker ("keep-awake applied", "TrySpikeStart fired state=X") - without it, "fix not compiled" and "fix insufficient" are indistinguishable and cost a full rebuild+boot cycle. Cross-ref the CallLater 4.5h rule (Timer Rules) and `dayz-mod-workflow` debug hierarchy. Origin: LFHeli batch #1 (2026-07-11), wake-bug cycles c1-c4.

## Enforce has METHOD scope, not block scope - the same local in two `case` blocks = compile FATAL (SP-066, added 2026-07-14)

Enforce treats local variables with METHOD scope, not block scope (like old-JS `var`). Declaring the same variable in two different `case`/blocks of the SAME method = `SCRIPT (E): Multiple declaration of variable 'X'` -> `Can't compile "World" script module!` -> server crash. DayZDiag strict rejects it; retail may tolerate it -> latent bug if only tested on retail (same diag-vs-retail split as SP-047, `ref` on a param). Fix: rename per block (e.g. `cgVel` / `cgVelRec`) or declare once at the top of the method. Origin: LFHeli rework v2 2026-07-14, `LFHeli_Base.c:789` (`vector cgVel` in both the FLIGHT and EMERGENCY_RECOVERY branches of one StepStateMachine); caught by the diag server compile-gate (`Multiple declaration of variable 'cgVel'`).

## Reglas promovidas del corpus de lecciones (added 2026-07-27)

Promovidas desde `AI/20_Knowledge/lessons-learned.md` para que lleguen por trigger en vez
de depender de que alguien recuerde buscarlas. Cada regla cita su `LL-NNN` de origen;
la entrada completa (síntoma, origen, evidencia) vive allí. No quites la cita: el índice
`lessons-index.md` detecta la promoción buscando esa referencia dentro de las skills.

- **LL-101** — Trata la presencia de un símbolo `proto native` como prueba de firma, no de funcionamiento. Para APIs de captura, render, hardware o I/O, consulta tracker/prior art y ejecuta un probe que verifique el artefacto real antes de basar el diseño en ellas.
- **LL-141** — Antes de variar formatos de una API engine, reproduce el call-site vanilla exacto. Si también falla, detén el ajuste sintáctico y aísla el contexto de ejecución: server/client, headless/GUI, build y defines.
- **LL-016** — Valida en el servidor `sender`, su identidad y la igualdad del ID con el `PlayerBase` objetivo; aplica además un rate-limit por jugador. Rechaza por defecto aunque el payload no contenga datos sensibles.
- **LL-186** — No inicialices handles opacos Enfusion con literales (`FileHandle handle = 0`). Decláralos sin inicializar, asigna el retorno de la API y aplica la guardia según el valor documentado de esa API.
