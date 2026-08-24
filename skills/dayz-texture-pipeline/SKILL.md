---
name: dayz-texture-pipeline
description: Use when working with DayZ textures, .paa files, .rvmat materials, _co/_nohq/_smdi/_as/_mc/_dt maps, hiddenSelectionsTextures, hiddenSelectionsMaterials, material swaps, damage/destruct materials, emissive lights, glass, penetration materials, Multi shader masks, uvTransform, TexView/ImageToPAA, Blender/Substance texture export, or native PBR materials (MatPBR shader, .emat files, metallic/roughness/albedo maps) for DayZ.
---

# DayZ Texture Pipeline

Use this skill to design, edit, validate, and package DayZ texture/material work. It covers visual texture maps, `.paa` conversion, `.rvmat` authoring, config material wiring, damage materials, emissive/glass variants, penetration materials, and advanced Multi shader masks.

## Non-negotiable rules

1. Verify every DayZ path, config property, and material pattern against the current mod or unpacked vanilla data before writing a final answer or diff.
2. Prefer the lowest-risk material route that meets the goal:
   - texture-only skin: `hiddenSelectionsTextures[]` / `_co.paa`;
   - changed roughness/specular/normal/emissive behavior: `.rvmat`;
   - health visual states: damage/destruct `.rvmat` through `healthLevels[]`;
   - bullet/surface response: collision LOD penetration `.rvmat` with `.bisurf`;
   - many tiled materials on one static mesh: Multi shader only after section count and UV requirements justify it;
   - source is an authored metallic/roughness PBR set and damage-overlay/terrain support is not needed: MatPBR `.emat` route — community-verified, not Bohemia-documented; prefer Super/`.rvmat` when either is required.
3. Treat `_nohq` as DirectX/Y- for DayZ. If the source normal is OpenGL/Y+, invert the green channel before final DayZ export.
4. Copy the closest vanilla `.rvmat` category first. Do not invent absolute stage constants when vanilla examples diverge by asset class.
5. Mark templates as `[DESIGN]` until adapted to the real addon paths, selections, UV sets, and verified vanilla reference.
6. **UI textures (loading screens, menu backgrounds, map images): NEVER change the tone curve on the strength of an offline model — the engine's transfer function must be MEASURED from a screenshot first** (added 2026-08-21, rewritten same day after the first version shipped a regression).
   - **What is measured**: a mod running in production carried a full `sRGB→linear` decode on its source. An offline model built from a vault note ("1.29 washes UI by +35% luma, contrast 76→58", Bohemia T198202) said this was a ~4x overshoot, so it was replaced with a gentle photographic curve. **In-game the result was much brighter than before** — the user's report, the only real datum in the whole exercise. Working backwards, `linear→sRGB` on the old texture predicts a render of 132.31 against a source median of 132.51: an exact cancellation. So the engine plausibly treats the UI `.paa` as LINEAR data and encodes it for display, making `sRGB→linear` on the source the correct inverse and the note's "+35%" model wrong or measured on something else.
   - **Status: HYPOTHESIS.** It fits one qualitative report and arithmetic, not a measurement. Do not act on it either. Get a screenshot of the actual UI texture on screen, compare it pixel-wise against the known texture that produced it, and derive the real curve. One screenshot ends the guessing permanently.
   - **Second-order trap worth knowing**: storing linear data in an 8-bit DXT1 texture starves the shadows, and the engine's gamma expansion then amplifies exactly that quantization. Measured on the production mod: raw DXT1 error averaged 2.64/255, but in DISPLAY space it hit mean 7.46 / max 77 in the darkest 18% of the image — blotchy, banded shadows that read as "the picture looks a bit off" while the overall tone is perfect. If the linear-storage route is correct, the fix for that is precision (uncompressed/higher-bit PAA, or dithering before encode), NOT a tone change.
   - **Gate**: decode the shipped `.paa` back and compare its luma median against the source — a build script that "ran fine" proves nothing about the curve it applied. And an offline round-trip never predicts the render: look at it in-game before believing any of this.
   - **Power-of-two is an `ImageToPAA.exe` limit, not an engine limit.** The tool rejects 2048×1152 and 1920×1080 with `Error (Img is not of power of 2 size)`, yet non-POT `.paa` load fine at runtime (the loading-screen mask that ships in these mods is 1920×1080). Consequence: forcing a 16:9 source into 2048×1024 costs ~12.5% vertical stretch — budget a crop or another encoder before promising 16:9.

7. **For a UI texture (loading screens, menu backgrounds, map images): use a `.paa` from `ImageToPAA.exe`; do not ship a hand-written `.edds`.**
   - **What failed**: a Python-written `.edds` did not render — not self-contained LZ4, not a structural clone of a production file with the same tags, not `COPY`. `LoadImageFile` returned `true` in every case, so the log does not catch it. A Python round-trip `max_diff=0` does not predict the render; look at it in-game.
   - **What worked**: a `.paa` from DayZ Tools `ImageToPAA.exe`, referenced from script. First try. ~1 MB vs ~14 MB. 2048×1024 accepted; 1536×1024 rejected as not power-of-two.
   - **Decoder is for INSPECTING a foreign `.edds`, not for writing one.** Six production files decoded with `max_diff=0` on mip 0 vs their source PNG. Runtime layout: 128-byte DDS header (loading-screen backgrounds were BGRA8 uncompressed: `pf.flags 0x41`, R=`0x00FF0000`, A=`0xFF000000`; mips = floor(log2(max(w,h)))+1); from offset 128, 8 bytes per mip = `tag`(4) + uint32 size, tag `'COPY'` (raw) or `'LZ4 '`, smallest mip first, then payloads in the same order. DayZ Tools has no CLI writer; production files come from Workbench PNG import (the `.meta` records it).
   - **LZ4 slices are linked blocks.** A `'LZ4 '` payload is `uint32` uncompressed mip size, then 65536-byte slices each prefixed by compressed size with `OR 0x80000000` on the last. Slice 0 decompresses alone; later slices fail with "corrupt input or insufficient space" unless the previous slice is passed as dictionary (`lz4.block.decompress(data, uncompressed_size=n, dict=prev)`). That error reads as a size bug and is not.

## Workflow

1. Identify the asset type, selections, UV sets, and intended runtime behavior.
2. Read the nearest existing `.rvmat`, `config.cpp`, and texture paths from the mod or `P:\DZ`.
3. Pick the route:
   - simple color/skin: use `references/config-and-damage.md`;
   - new material response: use `references/rvmat-cookbook.md`;
   - damage/destruct: use `references/config-and-damage.md`;
   - glass, emissive, or penetration: use `references/rvmat-cookbook.md`;
   - Multi material masks: use `references/multi-rvmat-section-texturing.md`;
   - native PBR source (Substance/Quixel/AI-generated metallic-roughness sets), no damage overlay or terrain needed: use `references/matpbr-emat-pipeline.md`.
4. Export textures using the map conventions in `references/map-conventions.md`.
5. Validate with `references/validation-checklist.md` and, where useful, run:

```powershell
python .\scripts\rvmat_lint.py path\to\material.rvmat --pdrive-root P:\
```

6. If creating a new material from a template, start with:

```powershell
python .\scripts\rvmat_template.py super --prefix "myaddon\data\asset" --output "myaddon\data\asset.rvmat"
```

Then replace every placeholder with verified real paths.

## Reference loading guide

- `references/map-conventions.md`: texture suffixes, normal map orientation, SMDI packing, export notes.
- `references/rvmat-cookbook.md`: Super, flat, emissive, glass, penetration, and common stage patterns.
- `references/config-and-damage.md`: `hiddenSelectionsTextures[]`, `hiddenSelectionsMaterials[]`, `healthLevels[]`, vehicle light material swaps.
- `references/multi-rvmat-section-texturing.md`: enriched Multi shader reference with RGB+black mask mapping and UV requirements.
- `references/validation-checklist.md`: review gates before packaging or handing off.
- `references/vehicle-materials-and-color-variants.md`: shader choice (Super when faces have a _co vs NormalMapSpecularMap for constant-color/no-_co parts), tiled detail for overlapping/un-baked UVs, _nohq DirectX Y- orientation, and the color-variant subclass pattern (`color` hidden selection).
- `references/matpbr-emat-pipeline.md`: native PBR route via the MatPBR shader — `.emat`/`.rvmat` pairing, required albedo/normal/roughness/metallic/AO maps, env cubemap prep, Workbench import steps, glass presets, and hard limitations (no damage overlay, no terrain). Community-verified, not officially documented — read the Evidence section before treating any claim as settled.

## Stop and ask

Ask for clarification before generating final files when any of these are unknown:

- target addon root and packed path;
- exact selections that will receive texture/material swaps;
- whether the asset has one or two UV sets;
- whether the texture is only cosmetic or must affect surface, damage, glass, light, or penetration behavior;
- whether the output should be a mod diff, standalone reference, or `.skill` package.


## Checklist normal bake high→low (added 2026-06-24)

Patrón empírico verificado en LFInfectedBig S5 (5 iteraciones × 4 gotchas distintos). Cualquier bake high→low destinado a DayZ debe pasar esta checklist antes de la primera pasada, no iterar contra ella.

### Pre-bake (geometría)

- [ ] **Triangular `low` ANTES del bake**. Si no, las tangentes del bake (calculadas sobre quads) ≠ tangentes que el engine usa al renderizar (que son sobre triángulos) → normales desalineadas en runtime.
- [ ] **`bbox_dims(low_source) == bbox_dims(high_source)`** (±1 mm). Si difieren (típico tras re-pose / conform del low), bakear en una **pose donde coincidan** (BakeProxy = topo+UV del low final con posiciones del low pre-conform o pre-rig). Tangent-space normal map es invariante a la pose con misma topo+UV. Detalle: LL-159 en `lessons-learned.md`.
- [ ] **`high` visible, TODO lo demás OCULTO** en la escena (otras pasadas, ChestBones internos, proxys). Si no, AO y normal recogen oclusión/superficies que no tocan.
- [ ] **`low`**: `customdata_custom_splitnormals_clear` + `normals_make_consistent(inside=False)` + `shade_smooth`. Sin esto, las normales heredadas de retopo/voxel-remesh quedan inconsistentes → AO oscuro arbitrario.
- [ ] **`high`**: NO `normals_make_consistent`. En mallas no-watertight (AI generadas tipo Rodin/Hunyuan, retopo voxel) voltea shells enteros hacia dentro. Usar las normales **originales** del high + `shade_smooth`. Vienen consistentes para render por construcción.

### Pre-bake (imagen target)

- [ ] **Pre-rellenar la imagen target con el neutro del mapa**:
  - Normal map (tangent-space): RGB = `(128, 128, 255)` = vector `(0, 0, 1)` decodificado.
  - AO map: blanco `(255, 255, 255)` o gris `(192, 192, 192)` según convención.
- [ ] **`use_clear=False`** en los bake settings. Si no, los misses del bake quedan en negro `(0, 0, 0)` → el Normal Map node los decodifica como normal `(−1, −1, 0)` (hacia dentro) → renderiza negro bajo cualquier luz.
- [ ] Tamaño imagen acorde al texel target del mod (1024/2048/4096; 2048 para personajes humanoides DayZ es estándar).

### Bake settings

- [ ] **Cage 0.025 m / max_ray 0.05 m** como default para humanoides. Subir si la malla es gruesa (ChestBones internos al torso, vehículos con paneles separados). Bajar si hay autointersecciones del low (raras).
- [ ] Bake en **OGL/Blender** (default). Conversión a DirectX para DayZ (Y−) al final con PIL/ImageMagick.
- [ ] `samples` ≥ 16 para AO; 1 para normal (el normal no se beneficia de samples).

### Post-bake (formato DayZ)

- [ ] `_nohq` = normal con **canal verde invertido** (Y−, DirectX convention). Conversión:
  ```python
  from PIL import Image
  im = Image.open("normal_ogl.png").convert("RGB")
  r, g, b = im.split()
  g = g.point(lambda v: 255 - v)
  Image.merge("RGB", (r, g, b)).save("zombie_body_nohq.png")
  ```
- [ ] `_co` = albedo PBR; si solo hay placeholder del generador (Rodin/Hunyuan), tratarlo como tal y re-texturar sobre la UV nueva.
- [ ] `_smdi` = specular/diffuse mask si aplica al material DayZ.
- [ ] `.paa` final con TexView / ImageToPAA.

### Verificación rápida (renders de evidencia)

Antes de empaquetar, render comparativo 3 vistas:

- `pv_A_normal_*` = low + normal map aplicado.
- `pv_B_flat_*` = low plano (sin normal).
- `pv_C_high_*` = high original.

Pasa si `pv_A` está claramente más cerca de `pv_C` que de `pv_B` (el normal añade el detalle del high). Falla si hay manchas, arcoíris localizados, o el normal "no se ve" (transform incorrecto).

### Origen y cross-refs

LFInfectedBig S5 (autónoma) 2026-06-24, handoff `30_Sessions/2026-06-25-LFInfectedBig-uv-bake.md`. Gotchas individuales en LL-159 (BakeProxy en pose pre-conform). Reportado en CB-5 de la introspección 2026-06-24.

## Reglas promovidas del corpus de lecciones (added 2026-07-27)

Promovidas desde `AI/20_Knowledge/lessons-learned.md` para que lleguen por trigger en vez
de depender de que alguien recuerde buscarlas. Cada regla cita su `LL-NNN` de origen;
la entrada completa vive allí. No quites la cita: el índice detecta la promoción por ella.

- **LL-066** — En Blender 5.1 usa `RENDERED` + EEVEE + luz para materiales y captura el área `VIEW_3D`, no la ventana completa. Para Multi, conserva UV2/`tex1` y reproduce el blend por máscara; en Windows sin `python-lzo`, decodifica `.paa` con `lzokay` y el shim del viewer.
