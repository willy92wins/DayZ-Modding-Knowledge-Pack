# Config.cpp & Addon Structure

## Addon Folder Structure

```
@MyMod/
└── addons/
    └── my_addon.pbo          ← Packed from:

my_addon/                      ← Source folder
├── $PBOPREFIX$                ← Contains: my_addon (path prefix for the PBO)
├── config.cpp                 ← Game configuration
├── model.cfg                  ← Skeleton & animation definitions
├── data/
│   ├── my_object.p3d          ← The model
│   ├── textures/
│   │   ├── my_texture_co.paa  ← Diffuse/color texture
│   │   ├── my_texture_nohq.paa ← Normal map
│   │   └── my_texture_smdi.paa ← Specular map
│   └── materials/
│       └── my_material.rvmat  ← Material definition
```

## $PBOPREFIX$

A text file (no extension) containing a single line with the PBO prefix path:
```
my_addon
```
This determines how paths resolve inside the PBO. If prefix is `my_addon`, then
`my_addon\data\my_object.p3d` is the in-game path to the model.

## config.cpp — Basic Structure

```cpp
class CfgPatches
{
    class my_addon
    {
        units[] = {"MyObject"};           // Classes defined in this addon
        weapons[] = {};
        requiredVersion = 0.1;
        requiredAddons[] = {"DZ_Data"};   // Dependencies
    };
};

class CfgVehicles
{
    // Parent class — almost all DayZ placeable objects inherit from one of these:
    // - HouseNoDestruct — buildings, static structures
    // - Inventory_Base — items, placeable objects
    // - ItemBase — smaller items
    
    class HouseNoDestruct;  // External class declaration
    
    class MyObject: HouseNoDestruct
    {
        scope = 2;                                    // 2 = public, visible in-game
        displayName = "My Electrical Panel";
        descriptionShort = "An electrical panel for LF_PowerGrid";
        model = "my_addon\data\my_object.p3d";       // Path to model
        
        // Animation sources for script-controlled animations
        class AnimationSources
        {
            class switch_source
            {
                source = "user";
                initPhase = 0;
                animPeriod = 0.5;
            };
            class indicator_source
            {
                source = "user";
                initPhase = 0;
                animPeriod = 0.3;
            };
        };
        
        // For buildings with doors
        class Doors
        {
            class Door1
            {
                displayName = "Panel Door";
                component = "door1";                  // Fire Geometry component name
                soundPos = "door1_soundPos";          // Memory LOD point
                initPhase = 0;
                initOpened = 0.3;
                soundOpen = "DoorWoodThinOpen_SoundSet";
                soundClose = "DoorWoodThinClose_SoundSet";
            };
        };
        
        // Damage system (if destructible)
        class DamageSystem
        {
            class DamageZones
            {
                class Zone_Door1
                {
                    class Health
                    {
                        hitpoints = 200;
                        healthLevels[] =
                        {
                            {1.0, {}},    // Pristine
                            {0.7, {}},    // Worn
                            {0.5, {}},    // Damaged
                            {0.3, {}},    // Badly damaged
                            {0.0, {}}     // Ruined
                        };
                    };
                    componentNames[] = {"door1"};     // Fire Geometry component
                    fatalInjuryCoef = -1;
                };
            };
        };
        
        // Bounding override (if animated parts extend beyond default sphere)
        bounding = "bounding_box";   // Named selection in Memory LOD
    };
};
```

## config.cpp for DayZ Buildings

All buildings inherit from `HouseNoDestruct`. The class name MUST follow the pattern
`land_modelname` for the engine to automatically link config to model:

```cpp
class land_my_building: HouseNoDestruct
{
    scope = 2;
    model = "my_addon\data\my_building.p3d";
    // ... rest of config
};
```

The `land_` prefix + model name (without .p3d) creates the automatic link.

## config.cpp for Inventory Items / Placeable Objects

```cpp
class CfgVehicles
{
    class Inventory_Base;
    
    class LFPG_SolarPanel: Inventory_Base
    {
        scope = 2;
        displayName = "Solar Panel";
        descriptionShort = "A solar panel for electrical generation";
        model = "my_addon\data\solar_panel.p3d";
        weight = 5000;                    // Weight in grams
        itemSize[] = {5, 5};             // Inventory slot size
        rotationFlags = 16;               // Placement rotation options
        
        class AnimationSources
        {
            // ...
        };
    };
};
```

## CfgNonAIVehicles — Proxy Attachment Definitions

Required for items to render visually when attached to another object.
Without this, the attachment is logically present but invisible on the 3D model.

This works together with the proxy system:
1. Parent p3d has proxy face + selection in visual LODs (see `memory-and-selections.md`)
2. A proxy .p3d exists at the referenced path (see `py3d-direct-generation.md`)
3. **This config entry** maps inventory slots to the proxy model

```cpp
class CfgNonAIVehicles
{
    class ProxyAttachment;    // External class — MUST be declared or causes
                              // "Undefined base class" build error

    class ProxyMySlot : ProxyAttachment
    {
        scope = 2;
        inventorySlot[] = {"CarBattery", "TruckBattery"};   // Vanilla slot names
        model = "\MyAddon\data\proxy_slot.p3d";              // Path to proxy p3d
    };
};
```

**Key rules:**
- `class ProxyAttachment;` forward declaration is MANDATORY — without it AddonBuilder fails
- `inventorySlot[]` must match the slot names used in `attachments[]` of the parent CfgVehicles class
- `model` path must point to the proxy .p3d file that exists in the addon
- Class name (`ProxyMySlot`) must be unique across all loaded addons
- Multiple slots can point to the same proxy .p3d
- For vanilla slots (CarBattery, TruckBattery, SparkPlug, etc.), no CfgSlots entry needed

**Common pattern for LFPowerGrid Battery Adapter:**
```cpp
class CfgNonAIVehicles
{
    class ProxyAttachment;
    class ProxyLFPG_BatterySlot : ProxyAttachment
    {
        scope = 2;
        inventorySlot[] = {"CarBattery", "TruckBattery"};
        model = "\LFPowerGrid\data\battery_adapter\proxy_battery.p3d";
    };
};
```

## Texture & Material Configuration

### .rvmat (Material) File Format
```cpp
ambient[] = {1.0, 1.0, 1.0, 1.0};
diffuse[] = {1.0, 1.0, 1.0, 1.0};
forcedDiffuse[] = {0.0, 0.0, 0.0, 0.0};
emmisive[] = {0.0, 0.0, 0.0, 1.0};    // For glowing parts (LEDs etc)
specular[] = {0.3, 0.3, 0.3, 1.0};
specularPower = 80;
PixelShaderID = "Super";
VertexShaderID = "Super";

class Stage1
{
    texture = "my_addon\data\textures\my_texture_nohq.paa";   // Normal map
    uvSource = "tex";
    class uvTransform
    {
        aside[] = {1.0, 0.0, 0.0};
        up[] = {0.0, 1.0, 0.0};
        dir[] = {0.0, 0.0, 0.0};
        pos[] = {0.0, 0.0, 0.0};
    };
};

class Stage2
{
    texture = "#(argb,8,8,3)color(0.5,0.5,0.5,1.0,dt)";      // Detail texture
    uvSource = "tex";
    class uvTransform
    {
        aside[] = {10.0, 0.0, 0.0};
        up[] = {0.0, 10.0, 0.0};
        dir[] = {0.0, 0.0, 0.0};
        pos[] = {0.0, 0.0, 0.0};
    };
};

class Stage3
{
    texture = "my_addon\data\textures\my_texture_smdi.paa";   // Specular/gloss map
    uvSource = "tex";
    class uvTransform
    {
        aside[] = {1.0, 0.0, 0.0};
        up[] = {0.0, 1.0, 0.0};
        dir[] = {0.0, 0.0, 0.0};
        pos[] = {0.0, 0.0, 0.0};
    };
};
```

### Texture Naming Convention
| Suffix | Purpose |
|--------|---------|
| `_co.paa` | Color / diffuse texture |
| `_nohq.paa` | Normal map |
| `_smdi.paa` | Specular / metallic / gloss |
| `_as.paa` | Ambient shadow |
| `_mc.paa` | Macro color (overall tint overlay) |

### Emissive Materials (for LEDs, indicators)
Set `emmisive[]` to non-zero values for parts that should glow.
Can be controlled per-selection using hiddenSelections and hiddenSelectionsMaterials
in config.cpp to swap materials at runtime (e.g., LED on vs LED off).

## Packing into PBO

### Using Addon Builder (Official)
1. Open Addon Builder (from DayZ Tools / Arma 3 Tools on Steam)
2. Set source directory to your addon folder
3. Set destination to `@MyMod\addons\`
4. Check "Binarize" to binarize .p3d and .wrp files
5. Build

### Using Mikero's Tools (Community)
```bash
# pboProject binarizes and packs in one step
pboProject -P my_addon
```

### Using BinPBO
```bash
BinPBO.exe -SIGN my_addon @MyMod\addons\my_addon.pbo
```

## Testing

1. Place the `@MyMod` folder in your DayZ game directory
2. Add `-mod=@MyMod` to launch parameters
3. Use the in-game admin tools or script to spawn the object
4. Verify: visual appearance, collision, bullet interaction, animations, sounds
