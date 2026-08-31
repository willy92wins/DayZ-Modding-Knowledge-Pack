#!/usr/bin/env python3
"""
check_dayz_winding.py - OFFLINE "model renders inside-out" detector for DayZ source MLOD .p3d.

WHY THIS EXISTS
  A Blender/Three.js preview is double-sided, so it NEVER reveals DayZ's single-sided backface
  culling. The recurring failure is shipping a model whose exterior faces are back-facing in the
  engine -> textures show on the INTERIOR, exterior is see-through. It costs an in-game cycle every
  time. This catches it offline.

GROUND TRUTH (derived from an in-game-confirmed inside-out build, LFInfectedBig S6 2026-06-25):
  A correct DayZ VISUAL LOD, in SOURCE-MLOD form (what AddonBuilder ingests), has:
    (1) per-vertex normals pointing OUTWARD, and
    (2) face winding such that cross(v1-v0, v2-v0) points OPPOSITE the outward normal
        (i.e. dot(cross, normal) < 0  ==  cross points INWARD in the source MLOD).
  The inside-out build had outward normals BUT cross.normal > 0 (cross outward) -> inside-out.
  AddonBuilder reverses winding at binarize, so "cross inward in source" => "cross outward in ODOL",
  which is what the engine renders as front-facing. (Collision LODs follow the same rule:
  dayz-model-pipeline Rule 18 wants the geometry cross INWARD too.)

  NOTE on comparing to vanilla: do NOT measure a debinarized vanilla model for this - the
  ODOL->MLOD converter's winding handling inverts the comparison. The rule above is self-contained.

USAGE
  python check_dayz_winding.py path\to\model.p3d            # source MLOD
  python check_dayz_winding.py path\to\model.p3d --py3d C:\path\to\py3d
  exit code 0 = PASS, 1 = model defect (winding/normals), 2 = invalid or not measurable
"""
import sys, os, argparse, struct, numpy as np

NORMALS_OUTWARD_MIN = 0.35

def load_py3d(extra):
    for p in ([extra] if extra else []) + [
        r"<dayz-projects>\py3d",
        os.path.join(os.path.dirname(__file__), "py3d")]:
        if p and os.path.isdir(p) and p not in sys.path:
            sys.path.insert(0, p)
    import py3d
    return py3d

def per_vertex_normal(lod):
    N=len(lod.points); acc=np.zeros((N,3))
    for f in lod.faces:
        for v in f.vertices:
            acc[v.point_index]+=np.array(lod.facenormals[v.normal_index])
    return acc

def proxy_point_ids(lod):
    bad=set()
    for name,sel in lod.selections.items():
        if str(name).startswith("proxy:"):
            for p,w in sel.points.items():
                if w>0: bad.add(id(p))
    return bad

def outward_frac(lod):
    """Winding-INDEPENDENT: at axis-extreme verts (excluding proxies/outliers), does the stored
    normal point away from the body centroid?"""
    P=np.array([p.coords for p in lod.points]); nrm=per_vertex_normal(lod)
    nlen=np.linalg.norm(nrm,axis=1)
    bad=proxy_point_ids(lod)
    keep=np.array([ (id(p) not in bad) for p in lod.points ]) & (nlen>1e-6)
    idx=np.where(keep)[0]
    if len(idx)<8: return None
    # robust core: drop farthest 2% per axis (proxy legs / spikes)
    c0=P[idx].mean(0); d=np.linalg.norm(P[idx]-c0,axis=1)
    idx=idx[d<=np.percentile(d,98)]
    c=P[idx].mean(0)
    res=[]
    for ax in range(3):
        for sgn in (+1,-1):
            vi=idx[np.argmax(P[idx,ax]*sgn)]
            n=nrm[vi]; n=n/np.linalg.norm(n)
            o=P[vi]-c; o=o/np.linalg.norm(o)
            res.append(np.dot(n,o))
    return sum(1 for d in res if d>0)/len(res)

def crossnorm_pos_frac(lod):
    pos=tot=0
    for f in lod.faces:
        if len(f.vertices)<3: continue
        p0=np.array(lod.points[f.vertices[0].point_index].coords)
        p1=np.array(lod.points[f.vertices[1].point_index].coords)
        p2=np.array(lod.points[f.vertices[2].point_index].coords)
        cr=np.cross(p1-p0,p2-p0); L=np.linalg.norm(cr)
        if L<1e-12: continue
        sn=sum(np.array(lod.facenormals[v.normal_index]) for v in f.vertices[:3]); Ls=np.linalg.norm(sn)
        if Ls<1e-9: continue
        tot+=1
        if np.dot(cr/L,sn/Ls)>0: pos+=1
    return pos/tot if tot else None

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("p3d"); ap.add_argument("--py3d", default=None)
    a=ap.parse_args()
    try:
        with open(a.p3d, "rb") as stream:
            signature = stream.read(4)
    except OSError as exc:
        print(f"invalid input: {exc}")
        sys.exit(2)
    if signature == b"ODOL":
        print("invalid input: this file is ODOL; convert it to MLOD first with an external "
              "ODOL->MLOD converter (not distributed with this pack).")
        sys.exit(2)
    py3d=load_py3d(a.py3d)
    try:
        with open(a.p3d,"rb") as stream:
            m=py3d.P3D(stream)
    except (OSError, AssertionError, EOFError, ValueError, IndexError, struct.error) as exc:
        print(f"invalid input: {exc}")
        sys.exit(2)
    vis=[l for l in m.lods if 0.0<=l.resolution<10]
    if not vis:
        print("no visual LOD"); sys.exit(2)
    ok=True
    invalid=False
    for lod in sorted(vis,key=lambda l:l.resolution):
        ofrac=outward_frac(lod); cn=crossnorm_pos_frac(lod)
        if ofrac is None or cn is None:
            invalid=True
            oinfo = f"{ofrac:.2f}" if ofrac is not None else "n/a"
            cinfo = f"{cn:.2f}" if cn is not None else "n/a"
            print(f"[ERROR] res={lod.resolution:.1f}  cross.normal_positive={cinfo}  normals_outward={oinfo}")
            print("        -> visual LOD is not measurable; no model verdict was produced.")
            continue
        # GATE = cross.normal sign (the validated inside-out discriminator; winding is binary, and the
        # cross.normal-positive state is the in-game-confirmed inside-out one). Correct => cross.normal<0.
        wind_ok = cn<=0.30
        warn_in = 0.30<cn<0.70
        normals_ok = ofrac>=NORMALS_OUTWARD_MIN
        tag="PASS" if wind_ok and normals_ok else ("WARN" if warn_in and normals_ok else "FAIL")
        if not wind_ok or not normals_ok: ok=False
        print(f"[{tag}] res={lod.resolution:.1f}  cross.normal_positive={cn:.2f}  normals_outward={ofrac:.2f}")
        if not wind_ok:
            print("       -> WINDING will render INSIDE-OUT in DayZ (textures on interior faces).")
            print("          Fix: reverse vertex order of every visual face (face.vertices.reverse()).")
        if not normals_ok:
            print(f"       -> NORMALS point INWARD globally ({ofrac:.2f} < {NORMALS_OUTWARD_MIN:.2f}).")
            print("          Fix: orient stored normals outward, then re-run this gate.")
    if invalid:
        print("DAYZ WINDING/NORMAL CONVENTION: INVALID (not measurable)")
        sys.exit(2)
    print("DAYZ WINDING/NORMAL CONVENTION:", "PASS" if ok else "FAIL (model defect) - do NOT ship")
    sys.exit(0 if ok else 1)

if __name__=="__main__":
    main()
