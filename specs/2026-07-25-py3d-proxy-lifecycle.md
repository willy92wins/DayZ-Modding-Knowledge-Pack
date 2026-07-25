# Feature Spec: py3d proxy lifecycle

**Mod / PBO**: `tools/py3d` offline MLOD codec
**Date**: 2026-07-25
**Status**: Ready-to-implement
**Plan**: `plans/2026-07-25-04a-py3d-proxy-lifecycle.md`
**DPF trace**: F1, F5

## Context / Why

py3d 1.3.0 can create and enumerate proxy triangles, but it cannot align or
remove them and its documentation confuses the raw MLOD frame with the frame
rendered by DayZ. Invalid scale, rotation, path and index values can also
produce degenerate or undiscoverable proxy geometry. This feature adds a
complete fail-closed lifecycle without changing the meaning of existing valid
`rotation` calls.

Evidence aliases:

- `PY3D` = `tools/py3d/py3d/__init__.py`;
- `PROXY_SKILL` = installed `dayz-proxy-align/SKILL.md`, evidence-only;
- `A3OB` = Arma3ObjectBuilder proxy utilities, research-only GPL oracle.

## Acceptance Scenarios

1. **Given** an empty synthetic MLOD visual LOD and a known raw rotation,
   **When** a proxy is added, saved and reloaded, **Then** its name, anchor,
   raw frame, engine frame, scale, three-point selection and one triangle are
   preserved within float32 tolerance.
   - **Repro in-game**: binarize the first-party fixture, attach a visible
     first-party cube through the generated proxy and inspect it in DayZDiag;
     the raw-frame fixture must match its documented engine-space pose.

2. **Given** an existing canonical proxy, **When** it is aligned using an
   engine-space identity matrix, **Then** the same selection and face objects
   remain registered, its raw frame becomes the DayZ correction matrix and
   unrelated model data remains semantically unchanged.
   - **Repro in-game**: reload the same fixture with the aligned proxy; the cube
     must render upright at the new anchor without recreating or duplicating
     the proxy selection.

3. **Given** a canonical proxy whose points, face and normal are exclusively
   owned, **When** it is removed, **Then** its selection, face and points
   disappear, all surviving vertex and sharp-edge indices remain valid, and
   no unrelated selection membership changes.
   - **Repro in-game**: binarize/spawn the post-removal fixture; the attached
     cube is absent and the base model still renders with no proxy/model error
     in the delimited RPT segment.

4. **Given** a malformed or shared proxy anatomy, a non-positive/non-finite
   scale, a reflection/non-orthonormal matrix, a path ending in `.p3d` or an
   invalid index, **When** add/align/remove is requested, **Then** the operation
   raises before mutation and a semantic snapshot of the LOD is unchanged.
   - **Repro in-game**: none; these are pre-binarize negative gates and must
     never consume an engine test cycle.

5. **Given** a caller using the 1.3.0 defaults and valid raw-space inputs,
   **When** the same call runs on 1.4.0, **Then** the emitted proxy triangle,
   legacy `frame` value and selection name remain equivalent.
   - **Repro in-game**: compare the 1.3.0 and 1.4.0 positive raw-space fixtures
     in one DayZDiag batch; no pose delta is permitted.

## Success Criteria

- **SC-001 / F1 add**: raw-space add→save→reload returns exactly one matching
  proxy with three points, one triangular face, weights `1`, and anchor/frame
  error ≤ `1e-3` after float32 serialization.
- **SC-002 / F1 spaces**: for every test matrix,
  `engine_frame = P' × raw_frame` and
  `raw_frame = P' × engine_frame`, where
  `P' = ((-1,0,0),(0,0,1),(0,1,0))`; applying either conversion twice returns
  the original within `1e-9`.
- **SC-003 / F1 align**: align mutates exactly the existing proxy points and
  exclusive normal; selection and face identities and total point/face counts
  do not change.
- **SC-004 / F1 remove**: remove deletes exactly one selection, one face and
  three points; all surviving face vertex indices, `sharp_edges` and selection
  memberships equal the pre-removal semantic snapshot after index remap.
- **SC-005 / F1 atomicity**: every directed invalid/shared-anatomy fixture
  raises `TypeError` or `ValueError` and leaves the serialized semantic
  snapshot byte-identical to the pre-call snapshot.
- **SC-006 / F1 validation**: accepted rotation is finite, 3×3, orthonormal and
  has determinant `+1 ± 1e-6`; scale is finite, positive and remains
  non-degenerate after float32 packing; index is an `int >= 1` excluding
  `bool`; path is non-empty and does not end in `.p3d` case-insensitively.
- **SC-007 / F1 enumeration**: `get_proxies()` keeps the legacy `frame` key as
  raw frame and adds `raw_frame`, `engine_frame` and `scale`;
  `get_proxies(strict=True)` rejects every proxy-named selection whose anatomy
  is not canonical.
- **SC-008 / F5 regression**: all historical py3d tests remain green; the
  pre-change baseline `130 passed, 10 skipped` does not lose or skip any
  previously passing test.
- **SC-009 / F5 distribution**: package version is `1.4.0`; the reproducibly
  generated wheel and its versioned hash manifest, rollout projection,
  `MANIFEST.txt`, source map and promotion receipt identify one canonical byte
  set and contain no private path. The ignored `dist/` wheel is a release
  artifact, not a second source tree.

## Scope — Out of scope

- ODOL reading/writing, animation formats and pre-export contracts.
- Automatically repairing malformed or shared proxy anatomy.
- Guessing a path, adding/removing `.p3d`, changing slash/case, or choosing an
  available index on behalf of the caller.
- Incremental/partial align operations; align writes a complete transform.
- Changing the legacy default from raw-space identity to engine-space identity.
- Editing the installed plugin source directly; skill updates use the
  repository patch/promotion workflow.

## Assumptions

- **RESOLVED 2026-07-25**: the user approved preserving `rotation` as raw MLOD
  space and adding engine space explicitly.
- **RESOLVED 2026-07-25**: proxy indices start at `1`; index `0`, negatives,
  floats and booleans are invalid.
- **RESOLVED by source/probe**: DayZ applies
  `engine_frame = P' × raw_frame`; `PROXY_SKILL:201-234` records the in-game
  correction and the 2026-07-25 probe reproduces it.

## Forward Contract

| Consumer | Symbol it reads | Kind | Verify status |
|---|---|---|---|
| existing callers | `canonical_proxy_triangle(anchor, rotation=None, scale=0.001)` | existing Python API | `[EXACT] PY3D:237-252` |
| existing callers | `LOD.add_proxy(path, index=1, origin=(0,0,0), rotation=None, scale=0.001)` | existing Python API | `[EXACT] PY3D:1515-1555` |
| existing callers | `LOD.get_proxies()` and descriptor key `frame` | existing Python API | `[EXACT] PY3D:1557-1584` |
| proxy parser | `PROXY_NAME_RE` path/index groups | existing regex contract | `[EXACT] PY3D:135-136` |
| frame derivation | `derive_proxy_frame(tri)` | existing Python API | `[EXACT] PY3D:214-234` |
| add/align/enumerate | `PROXY_ENGINE_CORRECTION` | new public constant | `[DESIGN] this spec SC-002` |
| callers | `proxy_frame_to_engine(rotation)` | new public function | `[DESIGN] 3×3 rotation → 3×3 rotation; this spec SC-002` |
| callers | `proxy_frame_from_engine(rotation)` | new public function | `[DESIGN] 3×3 rotation → 3×3 rotation; this spec SC-002` |
| callers | `canonical_proxy_triangle(anchor, rotation=None, scale=0.001, space="raw")` | compatible extension | `[DESIGN] space is exactly raw or engine` |
| callers | `LOD.add_proxy(path, index=1, origin=(0,0,0), rotation=None, scale=0.001, space="raw")` | compatible extension | `[DESIGN] legacy positional parameters unchanged; space appended` |
| callers | `LOD.align_proxy(name, origin, rotation=None, scale=0.001, space="raw")` | new mutator | `[DESIGN] complete-transform write; returns the name` |
| callers | `LOD.remove_proxy(name)` | new mutator | `[DESIGN] exclusive canonical anatomy only; returns the name` |
| audit/preflight | `LOD.get_proxies(strict=False)` | compatible extension | `[DESIGN] default preserves legacy filtering; strict rejects malformed proxy selections` |
| wheel/rollout | `py3d.__version__ == "1.4.0"` | distribution marker | `[DESIGN] created in this feature; current marker is 1.3.0 at PY3D:33-34` |

All new symbols are explicitly `[DESIGN]`; their first failing tests create the
contract before any consumer is implemented. No existing symbol remains
unverified.

## Data / Lifecycle

- All validation and anatomy resolution completes before the first mutation.
- `align_proxy` mutates list members in place so `Selection.all_points` and
  `Selection.all_faces` retain their identity bindings.
- `remove_proxy` mutates the owning lists in place and remaps surviving
  `Vertex.point_index` and `sharp_edges`; it never replaces the list objects.
- Save/reload is the persistence boundary. Version 1.4.0 changes no MLOD binary
  schema; legacy and rollback readers therefore continue to read the same
  format.
- Rollback from 1.4.0 to 1.3.0 can read files produced by 1.4.0 because only
  canonical MLOD proxy geometry is emitted; engine-space metadata is not
  persisted.

## Error Cases

| Case | Required result |
|---|---|
| duplicate proxy name | `ValueError`, no mutation |
| path empty or ending `.p3d` | `ValueError`, no mutation |
| index not strict `int >= 1` | `TypeError`/`ValueError`, no mutation |
| scale `<=0`, NaN, infinity or float32-degenerate | `ValueError`, no mutation |
| matrix wrong shape/non-numeric/non-finite | `ValueError`, no mutation |
| matrix scaled, sheared, reflected or det not near +1 | `ValueError`, no mutation |
| proxy selection not exactly 3 points + 1 triangle | strict operation rejects |
| selected face does not use exactly selected points | strict operation rejects |
| proxy points/face/normal shared by unrelated anatomy | align/remove rejects |
| malformed proxy during legacy enumeration | omitted as in 1.3.0 |
| malformed proxy during strict enumeration | `ValueError` naming selection and issue |

## Observability

- Exceptions name the operation, proxy selection and failed invariant.
- `get_proxies(strict=False)` exposes `raw_frame`, `engine_frame` and `scale`
  while preserving `frame`.
- Tests compare semantic snapshots before/after failures and after save/reload.
- Distribution verification records version, wheel hash, source-tree hash and
  rollout target hashes without physical roots.

## Verification Plan

| Criterion | Verification | Where |
|---|---|---|
| SC-001–SC-003 | matrix table + add/align/save/reload tests | offline py3d suite |
| SC-004 | removal fixture with faces, selections and sharp edges before/after | offline py3d suite |
| SC-005–SC-007 | parameterized invalid/shared/malformed fixtures | offline py3d suite |
| SC-008 | `python -m pytest -q tools/py3d/tests` plus historical node-id census | offline |
| SC-009 | wheel build twice, hash compare, rollout dry-run/readback, `packctl gate` | offline |
| engine pose | one first-party proxy fixture in DayZDiag | final batched in-game check |

## Implementation Slices

1. Public frame-space constants/conversion and fail-closed validators.
2. Compatible add/enumerate extensions and failing tests.
3. Strict anatomy resolver plus align.
4. Remove with index remap and atomicity tests.
5. Version/docs/wheel/rollout/source-map/promotion.

Each slice remains green before the next begins. No distribution or skill
promotion occurs until all code/tests and the independent diff review pass.

## Open Questions / NEEDS CLARIFICATION

None. Product, compatibility, frame-space and index decisions were approved by
the user on 2026-07-25.

## Spec Quality Checklist

- [x] CHK001 Every Success Criterion is measurable.
- [x] CHK002 No vague adjective is used as a criterion.
- [x] CHK003 Numeric criteria carry units/counts/tolerances.
- [x] CHK004 Every scenario is Given/When/Then with a concrete DayZDiag repro
  or an explicit pre-binarize reason not to spend an engine cycle.
- [x] CHK005 Every criterion/scenario has a verification path.
- [x] CHK006 Offline-verifiable criteria are marked offline.
- [x] CHK007 Every guess is marked and resolved.
- [x] CHK008 Correctness-deciding assumptions are resolved.
- [x] CHK009 No template placeholder remains.
- [x] CHK010 Existing Forward-Contract symbols have `path:line`; new symbols
  are `[DESIGN]`.
- [x] CHK011 Existing proxy APIs and selection/list bindings were opened and
  verified.
- [x] CHK012 No `[UNVERIFIED]` dependency remains.
- [x] CHK013 Out-of-scope is explicit.
- [x] CHK014 Canonical terms are stable: raw frame, engine frame, proxy
  anatomy, align and remove.
- [x] CHK015 Criteria and scenarios do not contradict.
- [x] CHK016 No persistence/progression/admin queue is introduced; binary
  compatibility and rollback behavior are explicit.

**Result: 16/16 PASS.**
