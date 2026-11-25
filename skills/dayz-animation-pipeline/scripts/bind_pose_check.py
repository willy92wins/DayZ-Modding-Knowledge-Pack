#!/usr/bin/env python3
"""Check an armature's rest pose against the game bind pose (SEModel).

Usage (Blender):
  blender -b rig.blend --python bind_pose_check.py -- --semodel player_testing.semodel
      [--armature _DayZ_Character] [--tol-deg 0.05] [--tol-mm 0.01] [--report out.json]

The SEModel is the DayZATool --extract-mdl output described in
references/player-skeleton.md. Each bone's local frame in the armature is
compared with the SEModel local position (cm) and rotation through the map
of scripts/seanim_export.py (seanim_rot, seanim_pos_cm, detect_rig_frame);
the map is imported, not copied. With a jd rig the three armature roots
(Pelvis, EntityPosition, Collision) are also compared with the JD Master
Rig constants below, in armature space.

Exits: 0 pass; 1 fail (a local or a root over tolerance, a parent
mismatch, a non-finite number); 2 input error (missing file or armature,
an unreadable SEModel, a rig frame that cannot be read, a --report path
that is an input); 3 the tool itself crashed.

Every angle and distance is computed in double precision from Python
floats copied out of the inputs: mathutils stores and computes in
float32, where a quaternion dot product cannot resolve less than about
0.03 deg next to the 0.05 deg tolerance (measured 2026-11-19), so no
mathutils value is ever compared here.
"""
import argparse
import json
import math
import os
import struct
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
from seanim_export import detect_rig_frame, seanim_pos_cm, seanim_rot  # noqa: E402


class InputError(Exception):
    """An input error: exit 2."""


# JD Master Rig roots in armature space (Blender 5.3, object matrix_world
# identity; measured 2026-11-25, byte for byte the 2026-11-18 values).
JD_ROOTS = {
    "Collision": {
        "head": [0.0, 0.0, 0.0],
        "matrix_local": [[1.0, 0.0, 0.0, 0.0], [0.0, 0.0, -1.0, 0.0],
                         [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0]],
    },
    "EntityPosition": {
        "head": [0.0, 0.0, 0.0],
        "matrix_local": [[1.0, 0.0, 0.0, 0.0], [0.0, 0.0, -1.0, 0.0],
                         [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0]],
    },
    "Pelvis": {
        "head": [0.0, 0.0, 1.0],
        "matrix_local": [[1.0, 2.220446049250313e-16, 2.220445519854721e-16, 0.0],
                         [2.220445784552517e-16, -4.371139183945161e-08, -1.0, 0.0],
                         [-2.220446049250313e-16, 1.0, -1.1920928955078125e-07, 1.0],
                         [0.0, 0.0, 0.0, 1.0]],
    },
}

ROOT_NAMES = ("Pelvis", "EntityPosition", "Collision")
_SE_FIELDS = (("global_position", 3), ("global_rotation", 4),
              ("local_position", 3), ("local_rotation", 4), ("scale", 3))


def read_semodel(path):
    """Read an SEModel bind pose.

    Returns {name: {"parent", "parent_index", "flags", "global_position",
    "global_rotation", "local_position", "local_rotation", "scale"}} with
    every value a Python float (positions in cm, rotations xyzw). Raises
    InputError on a missing file, bad magic, a short header or records,
    a parent out of range, or a root count other than one.
    """
    if not path or not os.path.isfile(path):
        raise InputError("file not found: %s" % path)
    with open(path, "rb") as handle:
        data = handle.read()
    if len(data) < 29:
        raise InputError("file too short for an SEModel header (%d B)" % len(data))
    if data[:7] != b"SEModel":
        raise InputError("not an SEModel file (magic %r)" % data[:7])
    count = struct.unpack_from("<I", data, 14)[0]
    if not 0 < count < 10000:
        raise InputError("boneCount %d out of range" % count)
    off = 29
    names = []
    try:
        for _ in range(count):
            end = data.index(b"\0", off)
            names.append(data[off:end].decode("utf-8"))
            off = end + 1
    except (ValueError, UnicodeDecodeError) as exc:
        raise InputError("bone name table unreadable: %s" % exc)
    if len(data) < off + 73 * count:
        raise InputError("file too short for %d bone records of 73 B" % count)
    bones = {}
    roots = []
    for index in range(count):
        parent_index = struct.unpack_from("<i", data, off + 1)[0]
        if parent_index < -1 or parent_index >= count:
            raise InputError("bone %s: parent index %d out of range"
                             % (names[index], parent_index))
        if parent_index < 0:
            roots.append(names[index])
        bones[names[index]] = {
            "parent": names[parent_index] if parent_index >= 0 else None,
            "parent_index": parent_index,
            "flags": struct.unpack_from("<B", data, off)[0],
            "global_position": tuple(float(v) for v in struct.unpack_from("<3f", data, off + 5)),
            "global_rotation": tuple(float(v) for v in struct.unpack_from("<4f", data, off + 17)),
            "local_position": tuple(float(v) for v in struct.unpack_from("<3f", data, off + 33)),
            "local_rotation": tuple(float(v) for v in struct.unpack_from("<4f", data, off + 45)),
            "scale": tuple(float(v) for v in struct.unpack_from("<3f", data, off + 61)),
        }
        bones[names[index]]["lp"] = bones[names[index]]["local_position"]
        bones[names[index]]["lq"] = bones[names[index]]["local_rotation"]
        off += 73
    if len(roots) != 1:
        raise InputError("expected exactly one root, got %s" % roots)
    return bones


def _float_matrix(matrix):
    return [[float(matrix[r][c]) for c in range(4)] for r in range(4)]


def _mat_mul(a, b):
    return [[sum(a[r][k] * b[k][c] for k in range(4)) for c in range(4)]
            for r in range(4)]


def _rigid_inverse(m):
    out = [[0.0] * 4 for _ in range(4)]
    for r in range(3):
        for c in range(3):
            out[r][c] = m[c][r]
    for r in range(3):
        out[r][3] = -sum(out[r][k] * m[k][3] for k in range(3))
    out[3][3] = 1.0
    return out


def _quat_from_matrix(m):
    """Quaternion (x, y, z, w) of the rotation part, in double precision."""
    r = [[float(m[i][j]) for j in range(3)] for i in range(3)]
    trace = r[0][0] + r[1][1] + r[2][2]
    if trace > 0.0:
        s = math.sqrt(trace + 1.0) * 2.0
        q = ((r[2][1] - r[1][2]) / s, (r[0][2] - r[2][0]) / s,
             (r[1][0] - r[0][1]) / s, 0.25 * s)
    elif r[0][0] > r[1][1] and r[0][0] > r[2][2]:
        s = math.sqrt(1.0 + r[0][0] - r[1][1] - r[2][2]) * 2.0
        q = (0.25 * s, (r[0][1] + r[1][0]) / s, (r[0][2] + r[2][0]) / s,
             (r[2][1] - r[1][2]) / s)
    elif r[1][1] > r[2][2]:
        s = math.sqrt(1.0 + r[1][1] - r[0][0] - r[2][2]) * 2.0
        q = ((r[0][1] + r[1][0]) / s, 0.25 * s, (r[1][2] + r[2][1]) / s,
             (r[0][2] - r[2][0]) / s)
    else:
        s = math.sqrt(1.0 + r[2][2] - r[0][0] - r[1][1]) * 2.0
        q = ((r[0][2] + r[2][0]) / s, (r[1][2] + r[2][1]) / s, 0.25 * s,
             (r[1][0] - r[0][1]) / s)
    return _normalize_quat(q)


def _normalize_quat(q):
    q = tuple(float(v) for v in q)
    norm = math.sqrt(sum(v * v for v in q))
    if norm == 0.0 or not math.isfinite(norm):
        return q
    return tuple(v / norm for v in q)


def _angle_deg(a, b):
    """Angle in degrees between rotations a and b (xyzw), in double.

    Uses the relative quaternion and 2*atan2(|v|, |w|), well conditioned
    near zero and independent of either quaternion's sign.
    """
    qa = _normalize_quat(a)
    qb = _normalize_quat(b)
    rel = _quat_mul((-qa[0], -qa[1], -qa[2], qa[3]), qb)
    vec = math.sqrt(rel[0] ** 2 + rel[1] ** 2 + rel[2] ** 2)
    return math.degrees(2.0 * math.atan2(vec, abs(rel[3])))


def _quat_mul(a, b):
    ax, ay, az, aw = (float(v) for v in a)
    bx, by, bz, bw = (float(v) for v in b)
    return (aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz)


def _norm_path(path):
    return os.path.normcase(os.path.abspath(path)) if path else None


def _report_input_kind(report_path, semodel_path, blend_path):
    """'semodel', 'blend' or None: which input a report path would replace."""
    if not report_path:
        return None
    target = _norm_path(report_path)
    for kind, candidate in (("semodel", semodel_path), ("blend", blend_path)):
        if candidate and target == _norm_path(candidate):
            return kind
    if os.path.exists(report_path):
        for kind, candidate in (("semodel", semodel_path), ("blend", blend_path)):
            if candidate and os.path.isfile(candidate):
                try:
                    if os.path.samefile(report_path, candidate):
                        return kind
                except OSError:
                    pass
    return None


def _new_report(frame, armature, tol_deg, tol_mm):
    return {"exit": 0, "frame": frame, "armature": armature,
            "tol_deg": tol_deg, "tol_mm": tol_mm, "compared": 0,
            "max_deg": None, "max_mm": None, "over": [],
            "parent_mismatch": [], "absent_in_armature": [],
            "not_compared": [], "roots_compared": False, "roots_over": [],
            "roots_missing": [], "non_finite": []}


def _write_report(report_path, report):
    if report_path:
        with open(report_path, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, sort_keys=True)
            handle.write("\n")


def _finish(report, report_path, code):
    report["exit"] = code
    _write_report(report_path, report)
    return code


def run_check(semodel_path, bones, blend_path, report_path=None,
              tol_deg=0.05, tol_mm=0.01, frame=None,
              armature="_DayZ_Character"):
    """Run the bind-pose check and return the exit code (0, 1 or 2).

    bones maps each bone of the armature to {"parent": <name or None>,
    "matrix_local": <4x4 nested list, rows, armature space, meters>}.
    blend_path is the loaded .blend file, used only to keep --report from
    replacing an input. With frame None the frame comes from
    detect_rig_frame. The report is written to report_path when one is
    given and it is safe to write; this function never exits the process.
    """
    report = _new_report(frame, armature, tol_deg, tol_mm)
    kind = _report_input_kind(report_path, semodel_path, blend_path)
    if kind is not None:
        report["exit"] = 2
        report["error"] = ("--report %s is the %s input; refusing to "
                           "overwrite it" % (report_path, kind))
        print(report["error"], file=sys.stderr)
        return 2
    try:
        semodel = read_semodel(semodel_path)
    except InputError as exc:
        report["error"] = str(exc)
        return _finish(report, report_path, 2)

    non_finite = []
    for name, rec in semodel.items():
        for field, _size in _SE_FIELDS:
            for index, value in enumerate(rec[field]):
                if not math.isfinite(float(value)):
                    non_finite.append({"bone": name,
                                       "field": "%s[%d]" % (field, index)})
    rig = {}
    for name, bone in bones.items():
        matrix = _float_matrix(bone["matrix_local"])
        rig[name] = {"parent": bone.get("parent"), "matrix_local": matrix}
        for r in range(4):
            for c in range(4):
                if not math.isfinite(matrix[r][c]):
                    non_finite.append(
                        {"bone": name, "field": "matrix_local[%d][%d]" % (r, c)})
    if non_finite:
        report["non_finite"] = non_finite
        print("bind_pose_check: non-finite input: %s" % non_finite,
              file=sys.stderr)
        return _finish(report, report_path, 1)

    locals_ = {}
    for name, bone in rig.items():
        parent = bone["parent"]
        if parent is not None and parent in rig:
            local = _mat_mul(_rigid_inverse(rig[parent]["matrix_local"]),
                             bone["matrix_local"])
        else:
            local = [row[:] for row in bone["matrix_local"]]
        locals_[name] = {"parent": parent, "matrix": local,
                         "pos": tuple(local[r][3] for r in range(3)),
                         "quat": _quat_from_matrix(local)}
    if frame is None:
        rig_for_frame = {"bones": [
            {"name": name, "parent": item["parent"], "pos": item["pos"]}
            for name, item in locals_.items()]}
        try:
            frame = detect_rig_frame(rig_for_frame)
        except ValueError as exc:
            report["error"] = str(exc)
            return _finish(report, report_path, 2)
        report["frame"] = frame

    mapped = {}
    for name, item in locals_.items():
        try:
            pos_cm = tuple(float(v) for v in seanim_pos_cm(frame, item["pos"]))
            rot = tuple(float(v) for v in seanim_rot(frame, item["quat"]))
        except ValueError as exc:
            report["error"] = str(exc)
            return _finish(report, report_path, 2)
        for label, values in (("local_position_cm", pos_cm),
                              ("local_rotation", rot),
                              ("local_position", item["pos"]),
                              ("local_quaternion", item["quat"])):
            for index, value in enumerate(values):
                if not math.isfinite(value):
                    non_finite.append(
                        {"bone": name, "field": "%s[%d]" % (label, index)})
        mapped[name] = {"pos_cm": pos_cm, "rot": rot}
    if non_finite:
        report["non_finite"] = non_finite
        print("bind_pose_check: non-finite result: %s" % non_finite,
              file=sys.stderr)
        return _finish(report, report_path, 1)
    return _compare(report, report_path, semodel, rig, locals_, mapped,
                    frame, tol_deg, tol_mm)


def _compare(report, report_path, semodel, rig, locals_, mapped, frame,
             tol_deg, tol_mm):
    rows = []
    for name, rec in semodel.items():
        if rec["parent"] is None:
            report["not_compared"].append([name, "game root"])
            continue
        if name not in rig:
            report["absent_in_armature"].append(name)
            continue
        here = locals_[name]["parent"]
        if here != rec["parent"]:
            if rec["parent"] not in rig and here is None:
                report["not_compared"].append(
                    [name, "game parent %s absent, root here" % rec["parent"]])
                continue
            report["parent_mismatch"].append([name, here, rec["parent"]])
            continue
        deg = _angle_deg(mapped[name]["rot"], rec["local_rotation"])
        mm = 10.0 * math.dist(mapped[name]["pos_cm"], rec["local_position"])
        for field, value in (("angle_deg", deg), ("distance_mm", mm)):
            if not math.isfinite(value):
                report["non_finite"].append({"bone": name, "field": field})
        rows.append((name, deg, mm))
        if deg > tol_deg or mm > tol_mm:
            report["over"].append({"bone": name, "deg": round(deg, 4),
                                   "mm": round(mm, 4)})
    report["over"].sort(key=lambda e: (-e["deg"], -e["mm"]))
    report["absent_in_armature"] = sorted(report["absent_in_armature"])
    report["compared"] = len(rows)
    report["max_deg"] = round(max(r[1] for r in rows), 4) if rows else None
    report["max_mm"] = round(max(r[2] for r in rows), 4) if rows else None
    if report["non_finite"]:
        return _finish(report, report_path, 1)

    if frame == "jd":
        report["roots_compared"] = True
        for name in ROOT_NAMES:
            if name not in rig:
                report["roots_missing"].append(name)
                continue
            matrix = rig[name]["matrix_local"]
            head = tuple(matrix[r][3] for r in range(3))
            jd = JD_ROOTS[name]
            deg = _angle_deg(_quat_from_matrix(matrix),
                             _quat_from_matrix(jd["matrix_local"]))
            mm = 1000.0 * math.dist(head, jd["head"])
            for field, value in (("root_angle_deg", deg),
                                 ("root_distance_mm", mm)):
                if not math.isfinite(value):
                    report["non_finite"].append({"bone": name, "field": field})
            if deg > tol_deg or mm > tol_mm:
                report["roots_over"].append(
                    {"bone": name, "deg": round(deg, 4), "mm": round(mm, 4)})
    else:
        report["roots_compared"] = False
        print("bind_pose_check: roots not compared (frame %s)" % frame)
    if report["non_finite"]:
        return _finish(report, report_path, 1)
    failed = bool(report["over"] or report["parent_mismatch"]
                  or report["roots_over"])
    print("bind_pose_check: compared %d, max %s deg / %s mm, over %d, "
          "parent mismatches %d, roots over %d"
          % (report["compared"], report["max_deg"], report["max_mm"],
             len(report["over"]), len(report["parent_mismatch"]),
             len(report["roots_over"])))
    return _finish(report, report_path, 1 if failed else 0)


def _blender_main(argv):
    parser = argparse.ArgumentParser(prog="bind_pose_check.py")
    parser.add_argument("--semodel", required=True)
    parser.add_argument("--armature", default="_DayZ_Character")
    parser.add_argument("--tol-deg", type=float, default=0.05)
    parser.add_argument("--tol-mm", type=float, default=0.01)
    parser.add_argument("--report", default=None)
    args = parser.parse_args(argv)
    report_path = args.report
    try:
        import bpy
        blend_path = bpy.data.filepath or None
        obj = bpy.data.objects.get(args.armature)
        if obj is None or obj.type != "ARMATURE":
            report = _new_report(None, args.armature, args.tol_deg, args.tol_mm)
            kind = _report_input_kind(report_path, args.semodel, blend_path)
            if kind is not None:
                print("--report %s is the %s input; refusing to overwrite it"
                      % (report_path, kind), file=sys.stderr)
                return 2
            report["error"] = "armature %s not found" % args.armature
            return _finish(report, report_path, 2)
        bones = {}
        for bone in obj.data.bones:
            bones[bone.name] = {
                "parent": bone.parent.name if bone.parent else None,
                "matrix_local": [[float(bone.matrix_local[r][c])
                                  for c in range(4)] for r in range(4)],
            }
        return run_check(args.semodel, bones, blend_path,
                         report_path=report_path, tol_deg=args.tol_deg,
                         tol_mm=args.tol_mm, frame=None,
                         armature=args.armature)
    except Exception as exc:  # the tool itself crashed: exit 3
        import traceback
        traceback.print_exc()
        kind = _report_input_kind(report_path, args.semodel, None)
        if report_path and kind is None:
            try:
                report = _new_report(None, args.armature, args.tol_deg,
                                     args.tol_mm)
                report["error"] = "%s: %s" % (type(exc).__name__, exc)
                _finish(report, report_path, 3)
            except Exception:
                pass
        return 3


if __name__ == "__main__":
    _argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    _code = _blender_main(_argv)
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(_code)
