# Classify viewer — review/changes of session A without opening Blender

Three.js viewer (r128 UMD) over GLB export of a session A scene.
**Advisory + delta capture**: authority remains `.blend` →
`blender_export_asset_contract.py` → ledger entry. Viewer deltas are applied to
`.blend` via headless script (pattern `fix_roofvent`), never manually.

> **`lib/` is not bundled in the pack.** The viewer needs `three.min.js`,
> `GLTFLoader.js` and `OrbitControls.js` (Three.js r128 UMD, MIT, ~726 KB) in a
> `lib\` subfolder next to `index.html`. They are not packaged here per the same
> policy as the rest of the pack: name the third-party tool and do not
> redistribute its code (see `THIRD_PARTY_NOTICES.md`). Download them from
> <https://github.com/mrdoob/three.js/tree/r128/build> and
> `examples/js/{loaders/GLTFLoader.js,controls/OrbitControls.js}`.
> **r128 UMD, not ESM**: `index.html` loads them with `<script src=…>`, and the
> `importmap` of ESM versions fails from `file://` in many Chromes.

## Usage per car

1. Export the GLB (does not touch the .blend):
   `blender --background --python export_car_glb.py -- --blend <sessionA.blend> --out <dir>\car.glb`
2. Copy `index.html` + `lib\` alongside `car.glb` (or generate the GLB in the viewer folder).
3. Serve via http (not `file://` — GLB fetch blocked): entry in
   `.claude\launch.json` with `python -m http.server <port> --directory <dir>` + `preview_start`.
4. The human clicks part → INCLUDE/MOVABLE/EXCLUDE (+ reason). Changes live in
   `window.DZ_DELTAS` ({stem: {from, to, reason}}); the agent reads them with
   `javascript_tool` or the human uses "Copy changes (JSON)".
5. Apply deltas to `.blend` headless (move objects whose `source_id` == stem or
   starts with `stem__obj`, update `dz_exclude_reason`/`dz_responsible`),
   reverify sanity and follow normal lane (export → import-blender → check).

## Data contract expected from GLB

Per-node extras (`export_car_glb.py` sets them from custom props):
`source_id` (stable, `stem__objNN` for sub-objects), `dz_coll`, `dz_review`,
`dz_movable_group`, `dz_reason`. Non-mesh parts (EMPTY placeholders) appear
in the list as "(no geometry)".

First real use: sub_wrxsti_04 (2026-08-06), 128 parts / 24.7 MB GLB,
verified with deltas round-trip and zero console errors.
