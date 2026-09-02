# Direct P3D Generation with py3d

## Overview

La lib `py3d` (fork DayZ >= 1.6.0 sobre el codec de KoffeinFlummi) lee y escribe Arma/DayZ `.p3d` en MLOD
(unbinarized) format directly from Python. No Blender, no Object Builder, no external
tools needed.

- **Repo:** el fork vive en el pack (`tools/py3d`, 1.7.0) y en GitHub `willy92wins/py3d-dayz` (upstream https://github.com/KoffeinFlummi/py3d, muerto). `P:\py3d` es un clon de jun-2026 congelado en 1.3.0: no es fuente.
- **Install:** pack `tools/py3d` + `pip install opensimplex --break-system-packages`:

```bash
# py3d DayZ fork >= 1.6.0 (`pip install -e tools/py3d`).
# NUNCA `pip install py3d` (PyPI = point-cloud lib) NI git+upstream (sin guards).
pip install -e tools/py3d
python3 -c "import py3d; assert getattr(py3d,'IS_DAYZ_FORK',False) and tuple(map(int,py3d.__version__.split('.')))>=(1,6,0), (py3d.__version__, py3d.__file__)"
```
- **License:** Open source
- **Dependencies:** numpy, pillow, opensimplex

> **CRITICAL: Do NOT use `pip install py3d`** — that installs a completely different
> 3D visualization library (py3d 0.1.x), NOT the Arma/DayZ MLOD parser. The correct
> package is the **DayZ fork >= 1.6.0** (`pip install -e tools/py3d`). It provides `P3D`, `LOD`,
> `Face`, `Point`, `Selection`, `Vertex` + fork APIs (`get_lod`/`kind`, `bbox`,
> `triangulate`, `set_selection`, `set_total_mass`, `add_proxy`/`get_proxies`,
> `to_dict`/`from_dict`, `validate()`, `save(verify=True)`).
> Verify: `python3 -c "import py3d; assert py3d.IS_DAYZ_FORK"`

## Core API

```python
import py3d

# Create a new P3D file
p3d_file = py3d.P3D()

# Create a LOD
lod = py3d.LOD()
lod.resolution = 0.0   # Resolution LOD 0 (full detail visual)

# Add a point (vertex)
point = py3d.Point()
point.coords = (x, y, z)    # XYZ coordinates in meters
point.flags = 0              # Point flags (usually 0)
point.mass = 10.0            # Mass (only needed for Geometry/Fire LODs)
lod.points.append(point)

# Add a face normal
lod.facenormals.append((nx, ny, nz))  # Unit vector

# Create a face (triangle or quad)
face = py3d.Face(lod.points, lod.facenormals)
face.flags = 0
face.texture = "addon_name\\data\\textures\\my_texture_co.paa"
face.material = "addon_name\\data\\materials\\my_material.rvmat"

# Add vertices to the face (3 for triangle, 4 for quad)
vertex = py3d.Vertex(lod.points, lod.facenormals)
vertex.point_index = 0       # Index into lod.points
vertex.normal_index = 0      # Index into lod.facenormals
vertex.uv = (u, v)           # UV coordinates
face.vertices.append(vertex)
# ... repeat for 2 more vertices (triangle)
lod.faces.append(face)

# Named selections
selection = py3d.Selection(lod.points, lod.faces)
selection.points[lod.points[0]] = 1    # Weight 1.0 = fully selected
selection.faces[lod.faces[0]] = 1
lod.selections["my_selection"] = selection

# Named properties (e.g., class=house for Geometry LOD)
lod.properties["class"] = "house"

# Add LOD to P3D
p3d_file.lods.append(lod)

# Write to file
with open("output.p3d", "wb") as f:
    p3d_file.write(f)

# Verify by reading back
with open("output.p3d", "rb") as f:
    verify = py3d.P3D(f)
    print(f"LODs: {len(verify.lods)}")
```

## LOD Resolution Values

The engine identifies LOD types by their resolution float value:

```python
LOD_RESOLUTION = {
    "visual_0":       0.0,       # Visual, full detail
    "visual_1":       1.0,       # Visual, medium detail
    "visual_2":       4.0,       # Visual, low detail
    "visual_3":       8.0,       # Visual, very low detail
    "shadow_close":   1.0e4,     # ShadowVolume (close)
    "shadow_far":     1.1e4,     # ShadowVolume (far)
    "geometry":       1.0e13,    # Collision geometry
    "memory":         1.0e15,    # Memory points
    "land_contact":   2.0e15,    # LandContact
    "roadway":        3.0e15,    # Roadway
    "paths":          4.0e15,    # Paths (AI navigation)
    "hitpoints":      5.0e15,    # Hit points / damage zones
    "view_geometry":  6.0e15,    # ViewGeometry (DayZ; NOT Arma3 3e13)
    "fire_geometry":  7.0e15,    # FireGeometry (DayZ; NOT Arma3 2e13)
}
```

## Geometry Generation Patterns

### Cylinder (for buttons, housings, pipes)
```python
def make_cylinder(radius_top, radius_bot, height, y_offset, segments):
    points, normals, faces = [], [], []
    for i in range(segments):
        angle = 2 * math.pi * i / segments
        # Bottom ring
        points.append((math.cos(angle)*radius_bot, y_offset, math.sin(angle)*radius_bot))
        normals.append((math.cos(angle), 0, math.sin(angle)))
    for i in range(segments):
        angle = 2 * math.pi * i / segments
        # Top ring
        points.append((math.cos(angle)*radius_top, y_offset+height, math.sin(angle)*radius_top))
        normals.append((math.cos(angle), 0, math.sin(angle)))
    # Add center points for caps, then generate triangle faces...
    return points, normals, faces
```

### Convex Box (for Geometry/Fire/View LODs)
```python
def make_box(x_min, y_min, z_min, x_max, y_max, z_max):
    points = [
        (x_min,y_min,z_min), (x_max,y_min,z_min),
        (x_max,y_min,z_max), (x_min,y_min,z_max),
        (x_min,y_max,z_min), (x_max,y_max,z_min),
        (x_max,y_max,z_max), (x_min,y_max,z_max),
    ]
    # 12 triangles for 6 faces
    return points, normals, faces
```

### Dome/Hemisphere (for LEDs, indicator lights)
Generate rings from equator to pole, connect with triangles.

## Selection Patterns

### Static part (present in all visual LODs)
```python
lod.selections["zbytek"] = selection_covering_static_points
```

### Animated part (MUST be in ALL LOD types)
```python
for lod in [visual_lod0, visual_lod1, geometry_lod, fire_lod, view_lod, shadow_lod]:
    lod.selections["button_push"] = selection_covering_button_points
```

### Material swap selection (for hiddenSelections)
```python
visual_lod.selections["led_indicator"] = selection_covering_led_points
```

### Geometry components
```python
geometry_lod.selections["Component01"] = selection_covering_housing
geometry_lod.selections["Component02"] = selection_covering_button
```

## Memory LOD Pattern

Memory LOD has points but NO faces. Each memory point is a named vertex.

```python
memory_lod = py3d.LOD()
memory_lod.resolution = 1.0e15

# Animation axis = 2 points
pt1 = py3d.Point(); pt1.coords = (0, 0.02, 0)
pt2 = py3d.Point(); pt2.coords = (0, 0.04, 0)
memory_lod.points.extend([pt1, pt2])

sel = py3d.Selection(memory_lod.points, memory_lod.faces)
sel.points[pt1] = 1
sel.points[pt2] = 1
memory_lod.selections["button_axis"] = sel

# Interaction point = 1 point
action = py3d.Point(); action.coords = (0.03, 0.03, 0)
memory_lod.points.append(action)
sel_action = py3d.Selection(memory_lod.points, memory_lod.faces)
sel_action.points[action] = 1
memory_lod.selections["actionPos"] = sel_action
```

## Complete Build Order

1. Create `py3d.P3D()` instance
2. Build Resolution LOD 0 (32 segments) → append
3. Build Resolution LOD 1 (16 segments) → append
4. Build Resolution LOD 2 (8 segments) → append
5. Build Geometry LOD (convex boxes, mass, properties) → append
6. Build Fire Geometry LOD (convex boxes, penetration materials) → append
7. Build View Geometry LOD (single simplified box) → append
8. Build Shadow Volume LOD close (shrunk 97%) → append
9. Build Shadow Volume LOD far (shrunk 97%) → append
10. Build Memory LOD (points only, no faces) → append
11. Write to file
12. Read back and verify

## Validation Checklist

After generating, verify:
- [ ] File reads back without errors
- [ ] Correct number of LODs (DayZ-modern resolutions: Geometry=1e13, Memory=1e15, LandContact=2e15, Roadway=3e15, Hitpoints=5e15, ViewGeo=6e15, FireGeo=7e15 — NOT Arma 3 legacy 2e13/3e13)
- [ ] Resolution LOD 0 has the most vertices
- [ ] Geometry LOD has `class=house` property (if building)
- [ ] **`autocenter=0` named property on EVERY collision LOD** (Geometry, FireGeo, ViewGeo, Roadway, Hitpoints, LandContact) — Rule 16. Bug: missing on FireGeo causes ~22cm displacement of collision mesh from visual.
- [ ] **Every face in collision LODs has a penetration `.rvmat` material assigned** — Rule 17. `face.material = "dz\\data\\data\\penetration\\<surface>.rvmat"`. Without it bullets pass through.
- [ ] Geometry/Fire LOD points have mass assigned
- [ ] Memory LOD has 0 faces
- [ ] Memory LOD has named-selection points: `boundingbox_min`, `boundingbox_max`, `ce_center`, `invview` (placement system uses these)
- [ ] All animated selections exist in Resolution, Geometry, Fire, View, and Memory LODs
- [ ] Texture paths use backslashes and .paa extension
- [ ] Material paths use backslashes
- [ ] If imported from Blender: Z-up → Y-up rotation applied (see below)
- [ ] After source-axis conversion: reverse face winding only for a reflection (det<0) or a non-engine-winding source (glTF/CCW); do not reverse a det=+1 rotation whose source winding already matches the engine. For that det=+1 case, verify `check_face_winding` reports ~0% flipped (UNIFORM_NON_FLIPPED).
- [ ] If accepting attachments: proxy faces + selections present in visual LODs

## Blender Z-up → DayZ Y-up Rotation (MANDATORY for Blender exports)

Blender uses Z as the up-axis. DayZ uses Y. If you generate geometry in Blender
or in code using Z-up conventions, you MUST rotate all data before writing the p3d.

**Transform: `x' = x,  y' = z,  z' = -y`**

This is a -90° rotation around the X axis. Apply to BOTH vertex positions AND face normals.

```python
def rot_coords(c):
    return (c[0], c[2], -c[1])

def rot_normal(n):
    return (n[0], n[2], -n[1])

# Apply to ALL LODs (visual, geometry, fire, view, shadow, memory)
for lod in model.lods:
    for pt in lod.points:
        pt.coords = rot_coords(pt.coords)
    new_normals = []
    for n in lod.facenormals:
        new_normals.append(rot_normal(n))
    lod.facenormals = new_normals
```

**WARNING (corregido 2026-07-06 — alinea con `SKILL.md` Rule 13 / LL-020, verificado in-game):** la
reversión de winding NO es incondicional. La rotación `(x,z,-y)` es una **rotación PROPIA (det=+1)** →
PRESERVA handedness y winding → **NO se reversa** (reversar sobre un det=+1 da 100% flipped: modelo solo
visible desde dentro / negro por fuera, LL-020). Se reversa SÓLO si (a) la transform introduce una
REFLEXIÓN (det<0, p.ej. el pure swap `(x,z,y)` de los imports glTF), o (b) el source no trae ya el
winding del engine (glTF front faces = CCW por spec → import glTF va con pure swap `(x,z,y)` det=-1 +
reverse). Verifica SIEMPRE con `check_face_winding` (cross(e1,e2)·normal) tras ensamblar: ~0% flipped.

## Face Winding Order Fix (CONDICIONAL — solo si det<0 o source glTF/CCW)

Refinado por LL-020: reversa el orden de vértices SÓLO cuando la transform introduce una reflexión
(det<0) o el source no trae ya el winding del engine. Geometría generada en Z-up y rotada con la
rotación propia `(x,z,-y)` (det=+1) → NO se reversa. Cuando SÍ toca (típico: import glTF/GLB resuelto
como pure swap `(x,z,y)` det=-1), reversa cada cara de cada LOD — EXCEPTO triángulos proxy (su orden
codifica el frame P0/P1/P2, no tocar):

```python
for lod in model.lods:
    for face in lod.faces:
        face.vertices.reverse()
```

**Symptoms of wrong winding order:**
- Textures visible only from inside the object
- Object appears transparent/invisible from the outside
- Object appears solid black from outside (backface culling)

**This applies to ALL LODs** including Geometry, Fire Geometry, View Geometry,
and Shadow LODs — not just visual LODs.

## Proxy Faces for Attachment Rendering

When a DayZ item accepts attachments (e.g., a cradle that holds a battery),
the attached item's 3D model must be rendered at a specific position on the
parent. This requires the **proxy system**: a special face + named selection
in the parent p3d's visual LODs.

### How Proxies Work

1. A tiny triangle face is added to visual LODs (Res0, Res1, Res2)
2. The face is assigned to a named selection with the pattern:
   `proxy:addon_path\proxy_model.p3d.NNN`
3. The engine finds this selection, reads the face position/orientation,
   and renders the attached item's model there
4. A minimal proxy .p3d must exist at the referenced path
5. A `CfgNonAIVehicles` entry must map `inventorySlot` to the proxy model

### Creating Proxy in py3d

```python
# Selection name follows strict convention
proxy_sel_name = "proxy:MyAddon\\data\\proxy_slot.p3d.001"

# Position where the attachment should render
proxy_center = (0.0, 0.05, 0.0)  # center of cradle/slot

# Proxy face: 3 points forming a tiny triangle
# Point 0 = position, Point 1 = forward, Point 2 = up
proxy_pts_coords = [
    (proxy_center[0],        proxy_center[1],         proxy_center[2]),
    (proxy_center[0],        proxy_center[1],         proxy_center[2] + 0.001),
    (proxy_center[0],        proxy_center[1] + 0.001, proxy_center[2]),
]
proxy_normal = (0.0, 0.0, 1.0)

# Add to each visual LOD
for lod in [lod0, lod1, lod2]:
    proxy_point_objs = []
    for pc in proxy_pts_coords:
        pt = Point()
        pt.coords = pc
        pt.flags = 0
        lod.points.append(pt)
        proxy_point_objs.append(pt)

    lod.facenormals.append(proxy_normal)
    norm_idx = len(lod.facenormals) - 1

    proxy_face = Face(lod.points, lod.facenormals)
    proxy_face.flags = 0
    proxy_face.texture = ""
    proxy_face.material = ""

    for pi, pobj in enumerate(proxy_point_objs):
        v = Vertex(lod.points, lod.facenormals)
        v.point_index = lod.points.index(pobj)
        v.normal_index = norm_idx
        v.uv = (0.0, 0.0)
        proxy_face.vertices.append(v)

    lod.faces.append(proxy_face)

    # Named selection covering the proxy face and its points
    proxy_sel = Selection(lod.points, lod.faces)
    proxy_sel.points[proxy_point_objs[0]] = 1
    proxy_sel.points[proxy_point_objs[1]] = 1
    proxy_sel.points[proxy_point_objs[2]] = 1
    proxy_sel.faces[proxy_face] = 1
    lod.selections[proxy_sel_name] = proxy_sel
```

### Creating a Minimal Proxy .p3d

The engine needs a physical .p3d file at the proxy path. It can be minimal —
a single triangle + Memory LOD:

```python
proxy = P3D()

# Resolution LOD: 1 tiny triangle
lod = LOD()
lod.resolution = 0.0
p0 = Point(); p0.coords = (0.0, 0.0, 0.0)
p1 = Point(); p1.coords = (0.01, 0.0, 0.0)
p2 = Point(); p2.coords = (0.0, 0.01, 0.0)
lod.points.extend([p0, p1, p2])
lod.facenormals.append((0.0, 0.0, 1.0))

face = Face(lod.points, lod.facenormals)
face.texture = ""
face.material = ""
for i in range(3):
    v = Vertex(lod.points, lod.facenormals)
    v.point_index = i
    v.normal_index = 0
    v.uv = (0.0, 0.0)
    face.vertices.append(v)
lod.faces.append(face)

sel = Selection(lod.points, lod.faces)
sel.points[p0] = 1; sel.points[p1] = 1; sel.points[p2] = 1
sel.faces[face] = 1
lod.selections["zbytek"] = sel
proxy.lods.append(lod)

# Memory LOD
mem = LOD()
mem.resolution = 1.0e15
ce = Point(); ce.coords = (0.0, 0.0, 0.0)
mem.points.append(ce)
ce_sel = Selection(mem.points, mem.faces)
ce_sel.points[ce] = 1
mem.selections["ce_center"] = ce_sel
proxy.lods.append(mem)

with open("proxy_slot.p3d", "wb") as f:
    proxy.write(f)
```

### Config.cpp Requirement

See `config-and-packing.md` for the `CfgNonAIVehicles` entry that completes
the proxy system.

---

## Reading & Inspecting Existing .p3d Files

py3d can read MLOD .p3d files as easily as writing them. This is essential for
diagnosing problems in generated models.

### Basic Read & LOD Enumeration

```python
import py3d

with open("my_model.p3d", "rb") as f:
    model = py3d.P3D(f)

print(f"Total LODs: {len(model.lods)}")

# LOD type classification by resolution value
def classify_lod(res):
    # DayZ canonical LOD resolutions (mirrors py3d.classify_lod_resolution)
    if res < 1e3:
        return f"Visual {res}"
    elif 1e4 <= res < 2e4:
        return f"Shadow {res}"
    elif abs(res - 1e13) < 1e11:
        return "Geometry"
    elif abs(res - 1e15) < 5e13:
        return "Memory"
    elif abs(res - 2e15) < 5e13:
        return "LandContact"
    elif abs(res - 3e15) < 5e13:
        return "Roadway"
    elif abs(res - 4e15) < 5e13:
        return "Paths"
    elif abs(res - 5e15) < 5e13:
        return "Hitpoints"
    elif abs(res - 6e15) < 5e13:
        return "View Geometry"
    elif abs(res - 7e15) < 5e13:
        return "Fire Geometry"
    else:
        return f"Unknown ({res})"

for i, lod in enumerate(model.lods):
    ltype = classify_lod(lod.resolution)
    print(f"LOD {i}: {ltype}")
    print(f"  Points: {len(lod.points)}, Faces: {len(lod.faces)}")
    print(f"  Selections: {list(lod.selections.keys())}")
```

### Accessing LOD Data

```python
lod = model.lods[0]  # Visual LOD 0

# Vertex coordinates
for pt in lod.points:
    x, y, z = pt.coords        # tuple of 3 floats (meters)
    flags = pt.flags            # int (usually 0)
    # mass = pt.mass            # float (only meaningful in Geometry/Fire LODs)

# Face normals (shared pool, referenced by index)
for i, normal in enumerate(lod.facenormals):
    nx, ny, nz = normal         # tuple of 3 floats (unit vector)

# Faces (triangles or quads)
for face in lod.faces:
    tex = face.texture           # str: "addon\\data\\tex_co.paa" or ""
    mat = face.material          # str: "addon\\data\\mat.rvmat" or ""
    flags = face.flags           # int

    for vert in face.vertices:
        pt_idx = vert.point_index      # index into lod.points
        norm_idx = vert.normal_index   # index into lod.facenormals
        u, v = vert.uv                 # UV coordinates (floats)

        coords = lod.points[pt_idx].coords
        normal = lod.facenormals[norm_idx]

# Named selections
for name, sel in lod.selections.items():
    # sel.points is dict {Point: weight} (weight 0 or 1)
    selected_pts = [p for p, w in sel.points.items() if w > 0]
    selected_faces = [f for f, w in sel.faces.items() if w > 0]
    print(f"  Selection '{name}': {len(selected_pts)} pts, {len(selected_faces)} faces")

# Properties (Geometry LOD typically has 'class', 'autocenter', etc.)
if hasattr(lod, 'properties'):
    for key, val in lod.properties.items():
        print(f"  Property: {key} = {val}")
```

### Computing Bounding Box

```python
def lod_bbox(lod):
    """Returns (min_xyz, max_xyz, center_xyz) for a LOD."""
    if not lod.points:
        return None
    xs = [p.coords[0] for p in lod.points]
    ys = [p.coords[1] for p in lod.points]
    zs = [p.coords[2] for p in lod.points]
    lo = (min(xs), min(ys), min(zs))
    hi = (max(xs), max(ys), max(zs))
    center = ((lo[0]+hi[0])/2, (lo[1]+hi[1])/2, (lo[2]+hi[2])/2)
    return lo, hi, center

lo, hi, center = lod_bbox(model.lods[0])
print(f"BBox: [{lo}] to [{hi}], center={center}")
```

### Collecting All Textures and Materials

```python
def collect_paths(model):
    """Returns all unique texture and material paths across all LODs."""
    textures = set()
    materials = set()
    for lod in model.lods:
        for face in lod.faces:
            if face.texture:
                textures.add(face.texture)
            if face.material:
                materials.add(face.material)
    return textures, materials

textures, materials = collect_paths(model)
```

---

## P3D Diagnostic & Validation Toolkit

These patterns detect the most common generation bugs. Run them on every
generated .p3d BEFORE packaging.

### 1. Model Centering Check

DayZ expects the model roughly centered at Y=0 (ground plane). If the model
is entirely above or below Y=0, the item preview will appear offset or inverted.

```python
def check_centering(model):
    """Check if visual LODs are properly centered around Y=0."""
    issues = []
    lod0 = model.lods[0]
    lo, hi, center = lod_bbox(lod0)

    # Check if model is entirely on one side of Y=0
    ys = [p.coords[1] for p in lod0.points]
    below = sum(1 for y in ys if y < 0)
    above = sum(1 for y in ys if y > 0)
    total = len(ys)

    if below > total * 0.95:
        issues.append(f"MODEL BELOW GROUND: {below}/{total} vertices below Y=0. "
                       f"Center at Y={center[1]:.4f}. Fix: shift all verts by Y+{-center[1]:.4f}")
    elif above > total * 0.95 and center[1] > 0.05:
        issues.append(f"MODEL FLOATING: {above}/{total} vertices above Y=0. "
                       f"Center at Y={center[1]:.4f}")

    # Check ce_center in Memory LOD
    mem_lod = None
    for lod in model.lods:
        if lod.resolution > 1e14:
            mem_lod = lod
            break
    if mem_lod and "ce_center" in mem_lod.selections:
        ce_pts = [p for p, w in mem_lod.selections["ce_center"].points.items() if w > 0]
        if ce_pts:
            ce = ce_pts[0].coords
            dist = ((ce[0]-center[0])**2 + (ce[1]-center[1])**2 + (ce[2]-center[2])**2)**0.5
            if dist > 0.02:
                issues.append(f"ce_center at {ce} is {dist:.3f}m from geometric center {center}. "
                               f"Should be near the center for correct item preview.")

    return issues
```

### 2. Axis Consistency Check (Visual vs Geometry LODs)

Detects when the Blender Z→Y rotation was applied to visual LODs but NOT to
collision LODs (or vice versa). The BBox shape should be the same in all LODs.

```python
def check_axis_consistency(model):
    """Compare BBox proportions between Visual LOD 0 and Geometry LOD."""
    issues = []
    visual_lod = None
    geo_lod = None

    for lod in model.lods:
        if lod.resolution == 0.0:
            visual_lod = lod
        elif abs(lod.resolution - 1e13) < 1e11:
            geo_lod = lod

    if not visual_lod or not geo_lod:
        return issues

    v_lo, v_hi, _ = lod_bbox(visual_lod)
    g_lo, g_hi, _ = lod_bbox(geo_lod)

    # Compute axis sizes
    v_sizes = sorted([v_hi[i] - v_lo[i] for i in range(3)])
    g_sizes = sorted([g_hi[i] - g_lo[i] for i in range(3)])

    # Sizes should be proportionally similar (within 15% margin for padding)
    for i in range(3):
        if v_sizes[i] > 0.001:
            ratio = g_sizes[i] / v_sizes[i]
            if ratio < 0.7 or ratio > 1.5:
                issues.append(
                    f"AXIS MISMATCH: Visual sorted sizes {[f'{s:.4f}' for s in v_sizes]} "
                    f"vs Geometry sorted sizes {[f'{s:.4f}' for s in g_sizes]}. "
                    f"Likely Z/Y axis rotation applied to visual but not geometry LODs.")
                break

    # Also check if Y and Z ranges are literally swapped
    v_y_range = v_hi[1] - v_lo[1]
    v_z_range = v_hi[2] - v_lo[2]
    g_y_range = g_hi[1] - g_lo[1]
    g_z_range = g_hi[2] - g_lo[2]

    if (abs(v_y_range - g_z_range) < 0.01 and abs(v_z_range - g_y_range) < 0.01
            and abs(v_y_range - v_z_range) > 0.02):
        issues.append(
            f"Y/Z AXES SWAPPED: Visual Y={v_y_range:.4f} Z={v_z_range:.4f}, "
            f"Geometry Y={g_y_range:.4f} Z={g_z_range:.4f}. "
            f"Apply same rotation to ALL LODs.")

    return issues
```

### 3. UV Flip Detection

DayZ uses V=0 at top. If textures were generated with OpenGL convention
(V=0 at bottom), they appear vertically flipped. Detect by checking if
the majority of UVs have V near 0 for top-facing geometry.

```python
def check_uv_range(model):
    """Check UV coordinates for potential V-flip issues."""
    issues = []
    lod0 = model.lods[0]

    all_uvs = []
    for face in lod0.faces:
        for vert in face.vertices:
            all_uvs.append(vert.uv)

    if not all_uvs:
        return issues

    us = [uv[0] for uv in all_uvs]
    vs = [uv[1] for uv in all_uvs]

    # Check for out-of-range UVs
    out_of_range = sum(1 for u, v in all_uvs if u < -0.01 or u > 1.01 or v < -0.01 or v > 1.01)
    if out_of_range > len(all_uvs) * 0.1:
        issues.append(f"UV OUT OF RANGE: {out_of_range}/{len(all_uvs)} UVs outside [0,1]. "
                       f"U range [{min(us):.3f}, {max(us):.3f}], V range [{min(vs):.3f}, {max(vs):.3f}]")

    # Check for degenerate UVs (all same coordinate)
    u_spread = max(us) - min(us)
    v_spread = max(vs) - min(vs)
    if u_spread < 0.01 or v_spread < 0.01:
        issues.append(f"DEGENERATE UVs: spread U={u_spread:.4f}, V={v_spread:.4f}. "
                       f"UV unwrap likely failed.")

    return issues
```

> Note: `check_uv_range` only catches out-of-range/degenerate UVs on LOD0 — for the full UV
> audit (overlap, islands, texel density, mirrored islands) see the `dayz-p3d-audit` UV step
> (SP-051).

### 4. Face Winding Verification

After axis conversion, reverse face winding only for a reflection (det<0) or when
the source does not already carry engine winding (e.g. glTF/CCW); a proper det=+1
rotation otherwise preserves it. See `SKILL.md` Rule 12 and the warning at lines
257-263 above. If normals point inward,
textures render on the inside only. Check by comparing geometric normal
(from cross product) with stored normal.

```python
import numpy as np

def check_face_winding(model):
    """Verify generic-pipeline and vehicle winding (cross dot stored normal > 0).
    The expected sign depends on asset class; character source MLODs use < 0:
    see skills/dayz-characters/references/check_dayz_winding.py."""
    issues = []
    lod0 = model.lods[0]

    flipped = 0
    total = 0

    for face in lod0.faces:
        if len(face.vertices) < 3:
            continue

        pts = [lod0.points[v.point_index].coords for v in face.vertices[:3]]
        v1 = np.array(pts[1]) - np.array(pts[0])
        v2 = np.array(pts[2]) - np.array(pts[0])
        geo_normal = np.cross(v1, v2)
        length = np.linalg.norm(geo_normal)
        if length < 1e-10:
            continue
        geo_normal = geo_normal / length

        stored_normal = np.array(lod0.facenormals[face.vertices[0].normal_index])
        dot = np.dot(geo_normal, stored_normal)

        total = total + 1
        if dot < 0:
            flipped = flipped + 1

    if total > 0:
        pct = flipped * 100 / total
        if pct > 50:
            issues.append(f"WINDING REVERSED: {flipped}/{total} faces ({pct:.0f}%) have "
                           f"inverted normals. Check the source transform determinant "
                           f"before reversing faces; reversing after det=+1 yields "
                           f"100% flipped.")
        elif pct > 5:
            issues.append(f"PARTIAL WINDING ISSUE: {flipped}/{total} faces ({pct:.0f}%) "
                           f"have inverted normals. Some faces may render inside-out.")

    return issues
```

### 5. Proxy System Validation

Checks that proxy selections exist, have the correct naming format,
and that proxy faces are present in all visual LODs.

```python
def check_proxy_system(model):
    """Validate proxy selections across all visual LODs."""
    issues = []

    # Find all proxy selections in LOD 0
    lod0 = model.lods[0]
    proxy_sels = [name for name in lod0.selections.keys() if name.startswith("proxy:")]

    if not proxy_sels:
        return issues  # No proxies, nothing to check

    for proxy_name in proxy_sels:
        # Check naming format: proxy:path\model.p3d.NNN
        parts = proxy_name.split(".")
        if len(parts) < 3 or not parts[-1].isdigit() or len(parts[-1]) != 3:
            issues.append(f"PROXY NAME FORMAT: '{proxy_name}' should end with .p3d.NNN "
                           f"where NNN is 3-digit index (e.g., .001)")

        # Check presence in all visual LODs (res < 10)
        for i, lod in enumerate(model.lods):
            if lod.resolution < 10 and lod.resolution >= 0:
                if proxy_name not in lod.selections:
                    issues.append(f"PROXY MISSING in LOD {i} (res={lod.resolution}): "
                                   f"'{proxy_name}' not found. Must be in ALL visual LODs.")
                else:
                    sel = lod.selections[proxy_name]
                    pts = [p for p, w in sel.points.items() if w > 0]
                    faces = [f for f, w in sel.faces.items() if w > 0]
                    if len(pts) != 3 or len(faces) != 1:
                        issues.append(f"PROXY GEOMETRY in LOD {i}: expected 3 points + 1 face, "
                                       f"got {len(pts)} points + {len(faces)} faces")

    return issues
```

### 6. Named Selection Consistency

Animated selections must exist in ALL LOD types (visual, geometry, fire, view, shadow).

```python
def check_selection_consistency(model):
    """Verify named selections are consistent across LOD types."""
    issues = []

    # Collect selections per LOD type
    lod_types = {}
    for lod in model.lods:
        ltype = classify_lod(lod.resolution)
        lod_types[ltype] = set(lod.selections.keys())

    # Selections in Visual 0.0 should also be in Geometry, Fire, View (except proxy)
    visual_sels = lod_types.get("Visual 0.0", set())

    for sel_name in visual_sels:
        if sel_name.startswith("proxy:"):
            continue  # Proxies only in visual LODs
        if sel_name in ("zbytek", "AGGzbytek"):
            continue  # Default selection, not critical

        for required_type in ["Geometry", "Fire Geometry", "View Geometry"]:
            if required_type in lod_types and sel_name not in lod_types[required_type]:
                issues.append(f"SELECTION MISSING: '{sel_name}' in Visual but not in {required_type}")

    return issues
```

### 7. Collision LOD Property Check

Validates Rules 16 (autocenter on all collision LODs) and 17 (penetration
material on every face). Also keeps the original Geometry-specific checks
for mass and Components.

```python
# DayZ-modern collision LOD resolutions (Mikero verified)
COLLISION_LOD_RANGES = {
    "Geometry":     (0.99e13, 1.01e13),
    "LandContact":  (1.99e15, 2.01e15),
    "Roadway":      (2.99e15, 3.01e15),
    "Hitpoints":    (4.99e15, 5.01e15),
    "ViewGeometry": (5.99e15, 6.01e15),
    "FireGeometry": (6.99e15, 7.01e15),
}


def collision_lod_label(r):
    for name, (lo, hi) in COLLISION_LOD_RANGES.items():
        if lo < r < hi:
            return name
    return None


def check_geometry_properties(model):
    """Verify ALL collision LODs have required properties + mass + materials.
    Rule 16: autocenter=0 on every collision LOD (not just Geometry).
    Rule 17: every face in collision LODs has a penetration .rvmat material.
    """
    issues = []

    for lod in model.lods:
        label = collision_lod_label(lod.resolution)
        if label is None:
            continue
        props = dict(lod.properties) if hasattr(lod, "properties") else {}

        # Rule 16: autocenter=0 required on every collision LOD
        if props.get("autocenter") != "0":
            issues.append(f"{label}: missing 'autocenter=0' named property "
                          f"(found: {props.get('autocenter', '(none)')!r}). "
                          f"Without it the engine recenters this LOD by bbox, "
                          f"displacing collision mesh from visual (Rule 16).")

        # Rule 17: every face must have a penetration .rvmat material
        no_mat = sum(1 for f in lod.faces if not (getattr(f, 'material', '') or '').strip())
        if no_mat > 0:
            issues.append(f"{label}: {no_mat}/{len(lod.faces)} faces missing "
                          f"penetration material. Set face.material to e.g. "
                          f"'dz\\\\data\\\\data\\\\penetration\\\\wood_desk.rvmat' "
                          f"on every collision-LOD face (Rule 17).")

        # Geometry-specific extras
        if label == "Geometry":
            if "class" not in props:
                issues.append("GEOMETRY: missing 'class' property "
                              "(typically 'house' for static objects).")
            no_mass = sum(1 for p in lod.points if not hasattr(p, 'mass') or p.mass <= 0)
            if no_mass > 0:
                issues.append(f"GEOMETRY: {no_mass}/{len(lod.points)} points "
                              f"have no mass. All Geometry LOD points need mass >= 10.")
            components = [n for n in lod.selections.keys() if n.lower().startswith("component")]
            if not components:
                issues.append("GEOMETRY: no Component selections found. "
                              "Need at least Component01 for collision to work.")

    return issues
```

### Full Validation Runner

```python
def validate_p3d(filepath):
    """Run all validation checks on a .p3d file. Returns list of issues."""
    with open(filepath, "rb") as f:
        model = py3d.P3D(f)

    all_issues = []
    all_issues.extend(check_centering(model))
    all_issues.extend(check_axis_consistency(model))
    all_issues.extend(check_uv_range(model))
    all_issues.extend(check_face_winding(model))
    all_issues.extend(check_proxy_system(model))
    all_issues.extend(check_selection_consistency(model))
    all_issues.extend(check_geometry_properties(model))

    if not all_issues:
        print("ALL CHECKS PASSED")
    else:
        for issue in all_issues:
            print(f"[!] {issue}")

    return all_issues
```

---

## P3D Repair Patterns

Common fixes that can be applied programmatically after detection.

### Fix 1: Re-center Model at Y=0

```python
def recenter_model_y(model):
    """Shift all LODs so the visual model is centered at Y=0."""
    # Calculate center from Visual LOD 0
    lod0 = model.lods[0]
    ys = [p.coords[1] for p in lod0.points]
    y_center = (min(ys) + max(ys)) / 2.0
    offset = -y_center

    # Apply to ALL LODs (visual, geometry, fire, view, shadow, memory)
    for lod in model.lods:
        for pt in lod.points:
            x, y, z = pt.coords
            pt.coords = (x, y + offset, z)

    print(f"Shifted all vertices by Y+{offset:.4f}")
```

### Fix 2: Flip UV V-coordinate

```python
def flip_uv_v(model):
    """Invert V coordinate on all visual and shadow LODs."""
    count = 0
    for lod in model.lods:
        if lod.resolution < 12000:  # Visual + Shadow LODs
            for face in lod.faces:
                for vert in face.vertices:
                    u, v = vert.uv
                    vert.uv = (u, 1.0 - v)
                    count = count + 1
    print(f"Flipped V on {count} vertex UVs")
```

### Fix 3: Apply Axis Rotation to Specific LODs

```python
def apply_axis_rotation(lod):
    """Apply Blender Z-up → DayZ Y-up rotation: x'=x, y'=z, z'=-y."""
    for pt in lod.points:
        x, y, z = pt.coords
        pt.coords = (x, z, -y)

    new_normals = []
    for nx, ny, nz in lod.facenormals:
        new_normals.append((nx, nz, -ny))
    lod.facenormals = new_normals

    # This proper det=+1 rotation preserves winding (Rule 12).
    # Do not reverse face vertices here.
```

### Fix 4: Update Memory LOD ce_center

```python
def fix_ce_center(model):
    """Set ce_center to the geometric center of Visual LOD 0."""
    lod0 = model.lods[0]
    lo, hi, center = lod_bbox(lod0)

    for lod in model.lods:
        if lod.resolution > 1e14:  # Memory LOD
            if "ce_center" in lod.selections:
                pts = [p for p, w in lod.selections["ce_center"].points.items() if w > 0]
                if pts:
                    pts[0].coords = center
                    print(f"Updated ce_center to {center}")
```

---

## LOD-resolution values are DayZ-canonical (corrected 2026-07-18)

Every LOD-resolution reference in this file uses the DayZ 9-LOD set: Geometry 1e13, Memory 1e15,
LandContact 2e15, Roadway 3e15, Paths 4e15, Hitpoints 5e15, ViewGeometry 6e15, FireGeometry 7e15
(visual < 1e3; ShadowVolume ~1e4). The old Arma-3 `2e13`/`3e13` Fire/View ids that DayZ ignores are
NOT used. Source of truth: `py3d.classify_lod_resolution` (py3d DayZ fork).

---

## Iterate mass/CoM OFFLINE with `binarize.exe` (no PBO, no deploy) (added 2026-06-05, LL-080/LL-081)

Mass and CoM are NOT in config — they are baked from the Geometry LOD vertex weights at
binarize time (`references/vehicle-config-and-modelcfg.md` §1). So to verify what mass/CoM
the engine will actually use, you must binarize — but you do NOT need a full PBO build +
deploy + in-game cycle (~5 min each). AddonBuilder invokes `binarize.exe` internally with
the SAME bake, so calling it standalone gives the identical result in ~30 s:

```
"...\DayZ Tools\Bin\Binarize\binarize.exe" -always -maxProcesses=0 -addon=<addonDir> <srcDir> <dstDir> <wildcard.p3d>
```

Then read `ModelInfo.CoM` (and inertia) straight from the resulting ODOL. Verified gotcha
(LFQuad N1.5, in-game-confirmed): the source **must live under `P:\`** for binarize to
resolve the model's material paths (`lfquad\...`); from `C:\tmp` the materials fail to load
**but the mass bake still works correctly** (control validated) — so a `C:\tmp` run is fine
when all you need is the baked CoM/mass, not the textures.

This turns a 5-minute build+deploy+spawn loop into a 30-second offline loop for any
mass/CoM/ride-height/placement iteration on a vehicle. Use it together with the per-LOD
`#Mass#` assertion (`SKILL.md` "Mass assembly: `point.mass = None`...") and the
`ECE_PLACE_ON_SURFACE` placement rule: spawn height is governed by the **baked CoM**, not
Geometry-Ymin / LandContact / bbox — empirically `h_origin ≈ CoM.y − Geometry_Ymin` — so a
model whose mass never bakes (CoM=0) spawns at ground origin (underground) and gets ejected,
and no geometry tweak fixes it until the mass bakes. Cross-ref `dayz-p3d-audit` "#Mass# debe
vivir solo en Geometry LOD", LL-079 (LOD bisection isolated the bug), LL-080/LL-081.

> Reference tooling (LFQuad-specific but the pattern generalizes): `LFQuad_dev/tools/lfq_modelinfo.py`
> (raw ODOL `ModelInfo` reader → `MASS BAKED YES/NO` without odol_reader), `fix_firegeo_mass.py`.

## (added 2026-06-05) Building a collision LOD from scratch with py3d (not just reading) (SP-025)

py3d can CONSTRUCT collision geometry, not only read it. Object model:
- `Point.coords` / `.flags` / `.mass`
- `Vertex.point_index` / `.normal_index` / `.uv`
- `Face(all_points, all_normals).vertices` / `.flags` / `.texture` / `.material`
- `Selection(all_points, all_faces).points` / `.faces` (both dicts)
- `LOD.resolution` / `.points` / `.facenormals` / `.faces` / `.selections`

Faces reference normals by `normal_index` into the LOD `facenormals` pool (not per-face inline).
Cylinder pattern (e.g. a wheel collider): build an N-gon ring in the Y-Z plane -> `scipy.ConvexHull`
-> `simplices` are the faces and `equations` give outward normals. After construction, compare the
collider's winding sign against the Visual LOD of the same model and make the signs match (SP-003).
Invariant 18 records the expected absolute DayZ state as `dot(outward, cross_n) < 0`, but this
coordinate-system-agnostic relative comparison is the operational gate; add one selection
`component01` over all points + faces; add ViewGeometry (6e15) and FireGeometry (7e15) copies as needed.

Gotcha (non-idempotent): a script that ADDS LODs is NOT idempotent -- re-running it over already-
processed output DUPLICATES the LODs (invalid model). Guard it (skip if the LOD resolution already
exists) or run only over the original/backup. Origin: SP-025, LFQuad rebuild_wheel.py 2026-06-01;
py3d site-packages/py3d/__init__.py.
