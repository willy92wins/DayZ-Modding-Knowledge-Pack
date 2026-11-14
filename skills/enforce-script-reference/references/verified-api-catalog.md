# Verified API Catalog

Extracted from `enforce-script-reference/SKILL.md` on 2026-07-07 (F3 sectioning).

Consultation catalog (not rules): reflection/introspection, verified global functions, and string/math/config-lookup API patterns.

---

## REFLECTION & INTROSPECTION (verified from LBmaster_Core production)

Enforce Script has a powerful reflection system used by production mods for
data binding, auto-registration, and dynamic dispatch.

### Reading/Writing Class Variables by Name
```
// Read any class field by string name:
int intVal;
EnScript.GetClassVar(instance, "fieldName", 0, intVal);

string strVal;
EnScript.GetClassVar(instance, "fieldName", 0, strVal);

Class classVal;
EnScript.GetClassVar(instance, "fieldName", 0, classVal);

// Write any class field by string name:
EnScript.SetClassVar(instance, "fieldName", 0, newValue);
// Works with: int, float, string, bool, vector, Class
```

### Dynamic Method Calls
```
// Call a method by string name:
Class returnVal;
g_Game.GameScript.CallFunction(instance, "MethodName", returnVal, singleParam);

// With typed parameters:
g_Game.GameScript.CallFunctionParams(instance, "MethodName", returnVal, 
    new Param1<string>(myString));
```

### Type Introspection
```
typename t = instance.Type();
int varCount = t.GetVariableCount();
for (int i = 0; i < varCount; i++) {
    string name = t.GetVariableName(i);
    typename varType = t.GetVariableType(i);
    bool isWidget = varType.IsInherited(Widget);
}
```

### Instantiation from String
```
typename tn = "MyClassName".ToType();
if (tn) {
    Class obj = tn.Spawn();
    MyClass typed = MyClass.Cast(obj);
}
```

### ScriptCaller — First-Class Function References
```
ScriptCaller caller = ScriptCaller.Create(MyClass.MyStaticMethod);
caller.Invoke();
// Used for: event handlers, deferred execution, test registration, RPC dispatch
```

### Attributes — Code Execution at Class Load Time
```
// Attribute executes at class load, return value assigned to decorated field:
[MyManager.Register(SomeParam)]
static ref SomeType myField;

// Real example (LBmaster test framework):
[LBTestManager.StartTest(ScriptCaller.Create(MyTest))]
private static void MyTest() {
    LBTest<int>.Assert(1 + 1, 2);
}
```

---

## VERIFIED GLOBAL FUNCTIONS (from LBmaster_Core production)

### Screen & Mouse
```
int w, h;
GetScreenSize(w, h);                   // screen resolution
int mx, my;
GetMousePos(mx, my);                   // mouse position (pixels)
Widget w = GetWidgetUnderCursor();     // hovered widget
Widget f = GetFocus();                 // focused widget
```

### Debugging & Profiling
```
string stack;
DumpStackString(stack);                // full call stack as string
int start = TickCount(0);             // start timer
int elapsed = TickCount(start);       // ticks since start (/ 10000 = ms)
```

### Command Line
```
bool has = IsCLIParam("myFlag");       // check -myFlag
string val;
GetCLIParam("port", val);             // read -port=2302
```

### File System — Directory Listing
```
string filename;
FileAttr attr;
FindFileHandle fh = FindFile(dir + "/*", filename, attr, FindFileFlags.ALL);
if (fh) {
    bool found = true;
    while (found) {                   // Enforce has no do...while
        bool isDir = (attr & FileAttr.DIRECTORY);
        found = FindNextFile(fh, filename, attr);
    }
    CloseFindFile(fh);
}
```

### REST API (verified production use)
```
RestApi api = GetRestApi();
if (!api) api = CreateRestApi();
RestContext ctx = api.GetRestContext("https://example.com/api");
ctx.SetHeader("application/json");
ctx.POST(new MyRestCallback(), "param=value", jsonBody);
// MyRestCallback extends RestCallback: OnSuccess/OnError/OnTimeout
```

### Sound System
```
// 3D positional: SEffectManager.PlaySound(soundSetName, worldPos);
// 2D UI sound:
SoundParams sp = new SoundParams(soundSetName);
if (sp.IsValid()) {
    SoundObjectBuilder sob = new SoundObjectBuilder(sp);
    SoundObject so = sob.BuildSoundObject();
    so.SetKind(WaveKind.WAVEEFFECT);
    AbstractWave wave = g_Game.GetSoundScene().Play2D(so, sob);
    wave.Loop(false);
    wave.Play();
}
```

### Notifications
```
// Server → client:
NotificationSystem.SendNotificationToPlayerIdentityExtended(identity, showTime, title, msg, icon);
// Client local:
NotificationSystem.AddNotificationExtended(showTime, title, msg, icon);
```

### Popup server→client without a client mod (SP-287)

`NotificationSystem.SendNotificationToPlayerIdentityExtended(identity, show_time, title, detail, icon)` (`3_game/client/notifications/notificationsystem.c:141-151`; `identity == null` = broadcast) sends `RPC_SEND_NOTIFICATION_EXTENDED` and the VANILLA client renders it. Calling the LOCAL `NotificationSystem` on the server (`AddNotification*`) notifies NOBODY — it is client-side. (Resolves the contradiction measured by ControlPlane.)

### Online Players
```
// Server (note vanilla typo "Indentities"):
array<PlayerIdentity> ids = new array<PlayerIdentity>();
g_Game.GetPlayerIndentities(ids);

// Client:
if (ClientData.m_PlayerList && ClientData.m_PlayerList.m_PlayerList) {
    foreach (SyncPlayer sp : ClientData.m_PlayerList.m_PlayerList) {
        string steamid = sp.m_Identity.GetPlainId();
    }
}
```

### `GetObjectsAtPosition3D` returns terrain statics mixed with dynamics (SP-287)

`GetObjectsAtPosition3D(pos, r, out objs, out cargos)` returns terrain statics (bushes, `Object` with empty `GetType()`) IN ADDITION to dynamics (players, items, vehicles, infected): filter by type if you only want entities. Radius 30 in open field = 38 objects.

### JSON Serialization
```
ref JsonSerializer serializer = new JsonSerializer();
string json, error;
serializer.WriteToString(instance, true, json);
serializer.ReadFromString(instance, jsonString, error);
// File helpers:
JsonFileLoader<MyClass>.LoadFile(path, out instance, error);
JsonFileLoader<MyClass>.SaveFile(path, instance, error);

// LoadFile returns bool — check it to detect failure (unlike JsonLoadFile which returns void).
// DEPRECATED: JsonLoadFile(path, out instance) / JsonSaveFile(path, instance) return void with no error signal.
//   Keep for reading legacy code only; do NOT use in new code.
// WARNING: JSON file I/O is SYNCHRONOUS (blocks the main thread). Never call in OnUpdate().
```

### Per-Frame Callbacks
```
// Every frame:
g_Game.GetUpdateQueue(CALL_CATEGORY_SYSTEM).Insert(MyCallback);
// void MyCallback(float timeslice)
g_Game.GetUpdateQueue(CALL_CATEGORY_SYSTEM).Remove(MyCallback);

// Single call next frame:
g_Game.GetCallQueue(CALL_CATEGORY_SYSTEM).Call(MyFunction);
```

### Input System — Complete Keybind API
```
// inputs.xml format:
// <modded_inputs>
//   <inputs>
//     <actions><input name="UAMyAction" loc="str_key_name" /></actions>
//     <sorting name="my_cat" loc="Category"><input name="UAMyAction" /></sorting>
//   </inputs>
//   <preset><input name="UAMyAction"><btn name="kU" /></input></preset>
// </modded_inputs>

// Detection (three patterns, all valid):
// 1) Simple:
g_Game.GetInput().LocalPress("UAMyAction", false);
// 2) Direct:
GetUApi().GetInputByName("UAMyAction").LocalPress();
// 3) Persistent (store once, check each frame):
UAIDWrapper wrapper = GetUApi().GetInputByName("UAMyAction").GetPersistentWrapper();
// later: if (wrapper.InputP() && wrapper.InputP().LocalPress()) { ... }

// Suppress (prevent other handlers):
GetUApi().GetInputByName("UAMyAction").Supress();

// Get display name:
string keyName = GetUApi().GetButtonName(input.Binding(0));

// Multi-alternative bindings:
for (int a = 0; a < input.AlternativeCount(); a++) {
    input.SelectAlternative(a);
    if (input.IsCombo()) { /* input.Binding(0) + input.Binding(1) */ }
    else { /* input.Binding(0) only */ }
}
```

### Clipboard & Time
```
g_Game.CopyToClipboard(stringValue);
int timeMs = g_Game.GetTime();         // ms since game start
```

### Window Resize Detection
```
// In modded DayZGame.OnEvent:
if (eventTypeId == WindowsResizeEventTypeID) {
    GetScreenSize(w, h);  // screen changed
}
```

### Bones
```
int idx = man.GetBoneIndex("Spine2");
vector worldPos = man.GetBonePositionWS(idx);
```

---

### Config Lookup
```
// Check if a config class exists
string cfgPath = "CfgVehicles";
string className = "MyItem";
string fullPath = cfgPath + " " + className;
if (GetGame().ConfigIsExisting(fullPath))
{
    // Class exists in config
}

// Read config value
string cfgPathItem = "CfgVehicles " + className + " itemSize[]";
TIntArray itemSize = new TIntArray;
GetGame().ConfigGetIntArray(cfgPathItem, itemSize);
```

[EXACT][CLAIM-ENF-CONFIGISEXISTING-TRAILING-SPACE] A trailing space after the class name
(`"CfgVehicles " + className + " "`) still finds the class: measured on DayZDiag 1.29.163709, a currency
catalog checked that way passed with its four real classes. Vanilla builds the path without it
(`VANILLA/4_world/systems/inventory/attachmentsoutofreach.c:82`), and so should new code. Not tested: a class
that does not exist, with the trailing space, so a false positive through that path is not ruled out.

### String Operations (Enforce limitations)
```
// No printf — format manually
int val = 42;
string msg = "Count: ";
msg = msg + val.ToString();

// Substring(start, length)
string full = "Hello World";
int len = full.Length();
string sub = full.Substring(0, 5); // "Hello"

// IndexOf (-1 if not found)
int pos = full.IndexOf("World"); // 6

// IndexOfFrom — search from position (VERIFIED working):
int second = full.IndexOfFrom(first, ":");

// LastIndexOf (VERIFIED working):
int idx = path.LastIndexOf("\\");

// Hash — returns int (VERIFIED working):
int h = myString.Hash();

// Replace — mutates string, returns count of replacements:
int count = myString.Replace(":", "");

// ToLower — mutates in place. Copy first if original needed:
string lower = original + "";  // "+" forces copy
lower.ToLower();

// Character access (returns string of length 1):
string firstChar = str[0];

// ToInt / ToFloat:
int n = str.ToInt();
float f = str.ToFloat();
```

### Math Operations
```
// Math.Clamp EXISTS (verified in LBGroups production):
float clamped = Math.Clamp(value, 0, 1.0);
int clamped2 = Math.Clamp(intVal, 0, 255);

// Also available:
float mn = Math.Min(a, b);
float mx = Math.Max(a, b);
float sq = Math.Sqrt(value);
int floored = Math.Floor(3.7);    // 3
int rounded = Math.Round(3.5);    // 4
int ceiled = Math.Ceil(3.1);      // 4
int rnd = Math.RandomInt(200, int.MAX - 1);

// vector operations
float dist = vector.Distance(posA, posB);
float distSq = vector.DistanceSq(posA, posB);  // cheaper, no sqrt
vector norm = dir.Normalized();
vector angles = dir.VectorToAngles();           // [0]=yaw, [1]=pitch

// World helpers
float groundY = GetGame().SurfaceY(x, z);      // terrain height at XZ
vector screenPos = GetGame().GetScreenPos(worldPos);  // 3D→2D projection
```


---

## ATTACHMENT LIFECYCLE & SELECTION VISIBILITY (verified vs vanilla 2026-07-14)

Item-side attach/detach hooks and runtime selection show/hide. Verified against vanilla
`P:\scripts`; cite path:line before relying.

### Attach / detach lifecycle (item side)
```
// Fires on the ITEM when it is attached to / detached from a parent's slot.
// Parent-side equivalents are EEItemAttached/EEItemDetached (see dayz-animation-pipeline).
override void OnWasAttached(EntityAI parent, int slot_id)
{
    super.OnWasAttached(parent, slot_id);
    // ...
}
override void OnWasDetached(EntityAI parent, int slot_id)
{
    super.OnWasDetached(parent, slot_id);
    // ...
}
// Verified: overrides in
//   P:\scripts\4_world\entities\core\inherited\inventoryitem.c:82,150,502,542,1093
//   P:\scripts\4_world\entities\core\inherited\itemoptics.c:287,300
//   P:\scripts\4_world\entities\explosivesbase\plastic_explosive.c:148,160
```

### Runtime selection visibility (EntityAI)
```
ShowSelection(string selection_name);   // make a named selection visible
HideSelection(string selection_name);   // hide it
// Verified: P:\scripts\3_game\entities\entityai.c:3364 (ShowSelection), :3355 (HideSelection)
// Override example: P:\scripts\4_world\entities\itembase\inventory_base\huntingoptic.c:34,44
```

### Pattern: swap a model by attach-state (performance)
Show a lighter model while attached, the full model on the ground, using two named
selections toggled from the item's attach hooks:
```
void MyItem()  // constructor: default to the ground model
{
    ShowSelection("not_attached");
    HideSelection("attached");
}
override void OnWasAttached(EntityAI parent, int slot_id)
{
    super.OnWasAttached(parent, slot_id);
    HideSelection("not_attached");
    ShowSelection("attached");
}
override void OnWasDetached(EntityAI parent, int slot_id)
{
    super.OnWasDetached(parent, slot_id);
    ShowSelection("not_attached");
    HideSelection("attached");
}
```
Source: community technique (YouTube "How to change the model of a proxy attachment",
RXIFoFo5stY, 2026). The two selections live in the .p3d; model.cfg pairs them via an
AnimationSource. Full model/LOD side in `dayz-animation-pipeline` ->
`references/item-ik-and-hide.md` (Pattern C). The script APIs above are verified; the exact
model.cfg AnimationSource wiring is [verify] against a vanilla two-model item (e.g. the flag).


### Slot enumeration — which API pair to use (SP-361; verified vs vanilla 2026-07-29)
Two `GameInventory` pairs look nearly identical but do the OPPOSITE:

| Pair | What it answers | Cite |
|---|---|---|
| `GetSlotIdCount()` / `GetSlotId(i)` | "number of slots **this item can belong to**" — where THIS item can attach **on another parent** | `P:\scripts\3_game\systems\inventory\inventory.c:167-175` |
| `GetAttachmentSlotsCount()` / `GetAttachmentSlotId(i)` | "number of slots **for attachments**" — slots the container **declares** | `P:\scripts\3_game\systems\inventory\inventory.c:176-184` |

**Rule**: "what attachment slots does this entity declare?" → always `GetAttachmentSlotsCount()` / `GetAttachmentSlotId(i)`.
`GetSlotIdCount()` / `GetSlotId(i)` only answer "where can THIS item be attached".

**Silent failure**: wrong pair on a container/vehicle does NOT throw. `CivilianSedan` (attaches to nothing)
returns count=1, invalid id; `InventorySlots.GetSlotName(id)` (`inventoryslots.c:48`) returns `""`.
Result: `[""]` — one empty element, no exception, no empty list. Looks like a data bug; is an API-pair bug.

**Tell you picked the wrong pair**: `[""]` or empty slot names on an entity that clearly has attachments.

### Hidden-selection texture and material getters (SP-210, added 2026-08-31)

There is no Enforce method named `GetObjectTextures()` (plural). Runtime texture and material state is singular and index-based: `GetObjectTexture(int)` / `GetObjectMaterial(int)` (`3_game\entities\entityai.c:2882-2885`). Iterate from zero to `GetHiddenSelections().Count() - 1` when a per-selection snapshot is required.

The config-array getters are `GetHiddenSelectionsTextures()` and `GetHiddenSelectionsMaterials()` (`3_game\entities\object.c:125-140`). For the embedded material list of a vobject, use `GetObjectMaterials(vobject, out string[])` (`1_core\proto\envisual.c:6-27`). Do not invent a plural runtime getter; an undefined call prevents the whole script module from compiling.

### Reflection limits and fail-closed test fixtures (SP-175, added 2026-08-31)

Correction to the broad `SetClassVar` guidance above: production use proves access to a `private bool`, but does **not** prove that reflection can replace a `ref` collection field. `EnScript.GetClassVar` and `EnScript.SetClassVar` return `1` on success. Eight runtime attempts to replace a `protected ref TManagedRefArray` returned `0`; there is no demonstrated reflection write for that field shape, so do not recommend it as a general test-hook technique.

`Class.Cast` returns null when the runtime type does not match; it does not throw. Cast to a local and guard before dereferencing, especially for `array<ref Managed>` / `TManagedRefArray` collections.

A reflection-based fixture is valid only when it is fail-closed:

1. Require `SetClassVar == 1` **and** assert the injected state before calling the code under test. Otherwise report `SETUP_FAIL`, never PASS.
2. Run the same fixture against the build without the guard and require RED first.
3. Use one invocation per case, so one exception cannot hide the remaining cases.
4. Hash the production PBO before and after qualification, and keep the fixture outside the publish set. Do not use `modded class` as the fixture: it changes the compiled hierarchy being qualified.

A failed write is not harmless. When `SetClassVar` returns `0`, abort the oracle and quarantine the subject; do not continue using it or send it through its normal deletion path. In the measured ref-collection probe, eight failed writes were followed by 48 null-pointer exceptions during deletion, while a no-reflection control had zero and retained valid elements. The internal mechanism is undetermined; do not claim a specific partial mutation.

## DayZ 1.30 — engine / inventory catalog

This catalog never listed `TakeEntityToCargo` / `World.Is3rdPersonDisabled` / `Weather.GetNoiseReductionByWeather` / "vector has no Cross" (digest E/O mapped those claims here; they were not in the 1.29 text). 1.30 additions, re-opened:

- (hasta 1.29: `TakeEntityToCargo` / `TakeEntityToCargoEx` / `TakeEntityAsAttachment` / `TakeEntityAsAttachmentEx`). (desde 1.30: all four `[Obsolete]` at `Inventory.c:1345-1386`. Use `TakeEntityToTargetCargo` `:1077`, `TakeEntityToTargetCargoEx` `:1084`, `TakeEntityAsTargetAttachmentEx` `:1100`, `TakeEntityAsTargetAttachment` `:1142`.)
- (hasta 1.29: `World.Is3rdPersonDisabled()` bool). (desde 1.30: `[Obsolete]`; `GetThirdPersonViewMode()` returns `ThirdPersonMode` {`DISABLED`,`ENABLED`,`VEHICLES_ONLY`} — `World.c:177`, `:291-305`. Digest O `:49-50` is moon/sun, not this API.)
- (hasta 1.29: `Weather.GetNoiseReductionByWeather()`). (desde 1.30: **not deleted**. `[Obsolete]` → `GetNoiseReductionByWeatherEx(notnull Object object)` at `Weather.c:407-408`, itself `[Obsolete]` "Kept for HUD and old mods" because AI damping is native AIParams. Vanilla still calls Ex: `SensesAIEvaluate.c:23`.)
- `vector.Cross(vector v)` was a script method in 1.30.164014 Exp and 1.30.164078 (`EnConvert.c:239-246`); 1.30.164200 stable removed it. Digest O `:29-36` is `int.MAX`/`MIN`.
- `array<T>.Slice(int from, int to)` inclusive-`to` (`EnScript.c:720-727`). Digest O `:33-40` is `ClassName` docs.
- `typename.EnumFlagsToString` / `Enum.EnumFlagsToString` (`EnConvert.c:593`, `:683`).
- `class DoOnce` (`3_Game\DoOnce.c:1`); `DayZPlayer.IsFirstRenderFrame()` (`dayzplayer.c:1186-1189`); `Entity.DisableSimulation` / `GetIsSimulationDisabled` (`Entity.c:3-6`).
- `GAME_STORAGE_VERSION = 144` (`Game.c:5`; 1.29 was `142` at the same line). `OnCEIterate` replaces `OnCEUpdate` (`EntityAI.c:3904`, `:4924-4925`).

Full `[EXACT]` bodies: `references/dayz-1-30-enforce-script.md`.

## DayZ 1.30.164289 — language limits, typedefs, weather, players, inventory, actions, mission hooks

Paths are relative to the extracted vanilla `scripts/` tree of DayZ 1.30.164289 (Steam build 26220720 of the
dedicated server). "Measured" means a probe in a dedicated server's mission `init.c` on that build.

### Language limits and built-ins

- **At most 16 parameters per method.** Measured: a 16-parameter static method compiled and returned the right
  value; the same method with a 17th parameter failed with
  `Maximum arguments count 16 exceeded in method 'Sum'` and `Can't compile mission init script`. Past 16, pass
  one object that carries the values.
- **Generic script classes** are allowed with the same syntax as vanilla's containers
  (`class array<Class T>`, `scripts/1_Core/proto/EnScript.c:374`; `map<Class TKey,Class TValue>` `:846`).
  Measured: `class Box<Class T> { T m_Value; ... }` worked as `Box<int>` and `Box<string>` in one script.
- **Container typedefs**: `TFloatArray`, `TIntArray`, `TVectorArray` (`EnScript.c:732`, `:733`, `:738`),
  `TStringStringMap = map<string, string>` (`EnScript.c:1004`) and its twin `TStringMap`
  (`scripts/3_Game/tools/tools.c:988`).
- **Float constants**: `FLT_MAX` and `FLT_MIN` are engine globals (documented at `EnScript.c:4-5`, used by
  `float.MAX`/`float.MIN` at `scripts/1_Core/proto/EnConvert.c:111-113`). `FLT_MIN` is the smallest positive
  normal float, **not** the most negative one: measured `FLT_MAX=3.40282e+38`, `FLT_MIN=1.17549e-38`. Use
  `float.LOWEST` (`= -FLT_MAX`) as the start value of a maximum search.
- `ftime` is a global float documented as the delta time since the last frame (`EnScript.c:3`); measured `0`
  when read in the mission's `main()`, before any frame ran.

### Weather (`scripts/3_Game/Weather.c`)

`g_Game.GetWeather()` returns the `Weather` object (`scripts/3_Game/Global/Game.c:1371`). Phenomena:
`GetOvercast()`, `GetFog()`, `GetRain()`, `GetSnowfall()`, `GetWindDirection()` (`:183-199`), each a
`WeatherPhenomenon` with `GetActual()` / `GetForecast()` (`:38-41`), `Set(float forecast, float time = 0, float
minDuration = 0)` (time = seconds to interpolate, minDuration = seconds the value holds, `:43-49`) and
`SetLimits` / `SetForecastChangeLimits` (`:74`, `:95`). Wind speed is a plain float on `Weather`:
`GetWindSpeed()` / `SetWindSpeed()` / `GetWindMaximumSpeed()` / `SetWindMaximumSpeed()` (`:248-269`).
`SetStorm(float density, float threshold, float timeOut)` sets lightning: density 0..1, the overcast above which
lightning may appear, and the minimum seconds between strikes (`:211-219`). Measured on a fresh Chernarus
server: overcast 0.484, rain 0, fog 0, wind speed 10.

### Where the entity queries live

- On `Object` (`scripts/3_Game/Entities/Object.c`): `IsMan()` `:523`, `IsItemBase()` `:553`, `IsBuilding()`
  `:642`, `IsTransport()` `:686`, `GetSpeed()` (velocity vector in world space) `:335`, and
  `ProcessDirectDamage(int damageType, EntityAI source, string componentName, string ammoName, vector modelPos,
  float damageCoef = 1.0, int flags = 0)` `:1138`, whose `componentName` is the damage zone (doc `:1128-1137`).
- On `EntityAI`: `IsAnimal()` / `IsZombie()` (`scripts/3_Game/Entities/EntityAI.c:734`, `:739`).
- On `IEntity`: `GetTransform(out vector mat[])` / `SetTransform(vector mat[4])`
  (`scripts/1_Core/proto/EnEntity.c:288`, `:356`).

### Player state (`scripts/4_World/Entities/ManBase/PlayerBase.c`)

`GetStatWater()`, `GetStatEnergy()`, `GetStatHeatComfort()` return `PlayerStat<float>` (`:8197`, `:8215`,
`:8224`); read with `.Get()`, write with `.Set(value)` / `.Add(value)`
(`scripts/4_World/Classes/PlayerStats/PlayerStatBase.c:85`, `:129`). `GetBrokenLegs()` returns `eBrokenLegs`
(`:3966`; `NO_BROKEN_LEGS`, `BROKEN_LEGS`, `BROKEN_LEGS_SPLINT`, `scripts/3_Game/Enums/EBrokenLegs.c:1-6`).
`IsControlledPlayer()` is true only on the client that controls this character
(`scripts/4_World/Entities/ManBase.c:8-13`).

### Inventory (`scripts/3_Game/Systems/Inventory/`)

- `GameInventory` (`Inventory.c:80`): `CanAddEntityInCargo(EntityAI e, bool flip)` `:154`,
  `CanAddAttachment(EntityAI e)` `:241`, `FindFreeLocationFor(EntityAI item, FindInventoryLocationType flags, out
  InventoryLocation loc)` `:276`, `CreateEntityInCargo(string)` `:143`, `CreateAttachment(string)` `:209`,
  `CreateInInventory(string)` `:876`, `AttachmentCount()` `:205`, `GetAttachmentFromIndex(int)` `:220`,
  `GetCargo()` `:138` (a `CargoBase` with `GetItemCount()` / `GetItem(int)`, `Cargo.c:28`, `:32`), and
  `TakeEntityToInventory(InventoryMode mode, FindInventoryLocationType flags, EntityAI item)` `:1013`.
- `InventoryMode` is `PREDICTIVE`, `LOCAL`, `JUNCTURE`, `SERVER` (`Inventory.c:21-27`; `SERVER` only for code
  that runs on the server alone). `FindInventoryLocationType` is `ATTACHMENT`, `CARGO`, `HANDS`, `PROXYCARGO`,
  `ANY_CARGO`, `ANY`, `NO_SLOT_AUTO_ASSIGN` (`InventoryLocation.c:17-26`).
- `HumanInventory.CreateInHands(string)` (`HumanInventory.c:44`);
  `InventoryLocation.SetCargo(EntityAI parent, EntityAI e, int idx, int row, int col, bool flip)`
  (`InventoryLocation.c:152`).
- Player moves on `Man` (`scripts/3_Game/Entities/Man.c`): `PredictiveTakeEntityToHands(EntityAI)` `:178`,
  `PredictiveTakeEntityToInventory(FindInventoryLocationType, EntityAI)` `:381`,
  `ServerTakeEntityToInventory(FindInventoryLocationType, EntityAI)` `:402`,
  `PredictiveTakeToDst(InventoryLocation src, InventoryLocation dst)` `:738`.
- Item hooks: `ItemBase.OnInventoryEnter(Man)` / `OnInventoryExit(Man)`
  (`scripts/4_World/Entities/ItemBase.c:3906`, `:3918`); `EntityAI.OnMovedWithinCargo(EntityAI container)`,
  `OnWasAttached(EntityAI parent, int slot_id)`, `OnWasDetached(EntityAI parent, int slot_id)`
  (`scripts/3_Game/Entities/EntityAI.c:1375`, `:1864`, `:1867`).
- Quantity on `ItemBase`: `GetQuantity()` `:3490`, `GetQuantityMax()` `:3439`, `SetQuantity(...)` `:3319`,
  `AddQuantity(...)` `:3393`; rounds in a magazine: `Magazine.GetAmmoCount()`
  (`scripts/4_World/Entities/ItemBase/Magazine/Magazine.c:68`).

### Actions (`scripts/4_World/Classes/UserActionsComponent/`)

- Bases: `ActionSingleUseBase` (`Actions/ActionSingleUseBase.c:29`), `ActionContinuousBase`
  (`Actions/ActionContinuousBase.c:120`), `ActionInteractBase` (`Actions/ActionInteractBase.c:38`), all on
  `AnimatedActionBase`; `FirearmActionBase` sits directly on `ActionBase`
  (`Actions/Weapons/FirearmActionBase.c:1`).
- `CreateConditionComponents()` sets `m_ConditionItem` and `m_ConditionTarget` (`ActionBase.c:63-64`,
  `:245-248`). Item conditions in `ItemConditionComponents/`: `CCINone`, `CCIDummy`, `CCIPresent`,
  `CCINotPresent`, `CCINonRuined`, `CCINotEmpty`, `CCINotRuinedAndEmpty`, `CCINotRuinedAndDry`. Target
  conditions in `TargetConditionsComponents/`: `CCTNone`, `CCTDummy`, `CCTSelf`, `CCTMan`, `CCTObject(dist)`,
  `CCTParent`, `CCTCursor(dist)` and its `NoRuinCheck` / `Inherited` / `Parent` / `NoObject` variants,
  `CCTNonRuined`, `CCTSurface`, `CCTTree`, `CCTWaterSurface`, `CCTWaterSurfaceEx`, `CCTLiquid`. Distances come
  from `UAMaxDistances` (`Actions/ActionConstants.c:111-122`: `SMALL` 1.3, `DEFAULT` 2.0, `REPAIR` 3.0,
  `LARGE` 8.0, ...).
- Overrides: `GetText()` (returns `m_Text`, `ActionBase.c:330-333`), `ActionCondition(PlayerBase, ActionTarget,
  ItemBase)` (`:441`), `OnStartServer` / `OnStartClient` / `OnEndServer` / `OnEndClient` (`:1388-1409`),
  `OnExecuteServer` / `OnExecuteClient` (`AnimatedActionBase.c:179`, `:183`), `OnFinishProgressServer` /
  `OnFinishProgressClient` for continuous actions (`ActionContinuousBase.c:289`, `:293`),
  `CanBeUsedInVehicle()` (`ActionBase.c:361`).
- `ActionData` carries `m_Player`, `m_MainItem`, `m_Target` (an `ActionTarget`) and `m_ActionComponent`
  (`ActionBase.c:21-49`).
- A continuous action needs a callback class that sets its progress component. Vanilla pattern
  (`Actions/Continuous/ActionActivateTrap.c:1-34`): `class MyActionCB : ActionContinuousBaseCB` overrides
  `CreateActionComponent()` with `m_ActionData.m_ActionComponent = new CAContinuousTime(seconds);`, and the
  action's constructor sets `m_CallbackClass = MyActionCB;` (the base default is the plain
  `ActionContinuousBaseCB`, `ActionContinuousBase.c:126`).
- Registration: on an item, `override void SetActions()` with `super.SetActions(); AddAction(MyAction);`
  (`scripts/4_World/Entities/ItemBase.c:246`, `:255`). On the player, the current form is
  `SetActions(out TInputActionMap InputActionMap)` with `AddAction(MyAction, InputActionMap)`
  (`PlayerBase.c:1695`, `:1817`); the argument-less forms are kept only for backward compatibility (`:1747`, `:1838`).

### `MissionServer` hooks (`scripts/5_Mission/mission/missionServer.c`)

`OnEvent` (`:309`) dispatches the client events: `OnClientPrepareEvent` `:449`; `OnClientNewEvent` `:549` (which
calls `CreateCharacter(PlayerIdentity, vector pos, ParamsReadContext, string characterName)` `:499`, returning the
new `PlayerBase`) followed by `InvokeOnConnect`; `OnClientReadyEvent(PlayerIdentity, PlayerBase)` `:599` for a
character loaded from the database, also followed by `InvokeOnConnect(PlayerBase, PlayerIdentity)` `:435`;
`OnClientRespawnEvent` `:611`; `OnClientReconnectEvent` `:633`; `OnClientDisconnectedEvent(identity, player,
int logoutTime, bool authFailed)` `:641`. That one either starts the logout timer or, for an instant logout, calls
`PlayerDisconnected(PlayerBase, PlayerIdentity, string uid)` `:690`, which runs `InvokeOnDisconnect`, saves the
player and removes it. `uid` is `identity.GetId()`, and the source warns that `identity` may already be deleted
there (`:692`), so key any save on `uid`.
