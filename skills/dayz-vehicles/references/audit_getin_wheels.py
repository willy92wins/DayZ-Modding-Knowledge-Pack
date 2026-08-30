#!/usr/bin/env python3
# Offline audit: get-in geometry (memory points + seat selections) and wheel-axis
# handedness (mirrored vs uniform -> predicts reversed wheel spin) for the two cars
# vs the LFQuad reference that works in-game.
import sys, os, math, py3d

def lodname(res):
    for v, n in {1e13:'Geo',1e15:'Mem',2e15:'Land',5e15:'Hit',6e15:'View',7e15:'Fire'}.items():
        if v and abs(res-v)/v < 0.03:
            return n
    if res < 1e3:
        return f'Vis{int(round(res))}'
    return f'{res:.3g}'

def sel_points(lod, name):
    sel = lod.selections.get(name)
    if not sel:
        return None
    pts = [p.coords for p in sel.points]
    if not pts:
        seen = {}
        for f in sel.faces:
            for v in f.vertices:
                seen[v.point_index] = lod.points[v.point_index].coords
        pts = list(seen.values())
    return pts

def centroid(pts):
    n = len(pts)
    return [sum(p[k] for p in pts)/n for k in range(3)]

def axis_dir(pts):
    # axis memory point = 2 points; dir = normalize(p1-p0)
    if len(pts) < 2:
        return None
    a, b = pts[0], pts[1]
    d = [b[k]-a[k] for k in range(3)]
    L = math.sqrt(sum(x*x for x in d)) or 1.0
    return [round(d[k]/L, 3) for k in range(3)]

GETIN_MEM = ['crewdriver','crewcodriver','pos_driver','pos_driver_dir',
             'pos_codriver','pos_codriver_dir','seat_con_1_1','seat_con_2_1']
SEAT_SEL  = ['seat_driver','seat_codriver','seatback_driver','seatback_codriver']
WHEEL_AX  = ['wheel_1_1_axis','wheel_2_1_axis','wheel_1_2_axis','wheel_2_2_axis']

if not sys.argv[1:]:
    print("USAGE: audit_getin_wheels.py MODEL.p3d [MODEL.p3d ...]", file=sys.stderr)
    sys.exit(2)

# Parse every input before auditing. An unreadable input is not a model defect.
_PARSED = {}
for _path in sys.argv[1:]:
    if not os.path.isfile(_path):
        print(f"INPUT_ERROR: missing file: {_path}", file=sys.stderr)
        sys.exit(2)
    try:
        with open(_path, 'rb') as _fh:
            _PARSED[_path] = py3d.P3D(_fh)
    except Exception as _exc:
        print(f"INPUT_ERROR: cannot parse {_path}: {type(_exc).__name__}: {_exc}", file=sys.stderr)
        sys.exit(2)


for path in sys.argv[1:]:
    if not os.path.exists(path):
        print(f"MISSING: {path}"); continue
    with open(path,'rb') as fh:
        m = py3d.P3D(fh)
    print("="*88)
    print(os.path.basename(path), "| LODs:", ", ".join(lodname(l.resolution) for l in m.lods))

    # Memory LOD: get-in anchors + wheel axes
    mem = next((l for l in m.lods if abs(l.resolution-1e15)/1e15 < 0.03), None)
    if mem:
        print("  -- Memory LOD get-in anchors --")
        for nm in GETIN_MEM:
            pts = sel_points(mem, nm)
            if pts is None:
                print(f"     {nm:18s} ABSENT")
            else:
                c = centroid(pts)
                print(f"     {nm:18s} OK  n={len(pts)} centroid=({c[0]:.2f},{c[1]:.2f},{c[2]:.2f})")
        print("  -- wheel axis handedness (X sign: mirrored if L/R differ) --")
        for nm in WHEEL_AX:
            pts = sel_points(mem, nm)
            if pts is None:
                print(f"     {nm:18s} ABSENT")
            else:
                print(f"     {nm:18s} dir={axis_dir(pts)} (n={len(pts)})")
    else:
        print("  NO Memory LOD")

    # View/Fire: seat selections present?
    for l in m.lods:
        lab = lodname(l.resolution)
        if lab not in ('View','Fire','Geo'):
            continue
        present = [s for s in SEAT_SEL if s in l.selections]
        print(f"  -- {lab} seat selections present: {present}")

# SP-294 (added 2026-08-31): make this audit falsifiable and distinguish bad input.
# Three-state contract: 0=all required evidence present, 1=model defect,
# 2=input missing/unreadable (handled by the preflight above).
_audit_failures = []
for _path, _model in _PARSED.items():
    _mem = next((l for l in _model.lods if abs(l.resolution-1e15)/1e15 < 0.03), None)
    if _mem is None:
        _audit_failures.append(f"{_path}: missing Memory LOD")
        continue
    for _name in GETIN_MEM:
        _points = sel_points(_mem, _name)
        if not _points:
            _audit_failures.append(f"{_path}: Memory selection {_name} missing or empty")
    for _name in WHEEL_AX:
        _points = sel_points(_mem, _name)
        if not _points or len(_points) < 2:
            _audit_failures.append(f"{_path}: wheel axis {_name} needs at least two points")
    _seat_lods = [l for l in _model.lods if lodname(l.resolution) in ('View', 'Geo')]
    if not _seat_lods:
        _audit_failures.append(f"{_path}: no ViewGeometry or Geometry LOD for seat selections")
    else:
        for _name in SEAT_SEL:
            if not any(_name in _lod.selections for _lod in _seat_lods):
                _audit_failures.append(f"{_path}: seat selection {_name} absent from View/Geometry")

for _failure in _audit_failures:
    print(f"FAIL: {_failure}", file=sys.stderr)
sys.exit(1 if _audit_failures else 0)
