import sys, struct, os, math
sys.path.insert(0, r"C:\Users\<you>\odol-backend\scripts")  # external ODOL->MLOD backend (odol_reader.py + siblings)
from bis_reader import BisReader
from odol_reader import LOD, ODOL_ModelInfo, AnimationClass

def open_odol(path):
    reader = BisReader.from_file(path)
    idx = reader.data.find(b"ODOL")
    reader.position = idx
    assert reader.read_ascii(4)=="ODOL"
    ver = reader.read_uint32()
    reader.version = ver
    if ver >= 44: reader.use_lzo = True
    if ver >= 64: reader.use_compression_flag = True
    if ver >= 59: reader.read_uint32()
    if ver >= 58: reader.read_asciiz()
    n = reader.read_int32()
    ress = [reader.read_float() for _ in range(n)]
    mi = ODOL_ModelInfo.read(reader, n)
    saved = reader.position
    file_size = len(reader.data)
    return reader, ver, n, ress, mi, saved, file_size

def find_table(reader, n, saved, file_size):
    def try_lod(pos):
        if pos + n*9 > file_size:
            return None
        ls = [struct.unpack_from("<I", reader.data, pos+i*4)[0] for i in range(n)]
        le = [struct.unpack_from("<I", reader.data, pos+n*4+i*4)[0] for i in range(n)]
        pm = [reader.data[pos+n*8+i] for i in range(n)]
        if any(s==0 or s>=file_size or e>file_size or e<s for s,e in zip(ls,le)):
            return None
        if any(p not in (0,1) for p in pm):
            return None
        return ls, le, pm
    best=None
    for off in range(saved, min(file_size-n*9, saved+200000)):
        got=try_lod(off)
        if not got: continue
        ls,le,pm=got
        # prefer chain-like (each end is next start when sorted) and max_end near filesize
        score = 0
        if max(le) >= file_size-8: score += 100
        # chained decreasing (common in this file)
        if all(le[i]==ls[i-1] for i in range(1,n)): score += 50
        if all(ls[i] > ls[i+1] for i in range(n-1)): score += 20
        if all(ls[i] < ls[i+1] for i in range(n-1)): score += 20
        sizes=[le[i]-ls[i] for i in range(n)]
        if max(sizes) > 100000: score += 10
        if best is None or score > best[0]:
            best=(score, off, ls, le, pm)
    return best

def ns_by_name(lod, name):
    for ns in lod.named_selections:
        if ns.name.lower()==name.lower():
            return ns
    return None

def cover_map(lod):
    cover={}
    for si,sec in enumerate(lod.sections):
        for fi in sec.get_face_indices(lod.faces):
            cover.setdefault(fi, []).append(si)
    return cover

def tex_of(lod, sec):
    if 0<=sec.texture_index<len(lod.textures):
        return lod.textures[sec.texture_index]
    return f"<tex {sec.texture_index}>"

def mat_of(lod, sec):
    if sec.material_index==-1:
        return sec.mat_name
    if 0<=sec.material_index<len(lod.materials):
        return lod.materials[sec.material_index].material_name
    return f"<mat {sec.material_index}>"

def vxyz(lod, vi):
    v=lod.vertices[vi]
    return (v.x,v.y,v.z)

def uv(lod, vi):
    d=lod.uv_sets[0].uv_data
    return d[vi*2], d[vi*2+1]

def dump_sel(lod, name, tag):
    ns=ns_by_name(lod, name)
    print(f"  [{tag}] {name}:", end=" ")
    if ns is None:
        print("MISSING"); return
    print(f"faces={len(ns.selected_faces)} verts={len(ns.selected_vertices)} sectional={ns.is_sectional} sections={list(ns.sections)}")
    cover=cover_map(lod)
    fis=list(ns.selected_faces)
    vis=list(ns.selected_vertices)
    print(f"    selected_faces={fis}")
    print(f"    selected_verts n={len(vis)} {vis[:24]}")
    sec_hits=set()
    for fi in fis:
        sec_hits.update(cover.get(fi, []))
    print(f"    faces_in_sections {sorted(sec_hits)}")
    for si in sorted(set(list(ns.sections)+list(sec_hits))):
        if si<0 or si>=len(lod.sections):
            print("    bad sec", si); continue
        sec=lod.sections[si]
        fis2=sec.get_face_indices(lod.faces)
        print(f"    sec[{si}] lower={sec.face_lower} upper={sec.face_upper} nfaces={len(fis2)} min_bone={sec.min_bone} bones={sec.bones_count} tex_i={sec.texture_index} special=0x{sec.special:08X} mat_i={sec.material_index} aot={sec.area_over_tex}")
        print(f"           tex={tex_of(lod,sec)!r}")
        print(f"           mat={mat_of(lod,sec)!r}")
    bbmin=(lod.b_min.x,lod.b_min.y,lod.b_min.z)
    bbmax=(lod.b_max.x,lod.b_max.y,lod.b_max.z)
    us=[]; vs=[]
    inside=0; outside=0
    for vi in vis:
        p=vxyz(lod,vi)
        u,v=uv(lod,vi)
        us.append(u); vs.append(v)
        inb = bbmin[0]<=p[0]<=bbmax[0] and bbmin[1]<=p[1]<=bbmax[1] and bbmin[2]<=p[2]<=bbmax[2]
        inside += int(inb); outside += int(not inb)
        br = lod.vertex_bone_ref[vi] if vi < len(lod.vertex_bone_ref) else None
        print(f"    v[{vi}] xyz=({p[0]:.6f},{p[1]:.6f},{p[2]:.6f}) uv=({u:.6f},{v:.6f}) in_bbox={inb} bone={None if br is None else br.pairs}")
    if us:
        print(f"    UV U[{min(us):.6f},{max(us):.6f}] span={max(us)-min(us):.6f} V[{min(vs):.6f},{max(vs):.6f}] span={max(vs)-min(vs):.6f}")
    print(f"    verts_in_bbox {inside} out {outside}")
    for fi in fis:
        face=lod.faces[fi]
        idxs=face.vertex_indices
        print(f"    face[{fi}] n={len(idxs)} idx={idxs}")
        if len(idxs)>=3:
            o=vxyz(lod,idxs[0]); area=0
            for k in range(1,len(idxs)-1):
                b=vxyz(lod,idxs[k]); c=vxyz(lod,idxs[k+1])
                ux,uy,uz=b[0]-o[0],b[1]-o[1],b[2]-o[2]
                vx,vy,vz=c[0]-o[0],c[1]-o[1],c[2]-o[2]
                cx,cy,cz=uy*vz-uz*vy, uz*vx-ux*vz, ux*vy-uy*vx
                area += 0.5*math.sqrt(cx*cx+cy*cy+cz*cz)
            print(f"      area_mm2={area*1e6:.4f}")

PATHS = {
    "NEW": r"C:\Users\<you>\AppData\Local\Temp\claude\pbo_check8\SUB_BRZ\sub_brz.p3d",
}

reader, ver, n, ress, mi, saved, file_size = open_odol(PATHS["NEW"])
print("ver", ver, "n", n, "res", ress, "saved", saved)
print("skeleton", mi.skeleton)
if mi.skeleton:
    for i,(nm,par) in enumerate(mi.skeleton.bones):
        if "gps" in nm.lower() or nm.startswith("nav_w00"):
            print(f"  bone[{i}] {nm!r} parent={par!r}")

best = find_table(reader, n, saved, file_size)
print("best table score", best[0], "off", best[1])
score, off, ls, le, pm = best

# parse lod 0 and 1100
for want in (0.0, 1100.0):
    i = ress.index(want)
    reader.position = ls[i]
    lod = LOD.read(reader, want)
    print(f"\n======== ODOL {want} verts={len(lod.vertices)} faces={len(lod.faces)} secs={len(lod.sections)} ns={len(lod.named_selections)}")
    print(f"  bbox {lod.b_min}->{lod.b_max} r={lod.b_radius}")
    print(f"  or_hints=0x{lod.or_hints:08X} and_hints=0x{lod.and_hints:08X} special=0x{lod.special:08X}")
    u0=lod.uv_sets[0]
    print(f"  uv0 disc={u0.is_discretized} U[{u0.min_u:.6f},{u0.max_u:.6f}] V[{u0.min_v:.6f},{u0.max_v:.6f}] n={u0.n_vertices} fill={u0.default_fill}")
    print("  relevant textures:")
    for ti,t in enumerate(lod.textures):
        tl=t.lower()
        if any(s in tl for s in ("gps","marker","cluster","screen","argb","color","dashboard","cab_screen")):
            print(f"    tex[{ti}] {t!r}")
    print("  relevant materials:")
    for mi2,m in enumerate(lod.materials):
        nl=m.material_name.lower()
        if any(s in nl for s in ("gps","marker","cluster","dashboard","screen")):
            print(f"    mat[{mi2}] {m.material_name!r} em={m.emissive} dif={m.diffuse}")
    uncovered=0
    cover=cover_map(lod)
    uncovered=[fi for fi in range(len(lod.faces)) if fi not in cover]
    print(f"  uncovered_faces {len(uncovered)}")
    for name in ("gps_marker_arrow","gps_marker","screen_nav","light_dashboard","light_dashboard_static","nav_w00"):
        dump_sel(lod, name, "CUR")
    print("  -- field compare --")
    for name in ("gps_marker_arrow","screen_nav","nav_w00","light_dashboard"):
        ns=ns_by_name(lod,name)
        if not ns: 
            print("  ", name, "MISSING"); continue
        for si in ns.sections:
            sec=lod.sections[si]
            print(f"  {name} sec[{si}] lower={sec.face_lower} upper={sec.face_upper} min_bone={sec.min_bone} bones={sec.bones_count} tex_i={sec.texture_index} special=0x{sec.special:08X} mat_i={sec.material_index} aot={sec.area_over_tex}")
    print("  proxies", len(lod.proxies))
    for pr in lod.proxies:
        print(f"    proxy {pr.model!r} bone={pr.bone_index} sec={pr.section_index} nsel={pr.named_selection_index}")
