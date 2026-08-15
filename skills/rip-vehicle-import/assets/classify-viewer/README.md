# Classify viewer — revisión/cambios de la sentada A sin abrir Blender

Visor Three.js (r128 UMD) sobre el export GLB de una escena de sentada A.
**Consultivo + captura de deltas**: la autoridad sigue siendo el `.blend` →
`blender_export_asset_contract.py` → ficha. Los deltas del visor se aplican al
`.blend` por script headless (patrón `fix_roofvent`), nunca a mano.

> **`lib/` no viaja en el pack.** El visor necesita `three.min.js`,
> `GLTFLoader.js` y `OrbitControls.js` (Three.js r128 UMD, MIT, ~726 KB) en una
> subcarpeta `lib\` junto a `index.html`. No se empaquetan aquí por la misma
> política que el resto del pack: se nombra la herramienta de terceros y no se
> redistribuye su código (ver `THIRD_PARTY_NOTICES.md`). Descárgalas de
> <https://github.com/mrdoob/three.js/tree/r128/build> y
> `examples/js/{loaders/GLTFLoader.js,controls/OrbitControls.js}`.
> **r128 UMD, no ESM**: `index.html` las carga con `<script src=…>`, y el
> `importmap` de las versiones ESM falla desde `file://` en muchos Chrome.

## Uso por coche

1. Exportar el GLB (no toca el .blend):
   `blender --background --python export_car_glb.py -- --blend <sentA.blend> --out <dir>\car.glb`
2. Copiar `index.html` + `lib\` junto al `car.glb` (o generar el GLB en la carpeta del visor).
3. Servir por http (no `file://` — fetch del GLB bloqueado): entrada en
   `.claude\launch.json` con `python -m http.server <puerto> --directory <dir>` + `preview_start`.
4. El humano clica pieza → INCLUDE/MOVABLE/EXCLUDE (+ razón). Los cambios viven en
   `window.DZ_DELTAS` ({stem: {from, to, reason}}); el agente los lee con
   `javascript_tool` o el humano usa «Copiar cambios (JSON)».
5. Aplicar deltas al `.blend` headless (mover objetos cuyo `source_id` == stem o
   empiece por `stem__obj`, actualizar `dz_exclude_reason`/`dz_responsible`),
   re-verificar sanity y seguir el carril normal (export → import-blender → check).

## Contrato de datos que espera del GLB

Extras por nodo (los pone `export_car_glb.py` desde las custom props):
`source_id` (estable, `stem__objNN` para sub-objetos), `dz_coll`, `dz_review`,
`dz_movable_group`, `dz_reason`. Piezas sin malla (placeholders EMPTY) aparecen
en la lista como «(sin geometría)».

Primer uso real: sub_wrxsti_04 (2026-08-06), 128 piezas / 24,7 MB de GLB,
verificado con round-trip de deltas y cero errores de consola.
