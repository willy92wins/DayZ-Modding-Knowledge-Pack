"""Contract helpers for the tests: byte-identity against upstream, and
the semantic invariants of a round trip."""

import hashlib
import io
import struct

FRAC = 1.0 / 255.0  # resolution of the fractional weight encoding


def f32(x):
    """Round-trip float64 -> float32: what survives struct 'f'."""
    return struct.unpack("f", struct.pack("f", x))[0]


def write_bytes(p3d):
    buf = io.BytesIO()
    p3d.write(buf)
    return buf.getvalue()


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def read_p3d(m, data):
    return m.P3D(io.BytesIO(data))


def _sel_indices(lod, sel):
    pts = sorted(lod.points.index(p) for p in sel.points)
    fcs = sorted(lod.faces.index(fa) for fa in sel.faces)
    return pts, fcs


def _assert_weight(expected, got, ctx):
    if isinstance(expected, float) and expected in (0.0, 1.0):
        expected = int(expected)  # the fork coerces these on write
    if isinstance(expected, int):
        assert got == expected, \
            "%s: integer weight %r came back as %r" % (ctx, expected, got)
    else:
        assert abs(got - expected) <= FRAC + 1e-9, \
            "%s: fractional weight %r came back as %r" % (ctx, expected, got)


def assert_sem_inv(m, model, data=None):
    """Write -> reopen -> invariants against the in-memory model.

    Per LOD: counts, resolution (f32), coordinates (f32), faces
    (vertices, texture, material, uv), selections (names, POSITIONAL
    membership, exact integer weights or fractional ones to +-1/255),
    properties, and total mass to +-1e-3.
    """
    if data is None:
        data = write_bytes(model)
    reread = read_p3d(m, data)

    assert len(reread.lods) == len(model.lods), \
        "the number of LODs changed across the round trip"

    for li, (a, b) in enumerate(zip(model.lods, reread.lods)):
        ctx = "LOD[%d]" % li
        assert b.resolution == f32(a.resolution), ctx + ": resolution"
        assert len(b.points) == len(a.points), ctx + ": n points"
        assert len(b.facenormals) == len(a.facenormals), ctx + ": n facenormals"
        assert len(b.faces) == len(a.faces), ctx + ": n faces"

        for pi, (pa, pb) in enumerate(zip(a.points, b.points)):
            want = tuple(f32(c) for c in pa.coords)
            assert pb.coords == want, "%s point[%d] coords" % (ctx, pi)

        for fi, (fa, fb) in enumerate(zip(a.faces, b.faces)):
            fctx = "%s face[%d]" % (ctx, fi)
            assert len(fb.vertices) == len(fa.vertices), fctx + ": n vertices"
            assert fb.texture == fa.texture, fctx + ": texture"
            assert fb.material == fa.material, fctx + ": material"
            for vi, (va, vb) in enumerate(zip(fa.vertices, fb.vertices)):
                assert vb.point_index == va.point_index, fctx + ": point_index"
                want_uv = tuple(f32(u) for u in va.uv)
                assert vb.uv == want_uv, fctx + " v[%d]: uv" % vi
                for k, uv in getattr(va, "uv_sets", {}).items():
                    want = tuple(f32(u) for u in uv)
                    assert vb.uv_sets.get(k) == want, \
                        fctx + " v[%d]: uv set %r" % (vi, k)
        if hasattr(a, "uv_set_ids"):
            assert b.uv_set_ids() == a.uv_set_ids(), ctx + ": uv_set_ids"

        assert list(b.selections.keys()) == list(a.selections.keys()), \
            ctx + ": selection names or their order"
        for name in a.selections:
            sa, sb = a.selections[name], b.selections[name]
            pa_idx, fa_idx = _sel_indices(a, sa)
            pb_idx, fb_idx = _sel_indices(b, sb)
            sctx = "%s selection '%s'" % (ctx, name)
            assert pb_idx == pa_idx, sctx + ": point membership"
            assert fb_idx == fa_idx, sctx + ": face membership"
            for p, w in sa.points.items():
                w2 = sb.points[b.points[a.points.index(p)]]
                _assert_weight(w, w2, sctx)
            for fc, w in sa.faces.items():
                w2 = sb.faces[b.faces[a.faces.index(fc)]]
                _assert_weight(w, w2, sctx)

        assert dict(b.properties) == dict(a.properties), ctx + ": properties"

        if a.mass is None:
            assert b.mass is None, ctx + ": mass should be None"
        else:
            assert b.mass is not None and abs(b.mass - a.mass) <= 1e-3, \
                ctx + ": Smasa (%r vs %r)" % (a.mass, b.mass)

    return reread


# ---- UV sets (1.6.0) ---------------------------------------------------------

# The empty #UVSet# tag Object Builder writes for a LOD without faces: active
# byte, name, 4-byte payload length, 4-byte set id 0.
EMPTY_UVSET_TAG = b"\x01#UVSet#\0" + struct.pack("<L", 4) + struct.pack("<L", 0)
EOF_TAG = b"\x01#EndOfFile#\0"


def _asciiz(f):
    out = bytearray()
    while True:
        b = f.read(1)
        if not b:
            raise EOFError("unterminated asciiz")
        if b == b"\0":
            return out.decode("utf-8")
        out += b


def scan_taggs(data):
    """Independent MLOD walker (does not use py3d): per LOD, the ordered list
    of (tag name, payload size, uv set id or None). The instrument that
    counts #UVSet# tags must not share the reader under test."""
    f = io.BytesIO(data)
    assert f.read(4) == b"MLOD"
    _, nlods = struct.unpack("<LL", f.read(8))
    lods = []
    for _ in range(nlods):
        assert f.read(4) == b"P3DM"
        _, _, npts, nnrm, nfaces = struct.unpack("<LLLLL", f.read(20))
        f.seek(4, 1)
        f.seek(16 * npts + 12 * nnrm, 1)
        for _ in range(nfaces):
            nv = struct.unpack("<L", f.read(4))[0]
            f.seek(16 * nv + (16 if nv == 3 else 0) + 4, 1)
            _asciiz(f)
            _asciiz(f)
        assert f.read(4) == b"TAGG"
        taggs = []
        while True:
            f.read(1)
            name = _asciiz(f)
            size = struct.unpack("<L", f.read(4))[0]
            payload = f.read(size)
            uv_id = None
            if name == "#UVSet#":
                uv_id = struct.unpack("<L", payload[:4])[0]
            taggs.append((name, size, uv_id))
            if name == "#EndOfFile#":
                break
        f.read(4)  # resolution
        lods.append(taggs)
    assert f.read() == b"", "trailing bytes after the last LOD"
    return lods


def uvset_inventory(data):
    """Per LOD: list of (uv set id, payload size) in file order."""
    return [[(uv_id, size) for name, size, uv_id in taggs if name == "#UVSet#"]
            for taggs in scan_taggs(data)]
