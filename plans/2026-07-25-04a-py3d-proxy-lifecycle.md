# py3d proxy lifecycle — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use
> `superpowers:executing-plans` and execute this plan inline. Do not delegate
> tasks; the project handoff requires Codex inline execution.

**Goal:** Close DPF F1 and the py3d portion of F5 with a backward-compatible,
fail-closed add/inspect/align/remove proxy lifecycle and one reproducible 1.4.0
distribution.

**Architecture:** Keep the MLOD binary schema unchanged. Extend the existing
single-file py3d implementation with validated frame-space helpers and a
private canonical-anatomy resolver. Mutators validate completely before
changing list-backed model state. Distribution remains source-first:
`tools/py3d/py3d` is canonical, while the ignored wheel is reproducibly built
and identified by a tracked hash manifest.

**Tech stack:** Python standard library, pytest, setuptools/wheel, PowerShell
5.1+, existing packctl.

**Authoritative spec:** `specs/2026-07-25-py3d-proxy-lifecycle.md`

## Scope and constraints

- Modify `tools/py3d/py3d/__init__.py`,
  `tools/py3d/tests/conftest.py`,
  `tools/py3d/tests/test_s4_proxy_lifecycle.py`,
  `tools/py3d/setup.py`, `tools/py3d/README.md`,
  `tools/py3d/rollout/README.md`,
  `tools/py3d/rollout/apply-s2-rollout.ps1`,
  `tools/py3d/rollout/build-wheel.ps1`,
  `tools/py3d/rollout/wheel-manifest.json`, and the affected patched proxy
  skill projection.
- Update only directly affected root release metadata, source-map entries,
  manifest inventory and product/handoff records.
- Preserve the legacy raw-space default, positional argument order, `frame`
  descriptor and MLOD bytes for existing valid calls.
- Do not add NumPy, repair malformed proxies, infer paths/indices, or change
  ODOL/animation/preflight code in this child plan.

## Task 1 — Freeze frame-space and validation contracts

**Files**

- Create `tools/py3d/tests/test_s4_proxy_lifecycle.py`.
- Modify `tools/py3d/py3d/__init__.py`.

1. Add RED tests for:
   - correction-matrix involution and exact raw↔engine table;
   - finite 3×3 orthonormal determinant-`+1` validation;
   - strict index validation excluding `bool`;
   - non-empty path without a case-insensitive `.p3d` suffix;
   - positive finite scale whose float32 triangle remains non-degenerate;
   - semantic snapshot equality after every rejected call.
2. Run only the new node IDs and confirm failure is caused by missing new
   symbols, not fixture construction.

[EXACT]
```powershell
python -m pytest -q tools/py3d/tests/test_s4_proxy_lifecycle.py
```

3. Implement `[DESIGN] PROXY_ENGINE_CORRECTION`,
   `[DESIGN] proxy_frame_to_engine(rotation)`,
   `[DESIGN] proxy_frame_from_engine(rotation)` and private validators.
4. Extend `[EXACT] canonical_proxy_triangle` at
   `tools/py3d/py3d/__init__.py:237` by appending `space="raw"`. Convert engine
   input once before the existing triangle construction.
5. Re-run the focused tests to green.

## Task 2 — Compatible add and strict enumeration

**Files**

- Modify `tools/py3d/tests/test_s4_proxy_lifecycle.py`.
- Modify `tools/py3d/py3d/__init__.py`.

1. Add RED tests proving:
   - raw default emits the exact legacy triangle and descriptor;
   - engine identity emits the correction matrix in raw space;
   - add→save→reload preserves name, anchor, raw/engine frames and scale
     within `1e-3`;
   - `get_proxies()` retains `frame` and adds `raw_frame`, `engine_frame`,
     `scale`;
   - `get_proxies(strict=True)` rejects each malformed proxy anatomy.
2. Extend `[EXACT] LOD.add_proxy` at
   `tools/py3d/py3d/__init__.py:1515` by appending `space="raw"` and performing
   all validation before list mutation.
3. Add one private resolver returning the selection, its exact three points,
   one triangular face, its exclusive normal and derived frame. The resolver
   has a read-only mode for enumeration and an exclusive-ownership mode for
   mutators.
4. Extend `[EXACT] LOD.get_proxies` at
   `tools/py3d/py3d/__init__.py:1557` by appending `strict=False`.
5. Re-run the focused file and historical proxy recipe tests.

[EXACT]
```powershell
python -m pytest -q tools/py3d/tests/test_s4_proxy_lifecycle.py tools/py3d/tests/test_s2_proxy_recipe.py
```

## Task 3 — Atomic align and remove

**Files**

- Modify `tools/py3d/tests/test_s4_proxy_lifecycle.py`.
- Modify `tools/py3d/py3d/__init__.py`.

1. Add RED fixtures with unrelated points, faces, selections, normals and
   sharp edges around one canonical proxy.
2. Assert `[DESIGN] LOD.align_proxy(name, origin, rotation=None,
   scale=0.001, space="raw")`:
   - validates name/anatomy/ownership/transform before mutation;
   - mutates the same point and exclusive-normal objects;
   - leaves selection/face identities and list counts unchanged;
   - returns the selection name.
3. Assert `[DESIGN] LOD.remove_proxy(name)`:
   - rejects shared points, face or normal before mutation;
   - removes exactly the selection, face and three points;
   - mutates owning lists in place;
   - remaps all surviving `Vertex.point_index`, `sharp_edges` and selection
     bindings;
   - returns the selection name.
4. Implement the two mutators with a precomputed mutation plan. No list is
   changed until every invariant and remap target has been validated.
5. Run positive, shared-anatomy, malformed and atomicity matrices.

## Task 4 — Version and reproducible distribution

**Files**

- Modify `tools/py3d/py3d/__init__.py`.
- Modify `tools/py3d/setup.py`.
- Modify `tools/py3d/tests/conftest.py`.
- Create `tools/py3d/rollout/build-wheel.ps1`.
- Create `tools/py3d/rollout/wheel-manifest.json`.
- Modify `tools/py3d/rollout/apply-s2-rollout.ps1`.
- Modify `tools/py3d/rollout/README.md`.

1. Set both verified version markers to `1.4.0` and update the fixture
   assertion.
2. Add a PowerShell build script resolved from `$PSScriptRoot`, with a fixed
   `SOURCE_DATE_EPOCH`, clean output staging and `python -m pip wheel
   --no-deps`. It must never use a private project root.
3. Build twice into two temporary output directories and require identical
   SHA-256.
4. Record filename, SHA-256, fixed epoch and source version in
   `wheel-manifest.json`. The wheel itself remains under ignored `dist/`.
5. Make rollout resolve its source tree relative to the script, verify the
   tracked wheel manifest, accept the target skill root as an explicit
   parameter, and support a no-write verification mode. Preserve backups for
   actual replacement.
6. Update only the patched proxy skill projection and its patch so it documents
   raw/engine semantics and the 1.4.0 APIs.

## Task 5 — Docs, provenance and full gates

**Files**

- Modify `tools/py3d/README.md`, root `README.md`, `CHANGELOG.md`,
  `product-spec.md`, `HANDOFF.md`, `sources/source-map.json`,
  `MANIFEST.txt` and directly affected promotion metadata.

1. Document exact raw/engine formulas, strict anatomy, failures and
   add→align→remove examples.
2. Add/refresh source-map entries and hashes for every touched/tracked file.
   Classify original implementation as MIT and A3OB proxy utilities as
   comparison-only evidence; copy no GPL bytes.
3. Regenerate the payload inventory mechanically and run source-map,
   license/private-path and promotion-routing checks.
4. Run all py3d tests and require the historical census to remain at least
   `130 passed, 10 skipped`, with all new tests passing.
5. Run the complete pack suite and two reproducible pack builds.

[EXACT]
```powershell
python -m pytest -q tools/py3d/tests
python -m pytest -q
python -m packctl validate --root .
python -m packctl gate --root .
```

6. Inspect the final diff for incidental refactors, mutation-before-validation,
   index remap errors, version drift and private paths. Do not promote to
   installed skill roots until the repository commit is green and the
   promotion plan is dry-run clean.

## Exit gate

- SC-001 through SC-009 in the authoritative spec have a named passing test or
  release check.
- Existing valid raw calls are byte/semantic compatible.
- The 1.4.0 wheel is reproducible and its tracked hash matches.
- No installed target is mutated by this plan before the final promotion gate.
