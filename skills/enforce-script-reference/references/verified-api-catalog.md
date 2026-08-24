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
    do {
        bool isDir = (attr & FileAttr.DIRECTORY);
    } while (FindNextFile(fh, filename, attr));
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
//   P:\scripts\4_world\entities\core\inherited\inventoryitem.c:81,149,293,948
//   P:\scripts\4_world\entities\core\inherited\itemoptics.c:258,271
//   P:\scripts\4_world\entities\explosivesbase\plastic_explosive.c:148,160
```

### Runtime selection visibility (EntityAI)
```
ShowSelection(string selection_name);   // make a named selection visible
HideSelection(string selection_name);   // hide it
// Verified: P:\scripts\3_game\entities\entityai.c:3356 (ShowSelection), :3365 (HideSelection)
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


### Slot enumeration — which API pair to use (verified vs vanilla 2026-07-29)
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
