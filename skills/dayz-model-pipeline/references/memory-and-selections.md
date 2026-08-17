# Memory Points & Named Selections

## Memory Points (Memory LOD)

Memory points are **single vertices** in the Memory LOD. They are NOT faces or edges — just
isolated points in 3D space with a name (via vertex group / named selection).

### How to Create Memory Points

**In Object Builder:**
- Switch to Memory LOD
- Create single vertices at the desired positions
- Assign them to named selections

**In Blender (for automation):**
- Create Empty objects or single-vertex meshes at the required positions
- Assign them to vertex groups with the correct names
- The Arma 3 Object Builder addon handles export to Memory LOD

**Workaround for external tools without plugin:**
- Create a triangle, position 1-2 vertices where needed
- Import to Object Builder
- Delete the extra vertex/vertices of the triangle

### Common Memory Point Types

#### Animation Axes
Two vertices define a line (axis) around which a selection rotates or along which it translates.

| Points | Purpose | Example |
|--------|---------|---------|
| `door1_axis` (2 pts) | Rotation axis for door1 | Two points on the hinge line |
| `lever_axis` (2 pts) | Rotation axis for a lever | Two points at the pivot |
| `switch_axis` (2 pts) | Rotation axis for a switch | Two points at the toggle point |
| `slide_axis` (2 pts) | Translation axis for sliding parts | Two points defining slide direction |

The axis is the LINE between the two vertices. Rotation happens around this line.
Translation happens along this line.

**Placement rules:**
- For a door hinge: both points on the vertical edge where the hinge is, one at top, one at bottom
- For a lever pivot: both points at the pivot location, separated along the pivot axis
- The ORDER of the two points determines rotation direction (right-hand rule)

#### Interaction Points
Single vertices where the player action widget (scroll menu) appears.

| Point | Purpose |
|-------|---------|
| `actionPos` | Where the interaction prompt appears |
| `doorX_action` | Action point for door X |
| `soundPos` or `doorX_soundPos` | Where door/interaction sounds play |

#### Central Economy Points
Used by DayZ's loot spawning system.

| Point | Purpose |
|-------|---------|
| `ce_center` | Center point for loot placement calculations |
| `ce_radius` | Single point — distance from ce_center defines spawn radius |

#### Bounding Override
If animated parts move outside the default bounding sphere (common with doors):

- Create a named selection in Memory LOD covering the full area the object occupies when animated
- Reference it in config.cpp: `bounding = "selection_name";`
- Without this, ray-casting for actions may fail at certain angles

#### Weapon-Specific Points (for reference)
| Point | Purpose |
|-------|---------|
| `usti hlavne` | Muzzle position |
| `konec hlavne` | End of barrel |
| `eye` | Ironsight eye position |
| `nabojnicestart` / `nabojniceend` | Magazine well |
| `recoil` | Recoil application point |
| `optics` | Optics attachment point |

### Memory Points Can Be Animated
Memory LOD selections can be animated via model.cfg just like any other LOD. This is useful
for moving interaction points with animated parts.

---

## Named Selections

Named selections are vertex groups that identify parts of the model by name. They serve
different purposes in different LODs.

### Where Named Selections Must Be Present

For an animated part (e.g., a lever):

| LOD | Required? | Why |
|-----|-----------|-----|
| Resolution LOD(s) | YES | So the visual mesh animates |
| Geometry LOD | YES | So collision follows the animation |
| Fire Geometry LOD | YES | So bullet interaction follows the animation |
| View Geometry LOD | YES | So occlusion follows the animation |
| Memory LOD | YES | For axis points and bone definitions |
| Shadow Volume | Optional | Shadows follow animation (recommended) |

**CRITICAL: The selection must have the SAME NAME in every LOD where it appears.**

### Selection Naming Conventions

| Pattern | Purpose |
|---------|---------|
| `door1`, `door2` | Animated door selections |
| `lever`, `switch` | Animated mechanical parts |
| `Component01`, `Component02` | Geometry/Fire/View geometry components |
| `camo` | Texture swap selection (for hiddenSelections) |
| `zbytek` | "Remainder" — everything not in another selection |

### Doors & ladders — esquema REAL verificado vanilla (2026-07-06, 9 modelos debinarizados)

Verificado debinarizando garage_small / barn_wood1 / farm_cowsheda / 6 ladders (ODOL v54). Corrige/precisa
las tablas de arriba (que usan `door1` singular):

- **Puertas**: la selección es **`doorsN` (PLURAL, con 's')** — los 9 vanilla usan `doors1`/`doors2`…, no
  `door1`. En Memory LOD: `doorsN_axis` (eje de rotación) + `doorsN_action` (punto de acción). Puertas
  gemelas = **`doorstwinN` + `twinN_action`**. La selección `doorsN` va en TODOS los LODs relevantes
  (visual / geometry / memory / view_geometry / fire_geometry / hitpoints). Named properties del Geometry
  LOD: `class=house` + `map=building` + `damage=no`.
- **Escaleras** (DOS esquemas, según prop suelto vs integrada en edificio): (a) **prop suelto** climbable
  (`ladder.p3d`) = Memory `start`/`end` (o `start1`/`end1`) + Roadway 3e15 debajo; (b) **integrada en
  edificio** (lighthouse/watchtower/silo) = `ladderN` (base + componente ViewGeo) + Memory
  `ladderN_bottom_front` + `ladderN_top_front` + `ladderN_middle_X`(+`_align`, pisos intermedios) +
  `ladderN_con`/`ladderN_con_dir`/`ladderN_dir` + Roadway. El `ladderN_*` de la wiki es correcto para
  el caso EDIFICIO.
- **Paths LOD (AI)**: `posXX` (stop-vertices, usables por `buildingpos`) + `inXX` (entry) + `actionbeginN`/`actionendN`.
- Detalle completo + tabla de resoluciones LOD (geometry 1e13…firegeo 7e15): `AI/20_Knowledge/dayz-objectbuilder-lod-conventions.md`.

### In Blender
Named selections = Vertex Groups in Blender.

- Create vertex groups with the correct names
- Assign vertices to them with weight 1.0
- The Arma 3 Object Builder addon exports vertex groups as named selections
- A vertex can belong to multiple selections (e.g., part of both `Component01` and `lever`)

### Selections for LF_PowerGrid Objects

- `cable_attach_point` — where cables connect
- `status_indicator` — LED or indicator that changes with power state
- `switch_handle` — interactive switch part
- `panel_door` — openable panel cover

---

## Proxy Selections (Attachment Rendering)

Proxy selections tell the engine where to render attached items (e.g., a CarBattery
sitting inside a Battery Adapter cradle). Without proxies, the attachment exists
logically in inventory but is invisible on the 3D model.

### Naming Convention

```
proxy:addon_path\proxy_model.p3d.NNN
```

- `addon_path\proxy_model.p3d` — path to a minimal proxy .p3d file
- `.NNN` — 3-digit index starting at `001` (e.g., `.001`, `.002`)
- Example: `proxy:LFPowerGrid\data\battery_adapter\proxy_battery.p3d.001`

### Where Proxy Selections Must Exist

| LOD | Required? | Why |
|-----|-----------|-----|
| Resolution LOD(s) | **YES** | Engine reads proxy face position from visual LODs |
| Geometry LOD | No | Proxy face is not a collision surface |
| Fire Geometry LOD | No | Proxy face is not a ballistic surface |
| Memory LOD | No | Proxy position is defined by the face, not memory points |

**SP-012 — Wheel/suspension slot proxies (vehicles):** the `Fire Geometry LOD | No` row above applies to ITEM-ATTACHMENT proxies (battery, headlight torch, etc.) only. For VEHICLE wheel/suspension slot proxies it is wrong: verified 4/4 vanilla (civiliansedan, hatchback_02, offroadhatchback, offroad_02) that wheel proxies appear in the Resolution LOD AND in the FireGeometry LOD (same positions). Causation caveat: adding wheel proxies to FireGeo was required PARITY but did NOT by itself fix LFQuad's "wheels never simulate" — do not present their absence as the single cause of that bug (the wheel-sim gate is the CfgSlots.selection↔FireGeo selection wiring, see SP-017 in dayz-p3d-audit).

### What a Proxy Selection Contains

A proxy selection consists of:
- **1 tiny triangle face** (3 vertices) positioned where the attachment should appear
- The face's center = attachment position
- The face's orientation = attachment orientation (vertex 0 = origin, vertex 1 = forward, vertex 2 = up)
- The face has **empty texture and material** (`""`)
- All 3 vertices and the face are assigned weight 1 in the selection

### Complete Proxy System (3 Required Parts)

For an attachment to render visually, ALL THREE parts must be present:

1. **Proxy face + selection in parent p3d** — in all visual LODs (Res0, Res1, Res2)
2. **Proxy .p3d file** — minimal model at the path referenced in the selection name
3. **CfgNonAIVehicles entry** — in config.cpp, mapping `inventorySlot` to the proxy model

Missing any one of these three = attachment is logically attached but invisible.

### Vanilla Attachment Model Paths (DayZ SA)

Common vanilla item models used in proxy systems:

| Item | Model Path |
|------|-----------|
| CarBattery | `DZ\vehicles\parts\battery_car.p3d` |
| TruckBattery | `DZ\vehicles\parts\battery_truck.p3d` |

Note: For proxy rendering you do NOT reference the vanilla model directly in the
proxy selection name. Instead, you create your own proxy .p3d and link vanilla
attachment slots to it via `CfgNonAIVehicles`. The engine then renders the
attached item's own model at the proxy position.

See `py3d-direct-generation.md` for code to create proxy faces and proxy .p3d files.
See `config-and-packing.md` for the `CfgNonAIVehicles` config entry.

<!-- [merged 2026-06-05 from <claude-home>\skills user copy during plugin-canonical migration] -->
### LFPG Electrical Port Convention (Memory LOD)

LFPG devices connect to each other via cables that the engine resolves by
name. The device script calls `LFPG_AddPort("input_1", ...)` /
`LFPG_AddPort("output_1", ...)` in its constructor, and the framework
looks up memory points with the matching prefixed names at runtime.

**Required memory-point names per port:**

| Memory point | Script port name | Purpose |
|---|---|---|
| `port_input_N` | `input_N` | Anchor point where an incoming cable attaches |
| `port_output_N` | `output_N` | Anchor point for outgoing cable |
| `port_input_N_dir` | (paired) | Direction vector: line from `port_input_N` to `port_input_N_dir` defines how the cable exits |
| `port_output_N_dir` | (paired) | Same for the output |

`N` is a small integer — 0-indexed (`port_input_0`) on older items
(switch_v1, sprinkler) and 1-indexed (`port_input_1`) on newer ones
(ceiling_light, wall_lamp). **Match the indexing used by the script's
`LFPG_AddPort` calls.** Mismatched naming = cable can't attach.

**Other LFPG memory points commonly set:**

| Memory point | Required? | Purpose |
|---|---|---|
| `light` | If device emits light | PointLight spawn origin (also used as `CreateLightAtObjMemoryPoint` target) |
| `light_emit` | Optional | Paired visual anchor for the emissive selection (convention seen in `ceiling_light.p3d`) |
| `ce_center` | Yes | Geometric center for Central Economy loot calculations |
| `ce_radius` | Yes | Single point whose distance from `ce_center` defines the loot spawn radius |
| `boundingbox_min` / `boundingbox_max` | Yes | Tight bbox corners used by inventory preview framing and some collision logic |
| `invview` | Optional | Camera anchor for the inventory preview thumbnail (offset forward from the model) |

**Example: electrical port layout for a wall-mounted device** (Z+ = back
= wall side; cables exit through the wall):

```python
port_input_1      = (+0.0, cy + 0.04, z_back)        # upper port
port_input_1_dir  = (+0.0, cy + 0.04, z_back + 0.03) # 3cm behind wall
port_output_1     = (+0.0, cy - 0.04, z_back)        # lower port
port_output_1_dir = (+0.0, cy - 0.04, z_back + 0.03)
```

Inspect a sibling device's memory LOD in `dayz-p3d-inspector` before
designing your own — placement relative to the visible mesh is what
makes cables look attached-not-floating, and it varies by device.

---
