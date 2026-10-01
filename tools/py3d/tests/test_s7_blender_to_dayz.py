"""Blender -> DayZ: blender_to_dayz(), ROT_X_NEG90 and the deprecated
BLENDER_TO_DAYZ.

The fixture is the model of the in-game test of 2026-10-01 (DayZDiag
1.29.163709): an "F" in relief on a plate, authored in Blender space -
right-handed, Z up, front at -Y, faces counter-clockwise seen from outside
and outward normals - written three ways and binarized with AddonBuilder:

  B  blender_to_dayz()                                  solid, the F reads
  A  ROT_X_NEG90, then faces reversed, normals negated  solid but MIRRORED
  C  transform(ROT_X_NEG90) alone                       inside-out AND mirrored

MEASURED holds the SHA-256 of the three MLODs that were binarized and looked
at in game, and the fixture below rebuilds them byte for byte, so these
tests are about the geometry the game showed, not about a lookalike. A and C
are the negative controls: each property check has to fail on at least one
of them, or it is not checking anything.
"""

import hashlib
import math
import warnings

import pytest

from builders import build_chiral_f_p3d, build_multilod_v2_p3d
from helpers import f32, read_p3d, write_bytes

MEASURED = {
    "A": "b08372a6248d826aad7557827346af030b1d448e4e0d75da3afd0a67a0c16d27",
    "B": "f1be491df6304534f2100d053e972a9792b1780e026223408f5c200b465201d7",
    "C": "ac5f0f77f6d93db93226e631ed0b02c3492c6e13d815a621bd9ed82e2b4e1da8",
}
PLATE, STEM, TOP_ARM, MID_ARM = range(4)
BLENDER_UP = (0.0, 0.0, 1.0)
DAYZ_UP = (0.0, 1.0, 0.0)
PROXY = "proxy:\\dz\\data\\proxies\\flag.001"


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def centroid(pts):
    return tuple(sum(p[i] for p in pts) / len(pts) for i in range(3))


def close3(a, b, tol=1e-9):
    return all(abs(x - y) <= tol for x, y in zip(a, b))


def variant(m, tag):
    """The fixture, written the way the in-game test wrote variant *tag*."""
    p3d = build_chiral_f_p3d(m)
    if tag == "B":
        m.blender_to_dayz(p3d)
    elif tag == "A":
        p3d.transform(m.ROT_X_NEG90)
        for lod in p3d.lods:
            for fa in lod.faces:
                fa.vertices.reverse()
            for i, n in enumerate(lod.facenormals):
                lod.facenormals[i] = (-n[0], -n[1], -n[2])
    elif tag == "C":
        p3d.transform(m.ROT_X_NEG90)
    return p3d


def box_points(lod, box):
    return [p.coords for p in lod.points[8 * box:8 * box + 8]]


def inward_counts(p3d):
    """(faces, cross product inward, normal inward). Inward is measured
    against the centroid of the face's own box, and every box is convex."""
    lod = p3d.lods[0]
    faces = cross_in = normal_in = 0
    for fa in lod.faces:
        vs = [v.point.coords for v in fa.vertices]
        out = sub(centroid(vs),
                  centroid(box_points(lod, fa.vertices[0].point_index // 8)))
        cr = cross(sub(vs[1], vs[0]), sub(vs[2], vs[0]))
        faces += 1
        cross_in += dot(cr, out) < 0
        normal_in += dot(fa.vertices[0].normal, out) < 0
    return faces, cross_in, normal_in


def screen_right(toward_viewer, up, left_handed):
    """Screen-right for a viewer facing -toward_viewer with *up* up.

    Right-handed coordinates: up x toward_viewer - Blender's front view,
    looking along +Y, has +X on the right. Left-handed coordinates (DayZ:
    X east, Y up, Z north) give the same direction as toward_viewer x up,
    because there the arithmetic cross product follows the left hand:
    looking north from the south, +X - east - is on the right, as on a map.
    """
    if left_handed:
        return cross(toward_viewer, up)
    return cross(up, toward_viewer)


def reading(p3d, up, left_handed):
    """'F' or 'mirrored F', seen face-on from the side carrying the relief."""
    lod = p3d.lods[0]
    plate = box_points(lod, PLATE)
    glyph = [p for box in (STEM, TOP_ARM, MID_ARM)
             for p in box_points(lod, box)]
    size = [max(p[i] for p in plate) - min(p[i] for p in plate)
            for i in range(3)]
    depth = size.index(min(size))
    toward_viewer = [0.0, 0.0, 0.0]
    toward_viewer[depth] = (1.0 if centroid(glyph)[depth]
                            > centroid(plate)[depth] else -1.0)
    arms = sub(centroid(box_points(lod, TOP_ARM) + box_points(lod, MID_ARM)),
               centroid(box_points(lod, STEM)))
    right = screen_right(tuple(toward_viewer), up, left_handed)
    return "F" if dot(arms, right) > 0 else "mirrored F"


# ---- the fixture is the model the game showed ---------------------------

def test_b2d_writes_the_measured_bytes(fork):
    """blender_to_dayz() writes exactly the MLOD that rendered solid with a
    correctly reading F in game; the two control recipes write exactly the
    two that rendered mirrored."""
    for tag in "BAC":
        data = write_bytes(variant(fork, tag))
        assert hashlib.sha256(data).hexdigest() == MEASURED[tag], tag


def test_b2d_screen_right_rule(fork):
    """The viewing rule the chirality check rests on, against two facts:
    Blender's front view has +X on the right, and in DayZ +X is east, on
    the right of a viewer facing north. It predicted A and B correctly in
    game."""
    assert screen_right((0.0, -1.0, 0.0), BLENDER_UP, False) == (1.0, 0.0, 0.0)
    assert screen_right((0.0, 0.0, -1.0), DAYZ_UP, True) == (1.0, 0.0, 0.0)
    assert screen_right((0.0, 0.0, 1.0), DAYZ_UP, True) == (-1.0, 0.0, 0.0)


# ---- the two properties the game showed ---------------------------------

def test_b2d_keeps_handedness(fork):
    """Seen face-on from the relief side, the F reads correctly in Blender
    and, after blender_to_dayz(), in DayZ. A and C read mirrored, so the
    check can fail; up stays up in all three."""
    assert reading(build_chiral_f_p3d(fork), BLENDER_UP, False) == "F"
    readings = {}
    for tag in "BAC":
        p3d = variant(fork, tag)
        lod = p3d.lods[0]
        assert (centroid(box_points(lod, TOP_ARM))[1]
                > centroid(box_points(lod, MID_ARM))[1]), tag
        readings[tag] = reading(p3d, DAYZ_UP, True)
    assert readings == {"B": "F", "A": "mirrored F", "C": "mirrored F"}


def test_b2d_mlod_winding_points_inward(fork):
    """MLOD convention: the vertex-order cross product and the normals point
    INWARD, on all 48 faces after blender_to_dayz() - also once written and
    read back. The Blender input points outward on all 48, and so does C,
    which rendered inside-out."""
    assert inward_counts(build_chiral_f_p3d(fork)) == (48, 0, 0)
    converted = variant(fork, "B")
    assert inward_counts(converted) == (48, 48, 48)
    assert inward_counts(read_p3d(fork, write_bytes(converted))) == (48, 48, 48)
    assert inward_counts(variant(fork, "C")) == (48, 0, 0)


def test_b2d_winding_cannot_see_a_mirror(fork):
    """A passes the same inward check, 48 of 48, and is mirrored in game: a
    winding gate is not a chirality gate."""
    a = variant(fork, "A")
    assert inward_counts(a) == (48, 48, 48)
    assert reading(a, DAYZ_UP, True) == "mirrored F"


def test_b2d_reflection_alone_is_inside_out(fork):
    """transform() with the det=-1 matrix alone puts every point where
    blender_to_dayz() does but reverses every face: cross product and
    normals OUTWARD. That is why the matrix stays private."""
    p3d = build_chiral_f_p3d(fork)
    p3d.transform(fork._BLENDER_TO_DAYZ_AXES)
    assert inward_counts(p3d) == (48, 0, 0)
    assert reading(p3d, DAYZ_UP, True) == "F"
    b = variant(fork, "B")
    assert ([p.coords for p in p3d.lods[0].points]
            == [p.coords for p in b.lods[0].points])


# ---- what it does to the data ---------------------------------------------

def test_b2d_maps_points_keeps_order_negates_normals(fork):
    """Points (x,y,z) -> (x,z,y); vertex order, normal_index and uv
    unchanged; normals (nx,ny,nz) -> (-nx,-nz,-ny). Checked on the bytes
    read back, which is what AddonBuilder gets."""
    src = build_chiral_f_p3d(fork).lods[0]
    got = read_p3d(fork, write_bytes(variant(fork, "B"))).lods[0]
    for old, new in zip(src.points, got.points):
        x, y, z = old.coords
        assert new.coords == tuple(f32(c) for c in (x, z, y))
    for old, new in zip(src.facenormals, got.facenormals):
        nx, ny, nz = old
        assert new == tuple(f32(c) for c in (-nx, -nz, -ny))
    assert len(got.faces) == len(src.faces) == 48
    for old, new in zip(src.faces, got.faces):
        assert ([v.point_index for v in new.vertices]
                == [v.point_index for v in old.vertices])
        assert ([v.normal_index for v in new.vertices]
                == [v.normal_index for v in old.vertices])
        assert ([v.uv for v in new.vertices]
                == [tuple(f32(c) for c in v.uv) for v in old.vertices])


def test_b2d_multilod_every_lod_validate_clean(fork):
    """Every LOD converts - visual, the three collision LODs and the memory
    points - and validate() stays [] on the clean multi-LOD model."""
    p3d = build_multilod_v2_p3d(fork)
    assert p3d.validate() == []
    before = [([p.coords for p in lod.points], list(lod.facenormals),
               [[v.point_index for v in fa.vertices] for fa in lod.faces])
              for lod in p3d.lods]
    mem = p3d.get_lod("memory")
    mem_before = mem.get_memory_points()
    fork.blender_to_dayz(p3d)
    assert p3d.validate() == []
    kinds = [lod.kind() for lod in p3d.lods]
    assert kinds == ["visual", "geometry", "view_geometry", "fire_geometry",
                     "memory"]
    for lod, kind, (points, normals, orders) in zip(p3d.lods, kinds, before):
        assert len(lod.points) == len(points), kind
        for (x, y, z), p in zip(points, lod.points):
            assert close3(p.coords, (x, z, y)), kind
        for (nx, ny, nz), n in zip(normals, lod.facenormals):
            assert close3(n, (-nx, -nz, -ny)), kind
        assert [[v.point_index for v in fa.vertices]
                for fa in lod.faces] == orders, kind
    for name, (x, y, z) in mem_before.items():
        assert close3(mem.get_memory_points()[name], (x, z, y)), name


@pytest.mark.parametrize("shared", ["point", "facenormals"])
def test_b2d_refuses_shared_data_before_any_change(fork, shared):
    """A Point object or a facenormals list in two LODs would be mapped
    twice by transform(): (1,2,3) would come back unconverted. The call
    raises and leaves the model as it was."""
    p3d = fork.P3D()
    vis = build_chiral_f_p3d(fork).lods[0]
    other = build_chiral_f_p3d(fork).lods[0]
    other.resolution = 1.0
    if shared == "point":
        other.points[0] = vis.points[0]
    else:
        other.facenormals = vis.facenormals
    p3d.lods += [vis, other]
    snapshot = [([p.coords for p in lod.points], list(lod.facenormals),
                 [[v.point_index for v in fa.vertices] for fa in lod.faces])
                for lod in p3d.lods]
    with pytest.raises(ValueError, match="Nothing was changed"):
        fork.blender_to_dayz(p3d)
    assert snapshot == [([p.coords for p in lod.points], list(lod.facenormals),
                         [[v.point_index for v in fa.vertices]
                          for fa in lod.faces])
                        for lod in p3d.lods]


def test_b2d_second_call_undoes_the_first(fork):
    """The map is its own inverse and so is the normal sign: two calls give
    the model back - points, normals and vertex order. By value, not by
    bytes: a zero normal component can come back as -0.0."""
    p3d = build_chiral_f_p3d(fork)
    lod = p3d.lods[0]
    points = [p.coords for p in lod.points]
    normals = list(lod.facenormals)
    orders = [[v.point_index for v in fa.vertices] for fa in lod.faces]
    fork.blender_to_dayz(p3d)
    assert [p.coords for p in lod.points] != points
    fork.blender_to_dayz(p3d)
    assert [p.coords for p in lod.points] == points
    assert lod.facenormals == normals
    assert [[v.point_index for v in fa.vertices] for fa in lod.faces] == orders


# ---- proxies: measured in game the same day --------------------------------

# Blender poses of the in-game proxy test: canonical raw rows (x, y, z) in
# Blender coordinates. Identity, yaw +90 about Blender Z, and yaw +90 after a
# 30 degree tilt about Blender X.
_C30, _S30 = math.cos(math.radians(30.0)), math.sin(math.radians(30.0))
BLENDER_PROXY_POSES = {
    "identity": ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
    "yaw90": ((0.0, 1.0, 0.0), (-1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
    "yaw90_tilt30": ((0.0, 1.0, 0.0), (-_C30, 0.0, _S30), (_S30, 0.0, _C30)),
}


def swap(v):
    return (v[0], v[2], v[1])


@pytest.mark.parametrize("pose", sorted(BLENDER_PROXY_POSES))
def test_b2d_blender_proxy_equals_engine_space_proxy(fork, pose):
    """What the binarized files showed, pinned offline: a proxy drawn in
    Blender with add_proxy(space="raw") and converted with the model becomes
    the very triangle add_proxy(space="engine") builds in DayZ space for the
    frame worked out by hand - aside = M x, up = M z, dir = M y, M the swap.
    In game those proxies rendered in the pose drawn in Blender; the same
    matrices with space="raw" in DayZ space - raw frames passed off as engine
    frames - did not."""
    rows = BLENDER_PROXY_POSES[pose]
    engine_rows = (swap(rows[0]), swap(rows[2]), swap(rows[1]))
    anchor = (1.5, 2.0, 0.25)
    p3d = fork.P3D()
    lod = fork.LOD()
    lod.resolution = 1.0
    p3d.lods.append(lod)
    lod.add_proxy("\\kp\\target", 1, origin=anchor, rotation=rows, space="raw")
    fork.blender_to_dayz(p3d)
    want = fork.canonical_proxy_triangle(swap(anchor), engine_rows, 0.001,
                                         "engine")
    for got, expected in zip([p.coords for p in lod.points], want):
        assert close3(got, expected), pose
    frame = lod.get_proxies(strict=True)[0]["engine_frame"]
    for got, expected in zip(frame, engine_rows):
        assert close3(got, expected), pose
    raw_twin = fork.canonical_proxy_triangle(swap(anchor), engine_rows, 0.001,
                                             "raw")
    assert not all(close3(p.coords, q) for p, q in zip(lod.points, raw_twin))


def test_b2d_proxy_moves_like_any_face(fork):
    """A proxy triangle gets nothing special: its points are mapped and its
    vertex order kept, like every other face."""
    p3d = build_multilod_v2_p3d(fork)
    vis = p3d.lods[0]
    face = next(iter(vis.selections[PROXY].faces))
    order = [v.point_index for v in face.vertices]
    coords = [vis.points[i].coords for i in order]
    fork.blender_to_dayz(p3d)
    assert [v.point_index for v in face.vertices] == order
    for (x, y, z), i in zip(coords, order):
        assert vis.points[i].coords == (x, z, y)


def test_b2d_emits_no_warning(fork):
    """Not even for a model with a proxy."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        fork.blender_to_dayz(build_multilod_v2_p3d(fork))
        fork.blender_to_dayz(build_chiral_f_p3d(fork))
    assert caught == []


# ---- the deprecated constant ------------------------------------------------

def test_blender_to_dayz_constant_deprecated_value_unchanged(fork):
    """Reading BLENDER_TO_DAYZ warns, at the caller's line, and still gives
    the det=+1 rotation it always gave - now ROT_X_NEG90."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        value = fork.BLENDER_TO_DAYZ
    assert len(caught) == 1
    assert caught[0].category is FutureWarning
    assert caught[0].filename == __file__
    assert "blender_to_dayz" in str(caught[0].message)
    assert "ROT_X_NEG90" in str(caught[0].message)
    assert value is fork.ROT_X_NEG90
    assert value == ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, -1.0, 0.0))
    assert fork._det3(value) == 1.0
    assert fork._det3(fork._BLENDER_TO_DAYZ_AXES) == -1.0


def test_blender_to_dayz_constant_from_import_warns(fork):
    with pytest.warns(FutureWarning, match="MIRRORED"):
        from py3d import BLENDER_TO_DAYZ
    assert BLENDER_TO_DAYZ == fork.ROT_X_NEG90


def test_module_getattr_unknown_name_still_raises(fork):
    assert not hasattr(fork, "NO_SUCH_NAME")
    with pytest.raises(AttributeError, match="NO_SUCH_NAME"):
        fork.NO_SUCH_NAME
