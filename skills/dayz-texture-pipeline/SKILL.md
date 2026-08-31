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
   **Packing `[MECHANISM VERIFIED]` (vanilla `hatchback_02`/`sedan_02` `_nohq` mip 128 raw, 2026-08-30; same layout on two LFQuad2 maps the same night):** shipped `_nohq` is DXT5nm, not RGB-in-DXT5. Stored `(R,G,B,A)=(0,Y,Z,X)` with `TAGG SWIZ 05 04 02 03`; **X lives in alpha**. `ImageToPAA` with a `_nohq` filename deswizzles to RGB `(X,Y,Z)`. Measure amplitude/relief on that PNG, never on the raw DXT block. Do not infer packing from the suffix: read the current file **and** a vanilla `_nohq`.
   **Sign if height comes from albedo luminance:** dark pixels are valleys. A dark seam that comes out as a ridge is an inverted mold. Confirm with a 1D sweep across a known dark line (entering a horizontal groove: R>128; leaving: R<128; use G for a vertical sweep). Recalibrate Sobel gain per atlas — copying a strength that worked at another resolution or contrast overshoots. An exaggerated normal looks worse than a weak one. Detail: `references/map-conventions.md`.
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

### Material and atlas preflight (added 2026-08-31)

Before workflow step 2 borrows any vanilla `.rvmat`, run **Ambient-shadow maps and borrowed RVMATs**
below: measure `_as` per channel and verify Stage4, Stage5, and every `uvSource`. Before changing UV
orientation or winding, run **Atlas identity before mapping diagnosis**: decode the selected atlas
and overlay the affected faces first.

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
- **LL-368** — Mapas de DATOS (normal, AO, curvatura, displacement, ID, máscaras): `colorspace_settings.name = 'Non-Color'`, vista `Standard` / look `None` / exposure 0 / gamma 1, y después releer el fichero escrito contra el búfer pretendido (error máx. dentro del paso de cuantización). Sin ese round-trip el defecto se entrega.

## Ambient-shadow maps and borrowed RVMATs (added 2026-08-31)

Audit `_as` files **per channel, never as grayscale**. In the measured vanilla
`pile_of_planks_as.paa`, the AO signal is in G (min 0, mean 53.1; 74% of pixels below 48) while
R, B, and A are constant 255. A luminance conversion reports a bright image around 185 and hides the
very shadows the shader consumes.

Borrowing a vanilla `.rvmat` also borrows mesh-specific baked data. Its Stage4 `_as` can paint dark
patches from the donor mesh onto a custom model and look like broken lighting or normals; Stage5
`_smdi` carries the same reuse risk. Check the coordinate source too: the measured Stage4 uses
`uvSource="tex1"`, a second UV set that many custom MLODs do not have. Measuring the map over the
model's UV0 window does not prove what the shader samples. Engine behavior when UV1 is absent remains
unverified.

To remove donor AO, use the vanilla-proven neutral stage:

```cpp
texture="#(argb,8,8,3)color(1,1,1,1,AS)";
```

The source census found that form 4,262 times. If depth is wanted, bake an `_as` for the actual mesh
and route it through `uvSource="tex"`. An offline renderer that omits Stage4 is structurally unable
to detect this defect. Before trusting a visual bench, prove that the known-bad material makes it
red. The adjudicating control was an in-game, one-variable A/B: donor `_as`, neutral `_as`, and
self-shadow disabled.

## Atlas identity before mapping diagnosis (added 2026-08-31)

Before blaming mirrored UVs, winding, or the V convention:

1. Decode the atlas to PNG and **look at it**. Pillow opens DXT1/DXT5 DDS inputs directly.
2. Overlay the affected faces' UV polygons on that image with `image_y = (1 - v) * H`.
3. Only then investigate mapping conventions or geometry.

This two-minute preflight catches the expensive case where the selected atlas belongs to a different
asset. It also prevents a source-game material resolver from inventing color data: materials named
`*_[PRIMARY]` or `*_[SECONDARY]` intentionally have no diffuse atlas because their color comes from
the source game's paint palette. Use a flat paint texture or author a `_co`; never bind “the largest
atlas available”. Aircraft atlases can also contain a pre-mirrored copy of one side so markings read
correctly on both sides. Mirrored text on both sides does not by itself justify a global U flip.


## `healthLevels[]` es un writer NATIVO de material sobre prendas (added 2026-08-31)

Medido con cliente real el 2026-08-31. Importa a cualquier mod que pinte ropa: vista térmica,
camuflaje dinámico, marcado de equipo, resaltado de objetivos.

**El hecho.** `DamageSystem.GlobalHealth.Health.healthLevels[]` mapea umbrales de salud a rvmat —
en `DZ\characters\tops\config.cpp:2276-2333`, `1.0`/`0.7` → `tshirt.rvmat`, `0.5`/`0.3` →
`tshirt_damage.rvmat`, `0` → `tshirt_destruct.rvmat`. **Lo aplica el motor**: `GetHealthLevel` es
`proto native` (`P:/scripts/3_game/entities/object.c:1167`) y **ningún script de `P:/scripts` lee
`healthLevels` para llamar a `SetObjectMaterial`**. Un audit estático de los scripts vanilla con
cero hits NO descarta este writer, porque no está en los scripts.

**Consecuencia**: cruzar un umbral de salud **borra cualquier override de material** en el
fotograma siguiente. No hay hook que interceptarlo.

**La humedad, en cambio, NO repinta prendas.** Cruzados los cuatro umbrales `EWetnessLevel`
(`P:/scripts/3_game/constants.c:875-878`), el override sigue intacto. En vanilla el único swap de
material por humedad está en `GardenBase` (`P:/scripts/4_world/entities/gardenbase.c:605,610`) y es
**de script**. Bajo `DZ\characters\` hay **0** assets `*wet*` frente a 349 `*damage*.rvmat` con la
misma búsqueda: la ausencia está controlada, no supuesta.

## `SetObjectMaterial` sobre prenda vestida se RE-AFIRMA, no se llama una vez (added 2026-08-31)

> **PARCIALMENTE CONTESTADA la misma tarde — lee antes «Escribir MÁS no hace que el material
> prenda» más abajo.** Los datos de esta tabla se mantienen, pero la causa que sugieren (la
> frecuencia) es falsa: 6648 escrituras continuas sobre una prenda sin cambios de nivel de salud
> no renderizan nada. Aplicar solo la receta de esta sección hace perder corridas.

Medido en la misma corrida, y es la parte accionable:

| escrituras | resultado |
|---|---|
| 1, justo después de un cambio de nivel de salud | **renderiza** — ⚠ no reproducido: ver la sección contestataria |
| 1, ~50 s después del último cambio de estado | **no renderiza** — y la llamada se hizo, con índices válidos |
| ~19/s sostenidas | renderiza a niveles de salud 0, 2 y 4, estable y sin parpadeo |
| se deja de escribir | **se queda** puesto |

**El mecanismo NO está establecido.** «La escritura queda latente hasta que el motor reconstruye el
visual» encaja con las cuatro observaciones y no está probado.

**Cómo aplicarlo**: re-afirmar el override al activar el efecto y tras cada evento que repinte la
prenda (cambio de nivel de salud, cambio de equipamiento), o mantenerlo por tick mientras el efecto
esté activo. **No** llamarlo una vez y darlo por puesto.

Y dejar fuera del lease la selección `personality`: ahí ya escribe vanilla
(`P:/scripts/4_world/entities/itembase/clothing_base.c:154`), y pisarla convierte un repintado
normal en un falso positivo de «me lo han robado».

### Cómo se midió, por si hay que repetirlo

Override con `dz\data\data\mirror.rvmat` (negro especular, `PixelShaderID="Super"`, diffuse 0.097 /
specular 2) sobre las selecciones camo: es binario a simple vista y quita el juicio sobre el JPEG.
**El PASS no lo da el fotograma donde el override sigue: lo da el par** — un escalón de salud borra
el mismo override, mismo entity y misma cámara. Sin ese control, «sigue ahí» es indistinguible de
un instrumento ciego.

## Escribir MÁS no hace que el material prenda: hace falta reconstruir el visual (added 2026-08-31, tarde)

Corrección medida de las dos secciones anteriores. Aquella tabla describe bien lo que se vio, pero
sugiere una causa equivocada —la frecuencia—, y el siguiente proyecto que la lea intentará escribir
más rápido. No funciona, y cuesta dos corridas averiguarlo.

**El negativo diseñado.** Sobre una prenda NUEVA en cada brazo (reset por `CreateAttachment`, para
que ningún render anterior contamine el siguiente: el override, una vez prende, es pegajoso) y sin
un solo cambio de nivel de salud:

| tratamiento | escrituras | render |
|---|---|---|
| ninguna (control −) | 0 | vanilla |
| ráfaga 0,1 s | ~6 | vanilla |
| ráfaga 5 s | 291 | vanilla |
| continuo 43 s | 2478 | vanilla |
| continuo 128 s + cruce de umbral de humedad inyectado | 6648 | vanilla |

Las ráfagas intermedias (0,5 / 1 / 2 s) no necesitan fotograma: son subconjuntos estrictos del
patrón continuo sobre sujetos idénticos, así que el fallo del tratamiento máximo las cubre por
monotonía.

**El reset por prenda nueva no es comodidad, es NECESARIO, y si lo saltas el barrido mide su propia
historia.** El override es pegajoso: una vez prende sobrevive ≥97 s sin una sola escritura y a
través de un escalón de salud. Sin sujeto virgen, cada brazo arranca contaminado por el anterior —
en la corrida previa el control positivo estaba en mitad del calendario y envenenó todos los brazos
posteriores. Y la persistencia entre corridas muerde igual: un baseline puede llegar con
`wetlevel=4 hplevel=2` de la sesión anterior y hacer pasar por «el control no dispara» lo que en
realidad es un sujeto sucio. Normaliza el sujeto al empezar y compruébalo en el log, no de palabra.

**Lo que sí lo hace prender** es que esté ocurriendo un cruce de umbral de salud: la misma escritura
continua, en una corrida donde el servidor escalonaba la salud, sí renderizó. O sea que el
`healthLevels[]` de la sección anterior no es solo lo que BORRA el override — es lo único que se ha
visto INSTALARLO.

**La humedad no vale como disparador, y se probó a propósito**: con el escritor continuo en marcha
se inyectó lluvia y se cruzó `wetlevel` 0→1. El motor repintó de verdad —los pantalones cambian
visiblemente al mojarse— y la prenda siguió sin tomar el override. Coherente con la sección
anterior, y descarta el candidato obvio.

**Consecuencia de diseño**: no se puede pintar una prenda vestida A DEMANDA escribiendo material. Si
el efecto tiene que aparecer cuando el jugador lo activa, hay que forzar la reconstrucción por otra
vía.

**`SwitchItemSelectionTextureEx` NO es esa vía, y aquí estuvo publicada unas horas como si lo
fuera.** Es una **declaración sin cuerpo** (`P:/scripts/3_game/entities/entityai.c:1170`): hook de
script, no `proto native`, así que llamarla no reconstruye nada — solo corre los overrides que
existan, y el de `Clothing_Base` sale por `return` temprano si `par` es null. Lo que engaña es
quién la llama: vanilla la invoca desde `EEItemAttached`
(`P:/scripts/4_world/entities/manbase/playerbase.c:1469-1471`), o sea que **la reconstrucción es el
attach** y ella va de pasajera. Queda escrita como descartada **con el motivo**, no como pendiente:
un pendiente lo hereda alguien dentro de un mes y se gasta la tarde en él.

**El candidato vivo es `SetSimpleHiddenSelectionState`**
(`P:/scripts/3_game/entities/entityai.c:2892`): `proto native` de verdad, y toca la visibilidad de
**la misma selección** que lleva el override, así que apagarla y encenderla podría forzar al motor a
re-evaluarla. Es además el único que queda: un barrido de `proto native` sobre `entityai.c` y
`object.c` devuelve solo `SetObjectTexture`, `SetObjectMaterial` y ese. **No existe ningún
`UpdateVisuals`** — si buscas una llamada de refresco genérica, no la hay, y eso ahorra la búsqueda.

Al medirlo, separa dos fallos que dan el mismo fotograma vanilla: «no hubo refresco» y «hubo
refresco y el apagado se llevó el override por delante». Se distinguen re-estampando después del
ciclo y leyendo el getter en los tres momentos — para esa pregunta el getter **sí** sirve, porque
testigo del slot y oráculo del render son cosas distintas y solo lo segundo está desacreditado.

**Y contesta la fila «1, justo después de un cambio de nivel de salud → renderiza»** de la tabla
anterior: hoy, una escritura en el primer tick tras el cambio observado NO renderizó, con fotograma
y con el log confirmando que la escritura se hizo con índices válidos. Las dos observaciones son de
una muestra y se dejan las dos escritas. Lo que no depende del tamaño de muestra es el negativo de
6648 escrituras.

**El hook que parece la solución y no lo es**: `EEHealthLevelChanged` SÍ corre en cliente (medido;
el cuerpo vanilla de `clothing_base.c:111-125` está guardado por `!IsDedicatedServer` y solo hace
trabajo de cliente), pero **el motor escribe DESPUÉS del hook** — dentro del hook la lectura ya
devuelve tu material, y al tick siguiente está vacía. Re-afirmar ahí dentro está perdido por orden.

## `GetObjectMaterial` NO es oráculo de lo que se renderiza (added 2026-08-31, tarde)

Falsado en las DOS direcciones dentro de una misma corrida. Es la trampa más cara de esta skill,
porque convierte el log en evidencia falsa y en verde:

| lo que devuelve el getter | lo que muestra el fotograma |
|---|---|
| `dz\data\data\mirror.rvmat` | camiseta vanilla negra — dice que tu override está puesto, y no se ve |
| cadena vacía | camiseta con el material espejo — dice que no está, y se ve |

**Regla**: para acreditar que un material se aplicó, el instrumento es el fotograma.
`GetObjectMaterial` solo informa del slot de script, que es una cosa distinta del render. Un gate
que lea el getter puede firmar PASS sobre una prenda que se ve vanilla, y FAIL sobre una que se ve
pintada.

**Alcance, para que esto no se propague de más**: lo que queda invalidado es el GETTER como
instrumento, **no** los veredictos que se apoyaron en píxeles. El PASS de G10 de LFThermalCore no
usó ningún getter — se apoyó en ocho fotogramas con un rvmat binario a simple vista y en un par
control (misma entidad, misma cámara: la humedad deja el override, un escalón de salud lo borra), y
sigue en pie. La regla completa es **el getter no sirve de oráculo y los píxeles sí**, que es el
instrumento que han usado las dos corridas.

Dos hechos menores del mismo getter, útiles para leer un log: devuelve **cadena vacía** cuando el
motor tiene el material (no una ruta vanilla normalizada, que era lo que cabía esperar), y en
**servidor devuelve vacío siempre** — el material de prenda es puramente de cliente.
