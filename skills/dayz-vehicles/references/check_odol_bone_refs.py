# Which skeleton bone do the marker/witness vertices bind to in the deployed
# ODOL? A vertex bound to a bone whose hide animation starts at phase 1 is
# invisible from spawn no matter what the material or section says.
import sys
import io

sys.path.insert(0, r"C:\Users\<you>\.grok\skills\dayz-p3d-debinarizer\scripts")
GATE = r"C:\Users\<you>\ForzaDayZ\work\navscreen_planb\gate_sections.py"
src = io.open(GATE, encoding="utf-8").read().split("PATHS = {")[0]
exec(compile(src, "gatehead", "exec"))
from odol_reader import LOD  # noqa: E402

ODOL = r"C:\Users\<you>\AppData\Local\Temp\claude\pbo_check13\SUB_BRZ\sub_brz.p3d"

reader, ver, n, ress, mi, saved, file_size = open_odol(ODOL)
bones = mi.skeleton.bones if mi.skeleton else []
print("skeleton bones:", len(bones))
score, off, ls, le, pm = find_table(reader, n, saved, file_size)

for want in (0.0, 1100.0):
    i = ress.index(want)
    reader.position = ls[i]
    lod = LOD.read(reader, want)
    print("\n=== LOD %.0f ===" % want)
    for si, sec in enumerate(lod.sections):
        tex = tex_of(lod, sec)
        if not ("gps_arrow" in tex or ("cluster" in tex and len(sec.get_face_indices(lod.faces)) == 2)):
            continue
        label = "ARROW" if "gps_arrow" in tex else "WITNESS"
        fis = sec.get_face_indices(lod.faces)
        vis = sorted({vi for fi in fis for vi in lod.faces[fi].vertex_indices})
        print("  %s sec[%d] faces=%s verts=%s" % (label, si, fis, vis))
        for vi in vis:
            br = lod.vertex_bone_ref[vi] if vi < len(lod.vertex_bone_ref) else None
            pairs = getattr(br, "pairs", None) if br else None
            names = []
            if pairs:
                for (b, w) in pairs:
                    nm = bones[b][0] if 0 <= b < len(bones) else "?"
                    names.append("%s(b%d,w%d)" % (nm, b, w))
            print("     v[%d] bone=%s" % (vi, ", ".join(names) if names else "NONE/static"))
    # Reference: a face of the panel that renders
    for si, sec in enumerate(lod.sections):
        if tex_of(lod, sec).endswith("brz_cluster_co.paa") and len(sec.get_face_indices(lod.faces)) > 10:
            fi = sec.get_face_indices(lod.faces)[0]
            vi = lod.faces[fi].vertex_indices[0]
            br = lod.vertex_bone_ref[vi] if vi < len(lod.vertex_bone_ref) else None
            pairs = getattr(br, "pairs", None) if br else None
            nm = "NONE/static"
            if pairs:
                nm = ", ".join("%s(b%d)" % (bones[b][0] if 0 <= b < len(bones) else "?", b) for b, _ in pairs)
            print("  PANEL(renders) sec[%d] first vert bone=%s" % (si, nm))
            break
