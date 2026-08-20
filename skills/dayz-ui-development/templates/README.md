# UI layout templates

Copy one of these, rename the widgets, put `#STR_` keys in your stringtable.
`stringtable.csv` here defines the seven keys the templates reference; copy its
rows into your addon's own `stringtable.csv` (addon root, next to `config.cpp`).
Without them the layouts render the key verbatim — `STR_UI_YES` instead of `Yes`
— which reads as a broken template, and the engine logs **nothing** about it
(measured 2026-08-20: zero RPT lines for `STR_UI_`). Note the CSV carries the key
without the leading `#`; the `#` belongs only to the reference in the layout.
A stringtable is addon-level: it is read from the PBO at load, so unlike a
`$profile:` layout it does not hot-reload.

`Message` in `modal_panel.layout` renders with a very large glyph because its box is
0.58 of a 0.70-tall panel — 292 px at 720p — and glyph height was measured to track the
widget height. `text_proportion` is honoured on `TextWidgetClass` and `ButtonWidgetClass`
(glyph = 0.74 x value x box height, measured to within 2% on 2026-08-21) and **ignored on
`MultilineTextWidgetClass`**, which is why the six-value sweep of 2026-08-20 moved nothing.
On a multiline, size the box; the attribute is not the lever. Numbers and controls:
`../references/hot-iteration.md` section 6.
Iterate from `$profile:` with `ui_reload_layout` — the loop is in
[`../references/hot-iteration.md`](../references/hot-iteration.md).

The sibling `*.rects.1920.json` / `*.rects.1280.json` are the offline
prediction at those resolutions. Compare a live `ui_tree` / `ui_reload_layout`
against them. Perfect rects do not prove anything is drawn.

| File | Use when | Do not use when |
|---|---|---|
| `modal_panel.layout` | Confirm / yes-no / blocking prompt, centred | Persistent HUD, a form (see `form_row`), a list (see `scroll_list`) |
| `hud_overlay.layout` | A corner readout that must not steal the mouse | Anything clickable, a menu, a modal |
| `form_row.layout` | One label + `EditBoxWidget`, stacked by parenting copies | A finished dialog (compose it into `modal_panel`) |
| `scroll_list.layout` | A viewport whose content is taller than the box | A short fixed list (just a `GridSpacerWidget` with no `ScrollWidget`) |

## Offline gate (tool in this pack)

```
python tools/dayz-ui-lab/dayz_ui_lab/parse.py skills/dayz-ui-development/templates/<this.layout> --check
python tools/dayz-ui-lab/dayz_ui_lab/parse.py skills/dayz-ui-development/templates/<this.layout> --canvas-width 1920 --canvas-height 1080
python tools/dayz-ui-lab/dayz_ui_lab/parse.py skills/dayz-ui-development/templates/<this.layout> --canvas-width 1280 --canvas-height 720
```

`--check` is a parse/structure gate (OK + widget count). It is not a geometry
lint. The JSON dump is the pack parser's geometry, including `right_ref` /
`bottom_ref` (inward subtraction, `parse.py:790-803`).

## `ui_rect_lint.py` is not distributed with this pack

It lives in the author's DayZ_Tooling / vault, not here. The sibling `.rects`
files were produced by its `predict`. If you have it:

```
python ui_rect_lint.py lint --layout <this.layout> --res 1920x1080 --expect-visible <names>
python ui_rect_lint.py predict --layout <this.layout> --res 1920x1080 --out <this>.rects.1920.json
python ui_rect_lint.py predict --layout <this.layout> --res 1280x720  --out <this>.rects.1280.json
```

`--expect-visible` names for these four:

| File | `--expect-visible` |
|---|---|
| `modal_panel.layout` | `BtnYes,BtnNo` |
| `hud_overlay.layout` | `HudBadge,HudIcon,HudLabel,HudValue` |
| `form_row.layout` | `RowEdit` |
| `scroll_list.layout` | `ScrollListPanel,ScrollList,ScrollContent` |

Without `--expect-visible`, `ui_rect_lint.py:302-306` restricts `targets` to
clickable types (`CLICKABLE_TYPES`, `:32-39`): Button, EditBox, CheckBox,
Slider, Combo. `R5-zero-size`, `R6-off-screen` and `R7-overlap` then only look
at those. `hud_overlay` (Panel + Image + 2 Text) and `scroll_list` (Panel +
Scroll + Spacer) have none.

**`CLEAN` on `hud_overlay` and `scroll_list` means *not measured*, not *passes*.**
Someone who copies `hud_overlay`, moves the badge off-screen, sees `CLEAN`, and
deploys, has not been certified. `--expect-visible` is what forces those
widgets into `targets`. Predicted-only lint also does not evaluate R1/R2/R3 —
those need a `ui_tree` capture.

On `hud_overlay` the whole tree is `ignorepointer 1` (HUD must not steal aim).
`--expect-visible HudBadge` therefore always reports `[R4-ignore-pointer]` on a
correct copy — that is the pass-through contract, not a geometry fail. R5 and
R6 are the rules that mutation actually kills.

`scroll_list` reports two findings on a correct copy as well: `[R4-ignore-pointer]`
and `[R5-zero-size]`, both on `ScrollContent`. The spacer is authored at height 0
and the engine grows it at runtime (`"Size To Content V" 1`), so a zero box there is
the contract, not a defect. **Do not "fix" it by giving the spacer a height** — that
reintroduces trap 4. R5 still earns its keep on this template: it is what kills the
mutation that sets the panel itself to `size 0 0`.

Files cited from outside this pack (not distributed): `mcp_dialog.layout`,
`cable_hud.layout`, `LFPG_TankHUD.layout`. Vanilla cites are under
`P:\gui\layouts\` (and `gui/looknfeel/dayzwidgets.styles`).

## The four construction traps

These are the defects the templates exist to stop you paying in deploys.
Each one has a style or attribute that *looks* right and is not.

### 1. Invisible panel

**Symptom.** Widget tree is correct, rects match, `ui_tree` color is correct,
the panel is not on screen. Text floats over the world.

**Cause.** `PanelWidgetClass` paints only through a style whose `Normal`
`Center` image is non-empty. The name is scoped per widget type.

| Style | Type it belongs to | What `Normal` draws |
|---|---|---|
| `Colorable` | `WindowWidget` (`gui/layouts/dialog.layout:16`) | WhitePixel (window) |
| `ColorablePanel` | `PanelWidget` (`dayzwidgets.styles:3327`) | `Center=""` — nothing |
| `rover_sim_colorable` | `PanelWidget` (`dayzwidgets.styles:3223`) | `Center="WhitePixel"` |

Vanilla uses `rover_sim_colorable` on panels **577 times**. `ColorablePanel`
exists and is the wrong guess. Existence is not enough; open
`gui/looknfeel/dayzwidgets.styles`, find `<Widget Name="PanelWidget">`, and
read the `Center` image. Detail: [`../references/styles-format.md`](../references/styles-format.md).

### 2. Title clipped on both sides

**Symptom.** A centred title longer than the box loses characters on the left
*and* the right.

**Cause.** `TextWidgetClass` + `"text halign" center` + no wrap. `text_proportion`
sizes by **height**; it does not fit a long string horizontally.

**Fix in these templates.** `MultilineTextWidgetClass` + `wrap 1`
(329/331 vanilla MultilineText). `wrap` on `TextWidgetClass` is **0×** in the
214 vanilla files and is **[UNVERIFIED]** at runtime — do not rely on it.

### 3. White button, white label

**Symptom.** An `EmptyHighlight` button is fine until it is focused; then the
body fills white and the label disappears.

**Cause.** `ButtonWidget/EmptyHighlight` `Focus` `Center="WhitePixel"`
(`dayzwidgets.styles:2232`). Default label is white. Without a body `color`
the pixel stays white.

**Fix in these templates.** `color 1 0 0 1` (body, not `"text color"`) +
`inheritalpha 0`, copied from `gui/layouts/dialog.layout:31-42` and
`mcp_dialog.layout` (not distributed). 14/28 vanilla `EmptyHighlight` buttons
set `inheritalpha 0`.

### 4. List does not scroll

**Symptom.** Content is taller than the box; the wheel does nothing; no bar.

**Cause.** `ScrollWidgetClass` with no spacer child. Vanilla first-child of
51 scroll hosts: `GridSpacer` 23, `WrapSpacer` 10, `Panel` 9, `Frame` 4.

**Fix in these templates.** Direct child `GridSpacerWidgetClass` with
`size 1 0`, `vexactsize 1`, `"Size To Content V" 1` — copied from
`gui/layouts/new_ui/options/keybindings_selectors/keybinding_container.layout:35-54`.
That vanilla spacer has **no children in the file**; script fills it at
runtime. Same here. Do not author sample rows under it.

## Hot-iteration traps (runtime, not authoring)

The four measured failures of the `$profile:` loop live in
[`../references/hot-iteration.md`](../references/hot-iteration.md) §4:
missing path kills `CreateWidgets`; a second load stacks; a missing texture
paints flat white and logs nothing; perfect rects say nothing about paint.
End every loop with a frame.

## What these files are not

They are not in-game verified. The pack parser is offline format + geometry.
Ship them through `ui_reload_layout` and look at the frame before you trust a
colour or a wrap.
