---
name: dayz-p3d-debinarizer
description: >
  DayZ ODOL P3D debinarizer — converts binarized .p3d models (ODOL format) to editable MLOD format
  for Object Builder. Handles DayZ-specific ODOL v54 differences vs Arma 3, including Material v20
  extended PBR fields, missing hasAnims byte detection, and Fire Packer container offset correction.
  Full pipeline: ODOL parsing → MLOD conversion → py3d file output.
  Use this skill for: debinarize p3d, convert ODOL to MLOD, recover binarized DayZ model,
  reverse engineer p3d format, read binarized p3d, extract model from protected PBO,
  Fire Packer p3d recovery, ODOL reader, p3d to Object Builder, DayZ model decompilation.
  Also consult for: understanding ODOL binary format, LZO/LZSS decompression in BI formats,
  DayZ vs Arma 3 format differences, EmbeddedMaterial v20 structure, BI compressed arrays.
  Always consult this skill BEFORE attempting ANY p3d debinarization or ODOL format work.
---

# DayZ P3D Debinarizer

Converts binarized DayZ .p3d files (ODOL format) to editable MLOD format for Object Builder.

## Quick Start

```bash
# Install dependencies (REQUIRED)
# LZO decompression is pure-Python and bundled — no native liblzo2 needed.
# py3d DayZ fork >= 1.5.0 (`pip install -e tools/py3d`).
# NUNCA `pip install py3d` (PyPI = point-cloud lib) NI git+upstream (sin guards).
pip install -e tools/py3d
python3 -c "import py3d; assert getattr(py3d,'IS_DAYZ_FORK',False) and tuple(map(int,py3d.__version__.split('.')))>=(1,5,0), (py3d.__version__, py3d.__file__)"

# Run conversion
cd /path/to/skill/scripts
python3 odol_to_mlod.py input.p3d output_mlod.p3d
```

## Architecture

```
scripts/
├── odol_to_mlod.py    # Main converter: ODOL → MLOD (entry point; skips unparseable LODs)
├── odol_reader.py     # ODOL v28-73 parser with DayZ v54 support + per-LOD resilience
├── bis_reader.py      # Binary reader (LZO/LZSS, compressed arrays, condensed arrays)
├── math_types.py      # Vector3P, Matrix3P, Matrix4P
├── lzo_decompress.py  # LZO1X decompressor (canonical lzo1x_decompress port)
└── lzss_decompress.py # LZSS decompressor with checksum validation
```

## Workflow

### Step 1: Check the file

```python
import struct
data = open('input.p3d', 'rb').read()
sig = data[:4]
if sig == b'ODOL':
    print("Clean ODOL file")
elif sig == b'MLOD':
    print("Already MLOD — no conversion needed")
else:
    # Search for ODOL signature (may be inside a container)
    idx = data.find(b'ODOL')
    if idx > 0:
        print(f"ODOL found at offset {idx} — container file (e.g. Fire Packer)")
    else:
        print("Not a P3D file")
```

### Step 2: Parse ODOL

```python
from odol_reader import ODOL
odol = ODOL.from_file('input.p3d')  # Auto-detects ODOL offset
print(f'{odol}')  # Shows version, LOD count, mass
for i, lod in enumerate(odol.lods):
    if lod is None:
        print(f'  LOD {i}: FAILED — {odol.lod_errors.get(i)}')  # per-LOD resilience
    else:
        print(f'  LOD {i}: {lod}')
```

### Step 3: Convert to MLOD

```python
from odol_to_mlod import convert_odol_to_mlod, emit_model_cfg
import py3d

mlod = convert_odol_to_mlod(odol)   # skips any LOD that failed to parse (partial MLOD)
with open('output_mlod.p3d', 'wb') as f:
    mlod.write(f)

# Animated models: the MLOD format can't store animations, so recover them as a
# model.cfg snippet (returns None for static models). See "Fidelity recovery" below.
cfg = emit_model_cfg(odol, 'output_mlod')
if cfg:
    open('model.cfg', 'w').write(cfg)
```

The CLI (`python3 odol_to_mlod.py in.p3d out.p3d`) writes `model.cfg` automatically
next to the output whenever the source ODOL carried animations.

### Step 4: Verify

```python
with open('output_mlod.p3d', 'rb') as f:
    verify = py3d.P3D(f)
print(f'{len(verify.lods)} LODs read back OK')
```

## Fire Packer Container Handling

Fire Packer prepends data to the .p3d but does NOT update LOD addresses. Detection and fix:

```python
data = open('protected.p3d', 'rb').read()
odol_offset = data.find(b'ODOL')  # e.g. 420400

if odol_offset > 0:
    # LOD addresses need odol_offset added
    # The ODOL._seek_odol() method handles finding the signature automatically
    # But LOD addresses must be adjusted manually for container files

    # After parsing header, adjust each LOD start/end address:
    lod_starts = [reader.read_uint32() + odol_offset for _ in range(n_lods)]
    lod_ends = [reader.read_uint32() + odol_offset for _ in range(n_lods)]
```

**Detection signs of Fire Packer:**
- File starts with zeros (not 'ODOL')
- ODOL signature found at large offset (>1000)
- pbo.json in same PBO contains `"obfuscated": "true"` headers
- Text `"============Fire Packer============"` in PBO headers

## DayZ vs Arma 3 Differences (CRITICAL)

Read `references/format_notes.md` for full details. Summary of key differences:

### 1. ModelInfo — 3 extra fields (v54)
- `allowAnimation` (bool) after `canBeOccluded`
- `forceNotAlpha` as uint32 (not bool) — 3 bytes extra
- `disableCover` (bool) before `animated`

### 2. No hasAnims byte — robust detection required
DayZ v54 sometimes omits the `hasAnims` byte AND can also place Animations
data directly after ModelInfo with no preamble at all (observed on
`dz/gear/containers/55galDrum.p3d` — barrel model, where the byte after
ModelInfo is `0x02` = `n_animations`, not a hasAnims flag).

The simple peek heuristic is NOT enough. `odol_reader.py::ODOL._read` tries
every plausible interpretation and validates by checking that the resulting
LOD address table is internally consistent (every `lod_start[i]` and
`lod_end[i]` inside file bounds, `lod_end >= lod_start`, `permanent[i]`
in `{0, 1}`):

| Candidate | Reads from `saved` | Validates |
|---|---|---|
| **A** | hasAnims byte = 0, LOD addrs at saved+1 | LOD table at saved+1 |
| **B** | hasAnims byte = 1, Animations from saved+1 | LOD table at end of Animations |
| **C** | NO hasAnims byte, Animations directly at saved | LOD table at end of Animations |
| **D** | LOD addrs directly at saved (no anims at all) | LOD table at saved |

Priority: B (canonical Arma 3) > C (DayZ no-byte anims) > A (no-anims byte=0) > D (raw).

### 3. EmbeddedMaterial — extended floats are material-version dependent
After `pixelShader`, before `vertexShader`, BI materials carry a block of extended
floats whose count depends on the **material version** (read per material, distinct
from the ODOL version):
- **v20** (DayZ PBR): 25 floats (100 bytes) + 1 extra uint32 (typically 1).
- **v16** (Arma 2 era, e.g. the Croco quadbike v53): **14 floats** (verified
  2026-05-27 — boundary-exact on FireGeo + visual + wheel-proxy LODs).
- Unknown versions: >=20 default to 25, <20 default to 0 (`{20:25, 16:14}` table in
  `EmbeddedMaterial.read`; extend as new versions are verified).

### 4. BI LZO variant — M4 offset is ODOL-version-dependent
Standard LZO1X subtracts 16384 in the M4 match offset calculation; BI's variant does
not. `decompress_lzo` defaults to the BI variant (`std_m4=False`) and exposes
`std_m4=True` for the standard one. **The correct variant is ODOL-version-dependent**
(verified 2026-05-27 with a 173-model regression sweep over vanilla v54 + v55 + the
Croco v53): ODOL >= 54 (DayZ/Arma 3) needs the BI variant; ODOL <= 53 (Arma 2 era)
needs the standard one. The two are identical for blocks < 16 KB (no long-distance M4
matches are emitted), so small-block LODs decode correctly either way — but a block
> 16 KB decoded with the wrong variant yields garbage vertices while still ending
*boundary-exact* at its `lod_end` (silent corruption). `BisReader._read_lzo`
dispatches by ODOL version (`std_m4 = self.version <= 53`), so large v53 visual
LODs and v54/v55 large blocks use the verified variant.

### 5. LZO trailing EOF marker (consumed-bytes correction)
The pure-Python LZO core can exit at `op == expected_size` mid-instruction
without consuming the 3-byte EOF marker `\x11\x00\x00` that some BI streams
append after the final literal run. The `decompress_lzo` public entry point
peeks for that marker after the core returns and adds 3 to `consumed`
when present. Without this, the off-by-3 contaminates the next field in
the parent stream — e.g. on `55galDrum.p3d` LOD 2 UV0 it caused
`n_uv_sets` to be misread, then a bogus `n_vertices`, then LZO failure on the
next compressed block.

## Compression System

Read `references/format_notes.md` Section 2 for full details.

- **1024 rule** (v < 64): arrays >= 1024 bytes are compressed; smaller are raw
- **Compression flag** (v >= 64): explicit bool before each compressible block
- **LZO** (v >= 44): LZO1X (canonical `lzo1x_decompress` port; BI M4 variant by default)
- **LZSS** (v < 44): LZSS with checksum validation
- **Condensed arrays**: DefaultFill pattern (1 value for all) or compressed array

## v55 Animations desync — scan fallback (added 2026-05-20)

Some DayZ **v55** models desync `Animations.read` (buffer overrun while reading
bones2anims) even when `hasAnims` detection is correct. When the A-D candidates in
Step 2 all fail to validate, `ODOL._read` falls back to a **scan**: starting at
`saved`, it walks forward up to 64 KB and stops at the first offset where
`_try_lod_addrs` validates a clean LOD address chain, fixes the reader there, and
sets `has_anims = False`.

Why this is acceptable for the common case: source animations are not needed to
extract geometry, memory points, or named selections — and on a rig job they get
replaced anyway. This fallback is what unblocked `kt_roadkill_scum.p3d` (6 LODs,
7456 pts in LOD0, 157 selections) and `engine_gun.p3d` (11 LODs).

**Limitation:** the source animations are discarded (`has_anims=False`) — fine for
inspecting or editing geometry, not for preserving the original rig.

## v53 / Arma 2-era support — three fixes (added 2026-05-27)

Verified end-to-end on the Croco `quadbike.p3d` (ODOL **v53**): all 12 LODs parse and
a full MLOD round-trips through py3d. Three independent fixes were needed; the previous
"v28-53 Partial" status was the symptom of all three.

1. **LZO core (correctness, all versions).** The old hand-rolled `lzo_decompress.py`
   desynced on some LZO1X streams (`LZOError: Unexpected t<16 in match sequence`), e.g.
   the Croco Geometry LOD (280-vertex block, expected_size 3360). Replaced with a
   faithful canonical `lzo1x_decompress` port (minilzo). **No regression**: byte-identical
   to the old core on `kt_roadkill_scum.p3d` (v55) across all 6 LODs (vertices +
   selections). This benefits every version, not just v53. Note: the LZO *core* bug (the
   desync) was upstream of any M4 match, so fixing it was variant-independent — but a
   later 173-model sweep (2026-05-27) showed the M4 *variant* still matters for v53
   blocks > 16 KB (large visual LODs): they need the standard variant, not the BI
   default. `BisReader._read_lzo` now dispatches the variant by ODOL version (see
   difference #4).

2. **EmbeddedMaterial v16 (Arma 2-era materials).** Material `version == 16` (Croco
   visual + FireGeo LODs) carries 14 extended floats after `pixelShader` (vs 25 for
   DayZ v20). The reader now gates the count by material version — see DayZ-vs-Arma3
   difference #3. Verified boundary-exact: FireGeo, a visual LOD, and the wheel-proxy
   LOD each end *exactly* at their declared `lod_end`, and FireGeo selections decode to
   real proxy/slot names (`proxy:\...\quadbike_wheel.001`, `wheel_X_X`, `dmgzone_*`).

3. **Per-LOD resilience.** `ODOL._read` wraps each `LOD.read` in try/except: a LOD that
   fails to parse is recorded in `odol.lod_errors[i]` and set to `None` instead of
   aborting the whole model. `odol_to_mlod.convert_odol_to_mlod` skips `None` LODs, so a
   model that desyncs in one LOD still yields a valid **partial MLOD** of every LOD that
   parsed. Robust default for any ODOL with one bad LOD — a vehicle's geometry/memory
   LODs have no materials and survive almost any material-layout issue.

## Fidelity recovery — normals, animations, mass, face-selection map (added 2026-05-27)

The conversion to MLOD preserves more of the original ODOL than a geometry-only
extract. Verified end-to-end on two clean DayZ v54 models, `tradepost_heli.p3d`
(8 LODs, animated) and `tradepost_helipad.p3d` (7 LODs, static):

- **Original per-vertex normals (G2).** ODOL stores one normal per vertex, parallel
  to the vertex array. `convert_lod` dumps those normals straight into the MLOD
  `facenormals` pool and indexes each vertex by its `point_index`, preserving the
  authored smoothing instead of recomputing flat per-face normals. Gated on the
  parallel-array invariant (`len(normals) == n_verts`) and on the LOD having drawable
  sections; otherwise it falls back to the flat recompute. Verified: every MLOD vertex
  normal matches the original (cosine = 1.0) across both models after round-trip.
- **Animations → model.cfg (G3).** MLOD cannot store animations; `emit_model_cfg`
  reconstructs a `CfgSkeletons` + `CfgModels` snippet from `odol.animations` (class
  name, `source`, `type` rotation/translation/hide, `minValue`/`maxValue`, the
  `angle0`/`angle1` or `offset0`/`offset1` endpoints, and the recovered geometric axis
  as a comment). The `selection`/`axis` fields are left as `""` with a TODO: the ODOL
  binds animations to skeleton bones and a geometric axis, not directly to mesh
  selection names, so re-bind them against the model's memory points before shipping.
  Recovered the heli's `Doors1` (rotation, source `doors1`, 0→1, angle1 ≈ -1.92 rad).
- **Mass (G4).** When the binarized ODOL retained a real per-point mass array
  (`model_info.mass_array`, one entry per geometry point), it is copied faithfully.
  **Finding:** binarization usually STRIPS this array — it was empty on every model
  checked (tradepost_heli/helipad v54, Croco quadbike + wheels v53), leaving only the
  scalar total mass + center-of-mass + inertia tensor. In that (common) case the
  converter falls back to distributing the total uniformly, which conserves the total
  exactly (sum of per-point mass == `model_info.mass`). So the per-point path is
  correct-when-present but rarely exercised by real binarized files.
- **Section-aware face-selection map (G7).** `dst.faces` is built in section order,
  which need not match ODOL face order. Face-based selections now resolve through an
  `odol_face_index → MLOD Face` map built during section iteration, instead of the
  naive `dst.faces[fi]`. On the two fixtures face order already coincides with section
  order (so output is unchanged), but a synthetic reversed-section fixture confirms the
  map picks the correct face where the direct index would pick the wrong one.

Vertex-selection membership (SP-001) is preserved unchanged; selection point/face sets
are byte-for-byte identical to the previous converter on v53+v54 models (no regression).

## Regression coverage (2026-05-27)

The canonical LZO core was validated against the previous hand-rolled core across a
173-model sweep — 154 vanilla v54 + 13 v55 + 6 v53 (Croco) — with two oracles:
old-vs-new byte-identity per LZO block, and structural validity (each parsed LOD ends
*boundary-exact* at its `lod_end`; vertices within the LOD bbox). On every block the
old core could decode, the new core is byte-identical; 0 boundary mismatches. **16
vanilla v54 models contain decompressed blocks > 400 KB (up to 786 KB) and decode
correctly — there is no large-block size limit with the canonical core.** The former
large Croco v53 visual-LOD divergences are resolved by version-dependent M4 dispatch.
Reusable harness: `<vault>\AI\20_Knowledge\skills-drafts\dayz-p3d-debinarizer-v53-lzo-fix\regression\regression_harness.py`.

## Known Limitations

1. **Named selections** from bone-based reconstruction not implemented (ODOL sections + vertex weights work)
2. **Face winding** is reversed during conversion (ODOL→MLOD) — may need manual flip in Object Builder
3. **UV coordinates** use the first UV set only; additional UV sets are dropped
4. **Proxy geometry** appears as named selections (correct behavior for MLOD)
5. **Mass distribution** uses the real per-point array (`model_info.mass_array`) when the binarized ODOL retained it; binarization usually strips it (empty on every v53/v54 model checked), so the common path is uniform distribution that conserves the total exactly (see "Fidelity recovery", G4)
6. **Source animations dropped on v55 scan-fallback** — when the Animations parser desyncs (some v55 models), the scan-fallback skips them (`has_anims=False`); geometry/memory/selections are preserved but the original rig is not
7. **Material versions other than 16/20** carry an unverified extended-float count — extend the `{20:25, 16:14}` table when a new version is encountered (a wrong count desyncs that LOD, but per-LOD resilience keeps the rest). The 173-model regression sweep (2026-05-27) saw only v20 (all vanilla v54/v55) and v16 (Croco v53) — no other material version appeared in the vanilla corpus
8. **v53 large visual LODs (>16 KB blocks) are supported with version-dependent M4 dispatch.** `BisReader._read_lzo` passes `std_m4=True` for ODOL <= 53 and keeps `std_m4=False` for ODOL >= 54; Croco LOD0/LOD1/LOD7 no longer produce garbage vertices, and the v54/v55 regression sweep remains byte-identical

## Dependencies

| Package | Purpose | Install |
|---------|---------|---------|
| py3d (fork DayZ >= 1.5.0) | MLOD P3D writing | `pip install -e tools/py3d` (NUNCA `pip install py3d`) |

**Note:** LZO is handled entirely by the bundled pure-Python `lzo_decompress.py` (canonical `lzo1x_decompress` port) — it decodes every block in the 173-model vanilla corpus. The old `python-lzo` native fallback was removed 2026-05-27: liblzo2 never builds in the Cowork sandbox, so the branch was dead code (R25).

## Version Support

| Version | Game | Status |
|---------|------|--------|
| v53 | Arma 2-era (DayZ ports, e.g. Croco) | ✅ Supported for verified Croco v53 fixture: Geometry/Memory/LandContact/FireGeo + large visual LODs decode with LZO core + version-dependent M4 + v16 material + per-LOD resilience |
| v54 | DayZ Standalone | ✅ Full support |
| v55 | DayZ Standalone | ✅ geometry/memory/selections (v55 scan-fallback; source anims dropped) |
| v28-52 | Arma 2/3 | ⚠️ Same core + per-LOD resilient, but older material/LOD layouts not version-tested |
| v56-73 | Arma 3 latest | ⚠️ Untested |
| v7 | OFP | ❌ Not supported |

## (added 2026-06-05) Comparing a source MLOD vs a binarized reference is not apples-to-apples (SP-016)

When using the debinarizer to compare an OWN model (typically a source MLOD) against a working
REFERENCE model (typically the binarized ODOL from the reference PBO), do NOT compare the
source-MLOD directly against the binarized-ODOL: some elements differ only by binarization state,
not by design. Verified empirically (LFQuad v55 vs its own source MLOD): entire LODs (FireGeo,
ViewGeo), auto-authored selections, named properties, and the convexity points
(ce_center/ce_radius/boundingbox_min/max/invview) are NOT auto-generated on binarize — AddonBuilder
binarizes what the MLOD has; it does not invent missing LODs or convexity points.

Operational rule: for a reliable parity comparison, debinarize the binarized form of BOTH models
(own + reference) and compare ODOL-vs-ODOL; or know that for authored elements
(LODs/selections/named-properties) the source MLOD is already faithful. Origin: SP-016, LFQuad
2026-05-27 (vault skill-patches-pending.md).
## (added 2026-06-05) How to validate a fork/port of the debinarizer core (SP-018)

Byte-vs-byte against a baseline is NOT enough if the baseline was buggy. Two real escapes on
2026-05-27: SP-001 was silently reverted in a fork branched before the fix; SP-014 (M4 variant)
passed "byte-identical old-vs-new" because both cores shared the same bug. When forking/porting the
core or any module:

1. Regression vs HEAD, not vs fork-base: before repackaging, list the files the branch modified and
   diff ALL non-modified files against the most recent shipped .skill. Any unexpected diff in an
   untouched file means a stale base — re-merge before shipping.
2. Independent structural oracle: byte-vs-byte cannot catch a baseline bug. Add a domain oracle
   (verts inside bbox, boundary-exact at lod_end, valid schema) that classifies each block into
   {PASS_IDENTICAL, IMPROVEMENT, REGRESSION, DIVERGENCE}; the 4th class triggers investigation.
3. Collateral coverage: run the regression harness
   (`<vault>\AI\20_Knowledge\skills-drafts\dayz-p3d-debinarizer-v53-lzo-fix\regression\regression_harness.py`) also over
   areas NOT touched by the branch (selection-membership transfer, model.cfg emit, mass mapping,
   face-index mapping) — not only the touched area. Origin: SP-018, LL-046/LL-047.

## Known limitation — vanilla CHARACTER bodies (SP-034)

`ODOL.from_file` + `convert_odol_to_mlod` on vanilla character bodies v54 (e.g.
`DZ\characters\zombies\soldier_normal_m.p3d`) produces a visual LOD with a NON-human
bounding box (span 4.615 x 3.006 x 3.085 vs ~1.8 m real). Verified identical with the
py3d fork 1.3.0 and with a direct `odol_reader` pass. The skinning WEIGHTS do decode
correctly. Probable cause: the packed-vertex unpack of character visual LODs uses the
wrong scale factor (vehicles/props decode correctly). Workaround: take the body from
the `Male_body` mesh of `animation_rig_character.fbx` (Blender) — positions and weights
are correct there. Cross-ref: skill `dayz-characters` §addendum 2026-06-28.

## Reglas promovidas del corpus de lecciones (added 2026-07-27)

Promovidas desde `AI/20_Knowledge/lessons-learned.md` para que lleguen por trigger en vez
de depender de que alguien recuerde buscarlas. Cada regla cita su `LL-NNN` de origen;
la entrada completa vive allí. No quites la cita: el índice detecta la promoción por ella.

- **LL-107** — Antes de empaquetar un campo `Ns` terminado en NUL, valida que su UTF-8 ocupe como máximo `N-1` bytes. Rechaza o avisa al leer exactamente N bytes: es una huella de truncado.
