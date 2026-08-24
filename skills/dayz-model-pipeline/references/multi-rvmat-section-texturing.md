# Multi-material rvmat: per-section texturing (Multi shader)

> Sources: DayZ Modders Discord
> thread on multi-rvmat (2026-06), community template `multimat_template.rvmat`,
> [Mondkalb's MultiMaterial Tutorial](https://community.bistudio.com/wiki/Mondkalb%27s_MultiMaterial_Tutorial).

## When to use which per-section technique

| Technique | Use when | Cost |
|---|---|---|
| One rvmat per named selection (`hiddenSelections` / per-face material) | Few large sections, runtime swapping needed (LED on/off, skins) | 1 draw section per material |
| **Multi shader (this doc)** | One mesh region needs 2-4 tiling detail textures (walls, large props, terrain-like surfaces) with high texel density | Single material, but ~15 texture fetches; heavier pixel shader |
| UV-atlas bake | Small items, one material budget | Cheapest, lowest fidelity |

Multi shader is rare on DayZ items for performance reasons — it suits buildings/large
statics, not handheld items. Per-section specular is its killer feature: each masked
material gets its own SMDI response (polished metal ≠ painted metal ≠ rubber) instead
of one global gray-plastic specular. A correct per-section roughness/gloss response
beats decorative emissive effects.

## How it works

A low-res **RGB+Black mask** (painted on the model's UV layout) selects which of 4
tiling detail texture sets shows where: **Black, Red, Green, Blue** → texGen 0-3.
Each region is "what is white in a normal alpha mask". Workflow from Blender: paint or
generate one standard B/W mask per material, then composite them into the R/G/B
channels (4th material = black = none of the three).

### Stage → texGen → color mapping

| Color | CO stage | SMDI stage | NOHQ stage | texGen |
|---|---|---|---|---|
| Black | Stage0 | Stage5 | Stage11 | 0 (5 for SMDI) |
| Red | Stage1 | Stage6 | Stage12 | 1 (6 for SMDI) |
| Green | Stage2 | Stage7 | Stage13 | 2 (7 for SMDI) |
| Blue | Stage3 | Stage8 | Stage14 | 3 |
| Mask / MC / AS | Stage4 (mask), Stage9 (MC), Stage10 (AS/ADS) | — | — | 4 |

- `PixelShaderID = "Multi"; VertexShaderID = "Multi";`
- Stage4 mask = the RGB+Black `_co.paa` painted on UVSet 1.
- Stage9 MC = macro color tint over the whole model ("the real texture"; details overlay it).
- Stage10 = `_as.paa` / `_ads.paa` ambient shadow.
- Per-section SMDI can be procedural: `#(argb,8,8,3)color(0.5,G,B,1,DTSMDI)` where
  G = specular intensity, B = glossiness — tune per material type instead of sharing one.

## Dual UV set (the part everyone misses)

Two UV sets are REQUIRED:

- **UVSet 1** (`uvSource="tex1"`): the original unwrap. Drives mask/MC/AS placement
  (texGen 4). **Never touch it.**
- **UVSet 0** (`uvSource="tex"`): copy of UVSet 1, then scaled UP heavily. Drives the
  tiling of detail textures (texGen 0-3). Bigger UVs = more tiling = more texel density.

Canonical (Mondkalb) assignment: texGen 0-3 → `tex`, texGen 4 → `tex1`. Community
templates sometimes give individual sections their own UV set (`tex2` etc.) for
independent tiling control — valid, the engine supports tex/tex1/tex2.

**Export pitfall**: the .p3d must actually contain both UV sets. In Blender keep two UV
layers and verify after export (py3d: check `uvsets` count per LOD). If UVSet 1 is
missing, the mask smears across the tiled UVs.

## uvTransform cheat sheet (applies to ANY rvmat, not just Multi)

```cpp
class uvTransform
{
    aside[] = {0.5, 0, 0};  // [U scale, shear, 0]
    up[]    = {0, 0.5, 0};  // [shear, V scale, 0]
    dir[]   = {0, 0, 1};    // leave {0,0,1}
    pos[]   = {0, 0, 0};    // [U offset, V offset, 0] — shift UVs here
};
```

- Scale **< 1 scales the UVs down → texture appears BIGGER** (0.5 = 2× larger).
- Scale > 1 = more tiling (skill already uses `{10,0,0}` for detail maps).
- To nudge a texture into place, start with `pos[]` offsets before rescaling.
- Note: the BI wiki tutorial shows `dir[]={0,0,0}; pos[]={0,0,1};` — that's a wiki
  transcription quirk; use the form above (matches working community template).

## Template (annotated, from working community template)

```cpp
ambient[]  = {0.5,0.75,0.5,1};
diffuse[]  = {1,1,1,1};
forcedDiffuse[] = {0,0,0,0};
emmisive[] = {0,0,0,1};
specular[] = {0.15,0.15,0.15,1};
specularPower = 10;
PixelShaderID = "Multi";
VertexShaderID = "Multi";
// BLACK section
class TexGen0 { uvSource="tex";  class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,1}; pos[]={0,0,0}; }; };
class TexGen5 { uvSource="tex";  class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,1}; pos[]={0,0,0}; }; };
class Stage0  { texture="MyMod\data\black_section_co.paa";   texGen="0"; };
class Stage5  { texture="MyMod\data\black_section_smdi.paa"; texGen="5"; };
class Stage11 { texture="MyMod\data\black_section_nohq.paa"; texGen="0"; };
// RED section (reuses vanilla DZ texture — legal and common)
class TexGen1 { uvSource="tex";  class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,1}; pos[]={0,0,0}; }; };
class TexGen6 { uvSource="tex";  class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,1}; pos[]={0,0,0}; }; };
class Stage1  { texture="DZ\structures\walls\data\wall_stone_moss_co.paa";   texGen="1"; };
class Stage6  { texture="#(argb,8,8,3)color(0.5,0,0.55,1,DTSMDI)";           texGen="6"; };
class Stage12 { texture="DZ\structures\walls\data\wall_stone_moss_nohq.paa"; texGen="1"; };
// GREEN section (unused here — comment out whole block if only 3 materials)
// BLUE section
class TexGen3 { uvSource="tex";  class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,1}; pos[]={0,0,0}; }; };
class Stage3  { texture="#(argb,8,8,3)color(0,0,0,1,co)";              texGen="3"; };
class Stage8  { texture="#(argb,8,8,3)color(0.5,0,0.1,1,DTSMDI)";      texGen="3"; };
class Stage14 { texture="dz\structures\data\concrete\concrete_old_nohq.paa"; texGen="3"; };
// MASK + MC + AS — placement UV set
class TexGen4 { uvSource="tex1"; class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,1}; pos[]={0,0,0}; }; };
class Stage4  { texture="MyMod\data\mymodel_mask.paa"; texGen="4"; };
class Stage9  { texture="MyMod\data\mymodel_mc.paa";   texGen="4"; };
class Stage10 { texture="MyMod\data\mymodel_as.paa";   texGen="4"; };
```

Apply in Object Builder / py3d: select the faces, REMOVE the texture (faces get material
only — texture field empty), assign this rvmat.

## Pitfalls

- Mask painted with gradients/anti-aliasing → sections blend; keep hard pure-color edges
  unless blending is intentional.
- Stage ↔ texGen mismatch is silent: each detail CO/NOHQ pair must share the section's
  texGen; SMDI uses its own texGen (5-8) so its tiling can differ.
- Faces still carrying a texture + Multi rvmat → wrong output; texture must be removed.
- Only 4 sections max (B/R/G/B). Need more → split mesh into multiple Multi materials
  or fall back to per-selection rvmats.
- Per-section specular: don't ship one gray `specular[]` for everything — the SMDI
  stage per section is where metal vs paint vs rubber is defined.
