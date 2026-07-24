# DayZ Model Pipeline

Source skill: `C:\Users\<you>\.agents\skills\dayz-model-pipeline\SKILL.md:59-236`
Extraction date: 2026-05-14
Evidence level: skill-sourced pipeline summary. Exact tool commands and py3d APIs must be verified before use in a project.

## Preferred Pipeline

Primary path: Blender headless for quality geometry, then py3d assembly for DayZ `.p3d` output.

1. Define object behavior, visual states, animated parts, interaction points, and connection points.
2. Optionally create an interactive Three.js preview for user validation before building the real model.
3. Generate geometry in Blender with modifiers, UVs, LOD decimation, and optional AO bake.
4. Generate procedural textures using coherent noise/FBM, not random-per-pixel noise.
5. Assemble `.p3d` with visual LODs, Geometry/Fire/View LODs, Memory LOD, selections, texture/material paths, and read-back verification.
6. Generate `.rvmat`, `model.cfg`, `config.cpp`, `$PBOPREFIX$`, and packaging structure.
7. Run `dayz-p3d-audit` before treating the model as accepted.

## Alternative Paths

- py3d-only: quick prototypes and simple primitives.
- External mesh import: artist-authored OBJ/FBX/GLB integration, scale/orientation normalization, decimation, texture preservation.
- Manual Blender workflow: complex meshes where manual LOD/UV/AO control matters.
- Viewer/tagger: user labels external model parts interactively before config generation.

## Critical Rules

- Use the DayZ/Arma py3d library, not the unrelated PyPI point-cloud package.
- Geometry, Fire, and View LOD components need valid collision-style structure and mass where applicable.
- Memory points are single vertices; animation axes need exactly two points.
- Named selections must be consistent across relevant LODs.
- Texture paths in final P3D should target `.paa`, even if intermediate generation uses `.png`.
- `model.cfg` model class names must match P3D filenames.
- Blender-to-DayZ coordinate conversion and winding correction are coupled. Verify orientation and face winding after generation.
- Attachments need proxy geometry, proxy P3D, and config mapping; logical attachment without proxy setup can be invisible.

## LOD Values To Verify

Modern DayZ values from the skill:

| LOD Type | Value |
|---|---|
| Geometry | `1.0e13` |
| Memory | `1.0e15` |
| LandContact | `2.0e15` |
| Roadway | `3.0e15` |
| View Geometry | `6.0e15` |
| Fire Geometry | `7.0e15` |

Keep legacy values when editing older working models unless the project has verified reason to migrate.

## Acceptance Gate

A rendered viewer is not enough. The acceptance signal is a green P3D audit plus project-specific in-game validation where collision/action targeting matters.

## Related

- [`AI/20_Runbooks/dayz-p3d-audit.md`](../20_Runbooks/dayz-p3d-audit.md)
- [`AI/20_Runbooks/dayz-p3d-inspector.md`](../20_Runbooks/dayz-p3d-inspector.md)
- [`AI/20_Runbooks/dayz-3d-viewer.md`](../20_Runbooks/dayz-3d-viewer.md)
- [[dayz-debinarizer-inspector-memory-selection-bugs]] — bugs que vacían selecciones de Memory LOD al debinarizar/round-trip; gate antes de rebuild irreversible.
- [[dayz-custom-infected]] — caso de modelo humanoide (LODs con hueco, Geometry convexo, escala horneada).
- [[stage-01-mesh-retopo-uv-bake]] — retopo/UV/AO bake en Blender previo al assembly py3d.
- [[dayz-mod-implementation-checklists]] — checklist de model.cfg/config.cpp y mínimos del engine (§6) para el modelo final.
- [[dayz-animations-creatures-weapons]] — named selections + axes (2 puntos) que la capa de animación consume.

## Caveat — proxies de rueda/suspensión SÍ van en la FireGeometry LOD (added 2026-05-26)

La regla genérica de proxies ("un proxy de attachment NO va en Fire/Geometry/Memory LOD,
solo en las Resolution LODs" — `memory-and-selections.md` §Proxy Selections) es correcta
para proxies de **ítem-attachment** (batería, faro). **NO** aplica a los proxies de **slot
de rueda/suspensión** de un vehículo: verificado en **4/4 vehículos vanilla**
(`civiliansedan`, `hatchback_02`, `offroadhatchback`, `offroad_02`), los wheel-proxies
aparecen en la Resolution LOD **y** en la FireGeometry LOD (mismas posiciones). Al hornear
la FireGeometry de un vehículo, **replicar los wheel-proxies** ahí para casar con vanilla.

**Matiz de causación (R31/R35)**: en LFQuad, añadir los wheel-proxies que faltaban en la
FireGeo era necesario por paridad, pero **no** resolvió por sí solo el bug "las ruedas no
simulan/no ruedan" (que siguió abierto con otra causa). Incluirlos por paridad; no asumir
que su ausencia es la causa única de un fallo de simulación de rueda.

Origen: LFQuad `bug-ledger.md` 2026-05-26 (P1, UPDATE 1/2) + [`research/2026-05-26-fix-firegeo-wheel-proxies-claude.md`](../10_Projects/LFQuad/research/2026-05-26-fix-firegeo-wheel-proxies-claude.md) + handoff [`30_Sessions/2026-05-26-LFQuad-wheelsim-debug-handoff.md`](../30_Sessions/2026-05-26-LFQuad-wheelsim-debug-handoff.md). Parche al plugin pendiente: [`skill-patches-pending.md`](skill-patches-pending.md) SP-012.
