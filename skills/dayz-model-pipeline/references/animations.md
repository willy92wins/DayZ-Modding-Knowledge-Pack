# DayZ Model.cfg Animation System Reference

Complete reference for model.cfg animations in DayZ objects. Covers skeleton definition, animation types, script control, and working examples.

## 1. Model.cfg Structure Overview

The animation system requires two main class blocks in `model.cfg`:

### CfgSkeletons (Bone Structure)

Defines the bone hierarchy used by animations:

```cpp
class CfgSkeletons {
    class MyObject_Skeleton {
        isDiscrete = 1;                    // 1 for mechanical objects (no interpolation)
        skeletonInherit = "";              // empty for new skeleton, or inherit from parent
        skeletonBones[] = {
            "switch", "",                  // bone_name, parent_bone (empty = root)
            "button", "",
            "led_indicator", "",
            "cover", ""
        };
    };
};
```

**Key Points:**
- `isDiscrete = 1` → Mechanical objects (switches, doors). Prevents interpolation artifacts.
- `isDiscrete = 0` → Smooth/organic movement (flags, cloth).
- Parent `""` = root bone (world origin). Most DayZ objects use root for all bones.
- Bone names MUST match selection names in the p3d file.

### CfgModels (Visual Properties & Animations)

Defines model appearance and animation classes:

```cpp
class CfgModels {
    class Default {
        // base class - empty
    };

    class MyObject: Default {
        skeletonName = "MyObject_Skeleton";  // link to skeleton
        sections[] = {
            "led_green",
            "led_red"                        // hiddenSelections for material swaps
        };
        class Animations {
            // animation definitions here (see section 2)
        };
    };
};
```

**sections[]** = Named selections that can have materials swapped via `SetObjectTexture()`.

---

## 2. Animation Types (Complete Syntax)

### ROTATION (Most Common)

For rotating parts: switches, dials, valves, lids.

```cpp
class switch_rotate {
    type = "rotation";
    source = "switch_state";              // AnimationSource name (from config.cpp)
    selection = "switch";                 // Named selection in p3d (must match bone)
    axis = "switch_axis";                 // 2 memory points defining rotation axis
    minValue = 0;                         // source value at angle0
    maxValue = 1;                         // source value at angle1
    angle0 = 0;                           // radians when source = minValue
    angle1 = "rad 45";                    // radians when source = maxValue
    // angle1 = 0.7854;                   // alternative: direct radians (45° = 0.7854)
};
```

**How it works:**
- The axis is a line in 3D space defined by two memory points.
- When `source` = minValue, the selection rotates by `angle0` around the axis.
- When `source` = maxValue, the selection rotates by `angle1` around the axis.
- Linear interpolation between minValue and maxValue.
- Right-hand rule: thumb along axis, fingers curl = positive rotation direction.

---

### TRANSLATION (Linear Movement)

For moving parts: buttons, sliders, drawers, pistons.

```cpp
class button_press {
    type = "translation";
    source = "button_state";
    selection = "button";
    axis = "button_axis";                 // 2 memory points, direction = point1 → point2
    minValue = 0;
    maxValue = 1;
    offset0 = 0;                          // meters movement when source = minValue
    offset1 = 0.003;                      // 3mm when source = maxValue
};
```

**How it works:**
- Translation follows the axis direction (from point 1 to point 2 of the axis).
- `offset0` = 0, `offset1` = 0.003 means travel 3mm total.
- At source = 0.5, the selection moves 1.5mm along the axis.
- Movement is linear with source value.

---

### HIDE (Show/Hide Based on State)

For discrete visibility: LED indicators, cover panels, interchangeable parts.

```cpp
class hide_cover {
    type = "hide";
    source = "cover_open";
    selection = "cover";
    minValue = 0;
    maxValue = 1;
    hideValue = 0.5;                      // hidden when source >= hideValue
};
```

**How it works:**
- When `source >= hideValue` → selection is hidden.
- When `source < hideValue` → selection is visible.
- No intermediate states: binary on/off.

**Variant: Hide with Inverse Logic**
```cpp
class hide_battery_missing {
    type = "hide";
    source = "battery_installed";
    hideValue = 0.5;
    minValue = 0;
    maxValue = 1;
    // Hidden when source >= 0.5 (battery NOT installed = source 0)
    // Visible when source < 0.5 (battery installed = source 1)
};
```

---

### ROTATIONX, ROTATIONY, ROTATIONZ (Axis-Locked)

For rotation around a single fixed axis: dials with full 360° rotation.

```cpp
class dial_rotate {
    type = "rotationZ";                   // Z axis rotation
    source = "dial_value";
    selection = "dial";
    axis = "";                            // NOT needed for axis-locked types
    angle0 = 0;                           // radians at minValue
    angle1 = "rad 270";                   // 270° = 3/4 rotation at maxValue
    minValue = 0;
    maxValue = 1;
};
```

**Axis-Locked Types:**
- `rotationX` → Rotate around X axis (pitch)
- `rotationY` → Rotate around Y axis (yaw)
- `rotationZ` → Rotate around Z axis (roll)

**When to use:**
- Use when you only need rotation on one axis and the axis never changes.
- More stable than "rotation" type for full 360° (avoids gimbal lock).
- Axis memory points NOT required.

---

## 3. Animation Sources (config.cpp)

Define animation sources in the object's config.cpp class:

```cpp
class CfgVehicles {
    class MyObject: HouseNoDestruct {
        model = "\path\to\myobject.p3d";
        displayName = "My Device";

        class AnimationSources {
            class switch_state {
                source = "user";           // "user" = script-controlled
                initPhase = 0;             // initial value (0.0 to 1.0)
                animPeriod = 0.5;          // seconds to complete full animation
                sound = "";                // optional click sound EH
            };

            class button_state {
                source = "user";
                initPhase = 0;
                animPeriod = 0.1;          // faster: 100ms button press
            };

            class cover_open {
                source = "user";
                initPhase = 0;
                animPeriod = 0.8;          // slower: 800ms for smooth reveal
            };
        };
    };
};
```

**Key Properties:**

| Property | Purpose |
|----------|---------|
| `source = "user"` | Script controls animation via SetAnimationPhase() |
| `initPhase = X` | Starting value (0.0 = minValue, 1.0 = maxValue) |
| `animPeriod = X` | Time in seconds to complete full animation (0→1 range) |
| `sound = "..."` | Sound event hash (optional) |

**CRITICAL:** `animPeriod` is NOT the duration of a single SetAnimationPhase call. It's the time the animation takes to play from phase 0 to phase 1. If you call `SetAnimationPhase("switch_state", 1.0)` with `animPeriod = 0.5`, the animation visually plays over 0.5 seconds.

---

## 4. Script Control (Enforce Script)

### Server-Side Animation Control

```cpp
// Set animation phase (0.0 = minValue, 1.0 = maxValue)
SetAnimationPhase("switch_state", 1.0);

// Get current phase
float currentPhase = GetAnimationPhase("switch_state");

// Example: Toggle switch
if (GetAnimationPhase("switch_state") < 0.5) {
    SetAnimationPhase("switch_state", 1.0);  // on
} else {
    SetAnimationPhase("switch_state", 0.0);  // off
}
```

**IMPORTANT:** `SetAnimationPhase()` is **server-only** for networked objects. The animation state is stored in a SyncVar and automatically syncs to all clients. DO NOT call from client scripts.

### Complete Example: Toggle Switch (EventHandler)

```cpp
// In config.cpp AnimationSources
class switch_state {
    source = "user";
    initPhase = 0;
    animPeriod = 0.3;
};

// In Enforce Script (on the object instance)
void ToggleSwitch() {
    float phase = GetAnimationPhase("switch_state");
    if (phase < 0.5) {
        SetAnimationPhase("switch_state", 1.0);  // animation plays to 1.0 over 0.3s
    } else {
        SetAnimationPhase("switch_state", 0.0);  // animation plays to 0.0 over 0.3s
    }
}
```

---

## 5. Memory Points for Axes

In Blender/O2 p3d editor, create a Memory LOD with axis definition points.

### Axis Structure

Each animation using an axis requires exactly 2 memory points in the Memory LOD:

```
Axis Name: "switch_axis"
├── Point 1: (0, 0, 0.05)    [line start]
└── Point 2: (0, 0, -0.05)   [line end]
```

The axis vector is: Point2 - Point1 = direction of rotation/translation.

### Placement Rules

1. **Rotation Axis:**
   - Place at the pivot point of the rotating part.
   - Direction (P1→P2) determines rotation axis.
   - Right-hand rule applies: curl fingers in rotation direction, thumb points along axis.

   Example: Door hinge at bottom-left corner:
   ```
   "door_axis"
   P1: (-0.5, 0, 0)     [bottom of hinge]
   P2: (-0.5, 1, 0)     [top of hinge, axis = Y direction]
   Rotation: Y axis (pitch) opens/closes door
   ```

2. **Translation Axis:**
   - P1→P2 vector = direction and magnitude reference.
   - `offset` values apply along this direction.
   - Example: Sliding panel moving left 0.2m:
   ```
   "panel_slide_axis"
   P1: (0, 0, 0)
   P2: (-1, 0, 0)       [normalized to -X direction]
   offset1 = 0.2        [moves -0.2m in X]
   ```

3. **Scale:**
   - Axis vector doesn't define scale; only direction matters.
   - Can use (0,0,0)→(0,0,1) or (0,0,0)→(0,0,100) — both are Z axis.

---

## 6. Skeleton Bones

Bones form the animated skeleton. Each animated selection MUST have a corresponding bone.

### Basic Skeleton (Flat Hierarchy)

Most DayZ objects use flat hierarchy (all bones parented to root):

```cpp
class CfgSkeletons {
    class SimpleDevice_Skeleton {
        isDiscrete = 1;
        skeletonBones[] = {
            "switch", "",      // all rooted
            "button", "",
            "cover", "",
            "led", ""
        };
    };
};
```

### Hierarchical Skeleton (Chains)

For multi-part movements (arm → forearm → hand):

```cpp
class Arm_Skeleton {
    isDiscrete = 1;
    skeletonBones[] = {
        "arm", "",           // root
        "forearm", "arm",    // child of arm
        "hand", "forearm"    // child of forearm
    };
};
```

Parent relationships:
- Child inherits parent's transformation.
- If `arm` rotates 45°, `forearm` and `hand` rotate with it.
- Then `forearm` rotates an additional amount independently.

### Requirements

- Bone name MUST match the selection name in the p3d.
- Each selection to be animated needs a bone.
- Non-animated selections don't need bones.
- Parent bone must be declared BEFORE child bone in skeletonBones[].

---

## 7. Named Selections Across LODs

DayZ p3d files use multiple LODs: Resolution, Geometry, Fire, View, etc.

### Animated Selections

- **MUST exist** in **Resolution LOD** (visual model).
- The vertices in the selection = vertices that move with animation.
- DO NOT need to exist in Geometry/Fire/View LODs.

### Named Selection Best Practice

```
MyObject.p3d
├── LOD 1000 (Resolution)
│   ├── Geometry
│   │   ├── switch (named selection - WILL ANIMATE)
│   │   ├── button
│   │   ├── cover
│   │   └── housing
│   └── Named Selections: switch, button, cover
│
├── LOD 5000 (Geometry)
│   └── Geometry
│       ├── switch, button, cover, housing (combined or separate)
│       └── NO named selections (optional - animation ignored at this LOD)
│
└── Memory LOD
    └── switch_axis, button_axis, cover_axis (axis memory points)
```

### Selection Priority

If a vertex is in multiple named selections:
- The LAST animation in the Animations class wins.
- Example: If "button" vertex is in both "button" and "housing", and both have animations, the button animation takes precedence.

---

## 8. Common Animation Patterns for DayZ Devices

### Toggle Switch (On/Off)

```cpp
// model.cfg
class switch_on_off {
    type = "rotation";
    source = "switch_state";
    selection = "switch";
    axis = "switch_axis";
    minValue = 0;
    maxValue = 1;
    angle0 = "rad -22.5";    // -22.5° at OFF (0)
    angle1 = "rad 22.5";     // +22.5° at ON (1)
};

// config.cpp
class switch_state {
    source = "user";
    initPhase = 0;
    animPeriod = 0.3;
};
```

### Push Button (Momentary)

```cpp
class button_press {
    type = "translation";
    source = "button_state";
    selection = "button";
    axis = "button_axis";
    minValue = 0;
    maxValue = 1;
    offset0 = 0;             // resting
    offset1 = 0.003;         // 3mm down
};

// config.cpp animPeriod
class button_state {
    source = "user";
    initPhase = 0;
    animPeriod = 0.1;        // 100ms press/release
};

// Script (resets button after press)
void PressButton() {
    SetAnimationPhase("button_state", 1.0);
    GetGame().GetCallQueue(CALL_CATEGORY_SYSTEM).CallLater(this, "ReleaseButton", 150);  // 150ms
}

void ReleaseButton() {
    SetAnimationPhase("button_state", 0.0);
}
```

### Hinged Door/Lid (90° Swing)

```cpp
class lid_open {
    type = "rotation";
    source = "lid_state";
    selection = "lid";
    axis = "lid_hinge";      // hinge axis (usually Y for vertical hinge)
    minValue = 0;
    maxValue = 1;
    angle0 = 0;              // closed
    angle1 = "rad 90";       // 90° open
};

// config.cpp
class lid_state {
    source = "user";
    initPhase = 0;
    animPeriod = 0.8;        // smooth 800ms open
};
```

### Multi-State Dial (Discrete Positions)

```cpp
class dial_select {
    type = "rotationZ";      // full 360° rotation
    source = "dial_state";
    selection = "dial";
    angle0 = 0;
    angle1 = "rad 360";      // full rotation
    minValue = 0;
    maxValue = 1;
};

// config.cpp
class dial_state {
    source = "user";
    initPhase = 0;
    animPeriod = 0.5;
};

// Script: 4 discrete positions
void SetDialPosition(int position) {
    // position: 0, 1, 2, 3
    float phase = position / 4.0;  // 0.0, 0.25, 0.5, 0.75
    SetAnimationPhase("dial_state", phase);
}
```

### Sliding Panel (Drawer)

```cpp
class drawer_slide {
    type = "translation";
    source = "drawer_state";
    selection = "drawer";
    axis = "drawer_axis";    // axis points along slide direction (-X)
    minValue = 0;
    maxValue = 1;
    offset0 = 0;             // fully closed
    offset1 = 0.4;           // 40cm extended
};

// config.cpp
class drawer_state {
    source = "user";
    initPhase = 0;
    animPeriod = 0.6;
};
```

---

## 9. Multiple Animations

A single object can have many animations controlled independently or together.

### Independent Animations (Different Sources)

```cpp
class Animations {
    class switch_rotate {
        type = "rotation";
        source = "switch_state";
        selection = "switch";
        // ...
    };

    class button_press {
        type = "translation";
        source = "button_state";
        selection = "button";
        // ...
    };

    class led_indicator {
        type = "hide";
        source = "led_state";
        selection = "led";
        hideValue = 0.5;
    };
};
```

Script controls each independently:
```cpp
SetAnimationPhase("switch_state", 1.0);  // switch moves
SetAnimationPhase("button_state", 1.0);  // button moves
SetAnimationPhase("led_state", 1.0);     // LED shows
// All three happen at the same time, but driven by different sources
```

### Linked Animations (Same Source)

Multiple animations can share a source to move together:

```cpp
class Animations {
    class door_left {
        type = "rotation";
        source = "both_doors";  // SAME source
        selection = "door_left";
        axis = "door_left_axis";
        angle0 = 0;
        angle1 = "rad 90";
    };

    class door_right {
        type = "rotation";
        source = "both_doors";  // SAME source
        selection = "door_right";
        axis = "door_right_axis";
        angle0 = 0;
        angle1 = "rad -90";     // opposite direction
    };
};
```

Script:
```cpp
SetAnimationPhase("both_doors", 0.5);  // both doors move together at phase 0.5
```

---

## 10. Complete Working Example: Industrial Switch Box

Full functional example: a device with toggle switch, push button, RGB LED (material swap), and hinged cover.

### model.cfg

```cpp
class CfgSkeletons {
    class SwitchBox_Skeleton {
        isDiscrete = 1;
        skeletonBones[] = {
            "switch", "",
            "button", "",
            "cover", "",
            "led_indicator", ""
        };
    };
};

class CfgModels {
    class Default {};

    class SwitchBox: Default {
        skeletonName = "SwitchBox_Skeleton";
        sections[] = {"led_green", "led_red", "led_blue"};

        class Animations {
            class switch_toggle {
                type = "rotation";
                source = "switch_state";
                selection = "switch";
                axis = "switch_axis";
                minValue = 0;
                maxValue = 1;
                angle0 = "rad -30";
                angle1 = "rad 30";
            };

            class button_press {
                type = "translation";
                source = "button_state";
                selection = "button";
                axis = "button_axis";
                minValue = 0;
                maxValue = 1;
                offset0 = 0;
                offset1 = 0.005;
            };

            class cover_hinge {
                type = "rotation";
                source = "cover_state";
                selection = "cover";
                axis = "cover_hinge_axis";
                minValue = 0;
                maxValue = 1;
                angle0 = 0;
                angle1 = "rad 120";
            };

            class led_hide {
                type = "hide";
                source = "led_state";
                selection = "led_indicator";
                minValue = 0;
                maxValue = 1;
                hideValue = 0.5;
            };
        };
    };
};
```

### config.cpp

```cpp
class CfgVehicles {
    class HouseNoDestruct;

    class SwitchBox: HouseNoDestruct {
        model = "\path\to\switchbox.p3d";
        displayName = "Industrial Switch Box";
        descriptionShort = "Functional control panel";

        class AnimationSources {
            class switch_state {
                source = "user";
                initPhase = 0;
                animPeriod = 0.4;
            };

            class button_state {
                source = "user";
                initPhase = 0;
                animPeriod = 0.15;
            };

            class cover_state {
                source = "user";
                initPhase = 0;
                animPeriod = 1.0;
            };

            class led_state {
                source = "user";
                initPhase = 0;
                animPeriod = 0.2;
            };
        };
    };
};
```

### Usage (Enforce Script)

```cpp
SwitchBox switchBox = GetGame().CreateObjectEx("SwitchBox", position);

// Toggle switch
void ToggleSwitch() {
    if (GetAnimationPhase("switch_state") < 0.5) {
        SetAnimationPhase("switch_state", 1.0);
        SetObjectTexture(switchBox, 0, "\path\to\led_green.paa");  // green LED
    } else {
        SetAnimationPhase("switch_state", 0.0);
        SetObjectTexture(switchBox, 0, "\path\to\led_red.paa");    // red LED
    }
}

// Press button with release
void PressButton() {
    SetAnimationPhase("button_state", 1.0);
    GetGame().GetCallQueue(CALL_CATEGORY_SYSTEM).CallLater(this, "ReleaseButton", 100);
}

void ReleaseButton() {
    SetAnimationPhase("button_state", 0.0);
}

// Open cover
void OpenCover() {
    SetAnimationPhase("cover_state", 1.0);  // smoothly opens over 1.0 second
}

// Show LED when condition met
void SetLEDActive(bool active) {
    SetAnimationPhase("led_state", active ? 1.0 : 0.0);
}
```

---

## 11. Common Mistakes & Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| Animation doesn't work (no error) | Axis points not in Memory LOD | Add axis memory points to Memory LOD in editor |
| Silent failure, no animation | Selection name mismatch (p3d vs model.cfg) | Verify selection name matches exactly (case-sensitive) |
| Crash on load | Missing bone in skeleton | Add bone to `skeletonBones[]` for every animated selection |
| Animation jittery/twitchy | `isDiscrete = 0` on mechanical object | Set `isDiscrete = 1` for mechanical parts |
| Animation plays instantly | `animPeriod = 0` | Set `animPeriod` to > 0 (e.g., 0.5 seconds) |
| Animation doesn't reach maxValue | Axis vector is zero | Ensure axis P1 ≠ P2 (non-zero vector) |
| Wrong rotation direction | Axis vector points wrong way | Swap P1 and P2, or negate angle values |
| Multiple animations fight | Same selection in different animations | Ensure each selection is in only one animation |
| Bone inherits wrong transform | Bone parent mismatch | Parent bone must be declared first in `skeletonBones[]` |

---

## Reference: Radians Conversion

```
"rad 45"   = 45° = 0.7854 radians
"rad 90"   = 90° = 1.5708 radians
"rad 180"  = 180° = 3.1416 radians
"rad 270"  = 270° = 4.7124 radians
"rad 360"  = 360° = 6.2832 radians
```

Use `"rad X"` syntax in model.cfg for readability, or calculate radians directly: `angle = degrees * π / 180`.

---

## Key Takeaways

1. **Skeleton** defines bone hierarchy; each animated selection needs a bone.
2. **Animation classes** in model.cfg link bone to visual result (rotation/translation/hide).
3. **AnimationSources** in config.cpp define the source state and timing.
4. **Memory points** define axes for rotation and translation; MUST be in Memory LOD.
5. **SetAnimationPhase()** controls animation from script (server-only for synced objects).
6. **isDiscrete = 1** prevents jitter on mechanical objects.
7. **Named selections** must exist in Resolution LOD but can be absent from lower LODs.

<!-- [merged 2026-06-05 from <claude-home>\skills user copy during plugin-canonical migration] -->
### Screen on/off: two-layer translation pattern (vs. material swap)

For a device that needs an **emissive lit screen** when "on" and a black
screen when "off", there are two valid approaches. Don't mix them:

**Pattern A — Translation animation over an emissive face (recommended)**

The model has two overlapping face sets in the same selection slot:
- A `screen` selection with the emissive texture (`_Emission.paa`, etc.).
- A `HideScreen` selection with a black/off texture, positioned a hair
  above `screen` so it covers it at rest.

A translation animation physically slides `HideScreen` out of view when
the device is on, exposing the emission underneath:

```cpp
// model.cfg
class HideScreen {
    type       = "translation";
    source     = "user";
    selection  = "HideScreen";
    axis       = "HideScreen_axis";      // 2-point memory axis
    minValue   = 0.0;
    maxValue   = 1.0;
    offset0    = 0.0;
    offset1    = 0.5;                    // 0.5m — well off-screen
};
```

```cpp
// config.cpp — two variants of the same model
class MyDevice_Admin : Inventory_Base  // always-on variant
{
    class AnimationSources { class HideScreen { source="user"; initPhase=1; animPeriod=0.3; }; };
    // HideScreen cover hidden from spawn → emission visible
};

class MyDevice : Inventory_Base         // power-gated variant
{
    class AnimationSources { class HideScreen { source="user"; initPhase=0; animPeriod=0.3; }; };
    // Starts with cover visible (off look); script toggles.
};
```

```c
// Enforce Script — in OnVariablesSynchronized / LFPG_OnVarSync
if (m_PoweredNet) SetAnimationPhase("HideScreen", 1.0);  // hide cover → emission shows
else              SetAnimationPhase("HideScreen", 0.0);  // show cover → black screen
```

**Pattern B — Material swap via `hiddenSelections`**

Swap the screen face's `.rvmat` at runtime. Works for solid-color LEDs but
**fails silently for textured screens** when the replacement rvmat uses
procedural `#(argb,…)color(...)` stages — the engine renders black.

**Choosing:** if the "on" look needs a real texture (logo, gradient, UI
bitmap) → use Pattern A. If it's a single emissive color dot → use
`hiddenSelections` with Normal/Basic shader rvmats (see
`emissive-leds-and-dynamic-lights.md`, Pattern A).

**Pitfall — don't combine them:** if you register the screen selection
in `hiddenSelections[]` AND drive it with a translation animation, the
engine does both (swap material + translate), which usually breaks one
of the two effects. Keep the animated selection OUT of `hiddenSelections`.

---
