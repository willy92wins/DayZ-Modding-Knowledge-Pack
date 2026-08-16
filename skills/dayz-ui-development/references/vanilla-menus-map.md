# Vanilla DayZ Menus & HUD — Source Map + Copyable Patterns

Added 2026-07-04. Source: sweep of `scripts/5_mission` (209 files) + `3_game/tools/uiscriptedmenu.c`
+ `uimanager.c` + `3_game/gui/widgetlayoutname.c`, adversarially verified (every path:line re-read).
Paths relative to `<dayz-projects>\scripts\`. Use this file to find
WHICH vanilla menu to copy from, and the contracts that make copied code behave.

## 1. Menu → class file → layout table

| Menu | Class file | Layout loaded |
|---|---|---|
| MainMenu | `5_mission/gui/newui/mainmenu/mainmenu.c:55` | `new_ui/main_menu.layout` (consoles: `mainmenuconsoles.c:47/49`) |
| InGameMenu (ESC) | `gui/ingamemenu.c:38` | `day_z_ingamemenu.layout` (Xbox: `ingamemenuxbox.c:131/133`) |
| InventoryMenu | `gui/inventorymenu.c:34` — **no CreateWidgets**: `layoutRoot = m_Inventory.GetMainWidget()` | via `WidgetLayoutName` registry: `inventory_new/{narrow\|medium\|wide\|xbox}/day_z_inventory_new.layout` |
| OptionsMenu | `gui/newui/options/optionsmenu.c:42-51` | `new_ui/options/{msstore\|xbox\|ps\|pc}/options_menu.layout` |
| CharacterCreation | `gui/newui/charactercreation/charactercreationmenu.c:82/85` | `new_ui/character_creation/{xbox\|pc}/...` |
| MapMenu | `gui/mapmenu.c:51` | `day_z_map.layout` |
| ServerBrowser | `newui/serverbrowsermenu/serverbrowsermenunew.c:32/37` | `new_ui/server_browser/{xbox\|pc}/server_browser.layout` |
| Keybindings | `newui/keybindings/keybindingsmenu.c:33/35` | `new_ui/options/{msstore\|pc}/keybinding_menu.layout` |
| GesturesMenu (radial) | `gesturesmenu.c:197` | `radial_menu/radial_gestures/day_z_gestures.layout` |
| RadialQuickbar | `radialquickbarmenu.c:171` | `radial_menu/radial_quickbar/radial_quickbar_menu.layout` |
| ChatInput | `chat/chatinputmenu.c:16` | `day_z_chat_input.layout` |
| LogoutMenu | `logoutmenu.c:47` | `day_z_logout_dialog.layout` |
| RespawnDialogue | `respawndialogue.c:21` | `day_z_respawn_dialogue.layout` |
| NoteMenu | `notemenu.c:90` | `day_z_inventory_note.layout` |
| BookMenu | `bookmenu.c:13` | `day_z_book.layout` |
| InspectMenuNew | `inspectmenunew.c:33` | `inventory_new/day_z_inventory_new_inspect.layout` |
| Loading / Startup | `loadingmenu.c:13` / `startupmenu.c:13` | `loading.layout` / `startup.layout` |
| Tutorials / Credits | `newui/mainmenu/tutorialsmenu.c:27/29` / `newui/credits/creditsmenu.c:33` | `new_ui/tutorials/...` / `new_ui/credits/credits_menu.layout` |
| ScriptConsole (diag) | `scriptconsole.c:124` | `script_console/script_console.layout` |
| **HUD root (not a menu)** | `mission/missiongameplay.c:125` | `day_z_hud.layout` |

Platform pattern: `#ifdef PLATFORM_CONSOLE` guards (charactercreation/serverbrowser/tutorials) or the
full `PLATFORM_MSSTORE → PLATFORM_XBOX → PLATFORM_PS4 → PLATFORM_WINDOWS` cascade at CreateWidgets
time (`optionsmenu.c:41-55`).

## 2. Registering a modded menu ID (the vanilla-mirroring recipe)

`MissionBase.CreateScriptedMenu` (`5_mission/mission/missionbase.c:185-333`) is the single factory
switch mapping 42 `MENU_*` ids → classes, with **SetID applied ONCE, AFTER the switch**
(`:327-330: if (menu) { menu.SetID(id); } return menu;`). Copyable modded registration:

```c
modded class MissionGameplay
{
    override UIScriptedMenu CreateScriptedMenu(int id)
    {
        UIScriptedMenu menu = super.CreateScriptedMenu(id);
        if (!menu)
        {
            switch (id)
            {
                case MY_MENU_ID: menu = new MyMenu(); break;
            }
            if (menu) menu.SetID(id);   // vanilla-mirroring: MISSING THIS leaves GetID()==MENU_UNKNOWN
        }
        return menu;
    }
}
```

Skipping `SetID` breaks `FindMenu/IsMenuOpen/CloseMenu`, which walk the menu chain comparing
`GetID()` (`3_game/tools/uimanager.c:117-175`; ctor sets `m_id = MENU_UNKNOWN`,
`uiscriptedmenu.c:138`). Vanilla ids are 1..46 — pick an arbitrary high int.

## 3. UIScriptedMenu contract (rules that bite)

From `3_game/tools/uiscriptedmenu.c`:
- **Init()** (:161-166): create widgets, return layout root. "widgets will be destroyed automatically
  by c++ side" — **do NOT Unlink layoutRoot in a menu** (grep: no vanilla menu ever does).
- **OnShow/OnHide** (:173-192) auto Lock/UnlockControls (per-device ChangeGameFocus + cursor;
  UnlockControls restores the cursor to the PARENT menu's `UseMouse()` preference) and register/remove
  the player-death invoker. Call `super` when overriding.
- **CRITICAL non-obvious rule: EVERY event override must call `super`** — the base fans all 23 events
  out to active `UIScriptedWindow` instances (`:238-252` OnClick loops
  `UIScriptedWindow.GetActiveWindows()`); skipping super silently breaks scripted windows (e.g. the
  MissionLoader window, `uimanager.c:193`).
- **IsHandlingPlayerDeathEvent()** returns true by default → menu force-`Close()`s on death
  (:603-611); override to false to survive.
- Submenus: `EnterScriptedMenu(id)` from the current menu sets it as parent (:11-12;
  `ingamemenu.c:251-254`); `UIManager.Back()` pops (:uimanager.c:62-75).
- Console-only: `SetWidgetAnimAlpha(w)` + base `Update()` gives the pulsing selected-element
  animation on PLATFORM_CONSOLE (:155-159, 195-228).

## 4. Two instantiation strategies (pick per menu weight)

- **(A) create-per-open** — `EnterScriptedMenu(MENU_X, parentMenu)`; vanilla pause menu:
  `missiongameplay.c:1285` + `AddActiveInputExcludes({"menu"})` + INVENTORY restriction (:1291-1292);
  closed via `Continue()` → RemoveActiveInputExcludes + `CloseMenu(MENU_INGAME)` (:1297-1312).
  For cheap dialogs.
- **(B) create-ONCE + show/hide** — vanilla inventory: `InitInventory()` creates once via
  `CreateScriptedMenu(MENU_INVENTORY, null)` (:208-214); `ShowInventory()` re-shows the SAME cached
  instance via `ShowScriptedMenu(m_InventoryMenu, null)` (:1153-1172); `HideInventory()` →
  HideScriptedMenu (:1174-1184). Keeps the Init()-built widget tree alive across opens — copy for
  heavyweight menus (inventory rebuilds a whole container tree in Init).
- Key-open pattern = input polling in Mission OnUpdate: `GetUApi().GetInputByID(UAGear).LocalPress()`
  → ShowInventory (:501-512); `UAUIMenu` → Pause (:691-697).
- Vanilla input-exclude group names used in missiongameplay.c: `"menu"`, `"inventory"`,
  `"radialmenu"`, `"loopedactions"`, `"map"`.

## 5. HUD ownership chain + extension points

- `MissionGameplay` ctor creates `m_Hud = new IngameHud` (`missiongameplay.c:67`); `OnInit()` loads
  ONE layout `day_z_hud.layout` (:125), hides it (:127; shown at :488 only when player exists, is
  ALIVE and conscious), then Inits each subsystem with a NAMED SUBTREE: Chat→`ChatFrameWidget`
  (:129), ActionMenu→`ActionsPanel` (:131), IngameHud→`HudPanel` (:133), mic/voice/chat-channel
  panels (:136-158). `OnMissionFinish` deletes the root (:266) — **modded HUD widgets parented
  elsewhere must self-clean**.
- `IngameHud.Init` resolves ~31 sub-widgets by name (+~35 generated in InitBadgesAndNotifiers)
  (`ingamehud.c:143-240`) — **the widget names in day_z_hud.layout are load-bearing API**.
- Safest modded extension points: (1) `modded class IngameHud` override `Init(Widget hud_panel)` →
  super, then add widgets inside the HudPanel subtree; (2) `modded class MissionGameplay` override
  `OnInit` → super, then `CreateWidgets(your.layout)` as a SIBLING root — the same pattern vanilla
  uses for HudDebug (:168).
- **Show/hide HUD groups = flag system, not ad-hoc Show()**: `IngameHudVisibility`
  (`gui/ingamehudvisibility.c`) maps an `EHudContextFlags` bitmask (HUD_DISABLE=1, HUD_HIDE=2,
  VEHICLE_DISABLE=4, DRIVER=8, VEHICLE=16, MENU_OPEN=32, NO_BADGE=64, QUICKBAR_DISABLE=128,
  QUICKBAR_HIDE=256, QUICKBAR_GLOBAL=512, INVENTORY_OPEN=1024, UNCONSCIOUS=2048; :15-29) to element
  lists (`LinkElementsToFlags` :69-87); `SetContextFlag(flag,state)` refreshes only affected elements
  (:90-102). Public API = thin wrappers: `ShowHudUI→MENU_OPEN` (`ingamehud.c:906-909`),
  `ShowQuickbarUI→QUICKBAR_DISABLE` (:888-891), `ShowHudPlayer→HUD_HIDE` (:900-903), etc.
  Menus hide the HUD via `mission.GetHud().ShowHudUI(false)+ShowQuickbarUI(false)`
  (`ingamemenu.c:135-147`). **For "hide my custom HUD when X", extend
  `modded IngameHudVisibility.LinkElementsToFlags`** — do not roll a parallel system.
- Vehicle HUD plug-in: `IngameHud.Init` builds `map<string, VehicleHudBase>`
  (`'VehicleTypeCar'→CarHud`) each loading its own layout into the widget named `VehicleHUDPanels`
  (`ingamehud.c:173-186`).
- Sibling overlays NOT inside IngameHud (map for extending them): watermark `gui/watermark.c:10`;
  debug monitor `gui/debugmonitor.c:25`; player tag `ingamehud.c:1102`
  (`new_ui/hud/hud_player_tag.layout`, lazy); chat lines `chat/chatline.c:25`.

## 6. Inventory architecture (the biggest vanilla UI — patterns to steal)

- `InventoryMenu` is a thin shell; composition lives in `Inventory : LayoutHolder`
  (`gui/inventorynew/inventory.c:26`, ctor :74-90 creates ItemManager/ColorManager singletons +
  LeftArea/RightArea/HandsArea/PlayerPreview + Quickbar).
- **`LayoutHolder extends ScriptedWidgetEventHandler`** (`layoutholder.c:1`) is the reusable building
  block: ctor takes parent holder → overridable `SetLayoutName()` → `CreateWidgets(m_LayoutName,
  null, false)` → `parent.GetMainWidget().AddChild(...)` (:89-121); dtor deletes root (:123-127).
  `Container extends LayoutHolder` adds `array<ref LayoutHolder> m_Body` + focused-container/column
  state for gamepad nav (`containers/container.c:1-80`) + `Insert(holder, pos)` (:1201).
- Width classes: `InventoryMenu` ctor computes static ScreenWidthType from aspect ratio (>1.75 WIDE,
  >1.5 MEDIUM, else NARROW; `inventorymenu.c:38-52`); layout paths centralized as consts in
  `class WidgetLayoutName` (`3_game/gui/widgetlayoutname.c:1-51`) with narrow/medium/wide/xbox
  variants for the components that need them — vanilla's own layout registry (same idea as the
  LBmaster LayoutManager pattern, const-based and width-class-aware). Not universal: a few paths are
  hardcoded inline (tooltips `itemmanager.c:54-58`, `ammo_icon` `icon.c:1522`).

## 7. Focus & gamepad (corrects earlier hint)

- The ONLY focus API vanilla calls is the global pair `SetFocus(Widget)/GetFocus()`
  (`enwidgets.c:698/702`; 87 call sites). **`SetActiveWindow` has ZERO vanilla call sites** (proto
  only, :695; `SetModal` :700 likewise unused) — do not design around it.
- Conventions: mouse-first menus clear or root the focus in Init (`mainmenu.c:109 SetFocus(null)`;
  optionsmenu sets `SetFocus(layoutRoot)` on PC, :98); console menus focus the default button
  (`respawndialogue.c:27`, `ingamemenuxbox.c:961-979 UpdateMenuFocus()`); EditBox menus focus the box
  on show (`chatinputmenu.c:58`).
- Hover and focus share ONE highlight path: OnMouseEnter/OnMouseLeave AND OnFocus/OnFocusLost all
  route to ColorHighlight/ColorNormal gated by an `IsFocusable(w)` whitelist (`mainmenu.c:275-350`).
- Device hot-swap: subscribe `g_Game.GetMission().GetOnInputDeviceChanged().Insert(fn)`
  (+ GetOnInputPresetChanged) — 23 vanilla files do this and **Remove in destructor**
  (`mapmenu.c:41-47,162-163`).

## 8. Facts that correct/extend the skill

- **Menu blur (CORRECTIVE)**: vanilla's current mechanism is the PPE requester system —
  `PPERequesterBank.GetRequester(PPERequesterBank.REQ_INVENTORYBLUR).Start()/.Stop()` in
  InventoryMenu.OnShow/OnHide (`gui/inventorymenu.c:109/146`). `PPEffects` (the skill's documented
  `SetBlurMenu` route) is initialized with an explicit DEPRECATED comment — it still works (Expansion
  uses it) but new code should prefer the requester.
- **UI sounds (verified negative)**: vanilla menus play NO per-click/hover sounds — no UI-sound API
  exists to copy; the only menu audio is main-menu music via `SoundParams` +
  `GetGame().GetSoundScene().Play2D`. Mod click sounds (SEffectManager pattern) are a mod convention,
  not vanilla parity.
- **Compound-button convention**: a vanilla button named `X` has children `X_panel` (bg) and
  `X_label` (text), accessed generically via `w.FindWidget(w.GetName() + "_label")` —
  ButtonSetText/ButtonSetColor helpers (`ingamemenu.c:392-415`). Follow it and generic helpers work
  on your buttons too.
- **Deferred transitions**: mission-continue/logout/respawn-dialogue transitions from a click are
  deferred via `g_Game.GetCallQueue(CALL_CATEGORY_GUI).Call(...)` (`ingamemenu.c:215/242/259`) —
  common for transitions that destroy the current menu; not an absolute rule (OnClick_Options enters
  the options menu synchronously, :253).
- **Widget-tree dumper for "half my UI is missing"**: `MissionBase.DumpCurrentUILayout()`
  (`missionbase.c:357-377`) recursively Prints every widget of the current menu as
  `name (TypeName) [invisible]` with TOTAL/INVISIBLE/VISIBLE counts — call it from any diag hook
  instead of writing your own walker.
- **WidgetEventHandler singleton** (`gui/widgeteventhandler.c`): lets ANY class receive widget events
  without subclassing ScriptedWidgetEventHandler — `RegisterOnClick(w, handler, "FnName")` keeps
  per-event `map<Widget, Param2<Managed,string>>` registries and dispatches by function-name string.
  Drag&drop keying (verified): OnDrag/OnDrop dispatch keyed to the SOURCE widget; OnDraggingOver/
  OnDropReceived keyed to the RECEIVER under the cursor (`widgeteventhandler.c:288-367`); enable
  dragging via `SetFlags(WidgetFlags.DRAGGABLE)` (vanilla wrapper `ItemManager.SetWidgetDraggable`,
  `itemmanager.c:693-702`); mid-drag globals `GetDragWidget()/GetWidgetUnderCursor()/
  CancelWidgetDragging()` (`enwidgets.c:184-186`).
