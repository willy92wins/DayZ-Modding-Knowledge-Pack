# Advanced Pitfalls & Debugging

## Compiler Bugs & Quirks

### 1. `int.MIN` Comparison Bug

```
// BROKEN — Enforce Script bug
1 < int.MIN;       // returns TRUE (should be false)
1 < -2147483647;   // also returns TRUE

// The root cause: integer overflow in the comparison logic
// Workaround: avoid comparing against int.MIN directly
```

### 2. Negation of Array Element Doesn't Compile

```
// BROKEN — doesn't compile
if (!list[1])  // compile error

// CORRECT
if (list[1] == 0)  // compiles fine
```

### 3. switch/default Return Bug

```
// BROKEN — compiler claims "not all paths return a value"
string Test(string what)
{
    switch (what)
    {
        case "A":
        case "B":
            return "X";
        default:
            return "Y";
    }
    // Compiler insists there's a missing return even though
    // default catches everything
}

// WORKAROUND — move last return out of switch
string Test(string what)
{
    switch (what)
    {
        case "A":
        case "B":
            return "X";
    }
    return "Y";  // default case, outside switch
}
```

### 4. Compile Errors Show Wrong File/Line

When a class referenced in code doesn't exist (e.g., missing addon), the
compiler shows the **last successfully parsed file at EOF**, not the file
with the actual error. This is extremely misleading.

**Debugging strategy**: If you get a compile error in a file that looks
correct, check if any class it references requires an addon that isn't loaded.

### 5. Empty #ifdef Blocks Cause Segfault

```
// SEGFAULT — empty block (even with comments)
#ifdef MY_MOD
// This comment doesn't count as content
#endif

// CORRECT — at least one statement
#ifdef MY_MOD
int _placeholder;
#endif
```

---

## Runtime Crashes (Segfaults)

### 6. Compound Expression Assigned to Array Element

```
// SEGFAULT
m_IsInside[index] = vector.DistanceSq(a, b) <= distSq;

// CORRECT — split into two statements
bool isInside = vector.DistanceSq(a, b) <= distSq;
m_IsInside[index] = isInside;
```

**Rule**: Never assign the result of a compound expression (comparison,
arithmetic, function call chain) directly to an array element. Always
use an intermediate local variable.

### 7. NormalMapMacro Shader on Dedicated Server

Using `NormalMapMacro` shader in .rvmat files causes dedicated server crash
at model load time. The shader references client-only rendering paths.

```
// CRASH on dedicated server
Stage3
{
    texture = "...nohq.paa";
    uvSource = "tex";
    class uvTransform { ... };
    shader = NormalMapMacro;  // CRASH
}

// CORRECT — use Super shader with 7 stages for all rvmats
shader = Super;
```

### 8. ProjectionBasedOnParent Creates Real Entities

If a kit/hologram uses `ProjectionBasedOnParent`, the engine creates an
actual entity during placement preview. Without overriding `PlaceEntity()`,
ghost entities accumulate.

```
// REQUIRED override in Hologram
override EntityAI PlaceEntity(EntityAI newEntity)
{
    // Prevent ghost spawn by returning the projected entity
    return newEntity;
}
```

### 9. map<Widget, T> Runtime Crash

```
// COMPILES but CRASHES at runtime
ref map<Widget, int> m_Map;  // Widget is not a valid key type

// Use parallel arrays instead
ref array<Widget> m_Keys;
ref array<int> m_Values;
```

### 10. ScriptView Constructor from RPC Context

```
// CRASH — new ScriptView() calls CreateWidgets() internally
// CreateWidgets() fails in RPC context (no workspace available)
void OnRPC(...)
{
    LFPG_SorterView view = new LFPG_SorterView();  // CRASH
}

// CORRECT — pre-create in MissionInit, show/hide later
class MissionGameplay
{
    ref LFPG_SorterView m_SorterView;

    override void OnInit()
    {
        m_SorterView = new LFPG_SorterView();  // safe here
    }
}
```

---

## Operator Precedence Trap

Enforce Script follows C/C++ precedence where bitwise operators have
LOWER priority than comparison operators:

```
// WRONG — interpreted as a & (b == b) = a & true = a & 1
int result = a & b == b;

// CORRECT — explicit parentheses
int result2 = (a & b) == b;
```

This catches developers coming from Python where bitwise ops have higher
precedence than comparisons.

---

## modded class Rules

`modded class` extends vanilla or other mod classes without inheritance:

```
modded class PlayerBase
{
    override void OnConnect()
    {
        super.OnConnect();
        // Custom code
    }

    // Can ADD new methods
    void MyCustomMethod()
    {
    }
}
```

**CRITICAL RULES:**
1. `modded class` **CANNOT add new member variables** — only methods/overrides
2. Two `modded class` declarations for the same class CAN coexist in different files
3. Call `super.MethodName()` in overrides to preserve vanilla behavior
4. Only ONE `modded class Hologram` can exist across ALL files — multiple declarations conflict

### Detecting Other Mods

```
// Compile-time detection (addon loaded)
#ifdef EXPANSION
// Expansion code here
#endif

// Runtime detection (config exists)
string cfgCheck = "CfgPatches ExpansionHardline";
bool hasHardline = GetGame().ConfigIsExisting(cfgCheck);
```

---

## Variable Scoping Traps

### Sibling Scope Re-declaration

```
// COMPILE ERROR — same name in sibling scopes
if (condition)
{
    int x = 5;
}
else
{
    int x = 10;  // ERROR: multiple declaration
}

// CORRECT — hoist before conditional
int x;
if (condition)
{
    x = 5;
}
else
{
    x = 10;
}
```

### Nested Scope Re-declaration

```
// COMPILE ERROR — nested scope shadows outer
int i = 5;
for (int i = 0; i < 12; i = i + 1)  // ERROR
{
}

// CORRECT — different name or hoist
int i = 5;
int j;
for (j = 0; j < 12; j = j + 1)
{
}
```

---

## Debugging Tools

### Print / PrintFormat

```
// Basic print
Print("Hello");
Print(myInt);
Print(myVector);

// Formatted print (format string with %1, %2, etc.)
PrintFormat("Device %1 at pos %2 has load %3", typeName, pos.ToString(), load.ToString());
```

### Error / ErrorEx

```
// Log as error (shows in script errors)
Error("Something failed");

// ErrorEx with detail
ErrorEx("Failed to load config", ErrorExSeverity.WARNING);
```

### Script Console

In Workbench or with admin tools, the script console can execute
Enforce Script at runtime — useful for testing snippets:
```
Print(GetGame().GetTime());
```

### RPT Log Analysis

Common log patterns and what they mean:

| Log Pattern | Meaning |
|---|---|
| `SCRIPT (E): ...` | Script error (non-fatal, usually null reference) |
| `Segmentation fault` | Fatal crash — array bounds, dead pointer, shader |
| `Illegal write at ...` | Heap corruption — usually from timer/alloc fragmentation |
| `Multiple declaration of 'X'` | Variable declared in sibling scopes |
| `'X' not found` | Class/method doesn't exist — missing addon or typo |
| `Scripted variables corrupted upon "X"` | OnStoreLoad order mismatch |
| `Cannot create object of type 'X'` | Class not in config.cpp or wrong parent |

---

## String & Number Gotchas

### String Parameters — Always Local Variable

```
// CRASH or compile error — string literal as parameter
widget.FindAnyWidget("MyWidget");  // May cause issues

// CORRECT — assign to local first
string wName = "MyWidget";
widget.FindAnyWidget(wName);
```

### Float Precision

```
// Enforce uses 32-bit float — precision ~7 significant digits
// Large timestamps lose precision after 16,777,216 (2^24)
float time = GetGame().GetTime();  // milliseconds as float
// After 4.66 hours, this value loses sub-millisecond precision
// After 46 hours, loses sub-second precision
```

### ToString Limitations

```
// int.ToString() and float.ToString() work
int x = 42;
string s = x.ToString();  // "42"

// No printf-style formatting — build manually
// See FormatFloat1 pattern in LFPG_DeviceInspector for decimal formatting
```

---

# ADDITIONAL PITFALLS — Style guide & performance

Extracted from `enforce-script-reference/SKILL.md` on 2026-07-07 (F3 sectioning).


Aggregated from the EnScript Style Guide (TrueDolphin / Expansion devs) and verified
against vanilla DayZ source where applicable. Each entry notes verification status.

### Compiler / language quirks

- **Empty `#ifdef` / `#ifndef` blocks segfault** — even if they only contain comments.
  Either remove the block entirely or put at least one statement inside (`int dummy;`).
  *(Reported by Expansion devs; engine-level, hard to verify in vanilla source.)*

- **`1 < int.MIN` returns TRUE** — and `1 < -2147483647` also returns TRUE. Integer
  comparison against `int.MIN` is broken. Always guard MIN/MAX comparisons explicitly.
  *(Reported community quirk; not a vanilla pattern.)*

- **Switch with `default` STILL requires a return outside** — even though every case
  including default returns, the compiler complains "function must return a value".
  Workaround: move the default branch's return to a final `return Y;` after the switch:

  ```c
  string Test(string what)
  {
      switch (what)
      {
          case "A":
          case "B":
              return "X";
      }
      return "Y";  // default moved outside
  }
  ```

- **`if (a & b == b)` parses as `a & (b == b)`** — bitwise has lower precedence than
  comparison in EnScript (C/C++ semantics). Always parenthesize:

  ```c
  if ((a & b) == b)   // CORRECT
  ```

- **Compiler errors with undefined classes / name conflicts point to the WRONG file** —
  the error shows the last `.c` parsed at EOF, NOT the line that triggered the issue.
  When the error location seems wrong, search the entire codebase for the symbol and
  check that all required addons are loaded.

- **`crash_<date>_<time>.log` contains EXCEPTIONS, NOT segfaults** — actual crashes
  (memory faults) write a different dump. When debugging, check both: exception logs
  for handled errors, separate crash dumps for hard segfaults.

### Performance traps (verified in vanilla `P:\scripts\3_game\global\game.c`)

- **`GetObjectsAtPosition` / `GetObjectsAtPosition3D` are slow** — `proto native` at
  `game.c:922,929`. Avoid in tick paths. Prefer:
  - Static arrays on the class you're looking for (`s_AllInstances`)
  - Triggers (`ScriptedEntity`-derived with collision events)
  - `GetScene()` API for scene-graph queries
  *(Vanilla call, performance claim is community guidance.)*

- **`SurfaceIsPond` / `SurfaceIsSea` / `SurfaceRoadY` are slow** — all `proto native`
  at `game.c:1181-1183`. For "is this point in water?" prefer:

  ```c
  if (g_Game.GetWaterDepth(pos) > 0)  // pos is vector
  ```

  Vanilla itself uses both patterns (`hologram.c:1128` uses `SurfaceIsSea/Pond`,
  `transport.c:357` and `playerbase.c:6817` use `GetWaterDepth`). When you control
  the call site, prefer `GetWaterDepth`.

- **Surface Y position fast pattern**:

  ```c
  vector GetSurfacePosition(float x, float z)
  {
      return Vector(x, g_Game.SurfaceY(x, z), z);
  }
  ```

### Type system — `GetType()` vs `ClassName()` (verified `object.c:473`)

For entities, `GetType()` returns the **config.cpp class name** (resolved via
`g_Game.ObjectGetType(this, ret)`), while `ClassName()` returns the **script class
name**. They differ when the script class has no matching config declaration.

```c
// PREFERRED for entities
if (entity.GetType() == "MyMod_Vest") { ... }

// Use ClassName() only when you specifically need the script class name
```

Vanilla uses `GetType()` heavily for hidden selections lookup
(`object.c:128,134,140`) and config path construction (`object.c:430,436,442`).

### `[Obsolete()]` attribute (verified vanilla)

Marks methods/fields/vars as deprecated. Workbench surfaces a warning at call sites.
Use when removing API would break dependent mods — soft-deprecate first.

```c
[Obsolete("Use GizmoApi.GetCount")]
proto native int GetGizmoCount();
```

Vanilla examples: `game.c:801,807,813`, `ecrewmemberstate.c:1`.

### `notnull` keyword for parameters

Propagates non-nullness guarantees. The caller has already verified non-null, so the
function can skip the check. Combined with the EnScript rule "null-check where you
know how to handle it":

```c
void Foo()
{
    EntityAI entity = FindSomeEntitySomehow();
    if (!entity) { Print("entity not found"); return; }
    DoStuff(entity);
}

void DoStuff(notnull EntityAI entity)
{
    GameInventory inventory = entity.GetInventory();
    // entity guaranteed non-null; only check inventory if null is semantically valid
}
```

### Modded class member-var prefix convention

When adding members to `modded class X` or to a class extending vanilla, ALWAYS
prefix the member to avoid collision with other mods that also extend `X`:

```c
modded class ItemBase
{
    bool m_Expansion_CustomFlag;       // GOOD — prefixed
    int  m_LFPG_PowerDraw;             // GOOD — prefixed
    bool m_CustomFlag;                 // BAD — collides with any other mod's m_CustomFlag
}
```

### `EXTrace.Start` (Expansion / Community Framework only)

Modern minimal-overhead tracing. **NOT in vanilla DayZ.** Available when Expansion
or DayZ Community Framework is loaded. Replaces older `CF_Trace_0` pattern that
required `#ifdef EXPANSIONTRACE` guards.

```c
auto trace = EXTrace.Start(EXTrace.GENERAL, this, "MethodName");
// no #ifdef needed — no-op when tracing disabled
```

If your mod targets vanilla-only servers, fall back to `Print()` or your own
conditional logger.

### `defines[]` array in CfgMods (DayZ 1.26+)

Auto-generates `#define <ModClassName>` and any custom defines listed:

```cpp
class CfgMods
{
    class YourMod
    {
        defines[] = {"YOURMOD", "YOURMOD_FEATURE_X"};
    };
}
```

Then in script:

```c
#ifdef YOURMOD
    // mod-specific code
#endif
```

*(Version-gated — works only on DayZ 1.26 and later.)*

### Cross-mod `#ifdef` gates: use the CfgMods auto-define, NOT a manual `#define`

The CfgMods `defines[]` (or just the implicit `#define <ModClassName>` from
DayZ 1.26+) is visible to **other mods' compilation units**. A manual
`#define X` written inside `<TargetMod>/scripts/Common/Define.c` is **only
visible inside that target mod's own files** — even when the symbol name is
identical. A consumer mod's `#ifdef X` that gates code against the manual
define will silently compile to no-op.

```c
// In <YourMod>/scripts/4_World/...c — gating an override of a Boomlay class:

#ifdef bl_pallet_table   // CfgMods auto-define from bl_pallet_table.pbo
modded class bl_pallet_table_s { ... }   // works
#endif

#ifdef bl_pallet_furniture   // manual #define in bl_pallet_table/Common/Define.c
modded class bl_pallet_table_s { ... }   // never compiles, override silently lost
#endif
```

Symptom: the `modded class` body never runs. `IsKindOf` / `Open` / hook calls
behave as if the override does not exist, but the codebase compiles cleanly.

Rule: when picking the cross-mod gate symbol, audit the target PBO's
`config.cpp` `CfgPatches` / `CfgMods.defines[]` entries — never trust a
matching `#define` in `scripts/Common/Define.c` to propagate.

### `#ifdef DEVELOPER` ≠ `DIAG_DEVELOPER` — read the actual compile defines (SP-037, added 2026-06-29)

Anti-confabulation. Vanilla has APIs guarded by `#ifdef DEVELOPER` (e.g. `DayZPlayerSyncJunctures.SendGetInVehicle` → `SJ_DEBUG_GET_IN_VEHICLE`, much of `plugindeveloper.c`). Standard `DayZDiag_x64` defines `DIAG_DEVELOPER` but does **NOT** define `DEVELOPER`. Emitting a `DEVELOPER`-only symbol from your mod breaks the compilation of the **entire PBO** (cross-mod compile failure, no clean RPT, only "PBO not loaded" / addons missing) — not a silent no-op. Before relying on any `#ifdef <SYMBOL>` API, verify the `defines:` line of `<profiles>\script_*.log` for BOTH server and client peers (the runtime tells you what is defined). That `OnDebugSpawn` (`#ifdef DIAG_DEVELOPER`) works does NOT prove `DEVELOPER` is active — different macros. Origin: DayZ-MCP Fase 5 Tramo A 2026-06-28 (1st hypothesis refuted by adversarial review reading the real compile logs; would have shipped a broken PBO). Cross-ref: LL-173.

### `foreach` on getter results re-calls the getter

Every iteration calls the method again. Hoist to a local first:

```c
// BAD — getter called N times
foreach (string t : GetTest()) { Print(t); }

// GOOD — getter called once
TStringArray test = GetTest();
foreach (string t : test) { Print(t); }

// ALSO GOOD — direct member access doesn't recall
foreach (string t : m_Test) { Print(t); }
```
