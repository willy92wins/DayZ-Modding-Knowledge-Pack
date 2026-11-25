"""Tests for bind_pose_check.py: SEModel reading and the bind-pose check.

Pure Python, no numpy, no bpy. SEModels are synthetic, built with struct
in tmp_path; rigs are nested-list matrices built here. The cases are the
24 numbered cases of the bind-pose check brief.
"""

import copy
import importlib.util
import json
import math
import struct
from pathlib import Path

import pytest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bpc = _load("bind_pose_check", SCRIPTS / "bind_pose_check.py")
se = _load("seanim_export_for_bind_test", SCRIPTS / "seanim_export.py")

IDENT = (0.0, 0.0, 0.0, 1.0)
ALPHA_POS = (0.1, -0.2, 0.3)
BETA_POS = (0.0, 0.1, 0.0)


def _q_axis(axis, deg):
    half = math.radians(deg) / 2.0
    s = math.sin(half)
    return (axis[0] * s, axis[1] * s, axis[2] * s, math.cos(half))


def _mat(pos, quat):
    x, y, z, w = quat
    r = [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
         [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
         [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]
    return [r[0] + [pos[0]], r[1] + [pos[1]], r[2] + [pos[2]],
            [0.0, 0.0, 0.0, 1.0]]


def _mul(a, b):
    return [[sum(a[r][k] * b[k][c] for k in range(4)) for c in range(4)]
            for r in range(4)]


def _spec(name, parent, lp=(0.0, 0.0, 0.0), lq=IDENT, **kw):
    spec = {"name": name, "parent": parent, "lp": lp, "lq": lq,
            "flags": 0, "gp": (0.0, 0.0, 0.0), "gr": IDENT,
            "scale": (1.0, 1.0, 1.0)}
    spec.update(kw)
    return spec


def _write_semodel(path, specs, parent_indices=None):
    names = [s["name"] for s in specs]
    out = bytearray()
    out += b"SEModel" + struct.pack("<HH", 1, 20) + b"\0\0\0"
    out += struct.pack("<III", len(specs), 0, 0) + b"\0\0\0"
    assert len(out) == 29
    for name in names:
        out += name.encode("utf-8") + b"\0"
    for i, s in enumerate(specs):
        if parent_indices is not None:
            par = parent_indices[i]
        elif s["parent"] is None:
            par = -1
        else:
            par = names.index(s["parent"])
        out += struct.pack("<Bi", s["flags"], par)
        out += struct.pack("<3f", *s["gp"])
        out += struct.pack("<4f", *s["gr"])
        out += struct.pack("<3f", *s["lp"])
        out += struct.pack("<4f", *s["lq"])
        out += struct.pack("<3f", *s["scale"])
    Path(path).write_bytes(bytes(out))
    return Path(path)


def _default_specs(frame, beta_pos=BETA_POS, beta_quat=IDENT, beta_lq=None):
    return [
        _spec("Scene_Root", None),
        _spec("Alpha", "Scene_Root",
              lp=se.seanim_pos_cm(frame, ALPHA_POS),
              lq=se.seanim_rot(frame, IDENT)),
        _spec("Beta", "Alpha",
              lp=se.seanim_pos_cm(frame, beta_pos),
              lq=beta_lq if beta_lq is not None else se.seanim_rot(frame, beta_quat)),
    ]


def _rig(beta_pos=BETA_POS, beta_quat=IDENT, beta_parent="Alpha"):
    alpha = _mat(ALPHA_POS, IDENT)
    beta = _mul(alpha, _mat(beta_pos, beta_quat))
    rig = {"Alpha": {"parent": None, "matrix_local": alpha},
           "Beta": {"parent": beta_parent, "matrix_local": beta}}
    if beta_parent not in (None, "Alpha"):
        rig[beta_parent] = {"parent": None,
                            "matrix_local": _mat((0.5, 0.0, 0.0), IDENT)}
        beta = _mul(rig[beta_parent]["matrix_local"], _mat(beta_pos, beta_quat))
        rig["Beta"] = {"parent": beta_parent, "matrix_local": beta}
    return rig


def _jd_rig(beta_pos=BETA_POS, beta_quat=IDENT):
    rig = _rig(beta_pos, beta_quat)
    for name, jd in bpc.JD_ROOTS.items():
        rig[name] = {"parent": None,
                     "matrix_local": copy.deepcopy(jd["matrix_local"])}
    return rig


def _run(tmp_path, specs, rig, frame, report="report.json", se_name="model.semodel"):
    se_path = _write_semodel(tmp_path / se_name, specs)
    blend = tmp_path / "rig.blend"
    blend.write_bytes(b"fake blend")
    report_path = tmp_path / report if report else None
    code = bpc.run_check(str(se_path), rig, str(blend),
                         report_path=str(report_path) if report_path else None,
                         frame=frame)
    data = json.loads(report_path.read_text()) if report_path and report_path.exists() else None
    return code, data, se_path, blend


def test_case01_valid_semodel_read():
    """Case 1: a valid 3-bone SEModel reads names, parents, all 17 floats."""
    import tempfile, os
    specs = [
        _spec("Scene_Root", None, flags=1, gp=(1.0, 2.0, 3.0),
              gr=(0.5, -0.5, 0.25, 1.0), lp=(4.0, 5.0, 6.0),
              lq=(0.0, 0.5, -0.25, 1.0), scale=(1.0, 2.0, 0.5)),
        _spec("Alpha", "Scene_Root", flags=2, gp=(-1.0, 0.5, 2.5),
              gr=(1.0, 0.0, 0.0, 0.5), lp=(7.0, 8.0, 9.0),
              lq=(0.25, 0.25, 0.25, 1.0), scale=(0.5, 0.5, 2.0)),
        _spec("Beta", "Alpha", flags=3, gp=(3.5, -2.5, 1.5),
              gr=(0.0, 1.0, 0.0, 0.5), lp=(10.0, 11.0, 12.0),
              lq=(1.0, 1.0, 0.0, 0.0), scale=(2.0, 1.0, 1.0)),
    ]
    with tempfile.TemporaryDirectory() as td:
        path = _write_semodel(Path(td) / "m.semodel", specs)
        bones = bpc.read_semodel(str(path))
    assert list(bones) == ["Scene_Root", "Alpha", "Beta"]
    assert bones["Scene_Root"]["parent"] is None
    assert bones["Alpha"]["parent"] == "Scene_Root"
    assert bones["Beta"]["parent"] == "Alpha"
    for spec in specs:
        rec = bones[spec["name"]]
        assert rec["flags"] == spec["flags"]
        for key, field in (("gp", "global_position"), ("gr", "global_rotation"),
                           ("lp", "local_position"), ("lq", "local_rotation"),
                           ("scale", "scale")):
            assert rec[field] == pytest.approx(spec[key]), (spec["name"], field)


def _input_error(tmp_path, mutate):
    se_path = _write_semodel(tmp_path / "model.semodel", _default_specs("fbx"))
    mutate(se_path)
    blend = tmp_path / "rig.blend"; blend.write_bytes(b"fake")
    report = tmp_path / "report.json"
    code = bpc.run_check(str(se_path), _rig(), str(blend),
                         report_path=str(report), frame="fbx")
    assert code == 2
    assert "error" in json.loads(report.read_text())


def test_case02_bad_magic(tmp_path):
    """Case 2: bad magic is an input error, exit 2 through run_check."""
    def mutate(p):
        data = bytearray(p.read_bytes()); data[:7] = b"XXXXXXX"; p.write_bytes(bytes(data))
    _input_error(tmp_path, mutate)


def test_case03_short_header(tmp_path):
    """Case 3: a short header is an input error, exit 2."""
    def mutate(p):
        p.write_bytes(b"SEModel" + b"\0" * 10)
    _input_error(tmp_path, mutate)


def test_case04_short_records(tmp_path):
    """Case 4: short bone records are an input error, exit 2."""
    def mutate(p):
        p.write_bytes(p.read_bytes()[:-10])
    _input_error(tmp_path, mutate)


def test_case05_two_roots(tmp_path):
    """Case 5: two roots are an input error, exit 2."""
    specs = _default_specs("fbx")
    specs[1]["parent"] = None
    se_path = _write_semodel(tmp_path / "model.semodel", specs)
    blend = tmp_path / "rig.blend"; blend.write_bytes(b"fake")
    report = tmp_path / "report.json"
    code = bpc.run_check(str(se_path), _rig(), str(blend),
                         report_path=str(report), frame="fbx")
    assert code == 2 and "error" in json.loads(report.read_text())


def test_case06_parent_out_of_range(tmp_path):
    """Case 6: a parent index out of range is an input error, exit 2."""
    specs = _default_specs("fbx")
    se_path = _write_semodel(tmp_path / "model.semodel", specs,
                             parent_indices=[-1, 0, 99])
    blend = tmp_path / "rig.blend"; blend.write_bytes(b"fake")
    report = tmp_path / "report.json"
    code = bpc.run_check(str(se_path), _rig(), str(blend),
                         report_path=str(report), frame="fbx")
    assert code == 2 and "error" in json.loads(report.read_text())


def test_case07_identical_frames_pass(tmp_path):
    """Case 7: identical frames pass, nothing listed."""
    code, data, _, _ = _run(tmp_path, _default_specs("fbx"), _rig(), "fbx")
    assert code == 0
    assert data["over"] == [] and data["parent_mismatch"] == []
    assert data["non_finite"] == [] and data["compared"] == 1


def test_case08_sign_flipped_quaternion_passes(tmp_path):
    """Case 8: a quaternion with its sign flipped passes."""
    specs = _default_specs("fbx", beta_lq=(0.0, 0.0, 0.0, -1.0))
    code, data, _, _ = _run(tmp_path, specs, _rig(), "fbx")
    assert code == 0 and data["over"] == []


def test_case09_turned_006_deg_fails_only_that_bone(tmp_path):
    """Case 9: a bone turned 0.06 deg fails and is the only one listed."""
    quat = _q_axis((1.0, 0.0, 0.0), 0.06)
    code, data, _, _ = _run(tmp_path, _default_specs("fbx"),
                            _rig(beta_quat=quat), "fbx")
    assert code == 1
    assert [e["bone"] for e in data["over"]] == ["Beta"]
    assert data["over"][0]["deg"] == pytest.approx(0.06, abs=0.001)


def test_case10_moved_002_mm_fails(tmp_path):
    """Case 10: a bone moved 0.02 mm fails."""
    pos = (BETA_POS[0], BETA_POS[1] + 0.00002, BETA_POS[2])
    code, data, _, _ = _run(tmp_path, _default_specs("fbx"),
                            _rig(beta_pos=pos), "fbx")
    assert code == 1
    assert [e["bone"] for e in data["over"]] == ["Beta"]
    assert data["over"][0]["mm"] == pytest.approx(0.02, abs=0.001)


def test_case11_different_parent_fails(tmp_path):
    """Case 11: a different parent fails."""
    code, data, _, _ = _run(tmp_path, _default_specs("fbx"),
                            _rig(beta_parent="Gamma"), "fbx")
    assert code == 1
    assert data["parent_mismatch"] and data["parent_mismatch"][0][0] == "Beta"


def test_case12_root_and_absent_game_parent_not_compared(tmp_path):
    """Case 12: the game root, and 'game parent absent, root here', are not compared."""
    code, data, _, _ = _run(tmp_path, _default_specs("fbx"), _rig(), "fbx")
    assert code == 0
    listed = [entry[0] for entry in data["not_compared"]]
    assert "Scene_Root" in listed and "Alpha" in listed
    assert data["over"] == []


def test_case13_game_bone_missing_is_listed_not_failing(tmp_path):
    """Case 13: a game bone missing from the rig is listed and does not fail."""
    specs = _default_specs("fbx")
    specs.append(_spec("Gamma", "Alpha", lp=(1.0, 2.0, 3.0)))
    code, data, _, _ = _run(tmp_path, specs, _rig(), "fbx")
    assert code == 0
    assert data["absent_in_armature"] == ["Gamma"]


def test_case14_jd_roots_pass(tmp_path):
    """Case 14: roots equal to the JD roots pass."""
    code, data, _, _ = _run(tmp_path, _default_specs("jd"), _jd_rig(), "jd")
    assert code == 0
    assert data["roots_compared"] is True
    assert data["roots_over"] == [] and data["roots_missing"] == []


def test_case15_pelvis_turned_180_fails_only_root(tmp_path):
    """Case 15: Pelvis turned 180 deg about Z fails, the only root listed."""
    rig = _jd_rig()
    turn = _mat((0.0, 0.0, 0.0), _q_axis((0.0, 0.0, 1.0), 180.0))
    rig["Pelvis"]["matrix_local"] = _mul(turn, rig["Pelvis"]["matrix_local"])
    code, data, _, _ = _run(tmp_path, _default_specs("jd"), rig, "jd")
    assert code == 1
    assert [e["bone"] for e in data["roots_over"]] == ["Pelvis"]
    assert data["roots_over"][0]["deg"] == pytest.approx(180.0, abs=0.01)


def test_case16_entityposition_turned_120_fails(tmp_path):
    """Case 16: EntityPosition turned 120 deg fails."""
    rig = _jd_rig()
    turn = _mat((0.0, 0.0, 0.0), _q_axis((0.0, 0.0, 1.0), 120.0))
    rig["EntityPosition"]["matrix_local"] = _mul(
        turn, rig["EntityPosition"]["matrix_local"])
    code, data, _, _ = _run(tmp_path, _default_specs("jd"), rig, "jd")
    assert code == 1
    assert [e["bone"] for e in data["roots_over"]] == ["EntityPosition"]
    assert data["roots_over"][0]["deg"] == pytest.approx(120.0, abs=0.01)


def test_case17_fbx_roots_not_compared(tmp_path):
    """Case 17: on an fbx rig the roots are not compared, and the report says so."""
    rig = _rig()
    for name in bpc.JD_ROOTS:
        turned = _mat((1.0, 2.0, 3.0), _q_axis((0.0, 0.0, 1.0), 90.0))
        rig[name] = {"parent": None, "matrix_local": turned}
    code, data, _, _ = _run(tmp_path, _default_specs("fbx"), rig, "fbx")
    assert code == 0
    assert data["roots_compared"] is False
    assert data["roots_over"] == []


@pytest.mark.parametrize("kind,bone,field", [
    ("rig_matrix", "Beta", "matrix_local"),
    ("root_matrix", "Pelvis", "matrix_local"),
    ("se_local_rotation", "Beta", "local_rotation"),
    ("se_global_rotation", "Beta", "global_rotation"),
])
def test_case18_nan_names_bone(tmp_path, kind, bone, field):
    """Case 18: a NaN (parametrized by where it sits) exits 1 naming its bone."""
    nan = float("nan")
    if kind.startswith("se_"):
        specs = _default_specs("jd" if kind == "root_matrix" else "fbx")
        if kind == "se_local_rotation":
            specs[2]["lq"] = (nan, 0.0, 0.0, 1.0)
        else:
            specs[2]["gr"] = (0.0, nan, 0.0, 1.0)
        code, data, _, _ = _run(tmp_path, specs, _rig(), "fbx")
    elif kind == "rig_matrix":
        rig = _rig(); rig["Beta"]["matrix_local"][0][0] = nan
        code, data, _, _ = _run(tmp_path, _default_specs("fbx"), rig, "fbx")
    else:
        rig = _jd_rig(); rig["Pelvis"]["matrix_local"][1][1] = nan
        code, data, _, _ = _run(tmp_path, _default_specs("jd"), rig, "jd")
    assert code == 1
    hits = [e for e in data["non_finite"] if e["bone"] == bone]
    assert hits and field in hits[0]["field"], data["non_finite"]


@pytest.mark.parametrize("kind,bone,field", [
    ("rig_translation", "Beta", "matrix_local"),
    ("se_local_position", "Beta", "local_position"),
    ("se_global_position", "Beta", "global_position"),
    ("se_scale", "Beta", "scale"),
])
def test_case19_infinity_names_bone(tmp_path, kind, bone, field):
    """Case 19: an infinity (parametrized) exits 1 naming its bone."""
    inf = float("inf")
    if kind == "rig_translation":
        rig = _rig(); rig["Beta"]["matrix_local"][0][3] = inf
        code, data, _, _ = _run(tmp_path, _default_specs("fbx"), rig, "fbx")
    else:
        specs = _default_specs("fbx")
        if kind == "se_local_position":
            specs[2]["lp"] = (inf, 0.0, 0.0)
        elif kind == "se_global_position":
            specs[2]["gp"] = (0.0, inf, 0.0)
        else:
            specs[2]["scale"] = (1.0, inf, 1.0)
        code, data, _, _ = _run(tmp_path, specs, _rig(), "fbx")
    assert code == 1
    hits = [e for e in data["non_finite"] if e["bone"] == bone]
    assert hits and field in hits[0]["field"], data["non_finite"]


def test_case20_double_precision_angle(tmp_path):
    """Case 20 (R1): 0.03 deg reports 0.03 within 0.001 and passes; 0.049 passes; 0.051 fails."""
    for deg, expected in ((0.03, 0), (0.049, 0), (0.051, 1)):
        quat = _q_axis((1.0, 0.0, 0.0), deg)
        sub = tmp_path / ("case%g" % deg); sub.mkdir()
        code, data, _, _ = _run(sub, _default_specs("fbx"),
                                _rig(beta_quat=quat), "fbx")
        assert code == expected, (deg, data)
        assert data["max_deg"] == pytest.approx(deg, abs=0.001), (deg, data)


@pytest.mark.parametrize("which", ["semodel", "blend", "semodel_dotdot"])
def test_case21_report_must_not_replace_input(tmp_path, capsys, which):
    """Case 21 (R4): --report equal to an input exits 2, bytes kept, no report written."""
    se_path = _write_semodel(tmp_path / "model.semodel", _default_specs("fbx"))
    blend = tmp_path / "rig.blend"; blend.write_bytes(b"fake blend bytes")
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    if which == "semodel":
        report = str(se_path)
    elif which == "blend":
        report = str(blend)
    else:
        (tmp_path / "sub").mkdir()
        report = str(tmp_path / "sub" / ".." / "model.semodel")
    code = bpc.run_check(str(se_path), _rig(), str(blend),
                         report_path=report, frame="fbx")
    captured = capsys.readouterr()
    assert code == 2
    assert ("semodel" in captured.err) if which != "blend" else ("blend" in captured.err)
    after = {p.name: p.read_bytes() for p in tmp_path.iterdir() if p.is_file()}
    assert after == before


def test_case22_nonfinite_result_from_finite_inputs(tmp_path):
    """Case 22 (R2): a rig offset of 1e307 m exits 1 naming its bone in non_finite."""
    rig = _rig(beta_pos=(1e307, 0.1, 0.0))
    code, data, _, _ = _run(tmp_path, _default_specs("jd"), rig, "jd")
    assert code == 1
    hits = [e for e in data["non_finite"] if e["bone"] == "Beta"]
    assert hits, data["non_finite"]


@pytest.mark.parametrize("root", ["Pelvis", "EntityPosition", "Collision"])
def test_case23_each_root_alone(tmp_path, root):
    """Case 23 (R5): each root alone, turned 1 deg or moved 0.02 mm, is the only root listed."""
    turn_dir = tmp_path / "turn"; turn_dir.mkdir()
    rig = _jd_rig()
    turn = _mat((0.0, 0.0, 0.0), _q_axis((0.0, 0.0, 1.0), 1.0))
    rig[root]["matrix_local"] = _mul(turn, rig[root]["matrix_local"])
    code, data, _, _ = _run(turn_dir, _default_specs("jd"), rig, "jd")
    assert code == 1 and [e["bone"] for e in data["roots_over"]] == [root], data
    move_dir = tmp_path / "move"; move_dir.mkdir()
    rig = _jd_rig()
    rig[root]["matrix_local"][0][3] += 0.00002
    code, data, _, _ = _run(move_dir, _default_specs("jd"), rig, "jd")
    assert code == 1 and [e["bone"] for e in data["roots_over"]] == [root], data
    assert data["roots_over"][0]["mm"] == pytest.approx(0.02, abs=0.001)


def test_case24_jd_constants_match_measured_values():
    """Case 24: the JD constants equal the measured JD Master Rig values within 1e-9."""
    expected = {
        "Collision": ([0.0, 0.0, 0.0],
                      [[1.0, 0.0, 0.0, 0.0], [0.0, 0.0, -1.0, 0.0],
                       [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0]]),
        "EntityPosition": ([0.0, 0.0, 0.0],
                           [[1.0, 0.0, 0.0, 0.0], [0.0, 0.0, -1.0, 0.0],
                            [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0]]),
        "Pelvis": ([0.0, 0.0, 1.0],
                   [[1.0, 2.220446049250313e-16, 2.220445519854721e-16, 0.0],
                    [2.220445784552517e-16, -4.371139183945161e-08, -1.0, 0.0],
                    [-2.220446049250313e-16, 1.0, -1.1920928955078125e-07, 1.0],
                    [0.0, 0.0, 0.0, 1.0]]),
    }
    assert set(bpc.JD_ROOTS) == set(expected)
    for name, (head, matrix) in expected.items():
        got = bpc.JD_ROOTS[name]
        assert got["head"] == pytest.approx(head, abs=1e-9), name
        for r in range(4):
            assert got["matrix_local"][r] == pytest.approx(matrix[r], abs=1e-9), (name, r)
