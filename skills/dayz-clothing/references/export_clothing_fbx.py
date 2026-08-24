import sys, os
sys.path.insert(0, r"<dayz-projects>\py3d")
import py3d
import bpy
from mathutils import Vector

SRC = r"<dayz-projects>\ArmorHneck\data"
OUT = r"<tmp>\armorhneck_entrega\fbx_work"
TEX = os.path.join(OUT, "armorhneck_beige_co.png")
BONES = ["leftarm", "rightarm", "leftforearm", "rightforearm", "leftupleg", "rightupleg", "neck", "pelvis", "spine", "spine3"]

def dayz_to_blender(c):
    return (c[0], -c[2], c[1])

bpy.ops.wm.read_factory_settings(use_empty=True)

for fname, objname in (("armorhneck_m.p3d", "armorhneck_m"), ("armorhneck_f.p3d", "armorhneck_f")):
    with open(os.path.join(SRC, fname), "rb") as f:
        p = py3d.P3D(f)
    lod = p.lods[0]
    pt_index = {id(pt): i for i, pt in enumerate(lod.points)}
    verts = [dayz_to_blender(pt.coords) for pt in lod.points]
    faces = []
    uvs_per_face = []
    for face in lod.faces:
        faces.append([v.point_index for v in face.vertices])
        uvs_per_face.append([(v.uv[0], 1.0 - v.uv[1]) for v in face.vertices])

    mesh = bpy.data.meshes.new(objname)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    uv_layer = mesh.uv_layers.new(name="UVMap")
    li = 0
    for poly, face_uvs in zip(mesh.polygons, uvs_per_face):
        for k in range(poly.loop_total):
            uv_layer.data[li].uv = face_uvs[k]
            li += 1

    obj = bpy.data.objects.new(objname, mesh)
    bpy.context.collection.objects.link(obj)

    bone_weights = {}
    bone_heads = {}
    for selname, sel in lod.selections.items():
        nm = selname.lower()
        if nm not in BONES:
            continue
        entries = []
        acc = Vector((0, 0, 0)); tot = 0.0
        for pt, w in sel.points.items():
            wv = float(w) if w is not None else 0.0
            if wv > 0:
                i = pt_index[id(pt)]
                entries.append((i, wv))
                acc += Vector(verts[i]) * wv; tot += wv
        bone_weights[nm] = entries
        bone_heads[nm] = (acc / tot) if tot else Vector((0, 0, 1))

    arm_data = bpy.data.armatures.new(objname + "_rig")
    arm_obj = bpy.data.objects.new(objname + "_rig", arm_data)
    bpy.context.collection.objects.link(arm_obj)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="EDIT")
    for nm in BONES:
        if nm not in bone_heads:
            continue
        eb = arm_data.edit_bones.new(nm)
        h = bone_heads[nm]
        eb.head = h
        eb.tail = h + Vector((0, 0, 0.08))
    bpy.ops.object.mode_set(mode="OBJECT")

    for nm, entries in bone_weights.items():
        vg = obj.vertex_groups.new(name=nm)
        for i, wv in entries:
            vg.add([i], wv, "REPLACE")

    obj.parent = arm_obj
    mod = obj.modifiers.new("Armature", "ARMATURE")
    mod.object = arm_obj

    mat = bpy.data.materials.new(objname + "_mat")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if os.path.exists(TEX):
        teximg = mat.node_tree.nodes.new("ShaderNodeTexImage")
        teximg.image = bpy.data.images.load(TEX)
        mat.node_tree.links.new(teximg.outputs["Color"], bsdf.inputs["Base Color"])
    mesh.materials.append(mat)

    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    arm_obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj
    fbx_path = os.path.join(OUT, objname + ".fbx")
    bpy.ops.export_scene.fbx(filepath=fbx_path, use_selection=True, path_mode="COPY", embed_textures=False, add_leaf_bones=False)
    print("EXPORTED %s: %d verts %d faces %d bone-groups" % (fbx_path, len(verts), len(faces), len(bone_weights)))

bpy.ops.wm.read_factory_settings(use_empty=True)
for objname in ("armorhneck_m", "armorhneck_f"):
    fbx_path = os.path.join(OUT, objname + ".fbx")
    before = set(o.name for o in bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=fbx_path)
    meshes = [o for o in bpy.data.objects if o.name not in before and o.type == "MESH"]
    assert meshes, "no mesh reimported for %s" % objname
    o = meshes[0]
    gnames = sorted(g.name for g in o.vertex_groups)
    wsum = 0
    for v in o.data.vertices[:500]:
        wsum += sum(g.weight for g in v.groups)
    print("REIMPORT %s: %d verts %d vgroups %s uv=%s sample500_weightsum=%.1f" % (
        objname, len(o.data.vertices), len(o.vertex_groups), gnames[:4], len(o.data.uv_layers) > 0, wsum))

print("FBX_EXPORT_ALL_OK")
