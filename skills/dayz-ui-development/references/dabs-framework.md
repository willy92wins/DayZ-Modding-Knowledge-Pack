# Dabs Framework — Verified Reference

Source: github.com/InclementDab/DayZ-Dabs-Framework (cloned and read 2026-03-23).
Every statement verified against actual source code.

> **PATH/BRANCH CORRECTION (2026-07-04, from layout-empirical-corpus.md §3, verified 2026-05-13):**
> the active branch is **`production`** (not master) and MVC sources live at
> `DabsFramework/Scripts/3_Game/DabsFramework/MVC/` (capitalized `Scripts` + extra `DabsFramework`
> segment — NOT the `DabsFramework/scripts/3_Game/MVC/` path used below). Raw URL pattern:
> `https://raw.githubusercontent.com/InclementDab/DayZ-Dabs-Framework/production/DabsFramework/Scripts/3_Game/DabsFramework/MVC/<File>.c`.
> The `Debug_Logging` field mentioned in older notes was NOT found at HEAD 2026-05-13 — treat as removed.

---

## Class Hierarchy

```
Managed
  └─ ScriptedViewBase          // base: m_LayoutRoot, m_WidgetController, events
       ├─ ViewController       // data binding, NotifyPropertyChanged, event dispatch
       ├─ ViewBinding          // Binding_Name, Two_Way_Binding, Relay_Command
       └─ ScriptView           // layout creation, Update loop, widget variable loading
            ├─ ScriptViewMenu  // input locking, cursor, UIManager integration
            └─ QuickView<T>    // programmatic widget creation (no layout file)
```

---

## ScriptView — Lifecycle (ScriptView.c)

### Constructor
1. `CreateWidget(null)` → `workspace.CreateWidgets(GetLayoutFile(), parent)`
2. `LoadWidgetsAsVariables(this, m_LayoutRoot)` — scans class fields of type Widget,
   matches by name via FindAnyWidget, assigns via EnScript.SetClassVar. ONE TIME ONLY.
3. `m_LayoutRoot.GetScript(m_Controller)` — checks if layout root has scriptclass
4. If no controller found: `GetControllerType().Spawn()` creates one
5. `LoadWidgetsAsVariables(m_Controller, m_LayoutRoot)` — same scan for controller fields
6. `m_Controller.OnWidgetScriptInit(m_LayoutRoot)` — loads ViewBindings, sets handler
7. If `UseUpdateLoop()` true: registers Update in CALL_CATEGORY_SYSTEM queue

### Destructor
1. Remove from update queue (with GetGame() null check)
2. `delete m_Controller`
3. `m_LayoutRoot.Unlink()` — destroys entire widget tree
4. Remove from static `All` array

### Key overrides
```
string GetLayoutFile()           // REQUIRED — path to .layout
typename GetControllerType()     // default: ViewController
bool UseUpdateLoop()             // default: true
void Update(float dt)            // called every frame if UseUpdateLoop
```

### GetLayoutRoot() timing
Valid IMMEDIATELY after constructor. `TooltipView` in Dabs creates a ScriptView
and calls GetLayoutRoot().GetScreenSize() on the next line — works in production.

---

## ViewController — Data Binding (ViewController.c)

### LoadDataBindings (called in OnWidgetScriptInit)
Walks the widget tree recursively. For each widget with `scriptclass "ViewBinding"`:
1. Sets parent to this controller
2. Inserts into `m_ViewBindingHashMap` (map<Widget, ViewBinding>)
3. Inserts into `m_DataBindingHashMap` (map<string, set<ViewBinding>>)
4. Loads RelayCommand if specified
5. Calls initial `NotifyPropertyChanged(binding_name, false)` to sync view

Stops recursion when it hits another ViewController (child controllers).

### NotifyPropertyChanged(string property_name, bool notify_controller = true)
- With name: looks up `m_DataBindingHashMap[name]`, calls `UpdateView` on each
- Empty name: iterates ALL bindings (expensive, logged as "NOT recommended")
- `notify_controller = false` skips PropertyChanged callback — prevents recursion
- `NotifyPropertiesChanged(array<string>)` — batch update

### PropertyChanged(string property_name)
Virtual callback, called AFTER view is updated. Override for cross-property logic.
Use `notify_controller = false` when setting properties inside PropertyChanged to
avoid infinite loops.

### Sub-property binding
Supports dot notation: `"m_MyObj.value"` resolves via `PropertyInfo.GetSubScope`.
Demonstrated in SampleMVC.c:185.

---

## ViewBinding — The Glue (ViewBinding.c)

### Layout properties
```
reference string Binding_Name;     // controller property name
reference string Selected_Item;    // selection property name
reference bool Two_Way_Binding;    // view→controller sync
reference string Relay_Command;    // command name or function name
```

### UpdateView (Controller → Widget)
Reads property from controller via TypeConverter, writes to widget via WidgetController.Set().
Called by NotifyPropertyChanged.

### UpdateController (Widget → Controller)
Only if Two_Way_Binding AND CanTwoWayBind(). Reads widget, writes to controller,
calls NotifyPropertyChanged. Triggered by OnClick/OnChange.

### InvokeCommand
Priority: 1) RelayCommand variable on controller, 2) RelayCommand typename,
3) `g_Script.CallFunction(context, name, handled, args)`.
If not handled, propagates UP to parent controller.

---

## Relay_Command — Three Patterns

### Pattern 1: Function on controller (SIMPLEST — RECOMMENDED)
```
// Layout: Relay_Command "OnSaveExecute"
// Controller:
bool OnSaveExecute(ButtonCommandArgs args)
{
    // your logic
    return true; // handled
}
```

### Pattern 2: RelayCommand variable on controller
```
// Controller field:
ref RelayCommand m_SaveCommand;
// Dabs auto-initializes if null
```

### Pattern 3: RelayCommand class by typename
```
// Layout: Relay_Command "MySaveCommand"
// Separate class:
class MySaveCommand : RelayCommand
{
    override bool Execute(Class sender, CommandArgs args) { return true; }
}
```

### CommandArgs types
- `ButtonCommandArgs` — has ButtonWidget ref + button int
- `CheckBoxCommandArgs` — has CheckBoxWidget ref
- Generic `CommandArgs` — base class with Context (ViewBinding)

---

## ObservableCollection (ObservableCollection.c)

### Constructor
```
ref ObservableCollection<MyView> m_Items = new ObservableCollection<MyView>(this);
```
Must pass ViewController reference. Template type must be a Class (ref type).

### Operations (all auto-notify UI)
```
int Insert(TValue value)
int InsertAt(TValue value, int index)
void InsertAll(array<TValue> from)
void Remove(int index)
void Remove(TValue value)
void RemoveOrdered(int index)
void Set(int index, TValue value)
int MoveIndex(int index, int moveIndex)
void SwapItems(int itemA, int itemB)
void Clear()
TValue Get(int index)
int Count()
int Find(TValue value)
array<ref TValue> GetArray()
```

### SpacerBase integration
Bind to a SpacerBaseWidget (WrapSpacer, GridSpacer). ObservableCollection items that
are ScriptView instances automatically have their layout root added/removed as children.
TypeConversionScriptView.GetWidget() returns the ScriptView's layout root.

### Circular ref warning
If items hold `ref` to the parent controller, GC cannot break the cycle.
Fix: null the back-ref in item destructor.

---

## Two_Way_Binding Support

| Widget | CanTwoWayBind | Set (C→V) | Get (V→C) |
|---|---|---|---|
| EditBoxWidget | YES | SetText | GetText |
| ButtonWidget | YES | SetState(bool) | GetState |
| CheckBoxWidget | YES | SetChecked | IsChecked |
| SliderWidget | YES | SetCurrent | GetCurrent |
| SpacerBaseWidget | YES | AddChild | GetFocus (selection) |
| MultilineEditBoxWidget | YES | SetText | GetText |
| TextWidget | NO | SetText | — |
| ImageWidget | NO | LoadImageFile | — |
| XComboBoxWidget | — | — | — |

---

## WidgetAnimator (Core/WidgetAnimator.c)

Complete animation system built into Dabs. DO NOT build custom tween systems.

### API
```
// Animate from current to end
static void Animate(Widget src, WidgetAnimatorProperty prop, float end, TimeSpan time)

// Animate with explicit start
static void Animate(Widget src, WidgetAnimatorProperty prop, float start, float end, int time)

// Animate with easing
static void AnimateEx(Widget src, WidgetAnimatorProperty prop, float end, TimeSpan time, WidgetAnimatorEasing easing)

// Loop animation
static void AnimateLoop(Widget src, WidgetAnimatorProperty prop, float end, int time)

// Color animation with blend modes
static void AnimateColor(Widget src, LinearColor end, TimeSpan time, BlendMode blend, bool loop)
static void AnimateColor(Widget src, LinearColor start, LinearColor end, TimeSpan time, BlendMode blend, bool loop)

// HSV color animation
static void AnimateColorHSV(Widget src, vector start, vector end, TimeSpan time, bool loop, WidgetAnimatorEasing easing)

// Control
static void CancelAnimate(Widget src, WidgetAnimatorProperty prop = -1, bool reset = false)
static bool HasAnimation(Widget src, WidgetAnimatorProperty prop)
static WidgetAnimatorProperty GetAnimations(Widget src)
```

### WidgetAnimatorProperty (bitmask flags)
```
POSITION_X = 1      POSITION_Y = 2
SIZE_W = 4           SIZE_H = 8
SIZE_EXACT_W = 32768 SIZE_EXACT_H = 65536
ROTATION_X = 16      ROTATION_Y = 32      ROTATION_Z = 64
COLOR_A = 128        COLOR_R = 256        COLOR_G = 512     COLOR_B = 1024
COLOR_H = 2048       COLOR_S = 4096       COLOR_V = 8192
EXACT_TEXT = 16384
LINEAR_COLOR = 1920  // A+R+G+B combined
```

### WidgetAnimatorEasing (30 curves)
NONE, EASE_IN/OUT/INOUT for: Sine, Quad, Cubic, Quart, Quint, Exponential,
Circ, Back, Elastic, Bounce.

### Internals
- Uses CALL_CATEGORY_GUI update queue
- Auto-cancels previous animation of same property on same widget
- Self-deletes timer on completion
- TextWidget COLOR_A also updates outline alpha

---

## LinearColor (Core/Color.c)

ARGB integer format with full color utilities.

### Construction
```
LinearColor.Create(r, g, b)           // ints 0-255
LinearColor.Create(a, r, g, b)        // ints 0-255
LinearColor.CreateF(r, g, b)          // floats 0-1
LinearColor.CreateF(a, r, g, b)       // floats 0-1
LinearColor.CreateHSV(hue, sat, val, alpha)  // hue 0-360, rest 0-1
```

### Access
```
int GetAlpha(), GetRed(), GetGreen(), GetBlue()
void SetAlpha(int), SetRed(int), SetGreen(int), SetBlue(int)
float GetLuminance()
string ToHexColor()
vector ToVector()            // float RGB [0,1]
```

### Operations
```
LinearColor.Lerp(a, b, blendMode, t)   // interpolation
LinearColor.Blend(a, b, blendMode)     // blend
bool IsEqual(other, epsilon)            // fuzzy compare
LinearColor Add/Subtract/Multiply
```

### BlendModes
NORMAL, MULTIPLY, SCREEN, OVERLAY, HARD_LIGHT, SOFT_LIGHT

### Named constants (140+)
LinearColor.RED, .BLUE, .DARK_SLATE_GRAY, .CORNFLOWER_BLUE, etc. (X11 color set)

---

## ScriptViewMenu (MVC/ScriptViewMenu.c)

Extends ScriptView with automatic input/cursor management.

### Overrides
```
bool UseMouse()            // default true — shows cursor, locks mouse
bool UseKeyboard()         // default false — locks keyboard
bool UseUIManager()        // default true — registers with UIManager
array<string> GetInputExcludes()  // specific.xml exclude names
bool HidesParentMenu()     // default true
bool CanClose()            // guard for close
bool CanCloseWithEscape()  // ESC handling
```

### Methods
```
void Close()                              // deferred delete via CallLater
UIScriptedMenu EnterChildMenu(ScriptViewMenu menu)
UIScriptedMenu EnterChildMenu(int id)
void ShowDialog(string caption, text, id, buttons, default, type)
```

### What it handles automatically
- `ChangeGameFocus(1, INPUT_DEVICE_MOUSE/KEYBOARD)` on create
- `SetMouseCursorDesiredVisibility` with 2-frame delay safety
- Input excludes via `AddActiveInputExcludes`
- Menu hierarchy via `ShowScriptedMenu/HideScriptedMenu`
- OnMenuEnter/OnMenuExit for parent/child transitions

### Trade-off
Uses UIManager menu stack. May conflict with other mods that manage menus.
For floating windows that coexist with gameplay (Sorter), manual
ChangeGameFocus + SetDisabled is still recommended.

---

## Prefab Layouts Available in Dabs

```
DabsFramework/GUI/layouts/prefabs/
  ButtonPrefab.layout
  CheckBoxPrefab.layout
  ColorPickerPrefab.layout
  DropdownPrefab.layout + DropdownElementPrefab.layout
  EditBoxPrefab.layout
  EditboxSliderPrefab.layout
  GroupPrefab.layout
  HorizontalSpacerPrefab.layout
  ListBoxPrefab.layout
  MultilineEditBoxPrefab.layout
  MessageBoxPrefab.layout (uses RichTextWidget)
```

---

## Proven Production Patterns

### ScrollWidget + WrapSpacer + ObservableCollection
From Dabs options_tab.layout:
```
ScrollWidgetClass Scroll {
  "Scrollbar V" 1
  {
    WrapSpacerWidgetClass Content {
      scriptclass "ViewBinding"
      "Size To Content V" 1
      {
        ScriptParamsClass {
          Binding_Name "MyCollection"
        }
      }
    }
  }
}
```

### Function-as-command (from SampleMVC.c)
```
// Layout: Relay_Command "SwapItemsExecute"
bool SwapItemsExecute(ButtonCommandArgs args)
{
    m_Collection.SwapItems(m_Left, m_Right);
    return true;
}
```

### Color animation (from OptionSelectorColorViewController.c)
```
WidgetAnimator.AnimateColor(ColorPickerPanel, Value, 10);
```

### Widget position relative to parent (from OptionSelectorColorViewController.c)
```
static void SetWidgetPosRelativeToParent(Widget w, float x, float y)
{
    x = Math.Clamp(x, 0, 1);
    y = Math.Clamp(y, 0, 1);
    Widget parent = w.GetParent();
    float pW, pH;
    parent.GetScreenSize(pW, pH);
    float wW, wH;
    w.GetScreenSize(wW, wH);
    w.SetPos((pW * x) - (wW / 2), (pH * y) - (wH / 2));
}
```


---

# HEAD DEEP-DIVE 2026-07-05 — verified at production commit fd859fd8 (shallow clone)

Everything below was read from a real clone of `production` HEAD (fd859fd8, last code commit
2025-12-18) and adversarially verified. **Branch/version state**: `production` is the default branch;
the Steam Workshop build (id 2545327648, 3.36M subscribers, updated 2026-05-30) tracks `staging` —
but **the MVC/UI layer is byte-identical between the two** (the 31-file branch diff touches nothing
under `MVC/` or `!Core/WidgetAnimator*`), so these cites describe what servers actually run. There
are NO releases/tags. Feature-detect with `#ifdef DABSFRAMEWORK_1_51` (defined atop
`ScriptedViewBase.c`), not Version.hpp (stuck at '1.5' on both branches).
PBO/dependency reality: DF ships CfgPatches classes **`DF_Scripts`** (requires `DZ_Scripts`,`DF_GUI`)
and **`DF_GUI`** — mods must require those, never "DabsFramework" (that is only the CfgMods name).

## ScriptViewMenu — the real contract (corrects this file's older notes + SKILL.md)

- **NO OnShow/OnHide exist on ScriptView/ScriptViewMenu.** The only OnShow/OnHide in the repo are
  UIScriptedMenu overrides inside the internal wrapper `UIScriptViewMenu.c:54/:61`, which forward to
  `ScriptViewMenu.OnMenuEnter(parent)/OnMenuExit(parent)` — those two are the overridable lifecycle
  hooks. Show/hide a plain ScriptView with `ScriptedViewBase.Show(bool)` / `IsVisible()`.
- **Construct-to-open, Close-to-deferred-delete**: the ScriptViewMenu constructor itself registers
  and shows the menu (creates `ref UIScriptViewMenu m_UIScriptViewMenu = new UIScriptViewMenu(this)`
  and calls `ShowScriptedMenu(...)` when `UseUIManager()`); `Close()` → `CallLater(_Close)` in
  CALL_CATEGORY_GUI → `if (CanClose()) delete this`.
- **ESC does NOT close a Dabs menu** (corrects SKILL.md's "handles ESC automatically"):
  `CanCloseWithEscape()` exists but has ZERO callers repo-wide (author comment: "tbd how i want to
  handle this"). Wire ESC yourself (e.g. OnKeyPress KC_ESCAPE → Close()).
- **Override-point list at HEAD**: `UseMouse()` [def true], `UseKeyboard()` [def false],
  `UseUIManager()` [def true], `GetInputExcludes()` [wired: Mission.AddActiveInputExcludes in ctor /
  Remove in dtor], `GetInputRestrictions()` [**DEAD CODE** — ctor/dtor iterate a fresh empty local
  array instead of calling it; overriding does nothing], `HidesParentMenu(UIMenuPanel parent)` [now
  takes a parameter; def true], `CanClose()`, `CanCloseWithEscape()` [uncalled], `OnMenuEnter/OnMenuExit`.
- **Game-focus release on close is COMMENTED OUT** in the dtor (`//g_Game.GetInput().ChangeGameFocus(-1,...)`)
  and `UIScriptViewMenu` overrides LockControls/UnlockControls as EMPTY — only cursor visibility is
  restored. A mod stacking its own ChangeGameFocus around a Dabs menu can leak focus counts; verify
  input state after close.
- `ScriptViewTemplate<Class T>` / `ScriptViewMenuTemplate<Class T>` exist (undocumented before):
  typed-controller sugar — `GetControllerType()` returns T, `GetTemplateController()` returns it typed.

## LoadWidgetsAsVariables — mechanism (resolves SKILL.md Rule 8's "why")

- Implementation is a **flat loop**: for every Widget-typed property it does exactly ONE
  `root.FindAnyWidget(property_name)` — no recursion, no ButtonWidget special-casing, no workaround.
  The `// fixes bug that breaks everything` guard only skips assignment on null.
- The framework's own answer for nested/child lookup is **dot-naming**: name children `Button.Icon`,
  `Button.Text` in the layout and resolve via `ScriptView.FindWidgetClass(parent, classname)` (splits
  on '.') or the generic `FindWidget<T>.SearchDown(parent, name)` in 1_Core.
- **Asymmetry**: when ScriptView auto-spawns the controller (no scriptclass on layout root), it calls
  `LoadWidgetsAsVariables(m_Controller, root)` so controller Widget fields populate; when the
  controller IS declared as `scriptclass` on the root (Workbench style), NOTHING populates its Widget
  fields — bind them yourself or use ViewBindings.
- Constructor deltas vs the 7-step lifecycle above: steps 5-6 only run in the auto-spawn branch; new
  steps `m_Controller.SetParent(this)` + `m_LayoutRoot.SetUserData(this)`; server-side creation is
  guarded (`ErrorEx` under `#ifndef COMPONENT_SYSTEM/NO_GUI`).
- **`Debug_Logging` EXISTS** (corrects layout-empirical-corpus.md §3's "treat as unverified"): it is
  `[NonSerialized()] reference bool Debug_Logging` on ScriptedViewBase — settable from layout
  ScriptParams, propagates to children via SetParent.
- **DIAG hot-reload**: under `#ifdef DIAG_DEVELOPER`, `static ScriptView.ReloadAll()`
  (`MVC/ScriptView.c:126-134`, comment "Hot reload all widgets layouts") Unlinks + rebuilds every
  live ScriptView's layout — a ready-made layout-iteration accelerator for Dabs UIs under DayZDiag;
  wire it to a keybind/DbgUI button.

## Relay_Command / RelayCommand — dispatch reality

- **Relay_Command only fires from TWO widget types**: ButtonWidget (ViewController.OnClick →
  ButtonCommandArgs) and CheckBoxWidget (OnChange → CheckBoxCommandArgs). XComboBoxCommandArgs /
  WrapSpacerCommandArgs exist in CommandArgs.c but extend Param2 and have NO dispatch site.
- **Double-fire mechanism corrected** (refines SKILL.md Rule 20): at HEAD, ViewController.OnClick
  returns true immediately when InvokeCommand reports handled (super.OnClick is NOT then called).
  The REAL double-execution risk: a command handler that returns false/void — ViewBinding.InvokeCommand
  then walks UP the parent chain re-invoking the SAME function name on each ancestor.
  **Rule: command handlers must `return true` when handled.**
- `RelayCommand` class contract: abstract `Managed` subclass with `SetController/SetViewBinding`,
  overridable `bool CanExecute()` (checked before Execute) and abstract
  `bool Execute(Class sender, CommandArgs args)`. Resolution order in LoadRelayCommand:
  (1) controller property with that name, (2) typename spawn, (3) plain function call.

## Observables — full contract

- `ObservableCollection<T>` full API (adds RemoveRange to the older list): `Insert(v)→int`,
  `InsertAt(v,idx)`, `InsertAll(array)`, `Remove(idx)`, `Remove(value)`, `RemoveOrdered(idx)`,
  `RemoveRange(start,end)`, `Set(idx,v)`, `MoveIndex(idx,to)`, `SwapItems(a,b)`, `Clear()`,
  `Get(idx)`, `Count()`, `Find(v)→int`, `GetArray()`. Storage `ref array<ref TValue>`.
- **Binding contract**: the layout ViewBinding's `Binding_Name` must equal the CONTROLLER VARIABLE
  NAME holding the collection — NotifyCollectionChanged resolves it by reverse instance lookup and
  errors 'could not find variable' otherwise.
- **Item-view contract** for collections of ScriptView: element type = ScriptView subclass overriding
  `GetLayoutFile()`; each instance builds its own tree (parent null); on Insert the item's layout
  root is reparented into the bound spacer via `AddChild`.
- **ObservableSet is broken at HEAD — do not recommend** (references enum members Add/Set that don't
  exist in NotifyCollectionChangedAction).
- Widget↔controller registry is **EXACT-type** (map lookup on `data.Type()`, no inheritance walk):
  a binding on an unregistered widget type errors 'Could not find WidgetController for type X'.
- ButtonWidgetController two-way semantics: Set/Get ↔ SetState/GetState (pressed bool);
  `Selected_Item` on a button binds its LABEL text (SetText/GetText). ViewBinding validates
  Two_Way_Binding at init (Error 'Two Way Binding ...' on non-two-way widgets).

## WidgetAnimator — verified pitfalls (5)

File really lives at `Scripts/3_Game/DabsFramework/!Core/WidgetAnimator.c` (not MVC/).
1. **Time unit is MILLISECONDS**, but the `TimeSpan` typedef's helpers are SECONDS-based —
   `TimeSpan.FromMinutes(1)` animates over 60 **ms**: a 1000× trap. Pass plain ms ints.
2. **EASE_IN_BOUNCE and EASE_OUT_BOUNCE are SWAPPED** in the implementation.
3. **AnimateColor silently no-ops when current == end color** (including loop=true).
4. **AnimateColorHSV does NOT cancel prior animations** (every other entry point does) and spawns 3
   separate timers (H/S/V).
5. Completed/self-deleted timers are **never removed from the static m_RunningTimers array** (only
   CancelAnimate removes) — long sessions leak slots. Deleting/Unlinking a widget mid-animation is
   safe (weak ref; timer self-cleans next GUI tick).

## Event flow + issues

- All ScriptedViewBase On* events bubble UP via m_ParentScriptedViewBase (ViewController →
  ScriptView), dispatched from the root's SetHandler installed in ViewController.OnWidgetScriptInit
  (confirms Rule 10's "Dabs does SetHandler automatically"). Exception: **OnResize is dead code**.
- LoadDataBindings recursion: stops descending at widgets whose script instance is another
  ViewController (child-controller subtrees are skipped and get SetParent) and never bleeds into the
  root's siblings — relevant when debugging 'binding not found'.
- GitHub wiki is empty for UI; the 43-issue tracker has ZERO ViewBinding/ScriptView/WidgetAnimator
  reports — the MVC layer's known issues are only discoverable by reading source (as done here).

## ScriptView click dispatch and external automation (added 2026-08-31)

Dabs uses two different objects in its click path. Confusing them produces a silent “no handler”:

1. `ScriptedViewBase` derives from `Managed`, not `ScriptedWidgetEventHandler`
   (`ScriptedViewBase.c:4`). The actual event bridge is
   `ScriptedViewBaseHandler : ScriptedWidgetEventHandler` (`ScriptedViewBaseHandler.c:2-13`), which
   forwards `OnClick(Widget w, int x, int y, int button)` to its `ScriptedViewBase`.
2. `ViewController` owns that bridge and installs it with
   `m_LayoutRoot.SetHandler(m_ScriptedViewBaseHandler)` (`ViewController.c:56-63`). Separately,
   `ScriptView` writes the **view** into root userdata with `m_LayoutRoot.SetUserData(this)`
   (`ScriptView.c:86-87,149-150`). `SetHandler` does not make `GetScript()` return the handler.
3. Event methods bubble `ViewController -> ScriptView`
   (`ScriptedViewBase.c:148-151`). Always pass the widget that was actually clicked. A view that
   dispatches on `w.GetUserID()` silently misses when automation substitutes the layout root.

A generic handler search that walks parents and casts only `GetScript()`/`GetUserData()` to
`ScriptedWidgetEventHandler` will therefore miss a valid Dabs view: root userdata is a
`ScriptView`, while the bridge is held by the controller. This describes the framework's internal
contract; it does **not** override `SKILL.md` §“Los clics sobre ScriptViews no son automatizables por
el MCP”. An external harness still needs a way to discover the ScriptView root and target the real
clicked widget, and the measured 2026-08-29 bridge did not provide that path.

Visual dimming is not input gating. `DimButton`-style helpers only tint the widget; a dim button
continues to receive clicks. Put the permission/state guard in the handler and return before any
RPC or state change.
