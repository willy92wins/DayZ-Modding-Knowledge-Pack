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
- Existing `.paa` `_nohq` can be DXT5nm-swizzled; do not audit it as a plain RGB normal until it has been converted/deswizzled correctly.

Evidence:

- Local lesson LL-123: `AI/20_Knowledge/lessons-learned.md:2111` to `:2123`.
- BI RVMAT basics documents X+ Y- normal convention: https://community.bistudio.com/wiki/RVMAT_basics

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
- Local SMDI table source: `dayz-model-pipeline/references/procedural-textures.md:583` to `:635`.

## Export and path rules

- Final config/rvmat references should point to `.paa`, not `.png`, `.tga`, `.jpg`, or `.dds`.
- Use packed game paths such as `dz\...` or `myaddon\...`, not local absolute filesystem paths.
- Keep source files (`.png`, `.xcf`, `.psd`, `.blend`, `.sbsar`) outside final game paths or under a clear source/art folder excluded from PBO if needed.
- When a tool auto-converts by suffix, still verify the resulting `.paa` visually and in-game. Treat community claims about automatic TexView suffix behavior as helpful but not canonical until tested locally.

