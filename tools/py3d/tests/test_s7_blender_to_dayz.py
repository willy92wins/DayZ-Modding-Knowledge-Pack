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
    bytes: a zero normal component can come back as -0.0. The model's
    normals are unit vectors; one that is not comes back unit-length,
    because P3D.transform() renormalizes."""
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
    lod.facenormals[0] = (0.0, 2.0, 0.0)
    fork.blender_to_dayz(p3d)
    fork.blender_to_dayz(p3d)
    assert lod.facenormals[0] == (0.0, 1.0, 0.0)


# ---- ERR_WINDING_VS_NORMALS: a disagreement, not a direction ---------------

def negate_normals(lod):
    for i, n in enumerate(lod.facenormals):
        lod.facenormals[i] = (-n[0], -n[1], -n[2])


def reverse_faces(lod):
    for fa in lod.faces:
        fa.vertices.reverse()


def turned(fork, side):
    """B, the export that rendered right, with one side turned on every
    face: its normals ("normals") or its vertex order ("winding")."""
    p3d = variant(fork, "B")
    {"normals": negate_normals, "winding": reverse_faces}[side](p3d.lods[0])
    return p3d


def shell_volume(lod, box):
    """Signed volume by winding of one box, a closed shell with its own
    eight points: the sum of dot(v0, v1 x v2) / 6 over the fan triangles of
    its faces. Negative when the cross product points into the box, the
    sign of a solid seen from outside on shipped MLODs."""
    total = 0.0
    for fa in lod.faces:
        if fa.vertices[0].point_index // 8 != box:
            continue
        vs = [v.point.coords for v in fa.vertices]
        for i in range(1, len(vs) - 1):
            total += dot(vs[0], cross(vs[i], vs[i + 1])) / 6.0
    return total


def vs_normals(p3d):
    return [f for f in p3d.validate() if f.code == "ERR_WINDING_VS_NORMALS"]


def boxes(lod):
    return [[fa for fa in lod.faces if fa.vertices[0].point_index // 8 == k]
            for k in range(4)]


def corners_right(p3d):
    """Corner normals, of all 144, that point into their box: inward_counts()
    reads only each face's first corner, as the check does."""
    lod = p3d.lods[0]
    right = 0
    for fa in lod.faces:
        out = sub(centroid([v.point.coords for v in fa.vertices]),
                  centroid(box_points(lod, fa.vertices[0].point_index // 8)))
        right += sum(dot(v.normal, out) < 0 for v in fa.vertices)
    return right


def negate_normals_of(lod, faces):
    """Negate every corner normal of *faces*, whatever it points at: a pool
    entry no other face uses in place, one that another face also uses as a
    negated copy that only the corners of *faces* are re-pointed to."""
    mine = {id(fa) for fa in faces}
    kept = {v.normal_index for fa in lod.faces if id(fa) not in mine
            for v in fa.vertices}
    copies = {}
    for fa in faces:
        for v in fa.vertices:
            j = v.normal_index
            if j in kept:
                if j not in copies:
                    n = lod.facenormals[j]
                    lod.facenormals.append((-n[0], -n[1], -n[2]))
                    copies[j] = len(lod.facenormals) - 1
                v.normal_index = copies[j]
    for j in {v.normal_index for fa in faces for v in fa.vertices} - kept:
        if j not in copies.values():
            n = lod.facenormals[j]
            lod.facenormals[j] = (-n[0], -n[1], -n[2])


def fix_corners(lod):
    """The normals step, once the winding is settled: negate each corner
    normal that points against its face's cross product. An entry only such
    corners use is negated in place. An entry that a kept corner also uses
    stays, and the corner is re-pointed to a kept entry that already holds
    the negated value, or else to a negated copy."""
    flip, keep = [], set()
    for fa in lod.faces:
        vs = [v.point.coords for v in fa.vertices]
        cr = cross(sub(vs[1], vs[0]), sub(vs[2], vs[0]))
        for v in fa.vertices:
            if dot(cr, v.normal) < 0:
                flip.append(v)
            else:
                keep.add(v.normal_index)
    kept_value = {}
    for j in sorted(keep):
        kept_value.setdefault(lod.facenormals[j], j)
    in_place = {v.normal_index for v in flip} - keep
    for j in in_place:
        n = lod.facenormals[j]
        lod.facenormals[j] = (-n[0], -n[1], -n[2])
    copies = {}
    for v in flip:
        if v.normal_index in in_place:
            continue
        n = lod.facenormals[v.normal_index]
        target = (-n[0], -n[1], -n[2])
        if target in kept_value:
            v.normal_index = kept_value[target]
            continue
        if target not in copies:
            lod.facenormals.append(target)
            copies[target] = len(lod.facenormals) - 1
        v.normal_index = copies[target]


def share_pool(lod):
    """One pool entry per distinct normal, so an entry serves several
    boxes."""
    pool = []
    for fa in lod.faces:
        for v in fa.vertices:
            n = v.normal
            if n not in pool:
                pool.append(n)
            v.normal_index = pool.index(n)
    lod.facenormals[:] = pool


def faces_against_every_neighbour(lod):
    """Faces each of whose edges another face runs in the same direction: a
    face turned on its own inside a shell. A turned group of faces needs a
    flood fill over shared edges instead; none of these fixtures has one."""
    runs = {}
    for fa in lod.faces:
        idx = [v.point_index for v in fa.vertices]
        for edge in zip(idx, idx[1:] + idx[:1]):
            runs[edge] = runs.get(edge, 0) + 1
    against = []
    for fa in lod.faces:
        idx = [v.point_index for v in fa.vertices]
        if all(runs[edge] > 1 for edge in zip(idx, idx[1:] + idx[:1])):
            against.append(fa)
    return against


def test_vs_normals_cannot_tell_which_side_is_wrong(fork):
    """Normals turned and faces turned read alike: 0 % agreement and the
    same finding with the same text, though they need opposite fixes. So
    the message gives an order that works for both - the winding first,
    the normals after - not one fix. B passes."""
    assert vs_normals(variant(fork, "B")) == []
    msgs = []
    for side in ("normals", "winding"):
        p3d = turned(fork, side)
        assert fork._pct_normal_agreement(p3d.lods[0]) == 0.0, side
        found = vs_normals(p3d)
        assert [(f.severity, f.lod) for f in found] == [("ERROR", 0)], side
        msgs.append(found[0].msg)
    assert msgs[0] == msgs[1]
    for needle in ("not which one is wrong", "first corner",
                   "winding first, normals untouched",
                   "WARN_WINDING_EDGE_INCOHERENT", "signed volume",
                   "face.vertices.reverse()", "vertices[1]/[2] swap",
                   "each corner normal that still points against its face",
                   "lod.facenormals[j] = (-x, -y, -z)", "negated copy"):
        assert needle in msgs[0], needle
    assert "wound backwards" not in msgs[0]


def test_vs_normals_direction_picks_the_fix(fork):
    """The signed volume tells the two apart: with the normals turned every
    box keeps B's negative sign, so the winding stays; with the faces
    turned every box flips, so every face is reversed. Then the corners
    that still point against their face are negated, and B comes back,
    cross product and normals inward on 48 of 48 faces. The other fix
    silences the finding just as well - 100 % agreement, validate()
    returns [] - and leaves both outward, the orientation C rendered
    inside-out with; on the normals-turned model it is the fix this
    message used to give. The signs the message gives are the ones
    measured here: B, a solid seen from outside that rendered right in
    game, is negative, and B turned deliberately inside-out, faces and
    normals, which is what a room seen from inside is, is positive."""
    b = variant(fork, "B").lods[0]
    assert all(shell_volume(b, k) < 0 for k in range(4))
    msg = vs_normals(turned(fork, "normals"))[0].msg
    assert "negative for a solid seen from outside" in msg
    room = variant(fork, "B").lods[0]
    reverse_faces(room)
    negate_normals(room)
    assert all(shell_volume(room, k) > 0 for k in range(4))
    assert "positive for a room seen from inside" in msg
    for side, winding_right in (("normals", True), ("winding", False)):
        p3d = turned(fork, side)
        lod = p3d.lods[0]
        assert ([shell_volume(lod, k) < 0 for k in range(4)]
                == [winding_right] * 4), side
        if not winding_right:
            reverse_faces(lod)
        fix_corners(lod)
        assert inward_counts(p3d) == (48, 48, 48), side
        assert p3d.validate() == [], side
        wrong = turned(fork, side)
        if winding_right:
            reverse_faces(wrong.lods[0])
        else:
            negate_normals(wrong.lods[0])
        assert inward_counts(wrong) == (48, 0, 0), side
        assert wrong.validate() == [], side


def test_vs_normals_blind_to_faces_and_normals_turned_together(fork):
    """C rendered inside-out in game and validate() has nothing to say about
    it: its faces and normals agree on every face."""
    c = variant(fork, "C")
    assert inward_counts(c) == (48, 0, 0)
    assert fork._pct_normal_agreement(c.lods[0]) == 100.0
    assert c.validate() == []


def test_vs_normals_collision_lod_asks_for_the_component_check(fork):
    """On a collision LOD the message asks for the per-component check
    instead of the signed volume, with the sign blender_to_dayz writes: on
    the converted Geometry cube, one convex component, every face's cross
    product points inward."""
    p3d = build_multilod_v2_p3d(fork)
    fork.blender_to_dayz(p3d)
    index = [lod.kind() for lod in p3d.lods].index("geometry")
    geo = p3d.lods[index]
    middle = centroid([p.coords for p in geo.points])
    for fa in geo.faces:
        vs = [v.point.coords for v in fa.vertices]
        out = sub(centroid(vs), middle)
        assert dot(cross(sub(vs[1], vs[0]), sub(vs[2], vs[0])), out) < 0
    negate_normals(geo)
    found = vs_normals(p3d)
    assert [(f.severity, f.lod) for f in found] == [("ERROR", index)]
    assert "inward expected" in found[0].msg
    assert "convex component" in found[0].msg
    assert "signed volume" not in found[0].msg


def test_vs_normals_shared_pool_entry_gets_a_copy(fork):
    """Three boxes with their normals turned and the stem with its faces
    turned, on a pool of six entries that serve every box. Negating the
    entries of the boxes whose normals are wrong also turns the stem's,
    which were right: 75 %, its 12 faces disagreeing. Reversing the stem by
    its volume, then fixing corner by corner, gives back B, re-pointing
    corners to entries that already hold the negated values: the pool
    stays at six."""
    def broken():
        p3d = variant(fork, "B")
        lod = p3d.lods[0]
        for k, faces in enumerate(boxes(lod)):
            if k == STEM:
                for fa in faces:
                    fa.vertices.reverse()
            else:
                negate_normals_of(lod, faces)
        share_pool(lod)
        return p3d
    p3d = broken()
    lod = p3d.lods[0]
    assert len(lod.facenormals) == 6
    assert [f.code for f in p3d.validate()] == ["ERR_WINDING_VS_NORMALS"]
    assert ([shell_volume(lod, k) < 0 for k in range(4)]
            == [k != STEM for k in range(4)])
    parts = boxes(lod)
    normals_wrong = [fa for k in range(4) if k != STEM for fa in parts[k]]
    for j in {v.normal_index for fa in normals_wrong for v in fa.vertices}:
        n = lod.facenormals[j]
        lod.facenormals[j] = (-n[0], -n[1], -n[2])
    for fa in parts[STEM]:
        fa.vertices.reverse()
    assert fork._pct_normal_agreement(lod) == 75.0
    assert inward_counts(p3d) == (48, 48, 36)
    p3d = broken()
    lod = p3d.lods[0]
    for fa in boxes(lod)[STEM]:
        fa.vertices.reverse()
    fix_corners(lod)
    assert inward_counts(p3d) == (48, 48, 48)
    assert corners_right(p3d) == 144
    assert len(lod.facenormals) == 6
    assert p3d.validate() == []


def test_vs_normals_shell_agrees_with_itself_before_its_volume_counts(fork):
    """Every normal turned, and one face of the plate turned back with an
    inward normal of its own: 0 % agreement and an incoherent edge. The
    plate keeps its negative volume, so the volume alone picks "negate the
    normals", which leaves that face inside-out and the edge warning
    standing. Turning first the vertex order of the face that disagrees
    with its neighbours makes the shell coherent; its volume then keeps the
    winding, and fixing the corners gives back B."""
    def broken():
        p3d = variant(fork, "B")
        lod = p3d.lods[0]
        negate_normals(lod)
        fa = lod.faces[0]
        fa.vertices.reverse()
        n = fa.vertices[0].normal
        lod.facenormals.append((-n[0], -n[1], -n[2]))
        for v in fa.vertices:
            v.normal_index = len(lod.facenormals) - 1
        return p3d
    p3d = broken()
    lod = p3d.lods[0]
    assert lod.faces[0].vertices[0].point_index // 8 == PLATE
    assert [f.code for f in p3d.validate()] == [
        "ERR_WINDING_VS_NORMALS", "WARN_WINDING_EDGE_INCOHERENT"]
    assert shell_volume(lod, PLATE) < 0
    negate_normals(lod)
    assert fork._pct_normal_agreement(lod) == 100.0
    assert [f.code for f in p3d.validate()] == ["WARN_WINDING_EDGE_INCOHERENT"]
    assert inward_counts(p3d) == (48, 47, 47)
    p3d = broken()
    lod = p3d.lods[0]
    against = faces_against_every_neighbour(lod)
    assert against == [lod.faces[0]]
    for fa in against:
        fa.vertices.reverse()
    assert [f.code for f in p3d.validate()] == ["ERR_WINDING_VS_NORMALS"]
    assert shell_volume(lod, PLATE) < 0
    fix_corners(lod)
    assert inward_counts(p3d) == (48, 48, 48)
    assert p3d.validate() == []


def test_vs_normals_turn_the_odd_face_without_its_normal(fork):
    """The plate with 11 of its 12 faces reversed, their normals right, and
    the other boxes with their normals turned: 2 % agreement and an
    incoherent edge. The plate's one face that disagrees with its
    neighbours is the right one. Turning it with its normal, then the
    shell by its volume, then the normals of the boxes left (the order of
    the previous message) leaves that face's normal wrong, and validate()
    returns [] at 47 of 48. Turning only its vertex order, then the shell,
    then every corner still against its face gives back B."""
    def broken():
        p3d = variant(fork, "B")
        lod = p3d.lods[0]
        parts = boxes(lod)
        for fa in parts[PLATE][1:]:
            fa.vertices.reverse()
        negate_normals_of(lod, [fa for k in range(4) if k != PLATE
                                for fa in parts[k]])
        return p3d
    for together in (True, False):
        p3d = broken()
        lod = p3d.lods[0]
        parts = boxes(lod)
        assert [f.code for f in p3d.validate()] == [
            "ERR_WINDING_VS_NORMALS", "WARN_WINDING_EDGE_INCOHERENT"]
        odd = faces_against_every_neighbour(lod)
        assert odd == [parts[PLATE][0]]
        for fa in odd:
            fa.vertices.reverse()
        if together:
            negate_normals_of(lod, odd)
        assert shell_volume(lod, PLATE) > 0
        for fa in parts[PLATE]:
            fa.vertices.reverse()
        if together:
            negate_normals_of(lod, [fa for k in range(4) if k != PLATE
                                    for fa in parts[k]])
            assert inward_counts(p3d) == (48, 48, 47)
        else:
            fix_corners(lod)
            assert inward_counts(p3d) == (48, 48, 48)
        assert p3d.validate() == []


def test_vs_normals_fix_normals_corner_by_corner(fork):
    """B with only each face's first corner turned: the check reads 0 %, as
    it reads first corners, though 96 of 144 corners are right. Negating
    whole faces turns those too - 48 of 144 right while the check reads
    100 % and validate() returns [] - and negating each corner that points
    against its face gives back all 144."""
    def broken():
        p3d = variant(fork, "B")
        lod = p3d.lods[0]
        for fa in lod.faces:
            n = fa.vertices[0].normal
            lod.facenormals.append((-n[0], -n[1], -n[2]))
            fa.vertices[0].normal_index = len(lod.facenormals) - 1
        return p3d
    p3d = broken()
    assert corners_right(p3d) == 96
    assert fork._pct_normal_agreement(p3d.lods[0]) == 0.0
    negate_normals_of(p3d.lods[0], p3d.lods[0].faces)
    assert fork._pct_normal_agreement(p3d.lods[0]) == 100.0
    assert corners_right(p3d) == 48
    assert p3d.validate() == []
    p3d = broken()
    fix_corners(p3d.lods[0])
    assert corners_right(p3d) == 144
    assert p3d.validate() == []


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
