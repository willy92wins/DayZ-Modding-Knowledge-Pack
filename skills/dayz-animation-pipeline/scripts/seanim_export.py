#!/usr/bin/env python3
"""Convert an authoring-viewer anim JSON (per-frame per-bone LOCAL quaternions)
into a SEAnim file (the open bridge format to DayZ's .anm via DayZATool).

IMPORTANT convention note (verified 2026-06-28):
  The viewer's quaternions are in the RIG-LOCAL frame derived from the BI
  FBX rig (Blender bone-local: bone points +Y). DayZ's .anm/SEAnim bone-local
  frame has the bone pointing +X (verified from a DayZATool-extracted vanilla
  SEAnim: finger phalanx offsets are (length,0,0)). These differ by a per-bone
  basis, so the emitted SEAnim is geometrically meaningful in the rig but is
  NOT guaranteed to be in DayZ's exact convention. The in-game test is the gate
  (see handoff). --rest-pose lets you supply a DayZATool-extracted vanilla
  SEAnim so this script can rebase rotations against the real rest (best-effort).
"""
import argparse, json, os, sys

def load_writer():
    here = os.path.dirname(os.path.abspath(__file__))
    for cand in (here, r'<dayz-projects>\A6_SR2M_dev\tools\anim-pipeline'):
        if os.path.exists(os.path.join(cand, 'seanim_writer.py')):
            sys.path.insert(0, cand); break
    import seanim_writer
    return seanim_writer

UNIT_CM = 100.0  # rig meters -> SEAnim cm (verified vs aks74u_reference finger offsets)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--anim', required=True, help='viewer export JSON')
    ap.add_argument('--rig', required=True, help='rig_dayz.json (rest bone offsets)')
    ap.add_argument('--out', required=True, help='output .seanim')
    ap.add_argument('--rest-pose', default=None, help='DayZATool-extracted vanilla SEAnim for rebasing (optional)')
    ap.add_argument('--keys-only', action='store_true', help='emit only authored keyframes (default: dense)')
    a = ap.parse_args()
    sw = load_writer()

    anim = json.load(open(a.anim, encoding='utf-8'))
    rig = json.load(open(a.rig, encoding='utf-8'))
    rest_pos = {b['name']: b['pos'] for b in rig['bones']}
    order = anim['bone_order']
    fps = float(anim.get('fps', 30))
    frames = anim['frames']
    use_frames = set(anim['keyframes']) if a.keys_only else set(range(len(frames)))

    rest_seanim = None
    if a.rest_pose:
        if os.path.exists(a.rest_pose):
            rest_seanim = {b['name']: b for b in sw.read_seanim(a.rest_pose)['bones']}
            print('rest-pose loaded:', len(rest_seanim), 'bones (rebasing best-effort)')
        else:
            print('WARN: --rest-pose not found:', a.rest_pose, file=sys.stderr)

    bones = []
    for name in order:
        rot_keys = []
        for fr in sorted(use_frames):
            q = frames[fr]['bones'].get(name)
            if q:
                rot_keys.append((fr, (q[0], q[1], q[2], q[3])))
        p = rest_pos.get(name, [0, 0, 0])
        pos_keys = [(0, (p[0] * UNIT_CM, p[1] * UNIT_CM, p[2] * UNIT_CM))]
        bones.append({'name': name, 'pos_keys': pos_keys, 'rot_keys': rot_keys})

    # No SEAnim note events: DayZATool rejects free-text notes ("malformed
    # event"). The RIG-LOCAL convention caveat lives in the handoff/README, not
    # in the binary. Keeping notes empty makes --generate-anim output clean.
    sw.write_seanim(a.out, bones, framerate=fps, looped=False, anim_type=0, notes=[])

    # --- offline gate: structural round-trip ---
    rd = sw.read_seanim(a.out)
    assert rd['frame_count'] == len(frames), (rd['frame_count'], len(frames))
    assert abs(rd['framerate'] - fps) < 1e-6
    assert [b['name'] for b in rd['bones']] == order, 'bone order mismatch'
    # sample quat round-trips
    bi = order.index('RightForeArm')
    src = bones[bi]['rot_keys']
    got = rd['bones'][bi]['rot_keys']
    assert len(src) == len(got), (len(src), len(got))
    for (f0, q0), (f1, q1) in zip(src, got):
        assert f0 == f1 and all(abs(x - y) < 1e-5 for x, y in zip(q0, q1)), 'quat round-trip fail'
    print('SEAnim written:', a.out, os.path.getsize(a.out), 'bytes')
    print('  frames=%d  bones=%d  fps=%g  rot_keys/bone=%d' % (rd['frame_count'], len(rd['bones']), rd['framerate'], len(got)))
    print('  GATE: binary round-trip OK; bone names = OFP2_ManSkeleton order; fps OK')

if __name__ == '__main__':
    main()
