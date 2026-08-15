# py3d-dayz

Read and write Arma / DayZ `.p3d` models in their unbinarized **MLOD** form,
from Python. No dependencies, pure stdlib.

This is a maintained fork of [KoffeinFlummi/py3d](https://github.com/KoffeinFlummi/py3d)
by Felix "KoffeinFlummi" Wiegand (MIT, last released in 2018). The original is a
compact, correct MLOD codec and it is still the foundation of this code — its
copyright notice is preserved verbatim in [LICENSE](LICENSE).

> **The importable module is still `py3d`.** Only the *distribution* name
> differs, because `py3d` on PyPI is an unrelated 3D library. So `import py3d`
> keeps working, and `py3d.IS_DAYZ_FORK` lets a script assert it got this one.

## Why a fork

Upstream is a minimal codec: it assumes well-formed input and trusts the caller.
That is a reasonable design, but in a modding pipeline the input is frequently
*not* well formed — a half-written export, a mesh straight out of Blender, a
selection rebuilt by hand. This fork adds two things on top:

1. **Guards.** Paths that used to corrupt a `.p3d` silently, or blow up much
   later with an unrelated error, now fail early with a message that names the
   offending selection, property or LOD.
2. **A DayZ model validator.** `P3D.validate()` returns a list of `Finding`s
   about things that are legal MLOD but wrong for DayZ.

## Install

```bash
pip install git+https://github.com/willy92wins/py3d-dayz
```

Verify you imported the right library:

```python
import py3d
assert py3d.IS_DAYZ_FORK
```

## Quick start

```python
import py3d

with open("crate.p3d", "rb") as f:
    model = py3d.P3D(f)

for lod in model.lods:
    print(lod.kind(), lod.resolution, len(lod.points), len(lod.faces))

for finding in model.validate():
    print(finding.severity, finding.code, finding.msg)

model.save("crate_out.p3d")          # atomic write + verify + optional backup
```

Command line:

```bash
python -m py3d info     model.p3d    # LODs, counts, selections, memory points
python -m py3d validate model.p3d    # validator findings; exit 1 if any ERROR
python -m py3d diff     a.p3d b.p3d  # structural comparison
```

## What this fork adds

**Correctness guards**
- Selection weights validated on write, naming the selection that is wrong.
- `#Property#` keys/values over 63 UTF-8 bytes raise instead of being silently
  truncated (a 64-byte value loses its NUL terminator and corrupts the reader).
- Stale selections — bound to lists that were replaced — raise instead of
  silently losing their membership.
- `P3D.save(path, verify=True, backup_dir=...)`: atomic write, reopened and
  re-parsed before replacing the original.

**DayZ knowledge**
- Canonical LOD resolutions and `LOD.kind()` / `P3D.get_lod("geometry")`.
  Note DayZ does **not** use the Arma-3-era `e13` ids for FireGeo/ViewGeo:
  they are `7e15` and `6e15`. Getting this wrong means bullets pass through
  your model.
- `P3D.validate()` reports missing/misnamed `Component01`, `#Mass#` outside the
  Geometry LOD, non-watertight collision, degenerate faces, memory-point
  structure, winding problems, and more.

**Editing helpers**
- `bbox`, `triangulate`, `set_selection`, `set_total_mass`, `set_memory_point`,
  `make_double_sided`, `transform` (with `py3d.BLENDER_TO_DAYZ`).
- A full proxy lifecycle: `add_proxy` / `get_proxies(strict=True)` /
  `align_proxy` / `remove_proxy`, with explicit raw↔engine frame conversion.

**Write contract.** For valid canonical input the bytes written are identical to
what upstream writes. Where upstream would have corrupted the file or crashed
later, this fork raises instead. Do not assume `input_bytes == output_bytes` for
input that was not canonical to begin with.

## Winding: read this before trusting any validator

The single most common way to break a DayZ model is to export from Blender
(Z-up) to DayZ (Y-up) without reordering face vertices. Handedness flips, the
texture becomes visible only from *inside*, and raycasts pass through.

This fork checks winding two ways:

- **Absolute** (`ERR_WINDING_VS_NORMALS`): does each face's winding agree with
  its own declared normal? Both vectors live in the same space, so this is
  immune to the left-handed/right-handed confusion.
- **Relative** (`ERR_WINDING_INVERTED`): is a collision LOD wound the opposite
  way from the Visual LOD?

The relative check alone **cannot** see a model where *every* LOD is inverted —
everything is consistent with everything else. That is exactly what the bad
export produces, which is why the absolute check exists.

The correct fix for an inverted face is always `face.vertices.reverse()`.
Do **not** swap `vertices[1]` and `vertices[2]`: that inverts a triangle but
turns a quad `[0,1,2,3]` into `[0,2,1,3]`, a crossed face.

## Status and known issues

The library is used in a real modding pipeline, and 213 tests pass. It has also
been through a deliberately adversarial audit, and **not every problem it found
is fixed yet**. Before relying on this for anything you cannot redo, read
[KNOWN-ISSUES.md](KNOWN-ISSUES.md) — in particular the entries about
`save(verify=True)`, `python -m py3d diff` and the Recipe JSON round-trip, which
are weaker than their names suggest.

## Tests

```bash
python -m pytest -q

# The CANON tests compare byte-for-byte output against upstream and are
# skipped unless you point them at a local clone of it:
PY3D_UPSTREAM_PATH=/path/to/KoffeinFlummi/py3d python -m pytest -q
```

Fixtures are synthetic — no Bohemia Interactive assets are included or required.

## License

MIT, same as upstream. Copyright (c) 2017 Felix Wiegand for the original work;
see [LICENSE](LICENSE). Fork maintained by [@willy92wins](https://github.com/willy92wins).
