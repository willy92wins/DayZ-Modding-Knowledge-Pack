# Contractual DayZ model preflight — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use
> `superpowers:executing-plans` and execute this plan inline. Do not delegate
> tasks; the project handoff requires Codex inline execution.

**Goal:** Close DPF F3 with a deterministic, read-only MLOD preflight that
checks consumer-declared scale, bone selections and complete face lineage,
composed with py3d validation and without repair.

**Architecture:** Create a small dependency-free package that loads a strict
versioned JSON contract, verifies the installed DayZ py3d fork, parses target
and source MLOD files once and runs independent validators. Winding is judged
from explicit source→target face evidence plus affine determinant, never from
normals or inferred intent.

**Tech stack:** Python standard library, pytest, JSON Schema, local py3d 1.4.0.

**Authoritative spec:** `specs/2026-07-25-dayz-model-preflight.md`

## Scope and constraints

- Create `tools/dayz-model-preflight/pyproject.toml`.
- Create package files under
  `tools/dayz-model-preflight/dayz_model_preflight/`:
  `__init__.py`, `errors.py`, `contract.py`, `findings.py`, `winding.py`,
  `runner.py`, `__main__.py`.
- Create schema/tests/first-party synthetic fixtures within the tool.
- Update only directly affected model/proxy/audit skill material, docs,
  notices/provenance, manifest, product and handoff records.
- Require `IS_DAYZ_FORK == True` and py3d version `>=1.4.0`; do not declare a
  PyPI dependency that could resolve to upstream py3d.
- Do not infer expected scale, bone identity or face lineage; do not mutate or
  emit a `.p3d`.

## Task 1 — Strict contract and dependency gate

**Files**

- Create
  `tools/dayz-model-preflight/schemas/dayz-model-preflight-v1.schema.json`.
- Create `tools/dayz-model-preflight/dayz_model_preflight/contract.py`.
- Create `tools/dayz-model-preflight/dayz_model_preflight/errors.py`.
- Create `tools/dayz-model-preflight/tests/test_contract.py`.

1. Add RED schema/semantic tests for every required field, strict unknown
   properties, finite positive numbers, scalar/vector tolerance, unique
   non-empty selection names, affine last row, path escape and non-empty
   one-to-one face map.
2. Add RED dependency tests for missing, upstream, 1.3.0 and valid 1.4.0 py3d.
3. Implement `[DESIGN] load_contract(path)` with post-schema finite/uniqueness/
   path-containment checks.
4. Implement a lazy py3d identity gate so importing the CLI for `--help` does
   not pull an unrelated PyPI package, while every check run fails closed with
   `PREFLIGHT_PY3D_UNAVAILABLE` when identity/version is wrong.
5. Run focused tests.

[EXACT]
```powershell
python -m pytest -q tools/dayz-model-preflight/tests/test_contract.py
```

## Task 2 — Deterministic findings, scale and bones

**Files**

- Create `tools/dayz-model-preflight/dayz_model_preflight/findings.py`.
- Create `tools/dayz-model-preflight/dayz_model_preflight/runner.py`.
- Create `tools/dayz-model-preflight/tests/test_scale_bones.py`.

1. Build synthetic source/target MLOD files using the verified py3d constructors
   and normal save path; do not handcraft private binary offsets.
2. Add RED tests for:
   - per-axis bounds dimensions and scalar/vector tolerance;
   - missing LOD as `PREFLIGHT_LOD_MISSING`;
   - missing versus empty exact-case selection;
   - unrelated selections ignored;
   - py3d ERROR findings preserved as `PREFLIGHT_PY3D_ERROR`;
   - warnings visible without changing a zero-error verdict.
3. Implement stable finding records and sorting by severity, code, LOD, face
   and selection.
4. Open each MLOD with `[EXACT] P3D(f)` at
   `tools/py3d/py3d/__init__.py:1791-1802`, call `[EXACT] LOD.bbox()` at
   `tools/py3d/py3d/__init__.py:1345-1360` and `[EXACT] P3D.validate()` at
   `tools/py3d/py3d/__init__.py:2079-2119`.

## Task 3 — Complete affine face-lineage winding

**Files**

- Create `tools/dayz-model-preflight/dayz_model_preflight/winding.py`.
- Create `tools/dayz-model-preflight/tests/test_winding.py`.

1. Add RED fixtures for identity, rotation/translation, reflection,
   preserve/reverse cyclic shifts, mixed relation, geometry mismatch,
   singular/non-finite matrix, duplicates, uncovered faces, out-of-range
   addresses, triangle↔quad and one-to-many attempts.
2. Implement determinant of the upper 3×3; absolute value at most `1e-12` is
   invalid. Positive requires `PRESERVE`, negative requires `REVERSE`.
3. Transform source positions with the complete affine 4×4 matrix and compare
   each mapped polygon within `position_tolerance_m`.
4. Determine order only by cyclic equivalence of matched vertices. Never use
   generated normals, centroids or a repair operation.
5. Require every face in each referenced source and target LOD to occur exactly
   once and reject unsupported arity/splits before producing a verdict.
6. Run the winding matrix and compare its normalized cases against the private
   source-game oracle baseline without copying its implementation.

## Task 4 — Pure API, CLI, exits and immutability

**Files**

- Create `tools/dayz-model-preflight/dayz_model_preflight/__init__.py`.
- Create `tools/dayz-model-preflight/dayz_model_preflight/__main__.py`.
- Create `tools/dayz-model-preflight/tests/test_runner_cli.py`.

1. Add RED tests for `[DESIGN] run_preflight(model_path, contract_path)` and
   CLI exits `0/1/2`.
2. Hash target/source/contract bytes before parsing and after every positive,
   FAIL and INVALID run; require equality and no new `.p3d`.
3. Emit `dayz-model-preflight-result-v1` JSON with no timestamp/absolute path,
   sorted keys and deterministic findings. Paths in messages are logical roles
   only.
4. Write `--json` atomically after complete validation; invalid output paths
   must not alter the model or contract.

[EXACT]
```powershell
python -m pytest -q tools/dayz-model-preflight/tests
```

## Task 5 — Docs, provenance and release gates

**Files**

- Create `tools/dayz-model-preflight/README.md`.
- Modify directly affected repository skill/reference projections.
- Modify root `README.md`, `CHANGELOG.md`, `product-spec.md`, `HANDOFF.md`,
  `sources/source-map.json` and `MANIFEST.txt`.

1. Document the complete v1 contract, exits, stable codes, examples and
   explicit unsupported split boundary.
2. Record private source-game scripts only as comparison evidence in the source map;
   run a source similarity review and include zero private source bytes.
3. Run the new suite, full py3d suite, fixed source-game oracle suite, complete pack
   suite and packctl gates.

[EXACT]
```powershell
python -m pytest -q tools/dayz-model-preflight/tests
python -m pytest -q tools/py3d/tests
python -m pytest -q
python -m packctl validate --root .
python -m packctl gate --root .
```

4. Review for incomplete coverage, path escape, same-pipeline tautologies,
   dependency confusion, mutation and severity/exit mismatches.

## Exit gate

- SC-001 through SC-012 have named passing checks.
- Every PASS has complete explicit scale, bone and lineage evidence.
- Missing/unsupported evidence is INVALID or FAIL exactly as specified.
- Model/source/contract hashes are unchanged for every test path.
