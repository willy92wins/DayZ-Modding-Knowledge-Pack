# Input Bindings (Inputs.xml + config)

Flight-control input registration in Inputs.xml, the standard keyboard/Xbox binding scheme, stringtable tie-in, and multi-aircraft config variants.

_Extracted from `dayz-aviation/SKILL.md` 2026-07-07 (F3)._

## Input Bindings (Inputs.xml + config)

### XML registration

In `scripts/data/Inputs.xml`:

```xml
<modded_inputs>
    <inputs>
        <actions>
            <input name="UALlamaPlanePitchForward" loc="llama_plane_pitch_forward"/>
            <!-- ... 11 actions total -->
        </actions>
        <sorting name="llama_plane" loc="llama_plane_controls">
            <input name="UALlamaPlanePitchForward"/>
            <!-- groups inputs in keybind menu under "llama_plane_controls" category -->
        </sorting>
        <exclude name="LlamaPlane_Controls">
            <!-- excludes these inputs from default vanilla binding conflicts -->
        </exclude>
    </inputs>
    <preset>
        <input name="UALlamaPlanePitchForward">
            <btn name="kW"/>
            <btn name="x1LeftThumbUp"/>
        </input>
        <!-- ... -->
    </preset>
</modded_inputs>
```

### Standard aviation binding scheme

| Action | Keyboard | Xbox |
|---|---|---|
| Pitch forward (nose down) | W | LeftThumb Up |
| Pitch back (nose up) | S | LeftThumb Down |
| Roll left | A | LeftThumb Left |
| Roll right | D | LeftThumb Right |
| Rudder left | Q | Shoulder Left (LB) |
| Rudder right | E | Shoulder Right (RB) |
| Throttle up | LShift | Trigger Right (RT) |
| Throttle down | LCtrl | Trigger Left (LT) |
| Toggle mode (Air/Ground) | G | LeftThumb click |
| Free look | LAlt | RightThumb click |
| Shoot (weapons) | Space | A |

Key prefix convention: `k` for keyboard (`kW`, `kSpace`, `kLShift`, `kLControl`, `kLMenu`), `x1` for Xbox (`x1LeftThumbUp`, `x1A`, `x1ShoulderLeft`, `x1TriggerRight`).

### Stringtable + config.cpp tie-in

`Stringtable.csv` defines display strings for each `loc="..."` key. Llama sets all 13 locales to identical English (no real i18n) — pragmatic, leaves the structure ready for translation later.

`config.cpp` root references the XML:

```cpp
class CfgMods {
    class LM_Planes {
        inputs = "LM_Planes/scripts/data/Inputs.xml";
        // ...
    };
};
```

### Multi-aircraft variants in one config

```cpp
class CfgVehicles {
    class LM_Tigermoth: CarScript { /* base biplane */ };
    class LM_Tigermoth_MK2: CarScript { /* sport variant, top wing removed */ };
    class LM_Tigermoth_MK3: CarScript { /* seaplane variant with Buoyancy */ };
};
```

Family of variants share `LM_Planes\LM_Tigermoth\*.p3d` directory but each has its own model file. Reduces config duplication while allowing visual + behavior differences.
