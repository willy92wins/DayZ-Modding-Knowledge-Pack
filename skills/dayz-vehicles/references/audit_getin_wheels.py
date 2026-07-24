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
