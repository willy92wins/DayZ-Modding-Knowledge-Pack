# DayZ 3D Viewer — States, Animations & LEDs Reference

## Architecture Overview

Three separate files define the interactive behavior of a DayZ model:

```
P3D (geometry)          model.cfg (animations)       config.cpp (runtime states)
├─ Visual LODs          ├─ CfgSkeletons              ├─ CfgVehicles
│  ├─ faces             │  └─ skeletonBones[]         │  ├─ model = "..p3d"
│  ├─ selections        ├─ CfgModels                  │  ├─ hiddenSelections[]
│  │  ├─ "switch"       │  ├─ sections[]              │  ├─ hiddenSelectionsTextures[]
│  │  ├─ "light_led"    │  └─ Animations{}            │  ├─ hiddenSelectionsMaterials[]
│  │  └─ "camo"         │     ├─ type                 │  └─ AnimationSources{}
│  └─ textures/mats     │     ├─ selection            │     ├─ source = "user"
├─ Memory LOD           │     ├─ axis                 │     ├─ initPhase = 0
│  ├─ "switch_axis"     │     ├─ offset0/offset1      │     └─ animPeriod = 0.3
│  ├─ "actionPos"       │     └─ angle0/angle1        │
│  └─ "ce_center"       │                             │
└─ Geometry LODs        └─                            └─
```

## Data Flow: File → Viewer

### Step 1: P3D → Selections (ground truth)

The P3D file is the source of truth for geometry. Each visual LOD contains **named selections**
— groups of vertices/faces that can be animated or have their material swapped.

```python
# Selections overlap! A face can be in multiple selections.
# Example from LFPG Push Button:
#
# Selection         | Points | Faces | Role
# ------------------|--------|-------|------
# "zbytek"          |    132 |   256 | Static housing + base plate
# "button_push"     |    196 |   384 | Animated part (button body + LED)
# "led_indicator"   |    130 |   256 | Material-swappable (LED only)
#
# Overlap: led_indicator ⊂ button_push (LED moves with the button AND changes color)
# No overlap: zbytek ∩ button_push = ∅ (static never moves)
# Coverage: every face is in at least one selection
```

**Key: selections are NOT mutually exclusive.** A face can be in an animation selection
AND a material-swap selection simultaneously (e.g., LED moves with button AND glows).

### Step 2: model.cfg → Animations

The `CfgModels` class matching the P3D filename defines:

**sections[]** — which P3D selections should be separated for material swap.
These MUST match selection names in the P3D exactly.

**Animations{}** — each animation entry has:

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | `"translation"` or `"rotation"` |
| `source` | string | Name of AnimationSource (from config.cpp) |
| `selection` | string | P3D selection name to move |
| `axis` | string | Memory LOD selection name (2 points defining axis) |
| `memory` | int | 1 = axis from Memory LOD, 0 = from geometry |
| `minValue` | float | Phase at which animation starts (0.0-1.0) |
| `maxValue` | float | Phase at which animation ends (0.0-1.0) |
| `offset0` | float | Translation at minValue (relative to axis length) |
| `offset1` | float | Translation at maxValue (relative to axis length) |
| `angle0` | float | Rotation at minValue (radians) |
| `angle1` | float | Rotation at maxValue (radians) |

**Translation math:**
```
axis_origin = Memory LOD point A of axis selection
axis_end    = Memory LOD point B of axis selection
axis_dir    = normalize(B - A)
axis_length = distance(A, B)

phase = clamp(source_value, minValue, maxValue)
t = (phase - minValue) / (maxValue - minValue)
displacement = lerp(offset0, offset1, t) * axis_length
new_position = original_position + axis_dir * displacement
```

**Rotation math:**
```
axis_origin  = Memory LOD point A of axis selection
axis_dir     = normalize(B - A)

phase = clamp(source_value, minValue, maxValue)
t = (phase - minValue) / (maxValue - minValue)
angle = lerp(angle0, angle1, t)    # radians
# Rotate all selection vertices around axis_origin by angle along axis_dir
```

**Sequential animations** (e.g., AND gate lid):
```
latches: minValue=0.0, maxValue=0.2, angle0=0, angle1=-0.5 rad (-28.6°)
lid:     minValue=0.2, maxValue=1.0, angle0=0, angle1=-1.5 rad (-85.9°)

phase 0.0→0.2: latches rotate, lid stays
phase 0.2→1.0: latches stop, lid rotates
```

### Step 3: config.cpp → Material States

`hiddenSelections[]` defines which P3D selections support runtime material/texture swap.
The textures and materials arrays are **index-aligned**:

```
hiddenSelections[]          = {"camo",           "switch",          "light_led"};
hiddenSelectionsTextures[]  = {"switch_co.paa",  "switch_co.paa",   ""};
hiddenSelectionsMaterials[] = {"switch.rvmat",   "switch.rvmat",    "led_off.rvmat"};
                               ↑ index 0         ↑ index 1          ↑ index 2
```

Scripts swap materials at runtime via:
```cpp
SetObjectMaterial(2, "path\\to\\led_green.rvmat");  // index 2 = light_led
SetObjectTexture(0, "path\\to\\alt_co.paa");         // index 0 = camo
```

**The alternative materials are NOT defined in config.** They come from script logic.
For LEDs, the convention is: `led_off.rvmat`, `led_green.rvmat`, `led_red.rvmat`.
The viewer should detect these by filename pattern or accept them as explicit input.

### Step 4: Memory LOD → Axes

Animation axes are defined by 2 points in the Memory LOD sharing a named selection:

```python
# "button_axis": 2 points
#   Point A = (0.0, 0.0, 0.023)
#   Point B = (0.0, 0.0, 0.041)
#   Direction = (0, 0, 1) — Z axis
#   Length = 0.018m
```

Other Memory LOD selections are NOT axes:
- 1 point = interaction point (actionPos, cable_attach, ce_center, port_*)
- 2 points = animation axis

## Real Examples from LFPG

### Switch V1 (translation + LED)
```
P3D selections: switch, light_led, camo
Animation: translation, selection="switch", axis="switch_axis", offset 0→0.5
LED: light_led section, default=led_off.rvmat, states=[led_green, led_red]
```

### Switch V2 (rotation + LED)
```
P3D selections: switch, light_led, camo
Animation: rotation, selection="switch", axis="switch_axis", angle 0→-3.0 rad (172°)
LED: light_led section, default=led_off.rvmat, states=[led_green, led_red]
```

### AND/OR/XOR Gate (sequential rotation + multi-LED)
```
P3D selections: unit, lid, latches, bolts, light_led_input0, light_led_input1, light_led_output0, camo, camosymbol
Animations:
  latches: rotation, phase 0.0→0.2, angle 0→-0.5 rad
  lid:     rotation, phase 0.2→1.0, angle 0→-1.5 rad
LEDs: light_led_input0, light_led_input1, light_led_output0 (each independently swappable)
```

### RF Broadcaster / Intercom (3 knobs + 2 LEDs)
```
P3D selections: camo, camoscreen, light_led, light_led2, microphone, knob_freq, knob_input, knob_vol
Animations:
  knob_freq:  rotation, angle 0→-4.712 rad (270°)
  knob_input: rotation, angle 0→-1.5708 rad (90°)
  knob_vol:   rotation, angle 0→-4.712 rad (270°)
LEDs: light_led, light_led2
Screen: camoscreen (texture swap for display)
```

### Fridge (door rotation + LED)
```
Animation: door rotation, angle 0→3.0 rad (172°)
LED: light_led
```

### Searchlight (pitch rotation + lens glow)
```
Animation: light_main rotation, angle 1.5708→-1.5708 rad (±90° pitch)
Glow: light section (rvmat swap for lens emissive)
```

## Three.js Implementation Strategy

### Geometry Separation

Instead of one flat mesh, build a **hierarchy of THREE.Groups**:

```
modelRoot (THREE.Group)
├── static_group (THREE.Group) — faces in no animation selection
│   ├── Mesh (material: housing.rvmat)
│   └── Mesh (material: base_plate.rvmat)
├── anim_switch (THREE.Group) — "switch" selection
│   ├── Mesh "switch_body" (material: button.rvmat)
│   └── Mesh "light_led" (material: led_off.rvmat) ← swappable
└── anim_lid (THREE.Group) — "lid" selection
    └── Mesh (material: lid.rvmat)
```

**Why groups?** Translating/rotating a Group transforms all children.
The LED mesh is a child of the button group → moves with the button AND can independently swap material.

### Building the hierarchy

```python
# 1. Identify all animated selections from model.cfg Animations
animated_selections = {"switch", "lid", "latches", ...}

# 2. Identify material-swap selections from config.cpp hiddenSelections
swap_selections = {"light_led", "camo", "camoscreen", ...}

# 3. For each face in the P3D visual LOD:
#    a. Find which animation selection(s) it belongs to
#    b. Find which swap selection(s) it belongs to
#    c. Assign to the MOST SPECIFIC group:
#       - If in an animation selection → that animation group
#       - If in multiple animation selections → deepest in bone hierarchy
#       - If in no animation selection → static group
#    d. Within the group, separate meshes by material (for swapping)

# 4. For overlapping selections (led ⊂ button):
#    - LED faces go into a sub-mesh within the button group
#    - When button translates, LED moves with it (parent group)
#    - When LED swaps material, only its sub-mesh changes
```

### Animation Application

For **translation**:
```javascript
// anim_group is the THREE.Group for this selection
const phase = slider.value; // 0..1
const t = clamp((phase - minValue) / (maxValue - minValue), 0, 1);
const disp = lerp(offset0, offset1, t) * axisLength;
anim_group.position.copy(axisOrigin);
anim_group.position.addScaledVector(axisDir, disp);
// Actually: store original position, add displacement
anim_group.position.copy(originalPos).addScaledVector(axisDir, disp);
```

For **rotation**:
```javascript
const t = clamp((phase - minValue) / (maxValue - minValue), 0, 1);
const angle = lerp(angle0, angle1, t);
// Reset rotation, then rotate around axis
anim_group.rotation.set(0, 0, 0);
anim_group.position.copy(originalPos);
// Rotate around axis (not origin)
const quaternion = new THREE.Quaternion().setFromAxisAngle(axisDir, angle);
anim_group.applyQuaternion(quaternion);
// Translate to rotate around axis point, not world origin
anim_group.position.sub(axisOrigin);
anim_group.position.applyQuaternion(quaternion);
anim_group.position.add(axisOrigin);
```

### Material Swap

```javascript
// Pre-load all material variants
const ledMaterials = {
    off:   new THREE.MeshStandardMaterial({ color: [0.4,0.4,0.4], ... }),
    green: new THREE.MeshStandardMaterial({ color: [0,0.8,0], emissive: [0,1,0], ... }),
    red:   new THREE.MeshStandardMaterial({ color: [0.8,0,0], emissive: [1,0,0], ... }),
};

// On state change:
ledMesh.material = ledMaterials[newState];

// Optional: add/remove PointLight at LED position
if (newState !== 'off') {
    pointLight.color.set(newState === 'green' ? 0x00ff00 : 0xff0000);
    pointLight.intensity = 0.5;
} else {
    pointLight.intensity = 0;
}
```

### Viewer UI

```
┌─────────────────────────────────────────┐
│  Model Name                    [controls]│
│  Verts: 328 | Tris: 640 | Mats: 4      │
│                                         │
│                                         │
│           [3D VIEWPORT]                 │
│                                         │
│                                         │
├─────────────────────────────────────────┤
│  ▸ Animations                           │
│    switch_state: ──●─────────── 0.30    │
│    open_lid:     ─────●──────── 0.55    │
│                                         │
│  ▸ States                               │
│    LED:  [Off] [Green] [Red]            │
│    Skin: [Default] [Alt 1]              │
└─────────────────────────────────────────┘
```

## Parsers Needed

### config_parser.py — Parse CfgVehicles

Extract from config.cpp for a given class name:
```python
{
    "class": "LFPG_PushButton",
    "model": "\\LFPowerGrid\\data\\switch_v1\\switch_v1.p3d",
    "hiddenSelections": ["camo", "switch", "light_led"],
    "hiddenSelectionsTextures": ["switch_co.paa", "switch_co.paa", ""],
    "hiddenSelectionsMaterials": ["switch.rvmat", "switch.rvmat", "led_off.rvmat"],
    "animationSources": {
        "switch_state": {"source": "user", "initPhase": 0, "animPeriod": 0.3}
    }
}
```

### modelcfg_parser.py — Parse CfgModels + CfgSkeletons

Extract from model.cfg for a given model name:
```python
{
    "model": "switch_v1",
    "skeleton": {
        "bones": [
            {"name": "unit", "parent": ""},
            {"name": "switch", "parent": ""},
            {"name": "light_led", "parent": ""}
        ]
    },
    "sections": ["switch", "light_led", "camo"],
    "animations": [
        {
            "name": "SwitchToggle",
            "type": "translation",
            "source": "switch_state",
            "selection": "switch",
            "axis": "switch_axis",
            "minValue": 0.0,
            "maxValue": 1.0,
            "offset0": 0.0,
            "offset1": 0.5
        }
    ]
}
```

### Extend extract_geometry_for_viewer()

Add to the output:
```python
{
    "positions": [...],
    "normals": [...],
    "uvs": [...],
    "groups": [...],  # existing

    # NEW: selection membership per vertex
    "selections": {
        "switch": [0, 1, 2, 5, 6, ...],        # vertex indices
        "light_led": [100, 101, 102, ...],
        "camo": [200, 201, ...]
    },

    # NEW: animation axes from Memory LOD
    "axes": {
        "switch_axis": {
            "origin": [0.0, 0.0, 0.023],
            "direction": [0.0, 0.0, 1.0],
            "length": 0.018
        }
    },

    # NEW: animation definitions (from model.cfg)
    "animations": [
        {
            "type": "translation",
            "source": "switch_state",
            "selection": "switch",
            "axis": "switch_axis",
            "minValue": 0, "maxValue": 1,
            "offset0": 0, "offset1": 0.5
        }
    ],

    # NEW: material states (from config.cpp hiddenSelections + rvmat alternatives)
    "material_states": {
        "light_led": {
            "default": {"color": [0.4,0.4,0.4], "emissive": [0,0,0], ...},
            "green":   {"color": [0,0.8,0], "emissive": [0,1,0], ...},
            "red":     {"color": [0.8,0,0], "emissive": [1,0,0], ...}
        }
    }
}
```

## Implementation Phases

### Phase A: Config Parsers (new scripts)
- `config_parser.py`: Parse config.cpp → extract class by name
- `modelcfg_parser.py`: Parse model.cfg → extract model + skeleton + animations
- Both use regex on C-style config text (NOT a full C parser — BI config is simpler)
- Handle: nested classes, arrays, quoted strings, comments

### Phase B: Geometry Separation
- Extend `extract_geometry_for_viewer()` to output per-selection vertex indices
- Extract axes from Memory LOD (2-point selections → origin + direction + length)
- Build group hierarchy based on animation selections

### Phase C: Material Presets
- For each hiddenSelection, collect all possible rvmat alternatives
- Auto-detect by filename pattern: `led_off` → look for `led_green`, `led_red` in same dir
- Parse each alternative rvmat → extract PBR properties
- If PAA textures available for each state, convert and embed as base64

### Phase D: Viewer UI + Animation Engine
- Add animation control panel (sliders per source)
- Add state toggle buttons (per hiddenSelection with alternatives)
- Implement translation/rotation in Three.js via Group transforms
- Implement material swap via pre-built material objects
- Optional: PointLight at LED positions for glow effect

### Phase E: Web Mode
- For web mode: export all animation/state data as JSON sidecar
- Web viewer loads .glb + .json, applies same logic
- Alternative: export as animated glTF with morph targets or skeleton
