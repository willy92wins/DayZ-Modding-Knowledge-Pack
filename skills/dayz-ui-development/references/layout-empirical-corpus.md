# DayZ `.layout` — Empirical Corpus + Renderer Reference

Added 2026-05-13. Append-only. Source: full grep of 459 `.layout` files in `P:\`
+ verification of Dabs Framework against `production` branch HEAD on 2026-05-13.

This file complements (does not replace) `layout-format.md`, `widget-api.md`,
`dabs-framework.md`. Use it when you need:

- "What's actually used in production layouts?" → see §1 + §2.
- Path/branch corrections vs the older clone snapshot → see §3.
- The static HTML renderer for previewing layouts outside DayZ → see §4.
- Second-sweep calibrations (819 files, 2026-08-19) → see §6.

---

## 1. Widget class frequency (from 459 `.layout` files in P:\)

```
2645 TextWidgetClass
2090 PanelWidgetClass
2072 ImageWidgetClass
1341 FrameWidgetClass
1325 ButtonWidgetClass
1160 GridSpacerWidgetClass
 508 EditBoxWidgetClass
 446 CheckBoxWidgetClass
 351 MultilineTextWidgetClass   ← not previously catalogued
 294 WrapSpacerWidgetClass
 244 RichTextWidgetClass
 133 TextListboxWidgetClass     ← not previously catalogued
 129 SliderWidgetClass
  95 ScrollWidgetClass
  81 XComboBoxWidgetClass
  66 WindowWidgetClass          ← not previously catalogued
  65 ItemPreviewWidgetClass
  54 ProgressBarWidgetClass
  29 CanvasWidgetClass
  20 ContentWidgetClass         ← not previously catalogued, use unclear
  17 SpacerWidgetClass
  16 MapWidgetClass
  10 ThreeStateCheckboxWidgetClass  ← variant of CheckBox
   9 MultilineEditBoxWidgetClass
   5 VideoWidgetClass
   5 PlayerPreviewWidgetClass   ← not previously catalogued
   3 SmartPanelWidgetClass      ← not previously catalogued, use unclear
   3 EmbededWidgetClass         ← (typo of Embedded?) not previously catalogued
   2 HtmlWidgetClass            ← not previously catalogued
   1 ServerBrowserWidgetClass   ← not previously catalogued
   1 PasswordEditBoxWidgetClass ← variant of EditBox with masked input
```

### Renderer coverage decisions

- **v1 must-have:** TextWidgetClass, ImageWidgetClass, FrameWidgetClass,
  PanelWidgetClass, ButtonWidgetClass, GridSpacerWidgetClass,
  WrapSpacerWidgetClass, ScrollWidgetClass, EditBoxWidgetClass — 9 classes
  cover 89% of widget instances in the corpus.
- **v2 should-have:** CheckBoxWidgetClass, MultilineTextWidgetClass,
  RichTextWidgetClass, SliderWidgetClass, XComboBoxWidgetClass,
  TextListboxWidgetClass — adds ~10% more coverage.
- **v3 defer:** ItemPreviewWidgetClass, MapWidgetClass, PlayerPreviewWidgetClass,
  CanvasWidgetClass, VideoWidgetClass, HtmlWidgetClass — these render game
  state, not parseable from `.layout` alone.

---

## 2. Attribute frequency (top 50, across 300 sampled layouts)

```
10349 size                hexactsize/vexactsize toggle units
10302 vexactsize          0=fraction, 1=pixels
10256 hexactsize          0=fraction, 1=pixels
10242 vexactpos           0=fraction, 1=pixels
10242 hexactpos           0=fraction, 1=pixels
 7778 position
 7494 ignorepointer       1=transparent to mouse
 4518 valign              top|center|bottom|*_ref|0|1|2
 4173 visible
 4157 halign              left|center|right|*_ref|0|1|2
 3412 style               ← ref to widgetStyles.xml; renderer best-effort
 3210 text
 3074 color               R G B A floats 0-1
 2833 clipchildren        1=overflow:hidden equiv
 2350 font
 1697 mode                ← blend mode; values 0/1/2 observed
 1440 priority            ← z-order hint; renderer can sort by this
 1360 image0              path or "#(argb,8,8,3)color(R,G,B,A,CO)"
 1329 Margin              GridSpacer/WrapSpacer outer margin px
 1322 Padding             GridSpacer/WrapSpacer inner padding px
 1129 inheritalpha        1=multiply with parent alpha
 1069 Rows                GridSpacer rows
 1060 Columns             GridSpacer columns
  939 scaled              resolution scaling toggle
  884 draggable           enables DRAGGABLE flag
  756 filter              texture filtering
  694 content_valign      inside-spacer alignment
  591 content_halign
  505 wrap                word wrap on text widgets -- NOT a WrapSpacer mode
  NOTE (2026-08-19): the "WrapSpacer wrap mode" label on this line was wrong, and
  the 505 is a 300-layout sample. Two independent censuses over the full 819-layout
  corpus -- one with the tooling tokenizer plus a widget stack, one with a separate
  header rule -- agree that `wrap` sits on text widgets and on ZERO spacer widgets:
  MultilineText ~355, RichText 236, Html 9, Text 4. Restricting the same census to
  the `gui\` subtree reproduces this line's 505, which is what identifies the two
  numbers as the same attribute over different populations.
  489 scriptclass         "ViewBinding" or custom controller class
  467 userID              int ID for script-side lookup
  461 fixaspect           image aspect ratio lock
  437 text_proportion     text size as fraction of widget height (0-1)
  NOTE: 437 is this §2 sample (2026-05-13, 300 layouts). It is NOT the 1048 from the 819-file sweep (2026-08-19) in layout-format.md (679 Text + 361 Button + 5 RichText + 3 MultilineText). Keep both; they are different corpora.
  376 nocache             skip texture cache
  333 (other widget classes)
  317 disabled            DISABLED flag
  268 (other)
  258 stretch             1 = STRETCH flag, image fills widget
  173 imageTexture        alt to image0
  163 keepsafezone        respect TV-safe margins
  154 Progress            ProgressBarWidget initial value
```

### Newly documented attributes (semantics inferred from corpus + community wiki)

| Attribute | Semantics | Confidence |
|---|---|---|
| `style "<name>"` | Reference to a widget style defined in `widgetStyles.xml`. Common values: `Bold`, `DayZNormal`, `DayZInventoryButtonAll`, `Default`, `Empty`, `Colorable`, `Editor`. | Verified empirically. Engine-side semantics inferred. |
| `mode 0\|1\|2` | Image blend mode. 0=normal, 1=additive(?), 2=multiply(?). | Inferred from typical engine patterns. Not engine-verified. |
| `priority N` | Z-order hint within parent. Higher = on top. | Inferred. `SetSort` API does similar but additively. |
| `image0` ... `image7` | Image slot 0–7 (engine supports 8 textures per widget via `LoadImageFile(int num, ...)`). `image0` is default; switched with `SetImage(int)`. | Engine API confirms 8 slots. |
| `inheritalpha 1` | If 1, widget's alpha is multiplied with parent's. | Common in HUDs; verified empirically. |
| `scaled 1` | Resolution scaling enabled (uses `Widget.SetResolutionScale`). | Inferred. |
| `fixaspect 1` | Lock image aspect ratio (don't stretch). | Inferred from naming. |
| `keepsafezone 1` | Respect TV-safe margins (console builds). | Inferred from naming. |
| `text_proportion 0.5` | Text size as fraction of widget height (0–1). Verified in engine API as `SetTextProportion(float)`. | [ENGINE-API verified] |
| `nocache 1` | Skip texture cache. Useful for procedural images. | Inferred from naming. |

---

## 3. Dabs Framework — path/branch correction (verified 2026-05-13)

**Previous skill state** (`dabs-framework.md`, clone from 2026-03-23):
- Path: `DabsFramework/scripts/3_Game/MVC/`
- Branch: `master` assumed

**Verified at production HEAD 2026-05-13 via WebFetch on raw.githubusercontent.com:**
- **Path:** `DabsFramework/Scripts/3_Game/DabsFramework/MVC/` (note capitalized `Scripts`, and the extra `DabsFramework/` segment)
- **Branch:** `production`

**Verified file:line citations at 2026-05-13:**

| Fact | File | Line |
|---|---|---|
| `class ViewBinding : ScriptedViewBase` | ViewBinding.c | 1 |
| `reference string Binding_Name;` | ViewBinding.c | 4 |
| `reference string Selected_Item;` | ViewBinding.c | 7 |
| `reference bool Two_Way_Binding;` | ViewBinding.c | 10 |
| `reference string Relay_Command;` | ViewBinding.c | 13 |
| `OnWidgetScriptInit` method body | ViewBinding.c | 40-50 |
| `class ScriptView : ScriptedViewBase` | ScriptView.c | 39 |
| `static ref array<ScriptView> All` | ScriptView.c | 41 |
| ScriptView constructor body | ScriptView.c | 45-98 |
| `CreateWidget(null)` call | ScriptView.c | 55 |
| `LoadWidgetsAsVariables(this, m_LayoutRoot)` (first call) | ScriptView.c | 60 |
| `m_LayoutRoot.GetScript(m_Controller)` | ScriptView.c | 62 |
| `GetControllerType().Spawn()` | ScriptView.c | 74 |
| `LoadWidgetsAsVariables(m_Controller, m_LayoutRoot)` (second) | ScriptView.c | 81 |
| `m_Controller.OnWidgetScriptInit(m_LayoutRoot)` | ScriptView.c | 84 |
| `UseUpdateLoop()` check + queue insert | ScriptView.c | 90-92 |
| ScriptView destructor body | ScriptView.c | 100-125 |
| `NotifyPropertyChanged` body | ViewController.c | 80-110 (approx) |
| `m_DataBindingHashMap[property_name]` lookup | ViewController.c | ~105 |

**`Debug_Logging` field:** mentioned in some older docs but NOT visible in the
first 60 lines of `ViewBinding.c` on 2026-05-13. Treat as unverified — may have
been removed or never existed. Don't recommend without re-checking.

**URL pattern** (production branch):
```
https://raw.githubusercontent.com/InclementDab/DayZ-Dabs-Framework/production/DabsFramework/Scripts/3_Game/DabsFramework/MVC/<FileName>.c
```

---

## 4. Static HTML renderer (preview without DayZ)

A Python renderer that converts `.layout` files to static HTML+CSS preview
lives at:

```
<notes>\DayZ_UI_Research\renderer\dayz_layout_render.py
```

### Usage

```
python dayz_layout_render.py <input.layout> [output.html]
```

Open the resulting `.html` in any browser.

### Coverage

| Aspect | Handled | Notes |
|---|---|---|
| 9 core widget classes | ✓ | Frame/Image/Text/Button/EditBox/Scroll/Grid/Wrap/Panel |
| Geometry (pixel + fractional) | ✓ | Both hexactpos/size modes, halign/valign anchors |
| Color attribute (R G B A floats) | ✓ | Renders as rgba() background or text color |
| Procedural color images `#(argb,...)color(...)` | ✓ | Detected and emitted as flat CSS color |
| Real PAA texture references | ⊘ | Not in v1 — reuse PAA decoder from `dayz-3d-viewer` skill |
| `text "..."` literal text | ✓ | Including `#STR_KEY` → `[loc:#STR_KEY]` placeholder |
| Dabs `scriptclass "ViewBinding"` | ✓ | Skipped visually; binding name shown as `{Name}` placeholder when widget has no literal text |
| `ScriptParamsClass { ... }` metadata | ✓ | Skipped visually |
| `Relay_Command` | ✓ | Surfaced as `[→ Name]` badge overlay |
| Font weight (Metron vs MetronBook) | ✓ | Mapped to CSS font-weight 600 vs 400 |
| Text alignment (`text halign` / `text valign`) | ✓ | Mapped to CSS text-align + flex |
| `clipchildren` | ✓ | CSS `overflow: hidden` |
| `ignorepointer` | ✓ | CSS `pointer-events: none` |
| `visible 0` | ✓ | CSS `display: none` |
| Animations / WidgetAnimator | ⊘ | Out of v1 — static preview only |
| Live binding data | ⊘ | Bindings shown as placeholders, no runtime resolution |
| ItemPreview / MapWidget / PlayerPreview | ⊘ | Need game state |
| `style` attribute → widgetStyles.xml | ⊘ | Defer until we can read widgetStyles |

### Test cases (rendered successfully on 2026-05-13)

```
LFPG_Sorter.layout              (2470 lines, 196 widgets) ✓
LFPG_SorterPreviewRow.layout    (109 lines, 10 widgets)   ✓
LFPG_SorterTag.layout           (76 lines, 6 widgets)     ✓
BaseBuildingPlus/Book.layout    (3rd-party)                ✓
CodeLock/enterComboCode.layout  (3rd-party)                ✓
A6_Gunplay/ItemStatsDisplay     (3rd-party)                ✓
```

### Output features (in HTML)

- **Theme toggle** (default ON): applies sensible default colors when the layout
  omits explicit `color` attrs (DayZ mods typically set colors via script
  `SetColor()` at runtime, not in `.layout`).
- **Debug outlines toggle:** colored dashed outlines per widget type.
- **Binding badges:** small overlays showing binding name / relay command.
- **Hover info:** bottom-right shows widget type, name, position, size.

### Renderer limitations to document

1. **Pixel-perfect color match impossible.** Mods apply colors via script
   `SetColor(ARGB)` after `CreateWidgets`. The renderer cannot statically infer
   what those colors are. Theme mode is best-effort approximation by widget
   name patterns (PanelBg, HeaderBg, etc.).
2. **Font fallback.** DayZ uses Bohemia's proprietary Metron font. Renderer
   uses Bahnschrift / Roboto Condensed / Arial Narrow as fallbacks. Widget
   spacing will differ ~5%.
3. **No script-side recalculation.** Widgets resized/repositioned at runtime
   (e.g. `RecalculateLayout` in `dayz-ui-development` advanced-patterns §1)
   won't update in the preview.
4. **`style` attribute ignored.** Reading widgetStyles.xml is a separate task.

---

## 5. When to expand v1 → v2

Trigger expansion when:

- You start using widgets not in the 9-core set on a regular basis.
- You want to preview a vanilla DayZ menu (which uses `style` references
  heavily — needs widgetStyles.xml parsing).
- You need RichText inline `<image>` / `<font>` tag rendering.
- You want to preview MultilineTextWidget content layout (line breaks).

For each expansion, follow the same discipline:
1. Add empirical corpus check for new attribute usage.
2. Verify against engine API doc (`widget-api.md` is engine-protos derived).
3. Test on at least 1 LFPG layout + 1 third-party layout.

---

*End. Append-only; do not edit existing references.*


---

## 6. Second sweep: 819 `.layout` files (2026-08-19)

Plugin source numbered this heading as §5; the existing “When to expand v1 → v2”
section already occupies §5, so the harvest uses §6. Body unchanged.

Re-measured with a token parser over every `.layout` reachable from
`<dayz-projects>\` (vanilla + third-party + ours), not only `P:\`. Purpose was
calibrating a geometry gate, so the numbers below are about what is NORMAL in
shipped layouts — which is what decides whether a rule is a detector or a
false-positive generator.

- **Corpus**: 819 files. A brace-format token parser reads **807 (98.5%)** with
  zero exceptions; the 12 that yield no widget are the XML dialect that
  `LAYOUT-XML-FORMAT` already owns. A naive line-based parser managed 469 (57%)
  — the difference is `ScriptParamsClass` blocks (277 files), `{}` on one line
  (45) and children opening on their own line.

- **Two clickable siblings whose rects OVERLAP: 884 cases across 32 files,
  vanilla included.** Stacking widgets that a script toggles is standard
  authoring. Narrowing to "both declared `visible 1`" only drops it to 768, and
  "identical rect" to 677. **Conclusion: overlap is not a file-level defect.**
  It only means something with runtime `visible_hierarchy`, i.e. on a `ui_tree`
  capture — never on the file alone.

- **A child overflowing its parent's box: 18 cases / 12 files, deliberate.**
  Vanilla's `compassimage` is 4.0 wide; `details_mode_result` is 6.0 tall
  (scrollable content). Not a defect either.

- **Duplicate widget name: 5 files (0.6%); duplicate name where at least one is
  clickable: 1 file (0.1%)** — vanilla's `scene_editor`. Rare enough to be a
  real signal, and it is the one that breaks automation, because
  `FindAnyWidget` resolves by name and returns one match.

- **Class identifier vs the `name` attribute: 0 mismatches in 819 files.** The
  corpus keeps them equal without exception.

These calibrations are wired as `LAYOUT-DUPLICATE-CLICKABLE-NAME`,
`LAYOUT-CLICKABLE-ZERO-SIZE`, `LAYOUT-DUPLICATE-WIDGET-NAME` and
`LAYOUT-NAME-ATTR-MISMATCH` in
`<tooling>\scripts\detectors\layout_addressability.py`,
on top of the shared parser `scripts\shared\layout_ast.py`. The rules that did
NOT survive calibration (overlap, overflow, `ignorepointer` on a clickable) are
documented in that detector's header as deliberately not implemented.
