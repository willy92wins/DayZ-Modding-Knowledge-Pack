# Known issues

This library was put through a deliberately adversarial audit in August 2026 —
several independent reviewers, each reproducing findings by executing code
rather than reading it. What follows is what that audit found and what is still
open. It is published in full, unflattering parts included, because a modelling
tool that hides its blind spots is worse than one that has none.

Fixed items are listed at the bottom.

---

## Do not use these as approval gates

The three issues below share one shape: **an instrument that cannot fail for the
reason you care about.** A clean result from any of them is not evidence.

### `save(verify=True)` does not verify geometry

`_verify_against` compares LOD counts, point/face counts, selection names and
total mass. It does **not** compare coordinates, UVs, winding, indices, normals,
flags, materials or textures.

Reproduced: two models identical except for one point at `(0,0,0)` vs
`(99,99,99)` — verify passes. It also accepts out-of-range point indices.

*Use it as a "the file is structurally re-readable" check, not as proof that
what you wrote is what you meant.*

### `python -m py3d diff` reports "equal" for materially different models

Same root cause. The same `(0,0,0)` vs `(99,99,99)` pair prints `total: 0` and
exits 0. Since 1.6.0 it does compare the UV set ids of every LOD, so a dropped
UV set is no longer invisible to it; coordinates and UV values still are.

*Do not use `diff` to verify that an edit did what you intended.*

### `tools/audit_p3d.py` can print `ALL PASSED` when nothing was checked

The wrapper returns exit 0 and `OVERALL: ALL PASSED` when given no inputs, when
pointed at a directory that does not exist, and even after printing a read error
for a file it could not open. Warnings also end in exit 0.

*Check that the file count in its output is what you expected.*

---

## Data-loss risks

### Recipe JSON (`to_dict` / `from_dict`) is lossy — not a persistence format

- The Recipe classifier disagrees with `LOD.kind()`. A Visual LOD with
  `resolution=16` round-trips into a **ShadowVolume at 10000.0**, losing its
  textures, materials and UVs.
- `from_dict()` writes `#Mass#` into FireGeometry LODs, which `validate()` then
  correctly rejects — and which makes the binarizer bake a wrong centre of mass.
- Visual LOD resolutions are snapped to a canonical table, so two distinct
  visual levels can collapse onto one.
- Selection membership is recorded as indices into the original arrays and
  re-applied to a rebuilt, deduplicated array, so named selections on visual
  LODs can end up pointing at different geometry.
- Additional UV sets (`Vertex.uv_sets`) are not part of the Recipe schema;
  `from_dict()` rebuilds a model with set 0 only.

*Use Recipe for inspection. Use the `.p3d` itself for persistence.*

### `write()` straight to an open file can destroy the previous file

The guards validate **inside** `write()`, by which point `open(path, "wb")` has
already truncated the target. The resulting partial file is unreadable.

`save()` is **not** affected — it writes to a temporary file first and the
original survives intact. Verified both ways.

*Prefer `save()`. Reserve `write()` for streams you own.*

### `transform()` applies the matrix twice to points shared between LODs

It iterates per LOD and mutates `Point` objects in place, so a point present in
two LODs is transformed once per LOD. `(0,1,0)` ends up at `(0,-1,0)` instead of
`(0,0,-1)`, and `save(verify=True)` accepts the result.

### `make_double_sided()` breaks proxies

The generated twin face is added to *every* selection that contained the
original, so a proxy selection goes from one face to two and
`get_proxies(strict=True)` / `align_proxy()` then raise.

*Run it before adding proxies, or on LODs that have none.*

---

## Silent wrong answers

- **Selection weights below `w ≈ 0.00196` cannot be written.** Validation accepts
  any float in `(0,1)`, but the encoder computes `round((1-w)*255)+1`, which
  overflows a byte and raises `ValueError` at write time.
- **`set_selection(name, face_idx=0)` silently produces an empty selection**,
  because `face_idx or ()` treats the integer `0` as empty. `face_idx=[0]` works.
- **A selection whose name contains `#` corrupts the file.** Writing is allowed;
  on read, a name like `#EndOfFile#` terminates the tag loop early, leaving the
  LOD with a garbage resolution and no selections.
- **`validate()` raises `IndexError` on out-of-range point indices** instead of
  reporting a finding, so a corrupt file crashes the validator.
- **N-gons (>4 vertices) can be written but not read back.** `save(verify=True)`
  correctly refuses; `verify=False` leaves an unreadable file.
- **`Selection.read` ignores the declared `num_bytes`** and the MLOD version
  field is ignored on read and always written as 257.
- **Watertight only flags edges used once**, so an edge shared by three or more
  faces passes as watertight.
- **All format validation uses bare `assert`**, so running under `python -O`
  disables it — and because the asserts also advance the stream, valid files
  fail to load. The user-facing error is an empty `AssertionError`.
- **Floats are read/written in native byte order** while integers are explicit
  little-endian. Harmless on x86; wrong on a big-endian host.

## Compatibility

- **`Selection(list(lod.points), list(lod.faces))` now raises** where upstream
  accepted it and wrote byte-identical output. The guard tests list *identity*
  when the bug it targets is one of *length*. This is the fork's one true
  behavioural regression against upstream.

---

## Fixed

- **Additional UV sets were dropped on save, and point-only LODs lost their
  `#UVSet#` tag.** `LOD.read` discarded every `#UVSet#`, and `LOD.write`
  emitted set 0 only, and only when the LOD had faces. Measured on a skinned
  body with two UV sets: 4,761,261 → 4,409,836 bytes and the second set gone;
  the Memory LOD of a BI-authored file lost its 4-byte `#UVSet#`. Sets beyond
  the first now live in `Vertex.uv_sets` and are written back in id order; a
  LOD without faces gets the empty tag Object Builder writes; a payload whose
  length does not match the faces, or a set id declared twice, raises on
  read. Still not preserved: the source file's tag order and editor-state
  tags (`#Selected#`).
- **Infinite hang on an unterminated string.** `_read_asciiz` looped forever
  when a file reached EOF without a NUL byte — the process hung with no
  traceback, which no caller could catch. Inherited from upstream; a truncated
  `.p3d` is the normal way to hit it. Now raises, naming the offset.
- **The validator recommended a fix that corrupts quads.** `ERR_WINDING_INVERTED`
  advised swapping `vertices[1]` and `vertices[2]`, which inverts a triangle but
  turns a quad `[0,1,2,3]` into `[0,2,1,3]` — a crossed face. It now recommends
  `face.vertices.reverse()` and warns against the swap.
- **Globally inverted winding was invisible.** The only winding check was
  relative to the Visual LOD, so inverting *every* LOD — precisely what a Z-up to
  Y-up export does — left the model self-consistent and `validate()` returned
  `[]`. Two order-independent signals were added: agreement between winding and
  each face's own declared normal, and edge-traversal coherence between
  neighbouring faces. Neither assumes convexity nor a handedness convention.
  Measured at 100% on 15 vanilla LODs (1274/1274 faces), where the old
  centroid-based measure ranged from 0% to 31.8% without meaning anything.
- **The relative check used the wrong reference LOD** — the first visual LOD in
  file order rather than the one with the lowest resolution, so LOD ordering on
  disk changed the verdict.
