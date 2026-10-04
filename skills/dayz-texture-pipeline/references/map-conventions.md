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
  differ by more than one 8-bit step of the normal (2/255); otherwise no answer. Rounding to
  8 bits alone moves each residual by up to one step (p and q by half a step, the central
  difference keeps that, the residual adds two of them), so closer medians are noise. The
  floor was added after a vanilla map whose residuals sat one half-step apart read OpenGL
  (product test, 2026-10-04).
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
| R | Keep near white unless cloning a vanilla exception | 255 |
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

## Export and path rules

- Final config/rvmat references should point to `.paa`, not `.png`, `.tga`, `.jpg`, or `.dds`.
- Use packed game paths such as `dz\...` or `myaddon\...`, not local absolute filesystem paths.
- Keep source files (`.png`, `.xcf`, `.psd`, `.blend`, `.sbsar`) outside final game paths or under a clear source/art folder excluded from PBO if needed.
- When a tool auto-converts by suffix, still verify the resulting `.paa` visually and in-game. Treat community claims about automatic TexView suffix behavior as helpful but not canonical until tested locally.

