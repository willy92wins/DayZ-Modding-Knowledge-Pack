# Feature Spec: DayZ animation interchange formats

**Mod / PBO**: `tools/dayz-animation-formats` offline tool
**Date**: 2026-07-25
**Status**: Ready-to-implement
**Plan**: `plans/2026-07-25-04b-dayz-animation-formats.md`
**DPF trace**: F2

## Context / Why

The installed animation skill contains a useful but permissive SEAnim helper
and incorrectly states that no pure-Python RTM writer exists. F2 needs a
redistributable, strict interchange layer with explicit limits. The new tool
owns SEAnim v1 and unbinarized RTM `RTM_0101`; proprietary `.anm`/BMTR
conversion remains outside the pack.

Evidence aliases:

- `ANIM_DRAFT` =
  `VAULT/AI/20_Knowledge/skills-drafts/dayz-animation-pipeline`;
- `SE2DEV` = `SE2Dev/io_anim_seanim` primary MIT implementation;
- `A3OB` = installed Arma3ObjectBuilder, GPLv3 external oracle only.

## Acceptance Scenarios

1. **Given** a synthetic first-party animation containing position, rotation,
   scale, notes, modifiers and a non-default precision mode, **When** the local
   SEAnim writer emits bytes, **Then** the SE2Dev reader accepts them and both
   implementations report the same semantic document.
   - **Repro in-game**: convert the accepted `.seanim` to `.anm` with the
     user's DayZATool workflow, bind it to a first-party test action and observe
     the keyed translation/rotation plus note timing in one DayZDiag batch.

2. **Given** one semantic animation for each type
   `ABSOLUTE|ADDITIVE|RELATIVE|DELTA`, **When** it is written, read and written
   again, **Then** type, keys, notes, modifiers, precision, loop flag,
   framerate and frame count round-trip within the selected float precision.
   - **Repro in-game**: only the type used by the accepted DayZ fixture is sent
     to DayZDiag; the four-type matrix is an offline format gate.

3. **Given** bad magic/version/header size, a truncated count/payload, an
   unterminated string, an invalid index/flag or trailing bytes, **When** the
   SEAnim reader parses it, **Then** it fails closed with an offset-bearing
   error and emits no partial document.
   - **Repro in-game**: none; invalid interchange bytes are blocked before
     DayZATool or DayZ sees them.

4. **Given** a synthetic first-party RTM document generated independently by
   A3OB with `RTM_MDAT` and `RTM_0101`, **When** the local reader parses it and
   the local writer re-emits the same semantic document, **Then** A3OB accepts
   the local bytes and reports identical motion, phases, bone casing,
   transforms and MDAT records.
   - **Repro in-game**: import the local RTM in Object Builder/DayZ animation
     tooling and play the two-frame single-bone fixture; frame 0 and frame 1
     must match the documented transform.

5. **Given** BMTR, an unknown RTM block, duplicate animation blocks, invalid
   counts, a bone name that does not fit its fixed field or trailing garbage,
   **When** the local RTM reader/writer is used, **Then** it rejects the input
   without fallback or truncation.
   - **Repro in-game**: none; unsupported/corrupt formats are stopped offline.

## Success Criteria

- **SC-001 / SEAnim default**: omitting `anim_type` writes
  `RELATIVE == 2`; explicit values `0..3` round-trip unchanged.
- **SC-002 / SEAnim semantic parity**: the frozen first-party fixture is
  accepted by SE2Dev and matches local output for bone names, channel keys,
  frame indices, notes, modifiers, precision, flags, framerate and frame count.
- **SC-003 / SEAnim precision**: float32 mode round-trips each scalar within
  `1e-6`; float64 mode within `1e-12`.
- **SC-004 / SEAnim strictness**: every directed magic/version/header/count/
  truncation/NUL/index/flag/trailing mutation raises one stable code and never
  returns a document.
- **SC-005 / RTM oracle**: A3OB generates and reads the first-party fixture;
  the local reader and writer agree with it on exactly two frames, one bone,
  motion `(1,2,3)`, phases `0.0/1.0`, two transforms and at least one MDAT
  record.
- **SC-006 / RTM strictness**: only zero or one `RTM_MDAT` followed by exactly
  one `RTM_0101` is accepted; BMTR and unknown/duplicate/out-of-order blocks
  fail closed.
- **SC-007 / bounds**: every count is validated against bytes remaining before
  allocation; fixed 32-byte RTM bone fields require UTF-8 payload ≤31 bytes
  plus NUL and are never truncated.
- **SC-008 / licensing**: the payload contains zero A3OB source bytes and zero
  `BisDLL-Arma-3` source bytes; `THIRD_PARTY_NOTICES.md` retains SE2Dev MIT
  attribution and lists A3OB only as a research/oracle dependency under GPLv3.
- **SC-009 / tool contract**: `python -m dayz_animation_formats inspect FILE`
  returns exit `0` plus deterministic JSON for valid SEAnim/RTM, exit `2` plus
  a stable error code for invalid/unsupported input, and writes no timestamp or
  physical path.

## Scope — Out of scope

- DayZ `.anm`, BMTR, `.txa`, `.asi`, animation graph or Workbench conversion.
- Copying or linking A3OB GPL code into the MIT package.
- Claiming that SEAnim alone is a DayZ runtime format.
- Blender authoring, retargeting, skeleton selection or gameplay wiring.
- SEAnim custom-data sections not supported by the accepted SEAnim v1 primary
  implementation.
- Auto-normalizing bone case, reordering keys or repairing corrupt files.
- Supporting unknown future magic/version/block values by best effort.

## Assumptions

- **RESOLVED by primary source**: SE2Dev defines animation types
  `0..3` and uses `RELATIVE == 2` as its default; primary source:
  <https://github.com/SE2Dev/io_anim_seanim/blob/master/seanim.py>.
- **RESOLVED by cross-implementation probe**: the existing local writer with
  `anim_type=2` is accepted by SE2Dev for 11 frames, one bone and one note.
- **RESOLVED by source**: A3OB implements `RTM_Transform.write`,
  `RTM_0101.write`, `RTM_MDAT.write` and `RTM_File.write_file`;
  `A3OB/io/data_rtm.py:21-207`.
- **RESOLVED by license**: A3OB is GPLv3 and remains an external oracle;
  `A3OB/LICENSE:1-20`.
- **RESOLVED by environment**: Blender 5.1 and the installed A3OB extension are
  available for the one-time oracle fixture generation; runtime use of the
  released tool does not require Blender.

## Forward Contract

| Consumer | Symbol it reads | Kind | Verify status |
|---|---|---|---|
| legacy helper users | `write_seanim(path, bones, framerate=30.0, looped=False, anim_type=0, notes=None)` | existing private helper | `[EXACT] ANIM_DRAFT/scripts/seanim_writer.py:28-60` |
| legacy helper users | `read_seanim(path)` | existing private helper | `[EXACT] ANIM_DRAFT/scripts/seanim_writer.py:139-194` |
| oracle generator | `A3OB.RTM_File.write_file(filepath)` | external API | `[EXACT] A3OB/io/data_rtm.py:168-207` |
| oracle reader | `A3OB.RTM_File.read_file(filepath)` | external API | `[EXACT] A3OB/io/data_rtm.py:168-196` |
| Python callers | `AnimType.{ABSOLUTE,ADDITIVE,RELATIVE,DELTA}` | new enum | `[DESIGN] values exactly 0, 1, 2 and 3` |
| Python callers | `write_seanim(path, bones, framerate=30.0, looped=False, anim_type=AnimType.RELATIVE, notes=None, modifiers=None, precision="float32")` | new public API | `[DESIGN] compatible positional prefix; strict validated extensions` |
| Python callers | `read_seanim(path)` | new strict public API | `[DESIGN] returns a deterministic document dict or raises AnimationFormatError` |
| tests/CLI | `write_seanim_bytes(document)` / `read_seanim_bytes(data)` | new pure APIs | `[DESIGN] no filesystem metadata in result` |
| Python callers | `write_rtm_bytes(document)` / `read_rtm_bytes(data)` | new RTM_0101 APIs | `[DESIGN] optional MDAT + exactly one RTM_0101` |
| CLI | `python -m dayz_animation_formats inspect FILE` | new command | `[DESIGN] exit 0 valid, exit 2 invalid/unsupported` |
| all consumers | `AnimationFormatError.code`, `.offset`, `.message` | new error contract | `[DESIGN] stable machine code and byte offset` |

The A3OB methods were opened in the installed source. New local interfaces are
`[DESIGN]` until their first RED tests. No unverified engine API is required.

## Format / Compatibility Contract

### SEAnim

- Magic `SEAnim`, version `1`, header size `28`, little-endian.
- Bone names and note names are NUL-terminated UTF-8.
- The writer derives the smallest legal frame-index width from frame count.
- Bone modifiers remain raw validated uint8 values; this feature does not
  invent DayZ semantics for them.
- `precision` is exactly `float32` or `float64` and maps to the v1 data-property
  flag used by SE2Dev.
- The parser consumes the complete byte stream; trailing bytes are an error.

### RTM

- Accepted blocks are optional `RTM_MDAT` then mandatory `RTM_0101`.
- `RTM_0101` stores motion, frame/bone counts, 32-byte bone fields, phases and
  one 3×4 transform per bone/frame.
- The public document exposes each transform as a 4×4 row-major matrix with
  final row `(0,0,0,1)`.
- The writer follows the axis/component order validated by the A3OB fixture;
  it does not expose an alternate implicit coordinate mode.
- Every block and the entire stream must end at a computed boundary.

No private persistent schema changes. Existing standard-compliant SEAnim/RTM
files are legacy inputs. Rolling back the pack leaves files readable by
SE2Dev/A3OB/DayZ tooling because the feature writes their established formats.

## Error Cases

| Case | Required result |
|---|---|
| bad SEAnim magic/version/header size | stable error + byte offset |
| count impossible for bytes remaining | reject before allocation |
| unterminated/invalid UTF-8 string | reject; no replacement characters |
| non-finite framerate/key/matrix scalar | reject |
| frame outside declared range | reject |
| bone/modifier index outside bone count | reject |
| unsupported presence/property flag | reject |
| trailing bytes | reject |
| RTM BMTR or unknown signature | unsupported-format error |
| RTM duplicate/out-of-order blocks | reject |
| RTM fixed string >31 UTF-8 bytes | reject; never truncate |
| writer input with duplicate bone names or mismatched transform count | reject before bytes are emitted |

## Observability

- Deterministic inspect JSON contains format, version, flags, frame/bone/note/
  property counts and a SHA-256 of the input bytes, never a physical root.
- All parser errors expose stable code and byte offset.
- Oracle-generation script records Blender version, A3OB source hash, fixture
  hash and expected JSON; it is development-only and not required at runtime.
- Cross-reader tests print semantic deltas by field, not merely “files differ”.

## Verification Plan

| Criterion | Verification | Where |
|---|---|---|
| SC-001–SC-004 | local unit/mutation tests + SE2Dev cross-reader | offline |
| SC-005–SC-007 | A3OB fixture generation/readback + local RTM tests | offline Blender once + normal Python |
| SC-008 | provenance/source-map/license scan and payload similarity review | offline |
| SC-009 | CLI golden JSON + exit-code tests | offline |
| accepted DayZ animation | DayZATool/Object Builder/DayZDiag batch | final manual/in-game gate |

## Implementation Slices

1. Freeze SE2Dev/A3OB revisions and generate first-party oracle fixtures.
2. Strict binary reader primitives and typed errors.
3. SEAnim RED→GREEN plus cross-reader verification.
4. RTM_0101/MDAT RED→GREEN plus A3OB cross-reader verification.
5. CLI, docs, source map, notices and animation-skill patch/promotion.

If the A3OB fixture cannot be generated and read back independently, RTM code
does not begin; SEAnim may still close its own slice without weakening F2.

## Open Questions / NEEDS CLARIFICATION

None. Component ownership and the GPL/MIT boundary were approved by the user
on 2026-07-25.

## Spec Quality Checklist

- [x] CHK001 Every Success Criterion is measurable.
- [x] CHK002 No vague adjective is used as a criterion.
- [x] CHK003 Numeric criteria include counts/tolerances.
- [x] CHK004 Every scenario is Given/When/Then with concrete tool/DayZ repro.
- [x] CHK005 Every criterion/scenario has a verification path.
- [x] CHK006 Format and mutation checks are offline.
- [x] CHK007 Every assumption is marked and resolved.
- [x] CHK008 Correctness-deciding format/license assumptions are resolved.
- [x] CHK009 No template placeholder remains.
- [x] CHK010 Existing Forward-Contract APIs have source lines; new APIs are
  `[DESIGN]`.
- [x] CHK011 External methods and licenses were opened and verified.
- [x] CHK012 No `[UNVERIFIED]` dependency remains.
- [x] CHK013 Out-of-scope is explicit.
- [x] CHK014 Terms are stable: SEAnim, RTM_0101, RTM_MDAT, BMTR and oracle.
- [x] CHK015 Criteria and scenarios do not contradict.
- [x] CHK016 No persistence/progression/admin path is introduced; standard
  format legacy/rollback behavior is explicit.

**Result: 16/16 PASS.**
