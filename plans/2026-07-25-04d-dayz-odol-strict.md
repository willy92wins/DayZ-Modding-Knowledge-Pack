# Strict ODOL read-only adapter — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use
> `superpowers:executing-plans` and execute this plan inline. Do not delegate
> tasks; the project handoff requires Codex inline execution.

**Goal:** Close DPF F4 with deterministic strict anatomy reads for legal ODOL
v53/v54/v55 fixtures, while keeping the no-license recovery parser external
and rejecting all partial/boundary-uncertain results.

**Architecture:** Create an original MIT adapter with four trust boundaries:
header/container preflight, backend hash identity, isolated worker invocation
and complete post-parse validation. The repository ships legal fixture bytes,
schemas and expected summaries, but no backend source. Inspect returns only a
fully validated result; diff is a pure comparison over validated summaries.

**Tech stack:** Python standard library, pytest, JSON Schema, external pinned
ODOL backend supplied by explicit root.

**Authoritative spec:** `specs/2026-07-25-dayz-odol-strict.md`

## Scope and constraints

- Create `tools/dayz-odol-strict/pyproject.toml`.
- Create package files under
  `tools/dayz-odol-strict/dayz_odol_strict/`:
  `__init__.py`, `errors.py`, `manifest.py`, `preflight.py`, `worker.py`,
  `inspect.py`, `diff.py`, `__main__.py`.
- Create schemas/tests/authorized fixtures under the tool.
- Update only directly affected ODOL/debinarizer/inspector skill material,
  docs, notices/provenance, manifest, product and handoff records.
- Never copy/import the backend in-process, redistribute its source, accept
  partial recovery, write ODOL/MLOD, or expand supported versions silently.

## Task 1 — Promote only the authorized fixtures

**Files**

- Create `tools/dayz-odol-strict/tests/fixtures/odol-v53-ammo-box.p3d`.
- Create `tools/dayz-odol-strict/tests/fixtures/odol-v54-rugermarkiv-optic.p3d`.
- Create `tools/dayz-odol-strict/tests/fixtures/odol-v55-lfquad-body.p3d`.
- Create `tools/dayz-odol-strict/tests/fixtures/fixtures.json`.
- Create `tools/dayz-odol-strict/tests/test_fixture_provenance.py`.

1. Re-hash the three approved source files before copying.
2. Copy each binary by exact literal path, then verify destination size and
   SHA-256 immediately:
   - v53: `c2ba93cc05d3d47df5400c6f5f68aef928687eef06ce38747340927cd39e96ba`;
   - v54: `ccdb62e78661f2a0d98e5d5ca8844a8a7f0ae5242c2e1f403530d01d0ef037f9`;
   - v55: `9dd2b16a70001b5e6513bf26da0b24db6c2a92c09f6fa09ae9aab20f77ef19d3`.
3. Record only logical fixture names, version, size, hash, approved rights
   statement and expected LOD count in `fixtures.json`; no source machine path.
4. Add a provenance test that fails on any byte drift.

## Task 2 — Backend manifest and isolated worker contract

**Files**

- Create `tools/dayz-odol-strict/backend/manifest-v1.json`.
- Create `tools/dayz-odol-strict/dayz_odol_strict/errors.py`.
- Create `tools/dayz-odol-strict/dayz_odol_strict/manifest.py`.
- Create `tools/dayz-odol-strict/dayz_odol_strict/worker.py`.
- Create `tools/dayz-odol-strict/tests/test_backend_manifest.py`.
- Create `tools/dayz-odol-strict/tests/fake_backend/`.

1. Hash every external backend Python file required by
   `[EXACT] ODOL.from_bytes(data)` at external
   `odol_reader.py:779-783`; record relative paths, SHA-256, manifest id and
   API id. Record no physical root.
2. Add RED tests for absent root/file, path escape, extra absolute path,
   changed byte, manifest drift and exact match.
3. Implement manifest verification before subprocess launch. Reject symlink/
   resolved-path escape and return only stable missing/drift codes.
4. Define a worker JSON protocol over stdin/stdout. The parent supplies the
   already-sliced payload path and verified backend root; the worker imports
   only after verification, calls the exact external API and serializes counts,
   names/properties, intervals and errors. It never labels output PASS.
5. Exercise worker failures with an original tiny fake backend; do not use
   copied parser code.

## Task 3 — Header/container preflight

**Files**

- Create `tools/dayz-odol-strict/dayz_odol_strict/preflight.py`.
- Create `tools/dayz-odol-strict/tests/test_preflight.py`.

1. Add RED tests for direct, 16-byte and 4096-byte prefixes; missing and
   ambiguous signatures; unsupported versions; signed counts `0`, negative,
   `65`; truncated resolution table and a plausible signature inside arbitrary
   payload.
2. Enumerate `ODOL` occurrences, parse little-endian version and signed
   `n_lods`, require version `53|54|55`, `1..64` LODs and at least
   `12 + 4*n_lods` remaining bytes.
3. Distinguish a direct unsupported ODOL header as
   `ODOL_VERSION_UNSUPPORTED`; otherwise require exactly one supported
   plausible candidate.
4. Slice from the accepted offset and hash both complete input and payload.
   Do not invoke or import the backend in any failed preflight case.

## Task 4 — Complete post-parse validation and anatomy schema

**Files**

- Create `tools/dayz-odol-strict/dayz_odol_strict/inspect.py`.
- Create `tools/dayz-odol-strict/dayz_odol_strict/__init__.py`.
- Create `tools/dayz-odol-strict/schemas/dayz-odol-strict-v1.schema.json`.
- Create `tools/dayz-odol-strict/tests/test_inspect_contract.py`.
- Create `tools/dayz-odol-strict/tests/test_real_fixtures.py`.

1. Add fake-worker RED results for count/table mismatch, `lod_errors`, `None`
   LOD, OOB interval, sorted overlap and inexact actual end.
2. Validate backend version/count/resolutions/table lengths before inspecting
   any LOD. Require zero errors, zero missing LODs and exactly matching counts.
3. Sort intervals only for overlap validation; preserve declared LOD order in
   output. Require `0 <= start < end <= payload_size` and
   `actual_end == declared_end`.
4. Hash raw LOD slices in the parent and build deterministic anatomy counts,
   sorted selection names and sorted named properties only after all checks
   pass.
5. Validate output against `dayz-odol-strict-v1`; omit timestamp, username,
   physical path and partial fields.
6. Run real integration with the explicitly supplied local backend and require
   `1/1`, `1/1`, `5/5` complete LODs plus exact fixture hashes.

## Task 5 — Deterministic inspect/diff CLI

**Files**

- Create `tools/dayz-odol-strict/dayz_odol_strict/diff.py`.
- Create `tools/dayz-odol-strict/dayz_odol_strict/__main__.py`.
- Create `tools/dayz-odol-strict/tests/test_cli_diff.py`.

1. Add RED CLI tests for inspect success/invalid exits and self-diff/mutation/
   invalid-summary exits `0/1/2`.
2. Diff validated summaries recursively by stable JSON-pointer-like field
   path, excluding no anatomy field. Sort findings by path.
3. Emit deterministic sorted JSON and write output atomically only after a
   complete result.
4. Add one directed mutation each for resolution, selection, property, proxy
   count and raw LOD hash; each must yield exactly one finding at the expected
   path.

[EXACT]
```powershell
if (-not (Test-Path Env:DAYZ_ODOL_BACKEND_ROOT)) {
    throw 'Set DAYZ_ODOL_BACKEND_ROOT to the external pinned backend first.'
}
python -m pytest -q tools/dayz-odol-strict/tests
Remove-Item Env:DAYZ_ODOL_BACKEND_ROOT
```

## Task 6 — Documentation, licensing and release gates

**Files**

- Create `tools/dayz-odol-strict/README.md`.
- Modify directly affected repository skill/reference projections.
- Modify `THIRD_PARTY_NOTICES.md`, root `README.md`, `CHANGELOG.md`,
  `product-spec.md`, `HANDOFF.md`, `sources/source-map.json` and
  `MANIFEST.txt`.

1. Document supported versions, `64` guard and measured `13,108`-file corpus
   maximum `15`, external backend setup, strict/recovery distinction and all
   stable errors.
2. Record fixture authorization as first-party/user-authorized. Record
   BisDLL/backend only as external no-license evidence and copy zero source.
3. Run tracked-payload scans for backend fragments, private paths and
   unlicensed source; manually inspect any similarity hit.
4. Run ODOL tests with and without backend env, full pack tests and packctl
   reproducibility gates.

[EXACT]
```powershell
python -m pytest -q tools/dayz-odol-strict/tests
python -m pytest -q
python -m packctl validate --root .
python -m packctl gate --root .
```

5. Review for in-process imports, backend invocation before preflight/hash
   gate, partial PASS, offset-base mistakes, interval ordering assumptions,
   fixture drift and overclaimed ODOL support.

## Exit gate

- SC-001 through SC-012 have named passing checks.
- All three authorized fixtures parse completely with the pinned backend.
- Every partial/boundary/backend-identity defect exits `2`.
- The MIT payload contains no backend/BisDLL source.
