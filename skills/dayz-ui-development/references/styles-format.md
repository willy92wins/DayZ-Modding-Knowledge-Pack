# DayZ .styles System — Complete Reference (dissected from vanilla ground truth)

Added 2026-07-04. Source: full parse of `gui\looknfeel\dayzwidgets.styles` (4,462 lines, 28 widget
types, 130 styles) cross-checked against all 214 vanilla `.layout` files, plus the LBmaster_Core
shipped-mod example and `enwidgets.c` protos. Every stat independently reproduced by an adversarial
verify pass (scripts `styles_audit.py` / `verify_styles_claim.py`, session scratchpad 2026-07-04).
This resolves the skill's former largest known-unknown (`style` = 3rd most common layout attribute).

## 1. How a layout selects a style

- Attribute: `style NAME` — **always unquoted, one token** (3,134 occurrences across the 214 vanilla
  layouts; zero quoted forms exist).
- The engine maps the layout widget class to the styles-file `<Widget Name>` by **stripping the
  `Class` suffix**: `TextWidgetClass` → `<Widget Name="TextWidget">`. Under this mapping **all 3,134
  vanilla refs resolve — zero dangling** (mechanism corroborated by the perfect data-side
  correspondence; not traced in engine binaries).
- **Style names are SCOPED to their widget type**: `TextWidget` has `Normal`/`Bold` while
  MultilineText/RichText/Html use `DayZNormal`/`DayZBold` — the same name can mean different things
  under different widget types, and a style must be declared under EVERY widget type that uses it.
- **Default when `style` is omitted: UNKNOWN offline** `[verify in-game]`. 4,000+ vanilla widgets
  omit it (192 text widgets ship with neither `style` nor `font`), so an engine fallback exists, but
  nothing in scripts names it. `Widget.GetStyleName()` (`enwidgets.c:133`) can settle it in-game.
- Runtime API is read-only + load-only: `GetStyleName()` getter and global
  `LoadWidgetStyles(string filename)` (`enwidgets.c:693`). There is **NO SetStyle/SetStyleName** —
  a widget's style cannot be changed at runtime; plan state changes via styles' own State system or
  script SetColor/Show.

## 2. File format

```xml
<WidgetStyles>
    <Widget Name="PanelWidget">                                   <!-- widget TYPE (class minus 'Class') -->
        <Style Name="MyStyle" Font="gui/fonts/MetronBook" ImageSet="my_set" Color="4294967295">
            <State Name="Normal">
                <Item Name="Center" Image="SomeImagesetImage" />  <!-- 9-slice items -->
            </State>
        </Style>
    </Widget>
</WidgetStyles>
```

- **Color** = decimal packed 32-bit color; `4294967295` = 0xFFFFFFFF opaque white (82% of styles,
  105/128). Every non-white value in the vanilla file is a transparency setting (alpha byte 0x00),
  not a hue.
- **Font** accepts two forms: size-suffixed atlas (`gui/fonts/sdf_MetronLight24`) or **size-less
  family** (`gui/fonts/MetronBook`) resolved via `gui/fonts/<family>.xml` `fontGenerator` descriptors
  that enumerate the baked sizes.
- **ImageSet** + each Item's **Image** refer to the imageset's registered NAME (line-2 `Name` field
  of the `.imageset`) and an image Name inside it — never file paths. Vanilla styles use 6 sets:
  `dayz_gui` (85 styles), `rover_imageset` (18), `ccgui_enforce` (14), `empty` (9), plus 2 minor.
  A mod style may freely reference a vanilla imageset.
- Empty `Image=""` on a slice/state is presumed to draw nothing (consistent with vanilla data;
  engine behavior inferred, not tested).

## 3. State vocabulary (complete — nothing else exists in the vanilla file)

`Normal, Pushed, Highlight, Focus, Disabled, Mark, Checked, Crossed, Empty`

- There is **NO 'Hover'** (mouse-over = `Highlight`) and **NO 'Pressed'** (= `Pushed`).
- Per widget kind:
  - **ButtonWidget** = Normal/Pushed/Highlight/Focus/Disabled
  - **XComboBoxWidget** = Normal/Focus/Highlight/Disabled
  - **listbox family + EditBox/PasswordEditBox/Slider** = Normal/Focus/Disabled
  - **MultilineEditBoxWidget** = Normal/Focus ONLY (no Disabled)
  - **ProgressBar/SimpleProgressBar/Window/Panel/SmartPanel/Scroll/GridSpacer/WrapSpacer** =
    Normal/Disabled only
  - **CheckBoxWidget** = Normal/Disabled/Mark(=checked, Image "MarkDone")/Highlight
  - **ThreeStateCheckboxWidget** = Checked/Crossed/Empty/Disabled/Highlight (no Normal)
  - **graph widgets** (4) = Normal only
  - **TextWidget/MultilineText/RichText/Html** = no `<State>` blocks at all (font+color only,
    self-closing `<Style/>`)

## 4. Item-name contracts per widget type (the 9-slice system)

Base 9-slice: `LeftTop/Top/RightTop/Right/RightBottom/Bottom/LeftBottom/Left/Center` — exactly the
set for ButtonWidget, EditBoxWidget, PasswordEditBoxWidget, PanelWidget, ScrollWidget,
GridSpacerWidget, WrapSpacerWidget and the 4 graph widgets.

Extensions:
- **ProgressBarWidget** = 9 + a `Bar*` mirror of all 9 (18 items; Default style: `Center` = trough
  image, `BarCenter` = fill image, frame slices empty).
- **SimpleProgressBarWidget** = ONLY the `Bar*` 9-set.
- **SliderWidget** = frame 9 + `Bar*` 9 (18).
- **WindowWidget** = 9 + a `Title*` mirror of all 9 (18) for the title bar.
- **XComboBoxWidget** = 9 + `ArrowLeft` + `ArrowRight` (11).
- **SmartPanelWidget** = 9 + `Overlay` (10).
- **CheckBoxWidget / ThreeStateCheckboxWidget** = a single Item named `CheckBox`.
- **MultilineEditBoxWidget** = a single Item named `Highlight` (text-selection highlight). NOTE: the
  single-line EditBoxWidget style has NO Highlight item — plain 9-slice border only.
- **Listbox family** (GenericListbox/UniversalListbox/ServerBrowser/TextListbox) = identical 31-item
  union: 9-slice with `*Center` edge naming (`TopCenter/BottomCenter/LeftCenter/RightCenter`) +
  `Header*` 9-set + `TitleLeftCenter/TitleCenter/TitleRightCenter` + `TitleCenterSeparator` +
  `Separator/TopSeparator/BottomSeparator` + `ScrollBarTop/ScrollBarCenter/ScrollBarBottom` +
  `Highlight` + `LeftTopWithTitle/RightTopWithTitle`.

## 5. The 'Colorable' mechanism (why script SetColor works on styled widgets)

`ButtonWidget/Colorable` (`dayzwidgets.styles:2163-2219`): `Color="0"` + `Center Item = "WhitePixel"`
(a 1×1 white region, `rover_imageset.imageset:11-14`) in **all 5 states** → the widget renders a
white pixel that script `SetColor(ARGB)` then tints. **This is the verified mechanism behind the
skill fact "ButtonWidget.SetColor() works directly, no LoadImageFile needed"** — it holds for styles
whose Center is a white/colorable image (the WhitePixel Center is the load-bearing part;
`WindowWidget/Colorable` keeps Color=white and is still colorable via its WhitePixel Center).

Also style-driven for free: ButtonWidget/Default overlays `alpha_176` on Pushed, `alpha_128` on
Focus, `alpha_64` on Disabled (`:1613/:1635/:1646`) — **picking `style Default` on a button gives
working press/focus/disabled visual feedback with zero script**.

## 6. Style inventory (what exists to pick from — most-used names)

28 widget types have styles; **ImageWidget and FrameWidget have NO entry** (never styleable).
Top vanilla usage: `PanelWidget/rover_sim_colorable` 577×, `GridSpacerWidget/DayZDefaultPanel` 455×,
`PanelWidget/blank` 210×, `TextWidget/Normal` 174×, `ButtonWidget/Colorable` 174×.

Highlights per type (full inventory in the styles file itself):
- TextWidget: `Normal, Bold, Light, None` · MultilineText/RichText/Html: `DayZNormal, DayZBold`
- ButtonWidget (22): `Default, Colorable, Empty, EmptyHighlight, MainMenu, MenuDefault, Editor,
  InventoryActionMenu, OldStyle, DayZDefaultButton(+NoBorder/Bottom/Sides/Top/All/_DisabledState),
  DayZInventoryButton(All/Top/Bottom/Right/Left)`
- PanelWidget (21): `rover_sim_colorable, blank, Outline, ColorablePanel, editor_quad,
  editor_quad_dark, dashed, DayZDefaultPanel(+Left/Right/Top/Bottom/Sides), ToolbarWidget,
  UIDefaultPanel, rover_sim_black(_2), InventoryPanel, EditorPanel, editor_selection`
- ProgressBarWidget: `Default, DayZLoading, Stamina, Quantity, Loading`
- Styles exist for XComboBox/SmartPanel/Html/ThreeStateCheckbox/graph widgets too — the 4 graph
  widgets are the only types with styles but zero vanilla layout instantiation.

## 7. Custom-style recipe (production-proven, LBmaster_Core)

1. **File** `<ModDir>/gui/styles/<name>.styles` — one `<Widget>` block PER TARGET WIDGET TYPE (the
   style must be declared separately under each type it will be used on; LBmaster declares
   `LB_Clean_outline` twice: under PanelWidget AND GridSpacerWidget, `lbstyles.styles:2-27/28-53`).
   The outline-only trick: Normal state sets the 8 border slices to `Image="pixel"` and
   `Center=""`.
2. **Registration** in `config.cpp` inside `CfgMods > <ModName> > class defs`:
   ```cpp
   class widgetStyles { files[] = {"LBmaster_Core/gui/styles/lbstyles.styles"}; };
   class imageSets    { files[] = {"LBmaster_Core/gui/imagesets/lb_core_set.imageset"}; };
   ```
   (prefix-relative path, no leading slash). **An unregistered .styles file is inert** —
   LBmaster_Groups ships a dead `customStyles.styles` with no registration and no refs: anti-example.
3. **Usage**: `style LB_Clean_outline` on matching widget classes in the mod's layouts.
   Registration is **global**: LBmaster_Groups uses the style registered by its Core dependency
   (requiredAddons) without registering anything itself.
4. **Merge semantics**: a mod `.styles` file ADDS styles to existing vanilla widget types —
   additive merge with `dayzwidgets.styles`, not replacement (evidenced by shipped layouts mixing
   `LB_Clean_outline` and vanilla `rover_sim_colorable` in the same file; runtime semantics inferred
   from shipped-mod structure). Custom styles may reference vanilla fonts and imagesets.
5. **Workbench preview**: also register the .styles/.imageset in `dayz.gproj` or the Layout Editor
   renders them blank — see `plan-to-implementation.md §3` (dual registration).

## 8. Practical guidance

- Building a themed panel/button UI? **Reach for a style before hand-composing Image+Text widgets**:
  a 9-slice style gives borders, state feedback (press/focus/disabled) and script-tintability
  (WhitePixel Center + SetColor) declaratively.
- Debugging "my style does nothing": (1) is the style declared under THIS widget's type (Class-suffix
  stripped)? (2) is the .styles file registered in `config.cpp class defs > widgetStyles`? (3) does
  the ImageSet name (not filename) resolve? (4) for Workbench preview, is it in dayz.gproj?
- The HTML renderer (`build_viewer.py`) does NOT resolve styles — styled widgets preview as
  invisible/plain. Note it in the spec and rely on in-game verification for styled chrome.


---

## Before writing `style X`, check the block of THAT widget type (measured 2026-08-19)

The style namespace is **per widget type**, and a name borrowed from another
type fails **silently**: no load error, no warning, no log line. The widget
simply has no ImageSet to tint, so its `color` never paints and you get text
floating over the game world.

Real case, cost a full in-game session to notice and a human to see it:
`MCPDialogPanel` is a `PanelWidgetClass` and declared `style Colorable`.

- `<Widget Name="WindowWidget">` DOES declare `Colorable` (6 styles: Default,
  rover_sim_black, rover_sim_black_2, Colorable, Simple, debugUI).
- `<Widget Name="PanelWidget">` declares 21 styles and **none** is `Colorable`;
  its equivalent is `ColorablePanel`.

So the name was real, the layout looked plausible, vanilla itself uses
`style Colorable` on `gui\layouts\dialog.layout:1-16` — but that is a
`WindowWidgetClass`. Same word, different type, nothing painted.

**The check is mechanical:** open `gui\looknfeel\dayzwidgets.styles`, find
`<Widget Name="<YourWidgetType>">`, confirm the style name is inside THAT block.
Having seen the name in another working layout proves nothing.

**And grep the XML as XML.** This file is `<WidgetStyles><Widget Name=...>
<Style Name=... ImageSet=.../>`. A grep written for the brace format returns
zero hits and reads as "that style does not exist anywhere" — a false negative
that sounds like an answer.
