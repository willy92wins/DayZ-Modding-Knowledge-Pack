# Feature Spec: contractual DayZ model preflight

**Mod / PBO**: `tools/dayz-model-preflight` offline tool
**Date**: 2026-07-25
**Status**: Ready-to-implement
**Plan**: `plans/2026-07-25-04c-dayz-model-preflight.md`
**DPF trace**: F3

## Context / Why

A `.p3d` cannot reveal the scale its author intended, which named selections
are bones, or whether an import transform was supposed to preserve/reverse
face winding. A validator that guesses these facts would produce false green
results. This feature makes the missing truth an explicit, versioned contract
and composes it with py3d's existing structural validation. It reports stable
findings and never repairs the model.

Evidence aliases:

- `PY3D` = `tools/py3d/py3d/__init__.py`;
- `RIP_ORACLE` = private first-party VehicleImport composition/winding gates,
  comparison-only and not redistributed.

## Acceptance Scenarios

1. **Given** a target MLOD and a valid contract with expected dimensions,
   required bone selections and complete source→target face lineage,
   **When** preflight runs, **Then** it returns exit `0`, deterministic JSON
   and zero error findings.
   - **Repro in-game**: binarize and spawn the first-party positive model in
     DayZDiag; observe expected size/orientation and review the delimited RPT
     segment for model/skeleton errors.

2. **Given** the same model with one axis scaled outside tolerance, **When**
   preflight runs, **Then** it emits `PREFLIGHT_SCALE_MISMATCH`, reports
   expected/actual dimensions in metres and returns exit `1`.
   - **Repro in-game**: none; the model is rejected before binarize.

3. **Given** a contract naming required bone selections in exact LOD indices,
   **When** one selection is missing or empty, **Then** preflight emits the
   corresponding stable finding with bone name and LOD index and returns
   exit `1`; unrelated named selections are not guessed to be bones.
   - **Repro in-game**: the positive control is exercised in the final batch;
     missing-bone negatives stay offline.

4. **Given** a complete face map and an affine transform with positive or
   negative determinant, **When** the target preserves or reverses each mapped
   polygon, **Then** preflight derives the expected relation from the
   determinant and accepts only that relation for every face.
   - **Repro in-game**: use the positive transformed fixture as one visible
     surface; verify culling/collision from the intended side in DayZDiag.

5. **Given** absent lineage, duplicate/uncovered face records, non-finite or
   singular transform, geometry that does not match after transform, or a
   one-to-many split outside the v1 contract, **When** preflight runs,
   **Then** it cannot return PASS and emits a contract/evidence error without
   inspecting generated normals as a substitute.
   - **Repro in-game**: none; missing evidence is a pre-binarize hard stop.

6. **Given** any failing contract check, **When** preflight exits, **Then** the
   input model and contract hashes are unchanged and no repaired `.p3d` is
   produced.
   - **Repro in-game**: none; immutability is verified offline by SHA-256.

## Success Criteria

- **SC-001 / contract**: `dayz-model-preflight-v1` validates schema version,
  relative source path, finite 4×4 affine transform, non-empty face map,
  positive finite tolerances, expected dimensions and bone requirements;
  malformed/missing required evidence returns exit `2`.
- **SC-002 / scale**: actual dimensions are `bbox.max - bbox.min` for the exact
  contract LOD index; each axis must differ from `expected_dimensions_m` by
  no more than its `tolerance_m`, reported to at least six decimal places.
- **SC-003 / bones**: every required bone selection exists in each listed LOD
  and contains at least one point or face; the tool does not classify any
  additional selection as a bone.
- **SC-004 / winding relation**: the determinant of the transform's upper 3×3
  is computed by the tool; `det>0` requires cyclic `PRESERVE`, `det<0` requires
  cyclic `REVERSE`, and `det==0` within `1e-12` is invalid evidence.
- **SC-005 / lineage coverage**: every source and target face address occurs
  exactly once, polygon arity matches (`3` or `4`), transformed source
  coordinates match target coordinates within `position_tolerance_m`, and
  missing/duplicate/unsupported-split records cannot PASS.
- **SC-006 / py3d composition**: all `ERROR` findings returned by
  `P3D.validate()` are preserved with their original code/message and cause
  exit `1`; warnings remain visible but do not become errors silently.
- **SC-007 / findings**: output schema contains
  `schema_version`, `verdict`, `model_sha256`, `contract_sha256`, and ordered
  findings with `code`, `severity`, `message`, `lod_index` and optional
  `face_index`/`selection`; identical inputs yield byte-identical JSON.
- **SC-008 / exits**: exit `0` means zero errors and valid complete evidence;
  exit `1` means a valid run with one or more model findings; exit `2` means
  invalid contract/input/unsupported evidence.
- **SC-009 / immutability**: every positive and negative run leaves input
  SHA-256 unchanged and creates no `.p3d`; there is no repair flag or API.
- **SC-010 / oracle parity**: preserve/reverse/mixed, determinant `±1`,
  missing determinant/lineage and partial-coverage fixtures agree with the
  independently existing source-game oracle; its focused baseline remains `27/27`.
- **SC-011 / licensing**: zero source bytes from the private source-game scripts are
  copied into the payload; source map classifies them as comparison evidence.
- **SC-012 / dependency identity**: the tool requires the DayZ py3d fork with
  `IS_DAYZ_FORK == True` and version `>=1.4.0`; an absent, upstream or older
  module returns `PREFLIGHT_PY3D_UNAVAILABLE`, exit `2`, without touching the
  model.

## Scope — Out of scope

- Inferring intended size from an arbitrary model or photographs.
- Discovering the skeleton/model.cfg automatically or treating every named
  selection as a bone.
- One-to-many face splits, triangulation lineage or chunk composition in
  schema v1; those require an explicit later schema revision.
- Judging visual correctness from generated normals, Blender rendering or a
  winding↔normal check produced by the same pipeline.
- Repairing scale, selections, face order, normals or any model bytes.
- ODOL parsing, binarization, PBO build or in-game automation.
- Copying the private source-game implementation into the public pack.

## Assumptions

- **RESOLVED 2026-07-25**: the user approved a consumer-provided contract and
  fail-closed behavior when evidence is absent.
- **RESOLVED by code**: `LOD.bbox()` only measures current model bounds and
  cannot supply intended scale; `PY3D:1345-1360`.
- **RESOLVED by data model**: py3d exposes named selections but no universal
  bone taxonomy; bone identity must be supplied by the consumer.
- **RESOLVED by prior art**: determinant sign and source-face lineage are
  required for a non-tautological import winding gate;
  `RIP_ORACLE/scripts/winding_lineage_gate.py:46-135`.

## Forward Contract

| Consumer | Symbol it reads | Kind | Verify status |
|---|---|---|---|
| preflight | `P3D.validate(normals_budget=32768, normals_severity="WARN")` | existing py3d API | `[EXACT] PY3D:2079-2119` |
| preflight | `LOD.bbox()` | existing py3d API | `[EXACT] PY3D:1345-1360` |
| tests/consumers | `P3D.get_lod(name)` | existing py3d API | `[EXACT] PY3D:1878-1894` |
| oracle comparison | `winding_lineage_gate(source_mlod, target_mlod, manifest)` | private oracle API | `[EXACT] RIP_ORACLE/scripts/winding_lineage_gate.py:76-135; not payload` |
| CLI/library | `dayz-model-preflight-v1` | new JSON contract | `[DESIGN] defined below` |
| Python callers | `run_preflight(model_path, contract_path) -> dict` | new pure result API | `[DESIGN] no mutation; deterministic result` |
| CLI | `python -m dayz_model_preflight check MODEL --contract CONTRACT --json OUTPUT` | new command | `[DESIGN] exits 0/1/2 per SC-008` |
| downstream gates | finding codes `PREFLIGHT_*` | new machine contract | `[DESIGN] closed list in Error Cases` |

No engine API is used. Existing py3d and oracle methods were opened and
verified; the private oracle remains outside the payload.

## `dayz-model-preflight-v1` Contract

The JSON object contains:

- `schema_version`: literal `dayz-model-preflight-v1`;
- `scale`:
  - `lod_index`: non-negative integer;
  - `expected_dimensions_m`: three positive finite numbers;
  - `tolerance_m`: one positive finite number or three positive finite numbers;
- `bones`:
  - `requirements`: non-empty list of
    `{lod_index: int, selections: [non-empty unique strings]}`;
- `winding`:
  - `source_model`: relative path resolved against the contract directory,
    without `..` escape;
  - `transform`: finite 4×4 row-major affine matrix whose last row is
    `(0,0,0,1)` within `1e-12`;
  - `position_tolerance_m`: positive finite number;
  - `faces`: non-empty list of
    `{source:{lod_index,face_index}, target:{lod_index,face_index}}`.

All three sections are required in v1. A consumer needing only a subset must
create a later explicitly scoped schema; omission is not treated as PASS.

## Data / Lifecycle

- The tool reads source model, target model and contract once, hashes their
  bytes and performs no write to either input.
- Relative `source_model` resolution is fail-closed against path escape.
- Contract validation and full lineage coverage finish before verdict PASS.
- The result is a derived JSON artifact; it contains no timestamp or absolute
  path and can be safely regenerated.
- No persistent binary/network schema changes. Rolling back only removes the
  checker; model files remain unchanged and readable.

## Error Cases

| Code | Required trigger/result |
|---|---|
| `PREFLIGHT_CONTRACT_INVALID` | malformed schema/value/path; exit 2 |
| `PREFLIGHT_MODEL_UNREADABLE` | target/source MLOD cannot be parsed; exit 2 |
| `PREFLIGHT_PY3D_UNAVAILABLE` | DayZ fork absent, upstream or older than 1.4.0; exit 2 |
| `PREFLIGHT_LOD_MISSING` | a contract LOD index does not exist in its model; exit 1 |
| `PREFLIGHT_PY3D_ERROR` | wrapped py3d `ERROR`; exit 1 |
| `PREFLIGHT_SCALE_MISMATCH` | any dimension outside tolerance; exit 1 |
| `PREFLIGHT_BONE_SELECTION_MISSING` | required name absent in required LOD; exit 1 |
| `PREFLIGHT_BONE_SELECTION_EMPTY` | required selection has zero points and faces; exit 1 |
| `PREFLIGHT_WINDING_EVIDENCE_MISSING` | empty/incomplete/duplicate face map; exit 2 |
| `PREFLIGHT_WINDING_TRANSFORM_INVALID` | non-affine/non-finite/singular transform; exit 2 |
| `PREFLIGHT_WINDING_GEOMETRY_MISMATCH` | transformed source polygon cannot match target; exit 2 |
| `PREFLIGHT_WINDING_UNSUPPORTED_SPLIT` | arity differs or one-to-many evidence supplied; exit 2 |
| `PREFLIGHT_WINDING_RELATION_MISMATCH` | actual cyclic order differs from determinant expectation; exit 1 |

## Observability

- JSON verdict is `PASS`, `FAIL` or `INVALID`, matching exits `0`, `1`, `2`.
- Findings are sorted by severity, code, LOD, face and selection.
- Every finding includes expected and observed values where applicable.
- Hashes identify the exact model/contract without exposing their paths.
- The CLI prints the JSON result to stdout unless `--json` is supplied; stderr
  is reserved for unexpected process failures.

## Verification Plan

| Criterion | Verification | Where |
|---|---|---|
| SC-001 | JSON Schema positive/negative fixtures and path-escape cases | offline |
| SC-002–SC-003 | synthetic py3d models with scale and selection mutations | offline |
| SC-004–SC-005 | preserve/reverse/mixed/partial/duplicate face maps | offline |
| SC-006 | py3d finding propagation fixture | offline |
| SC-007–SC-009, SC-012 | golden JSON, dependency/exit matrix and SHA-256 before/after | offline |
| SC-010 | existing source-game focused suite + semantic comparison table | offline |
| positive runtime | binarize/spawn one first-party accepted model | final DayZDiag batch |

## Implementation Slices

1. Contract schema, strict loader and result/finding types.
2. Scale and required-bone validators.
3. Generic affine face-lineage/winding validator.
4. py3d composition, deterministic CLI and mutation suite.
5. Docs, source map, domain-skill references and promotion.

Each slice starts with failing positive/negative fixtures. Missing or
unsupported lineage never degrades to a warning/PASS.

## Open Questions / NEEDS CLARIFICATION

None. The consumer-contract architecture and no-repair boundary were approved
by the user on 2026-07-25.

## Spec Quality Checklist

- [x] CHK001 Every Success Criterion is measurable.
- [x] CHK002 No vague adjective is used as a criterion.
- [x] CHK003 Numeric criteria include units/tolerances/counts.
- [x] CHK004 Every scenario is Given/When/Then with concrete repro or an
  explicit pre-binarize reason to remain offline.
- [x] CHK005 Every criterion/scenario has a verification path.
- [x] CHK006 Offline-verifiable checks remain offline.
- [x] CHK007 Every assumption is marked and resolved.
- [x] CHK008 Correctness-deciding scale/bone/winding inputs are explicit.
- [x] CHK009 No template placeholder remains.
- [x] CHK010 Existing Forward-Contract APIs have `path:line`; new contracts
  are `[DESIGN]`.
- [x] CHK011 Existing py3d/oracle methods were opened and verified.
- [x] CHK012 No `[UNVERIFIED]` dependency remains.
- [x] CHK013 Out-of-scope is explicit.
- [x] CHK014 Terms are stable: contract, source, target, lineage and relation.
- [x] CHK015 Criteria and scenarios do not contradict.
- [x] CHK016 No data-critical persistence/progression/admin flow is added;
  immutability and rollback are explicit.

**Result: 16/16 PASS.**
