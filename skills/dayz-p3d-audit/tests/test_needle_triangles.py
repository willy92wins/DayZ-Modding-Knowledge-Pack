#!/usr/bin/env python3
"""Needle triangles in the collision components: the ddce check of scripts/audit_p3d.py.

Run: python -m pytest -q -p no:cacheprovider skills/dayz-p3d-audit/tests
 or: python -m unittest discover -s skills/dayz-p3d-audit/tests

No .p3d is read and py3d is not needed (the CI runner installs pytest only). audit_p3d.py
imports py3d at the top and exits without it, so it is loaded here with a stand-in py3d that
classifies the five LOD resolutions these tests use. The LODs are stand-ins too, with the
attributes the check reads from py3d's classes: LOD.resolution, .points, .faces and
.selections, Point.coords, Face.vertices, Vertex.point_index and Selection.faces.

The hulls are closed and convex, wound outward as Qhull's simplices come (the check reads no
winding): a 1 x 0.5 x 0.25 m box; the box with a point just outside the middle of its top front
edge, whose top face is triangulated with a needle (the shape pipeline inbox
fb-20261002-175602-ddce reports from Qhull); and the box with one corner cut by a 1 mm face.
"""
import contextlib
import importlib.util
import io
import math
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_p3d.py"
KINDS = {0.0: "visual", 1e13: "geometry", 1e15: "memory", 6e15: "view_geometry", 7e15: "fire_geometry"}


def _load_audit():
    stand_in = types.ModuleType("py3d")
    stand_in.IS_DAYZ_FORK = True
    stand_in.__version__ = "1.10.1"
    stand_in.classify_lod_resolution = KINDS.get
    saved = sys.modules.get("py3d")
    sys.modules["py3d"] = stand_in
    try:
        spec = importlib.util.spec_from_file_location("audit_p3d_under_test", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        if saved is None:
            del sys.modules["py3d"]
        else:
            sys.modules["py3d"] = saved
    return module


audit = _load_audit()

L, W, H = 1.0, 0.5, 0.25
BOX = [(0, 0, 0), (L, 0, 0), (L, W, 0), (0, W, 0), (0, 0, H), (L, 0, H), (L, W, H), (0, W, H)]
BOX_TRIANGLES = [(0, 2, 1), (0, 3, 2), (3, 7, 6), (3, 6, 2), (0, 4, 7), (0, 7, 3),
                 (1, 2, 6), (1, 6, 5), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4)]
BOX_QUADS = [(0, 3, 2, 1), (3, 7, 6, 2), (0, 4, 7, 3), (1, 2, 6, 5), (4, 5, 6, 7), (0, 1, 5, 4)]
NEEDLE_FACE = 6
CHAMFER_FACE = 13


def needle_box(offset):
    """The box and point 8 at `offset` outside the middle of its top front edge (4-5), in the
    plane of the top face. That face is triangulated with the needle (4, 8, 5) at position
    NEEDLE_FACE: its longest edge is 4-5, 1 m, so its area and its ratio are both offset / 2."""
    points = BOX + [(L / 2, -offset, H)]
    faces = [(0, 2, 1), (0, 3, 2), (3, 7, 6), (3, 6, 2), (0, 4, 7), (0, 7, 3),
             (4, 8, 5), (4, 5, 6), (4, 6, 7), (1, 2, 6), (1, 6, 5),
             (0, 1, 8), (0, 8, 4), (1, 5, 8)]
    return points, faces


def chamfered_box(cut):
    """The box with corner 6 cut at `cut` along its three edges: the cut face (6, 8, 9), at
    position CHAMFER_FACE, is equilateral, of side cut * sqrt(2), area sqrt(3) / 2 * cut^2 and
    ratio sqrt(3) / 4. The faces beside it are pentagons, triangulated."""
    points = list(BOX)
    points[6] = (L - cut, W, H)
    points += [(L, W - cut, H), (L, W, H - cut)]
    faces = [(0, 2, 1), (0, 3, 2), (3, 7, 6), (3, 6, 9), (3, 9, 2), (0, 4, 7), (0, 7, 3),
             (1, 2, 9), (1, 9, 8), (1, 8, 5), (4, 5, 8), (4, 8, 6), (4, 6, 7),
             (6, 8, 9), (0, 1, 5), (0, 5, 4)]
    return points, faces


class Point:
    def __init__(self, coords):
        self.coords = tuple(float(x) for x in coords)


class Vertex:
    def __init__(self, point_index):
        self.point_index = point_index
        self.normal_index = 0
        self.uv = (0.0, 0.0)


class Face:
    def __init__(self, corners):
        self.vertices = [Vertex(k) for k in corners]
        self.material = ""


class Selection:
    def __init__(self, faces):
        self.points = {}
        self.faces = {face: 1 for face in faces}


class LOD:
    def __init__(self, resolution, points=(), faces=(), selections=None):
        self.resolution = resolution
        self.points = [Point(coords) for coords in points]
        self.faces = [Face(corners) for corners in faces]
        self.facenormals = [(0.0, 0.0, 1.0)]
        self.properties = {}
        self.selections = {name: Selection([self.faces[n] for n in members])
                           for name, members in (selections or {}).items()}

    @property
    def num_vertices(self):
        return sum(len(face.vertices) for face in self.faces)


class Model:
    def __init__(self, lods):
        self.lods = lods

    def validate(self):
        return []


def two_hulls(second, name="Component02"):
    """A collision LOD's points, faces and selections: the box as Component01 (points 0-7,
    faces 0-11) and the hull `second`, (points, faces), after it as `name`."""
    points, faces = second
    base = len(BOX)
    first = len(BOX_TRIANGLES)
    all_faces = BOX_TRIANGLES + [tuple(base + k for k in face) for face in faces]
    return BOX + points, all_faces, {"Component01": range(first), name: range(first, len(all_faces))}


class TriangleArithmetic(unittest.TestCase):
    def test_area_and_ratio_of_known_triangles(self):
        cases = [
            (((0, 0, 0), (1, 0, 0), (0, 1, 0)), 0.5, 0.25),
            (((0, 0, 0), (2, 0, 0), (1, math.sqrt(3), 0)), math.sqrt(3), math.sqrt(3) / 4),
            (((0, 0, 0), (1, 0, 0), (2, 0, 0)), 0.0, 0.0),
            (((1, 1, 1), (1, 1, 1), (1, 1, 1)), 0.0, 0.0),
        ]
        for corners, area, ratio in cases:
            got = audit.triangle_area_ratio(*corners)
            self.assertAlmostEqual(got[0], area, places=12, msg=corners)
            self.assertAlmostEqual(got[1], ratio, places=12, msg=corners)


class NeedleTriangles(unittest.TestCase):
    """needle_triangles() on points and faces."""

    def test_a_healthy_hull_passes(self):
        self.assertEqual(audit.needle_triangles(BOX, BOX_TRIANGLES), [])
        # It is read: its four thinnest triangles (legs 1 and 0.25 m, ratio 0.118) fail at 0.12.
        thinnest = audit.needle_triangles(BOX, BOX_TRIANGLES, min_ratio=0.12)
        self.assertEqual([face for face, _, _, _ in thinnest], [2, 3, 10, 11])

    def test_a_quad_reads_as_two_triangles_and_a_box_of_quads_passes(self):
        self.assertEqual(audit.needle_triangles(BOX, BOX_QUADS), [])
        # At a ratio no triangle reaches every triangle is listed: (a, b, c) and (a, c, d) per quad.
        every = audit.needle_triangles(BOX, BOX_QUADS, min_ratio=1.0)
        self.assertEqual([(face, corners) for face, corners, _, _ in every],
                         [(n, t) for n, (a, b, c, d) in enumerate(BOX_QUADS) for t in ((a, b, c), (a, c, d))])

    def test_a_large_thin_triangle_above_the_ratio_passes(self):
        # 2 m long and 0.476 mm high: area 4.76e-4 m^2 and ratio 1.19e-4, the lowest ratio that
        # took rays in the ticket's runs.
        points = [(0, 0, 0), (2, 0, 0), (1, 4.76e-4, 0)]
        self.assertEqual(audit.needle_triangles(points, [(0, 1, 2)]), [])
        (needle,) = audit.needle_triangles(points, [(0, 1, 2)], min_ratio=1.2e-4)
        self.assertAlmostEqual(needle[2], 4.76e-4, delta=1e-12)
        self.assertAlmostEqual(needle[3], 1.19e-4, delta=1e-12)

    def test_a_needle_by_ratio_fails_and_is_named(self):
        points, faces = needle_box(2e-5)
        (needle,) = audit.needle_triangles(points, faces)
        face, corners, area, ratio = needle
        self.assertEqual((face, corners), (NEEDLE_FACE, (4, 8, 5)))
        self.assertAlmostEqual(area, 1e-5, delta=1e-15)
        self.assertAlmostEqual(ratio, 1e-5, delta=1e-15)
        self.assertGreater(area, audit.NEEDLE_MIN_AREA)

    def test_a_small_triangle_fails_by_area_and_is_named(self):
        points, faces = chamfered_box(1e-3)
        (needle,) = audit.needle_triangles(points, faces)
        face, corners, area, ratio = needle
        self.assertEqual((face, corners), (CHAMFER_FACE, (6, 8, 9)))
        self.assertAlmostEqual(area, math.sqrt(3) / 2 * 1e-6, delta=1e-15)
        self.assertAlmostEqual(ratio, math.sqrt(3) / 4, delta=1e-9)

    def test_a_needle_of_the_ticket_s_size_fails_and_is_named(self):
        # The ticket's needles: area about 3e-8 m^2, ratio 1.6e-7 and 4.6e-7.
        points, faces = needle_box(6e-8)
        (needle,) = audit.needle_triangles(points, faces)
        face, corners, area, ratio = needle
        self.assertEqual((face, corners), (NEEDLE_FACE, (4, 8, 5)))
        self.assertAlmostEqual(area, 3e-8, delta=1e-18)
        self.assertAlmostEqual(ratio, 3e-8, delta=1e-18)


class CollisionComponents(unittest.TestCase):
    """check_collision_needle_triangles() on a stand-in model."""

    def test_the_finding_names_the_lod_the_component_the_face_and_both_numbers(self):
        points, faces, selections = two_hulls(needle_box(2e-5))
        lower = {name.lower(): members for name, members in selections.items()}
        model = Model([
            LOD(0.0, points, faces, selections),
            LOD(1e13, points, faces, selections),
            LOD(1e15, [(0, 0, 0)]),
            LOD(6e15, points, faces, lower),
            LOD(7e15, points, faces, selections),
        ])
        issues = audit.check_collision_needle_triangles(model)
        face = len(BOX_TRIANGLES) + NEEDLE_FACE
        heads = ["LOD[1] Geometry, Component02, face %d: " % face,
                 "LOD[3] ViewGeo, component02, face %d: " % face,
                 "LOD[4] FireGeo, Component02, face %d: " % face]
        self.assertEqual([severity for severity, _ in issues], ["CRITICAL"] * len(heads), issues)
        for (_, message), head in zip(issues, heads):
            self.assertTrue(message.startswith(
                head + "needle triangle (points 12, 16, 13), area 1.00e-05 m^2, "
                "area/longest edge^2 1.00e-05 (this check fails a triangle under 1e-06 m^2 or "
                "1e-04)."), message)
            self.assertIn("without point 16, the corner opposite the longest edge", message)

    def test_a_proxy_triangle_in_a_component_is_not_read(self):
        # A 1 mm triangle (area 5e-7 m^2) in Component01, once as the one face of a proxy selection.
        points = BOX + [(5, 5, 5), (5.001, 5, 5), (5, 5.001, 5)]
        faces = BOX_TRIANGLES + [(8, 9, 10)]
        proxy = "proxy:\\dz\\vehicles\\parts\\battery_car.001"
        bare = Model([LOD(1e13, points, faces, {"Component01": range(13)})])
        held = Model([LOD(1e13, points, faces, {"Component01": range(13), proxy: [12]})])
        (issue,) = audit.check_collision_needle_triangles(bare)
        self.assertTrue(issue[1].startswith("LOD[0] Geometry, Component01, face 12: "), issue)
        self.assertEqual(audit.check_collision_needle_triangles(held), [])

    def test_a_face_in_no_component_is_not_read(self):
        points, faces = needle_box(2e-5)
        rest = [n for n in range(len(faces)) if n != NEEDLE_FACE]
        covered = Model([LOD(1e13, points, faces, {"Component01": range(len(faces))})])
        outside = Model([LOD(1e13, points, faces, {"Component01": rest, "lid": [NEEDLE_FACE]})])
        (issue,) = audit.check_collision_needle_triangles(covered)
        self.assertTrue(issue[1].startswith("LOD[0] Geometry, Component01, face 6: "), issue)
        self.assertEqual(audit.check_collision_needle_triangles(outside), [])


class Wiring(unittest.TestCase):
    """main() runs the check on a .p3d and exits 1 on a needle."""

    def run_main(self, model):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "model.p3d"
            path.write_bytes(b"MLOD" + bytes(12))  # the signature audit_p3d() reads; P3D() is the stand-in's
            out = io.StringIO()
            with mock.patch.object(audit.py3d, "P3D", lambda stream: model, create=True), \
                    mock.patch.object(sys, "argv", ["audit_p3d.py", str(path)]), \
                    contextlib.redirect_stdout(out):
                with self.assertRaises(SystemExit) as stop:
                    audit.main()
        return stop.exception.code, out.getvalue()

    def model(self, second):
        points, faces, selections = two_hulls(second)
        box = {"Component01": range(len(BOX_TRIANGLES))}
        return Model([
            LOD(0.0, BOX, BOX_TRIANGLES),
            LOD(1e13, points, faces, selections),
            LOD(1e15, [(0, 0, 0)]),
            LOD(6e15, BOX, BOX_TRIANGLES, box),
            LOD(7e15, BOX, BOX_TRIANGLES, box),
        ])

    def test_main_exits_1_on_a_needle_and_0_without_one(self):
        code, out = self.run_main(self.model((BOX, BOX_QUADS)))
        self.assertEqual(code, 0, out)
        self.assertIn("RESULT: ALL CHECKS PASSED", out)
        code, out = self.run_main(self.model(needle_box(2e-5)))
        self.assertEqual(code, 1, out)
        self.assertIn("  CRITICAL: LOD[1] Geometry, Component02, face 18: needle triangle", out)
        self.assertIn("RESULT: 1 CRITICAL, 0 WARNING, 0 NOTE", out)


if __name__ == "__main__":
    unittest.main()
