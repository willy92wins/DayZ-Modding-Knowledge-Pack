---
name: dayz-3d-viewer
description: >
  Convert DayZ .p3d models, .paa textures, and .rvmat materials into interactive
  Three.js 3D viewers. Supports MLOD .p3d files (via py3d), PAA texture decoding
  (DXT1/DXT5/DXT3/RGBA4444/RGBA5551/LuminanceAlpha/RGBA8888 with LZO/LZSS),
  RVMAT material parsing with emissive/specular support, and outputs .glb (binary glTF)
  + standalone HTML viewer. Two viewer modes: embedded (works in Claude chat sandbox —
  no fetch, no GLTFLoader) and web (GLTFLoader + external .glb for deployment).
  Use when user mentions: 3D viewer, p3d viewer, PAA to PNG, PAA converter, texture
  conversion, model preview, model visualization, Three.js DayZ, glTF export, GLB
  convert, interactive model, web 3D model, item display, wiki model viewer, or
  any request to visualize/preview/display a DayZ .p3d model. Also trigger for
  PAA↔PNG conversion requests even without a 3D model context. Always consult this
  skill before attempting any DayZ 3D visualization or PAA texture work.
---

# DayZ 3D Viewer — P3D + PAA + RVMAT → Interactive Three.js

Converts DayZ mod assets into interactive 3D viewers for chat and web.
Battle-tested with real LFPG Push Button model (328 verts, 640 faces, 4 materials, DXT1+LZO textures).

The executable lives in the pack tool `tools/dayz-3d-viewer`. This skill is
the playbook; do not look for `scripts/` or a vendored py3d wheel here.

## Install Dependencies

```bash
pip install -e tools/py3d
pip install -e "tools/dayz-3d-viewer[all]"
# Preferred when python-lzo will not compile (Windows Py3.14+ / sandbox):
#   pip install lzokay
#   python -m dayz_3d_viewer install-lzo-shim
# CRITICAL: py3d = the pack DayZ fork >= 1.5.0 (tools/py3d).
# NUNCA `pip install py3d` (PyPI = point-cloud lib) NI git+upstream (sin guards).
python -c "import py3d; assert getattr(py3d,'IS_DAYZ_FORK',False) and tuple(map(int,py3d.__version__.split('.')))>=(1,5,0), (py3d.__version__, py3d.__file__)"
```

## Commands

All via `python -m dayz_3d_viewer`:

| Command | Purpose |
|--------|---------|
| `paa-to-png` | PAA → PNG converter (DXT1/5/3, RGBA, LumAlpha, with LZO/LZSS) |
| `p3d-to-glb` | P3D MLOD → glTF/GLB converter (geometry + textures + RVMAT materials) |
| `parse-rvmat` | RVMAT parser (colors, specular, emissive, texture stage mapping) |
| `build-viewer` | Full orchestration (glb + HTML; embedded or web) |
| `install-lzo-shim` | Installs an lzokay-based `lzo` shim — preferred route when `python-lzo` will not compile (Windows Py3.14+/sandbox) |

Public library names are unchanged: `convert_paa_to_png`, `parse_rvmat`,
`extract_geometry_for_viewer`, `generate_viewer_html`, `p3d_to_glb`,
`run_pipeline`.

## Scripts

In the Cowork plugin projection these were `scripts/*.py`. In this pack they
map to `python -m dayz_3d_viewer` (see Commands above). Historical names:

| Script | Pack command |
|--------|---------|
| `paa_to_png.py` | `paa-to-png` |
| `p3d_to_gltf.py` | `p3d-to-glb` |
| `rvmat_parser.py` | `parse-rvmat` |
| `viewer_template.py` / `pipeline.py` | `build-viewer` |
| `install_lzo_shim.py` | `install-lzo-shim` |

## Two Viewer Modes

### Embedded (for Claude chat / sandboxed iframes)

Bakes geometry as `Float32Array` + textures as `data:image/png;base64` directly into HTML.
Uses raw `THREE.BufferGeometry` + `THREE.MeshStandardMaterial` — **NO GLTFLoader, NO fetch,
NO blob URLs**. This is critical because Claude's artifact sandbox blocks all network requests
including `fetch()`, `XMLHttpRequest`, and `URL.createObjectURL()`.

```python
from dayz_3d_viewer import extract_geometry_for_viewer, generate_viewer_html

geo = extract_geometry_for_viewer('model.p3d', texture_map={'base_co': 'base_co.png'}, rvmat_data=rvmats)
generate_viewer_html(model_name='My Model', mode='embedded', geometry_data=geo, output_path='viewer.html')
```

### Web (for deployment)

References external `.glb` file via `GLTFLoader.load()`. Separate files, cacheable.

```python
generate_viewer_html(model_name='My Model', mode='web', glb_url='model.glb', output_path='viewer.html')
```

Generated HTML loads **three.js 0.160.0 from jsDelivr**. It is not embedded;
a render needs a network. See `tools/dayz-3d-viewer/README.md`.

## Recommended Workflow (Chat)

This is the proven workflow for when user uploads `.p3d` + `.paa` + `.rvmat` files:

```python
from dayz_3d_viewer import convert_paa_to_png, parse_rvmat
from dayz_3d_viewer import extract_geometry_for_viewer, generate_viewer_html
import os

# 1. Convert PAA textures to PNG
convert_paa_to_png('base_co.paa', 'base_co.png', verbose=True)

# 2. Parse RVMAT files
rvmat_data = {}
for f in ['housing.rvmat', 'button.rvmat', 'led_off.rvmat']:
    rvmat_data[os.path.splitext(f)[0]] = parse_rvmat(f)

# 3. Extract geometry with materials + textures baked in
texture_map = {'base_co': 'base_co.png'}  # stem -> png_path
geo = extract_geometry_for_viewer('model.p3d', texture_map=texture_map, rvmat_data=rvmat_data)

# 4. Generate embedded viewer (works in Claude chat)
generate_viewer_html(
    model_name='LFPG Push Button',
    mode='embedded',
    geometry_data=geo,
    output_path='viewer.html',
)
```

## Pipeline Script (Alternative)

For CLI or batch processing, `build-viewer` orchestrates everything:

```bash
python -m dayz_3d_viewer build-viewer model.p3d --textures ./textures --rvmats ./materials --name "My Model" --mode embedded -v
```

The pipeline auto-discovers assets: reads P3D → finds referenced texture/material paths →
searches provided directories → converts PAA → parses RVMAT → builds viewer.

## PAA Format Support

| Type | Code | Compression | Status |
|------|------|-------------|--------|
| DXT1 | 0xFF01 | Raw or LZO | ✅ Tested with real files |
| DXT5 | 0xFF05 | Raw or LZO | ✅ Full |
| DXT3 | 0xFF03 | Raw or LZO | ✅ Full |
| RGBA 4:4:4:4 | 0x4444 | LZSS | ✅ Full |
| RGBA 5:5:5:1 | 0x1555 | LZSS | ✅ Full |
| LuminanceAlpha | 0x8080 | LZSS | ✅ Full |
| RGBA 8:8:8:8 | 0x8888 | LZSS | ✅ Full |
| Index Palette | 0x4747 | LZSS/RLE | ❌ Not yet (very rare) |

### PAA Internals

- File starts with 2-byte type magic, then optional GGAT tags (OFFS, AVGC, MAXC, FLAG, SWIZ)
- Mipmaps stored largest-first, each with 2-byte width + 2-byte height + 3-byte data size
- DXT data passed to Pillow's DDS decoder via synthetic DDS header
- LZO flag: top bit of width field set → `python-lzo` decompression before DDS decode
- Non-DXT formats use BI's LZSS variant (ring buffer 4096, init 0x20)
- End of mipmaps: 6 zero bytes

The `SWIZ` tag is stored and not applied. Proxy triangles export as visible
geometry. Resolution 1100 (ViewPilot) is classified as `shadow`, not as a
view-pilot kind. Details: `tools/dayz-3d-viewer/KNOWN-ISSUES.md`.

## P3D Format Support

| Format | Support | Notes |
|--------|---------|-------|
| MLOD (unbinarized) | ✅ Full | Via py3d (KoffeinFlummi). Your generated models are MLOD. |
| ODOL (binarized) | ✅ via sibling skill | Vanilla game .p3d files. ODOL input → pre-process with the sibling skill `dayz-p3d-debinarizer` (ODOL→MLOD), then run the normal pipeline. |

## RVMAT Material Mapping

The RVMAT parser extracts and maps to PBR:
- `diffuse[]` → base color (fallback when no texture)
- `forcedDiffuse[]` → overrides diffuse if non-zero (used for LED tinting)
- `specular[]` → metallic factor (avg * 2, clamped)
- `specularPower` → roughness (1 - power/100)
- `emmisive[]` → emissive color + intensity (BI values like `{0,40,0}` normalized to 0-1)
- Texture stages: Stage1=normal `_nohq`, Stage3=specular `_smdi` (parsed but only `_co` applied in viewer)

## Known Gotchas (Fixed)

1. **Backslash paths on Linux**: P3D stores texture paths with Windows backslashes (`lfpg_button\data\textures\base_co.paa`). `os.path.basename()` on Linux doesn't split these. Fix: always normalize with `.replace('\\', '/')` before `os.path.basename()`.

2. **GLTFLoader in sandbox**: Claude's artifact iframe blocks `fetch()` and `Request.clone()`. GLB loading via `loader.load()` or even `loader.parse()` fails because the loader internally resolves buffer/image URIs via fetch. Fix: bypass GLTFLoader entirely for embedded mode, build geometry from raw typed arrays.

3. **PyPI py3d collision**: `pip install py3d` installs a point cloud visualization library, NOT the DayZ P3D library. Install the pack fork (`pip install -e tools/py3d`) and assert `py3d.IS_DAYZ_FORK`.

4. **LZO on DXT mipmaps**: Arma2+ PAA files compress large mipmaps (256+) with LZO. Indicated by top bit of width field. Requires `python-lzo` or `lzokay` plus `python -m dayz_3d_viewer install-lzo-shim`.

## Viewer Features

- Orbit controls (LMB rotate, RMB pan, scroll zoom)
- Wireframe overlay toggle
- Grid toggle
- Auto-rotate toggle
- Background color cycling (5 presets)
- Camera reset
- Model stats HUD (vertices, triangles, materials)
- ACES filmic tone mapping
- 4-light setup (key, fill, rim, ambient)
- Responsive sizing
- PBR materials with metallic/roughness from RVMAT
- Emissive materials for LEDs

## Limitations & Future Work

- **ODOL input**: pre-process with the sibling skill `dayz-p3d-debinarizer` (ODOL→MLOD), then run the normal pipeline. (The previously documented `cfgconvert -txt` workaround was wrong — CfgConvert converts config.bin↔cpp, not `.p3d`.)
- **Normal maps**: Parsed from RVMAT but not yet applied in Three.js viewer.
- **PNG → PAA encoding**: Not implemented. Would need DXT compression + PAA header assembly.
- **Multiple LOD viewer**: Currently shows only best visual LOD. Could add LOD switcher.

### States, Animations & LEDs (Phase 3 — Planned)

Full implementation plan in `references/states-animations-leds.md`. Summary:

**What it enables:** Interactive viewers with animated buttons/levers/doors/knobs,
LED state toggles (off/green/red), and material swaps — matching in-game behavior.

**Data sources needed per model:**
- `.p3d` — selections (vertex groups) + Memory LOD axes
- `model.cfg` → `CfgModels` class → `sections[]` + `Animations{}` (type, axis, offset/angle)
- `config.cpp` → `CfgVehicles` class → `hiddenSelections[]` + alternative materials

**Implementation phases:**
- Phase A: `config_parser.py` + `modelcfg_parser.py` (parse BI config format)
- Phase B: Extend geometry extraction with per-selection vertex groups + axis data
- Phase C: Material preset system (auto-detect LED alternatives by filename pattern)
- Phase D: Viewer UI (animation sliders + state toggle buttons + PointLights for LEDs)
- Phase E: Web mode sidecar JSON for animation data

**Key insight:** P3D selections overlap — a face can be in both an animation group AND
a material-swap group (e.g., LED moves with button AND changes color independently).
The viewer must build a THREE.Group hierarchy where swappable meshes are children of
animated groups.


## Fit editor + flat-color materials (added 2026-05-23)

### Interactive "fit editor" mode for Memory-LOD points (SP-006)
Beyond the inspection viewer, a reusable "fit editor" places Memory-LOD points that are NOT
tunable in-game (crewDriver, pos_driver/_dir, animation axes, cameras) — baked points cost a
rebuild per tweak, so dial them in OFFLINE first (R5). Pattern: a Three.js viewer that loads
the LOD0 of the .p3d(s) with geometry embedded as base64 (no fetch), plus articulated
mannequin(s) at scale (pelvis-origin local pose) driven by sliders (X/Y/Z/yaw), fixed
reference markers (handlebar grips, get-in points), and a live copyable coord readout. Supports
multiple occupants (driver+codriver, distinct colors) to fit without overlap. The real seated
pose comes from the animation; the mannequin is a geometric reference. Reference impl:
build_viewer3.py (p3d → per-material groups + base64 loader) + build_viewer4.py
(buildRider(root,mat), sliders, readout). No-browser verify (when Chromium will not fit on
disk): parse the embedded JSON payload + `node --check` the inline script.

### Flat-color models: per-material .rvmat, NOT a UV-atlas bake (LL-021)
For monochrome / flat-color-per-piece models (no real texture detail), generate one .rvmat per
material with `diffuse[]` = base color (from the .mtl) and `texture=""`; zero UV, zero gaps. A
UV-atlas bake of many flat materials produces black holes / circles / smudges (tiny islands
over a black background; any UV drift samples the background). Atlas baking is for models with
real texture detail.

## (added 2026-06-05) Self-test de un visor HTML con el preview MCP (sin Puppeteer/disco) (SP-024)

Para self-testear un visor Three.js sin Puppeteer (Chromium llena el disco del sandbox):
servir el HTML con un `http.server` estático + el **preview MCP**: `preview_start`, luego
`preview_eval` para estado/DATA/THREE, `preview_console_logs` level=error, `preview_screenshot`.
Verifica render + consola limpia + estado sin descargar Chromium. Caveat: el screenshot puede
flakear (timeout) con el loop rAF -> el `preview_eval` del estado es la verificacion robusta.
Origen: SP-024, LFQuad wheel-well tuner 2026-06-01. Cross-ref `cowork-entorno-y-tooling-gotchas`.
