#!/usr/bin/env python3
"""
ODOL → MLOD Converter
Converts binarized DayZ/Arma .p3d files to editable MLOD format.
Uses our ODOL reader + py3d for MLOD writing.

Based on BisDLL Conversion.cs logic by T_D/Crip12.
"""
import sys
import os
import struct
import math
import collections

sys.path.insert(0, os.path.dirname(__file__))

from odol_reader import ODOL
import py3d


def convert_odol_to_mlod(odol):
    """Convert a parsed ODOL object to a py3d P3D (MLOD) object."""
    mlod = py3d.P3D()
    
    skipped = []
    for i, src_lod in enumerate(odol.lods):
        if src_lod is None:
            # LOD failed to parse upstream (see odol.lod_errors); skip it so the
            # MLOD still contains every LOD that DID parse (partial conversion).
            skipped.append(i)
            continue
        dst_lod = convert_lod(odol, src_lod, i)
        mlod.lods.append(dst_lod)

    if skipped:
        errs = getattr(odol, 'lod_errors', {})
        print(f"  [partial] skipped {len(skipped)} unparseable LOD(s): "
              + ", ".join(f"#{i} ({errs.get(i,'?')})" for i in skipped))
    return mlod


def convert_lod(odol, src, lod_index):
    """Convert a single ODOL LOD to py3d LOD."""
    dst = py3d.LOD()
    dst.resolution = src.resolution
    
    # ── Points ──
    # ODOL vertices are relative to boundingCenter; MLOD uses absolute coords
    bc = odol.model_info.bounding_center
    offset = (bc.x, bc.y, bc.z)
    
    n_verts = len(src.vertices)
    for vi in range(n_verts):
        pt = py3d.Point()
        v = src.vertices[vi]
        pt.coords = (v.x + offset[0], v.y + offset[1], v.z + offset[2])
        # ClipFlags → PointFlags (simplified: store raw clip value)
        pt.flags = src.clip[vi] if src.clip and vi < len(src.clip) else 0
        dst.points.append(pt)
    
    # ── Normals (G2: preserve original per-vertex normals) ──
    # ODOL stores one normal per vertex (parallel to the vertex array). The MLOD
    # facenormals pool is indexed per-vertex via Vertex.normal_index, so we dump the
    # ORIGINAL normals into the pool 1:1 and index each MLOD vertex by its point_index
    # — preserving the authored smoothing instead of recomputing flat per-face normals.
    # Only when the parallel-array invariant holds and the LOD has drawable geometry
    # (sections); otherwise fall back to the flat recompute in the face loop.
    use_orig_normals = (n_verts > 0
                        and len(src.normals) == n_verts
                        and len(src.sections) > 0)
    if use_orig_normals:
        for nrm in src.normals:
            dst.facenormals.append((nrm.x, nrm.y, nrm.z))
    
    # ── Faces ──
    # ODOL groups faces into sections; each section references a material.
    # We iterate sections to assign texture/material per face.
    uv_data = None
    if src.uv_sets and src.uv_sets[0]:
        uv_data = src.uv_sets[0].uv_data
    
    # G7: map each ODOL face index to the MLOD Face created for it, so face-based
    # selections transfer correctly even though dst.faces is built in SECTION order
    # (not ODOL face order).
    odol_face_to_mlod = {}
    face_list = []
    for section in src.sections:
        # Determine texture and material for this section
        textures = getattr(src, 'textures', [])
        materials = getattr(src, 'materials', [])
        
        tex_str = ''
        if hasattr(section, 'texture_index') and section.texture_index >= 0:
            if section.texture_index < len(textures):
                tex_str = textures[section.texture_index]
        
        mat_str = ''
        if hasattr(section, 'material_index') and section.material_index >= 0:
            if section.material_index < len(materials):
                mat_str = materials[section.material_index].material_name
        
        # Get face indices for this section
        face_indices = section.get_face_indices(src.faces)
        
        for fi in face_indices:
            if fi >= len(src.faces):
                continue
            polygon = src.faces[fi]
            n_face_verts = len(polygon.vertex_indices)  # 3 or 4
            
            # Build face
            face = py3d.Face(dst.points, dst.facenormals)
            face.texture = tex_str
            face.material = mat_str
            face.flags = 0
            
            face.vertices = []
            positions = []
            
            for k in range(n_face_verts):
                # ODOL stores in one winding; MLOD uses reversed
                vi = polygon.vertex_indices[n_face_verts - 1 - k]
                
                vert = py3d.Vertex(dst.points, dst.facenormals)
                vert.point_index = vi
                if use_orig_normals:
                    # facenormals pool is parallel to points → index by vertex
                    vert.normal_index = vi
                else:
                    vert.normal_index = len(dst.facenormals)  # set after (flat)
                
                # UV data
                if uv_data and vi * 2 + 1 < len(uv_data):
                    vert.uv = (uv_data[vi * 2], uv_data[vi * 2 + 1])
                else:
                    vert.uv = (0.0, 0.0)
                
                face.vertices.append(vert)
                
                if vi < len(dst.points):
                    positions.append(dst.points[vi].coords)
            
            face_list.append(face)
            odol_face_to_mlod[fi] = face  # G7
            
            if not use_orig_normals:
                # Fallback: compute a flat face normal from vertex positions
                fn = _compute_face_normal(positions)
                normal_idx = len(dst.facenormals)
                dst.facenormals.append(fn)
                for v in face.vertices:
                    v.normal_index = normal_idx
    
    dst.faces = face_list
    
    # ── Named Selections ──
    # ODOL named selections reference vertex/face indices.
    # We need to map them to py3d Point/Face objects.
    for ns in src.named_selections:
        sel = py3d.Selection(dst.points, dst.faces)
        sel.points = {}
        sel.faces = {}
        
        # Vertex-based selection membership (SP-001 fix 2026-05-23; restored
        # 2026-05-27 — the v53 branch had forked from a pre-SP-001 base and lost it,
        # silently dropping every vertex selection on conversion). Map ALL
        # selected_vertices as members. Memory selections (*_axis, dmgzone_*, pos_*,
        # crew*) carry selected_vertices but EMPTY vertex_weights; gating on
        # vertex_weights dropped them (names present, 0 points). The BI weight byte 0
        # can also mean 1.0, so the old `if w > 0` filter was wrong even for skinned ones.
        if ns.selected_vertices:
            for vi in ns.selected_vertices:
                if vi < len(dst.points):
                    sel.points[dst.points[vi]] = 1
        
        # Face-based selection (G7: resolve ODOL face index via the section-aware map
        # built above, not dst.faces[fi] — dst.faces is in section order).
        if ns.selected_faces:
            for fi in ns.selected_faces:
                f = odol_face_to_mlod.get(fi)
                if f is not None:
                    sel.faces[f] = 1
        
        dst.selections[ns.name] = sel
    
    # ── Properties ──
    for k, v in src.named_properties:
        dst.properties[k] = v
    
    # ── Mass (G4) ──
    # Mass lives on the Geometry LOD (resolution ~1e13). When the binarized ODOL
    # retained a real per-point mass array (model_info.mass_array, one entry per
    # geometry point), copy it faithfully. NOTE: binarization usually STRIPS this
    # array (verified empty on tradepost_heli/helipad + Croco quadbike), leaving only
    # the scalar total mass + center_of_mass + inertia tensor; in that case we fall
    # back to the historical uniform distribution, which preserves the total exactly.
    if abs(src.resolution - 1e13) / 1e13 < 0.01:  # Geometry LOD
        mass_array = getattr(odol.model_info, 'mass_array', None) or []
        if len(mass_array) == n_verts and n_verts > 0:
            for i, pt in enumerate(dst.points):
                pt.mass = mass_array[i]
        else:
            total_mass = odol.model_info.mass
            if n_verts > 0 and total_mass > 0:
                mass_per_vert = total_mass / n_verts
                for pt in dst.points:
                    pt.mass = mass_per_vert
    
    return dst


def _compute_face_normal(positions):
    """Compute face normal from 3+ vertex positions."""
    if len(positions) < 3:
        return (0.0, 1.0, 0.0)
    
    # Use first 3 vertices
    p0, p1, p2 = positions[0], positions[1], positions[2]
    
    # Edge vectors
    e1 = (p1[0]-p0[0], p1[1]-p0[1], p1[2]-p0[2])
    e2 = (p2[0]-p0[0], p2[1]-p0[1], p2[2]-p0[2])
    
    # Cross product
    nx = e1[1]*e2[2] - e1[2]*e2[1]
    ny = e1[2]*e2[0] - e1[0]*e2[2]
    nz = e1[0]*e2[1] - e1[1]*e2[0]
    
    # Normalize
    length = math.sqrt(nx*nx + ny*ny + nz*nz)
    if length < 1e-10:
        return (0.0, 1.0, 0.0)
    
    return (nx/length, ny/length, nz/length)


# AnimType (ODOL) → model.cfg "type" string. Axis-aligned rotation/translation
# variants all map to the generic rotation/translation in model.cfg (the axis is
# carried by the axis selections, not the type name).
_ANIM_TYPE_NAME = {
    0: 'rotation', 1: 'rotationX', 2: 'rotationY', 3: 'rotationZ',
    4: 'translation', 5: 'translationX', 6: 'translationY', 7: 'translationZ',
    8: 'direct', 9: 'hide',
}


def emit_model_cfg(odol, model_name):
    """G3: emit a model.cfg snippet from odol.animations.

    The MLOD format does NOT store animations — they live in model.cfg. The ODOL
    keeps the compiled animation classes (type, source, phases, value range and the
    rotation angle / translation offset endpoints), which we reconstruct here so an
    animated model isn't silently flattened on recovery.

    Returns the model.cfg text, or None if the model has no animations.
    """
    anims = getattr(odol, 'animations', None)
    if not anims or not getattr(anims, 'classes', None):
        return None

    skel = odol.model_info.skeleton
    skel_name = getattr(skel, 'name', None) or f"{model_name}_skeleton"

    lines = []
    lines.append("// Auto-generated from binarized ODOL by dayz-p3d-debinarizer (G3).")
    lines.append("// Animation classes recovered from the ODOL; verify axis/source")
    lines.append("// selections against the model's memory points before shipping.")
    lines.append("class CfgSkeletons")
    lines.append("{")
    lines.append(f"\tclass {skel_name}")
    lines.append("\t{")
    lines.append("\t\tisDiscrete=1;")
    bones = getattr(skel, 'bones', None) or []
    if bones:
        bone_pairs = []
        for b in bones:
            name = b[0] if isinstance(b, (list, tuple)) else getattr(b, 'name', str(b))
            parent = b[1] if isinstance(b, (list, tuple)) and len(b) > 1 else ''
            bone_pairs.append(f'"{name}","{parent}"')
        lines.append("\t\tskeletonBones[]=")
        lines.append("\t\t{")
        lines.append("\t\t\t" + ",".join(bone_pairs))
        lines.append("\t\t};")
    lines.append("\t};")
    lines.append("};")
    lines.append("class CfgModels")
    lines.append("{")
    lines.append(f"\tclass {model_name}")
    lines.append("\t{")
    lines.append(f'\t\tskeletonName="{skel_name}";')
    lines.append("\t\tsections[]={};")
    lines.append("\t\tclass Animations")
    lines.append("\t\t{")
    for ci, a in enumerate(anims.classes):
        tname = _ANIM_TYPE_NAME.get(a.anim_type, 'rotation')
        # Guard against an empty/blank anim name (asciiz can be empty) which
        # would emit an invalid `class {` — synthesize a stable fallback name.
        cls_name = a.anim_name.strip() if (a.anim_name and a.anim_name.strip()) else f"Anim_{ci}"
        lines.append(f"\t\t\tclass {cls_name}")
        lines.append("\t\t\t{")
        lines.append(f'\t\t\t\ttype="{tname}";')
        lines.append(f'\t\t\t\tsource="{a.anim_source}";')
        lines.append('\t\t\t\tselection="";  // TODO: bind to the moving part selection')
        lines.append('\t\t\t\taxis="";       // TODO: bind to the axis memory selection')
        lines.append("\t\t\t\tmemory=1;")
        lines.append(f"\t\t\t\tminValue={_fmt(a.min_value)};")
        lines.append(f"\t\t\t\tmaxValue={_fmt(a.max_value)};")
        if a.anim_type in (0, 1, 2, 3):  # rotation*
            lines.append(f"\t\t\t\tangle0={_fmt(a.angle0)};")
            lines.append(f"\t\t\t\tangle1={_fmt(a.angle1)};")
        elif a.anim_type in (4, 5, 6, 7):  # translation*
            lines.append(f"\t\t\t\toffset0={_fmt(a.offset0)};")
            lines.append(f"\t\t\t\toffset1={_fmt(a.offset1)};")
        elif a.anim_type == 9:  # hide
            lines.append(f"\t\t\t\thideValue={_fmt(a.hide_value)};")
        # Recovered geometric axis (axis_pos, axis_dir) from the highest-res LOD that
        # carries it — emitted as a comment since model.cfg expects named selections.
        axis = _first_axis_for(anims, ci)
        if axis is not None:
            (p0, p1) = axis
            lines.append(f"\t\t\t\t// recovered axis pos=({_fmt(p0.x)},{_fmt(p0.y)},{_fmt(p0.z)}) "
                         f"dir=({_fmt(p1.x)},{_fmt(p1.y)},{_fmt(p1.z)})")
        lines.append("\t\t\t};")
    lines.append("\t\t};")
    lines.append("\t};")
    lines.append("};")
    return "\n".join(lines) + "\n"


def _fmt(x):
    """Format a float for config output (trim trailing zeros, keep determinism)."""
    s = f"{x:.6f}".rstrip('0').rstrip('.')
    return s if s not in ('', '-0') else '0'


def _first_axis_for(anims, class_index):
    """Return the first non-None (pos,dir) axis pair for a given animation class
    across the per-LOD axis_data, or None."""
    for lod_axes in getattr(anims, 'axis_data', []) or []:
        if class_index < len(lod_axes) and lod_axes[class_index] is not None:
            return lod_axes[class_index]
    return None


def main():
    if len(sys.argv) < 2:
        print("Usage: odol_to_mlod.py <input.p3d> [output.p3d]")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else input_path.replace('.p3d', '_mlod.p3d')
    
    print(f"Reading ODOL: {input_path}")
    odol = ODOL.from_file(input_path)
    print(f"  {odol}")
    
    print(f"Converting to MLOD...")
    mlod = convert_odol_to_mlod(odol)
    print(f"  {len(mlod.lods)} LODs converted")
    
    for i, lod in enumerate(mlod.lods):
        print(f"    LOD {i}: res={lod.resolution:.0f}, "
              f"{len(lod.points)} pts, {len(lod.faces)} faces, "
              f"{len(lod.facenormals)} normals, "
              f"{len(lod.selections)} sels")
    
    print(f"Writing MLOD: {output_path}")
    with open(output_path, 'wb') as f:
        mlod.write(f)
    
    file_size = os.path.getsize(output_path)
    print(f"  Written {file_size} bytes")

    # G3: emit model.cfg alongside the MLOD when the ODOL carried animations.
    model_name = os.path.splitext(os.path.basename(output_path))[0]
    cfg = emit_model_cfg(odol, model_name)
    if cfg:
        cfg_path = os.path.join(os.path.dirname(output_path) or '.', 'model.cfg')
        with open(cfg_path, 'w') as f:
            f.write(cfg)
        n_anims = len(odol.animations.classes)
        print(f"  Emitted model.cfg with {n_anims} animation(s): {cfg_path}")
    
    # Verify by re-reading
    print(f"Verifying...")
    with open(output_path, 'rb') as f:
        verify = py3d.P3D(f)
    print(f"  Read back {len(verify.lods)} LODs")
    for i, lod in enumerate(verify.lods):
        print(f"    LOD {i}: {len(lod.points)} pts, {len(lod.faces)} faces, "
              f"{len(lod.selections)} sels, res={lod.resolution:.0f}")
    
    print("Done!")


if __name__ == '__main__':
    main()
