"""validate() 1.2.0: one negative per finding code, and parity with
tools/audit_p3d.py."""

import os
import subprocess
import sys

import pytest

from builders import build_multilod_v2_p3d

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIT = os.path.join(REPO, "tools", "audit_p3d.py")


def codes(findings):
    return sorted({f.code for f in findings})


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

def mut_component_lowercase(m, p3d):
    geo = p3d.get_lod("geometry")
    geo.selections["component01"] = geo.selections.pop("Component01")
    return ["ERR_COMPONENT_NAMING"]

def mut_component_none(m, p3d):
    p3d.get_lod("geometry").selections.pop("Component01")
    return ["ERR_COMPONENT_NAMING"]

def mut_component_case(m, p3d):
    geo = p3d.get_lod("geometry")
    geo.selections["COMPONENT01"] = geo.selections.pop("Component01")
    return ["WARN_COMPONENT_NAMING"]

def mut_component_coverage(m, p3d):
    geo = p3d.get_lod("geometry")
    sel = geo.selections["Component01"]
    first = next(iter(sel.points))
    del sel.points[first]
    return ["WARN_COMPONENT_COVERAGE"]

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
    ("component_lowercase", mut_component_lowercase),
    ("component_none", mut_component_none),
    ("component_case", mut_component_case),
    ("component_coverage", mut_component_coverage),
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
