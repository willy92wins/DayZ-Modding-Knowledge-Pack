"""validate() 1.2.0: one negative per finding code, and parity with
tools/audit_p3d.py."""

import os
import subprocess
import sys

import pytest

from builders import (CUBE_POINTS, CUBE_QUADS, add_proxy_triangle,
                      build_multilod_v2_p3d)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIT = os.path.join(REPO, "tools", "audit_p3d.py")


def codes(findings):
    return sorted({f.code for f in findings})


def add_box(m, lod, scale, name=None, mass=None):
    """Append a closed box to *lod*: the builders' unit cube scaled per
    axis, with its winding and normals, so a box centred on the origin
    keeps every winding check quiet. *name* gets (or creates) a selection
    holding the box's points and faces. Returns (points, faces)."""
    base = len(lod.points)
    pts = []
    for c in CUBE_POINTS:
        p = m.Point()
        p.coords = tuple(c[j] * scale[j] for j in range(3))
        p.mass = mass
        lod.points.append(p)
        pts.append(p)
    faces = []
    for quad, n in CUBE_QUADS:
        lod.facenormals.append(n)
        fa = m.Face(lod.points, lod.facenormals)
        for pi in quad:
            v = m.Vertex(lod.points, lod.facenormals)
            v.point_index = base + pi
            v.normal_index = len(lod.facenormals) - 1
            v.uv = (0.0, 0.0)
            fa.vertices.append(v)
        fa.texture = fa.material = ""
        lod.faces.append(fa)
        faces.append(fa)
    if name:
        sel = lod.new_selection(name)
        sel.points.update((p, 1) for p in pts)
        sel.faces.update((fa, 1) for fa in faces)
    return pts, faces


def select_all(lod, name):
    """*name* holds every point and face of *lod* (created if missing)."""
    sel = lod.new_selection(name)
    sel.points = {p: 1 for p in lod.points}
    sel.faces = {fa: 1 for fa in lod.faces}
    return sel


# A thin box across the Geometry cube, centred on the origin like it.
CROSS = (0.5, 2.0, 0.5)


# ---- mutators: each produces exactly the expected codes ----------

# These three mutants now ALSO emit the absolute check's codes
# (_check_winding_absolute). That is not duplicate noise: the
# relative one says "differs from the Visual LOD" and the absolute
# one says "contradicts its own normals", which are diagnosed and
# fixed differently. And in the case that motivated the fork -
# inverting EVERY LOD - the relative check stays quiet and the
# absolute one is the only one that speaks.
def mut_winding_inverted(m, p3d):
    for fa in p3d.get_lod("geometry").faces:
        fa.vertices.reverse()
    return ["ERR_WINDING_INVERTED", "ERR_WINDING_VS_NORMALS"]

def mut_winding_mixed(m, p3d):
    for fa in p3d.get_lod("geometry").faces[:2]:
        fa.vertices.reverse()
    return ["WARN_WINDING_MIXED", "WARN_WINDING_NORMAL_MISMATCH",
            "WARN_WINDING_EDGE_INCOHERENT"]

def mut_winding_lowconf(m, p3d):
    for fa in p3d.get_lod("visual").faces[:160]:
        fa.vertices.reverse()
    # one per collision LOD; the set collapses. A half-inverted
    # visual LOD also trips the absolute check on the visual itself.
    return ["WARN_WINDING_LOWCONF", "WARN_WINDING_NORMAL_MISMATCH",
            "WARN_WINDING_EDGE_INCOHERENT"]

# A collision LOD with faces and no component collides with nothing in
# game (measured 2026-10-02 with all three missing); each LOD is checked.
def mut_component_none(m, p3d):
    p3d.get_lod("geometry").selections.pop("Component01")
    return ["ERR_COMPONENT_NAMING"]

def mut_component_none_view(m, p3d):
    p3d.get_lod("view_geometry").selections.pop("Component01")
    return ["ERR_COMPONENT_NAMING"]

def mut_component_none_fire(m, p3d):
    p3d.get_lod("fire_geometry").selections.pop("Component01")
    return ["ERR_COMPONENT_NAMING"]

def mut_component_spelling(m, p3d):
    geo = p3d.get_lod("geometry")
    geo.selections["Component_01"] = geo.selections.pop("Component01")
    return ["WARN_COMPONENT_NAMING"]

def mut_component_newline(m, p3d):
    # "$" in re.match() accepts a trailing newline; fullmatch() does not
    geo = p3d.get_lod("geometry")
    geo.selections["Component01\n"] = geo.selections.pop("Component01")
    return ["WARN_COMPONENT_NAMING"]

def mut_component_coverage(m, p3d):
    geo = p3d.get_lod("geometry")
    sel = geo.selections["Component01"]
    first = next(iter(sel.points))
    del sel.points[first]
    return ["WARN_COMPONENT_COVERAGE"]

def mut_coverage_face_outside(m, p3d):
    # two components; one face of the second is in neither
    geo = p3d.get_lod("geometry")
    _, faces = add_box(m, geo, CROSS, "Component02", mass=25.0)
    del geo.selections["Component02"].faces[faces[0]]
    return ["WARN_COMPONENT_COVERAGE"]

def mut_coverage_lowercase(m, p3d):
    # the same gap, components named in lowercase (they collide alike)
    geo = p3d.get_lod("geometry")
    geo.selections["component01"] = geo.selections.pop("Component01")
    _, faces = add_box(m, geo, CROSS, "component02", mass=25.0)
    del geo.selections["component02"].faces[faces[0]]
    return ["WARN_COMPONENT_COVERAGE"]

def _cover_all_but_one_face(lod):
    sel = select_all(lod, "Component01")
    del sel.faces[lod.faces[0]]
    return ["WARN_COMPONENT_COVERAGE"]

def mut_coverage_view(m, p3d):
    return _cover_all_but_one_face(p3d.get_lod("view_geometry"))

def mut_coverage_fire(m, p3d):
    return _cover_all_but_one_face(p3d.get_lod("fire_geometry"))

def mut_autocenter_missing(m, p3d):
    del p3d.get_lod("geometry").properties["autocenter"]
    return ["WARN_AUTOCENTER_MISSING"]

def mut_not_watertight(m, p3d):
    geo = p3d.get_lod("geometry")
    fa = geo.faces.pop()
    del geo.selections["Component01"].faces[fa]
    return ["WARN_NOT_WATERTIGHT"]

def mut_degenerate(m, p3d):
    geo = p3d.get_lod("geometry")
    fa = m.Face(geo.points, geo.facenormals)
    fa.texture = fa.material = ""
    for _ in range(3):
        v = m.Vertex(geo.points, geo.facenormals)
        v.point_index = 0
        v.normal_index = 0
        v.uv = (0.0, 0.0)
        fa.vertices.append(v)
    geo.faces.append(fa)
    geo.selections["Component01"].faces[fa] = 1
    # the degenerate face also counts as "not outward" in the
    # relative check, matching the original audit's behaviour
    return ["WARN_DEGENERATE_FACES", "WARN_WINDING_MIXED"]

def mut_memory_pos_center(m, p3d):
    mem = p3d.get_lod("memory")
    mem.selections["pos_center"] = mem.selections.pop("pos center")
    return ["WARN_MEMORY_POS_CENTER"]

def mut_memory_box_placing(m, p3d):
    p3d.get_lod("memory").selections.pop("box_placing_max")
    return ["WARN_MEMORY_BOX_PLACING"]

def mut_memory_axis_points(m, p3d):
    mem = p3d.get_lod("memory")
    mem.set_selection("flag_mast_axis", point_idx=[0])
    # the axis also requires a 'flag_mast' selection in the Visual LOD
    return ["ERR_MEMORY_AXIS_POINTS", "ERR_AXIS_SELECTION_MISSING"]

def mut_memory_axis_short(m, p3d):
    mem = p3d.get_lod("memory")
    a = mem.set_memory_point("mast_lo", (0.0, 0.0, 0.0))
    b = mem.set_memory_point("mast_hi", (0.0, 0.05, 0.0))
    sel = mem.new_selection("flag_mast_axis")
    sel.points = {a: 1, b: 1}
    p3d.get_lod("visual").set_selection("flag_mast", point_idx=[0, 1])
    return ["WARN_MEMORY_AXIS_SHORT"]

def mut_memory_has_faces(m, p3d):
    mem = p3d.get_lod("memory")
    mem.facenormals.append((0.0, 1.0, 0.0))
    fa = m.Face(mem.points, mem.facenormals)
    fa.texture = fa.material = ""
    for i in range(3):
        v = m.Vertex(mem.points, mem.facenormals)
        v.point_index = i
        v.normal_index = 0
        v.uv = (0.0, 0.0)
        fa.vertices.append(v)
    mem.faces.append(fa)
    return ["WARN_MEMORY_HAS_FACES"]

def mut_axis_selection_missing(m, p3d):
    p3d.get_lod("memory").set_selection("door_axis", point_idx=[0, 1])
    return ["ERR_AXIS_SELECTION_MISSING"]

def mut_axis_selection_empty(m, p3d):
    p3d.get_lod("memory").set_selection("door_axis", point_idx=[0, 1])
    p3d.get_lod("visual").set_selection("door")
    return ["WARN_AXIS_SELECTION_EMPTY"]

def mut_pdrive(m, p3d):
    p3d.get_lod("visual").faces[0].texture = "P:\\lf\\data\\stone_co.paa"
    return ["WARN_PDRIVE_PATH"]

def mut_kind_unknown(m, p3d):
    p3d.get_lod("fire_geometry").resolution = 5.5e14
    return ["WARN_LOD_KIND_UNKNOWN"]


CASES = [
    ("winding_inverted", mut_winding_inverted),
    ("winding_mixed", mut_winding_mixed),
    ("winding_lowconf", mut_winding_lowconf),
    ("component_none", mut_component_none),
    ("component_none_view", mut_component_none_view),
    ("component_none_fire", mut_component_none_fire),
    ("component_spelling", mut_component_spelling),
    ("component_newline", mut_component_newline),
    ("component_coverage", mut_component_coverage),
    ("coverage_face_outside", mut_coverage_face_outside),
    ("coverage_lowercase", mut_coverage_lowercase),
    ("coverage_view", mut_coverage_view),
    ("coverage_fire", mut_coverage_fire),
    ("autocenter_missing", mut_autocenter_missing),
    ("not_watertight", mut_not_watertight),
    ("degenerate", mut_degenerate),
    ("memory_pos_center", mut_memory_pos_center),
    ("memory_box_placing", mut_memory_box_placing),
    ("memory_axis_points", mut_memory_axis_points),
    ("memory_axis_short", mut_memory_axis_short),
    ("memory_has_faces", mut_memory_has_faces),
    ("axis_selection_missing", mut_axis_selection_missing),
    ("axis_selection_empty", mut_axis_selection_empty),
    ("pdrive", mut_pdrive),
    ("kind_unknown", mut_kind_unknown),
]


def test_val_pos_v2_clean(fork):
    """The complete v2 fixture produces no findings."""
    assert build_multilod_v2_p3d(fork).validate() == []


COLLISION_KINDS = ("geometry", "view_geometry", "fire_geometry")


@pytest.mark.parametrize("name", ["Component01", "component01",
                                  "COMPONENT01", "Component02"])
def test_val_component_name_any_case(fork, name):
    """In game (2026-10-02) component01 collided exactly like Component01,
    and binarize writes both as component01: "Component" and a number, in
    any case, raises nothing on any collision LOD. Up to 1.8.0 a
    lowercase component01 raised ERR_COMPONENT_NAMING."""
    p3d = build_multilod_v2_p3d(fork)
    for kind in COLLISION_KINDS:
        lod = p3d.get_lod(kind)
        lod.selections[name] = lod.selections.pop("Component01")
    assert p3d.validate() == []


@pytest.mark.parametrize("kind", COLLISION_KINDS)
def test_val_component_missing_names_the_lod(fork, kind):
    """The ERROR sits on the LOD without a component, names its kind and
    says its collision is lost silently; it no longer says the case of
    the name matters."""
    p3d = build_multilod_v2_p3d(fork)
    lod = p3d.get_lod(kind)
    lod.selections.pop("Component01")
    index = next(i for i, l in enumerate(p3d.lods) if l is lod)
    found = [f for f in p3d.validate() if f.code == "ERR_COMPONENT_NAMING"]
    assert [(f.severity, f.lod) for f in found] == [("ERROR", index)]
    msg = found[0].msg
    assert msg.startswith("%s LOD: 6 face(s) and no ComponentNN selection"
                          % kind), msg
    # the measured case (none in any collision LOD) is said as measured,
    # one LOD missing it alone as not measured
    assert "in any of its collision LODs lost its collision silently" in msg
    assert "while the others have one was not measured" in msg
    assert "uppercase" not in msg.lower()


def test_val_component_mixed_names(fork):
    """One "Component" and a number is enough: next to component01, an
    irregular Component_01 raises nothing (the WARN is for a LOD whose
    component-like names are none of them "Component" and a number)."""
    p3d = build_multilod_v2_p3d(fork)
    for kind in COLLISION_KINDS:
        lod = p3d.get_lod(kind)
        lod.selections["component01"] = lod.selections.pop("Component01")
        lod.set_selection("Component_01", point_idx=[0])
    assert p3d.validate() == []


COMPONENT_CODES = {"ERR_COMPONENT_NAMING", "WARN_COMPONENT_NAMING"}
RESOLUTION = {"geometry": 1.0e13, "view_geometry": 6.0e15,
              "fire_geometry": 7.0e15}


@pytest.mark.parametrize("kind", COLLISION_KINDS)
def test_val_component_not_required_without_own_faces(fork, kind):
    """A collision LOD with no faces (a Geometry LOD that only carries
    mass, the shape a worn item's has) or whose only face is a proxy
    triangle has no collision geometry of its own: no component finding,
    on each of the three kinds. The control: one face outside the proxy
    makes the same LOD raise the ERROR."""
    m = fork
    bare = m.LOD()
    bare.resolution = RESOLUTION[kind]
    pt = m.Point()
    pt.coords = (0.0, 0.0, 0.0)
    if kind == "geometry":
        pt.mass = 10.0
    bare.points.append(pt)
    proxied = m.LOD()
    proxied.resolution = RESOLUTION[kind]
    add_proxy_triangle(m, proxied, "proxy:\\dz\\data\\proxies\\flag.001")
    p3d = m.P3D()
    p3d.lods += [bare, proxied]
    assert not COMPONENT_CODES & set(codes(p3d.validate()))
    # the same builder, under a selection that is not a proxy: a face of
    # the LOD's own
    add_proxy_triangle(m, proxied, "glass", origin=(1.0, 1.0, 1.0))
    found = [f for f in p3d.validate() if f.code in COMPONENT_CODES]
    assert [(f.code, f.lod) for f in found] == [("ERR_COMPONENT_NAMING", 1)]
    assert found[0].msg.startswith(
        "%s LOD: 1 face(s) and no ComponentNN selection" % kind)


@pytest.mark.parametrize("kind", COLLISION_KINDS)
def test_val_component_proxy_name_is_not_enough(fork, kind):
    """Faces are proxy triangles only when their 'proxy:...' selection has
    a proxy's shape (1 triangle and its 3 corners). A cube whose 8 points and 6
    quads sit under a proxy name is collision geometry with no component."""
    p3d = build_multilod_v2_p3d(fork)
    lod = p3d.get_lod(kind)
    lod.selections["proxy:\\dz\\data\\proxies\\flag.001"] = \
        lod.selections.pop("Component01")
    index = next(i for i, l in enumerate(p3d.lods) if l is lod)
    found = [f for f in p3d.validate() if f.code in COMPONENT_CODES]
    assert [(f.code, f.lod) for f in found] == [("ERR_COMPONENT_NAMING", index)]


@pytest.mark.parametrize("kind", COLLISION_KINDS)
def test_val_component_proxy_points_are_its_corners(fork, kind):
    """A proxy selection's 3 points must be its triangle's corners: one
    that selects 3 other points does not make the triangle a proxy. The
    control is the same LOD before its selection is re-pointed."""
    m = fork
    lod = m.LOD()
    lod.resolution = RESOLUTION[kind]
    sel = add_proxy_triangle(m, lod, "proxy:\\dz\\data\\proxies\\flag.001")
    p3d = m.P3D()
    p3d.lods.append(lod)
    assert not COMPONENT_CODES & set(codes(p3d.validate()))
    others = []
    for xyz in ((4.0, 0.0, 0.0), (5.0, 0.0, 0.0), (4.0, 1.0, 0.0)):
        pt = m.Point()
        pt.coords = xyz
        lod.points.append(pt)
        others.append(pt)
    sel.points = {pt: 1 for pt in others}
    found = [f for f in p3d.validate() if f.code in COMPONENT_CODES]
    assert [(f.code, f.lod) for f in found] == [("ERR_COMPONENT_NAMING", 0)]


@pytest.mark.parametrize("name,mutate", CASES, ids=[c[0] for c in CASES])
def test_val_neg_code_1to1(fork, name, mutate):
    """Each negative fixture produces EXACTLY the expected codes."""
    p3d = build_multilod_v2_p3d(fork)
    expected = sorted(set(mutate(fork, p3d)))
    assert codes(p3d.validate()) == expected


@pytest.mark.parametrize("name,mutate", CASES, ids=[c[0] for c in CASES])
def test_val_audit_parity(fork, name, mutate, tmp_path):
    """The pruned audit (tools/audit_p3d.py, delegating to this library)
    reports the SAME findings, with severities mapped: ERROR to CRITICAL
    and exit 1, WARN to WARNING and exit 0."""
    p3d = build_multilod_v2_p3d(fork)
    expected = sorted(set(mutate(fork, p3d)))
    fx = tmp_path / ("%s.p3d" % name)
    with open(str(fx), "wb") as f:
        p3d.write(f)
    env = dict(os.environ, PYTHONPATH=REPO)
    r = subprocess.run([sys.executable, AUDIT, str(fx)],
                       capture_output=True, text=True, env=env, cwd=REPO)
    for code in expected:
        assert "[%s]" % code in r.stdout, (code, r.stdout)
        sev = "CRITICAL" if code.startswith("ERR_") else "WARNING"
        assert any(sev in ln and "[%s]" % code in ln
                   for ln in r.stdout.splitlines()), (code, r.stdout)
    has_err = any(c.startswith("ERR_") for c in expected)
    assert r.returncode == (1 if has_err else 0), r.stdout


def test_val_audit_parity_clean(fork, tmp_path):
    """The clean model passes the pruned audit: ALL PASSED, exit 0."""
    fx = tmp_path / "clean.p3d"
    with open(str(fx), "wb") as f:
        build_multilod_v2_p3d(fork).write(f)
    env = dict(os.environ, PYTHONPATH=REPO)
    r = subprocess.run([sys.executable, AUDIT, str(fx)],
                       capture_output=True, text=True, env=env, cwd=REPO)
    assert r.returncode == 0
    assert "ALL CHECKS PASSED" in r.stdout and "OVERALL: ALL PASSED" in r.stdout


# ---- WARN_COMPONENT_COVERAGE: the union of the components (1.9.0) -----

def coverage(findings):
    return [f for f in findings if f.code == "WARN_COMPONENT_COVERAGE"]


def test_coverage_pos_components_together(fork):
    """Each collision LOD holds two components that together cover every
    face: no finding. Up to 1.8.0 the Geometry LOD read 'Component01
    covers 8/16 vertices' and '6/12 faces'."""
    p3d = build_multilod_v2_p3d(fork)
    for kind, mass in (("geometry", 25.0), ("view_geometry", None),
                       ("fire_geometry", None)):
        lod = p3d.get_lod(kind)
        select_all(lod, "Component01")
        add_box(fork, lod, CROSS, "Component02", mass=mass)
    assert p3d.validate() == []


def test_coverage_pos_lowercase_components(fork):
    """Components named in lowercase count like 'ComponentNN'."""
    p3d = build_multilod_v2_p3d(fork)
    geo = p3d.get_lod("geometry")
    geo.selections["component01"] = geo.selections.pop("Component01")
    add_box(fork, geo, CROSS, "component02", mass=25.0)
    assert p3d.validate() == []


def test_coverage_pos_loose_point_not_counted(fork):
    """A point that no face uses has nothing to collide with: no finding.
    Up to 1.8.0: 'Component01 covers 8/9 vertices'."""
    p3d = build_multilod_v2_p3d(fork)
    p = fork.Point()
    p.coords = (0.0, 0.0, 0.0)
    p.mass = 25.0
    p3d.get_lod("geometry").points.append(p)
    assert p3d.validate() == []


def _geometry_with_proxy(m):
    p3d = build_multilod_v2_p3d(m)
    geo = p3d.get_lod("geometry")
    add_proxy_triangle(m, geo, "proxy:\\dz\\data\\proxies\\flag.001",
                       origin=(0.0, 0.0, 0.2))
    for p in geo.points[-3:]:
        p.mass = 0.0
    return p3d, geo


def test_coverage_proxy_triangle_not_counted(fork):
    """A proxy triangle outside every component is not a face to cover.
    Up to 1.8.0: 'Component01 covers 8/11 vertices' and '6/7 faces'."""
    p3d, _ = _geometry_with_proxy(fork)
    assert coverage(p3d.validate()) == []


def test_coverage_counts_exclude_proxy_faces(fork):
    """With a face of its own outside every component, the proxy triangle
    stays out of the count: 1 of 6 faces, not of 7."""
    p3d, geo = _geometry_with_proxy(fork)
    del geo.selections["Component01"].faces[geo.faces[0]]
    (f,) = coverage(p3d.validate())
    assert f.lod == 1 and f.severity == "WARN"
    assert f.msg.startswith(
        "geometry LOD: 1 of its 6 face(s) (proxy triangles not counted) are "
        "in no ComponentNN selection."), f.msg


def test_coverage_proxy_named_box_counts(fork):
    """A whole box under a proxy name is not a proxy triangle: its faces
    are collision geometry and, in no component, are counted (6 of 12)."""
    p3d = build_multilod_v2_p3d(fork)
    geo = p3d.get_lod("geometry")
    add_box(fork, geo, CROSS, "proxy:\\dz\\data\\proxies\\crate.001",
            mass=25.0)
    (f,) = coverage(p3d.validate())
    assert f.msg.startswith(
        "geometry LOD: 6 of its 12 face(s) (proxy triangles not counted) "
        "are in no ComponentNN selection, nor are 8 of the 16 point(s) its "
        "faces use."), f.msg


def test_coverage_empty_component_selection(fork):
    """A component selection that holds nothing is accepted by the naming
    check; coverage reports every face and point of the LOD."""
    p3d = build_multilod_v2_p3d(fork)
    sel = p3d.get_lod("geometry").selections["Component01"]
    sel.points = {}
    sel.faces = {}
    findings = p3d.validate()
    assert codes(findings) == ["WARN_COMPONENT_COVERAGE"]
    (f,) = coverage(findings)
    assert f.msg.startswith(
        "geometry LOD: 6 of its 6 face(s) (proxy triangles not counted) are "
        "in no ComponentNN selection, nor are 8 of the 8 point(s) its faces "
        "use."), f.msg


def test_coverage_message_faces(fork):
    """One face of the second component in neither: the count is over
    both components' faces, and no point is counted (its points stay in
    Component02)."""
    p3d = build_multilod_v2_p3d(fork)
    mut_coverage_face_outside(fork, p3d)
    (f,) = coverage(p3d.validate())
    assert f.lod == 1
    assert f.msg.startswith(
        "geometry LOD: 1 of its 12 face(s) (proxy triangles not counted) "
        "are in no ComponentNN selection."), f.msg


def test_coverage_message_faces_and_points(fork):
    """The face and its four corners out of Component02: the corners are
    counted against the 16 points the faces use."""
    p3d = build_multilod_v2_p3d(fork)
    geo = p3d.get_lod("geometry")
    _, faces = add_box(fork, geo, CROSS, "Component02", mass=25.0)
    sel = geo.selections["Component02"]
    del sel.faces[faces[0]]
    for v in faces[0].vertices:
        del sel.points[v.point]
    (f,) = coverage(p3d.validate())
    assert f.msg.startswith(
        "geometry LOD: 1 of its 12 face(s) (proxy triangles not counted) "
        "are in no ComponentNN selection, nor are 4 of the 16 point(s) its "
        "faces use."), f.msg


def test_coverage_message_points_only(fork):
    """Every face in a component but one of its points in none."""
    p3d = build_multilod_v2_p3d(fork)
    mut_component_coverage(fork, p3d)
    (f,) = coverage(p3d.validate())
    assert f.lod == 1
    assert f.msg.startswith(
        "geometry LOD: every face (proxy triangles not counted) is in a "
        "ComponentNN selection, but 1 of the 8 point(s) its faces use are "
        "in none."), f.msg


@pytest.mark.parametrize("kind,index", [("view_geometry", 2),
                                        ("fire_geometry", 3)])
def test_coverage_view_and_fire(fork, kind, index):
    """View and Fire are read like Geometry (up to 1.8.0, not at all)."""
    p3d = build_multilod_v2_p3d(fork)
    _cover_all_but_one_face(p3d.get_lod(kind))
    (f,) = coverage(p3d.validate())
    assert f.lod == index
    assert f.msg.startswith(
        "%s LOD: 1 of its 6 face(s) (proxy triangles not counted) are in no "
        "ComponentNN selection." % kind), f.msg


def test_coverage_zero_weight_is_not_cover(fork):
    """A zero weight is not written, so that face is in no component.
    (The in-memory round trip also reports the membership change.)"""
    p3d = build_multilod_v2_p3d(fork)
    sel = p3d.get_lod("geometry").selections["Component01"]
    sel.faces[next(iter(sel.faces))] = 0
    (f,) = coverage(p3d.validate())
    assert f.msg.startswith("geometry LOD: 1 of its 6 face(s)"), f.msg


def test_coverage_zero_point_weight_is_not_cover(fork):
    """The same for a point: every face is covered, one corner is not."""
    p3d = build_multilod_v2_p3d(fork)
    geo = p3d.get_lod("geometry")
    geo.selections["Component01"].points[geo.points[0]] = 0
    (f,) = coverage(p3d.validate())
    assert f.msg.startswith(
        "geometry LOD: every face (proxy triangles not counted) is in a "
        "ComponentNN selection, but 1 of the 8 point(s) its faces use are "
        "in none."), f.msg


def test_coverage_fractional_weights_cover(fork):
    """Any nonzero weight is a member, in memory and once written and read
    back (MLOD stores a fractional weight as a nonzero byte)."""
    import io
    p3d = build_multilod_v2_p3d(fork)
    sel = p3d.get_lod("geometry").selections["Component01"]
    sel.points = {p: 0.5 for p in sel.points}
    sel.faces = {fa: 0.25 for fa in sel.faces}
    assert coverage(p3d.validate()) == []
    buf = io.BytesIO()
    p3d.write(buf)
    buf.seek(0)
    reread = fork.P3D(buf)
    weights = reread.get_lod("geometry").selections["Component01"].faces
    assert len(weights) == 6 and all(0 < w < 1 for w in weights.values())
    assert coverage(reread.validate()) == []


def test_coverage_silent_on_proxy_only_lod(fork):
    """A collision LOD that holds only a proxy triangle has no face of its
    own to cover, even with a component selection present. Up to 1.8.0,
    on the Geometry LOD: 'Component01 covers 0/3 vertices' and '0/1
    faces'."""
    p3d = build_multilod_v2_p3d(fork)
    geo = p3d.get_lod("geometry")
    lod = fork.LOD()
    lod.resolution = geo.resolution
    lod.properties["autocenter"] = "0"
    add_proxy_triangle(fork, lod, "proxy:\\dz\\data\\proxies\\flag.001")
    lod.new_selection("Component01")
    p3d.lods[p3d.lods.index(geo)] = lod
    assert coverage(p3d.validate()) == []


def test_coverage_silent_without_components(fork):
    """No component selection at all is ERR_COMPONENT_NAMING's finding;
    coverage adds nothing."""
    p3d = build_multilod_v2_p3d(fork)
    p3d.get_lod("geometry").selections.pop("Component01")
    assert coverage(p3d.validate()) == []
