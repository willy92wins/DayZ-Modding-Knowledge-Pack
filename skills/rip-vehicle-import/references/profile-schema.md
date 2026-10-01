# profiles/<car>.json — legacy/in-flight schema (status 2026-07-11)

> Source of truth for a car in the pipeline. Common loader: `load_profile()` in
> `<vehicle-import>\scripts\rip_p3_structural.py`. `brz.json` is NOT a clean template:
> it mixes fleet contract with surgical `exceptions` approved in-game (E_flip, C1_safe,
> sunk_keep_z, cabin palette) — for car #2 copy ONLY the contract, never the
> exceptions. Fields marked (s1) are introduced by spec
> `<vehicle-import>\plans\2026-07-11-s1-frontend-intake.md` (verify merge before using them).

>
> **CAMBIO-0 (2026-08-05):** this schema preserves wiring of already started cars and
> manual tools. It is not a template for the next B. In particular,
> `source_inventory`, `manifest_decisions`, per-run receipts and `artifact_gates` outside
> B1-B6 are not inputs of the new happy path. Existing consumers are not modified here;
> the new B stops before geometry as long as its downstream path does not exist.

## Identity and paths

| Field | What it is | Consumer |
|---|---|---|
| `name` | short token of car (`brz`) — prefixes work outputs | all |
| `shell_path` | DEPLOYED `.p3d` (OneDrive, mod tree) — read-only/transplant | repaint, gates, transplant |
| `struct_shell_in` | WORK shell feeding structural builder | rip_p3_structural |
| `out_path` | full output `.p3d` of builder in work | rip_p3_structural |
| `report_path` | structural build JSON | rip_p3_structural, gates |
| `geo_npz` / `geo_meta` | phase 2 geometry+MAT npz/json (group) | builder v2, repaint |
| `locators_path` | rip `Locators.xml` (memory/dims) | rip_p3_structural |

## Transform and physics

| Field | What it is |
|---|---|
| `transform{LIFT, hub_lift, contact_y, wheel_hub_rip_y}` | derives `Y0 = (wheel_R − wheel_hub_rip_y) + LIFT`; `hub_lift` DECOUPLES hub from body lift (rally lift ≠ hub: hub_lift=0 leaves wheel at knuckle) |
| `WHEEL_R` | radius of MOUNTED wheel (== real item radius; 0.3637 vs 0.34 mounted cost "wheels up") |
| `TARGET_MASS` | target mass (kg) for `#Mass#` in Geometry — cross-checked vs public FH6 stats |
| `seats{driver_x,y,z}` | seats anchor |

## Visual builder and structure

| Field | What it is |
|---|---|
| `builder{}` | v2 builder policies: `interior_out` (prox_int), `budget` (merge classes with authored LOD; micro-classes VERBATIM + AUTO-FULL by inflation), `negate_classes`, `skip`, `glass_int_policy` |
| `interior{viewpilot_subset, viewpilot_full}` | single interior (prox_int pattern): full → res 1.0, subset ≤16k → res 1100; `viewpilot_full` = BRZ decision (known lag), car #2 = subset |
| `viewpilot_parts` | DEPRECATED (Task 11 R2) — do not use |
| `sedanwheel`, `crew_driver`, `crew_cargo` | vanilla proxy paths (WITHOUT `.p3d`) |
| `shadow{max_faces}` | shadow LOD budget (≤5000; 40° dissolve) |
| `dual_tag` | componentNN dual-tag ON (mandatory; OFF only for negative fixture) |
| `collision{chassis, dmgzones, seat_con, refill, crew}` | exact box override (BRZ) or bbox-bands fallback (other shapes); dmgzones == hitpoints == config.componentNames |

## Legacy/in-flight gates

| Field | What it is |
|---|---|
| `gates{import_report, gb_paths, gbplus_new, gbplus_ref, bands}` | gates_v2 wiring: multi-anchor G0 (import_report MANDATORY, fail-closed), Gb/Gb+ winding, per-profile bands |
| `gate{proxy_dir, chunk_prefix, body_selections, exclude_selections, raycast, twin_eps_mm}` | gate_car (see-through): filter by body selection + twin-test + COMPLETE raycast params |
| `artifact_gates{perf_budget, lod_semantics, interior_rayfan, glass_occ, winding}` | the 8 fail-loud gates of ledger; calibrations ALWAYS evidence-scoped (never disable); BRZ has approved overrides (visual 231k WARN-only) that car #2 DOES NOT inherit |

## (s1) Legacy blocks — do not copy to next B

| Field | What it is |
|---|---|
| `source{car_root, game_path, importer, manifest_dir, work_stem, import_report, blender_exe, material_type_overrides?}` | rip paths and derivation of ALL front-end work paths (`<stem>_p2_raw.blend`, `<stem>_p2_geo.npz`, `<stem>_material_map.json`); `material_type_overrides` is an optional list of `{part, mat_name, mat_path, type}`; each entry must match exactly one visible mesh or map fails closed |
| `intake{budgets{visual_total_faces_max, viewpilot_resolved_max, shadow_faces_max, uv_uniq_min, dup_face_rate_max}, ladder_policy}` | INTAKE budgets + `authored_lod_by_budget` policy → `lod_plan.json` (part→authored LOD); FAIL if no plan fits |

## Usage rules

1. Missing required key = FAIL with key name. No silent defaults.
2. Calibrations/`exceptions` include evidence note (`*_note`) and remain
   profile-scoped: they are car history, not pipeline doctrine.
3. Schema changes → update THIS doc in the same commit (it is the contract read
   by car #N).
4. [EXACT][CLAIM-R21-RIP-MATERIAL-OVERRIDE-SCHEMA] `material_type_overrides` does
   not substitute global folder classification. Preserves `source_type`,
   records `override=source.material_type_overrides` and is only admitted with
   exact identity `part + mat_name + mat_path`.
