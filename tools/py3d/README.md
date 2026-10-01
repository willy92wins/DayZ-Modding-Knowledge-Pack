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
  `make_double_sided`, `transform`.
- `blender_to_dayz(model)`: a model authored in Blender, converted to DayZ's
  frame without mirroring it. See [Blender → DayZ](#blender--dayz).
- A full proxy lifecycle: `add_proxy` / `get_proxies(strict=True)` /
  `align_proxy` / `remove_proxy`, with explicit raw↔engine frame conversion.

**Format fidelity**
- Every `#UVSet#` beyond the first is read into `Vertex.uv_sets` and written
  back in id order. Upstream dropped them on save: a skinned body that carried
  two UV sets lost the second one (4,761,261 → 4,409,836 bytes).
- A LOD without faces (Memory, LandContact) gets the empty `#UVSet#` tag that
  Object Builder writes and BI-authored files carry; upstream omitted it.
- The editor's current selection (`#Selected#`) is read into `LOD.selected` and
  written back with its payload intact, in the slot Object Builder writes it in
  (after `#SharpEdges#`, before the named selections). Upstream dropped it:
  re-saving `WeaponSpecialLODs.p3d` lost 202 bytes and `InfectedSpecialLODs.p3d`
  863. It is editor state, not model data -- `binarize.exe` discards it
  (measured; see KNOWN-ISSUES) -- but Object Builder preserves it verbatim, so
  dropping it silently discards the user's selection.
- `save(verify=True)`, `info` and `diff` compare the UV set ids of every LOD and
  the presence and membership of `#Selected#`.

**Write contract.** For valid canonical input the bytes written are identical to
what upstream writes, with two deliberate exceptions: a LOD without faces gets
the empty `#UVSet#` tag (17 bytes) that upstream omits, and `#Selected#` is
written back where upstream dropped it. Where upstream would have corrupted the
file or crashed later, this fork raises instead. A file written by Object
Builder survives a read/write cycle byte for byte; a file written by BI may not,
because tags are written in this library's order -- which is the order Object
Builder itself writes, and not always the source file's.

## Blender → DayZ

```python
import py3d

model = py3d.P3D()
# ... fill model.lods with points, faces and normals exactly as Blender has
# them: Blender coordinates, faces counter-clockwise seen from outside,
# outward normals ...
py3d.blender_to_dayz(model)   # once, before adding anything built in DayZ space
model.save("thing.p3d")
```

Blender is right-handed (Z up, front at −Y) and DayZ left-handed (X east, Y up,
Z north). A conversion that keeps the shape is therefore a reflection in the
numbers, `(x, y, z) → (x, z, y)`, determinant −1. That reflection on its own
already puts the faces in the MLOD order — vertex-order cross product pointing
inward — so `blender_to_dayz` keeps every face's vertex order and only negates
the normals, which MLOD also stores pointing inward. Measured in game on
2026-10-01 (DayZDiag 1.29.163709) with one chiral model, an "F" in relief on a
plate, written three ways and binarized with AddonBuilder:

| how the model was written | in game |
|---|---|
| `py3d.blender_to_dayz(model)` | solid, the F reads correctly |
| `model.transform(py3d.ROT_X_NEG90)`, then every face reversed and every normal negated | solid but **mirrored** |
| `model.transform(py3d.ROT_X_NEG90)` alone — the usage this README gave up to 1.7.0 | inside-out **and** mirrored |

The mirrored model passes the winding checks — vertex order against normals,
inward per component — so only an asymmetric feature shows the mirror.
Proxy frames were not part of that test: `blender_to_dayz` moves proxy
triangles like any other face and warns when the model has `proxy:`
selections. Add proxies after the conversion with
`add_proxy(..., space="engine")` where you can.

**Migrating from `py3d.BLENDER_TO_DAYZ`.** Up to 1.7.0 this README gave
`model.transform(py3d.BLENDER_TO_DAYZ)`, the det=+1 rotation `(x, z, −y)`, as
the Blender → DayZ step. It mirrors the model. From 1.8.0:

- geometry authored in Blender: call `py3d.blender_to_dayz(model)` instead;
- code that needs the rotation itself — for instance to undo a det=+1 export
  `(x, −z, y)` from DayZ to Blender, where the mirror cancels out — uses
  `py3d.ROT_X_NEG90`, the same matrix under a name that says what it is.

`py3d.BLENDER_TO_DAYZ` still holds that same matrix, so no model changes shape
behind your back, and every read of it raises a `FutureWarning` that says the
above.

## Winding: read this before trusting any validator

The single most common way to break a DayZ model is a Blender (Z-up) to DayZ
(Y-up) export whose face order or normal sign does not match its axis map: the
texture becomes visible only from *inside*, and raycasts pass through. (The
other common way, a mirrored model, is invisible to every check below; see
[Blender → DayZ](#blender--dayz).)

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

The library is used in a real modding pipeline, and 278 tests pass -- 271 of them
on a plain `pytest` run, plus the 7 CANON tests that need a local clone of
upstream (see [Tests](#tests)). It has also been through a deliberately
adversarial audit, and **not every problem it found is fixed yet**. Before
relying on this for anything you cannot redo, read
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
