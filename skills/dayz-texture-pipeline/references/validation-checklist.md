# Validation Checklist

Use this checklist before handing off texture/material work.

## Inputs

- Target addon root and packed paths are known.
- The relevant model selections are verified.
- The intended behavior is classified: texture-only, material response, damage state, emissive/glass, penetration, Multi, or native PBR (MatPBR).
- A close vanilla `.rvmat` / `config.cpp` reference has been read.

## Texture files

- Final game-facing paths reference `.paa`.
- `_nohq` source orientation is known; OpenGL/Y+ sources were converted to DayZ DirectX/Y-.
- Written `_nohq` packing was derived from the file (DXT5nm: raw R=0, X in alpha, SWIZ `05 04 02 03`) or from an `ImageToPAA` `_nohq` round-trip, not from the suffix. Amplitude/relief measured on the deswizzled PNG.
- If the normal was built from albedo luminance: a known dark seam was swept as a **valley** (not a ridge), and Sobel gain was calibrated on this atlas, not copied from another map.
- `_smdi` channels are intentional: R near white, G specular, B gloss/specular power.
- Alpha usage is deliberate for `_ca` or transparent materials.
- Source files are not accidentally referenced from `.rvmat` or config.

## RVMAT

- `PixelShaderID` and `VertexShaderID` are present and match the intended shader.
- Super shader materials have expected Stage1, Stage3, Stage5, Stage6, and Stage7 for the asset class, unless intentionally omitted.
- Damage/destruct materials use Stage3 overlay textures when visible damage is expected.
- Emissive materials use verified `emmisive[]` values and an off material where needed.
- Glass/chrome materials are cloned from a similar vanilla glass/chrome material.
- Penetration materials have `surfaceInfo` pointing to a `.bisurf` and are assigned to collision LOD faces.
- Multi materials have Stage4 mask on UVSet1 / `tex1`.

## MatPBR / .emat (native PBR route)

Only applies to materials using `references/matpbr-emat-pipeline.md`. Skip for Super/Multi.

- `.emat` and its companion `.rvmat` share the exact same file name (differing only in extension).
- The `.rvmat` is a stub only: `PixelShaderID`/`VertexShaderID` set, no Stage blocks.
- The `.emat` contains one `MatPBR { ... }` block with `AlbedoMap`, `NormalMap`, `RoughnessMap`, `MetalnessMap`, `AOMap` (and `EnvReflMap ... cube` unless intentionally a non-reflective material).
- Every map reference in the `.emat` is a `{HEX16}` Resource ID, not a plain file path — confirms it was actually registered/imported in Workbench, not hand-typed.
- Environment cube map source is exactly 256×128 before EDDS import.
- Normal map was **not** DXT-compressed; every other map (except normal) was.
- If the asset needs `healthLevels[]`-driven damage/destruct visuals or is terrain: confirm MatPBR is NOT being used for it (unverified/unsupported per `matpbr-emat-pipeline.md` limitations) — route to Super instead.

## Config

- `hiddenSelections[]` names match the model.
- `hiddenSelectionsTextures[]` and `hiddenSelectionsMaterials[]` array order matches selections.
- `healthLevels[]` references normal, damage, and destruct materials where damage visuals are required.
- Vehicle light on/off properties are cloned from the same vehicle family where possible.
- No local absolute paths appear in final config.

## Tooling checks

Run the linter on new or edited `.rvmat` files:

```powershell
python .\scripts\rvmat_lint.py path\to\material.rvmat --pdrive-root P:\
```

Useful variants:

```powershell
python .\scripts\rvmat_lint.py path\to\material.rvmat --warnings-as-errors
python .\scripts\rvmat_lint.py path\to\material.rvmat --json
```

The linter intentionally reports category-dependent vanilla differences as warnings, not hard failures.

## In-game review

- Inspect the asset in daylight and shadow.
- Check normal direction with a strong side light.
- Check wet/bright lighting for SMDI over-shine.
- Damage the item or force health state where applicable.
- For lights, test on/off transitions.
- For penetration surfaces, test bullet impact sound/material behavior.
- For Multi, verify each mask color and blend boundary in engine.

