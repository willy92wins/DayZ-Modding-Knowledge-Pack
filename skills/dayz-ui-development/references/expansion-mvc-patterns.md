# Expansion MVC Patterns — Verified Reference

Source: `salutesh/DayZ-Expansion-Scripts`, branch `release`, commit `8f75d554fda209b257c00deb8f01c181e67c980a`.
All path:line citations verified adversarially (claude + codex dual-arm, 0 discrepancies on codex-only cites).

---

## 1. Class Hierarchy (Expansion Core MVC)

```
Managed
  └─ ExpansionScriptView              // base: layout + controller + update timer
       └─ ExpansionScriptViewMenu     // adds: input lock, blur, UIManager lifecycle
            └─ (concrete menus)       // e.g. ExpansionMarketMenu, ExpansionQuestMenu
ExpansionViewController               // data binding hub (ObservableCollection, PropertyChanged)
ObservableCollection<ref T>           // notifies ViewController on Insert/Remove/Clear
```

Expansion's MVC is its own implementation in `DayZExpansion/Core/` — parallel to Dabs Framework
but NOT interchangeable. Do NOT mix Dabs `ScriptView` and `ExpansionScriptView` in the same menu.

---

## 2. ExpansionScriptViewMenu — OnShow/OnHide with blur + ForceDisable loop

**Path:line**: `DayZExpansion/Core/Scripts/5_Mission/DayZExpansion_Core/MVC/ScriptViews/Bases/ExpansionScriptViewMenu.c:43`
**Arms**: claude (C-P09) + codex (C-P14) — alta confianza.

```
override void OnShow()
{
    super.OnShow();
    LockControls();
    PPEffects.SetBlurMenu(0.5);
    SetFocus(GetLayoutRoot());
    CreateUpdateTimer();
}
override void OnHide()
{
    if (!g_Game) return;
    super.OnHide();
    PPEffects.SetBlurMenu(0.0);
    DestroyUpdateTimer();
    UnlockControls();
}
```

`LockControls()` iterates active inputs, preserves `UAUIBack`, and calls `ForceDisable` on each.
`CloseMenu()` delegates to `ExpansionUIManager`.

Rules:
- ALWAYS call `super.OnShow()` / `super.OnHide()` — base manages blur state and timer.
- ALWAYS guard `OnHide()` with `if (!g_Game) return` — called during shutdown.

---

## 3. ExpansionScriptView — Tick update opt-in (CALL_CATEGORY_GUI timer)

**Path:line**: `DayZExpansion/Core/Scripts/5_Mission/DayZExpansion_Core/MVC/ScriptViews/Bases/ExpansionScriptView.c:48`
**Arms**: claude (C-P10) — alta confianza.

```
float GetUpdateTickRate()
{
    return -1;   // -1 = no timer (default)
}
protected void CreateUpdateTimer()
{
    if (!m_UpdateTimer && GetUpdateTickRate() != -1)
    {
        m_UpdateTimer = new Timer(CALL_CATEGORY_GUI);
        m_UpdateTimer.Run(GetUpdateTickRate(), this, "Expansion_Update", NULL, true);
    }
}
```

Override `GetUpdateTickRate()` to return a positive float (seconds between ticks) to opt in.
Menu subclasses recreate the timer in `OnShow`/`OnHide`. Example: `ExpansionQuestHud` uses a
1-second tick to poll `GetClientQuestData()`.

---

## 4. ExpansionUIManager — Singleton menu lifecycle

**Path:line**: `DayZExpansion/Core/Scripts/3_Game/DayZExpansion_Core/ExpansionUIManager.c:101`
**Arms**: claude (C-P12) — alta confianza.

```
ExpansionScriptViewMenuBase CreateSVMenu(string viewName)
{
    ExpansionScriptViewMenuBase viewMenu;
    if (m_ActiveMenus.Find(viewName, viewMenu))
    {
        m_ActiveMenus.Remove(viewName);
        viewMenu.Destroy();
    }
    viewMenu = CreateMenuInstance(viewName);
    if (viewMenu)
    {
        SetMenu(viewMenu);
        m_ActiveMenus.Insert(viewName, viewMenu);
        viewMenu.Show();
```

`CreateSVMenu(viewName)` destroys any existing instance of the same class before creating a new
one — safe to call repeatedly. `CloseAll(includeVanilla)` closes ScriptViewMenus and
UIScriptedMenus separately. The range `MENU_EXPANSION_MENU_START..END` protects vanilla menus.

Open a menu from module code (e.g. after server-side validation):
```
// ExpansionMarketModule.c:4587 — after MoneyCheck() passes:
CreateSVMenu("ExpansionMarketMenu");
// Must be called on the client in MissionGameplay phase; workspace must be valid.
```

NEVER call `CreateSVMenu` from RPC handler context — workspace may be null mid-RPC.

---

## 5. ObservableCollection + ViewBinding — Declarative two-way binding

**Path:line (controller)**: `Scripts/5_Mission/DayZExpansion_Market/Market/ExpansionMarketMenu.c:3620`
**Path:line (layout root)**: `GUI/layouts/market/expansion_market_menu.layout:12`
**Path:line (widget binding)**: `GUI/layouts/market/expansion_market_menu.layout:77`
**Arms**: claude + codex — alta confianza.

```
class ExpansionMarketMenuController: ExpansionViewController
{
    ref ObservableCollection<ref ExpansionMarketMenuCategory> MarketCategories =
        new ObservableCollection<...>(this);
    ref ObservableCollection<ref ExpansionMarketMenuDropdownElement> DropdownElements = ...
    string MarketName;
    string PlayerTotalMoney;
    override void PropertyChanged(string property_name)
```

```
FrameWidgetClass ExpansionMarketMenu {
 scriptclass "ExpansionMarketMenuController"
 ...
      TextWidgetClass market_text {
       scriptclass "ViewBinding"
       Binding_Name "MarketName"
       Two_Way_Binding 1
```

Rules:
- Layout root: `scriptclass` names the controller class.
- Child widgets: `scriptclass "ViewBinding"` + `Binding_Name` must match a controller property exactly.
- Editable/checkbox widgets: `Two_Way_Binding 1` writes back to the controller.
- `ObservableCollection` auto-notifies the controller on `Insert`/`InsertAt`/`Remove`/`Clear`.

---

## 6. Subview composition — each row/element is its own ExpansionScriptView

**Path:line**: `Scripts/5_Mission/DayZExpansion_Market/Market/ExpansionMarketMenuItem.c:13` and `:119-126`
**Path:line**: `Scripts/5_Mission/DayZExpansion_Market/Market/ExpansionMarketMenuCategory.c:652`
**Arms**: codex (VERIFICADA) — alta confianza.

```
class ExpansionMarketMenuItem: ExpansionScriptView
    return "DayZExpansion/Market/GUI/layouts/market/expansion_market_menu_item_element.layout";

// Category controller (line 652):
ref ObservableCollection<ref ExpansionMarketMenuItem> MarketItems
```

Complex menus are NOT monoliths. Every item row, category panel, tooltip, dropdown, and dialog
is a separate subview with its own layout, controller, and observable collections.
The parent menu holds `ObservableCollection<ref SubviewType>` and inserts/removes subview
instances as data changes. This is the highest-value transferable pattern for complex Expansion menus.

---

## 7. Intermediate model filter before touching ObservableCollection

**Path:line**: `Scripts/5_Mission/DayZExpansion_Market/Market/ExpansionMarketMenu.c:436-452` and `:644-663`
**Arms**: codex (VERIFICADA) — alta confianza.

```
if (!m_TraderMarket.ItemExists(currentItem.ClassName) || m_TraderMarket.IsAttachmentBuySell(...))
    continue;
currentItem.m_ShowInMenu = true/false;  // filter in model
TempInsertItem(displayName, currentItem, tempItems);  // accumulate in temp list
...
m_MarketMenuController.MarketCategories.InsertAt(marketCategoryElement, i);  // only at the end
```

Maintain an intermediate model (`m_ShowInMenu` flag, temp lists) before modifying
`ObservableCollection`. The UI receives only pre-filtered, pre-sorted elements.
Avoids partial re-renders mid-collection.

---

## 8. ExpansionDialogBase — Composable dialogs via ObservableCollection

**Path:line**: `DayZExpansion/Core/Scripts/5_Mission/DayZExpansion_Core/MVC/ScriptViews/Dialogs/ExpansionDialogBase.c:118`
**Arms**: claude (C-P11) + codex (C-P15) — alta confianza.

```
class ExpansionDialogBaseController: ExpansionViewController
{
    ref ObservableCollection<ref ExpansionDialogContentBase> DialogContents =
        new ObservableCollection<ref ExpansionDialogContentBase>(this);
    ref ObservableCollection<ref ExpansionDialogButtonBase> DialogButtons =
        new ObservableCollection<ref ExpansionDialogButtonBase>(this);
    string DialogTitle;
};
```

Inject content/buttons via `AddContent()` / `AddButton()`. Conditional visibility controlled
by virtuals `HasHeader()`, `HasFooter()`, `HasCloseButton()`. Layout uses
`Binding_Name "DialogContents"` and `"DialogButtons"`.

---

## 9. Client settings UI — reflection via EnScript.GetClassVar with dot-path

**Path:line**: `DayZExpansion/Core/Scripts/3_Game/DayZExpansion_Core/Serialization/ExpansionSettingSerializationBase.c:53`
**Arms**: codex (C-P10, VERIFICADA) — alta confianza.

```
protected bool FindClassInstanceAndVariable()
{
    array<string> arr = {};
    m_Variable.Split( ".", arr );
    m_ActualInstance = m_Instance;
    for ( int i = 0; i < arr.Count() - 1; ++i )
    {
        EnScript.GetClassVar( m_ActualInstance, arr[i], 0, m_ActualInstance );
```

Accepts dot-path strings like `"Foo.Bar"` — walks the object graph via `EnScript.GetClassVar`.
`CreateToggle/CreateSlider/CreateEnum` build serialization objects per category. Use for generic
settings panels that bind UI controls to nested config objects without hardcoded field references.

---

## 10. HUD multi-pointer — Expansion vehicle HUD registration

**Path:line**: `DayZExpansion/Vehicles/Scripts/5_Mission/DayZExpansion_Vehicles/GUI/IngameHud.c:13`
**Path:line**: `DayZExpansion/Vehicles/Scripts/5_Mission/DayZExpansion_Vehicles/GUI/expansionboathud.c:39` and `:169`
**Path:line**: `DayZExpansion/Vehicles/GUI/layouts/hud/hud_boats.layout:170`
**Arms**: codex (Vehicles research) — alta confianza.

`modded class IngameHud` registers additional HUD panels keyed by a vehicle/entity type enum.
Each panel is a self-contained `ExpansionScriptView` subclass. The panel reads synced NetVar state
(`m_IsSync`, `m_HaltPhysics`, `m_IsInvulnerable`) and updates widget visibility in
`Expansion_Update()`. Pattern applies to any HUD overlay driven by server-synced state.

Note: legacy and modern HUD paths coexist under `EXPANSION_VEHICLES_HUD_OLD` compile flag.
Check which path is active in the target build before modifying HUD registration code.

---

## Key rules for Expansion MVC (summary)

1. NEVER instantiate `ExpansionScriptView` subclasses from RPC context — workspace may be null.
2. ALWAYS call `super.OnShow()` / `super.OnHide()` in every Expansion menu subclass.
3. The controller is an active state hub — `PropertyChanged` may cascade updates across multiple
   collections and settings simultaneously.
4. Filter and sort model data into a temp list BEFORE any `ObservableCollection` mutation.
5. `CreateSVMenu` is idempotent — safe to re-call; old instance is destroyed automatically.
6. `ObservableCollection` items with back-refs to their controller create circular ref leaks —
   null back-refs in item destructors.
