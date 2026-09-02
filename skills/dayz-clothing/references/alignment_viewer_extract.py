import sys, json, os
sys.path.insert(0, r"<tmp>\armorhneck_research_ws\tools")
import py3d
assert getattr(py3d, "IS_DAYZ_FORK", False) and tuple(map(int, py3d.__version__.split("."))) >= (1, 6, 0), (py3d.__version__, py3d.__file__)
from odol_reader import ODOL

OUT = r"<tmp>\armorhneck_viewer"

SIMPLE_REGIONS = ["leftarm", "rightarm", "leftforearm", "rightforearm", "leftupleg", "rightupleg"]
COMBO_REGIONS = {"abdomen": ["pelvis", "spine"]}
ALL_REGIONS = SIMPLE_REGIONS + list(COMBO_REGIONS.keys())

with open(r"<dayz-projects>\ArmorHneck\data\armorhneck_m.p3d", "rb") as f:
    p = py3d.P3D(f)
lod = p.lods[1]
pts = [pt.coords for pt in lod.points]
pt_index = {id(pt): i for i, pt in enumerate(lod.points)}

positions = []
for c in pts:
    positions.extend([round(c[0], 5), round(c[1], 5), round(c[2], 5)])

indices = []
for face in lod.faces:
    vs = [v.point_index for v in face.vertices]
    for k in range(1, len(vs) - 1):
        indices.extend([vs[0], vs[k], vs[k+1]])

def sel_weights(name):
    out = [0.0]*len(pts)
    for nm, s in lod.selections.items():
        if nm.lower() == name:
            for pt, w in s.points.items():
                out[pt_index[id(pt)]] = round(float(w or 0), 3)
            break
    return out

region_w = []
for rname in SIMPLE_REGIONS:
    region_w.append(sel_weights(rname))
for combo, parts in COMBO_REGIONS.items():
    acc = [0.0]*len(pts)
    for part in parts:
        pw = sel_weights(part)
        for i in range(len(pts)):
            acc[i] = min(1.0, acc[i] + pw[i])
    region_w.append([round(v, 3) for v in acc])

pivots = {}
for ri, rname in enumerate(ALL_REGIONS):
    idxs = [i for i, w in enumerate(region_w[ri]) if w > 0]
    if not idxs:
        continue
    ys = sorted(pts[i][1] for i in idxs)
    y_hi = ys[int(len(ys)*0.85)]
    top = [i for i in idxs if pts[i][1] >= y_hi]
    if rname == "abdomen":
        top = idxs
    n = len(top)
    pivots[rname] = [round(sum(pts[i][0] for i in top)/n, 4), round(sum(pts[i][1] for i in top)/n, 4), round(sum(pts[i][2] for i in top)/n, 4)]

odol = ODOL.from_file(r"<tmp>\armorhneck_research_ws\vanilla\chainmail_m.p3d")
glod = odol.lods[0]
gpos = []
for v in glod.vertices:
    gpos.extend([round(v.x, 5), round(v.y, 5), round(v.z, 5)])
gidx = []
for face in glod.faces:
    vs = list(getattr(face, "vertex_indices", []) or [])
    for k in range(1, len(vs) - 1):
        gidx.extend([vs[0], vs[k], vs[k+1]])

data = {
    "armor": {"positions": positions, "indices": indices, "regions": ALL_REGIONS, "weights": region_w, "pivots": pivots},
    "ghost": {"positions": gpos, "indices": gidx},
}
with open(os.path.join(OUT, "align_data.json"), "w") as f:
    json.dump(data, f, separators=(",", ":"))
print("v2 data: %d pts, regions=%s" % (len(pts), ALL_REGIONS))
print("pivots:", json.dumps(pivots))
