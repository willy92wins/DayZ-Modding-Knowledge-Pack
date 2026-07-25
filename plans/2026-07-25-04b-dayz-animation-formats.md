# DayZ animation interchange formats — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use
> `superpowers:executing-plans` and execute this plan inline. Do not delegate
> tasks; the project handoff requires Codex inline execution.

**Goal:** Close DPF F2 with a redistributable strict SEAnim v1 and unbinarized
`RTM_0101` reader/writer, explicit unsupported boundaries and two independent
oracle checks.

**Architecture:** Create one dependency-free Python tool with a shared bounded
binary cursor, stable errors and deterministic document JSON. SEAnim is an
original strict adaptation of the MIT SE2Dev contract. RTM is an original
implementation cross-validated against a first-party binary emitted and read
by the external GPL A3OB installation; no A3OB code or runtime import enters
the package.

**Tech stack:** Python standard library, pytest, JSON Schema, optional external
SE2Dev/A3OB oracle runs during development.

**Authoritative spec:** `specs/2026-07-25-dayz-animation-formats.md`

## Scope and constraints

- Create `tools/dayz-animation-formats/pyproject.toml`.
- Create package files under
  `tools/dayz-animation-formats/dayz_animation_formats/`:
  `__init__.py`, `errors.py`, `binary.py`, `seanim.py`, `rtm.py`,
  `inspect.py`, `__main__.py`.
- Create schemas, tests and first-party fixtures only under
  `tools/dayz-animation-formats/`.
- Update only directly affected docs, animation skill/reference projections,
  notices, source map, manifest, product and handoff records.
- Do not implement `.anm`, BMTR, `.txa`, `.asi`, custom SEAnim data, Blender
  authoring or gameplay wiring.

## Task 1 — Freeze independent oracle fixtures

**Files**

- Create `tools/dayz-animation-formats/tests/fixtures/seanim-v1-full.seanim`.
- Create `tools/dayz-animation-formats/tests/fixtures/seanim-v1-full.json`.
- Create `tools/dayz-animation-formats/tests/fixtures/rtm-0101-mdat.rtm`.
- Create `tools/dayz-animation-formats/tests/fixtures/rtm-0101-mdat.json`.
- Create `tools/dayz-animation-formats/tests/fixtures/ORIGINS.md`.

1. Generate the SEAnim fixture from first-party semantic data and verify it
   with the fixed SE2Dev source revision recorded in the research note.
2. Generate the RTM fixture outside the repository through the installed
   Blender 5.1/A3OB oracle, then read it back with A3OB before copying only the
   binary and expected semantic JSON into the pack.
3. Record fixture SHA-256, generator/oracle revision, license boundary and
   semantic counts. Do not add the temporary A3OB driver or any A3OB source.
4. Assert exact fixture hashes in a RED provenance test before writing local
   readers.

## Task 2 — Bounded binary primitives and stable errors

**Files**

- Create `tools/dayz-animation-formats/dayz_animation_formats/errors.py`.
- Create `tools/dayz-animation-formats/dayz_animation_formats/binary.py`.
- Create `tools/dayz-animation-formats/tests/test_binary.py`.

1. Add RED tests for exact reads, remaining-byte count, little-endian scalar
   reads, bounded counts, NUL-terminated UTF-8 and fixed NUL-padded UTF-8.
2. Define `[DESIGN] AnimationFormatError(code, message, offset)` with stable
   public attributes and deterministic string output.
3. Implement a cursor that checks required bytes and multiplication overflow
   before allocation/iteration. It must reject unterminated/invalid UTF-8 and
   expose the first failing byte offset.
4. Run the focused tests.

[EXACT]
```powershell
python -m pytest -q tools/dayz-animation-formats/tests/test_binary.py
```

## Task 3 — Strict SEAnim v1

**Files**

- Create `tools/dayz-animation-formats/dayz_animation_formats/seanim.py`.
- Create `tools/dayz-animation-formats/tests/test_seanim.py`.

1. Add RED tests for all four animation types, default `RELATIVE == 2`, both
   precisions, position/rotation/scale channels, notes, modifiers, loop flag,
   frame-index widths and exact read→write→read semantics.
2. Add one directed mutation per stable error class: magic, version, header
   size, count bounds, truncation, NUL, index, flag and trailing bytes.
3. Implement `[DESIGN] AnimType`,
   `[DESIGN] read_seanim_bytes(data)`,
   `[DESIGN] write_seanim_bytes(document)`,
   `[DESIGN] read_seanim(path)` and
   `[DESIGN] write_seanim(path, bones, framerate=30.0, looped=False,
   anim_type=AnimType.RELATIVE, notes=None, modifiers=None,
   precision="float32")`.
4. Derive index width from frame count, validate all indices before emission
   and consume the entire stream.
5. Compare the frozen fixture through both the local and SE2Dev readers; the
   normalized semantic JSON must be equal.

## Task 4 — Strict RTM_MDAT plus RTM_0101

**Files**

- Create `tools/dayz-animation-formats/dayz_animation_formats/rtm.py`.
- Create `tools/dayz-animation-formats/tests/test_rtm.py`.

1. Add RED tests for optional MDAT followed by exactly one RTM_0101, two
   frames, one bone, phases `0.0/1.0`, motion `(1,2,3)` and 4×4 public
   transforms.
2. Add RED negatives for BMTR, unknown/duplicate/out-of-order blocks,
   count/size truncation, invalid 32-byte bone field, invalid phase/transform
   scalar and trailing bytes.
3. Implement `[DESIGN] read_rtm_bytes(data)` and
   `[DESIGN] write_rtm_bytes(document)` without importing A3OB.
4. Require UTF-8 bone payload length at most 31 bytes and exact computed stream
   termination.
5. Read the frozen A3OB fixture locally, write it locally, then have the
   external A3OB oracle read the local bytes in a one-time validation run.
   Compare semantic JSON, not raw-byte identity.

## Task 5 — Deterministic CLI and package contract

**Files**

- Create `tools/dayz-animation-formats/dayz_animation_formats/inspect.py`.
- Create `tools/dayz-animation-formats/dayz_animation_formats/__init__.py`.
- Create `tools/dayz-animation-formats/dayz_animation_formats/__main__.py`.
- Create `tools/dayz-animation-formats/tests/test_cli.py`.
- Create `tools/dayz-animation-formats/schemas/animation-inspect-v1.schema.json`.

1. Add CLI RED tests for valid SEAnim/RTM exit `0`, invalid/unsupported exit
   `2`, stdout/output-file equivalence and stable JSON without timestamp or
   physical path.
2. Detect format only by exact magic/block header. Never fall back from one
   parser to another after recognition.
3. Sort object keys, preserve array order, terminate JSON with LF and keep
   expected format errors off stderr.
4. Validate every success output against the tracked schema.

[EXACT]
```powershell
python -m pytest -q tools/dayz-animation-formats/tests
```

## Task 6 — Documentation, licensing and release gates

**Files**

- Create `tools/dayz-animation-formats/README.md`.
- Modify `skills/dayz-animation-pipeline/SKILL.md` or its canonical repository
  projection and the matching rollout/reference material.
- Modify `THIRD_PARTY_NOTICES.md`, root `README.md`, `CHANGELOG.md`,
  `product-spec.md`, `HANDOFF.md`, `sources/source-map.json` and
  `MANIFEST.txt`.

1. Document that SEAnim/RTM are interchange formats and `.anm`/BMTR remain
   unsupported.
2. Attribute SE2Dev MIT use with fixed revision. List A3OB GPLv3 only as an
   external oracle and confirm that no A3OB or BisDLL source is present.
3. Add source-map entries for all files and first-party fixture rights; run a
   private-path and similarity review.
4. Run the tool suite twice, the complete pack suite and packctl validation/
   reproducible gate.

[EXACT]
```powershell
python -m pytest -q tools/dayz-animation-formats/tests
python -m pytest -q
python -m packctl validate --root .
python -m packctl gate --root .
```

5. Review the diff for permissive parsing, unchecked allocation, silent
   truncation, format fallbacks, GPL source leakage and claims that bypass
   DayZATool/DayZDiag.

## Exit gate

- SC-001 through SC-009 have named passing checks.
- Both frozen fixtures have user/first-party provenance and exact hashes.
- SE2Dev accepts local SEAnim; A3OB reads local RTM semantic output.
- The released package has no Blender/A3OB runtime dependency.
