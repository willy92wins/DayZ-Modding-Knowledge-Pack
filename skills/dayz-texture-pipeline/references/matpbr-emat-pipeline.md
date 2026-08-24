# MatPBR / .emat Pipeline (native PBR route)

Status: **community-verified, not Bohemia-documented**. Everything below comes from a
practitioner tutorial plus two real `.emat`/`.rvmat` example files, cross-checked against
one confirmed local fact (`PixelShaderID="CalmWater"` is a real vanilla shader ID, see
`P:\DZ\water\ponds\data\water_lake.rvmat`). None of it has been run through Workbench or
in-game by this skill yet — treat every claim here as `[DESIGN]` until your own import
confirms it, and prefer `rvmat-cookbook.md` (Super shader) when you need a well-trodden,
fully-documented path instead.

This is a second, parallel material route, not a replacement for the Super shader route
in `rvmat-cookbook.md`. It exists specifically for assets authored with a standard
metallic-roughness PBR texture set (Substance Painter/Designer, Quixel, purchased PBR
asset packs) where you want to plug the maps in with minimal channel-repacking, instead of
converting into SMDI (see `map-conventions.md` SMDI packing table for that other path).

## When to use this instead of Super/.rvmat

| Use MatPBR when | Use Super (`rvmat-cookbook.md`) when |
| --- | --- |
| Source is an authored metallic/roughness PBR set (Substance, Quixel, AI-generated) | Source is already DayZ-suffix textures or you're cloning a vanilla material |
| Asset is a weapon, clothing item, vehicle, or building | Asset is terrain (MatPBR has no known terrain path — see Limitations) |
| You don't need damage/destruct overlay variation on this material | You need `healthLevels[]`-driven damage/destruct visuals (see config-and-damage.md) |
| You're fine with a larger packaged texture footprint | Mod size / texel budget is tight |

Confirmed working (per tutorial, unverified by this skill): weapons, clothing, vehicles,
buildings. Explicitly **not** solved: terrain.

## Required textures

Unreal Engine-style suffixes, distinct from the DayZ legacy vocabulary in
`map-conventions.md`:

| Suffix | Role | Notes |
| --- | --- | --- |
| `_albedo` | Base color | Equivalent role to `_co`, different pipeline |
| `_ao` | Ambient occlusion | One AO per model is usually enough — see sharing tip below |
| `_metallic` | Metalness | "Works but in limited capacity" per source tutorial — verify per-asset |
| `_normal` | Normal map, **DirectX** convention | Same Y- convention as `_nohq`; do not compress this map |
| `_roughness` | Roughness | Do not confuse with SMDI gloss — opposite convention, see below |

## Required companion files

Three files work together per material — this is the core structural difference from the
Super pipeline, which only needs one `.rvmat`:

1. **`.emat`** — contains the actual `MatPBR { ... }` shader definition and every texture
   map reference (as Resource IDs, not plain paths).
2. **`.rvmat`** — a stub containing only `PixelShaderID`/`VertexShaderID`. The example
   files use `CalmWater` (confirmed real vanilla shader ID, normally used for water). Why
   `CalmWater` specifically works as a passthrough is not explained by the source tutorial
   and has not been independently verified here — treat it as an empirically-observed
   recipe, not an understood mechanism.
3. **Environment cube map** — a 256×128 EDDS, imported with `GenerateCubemap` ticked and
   `TiledTexture` unticked in the Import Settings tab. A fully bright env map is reported
   to work better than a traditional dark-bottom one for most surfaces; a **darker** env
   map is reported to work better specifically on glass.

**Critical naming rule**: the `.emat` and `.rvmat` must share the exact same file name
(differing only in extension). This is a hard requirement per the source tutorial, not a
convention — the engine pairs them by name.

## AO texture preparation

Default AO bakes render too dark in-game. Brightening recipe (Paint.NET, but portable to
any editor with a Screen blend mode):

1. Duplicate the AO layer.
2. Invert colors on the duplicate.
3. Set the duplicate's blend mode to `Screen`.
4. Flatten to a single layer.

## Importing into Workbench

1. Set up the file structure at the final destination — `.emat` and `.rvmat` must already
   have the matching name (see naming rule above).
2. Register and import both via DayZ Workbench.
3. Click each `.edds` in Workbench and confirm it imported correctly. If any failed:
   re-save the source as a 32-bit PNG (Paint.NET or equivalent) and re-import. Source
   tutorial does this preemptively for every texture to skip the failure-check step.
4. Select all `.edds` files **except the normal map** and re-import with `DXTCompression`
   (Import Settings tab, bottom right). Multi-select with Ctrl; a misclick means
   re-selecting the whole batch from scratch.
5. Open the `.emat` and copy each texture's Resource ID (the `{HEX16}` GUID Workbench
   generated on import) into the matching slot in the `.emat` file.

**GUID gotcha**: a texture's Resource ID is derived from its registered file path/name.
Renaming or moving a registered `.edds` breaks the GUID. To relocate a texture, move the
source PNG and re-import at the new destination instead of moving the registered file.

## Applying to an object

- Assign the `.rvmat` (the stub, not the `.emat`) as the Material — in Object Builder, in
  `config.cpp`, or via `SetObjectMaterial`.
- The `texture` field is ignored under MatPBR; leave it at its default value.

## Glass / transparency

Two methods from the source tutorial, reproduced as starting-point examples. The Resource
IDs below are the tutorial author's real GUIDs from their own project — regenerate your
own via the Workbench import steps above, do not reuse these verbatim.

Known caveats: doesn't handle overlapping transparent surfaces well (e.g. foliage), and
does not apply vertex animation the way the vanilla tree shader does.

### Method 1 — full-surface transparency (e.g. glass panes)

`Sort translucent` + `AlphaBlend`. Darker env map reported to work better here.

```
MatPBR {
 AlbedoMap "{107E0EF11826BF98}...glass_ca.edds"
 Sort translucent
 CastShadow 0
 ReceiveShadow 1
 Specular 0.1 0.1 0.1 0.5
 SpecularMul 0.05
 Diffuse 0.95 0.95 0.95 0.5
 BlendMode AlphaBlend
 NormalMap "{7E0685D245F77EF8}...glass_normal.edds"
 RoughnessMap "{9A31F3AB2ED461C8}...glass_roughness.edds"
 MetalnessMap "{E43FB2221EF03FF2}...glass_glass_metallic.edds"
 AOMap "{4EA7E41FBEECE7C7}...glass_ao.edds"
 EnvReflMap "{C67F75AABD568129}...env_landdark_co.edds" cube
}
```

### Method 2 — punch-through transparency (e.g. mesh, foliage with holes)

`AlphaTest` makes pixels below a threshold fully transparent. Uses the brighter env map.

```
MatPBR {
 AlbedoMap "{CD0D20E47EAAF7B4}...texture_albedo.edds"
 CastShadow 1
 ReceiveShadow 1
 SpecularMul 0.05
 AlphaTest 0.05
 NormalMap "{8C28C3AFF87D1AF7}...texture_normal.edds"
 RoughnessMap "{58B6DAB5DC14D87F}...texture_roughness.edds"
 MetalnessMap "{AE30B70648A7C2DE}...texture_metallic.edds"
 AOMap "{E66D5BFBF10675E1}...texture_ao.edds"
 EnvReflMap "{066623E928F029E6}...env_land_co.edds" cube
}
```

## Known limitations (from source tutorial — treat as hard constraints, not tips)

- **No `_mc`/DamageSystem overlay support.** The Super-shader damage/destruct pattern in
  `config-and-damage.md` (Stage3 macro overlay inside one material) does not apply to
  MatPBR — there is no Stage system at all. Whether `healthLevels[]` can still swap between
  whole separate MatPBR materials per health state (same config-level mechanism, different
  materials rather than one material's internal overlay) is a reasonable extrapolation from
  how `healthLevels[]` works with Super, but is **not confirmed** by the source tutorial or
  independently verified here — check in Workbench before relying on it for a damage-visual
  feature.
- Metallic response is limited/inconsistent — verify visually per asset, don't assume it
  matches the source PBR tool's preview.
- Total texture size is typically larger than the equivalent Super/SMDI material.
- Surfaces meant to show a clear env-map reflection need to be darker, or should use the
  traditional Super/`.rvmat` route instead — MatPBR's reflection response doesn't handle
  bright reflective surfaces as well.
- No terrain path found by the source author.

## Tips

- **Share maps across model parts** when the underlying surface is identical: `_roughness`/
  `_metallic`/`_normal` change the reflection response, so keep those per-material, but
  `_ao` is usually the same across a whole model — one AO map per model, not per part,
  cuts mod size.
- **Resolution budget**: 2K standard, 1K for small objects. 4K is supported and looks
  better but is 16× the pixel count of 1K and 4× that of 2K — costs real players load
  time/VRAM on lower-end hardware and slower storage.
- **Do not compress the normal map.** Compression loses significant detail, and metallic
  response is reported to look better when the normal isn't perfectly flat.
- **License check before using AI-assisted or purchased PBR sets.** Some purchased models
  explicitly forbid AI-assisted texture generation/editing in their license — check before
  feeding vendor textures to an AI tool.

## Evidence

- Two real example files supplied by the user (`.emat` + `.rvmat` pair), read directly —
  confirmed the `MatPBR { AlbedoMap / NormalMap / RoughnessMap / MetalnessMap / AOMap /
  EnvReflMap }` block shape and the `{HEX16}` Resource ID format.
- `PixelShaderID="CalmWater"` confirmed as a real, currently-used vanilla shader ID via
  local grep: `P:\DZ\water\ponds\data\water_lake.rvmat:1-2` (and 12 other vanilla water
  `.rvmat` files in the same tree).
- `MatPBR` and `.emat` do not appear anywhere in the local vanilla `P:\DZ` reference tree —
  consistent with this being a modder-discovered/Workbench-side technique rather than
  something shipped in any extracted vanilla asset.
- This skill's own multi-agent web research (2026-07-13) found zero independent
  confirmation of a native PBR shader path in DayZ's public documentation — the entire
  `.emat`/MatPBR mechanism is sourced from a single practitioner tutorial. Corroborate
  further (official patch notes, other modders' write-ups) before treating any specific
  claim in this file as settled.
