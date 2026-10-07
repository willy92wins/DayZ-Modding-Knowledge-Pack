# DayZ Texture Map Conventions

Use this reference when creating or auditing texture maps for DayZ `.rvmat` materials.

## Core suffixes

| Suffix | Role | Typical stage | Notes |
| --- | --- | --- | --- |
| `_co.paa` | Color/albedo | face texture or Stage0 in Multi | Use `.paa` in game-facing paths. |
| `_ca.paa` | Color with alpha | face texture or Stage0 | Use when alpha is required by the material. Verify shader/render flags. |
| `_nohq.paa` | Normal map | Stage1 | DayZ operational convention is DirectX/Y-. Invert G when source is OpenGL/Y+. |
| `_dt.paa` | Detail texture | Stage2 | Often procedural in vanilla. Copy category-near vanilla values. |
| `_mc.paa` | Macro texture/tint/damage overlay | Stage3 | Damage/destruct overlays commonly live here. |
| `_as.paa` | Ambient shadow | Stage4 | Can be a map or procedural color depending on asset. |
| `_smdi.paa` | Specular/gloss data | Stage5 | R usually white, G specular, B gloss/specular power. |

## Normal maps

Canon for this skill:

- DayZ `_nohq` is DirectX/Y-.
- Blender/Cycles and many baking workflows output OpenGL/Y+ by default.
- If source is OpenGL/Y+, invert the green channel before final DayZ export.
- A source of unknown convention is not guessed from where it came from: `scripts/normal_convention.py` (below) proposes a candidate, and the candidate is confirmed another way.
- Shipped `_nohq` is **DXT5nm**, not an RGB normal sitting in a DXT5 container. Do not audit the raw DXT block as `(X,Y,Z)` in RGB.

### Measuring a source map's convention (`scripts/normal_convention.py`, added 2026-10-03)

```
python scripts/normal_convention.py --normal <normal.png> --albedo <albedo.png> [--json]
```

It needs the normal map and the albedo of the same UV layout, same size, as PNG (decode a
`.paa` with ImageToPAA first). It takes two independent readings and proposes a convention only
when they agree:

- **Albedo reading.** The albedo's high-pass marks the hollows (a pixel darker than its blurred
  surroundings). Across a hollow d(nx)/dx and d(ny)/dy have the same sign in DirectX and
  opposite signs in OpenGL; the red channel calibrates the sign, so an albedo darker on the
  ridges than in the hollows gives the same answer. No answer when a correlation is under 0.02
  or undefined (a flat or clean albedo).
- **Curl reading.** With p = −nx/nz and q = ny/nz, the slopes of a height field satisfy
  d(p)/d(row) = d(q)/d(col) under OpenGL and d(p)/d(row) = −d(q)/d(col) under DirectX. The
  convention whose median residual is under 0.8 of the other's wins, provided the two medians
  differ by more than one 8-bit step of the normal (2/255); otherwise no answer. The floor is a
  heuristic, not a bound on rounding noise. Where the normals are nearly flat (nz close to 1),
  rounding to 8 bits moves p and q by up to about half a step, and the residual, which adds two
  central differences, by up to about one step; where they tilt, dividing by a smaller nz
  amplifies the error (one unit normal with nz = 0.4 already moves p by about 4 half-steps). The floor
  was added after a vanilla map whose residuals sat one half-step apart read OpenGL (product
  test, 2026-10-04).
- **Block stability.** When the two readings agree, the map is cut into a 6×6 grid of blocks
  and each block gets each reading from its own pixels, with the derivatives, masks and
  thresholds of the whole map. Among the blocks that name a convention, at most 1 in 10 may name
  the other one for the curl reading and 1 in 3 for the albedo reading, and at least one must
  name the candidate; otherwise no answer. A convention that is really inverted inverts a reading
  wherever there is relief. The albedo reading gets more room because it can flip legitimately
  where the surface curves opposite ways along x and y. Added after the second product test
  (2026-10-04): a flat brick decal (`decal_bricks_01_nohq`) and a cloth bag (`bagpack_nohq`),
  both DirectX by their own features, read OpenGL with readings that agreed on the whole map;
  block by block the decal's curl reading and the bag's albedo reading split.

Exit 0 = a candidate, `DirectX` or `OpenGL` (both readings agree, stable across the blocks),
2 = `INCONCLUSIVE`, 1 = bad input. With `--json` the block counts are
`curl_blocks_agree`/`curl_blocks_opposed`, `albedo_blocks_agree`/`albedo_blocks_opposed` and
`blocks_stable` (null when the readings do not agree). **A candidate is not proof.** The
cross-family review (2026-10-03) built known-DirectX maps that both readings call OpenGL: a
valid tangent-space bake on a sphere patch (the curved frame turns the slopes the readings
assume into something else) and undersampled tileable detail. The block check cannot see an
error that is the same in every block: the tileable detail still reads OpenGL in all 36
blocks. Neither can it see a map that mixes the two conventions inside every block (known
limit below). Confirm a candidate before inverting a channel: the baker's export setting, or a
render under a raking light in which a known groove reads as a groove.

**What a raking-light render does not confirm** (known limit, cross-family review round 3,
2026-10-03). Inverting the green channel changes the shading only through the light's V
component (n·L moves by 2·ny·Ly), so the render confirms a convention only when:

- the light crosses V: it comes from the top or the bottom of the texture, or diagonally, not
  only from a side. A light parallel to U renders the map and its inverted-green copy
  identically: maximum difference 0.0 on the reviewer's tileable fixture against 0.51 with the
  light along V (reproduced 2026-10-04; 0.0 against 0.92 on vanilla `bull_brown_nohq`);
- the known groove has relief along V: it runs along U, so its walls face the top and the bottom
  of the image. A groove that runs along V renders the same with either green under any light;
- the same render with the green inverted reads that groove as a ridge.

When the two renders look the same, the check is inconclusive, not a confirmation. On a mesh, U
and V are the texture's axes as the UV island lies on the surface, so a rotated island changes
which light in the scene crosses V.

- Measured: LFPowerGrid's heater (Sketchfab) gave the candidate **DirectX** both ways: red
  −0.130 and green −0.085 over 491,775 of 1,048,576 pixels (2026-09-21), and curl residuals
  0.013 under DirectX against 0.024 under OpenGL (2026-10-03). Not confirmed another way and not
  checked in game. With the block check it stays **DirectX**: curl 19 blocks for, 0 against;
  albedo 29 for, 2 against.
- Measured on vanilla `_nohq`/`_co` pairs decoded with ImageToPAA (product test v3, 2026-10-04).
  - On 284 pairs never used to design the block check (every tenth pair of `P:\DZ`, offset 2),
    the script gave 157 `DirectX`, 119 `INCONCLUSIVE` (41.9 %) and 8 `OpenGL`.
  - Each of the 8 `OpenGL` is consistent with OpenGL by its own features: ring targets, knobs,
    perforation holes, pores. None of them was a wrong candidate (0 of 165).
  - The `DirectX` answers are presumed right, not checked one by one.
  - On the two samples used to design it, 1 of the 18 `OpenGL` answers is wrong: `kancel_008_nohq`
    (known limit below).
  - Over the three samples (848 valid pairs, 502 candidates): 1 wrong candidate, no N1 error,
    and `INCONCLUSIVE` on about 41 % of the pairs.
  - At least 25 of these 848 vanilla `_nohq` files (about 3 %) are consistent with OpenGL by
    their own features. Do not take a vanilla file as a sign reference without checking it.
- **Maps that mix the two conventions inside every block** (known limit; the Pack owner accepted
  the measured rate on 2026-10-04). The block check only sees a convention that changes from one
  region to another. A map whose features disagree a few pixels apart, the same way in every
  block, passes it and can get a wrong candidate. Vanilla `kancel_008_nohq` is a door whose glass
  panes read DirectX by their own edges, located in the albedo (7 of 7 that count), while its
  hinge bolts and the outer step of its windows read OpenGL. The script calls it OpenGL with stable
  blocks (curl 28 for, 0 against; albedo 27 for, 4 against). Measured rate: 1 wrong candidate in
  502 over three vanilla samples, 0 in the 165 of the sample not used to design the check. Before
  inverting a channel, check features of known relief of more than one kind (a recessed panel and
  a raised bolt, for example).
- Limits of each reading, with a fixture in `tests/test_normal_convention.py`: the albedo
  reading is wrong, with strong correlations, on a surface that curves one way along x and the other
  along y (ribs whose amplitude grows down the image; found by the cross-family review,
  2026-10-03), and the two readings then disagree; the curl reading has no signal on a surface
  that is a sum of one function of x and one of y. Painted dark marks with no relief dilute the
  albedo reading, like the 1D sweep below. An inverted-green rerun is no control (it flips both
  readings).
- Which channel is off: both readings compare the sign of the green channel with the red one,
  so they cannot tell which of the two disagrees with the real relief. A map whose red is
  inverted against the relief (X−, Y−) reads `OpenGL` like a map whose green is inverted, and
  inverting its green gives a consistent DirectX map with the relief upside down. Measured
  2026-10-04 on two vanilla maps the script calls OpenGL, `generalstore_int_003_nohq` and
  `busstop_pavements_nohq`: their red reads the grout and curb joints, which are recessed, as
  ridges. Before inverting a channel, check red on a feature of known relief: across a recessed
  joint that runs along V, red goes bright then dark from left to right.
- Source: the albedo reading is contributed from LFPowerGrid_dev
  `assets/heater/normal_convencion.py` (commit `a4c6e29`, the Pack owner's) through pipeline
  ticket `fb-20260921-164248-a140`; on the heater maps it returns the same two correlations and
  pixel count as the original. The curl reading and the agreement rule were added after the
  review.

### DXT5nm packing `[MECHANISM VERIFIED]`

Vanilla vehicle `_nohq` (`hatchback_02_rust_body_nohq.paa`, `sedan_02_rust_body_nohq.paa`) and two regenerated LFQuad2 maps (body + detail, 2026-08-30) all store:

| Where | What |
| --- | --- |
| Type | `0xFF05` DXT5 |
| `TAGG SWIZ` | `05 04 02 03` |
| Raw mip (decoder does **not** apply SWIZ) | `(R,G,B,A)=(0,Y,Z,X)` — R is 0 on 100 % of pixels; **X lives in alpha** |
| After `ImageToPAA.exe` with a `_nohq` filename | RGB `(X,Y,Z)` (deswizzled) |

Measure amplitude `mean(sqrt((R-128)^2+(G-128)^2))` and relief (percent of pixels with amplitude >25) on the **ImageToPAA-decoded PNG**. Derive packing from the current file and a vanilla `_nohq`, not from the suffix.

### Height-from-luminance (only if you have no baked normal)

If height is albedo luma (`0.2126 R + 0.7152 G + 0.0722 B`), dark is low. Build the DayZ normal as `normalize((-s·dx, -s·dy, 1))` after a Sobel/8 so Y is already DirectX/Y−. Then:

- Confirm the **sign** on a known dark seam with a 1D sweep. Horizontal groove: R>128 entering, R<128 leaving. Vertical groove: use G. Two opposing slopes into a height minimum = valley. The opposite is an inverted mold.
- **Recalibrate `s` per atlas.** A gain that landed inside vanilla on a 1024 body map overshot on a 512 high-contrast detail map. Prefer the lower-middle of a vanilla envelope; an exaggerated normal looks worse than a weak one.
- This method cannot tell painted dirt from a real groove. Do not treat it as a bake.

Evidence:

- Local lesson LL-123: `AI/20_Knowledge/lessons-learned.md:2111` to `:2123`.
- BI RVMAT basics documents X+ Y- normal convention: https://community.bistudio.com/wiki/RVMAT_basics
- Packing and sign: LFQuad2 body + detail regen 2026-08-30, raw mip 128 vs vanilla hatchback_02 / sedan_02 (`CODEX-SOL-NORMAL-20260830.md`, `GROK-DETAIL-20260830.md`).

## SMDI packing

Operational default:

| Channel | Meaning | Starting value |
| --- | --- | --- |
| R | Keep near white; ImageToPAA forces it to 255 for `*_smdi.*` anyway | 255 |
| G | Specular intensity | dark matte, brighter shiny |
| B | Gloss/specular power | roughness inverted |
| A | Usually unused by the material | preserve/export safely |

Material starting points:

| Material | R | G | B | Notes |
| --- | ---: | ---: | ---: | --- |
| worn painted metal | 255 | 70-130 | 80-170 | Add edge wear in G/B. |
| raw steel | 255 | 150-220 | 150-230 | Avoid mirror unless matching vanilla. |
| black rubber | 255 | 20-60 | 30-80 | Low specular, broad highlight. |
| matte plastic | 255 | 35-90 | 60-120 | Raise B for polished plastic. |
| glass/chrome | 255 | 180-255 | 180-255 | Also needs appropriate shader/fresnel/env. |
| wood | 255 | 20-70 | 30-90 | Usually low specular and broad roughness. |

Evidence:

- BI Super shader channel description: https://community.bistudio.com/wiki/Super_shader
- Community DayZ Modders SMDI discussion: https://www.answeroverflow.com/m/1512098192869818471
- Measured DayZ `_smdi` PAAs (ticket fb-20260921-164235-718f, 2026-09-21): four assets (searchlight, battery_adapter, housing, battery_charger) decode with R min/mean **255**; G/B carry specular/gloss. `dayz-model-pipeline/references/procedural-textures.md` §7 generator/presets were wrong (old R=specular / B=Detail Index) and are now aligned to this packing.

### From a metallic/roughness set to the G channel (added 2026-10-07)

Community rule (Strykar, DayZ Modders Discord, 2026-10-07, `unverified` in game): do not copy a metallic map
straight into specular. Metallic is a blend factor between dielectric and metal, not a reflectance: copied as
specular, its black (insulators: wood, cloth, plastic) becomes zero specular, while real insulators reflect about
4 % at normal incidence (2-16 %) and metals 70-100 %. Replace the black with **#383838** and keep the bright metal.

- Arithmetic, checked offline: 4 % linear encoded to sRGB = 0.2209 → **56 = 0x38**; read back as sRGB it is 3.95 %.
  56 sits inside the G ranges of the table above for rubber, plastic and wood (20-90).
- **Not verified: whether the Super shader decodes `_smdi` G as sRGB.** If it reads G as raw linear, 0x38 is 0.22
  of full scale, about 5.6 times the intended 4 %; and that G behaves like a PBR F0 at all is not established
  either, so neither number is a calibrated reflectance. The rule rests on the sRGB assumption; confirm against a vanilla `_smdi` or in game
  before treating 0x38 as a calibrated value instead of a sensible starting point. A hint against it: DayZ Tools
  `Bin/ImageToPAA/TexConvert.cfg` comments the colour classes (`_co`, `_ca`, macro) as "sRGB color space" and gives
  `*_smdi.*` no such comment (read 2026-10-07). A comment, not the shader, so it does not settle the question.
- Strykar's right-click tool (`DayZ_Specular_Converter.zip`, ImageMagick) composites solid #383838 over the
  metallic map using the inverted metallic map as mask. Derived from ImageMagick's masked-composite rule for opaque
  inputs without an alpha channel (with alpha, ImageMagick masks by the mask's alpha instead of its intensity), not
  run here (no ImageMagick on this machine): `out = m·m + 0.2196·(1 − m)`, so 0 → 56, 64 → 58, 128 → 92, 255 → 255.
  Correct for a binary metallic map; it **darkens antialiased or grey transitions** (m² instead of m).
  [DESIGN] The textbook form is the linear blend `out = 0.2196 + (1 − 0.2196)·m` (128 → 156); pick one on purpose.
- Metal comes out at the metallic value (white = 255), not at the albedo's F0 colour. DayZ's G is a scalar, so that
  loss is inherent to the packing, not a tool bug.
- The tool writes a greyscale `<name>_Specular.<ext>` beside the source. It is the **G source of `_smdi`**, not a
  `_smdi`: pack R = 255, G = this map, B = gloss (inverted roughness) per the table above.
- Third-party payload with unknown licence: cite it, do not vendor it into the pack.

### Packing the `_smdi` from `_Specular` + roughness/gloss (added 2026-10-07)

Strykar's second tool ("DayZ SMDI Channel Packer", DayZ Modders Discord, 2026-10-07; `DayZ_SMDI_Packer.zip`,
`Pack_SMDI.bat` read 2026-10-07, not run: no ImageMagick on this machine). Right-click any image; the batch strips
`_Specular` from the name to get `<base>`, looks for `<base>_gloss`, `_glossy`, `_glossiness`, `_rough`,
`_roughness` or `_r` **with the same extension**, and runs one ImageMagick `-combine`: R = the specular filled
white, G = the specular as grey, B = the gloss as grey (`-negate` when it is roughness). Output `<base>_SMDI<ext>`.
That matches the packing table above. What reading the script shows:

- **Roughness beats gloss.** The roughness loop runs after the gloss loop and overwrites the match, so with both
  `<base>_gloss` and `<base>_rough` present the B channel is the inverted roughness, whatever the user meant.
- **Only exact siblings match**: same `<base>`, same extension. A `.png` specular next to a `.tga` roughness gives
  "Could not find a matching gloss or roughness map". The `_r` suffix is narrower than the post suggests
  (`<base>_r<ext>` only), but a red mask named that way would still be read as roughness.
- `cmd` substitution is case-insensitive, so `_Specular`, `_specular` and `_SPECULAR` all strip, wherever they sit
  in the name. Under `EnableDelayedExpansion`, a path containing `!` breaks the lookup.
- The output keeps the input's extension: a `.jpg` specular gives a lossy `_SMDI.jpg`. Whether ImageMagick writes
  the `.tga` RLE-compressed is not verified here; if it does, ImageToPAA rejects it (see `SKILL.md`).
- The inputs must share dimensions; how `-combine` handles a size mismatch is not verified here, so resize first.

- [EXACT][CLAIM-TEX-SMDI-SUFFIX-R255] **Painting R white is redundant when the file goes through ImageToPAA.** `TexConvert.cfg` class
  `specular_diffuseinverse_map` (`*_smdi.*`): DXT1, `channelSwizzleR="1"`, G and B kept, `channelSwizzleA="1"`.
  Round trip 2026-10-07 on a 64² flat fixture with R = 0, G = 56, B = 200, one file per folder (NTFS folds case, so
  `x_smdi.png` and `x_SMDI.png` in one folder are the same file): `x_SMDI` and `x_smdi` both decode back as
  (255, 56, 200, 255); the control `x_plain` keeps (0, 56, 200, 255). So the match is case-insensitive, and the
  suffix, not the content, forces R to 255. That is also why the measured `_smdi` PAAs above read R = 255.
- [EXACT][CLAIM-TEX-SMDI-PROCEDURAL-CENSUS] **The procedural `#(argb,...)color(r,g,b,a,SMDI)` has no single "default".**
  Census of every vanilla `.rvmat` under `P:\DZ` (2026-10-07): 993 procedural SMDI textures: R = 1 in 372, R = 0 in
  564, 0 < R < 1 in 55, and 2 out of range (`color(100,100,100,1,SMDI)` in two `ww2monument` rvmats). 914 of them sit in
  `PixelShaderID="Super"` materials: R = 0 in 543, R = 1 in 325, 0 < R < 1 in 44, 2 out of range. The most common is
  `color(0,0,1,1,SMDI)` (297; e.g. `DZ/characters/bodies/data/jeans_f_grd.rvmat`, a Super material): G = 0, no
  specular at all. Since Super materials ship R = 0 that often, R being white looks conventional rather than
  required; its effect in the shader is not verified, and the census says nothing about which G is neutral for a
  given material. For a neutral dielectric without a metallic map, Strykar suggests a flat G of #383838 (same sRGB
  caveat as above).
- **Bit depth: write 8 bits per channel.** A 16-bit greyscale PNG fails ImageToPAA (tested, see `SKILL.md`,
  ImageToPAA section); 16-bit RGB was not tested, so 8 bits is the safe target, not a requirement proven for every
  format. Strykar advises the 64-bit Q8 ImageMagick build; what matters is the depth of the file actually written,
  so on a Q16 build force `-depth 8`. [DESIGN] Not run here (no ImageMagick on this machine). `Pack_SMDI.bat` passes
  no `-depth`, so a 16-bit source run through a Q16 build can give a 16-bit `_SMDI`, depending on the output format.
- Same licence rule: cite, do not vendor.

## Export and path rules

- Final config/rvmat references should point to `.paa`, not `.png`, `.tga`, `.jpg`, or `.dds`.
- Use packed game paths such as `dz\...` or `myaddon\...`, not local absolute filesystem paths.
- Keep source files (`.png`, `.xcf`, `.psd`, `.blend`, `.sbsar`) outside final game paths or under a clear source/art folder excluded from PBO if needed.
- When a tool auto-converts by suffix, still verify the resulting `.paa` visually and in-game. Treat community claims about automatic TexView suffix behavior as helpful but not canonical until tested locally.

