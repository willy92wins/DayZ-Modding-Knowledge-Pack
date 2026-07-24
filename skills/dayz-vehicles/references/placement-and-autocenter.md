# Placement, `autocenter`, and the knee-height bug

A short but important reference: where `autocenter=0` actually belongs, and
why the "add it everywhere to be safe" advice is wrong and actively breaks
DayZ placements.

## Short answer

`autocenter=0` goes on the **config.cpp** class, not on any `.p3d` LOD — for
**Inventory_Base placeable items**; vehicles are the exception (see SCOPE below).

SCOPE (corrected s20 2026-07-02): this rule is for **Inventory_Base placeable items** (verified on
LFPG_PressurePad). **VEHICLES AND PROXY MODELS ARE THE EXCEPTION**: vanilla working vehicles carry
`autocenter=0` as a named property ON the Geometry LOD (CivilianSedan MLOD res=1e13 props
`{autocenter:0, class:vehicle}`, measured via py3d; QuadBike likewise), and the CivilianSedan config class
has NO config-level autocenter. For vehicles follow `vehicle-structural-parity.md`; never run
`strip_bad_autocenter` on a vehicle `.p3d`.

```cpp
class LFPG_PressurePad : Inventory_Base
{
    scope = 2;
    model = "\LFPowerGrid\data\pressure_pad\pressure_pad.p3d";
    autocenter = 0;   // ← THIS is the right place
    // ...
};
```

Do NOT duplicate `autocenter=0` onto the Geometry LOD, LandContact LOD,
Memory LOD, View Geometry LOD, or Fire Geometry LOD properties. The config
flag is authoritative.

## Why adding it to LODs breaks things

Verified on `LFPG_PressurePad` in April 2026:

- The `.p3d` had `autocenter=0` added to LOD 3 (Geometry, res 1 × 10¹³) and
  LOD 5 (LandContact, res 2 × 10¹⁵) by a previous pipeline/editor.
- In-game symptom: the placement hologram appeared floating ~0.4 m above
  ground (knee height), and the final placed object stayed at the same
  height. Both server-side and client-side.
- Removing just those two LOD-level `autocenter=0` properties restored
  correct ground placement immediately. No code changes needed.

The engine's ground-contact calculation uses the Geometry/LandContact
position to figure out where the "bottom" of the object is. When the
config's `autocenter=0` already freezes the model origin, re-asserting it
on the LOD effectively double-applies the offset and the engine places the
object with an extra shift on top of the visual origin.

## LOD resolution bands (DayZ)

For reference when reading/writing LOD properties:

| Type | Resolution |
|---|---|
| Visual 0, 1, 2… | 0, 1, 2, … |
| Shadow volume | 10 000 |
| Geometry (collision) | 1 × 10¹³ |
| Memory | 1 × 10¹⁵ |
| LandContact | 2 × 10¹⁵ |
| Roadway | 3 × 10¹⁵ |
| Paths | 4 × 10¹⁵ |
| HitPoints | 5 × 10¹⁵ |
| View Geometry | 6 × 10¹⁵ |
| Fire Geometry | 7 × 10¹⁵ |

Older skill notes listed GeoPhys at 2 × 10¹³, FireGeo at 3 × 10¹³, ViewGeo
at 7 × 10¹³. Those values are wrong for modern DayZ and cause LandContact,
ViewGeo, and FireGeo to all be misclassified as "memory".

## Audit / fix snippet

```python
import py3d

def strip_bad_autocenter(p3d_path, out_path=None):
    """Remove `autocenter=0` from collision/landcontact LODs only.

    Returns list of (lod_index, lod_type) tuples that were changed.
    """
    with open(p3d_path, "rb") as f:
        p = py3d.P3D(); p.read(f)

    changed = []
    for i, lod in enumerate(p.lods):
        res = lod.resolution
        # Everything except Visual (res < 1000) and Shadow (10000)
        is_non_visual = res >= 10000 and res != 10000
        # More specifically: Geometry, LandContact, Memory, View, Fire
        is_collision = (
            abs(res - 1e13) < 1e12 or    # Geometry
            abs(res - 1e15) < 1e14 or    # Memory
            abs(res - 2e15) < 1e14 or    # LandContact
            abs(res - 6e15) < 1e14 or    # ViewGeo
            abs(res - 7e15) < 1e14       # FireGeo
        )
        if is_collision and lod.properties.get("autocenter") == "0":
            del lod.properties["autocenter"]
            changed.append((i, f"res={res:.0g}"))

    if changed:
        with open(out_path or p3d_path, "wb") as f:
            p.write(f)
    return changed
```

## When config-level `autocenter=0` is appropriate

- **Always** for `Inventory_Base` items that are placeable on the ground
  (the vast majority of deployable kits and their placed devices).
- **Always** when you authored the model with the origin at the intended
  ground-contact point rather than at the geometric center.
- Skip it only if you know the engine's auto-centering gives you what you
  want (uncommon — usually only for small handheld items where the exact
  "sit on ground" pose doesn't matter).

## When someone might legitimately add LOD-level `autocenter=0`

Rare. The one case is a model where the LOD's geometry centroid is far
from the origin and you explicitly don't want the engine to recompute
the LOD's own center. In practice, for DayZ mod kits you should assume
"LOD-level autocenter is a bug" until proven otherwise.

## See also

- `dayz-p3d-audit` — `audit_p3d.py` warns if `autocenter=0` is found on a
  non-visual LOD.
- `dayz-p3d-inspector` — `p3d_inspector_build.py` does NOT auto-add
  `autocenter`; Recipe JSON `properties` is authoritative.
- `enforce-script-reference` — config.cpp conventions for placeable items.
