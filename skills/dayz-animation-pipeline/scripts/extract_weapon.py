import json, math, os, sys
import py3d
W=r"<dayz-projects>\A6_AnimRTTest\data\sr2m_body_raised.p3d"
SCR=r"C:\Users\<you>\AppData\Local\Temp\claude\C--Users-guill-OneDrive-Documentos-DayZ-Projects\38e5dcec-fbce-4f5a-bb24-b65ca2e8ee83\scratchpad"
def read(p):
    with open(p,'rb') as f: return py3d.P3D(f)
m=read(W)
MEMLO,MEMHI=9e14,2e15
def lod0_geo(model):
    lod=min((l for l in model.lods if l.points and l.resolution<1e4), key=lambda x:x.resolution)
    pos=[[round(c,5) for c in p.coords] for p in lod.points]
    sels=lod.selections
    items=sels.items() if isinstance(sels,dict) else [(s.name,s) for s in sels]
    proxy=set()
    for name,s in items:
        if name.startswith("proxy:") or "\\" in name:
            proxy.update(id(fc) for fc in s.faces.keys())
    faces=[]
    for face in lod.faces:
        if id(face) in proxy: continue
        vi=[v.point_index for v in face.vertices]
        if len(vi)==3: faces.append(vi)
        elif len(vi)==4: faces+=[[vi[0],vi[1],vi[2]],[vi[0],vi[2],vi[3]]]
        else:
            for k in range(1,len(vi)-1): faces.append([vi[0],vi[k],vi[k+1]])
    return pos,faces
def memory_points(model):
    out={}
    for lod in model.lods:
        if MEMLO<lod.resolution<MEMHI:
            sels=lod.selections
            items=sels.items() if isinstance(sels,dict) else [(s.name,s) for s in sels]
            for name,s in items:
                out[name]=[[round(c,5) for c in k.coords] for k in s.points.keys()]
    return out
pos,faces=lod0_geo(m)
mp={k:v for k,v in memory_points(m).items() if not (k.startswith("proxy:") or "\\" in k)}
xs=[p[0] for p in pos]; ys=[p[1] for p in pos]; zs=[p[2] for p in pos]
data={"name":os.path.basename(W),"verts":pos,"faces":faces,"mp":mp,
      "bbox":{"min":[min(xs),min(ys),min(zs)],"max":[max(xs),max(ys),max(zs)]}}
json.dump(data,open(os.path.join(SCR,'weapon.json'),'w'))
print("weapon verts",len(pos),"faces",len(faces),"mp",len(mp))
print("bbox min",[round(min(xs),3),round(min(ys),3),round(min(zs),3)],"max",[round(max(xs),3),round(max(ys),3),round(max(zs),3)])
print("memory points:", sorted(mp.keys())[:30])
