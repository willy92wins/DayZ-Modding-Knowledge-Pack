---
name: dayz-ui-development
description: "DayZ mod UI development in Enforce Script — planning, authoring, styling, debugging and verifying. Covers vanilla engine widgets (enwidgets.c protos), the .layout Enfusion brace format (units, exact flags, anchors, resolution independence), the .styles 9-slice system, vanilla menu/HUD architecture (UIScriptedMenu contract, menu-ID registration), ScriptedWidgetEventHandler, Dabs Framework MVC, Expansion MVC and the Market menu case, plus the plan→implementation fidelity playbook (offline lint/reconcile/preview toolchain, Workbench dual registration, parity gate). Use for DayZ UI, menu, layout, widget, HUD, panel, dialog, popup, overlay, CreateWidgets, FindAnyWidget, GetUIManager, ShowScriptedMenu, EnterScriptedMenu, floating window, animation, color theme, styles, imageset, font, scroll, drag, EditBox, RichText, gamepad focus — and ESPECIALLY when planning a new UI or when 'the UI doesn't look like the design / breaks at other resolutions'. Always consult this skill before writing ANY DayZ UI code."
---

# DayZ UI Development — Verified Reference (v3)

Built from: enwidgets.c engine protos, vanilla 5_mission source + unpacked gui/ PBO (layouts,
dayzwidgets.styles), Dabs Framework at production HEAD, LFPG/LBmaster production code, Discord
archives — every load-bearing claim carries a path:line or URL. Local ground truth on this machine:
vanilla scripts at `<dayz-projects>\scripts\`, vanilla GUI data at
`...\DayZ Projects\gui\` (verify any cite by opening the file).

## TASK ROUTER — open the right reference for the task, then come back here

| Your task | Read FIRST | Then |
|---|---|---|
| Any new UI (menu/HUD/panel) — planning it | `references/plan-to-implementation.md` (§5 spec table, §1 why UI diverges) | §2 units, WORKFLOW below |
| "It looks different in-game than designed / at other resolutions" | `plan-to-implementation.md §1` (root causes) | Rule 3 below |
| New menu opened by key / menu IDs / pause-style menu | `references/vanilla-menus-map.md` (§2 registration recipe, §4 strategies) | §3 contract |
| Extending the HUD / hide-show HUD groups | `vanilla-menus-map.md §5` (HUD chain + IngameHudVisibility) | — |
| Writing/debugging a `.layout` file | `references/layout-format.md` | Rules 1-4 below |
| Styled chrome (borders, buttons w/ press feedback, 9-slice, theming a panel) | `references/styles-format.md` | — |
| Dabs MVC (ScriptView, bindings, animations) | `references/dabs-framework.md` — **its §HEAD DEEP-DIVE supersedes older sections on conflicts** | Rules 15-18 below |
| Expansion menus/HUD | `references/expansion-mvc-patterns.md` + `expansion-market-menu-pattern.md` | — |
| Widget method signatures | `references/widget-api.md` ⚠️ see its correction note in the index below | or grep `scripts/1_core/proto/enwidgets.c` directly |
| Map/canvas/3D-markers/admin windows | `references/lbgroups-patterns.md`, `references/admin-ui-patterns.md` ⚠️ | — |
| Recolor/retheme requests | THEME REALITY section below (scope it before estimating) | — |
| Keybind to open the UI (`inputs.xml` schema, config.cpp `inputs=`) | **`enforce-script-reference` skill** (outside this skill's verified corpus) | vanilla-menus-map.md §4 for the OnUpdate polling pattern |

⚠️ = files with confabulated/unverified code: `advanced-patterns.md` (3 broken APIs — read its
CORRECTIONS banner first), `admin-ui-patterns.md` + `lbgroups-patterns.md` (zero path:line cites —
treat code as pseudocode until re-verified). Anything marked "corrected 2026-XX-XX" states current
truth; the date is provenance, not history you need.

## STANDARD WORKFLOW — follow this for ANY UI implementation on this machine

1. **Spec before layout**: fill the widget-tree spec table (`plan-to-implementation.md §5`) — every
   visual element gets a widget class, a name (the FindAnyWidget/binding contract), a unit mode, and
   a color source (layout attr vs script SetColor). Mockups must stay inside the widget model (no
   gradients/web fonts/border-radius — no `.layout` equivalent exists).
2. **Author** the `.layout` in brace format (NEVER XML — native CTD), proportional units by default
   (Rule 3), anchors + `position 0 0` idiom, `#STR_` keys for all text.
3. **Lint**: `python tools/dayz-script-validator/scripts/script_validator.py <addon_root>`
   (braces, XML-format, layout-file-exists, $PBOPREFIX$ path, OnMouseLeave arity; exit 0/1/2).
4. **Reconcile**: `python tools/dayz-script-validator/scripts/ui_reconcile.py <addon_root>`
   (every FindAnyWidget name ↔ layouts, every #STR ↔ stringtable.xml/csv; "did-you-mean" on typos).
5. **Preview offline**: `python "<notes>\DayZ_UI_Research\renderer\build_viewer.py" <layout>`
   → self-contained `.preview.html`, switch resolutions 1080p/1440p/ultrawide/720p to SEE exact-flag
   breakage. Approximation: trust it for structure/positioning/text, NEVER for pixels/colors/fonts/styles.
6. **Deploy + verify in-game** via the `dayz-test-ingame` skill (DayZDiag + filePatching, no signing).
   Post-session gates: grep RPT for `Cannot open layout`; screenshot at 1080p AND one other
   resolution; diff against the calibrated mockup. Group ALL pending UI checks into one session (R5).
7. **Parity gate** before calling it done: `plan-to-implementation.md §6` (spec table ↔ built layout
   ↔ bindings ↔ in-game screenshot).

Debug helpers when something is wrong in-game: `MissionBase.DumpCurrentUILayout()` (prints the
current menu's whole widget tree with visibility), DbgUI immediate-mode panel for live tuning
(`scripts/1_core/proto/dbgui.c`), Dabs `ScriptView.ReloadAll()` = layout hot-reload under DIAG.

## Reference Files

Read the relevant file BEFORE writing code:

- **★ Plan → implementation fidelity playbook (WHY UI diverges from the plan + the iteration loop + parity gate)** → `references/plan-to-implementation.md` — **READ THIS FIRST when the recurring pain is "the UI never comes out like I planned".** Covers resolution-independent units, the Workbench Layout Editor + dual asset registration, the offline→in-game iteration loop, the plan/spec artifact and the reconciliation gate.
- **Widget API (verified from engine protos + Dabs source)** → `references/widget-api.md` — ⚠️ its
  "TextWidget Extended" GETTER block (GetTextOutlineSize etc.) is mis-attributed: those getters live
  on **UIWidget** (base of Button/EditBox/CheckBox/Slider/listboxes/spacers, `enwidgets.c:323-339`),
  a SIBLING branch of TextWidget (whose getters are GetOutlineSize/GetShadowSize, no "Text" prefix).
  Also missing there: the UIWidget SETTERS — `SetTextColor(int)` (THE way to color a button/editbox
  LABEL; `Widget.SetColor` colors the body), `SetTextOutline`, `SetTextShadow`, `SetTextItalic/Bold`.
- **Dabs Framework deep dive (MVC + Animator + Color + Menu)** → `references/dabs-framework.md` —
  now includes a HEAD DEEP-DIVE (2026-07-05, production=Workshop-identical MVC): ScriptViewMenu real
  contract (no OnShow/OnHide; ESC NOT handled), LoadWidgetsAsVariables mechanism + dot-naming,
  WidgetAnimator's 5 verified traps (ms-vs-TimeSpan 1000× trap, swapped bounce easings...),
  Relay_Command dispatch reality, Observables full contract, DIAG `ScriptView.ReloadAll()` hot-reload.
- **Vanilla menus & HUD source map (menu→file→layout table, menu-ID registration, UIScriptedMenu
  contract, HUD chain + IngameHudVisibility flags, inventory architecture, focus model)** →
  `references/vanilla-menus-map.md`
- **.styles system — complete dissection (states, 9-slice item contracts, Colorable mechanism,
  custom-style recipe)** → `references/styles-format.md`
- **Layout file format (.layout Enfusion)** → `references/layout-format.md`
- **Advanced UI patterns (toggles, anti-overlap, tabs, hover, drag)** → `references/advanced-patterns.md` — ⚠️ contains 3 confabulated APIs (see the CORRECTIONS banner at the top of that file before copying any code).
- **Empirical layout corpus (widget/attribute frequency, HTML renderer, Dabs path fix)** → `references/layout-empirical-corpus.md`
- **LFPG production knowledge base (80+ verified facts)** → `references/LFPG_UI_KnowledgeBase_v3.md`
- **LBGroups production patterns (30 patterns from DayZ's top group mod)** → `references/lbgroups-patterns.md`
- **Admin UI patterns (floating windows, ESP, widgets, camera)** → `references/admin-ui-patterns.md`
- **In-game color/debug harness scaffold (F7 panel, SetLV A/B protocol)** → `references/LF_ColorTest_README.md`
- **AnswerOverflow community findings (mined 2026-05-17)** → `references/answeroverflow-2026-05-17.md`
- **Expansion MVC patterns (ExpansionScriptView/ViewController/ObservableCollection/UIManager/HUD)** → `references/expansion-mvc-patterns.md`
- **Expansion Market menu — canonical end-to-end pattern (MVC + RPC + state machine + stock)** → `references/expansion-market-menu-pattern.md`

### Expansion MVC — Key Topics (read `expansion-mvc-patterns.md` and `expansion-market-menu-pattern.md`)
Use when working with any DayZ Expansion menu or HUD: ExpansionScriptView lifecycle,
ExpansionScriptViewMenu OnShow/OnHide (blur + LockControls ForceDisable loop),
opt-in tick timer (CALL_CATEGORY_GUI), ExpansionUIManager CreateSVMenu singleton,
ObservableCollection + ViewBinding declarative two-way binding, subview composition
(each row/element is its own ScriptView), intermediate model filter before ObservableCollection
mutation, ExpansionDialogBase composable dialogs, client settings dot-path reflection
(EnScript.GetClassVar), HUD multi-pointer registration pattern (modded IngameHud + vehicle HUD).
For the full server-authoritative trader flow: state machine (7-state enum), buy confirmation
with blocking state before RPC, server price recheck ±1 tolerance, reserve/stock/money/spawn/Save
sequence, trader permissions entity, 4-step RPC handshake (StartTrading → batch load →
SI_SetTraderInvoker), Expansion_Register*RPC helpers, client-side attachment preset persistence.

### LBGroups Patterns — Key Topics (read `lbgroups-patterns.md`)
Layout Manager registry, ConnectClassWidgetVariables auto-binding,
MapWidget full API (ScreenToMap/MapToScreen/SetMapPos/SetScale/AddUserMark),
CanvasWidget drawing (DrawLine/Clear), 3D marker projection (GetScreenPos),
compass strip positioning, text width measurement (hidden widget trick),
chat ring buffer, dirty-check hash pattern, page/tab system, color picker
slider+editbox, ScriptInvoker global events, HUD overlay conditionals,
modded class widget hijack, drag-and-drop on map, client-side JSON
persistence, widget position manager, player list with health bars,
tactical ping raycast, EditBox event handler, float formatting, feature
flags, TextWidget advanced formatting (SetTextExactSize/SetShadow/SetOutline),
Widget.AddChild reparenting, ScrollWidget programmatic control.

---

## CRASH PREVENTION RULES — READ FIRST

Every rule below caused a real crash or visual failure in production.

### Layout Rules (every .layout file)

1. **Empty `{ }` child block on leaves is a SAFE CONVENTION, not a hard requirement.**
   *(Corrected 2026-07-03 against vanilla ground truth.)* Vanilla layouts routinely
   OMIT the child block on leaf widgets — e.g. `RichTextWidgetClass DefaultActionWidget`
   and every `ActionListItem0..N` in `gui/layouts/day_z_hud.layout` have no `{ }` and
   ship in the production HUD. So a missing leaf block does NOT reliably crash. What DOES
   break loading: **unbalanced braces** and **XML-format layouts** (`<?xml?>` / `<GUI><class type=...>`,
   which some design-kit tools emit) — those crash inside native `CreateWidgets` even when
   widget names and `#STR` keys reconcile GREEN (verified: LFGungame BUG, 4 layouts fixed by
   converting XML→brace format). The parser is otherwise fail-loud-but-partial: it loads
   widgets top-to-bottom until the first syntax error, then stops (widgets after the error
   silently never appear → the classic "half my UI is missing" symptom). Quantified 2026-07-04:
   vanilla omits the leaf block 99.6% of the time (5,315/5,337 leaves) and uses an empty `{ }`
   literally ZERO times — the empty-block convention has no vanilla precedent (mods use it 22.6%).
   Either form loads; when debugging a missing widget check brace balance and file format
   (brace vs XML), not leaf blocks. The ONE real use of an anonymous block on a leaf is holding
   `ScriptParamsClass` (see layout-format.md — dedicated block, 157/157 corpus instances).
   Vanilla's own tree dumper `MissionBase.DumpCurrentUILayout()` (missionbase.c:357-377) prints
   every widget of the current menu with visibility totals — use it for "half my UI is missing".

2. **`FrameWidgetClass`/`PanelWidgetClass` are INVISIBLE** (unless a `style` gives Panel a 9-slice
   — see styles-format.md). For visible backgrounds use `ImageWidgetClass` with `ignorepointer 1`
   and `stretch 1`. In script: `LoadImageFile(0, "#(argb,8,8,3)color(1,1,1,1,CO)")` then
   `SetColor(ARGB(...))`. ⚠️ The procedural texture FAILED on DayZ 1.29 ("Bad texture name" /
   "LoadImageFile can't load", observed on LFPowerGrid) — fallbacks: ship a 1×1 white `.edds` and
   LoadImageFile that, or use a `Colorable` style (WhitePixel Center, styles-format.md §5).

3. **Declare all 4 pos/size-mode flags EXPLICITLY (0 or 1) — do NOT default them to 1.**
   *(Corrected 2026-07-03; the old "always set all 4 to `1`" advice was a top cause of
   resolution-dependent divergence.)* The exact flags choose UNITS, not "definedness":
   `hexactpos/vexactpos/hexactsize/vexactsize 1` = **physical screen pixels**
   (`enwidgets.c:68-71`: `EXACTPOS //< Uses physical resolution (g_iWidth, h_iHeight)`), so an
   all-`1` layout authored at 1080p occupies different RELATIVE space at 1440p/ultrawide/console —
   this is exactly the "looked right in my mockup, lands wrong in-game" failure. `0` = **fraction of
   parent (0.0–1.0)**, which is what vanilla predominantly uses (`gui/layouts` stat: `hexactsize 0`
   5851× vs `hexactsize 1` 2727×; `loading.layout` uses all four = 0). RULE: default to
   **proportional (0)** for anything that must scale; use **exact (1)** only for elements that must be
   pixel-true (fixed icon/border sizes). For a resolution-independent full-screen background use the
   canonical `size 0.16 0.09` + `halign/valign center_ref` + `fixaspect outside` pattern
   (`gui/layouts/loading.layout:36-55`).
   Corpus refinements (2026-07-04, 8,671 vanilla widgets): **mixing exact and proportional axes on
   one widget is the vanilla NORM** (50.8%; top profiles: exact pos + proportional size 1,892×, and
   exact pos + prop width + pixel height 1,182×) — the old "mixing is fragile" warning is refuted.
   The dominant idiom is **anchor + zero offset**: `halign/valign *_ref` + `position 0 0` (70% of
   exact-pos widgets have position 0 0, where the unit distinction is moot) + proportional or
   height-pixel size. Per-class defaults for the spec table: MultilineText 93% all-proportional;
   Text/Frame/Panel favor exact-pos-anchor + proportional size. Omitting all 4 flags defaults to
   PROPORTIONAL in practice (42 vanilla widgets omit all four — incl. production menu ROOTS like
   `day_z_ingamemenu.layout:1` — and render correctly with fractional values); still declare them
   explicitly for readability.

4. **Brace count MUST match** — verify opens == closes.

### Script Rules (every .c file)

5. **Null-check `GetGame()` in ALL destructors** — returns null during shutdown.

6. **Null-check `GetWorkspace()` before `CreateWidgets()`** — null during early init.

7. **Null-check EVERY `FindAnyWidget()` and `Cast()` result.**

8. **`FindAnyWidget()` returns WRONG refs for widgets inside `ButtonWidget`.**
   Child-walk manually or use helper functions. Dabs `LoadWidgetsAsVariables`
   has this bug internally — store button child refs in arrays, not named fields.

9. **`new ScriptView()` calls `CreateWidgets()` internally.** NEVER instantiate
   from RPC context (workspace null). Pre-create in MissionInit, show/hide later.

10. **`SetHandler(this)` is MANDATORY for vanilla `ScriptedWidgetEventHandler`.**
    Dabs `ViewController` does this automatically — not needed in Dabs MVC.

### Enforce Script Restrictions (ALL code)

11. NO ternary operators — does not compile
12. `++/--`, `foreach`, `+=/-=`, string literals as params, multiline ALL WORK (verified LBmaster production)
13. Hoist variables before conditionals if reused across branches
14. Explicit typing always; `m_` prefix on all member fields

### Dabs MVC Rules

15. **`NotifyPropertyChanged("X")` is SAFE** — only updates ViewBindings with
    `Binding_Name == "X"`. Does NOT scan or overwrite other controller fields.
    Calling with empty string updates ALL bindings (expensive, avoid).
    Source: ViewController.c:84-117.

16. **Relay_Command double-execution — corrected mechanism (2026-07-05, production HEAD):**
    ViewController.OnClick returns true immediately when InvokeCommand reports handled
    (super.OnClick is NOT then called), so the old "Relay_Command + manual OnClick = double
    fire" wording was imprecise. The REAL risk: **a command handler that returns false/void**
    — ViewBinding.InvokeCommand then walks UP the parent chain re-invoking the SAME function
    name on each ancestor controller. Rule: **command handlers must `return true` when
    handled.** Also: Relay_Command only fires from ButtonWidget (OnClick) and CheckBoxWidget
    (OnChange) — no other widget type dispatches commands.

17. **ObservableCollection items with back-ref to controller = circular ref leak.**
    Null the back-ref in item destructor. Source: ObservableCollection uses
    `ref array<ref T>` — GC cannot break cycles.

18. **`map<Widget, T>` WORKS in Dabs production.** `ViewBindingHashMap` is
    `typedef map<Widget, ViewBinding>` used throughout ViewController.c.
    Previous claim it crashes was likely caused by something else.

---

## AUTO WIDGET BINDING — ConnectClassWidgetVariables (LBmaster pattern)

Automatically binds class Widget member variables to layout widgets by name match.
Eliminates dozens of FindAnyWidget calls.

```
// Global function (define yourself or use from framework):
bool ConnectClassWidgetVariables(Class instance, Widget layoutRoot,
    TStringArray ignored = null, TStringArray renames = null) {
    typename me = instance.Type();
    for (int i = 0; i < me.GetVariableCount(); i++) {
        string varName = me.GetVariableName(i);
        typename type = me.GetVariableType(i);
        if (type.IsInherited(Widget)) {
            string widgetName = varName;
            if (renames) {
                int idx = renames.Find(varName);
                if (idx != -1) widgetName = renames.Get(idx + 1);
            }
            if (ignored && ignored.Find(varName) != -1) continue;
            Widget w = layoutRoot.FindAnyWidget(widgetName);
            if (w) EnScript.SetClassVar(instance, varName, 0, w);
        }
    }
    return true;
}

// Usage:
class MyMenu : UIScriptedMenu {
    TextWidget titleText;      // auto-bound to widget named "titleText"
    ButtonWidget btnClose;     // auto-bound to "btnClose"
    EditBoxWidget searchInput; // auto-bound to "searchInput"
    
    override Widget Init() {
        layoutRoot = GetGame().GetWorkspace().CreateWidgets(LAYOUT_PATH);
        ConnectClassWidgetVariables(this, layoutRoot);
        return layoutRoot;
    }
}
```
Uses `typename.GetVariableCount/Name/Type` + `EnScript.SetClassVar` reflection.
Supports ignore lists and variable→widget rename mappings.

## DELIVERY CHECKLIST (updated 2026-07-05 — aligned with corrected rules + tooling)

### Automated first (run both, fix all findings)
- [ ] `python tools/dayz-script-validator/scripts/script_validator.py <addon_root>` → exit 0
- [ ] `python tools/dayz-script-validator/scripts/ui_reconcile.py <addon_root>` → exit 0 (FAIL = typo)

### Layout (.layout)
- [ ] Brace format, NOT XML (`<?xml` / `<GUI>` = native CTD); braces balanced
- [ ] All 4 unit flags DECLARED per widget (0=proportional default, 1=pixel only when pixel-true)
- [ ] Anchors (`halign/valign *_ref` + `position 0 0`) for placement that must survive resolutions
- [ ] Backgrounds: ImageWidgetClass `ignorepointer 1` + `stretch 1`, or a 9-slice style (styles-format.md)
- [ ] Widget names unique AND matching the spec table (they are the FindAnyWidget/binding contract)
- [ ] All user-visible text via `#STR_` keys in stringtable
- [ ] `ScriptParamsClass` in its own dedicated block (never mixed with child widgets)

### Script (.c)
- [ ] GetGame() null-checked in destructors; GetWorkspace() null-checked before CreateWidgets
- [ ] All FindAnyWidget/Cast results null-checked (a missing LAYOUT FILE still CTDs inside
      CreateWidgets — the null-check can't save you; that's what the linter gate is for)
- [ ] Input locked on open, unlocked on close AND destructor (per-device focus counts balance)
- [ ] HUD overlays: root `Unlink()`ed in OnMissionFinish (else ghost widgets stack across sessions)
- [ ] Dabs: command handlers `return true`; no OnShow/OnHide overrides on ScriptView; ESC wired manually
- [ ] No ternary operators; m_ prefix on members; variables hoisted

### Fidelity (the gate that was always missing)
- [ ] Offline preview eyeballed vs mockup (`build_viewer.py`, labelled approximation)
- [ ] In-game screenshot at 1080p AND one non-1080p resolution vs calibrated mockup
- [ ] Every spec-table row exists in the built layout with planned name/class/mode (parity gate §6)

---

## EVENT SIGNATURES (verified from enwidgets.c)

```
OnClick(Widget w, int x, int y, int button) → bool
OnDoubleClick(Widget w, int x, int y, int button) → bool
OnMouseEnter(Widget w, int x, int y) → bool               // 3 params
OnMouseLeave(Widget w, Widget enterW, int x, int y) → bool // 4 params ASYMMETRIC
OnMouseWheel(Widget w, int x, int y, int wheel) → bool
OnMouseButtonDown(Widget w, int x, int y, int button) → bool
OnMouseButtonUp(Widget w, int x, int y, int button) → bool
OnFocus(Widget w, int x, int y) → bool
OnFocusLost(Widget w, int x, int y) → bool
OnChange(Widget w, int x, int y, bool finished) → bool
OnKeyDown(Widget w, int x, int y, int key) → bool
OnKeyUp(Widget w, int x, int y, int key) → bool
OnKeyPress(Widget w, int x, int y, int key) → bool
OnDrag(Widget w, int x, int y) → bool
OnDragging(Widget w, int x, int y, Widget reciever) → bool
OnDraggingOver(Widget w, int x, int y, Widget reciever) → bool   // added 2026-07-04, enwidgets.c:678 — was omitted
OnDrop(Widget w, int x, int y, Widget reciever) → bool
OnDropReceived(Widget w, int x, int y, Widget reciever) → bool
OnResize(Widget w, int x, int y) → bool
OnChildAdd(Widget w, Widget child) → bool
OnChildRemove(Widget w, Widget child) → bool
OnUpdate(Widget w) → bool
OnSelect(Widget w, int x, int y) → bool
OnItemSelected(Widget w, int x, int y, int row, int col, int oldRow, int oldCol) → bool
OnModalResult(Widget w, int x, int y, int code, int result) → bool
OnController(Widget w, int control, int value) → bool
OnEvent(EventType eventType, Widget target, int param0, int param1) → bool
```

Return true to consume event (stops propagation).
OnMouseLeave has 4 params — asymmetric with OnMouseEnter (3 params).

---

## INPUT & CURSOR MANAGEMENT

```
// Lock input (stackable: each +1 needs exactly -1)
GetGame().GetInput().ChangeGameFocus(1);

// Show cursor
GetGame().GetUIManager().ShowUICursor(true);

// Block player actions but keep UI working
HumanInputController hic = man.GetInputController();
hic.SetDisabled(true);

// ESC: does NOT work via LocalPress("UAUIBack") when ChangeGameFocus active.
// Intercept in MissionGameplay.OnKeyPress with key == 1 (KC_ESCAPE).
```


### Mission-Level Input Blocking (LBmaster pattern)
```
Mission mission = g_Game.GetMission();
mission.AddActiveInputExcludes({"movement", "aiming", "menu"});
// Restore:
mission.RemoveActiveInputExcludes({"menu", "movement", "aiming"}, true);
mission.RemoveActiveInputRestriction(EInputRestrictors.INVENTORY);
mission.RefreshExcludes();
mission.PlayerControlEnable(true);
```

### Background Blur
```
// Vanilla-current mechanism (preferred, 2026-07-04): the PPE requester system —
// this is what vanilla InventoryMenu does (gui/inventorymenu.c:109/146):
PPERequesterBank.GetRequester(PPERequesterBank.REQ_INVENTORYBLUR).Start();  // OnShow
PPERequesterBank.GetRequester(PPERequesterBank.REQ_INVENTORYBLUR).Stop();   // OnHide

// Legacy route (works — Expansion still uses it — but PPEffects is initialized
// with an explicit DEPRECATED comment in vanilla; prefer the requester in new code):
PPEffects.SetBlurMenu(0.5);   // blur behind menu
PPEffects.SetBlurMenu(0);     // remove on close
```

### UIManager Operations
```
g_Game.GetUIManager().CloseAll();
g_Game.GetUIManager().ShowUICursor(true);
g_Game.GetUIManager().IsCursorVisible();
UIScriptedMenu current = g_Game.GetUIManager().GetMenu();
```

**Dabs alternative: `ScriptViewMenu`** handles game focus, cursor and menu hierarchy —
but **NOT ESC** (corrected 2026-07-05 at production HEAD: `CanCloseWithEscape()` has ZERO
callers; wire ESC yourself) and note it releases focus incompletely on close (the
`ChangeGameFocus(-1,...)` in its destructor is commented out — verify input state after
closing). Full verified contract: `references/dabs-framework.md` §HEAD DEEP-DIVE.

---

## DAYZ UI THEME REALITY — Why "change all the red" is hours, not minutes

DayZ does NOT have a centralized theme system. There is no `PrimaryAccentColor`
constant that flows through every widget. Color values come from THREE independent
places, each requiring a different override approach. This is a documented engine
limitation — and no framework plugs it (see the CUI correction below).

### The three sources of UI color

1. **`.layout` files in `P:\gui\layouts\` (~100+ files)**

   Color attributes are baked **per-widget** as RGBA tuples directly in the XML.
   `modded class` does NOT apply to `.layout` files. The only override path is to
   ship a same-named layout in your mod's `gui/layouts/` — which clobbers the
   ENTIRE layout (heavyweight, brittle across DayZ updates). One vanilla layout
   touched, the whole layout reshipped.

2. **Inline ARGB literals in `P:\scripts\5_mission\gui\` (10+ files)**

   Code calls `widget.SetColor(0xFFD70D11)` directly with a hex literal. To change
   that color, override the **containing class's method** (the function that calls
   `SetColor`) via `modded class`, NOT the constant itself.

   ```c
   // Vanilla:
   class IngameHud
   {
       void UpdateBleedIcon()
       {
           m_BleedIcon.SetColor(0xFFD70D11);  // baked at compile time
       }
   }

   // Override the METHOD, not the literal:
   modded class IngameHud
   {
       override void UpdateBleedIcon()
       {
           m_BleedIcon.SetColor(0xFF0D11D7);
       }
   }
   ```

3. **`Colors` / `FadeColors` constants in `P:\scripts\3_game\colors.c`** *(verified)*

   These look like the obvious target for a theme override. **They are not.**
   `modded class Colors { const int X = ...; }` is a **no-op for compile-time
   constants**: callers already baked the original integer value at compile time,
   re-declaring in a subclass changes nothing.

   Worse: `COLOR_DAYZ_RED` (the most-named "DayZ red") is referenced in **exactly
   one** call site across vanilla scripts — `mainmenupromo.c:158`, the main-menu
   promo banner. Verified 2026-05-04 against `P:\scripts\`. So even a working
   override of `COLOR_DAYZ_RED` would only recolor that one element.

### Implication

A request like *"change all the red UI to blue"* is **hours of work, not minutes**.
It requires:

- Sweeping `.layout` files for per-widget RGBA values and replacing each
- Finding every `SetColor(<red ARGB>)` call in `5_mission/gui/` and overriding
  the containing class's method via `modded class`
- The `Colors` constants are a red herring — don't waste time there

### How to scope a theme request

When the user asks for a UI color change, ask FIRST:

- **Single element** ("the bleeding icon", "the menu hover state") — feasible,
  scoped to one method override or one layout swap.
- **All red → all blue** ("retheme the whole UI") — push back. Define scope-by-scope
  and treat as a batch; no framework makes this a one-property edit (see below).

Never accept "change all the red" as a one-file task. Quote this section back to
the user before estimating effort.

### CUI reality check (corrected 2026-07-05 — the old recommendation was mis-sourced)

There is **no DayZ project named "Community UI Framework"**. In the DayZ community, **CUI =
"Colorful UI"** by DayZ-n-Chill (github.com/DayZ-n-Chill/DayZ-Colorful-UI, MIT, "Colorful UI 2.5 —
Community Edition Template", latest release v2.5.1 dated 2024-06 — usable but slow-moving). Its
mechanism is **reshipping ALL default layouts as individually editable files** ("Customize EVERY
ELEMENT INDIVIDUALLY!") — i.e. exactly the per-layout heavyweight mechanism this section already
calls brittle, NOT a centralized propagating theme layer. A "Pro" variant exists under CC BY-NC 4.0
(NonCommercial clause matters for monetized servers).

Implications: (a) do NOT promise that adopting CUI turns retheming into one-property edits — that
capability does not exist in the ecosystem; (b) CUI IS useful as a starting TEMPLATE when the goal
is "reskin the whole vanilla UI" (it has already done the reshipping work); (c) for one-off recolors
of an existing mod, stay scoped to the specific element. Also verified: Community Framework (CF)
ships NO MVC/UI layer (its changelog: MVC added deprecated in 1.1, removed in 1.3.1) — its only UI
surface worth knowing is the server-aware NotificationSystem.


---

## COLOR SYSTEM

- **DayZ renders UI colors darker by default** — engine applies negative LV to widgets.
- **FIX: call `Widget.SetLV(0)` and `Widget.SetTextLV(0)` once at mod init.**
  This normalizes all widget colors to match expected ARGB values exactly.
  Verified in-engine 2026-03-24: saturated colors barely affected, grays and
  pastels significantly darker without SetLV(0). One line fixes everything.
- Low alpha is clamped invisible by the engine. Honest bracket from the only real data points
  (corrected 2026-07-04 — the old "below 0x30 invisible" contradicted its own "0x26 works" example):
  0x12 (18) rendered invisible, 0x26 (38) rendered visible → threshold lies in (0x12, 0x26].
  Practical rule: stay ≥ 0x30 (48) for anything that must be seen; treat 0x13–0x2F as untested territory.
- Layout uses 0.0-1.0 floats. Script ARGB() uses 0-255 integers.
- Dabs `LinearColor` class has 140+ named colors, HSV, Lerp, BlendModes.
- `ButtonWidget.SetColor()` works directly (no LoadImageFile needed).

---

## WIDGET ALIGNMENT FLAGS (empirical hex values from LBmaster — NOT verifiable against protos)

**Status (resolved 2026-07-05):** the odd V_/H_ prefixes are LBmaster's OWN naming (V_* = horizontal
values, H_* = vertical; from their LBWidgetUtils.c) — the Horizontal/Vertical labels below are
semantically correct. The hex VALUES cannot be verified against the engine: the WidgetFlags enum
(`enwidgets.c:57-85`) declares 26 entries with NO explicit values and NO positional-alignment flags
at all. **Never hand-compute WidgetFlags hex or mix these alignment hexes with `WidgetFlags.*`
symbolic math** — under a naive 1<<index reading, 0x100000 would collide with DISABLED and 0x400000
with CLIPCHILDREN; vanilla only ever uses symbolic names. These hexes are LBmaster-production-proven
as-is; treat them as an opaque, working recipe.

```
// Horizontal: V_LEFT=0x00, V_CENTER=0x140, V_RIGHT=0x100 (mask: 0x1C0)
// Vertical:   H_TOP=0x00,  H_CENTER=0xA00, H_BOTTOM=0x800 (mask: 0xE00)
// Clear mask for position: 0xFC0
// Text: TEXT_LEFT=0x0, TEXT_CENTER=0x100000, TEXT_RIGHT=0x400000 (mask: 0x500000)

// Runtime alignment change:
widget.ClearFlags(0xFC0);
widget.SetFlags(0x140);  // V_CENTER
widget.Update();         // MUST call Update() after flag changes

// Runtime text alignment:
widget.ClearFlags(0x500000);
widget.SetFlags(0x100000);  // TEXT_CENTER
widget.Update();
```

## WIDGET TYPES QUICK REFERENCE

| Layout Class | Script Class | Visible? | Two_Way? | Notes |
|---|---|---|---|---|
| FrameWidgetClass | Widget | NO | — | Hierarchy node only |
| ImageWidgetClass | ImageWidget | YES | NO | Needs LoadImageFile for script color |
| TextWidgetClass | TextWidget | text | NO | SetText, SetBold, SetItalic, SetShadow |
| ButtonWidgetClass | ButtonWidget | style | YES | SetState(bool), SetColor works |
| EditBoxWidgetClass | EditBoxWidget | YES | YES | GetText, OnChange per keystroke |
| MultilineEditBoxWidgetClass | MultilineEditBoxWidget | YES | YES | GetLinesCount, GetCarriageLine/Pos |
| RichTextWidgetClass | RichTextWidget | text | NO | Markup: b, i, color, image, outline, shadow |
| CheckBoxWidgetClass | CheckBoxWidget | YES | YES | IsChecked, SetChecked |
| SliderWidgetClass | SliderWidget | YES | YES | SetMinMax, GetCurrent, SetStep |
| ScrollWidgetClass | ScrollWidget | NO | — | Full scroll API, VScrollToWidget(child) |
| GridSpacerWidgetClass | GridSpacerWidget | NO | — | Auto-layout grid |
| WrapSpacerWidgetClass | WrapSpacerWidget | NO | — | Wrapping flow layout |
| CanvasWidgetClass | CanvasWidget | draw | — | DrawLine, Clear |
| VideoWidgetClass | VideoWidget | YES | — | Load, Play, Pause, GetTime |
| MapWidgetClass | MapWidget | YES | — | ScreenToMap, SetMapPos, SetScale, GetScale, GetMapPos, ClearUserMarks |
| XComboBoxWidgetClass | XComboBoxWidget | YES | YES | AddItem, ClearAll, GetCurrentItem, SetCurrentItem, GetNumItems |
| TextListboxWidgetClass | TextListboxWidget | YES | YES | AddItem(text, userData, column, row=-1)→int, SetItem, GetItemText(row,col,out), SetItemColor(row,col,color), RemoveRow, GetSelectedRow, SelectRow, GetNumItems, GetItemData, EnsureVisible, ClearItems |
| ProgressBarWidgetClass | ProgressBarWidget | YES | — | SetCurrent(float 0-100, vanilla-confirmed); extends SimpleProgressBarWidget; NO SetMinMax (range = layout/style) |
| MultilineTextWidgetClass | MultilineTextWidget | text | NO | Plain multi-line text (extends TextWidget + SetLineBreakingOverride); 100+ vanilla uses — use for wrapping labels |
| PasswordEditBoxWidgetClass | PasswordEditBoxWidget | YES | — | extends EditBoxWidget + SetHideText(bool) |
| HtmlWidgetClass | HtmlWidget | YES | — | extends RichTextWidget + LoadFile(path); vanilla note/book UIs — long scrollable documents |
| WindowWidgetClass | WindowWidget | style | — | Titled window chrome (Title* 9-slice via style) |
| SimpleProgressBarWidgetClass | SimpleProgressBarWidget | YES | — | Bar*-only style set; base of ProgressBarWidget |

---

## SCRIPTCLASS & REFERENCE KEYWORD — Layout↔Script Parameters

When layout has `scriptclass "MyHandler"`, engine creates MyHandler and calls OnWidgetScriptInit:

```
class MyValidator : ScriptedWidgetEventHandler {
    reference int maxLength;     // 'reference' = populated from layout ScriptParams
    reference string pattern;
    
    void OnWidgetScriptInit(Widget w) {
        // w = widget this is attached to, maxLength/pattern already set
        w.SetHandler(this);
    }
}
```

Layout side:
```
EditBoxWidgetClass myInput {
    scriptclass "MyValidator"
    { ScriptParamsClass { maxLength 50   pattern "[a-z]+" } }
}
```

---

## TEXT STYLING API — TextWidget vs UIWidget (two SIBLING branches; corrected 2026-07-05)

```
// TextWidget branch (TextWidget, RichText, MultilineText — enwidgets.c:189+):
widget.SetTextExactSize(16);           // exact pixel size
widget.SetOutline(size, argbColor);    // NO "Text" prefix on this branch
widget.SetShadow(size, color, opacity, offsetX, offsetY);
widget.SetBold(true);  widget.SetItalic(true);
int w, h;
widget.GetTextSize(w, h);             // measure rendered text in pixels
// Getters: GetOutlineSize/GetOutlineColor, GetShadowSize/Color/Opacity/GetShadowOffset(out,out)
// Text color on this branch = plain Widget.SetColor().

// UIWidget branch (Button, EditBox, CheckBox, Slider, XCombo, listboxes, spacers —
// enwidgets.c:323-339; SIBLING of TextWidget, methods have the "Text" prefix):
btn.SetTextColor(color);               // THE way to color a button/editbox LABEL
                                       // (Widget.SetColor colors the widget BODY instead)
btn.SetTextOutline(size, argb);  btn.SetTextShadow(size, argb, opacity, offX, offY);
btn.SetTextItalic(true);  btn.SetTextBold(true);
// Getters: GetTextOutlineSize/Color, GetTextShadowSize/Color/Opacity/OffsetX/OffsetY,
// GetTextItalic, GetTextBold — these DO NOT exist on TextWidget (won't compile there).

// EditBoxWidget.GetText() returns string directly (no out param)
string text = editBox.GetText();
// MultilineEditBoxWidget uses out param:
string text2; multiEditBox.GetText(text2);

// ImageWidget:
bool ok = img.LoadImageFile(0, path);  // returns bool
int iw, ih; img.GetImageSize(0, iw, ih);

// Pixel-level positioning (any widget):
widget.SetScreenPos(px, py);  widget.SetScreenSize(pw, ph);
widget.GetScreenPos(outX, outY);  widget.GetScreenSize(outW, outH);

// Visibility:
widget.IsVisibleHierarchy();   // checks entire parent chain
```

## DABS FRAMEWORK ESSENTIALS

### ScriptView lifecycle
1. Constructor → `CreateWidget(null)` → `LoadWidgetsAsVariables` → create/find Controller
2. `GetLayoutRoot()` valid immediately after constructor
3. `UseUpdateLoop()` → true by default (override false to disable)
4. Destructor: remove update → delete controller → Unlink layout → remove from All

### Relay_Command (function-as-command pattern)
```
// In .layout:
Relay_Command "OnSaveExecute"

// In controller (bool return, CommandArgs param):
bool OnSaveExecute(ButtonCommandArgs args)
{
    // logic
    return true;
}
```
Dabs tries: 1) RelayCommand variable, 2) typename, 3) function call via g_Script.CallFunction.

### WidgetAnimator (built into Dabs — DO NOT build custom tween)
```
WidgetAnimator.Animate(widget, WidgetAnimatorProperty.COLOR_A, 1.0, 300);
WidgetAnimator.AnimateEx(widget, WidgetAnimatorProperty.POSITION_Y, 0, 300, WidgetAnimatorEasing.EASE_OUT_SINE);
WidgetAnimator.AnimateColor(widget, endColor, 300, BlendMode.NORMAL);
WidgetAnimator.CancelAnimate(widget);
```
30 easing curves. Properties: POSITION_X/Y, SIZE_W/H, ROTATION_X/Y/Z, COLOR_A/R/G/B/H/S/V, EXACT_TEXT.

### NotifyPropertyChanged
- `NotifyPropertyChanged("X")` — updates only bindings with Binding_Name "X"
- `NotifyPropertyChanged("")` — updates ALL (expensive, avoid)
- `NotifyPropertyChanged("X", false)` — skip PropertyChanged callback (prevent recursion)
- Sub-property: `NotifyPropertyChanged("m_Obj.value")` — dot notation supported

For full Dabs reference → `references/dabs-framework.md`
For complete widget API → `references/widget-api.md`
For layout format → `references/layout-format.md`
For advanced patterns (toggles, anti-overlap, tabs, hover) → `references/advanced-patterns.md`
For admin UI patterns (floating windows, ESP, resize, DPI, widgets) → `references/admin-ui-patterns.md`

---

## LOCALIZATION (stringtable.xml)

### File Format
Place `stringtable.xml` at addon ROOT (same level as config.cpp). Structure:

```xml
<?xml version="1.0" encoding="utf-8"?>
<Project name="MyMod">
    <Package name="MyAddon">
        <Key Id="STR_MYMOD_DEVICE_NAME">
            <Original>Device Name</Original>
            <English>Device Name</English>
            <Spanish>Nombre del Dispositivo</Spanish>
            <French>Nom de l'Appareil</French>
            <German>Gerätename</German>
        </Key>
    </Package>
</Project>
```

### Usage Rules

- **In .layout files:** `text "#STR_MYMOD_DEVICE_NAME"` (with `#` prefix and quotes)
- **In scripts:** `Widget.TranslateString("#STR_MYMOD_DEVICE_NAME")` or `SetText("#STR_MYMOD_...")` directly
- **Key Id NEVER includes `#`** — only references use it
- **`<Original>`** is fallback if player's language not found
- Omit unsupported languages (English + 1-2 others sufficient for mods)

### Naming Convention (LFPG example)
```
STR_LFPG_[DEVICE]_[ELEMENT]
e.g., STR_LFPG_BTC_BTN_BUY_BTC (Buy Bitcoin button on Bitcoin device)
e.g., STR_LFPG_PHONE_TITLE_MAIN (Main title on phone)
```
Keep consistent prefix for grep-ability and namespace isolation.

### Common Mistake
Using raw text in `.layout` instead of `#STR_` keys works visually but is **NOT translatable** and **FAILS translation mods**. Always externalize UI strings to stringtable.xml.

---

## LAYOUT REGISTRY PATTERN (from LBmaster)

Centralized layout management with mod-overridable paths:
```
class MyLayoutManager {
    static ref MyLayoutManager s_Instance;
    ref map<string, string> m_Layouts = new map<string, string>();
    
    static MyLayoutManager Get() {
        if (!s_Instance) s_Instance = new MyLayoutManager();
        return s_Instance;
    }
    void RegisterLayout(string name, string path) { m_Layouts.Insert(name, path); }
    void OverwriteLayout(string name, string path) { m_Layouts.Set(name, path); }
    Widget CreateLayout(string name, Widget parent = null) {
        string path;
        if (!m_Layouts.Find(name, path)) return null;
        return g_Game.GetWorkspace().CreateWidgets(path, parent);
    }
}
// Other mods override via: modded class MyLayoutManager { void MyLayoutManager() { OverwriteLayout("X", "newpath"); } }
```

---

## STYLES FILE FORMAT (.styles)

```xml
<WidgetStyles>
    <Widget Name="PanelWidget">
        <Style Name="MyStyle" Font="gui/fonts/MyFont" ImageSet="my_set" Color="4294967295">
            <State Name="Normal">
                <Item Name="Top" Image="pixel" />
                <Item Name="Center" Image="" />
                <!-- 9-slice: Top/Right/Bottom/Left + corners + Center -->
            </State>
        </Style>
    </Widget>
</WidgetStyles>
```
Register in config.cpp `class defs`:
```cpp
class widgetStyles { files[] = { "MyMod/gui/styles/mystyles.styles" }; };
class imageSets { files[] = { "MyMod/gui/imagesets/my_set.imageset" }; };
```

---

## CONFIG.CPP `defines[]` — Custom Preprocessor Defines

```cpp
class CfgMods {
    class MyMod {
        defines[] = { "MY_FEATURE_FLAG" };
    };
};
// Then in scripts: #ifdef MY_FEATURE_FLAG ... #endif
```
Useful for feature flags across mod boundaries.

## TROUBLESHOOTING — Common UI Failures & Quick Fixes

| Symptom | Root Cause | Fix |
|---------|-----------|-----|
| Widget not clickable | `ignorepointer 1` on widget or ancestor | Remove from interactive widgets, keep only on decorative |
| Text overlaps widget below | Absolute positioning + dynamic visibility | Use RecalculateLayout() pattern (see advanced-patterns.md) |
| Button click doesn't fire | Missing `SetHandler(this)` in vanilla handler | Add SetHandler in constructor; not needed with Dabs ViewController |
| OnMouseLeave never fires | Wrong parameter count (3 instead of 4) | Signature: `OnMouseLeave(Widget w, Widget enterW, int x, int y)` — 4 params |
| Colors appear darker than expected | DayZ default LV darkening | Call `Widget.SetLV(0)` and `Widget.SetTextLV(0)` once at mod init |
| Alpha below ~48 is invisible | Engine low-alpha clamp | Keep alpha ≥ 0x30 (48). Measured bracket: 0x12 invisible, 0x26 visible |
| Relay_Command runs more than once | Handler returned false/void → re-invoked up the parent chain | Command handlers must `return true` when handled (Rule 16) |
| EditBox text not updating | Binding not notified | Call `NotifyPropertyChanged("FieldName")` after changing value |
| Layout crashes game on load | XML-format layout, or unbalanced braces, or MISSING layout file (CTD inside native CreateWidgets — null-check never runs) | Brace format only; run the linter (LAYOUT-XML-FORMAT + ES-LAYOUT-FILE-MISSING detectors). NOT caused by missing leaf `{ }` (Rule 1) |
| UI right at 1080p, wrong at other resolutions | Exact flags = physical pixels | Proportional flags (0) + anchor idiom (Rule 3); verify with build_viewer.py resolution switch |
| Half my UI is missing (widgets after some point never appear) | Parser stops at first syntax error, loads partially | Check brace balance at/before the first missing widget; `MissionBase.DumpCurrentUILayout()` shows what actually loaded |
| Imageset/style renders in Workbench but blank in-game (or vice versa) | Dual registration missed | Register in BOTH `dayz.gproj` (editor) and `config.cpp class defs` (game) — plan-to-implementation.md §3 |
| Scroll content doesn't scroll | No spacer child in ScrollWidget | Add WrapSpacerWidget or GridSpacerWidget as direct child |
| ImageWidget invisible in script | No image loaded | `LoadImageFile(0, "#(argb,8,8,3)color(1,1,1,1,CO)")` then SetColor. ⚠️ this procedural texture FAILED on DayZ 1.29 ("Bad texture name", LFPowerGrid RPT) — if it fails, ship a 1×1 white .edds (or use a Colorable style, styles-format.md §5) |
| ViewBinding not updating UI | Binding_Name mismatch | Verify ScriptParams Binding_Name matches controller property exactly |
| CreateWidgets crashes | Called from RPC or early init | Pre-create views in MissionInit when GetWorkspace() is valid (Rule 9) |
| Widget z-order wrong | Children overlap in wrong order | Use `Widget.SetSort(int)` — higher value renders later (on top). SetSort(1000 - priority) for priority ordering |
| Map markers not updating | Full refresh every frame is too expensive | Use dirty-check pattern: compare counts/hashes, only refresh when changed (see lbgroups-patterns.md §9) |
| 3D marker behind camera | Not checking z depth from GetScreenPos | `GetGame().GetScreenPos(pos)` returns z in [2] — if z <= 0, marker is behind camera, hide it |
| EditBox OnChange not firing | No handler set | Create `ScriptedWidgetEventHandler`, call `editBox.SetHandler(handler)` — required for vanilla (not Dabs) |
| Chat text overflows | No word wrap in TextWidget | Use hidden TextWidget measurement trick (SetText → Update → GetScreenSize) to calculate width before placing |
| Widget not destroyed | Using `Show(false)` instead of destroying | Call `widget.Unlink()` to destroy widget and all children. `Show(false)` only hides |
| ComboBox selection resets | Items cleared and re-added without saving selection | Save `GetCurrentItem()` before `ClearAll()`, restore with `SetCurrentItem()` after re-add |
| Slider value not syncing with EditBox | One-directional binding | Implement bidirectional: slider OnChange → update editbox text, editbox OnChange → update slider current |

## MOCKUP FIDELITY — calibrate to text_proportion; don't edit .layout off a mockup (added 2026-06-03)

When building an HTML/preview mockup of a DayZ `.layout`, the mockup's CSS `font-size` (px) does
NOT represent the in-game render: DayZ TextWidget text size is driven by `text_proportion`
(fraction of widget height), not px. An arbitrary mockup font wraps/overlaps differently than in-game.

- **Calibrate** the mockup font to `text_proportion × box-height`, OR label the mockup explicitly
  as "approximation, not the in-game render".
- **Do NOT change the real `.layout`** (convert a widget to MultilineTextWidget, move positions,
  shrink text) to fix something seen ONLY in an unfaithful mockup — mark it `[verify in-game]`
  first; the in-game render may already be fine. Origin: a 25px mockup title wrapped + overlapped
  the subtitle and triggered a TitleText→MultilineTextWidget change that the calibrated
  (~18px ≈ text_proportion 0.34) render did not need. Cross-ref lessons-learned LL-086.
