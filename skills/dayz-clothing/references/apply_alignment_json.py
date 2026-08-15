import sys, os, math, json, shutil, hashlib
sys.path.insert(0, r"<dayz-projects>\py3d")
import py3d

ADJUST = {
    "leftarm":      {"pivot": [0.2067, 1.5152, 0.0092],  "rot_deg": [-8.5, -5, 12],   "offset": [-0.01, -0.025, 0]},
    "rightarm":     {"pivot": [-0.2064, 1.5154, 0.0094], "rot_deg": [-8.5, 5, -12],   "offset": [0.01, -0.025, 0]},
    "leftforearm":  {"pivot": [0.3762, 1.221, 0.0122],   "rot_deg": [-14.5, -42, -7], "offset": [0.12, -0.05, 0.08]},
    "rightforearm": {"pivot": [-0.376, 1.2213, 0.0123],  "rot_deg": [-14.5, 42, 7],   "offset": [-0.12, -0.05, 0.08]},
}

# three.js r128 Matrix4.makeRotationFromEuler, order "XYZ" (column-major)
def euler_xyz_matrix(rx, ry, rz):
    x, y, z = math.radians(rx), math.radians(ry), math.radians(rz)
    a, b = math.cos(x), math.sin(x)
    c, d = math.cos(y), math.sin(y)
    e, f = math.cos(z), math.sin(z)
    ae, af, be, bf = a*e, a*f, b*e, b*f
    # rows for v' = M @ v
    return (
        (c*e,      -c*f,     d),
        (af+be*d,  ae-bf*d,  -b*c),
        (bf-ae*d,  be+af*d,  a*c),
    )

def apply_region(coords, w, adj):
    px, py, pz = adj["pivot"]
    M = euler_xyz_matrix(*adj["rot_deg"])
    ox, oy, oz = adj["offset"]
    x, y, z = coords[0]-px, coords[1]-py, coords[2]-pz
    tx = M[0][0]*x + M[0][1]*y + M[0][2]*z + px + ox
    ty = M[1][0]*x + M[1][1]*y + M[1][2]*z + py + oy
    tz = M[2][0]*x + M[2][1]*y + M[2][2]*z + pz + oz
    return (coords[0] + w*(tx-coords[0]), coords[1] + w*(ty-coords[1]), coords[2] + w*(tz-coords[2]))

# Cross-check against viewer-computed samples (weight 1 vertices)
SAMPLES = {
    "leftarm":      {"before": [0.26471, 1.47306, -0.05007],  "after": [0.26712021231651306, 1.4534785747528076, -0.039239734411239624]},
    "rightarm":     {"before": [-0.26471, 1.47306, -0.05007], "after": [-0.26717138290405273, 1.453521728515625, -0.0391882099211216]},
    "leftforearm":  {"before": [0.47052, 1.12833, -0.13453],  "after": [0.6555596590042114, 1.057312250137329, 0.06586986780166626]},
    "rightforearm": {"before": [-0.47052, 1.12833, -0.13453], "after": [-0.6555469632148743, 1.0573089122772217, 0.06608349084854126]},
}
max_err = 0.0
for r, s in SAMPLES.items():
    got = apply_region(tuple(s["before"]), 1.0, ADJUST[r])
    err = max(abs(got[i] - s["after"][i]) for i in range(3))
    max_err = max(max_err, err)
    print("%-13s expected %s got (%.6f, %.6f, %.6f)  err=%.2e" % (r, s["after"], got[0], got[1], got[2], err))
assert max_err < 1e-4, "Euler convention mismatch vs viewer: %g" % max_err
print("CROSS-CHECK PASS (max err %.2e)\n" % max_err)

SRC = r"<dayz-projects>\ArmorHneck\data"
BK = r"<dayz-projects>\ArmorHneck_dev\_backups"
REGIONS = list(ADJUST.keys())

for fname in ("armorhneck_m.p3d", "armorhneck_f.p3d"):
    src = os.path.join(SRC, fname)
    shutil.copy2(src, os.path.join(BK, fname + ".bak_pre_armfit_20260803"))
    with open(src, "rb") as f:
        p = py3d.P3D(f)
    pre_counts = [(len(l.points), len(l.faces)) for l in p.lods]

    for lod in p.lods:
        if not lod.points:
            continue
        weights = {}
        for rname in REGIONS:
            sel = None
            for nm, s in lod.selections.items():
                if nm.lower() == rname:
                    sel = s; break
            if sel:
                weights[rname] = {id(pt): (pt, float(w or 0)) for pt, w in sel.points.items() if (w or 0) > 0}
        moved = {}
        for rname, table in weights.items():
            adj = ADJUST[rname]
            for key, (pt, w) in table.items():
                cur = moved.get(key, pt.coords)
                moved[key] = apply_region(cur, w, adj)
        for rname, table in weights.items():
            for key, (pt, w) in table.items():
                if key in moved:
                    pt.coords = moved.pop(key)

    assert [(len(l.points), len(l.faces)) for l in p.lods] == pre_counts
    p.save(src, verify=True)
    with open(src, "rb") as f:
        rb = py3d.P3D(f)
    assert [(len(l.points), len(l.faces)) for l in rb.lods] == pre_counts
    lod0 = rb.lods[0]
    sel = None
    for nm, s in lod0.selections.items():
        if nm.lower() == "leftforearm":
            sel = s; break
    pw = [(pt, w) for pt, w in sel.points.items() if (w or 0) > 0]
    cx = sum(pt.coords[0]*(w or 0) for pt, w in pw)/sum((w or 0) for _, w in pw)
    print("%s: applied, saved+verified. leftforearm centroid X now %.3f (was 0.400)" % (fname, cx))
