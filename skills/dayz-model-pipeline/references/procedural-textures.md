# DayZ Procedural Texture Generation Reference

A comprehensive guide for generating industrial-quality procedural textures for DayZ 3D models. This reference covers texture map formats, noise fundamentals, multi-layer compositing, and complete material recipes.

## 1. DayZ Texture Map Types

DayZ uses a standard PBR-inspired texture pipeline. All procedural generation targets these formats:

### Color/Diffuse Map (`_co.png`)
- **Purpose**: RGB diffuse color that defines the base appearance
- **Resolution**: 512x512 for small objects (switches, boxes), 1024x1024 for large objects
- **Format**: PNG, RGB mode (not RGBA—DayZ tools ignore alpha)
- **Value range**: [0, 255] per channel
- **Usage**: What you see in-game, before lighting

### Normal Map (`_nohq.png`)
- **Purpose**: Encodes surface detail without adding geometry
- **Format**: PNG, RGB (Red=X, Green=Y, Blue=Z)
- **Convention**: OpenGL standard (Y+ is up)
- **Strength**: Typical range 0.5–2.0 in engine
- **Generation**: Derived from a height map using Sobel filtering
- **Key fact**: Completely eliminates the need for high-poly details

### Specular/Metallic/Detail Map (`_smdi.png`)
- **Purpose**: Controls material properties in three channels
- **Format**: PNG, RGB mode
- **R channel (Specular)**: 0=completely matte, 255=mirror-like reflective
  - Painted metal: ~80–100
  - Raw steel: ~180–200
  - Rubber: ~20–40
  - Glass/clear plastic: ~220–240
- **G channel (Gloss/Smoothness)**: 0=extremely rough, 255=perfectly smooth
  - Weathered paint: ~100–140
  - Fresh paint: ~150–180
  - Polished metal: ~200–240
  - Rough rubber: ~60–100
- **B channel (Detail Index)**: Usually 0 for single-layer detail; can be 1–5 for multi-layer blending
- **Note**: B channel rarely varies in simple procedural work; set to 0

### Resolution Guidelines
- **Small objects** (switches, adapters, knobs): 512x512
- **Medium objects** (electrical boxes, panels): 1024x1024
- **Large objects** (barrels, machinery): 1024x1024 or higher
- **Performance**: 512x512 is sufficient for most DayZ objects

---

## 2. OpenSimplex Noise Fundamentals

OpenSimplex is a gradient-based coherent noise function superior to Perlin noise for texture generation. It produces smooth, natural-looking variations.

### Installation
```bash
pip install opensimplex pillow --break-system-packages
```

### Basic Usage
```python
from opensimplex import OpenSimplex

# Create a generator with a seed for reproducibility
gen = OpenSimplex(seed=42)

# Sample noise at 2D coordinates
value = gen.noise2(x * frequency, y * frequency)

# Output range: [-1.0, 1.0]
# Normalize to [0, 1]: normalized = (value + 1.0) / 2.0
```

### Key Parameters

**Frequency**: Controls the scale of noise features
- Low frequency (0.01–0.05): Large, slow-varying features (overall color)
- Medium frequency (0.05–0.2): Mid-scale details (paint streaks, patches)
- High frequency (0.2–1.0): Fine texture (grain, micro-roughness)
- Very high frequency (1.0+): Sub-pixel detail

**Seed**: Determines the random pattern
- Different seeds produce entirely different patterns
- Same seed always produces the same pattern (reproducibility)
- Use `seed=np.random.randint(0, 1000000)` for variety

### Important Properties
- **Continuous**: Slightly different input coordinates produce slightly different values (smooth gradients)
- **Deterministic**: Same input always produces same output
- **Non-repeating**: Effective period is very large; no visible tiling artifacts
- **Range**: Always [-1, 1]; manual normalization required

---

## 3. Fractional Brownian Motion (FBM)

FBM layers multiple octaves of noise at increasing frequencies and decreasing amplitudes, creating natural-looking complexity.

### Complete Working Function
```python
def fbm(gen, x, y, octaves=6, lacunarity=2.0, gain=0.5):
    """
    Fractional Brownian Motion: multi-layer noise composition.

    Args:
        gen: OpenSimplex generator instance
        x, y: Coordinates to sample
        octaves: Number of noise layers (more = more detail)
        lacunarity: Frequency multiplier per octave (2.0 standard)
        gain: Amplitude decay per octave (persistence; 0.5 standard)

    Returns:
        float: FBM value in range [-amplitude, amplitude]
    """
    value = 0.0
    amplitude = 1.0
    frequency = 1.0
    max_amplitude = 0.0

    for _ in range(octaves):
        value += amplitude * gen.noise2(x * frequency, y * frequency)
        max_amplitude += amplitude
        frequency *= lacunarity
        amplitude *= gain

    # Normalize to approximately [-1, 1]
    return value / max_amplitude if max_amplitude > 0 else 0.0
```

### Parameter Effects

**octaves** (typical: 4–8)
- 4 octaves: Smooth, large-scale variation
- 6 octaves: Good balance for most objects
- 8+ octaves: Intricate detail, computationally expensive

**lacunarity** (typical: 2.0–2.5)
- Controls frequency increase per octave
- 2.0: Standard; each octave is twice as fine
- 1.5: Slower frequency increase; smoother result
- 2.5: Faster frequency increase; more detail variety

**gain/persistence** (typical: 0.4–0.6)
- Controls amplitude decrease per octave
- 0.5: Standard; each octave contributes half of previous
- 0.6: Higher amplitude at high frequencies; more visible detail
- 0.4: Lower amplitude; smoother overall appearance

### Typical Combinations
```python
# Smooth, flowing textures (paint variation)
fbm(gen, x, y, octaves=4, lacunarity=2.0, gain=0.5)

# Detailed, grainy textures (rust, corrosion)
fbm(gen, x, y, octaves=7, lacunarity=2.2, gain=0.6)

# Subtle variation (worn metal)
fbm(gen, x, y, octaves=5, lacunarity=2.0, gain=0.4)
```

---

## 4. Multi-Layer Compositing: The Key to Realism

The difference between generic and industrial-quality textures is **layering**. Each layer serves a specific purpose and is composed using blend modes.

### Layering Strategy

**Layer 1: Base Color**
- Purpose: Overall color and large-scale variation
- Frequency: 0.02–0.05 (low)
- Octaves: 3–4
- Effect: Foundation; sets the dominant color
- Example: Dark gray (RGB 60, 60, 70) with ±10% variation

**Layer 2: Flow/Streak Pattern**
- Purpose: Directional wear (paint flow, application marks)
- Frequency: Y-axis compressed 0.1, X-axis stretched 0.02
- Octaves: 4
- Effect: Streaky, directional pattern
- Blend: Overlay or multiply
- Example: Factory paint application patterns

**Layer 3: Grain Texture**
- Purpose: Surface micro-texture (metal grain, plastic texture)
- Frequency: 0.3–0.5 (medium-high)
- Octaves: 5
- Effect: Visible but subtle grain
- Blend: Overlay, low opacity (0.2–0.4)
- Example: Brushed metal or molded plastic

**Layer 4: Micro-Variation**
- Purpose: Sub-pixel detail (dust, fingerprints)
- Frequency: 1.0–2.0 (very high)
- Octaves: 3
- Effect: Almost invisible; adds realism
- Amplitude: 0.02–0.05 (very low)
- Blend: Soft light or overlay, minimal opacity

**Layer 5: Wear/Edge Damage**
- Purpose: Lighter areas at edges where paint/coating wore away
- Based on: Position mask (edges) + noise
- Effect: Reveals underlying material at edges
- Blend: Additive or overlay
- Example: Light gray where dark paint is worn

**Layer 6: Sparse Details**
- Purpose: Random imperfections (rust spots, dirt, scratches)
- Frequency: 0.1–0.2 with thresholding
- Effect: Discrete spots/marks
- Blend: Multiply (for dark spots) or screen (for light marks)
- Example: Orange-brown rust over base color

### Blend Mode Functions

```python
import numpy as np

def blend_multiply(base, layer):
    """Darkens: result = base * layer"""
    return base * layer

def blend_screen(base, layer):
    """Lightens: result = 1 - (1 - base) * (1 - layer)"""
    return 1.0 - (1.0 - base) * (1.0 - layer)

def blend_overlay(base, layer):
    """Conditional: multiply if base < 0.5, screen otherwise"""
    return np.where(
        base < 0.5,
        2.0 * base * layer,
        1.0 - 2.0 * (1.0 - base) * (1.0 - layer)
    )

def blend_soft_light(base, layer):
    """Subtle overlay: useful for grain"""
    return np.where(
        layer < 0.5,
        base - (1.0 - 2.0 * layer) * base * (1.0 - base),
        base + (2.0 * layer - 1.0) * (
            (16.0 * base - 12.0) * base + 4.0) * base * (1.0 - base)
        if base < 0.25 else
        np.sqrt(base)
    )

def blend_lerp(base, layer, alpha):
    """Linear interpolation: result = base * (1 - alpha) + layer * alpha"""
    return base * (1.0 - alpha) + layer * alpha
```

### Complete Multi-Layer Composition Example
```python
import numpy as np
from PIL import Image
from opensimplex import OpenSimplex

def composite_texture(width, height, seed=42):
    """Generate a complete multi-layer texture."""
    gen = OpenSimplex(seed=seed)
    canvas = np.ones((height, width, 3), dtype=np.float32) * 0.5

    # Layer 1: Base color (dark gray with variation)
    base_layer = np.zeros((height, width), dtype=np.float32)
    for y in range(height):
        for x in range(width):
            val = fbm(gen, x / width * 2, y / height * 2, octaves=3, gain=0.5)
            base_layer[y, x] = (val + 1.0) / 2.0

    base_color = np.array([0.25, 0.25, 0.27])  # Dark gray
    canvas *= base_color * blend_lerp(np.ones_like(base_layer), base_layer, 0.3)

    # Layer 2: Directional streaks
    streak_layer = np.zeros((height, width), dtype=np.float32)
    for y in range(height):
        for x in range(width):
            val = fbm(gen, x / width * 0.05, y / height * 0.3, octaves=4)
            streak_layer[y, x] = (val + 1.0) / 2.0

    for c in range(3):
        canvas[:, :, c] = blend_overlay(canvas[:, :, c], streak_layer, 0.4)

    # Layer 3: Grain
    grain_layer = np.zeros((height, width), dtype=np.float32)
    for y in range(height):
        for x in range(width):
            val = fbm(gen, x / width * 5, y / height * 5, octaves=5, gain=0.5)
            grain_layer[y, x] = (val + 1.0) / 2.0

    for c in range(3):
        canvas[:, :, c] = blend_lerp(canvas[:, :, c], grain_layer, 0.15)

    # Layer 4: Edge wear (lighter at edges)
    edge_mask = np.ones((height, width), dtype=np.float32)
    for y in range(height):
        for x in range(width):
            dist_from_edge = min(x, y, width - x, height - y) / min(width, height)
            edge_mask[y, x] = dist_from_edge

    wear_amount = 0.05
    for c in range(3):
        canvas[:, :, c] = blend_lerp(canvas[:, :, c], edge_mask, wear_amount)

    # Clamp to [0, 1]
    canvas = np.clip(canvas, 0.0, 1.0)

    return canvas
```

---

## 5. Material-Specific Recipes

Complete texture generation recipes for common DayZ electrical objects.

### Recipe 1: Painted Metal (Industrial Gray/Green)

Common for electrical boxes, cabinets, control panels.

```python
def generate_painted_metal(width=512, height=512, seed=42):
    """Industrial painted metal with edge wear."""
    gen = OpenSimplex(seed=seed)
    canvas = np.ones((height, width, 3), dtype=np.float32)

    # Base: Dark gray (0.28, 0.28, 0.30)
    base_color = np.array([0.28, 0.28, 0.30])
    canvas *= base_color

    # Large-scale color variation (±0.08)
    variation = np.zeros((height, width), dtype=np.float32)
    for y in range(height):
        for x in range(width):
            val = fbm(gen, x / width * 2, y / height * 2, octaves=3, gain=0.5)
            variation[y, x] = (val + 1.0) / 2.0
    variation = variation * 0.16 - 0.08  # Scale to [-0.08, 0.08]
    for c in range(3):
        canvas[:, :, c] = np.clip(canvas[:, :, c] + variation, 0, 1)

    # Paint streak direction (top to bottom, factory application)
    streaks = np.zeros((height, width), dtype=np.float32)
    for y in range(height):
        for x in range(width):
            val = fbm(gen, x / width * 0.08, y / height * 0.2, octaves=4)
            streaks[y, x] = (val + 1.0) / 2.0
    streak_amount = 0.12
    for c in range(3):
        canvas[:, :, c] = blend_lerp(canvas[:, :, c], streaks * 0.95, streak_amount)

    # Grain (metallic substrate show-through)
    grain = np.zeros((height, width), dtype=np.float32)
    for y in range(height):
        for x in range(width):
            val = fbm(gen, x / width * 2.0, y / height * 2.0, octaves=5, gain=0.6)
            grain[y, x] = (val + 1.0) / 2.0
    for c in range(3):
        canvas[:, :, c] = blend_overlay(canvas[:, :, c], grain, 0.08)

    # Edge wear (light gray where paint is worn, revealing metal)
    edge_mask = np.zeros((height, width), dtype=np.float32)
    for y in range(height):
        for x in range(width):
            dist = min(x, y, width - x, height - y) / max(width, height)
            edge_mask[y, x] = 1.0 - (dist * 0.3)  # Wear extends 30% inward
    edge_color = 0.40  # Lighter gray
    for c in range(3):
        canvas[:, :, c] = blend_lerp(canvas[:, :, c], edge_color, edge_mask * 0.08)

    canvas = np.clip(canvas, 0, 1)
    return canvas
```

**SMDI Map for Painted Metal**:
- R (Specular): 85–95 (slightly reflective)
- G (Gloss): 120–140 (semi-matte factory finish)
- B (Detail): 0

### Recipe 2: Brushed Steel/Aluminum

Directional grain for metal surfaces, high reflectivity.

```python
def generate_brushed_steel(width=512, height=512, direction='horizontal', seed=42):
    """Brushed metal with strong directional grain."""
    gen = OpenSimplex(seed=seed)
    canvas = np.ones((height, width, 3), dtype=np.float32) * 0.50

    # Base: Medium gray (0.50, 0.50, 0.52)
    base_color = np.array([0.50, 0.50, 0.52])
    canvas *= base_color

    # Strong directional grain (compressed on one axis)
    grain = np.zeros((height, width), dtype=np.float32)
    for y in range(height):
        for x in range(width):
            if direction == 'horizontal':
                val = fbm(gen, x / width * 0.1, y / height * 8.0, octaves=6, gain=0.5)
            else:  # vertical
                val = fbm(gen, x / width * 8.0, y / height * 0.1, octaves=6, gain=0.5)
            grain[y, x] = (val + 1.0) / 2.0
    for c in range(3):
        canvas[:, :, c] = blend_overlay(canvas[:, :, c], grain, 0.25)

    # Micro-variation (subtle scratches)
    micro = np.zeros((height, width), dtype=np.float32)
    for y in range(height):
        for x in range(width):
            val = fbm(gen, x / width * 3.0, y / height * 3.0, octaves=4, gain=0.6)
            micro[y, x] = (val + 1.0) / 2.0
    for c in range(3):
        canvas[:, :, c] = blend_soft_light(canvas[:, :, c], micro, 0.05)

    canvas = np.clip(canvas, 0, 1)
    return canvas
```

**SMDI Map for Brushed Steel**:
- R (Specular): 180–200 (highly reflective)
- G (Gloss): 200–220 (highly smooth)
- B (Detail): 0

### Recipe 3: Rubber/Plastic (Cable Insulation)

Matte, smooth, minimal metallic properties.

```python
def generate_rubber(width=512, height=512, color=(0.15, 0.15, 0.18), seed=42):
    """Matte rubber or plastic insulation."""
    gen = OpenSimplex(seed=seed)
    canvas = np.ones((height, width, 3), dtype=np.float32)

    # Base: Dark matte color (black rubber default)
    base_color = np.array(color)
    canvas *= base_color

    # Smooth, low-frequency variation (molding patterns)
    smooth_var = np.zeros((height, width), dtype=np.float32)
    for y in range(height):
        for x in range(width):
            val = fbm(gen, x / width * 0.5, y / height * 0.5, octaves=2, gain=0.4)
            smooth_var[y, x] = (val + 1.0) / 2.0
    smooth_var = smooth_var * 0.08 - 0.04
    for c in range(3):
        canvas[:, :, c] = np.clip(canvas[:, :, c] + smooth_var, 0, 1)

    # Very subtle grain (not metallic)
    grain = np.zeros((height, width), dtype=np.float32)
    for y in range(height):
        for x in range(width):
            val = fbm(gen, x / width * 1.0, y / height * 1.0, octaves=3, gain=0.5)
            grain[y, x] = (val + 1.0) / 2.0
    for c in range(3):
        canvas[:, :, c] = blend_lerp(canvas[:, :, c], grain, 0.03)

    canvas = np.clip(canvas, 0, 1)
    return canvas
```

**SMDI Map for Rubber**:
- R (Specular): 20–40 (non-reflective)
- G (Gloss): 60–100 (rough surface)
- B (Detail): 0

### Recipe 4: Rust/Corrosion Overlay

Apply over base paint for realistic weathering.

```python
def generate_rust_overlay(width=512, height=512, density=0.15, seed=42):
    """Rust patches for overlay on painted metal."""
    gen = OpenSimplex(seed=seed)
    rust = np.zeros((height, width, 3), dtype=np.float32)

    # Generate rust distribution using thresholded noise
    rust_mask = np.zeros((height, width), dtype=np.float32)
    for y in range(height):
        for x in range(width):
            val = fbm(gen, x / width * 1.5, y / height * 1.5, octaves=5, gain=0.6)
            noise_val = (val + 1.0) / 2.0
            rust_mask[y, x] = max(0, noise_val - (1.0 - density)) / density

    # Orange-brown rust color: (0.65, 0.35, 0.10)
    rust_color = np.array([0.65, 0.35, 0.10])

    # Add variation within rust patches
    rust_var = np.zeros((height, width), dtype=np.float32)
    for y in range(height):
        for x in range(width):
            val = fbm(gen, x / width * 4.0, y / height * 4.0, octaves=4, gain=0.5)
            rust_var[y, x] = (val + 1.0) / 2.0
    rust_var = rust_var * 0.3 + 0.7  # Range [0.7, 1.0]

    for c in range(3):
        rust[:, :, c] = rust_color[c] * rust_mask * rust_var

    return rust, rust_mask
```

**Usage**: Composite rust overlay onto base texture:
```python
base = generate_painted_metal()
rust, rust_mask = generate_rust_overlay()
result = blend_multiply(base, rust + (1.0 - rust_mask) * np.ones_like(base))
```

---

## 6. Normal Map Generation

Convert height maps to surface normals using Sobel filtering.

```python
def height_to_normal(height_map, strength=1.0):
    """
    Convert height map to normal map using Sobel filtering.

    Args:
        height_map: 2D numpy array [0, 1] representing surface height
        strength: Bump intensity (0.5–2.0 typical)

    Returns:
        3D numpy array [height, width, 3] with normal vectors
    """
    height = height_map.astype(np.float32)
    h, w = height.shape

    # Sobel kernels for X and Y gradients
    sobel_x = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float32)
    sobel_y = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], dtype=np.float32)

    # Compute gradients via convolution
    grad_x = np.zeros((h, w), dtype=np.float32)
    grad_y = np.zeros((h, w), dtype=np.float32)

    for y in range(1, h - 1):
        for x in range(1, w - 1):
            patch = height[y-1:y+2, x-1:x+2]
            grad_x[y, x] = np.sum(patch * sobel_x)
            grad_y[y, x] = np.sum(patch * sobel_y)

    # Apply strength scaling
    grad_x *= strength
    grad_y *= strength

    # Convert gradients to normal vectors
    normals = np.zeros((h, w, 3), dtype=np.float32)
    normals[:, :, 0] = grad_x  # X component
    normals[:, :, 1] = grad_y  # Y component
    normals[:, :, 2] = 1.0     # Z component (blue channel up)

    # Normalize to unit vectors
    lengths = np.sqrt(
        normals[:, :, 0]**2 + normals[:, :, 1]**2 + normals[:, :, 2]**2
    )
    lengths[lengths == 0] = 1.0  # Avoid division by zero

    normals[:, :, 0] /= lengths
    normals[:, :, 1] /= lengths
    normals[:, :, 2] /= lengths

    # Convert from [-1, 1] to [0, 1] for texture storage
    normals = (normals + 1.0) / 2.0
    normals = np.clip(normals, 0, 1)

    return normals

def generate_normal_from_texture(diffuse_path, strength=1.0):
    """Generate normal map from existing diffuse texture."""
    img = Image.open(diffuse_path).convert('RGB')
    rgb = np.array(img, dtype=np.float32) / 255.0

    # Luminance-based height map
    height = 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]

    normals = height_to_normal(height, strength)
    normals_uint8 = (normals * 255).astype(np.uint8)

    return Image.fromarray(normals_uint8, mode='RGB')
```

**Key Parameters**:
- **strength**: 0.5 = subtle bumps, 1.0 = moderate, 2.0 = pronounced detail
- **DayZ convention**: Green channel encodes Y (up) direction

---

## 7. SMDI Map Generation and Values

The SMDI map controls material properties. Generate per-material values:

```python
def generate_smdi_map(width, height, material='painted_metal'):
    """Generate SMDI map for specified material."""

    # Material property presets
    materials = {
        'painted_metal': {'r': 85, 'g': 130, 'b': 0},
        'brushed_steel': {'r': 190, 'g': 210, 'b': 0},
        'raw_steel': {'r': 180, 'g': 200, 'b': 0},
        'polished_aluminum': {'r': 220, 'g': 230, 'b': 0},
        'rubber': {'r': 25, 'g': 70, 'b': 0},
        'plastic': {'r': 40, 'g': 90, 'b': 0},
        'glass': {'r': 230, 'g': 245, 'b': 0},
        'worn_paint': {'r': 70, 'g': 100, 'b': 0},
    }

    props = materials.get(material, materials['painted_metal'])

    # Create solid SMDI map with slight variation
    smdi = np.zeros((height, width, 3), dtype=np.uint8)
    smdi[:, :, 0] = props['r']  # Specular
    smdi[:, :, 1] = props['g']  # Gloss
    smdi[:, :, 2] = props['b']  # Detail index

    # Optional: Add subtle variation to gloss
    gen = OpenSimplex(seed=99)
    for y in range(height):
        for x in range(width):
            var = gen.noise2(x / width * 2, y / height * 2)
            var = int((var + 1) / 2 * 15)  # ±15 variation
            smdi[y, x, 1] = np.clip(smdi[y, x, 1] + var, 0, 255)

    return Image.fromarray(smdi, mode='RGB')
```

**Material SMDI Values**:

| Material | R (Specular) | G (Gloss) | Notes |
|----------|--------------|-----------|-------|
| Painted Metal | 85–95 | 120–140 | Standard industrial |
| Brushed Steel | 180–200 | 200–220 | Directional grain |
| Raw Steel | 180–200 | 180–200 | Slightly rougher than brushed |
| Polished Aluminum | 220–230 | 230–245 | Mirror-like |
| Rubber | 25–35 | 60–90 | Very matte |
| Plastic (Matte) | 40–50 | 80–110 | Slightly reflective |
| Glass | 230–245 | 240–255 | Highly transparent/reflective |
| Worn Paint | 70–80 | 100–120 | Aged, weathered |

---

## 8. Ambient Occlusion Integration

If AO was baked in Blender, incorporate it to add depth at zero geometry cost:

```python
def integrate_ao(diffuse_path, ao_path):
    """Multiply AO into diffuse to darken recessed areas."""
    diffuse = Image.open(diffuse_path).convert('RGB')
    ao = Image.open(ao_path).convert('L')

    # Ensure same size
    ao = ao.resize(diffuse.size, Image.Resampling.LANCZOS)

    diffuse_array = np.array(diffuse, dtype=np.float32) / 255.0
    ao_array = np.array(ao, dtype=np.float32) / 255.0

    # Convert AO to RGB for multiplication
    ao_rgb = np.stack([ao_array, ao_array, ao_array], axis=2)

    # Blend: darken by AO
    result = diffuse_array * ao_rgb
    result = (result * 255).astype(np.uint8)

    return Image.fromarray(result, mode='RGB')
```

---

## 9. Complete Example: Industrial Electrical Box

Full script generating all three texture maps (512x512) for a typical DayZ electrical enclosure.

```python
import numpy as np
from PIL import Image
from opensimplex import OpenSimplex

def generate_electrical_box_textures(output_dir='textures', seed=42):
    """Generate complete texture set for electrical box."""

    width, height = 512, 512
    gen = OpenSimplex(seed=seed)

    # ===== DIFFUSE/COLOR MAP =====
    diffuse = generate_painted_metal(width, height, seed)

    # Add rust overlay (small patches)
    rust, rust_mask = generate_rust_overlay(width, height, density=0.08, seed=seed+1)
    for c in range(3):
        diffuse[:, :, c] = blend_multiply(diffuse[:, :, c],
                                          rust[:, :, c] + (1 - rust_mask))

    # Add small scuffed/worn areas
    scuffs = np.zeros((height, width), dtype=np.float32)
    for y in range(height):
        for x in range(width):
            val = fbm(gen, x / width * 3, y / height * 3, octaves=4, gain=0.6)
            if (val + 1) / 2 > 0.85:  # Only 15% of surface
                scuffs[y, x] = 1.0

    scuff_color = 0.45  # Light gray
    for c in range(3):
        diffuse[:, :, c] = blend_lerp(diffuse[:, :, c], scuff_color, scuffs * 0.06)

    diffuse = np.clip(diffuse, 0, 1)
    diffuse_uint8 = (diffuse * 255).astype(np.uint8)
    Image.fromarray(diffuse_uint8, mode='RGB').save(f'{output_dir}/box_co.png')

    # ===== NORMAL MAP =====
    # Create height map from diffuse luminance
    height_map = (0.299 * diffuse[:, :, 0] +
                  0.587 * diffuse[:, :, 1] +
                  0.114 * diffuse[:, :, 2])

    normals = height_to_normal(height_map, strength=1.2)
    normals_uint8 = (normals * 255).astype(np.uint8)
    Image.fromarray(normals_uint8, mode='RGB').save(f'{output_dir}/box_nohq.png')

    # ===== SMDI MAP =====
    smdi = generate_smdi_map(width, height, material='painted_metal')
    smdi.save(f'{output_dir}/box_smdi.png')

    print(f"Generated textures:")
    print(f"  {output_dir}/box_co.png (diffuse)")
    print(f"  {output_dir}/box_nohq.png (normal)")
    print(f"  {output_dir}/box_smdi.png (specular/metallic/detail)")

# Run: generate_electrical_box_textures()
```

---

## 10. Common Mistakes and Solutions

### Mistake 1: Using random() Instead of Coherent Noise
```python
# WRONG: Looks like TV static
for y in range(height):
    for x in range(width):
        canvas[y, x] = random.random()

# CORRECT: Smooth, natural variation
for y in range(height):
    for x in range(width):
        val = gen.noise2(x * frequency, y * frequency)
        canvas[y, x] = (val + 1.0) / 2.0
```

### Mistake 2: Forgetting Output Normalization
```python
# WRONG: Output range [-1, 1] becomes black/barely visible
noise_val = gen.noise2(x, y)  # Range [-1, 1]
pixel = int(noise_val * 255)  # Mostly negative or <128

# CORRECT: Normalize to [0, 1]
noise_val = gen.noise2(x, y)
normalized = (noise_val + 1.0) / 2.0  # Range [0, 1]
pixel = int(normalized * 255)  # Full range [0, 255]
```

### Mistake 3: Using Single-Layer Noise
```python
# WRONG: Looks obviously procedural, too uniform
val = gen.noise2(x * 0.1, y * 0.1)

# CORRECT: Multi-octave layering adds realism
val = fbm(gen, x, y, octaves=6, lacunarity=2.0, gain=0.5)
```

### Mistake 4: Same Frequency for All Details
```python
# WRONG: No scale variety, boring
noise1 = fbm(gen, x * 0.1, y * 0.1, octaves=6)
noise2 = fbm(gen, x * 0.1, y * 0.1, octaves=6)

# CORRECT: Different frequencies for different purposes
base = fbm(gen, x * 0.02, y * 0.02, octaves=3)  # Large features
grain = fbm(gen, x * 0.3, y * 0.3, octaves=5)   # Texture
micro = fbm(gen, x * 2.0, y * 2.0, octaves=3)   # Detail
```

### Mistake 5: Wrong Color Space
```python
# WRONG: RGBA mode loses information in DayZ
img = Image.new('RGBA', (512, 512))  # DayZ ignores alpha

# CORRECT: RGB mode only
img = Image.new('RGB', (512, 512))
img.save('texture_co.png')  # No alpha channel
```

### Mistake 6: Blown-Out or Invisible Textures
```python
# WRONG: Values outside [0, 1] range cause clipping
canvas[y, x] = 2.5  # Gets clipped to 1.0 (white)
canvas[y, x] = -0.5  # Gets clipped to 0.0 (black)

# CORRECT: Clamp explicitly
canvas = np.clip(canvas, 0.0, 1.0)
```

### Mistake 7: Uneven Normal Strength
```python
# WRONG: Normal map completely flat (strength 0)
normals = height_to_normal(height_map, strength=0)

# CORRECT: Strength 0.5–2.0 for visible bumps
normals = height_to_normal(height_map, strength=1.2)
```

---

## 11. Tips for Industrial Quality

1. **Reference Real Objects**: Photograph actual electrical boxes, metal surfaces, worn paint. Study the variation patterns.

2. **Layer Intentionally**: Each layer should serve a purpose (base color, wear, grain, details). Random layering looks chaotic.

3. **Respect Scale**: Frequency should reflect real-world size. Paint streaks are larger than metal grain.

4. **Use Edge Masks**: Wear and weathering concentrate at edges and corners. Use position-based masks.

5. **Add Imperfections**: Perfect surfaces look fake. Include dust, scratches, fingerprints, corrosion.

6. **Test in Engine**: Textures appear different under DayZ lighting. Preview early and adjust strength values.

7. **Preserve Reproducibility**: Use fixed seeds for consistent iteration. Document seed values.

8. **Optimize Frequency**: High-frequency noise is CPU expensive. Precompute at maximum resolution and downscale if needed.

9. **Composite Carefully**: Blend modes matter. Test multiply, screen, overlay to find the right look.

10. **SMDI Accuracy**: Match specular/gloss values to real material properties. Research typical values for your material.

---

## Quick Reference: Standard Texture Settings

```python
# Small electrical object (512x512)
gen = OpenSimplex(seed=42)
width, height = 512, 512

# Painted metal box
diffuse = generate_painted_metal(512, 512, seed=42)
height_map = compute_luminance(diffuse)
normals = height_to_normal(height_map, strength=1.2)
smdi = generate_smdi_map(512, 512, material='painted_metal')

# Save
Image.fromarray((diffuse * 255).astype(np.uint8), 'RGB').save('box_co.png')
Image.fromarray((normals * 255).astype(np.uint8), 'RGB').save('box_nohq.png')
smdi.save('box_smdi.png')
```

This reference provides everything needed to generate industrial-quality procedural textures for DayZ objects. Start with basic recipes and layer additional complexity based on visual feedback in-engine.
