---
name: rip-vehicle-import
description: "Use when: ripped racing-game Grub, rip vehicle import, non-Forza Grub rip. Same family-B template as forza-to-dayz (that name survives). Not ForzaTech/ForzaDayZ: forza-to-dayz; not vanilla CarScript: dayz-vehicles."
---

# Ripped racing-game vehicle → DayZ — family B adapter (CAMBIO-2)

> Day-0 critical path for the next source game Grub car, proxy-split and with moving parts.
> If the asset is in flight, use its frozen runbook. If an applicable entry is missing: **STOP**.
> The previous runbook is in `history/pre-cambio-1-family-b-runbook.md` and is not executable.

## Seis deltas obligatorios

| Field | Family B contract |
|---|---|
| Axes / units | Source `<vehicle-import>\rip\media\cars\<car>\`. Net transform `DayZ=(-Fx, Fy+Y0, -Fz)`, meters, without permuting axes and `det=+1`; `Y0` is measured and sealed in the ledger entry, never inherited from another car. Contract verified in `<vehicle-import>/tools/fit_transform.py:5-15,107-108`. |
| Monolithic vs proxy-split | Host/shell with structural LODs; visual parts exceeding budget and attachments are instantiated as proxy submodels. Do not use a monolith as a silent fallback. |
| Moving parts | Doors, hood, trunk and wheel/item retain their own identity, measured pivot and item↔slot↔proxy wiring; they are not merged into the shell. |
| Frame authority | Donor/golden frame rules for structure; source frame rules for imported visuals. Every conversion is tested with independent anchors. Never validate a part against a point produced by the same transform. |
| Golden | `<vehicle-import>\goldens\family-b\civiliansedan\r1\q1-structure.json`, revision `family-b-civiliansedan-r1`, 3,219,555 bytes, SHA-256 `3174D511F2761EE2F4E003694F566D7D92180BB30CE3479A8FA5F1EAA7C45AEB`; donor hashes in `golden-manifest.json`. Structural, not clone-ready: empty `mass_array` and proxy warnings require STOP before copying per-vertex mass or declaring full parity. |
| Checks allowlist | Only B1-B7 from the following table. No legacy gate, snapshot, or workspace copy expands the lane. |

## Source door inventory (measured 2026-08-06 on the library of 651 rips)

- Bilateral door container can come from EITHER side: the BRZ provides only `doorlf`, `SUB_WRXSTi_04` provides only `doorRF_a`, `FOR_BroncoRaptor_22` mixes sides (`doorLF_a`, `doorLF_b`, `doorLR_b`, `doorRF_a`). The real rule is "a single side per container, whichever it is" — do not assume LF when classifying, counting doors, or synthesizing the mirror.
- Variants `_a`/`_b` of the same door container = interchangeable platforms (removable Bronco doors): session A chooses ONE variant as INCLUDE and justifies the rest as EXCLUDE.
- jamb/handle/card of a door WITHOUT its `door<side>_<x>` panel = door merged into the bodywork (`BMW_M4_14`, `FOR_2_GT40_66`): this is not another naming convention; the openable part does not exist in the rip.

## Single ledger entry and identity checkpoint

- Full template: `<vehicle-import>\contracts\asset-contract.json`; review schema: `<vehicle-import>\contracts\asset-contract.schema.json`.
- The per-asset copy is named exactly `asset-contract.json`; it is the third and final day-0 file. It replaces parallel inventory/decisions: do not produce `source_inventory.json`, `manifest_decisions.json`, separate tombstones or any other list.
- Session A/B export: the human runs `<vehicle-import>\scripts\blender_export_asset_contract.py` on collections `DZ_INCLUDE` / `DZ_EXCLUDE` / `DZ_MOVABLE`. The JSON is import evidence; afterwards the ledger entry rules.
- Single primitive: `<vehicle-import>\scripts\asset_contract_checkpoint.py`, version declared in stdout. Copying it to a run is forbidden.
- Session A/B is imported with `import-blender`; after converting, `check` is the only `capability=LINEAGE_CHECKPOINT`.
- `PASS` allows continuing only within the issued capability. `DECISION_REQUIRED` returns to the human. `TOOL_FAIL` blocks and does not authorize touching geometry nor is it recorded as an asset failure.
- Coverage is N:M: every `INCLUDE`/`MOVABLE` appears in a `derived_from` within an authorized operation; each justified `EXCLUDE` is the tombstone. Source/output equality is not required.

## Allowlist B1-B6 and canonical location

| ID | Contract / location | Status for a new B |
|---|---|---|
| `B1_BINARIZE_LOAD` | Three-state oracle `PASS / CAPACITY_FAIL / OTHER_FAIL`: `<vehicle-import>\scripts\p3d_vertex_gate.py`. | Available; demonstrated authority with known-good, `CAPACITY_FAIL`, `OTHER_FAIL` and residual ODOL. |
| `B2_DEPLOY_IDENTITY` | `<vehicle-import>\scripts\rip_build_identity.py --stage` (`:420-442`). | Available. |
| `B3_VEHICLE_PARITY` | `<vehicle-import>\tools\verify_rip_car.py` in contractual mode (`:1538-1546,1734-1736,1817`), never legacy `build_checks()`. | Available. |
| `B4_CREW_ACTIONS` | `<vehicle-import>\scripts\rip_action_contract_gate.py` via its real CLI (`:732-742`). | Available. |
| `B5_DOOR_ALIGNMENT` | `<vehicle-import>\scripts\rip_door_engine_alignment_gate.py` via its real CLI (`:513-515`). | Available. |
| `B6_NATIVE_DOOR` | `<vehicle-import>\scripts\rip_native_door_contract_gate.py` via its canonical CLI (`--profile`, `--mlod-stage`, `--odol-stage`, `--debinarizer-scripts`, `--out`); W2 (`--matrix-authority` + `--matrix-out`) is an optional extension, not the base authority. | Available; family B authority demonstrated with non-BRZ profile, vanilla golden, structural mutation and instrumental failure. |
| `B7_VISUAL_SIGNOFF` | Render: `<vehicle-import>\scripts\rip_assembled_viewer.py`. Verdict: `<vehicle-import>\scripts\rip_visual_signoff.py` (`--render` / `--verdict` / check with `--out`). | Available; debuted with sub_wrxsti_04 on 2026-08-16, when the user's eye found in minutes four defects that B1-B6 had passed as good. |

**Single location:** each primitive/gate is executed only from its canonical path above. It is forbidden
to copy it to `work\`, `sNN\`, `_validation\`, `.superpowers\sdd\` or any run workspace.
Existing copies are evidence snapshots: they are preserved, can be hashed, and **are not executed**.
If the canonical path is missing, the result is STOP, never "use the newest copy".

## Classification viewer (session A review without Blender)

`assets/classify-viewer/` — Three.js viewer to review/reclassify session A by click
(GLB with extras + deltas that the agent applies to the `.blend` via headless script). Advisory:
authority remains `.blend` → export → ledger entry. Usage and data contract in its `README.md`.
Debuted with sub_wrxsti_04 (2026-08-06).

## B7 — visual signoff before build (debuted 2026-08-16, sub_wrxsti_04)

B1-B6 measure names, face counts, hashes and logical matrices. **Neither can see a color
nor the orientation of a proxy.** On 2026-08-16 the user opened the WRX in a viewer for the first
time and found in minutes four defects that the entire allowlist had passed as good:

- 64% of the car in ONE material and the entire interior in another — the import recorded
  `material_map: null` and sent 37 named parts (badges, mirrors, exhaust, jambs,
  skirts, underbody, suspension arms) to the bodywork paint bucket;
- the four wheel proxies written with the IDENTITY matrix, all four identical, when
  vanilla writes TWO mirrored frames, one per side. Same frame + mirrored anchors =
  one side mounted backwards by mathematical obligation;
- 176 mm vanilla sedan wheel instead of the car's wheel;
- a bodywork color that no one had verified.

The tool existed halfway: `rip_visual_sheet.py` already renders artifacts and its
own docstring says "renders, does not judge" — but it draws geometry in GRAY and separately, so
it could not show any of the four. B7 is the other half.

**How to run it**, in this order and without skipping the middle. ABSOLUTE PATHS: this project
has TWO trees — `<vehicle-import>` (scripts, profiles, work) and
`C:\Users\<you>\OneDrive\Documentos\DayZ Projects` (= `P:\`, the deployed mod) — and a
relative command only runs from one. The actual debut of B7 failed with
`can't open file ... No such file or directory` precisely because of that.

```
set FZ=<vehicle-import>

python "%FZ%\scripts\rip_visual_signoff.py" --car "%FZ%\profiles\<car>.json" ^
       --render "%FZ%\work\<car>_viewer.html"
   REM  (el humano lo abre y lo mira -- este paso no lo puede hacer el agente)
python "%FZ%\scripts\rip_visual_signoff.py" --car "%FZ%\profiles\<car>.json" ^
       --verdict pass^|fail --by "human:<quien>" --note "<que viste>"
python "%FZ%\scripts\rip_visual_signoff.py" --car "%FZ%\profiles\<car>.json" ^
       --out "%FZ%\work\_gates\b7.json"
```

**Three rules that make it a gate and not a rubber stamp:**

1. **The render must be ASSEMBLED and with materials.** Shell + chunks + interior + removables in their
   proxies + wheels in theirs, with the colors of the rvmats that ship. Floating doors
   and inverted rims ONLY appear when assembled; not in loose parts and in gray.
2. **The verdict is tied to the bytes.** It carries the sha256 of each artifact that was viewed, and the
   check hashes them again. Rebuilding a part renders the signoff STALE, not old, and the
   gate turns red until someone looks again. It is the same lesson already paid by
   `positive_control`: a control pointing to a path that the next build overwrites is
   a tautology.
3. **Fail-closed.** Without a verdict it is `NO_EVIDENCE`, never PASS. A verdict covering fewer
   artifacts than the car currently has is FAIL: a part that was not
   shown cannot be approved.

Signing on behalf of the human invalidates the entire gate. The `--verdict` command exists so that the
signature has a name and date; using it instead is forging it.

Two traps encapsulated by the render, paid on the same day: DayZ is LEFT-HANDED and three.js RIGHT-HANDED,
so passing the coordinates as-is **is a reflection** — a mirrored car looks
perfectly plausible until you read a badge, and the calibrator is brand text. And
proxy placement is `vertices @ effective_frame.T + anchor` with
`effective_frame = MLOD_PROXY_CONVENTION_FRAME @ raw_frame`
(`rip_detachable_doors.py:55-61,171-176`): deducing it by eye from the triangle placed each door
one meter from the car.

## Single symptom → cookbook index

| Symptom | Moved cookbook |
|---|---|
| Missing get-in | `cookbooks/family-b/get-in-ausente.md` |
| `wheelPresent=0` | `cookbooks/family-b/wheelpresent-0.md` |
| White car / missing texture | `cookbooks/family-b/coche-blanco.md` |
| Invisible attachment with intact sim | `cookbooks/family-b/attach-invisible.md` |
| Missing door radial | `cookbooks/family-b/radial-puerta-ausente.md` |

Do not create `INDEX.yaml`, a cookbook router or any other symptom→cookbook table. This is the only index.

## Secuencia day-0

1. Open this adapter from the `dayz-vehicles` selector.
2. Open a single ledger entry `asset-contract.json`, created from the canonical template, and verify source revision, `Y0`, golden revision and status.
3. The human classifies in Blender; the primitive captures hash/inventory and imports lists/transforms into that same ledger entry. The agent neither opens nor maintains schema/export as state documents.
4. Check canonical presence of B1-B6 without executing snapshots. **The B1-B7 allowlist is complete; any canonical absence results in STOP.**
5. Convert while preserving provenance and require `LINEAGE_CHECKPOINT=PASS`; the other two states block.
6. Execute only the allowlist; the final live test remains separate from preflight.
7. If one of the five symptoms appears, open only its cookbook. For other symptoms, STOP and explicit diagnosis.

## Step 5 conversion rail (SP-363; debuted sub_wrxsti_04, 2026-08-06)

The car profile declares `source.asset_contract` (path to ledger entry) — this activates the contract
mode of `rip_p2_import.py`: INCLUDE/SHADOW lists projected from the ledger entry by
`scripts/rip_contract_source.py` (fail-closed per-container homogeneity), never with
`manifest_decisions.json`, far-shell deferred to human classification, G0 anchors per
profile (`source.g0_anchors` = pairs [part, locator]). The three commands, in order:

```
blender --background --factory-startup --python-exit-code 1 --python scripts\rip_p2_import.py -- --car profiles\<car>.json
python scripts\asset_contract_checkpoint.py import-conversion --contract <ficha> --import-report <report> --contact-y-m C --hub-y-m H --lift-m L --y0-m Y0 --responsible "machine:rip_p2_import@<car>" --approved-by "human:<quien>" --out <ficha>
python scripts\asset_contract_checkpoint.py check --contract <ficha>
```

- `--python-exit-code 1` is MANDATORY: without it Blender returns exit 0 even if the python script
  dies (a G0 FAILED passed as "completed" at debut). Applies to ALL headless Blender
  launches, not just this step.
- `import-conversion` validates the derivation `Y0 == contact − hub + lift`, the
  MULTISET correspondence of object names per container (report vs inventory, blind to Blender
  `.NNN` suffixes) and that no excluded part was imported; seals 1:1 lineage `AXIS_UNIT_TRANSFORM` +
  frame, and is seal-once (retry = `CONVERSION_ALREADY_IMPORTED`).
- The new profile starts MINIMAL (see `profiles/wrx.json`): source block + anchors + measured
  transform + `WHEEL_R` == mounted wheel radius. Copying keys from `profiles/brz.json` is
  forbidden: they are scars specific to that car.
- Known downstream landmines (next surgery): `rip_p2_group.py:33` IN_BLEND hardcoded
  BRZ; `rip_p3_structural.py:715` defaults to `brz.json`.
