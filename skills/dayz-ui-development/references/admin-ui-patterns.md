# Admin UI Patterns — Floating Windows, ESP, Advanced Widgets

Extracted from LBmaster_AdminTools + LBmaster_Garage production code.

---

## 1. RESIZABLE FLOATING WINDOW SYSTEM

IDE-like windowing with drag, resize from all edges, pin-to-stay, z-priority:

**Architecture:**
- `LBAdminMenuFrame` base class — one per panel (PlayerInfo, ESP, ItemSpawner, etc)
- Each frame: own layout loaded into shared frame container with header/resize handles
- `LBAdminMenuMain` registers frames by classname → `typename.Spawn()` instantiation
- Frame order user-configurable via drag & drop with persistent save

**Resize from 8 edges/corners:**
```
// Detect which edge is under cursor
if (LBWidgetUtils.IsUnderMouse(resize_bottom_right)) { resizeBottom = true; resizeRight = true; }
// Per-frame update:
if (resizeBottom) {
    int diffY = dragStartY - mouseY;
    dragStartY = mouseY;
    float w, h;
    frame.GetScreenSize(w, h);
    frame.SetScreenSize(w, h - diffY);
}
// Clamp to min size + screen bounds
```

**Window persistence:**
- Save: position/size normalized by `heightScale` (DPI scaling)
- Restore: multiply by `heightScale` on load
- 9 preset slots: each stores all window positions/sizes → hotkey switch

**Z-priority:** `frame.SetSort(120)` for focused, `frame.SetSort(0)` for unfocused.
Exception: frames containing `MapWidget` or `ItemPreviewWidget` get lower sort (render bug workaround).

---

## 2. ESP — WORLD TO SCREEN PER-FRAME

Render labels for thousands of entities in world space:

```
// Setup: scan all entities
DayZPlayerUtils.SceneGetEntitiesInBox("0 -1000 0", Vector(mapSize, 10000, mapSize), allItems);

// Per frame:
vector camPos = g_Game.GetCurrentCameraPosition();
for (int i = 0; i < allItems.Count(); i++) {
    EntityAI item = allItems.Get(i);
    vector pos = item.GetPosition();

    // Use head bone for living entities
    PlayerBase pb = PlayerBase.Cast(item);
    if (pb) {
        int bone = pb.GetBoneIndexByName("Head");
        if (bone != -1) pos = pb.GetBonePositionWS(bone);
    }

    float distance = vector.Distance(pos, camPos);
    vector screen = g_Game.GetScreenPos(pos);

    if (screen[2] > 0 && screen[0] > 0 && screen[1] > 0) { // Behind camera check
        widget.SetScreenPos(screen[0], screen[1]);
        widget.Show(true);
        widget.SetSort(1000 - ((int)Math.Clamp(distance, 0, 1000))); // Nearer = higher z
        distanceText.SetText("(" + ((int)distance) + "m)");
    } else {
        widget.Show(false);
    }
}
```

**Entity registration pattern:**
- Each entity class (`ItemBase`, `PlayerBase`, `AnimalBase`, `ZombieBase`, `CarScript`, `BoatScript`) has modded constructor that adds to ESP if enabled
- `EEHealthLevelChanged` updates health indicator
- `EEItemLocationChanged` re-adds/removes when item moves to/from ground

---

## 3. SKELETON RENDERING VIA CANVASWIDGET

```
CanvasWidget canvas; // Cleared each frame with canvas.Clear()

void DrawBones(PlayerBase player, int thickness, TStringArray boneNames) {
    vector lastScreen; bool lastVisible = false;
    foreach (string boneName : boneNames) {
        int bone = player.GetBoneIndexByName(boneName);
        if (bone < 0) continue;
        vector world = player.GetBonePositionWS(bone);
        vector screen = g_Game.GetScreenPos(world);
        if (screen[2] <= 0) { lastVisible = false; continue; }
        if (lastVisible) {
            canvas.DrawLine(screen[0], screen[1], lastScreen[0], lastScreen[1], thickness, color);
        }
        lastScreen = screen; lastVisible = true;
    }
}
```

Bone chains for players: pelvis→spine→spine1→spine2→spine3→neck→neck1→head→face_forehead
Arms: lefthand→leftforearmroll→leftforearm→leftarmroll→leftarm→neck→rightarm...
Legs: righttoebase→rightfoot→rightlegroll→rightleg→rightupleg→pelvis

Adaptive thickness: 3px at <10m, 2px at <100m, 1px beyond.

---

## 4. BOX SELECTION

```
// On shift+drag start:
GetMousePos(selectX, selectY);
panel_selection.Show(true);

// Per frame during drag:
int mouseX, mouseY; GetMousePos(mouseX, mouseY);
int w = mouseX - selectX, h = mouseY - selectY;
int x = selectX, y = selectY;
if (w < 0) { x = mouseX; w = -w; }
if (h < 0) { y = mouseY; h = -h; }
panel_selection.SetScreenPos(x, y);
panel_selection.SetSize(w, h);

// Hit test all ESP widgets:
foreach widget: if (x < wX && y < wY && x+w >= wX && y+h >= wY) → selected
```

---

## 5. WIDGET APIs — EXTENDED

### TextListboxWidget (full API)
```
list.AddItem(text, data, column, row)  // data = Param1<Class> for object storage
list.SetItem(row, text, data, column)  // Update existing
list.SetItemColor(row, column, ARGB)   // Per-cell color
list.GetItemData(row, column, out data) // Read stored data
list.GetSelectedRow()                   // -1 if none
list.GetNumItems()                      // Total count
list.SelectRow(int)                     // Programmatic selection
list.ClearItems()                       // Clear all
```

### SliderWidget (full API)
```
slider.SetMinMax(min, max)
slider.SetStep(step)
slider.SetCurrent(value)
float val = slider.GetCurrent()
```

### XComboBoxWidget
```
combo.ClearAll()
combo.AddItem(text)
combo.SetCurrentItem(index)
int idx = combo.GetCurrentItem()
```

### ImageWidget
```
image.LoadImageFile(0, "path/to/icon.paa")
image.SetColor(ARGB(255, 0, 255, 0))
```

### TextWidget extras
```
txt.SetTextExactSize(int pixelSize)  // Exact pixel font size
txt.SetOutline(size, ARGB_color)     // Outline with separate alpha
int outlineColor = txt.GetOutlineColor()
int outlineSize = txt.GetOutlineSize()
```

### Widget extras
```
widget.SetSort(int)              // Z-order (higher = in front)
widget.SetRotation(x, y, z)     // Degrees
Widget.Update()                  // Force layout recalculate
```

### Global functions
```
Widget GetWidgetUnderCursor()    // Hit test at mouse pos
GetMousePos(out int x, out int y)
SetFocus(Widget)                 // null = clear focus
CancelWidgetDragging()
Widget GetDragWidget()
GetMouseState(MouseState.LEFT) & MB_PRESSED_MASK  // Raw mouse state
```

### PlayerPreviewWidget
```
m_CharacterPanelWidget.SetPlayer(player)       // Set displayed player
m_CharacterPanelWidget.UpdateItemInHands(item)  // Update held item
m_CharacterPanelWidget.GetDummyPlayer()         // Get preview dummy
m_CharacterPanelWidget.Refresh()                // Force refresh
```

---

## 6. MULTI-RESOLUTION SCALING SYSTEM

Design base: **1920×1080**. Everything scales proportionally at runtime.

### Core Variables

```
static int screenWidth, screenHeight;
static float heightScale;    // screenHeight / 1080.0
static float widthScale;     // screenWidth / 1920.0

static void UpdateScreenDimensions() {
    GetScreenSize(screenWidth, screenHeight);
    heightScale = ((float) screenHeight) / 1080.0;
    widthScale  = ((float) screenWidth) / 1920.0;
}
```

Called once in `DayZGame` constructor + on `WindowsResizeEventTypeID` event.

### The Rule: heightScale for EVERYTHING

`heightScale` is used for **all** dimensions — including widths. This keeps elements
square/proportional on any resolution. `widthScale` exists but is almost never used.

```
// Text: "16px at 1080p"
float realSize = 16 * LBWidgetUtils.heightScale;
txt.SetTextExactSize(realSize);

// Image: "300×200 at 1080p"
img.SetScreenSize(300 * heightScale, 200 * heightScale);

// Gap/margin: "10px at 1080p"
float gap = 10.0 * heightScale;

// Position: "place at 500,300 in 1080p coords"
widget.SetScreenPos(500 * heightScale, 300 * heightScale);
```

### Saving/Restoring Window Properties

Normalize to 1080p-space when saving, scale back when restoring:

```
// SAVE — divide out the scale
entry.windowX = x / LBWidgetUtils.heightScale;
entry.windowY = y / LBWidgetUtils.heightScale;
entry.windowW = w / LBWidgetUtils.heightScale;
entry.windowH = h / LBWidgetUtils.heightScale;

// RESTORE — multiply back
widget.SetScreenPos(entry.windowX * heightScale, entry.windowY * heightScale);
widget.SetScreenSize(entry.windowW * heightScale, entry.windowH * heightScale);
```

This means saved positions work correctly if the user changes resolution between sessions.

### Dynamic Gaps (LBGapHandler pattern)

`ScriptedWidgetEventHandler` for margins that adapt to resolution:

```
// gapHorizontal/gapVertical come from layout via 'reference' keyword
float newW = width - ((float) gapHorizontal) * LBWidgetUtils.heightScale / parentW;
float newH = height - ((float) gapVertical) * LBWidgetUtils.heightScale / parentH;
root.SetSize(newW, newH);
```

### Image Fit (Aspect-Ratio Preserving)

Scale image to fit container while maintaining aspect ratio:

```
// Get image natural size + container size
float imgW, imgH, containerW, containerH;
// Calculate scale factors
float scaleW = containerW / imgW;
float scaleH = containerH / imgH;
// If fits at natural size → use it. Otherwise scale by limiting axis
float min = Math.Min(scaleW, scaleH);
img.SetScreenSize(imgW * min, imgH * min);
```

### Auto-Fitting Text Size

Loop to find largest font that fits within parent width:

```
void FitText(TextWidget txt, int maxSize, int minSize) {
    float w, h, parentW, parentH;
    txt.GetParent().GetScreenSize(parentW, parentH);
    int current = maxSize;
    while (current >= minSize) {
        txt.SetTextExactSize(current);
        txt.Update();  // Force layout recalc
        txt.GetScreenSize(w, h);
        if (w < parentW * 0.9)
            break;
        --current;
    }
}
```

### What DOESN'T Need Scaling

- **Layout coordinates in 0.0–1.0 range** (relative/proportional) — engine handles these
- **SpacerWidget/WrapSpacerWidget children** — auto-flow is resolution-independent
- **Widget.SetSize(w, h)** with values 0.0–1.0 — these are proportional to parent

**Only pixel-absolute values need the multiplier:** `SetScreenSize`, `SetScreenPos`,
`SetTextExactSize`, pixel gaps, and any hardcoded distances used in hit-testing or
screen-space math.

---

## 7. PIN/NUMPAD UI

Keyboard intercept via `MissionGameplay.OnKeyPress(int key)`:
```
override void OnKeyPress(int key) {
    super.OnKeyPress(key);
    UIScriptedMenu menu = g_Game.GetUIManager().GetMenu();
    MyPinMenu pinMenu;
    if (Class.CastTo(pinMenu, menu))
        pinMenu.OnKeyNumpadPressed(key);
}
```

KeyCode mapping: `KC_NUMPAD0`-`KC_NUMPAD9`, `KC_0`-`KC_9`, `KC_BACK`, `KC_NUMPADENTER`, `KC_RETURN`

---

## 8. CAMERA PREVIEW IN MENU

Orbital camera for showing vehicles/items in garage-style UI:

```
// Calculate orbital position:
float height = Math.Sin(Math.DEG2RAD * angle) * distance;
float cos = Math.Cos(Math.DEG2RAD * rotation) * distance;
float sin = Math.Sin(Math.DEG2RAD * rotation) * distance;
vector cameraPos = center + Vector(sin, height, cos);
```

Blackbox pattern: spawn invisible building at y=109, display items inside it, override world time to noon per frame.

---

## 9. LOOKING AROUND WITHOUT MENU CLOSE

Toggle cursor visibility + input exclusions for camera control inside UI:
```
// Start looking around:
Mission mission = g_Game.GetMission();
mission.RemoveActiveInputExcludes({"menu", "movement", "aiming"}, true);
g_Game.GetUIManager().ShowUICursor(false);

// Stop:
mission.AddActiveInputExcludes({"movement", "aiming", "menu"});
g_Game.GetUIManager().ShowUICursor(true);
```
