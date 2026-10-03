---
name: dayz-ui-development
description: "Use when: DayZ UI, menu, .layout, widget, HUD, CreateWidgets, ShowScriptedMenu, UI doesn't look like the design. Full UI/layout/Dabs. Not general Enforce: enforce-script-reference; not in-game launch: dayz-test-ingame."
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
| Action info panels / construction cursor grids (1.30 Exp) | `references/hud-action-info-panels.md` | `vanilla-menus-map.md §5` |
| Writing/debugging a `.layout` file | `references/layout-format.md` | Rules 1-4 below |
| Starting from a copy-paste layout (modal / HUD / form row / scroll list) | [`templates/README.md`](templates/README.md) | that template + Rules 1-4 |
| Iterating a design without repacking (edit the file, see it in the running game) | `references/hot-iteration.md` | Rules 1-4 below |
| Styled chrome (borders, buttons w/ press feedback, 9-slice, theming a panel) | `references/styles-format.md` | — |
| Dabs MVC (ScriptView, bindings, animations) | `references/dabs-framework.md` — **its §HEAD DEEP-DIVE supersedes older sections on conflicts** | Rules 15-18 below |
| Expansion menus/HUD | `references/expansion-mvc-patterns.md` + `expansion-market-menu-pattern.md` | — |
| Widget method signatures | `references/widget-api.md` ⚠️ see its correction note in the index below | or grep `scripts/1_core/proto/enwidgets.c` directly |
| Incline/tilt a panel onto a world surface (widget rotation/transform) | `references/widget-api.md` | — |
| Map/canvas/3D-markers/admin windows | `references/lbgroups-patterns.md`, `references/admin-ui-patterns.md` ⚠️ | — |
| Recolor/retheme requests | THEME REALITY section below (scope it before estimating) | — |
| Keybind to open the UI (`inputs.xml` schema, config.cpp `inputs=`) | **`enforce-script-reference` skill** (outside this skill's verified corpus) | vanilla-menus-map.md §4 for the OnUpdate polling pattern |

⚠️ = files with confabulated/unverified code: `advanced-patterns.md` (3 broken APIs — read its
CORRECTIONS banner first), `admin-ui-patterns.md` + `lbgroups-patterns.md` (zero path:line cites —
treat code as pseudocode until re-verified). Anything marked "corrected 2026-XX-XX" states current
truth; the date is provenance, not history you need.

## Parser routing — which `.layout` reader

If you need **where** a widget is (rectangle, click centre, reachability): the geometry
parser (`layout_ast.py`) and `ui_rects.py`, both in DayZ_Tooling — not this pack. If you
need **what** it says (text, color, image, any key): `dayz-ui-lab`
(`python tools/dayz-ui-lab/dayz_ui_lab/parse.py <layout>`). Neither is a superset of the
other. Contract, the format parser's inline-`position` collapse, and the superseded
`DayZ_UI_Research/renderer/parse.py` (do not revive — it silently strips `\` from Windows
paths): [`TOOLS.md`](../../TOOLS.md).

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

⚠ **The path `tools/dayz-script-validator/...` is relative to Knowledge Pack root.**
From a project (`P:\<Mod>\`) it does not exist and command dies with `No such file or directory`,
reading as "not installed". Working way from anywhere:
`python <KNOWLEDGE_PACK>/tools/dayz-script-validator/scripts/script_validator.py <addon_root>`.
⚠ **And its exit code is 0 PASS / 1 FAIL / 2 WARN**: a clean tree with warnings exits with **2**,
so `if rc != 0` rejects it. Gate by JSON `len(errors)`, or treat 2 as pass.
Companion: `ui_reconcile.py <addon_root>` reconciles `FindAnyWidget` ↔ layouts and `#STR` ↔
stringtable, which no compiler catches; `--strict` turns its WARN into failure.

5. **Preview offline**: `python tools/dayz-layout-viewer/build_viewer.py <layout>`
   → a self-contained `.preview.html` you switch between 1080p / 1440p / 21:9 / 720p.
   Its geometry lays exact units out as pixels at every viewport
   (`tools/dayz-ui-lab/dayz_ui_lab/parse.py:772-775`), while the engine scales them with the
   screen height (Rule 3): at any viewport but 1080p it misplaces exact widgets and everything
   inside them, so trust those views only for widgets with no exact ancestor. *(corrected
   2026-10-03: this step said the viewports let
   you «SEE exact-flag breakage without a build».)*
   **What it does and does not model, read out of the code 2026-08-20.** Two copies of this
   skill used to disagree here — one said "structure and anchoring only", the other said to
   trust it for text — and neither was right. It DOES model text layout: font size from
   `text_proportion` (`html_template.py:110-112`), wrapping (`:116`), `text halign`/`valign`
   (`:104-105`, `:115`), and it clips with `overflow:hidden` (`:117`).
   What it cannot tell you is whether **your string** fits, for two measured reasons. The font
   is a browser substitute — Bahnschrift / Roboto Condensed / Arial Narrow (`:73`) — where the
   engine uses Metron bitmap atlases, so glyph widths differ. And a `#STR_` key is drawn
   bracketed and unresolved (`:107`): running it on `dialog_input_text.layout` puts
   `#STR_TextInputDialogRoot_MessageText0` on screen, not the translated sentence whose length
   actually decides the fit. Since this skill requires `#STR_` keys for all production text,
   that is the normal case, not an edge one.
   So: trust it for **where a box is and whether text of that size would overflow it**; never
   for whether the shipped string fits. That question is a build.
   One trap worth knowing: `wrap` defaults to **1** in the preview (`:116`), so a widget that
   never declared `wrap` still wraps here. If the engine turns out not to wrap `TextWidget` —
   still open, see `layout-format.md` — the preview hides the overflow by showing two lines
   where the game would clip one.
   To read the file rather than draw it,
   `python tools/dayz-ui-lab/dayz_ui_lab/parse.py <layout>` (Parser routing above). Do not call
   `DayZ_UI_Research/renderer/parse.py`.
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
  Includes DayZ 1.30 Exp native `PreviewWidget`, `ItemPreviewWidget` (`SetForceFlipEnable`, `SetForceFlip`),
  and `PlayerPreviewWidget` native APIs, plus verification debunking changelog tickets not exposed in scripts.
- **HUD Action Info Panels & Cursor Construction Grids (DayZ 1.30 Exp modular cursor pipeline)** → `references/hud-action-info-panels.md` —
  modular target action info architecture (`ActionTargetsCursor.c`, `ActionInfoPanels.c`, `ActionInfoGrids.c`, `ConstructionInfoIcons.c`, `action_info_spacer.layout`, `SimpleIconTemplate.layout`), tool/material requirement grids, action dimming (`SetAlpha(0.149)`), universal gamepad controller icon binding via RichText (`SetControllerIcon`).
- **Dabs Framework deep dive (MVC + Animator + Color + Menu)** → `references/dabs-framework.md` —
  now includes a HEAD DEEP-DIVE (2026-07-05, production=Workshop-identical MVC): ScriptViewMenu real
  contract (no OnShow/OnHide; ESC NOT handled), LoadWidgetsAsVariables mechanism + dot-naming,
  WidgetAnimator's 5 verified traps (ms-vs-TimeSpan 1000× trap, swapped bounce easings...),
  Relay_Command dispatch reality, Observables full contract, DIAG `ScriptView.ReloadAll()` hot-reload.
- **Vanilla menus & HUD source map (menu→file→layout table, menu-ID registration, UIScriptedMenu
  contract, HUD chain + IngameHudVisibility flags, inventory architecture, focus model)** →
  `references/vanilla-menus-map.md`
- **.styles system — complete dissection (states, 9-slice item contracts, Colorable mechanism,
  custom-style recipe, ActionWidget 9-slice gradient in 1.30)** → `references/styles-format.md`
- **Layout file format (.layout Enfusion)** → `references/layout-format.md`
- **Starting layouts (modal, HUD overlay, form row, scroll list)** → [`templates/README.md`](templates/README.md#the-four-construction-traps) — four copy-paste `.layout` files and the four construction traps they exist to stop. Offline gate is `tools/dayz-ui-lab` (`parse.py --check`); `ui_rect_lint.py` is not distributed with this pack.
- **★ Hot iteration — edit a `.layout` on disk and reload it into the RUNNING client (measured 2026-08-19)** → `references/hot-iteration.md` — the addon prefix is served by the PBO and only the PBO, but `$profile:` is re-read on every load, so a design can be iterated in seconds instead of one repack-and-boot per change. Carries the guard that keeps `CreateWidgets` from killing the client, the fact that a second load STACKS instead of replacing, and the two silent failures (a missing texture paints flat WHITE and logs nothing; perfect rects say nothing about whether anything is drawn).
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
   — see styles-format.md).
   *(hasta 1.29: For visible backgrounds use ImageWidgetClass with ignorepointer 1 and stretch 1; desde 1.30 Exp: vanilla systematically uses styled `PanelWidgetClass` (`style ActionWidget` in `dayzwidgets.styles:3700`) with parametric gradient slices across all interaction prompts in `day_z_hud.layout:2294, 2477, 2755, 3033, 3311`, replacing `ImageWidgetClass` with `linear_gradient.edds` / `card_drop.edds`).*
   ⚠️ **Breaking change 1.30:** `ImageWidget.Cast(m_Root.FindAnyWidget("interact"))` or `"item"` returns `null` in 1.30 (causing Null Pointer Exception when calling `LoadImageFile`/`SetColor`). Migrate to `PanelWidget.Cast(...)` or generic `Widget`.
   For procedural textures: In script `LoadImageFile(0, "#(argb,8,8,3)color(1,1,1,1,CO)")` then
   `SetColor(ARGB(...))`. ⚠️ The procedural texture FAILED on DayZ 1.29 ("Bad texture name" /
   "LoadImageFile can't load", observed on LFPowerGrid) — fallbacks: ship a 1×1 white `.edds` and
   LoadImageFile that, or use a `Colorable` style (WhitePixel Center, styles-format.md §5).

3. **Declare all 4 pos/size-mode flags EXPLICITLY (0 or 1).** The exact flags choose UNITS,
   not "definedness". `hexactpos/vexactpos/hexactsize/vexactsize 1` = **1/1080 of the screen
   HEIGHT, on both axes**: the engine draws `declared × height/1080` px whatever the width, so the
   screen is always 1080 units tall and `1080 × width/height` units wide (1920 at 16:9, 2560 at
   2560x1080). Measured in game at heights 461, 720, 900, 1080 and 1108 (`ui_tree` rects,
   `dayz_re_scratch/ui_matrix.md` sections 8, 9 and 11, 2026-08-28/29) and on frames (SimpleGroup,
   2026-09-28): a 400-unit panel 16 units from the right edge drew 400 px wide and 16 px from the
   edge at 1920x1080 and at 2560x1080, and 267 px wide and 11 px from it at 1280x720. A layout that
   fits in 1080 units of height fits vertically at every resolution; only the horizontal room
   changes with the aspect ratio. Do not reason in physical pixels (a reviewer who did flagged an
   overflow that did not exist), and do not rescale exact widgets from script by height/1080: the
   engine already did, and the script doubles it (TEXT SIZING LAWS). The header comment
   `EXACTPOS //< Uses physical resolution (g_iWidth, h_iHeight)` (`enwidgets.c:68-71`) does not
   describe what is drawn. `0` = **fraction of parent (0.0–1.0)**, which is what vanilla
   predominantly uses (`gui/layouts` stat: `hexactsize 0` 5851× vs `hexactsize 1` 2727×;
   `loading.layout` uses all four = 0). Choosing: exact (1) keeps a widget's shape and scales it
   with the screen height; proportional (0) stretches it with its parent. At 16:9 the two agree at
   every resolution measured; at another aspect ratio a proportional width follows the screen
   width and an exact one does not. For a resolution-independent full-screen background use the
   canonical `size 0.16 0.09` + `halign/valign center_ref` + `fixaspect outside` pattern
   (`gui/layouts/loading.layout:36-55`).
   *(corrected 2026-10-03)* This rule's heading added «— do NOT default them to 1», after a
   2026-07-03 note: «the old "always set all 4 to `1`" advice was a top cause of
   resolution-dependent divergence.» It said `1` means «**physical screen pixels**», «so an
   all-`1` layout authored at 1080p occupies different RELATIVE space at 1440p/ultrawide/console —
   this is exactly the "looked right in my mockup, lands wrong in-game" failure», and «RULE:
   default to **proportional (0)** for anything that must scale; use **exact (1)** only for
   elements that must be pixel-true (fixed icon/border sizes).» Measured in game, exact units keep
   their share of the screen height at every height above (1440 was not measured), and at
   another aspect ratio they keep their size in height units.
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
- [ ] All 4 unit flags DECLARED per widget (0 = fraction of parent, 1 = 1/1080 of screen height; Rule 3)
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
- [ ] Offline preview eyeballed vs mockup (`dayz-layout-viewer` / `build_viewer.py`, labelled approximation)
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

- **⚠️ NEVER call `Widget.SetLV()` or `Widget.SetTextLV()` from a mod.** They are
  `proto static` — global, not per-widget (`enwidgets.c:114-117`, whose own comment
  says "Set **global** LV of widgets"). Vanilla uses those exact two calls to apply
  the player's brightness preference: `SetHudBrightness()` is
  `Widget.SetLV(value); Widget.SetTextLV(value);` (`dayzgame.c:3778-3782`), fed from
  `EDayZProfilesOptions.HUD_BRIGHTNESS` (`:3784-3787`) at `OnInitialize()` (`:2075`).
  So `SetLV(0)` at mod init does not "normalize colors" — it **overwrites the
  player's HUD brightness setting**, globally, for vanilla UI too.
- If your colors look darker than their hex values, that is the player's brightness
  setting doing its job. Design against it: pick colors that survive it, and check
  them at a non-zero HUD brightness. Do not flatten it.
- The 2026-03-24 measurement behind the old advice (saturated colors barely
  affected, grays and pastels significantly darker) was real, but it measured **that
  machine's HUD_BRIGHTNESS**, not an engine constant. `SetLV`'s documented default
  is 0; a box that renders dark has a negative value in its profile.
- This corrects advice this skill shipped until 2026-08-22, which said "one line
  fixes everything" and prescribed the call at init. It was wrong in six places.
  Origin: LFHeli adversarial round 1; the HUD removed both calls and the UI gates
  held.
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
| PreviewWidgetClass | PreviewWidget | 3D render | — | Base class for in-UI 3D entity renders (ApplyToCamera, SetModelOrientation/Pos) |
| ItemPreviewWidgetClass | ItemPreviewWidget | 3D item | — | 3D item render; SetItem, GetItem, SetView, GetView, SetForceFlipEnable, SetForceFlip |
| PlayerPreviewWidgetClass | PlayerPreviewWidget | 3D player | — | 3D player render; UpdateItemInHands, SetPlayer, GetDummyPlayer, Refresh |

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

## LOCALIZATION (stringtable.xml / stringtable.csv)

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

### Stringtable CSV: column HEADER decides if engine registers it (measured 2026-08-21, two flights)

DayZ accepts `stringtable.csv` at addon root. Two ladders flown same day
(8 structural variants + 9 variants of CSV itself; evidence and frames in
`AI/10_Projects/DayZ_MCP/reviews/2026-08-19-ui-reload-layout/VERDICT-stringtable-ladder.md`):

- Resolution survives removing ALL structural elements (scripts + class defs, `data\`,
  `gui\`, `model.cfg`, `include.lst`, config body, richness of CfgPatches/CfgMods):
  a THREE-file addon (`$PBOPREFIX$` + minimal config + csv) resolves.
- **The toggle is the column header.** With the 7 baseline columns
  (`"Language","original","english","spanish","german","russian","chinesesimp"`) it resolves
  even with TWO data rows; with 4 (lacking german/russian/chinesesimp) it outputs raw at
  any scale (263 rows or 8), even if PBO loads (tested with crash report addon census)
  and even if client language column is present with text.
  Row count, corpus size, and physical blank lines: irrelevant.
- Packer does not matter (FileBank and MakePbo behave identically) and `$PBOPREFIX$`
  dialect (`prefix=...;product=...;` vs bare name) is harmless also under
  MakePbo, which does consume the file.
- Which of the three removed columns is critical remains un-bisected; safe rule
  is complete 7-column header.

**Practical rule**: every `stringtable.csv` you pack carries 7-column header
(untranslated columns copy English); rows, as many as needed — two suffice.
An unregistered key outputs raw WITHOUT `#` (engine recognized it as key and did not
find it), identical to "non-existent key". A `.layout` loaded via `$profile:` does NOT supply
stringtables (they only enter via addon PBO on boot) — for dynamic text use
literals or `ui_set_text`, without keys. The `templates/stringtable.csv` of this skill carries
the 7-column header precisely because of this.

### Paneles de preview on-demand (generador incluido)

`scripts/gen_panel_layout.py` generates layouts ready for the loop
`$profile:` + `ui_reload_layout` + `ui_set_text`: chat/log feed, label/value
panel, and minimal HUD, with contractual widget names (`TitleText`,
`FeedLine0..N-1`, `LabelK`/`ValueK`) documented in `scripts/CONTRACT.md`.
Flown in-game 2026-08-21 (10-line feed hot-injected with
`ui_set_text`, without stringtable). `--self-test` verifies balanced braces and
name uniqueness without opening game.

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
| Colors appear darker than expected | The player's HUD_BRIGHTNESS, applied globally by vanilla | Design against it. **Do NOT call `Widget.SetLV(0)`** — it is `proto static` and overwrites the player's setting (`dayzgame.c:3778-3782`). See COLOR SYSTEM |
| Alpha below ~48 is invisible | Engine low-alpha clamp | Keep alpha ≥ 0x30 (48). Measured bracket: 0x12 invisible, 0x26 visible |
| Relay_Command runs more than once | Handler returned false/void → re-invoked up the parent chain | Command handlers must `return true` when handled (Rule 16) |
| EditBox text not updating | Binding not notified | Call `NotifyPropertyChanged("FieldName")` after changing value |
| Layout crashes game on load | XML-format layout, or unbalanced braces, or MISSING layout file (CTD inside native CreateWidgets — null-check never runs) | Brace format only; run the linter (LAYOUT-XML-FORMAT + ES-LAYOUT-FILE-MISSING detectors). NOT caused by missing leaf `{ }` (Rule 1) |
| UI right at 1080p, wrong at other resolutions | Not the exact flags: they scale with the screen height (Rule 3, corrected 2026-10-03). A script that also scales exact widgets by height/1080 (double scaling), bitmap glyphs that do not shrink with their boxes (TEXT SIZING LAWS), or a proportional width at another aspect ratio | Drop the script-side scaling; size bitmap text for the smallest supported height; check in game at 720p and at your widest aspect. `dayz-layout-viewer` / `build_viewer.py` lay exact units out as pixels at every viewport (`tools/dayz-ui-lab/dayz_ui_lab/parse.py:772-775`), so their non-1080 views misplace exact widgets |
| Half my UI is missing (widgets after some point never appear) | Parser stops at first syntax error, loads partially | Check brace balance at/before the first missing widget; `MissionBase.DumpCurrentUILayout()` shows what actually loaded |
| Imageset/style renders in Workbench but blank in-game (or vice versa) | Dual registration missed | Register in BOTH `dayz.gproj` (editor) and `config.cpp class defs` (game) — plan-to-implementation.md §3 |
| Scroll content doesn't scroll | No spacer child in ScrollWidget | Add WrapSpacerWidget or GridSpacerWidget as direct child |
| A UI image comes out as a flat WHITE box | The texture path does not resolve | Check the path first, not the color or the style: a missing UI texture fills the slot with white (255,255,255, deviation 0,0) and writes **nothing** to the RPT (measured 2026-08-19) |
| Reloading a layout at runtime draws two copies, or clicks land on nothing | `CreateWidgets` STACKS a second tree, it does not replace the first | `Unlink()` the previous root before every load (hot-iteration.md trap 2) |
| ImageWidget invisible in script | No image loaded | `LoadImageFile(0, "#(argb,8,8,3)color(1,1,1,1,CO)")` then SetColor. ⚠️ this procedural texture FAILED on DayZ 1.29 ("Bad texture name", LFPowerGrid RPT) — if it fails, ship a 1×1 white .edds (or use a Colorable style, styles-format.md §5) |
| FindAnyWidget returns null for interact / item in HUD (1.30 Exp) | Interaction widgets in day_z_hud.layout mutated from ImageWidgetClass to PanelWidgetClass with style ActionWidget | Cast to PanelWidget instead of ImageWidget: `PanelWidget.Cast(m_Root.FindAnyWidget("interact"))` |
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

On the "No word wrap in TextWidget" row above, two different claims are easy to
confuse, and only one of them is measured. The 2026-08-19 census in
`layout-format.md` proves that the `wrap` attribute **is written** on
`TextWidgetClass` (4 occurrences) and on `RichTextWidgetClass` (236). It does not
prove the engine **honours** it there: four occurrences in a 819-layout corpus is
equally consistent with four layouts setting an attribute that does nothing. So:
`wrap` on a TextWidget is not "impossible" or absent from the corpus — that part
of the row was wrong — but a counting exercise cannot settle whether the engine
honours it. An in-game probe settled it on 2026-08-22: **it does not.**

### `wrap` is INERT on TextWidget — measured in-game (2026-08-22)

DayZDiag 1.29.163709, live client. One `.layout` holding three widgets side by
side with the **same** box (260x150, `hexactsize`/`vexactsize`), the same
`text_proportion 0.14` and the same 12-token string
`UNO DOS TRES CUATRO CINCO SEIS SIETE OCHO NUEVE DIEZ ONCE DOCE`:

| Widget class | Declares | Renders |
|---|---|---|
| `TextWidgetClass` | `wrap 1` | ONE line, clipped mid-token at `SEIS S` |
| `TextWidgetClass` | `wrap 0` | ONE line, clipped at the same token |
| `MultilineTextWidgetClass` | `wrap 1` | FIVE lines, all 12 tokens visible |

`wrap 1` and `wrap 0` on a TextWidget are indistinguishable in the frame. The
MultilineTextWidget is the **positive control**, and it is what makes the negative
admissible: five wrapped lines fit in that same 150 px box, so the TextWidget had
the room and did not use it.

Run twice by two independent routes — text assigned at runtime (`SetText`) and text
written literally into the `.layout` — with the same verdict, so the inertness is
not an artifact of the runtime setter. The instrument is the rendered frame, not
`GetTextSize()`: with an exact size the box cannot grow, so wrap can only show up as
line breaks inside it. Evidence:
`20_Knowledge/capturas/wrap-textwidget-{1of2-settext,2of2-literal}-20260822.jpg`
(sha256 `67C9D85D…` / `BDBEBCBB…`), probes `lf_wrap_probe.layout` (`7DAD7101…`) and
`lf_wrap_probe2.layout` (`0CAD0F24…`).

So the four corpus occurrences are exactly what the census could not rule out:
layouts setting an attribute that does nothing. `MultilineTextWidget` is not merely
the *reliable* choice for wrapping text — it is the only one.

This is consistent with there being no script-side switch either: the `WidgetFlags`
enum contains no text-wrap flag (`enwidgets.c:57-85`, 26 entries). `NOWRAP` (`:63`)
is a texture flag (`//< Do not do texture wrapping`), and the file's only other
`wrap` symbol, `class WrapSpacerWidget` (`:477`), is a flow-layout container type —
not a flag and not applicable to a `TextWidget`. `CreateWidget(TextWidgetTypeID,
...)` + `SetFlags(...)` cannot express wrap; the probe above shows the `.layout`
attribute cannot either.

## TEXT SIZING LAWS — measured in game (2026-08-21, 2026-08-28, 2026-09-28)

One probe layout (`$profile:` hot-reload, cases A-G), same strings, measured per-pixel on
full-res captures at TWO viewports on the SAME running client (846x461, then 1600x900 via
host-side SetWindowPos + reload — no reboot needed for a resolution sweep). Evidence:
`dayz_re_scratch/ui_matrix.md` section 9 (flight F, run dbca698d). The face laws below add
SimpleGroup's panels, hot-loaded and captured natively at 1920x1080, 1280x720 and 2560x1080
(2026-09-28). Rules to design by:

- **An unnumbered bitmap face (`gui/fonts/Metron`, `MetronBook`) or an SDF face, with no size
  key (no `"exact text size"`, no `text_proportion`), takes its glyph height from the widget
  box.** A numbered bitmap face (`Metron14`…) does not: next bullet. `sdf_MetronBook24` at
  720p: glyph = 0.74 × box height (`references/hot-iteration.md`, "Glyph height tracks the
  WIDGET height", 2026-08-20/21). The bitmap `gui/fonts/Metron` and `MetronBook` in
  SimpleGroup's shipped panel, on texts without descenders: ink 10 px in an 18-unit box and
  14 px in a 24-unit box at 1920x1080, 7 and 8 px at 1280x720, 0.5-0.6 of the box at both,
  nothing clipped. A plan built on
  a box-independent ~22 px glyph predicted clipping that did not happen. The one reading the
  other way: flight F's case G, a 20-unit box, drew the same glyph as case F's 40-unit box,
  clipped (at which of its two resolutions is not recorded; at 846x461 the box is 8.5 px tall).
  `gui/fonts/metron.xml` lists one atlas per size (12, 14, 16, 22, 28, 48, 58), so the
  readings are consistent with the engine picking an atlas by box height, with nothing smaller
  than 12 for a box too short for it — not verified. Corollary that closed a real bug: rects
  with exact flags scale by (height/1080) (Rule 3) and the glyphs scale with them. A script
  that then shrank the rects with SetSize (x0.444 at 720p) did not shrink the glyphs, and the
  text was guillotined (2026-08-28). Skip the scaler and both scale together for free.
  *(corrected 2026-10-03)* This bullet said: «**The font-only default (a `font` attribute and no
  size key) SCALES with the viewport and IGNORES the widget box.** Half-height box = same glyphs,
  clipped.» Its corollary had the default glyph size scale by (height/1080) on its own, «while
  glyphs stayed viewport-sized».
- **A numbered bitmap face (`gui/fonts/Metron14`, `MetronBook12`, `Metron22`…) keeps its pixel
  size at every resolution, whatever its box.** SimpleGroup's p9 panel, same capture pair: the
  ink of its `Metron22`, `Metron14`, `MetronBook12` and `Metron22` texts was 13, 10, 8 and 14 px
  at 1920x1080 and 13, 9, 8 and 14 px at 1280x720, so 0.46-0.50 of the box became 0.68-0.75 as
  the boxes shrank to 2/3. `MetronBook12` labels at ~84% box fill at 1080p touched both edges at
  720p, and a `MetronBook12` sentence became unreadable. Size such text for the smallest height
  you support: at 720p the box is 2/3 of its 1080p size and the glyph is not, so text that must
  fit there fills at most 2/3 of its box at 1080p, padding included. The ticket's rule of thumb,
  ~75%, held in that panel; by the arithmetic it overflows at 720p unless the glyph shrinks (one
  `Metron14` text did, by one pixel). Do not set sentences in `MetronBook12`; S2 sorter rule 2
  below is the same law ("POWERED" in `Metron12`).
- **`"exact text size" N` obeys a DIFFERENT law per widget class and face.** On
  `TextWidgetClass` with an SDF face — vanilla's inventory header recipe, `font
  "gui/fonts/sdf_MetronLight24"` + `"exact text" 1` + `"exact text size" 20`
  (`inventory_new/closable_header.layout:139-158`) — the text is drawn at about N px per 1080
  of screen height and scales with the boxes: SimpleGroup's title in `sdf_MetronBook24` at N=24
  drew 17 px of ink (no descender) at 1920x1080 and at 2560x1080 and 12 px at 1280x720
  (2026-09-28), and at N=20 the advance is ~10.5 px per Latin character at 1080p. That is the face to pick for text that must
  keep its proportions. On `TextWidgetClass` with the bitmap `gui/fonts/Metron` the rendered
  size scaled with the viewport too, but smaller (N=20 was unreadable ~3px at 461-high, ~9px
  cap at 900-high). Inside the canonical dialog recipe on `RichTextWidgetClass`
  (`"exact text" 1` + `"exact text size" 20` + `"size to text h/v" 1` + `wrap 1` +
  `clipchildren 1`) the glyphs stay PHYSICALLY CONSTANT across resolutions (cap ~10px at
  both). Use the dialog recipe when constant physical legibility is wanted; accept that it
  will not track panel size.
- **`text_proportion` has NO clean monotonic law across boxes or resolutions.** Same 0.5
  on a 40-high box rendered cap 9px@461 and 8px@900 (did not scale); on an 80-high box
  13->21 (did scale). Treat it as a per-widget empirically-calibrated knob, never as a
  predictable scaling mechanism.
- **`MultilineTextWidgetClass` does NOT wrap unless `wrap 1` is declared.** The 2026-08-22
  probe proved MultilineText+`wrap 1` wraps; this probe proved the attribute's default is
  NO wrap (one giant clipped line). Always declare `wrap 1` on multiline text.
- **`"size to text v" 1` really grows the box at runtime** (declared 60 -> engine-reported
  36 while siblings scaled to 25.6) and the grown text paints OVER the next sibling: give
  size-to-text widgets a clipping container or reserved room.
- **Glyphs bleed ~1-2px LEFT of the widget rect** (first-glyph bearing/AA; caught by eye
  on a live frame, confirmed per-pixel: background edge exactly on the rect, glyph 1px
  outside). Never start text flush at a colored box edge — pad >=4-8px horizontally.
- **The alpha channel of a layout `color R G B A` on a texture-less ImageWidget is IGNORED
  by the compositor** (three 0.25-alpha panels rendered their source color pure, measured
  per-pixel; the token itself DOES reach the engine — ui_tree reports it). On that widget
  declared translucent washes do not exist: pre-mix the wash into an opaque token, or SetColor at
  runtime. (Texture-less ImageWidget does paint a flat opaque fill — twice confirmed.)
  A `PanelWidgetClass` with `style rover_sim_colorable` (WhitePixel in all nine slices,
  `dayzwidgets.styles:3223-3246`) does honour the alpha: `color 0 0 0 0` drew nothing and
  `1 0 0 1` a red fill (SimpleGroup, 2026-09-28; partial alphas not measured). A
  `ButtonWidgetClass` with a `color` and no `style` drew no fill at all, while the same frame's
  `style Colorable` button did (`style Default` draws nothing in Normal either:
  `dayzwidgets.styles:1593-1604`). Vanilla's pause-menu buttons are an invisible
  `ButtonWidget` over a child `<name>_panel` the script tints, plus a `<name>_label`
  (`day_z_ingamemenu.layout:122-158`, `ingamemenu.c:365-415`).

## MOCKUP FIDELITY — calibrate to text_proportion; don't edit .layout off a mockup (added 2026-06-03)

When building an HTML/preview mockup of a DayZ `.layout`, the mockup's CSS `font-size` (px) does
NOT represent the in-game render: DayZ TextWidget text size is driven by `text_proportion`
(fraction of widget height), not px. An arbitrary mockup font wraps/overlaps differently than in-game.
*(scoped 2026-10-03: that holds for the faces that follow their box; a numbered bitmap face such
as `Metron14` keeps its pixel size, and an SDF face with `"exact text size"` N scales with the
screen height — TEXT SIZING LAWS.)*

- **Calibrate** the mockup font per face: `text_proportion × box-height` for a face that follows
  its box, the face's own pixel size for a numbered bitmap face, N × height/1080 for an SDF face
  with `"exact text size"` N. OR label the mockup explicitly as "approximation, not the in-game
  render".
- **Do NOT change the real `.layout`** (convert a widget to MultilineTextWidget, move positions,
  shrink text) to fix something seen ONLY in an unfaithful mockup — mark it `[verify in-game]`
  first; the in-game render may already be fine. Origin: a 25px mockup title wrapped + overlapped
  the subtitle and triggered a TitleText→MultilineTextWidget change that the calibrated
  (~18px ≈ text_proportion 0.34) render did not need. Cross-ref lessons-learned LL-086.

---

## A green automated UI gate says nothing about how the UI LOOKS (measured 2026-08-19)

A full acceptance run of a modal dialog passed **11 API cases and then 10/10
cases driven by real mouse clicks** — correct terminal states, values in
declared order, unicode round-trip, no button overlap, rects matching the
offline prediction to the decimal. While all of that was green, a human looking
at the screen found three defects in under a minute:

1. the panel background was not painting at all (white text over the game
   world), because the style name was valid for another widget type;
2. a 29-character title was clipped on both sides;
3. most buttons needed two clicks, the first apparently spent gaining focus.

None of the three is reachable from the automation path, and not by accident:

- **`ui_tree` returns the color, and the color was CORRECT.** What fails is the
  painting, and no verb reads pixels.
- **Text is unreadable to the machine by contract.** `FillUiNode` fills `text`
  only for `EditBoxWidget`, `MultilineEditBoxWidget` and `ButtonWidget`;
  `TextWidget`/`MultilineTextWidget`/`RichTextWidget` report
  `text_readable=false` with an empty string. A clipped title is invisible to
  every gate you can write.
- **`ui_click` is not a click.** It resolves the handler through
  `GetScript`/`GetUserData` and calls `OnClick(target, 0, 0, mouseButton)` with
  the coordinates hardcoded to zero, so it skips hit-testing, Z-order and
  `IGNOREPOINTER` by construction.

**Operational rule.** For any UI deliverable, a passing automated gate closes
the CONTRACT and nothing else. Rendering and interaction need a human, or a
screenshot that a human (or a vision model asked for a MEASUREMENT, not a
verdict) inspects. Put `capture_screenshot` in the acceptance protocol as
mandatory evidence rather than optional colour.

**And when the human is the instrument, the harness text is part of the
instrument.** A test dialog that said "No debe salir 'no'" — meaning the
returned `choice` — was read as "the No button should not be there" and reported
as a bug. Operator-facing text states what to DO and never what the expected
result is.

## Hot-loop S2 sorter — reglas nuevas medidas (added 2026-08-29)

Origin: `$profile:` preview of integrated 820x600 layout of sorter V4 TEST
(250 widgets, 1920x1080 and 1280x720). Evidence: `dayz_re_scratch/ui_matrix.md` §11,
captures `capture_20260829_003222_408` / `_003807_235`.

1. **`visible 0` declared in `.layout` WORKS** (engine and preview): overlapping section
   roots, overlays, and badges are born hidden without script (`visible:0` +
   `visible_hierarchy:0` in engine tree). Pattern for swappable sections:
   N identical overlapping roots, active one `visible 1`, rest `visible 0`;
   script only toggles root (kills stacked section gap, F-007).
2. **Glyphs do NOT compress linearly when lowering factor**: a box fitting at
   1080p can clip at 0.667 ("POWERED" lost the D with a 62 px box;
   needed 70). Size text box to WORST supported factor and verify
   there; +10-15% margin over width measured at 1080p.
3. **Typographic hierarchy in default font-only mode = sized faces**:
   `gui/fonts/Metron12/14/16` and `MetronBook12/14` exist and vanilla uses them
   (`day_z_hud.layout:1965` Metron14). Unnumbered faces ("Metron",
   "MetronBook") take their size from the box (TEXT SIZING LAWS), so with them the
   hierarchy is the box heights. Sized bitmap faces keep their pixel size at every
   resolution; text that must scale with the panel wants an SDF face with
   `"exact text size"` (same section). `text_proportion` remains
   barred (no consistency across resolutions).
   *(corrected 2026-10-03: this rule said unnumbered faces «yield ~22 and offer no fine
   hierarchy».)*
4. **Pre-mixed tokens validated end-to-end on real panel**: ARGB of
   `ui_tree` returns declared float byte-exact and render paints PURE
   color (declared alpha ignored). Recipe: `c = base*(1-a) + wash*a`, always
   A=1 in layout. Case token table: S2-LAYOUT-SPEC.md §2 (LFPG).
5. **Host-side resize (SetWindowPos) is NOT universal**: killed a client of
   1942x1136 (process died, no script crash); worked on 846x461 of
   flight F. Safe sweep: relaunch with width/height — and VERIFY viewport
   in tree (a 1280x720 request yielded exact 1280x720 this time; flight F
   got 846x461 with same request: mapping is not stable).
6. **`$profile:` preview is paint without menu context**: clicking
   window gives focus to game and camera CAPTURES mouse (cursor
   disappears and no further clicks occur). ESC (vanilla menu) returns it. No click
   on preview widgets works; interaction is tested with real panel.
7. **100% exact-flag layout geometry**: `ui_rects.py predict` does NOT model them
   (its own header). Valid route: `DayZ_Tooling/scripts/shared/layout_ast.py`
   — `parse_layout(SOURCE)` returns flat list with `.parent/.children` and typed
   attrs (position/size = [float,float]); containment, nesting, z-order and
   visible-0 are checked offline with ancestor summation arithmetic.
8. **Layout generation is delegable**: exhaustive table spec (name/
   class/rect/flags/color/font per widget) + mechanical gate (names exactly
   once, zero legacy, bindings, permitted fonts, alpha=1, one attribute per
   line) allowed a free lane (glm-5.3-flash) to produce 3.4k lines
   correct on first pass; the two real defects were caught by visual gate
   (glyph clip) and eye, not textual gate.

## Clicks on ScriptViews cannot be automated via MCP (added 2026-08-29)

Measured in-game on 2026-08-29 with DayZ-MCP bridge **healthy v10** (`bridge_status ready=true`, both
peers at `10~1.29.163709`, `version accepted`), on LFPowerGrid sorter panel, which
is a Dabs ScriptView and not a `UIScriptedMenu`:

- `ui_tree` with empty `path` returns `no_menu`: walker looks for active *scripted menu* and a
  ScriptView is not one. Via that route there is no widget tree to inspect.
- `ui_click` returns `not_handled` on buttons that exist and are visible on screen.

**The control that makes the second conclusive, and must always be repeated.** `not_handled` on
a button with permission guard is AMBIGUOUS: can be harness not reaching handler, or
controller's fail-closed rejecting action. Opposite conclusions. Distinguished by clicking
also a widget WITHOUT guard. Here close button (`BtnCloseX`), always allowed and independent
of power or link, also gave `not_handled`, and later capture showed panel still
open: click did nothing. Without that second click, result could have been recorded as
"verified fail-closed", which would have been false.

Consequences when planning a cycle: widget names are taken from `.layout`
(`ButtonWidgetClass <Name>`), not from a live tree; and **any gate depending on clicking,
typing in an EditBox, switching tabs, or closing with ESC belongs to user with real mouse**. That a
verb travels inside deployed PBO does not imply it is invokable —daemon tools registry
is fixed at BOOT, so `key_press` and `player_respawn` were in v10 PBO and did not exist as
tools—, nor that, being invokable, it reaches handler. Pipeline tickets: `fb-20260828-212912-f6ac`
(open), evidence in `fb-20260829-022838-7743`.

## Scripted-camera exit lifecycle (added 2026-08-31)

Use this checklist for a spectator, CCTV, drone, FLIR, or other scripted camera. The failure
usually appears on exit, after the feature itself looked complete.

1. **Reuse the engine camera.** Take `Camera.GetCurrentCamera()` and activate it. Do not create an
   unmanaged `staticcamera` object: the author-owned production comparison found that route can
   crash. Evidence: `<project>\scripts\4_World\CameraViewport.c:539-546`.
2. **Keep that camera active through `SelectPlayer`.** Deactivating it first leaves the engine with
   no active camera during player selection. Move `SetActive(false)` to post-selection cleanup
   (`CameraViewport.c:825-869`).
3. **Re-enable the `HumanInputController` before `SelectPlayer`, not after it.** The restored
   third-person camera reads that input in `DayZPlayerCamera3rdPersonErc.UpdateUDAngleUnlocked`
   (`VANILLA/scripts/4_world/.../dayzplayercamera3rdperson.c:54-55`). The diagnostic signature is
   specific: first person works, while third person remains pinned to the former camera transform
   and player actions are absent.
4. **Do not reuse a continuous-action binding as the exit binding.** Use a separate key such as
   SPACE or ESC. Otherwise the ActionManager can retain an action in progress, and vanilla blocks
   third-person look while a non-freelook action is active
   (`VANILLA/scripts/4_world/.../dayzplayercamera_base.c:157-177`).

Verification boundary: rules 1-2 were checked against an author-owned production implementation.
Rules 3-4 were source-checked and matched the observed 1PP/3PP asymmetry, but the originating
2026-08-08 flight had not yet confirmed each cause in game. `Input.ChangeGameFocus(+1/-1)` was
also observed around entry/exit, but its effect in this camera contract remains unverified.
Absence from vanilla is not a reason to remove a working mechanism: `HumanInputController.SetDisabled`
had no vanilla callers in that audit, yet removing it broke the working comparison.

## Transparent ImageWidgets require blend state (added 2026-08-31)

An alpha channel in a PNG/PAA is not enough. Every `ImageWidgetClass` that must composite
transparency declares both lines in its `.layout`:

```text
mode blend
"src alpha" 1
```

Without them, the canonical symptom is an opaque black rectangle the size of the widget with the
art still visible inside. This was isolated by an in-game A/B and matches the vanilla projected
crosshair (`VANILLA/gui/layouts/day_z_hud.layout:2263-2264`). Add this check during layout authoring
and again at delivery. For a strip or tape that must be clipped by its parent, the real attribute is
`clipchildren 1` (`day_z_hud.layout:555`), not `clipping`.

## In-seat interfaces: interrupt before excluding input (added 2026-08-31)

For an interface opened while the player is seated, `HumanInputController.SetDisabled(true)` does
not by itself stop action input. If the interface shares a key with a seat action, the same hold can
close the interface and complete the vanilla action underneath it.

- Add the relevant mission input exclude (for example `{"menu"}`) on open. Restore it on **every**
  exit path, guarded by a flag so a partial open cannot over-release another owner's exclude.
- **Before adding an exclude, interrupt any continuous action already in progress** with
  `ActionManagerClient.RequestInterruptAction()` (`actionmanagerclient.c:1280`). Excluding input
  first can hide the release event and leave the ActionManager permanently in progress until relog.
- While the exclude is active, `UAInput.LocalValue()` is gated to zero. Raw
  `KeyState(KeyCode.KC_X)` (`ensystem.c:291`) and `GetMouseState` still read hardware state, but
  `KeyState` ignores user rebinding. Treat it only as a coarse fallback.

The command-mod that lets a continuous action progress while seated, and the server-owned mirror
needed for late-join vehicle presentation, belong to `dayz-vehicles`/`dayz-aviation`, not this skill.

## Loading-screen hook contract (added 2026-08-31)

This section supersedes the timer/hand-written-`.edds` example in
`references/answeroverflow-2026-05-17.md` §UI-1.

- A loading-screen mod hooks `LoadingScreen`, `LoginQueueBase`, and `LoginTimeBase` with
  `modded class X` and **no `extends` clause**. `LoadingScreen` is not a `UIScriptedMenu`;
  `LoginQueueBase`/`LoginTimeBase` already inherit through `LoginScreenBase`
  (`VANILLA/scripts/3_game/dayzgame.c:63,110,205,688`).
- Do not add a `Timer` just to rotate backgrounds. Accumulate `timeslice` in
  `LoadingScreen.OnUpdate(float)` (called every loading frame at `dayzgame.c:2990-2992`) and in the
  inherited `LoginScreenBase.Update(float)` for the queue/time screens. Loading has no known total
  duration, so rotate on a fixed period rather than trying to divide it in half.
- Use a `.paa` produced by DayZ Tools `ImageToPAA.exe`; do not ship a hand-written `.edds`.
  A decoder round-trip is an inspection gate, not evidence that the engine will render the writer's
  output. See `dayz-texture-pipeline`.
- Replacing the background does not reset `LoadMaskTexture`/`SetMaskProgress`. A black frame can be
  the vanilla reveal mask at low progress, not a broken texture. For a diagnostic full reveal,
  `SetMaskProgress(1.0)` alone is temporary because `ProgressAsync` writes it again every frame;
  detach that updater with `ProgressAsync.SetUserData(null)` only for the controlled diagnostic.
- Never apply a tone compensation from an offline transfer-function model. Measure a known texture
  from an in-game screenshot first.

## SP-365 — Script-driven render-to-texture is dead in DayZ 1.29

`SetGUIWidget(IEntity, index, RTTextureWidget)` (`enwidgets.c:634-637`, "reference in shader as
$rendertarget") and `RTTextureWidget` do not work in the 1.29 runtime: the render target is never
filled from its child widgets. Do not spend cycles on it.

Two in-game probes, both negative:

- `SetObjectTexture(idx, "$rendertarget")` on a hidden selection paints EMPTY BLACK — the token
  resolves, so this is not a typo; a non-existent texture would paint WHITE.
- An `ImageWidget.SetImageTexture(0, rtt)` (`enwidgets.c:258`) mirroring the SAME render target
  paints non-existent-texture WHITE. Producer dead for both consumers.

Zero uses in vanilla scripts and layouts, and no community precedent. The opposite direction —
world into UI, via `RenderTargetWidget` / `SetWidgetWorld` (`rendertarget.c:66`) — does work; it is
the UI-onto-surface direction that is dead.

Live content on a model surface goes the PHYSICAL way instead: `SetObjectTexture` /
`SetObjectMaterial` per hidden selection (these do NOT replicate — server-authoritative int, apply
on both sides, watchdog re-assert), bones driven by model.cfg rotation/translation anims
(`SetAnimationPhase` replicates natively server-side), and hiding by transparent-texture override
(`type="hide"` kills the whole baked Animations block).

A screen-anchored 2D panel over the projected quad's AABB never matches a surface seen at an angle,
in orientation or in size. That is structural, not a tuning problem. Full case: SUB_BRZ GPS
(`SUB_BRZ_NavScreen.c`).

---

## Measured in-game on 2026-09-04 — name collision, engine scaling, and lying probes (added 2026-09-04)

An in-game window of DayZ 1.29.163709 on LFPowerGrid (sorter V4 TEST + production loaded
at once) yielded eight facts this skill lacked, and **three of them break a verification
method that seemed sound**. Everything below is measured, not inferred; citations are
`path:line` of actual tree.

### 1. Two layouts with same names make the second UNREACHABLE

It is the most expensive and easiest structural failure to commit: copying a `.layout` to make a
TEST/debug variant and not renaming its widgets.

Measured on LFPowerGrid:

```
LFPG_Sorter.layout            185 widgets
test/LFPG_Sorter_TEST.layout  213 widgets
NOMBRES QUE COLISIONAN        124        <-- incluidos SorterRoot, SorterPanel,
                                             HeaderFrame, BtnCloseX, BtnSave, todos
                                             los CatBtnN, todos los Edit*...
solo en TEST                   89        (Builder*, CatchAllRow*, BtnPreview*)
```

`LFPG_Sorter.layout:12 SorterRoot` · `:26 SorterPanel` · `:204 BtnCloseX`
`test/LFPG_Sorter_TEST.layout:7 SorterRoot` · `:14 SorterPanel` · `:289 BtnCloseX`
`LFPG_BTCAtm.layout:105 BtnCloseX` — third collision, from another screen of same mod.

Consecuencias medidas:

- `FindAnyWidget("SorterPanel")` and MCP name resolver **cannot distinguish them**.
  Historical symptom was a `ui_click` returning `not_handled`: was resolving in
  silence to PRODUCTION node, whose `OnClick` handles nothing because its view is not open.
- **Scoping by an ancestor does not always save you.** Chain of TEST `BtnCloseX` is
  `SorterRoot → SorterPanel → HeaderFrame → BtnCloseX` and **all three ancestors collide**: no
  exclusive ancestor exists by which to scope search. Button is literally
  unreachable by name.
- **It suffices for the other root to EXIST, not for it to be open.** Recommended pattern of
  pre-creating view in `MissionInit` and then `Show(false)` (Rule 9 of this skill) leaves production
  root instantiated entire session. Ambiguity is permanent, not situational.

**Rule**: widget names are API contract (§5 of `plan-to-implementation.md`). A
TEST/debug variant **prefixes all its names** (`TEST_`, `Dbg_`) or is not addressable. In
LFPowerGrid the 89 exclusive names (`BuilderTabCategory` and company) are precisely only ones
working; 124 shared ones, none.

**Cheap offline gate** — before approving a layout variant, count intersection:

```python
import re, io
def names(p):
    s = io.open(p, encoding="utf-8", errors="replace").read()
    return set(re.findall(r'^\s*\w+WidgetClass\s+(\w+)\s*\{', s, re.M))
print(sorted(names(PROD) & names(TEST)))   # must be empty
```

### 1b. How to fix a name collision: renaming the ROOT is enough (measured 2026-09-04)

Before prefixing 227 widgets, see if just **one** is enough. The bridge resolver contract
states it literally (`DayZ_MCP/scripts/5_Mission/MCPClientBridge.c:2038-2043`):

> `root` names a widget that must be unique in the whole workspace; `path` is then a name
> resolved **inside that scope**. Without `root`, `path` is resolved over the whole workspace,
> ScriptView roots included: 0 matches is `widget_not_found`, 2 or more is `ambiguous_path`, and
> the first homonym is never chosen.

And `ResolveUniqueUiWidget(scope, name)` (`:2114-2131`) counts matches **under `scope`**.
In other words: if the variant layout root is unique, its whole tree becomes addressable again
—`ui_tree/ui_click/ui_set_text` with `root: "TEST_SorterRoot"`— even though the other 135 names
keep colliding.

In LFPowerGrid that was **one line**: `LFPG_Sorter_TEST.layout:7`,
`FrameWidgetClass SorterRoot` → `TEST_SorterRoot`. Measured before touching anything: `SorterRoot`
appeared **exactly twice across the entire mod** (the production declaration and the TEST one),
zero literals in `.c`, zero `Binding_Name`, zero members. +5 bytes, brace balance
intact, production byte-identical.

**Why the order of those two checks matters.** The full prefix seemed the obvious
option and is the expensive one: in a Dabs MVC view there are **three overlapping naming systems** and
renaming widgets touches all of them at once.

| System | In this mod | Renaming the widget breaks it if… |
|---|---|---|
| Widget name in the `.layout` | 227 | — it is the goal |
| Member bound via `LoadWidgetsAsVariables` (member `X` ↔ widget `X`) | 139 | you do not also rename the member |
| `Binding_Name` of a `ViewBinding` | 15 | you rename the member (points to the controller PROPERTY, not to the widget) |

The last two pull in opposite directions: renaming members fixes auto-bind and breaks
`Binding_Name`; not renaming them kills auto-bind. It can be resolved (here: 122 members had
manual `FindAnyWidget`, 11 are resolved via child-walk from the button or via concatenation
`btnName + "Bg"` that tracks the renaming on its own, and only 6 remained exposed), but the failure
mode is **silent null** and the only real gate is another in-game window with PBO rebuild.

**Rule**: when facing `ambiguous_path`, the first question is not "how do I rename everything?" but
**"is there an ancestor I can make unique?"**. If there is, the fix is O(1) and verifiable
offline. The full prefix is still the right thing for a NEW layout — there it costs
nothing—, but for an active one with MVC it is a refactor with its own test cycle.

**And watch out for where the `.layout` lives**: it is served **from the PBO**, not via filePatching (only
`$profile:` is re-read from disk). A rename in the layout of the buildable folder **is not
live until the next build**; until then the client continues seeing the old name.

**Checks that close a root rename, all offline:**

```
1. grep del nombre en TODO el mod (.layout + .c + config.cpp) -> cuenta las apariciones
2. ¿es un Binding_Name?  ¿es un miembro?  -> si no, el cambio es de una linea
3. tras editar: parser OK, roots y widgets con el MISMO recuento que antes,
   balance de llaves igual, y el fichero de produccion byte-identico
4. el nombre nuevo declarado UNA vez y ausente de produccion
```

### 2. Resizing the window does NOT prove resolution independence

This invalidates the method that seems obvious for the #1 pain point of this skill ("it looks different at another
resolution").

DayZDiag retains the render resolution given to it by `-x/-y` on the command line and **scales
the composited surface** up to the window. **It does not recalculate the layout.** Measured with the same
probe before and after a `SetWindowPos` to an actual client rect of 1280x720:

| Campo del panel | ventana 1920x1080 | ventana 1280x720 | ratio |
|---|---|---|---|
| `size_w` | 820 | **546.667** | 2/3 |
| `size_h` | 600 | **400** | 2/3 |
| `pos_x` | 550 | **366.667** | 2/3 |
| `pos_y` | 240 | **160** | 2/3 |

**Everything** by the same factor, `1280/1920`. The unmistakable signature: a widget declared with an exact
size of **1 px** changed to reporting `screen_w = 0.6666666865`. If the engine had re-laid out,
an exact size would still be 1.

Dos corolarios que cuestan caro:

- To truly test another resolution you must **relaunch the client with different `-x/-y`**. There
  is no shortcut via window.
- **The absence of a scaler in the mod code does not prove that there is no scaling.** In this case
  it had been correctly measured that there is not a single appearance of `UIScaler` or `ScaleWidget` in
  the view, and from there it was deduced —wrongly— that the numbers would come out unscaled. Scaling is done by the
  engine; no grep of the mod can see it. When a prediction depends on "there is no scaler",
  the gate is an in-game measurement, not a grep.

### 3. A non-DPI-aware host helper lies, and the gate comes out GREEN anyway

With Windows scaling at 150%, a non-DPI-aware process receives **virtualized** coordinates:

```
GetWindowRect  -> 1295 x 757     real 1943 x 1136
GetClientRect  -> 1280 x 720     real 1921 x 1080
posicion       -> (1080, 56)     real (1620, 84)
```

The danger is not the read, it is the **gate**: `SetWindowPos` was requested at "1280x720" (logical =
1920x1080 physical, meaning no change) and the check `client_rect == requested` compared
logical against logical and **passed in green without having moved anything**. A gate that compares two values
from the wrong space detects nothing.

**Rule**: any helper that measures or moves the game window calls first
`ctypes.windll.shcore.SetProcessDpiAwareness(2)` (with fallback to `user32.SetProcessDPIAware()`).
And the cheap cross-check: MCP `capture_screenshot` returns `window.rect` **and**
`client_surface.rect_window` in physical pixels — if your helper does not match that, the one
lying is your helper.

### 4. ESC does not close if an EditBox is focused — and your probe may be the EditBox

Pattern of `HandleEscKey`, verified in source (`LFPG_SorterView_TEST.c`):

```cpp
Widget focused = GetFocus();
if (focused) {
    EditBoxWidget editCheck = EditBoxWidget.Cast(focused);
    if (editCheck) { SetFocus(null); return true; }   // consume el ESC, NO cierra
}
DoClose();
```

The code's own comment calls it "Double-ESC: first clears EditBox focus, second closes
panel". It is a sound UX pattern. The problem is the observer effect: **if your scripting hook
is an invisible `EditBoxWidget`** —which is the usual pattern to inject commands without
keyboard— and some call leaves it focused, the first ESC is consumed by it and the panel does not close. The
probe alters what it measures.

Mitigation: ensure the hook is a widget without focus (`ignore_pointer 1` is not enough: it must not
be focused), or explicit `SetFocus(null)` after typing into it, or test closing with the
actual button instead of ESC.

### 5. A probe writing to file without freshness stamp does not distinguish "unprocessed" from "stale"

The sorter hook responds by writing a JSON to profile
(`_client/profiles/lfpg_sorter_mcp.json`). The JSON carries state (`open`, `powered`, `paired`,
`status`, `rule_count`) but **no freshness mark**: no timestamp, no sequence, no echo
of the command with id.

Measured: with the panel **closed**, sending a `dump` leaves the file **byte-identical** (same
mtime, same sha) because the view's poll does not run while it is closed. A naive
consumer reads the file, sees `"open": true` from the PREVIOUS dump, and concludes that the panel is still
open. The opposite of the truth.

**Rules for any file-based UI probe:**

- The consumer compares **mtime and hash before and after** each command. No change = command
  not processed; the content is not a response.
- Better: have the probe include a `seq` or the echo of the received command, so that freshness lives
  INSIDE the artifact and does not depend on the filesystem.
- And do not write a gate that requires from the probe a value that **it cannot emit**: requesting a dump with
  `"open": false` is impossible if closing the view stops polling. Before setting the expected
  value, ask whether the instrument remains alive in that state.

### 6. Procedural texture remains broken in 1.29 (confirmed 2026-09-04)

Rule 2 of this skill already warned, with an old date. Reconfirmed in 1.29.163709, in the client
RPT, 4-5 occurrences per boot:

```
RESOURCES (E): Bad texture name '#(argb,8,8,3)color(1,1,1,1,CO)'
GUI       (E): ImageWidget::LoadImageFile can't load '#(argb,8,8,3)color(1,1,1,1,CO)'
```

The fallbacks (a 1x1 white `.edds`, or a Colorable `style` with WhitePixel Center) continue
to be the way. It is not an innocuous warning: the `ImageWidget` is left without texture.

### 7. MCP UI verbs now return what you sent, and the resolved path

Contract change relative to what the August notes documented. `ui_set_text` and
`ui_click` now return:

```json
"ui_request": {
  "requested_path": "BuilderTabCategory",
  "requested_root": "",
  "requested_text": "",
  "matched_path": "/@0/SorterRoot@1/SorterPanel@0/BuilderFrame@0/BuilderTabCategory@0"
}
```

Two gains: evidence receipts no longer need to be noted by hand, and **`matched_path`
exposes the resolver's decision**, which is exactly the data needed to diagnose
name collisions. The `@N` of each segment is the index among siblings: a `SorterRoot@1`
tells you that there are at least two.

And when the name is ambiguous, the resolver **no longer guesses**: it returns `ambiguous_path` instead
of resolving silently. That turns a silent bug into a readable error — but it also
means that a plain name `path` stops working as soon as a homonym exists.

### 8. Log marker trap

`logs_since(max_lines=1)` to "mark the now" returns a marker whose offset falls at the
**beginning** of the file when the log is below the 256 KiB cap. A gate that assumes
"from M0 there is no startup noise" swallows the entire startup. DayZ logs are already per-run
(the name carries the launch date), so to count patterns the reliable approach is to **count
over the run files and date each hit**, not trust the offset.

Related: the mod probe writes to `script_<date>.log`, **not** to the `.RPT`. A positive
control searched only in the RPT yields zero and makes it seem like the probe didn't run.

---

## Measured in-game on 2026-09-05 — hot-iteration contract, positive control of scope, and a correction (added 2026-09-05)

Second window on DayZ 1.29.163709. This entire section was measured **without repacking the mod**,
loading probe layouts via `$profile:` — which is precisely what makes hot-reload useful.
The probes are archived in
`LFPowerGrid_dev/reviews/2026-08-30-uiclick-collision/round-s3b/probes/`.

### CORRECTION — `ui_reload_layout` REPLACES; does not stack (corrected 2026-09-05)

This skill had been saying, in the `references/hot-iteration.md` entry, that "a second
load STACKS instead of replacing". **Measured: no.** Loading the same layout twice in a row
and subsequently querying for a tree widget:

```
ui_reload_layout($profile:uiprobe.layout, reload)   x2
ui_tree(path="ProbeMarker")
  -> UN solo nodo, matched_path "/@0/ProbeRoot@0/ProbeMarker@0"
  -> NO ambiguous_path
```

If it stacked there would be two `ProbeMarker`s and the resolver would have returned `ambiguous_path` — which is
exactly what it returns when there really are two (see §Positive control below). So the
discriminator is reliable and the verdict is firm.

Most likely interpretation of the discrepancy: the original warning described manual `CreateWidgets`,
which does leave the previous root dangling. The `ui_reload_layout` **tool** unlinks before loading.
Do not mix the two: the risk of stacking belongs to the manual path, not to this tool.

### Full contract of `ui_reload_layout`, verified end-to-end

| Call | Measured result |
|---|---|
| `reload` with `$profile:<f>.layout` | loads from disk **without PBO**; returns engine rects of the entire tree |
| `reload` twice | **replaces** (a single tree) |
| `close` | `ui.nodes: []`, and afterwards the widget gives `widget_not_found` — genuinely unlinks |
| `reload` with nonexistent file | `layout_not_found` and **the client remains alive** (`IsWindow` true) |

Two geometry facts that came out of the same probe and are useful to have at hand:

- The preview root reports **`screen_w/h = 1920x1080`**, meaning the engine viewport, not the
  system window size (see the 2026-09-04 section §2 and §3).
- **Child positions are relative to the parent**: a child with `position 110 110` inside a
  parent at `position 100 100` reports `screen_x/y = 210/210`. Obvious when said, easy to forget
  when reading a `matched_path`.
- `TextWidget`s again reported `text: ""` and `text_readable: 0`: **they have no getter**, and
  the tool does not fabricate a false label.

### Positive control of the `root` + `path` mechanism (and why it matters)

Before trusting that scoping by `root` resolves a name collision, **test it with a
case where you can distinguish success from chance**. Probe: two sibling subtrees with a child
of the same name and **different sizes** — size is what turns "it chose one" into
"it chose the correct one" (cardinality is not identity).

```
ScopeProbeRoot
├── ScopeAlpha  └── SharedChild   50x50  @ (210,210)   verde
└── ScopeBeta   └── SharedChild   70x70  @ (1210,210)  rojo
```

| Llamada | Resultado |
|---|---|
| `path:"SharedChild"` sin root | `ambiguous_path` |
| `root:"ScopeAlpha", path:"SharedChild"` | **50x50 @ (210,210)** · `.../ScopeAlpha@0/SharedChild@0` |
| `root:"ScopeBeta",  path:"SharedChild"` | **70x70 @ (1210,210)** · `.../ScopeBeta@0/SharedChild@0` |

The mechanism works and chooses well. That validates the recipe in §1b: **a unique root restores
addressability to its entire tree**, even if children continue sharing names with another tree.

### The A/B that proves when the collision appears

Same call, same session, the only thing changing between the two is opening the variant panel:

| State | `ui_tree(root:"SorterRoot", path:"BtnCloseX")` |
|---|---|
| variant CLOSED | resolves → **production**: 26x26 @ x=688, `visible_hierarchy: 0`, `SorterRoot@0` |
| variant OPEN | **`ambiguous_path`** |

Three things that can be read from there:

1. The **production** root **always exists** (pre-created and hidden), even if its screen has never
   been opened. The variant one is created upon opening it.
2. That is why the collision is not "sometimes": as soon as the variant opens, **all** shared
   names —and the root itself— become unresolvable.
3. `visible_hierarchy: 0` with `visible: 1` is the signature of a pre-created and hidden root. Useful for
   knowing which of the two you are looking at when the resolver returns one.

### Procedural texture: fails via script, silent via layout

Reconfirmed and **narrowed down**. In the same RPT, same build, same string
`#(argb,8,8,3)color(1,1,1,1,CO)`:

- declared via **script** (`ImageWidget.LoadImageFile`): **5** `Bad texture name` +
  **4** `LoadImageFile can't load`, all during mod startup
- declared via **layout** (`image0` in an `ImageWidgetClass`): **0 new lines** in the RPT

The check that the log was flowing at that time: the client script log did grow (fresh
`[MCP-CLIENT]` entries, including `ok=0` from an intentionally triggered `layout_not_found`).

**Caveat that cannot be skipped**: this proves that the layout route **does not emit an error**, not that the
texture is rendered. Distinguishing "loads well" from "fails silently" requires looking at pixels, and that
half remained undone. Do not count it as a validated fallback.

### `frame_client_all_black` might not be from the game

`capture_screenshot` returned `frame_client_all_black` three times in a row with the client
**perfectly healthy**: `camera_get` gave `player_camera_active` with real position and
direction, the window was visible, unminimized, in its rect and was foreground. Ruled out
that it was world time (`world_time_set` to 12:00 changed nothing). Most likely
hypothesis: monitor turned off or session locked — it was the middle of the night.

**Rule**: before diagnosing the game due to a black frame, check with a client verb
that does NOT depend on pixels (`camera_get` works) whether the client is alive and rendering. If it
is, the issue is on the host, not the mod. And consider lost for that night any question whose
arbiter is pixels.

### Questions that remain open for lack of pixels

The probes were set up and remained unread, ready in `round-s3b/probes/uiprobe.layout`:

- **Does a `TextWidget` wrap by default?** The probe provides three rows with the same long text
  and only the attribute changes (`without wrap`, `wrap 1`, `wrap 0`) plus a `MultilineTextWidget` for
  comparison. The rects do not respond: the widget measures what was declared whether the text wraps
  or overflows. **The eye is the arbiter.**
- **Is the procedural texture declared via layout rendered?** See caveat above.

To resume them, having the display turned on is enough: load `$profile:uiprobe.layout` and capture.

---

## DayZ 1.30 Exp (build 1.30.164014) — UI Architecture & Breaking Changes

### What changes in DayZ 1.30

1. **Widget type mutation in the interaction HUD (`day_z_hud.layout`)**:
   - `item` (`day_z_hud.layout:2294`), `interact` (:2477), `continuous_interact` (:2755), `single` (:3033), `continuous` (:3311), `ia_interact` (:4083), `ia_continuous_interact` (:4306) mutated from `ImageWidgetClass` to `PanelWidgetClass`.
   - They adopt the new style `style ActionWidget` (`looknfeel/dayzwidgets.styles:3700`), which renders a parametric 9-slice frame using `ActionWidgetGradient*` textures from the `dayz_gui` imageset.
2. **Modular action information and construction system on cursor (`ActionTargetsCursor.c`)**:
   - `ActionTargetsCursor` incorporates a decoupled supplementary panel pipeline (`TargetActionInfoPanelBase` and `ConstructionActionInfoPanel` in `ActionInfoPanels.c:82`) over `new_ui/hud/action_info_spacer.layout:1`.
   - Dynamically renders required tool grids (`ConstructionActionInfoToolsGrid`) comparing the `build_action_type` mask of the item in hands against `part.GetBuildIndicationTypeMask()`, and required materials (`ConstructionActionInfoMaterialsGrid`) in RichText format (`<color hex="...">X</color><color hex="...">/Y</color>`).
   - Decoupled icons from the inventory tree via `GenericIconBase: SlotsIconBase` (`GenericIcon.c:1`) over `new_ui/hud/SimpleIconTemplate.layout:1`.
3. **Visual dimming of unstartable actions**:
   - When `!action.CanBeStarted()`, button icons (`*_btn_icon` and `*_btn_icon_xbox`) reduce their opacity to `0.149` (`ActionTargetsCursor.c:1120-1121`).
4. **Deprecation of Xbox-specific controller methods**:
   - `SetInteractXboxIcon`, `SetContinuousInteractXboxIcon`, `SetSingleXboxIcon`, `SetContinuousXboxIcon`, `SetXboxIcon` marked as `[Obsolete("no replacement")]` (`ActionTargetsCursor.c:1368-1377`).
   - Replaced by `SetControllerIcon(string pWidgetName, string pInputName)` (`:146`), which renders dynamic RichText glyphs for any controller via `InputUtils.GetRichtextButtonIconFromInputAction(...)`.
5. **Architectural decoupling of `SlotsIconBase`**:
   - `SlotsIconBase: LayoutHolder` (`ContainedItems/SlotsIconBase.c:1`) absorbs 744 lines of generic inventory slot logic, reducing `SlotsIcon.c:1` to 217 lines of event registration.
6. **3D preview APIs in UI (`gameplay.c:276-314`)**:
   - `ItemPreviewWidget` incorporates `SetForceFlipEnable(bool)` and `SetForceFlip(bool)` (`gameplay.c:300-301`).
   - **Ticket T181406 refuted in script**: `WorldToScreen` and `ScreenToWorld` do NOT exist in 1.30 scripts (`[CHANGELOG]` / unexposed native). Nor does particle disabling in previews.
7. **Enfusion updates**:
   - Layout Editor updated to Enfusion 2023 (`changelog-1.30-exp-modding.md:64`).
   - Enfusion config parsing updated for `*.layout`, `*.emat` (`:23`).

### What breaks and how to migrate

| Breakage | Severity | Technical cause | How to migrate |
|---|---|---|---|
| `ImageWidget.Cast(m_Root.FindAnyWidget("interact"))` returns `null` | **CRITICAL** | Interaction widgets changed from `ImageWidgetClass` to `PanelWidgetClass` in `day_z_hud.layout:2294, 2477...` | Migrate variables and casting to `PanelWidget.Cast(...)` or `Widget`. For custom backgrounds use `w.SetStyle(...)` or modify the `ActionWidget` style. |
| Compilation warnings from obsolete Xbox methods | **MEDIUM** | `SetInteractXboxIcon` etc. marked `[Obsolete]` in `ActionTargetsCursor.c:1368` | Replace with `SetControllerIcon(widgetName, inputName)` (`ActionTargetsCursor.c:146`). |
| Slot modifications do not affect new cursor/HUD icons | **MEDIUM** | `SlotsIcon` is no longer the monolithic base class; `SlotsIconBase` was extracted and `GenericIconBase` was created | Mod/extend `SlotsIconBase` for slot logic or `GenericIconBase` for generic icons. |
| Assumption of `WorldToScreen` availability in previews | **LOW** | Ticket T181406 is not exposed in Enforce Script (`gameplay.c:276-314`) | Do not attempt to invoke `WorldToScreen`/`ScreenToWorld` on `ItemPreviewWidget`/`PlayerPreviewWidget` from script. |

### 1.30 migration checklist for UI developers

- [ ] Search across all mod code for `FindAnyWidget("interact")`, `"item"`, `"continuous_interact"`, `"single"`, `"continuous"`, `"ia_interact"` and replace `ImageWidget` with `PanelWidget`.
- [ ] Remove calls to `Set*XboxIcon` in scripts extending or modifying `ActionTargetsCursor`, adopting `SetControllerIcon`.
- [ ] If the mod decorated inventory slots, verify that extensions point to `SlotsIconBase` and retain calls to `super.InitIconWidgets` and `super.InitIcon`.
- [ ] For new cursor inspection panels, consult the modular architecture in `references/hud-action-info-panels.md`.
- [ ] Verify 9-slice style compatibility with the new `ActionWidget` style in `references/styles-format.md`.

### Detailed references for DayZ 1.30 Exp
- **Modular cursor panels and construction grids**: `references/hud-action-info-panels.md`
- **HUD mapping and inventory architecture**: `references/vanilla-menus-map.md`
- **Widget API catalog and verification**: `references/widget-api.md`
- **Style system specification (.styles)**: `references/styles-format.md`



