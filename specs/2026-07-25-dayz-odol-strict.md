# Feature Spec: strict ODOL read-only adapter

**Mod / PBO**: `tools/dayz-odol-strict` offline tool + legal fixtures
**Date**: 2026-07-25
**Status**: Ready-to-implement
**Plan**: `plans/2026-07-25-04d-dayz-odol-strict.md`
**DPF trace**: F4

## Context / Why

The installed ODOL backend can recover useful v53–v55 anatomy but is
deliberately permissive: it accepts a broad version range, can allocate from an
unbounded signed LOD count, returns partial models and mishandles container
offsets. Its Python source also ports a repository with no published license,
so it cannot be copied into this MIT pack. This feature adds an original
strict adapter that validates/slices before invocation and validates every
backend result afterward; the recovery reader remains an external dependency.

Evidence aliases:

- `ODOL_BACKEND` =
  `VAULT/AI/20_Knowledge/skills-drafts/dayz-p3d-debinarizer-paridad/dayz-p3d-debinarizer/scripts`;
- `BISDLL` = `ScripyZz/BisDLL-Arma-3`, external no-license source;
- `PACK` = this repository.

## Acceptance Scenarios

1. **Given** the three user-authorized fixtures ODOL v53, v54 and v55,
   **When** strict inspect runs with the pinned backend manifest, **Then** all
   declared LODs parse, every actual end equals its declared end, no LOD/error
   is missing and deterministic anatomy JSON is emitted.
   - **Repro in-game**: none; this is a read-only parity tool. The corresponding
     first-party models are separately known to load, but F4 does not claim to
     replace an engine load.

2. **Given** a valid fixture directly and embedded after 16 or 4096 prefix
   bytes, **When** strict inspect runs, **Then** the three summaries are
   semantically identical except `container_offset`, and all raw LOD offsets
   are interpreted relative to the sliced ODOL payload.
   - **Repro in-game**: none; container handling is an offline byte-boundary
     contract.

3. **Given** a backend result with one `lod_errors` entry, `None` LOD,
   mismatched count/table length, OOB/overlapping interval or
   `actual_end != declared_end`, **When** strict validation runs, **Then** it
   rejects the entire model with exit `2` and emits no partial PASS anatomy.
   - **Repro in-game**: none; partial recovery remains available only through
     the external backend and never satisfies F4.

4. **Given** version outside `53|54|55`, signed `n_lods <= 0`, `n_lods > 64`,
   truncated resolution bytes, multiple plausible ODOL signatures or a
   backend whose pinned files drift, **When** inspect is requested, **Then**
   the adapter rejects before invoking the backend.
   - **Repro in-game**: none; these inputs are blocked before parser allocation.

5. **Given** two strict summaries, **When** `diff` compares an identical copy,
   **Then** it returns exit `0` and zero findings; a directed mutation of
   resolution, selection set, named property, proxy count or LOD raw hash
   returns exit `1` with the exact stable field path.
   - **Repro in-game**: none; self-diff/parity is deterministic offline.

## Success Criteria

- **SC-001 / versions**: only ODOL versions `53`, `54` and `55` are accepted;
  any other version returns `ODOL_VERSION_UNSUPPORTED`, exit `2`.
- **SC-002 / preallocation guard**: the adapter reads magic/version/signed
  `n_lods` from the sliced header before backend import, requires
  `1 <= n_lods <= 64`, and requires at least `12 + 4*n_lods` payload bytes.
- **SC-003 / measured limit**: the default `64` is documented against the
  2026-07-25 local census of `13,108` v53–v55 files whose maximum observed
  `n_lods` is `15`; a higher explicit limit is never selected silently.
- **SC-004 / container**: exactly one plausible ODOL candidate is accepted;
  direct/16-byte/4096-byte variants produce identical version, resolutions,
  LOD anatomy and raw LOD SHA-256 values.
- **SC-005 / backend identity**: every backend file named by the versioned
  manifest matches its SHA-256 before import; missing/drifted files return
  `ODOL_BACKEND_MISSING|ODOL_BACKEND_DRIFT`, exit `2`.
- **SC-006 / completeness**: backend `version`, `n_lods`, resolutions, LOD
  list, start/end/actual-end tables all match the preflight count; there are
  zero `lod_errors` and zero `None` LODs.
- **SC-007 / boundaries**: each interval satisfies
  `0 <= start < end <= payload_size`, intervals do not overlap when sorted by
  start, and every `actual_end == end`; any failure rejects the whole model.
- **SC-008 / anatomy output**: schema `dayz-odol-strict-v1` contains input
  SHA-256, payload SHA-256, container offset, backend manifest id/hash,
  version, LOD count/resolutions and per-LOD declared interval/raw hash,
  vertex/face/normal/material/proxy/selection/property counts plus selection
  names and named properties.
- **SC-009 / determinism/privacy**: identical bytes/backend produce
  byte-identical sorted JSON with no timestamp, username or physical path.
- **SC-010 / fixtures**:
  - v53 `AmmoBox1.p3d`, SHA-256
    `c2ba93cc05d3d47df5400c6f5f68aef928687eef06ce38747340927cd39e96ba`,
    parses `1/1` LOD;
  - v54 `RugerMarkIV_Optic.p3d`, SHA-256
    `ccdb62e78661f2a0d98e5d5ca8844a8a7f0ae5242c2e1f403530d01d0ef037f9`,
    parses `1/1` LOD;
  - v55 `lfquad_body_preC11_odol.p3d`, SHA-256
    `9dd2b16a70001b5e6513bf26da0b24db6c2a92c09f6fa09ae9aab20f77ef19d3`,
    parses `5/5` LODs.
- **SC-011 / diff**: self-diff has zero findings/exit `0`; each directed
  anatomy mutation produces exactly one field-addressed finding/exit `1`;
  invalid summary input returns exit `2`.
- **SC-012 / licensing**: no file or substantial source fragment from
  BISDLL/ODOL_BACKEND enters Git; the source map and notices record them only
  as external backend/oracle evidence.

## Scope — Out of scope

- Shipping, relicensing or modifying the external recovery backend.
- ODOL→MLOD conversion, recovery PASS, writer ODOL or repair.
- Claiming full ODOL compatibility outside v53/v54/v55.
- Accepting partial LODs because “enough anatomy” survived.
- Interpreting animations whose backend skipped/fell back.
- Distributing vanilla/Croco/Workshop assets; only the three user-authorized
  fixtures enter the payload.
- Guessing among multiple embedded ODOL signatures.
- Treating a self-diff as proof of engine correctness; it proves deterministic
  read/parity only.

## Assumptions

- **RESOLVED 2026-07-25**: the user explicitly confirmed public
  redistribution rights for the three named fixtures and approved an external
  strict ODOL component.
- **RESOLVED by primary repository**: BISDLL commit
  `5600bad995c89154b4f6700ef087f86ef4c49315` publishes no LICENSE/COPYING or
  permission grant:
  <https://github.com/ScripyZz/BisDLL-Arma-3/tree/5600bad995c89154b4f6700ef087f86ef4c49315>.
- **RESOLVED by corpus census**: 13,108 direct-signature v53–v55 files had
  `n_lods` min/max `1/15` and zero negative counts on 2026-07-25; the measured
  default guard is `64`.
- **RESOLVED by fixture probe**: all three accepted fixtures have
  `actual_end == declared_end`; the v55 table is not ordered by file offset,
  so overlap validation sorts intervals rather than requiring table order.

## Forward Contract

| Consumer | Symbol it reads | Kind | Verify status |
|---|---|---|---|
| adapter backend | `ODOL.from_bytes(data)` | external backend API | `[EXACT] ODOL_BACKEND/odol_reader.py:779-783` |
| preflight | `ODOL.version`, `.n_lods`, `.resolutions`, `.lods`, `.lod_errors` | external result fields | `[EXACT] ODOL_BACKEND/odol_reader.py:751-764` |
| boundary gate | `.lod_start_table`, `.lod_end_table`, `.lod_actual_end` | external result fields | `[EXACT] ODOL_BACKEND/odol_reader.py:765-770,912-945` |
| anatomy | `LOD.vertices`, `.normals`, `.faces`, `.materials`, `.proxies`, `.named_selections`, `.named_properties` | external LOD fields | `[EXACT] ODOL_BACKEND/odol_reader.py:609-735` |
| CLI/library | `odol-backend-manifest-v1` | new backend hash manifest | `[DESIGN] relative file names + SHA-256 + API id` |
| CLI/library | `dayz-odol-strict-v1` | new anatomy summary schema | `[DESIGN] this spec SC-008` |
| Python callers | `inspect_odol(path, backend_root, backend_manifest) -> dict` | new read-only API | `[DESIGN] complete result or `OdolStrictError`` |
| Python callers | `diff_anatomy(reference, candidate) -> dict` | new pure diff API | `[DESIGN] exits/verdicts through CLI` |
| CLI | `python -m dayz_odol_strict inspect FILE --backend-root ROOT --backend-manifest MANIFEST` | new command | `[DESIGN] exit 0 or 2` |
| CLI | `python -m dayz_odol_strict diff REF.json OWN.json` | new command | `[DESIGN] exit 0 equal, 1 diff, 2 invalid` |
| all consumers | `OdolStrictError.code`, `.message`, `.offset` | new error contract | `[DESIGN] stable code; offset optional` |

The external backend symbols were opened. Their bytes are not part of this
Forward Contract and cannot be promoted into the MIT repository.

## Backend / Container Lifecycle

1. Read input bytes and hash them.
2. Enumerate `ODOL` signatures; retain candidates whose version is
   `53|54|55`, count is `1..64` and resolution table fits.
3. Require exactly one candidate and slice bytes from that offset.
4. Verify every backend file hash before changing `sys.path` or importing.
5. Invoke the backend in an isolated subprocess with the sliced bytes.
6. Validate count/completeness/boundaries and only then build anatomy JSON.
7. Discard subprocess state; never persist backend objects or partial output.

The backend manifest contains relative paths only. Physical roots are CLI or
ignored local configuration and never appear in output.

## Error Cases

| Code | Required trigger/result |
|---|---|
| `ODOL_SIGNATURE_MISSING` | no plausible signature; exit 2 |
| `ODOL_SIGNATURE_AMBIGUOUS` | more than one plausible signature; exit 2 |
| `ODOL_VERSION_UNSUPPORTED` | direct candidate version outside 53–55; exit 2 |
| `ODOL_LOD_COUNT_INVALID` | count outside 1–64; backend not invoked |
| `ODOL_HEADER_TRUNCATED` | count/resolution table exceeds payload |
| `ODOL_BACKEND_MISSING` | manifest/root/file unavailable |
| `ODOL_BACKEND_DRIFT` | any pinned SHA-256 mismatch |
| `ODOL_BACKEND_FAILURE` | worker non-zero/invalid JSON/exception |
| `ODOL_PARTIAL_RESULT` | any `lod_errors`, `None` LOD or count mismatch |
| `ODOL_BOUNDARY_OOB` | start/end outside sliced payload |
| `ODOL_BOUNDARY_OVERLAP` | sorted intervals overlap |
| `ODOL_BOUNDARY_INEXACT` | `actual_end != declared_end` |
| `ODOL_SUMMARY_INVALID` | diff input violates schema |
| `ODOL_OUTPUT_UNWRITABLE` | requested JSON output cannot be written atomically |

## Observability

- Inspect JSON records both full-input and sliced-payload hashes and the
  container offset.
- Backend manifest id/hash makes the effective parser identity reproducible.
- Every LOD records raw byte interval/hash and parsed count/set summaries.
- Failures expose one stable error code; no partial anatomy JSON is labeled
  PASS.
- Diff findings contain a JSON-pointer-like field path, expected and observed.

## Verification Plan

| Criterion | Verification | Where |
|---|---|---|
| SC-001–SC-003 | header mutation tests + recorded census fixture | offline |
| SC-004 | direct/16/4096 prefix matrix and ambiguous-signature negative | offline |
| SC-005–SC-007 | fake-backend contract mutations + real backend fixtures | offline |
| SC-008–SC-009 | JSON Schema/golden determinism/privacy tests | offline |
| SC-010 | three legal binary fixtures with pinned SHA-256 | offline integration |
| SC-011 | self-diff + one-field mutation matrix | offline |
| SC-012 | payload/source-map/license/similarity scan | offline |

## Implementation Slices

1. Promote the three authorized fixtures and expected metadata, not backend
   code.
2. Backend manifest/hash verifier and isolated worker.
3. Header/container preflight and strict result/boundary validator.
4. Anatomy schema/inspect CLI and real fixture integration.
5. Deterministic diff, negative mutation matrix, docs/source-map/promotion.

Any backend drift or partial parse is a hard stop. Recovery remains an
explicit external workflow and never closes F4.

## Open Questions / NEEDS CLARIFICATION

None. Fixture rights, target versions and external-backend architecture were
approved by the user on 2026-07-25.

## Spec Quality Checklist

- [x] CHK001 Every Success Criterion is measurable.
- [x] CHK002 No vague adjective is used as a criterion.
- [x] CHK003 Numeric criteria include counts/bytes/versions.
- [x] CHK004 Every scenario is Given/When/Then with a concrete offline repro;
  the read-only tool does not invent an in-game claim.
- [x] CHK005 Every criterion/scenario has a verification path.
- [x] CHK006 All F4-verifiable work remains offline.
- [x] CHK007 Every assumption is marked and resolved.
- [x] CHK008 Correctness/license/resource assumptions are resolved.
- [x] CHK009 No template placeholder remains.
- [x] CHK010 Existing backend symbols have `path:line`; new contracts are
  `[DESIGN]`.
- [x] CHK011 Backend fields, fixtures and upstream license state were opened.
- [x] CHK012 No `[UNVERIFIED]` dependency remains.
- [x] CHK013 Out-of-scope is explicit.
- [x] CHK014 Terms are stable: backend, adapter, payload, summary and recovery.
- [x] CHK015 Criteria and scenarios do not contradict.
- [x] CHK016 No persistence/progression/admin flow is introduced; inputs are
  read-only and rollback removes only derived tooling.

**Result: 16/16 PASS.**
