# Widget API — Verified Reference

Source: `enwidgets.c` (engine protos), Dabs Framework source, LFPG production.
Every function listed here is confirmed to exist in the engine.

---

## Widget (base class — all widgets inherit these)

```
// Identity
proto native string GetName();
proto native void SetName(string name);
proto native string GetTypeName();
proto native WidgetType GetTypeID();

// Visibility
proto native void Show(bool show, bool immedUpdate = true);
proto native void Enable(bool enable);
proto native bool IsVisible();
proto native bool IsVisibleHierarchy();  // checks entire parent chain

// Flags
proto native int GetFlags();
proto native int SetFlags(int flags, bool immedUpdate = true);   // ADDS flags
proto native int ClearFlags(int flags, bool immedUpdate = true); // REMOVES flags

// Position & Size (logical coordinates)
proto native void SetPos(float x, float y, bool immedUpdate = true);
proto void GetPos(out float x, out float y);
proto native void SetSize(float w, float h, bool immedUpdate = true);
proto void GetSize(out float width, out float height);

// Position & Size (screen/physical coordinates)
proto native void SetScreenPos(float x, float y, bool immedUpdate = true);
proto void GetScreenPos(out float x, out float y);
proto native void SetScreenSize(float w, float h, bool immedUpdate = true);
proto void GetScreenSize(out float width, out float height);

// Color & Alpha
proto native void SetColor(int color);     // ARGB int
proto native int GetColor();               // ARGB int
proto native void SetAlpha(float alpha);   // 0.0-1.0
proto native float GetAlpha();

// Transform
proto native void SetRotation(float roll, float pitch, float yaw, bool immedUpdate = true);
proto native vector GetRotation();         // returns (roll, pitch, yaw)
proto native void SetTransform(vector mat[4], bool immedUpdate = true);

// Z-Order
proto native int GetSort();
proto native void SetSort(int sort, bool immedUpdate = true);

// Hierarchy
proto native Widget GetParent();
proto native Widget GetChildren();         // first child
proto native Widget GetSibling();          // next sibling
proto native void AddChild(Widget child, bool immedUpdate = true);
proto native void RemoveChild(Widget child);
proto native void Unlink();                // DESTROYS widget and ALL children

// Search
proto native Widget FindWidget(string pathname);        // by path "a.b.c"
proto native Widget FindAnyWidget(string pathname);     // by name anywhere in tree
proto native Widget FindAnyWidgetById(int user_id);     // by user ID

// Script & Data
proto void GetScript(out Class data);
proto native void SetUserData(Class data);
proto void GetUserData(out Class data);
proto native int GetUserID();
proto native void SetUserID(int id);

// Event Handler
proto native void SetHandler(ScriptedWidgetEventHandler eventHandler);

// Misc
proto native bool IsControlClass();
proto native string GetStyleName();
proto native void Update();                // force update

// Global luminance control (static) — VERIFIED IN-ENGINE 2026-03-24
// SetLV(0) normalizes colors. Without it, DayZ darkens grays/pastels significantly.
proto static void SetLV(float lv);         // widgets brightness [-15, 0], default 0
proto static void SetTextLV(float lv);     // text brightness [-15, 0]
proto static void SetObjectLighting(float lighting); // object brightness [0, 1]
proto static string TranslateString(string stringId);
```

## WidgetFlags (verified from enwidgets.c)

```
SOURCEALPHA    // alpha from texture * color alpha
BLEND          // texture blended with surface
ADDITIVE       // texture added to surface
VISIBLE        // widget is visible
NOWRAP         // no texture wrapping
CENTER         // centers text horizontally
VCENTER        // centers text vertically
HEXACTPOS      // exact horizontal position
VEXACTPOS      // exact vertical position
EXACTPOS       // both exact pos (physical resolution)
HEXACTSIZE     // exact horizontal size
VEXACTSIZE     // exact vertical size
EXACTSIZE      // both exact size
NOFILTER       // no texture filtering
RALIGN         // right alignment for text
STRETCH        // stretch texture to fill
FLIPU          // flip texture U axis
FLIPV          // flip texture V axis
CUSTOMUV       // custom UV coordinates
IGNOREPOINTER  // ignore mouse/pointer events
DISABLED       // widget disabled
NOFOCUS        // cannot receive focus
CLIPCHILDREN   // clip children to bounds
RENDER_ALWAYS  // render even when not visible
NOCLEAR        // no clear
DRAGGABLE      // can be dragged
```

---

## TextWidget (extends Widget)

```
proto native void SetText(string text, bool immedUpdate = true);
proto void SetTextFormat(string text, void p1..p9);
proto native void SetTextExactSize(int size);    // requires "exact text" flag
proto native void SetTextSpacing(int horiz, int vert);
proto native void SetTextOffset(int left, int top);
proto void GetTextSize(out int sx, out int sy);  // size in pixels
proto native float GetTextProportion();
proto native void SetTextProportion(float val);  // ratio text/button height [0,1]

// Style
proto native void SetBold(bool bold);
proto native bool GetBold();
proto native void SetItalic(bool italic);
proto native bool GetItalic();

// Outline
proto native void SetOutline(int outlineSize, int argb = 0xFF000000);
proto native int GetOutlineSize();
proto native int GetOutlineColor();

// Shadow
proto native void SetShadow(int size, int argb, float opacity, float offX, float offY);
proto native int GetShadowSize();
proto native int GetShadowColor();
proto native float GetShadowOpacity();
proto void GetShadowOffset(out float sx, out float sy);
```

## RichTextWidget (extends TextWidget)

Supports markup tags: `<b>`, `<i>`, `<color rgba="R,G,B,A">`, `<color hex="0xAARRGGBB">`,
`<image set="..." name="..." scale="1" />`, `<outline>`, `<shadow>`, `<font>`.
Tags must NOT overlap. Requires SDF fonts for bold/italic.
Wrap + re-layout on runtime resize is expensive — avoid with long text.

```
proto native float GetContentHeight();
proto native float GetContentOffset();
proto native void SetContentOffset(float offset, bool snapToLine = false);
proto native void ElideText(int line, float maxWidth, string str);
proto native int GetNumLines();
proto native void SetLinesVisibility(int lineFrom, int lineTo, bool visible);
proto native float GetLineWidth(int line);
proto native float SetLineBreakingOverride(int mode);
```

## MultilineEditBoxWidget (extends TextWidget)

```
proto void GetText(out string text);
proto native void SetLine(int line, string text);
proto void GetLine(int line, out string text);
proto native int GetLinesCount();
proto native int GetCarriageLine();     // cursor line position
proto native int GetCarriagePos();      // cursor char position
```

---

## ImageWidget (extends Widget)

```
proto native bool LoadImageFile(int num, string name, bool noCache = false);
proto native bool SetImage(int num);           // switch active image (0-7)
proto native int GetImage();
proto void GetImageSize(int image, out int sx, out int sy);
proto native void SetImageTexture(int image, RTTextureWidget texture);
proto native void SetUV(float uv[4][2]);       // custom UV (needs CUSTOMUV flag)

// Alpha Mask (reveal/transition effects)
proto native bool LoadMaskTexture(string resource);
proto native float GetMaskProgress();
proto native void SetMaskProgress(float value);         // [0,1]
proto native float GetMaskTransitionWidth();
proto native void SetMaskTransitionWidth(float value);  // [0,1] softness
```

**Pattern for colored background:**
```
string tex = "#(argb,8,8,3)color(1,1,1,1,CO)";
img.LoadImageFile(0, tex);
img.SetColor(ARGB(alpha, r, g, b));
```

---

## ButtonWidget (extends UIWidget)

```
proto native bool GetState();
proto native bool SetState(bool state);
proto native void SetText(string text);
proto void GetText(out string text);
proto native void SetTextOffset(float xoff, float yoff);
proto native void SetTextHorizontalAlignment(int align);
proto native void SetTextVerticalAlignment(int align);
proto native void SetColor(int color);   // inherited - works WITHOUT LoadImageFile
```

## EditBoxWidget (extends UIWidget)

```
proto string GetText();
proto native void SetText(string str);
// OnChange fires on every keystroke
// SetFocus(null) clears focus (first ESC removes focus, second closes panel)
```

## CheckBoxWidget (extends UIWidget)

```
proto native bool IsChecked();
proto native void SetChecked(bool checked);
proto native void SetText(string str);
```

## SliderWidget (extends UIWidget)

```
proto native void SetMinMax(float minimum, float maximum);
proto native float GetMin();
proto native float GetMax();
proto native float GetCurrent();
proto native void SetCurrent(float curr);
proto native float GetStep();
proto native void SetStep(float step);
```

---

## ScrollWidget (extends SpacerBaseWidget)

Full scroll API — both horizontal and vertical.

```
proto native float GetScrollbarWidth();
proto native bool IsScrollbarVisible();

proto native float GetContentWidth();
proto native float GetContentHeight();

// Vertical
proto native float GetVScrollPos();         // absolute position
proto native float GetVScrollPos01();       // normalized [0,1]
proto native bool VScrollStep(int steps);
proto native void VScrollToPos(float pos);
proto native void VScrollToPos01(float pos01);
proto native void VScrollToWidget(Widget child);   // scroll to show child!

// Horizontal
proto native float GetHScrollPos();
proto native float GetHScrollPos01();
proto native bool HScrollStep(int steps);
proto native void HScrollToPos(float pos);
proto native void HScrollToPos01(float pos01);
proto native void HScrollToWidget(Widget child);
```

**Key layout properties:** `"Scrollbar V" 1`, `"Size To Content V" 1`

---

## SpacerBaseWidget / SpacerWidget / GridSpacerWidget / WrapSpacerWidget

```
// SpacerBaseWidget
proto native void AddChildAfter(Widget child, Widget after, bool immedUpdate = true);

// SpacerWidget (extends SpacerBaseWidget)
proto native WidgetAlignment GetContentAlignmentH();
proto native void SetContentAlignmentH(WidgetAlignment alignment);
proto native WidgetAlignment GetContentAlignmentV();
proto native void SetContentAlignmentV(WidgetAlignment alignment);
```

WidgetAlignment: `WA_LEFT(0)`, `WA_RIGHT(1)`, `WA_CENTER(2)`, `WA_TOP(0)`, `WA_BOTTOM(1)`

GridSpacer layout: `Columns N`, `Rows N`, `Padding X`, `Margin X`, `"Size To Content H/V" 1`
WrapSpacer layout: same + auto-wraps children to next row.
Both work inside ScrollWidget for dynamic lists.

---

## CanvasWidget

```
proto native void DrawLine(float x1, float y1, float x2, float y2, float width, int color);
proto native void Clear();
```

## VideoWidget

```
proto native bool Load(string name, bool looping = false, int startTime = 0);
proto native void Unload();
proto native bool Play();
proto native bool Pause();
proto native bool Stop();
proto native bool SetTime(int time, bool preload);
proto native int GetTime();
proto native int GetTotalTime();
proto native void SetLooping(bool looping);
proto native bool IsPlaying();
proto native VideoState GetState();
proto native void DisableSubtitles(bool disable);
proto void SetCallback(VideoCallback cb, func fn);
```

---

## Global Functions

```
proto native Widget GetWidgetUnderCursor();
proto native Widget CancelWidgetDragging();
proto native Widget GetDragWidget();
proto native void SetFocus(Widget w);
proto native Widget GetFocus();
proto native void SetModal(Widget w);
proto native void SetCursorWidget(Widget cursor);
proto native void ShowCursorWidget(bool show);
proto native bool SetActiveWindow(Widget w, bool resetFocus);
proto native void ReportMouse(int mousex, int mousey, Widget rootWidget);
proto native bool LoadWidgetImageSet(string filename);
proto native void LoadWidgetStyles(string filename);
proto native bool ReloadTexture(string path);

// Screen size (int version)
void GetScreenSize(out int w, out int h);

// Mouse position (int version)
void GetMousePos(out int x, out int y);
```

---

## ControlID (for OnController events)

```
CID_NONE = 0
CID_SELECT = 1     // select/use focused
CID_BACK = 2
CID_LEFT = 3       // navigation
CID_RIGHT = 4
CID_UP = 5
CID_DOWN = 6
CID_MENU = 7       // main menu
CID_DRAG = 8       // console dragging
CID_TABLEFT = 9
CID_TABRIGHT = 10
CID_RADIALMENU = 11
```

---

## Extended Widget APIs (verified from LBmaster_Core)

### TextWidget Extended
```
widget.SetTextExactSize(16);                    // pixel size (not font size)
widget.SetOutline(size, argbColor);             // text outline
widget.SetShadow(size, color, opacity, offsetX, offsetY);
widget.SetBold(true);
widget.SetItalic(true);
widget.SetColor(intARGB);                       // text color
int color = widget.GetColor();
int txtW, txtH;
widget.GetTextSize(txtW, txtH);                 // measure rendered text

// Text property getters (also on EditBoxWidget):
int outlineSize = widget.GetTextOutlineSize();
int outlineColor = widget.GetTextOutlineColor();
int shadowSize = widget.GetTextShadowSize();
int shadowColor = widget.GetTextShadowColor();
float shadowOpacity = widget.GetTextShadowOpacity();
float shadowOffsetX = widget.GetTextShadowOffsetX();
float shadowOffsetY = widget.GetTextShadowOffsetY();
bool isItalic = widget.GetTextItalic();
bool isBold = widget.GetTextBold();
```

### EditBoxWidget — GetText variants
```
// EditBoxWidget returns string directly:
string text = editBox.GetText();

// MultilineEditBoxWidget uses out parameter:
string text2;
multiEditBox.GetText(text2);
```

### ImageWidget Extended
```
bool loaded = img.LoadImageFile(0, path);       // returns success bool
int imgW, imgH;
img.GetImageSize(0, imgW, imgH);               // image dimensions in pixels
```

### Pixel-Level Positioning (any widget)
```
widget.SetScreenPos(pixelX, pixelY);            // absolute pixel position
widget.SetScreenSize(pixelW, pixelH);           // absolute pixel size
float x, y;
widget.GetScreenPos(x, y);                      // read pixel position
float w, h;
widget.GetScreenSize(w, h);                     // read pixel size
```

### Widget Flags — Alignment
```
// Set/clear flags at runtime:
widget.ClearFlags(flagMask);
widget.SetFlags(newFlags);
widget.Update();                                // MUST call after flag changes

// Horizontal: V_LEFT=0x00, V_CENTER=0x140, V_RIGHT=0x100 (mask: 0x1C0)
// Vertical: H_TOP=0x00, H_CENTER=0xA00, H_BOTTOM=0x800 (mask: 0xE00)
// Position clear mask: 0xFC0
// Text: TEXT_LEFT=0x0, TEXT_CENTER=0x100000, TEXT_RIGHT=0x400000 (mask: 0x500000)
```

### Visibility Checks
```
widget.IsVisibleHierarchy();                    // true only if ALL parents visible
widget.IsVisible();                             // this widget only
```

### Widget.TranslateString() — Static Localization
```
string translated = Widget.TranslateString("#STR_MY_KEY");
// Works without a widget instance — static method
// Handles multiple #keys in one string:
// "Hello #STR_WORLD" → "Hello World"
```

### CanvasWidget Drawing
```
CanvasWidget canvas;
// Drawing primitives available for custom rendering
// Used by LBmaster for QR code generation
```

### Global Widget Functions
```
Widget hovered = GetWidgetUnderCursor();         // widget under mouse
Widget focused = GetFocus();                     // focused widget
int mx, my;
GetMousePos(mx, my);                            // mouse position in pixels
int sw, sh;
GetScreenSize(sw, sh);                          // screen resolution
```
