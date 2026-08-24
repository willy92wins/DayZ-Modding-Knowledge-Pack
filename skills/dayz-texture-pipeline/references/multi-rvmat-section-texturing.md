# Multi RVMAT Section Texturing

This reference is based on the DayZ model pipeline note `references/multi-rvmat-section-texturing.md` and expanded with official BI documentation, local research, and validation gates.

Use Multi only when it is better than assigning one material per selection. For most DayZ items, one `.rvmat` per selection is simpler, easier to debug, and closer to vanilla authoring. Multi is most useful for large statics, terrain-like buildings, or assets that need several tiled material sets blended through a mask while keeping section count low.

## Technique choices

| Technique | Best use | Tradeoff |
| --- | --- | --- |
| One `.rvmat` per selection | Items, weapons, small props, clean material islands | More sections/draw calls, but simple and vanilla-like. |
| Multi shader | Large statics with tiled material families and RGB mask control | Requires specific stage layout, mask, and two UV sets. |
| UV atlas bake | Simple props with one baked material | Loses per-material tiling and SMDI control. |

## What Multi does

Multi uses a mask to select four material families:

| Mask color | Material family |
| --- | --- |
| Black | Base family |
| Red | Red family |
| Green | Green family |
| Blue | Blue family |

Each family can have separate color, SMDI, and NOHQ data. This is the main advantage over a simple atlas: roughness/specular/normal response can differ per masked material.

## Stage mapping

| Family | Color | SMDI | NOHQ |
| --- | --- | --- | --- |
| Black | Stage0 | Stage5 | Stage11 |
| Red | Stage1 | Stage6 | Stage12 |
| Green | Stage2 | Stage7 | Stage13 |
| Blue | Stage3 | Stage8 | Stage14 |

Shared stages:

| Stage | Purpose |
| --- | --- |
| Stage4 | RGB+black mask on UVSet1 / `tex1`. |
| Stage9 | Macro/MC. |
| Stage10 | AS/ADS. |

## UV requirements

Multi is a two-UV workflow:

- UVSet0 / `tex`: tiling coordinates for material textures.
- UVSet1 / `tex1`: non-overlapping mask placement coordinates.

If UVSet1 is missing, mirrored, overlapping, or scaled like the tiling UV, the mask will not land correctly.

## Required shader IDs

[DESIGN]

```cpp
PixelShaderID="Multi";
VertexShaderID="Multi";
```

Evidence:

- Mondkalb's MultiMaterial tutorial documents `PixelShaderID="Multi"` and `VertexShaderID="Multi"`: https://community.bistudio.com/wiki/Mondkalb%27s_MultiMaterial_Tutorial
- DayZ Modders community template thread: https://www.answeroverflow.com/m/1499902968651186378

## [DESIGN] Annotated stage skeleton

This is a skeleton, not a drop-in material. Replace every path and verify with a real mask and both UV sets.

```cpp
PixelShaderID="Multi";
VertexShaderID="Multi";

class TexGen0
{
	uvSource="tex";
	class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,1}; pos[]={0,0,0}; };
};
class TexGen1: TexGen0 {};
class TexGen2: TexGen0 {};
class TexGen3: TexGen0 {};
class TexGen4
{
	uvSource="tex1";
	class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,1}; pos[]={0,0,0}; };
};

class Stage0 { texture="myaddon\data\black_co.paa"; texGen="0"; };
class Stage1 { texture="myaddon\data\red_co.paa"; texGen="1"; };
class Stage2 { texture="myaddon\data\green_co.paa"; texGen="2"; };
class Stage3 { texture="myaddon\data\blue_co.paa"; texGen="3"; };
class Stage4 { texture="myaddon\data\asset_mask_co.paa"; texGen="4"; };

class Stage5 { texture="myaddon\data\black_smdi.paa"; texGen="0"; };
class Stage6 { texture="myaddon\data\red_smdi.paa"; texGen="1"; };
class Stage7 { texture="myaddon\data\green_smdi.paa"; texGen="2"; };
class Stage8 { texture="myaddon\data\blue_smdi.paa"; texGen="3"; };

class Stage9 { texture="#(argb,8,8,3)color(0,0,0,0,MC)"; texGen="0"; };
class Stage10 { texture="#(argb,8,8,3)color(1,1,1,1,AS)"; texGen="4"; };

class Stage11 { texture="myaddon\data\black_nohq.paa"; texGen="0"; };
class Stage12 { texture="myaddon\data\red_nohq.paa"; texGen="1"; };
class Stage13 { texture="myaddon\data\green_nohq.paa"; texGen="2"; };
class Stage14 { texture="myaddon\data\blue_nohq.paa"; texGen="3"; };
```

## Mask authoring

- Paint pure black, red, green, and blue when you need hard assignment.
- Use blends only if the visual result has been checked in engine.
- Keep mask UVs on UVSet1.
- Store the mask as `.paa` in the game path. The source working file can be `.png` or layered source, but the `.rvmat` should reference `.paa`.

## Pitfalls

- Using Multi for a small item that would be simpler with selections.
- Forgetting UVSet1 or assigning the mask to `tex` instead of `tex1`.
- Supplying only color maps and losing per-family SMDI/NOHQ, which removes most of the benefit of Multi.
- Treating the BI/Mondkalb tutorial as DayZ-vanilla proof. It is valid shader documentation, but local research did not find vanilla DayZ `.rvmat` examples using `PixelShaderID="Multi"`.
- Exporting source `.png`/`.tga` paths into the `.rvmat` instead of final `.paa`.

## Validation gate

Before accepting a Multi material:

1. Confirm `PixelShaderID` and `VertexShaderID` are both `Multi`.
2. Confirm Stage4 points to the mask and uses UVSet1 / `tex1`.
3. Confirm Stage0-3, Stage5-8, and Stage11-14 are present or intentionally omitted with a documented reason.
4. Confirm mask colors line up with the intended material families in engine.
5. Confirm the asset actually benefits from fewer sections or from per-family tiled material response.

