# CAMBIO-0 — retired required artifacts for a new family B asset

This is a history pointer, not an operative checklist. Nothing listed here is deleted. Existing
vehicles keep their frozen evidence; a new family B asset does not produce or consume these seven
document types in its happy path.

| Retired type | Preserved location / generator | Status after CAMBIO-0 |
|---|---|---|
| F0/freeze specs | `<vehicle-import>/scripts/rip_code_manifest_gate.py:3005,3012`; `<vehicle-import>/work/s39_f0_audit/F0_INVENTORY.md` | SUB_BRZ/in-flight history; manual only. |
| Readiness reports | `<vehicle-import>/scripts/smoke_checklist_f4.md:28-30`; `<vehicle-import>/work/sub_brz_final/*/receipts/offline-readiness.json` | Checklist and receipts preserved; not an import input. |
| Import validation-matrix | `<vehicle-import>/work/_r21_roadmap/inputs/40-validation-matrix.md` | SUB_BRZ traceability; not consumed by the generic runners. |
| Per-run manifests | `<vehicle-import>/scripts/rip_manifest.py:225-254`; sealed SUB_BRZ manifests | Generator and evidence preserved for manual/in-flight use. `Manifest.xml` remains source data. |
| Parallel part lists | `source_inventory.json`, `manifest_decisions.json`; consumers at `<vehicle-import>/scripts/rip_p2_import.py:58-62,141-171` | Legacy consumer preserved. A new B stops before geometry until its later path exists. |
| Separate alignment notes | `<vehicle-import>/work/_gates/s42_door_engine_alignment.json`; `work/sub_brz_final/*/receipts/brz-door-engine-alignment.json` | Technical gate outputs preserved; no separate narrative note is required. |
| Pilot report | `<vehicle-import>/scripts/smoke_checklist_f4.md:32-68` | Manual smoke remains possible; no separate pilot report is generated. |

The exact former DAY-1 checklist and 12-step pipeline are in
`history/pre-cambio-0-canonical-path.md`. RCA remains in
`dayz-vehicles/references/rip-import.md`.
