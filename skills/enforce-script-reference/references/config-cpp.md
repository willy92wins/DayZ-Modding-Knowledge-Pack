# config.cpp Patterns for DayZ Mods

## Structure Overview

Every DayZ mod needs a `config.cpp` defining its classes and dependencies.

```
class CfgPatches
{
    class LFPowerGrid
    {
        units[] = { "LF_MyDevice", "LF_MyDevice_Kit" };
        weapons[] = {};
        requiredVersion = 0.1;
        requiredAddons[] = { "DZ_Data", "DZ_Scripts" };
    };
};

class CfgMods
{
    class LFPowerGrid
    {
        type = "mod";
        dependencies[] = { "World", "Mission" };

        class defs
        {
            class worldScriptModule
            {
                value = "";
                files[] = { "LFPowerGrid/scripts/4_World" };
            };
            class missionScriptModule
            {
                value = "";
                files[] = { "LFPowerGrid/scripts/5_Mission" };
            };
            class gameScriptModule
            {
                value = "";
                files[] = { "LFPowerGrid/scripts/3_Game" };
            };
        };
    };
};
```

## CfgVehicles — Entity Definitions

### Basic Item (Inventory_Base)

```
class CfgVehicles
{
    class Inventory_Base;

    class LF_MyDevice: Inventory_Base
    {
        scope = 2;                    // 2 = visible in-game, 0 = hidden
        displayName = "$STR_LF_MYDEVICE";
        descriptionShort = "$STR_LF_MYDEVICE_DESC";
        model = "\LFPowerGrid\data\mydevice\lf_mydevice.p3d";
        weight = 500;                 // grams
        itemSize[] = { 3, 3 };        // inventory slots (width, height)
        rotationFlags = 17;           // rotation in inventory
        storageCategory = 1;          // enables persistence
        hiddenSelections[] = { "camo", "light_led" };
        hiddenSelectionsTextures[] = { "\LFPowerGrid\data\mydevice\texture.paa" };
        hiddenSelectionsMaterials[] = { "\LFPowerGrid\data\mydevice\material.rvmat" };

        class AnimationSources
        {
            class led_state
            {
                source = "user";
                animPeriod = 0.01;
                initPhase = 0;
            };
        };
    };
};
```

### Kit Item (Deployable)

```
class CfgVehicles
{
    class Inventory_Base;

    // CRITICAL: Kits MUST inherit from Inventory_Base in config.
    // Using DeployableContainer_Base breaks kits (item doesn't appear).
    // Tested twice — both times the item was invisible in-game.
    // Use DeployableContainer_Base ONLY in script class inheritance.
    class LF_MyDevice_Kit: Inventory_Base
    {
        scope = 2;
        displayName = "$STR_LF_MYDEVICE_KIT";
        descriptionShort = "$STR_LF_MYDEVICE_KIT_DESC";
        model = "\LFPowerGrid\data\kits\lf_kit_box.p3d";
        weight = 800;
        itemSize[] = { 2, 2 };
        rotationFlags = 17;

        // Kit placement configuration
        class Placement
        {
            // If kit and deployed model are different:
            deployableModel = "\LFPowerGrid\data\mydevice\lf_mydevice.p3d";
            // If same model (camera/door controller pattern): omit deployableModel
        };

        // hiddenSelections for kit appearance
        hiddenSelections[] = { "camo" };
        hiddenSelectionsTextures[] = { "\LFPowerGrid\data\kits\kitboxtexture.paa" };
        hiddenSelectionsMaterials[] = { "\LFPowerGrid\data\kits\lf_kit_box.rvmat" };
    };
};
```

### Important config.cpp Rules

1. **`scope = 2`** — Required for items to be spawnable/visible. `scope = 0` hides them.
2. **`units[]`** — List ALL your classes here. Missing = not loaded.
3. **`requiredAddons[]`** — Must include addons your classes inherit from.
4. **Forward declare parent classes** — `class Inventory_Base;` before using as parent.
5. **Semicolons after closing braces** — Every `};` needs the semicolon.
6. **No trailing comma in arrays** — Last element must NOT have comma.
7. **Case sensitivity** — Class names are case-sensitive in config lookups.

### hiddenSelections System

hiddenSelections allow runtime texture/material swaps:

```
// In config.cpp — declare selections
hiddenSelections[] = { "camo", "light_led", "screen" };
hiddenSelectionsTextures[] = {
    "\LFPowerGrid\data\mydevice\texture.paa",   // [0] camo
    "",                                           // [1] light_led (set by script)
    "\LFPowerGrid\data\mydevice\screen.paa"      // [2] screen
};
hiddenSelectionsMaterials[] = {
    "\LFPowerGrid\data\mydevice\material.rvmat",
    "\LFPowerGrid\data\mydevice\led_off.rvmat",
    "\LFPowerGrid\data\mydevice\screen.rvmat"
};
```

```
// In script — swap material at runtime
string rvmatOn = "\LFPowerGrid\data\mydevice\led_on.rvmat";
int selIndex = 1;  // light_led
SetObjectMaterial(selIndex, rvmatOn);

// Swap texture at runtime
string texAlt = "\LFPowerGrid\data\mydevice\texture_alt.paa";
int texIndex = 0;  // camo
SetObjectTexture(texIndex, texAlt);
```

**CRITICAL**: The index in `SetObjectMaterial`/`SetObjectTexture` corresponds
to the position in the `hiddenSelections[]` array. The selection name in the
p3d model must match exactly.

### model.cfg for Animations

```
class CfgModels
{
    class LF_MyDevice
    {
        sectionsInherit = "";
        sections[] = { "camo", "light_led", "screen" };

        class Animations
        {
            class led_state
            {
                type = "rotation";
                source = "led_state";
                selection = "light_led";
                axis = "led_axis";
                memory = 1;
                minValue = 0;
                maxValue = 1;
                angle0 = 0;
                angle1 = 0.01;  // minimal rotation for state change
            };
        };
    };
};
```

## $PBOPREFIX$ File

Required at mod root for DayZ to resolve baked p3d paths to correct PBO namespace:

```
// File: $PBOPREFIX$
// Content (single line, no trailing newline):
LFPowerGrid
```

Without this file, all model/texture/material paths that reference
`\LFPowerGrid\...` will fail to resolve at runtime.

## Script Module Organization

```
LFPowerGrid/
├── config.cpp
├── $PBOPREFIX$
├── scripts/
│   ├── 3_Game/       ← Shared utilities, settings, data classes
│   ├── 4_World/      ← Entity scripts, device logic, actions
│   └── 5_Mission/    ← UI code, menus, HUD overlays
├── data/             ← Models, textures, materials
└── gui/
    └── layouts/      ← .layout UI files
```

**Loading order matters**: 3_Game loads first, then 4_World, then 5_Mission.
Classes in 4_World can use 3_Game classes but not vice versa.
