# DayZ .layout File Format — Complete Reference

## Format Overview

`.layout` files use Enfusion brace format (NOT XML — an XML-format layout crashes native
CreateWidgets). Syntax: `WidgetClassName WidgetName { properties { children } }`

**Leaf `{ }` blocks are OPTIONAL** (corrected 2026-07-05; the old "MUST have or the parser
crashes" claim here was refuted — vanilla omits them 99.6% of the time). What actually breaks
loading: unbalanced braces and XML format. See SKILL.md Rule 1 for the full corrected semantics.

---

## Complete Widget Class Catalog

### Container Widgets (no visual rendering)

| Layout Class | Script Class | Renders | Notes |
|---|---|---|---|
| `FrameWidgetClass` | `Widget` | NO | Invisible container, most common parent |
| `ScrollWidgetClass` | `ScrollWidget` | NO | Scrollable container, auto-scrollbars |
| `GridSpacerWidgetClass` | `GridSpacerWidget` | NO | Auto-layout grid (ObservableCollection target) |
| `WrapSpacerWidgetClass` | `WrapSpacerWidget` | NO | Wrapping flow layout (ObservableCollection target) |

### Visual Widgets

| Layout Class | Script Class | Renders | Notes |
|---|---|---|---|
| `ImageWidgetClass` | `ImageWidget` | YES | Background, icons, colored panels |
| `TextWidgetClass` | `TextWidget` | Text only | Static/bound text display |
| `RichTextWidgetClass` | `RichTextWidget` | Rich text | Supports inline `<image>`, `<font>`, `<b>` tags |
| `ButtonWidgetClass` | `ButtonWidget` | Minimal | Clickable, receives OnClick events |
| `EditBoxWidgetClass` | `EditBoxWidget` | YES | Single-line text input |
| `MultilineEditBoxWidgetClass` | `MultilineEditBoxWidget` | YES | Multi-line text input |
| `CheckBoxWidgetClass` | `CheckBoxWidget` | YES | Toggle checkbox |
| `XComboBoxWidgetClass` | `XComboBoxWidget` | YES | Dropdown selector |
| `SliderWidgetClass` | `SliderWidget` | YES | Value slider (min/max/step) |
| `ProgressBarWidgetClass` | `ProgressBarWidget` | YES | Progress indicator |
| `SimpleProgressBarWidgetClass` | `SimpleProgressBarWidget` | YES | Simpler progress variant |
| `CanvasWidgetClass` | `CanvasWidget` | NO | Programmatic drawing (DrawLine) |
| `VideoWidgetClass` | `VideoWidget` | YES | Video playback |
| `RTTextureWidgetClass` | `RTTextureWidget` | YES | Render target (3D model preview) |

### Special / MVC Widgets

| Layout Class | Notes |
|---|---|
| `ScriptParamsClass` | Holds MVC params: `Relay_Command`, `Two_Way_Binding` |

### Corpus-verified additions (2026-07-04 — classes the tables above omitted; counts from the 459-layout corpus)

| Layout Class | Count | Notes |
|---|---|---|
| `PanelWidgetClass` | 2,090 | 2nd most-used class in the corpus. Container; renders ONLY via a `style` (9-slice) — without one it is invisible like Frame |
| `MultilineTextWidgetClass` | 351 | Multi-line static text (word-wraps; distinct from MultilineEditBox) |
| `TextListboxWidgetClass` | 133 | Row/column list (AddItem/GetSelectedRow API in SKILL.md table) |
| `WindowWidgetClass` | 66 | Titled window chrome |
| `ItemPreviewWidgetClass` | 65 | 3D item render; script API `SetItem(EntityAI)/SetView(idx)` — `gameplay.c:276-288` |
| `ThreeStateCheckboxWidgetClass` | 10 | CheckBox variant |
| `PlayerPreviewWidgetClass` | 5 | 3D player render; `SetPlayer(DayZPlayer)` — `gameplay.c:300-312` |
| `PasswordEditBoxWidgetClass` | 1 | EditBox with masked input |

Attributes the property reference below omits (corpus counts): `priority` (1,440 — layout-side
z-order, higher = on top), `mode` (1,697 — image blend mode), `inheritalpha` (1,129 — multiply
alpha with parent), `userID` (467 — int id for `FindAnyWidgetById`), `text_proportion` (437 —
text size as fraction of widget height; THE vanilla text-scaling mechanism), `scaled` (939),
`fixaspect` (461 — keyword values: `fixwidth`/`inside`/`outside`/`none`, NOT 0/1), `keepsafezone`
(163). Full frequency table in `layout-empirical-corpus.md` §2.

---

## Widget Properties — Complete Reference

### Positioning & Sizing

```
position X Y              // Position (pixels if hexactpos/vexactpos=1, fraction 0-1 if =0)
size W H                  // Size (pixels if hexactsize/vexactsize=1, fraction 0-1 if =0)
hexactpos 0|1             // 1=pixel X position, 0=proportional (0.0-1.0)
vexactpos 0|1             // 1=pixel Y position, 0=proportional (0.0-1.0)
hexactsize 0|1            // 1=pixel width, 0=proportional (0.0-1.0)
vexactsize 0|1            // 1=pixel height, 0=proportional (0.0-1.0)
```

**RULE** (corrected 2026-07-04): declare all 4 flags explicitly for readability — but omission
defaults to PROPORTIONAL in practice, not "undefined" (42 vanilla widgets omit all four, incl.
production menu ROOTS like `day_z_ingamemenu.layout:1`, and render correctly with fractional values).

**Common patterns** (corpus-quantified, 8,671 vanilla widgets):
- **Mixing exact and proportional axes on one widget is the vanilla NORM (50.8%)** — the old
  "mixing is fragile" warning here was refuted by ground truth. Top profiles: exact pos +
  proportional size (1,892×) and exact pos + prop width + pixel height (1,182×).
- The dominant positioning idiom is **anchor + zero offset**: `halign/valign *_ref` +
  `position 0 0` (70% of exact-pos widgets have position 0 0) + proportional or height-pixel size.
- Full proportional (0000): 26.0% — e.g. MultilineText is 93% all-proportional.
- Full pixel (1111): 21.9% — reserve for pixel-true chrome; it is what breaks off-1080p (exact
  units = physical resolution, `enwidgets.c:68-71`).

### Alignment

```
halign left_ref|center_ref|right_ref    // Horizontal alignment reference
valign top_ref|center_ref|bottom_ref    // Vertical alignment reference
```

Used with proportional positioning. `center_ref` centers the widget relative
to parent. **Heavily used, not rare** (corrected 2026-07-04: 4,518 `valign` +
4,157 `halign` occurrences in the 300-layout corpus — top-10 attributes, more
common than `text` or `color`). Anchoring is central to how vanilla positions
resolution-independent UI: e.g. `day_z_hud.layout` roots use `halign center_ref`
+ `valign center_ref` with proportional size; `loading.layout` anchors its 16:9
background the same way. Misunderstood anchors are a classic source of "looks
right in the mockup, lands elsewhere in-game".

### Visibility & Interaction

```
visible 0|1               // Initial visibility (0=hidden, 1=visible, default=1)
ignorepointer 0|1         // 1=transparent to mouse events, 0=receives events
clipchildren 0|1           // 1=children clipped to parent bounds (overflow hidden)
```

**CRITICAL**: `ignorepointer 1` on ALL background ImageWidgets.
Without it, backgrounds steal mouse events from interactive children.

### Visual Properties

```
color R G B A             // Color as floats 0.0-1.0 (ImageWidget, TextWidget)
stretch 0|1               // 1=stretch image to fill widget bounds
```

**Color in layout**: Always 0.0-1.0 floats: `color 0.12 0.12 0.12 0.92`
**Color in script**: ARGB 0-255 integers: `widget.SetColor(ARGB(235, 30, 30, 30))`

### Text Properties (TextWidget, RichTextWidget, ButtonWidget)

```
font "gui/fonts/Metron"         // Font path (Metron=bold, MetronBook=regular)
text "LABEL"                     // Static text content
"text halign" left|center|right  // Text horizontal alignment
"text valign" top|center|bottom  // Text vertical alignment
```

**Available fonts** (vanilla DayZ):
- `gui/fonts/Metron` — bold/medium weight, good for headers/labels
- `gui/fonts/MetronBook` — regular weight, good for body text
- `gui/fonts/amorserifpro` — serif font

### Dabs MVC Binding Properties

```
scriptclass "ViewBinding"         // Enable MVC auto-binding (on bound widgets)
Two_Way_Binding 1                 // Enable bidirectional binding (EditBox ↔ property)
```

**In ScriptParamsClass block** (empirically settled 2026-07-04, 157/157 corpus instances:
`ScriptParamsClass` always sits in a DEDICATED anonymous block containing no child widgets —
the widget's ONLY block on leaves, or a SECOND block when the widget has children; NEVER mixed
into the same block as child widgets. No inner `{ }` inside ScriptParamsClass — that form appeared
only in layouts that copied this file's old example):
```
ScriptParamsClass {
    Relay_Command "MethodName"    // Routes button OnClick to Controller method
}
```

### Scroll Widget Properties (in script)

```
ScrollWidget scroll;
float pos01 = scroll.GetVScrollPos01();  // 0.0-1.0 normalized position
scroll.VScrollToPos01(0.5);              // Scroll to middle
scroll.VScrollToWidget(childWidget);     // Scroll to make child visible
bool visible = scroll.IsScrollbarVisible();
float contentH = scroll.GetContentHeight();
float contentW = scroll.GetContentWidth();
```

### Spacer Widget Properties (in script)

```
SpacerWidget spacer;
spacer.SetContentAlignmentH(WidgetAlignment.WA_CENTER);
spacer.SetContentAlignmentV(WidgetAlignment.WA_TOP);
```

---

## Widget API — Key Script Functions

### Positioning (script-side)

```
// Relative to parent (what GetPos/SetPos use)
widget.GetPos(out float x, out float y);
widget.SetPos(float x, float y);
widget.GetSize(out float w, out float h);
widget.SetSize(float w, float h);

// Absolute screen coordinates
widget.GetScreenPos(out float x, out float y);
widget.SetScreenPos(float x, float y);
widget.GetScreenSize(out float w, out float h);
widget.SetScreenSize(float w, float h);

// NOTE: GetPos returns relative-to-parent. GetScreenPos returns absolute.
// For drag operations, be consistent — use one coordinate space throughout.
```

### Hierarchy Navigation

```
Widget parent = widget.GetParent();
Widget firstChild = widget.GetChildren();
Widget nextSibling = widget.GetSibling();

// Walk all children:
Widget child = parent.GetChildren();
while (child)
{
    // process child
    child = child.GetSibling();
}

// Find by name (recursive)
Widget found = root.FindAnyWidget("WidgetName");

// Find by path (parent/child/grandchild)
Widget found2 = root.FindWidget("Parent/Child/Grandchild");

// Find by integer ID
widget.SetUserID(42);
Widget found3 = root.FindAnyWidgetById(42);
```

### Custom Data Attachment

```
// Attach any Class to a widget (useful for tag/item data)
widget.SetUserData(myDataObject);

// Retrieve
Class data;
widget.GetUserData(data);
MyDataClass myData = MyDataClass.Cast(data);
```

### Dynamic Widget Creation

```
// From layout file (preferred)
Widget root = GetGame().GetWorkspace().CreateWidgets(layoutPath, parentWidget);

// Programmatic creation (rare, for dynamic needs)
Widget w = widget.CreateWidget(WidgetType, left, top, width, height, flags, color, sort, parent);

// Insert at specific position in child list
parent.AddChildAfter(newChild, afterThisChild);

// Remove from parent
parent.RemoveChild(child);

// Destroy widget and all children
widget.Unlink();
```

### Visual Effects

```
// Text outline (size in pixels, ARGB color)
textWidget.SetOutline(1, 0xFF000000);       // 1px black outline
int outSize = textWidget.GetOutlineSize();

// Text shadow
textWidget.SetShadow(2, 0x80000000, 0.8, 1.0, 1.0);  // size, color, opacity, offsetX, offsetY

// Text exact pixel size (requires exact text flag)
textWidget.SetTextExactSize(14);  // 14px

// Get rendered text dimensions
int textW;
int textH;
textWidget.GetTextSize(textW, textH);

// Text elision (truncate with "...")
textWidget.ElideText(0, 200.0, "...");  // line 0, max 200px, suffix "..."

// Alpha masking (circular reveals, wipes, etc.)
imageWidget.LoadMaskTexture("path/to/mask.edds");
imageWidget.SetMaskProgress(0.5);         // 0.0-1.0
imageWidget.SetMaskTransitionWidth(0.1);  // soft edge
```

### Performance

```
// Render every N frames (reduce GPU cost for static widgets)
widget.SetRefresh(2, 0);  // render every 2nd frame, offset 0

// Native resolution scaling (alternative to manual scaling)
widget.SetResolutionScale(1.5, 1.5);  // scale 150%

// Global widget brightness [-15, 0], 0=normal
SetLV(-2.0);       // darken all widgets
SetTextLV(-1.0);   // darken text only
```

### Z-Order

```
// Sort order (higher = rendered on top)
widget.SetSort(50000);   // high value = above most UI
int sort = widget.GetSort();

// NOTE (corrected 2026-07-03): SetSort is an ABSOLUTE set, not additive. The "ADDS to
// existing value" note was a mis-transcription — in enwidgets.c the `//! ADDS the value to
// the existing flag` comment belongs to SetFlags (line 128), and ClearFlags SUBSTRACTS
// (line 131). SetSort (line 130) carries no such comment. It is SetFlags/ClearFlags that
// are additive/subtractive, not SetSort. Layout-side equivalent of z-order: the `priority`
// attribute (higher = on top).
```

### Flags (script-side)

```
// WidgetFlags enum
SOURCEALPHA    // Use source alpha blending
BLEND          // Enable blending
ADDITIVE       // Additive blending
VISIBLE        // Widget visible
HEXACTPOS      // Horizontal exact position (pixels)
VEXACTPOS      // Vertical exact position (pixels)
HEXACTSIZE     // Horizontal exact size (pixels)
VEXACTSIZE     // Vertical exact size (pixels)
NOFILTER       // No texture filtering
STRETCH        // Stretch image to fill
IGNOREPOINTER  // Transparent to mouse
CLIPCHILDREN   // Clip children to bounds
DRAGGABLE      // Enable native drag support
NOFOCUS        // Cannot receive focus
RENDER_ALWAYS  // Render even when not visible (rare)
DISABLED       // Widget disabled

// Set/Clear flags
widget.SetFlags(WidgetFlags.IGNOREPOINTER);
widget.ClearFlags(WidgetFlags.VISIBLE);
```

---

## RichTextWidget — Inline Formatting

`RichTextWidget` supports HTML-like inline tags:

```
// In script:
RichTextWidget rtw = RichTextWidget.Cast(root.FindAnyWidget("MyRichText"));
string formatted = "<b>Bold</b> and <font name='gui/fonts/MetronBook'>different font</font>";
rtw.SetText(formatted);

// Inline image from imageset:
string withIcon = "<image set='dayz_gui' name='icon_pin' /> Location";
rtw.SetText(withIcon);
```

**Supported tags**: `<b>`, `<font name='...'>`, `<image set='...' name='...'/>`

---

## Layout Validation Checklist

Before delivering ANY .layout file:

- [ ] Brace format (not XML); brace count balanced (opens == closes)
- [ ] All 4 unit flags DECLARED on every widget (0=proportional default; 1 only for pixel-true)
- [ ] ALL ImageWidget backgrounds have `ignorepointer 1`
- [ ] ALL visible backgrounds use `ImageWidgetClass` (not Frame/Panel)
- [ ] Widget names unique across entire layout
- [ ] No `scriptclass "ViewBinding"` on root widget (causes double controller)
- [ ] EditBox/Button widgets do NOT have `ignorepointer 1` (need mouse events)
- [ ] `ScriptParamsClass` with `Relay_Command` inside every bound Button
- [ ] Layout path uses forward slashes, correct case (Linux-sensitive PBO)
- [ ] No trailing whitespace or BOM characters
- [ ] Consistent positioning strategy (all-pixel or all-proportional per widget)
- [ ] Color values as 0.0-1.0 floats (not 0-255 integers)
- [ ] `clipchildren 1` on scrollable/overflow containers
- [ ] `stretch 1` on ImageWidgets used as backgrounds

---

## Common Layout Patterns

### Colored Background Panel
```
ImageWidgetClass PanelBg {
    position 0 0
    size 400 300
    hexactpos 1
    vexactpos 1
    hexactsize 1
    vexactsize 1
    stretch 1
    ignorepointer 1
    color 0.12 0.12 0.12 0.92
    {
    }
}
```

### Button with Bg + Text + Relay_Command
```
ButtonWidgetClass BtnSave {
    position 10 10
    size 100 30
    hexactpos 1
    vexactpos 1
    hexactsize 1
    vexactsize 1
    {
        ImageWidgetClass BtnSaveBg {
            position 0 0
            size 1 1
            hexactpos 0
            vexactpos 0
            hexactsize 0
            vexactsize 0
            stretch 1
            ignorepointer 1
            {
            }
        }
        TextWidgetClass BtnSaveText {
            position 0 0
            size 1 1
            hexactpos 0
            vexactpos 0
            hexactsize 0
            vexactsize 0
            font "gui/fonts/Metron"
            "text halign" center
            "text valign" center
            text "SAVE"
            ignorepointer 1
        }
    }
    {
        ScriptParamsClass {
            Relay_Command "BtnSave"
        }
    }
}
```
*(Corrected 2026-07-04: `ScriptParamsClass` goes in its own SECOND anonymous block — the previous
version of this example put it alongside the child widgets, a form with ZERO empirical support in
157 corpus instances.)*

### MVC-Bound EditBox with Two-Way Binding
```
EditBoxWidgetClass EditPrefix {
    scriptclass "ViewBinding"
    Two_Way_Binding 1
    position 14 116
    size 286 28
    hexactpos 1
    vexactpos 1
    hexactsize 1
    vexactsize 1
    font "gui/fonts/MetronBook"
    {
    }
}
```

### Scrollable List Container
```
ScrollWidgetClass RulesScroll {
    position 0 30
    size 319 400
    hexactpos 1
    vexactpos 1
    hexactsize 1
    vexactsize 1
    clipchildren 1
    {
        GridSpacerWidgetClass RulesList {
            position 0 0
            size 319 0
            hexactpos 1
            vexactpos 1
            hexactsize 1
            vexactsize 0
            {
            }
        }
    }
}
```

### Fullscreen Click Blocker (with ignorepointer!)
```
// v2.7 pattern: ClickBlocker as visual-only element.
// ChangeGameFocus(1) + SetDisabled(true) handle click-through prevention.
// DO NOT remove ignorepointer — it steals mouse events from buttons!
ImageWidgetClass ClickBlocker {
    position 0 0
    size 1 1
    hexactpos 0
    vexactpos 0
    hexactsize 0
    vexactsize 0
    color 0.0 0.0 0.0 0.004
    stretch 1
    ignorepointer 1
    {
    }
}
```

---

## Gotchas & Pitfalls

1. **FrameWidgetClass/PanelWidgetClass are INVISIBLE** — use ImageWidgetClass for backgrounds
2. **Color 0.0-1.0 in layout, 0-255 in script** — mixing causes invisible or wrong-colored widgets
3. **DayZ darkens widget colors via global LV — the FIX is `SetLV(0)`, NOT boosting values.**
   *(Corrected 2026-07-03. The old "boost colors 30%+" advice is stale and, applied AFTER
   `SetLV(0)`, makes UI ~30% too bright.)* Call `Widget.SetLV(0)` + `Widget.SetTextLV(0)` once at
   mod init; that normalizes widget colors to match the ARGB you authored (saturated colors were
   barely affected either way; grays/pastels were the ones darkened). Do not also pre-boost the
   values. See SKILL.md COLOR SYSTEM + LFPG KB E7 (verified in-engine 2026-03-24).
4. **Low alpha clamps to invisible** — measured bracket: 0x12 invisible, 0x26 visible → threshold in
   (0x12, 0x26]. Keep alpha ≥ 0x30 (48) for must-see elements (corrected 2026-07-04; the old
   two-threshold claim here contradicted SKILL.md's own data points)
5. **`scriptclass "ViewBinding"` on root = double controller** — only on bound child widgets
6. **Button children need careful naming** — auto-bind may miss ImageWidget/TextWidget inside ButtonWidget. Use child-walk fallback (FindBtnChildBg/FindBtnChildText pattern)
7. **Widget name collisions** across the layout cause FindAnyWidget to return the wrong widget
8. **Comments are // style** (C++ line comments), NOT `<!-- -->` XML comments
9. **No semicolons** after property values (unlike config.cpp)
10. **Inline format is valid** but hard to verify: `ImageWidgetClass Bg { position 0 0 size 1 1 ... { } }`
11. **`SetSort` is an ABSOLUTE set** *(corrected 2026-07-03 — the additive `//! ADDS` comment in
    `enwidgets.c:128` belongs to `SetFlags`, not `SetSort` at `:130`)*. `SetFlags` ADDS and
    `ClearFlags` SUBSTRACTS; `SetSort` replaces. Layout-side z-order = the `priority` attribute.
12. **`GetPos` returns relative-to-parent**, `GetScreenPos` returns absolute — critical for drag
13. **JSON file > 64KB causes truncation** in DayZ file I/O (BI tracker T148095). Split large data across multiple files or compress.
14. **ImageSets** (`set:dayz_gui image:icon_name`) only work with `LoadImageFile` on ImageWidget or inline in RichTextWidget — not in layout `color` property.

---

## Production Patterns — Extracted from Popular Mods

Patterns used by Expansion Market, TraderPlus, LBmaster, COT/VPP, and
other production DayZ mods with polished UIs.

### Pattern: Imageset Icons (Expansion, LBmaster, Vanilla)

DayZ ships with built-in icon imagesets. No .edds needed.

```
// In script — load icon from vanilla imageset
ImageWidget icon = ImageWidget.Cast(root.FindAnyWidget("MyIcon"));
if (icon)
{
    string iconPath = "set:dayz_gui image:icon_pin";
    icon.LoadImageFile(0, iconPath);
}

// In RichTextWidget — inline icon
RichTextWidget rtw = RichTextWidget.Cast(root.FindAnyWidget("MyRichText"));
if (rtw)
{
    string rt = "<image set='dayz_gui' name='icon_pin' /> Location found";
    rtw.SetText(rt);
}
```

Common vanilla imagesets: `dayz_gui`, `dayz_inventory`, `dayz_crosshairs`.
Custom imagesets can be registered via `config.cpp` → `CfgMods` → `defs` → `imageSets`.

### Pattern: Tabbed Category Navigation (TraderPlus, Expansion Market)

Both TraderPlus and Expansion use tab bars for item categories.
Pattern: ButtonWidget per tab → shared content panel → swap visibility.

```
// Data model: which tab is active
protected int m_ActiveTab;

// Activate tab N
void SelectTab(int idx)
{
    m_ActiveTab = idx;

    // Visual: highlight active tab, dim others
    int i;
    for (i = 0; i < m_TabCount; i = i + 1)
    {
        bool isActive = (i == idx);
        ImageWidget tabBg = m_TabBgs[i];
        if (tabBg)
        {
            if (isActive)
            {
                tabBg.SetColor(COL_TAB_ACTIVE);
            }
            else
            {
                tabBg.SetColor(COL_TAB_INACTIVE);
            }
        }
    }

    // Content: show/hide panels or repopulate list
    RefreshContent();
}
```

### Pattern: Scrollable Item List with Dynamic Rows (TraderPlus, Expansion)

```
// Layout structure:
// ScrollWidgetClass ItemScroll {
//     GridSpacerWidgetClass ItemList {  // or WrapSpacerWidgetClass
//         // children added dynamically from script
//     }
// }

// Script — populate list
void PopulateItems(array<ItemData> items)
{
    // Clear previous children
    Widget child = m_ItemList.GetChildren();
    while (child)
    {
        Widget next = child.GetSibling();
        child.Unlink();  // destroy widget + children
        child = next;
    }

    // Create new rows from layout prefab
    int i;
    string rowLayout = "MyMod/gui/layouts/ItemRow.layout";
    for (i = 0; i < items.Count(); i = i + 1)
    {
        Widget row = GetGame().GetWorkspace().CreateWidgets(rowLayout, m_ItemList);
        if (!row)
            continue;

        // Populate row data
        TextWidget nameW = TextWidget.Cast(row.FindAnyWidget("ItemName"));
        if (nameW)
        {
            nameW.SetText(items[i].m_Name);
        }
        // ... price, icon, etc.
    }
}
```

**Performance note**: For lists > 50 items, consider virtual scrolling —
only create visible rows + buffer, recycle on scroll. TraderPlus V1 creates
all rows upfront which causes lag on servers with 1000+ items.

### Pattern: Search/Filter Bar (TraderPlus, Expansion Market)

```
// EditBox for search input
// In layout:
// EditBoxWidgetClass SearchInput { ... Two_Way_Binding 1 ... }

// In controller — filter on text change
string SearchText;  // bound to SearchInput via ViewBinding

void OnSearchChanged()
{
    string query = SearchText;
    query.ToLower();

    // Filter visible items
    int i;
    for (i = 0; i < m_AllItems.Count(); i = i + 1)
    {
        string itemName = m_AllItems[i].m_Name;
        itemName.ToLower();

        bool match = false;
        if (query == "")
        {
            match = true;
        }
        else if (itemName.IndexOf(query) >= 0)
        {
            match = true;
        }
        m_ItemWidgets[i].Show(match);
    }
}
```

### Pattern: Confirmation Dialog (TraderPlus, Expansion, LBmaster)

Two-phase button: first press → "Confirm?" state + timer → second press → execute.

```
protected bool m_ConfirmActive;
protected float m_ConfirmTimer;

void BtnDangerousAction()
{
    if (!m_ConfirmActive)
    {
        m_ConfirmActive = true;
        m_ConfirmTimer = 3.0;  // 3 seconds to confirm

        string confirmLabel = "Confirm?";
        if (BtnText)
        {
            BtnText.SetText(confirmLabel);
        }
        if (BtnBg)
        {
            BtnBg.SetColor(COL_RED);
        }
        return;
    }

    // Second press — execute action
    m_ConfirmActive = false;
    ExecuteDangerousAction();
    RestoreButtonNormal();
}

// In Update(dt): expire confirmation
if (m_ConfirmActive)
{
    m_ConfirmTimer = m_ConfirmTimer - dt;
    if (m_ConfirmTimer <= 0.0)
    {
        m_ConfirmActive = false;
        RestoreButtonNormal();
    }
}
```

### Pattern: Status Feedback Toast (TraderPlus, LBmaster)

Temporary status message that auto-fades.

```
protected float m_FeedbackTimer;
protected string m_FeedbackMsg;

void ShowFeedback(string msg, float durationS)
{
    m_FeedbackMsg = msg;
    m_FeedbackTimer = durationS;

    if (StatusLabel)
    {
        StatusLabel.SetText(msg);
        StatusLabel.SetColor(COL_GREEN);
    }
}

// In Update(dt):
if (m_FeedbackTimer > 0.0)
{
    m_FeedbackTimer = m_FeedbackTimer - dt;
    if (m_FeedbackTimer <= 0.0)
    {
        if (StatusLabel)
        {
            string defaultStatus = "READY";
            StatusLabel.SetText(defaultStatus);
            StatusLabel.SetColor(COL_TEXT_DIM);
        }
    }
}
```

### Pattern: Server-Configurable UI Colors (Expansion Market)

Expansion Market allows server owners to configure menu colors via JSON.
Pattern: load color config from server settings, apply at menu open.

```
class MyMenuColors
{
    int BaseBackground;
    int HeaderBackground;
    int ButtonNormal;
    int ButtonHover;
    int TextPrimary;
    int TextSecondary;
    int AccentColor;

    void SetDefaults()
    {
        BaseBackground = ARGB(235, 30, 30, 30);
        HeaderBackground = ARGB(240, 37, 42, 54);
        ButtonNormal = ARGB(255, 37, 53, 80);
        // ... etc
    }
}

// On menu open — apply server-configured or default colors
void ApplyColorScheme(MyMenuColors scheme)
{
    if (!scheme)
        return;

    if (PanelBg)
    {
        string tex = "#(argb,8,8,3)color(1,1,1,1,CO)";
        PanelBg.LoadImageFile(0, tex);
        PanelBg.SetColor(scheme.BaseBackground);
    }
    // ... apply to all themed widgets
}
```

### Pattern: RTTextureWidget for 3D Item Preview (Expansion Market)

Expansion Market shows 3D item previews in the UI using RTTextureWidget.

```
// In layout:
// RTTextureWidgetClass ItemPreview3D {
//     position 10 10
//     size 200 200
//     ... 4 exact flags ...
//     { }
// }

// In script — set up 3D preview
// Note: requires entity creation for the preview object
// and camera setup — complex pattern, see Expansion source
// for full implementation. Key API:
// RTTextureWidget has SetRTTextureWidget() on EntityAI
// for rendering entity to UI texture.
```

### Pattern: HUD Overlay (LBmaster, Expansion Notifications)

For HUD elements that persist across menus:

```
// Create in MissionGameplay.OnInit (or OnUpdate with once-guard)
// Layout: fullscreen frame, children positioned absolutely
// Use `root.SetSort(1000)` to layer above game HUD but below menus

// Critical: HUD widgets must NOT use ChangeGameFocus/ShowUICursor
// They are passive overlays — no input interception

// Update in MissionGameplay.OnUpdate:
if (m_HudWidget && m_HudWidget.IsVisible())
{
    UpdateHudData();
}
```

### Pattern: Sound Feedback (All polished mods)

```
// UI click sound (vanilla)
static void PlayUIClick()
{
    SEffectManager.PlaySound("Backpack_SoundSet", vector.Zero);
}

// UI action sound (more noticeable)
static void PlayUIAction()
{
    SEffectManager.PlaySound("pickUpBackPack_Metal_SoundSet", vector.Zero);
}
```

Use sparingly — on button clicks and confirmations, not on hover or tab switch.

---

## ScriptClass — Attaching Script Handlers to Layout Widgets

### Basic Pattern
A widget can have a `scriptclass` property pointing to a ScriptedWidgetEventHandler.
The engine instantiates it and calls `OnWidgetScriptInit`:

Layout:
```
EditBoxWidgetClass myInput {
    scriptclass "LBValidator_Number"
    position 10 10
    size 200 30
    hexactpos 1
    vexactpos 1
    hexactsize 1
    vexactsize 1
    {
    }
}
```

Script:
```
class LBValidator_Number : ScriptedWidgetEventHandler {
    Widget root;
    
    void OnWidgetScriptInit(Widget w) {
        root = w;
        w.SetHandler(this);  // required for events
        // Called once when layout is created
    }
    
    override bool OnChange(Widget w, int x, int y, bool finished) {
        // validate input...
        return false;
    }
}
```

### ScriptParamsClass — Passing Parameters from Layout to Script

The `reference` keyword in the handler class marks fields that receive values
from the layout's ScriptParamsClass block:

Script:
```
class LBGapHandler : ScriptedWidgetEventHandler {
    reference int gapHorizontal;    // populated from layout
    reference int gapVertical;      // populated from layout
    Widget root;
    
    void OnWidgetScriptInit(Widget w) {
        root = w;
        // gapHorizontal and gapVertical already have values from layout
        w.SetHandler(this);
    }
}
```

Layout:
```
PanelWidgetClass myPanel {
    scriptclass "LBGapHandler"
    position 0 0
    size 1 1
    hexactpos 1
    vexactpos 1
    hexactsize 0
    vexactsize 0
    {
    }
    {
        ScriptParamsClass {
            gapHorizontal -10
            gapVertical -10
        }
    }
}
```

Note: ScriptParamsClass goes in a SECOND child block of the widget.
The first `{ }` is for child widgets, the second `{ ScriptParamsClass { ... } }` is for params.

### Use Cases for ScriptClass
- **Validators**: Number-only, float-only, steamid format validation on EditBox
- **Gap/margin handlers**: Dynamic sizing based on parent
- **Auto-scroll**: Clip children based on scroll position
- **Tooltip triggers**: Show tooltip on hover
- **Drag handlers**: Custom drag-and-drop behavior
- **Loading animations**: Rotating/pulsing icon widgets

---

## Styles in Layout

Reference a registered style in layout:
```
PanelWidgetClass myBorder {
    style LB_Clean_outline
    color 1 1 1 1
    ...
}
```
The style name must match one registered in a .styles file declared in config.cpp.
Styles provide state-based rendering (Normal, Disabled, Focus, Pressed) with
9-slice image support from ImageSets.
