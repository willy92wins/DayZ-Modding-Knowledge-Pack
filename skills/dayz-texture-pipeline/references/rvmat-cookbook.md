# RVMAT Cookbook

Use this reference for `.rvmat` authoring patterns. Always clone the nearest working vanilla `.rvmat` first when possible.

## Decision table

| Goal | Prefer | Avoid |
| --- | --- | --- |
| Recolor or skin only | `_co.paa` plus `hiddenSelectionsTextures[]` | New `.rvmat` unless material response changes. |
| Change normal/specular/gloss | Super `.rvmat` with `_nohq` and `_smdi` | Baking specular into `_co`. |
| Health visual states | Normal, damage, destruct `.rvmat` through `healthLevels[]` | Procedural Stage3 tint-only damage unless deliberate. |
| Light on/off | Config material swap to emissive/non-emissive `.rvmat` | Runtime texture swaps for material properties only. |
| Glass/chrome | Clone vanilla glass/chrome `.rvmat` | Generic opaque Super material. |
| Bullet/surface response | Penetration `.rvmat` assigned to collision faces | Visual-only `.rvmat` on collision LOD. |
| One mesh with many tiled materials | Multi shader after UV/mask verification | Multi for small items where selections are simpler. |

## Super shader stage map

| Stage | Typical map | Purpose |
| --- | --- | --- |
| Stage1 | `_nohq.paa` | Normal map. |
| Stage2 | `_dt.paa` or procedural `DT` | Detail texture. |
| Stage3 | `_mc.paa` or procedural `MC` | Macro texture, damage/destruct overlay, or tint. |
| Stage4 | `_as.paa` or procedural `AS` | Ambient shadow. |
| Stage5 | `_smdi.paa` | Specular/gloss response. |
| Stage6 | procedural `fresnel(...)` | Fresnel response. |
| Stage7 | environment texture | Reflection/environment contribution. |

Evidence:

- BI Super shader reference: https://community.bistudio.com/wiki/Super_shader
- Vanilla vehicle example: `P:\DZ\vehicles\wheeled\van_01\data\van_01_body.rvmat:7` to `:83`.
- Vanilla weapon example: `P:\DZ\weapons\shotguns\saiga\data\saiga.rvmat:7` to `:77`.

## [DESIGN] Super material template

Replace paths and stage values with verified addon paths and a category-near vanilla reference.

```cpp
ambient[]={1,1,1,1};
diffuse[]={1,1,1,1};
forcedDiffuse[]={0,0,0,0};
emmisive[]={0,0,0,1};
specular[]={0.4,0.4,0.4,1};
specularPower=80;
PixelShaderID="Super";
VertexShaderID="Super";
class Stage1
{
	texture="myaddon\data\asset_nohq.paa";
	uvSource="tex";
	class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,1}; pos[]={0,0,0}; };
};
class Stage2
{
	texture="#(argb,8,8,3)color(0.5,0.5,0.5,0.5,DT)";
	uvSource="tex";
	class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,1}; pos[]={0,0,0}; };
};
class Stage3
{
	texture="#(argb,8,8,3)color(0,0,0,0,MC)";
	uvSource="tex";
	class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,1}; pos[]={0,0,0}; };
};
class Stage4
{
	texture="#(argb,8,8,3)color(1,1,1,1,AS)";
	uvSource="tex";
	class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,1}; pos[]={0,0,0}; };
};
class Stage5
{
	texture="myaddon\data\asset_smdi.paa";
	uvSource="tex";
	class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,1}; pos[]={0,0,0}; };
};
class Stage6
{
	texture="#(ai,32,1,1)fresnel(1.12,0.78)";
	uvSource="tex";
	class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,1}; pos[]={0,0,0}; };
};
class Stage7
{
	texture="dz\data\data\env_land_co.paa";
	uvSource="tex";
	class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,1}; pos[]={0,0,0}; };
};
```

Notes:

- Vanilla sometimes uses `dir[]={0,0,1}` and sometimes `dir[]={0,0,0}` in uvTransform. Copy the nearest vanilla family instead of normalizing blindly.
- Vanilla Stage2 `DT` alpha varies by asset class. Do not hard-fail alpha differences without an in-engine reason.
- The spelling `emmisive` is the engine-facing field used by vanilla `.rvmat` files.

## Damage/destruct Stage3

For damage/destruct materials, Stage3 should normally be a macro overlay texture, not only a procedural tint.

Vanilla evidence:

- Damage overlay: `P:\DZ\weapons\shotguns\saiga\data\saiga_damage.rvmat:35`.
- Destruct overlay: `P:\DZ\weapons\shotguns\saiga\data\saiga_destruct.rvmat:35`.
- Tiling 4x in both: `saiga_damage.rvmat:39` to `:40`, `saiga_destruct.rvmat:39` to `:40`.

## Emissive materials

Use an on/off material pair when a config or script swaps material state. Vanilla sedan lights show the pattern:

- on: `P:\DZ\vehicles\wheeled\sedan_02\data\sedan_02_lights_e.rvmat:4` has `emmisive[]={1,1,1,120}`.
- off: `P:\DZ\vehicles\wheeled\sedan_02\data\sedan_02_lights.rvmat:4` has `emmisive[]={1,1,1,0}`.

## Glass/chrome materials

Start from a vanilla glass/chrome material near the target asset. Common traits include high specular power, fresnel, environment texture, and sometimes render flags. Verify in the exact vanilla reference before copying.

Example vanilla glass:

- `P:\DZ\vehicles\wheeled\van_01\data\van_01_glass.rvmat:6` uses `specularPower=500`.
- `P:\DZ\vehicles\wheeled\van_01\data\van_01_glass.rvmat:71` uses fresnel.
- `P:\DZ\vehicles\wheeled\van_01\data\van_01_glass.rvmat:83` uses `dz\data\data\env_land_co.paa`.

## Penetration materials

Collision LOD faces need a penetration `.rvmat` when bullet/surface behavior matters. The `.rvmat` references a `.bisurf`.

[EXACT] Vanilla pattern:

```cpp
surfaceInfo="dz\data\data\penetration\wood_desk.bisurf";
ambient[]={0.78799999,0.55000001,0,1};
diffuse[]={0.78799999,0.55000001,0,1};
forcedDiffuse[]={0,0,0,0};
emmisive[]={0,0,0,1};
specular[]={0,0,0,1};
specularPower=1;
PixelShaderID="Normal";
VertexShaderID="Basic";
```

Source: `P:\DZ\data\data\penetration\wood_desk.rvmat:1` to `:9`.

