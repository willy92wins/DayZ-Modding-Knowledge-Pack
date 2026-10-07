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
   **Measure a candidate for the source's convention, then confirm it; do not guess it from where the asset came from** (added 2026-10-03). `python scripts/normal_convention.py --normal <normal.png> --albedo <albedo.png>` takes two independent readings and proposes a convention only when they agree. The albedo reading looks at the albedo's dark grooves: across a hollow, d(nx)/dx and d(ny)/dy have the same sign in DirectX and opposite signs in OpenGL, and the red channel calibrates the sign of the groove signal. The curl reading needs no albedo: the slopes of a height field have no curl, under one convention only; it names a convention only when its two median residuals differ by more than one 8-bit step of the normal (2/255), a heuristic floor: on nearly flat normals rounding to 8 bits alone moves them about that much, and more where the normal tilts. The candidate must also hold across a 6×6 grid of blocks, each block read with the same thresholds: at most 1 block in 10 of those that vote may name the other convention for the curl reading, and 1 in 3 for the albedo reading (added 2026-10-04 after a flat brick decal and a cloth bag read OpenGL on vanilla maps with readings that agreed on the whole map but not block by block). Exit 0 prints a candidate, `DirectX` or `OpenGL` (both readings agree, stable across the blocks); exit 2 is `INCONCLUSIVE` (they disagree, one has no signal, or the blocks disagree); exit 1 is bad input. Convert a `.paa` to PNG with ImageToPAA first. **A candidate is not proof**: the cross-family review (2026-10-03) built known-DirectX maps that both readings call OpenGL, a valid tangent-space bake on a sphere patch and undersampled tileable detail; the block check cannot see an error that is the same in every block, such as that tileable detail. Confirm a candidate another way before inverting the green: the baker's export setting, or a render under a raking light in which a known groove reads as a groove. **The raking light confirms only if it crosses V** (known limit, review round 3): the green changes the shading only through the light's V component, so a light parallel to U renders the map and its inverted-green copy identically, and so does a groove that runs along V under any light. Use a light from the top or the bottom of the texture on a groove that runs along U, and check that the inverted-green copy reads that groove as a ridge; two renders that look the same are inconclusive, not a confirmation (`references/map-conventions.md`). Measured on LFPowerGrid's heater, a Sketchfab asset: the albedo reading gave red −0.130, green −0.085 over 491,775 pixels (2026-09-21) and the curl reading a median residual of 0.013 under DirectX against 0.024 under OpenGL (2026-10-03), candidate **DirectX**, not confirmed another way and not checked in game. On 284 vanilla pairs not used to design the block check, it gave 157 `DirectX`, 119 `INCONCLUSIVE` and 8 `OpenGL`, all 8 consistent with OpenGL by their own features (2026-10-04). **Known limit, accepted by the Pack owner on 2026-10-04:** a map that mixes the two conventions inside every block passes the block check. Vanilla `kancel_008_nohq` (glass panes DirectX by their own edges; hinge bolts and window frames OpenGL) reads OpenGL with stable blocks. Over the three vanilla samples (848 pairs) that is 1 wrong candidate in 502, 0 in the 165 not used for the design, with no N1 error and about 41 % `INCONCLUSIVE`. Check features of known relief of more than one kind before inverting a channel. The albedo reading alone is also wrong, with strong correlations, on a flat surface that curves one way along x and the other along y; the curl reading alone has no signal on a surface that is a sum of one function of x and one of y. Inverting the green channel only flips both readings, so it is no control: the controls are the fixtures of known convention in `tests/test_normal_convention.py`. An `OpenGL` candidate only says that the green disagrees with the red: a map whose red is inverted against the real relief reads the same, and inverting its green then turns the relief upside down (two vanilla maps, 2026-10-04). Check red on a recessed joint of known relief before choosing the channel (`references/map-conventions.md`).
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

- `references/map-conventions.md`: texture suffixes, normal map orientation, SMDI packing, metallic→specular (G) conversion, export notes.
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

Empirical pattern verified on LFInfectedBig S5 (5 iterations × 4 distinct gotchas). Any high→low bake destined for DayZ must pass this checklist before the first pass, not iterate against it.

### Pre-bake (geometry)

- [ ] **Triangulate `low` BEFORE bake**. Otherwise, bake tangents (computed on quads) ≠ tangents engine uses when rendering (which are on triangles) → misaligned normals at runtime.
- [ ] **`bbox_dims(low_source) == bbox_dims(high_source)`** (±1 mm). If they differ (typical after re-pose / conform of low), bake in a **pose where they match** (BakeProxy = topo+UV of final low with positions of low pre-conform or pre-rig). Tangent-space normal map is pose-invariant with same topo+UV. Detail: LL-159 in `lessons-learned.md`.
- [ ] **`high` visible, EVERYTHING else HIDDEN** in scene (other passes, internal ChestBones, proxies). Otherwise, AO and normal collect occlusion/surfaces they shouldn't.
- [ ] **`low`**: `customdata_custom_splitnormals_clear` + `normals_make_consistent(inside=False)` + `shade_smooth`. Without this, normals inherited from retopo/voxel-remesh remain inconsistent → arbitrary dark AO.
- [ ] **`high`**: do NOT `normals_make_consistent`. On non-watertight meshes (AI-generated like Rodin/Hunyuan, voxel retopo) flips entire shells inward. Use **original** normals of high + `shade_smooth`. They come consistent for render by construction.

### Pre-bake (imagen target)

- [ ] **Pre-fill target image with neutral map value**:
  - Normal map (tangent-space): RGB = `(128, 128, 255)` = decoded vector `(0, 0, 1)`.
  - AO map: white `(255, 255, 255)` or gray `(192, 192, 192)` depending on convention.
- [ ] **`use_clear=False`** in bake settings. Otherwise, bake misses remain black `(0, 0, 0)` → Normal Map node decodes them as normal `(−1, −1, 0)` (inward) → renders black under any light.
- [ ] Image size according to mod texel target (1024/2048/4096; 2048 for DayZ humanoid characters is standard).

### Bake settings

- [ ] **Cage 0.025 m / max_ray 0.05 m** as default for humanoids. Increase if mesh is thick (internal ChestBones to torso, vehicles with separate panels). Decrease if low self-intersections (rare).
- [ ] Bake in **OGL/Blender** (default). Conversion to DirectX for DayZ (Y−) at end with PIL/ImageMagick.
- [ ] `samples` ≥ 16 for AO; 1 for normal (normal does not benefit from samples).

### Post-bake (formato DayZ)

- [ ] `_nohq` = normal with **inverted green channel** (Y−, DirectX convention). Conversion:
  ```python
  from PIL import Image
  im = Image.open("normal_ogl.png").convert("RGB")
  r, g, b = im.split()
  g = g.point(lambda v: 255 - v)
  Image.merge("RGB", (r, g, b)).save("zombie_body_nohq.png")
  ```
- [ ] `_co` = PBR albedo; if only generator placeholder exists (Rodin/Hunyuan), treat it as such and re-texture on new UV.
- [ ] `_smdi` = specular/diffuse mask if applicable to DayZ material.
- [ ] Final `.paa` with TexView / ImageToPAA.

### Quick verification (evidence renders)

Before packaging, 3-view comparative render:

- `pv_A_normal_*` = low + normal map aplicado.
- `pv_B_flat_*` = low plano (sin normal).
- `pv_C_high_*` = high original.

Passes if `pv_A` is clearly closer to `pv_C` than to `pv_B` (the normal map adds detail of the high). Fails if there are blemishes, localized rainbows, or normal "is not visible" (incorrect transform).

### Origin and cross-refs

LFInfectedBig S5 (autonomous) 2026-06-24, handoff `30_Sessions/2026-06-25-LFInfectedBig-uv-bake.md`. Individual gotchas in LL-159 (BakeProxy in pre-conform pose). Reported in CB-5 of 2026-06-24 introspection.

## Rules promoted from lessons corpus (added 2026-07-27)

Promoted from `AI/20_Knowledge/lessons-learned.md` to arrive via trigger instead
of depending on someone remembering to look them up. Each rule cites source `LL-NNN`;
complete entry lives there. Do not remove citation: the index detects promotion by it.

- **LL-066** — In Blender 5.1 use `RENDERED` + EEVEE + light for materials and capture `VIEW_3D` area, not full window. For Multi, keep UV2/`tex1` and reproduce blend by mask; on Windows without `python-lzo`, decode `.paa` with `lzokay` and viewer shim.
- **LL-368** — DATA maps (normal, AO, curvature, displacement, ID, masks): `colorspace_settings.name = 'Non-Color'`, `Standard` view / `None` look / exposure 0 / gamma 1, and then reread written file against intended buffer (max error within quantization step). Without that round-trip defect is delivered.

## Ambient-shadow maps and borrowed RVMATs (added 2026-08-31)

Audit `_as` files **per channel, never as grayscale**. In the measured vanilla
`pile_of_planks_as.paa`, the AO signal is in G (min 0, mean 53.1; 74% of pixels below 48) while
R, B, and A are constant 255. A luminance conversion reports a bright image around 185 and hides the
very shadows the shader consumes.

**`_as` encoding and gate criterion (added 2026-09-14, LFQuad3).** [EXACT] The native ImageToPAA route encodes `_as` by filename: the `*_as.*` pattern compresses DXT1 with `channelSwizzleR="1"`, `channelSwizzleG="G"`, `channelSwizzleB="1"`, `channelSwizzleA="1"` and `dynRange=0`, so the AO stays in G while R, B and A sit at 255 (confirmed decoding five vanilla vehicle `_as.paa`: civiliansedan, hatchback_02_body, sedan_02_body, truck_01_cab, offroad_02_wheel). [DESIGN] Gate a produced `_as` by decoding the PAA and requiring max G error <= 8/255 against the source, with R, B and A at 255. Never require per-channel RGB error against a gray PNG: that criterion pushed a worker to bypass the swizzle through an intermediate `_dxt1` suffix and ship gray `_as` maps (R=G=B). Keep the `_as` source name plain, with no intermediate suffixes.

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


## `healthLevels[]` is a NATIVE material writer on clothing (added 2026-08-31)

Measured with actual client on 2026-08-31. Matters to any mod painting clothing: thermal vision,
dynamic camouflage, team marking, target highlighting.

**The fact.** `DamageSystem.GlobalHealth.Health.healthLevels[]` maps health thresholds to rvmat —
in `DZ\characters\tops\config.cpp:2276-2333`, `1.0`/`0.7` → `tshirt.rvmat`, `0.5`/`0.3` →
`tshirt_damage.rvmat`, `0` → `tshirt_destruct.rvmat`. **Engine applies it**: `GetHealthLevel` is
`proto native` (`P:/scripts/3_game/entities/object.c:1167`) and **no script in `P:/scripts` reads
`healthLevels` to call `SetObjectMaterial`**. A static audit of vanilla scripts with
zero hits does NOT rule out this writer, because it is not in the scripts.

**Consequence**: crossing a health threshold **wipes out any material override** on the
following frame. There is no hook to intercept it.

**Wetness, on the other hand, does NOT repaint clothing.** Having crossed the four `EWetnessLevel`
thresholds (`P:/scripts/3_game/constants.c:875-878`), override remains intact. In vanilla sole material
swap by wetness is in `GardenBase` (`P:/scripts/4_world/entities/gardenbase.c:605,610`) and is
**script-side**. Under `DZ\characters\` there are **0** `*wet*` assets versus 349 `*damage*.rvmat` with
same search: absence is verified, not assumed.

## `SetObjectMaterial` on worn clothing is RE-ASSERTED, not called once (added 2026-08-31)

> **PARTIALLY DISPUTED same afternoon — read "Writing MORE does not make material
> stick" below first.** Data in this table holds, but the cause suggested (frequency)
> is false: 6,648 continuous writes on clothing without health level changes
> render nothing. Applying only this section's recipe wastes runs.

Measured in same run, and is the actionable part:

| writes | result |
|---|---|
| 1, right after health level change | **renders** — ⚠ not reproduced: see disputing section |
| 1, ~50 s after last state change | **does not render** — and call was made, with valid indices |
| ~19/s sustained | renders at health levels 0, 2, and 4, stable and flicker-free |
| stop writing | **remains** applied |

**Mechanism is NOT established.** "The write remains latent until engine rebuilds
visual" fits all four observations and is not proven.

**How to apply it**: re-assert override when activating effect and after every event repainting
clothing (health level change, equipment change), or maintain per tick while effect
is active. **Do not** call it once and assume it applied.

And leave `personality` selection out of lease: vanilla already writes there
(`P:/scripts/4_world/entities/itembase/clothing_base.c:154`), and stomping it turns normal
repainting into a false positive of "it was stolen from me".

### How it was measured, in case it needs repeating

Override with `dz\data\data\mirror.rvmat` (specular black, `PixelShaderID="Super"`, diffuse 0.097 /
specular 2) on camo selections: binary to the naked eye and removes judgment on JPEG.
**PASS is not given by frame where override remains: it is given by the pair** — health step clears
same override, same entity, and same camera. Without that control, "still there" is indistinguishable
from a blind instrument.

## Writing MORE does not make material stick: visual rebuild is needed (added 2026-08-31, evening)

Measured correction to the two previous sections. That table describes well what was seen, but
suggests wrong cause —frequency—, and the next project reading it will try to write
faster. Does not work, and takes two runs to find out.

**The designed negative.** On a NEW garment on each arm (reset via `CreateAttachment`, so
no previous render contaminates next: override, once it sticks, is sticky) and without
a single health level change:

| treatment | writes | render |
|---|---|---|
| none (control −) | 0 | vanilla |
| burst 0.1 s | ~6 | vanilla |
| burst 5 s | 291 | vanilla |
| continuous 43 s | 2478 | vanilla |
| continuous 128 s + injected wetness threshold crossing | 6648 | vanilla |

Intermediate bursts (0.5 / 1 / 2 s) do not need a frame: they are strict subsets of
continuous pattern on identical subjects, so failure of maximum treatment covers them by
monotonicity.

**Resetting with a new garment is not convenience, it is NECESSARY, and if you skip it the sweep measures its own
history.** Override is sticky: once it takes it survives ≥97 s without a single write and
across a health step. Without virgin subject, each arm starts contaminated by previous one —
in previous run positive control sat in middle of schedule and poisoned all subsequent
arms. And inter-run persistence bites equally: a baseline can arrive with
`wetlevel=4 hplevel=2` from previous session and make pass for "control does not fire" what in
reality is a dirty subject. Normalize subject at start and verify in log, not by word.

**What DOES make it stick** is an occurring health threshold crossing: the same continuous
write, in a run where server stepped health, did render. Meaning
`healthLevels[]` from previous section is not only what CLEARS override — it is the only thing
seen to INSTALL IT.

**Wetness does not work as a trigger, and was tested intentionally**: with continuous writer active
rain was injected and `wetlevel` crossed 0→1. Engine repainted for real —pants change
visibly when wet— and clothing still did not take override. Consistent with previous
section, and rules out obvious candidate.

**Design consequence**: worn clothing cannot be painted ON DEMAND by writing material. If
effect must appear when player activates it, reconstruction must be forced through another
route.

**`SwitchItemSelectionTextureEx` is NOT that route, and was published here for a few hours as if it
were.** It is a **bodyless declaration** (`P:/scripts/3_game/entities/entityai.c:1170`): script
hook, not `proto native`, so calling it rebuilds nothing — only runs whatever overrides
exist, and the one in `Clothing_Base` exits via early `return` if `par` is null. What is misleading is
who calls it: vanilla invokes it from `EEItemAttached`
(`P:/scripts/4_world/entities/manbase/playerbase.c:1469-1471`), meaning **rebuild is the
attach** and it rides along. It is recorded as ruled out **with the reason**, not as pending:
a pending item is inherited by someone in a month and wastes their afternoon.

**Neither is `SetSimpleHiddenSelectionState`, and for a reason worth knowing before calling it:
they are TWO distinct index spaces, and mixing them crashes the client.**

| API | indexa | comentario de vanilla |
|---|---|---|
| `SetObjectTexture` / `SetObjectMaterial` (`entityai.c:2895,2898`) | `hiddenSelections` | «Change texture/material **in hiddenSelections**» |
| `SetSimpleHiddenSelectionState` / `IsSimpleHiddenSelectionVisible` (`entityai.c:2891-2892`) | `simpleHiddenSelections` | «**Simple** hidden selection state; 0 == hidden» |

`GetHiddenSelectionIndex` (`entityai.c:2792`) returns an index of the **first** array — its own
comment says so: "index of the string found in cfg array `hiddenSelections`". Passing it to the
*simple* API indexes another array. Measured: **native client crash with minidump**, no trace
beneath script.

That they are distinct arrays is not inference: `weapon_base.c:62` declares
`m_weaponHideBarrelIdx` with comment "index in **simpleHiddenSelections** cfg array", and in
**30 vanilla call-sites of the simple API, ZERO** use `GetHiddenSelectionIndex` — they use fixed
ordinals (`SIMPLE_SELECTION_MELEE_RIFLE = 0` … `SHOULDER_MELEE = 3`, `dayzplayer.c:1160-1163`),
member indices (`weapon_base.c:391,2133,2141`), or dedicated getters (`GetHairIndex()`,
`GetBeardIndex()`, `playerbase.c:9055-9057`).

**And there is indeed a correct way to get simple index: Bohemia wrote it.** The equivalent of
`GetHiddenSelectionIndex` for this space is not a function, it is reading array and searching within.
`weapon_base.c:94-105` does both things —guard and resolution— in the same block:

```c
if ( ConfigIsExisting("simpleHiddenSelections") )              // 1. the guard: without array, no indices
{
    TStringArray selectionNames = new TStringArray;
    ConfigGetTextArray("simpleHiddenSelections", selectionNames);   // 2. array for THIS space
    m_weaponHideBarrelIdx        = selectionNames.Find("hide_barrel");  // 3. the index, by name
    m_magazineSimpleSelectionIndex = selectionNames.Find("magazine");
}
```

Same pattern in `bodyparts/head.c:20`, and guard alone appears twice in
`actionviewbinoculars.c:35` and `:56`. Practical rule: **`GetHiddenSelectionIndex` for texture and
material; `ConfigGetTextArray("simpleHiddenSelections", …)` + `Find()` for simple visibility.**
Never the first feeding the second.

**And for body clothing route dies in config, not in call.** Census of
`simpleHiddenSelections` under `DZ\characters`, one `config.cpp` per category: heads 3, headgear 2,
data 2, glasses 1 — and **tops, pants, vests, gloves, shoes, belts, backpacks, and masks: ZERO**. On a
t-shirt there is no array to index, so no index is valid. **Still available for headgear and
glasses**, with guard upfront: not working for a t-shirt is not same as not working.

And there is no fourth route: a sweep of `proto native` on `entityai.c` and `object.c` returns only
those four. **No `UpdateVisuals` exists** — if you look for a generic refresh call, there is
none, and that saves the search.

When measuring it, separate two failures giving same vanilla frame: "there was no refresh" and "there was
refresh and shutdown wiped out override". Distinguished by re-stamping after
cycle and reading getter at all three moments — for that question getter **does** work, because
slot witness and render oracle are distinct things and only second is discredited.

**And it disputes row "1, right after health level change → renders"** of previous
table: today, a write on first tick after observed change did NOT render, with frame
and log confirming write was made with valid indices. Both observations are from
one sample and both are left recorded. What does not depend on sample size is the negative of
6648 writes.

**The hook that seems the solution and is not**: `EEHealthLevelChanged` DOES run on client (measured;
vanilla body of `clothing_base.c:111-125` is guarded by `!IsDedicatedServer` and only does
client work), but **the engine writes AFTER the hook** — inside hook read already
returns your material, and on next tick it is empty. Re-asserting in there is lost by order.

## `GetObjectMaterial` is NOT an oracle of what renders (added 2026-08-31, evening)

Falsified in BOTH directions within a single run. It is most expensive trap of this skill,
because it turns log into false green evidence:

| what getter returns | what frame shows |
|---|---|
| `dz\data\data\mirror.rvmat` | black vanilla t-shirt — says your override is applied, and it is not visible |
| empty string | t-shirt with mirror material — says it is not there, and it is visible |

**Rule**: to prove a material applied, the instrument is the frame.
`GetObjectMaterial` only reports script slot, which is a different thing from render. A gate
reading getter can sign PASS on clothing looking vanilla, and FAIL on clothing looking
painted.

**Scope, so this does not over-propagate**: what is invalidated is the GETTER as
instrument, **not** verdicts backed by pixels. The G10 PASS of LFThermalCore did not
use any getter — relied on eight frames with visually binary rvmat and control pair
(same entity, same camera: wetness leaves override, health step wipes it), and
still stands. Complete rule is **the getter does not serve as oracle and pixels do**, which is the
instrument used by both runs.

Two minor facts about same getter, useful for reading a log: returns **empty string** when
engine holds material (not a normalized vanilla path, which was expected), and on
**server always returns empty** — clothing material is purely client-side.

## A selection the log calls painted can be hidden by config (SP-445, added 2026-09-28)

[EXACT] `hiddenSelectionsTextures[] = {""}` in config HIDES the selection — the script-side material/texture apply then succeeds and still nothing renders. Vanilla precedent: `XmasLights.HideOnItem` clears selection textures and materials with `""` (`xmaslights.c:94-103`), and `Blowtorch` hides its flame with `SetObjectTexture(0, "")` (`blowtorch.c:48-51`) (DayZ 1.30.164014 Exp). A selection whose material is swapped from script must declare its REAL texture in config, like `BatteryCharger` (`gear_camping/DZ/gear/camping/config.cpp:6975-6977`). [DESIGN] If the emissive must stay visible over a dark `_co` region, also switch that selection to a bright procedural colour texture (`#(argb,8,8,3)color(r,g,b,1,CO)`); not yet verified in game on its own.

## From baked PNG to `.paa` and atlas rvmat (added 2026-09-02)

Measured taking custom per-model atlas from Blender to mod (LFQuad, 4096^2,
`_nohq` + `_smdi`, 13 rewritten materials). Four things bit, and none gives a
guiding error.

### ImageToPAA rejects PNG written by Blender

`Error (Loading of img failed)` and nothing else. Blender PNG carries EXIF, `gamma`, and
`chromaticity`; same pixels resaved with PIL (`Image.open(src).convert("RGB")
.save(dst)`) succeeds on first try. Measured: 23.95 MB from Blender fails, 6.96 MB resaved
converts to a 7.39 MB `.paa`. An `_smdi` written by PIL from start never failed.

Skill already includes generic remedy ("re-save as a 32-bit PNG and re-import") for Workbench
import; here cause is identified and applies equally to CLI.

Same error, two more causes (offline-tested 2026-10-07, DayZ Tools ImageToPAA CLI, 256² fixtures):

- **RLE-compressed TGA** (header image type 10; per Strykar, Photopea offers no uncompressed TGA): fails;
  the same pixels as uncompressed TGA (type 2) convert. Fix: re-save uncompressed
  (`magick in.tga -compress none out.tga`, or PIL `save()` without `compression`).
- **16-bit-per-channel PNG** (greyscale tested; 16-bit RGB not tested): fails. Export 8-bit
  (ImageMagick: the Q8 build, as the community advises; or `-depth 8`).

The reverse direction works from the CLI: `ImageToPAA in.paa out.png` and `ImageToPAA in.paa out.tga`
both exit 0 (the TGA comes out uncompressed, type 2). Strykar's Explorer context-menu `.reg` files
(DayZ Modders Discord, 2026-10-07) wrap exactly these commands; the TGA one rewrites the file in
place with no backup.

**Source filename decides treatment**: ImageToPAA applies normal-map handling
by suffix, so source must be named `*_nohq.png`. A
`*_nohq_DX.png` is converted like any regular texture.

### `dir[]` of `uvTransform` does NOT have canonical identity

Census over all `.rvmat` in vanilla tree, 2026-09-02:

| campo | valores |
|---|---|
| `dir[]` | `{0,0,0}` **65.495** · `{0,0,1}` **42.460** · y media docena mas |
| `aside[]` | `{1,0,0}` **75.099** · `{10,0,0}` 43.045 · `{4,0,0}` 493 · ... |

`aside` (and `up`) have clear identity and their other values are tiling factor;
`dir` has none. Bohemia writes `{0,0,0}` in
`DZ\vehicles\parts\data\aircraft_battery.rvmat:17` and `{0,0,1}` in
`DZ\vehicles\wheeled\van_01\data\van_01_wheel.rvmat:17`, both under `PixelShaderID="Super"`.

Consequence for any gate checking "this texture samples 1:1": look at
`aside`, `up`, and `pos`, and **not** `dir`. A gate requiring `dir[]={0,0,1}` rejected 26 stages
copied verbatim from Bohemia's file.

### 7-stage Super template, and where to get it

Copy `DZ\vehicles\parts\data\aircraft_battery.rvmat` entirely and replace. Stage1 `_nohq`,
Stage2 `#(argb,8,8,3)color(0.5,0.5,0.5,1,DT)` **with `uvTransform` at zeroes** (that is how vanilla
writes it, not an oversight), Stage3 `...(0,0,0,0,MC)`, Stage4 `...(1,1,1,1,AS)`, Stage5
`_smdi`, Stage6 `#(ai,64,64,1)fresnel(0.4,0.4)`, Stage7 environment.

When migrating existing materials to Super, **preserve `ambient[]`/`diffuse[]`** if model
does not yet have `_co`: vanilla writes `{1,1,1,1}` because color comes in texture, and
copying it leaves object white. Also preserve `specular[]`/`specularPower` in the first
pass — `_smdi` already modulates them per texel, and changing map and constants simultaneously makes
any in-game regression unattributable.

For Stage7 DayZ ships dedicated environment maps in `DZ\data\data\`: **`env_land_chrome_co.paa`**
and `env_chrome_co.paa` for chrome, `env_land_co.paa` for metal, plus `env_mirror_co.paa`,
`env_land_plastic_co.paa`, and some twenty more. Flat black `#(argb,8,8,3)color(0,0,0,1,CO)`
is vanilla default, meaning without reflection.

### Blender `Image.save()` with relative path writes elsewhere, without warning

`img.filepath_raw = "folder\file.png"` resolves against open `.blend`, not against
working directory, and `save()` does not throw. An entire bake was assumed written and
was nowhere to be found. Use absolute path, and **check `os.path.isfile()` before logging
"written"** — saying it without checking is how it gets lost.

### SP-376 — Vehicle alpha decal: `Super` + `renderFlags[]={"nozwrite"}`

`PixelShaderID="Super"` alone IGNORES the alpha channel of section's `_ca`. Refuted in-game: SUB_BRZ
labels with real alpha rendered opaque. The fix is not changing shader, it is
completing the render state.

Vanilla pattern for an alpha decal on a vehicle is `Super`/`Super` +
`renderFlags[]={"nozwrite"}`, verified in Offroad stickers
(`DZ\vehicles\wheeled\offroad_02\data\offroad_02_decals.rvmat:7-12`).

What the flag does NOT cover, and must be declared in in-game gate: alpha sorting against other
transparencies, z-fighting if decal is almost coplanar, and that without `emmisive` symbol does
not self-illuminate at night. DXT5 preserves alpha but softens edges.

Recomposition from a DECAL source (icon in alpha channel): RGB = swatch color per pixel,
ALPHA = actual alpha. Never flatten alpha onto RGB — white-on-black bake was precisely that
error, producing the opaque decal looking like a shader issue.
