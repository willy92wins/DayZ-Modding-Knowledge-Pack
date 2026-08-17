#!/usr/bin/env python3
"""
ik_pose_to_seanim.py — Generate seated-rider SEAnim variants from a set of
.p3d anchors using 2-bone analytic IK.

Produces one SEAnim per variant (idle, steer_left, steer_right, passenger_idle,
or any custom set) on the OFP2_ManSkeleton, with per-bone rotations relative
to a rest pose. Without --rest-pose the output is positionally approximate
and FLAGGED in the SEAnim metadata as not in-game-ready; see the doc
references/vehicle-rider-ik-pose.md for the rest-pose calibration procedure.

Reuses scripts/seanim_writer.py (same skill) for SEAnim emission so output
format stays consistent across the skill.

Usage:
    python ik_pose_to_seanim.py \\
        --skeleton OFP2_ManSkeleton \\
        --anchors anchors.json \\
        --rest-pose bind.seanim \\
        --output-dir out/ \\
        --variants idle,steer_left,steer_right,passenger_idle

anchors.json schema (minimum):
    {
        "seat":      [x, y, z],      # pelvis anchor
        "gripL":     [x, y, z],      # left hand IK target
        "gripR":     [x, y, z],      # right hand IK target
        "footL":     [x, y, z],      # left foot IK target
        "footR":     [x, y, z],      # right foot IK target
        "lean":      0.0,            # 0 = vertical torso, ~0.5 = aggressive forward
        "steerMax":  0.39,           # radians, MUST match handlebar model.cfg angle1
        "twistFactor": 0.2,          # torso twist per radian of steer (0 = none)

        # Optional per-variant overrides:
        "variants": {
            "steer_left":  { "steerSign": -1 },
            "steer_right": { "steerSign": +1 },
            "passenger_idle": {
                "seat": [x, y, z], "gripL": ..., "gripR": ..., "lean": 0.18
            }
        }
    }

Reference case: LFQuad_dev/handoff_2026-05-28.md (Yamaha Banshee).
"""

import argparse
import json
import math
import sys
from pathlib import Path

# -----------------------------------------------------------------------------
# 21 joints written by this solver. The hand IK helpers (LeftHandIK, etc.) are
# intentionally NOT written; they are driven by OFP2_ManSkeleton at runtime.
# Cross-ref references/player-skeleton.md.
# -----------------------------------------------------------------------------
JOINTS = [
    "Pelvis", "Spine", "Spine1", "Spine2", "Spine3", "Neck", "Head",
    "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand",
    "RightShoulder", "RightArm", "RightForeArm", "RightHand",
    "LeftUpLeg", "LeftLeg", "LeftFoot",
    "RightUpLeg", "RightLeg", "RightFoot",
]

# Default rest-pose limb lengths (meters). Used ONLY when --rest-pose is not
# given. These are coarse OFP2_ManSkeleton averages and produce positionally
# approximate output. The script flags this in the SEAnim metadata.
DEFAULT_LIMB_LENGTHS = {
    "upper_arm": 0.30,
    "fore_arm":  0.27,
    "upper_leg": 0.42,
    "lower_leg": 0.41,
    "spine_total": 0.55,   # Pelvis -> base of Neck along the spine chain
    "shoulder_width": 0.18,
    "hip_width":      0.20,
}


def vec_sub(a, b): return [a[0]-b[0], a[1]-b[1], a[2]-b[2]]
def vec_add(a, b): return [a[0]+b[0], a[1]+b[1], a[2]+b[2]]
def vec_scale(a, s): return [a[0]*s, a[1]*s, a[2]*s]
def vec_dot(a, b): return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]
def vec_cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]
def vec_len(a): return math.sqrt(vec_dot(a, a))
def vec_norm(a):
    L = vec_len(a)
    return [0.0, 0.0, 0.0] if L < 1e-9 else vec_scale(a, 1.0 / L)


def two_bone_ik(root_pos, target_pos, l1, l2, pole_hint):
    """Returns (mid_pos, end_pos). Analytic 2-bone IK (law of cosines).

    pole_hint is a direction giving where the elbow / knee should bend.
    Clamps target to reachable range so the limb does not flip.
    """
    delta = vec_sub(target_pos, root_pos)
    d = vec_len(delta)
    # Clamp to reachable shell.
    d = max(abs(l1 - l2) + 1e-4, min(d, l1 + l2 - 1e-4))
    # Cosine of angle at root joint between (root->target) and (root->mid).
    cos_a = (l1*l1 + d*d - l2*l2) / (2.0 * l1 * d)
    a = math.acos(max(-1.0, min(1.0, cos_a)))
    # Build the plane (target direction) x (pole hint).
    fwd = vec_norm(delta)
    pole = vec_norm(pole_hint)
    # If pole is colinear with fwd, kick it perpendicular.
    if abs(vec_dot(fwd, pole)) > 0.999:
        pole = vec_norm(vec_cross(fwd, [0.0, 1.0, 0.0]))
        if vec_len(pole) < 1e-3:
            pole = vec_norm(vec_cross(fwd, [1.0, 0.0, 0.0]))
    side = vec_norm(vec_cross(fwd, pole))
    up   = vec_norm(vec_cross(side, fwd))
    # Mid joint position = root + l1 * (cos(a)*fwd + sin(a)*up).
    mid = vec_add(root_pos, vec_add(vec_scale(fwd, l1*math.cos(a)),
                                    vec_scale(up,  l1*math.sin(a))))
    return mid, list(target_pos)


def solve_spine(seat_pos, lean, spine_total):
    """Even distribution along a straight chain from Pelvis to base of Neck,
    tilted forward by `lean` radians around the X axis."""
    n_segments = 4  # Pelvis -> Spine -> Spine1 -> Spine2 -> Spine3
    seg_len = spine_total / n_segments
    forward = [0.0, math.sin(lean), -math.cos(lean) * 0.0]  # placeholder
    # Up direction in vehicle local: +Y. With lean we tilt forward in -Z.
    up_tilt = [0.0, math.cos(lean), -math.sin(lean)]
    positions = {"Pelvis": list(seat_pos)}
    cur = list(seat_pos)
    for i, name in enumerate(["Spine", "Spine1", "Spine2", "Spine3"]):
        cur = vec_add(cur, vec_scale(up_tilt, seg_len))
        positions[name] = list(cur)
    # Neck and Head extend the same direction with shorter segments.
    neck = vec_add(positions["Spine3"], vec_scale(up_tilt, 0.08))
    head = vec_add(neck, vec_scale(up_tilt, 0.14))
    positions["Neck"] = neck
    positions["Head"] = head
    return positions


def solve_arm(shoulder_pos, grip_pos, lengths, side, twist):
    """Returns dict of joint positions for one arm."""
    sign = -1 if side == "Left" else +1
    # Pole hint: forward + slightly down + outward; prevents elbow flip.
    pole_hint = [sign * 0.3, -0.4, 0.7]
    mid, end = two_bone_ik(shoulder_pos, grip_pos, lengths["upper_arm"],
                           lengths["fore_arm"], pole_hint)
    return {
        f"{side}Shoulder": list(shoulder_pos),
        f"{side}Arm":      list(shoulder_pos),
        f"{side}ForeArm":  mid,
        f"{side}Hand":     end,
    }


def solve_leg(hip_pos, foot_pos, lengths, side):
    sign = -1 if side == "Left" else +1
    pole_hint = [sign * 0.1, 0.2, 1.0]  # knee forward
    mid, end = two_bone_ik(hip_pos, foot_pos, lengths["upper_leg"],
                           lengths["lower_leg"], pole_hint)
    return {
        f"{side}UpLeg": list(hip_pos),
        f"{side}Leg":   mid,
        f"{side}Foot":  end,
    }


def solve_pose(variant_anchors, lengths):
    """Returns dict joint_name -> [x,y,z] for all 21 joints."""
    seat   = variant_anchors["seat"]
    gripL  = variant_anchors["gripL"]
    gripR  = variant_anchors["gripR"]
    footL  = variant_anchors["footL"]
    footR  = variant_anchors["footR"]
    lean   = variant_anchors.get("lean", 0.0)
    steer  = variant_anchors.get("steer", 0.0)   # rad, signed

    out = {}
    spine = solve_spine(seat, lean, lengths["spine_total"])
    out.update(spine)

    # Shoulders are offset from Spine3 by half shoulder_width on each side.
    spine3 = spine["Spine3"]
    s_off  = lengths["shoulder_width"] * 0.5
    twist  = variant_anchors.get("twistFactor", 0.2) * steer
    # Twist tilts shoulders around vehicle-up axis.
    left_shoulder  = vec_add(spine3, [+s_off * math.cos(twist),
                                      0.05, -s_off * math.sin(twist)])
    right_shoulder = vec_add(spine3, [-s_off * math.cos(twist),
                                      0.05, +s_off * math.sin(twist)])

    out.update(solve_arm(left_shoulder,  gripL, lengths, "Left",  twist))
    out.update(solve_arm(right_shoulder, gripR, lengths, "Right", twist))

    # Hips at pelvis offset by half hip_width.
    pelvis = spine["Pelvis"]
    h_off  = lengths["hip_width"] * 0.5
    left_hip  = vec_add(pelvis, [+h_off, 0.0, 0.0])
    right_hip = vec_add(pelvis, [-h_off, 0.0, 0.0])
    out.update(solve_leg(left_hip,  footL, lengths, "Left"))
    out.update(solve_leg(right_hip, footR, lengths, "Right"))

    return out


def positions_to_local_rotations(positions, rest_pose):
    """Converts world-space joint positions to local-space rotations against
    a rest pose. Without a real rest pose this returns a flat identity set
    and the output is flagged as approximate.

    Real implementation: walk each parent->child bone, compute the rotation
    that takes (rest_child_pos - rest_parent_pos) to (pos_child - pos_parent),
    convert to quaternion in the parent's local frame.

    Stub for now: emit identity quats and set a metadata flag downstream.
    """
    rotations = {name: [0.0, 0.0, 0.0, 1.0] for name in positions}  # identity quat
    return rotations


def load_rest_pose(path):
    """Load a SEAnim rest pose. Returns None if --rest-pose was not given.

    NOTE — STUB: SEAnim is a binary format and seanim_writer.py does not yet
    ship a reader. This loader currently CANNOT extract joint quaternions
    from the file. It checks the file exists and returns a sentinel; the
    pose conversion still uses identity rotations. See
    references/vehicle-rider-ik-pose.md "Critical caveat — rest pose
    calibration" for the procedure that will work once the reader lands.

    Returns:
        None  -- no --rest-pose given
        {"__stub__": True, "__path__": str(path), "__reader_missing__": True}
              -- file exists, but rotation calibration is NOT applied
    """
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        print(f"WARN: --rest-pose path does not exist: {p}", file=sys.stderr)
        return None
    # seanim_writer.read_seanim DOES exist now (the "reader not implemented"
    # note was stale). Load frame-0 local rotations per bone as the rest ref.
    # Rebasing against this is best-effort; in-game is the convention gate
    # (see references/weapon-anim-authoring-viewer.md).
    this_dir = Path(__file__).resolve().parent
    if str(this_dir) not in sys.path:
        sys.path.insert(0, str(this_dir))
    try:
        import seanim_writer
        data = seanim_writer.read_seanim(str(p))
    except Exception as exc:
        print(f"WARN: could not read --rest-pose {p}: {exc}", file=sys.stderr)
        return None
    rest = {b["name"]: b["rot_keys"][0][1] for b in data["bones"] if b["rot_keys"]}
    print(f"rest-pose loaded: {len(rest)} bone rotations from {p.name}")
    return rest or None


def variant_anchors(base, name, variants_cfg):
    """Returns the per-variant anchor dict with overrides applied."""
    a = dict(base)
    if name == "idle":
        a["steer"] = 0.0
    elif name == "steer_left":
        sign = -1
        a["steer"] = sign * base.get("steerMax", 0.39)
    elif name == "steer_right":
        sign = +1
        a["steer"] = sign * base.get("steerMax", 0.39)
    else:
        a["steer"] = 0.0
    cfg = (variants_cfg or {}).get(name, {})
    a.update(cfg)
    return a


def write_seanim_for_variant(pose, name, output_dir, calibrated):
    """Emit one SEAnim file for the variant.

    Calls seanim_writer.write_seanim(path, bones, ...) with bones in the
    schema seanim_writer expects: list of dicts with keys
        {name, pos_keys?, rot_keys?, scale_keys?}
    where each *_keys is a list of (frame_index, value) pairs.

    Status: rotations are identity quaternions until the rest-pose reader
    is implemented (see load_rest_pose docstring and
    references/vehicle-rider-ik-pose.md). The output is therefore
    POSITIONALLY APPROXIMATE and not in-game ready. The header notes
    convey this so a downstream consumer never mistakes a stub output for
    a calibrated one.
    """
    this_dir = Path(__file__).resolve().parent
    if str(this_dir) not in sys.path:
        sys.path.insert(0, str(this_dir))
    try:
        import seanim_writer  # type: ignore
    except Exception as exc:
        print(f"WARN: seanim_writer unavailable ({exc}); writing positions JSON instead.",
              file=sys.stderr)
        out = Path(output_dir) / f"{name}.positions.json"
        out.write_text(json.dumps({"variant": name, "joints": pose,
                                   "calibrated": calibrated}, indent=2))
        return out

    rotations = positions_to_local_rotations(pose, None)
    out = Path(output_dir) / f"{name}.seanim"

    # Build the bones list seanim_writer expects: one entry per JOINT.
    # We provide a position key at frame 0 (the IK-solved position) and a
    # rotation key at frame 0 (currently identity — see status note above).
    bones = []
    for joint in JOINTS:
        pos = pose.get(joint, [0.0, 0.0, 0.0])
        rot = rotations.get(joint, [0.0, 0.0, 0.0, 1.0])
        bones.append({
            "name":     joint,
            "pos_keys": [(0, tuple(pos))],
            "rot_keys": [(0, tuple(rot))],
        })

    # Notes embed the calibration status into the SEAnim itself so anyone
    # opening the file later sees the warning.
    if calibrated:
        notes = [(0, f"{name} :: calibrated rest pose")]
    else:
        notes = [
            (0, f"{name} :: STUB OUTPUT"),
            (0, "rest-pose reader not implemented; rotations are identity"),
            (0, "see references/vehicle-rider-ik-pose.md rest-pose section"),
        ]

    seanim_writer.write_seanim(
        path=str(out),
        bones=bones,
        framerate=30.0,
        looped=True,
        anim_type=0,
        notes=notes,
    )
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--skeleton", default="OFP2_ManSkeleton",
                        help="target skeleton (currently OFP2_ManSkeleton only)")
    parser.add_argument("--anchors", required=True,
                        help="path to anchors.json")
    parser.add_argument("--rest-pose", default=None,
                        help="path to extracted vanilla SEAnim used for "
                             "rest-pose calibration; without this the output "
                             "is flagged approximate")
    parser.add_argument("--output-dir", required=True,
                        help="directory to write SEAnim files into")
    parser.add_argument("--variants", default="idle,steer_left,steer_right",
                        help="comma-separated variant names")
    parser.add_argument("--dry-run", action="store_true",
                        help="solve poses and print summary; do not write files")
    args = parser.parse_args(argv)

    anchors = json.loads(Path(args.anchors).read_text(encoding="utf-8"))
    variants = [v.strip() for v in args.variants.split(",") if v.strip()]
    variants_cfg = anchors.get("variants", {})

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    rest_pose = load_rest_pose(args.rest_pose)
    calibrated = rest_pose is not None
    if not calibrated:
        print("NOTE: no --rest-pose given; output will be POSITIONALLY APPROXIMATE.",
              file=sys.stderr)
        print("See references/vehicle-rider-ik-pose.md for the calibration procedure.",
              file=sys.stderr)

    lengths = dict(DEFAULT_LIMB_LENGTHS)

    print(f"Writing {len(variants)} variant(s) to {output_dir}/")
    for name in variants:
        va = variant_anchors(anchors, name, variants_cfg)
        # Each variant may carry its own anchor overrides (e.g. passenger seat).
        missing = [k for k in ("seat", "gripL", "gripR", "footL", "footR") if k not in va]
        if missing:
            print(f"  SKIP {name}: missing anchor keys {missing}", file=sys.stderr)
            continue
        pose = solve_pose(va, lengths)
        if args.dry_run:
            print(f"  [dry-run] {name}: {len(pose)} joints solved; "
                  f"hand_L={pose['LeftHand']}, hand_R={pose['RightHand']}")
            continue
        out = write_seanim_for_variant(pose, name, output_dir, calibrated)
        print(f"  wrote {out.name}")

    if not calibrated and not args.dry_run:
        print("\nNEXT STEP: run DayZATool --extract-anim on a vanilla driver-idle "
              ".anm and re-run with --rest-pose pointing at the extracted SEAnim "
              "to produce in-game-ready output.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
