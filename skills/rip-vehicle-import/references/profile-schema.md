# profiles/<car>.json — schema campo a campo (estado 2026-07-11)

> Fuente de verdad de un coche en el pipeline. Loader común: `load_profile()` en
> `VehicleImport\scripts\rip_p3_structural.py`. El `brz.json` NO es plantilla limpia:
> mezcla contrato fleet con `exceptions` quirúrgicas aprobadas in-game (E_flip, C1_safe,
> sunk_keep_z, paleta cabina) — para el coche #2 copiar SOLO el contrato, nunca las
> excepciones. Campos marcados (s1) los introduce la spec
> `VehicleImport\plans\2026-07-11-s1-frontend-intake.md` (verificar merge antes de usarlos).

## Identidad y paths

| Campo | Qué es | Consumidor |
|---|---|---|
| `name` | token corto del coche (`brz`) — prefija outputs de work | todos |
| `shell_path` | `.p3d` DESPLEGADO (OneDrive, árbol del mod) — solo lectura/transplant | repaint, gates, transplant |
| `struct_shell_in` | shell de WORK que alimenta el builder estructural | rip_p3_structural |
| `out_path` | `.p3d` full de salida del builder en work | rip_p3_structural |
| `report_path` | JSON del build estructural | rip_p3_structural, gates |
| `geo_npz` / `geo_meta` | geometría+MAT npz/json de la fase 2 (group) | builder v2, repaint |
| `locators_path` | `Locators.xml` del rip (memoria/dims) | rip_p3_structural |

## Transform y físico

| Campo | Qué es |
|---|---|
| `transform{LIFT, hub_lift, contact_y, wheel_hub_rip_y}` | deriva `Y0 = (wheel_R − wheel_hub_rip_y) + LIFT`; `hub_lift` DESACOPLA el hub del lift del cuerpo (rally lift ≠ hub: hub_lift=0 deja la rueda al knuckle) |
| `WHEEL_R` | radio de la rueda MONTADA (== radio real del item; 0.3637 vs 0.34 montado costó "ruedas arriba") |
| `TARGET_MASS` | masa objetivo (kg) para `#Mass#` en Geometry — cross-checked vs stats públicos FH6 |
| `seats{driver_x,y,z}` | ancla de asientos |

## Builder visual y estructura

| Campo | Qué es |
|---|---|
| `builder{}` | políticas del builder v2: `interior_out` (prox_int), `budget` (merge de clases con LOD autorado; micro-clases VERBATIM + AUTO-FULL por inflación), `negate_classes`, `skip`, `glass_int_policy` |
| `interior{viewpilot_subset, viewpilot_full}` | interior único (patrón prox_int): full → res 1.0, subset ≤16k → res 1100; `viewpilot_full` = decisión BRZ (lag conocida), coche #2 = subset |
| `viewpilot_parts` | DEPRECATED (Task 11 R2) — no usar |
| `sedanwheel`, `crew_driver`, `crew_cargo` | paths de proxy vanilla (SIN `.p3d`) |
| `shadow{max_faces}` | budget del shadow LOD (≤5000; dissolve 40°) |
| `dual_tag` | componentNN dual-tag ON (obligatorio; OFF solo para la fixture negativa) |
| `collision{chassis, dmgzones, seat_con, refill, crew}` | override exacto de cajas (BRZ) o fallback bbox-bands (otras formas); dmgzones == hitpoints == config.componentNames |

## Gates

| Campo | Qué es |
|---|---|
| `gates{import_report, gb_paths, gbplus_new, gbplus_ref, bands}` | wiring de gates_v2: G0 multi-ancla (import_report OBLIGATORIO, fail-closed), Gb/Gb+ winding, bandas por-profile |
| `gate{proxy_dir, chunk_prefix, body_selections, exclude_selections, raycast, twin_eps_mm}` | gate_car (see-through): filtro por selección de carrocería + twin-test + params raycast COMPLETOS |
| `artifact_gates{perf_budget, lod_semantics, interior_rayfan, glass_occ, winding}` | los 8 gates fail-loud del ledger; calibraciones SIEMPRE evidence-scoped (nunca disable); BRZ lleva overrides aprobados (visual 231k WARN-only) que el coche #2 NO hereda |

## (s1) Bloques nuevos — pendientes de la tanda A/B

| Campo | Qué es |
|---|---|
| `source{car_root, game_path, importer, manifest_dir, work_stem, import_report, blender_exe}` | rutas del rip y derivación de TODOS los paths de work del front-end (`<stem>_p2_raw.blend`, `<stem>_p2_geo.npz`, `<stem>_material_map.json`); clave ausente = FAIL nombrando la clave |
| `intake{budgets{visual_total_faces_max, viewpilot_resolved_max, shadow_faces_max, uv_uniq_min, dup_face_rate_max}, ladder_policy}` | presupuestos de ENTRADA + política `authored_lod_by_budget` → `lod_plan.json` (pieza→LOD autorado); FAIL si ningún plan cabe |

## Reglas de uso

1. Ausencia de clave requerida = FAIL con nombre de clave. Nada de defaults silenciosos.
2. Las calibraciones/`exceptions` van con nota de evidencia (`*_note`) y quedan
   profile-scoped: son historia del coche, no doctrina del pipeline.
3. Cambios de schema → actualizar ESTE doc en el mismo commit (es el contrato que lee
   el coche #N).
