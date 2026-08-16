# Vehicle / hard-surface materials: shader choice, tiled detail, color variants

Verified 2026-06-14 against vanilla DayZ data, FC_Uaz_2206, and Croco QuadBike. Every
claim below cites a real file; re-verify with Read before quoting.

## Which shader for a model material

A model material's base color (albedo / `_co`) comes from the **face texture** assigned
in the `.p3d` (the implicit Stage0). The rvmat `diffuse[]` constant multiplies it. This
drives the shader choice:

- **Faces have a real `_co` (proper unwrap)** -> `Super` (full vehicle PBR-ish):
  `Stage1=_nohq`, `Stage5=_smdi`/`_dtsmdi`, `Stage2=DT` (tiled detail), `Stage6=fresnel`,
  `Stage7=env`. Mirror `dz\vehicles\wheeled\civiliansedan\data\civiliansedan.rvmat:1-93`
  or `FC_Uaz_2206\textures\body.rvmat`.
- **Constant-color material, NO face `_co`** -> `NormalMapSpecularMap`
  (`VertexShaderID="NormalMap"`): `Stage1=_nohq`, `Stage2=_sm`. The base color stays the
  `diffuse[]` constant; no Stage0/_co needed. Mirror vanilla roads
  `dz\structures_sakhal\roads\parts\data\asf2_sakhal.rvmat` and `mudsakhal_dirt.rvmat`.

Why it matters: `Super` expects a Stage0 `_co` from the face. On a mesh whose faces have
`face.texture=""` (color lives only in `diffuse[]`), `Super` loses the albedo.
`NormalMapSpecularMap` adds relief + a specular map on top of the diffuse constant, so it
upgrades a flat constant-color mesh **without a `_co` atlas and without editing the .p3d**.

### Vanilla shader distribution (sample, `*.rvmat` under `P:\dz`)
`Super` dominant for models/characters/animals; `NormalMapSpecularMap` used by
roads/terrain/decals (the constant-color tiled-surface case); plain `Normal` is the flat
no-stage shader (lighting from vertex normals only, no normal-map texture).

### Detect the "no face _co" case (py3d)
Read the `.p3d` LOD0 and check `face.texture` per face. All-empty (`""`) means the model
is Blender-exported flat-shaded: color is the rvmat `diffuse[]` only. This is the signal
to use `NormalMapSpecularMap`, not `Super`.

## Tiled detail on overlapping / un-baked UVs

When a body packs many materials into one overlapping UV atlas (or has no baked albedo),
a single unwrapped `_nohq`/`_co` cross-contaminates. Use a **tiled detail** map instead:
`uvSource="tex"` + a `uvTransform` whose `aside`/`up` scale repeats the map across each
face, independent of the base UV layout. Example tiling factor from `FC_Uaz_2206` body
`Stage2`: `aside[]={16,0,0}; up[]={0,16,0};`. Pick the factor by physical detail density,
then confirm in-game (tiling phase differs per part with overlapping UVs; that is fine for
subtle surface texture, visible for large directional patterns).

## Normal map orientation

DayZ/Arma `_nohq` are tangent-space **DirectX, X+ Y-** (green down) — same as 3ds Max and
Unreal default. If the source normal is OpenGL/Y+, invert the green channel before PAA
export. (BI community wiki, "RVMAT basics": "Normal maps used in Arma are Tangent-space
maps with the X+ Y- orientation".)

## Map suffixes (confirmed in real files)

`_co` color/albedo; `_nohq` normal (DirectX Y-); `_sm` specular map for
`NormalMapSpecularMap`; `_smdi` / `_dtsmdi` combined specular+macro+detail+illumination for
`Super`; `_as` ambient/SSAO; `_ca` color-alt/control. ImageToPAA picks compression from the
suffix, so name PNGs with the right suffix before converting.

## Color variants (skins) — the `color` hidden selection

A vehicle exposes a `color` hidden selection; the paint albedo is swapped per variant by a
**subclass that overrides `hiddenSelectionsTextures[<color index>]`**. `hiddenSelections`
overrides the texture on the named selection even when the `.p3d` face texture is empty, so
this works without touching the model.

Croco QuadBike (verified, `CrocoVehicles\QuadBike\config.cpp`):
```cpp
class Croco_QuadBike_Green: Croco_QuadBike_base
{
    hiddenSelections[]         = { ...8 lights..., "color" };               // "color" = last index
    hiddenSelectionsTextures[] = { "","","","","","","","","",  "CrocoVehicles\QuadBike\data\quadbike_green_ca.paa" };
    hiddenSelectionsMaterials[]= { ...lights.rvmat..., "CrocoVehicles\QuadBike\data\quadbike.rvmat" };
};
// siblings: _Yellow / _Red / _Black -> quadbike_<color>_ca.paa ; _Grey uses the base
```
FC_Uaz_2206 uses the same pattern (`body_black_full.paa` / `body_green_full.paa` ... at the
body color index). Canonical = texture-driven (override the `_co`); keep the paint on its
own selection with a neutral-`diffuse` rvmat so a variant is just **1 new `_co` + 1
subclass**. (For a per-color gloss change instead, override `hiddenSelectionsMaterials` at
the same index.)

## Stage block reference (NormalMapSpecularMap, constant-color part)

```cpp
ambient[]={...};            // keep the part's tuned color
diffuse[]={...};            // base color (no face _co needed)
specular[]={...};
specularPower=...;
PixelShaderID="NormalMapSpecularMap";
VertexShaderID="NormalMap";
class Stage1 { texture="MyMod\data\X_nohq.paa"; uvSource="tex"; class uvTransform { aside[]={N,0,0}; up[]={0,N,0}; dir[]={0,0,0}; pos[]={0,0,0}; }; };
class Stage2 { texture="MyMod\data\X_sm.paa";   uvSource="tex"; class uvTransform { aside[]={N,0,0}; up[]={0,N,0}; dir[]={0,0,0}; pos[]={0,0,0}; }; };
```

## Open verification (gate in-game)

Whether `NormalMapSpecularMap` falls back to the `diffuse[]` constant when there is no
Stage0/face `_co` is confirmed indirectly (the flat `Normal` shader already renders the
diffuse color on empty-texture faces) but should be confirmed in-game on first use. If a
part renders black/untextured, give that selection a `_co` via `hiddenSelectionsTextures`
(only possible for named hidden selections) or fall back to `Normal` + `Stage1 _nohq`.
