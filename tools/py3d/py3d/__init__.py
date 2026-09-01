#!/usr/bin/env python3

r"""py3d-dayz - read and write Arma/DayZ .p3d files (MLOD).

A maintained fork of https://github.com/KoffeinFlummi/py3d (master 7acd58b,
MIT, unmaintained since 2018) by Felix "KoffeinFlummi" Wiegand, whose
copyright is preserved in LICENSE. The importable module is still `py3d`,
so `import py3d` keeps working; only the distribution name differs, because
`py3d` on PyPI belongs to an unrelated library.

What this fork adds on top of upstream's MLOD codec:

- Anti-corruption guards: paths that used to corrupt a .p3d silently or
  crash late now fail EARLY with an actionable message (selection weight
  validation, #Property# length limit, stale-binding detection).
- DayZ LOD constants and `LOD.kind()` / `P3D.get_lod()`. Note DayZ does NOT
  use the Arma-3-era e13 ids for FireGeo/ViewGeo: they are 7e15 / 6e15.
- Geometry helpers: `bbox`, `triangulate`, `set_selection`,
  `set_total_mass`, `set_memory_point`, and a proxy lifecycle
  (add / inspect / align / remove) with explicit raw<->engine frames.
- `P3D.validate()`, a model validator that reports `Finding`s, and a CLI:
  `python -m py3d info|validate|diff`.
- Recipe JSON (`to_dict` / `from_dict`) for inspection. See KNOWN-ISSUES:
  it is lossy and is NOT a safe persistence format yet.
- Format fidelity for UV sets: every `#UVSet#` beyond the first survives a
  read/write cycle (`Vertex.uv_sets`), and a LOD without faces gets the
  empty `#UVSet#` tag Object Builder writes (Memory, LandContact).

Write contract: byte-identical to upstream for valid canonical inputs, with
one deliberate exception - the empty `#UVSet#` tag in LODs without faces;
it raises where upstream would have corrupted the file or crashed later.

`IS_DAYZ_FORK = True` is provided so scripts can assert they imported this
library and not the unrelated `py3d` from PyPI.
"""


import collections
import math
import os
import re
import struct
import tempfile


__version__ = "1.6.0"
IS_DAYZ_FORK = True

_REQUIRED = object()


def _read_asciiz(f, encoding="utf-8"):
    pos = f.tell()

    bts = b""
    while b"\0" not in bts:
        chunk = f.read(1024)
        if not chunk:
            # Upstream (master 7acd58b) itera aqui para siempre: en EOF
            # read() devuelve b"" indefinidamente y el proceso queda
            # COLGADO, sin traceback y sin ser capturable por el llamante.
            # Un .p3d truncado es el caso normal (escritura a medias,
            # descarga incompleta, sector danado).
            raise ValueError(
                "unterminated asciiz string starting at offset %d: reached "
                "EOF after %d bytes without a NUL terminator - the file is "
                "truncated or not a valid MLOD" % (pos, len(bts)))
        bts += chunk
    bts = bts[:bts.index(b"\0")]

    f.seek(pos + len(bts) + 1)

    return str(bts, encoding=encoding)



# ---------------------------------------------------------------------------
# S2 (F2-01): constantes LOD DayZ canonicas.
#
# Fuente consolidada (plan F2-01): dayz-model-pipeline/references/
# lods-and-geometry.md + dayz-p3d-inspector (extract.py:32-46,
# build.py:80-96), verificados contra MLODs reales. Sustituye a las 4
# copias historicas del mapa resolucion->LOD, que usaban tolerancias
# absolutas DISTINTAS (+-1e11, +-5e13, +-1e13 y rangos ad-hoc): aqui hay
# UNA tolerancia relativa.
#
# NOTA DayZ vs Arma 3 (anti-drift): los ids legacy de la familia e13 que
# circulan en tooling Arma (FireGeo/ViewGeo en 2e13/3e13/7e13) NO valen
# en DayZ. DayZ usa ViewGeometry=6e15 y FireGeometry=7e15. kind()
# devuelve None para esos valores y validate() emite
# WARN_LOD_KIND_UNKNOWN.
LOD_RESOLUTIONS = collections.OrderedDict([
    ("geometry",      1.0e13),
    ("memory",        1.0e15),
    ("landcontact",   2.0e15),
    ("roadway",       3.0e15),
    ("paths",         4.0e15),
    ("hitpoints",     5.0e15),
    ("view_geometry", 6.0e15),
    ("fire_geometry", 7.0e15),
])

#: |res - canon| <= LOD_RELATIVE_TOLERANCE * canon  =>  ese kind.
LOD_RELATIVE_TOLERANCE = 0.05

#: Niveles de detalle visuales (0.0, 1.0, 2.0, 4.0, 8.0, ...).
VISUAL_RESOLUTION_MAX = 1.0e3
#: ShadowVolume = 1e4 + subnivel (SV 0 -> 10000.0, SV 10 -> 10010.0).
SHADOWVOLUME_RESOLUTION_MIN = 1.0e4
SHADOWVOLUME_RESOLUTION_MAX = 2.0e4

#: F3-02: Blender Z-up -> DayZ Y-up, (x,y,z) -> (x,z,-y). det=+1 (rotacion
#: propia): NO invierte winding (LL-020; "siempre invertir tras rotar" es el
#: bug). Uso: p3d.transform(py3d.BLENDER_TO_DAYZ).
BLENDER_TO_DAYZ = (
    (1.0, 0.0, 0.0),
    (0.0, 0.0, 1.0),
    (0.0, -1.0, 0.0),
)

#: Alias aceptados por P3D.get_lod() (terminologia corta del pipeline).
LOD_KIND_ALIASES = {
    "viewgeo": "view_geometry",
    "firegeo": "fire_geometry",
    "shadow": "shadowvolume",
}

_GEOMETRY_CLASS_KINDS = ("geometry", "view_geometry", "fire_geometry")


def classify_lod_resolution(resolution):
    """F2-01: kind canonico de una resolucion MLOD, o None si desconocida.

    Kinds: "visual", "shadowvolume" y las claves de LOD_RESOLUTIONS.
    """
    if 0.0 <= resolution < VISUAL_RESOLUTION_MAX:
        return "visual"
    if SHADOWVOLUME_RESOLUTION_MIN <= resolution < SHADOWVOLUME_RESOLUTION_MAX:
        return "shadowvolume"
    for name, canon in LOD_RESOLUTIONS.items():
        if abs(resolution - canon) <= LOD_RELATIVE_TOLERANCE * canon:
            return name
    return None


# ---------------------------------------------------------------------------
# S2 (F2-06): frame de proxy MLOD.
#
# Port 1:1 (stdlib, sin numpy) de la convencion source-verified de
# dayz-proxy-align/scripts/proxy_frame.py:
#   - derive_frame()        -> proxy_frame.py:38-52  (ANGLE-SORT: el vertice
#     de mayor angulo interior es el anchor; el medio -> +Y local; el menor
#     -> +Z local; x = y X z; z = x X y re-ortogonalizado)
#   - canonical_triangle()  -> proxy_frame.py:54-61  (anchor + scale*R[1] +
#     2*scale*R[2]: tres angulos DISTINTOS => frame inambiguo)
# Fuente original: Arma3ObjectBuilder utilities/proxy.py + mrcmodding
# gitbook "proxy coordinates" (leido 2026-05-31 por esa skill).

PROXY_NAME_RE = re.compile(r"^proxy:(?P<path>.+)\.(?P<index>\d+)$",
                           re.IGNORECASE)
PROXY_ENGINE_CORRECTION = (
    (-1.0, 0.0, 0.0),
    (0.0, 0.0, 1.0),
    (0.0, 1.0, 0.0),
)
_IDENTITY_3 = (
    (1.0, 0.0, 0.0),
    (0.0, 1.0, 0.0),
    (0.0, 0.0, 1.0),
)


def _v_sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _v_cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _v_norm(v):
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def _v_unit(v, fallback):
    n = _v_norm(v)
    if n > 1e-12:
        return (v[0] / n, v[1] / n, v[2] / n)
    return fallback


def _mat_vec(m, v):
    """F3-02: producto matriz 3x3 (row-major) x vector columna."""
    return (m[0][0] * v[0] + m[0][1] * v[1] + m[0][2] * v[2],
            m[1][0] * v[0] + m[1][1] * v[1] + m[1][2] * v[2],
            m[2][0] * v[0] + m[2][1] * v[1] + m[2][2] * v[2])


def _det3(m):
    """F3-02: determinante 3x3 por formula cerrada."""
    return (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
            - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
            + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))


def _mat_mul3(a, b):
    return tuple(
        tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3))
        for i in range(3)
    )


def _validate_proxy_rotation(rotation):
    try:
        rows = tuple(tuple(float(value) for value in row) for row in rotation)
    except (TypeError, ValueError, OverflowError):
        raise ValueError("proxy rotation must be a finite 3x3 matrix")
    if len(rows) != 3 or any(len(row) != 3 for row in rows):
        raise ValueError("proxy rotation must be a finite 3x3 matrix")
    if any(not math.isfinite(value) for row in rows for value in row):
        raise ValueError("proxy rotation must be a finite 3x3 matrix")
    tolerance = 1e-6
    for i in range(3):
        for j in range(3):
            dot = sum(rows[k][i] * rows[k][j] for k in range(3))
            expected = 1.0 if i == j else 0.0
            if abs(dot - expected) > tolerance:
                raise ValueError(
                    "proxy rotation must be orthonormal with determinant +1"
                )
    if abs(_det3(rows) - 1.0) > tolerance:
        raise ValueError(
            "proxy rotation must be orthonormal with determinant +1"
        )
    return rows


def proxy_frame_to_engine(rotation):
    """Convert a validated raw MLOD proxy frame to its DayZ engine frame."""
    return _mat_mul3(
        PROXY_ENGINE_CORRECTION,
        _validate_proxy_rotation(rotation),
    )


def proxy_frame_from_engine(rotation):
    """Convert a validated DayZ engine proxy frame to its raw MLOD frame."""
    return _mat_mul3(
        PROXY_ENGINE_CORRECTION,
        _validate_proxy_rotation(rotation),
    )


def _validate_proxy_anchor(anchor):
    try:
        values = tuple(float(value) for value in anchor)
    except (TypeError, ValueError, OverflowError):
        raise ValueError("proxy anchor must contain three finite numbers")
    if len(values) != 3 or any(not math.isfinite(value) for value in values):
        raise ValueError("proxy anchor must contain three finite numbers")
    return values


def _validate_proxy_scale(scale):
    if isinstance(scale, bool):
        raise ValueError("proxy scale must be finite and greater than zero")
    try:
        value = float(scale)
    except (TypeError, ValueError, OverflowError):
        raise ValueError("proxy scale must be finite and greater than zero")
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError("proxy scale must be finite and greater than zero")
    try:
        packed = struct.unpack("<f", struct.pack("<f", value))[0]
    except (OverflowError, struct.error):
        raise ValueError("proxy scale must fit float32")
    if packed == 0.0:
        raise ValueError("proxy scale is degenerate after float32 packing")
    return value


def _validate_proxy_path_index(path, index):
    if not isinstance(path, str):
        raise TypeError("proxy path must be a string")
    if not path:
        raise ValueError("proxy path must not be empty")
    if "\0" in path:
        raise ValueError("proxy path must not contain NUL")
    if any(ord(char) < 32 or 0x7F <= ord(char) <= 0x9F for char in path):
        raise ValueError("proxy path must not contain control characters")
    if path.lower().endswith(".p3d"):
        raise ValueError("proxy path must omit the .p3d suffix")
    if isinstance(index, bool) or not isinstance(index, int):
        raise TypeError("proxy index must be an int >= 1 (bool is invalid)")
    if index < 1:
        raise ValueError("proxy index must be >= 1")
    return path, index


def _validate_transform_matrix(matrix):
    """F3-02 (D-S3-6, R22-P1-02): forma 3x3 numerica + contrato
    "ortogonal x escala uniforme" (columnas mutuamente ortogonales, normas
    iguales y no-cero, tolerancia relativa 1e-6). Fuera de contrato ->
    ValueError SIN mutar (las normales exigirian M^-T). Devuelve tuplas
    de float."""
    try:
        rows = [tuple(float(x) for x in row) for row in matrix]
    except (TypeError, ValueError):
        raise ValueError("transform(): matrix must be 3x3 numeric")
    if len(rows) != 3 or any(len(r) != 3 for r in rows):
        raise ValueError("transform(): matrix must be 3x3 numeric")
    m = tuple(rows)
    cols = [(m[0][j], m[1][j], m[2][j]) for j in range(3)]
    norms = [_v_norm(c) for c in cols]
    s = max(norms)
    tol = 1e-6
    if s <= 0.0 or any(abs(n - s) > tol * s for n in norms):
        raise ValueError(
            "transform(): matrix must be orthogonal times uniform scale")
    for a in range(3):
        for b in range(a + 1, 3):
            dot = (cols[a][0] * cols[b][0] + cols[a][1] * cols[b][1]
                   + cols[a][2] * cols[b][2])
            if abs(dot) > tol * norms[a] * norms[b]:
                raise ValueError(
                    "transform(): matrix must be orthogonal times "
                    "uniform scale")
    return m


def _proxy_angle(u, v):
    nu = _v_norm(u)
    nv = _v_norm(v)
    if nu < 1e-12 or nv < 1e-12:
        return 0.0
    c = (u[0] * v[0] + u[1] * v[1] + u[2] * v[2]) / (nu * nv)
    return math.acos(max(-1.0, min(1.0, c)))


def derive_proxy_frame(tri):
    """Port de proxy_frame.derive_frame (proxy_frame.py:38-52).

    tri: secuencia de 3 coords (x, y, z) en espacio MLOD crudo.
    Devuelve (anchor list, R filas (x, y, z) tuple-de-tuplas,
    ambiguous bool, angles_deg_desc list).
    """
    P = [tuple(float(c) for c in p) for p in tri]
    ang = [_proxy_angle(_v_sub(P[(i + 1) % 3], P[i]),
                        _v_sub(P[(i + 2) % 3], P[i])) for i in range(3)]
    order = sorted(range(3), key=lambda i: ang[i], reverse=True)
    center, vy, vz = P[order[0]], P[order[1]], P[order[2]]
    deg = sorted((math.degrees(a) for a in ang), reverse=True)
    ambiguous = abs(deg[1] - deg[2]) < 1.0
    y = _v_unit(_v_sub(vy, center), (0.0, 1.0, 0.0))
    z = _v_unit(_v_sub(vz, center), (0.0, 0.0, 1.0))
    x = _v_unit(_v_cross(y, z), (1.0, 0.0, 0.0))
    zc = _v_cross(x, y)
    n = _v_norm(zc) + 1e-12
    z = (zc[0] / n, zc[1] / n, zc[2] / n)
    return list(center), (x, y, z), bool(ambiguous), [float(d) for d in deg]


def canonical_proxy_triangle(anchor, rotation=None, scale=0.001, space="raw"):
    """Port de proxy_frame.canonical_triangle (proxy_frame.py:54-61).

    Triangulo inambiguo en *anchor* cuyo frame derivado == rotation
    (identidad si None). Orden: [anchor, vert_y (+Y, cateto corto),
    vert_z (+Z, cateto largo 2x)].
    """
    if space not in ("raw", "engine"):
        raise ValueError("proxy space must be 'raw' or 'engine'")
    a = _validate_proxy_anchor(anchor)
    raw_rotation = _IDENTITY_3 if rotation is None \
        else _validate_proxy_rotation(rotation)
    if space == "engine":
        raw_rotation = proxy_frame_from_engine(raw_rotation)
    scale = _validate_proxy_scale(scale)
    vy = (a[0] + scale * raw_rotation[1][0],
          a[1] + scale * raw_rotation[1][1],
          a[2] + scale * raw_rotation[1][2])
    vz = (a[0] + 2.0 * scale * raw_rotation[2][0],
          a[1] + 2.0 * scale * raw_rotation[2][1],
          a[2] + 2.0 * scale * raw_rotation[2][2])
    triangle = [list(a), list(vy), list(vz)]
    try:
        packed = [
            tuple(struct.unpack("<f", struct.pack("<f", value))[0]
                  for value in point)
            for point in triangle
        ]
    except (OverflowError, struct.error):
        raise ValueError("proxy scale/anchor must fit float32")
    if _v_norm(_v_cross(_v_sub(packed[1], packed[0]),
                          _v_sub(packed[2], packed[0]))) == 0.0:
        raise ValueError("proxy scale is degenerate after float32 packing")
    return triangle


# ---------------------------------------------------------------------------
# S2 (F2-07): Recipe JSON v1 — capa de compatibilidad con dayz-p3d-inspector.
#
# D7 (scoped): el schema del inspector ES la spec. Estos helpers son ports
# 1:1 de p3d_inspector_extract.py / p3d_inspector_build.py (sin numpy).
# El clasificador _recipe_lod_type reproduce VERBATIM los umbrales del
# extractor (extract.py:55-88) — es deliberadamente DISTINTO de
# classify_lod_resolution(): este modulo clasifica para el schema v1 del
# recipe; kind() es el clasificador canonico del fork.
#
# Perdidas conocidas del schema v1 (las mismas que extract/build HOY):
#   - masa por punto NO viaja en el recipe; from_dict la reasigna con la
#     politica de build (override/heuristica densidad) a geometry Y
#     fire_geometry -> ERR_MASS_ONLY_GEOMETRY esperado en el rebuilt
#     (LL-080; decision D-S3-8, parity verbatim);
#   - flags de puntos/caras -> 0; pesos de selection -> 1;
#   - resolution se "ajusta" a la canonica del tipo (build:108-112);
#   - el Memory LOD se reconstruye desde recipe["memory_points"].

_RECIPE_WIREFRAME_TYPES = (
    "geometry", "fire_geometry", "view_geometry",
    "landcontact", "roadway", "paths", "hitpoints",
)
_RECIPE_BUILD_WIREFRAME_TYPES = _RECIPE_WIREFRAME_TYPES + ("shadow",)
#: build.py masa geometry Y fire_geometry (port verbatim, D7). Decision
#: 2026-06-07 (plan S3, D-S3-8): se CONSERVA por parity aunque LL-080
#: prohibe #Mass# fuera de Geometry -> un modelo salido de from_dict
#: dispara ERR_MASS_ONLY_GEOMETRY (RECIPE-IDEM lo pinea). Fix upstream
#: pendiente en la skill del inspector (bug-ledger DayZ_Tooling).
_RECIPE_MASSED_TYPES = ("geometry", "fire_geometry")

# build.py:80-96 (verbatim)
_RECIPE_LOD_RESOLUTION = {
    "visual_0":       0.0,
    "visual_1":       1.0,
    "visual_2":       4.0,
    "visual_3":       8.0,
    "shadow":         1.0e4,
    "shadow_close":   1.0e4,
    "shadow_far":     1.1e4,
    "geometry":       1.0e13,
    "memory":         1.0e15,
    "landcontact":    2.0e15,
    "roadway":        3.0e15,
    "paths":          4.0e15,
    "hitpoints":      5.0e15,
    "view_geometry":  6.0e15,
    "fire_geometry":  7.0e15,
}

# build.py:40-60 (verbatim)
_RECIPE_DENSITY_KEYWORDS = [
    ("steel",   7800),
    ("iron",    7800),
    ("metal",   7800),
    ("alloy",   7500),
    ("copper",  8900),
    ("brass",   8500),
    ("aluminum", 2700),
    ("alum",    2700),
    ("wood",     600),
    ("timber",   600),
    ("plank",    600),
    ("plastic", 1200),
    ("rubber",  1100),
    ("glass",   2500),
    ("concrete", 2400),
    ("stone",   2600),
    ("fabric",   300),
    ("cloth",    300),
]
_RECIPE_DENSITY_DEFAULT = 2000


def _recipe_lod_type(resolution):
    """Clasificador del SCHEMA v1 (port verbatim de extract.py:55-88)."""
    if resolution < 0.5:
        return "visual_0"
    elif resolution < 2.0:
        return "visual_1"
    elif resolution < 6.0:
        return "visual_2"
    elif resolution < 10.0:
        return "visual_3"
    elif resolution < 1.5e4:
        return "shadow"
    elif abs(resolution - 1.0e13) < 1.0e11:
        return "geometry"
    elif abs(resolution - 1.0e15) < 5.0e13:
        return "memory"
    elif abs(resolution - 2.0e15) < 5.0e13:
        return "landcontact"
    elif abs(resolution - 3.0e15) < 5.0e13:
        return "roadway"
    elif abs(resolution - 4.0e15) < 5.0e13:
        return "paths"
    elif abs(resolution - 5.0e15) < 5.0e13:
        return "hitpoints"
    elif abs(resolution - 6.0e15) < 5.0e13:
        return "view_geometry"
    elif abs(resolution - 7.0e15) < 5.0e13:
        return "fire_geometry"
    else:
        return "unknown_%.0f" % resolution


def _recipe_classify_memory_point(selections):
    """Port de extract.py:91-109."""
    for sel in selections:
        s = sel.lower()
        if "axis" in s:
            return "axis"
        if s.startswith("pos ") or s == "pos center":
            return "center"
        if s.startswith("ce_") or s == "ce_center":
            return "center"
        if "actionpos" in s or "action_pos" in s:
            return "interaction"
        if "box_placing" in s:
            return "placing"
        if "port_" in s or "cable_" in s:
            return "port"
        if "proxy" in s:
            return "proxy"
    return "other"


def _recipe_visual_geometry(lod):
    """Port de extract.py:114-173 (dedup de vertices + V-flip glTF)."""
    vertex_map = {}
    positions = []
    normals = []
    uvs = []
    material_groups = collections.OrderedDict()

    for face in lod.faces:
        tex = face.texture if face.texture else ""
        mat = face.material if face.material else ""
        key = "%s|%s" % (tex, mat)
        if key not in material_groups:
            material_groups[key] = []

        face_indices = []
        for vertex in face.vertices:
            pt_idx = vertex.point_index
            norm_idx = vertex.normal_index
            u, v = vertex.uv if vertex.uv else (0.0, 0.0)
            vert_key = (pt_idx, norm_idx, round(u, 6), round(v, 6))
            if vert_key not in vertex_map:
                vertex_map[vert_key] = len(positions)
                positions.append(list(lod.points[pt_idx].coords))
                if norm_idx < len(lod.facenormals):
                    normals.append(list(lod.facenormals[norm_idx]))
                else:
                    normals.append([0.0, 1.0, 0.0])
                uvs.append([u, 1.0 - v])  # glTF V-flip
            face_indices.append(vertex_map[vert_key])

        if len(face_indices) == 3:
            material_groups[key].extend(face_indices)
        elif len(face_indices) == 4:
            material_groups[key].extend([
                face_indices[0], face_indices[1], face_indices[2],
                face_indices[0], face_indices[2], face_indices[3],
            ])
        elif len(face_indices) > 4:
            for i in range(1, len(face_indices) - 1):
                material_groups[key].extend(
                    [face_indices[0], face_indices[i], face_indices[i + 1]])

    return {
        "positions": positions,
        "normals": normals,
        "uvs": uvs,
        "material_groups": material_groups,
    }


def _recipe_wireframe(lod):
    """Port de extract.py:176-193. edges ORDENADAS (estabilidad RECIPE-IDEM;
    el extractor emite el orden de iteracion del set — igualdad semantica)."""
    positions = [list(p.coords) for p in lod.points]
    edges = set()
    faces_data = []
    for face in lod.faces:
        verts = [v.point_index for v in face.vertices]
        faces_data.append(verts)
        for i in range(len(verts)):
            edge = tuple(sorted([verts[i], verts[(i + 1) % len(verts)]]))
            edges.add(edge)
    return {
        "positions": positions,
        "edges": [list(e) for e in sorted(edges)],
        "faces": faces_data,
    }


def _recipe_selections(lod):
    """Port de extract.py:196-238 (indices via id(), weight > 0)."""
    selections = collections.OrderedDict()
    pt_idx = {id(p): i for i, p in enumerate(lod.points)}
    fc_idx = {id(f): i for i, f in enumerate(lod.faces)}
    for name, sel in lod.selections.items():
        vertex_indices = []
        for pt, weight in sel.points.items():
            if weight > 0:
                idx = pt_idx.get(id(pt))
                if idx is not None:
                    vertex_indices.append(idx)
        face_indices = []
        for fc, weight in sel.faces.items():
            if weight > 0:
                idx = fc_idx.get(id(fc))
                if idx is not None:
                    face_indices.append(idx)
        selections[name] = {
            "vertices": vertex_indices,
            "faces": face_indices,
            "vertex_count": len(vertex_indices),
            "face_count": len(face_indices),
        }
    return selections


def _recipe_memory_data(lod):
    """Port de extract.py:252-308. Devuelve (memory_points, axes)."""
    memory_points = []
    axes = collections.OrderedDict()
    point_to_selections = {}
    selection_point_map = collections.OrderedDict()

    pt_idx = {id(p): i for i, p in enumerate(lod.points)}
    for name, sel in lod.selections.items():
        pts_in_sel = []
        for pt, weight in sel.points.items():
            if weight > 0:
                idx = pt_idx.get(id(pt))
                if idx is None:
                    continue
                pts_in_sel.append(idx)
                point_to_selections.setdefault(idx, []).append(name)
        selection_point_map[name] = pts_in_sel

    for i, point in enumerate(lod.points):
        sels = point_to_selections.get(i, [])
        memory_points.append({
            "index": i,
            "position": list(point.coords),
            "selections": sels,
            "category": _recipe_classify_memory_point(sels),
            "label": sels[0] if sels else "point_%d" % i,
        })

    for name, pts in selection_point_map.items():
        if len(pts) == 2:
            p1 = list(lod.points[pts[0]].coords)
            p2 = list(lod.points[pts[1]].coords)
            direction = [p2[j] - p1[j] for j in range(3)]
            length = math.sqrt(sum(d * d for d in direction))
            if length > 1e-9:
                direction = [d / length for d in direction]
            axes[name] = {
                "points": [p1, p2],
                "point_indices": pts,
                "direction": direction,
                "length": length,
            }
    return memory_points, axes


def _recipe_guess_density(recipe):
    """Port de build.py:63-74."""
    paths = []
    refs = recipe.get("referenced_paths", {})
    paths.extend(refs.get("textures", []))
    paths.extend(refs.get("materials", []))
    blob = " ".join(paths).lower()
    for kw, d in _RECIPE_DENSITY_KEYWORDS:
        if kw in blob:
            return d
    return _RECIPE_DENSITY_DEFAULT


def _recipe_dedup_normals(per_vertex_normals):
    """Port de build.py:117-128."""
    pool = []
    lookup = {}
    index_map = []
    for n in per_vertex_normals:
        key = (round(n[0], 6), round(n[1], 6), round(n[2], 6))
        if key not in lookup:
            lookup[key] = len(pool)
            pool.append((float(n[0]), float(n[1]), float(n[2])))
        index_map.append(lookup[key])
    return pool, index_map


def _recipe_face_normal(positions, indices):
    """Port de build.py:286-300 (cross product, D8)."""
    try:
        p0, p1, p2 = (positions[indices[0]], positions[indices[1]],
                      positions[indices[2]])
        v1 = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
        v2 = (p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2])
        n = _v_cross(v1, v2)
        L = _v_norm(n) or 1.0
        return (n[0] / L, n[1] / L, n[2] / L)
    except (IndexError, TypeError):
        return (0.0, 1.0, 0.0)


def _recipe_build_selections(lod, selections_dict):
    """Port de build.py:397-407 (pesos -> 1; perdida scoped del schema)."""
    for sel_name, sel_data in selections_dict.items():
        sel = Selection(lod.points, lod.faces)
        for vi in sel_data.get("vertices", []):
            if 0 <= vi < len(lod.points):
                sel.points[lod.points[vi]] = 1
        for fi in sel_data.get("faces", []):
            if 0 <= fi < len(lod.faces):
                sel.faces[lod.faces[fi]] = 1
        lod.selections[sel_name] = sel


def _recipe_build_visual(lod_dict):
    """Port de build.py:152-212."""
    lod = LOD()
    lod.resolution = _RECIPE_LOD_RESOLUTION.get(
        lod_dict["type"], lod_dict.get("resolution", 0.0))
    geo = lod_dict.get("geometry", {})
    positions = geo.get("positions", [])
    normals = geo.get("normals", [])
    uvs = geo.get("uvs", [])
    material_groups = geo.get("material_groups", {})

    for pos in positions:
        pt = Point()
        pt.coords = (float(pos[0]), float(pos[1]), float(pos[2]))
        pt.flags = 0
        lod.points.append(pt)

    pool, normal_idx_map = _recipe_dedup_normals(normals)
    lod.facenormals = pool

    for key, indices in material_groups.items():
        if "|" in key:
            tex, mat = key.split("|", 1)
        else:
            tex, mat = key, ""
        for i in range(0, len(indices) - 2, 3):
            face = Face(lod.points, lod.facenormals)
            face.flags = 0
            face.texture = tex
            face.material = mat
            for vi in (indices[i], indices[i + 1], indices[i + 2]):
                vx = Vertex(lod.points, lod.facenormals)
                vx.point_index = vi
                vx.normal_index = (normal_idx_map[vi]
                                   if vi < len(normal_idx_map) else 0)
                if vi < len(uvs):
                    u, v = uvs[vi]
                    vx.uv = (float(u), 1.0 - float(v))  # des-flip glTF
                else:
                    vx.uv = (0.0, 0.0)
                face.vertices.append(vx)
            lod.faces.append(face)

    _recipe_build_selections(lod, lod_dict.get("selections", {}))
    for k, v in lod_dict.get("properties", {}).items():
        if not k.startswith("_"):
            lod.properties[str(k)] = str(v)
    return lod


def _recipe_assign_mass(lod, lod_dict, recipe):
    """Port de build.py:323-353 (override > meta > heuristica densidad)."""
    if not lod.points:
        return
    override = None
    if "_point_mass" in lod_dict.get("properties", {}):
        try:
            override = float(lod_dict["properties"]["_point_mass"])
        except (ValueError, TypeError):
            pass
    if override is None:
        meta_override = recipe.get("meta", {}).get("point_mass_default")
        if meta_override is not None:
            try:
                override = float(meta_override)
            except (ValueError, TypeError):
                pass
    if override is not None:
        per_point = override
    else:
        lo, hi, _center = lod.bbox()
        vol = max(1e-6, (hi[0] - lo[0]) * (hi[1] - lo[1]) * (hi[2] - lo[2]))
        per_point = max(0.1, vol * _recipe_guess_density(recipe)
                        / len(lod.points))
    for p in lod.points:
        p.mass = per_point


def _recipe_build_wireframe(lod_dict, lod_type, recipe):
    """Port de build.py:217-283.

    Divergencia documentada: el camino n-gon de build.py (303-320)
    desincroniza normal_index de las caras posteriores (bug latente,
    inalcanzable desde recipes del extractor — MLOD solo emite tri/quad);
    aqui los n-gons se triangulan con indices correctos.
    """
    lod = LOD()
    lod.resolution = _RECIPE_LOD_RESOLUTION.get(
        lod_type, lod_dict.get("resolution", 0.0))
    wf = lod_dict.get("wireframe", {})
    positions = wf.get("positions", [])
    faces_data = wf.get("faces", [])

    for pos in positions:
        pt = Point()
        pt.coords = (float(pos[0]), float(pos[1]), float(pos[2]))
        pt.flags = 0
        lod.points.append(pt)

    def _append_face(indices, normal_index):
        face = Face(lod.points, lod.facenormals)
        face.flags = 0
        face.texture = ""
        face.material = ""
        for pi in indices:
            vx = Vertex(lod.points, lod.facenormals)
            vx.point_index = int(pi)
            vx.normal_index = normal_index
            vx.uv = (0.0, 0.0)
            face.vertices.append(vx)
        lod.faces.append(face)

    for face_indices in faces_data:
        if len(face_indices) < 3:
            continue
        if len(face_indices) <= 4:
            lod.facenormals.append(_recipe_face_normal(positions,
                                                       face_indices))
            _append_face(face_indices, len(lod.facenormals) - 1)
        else:
            for i in range(1, len(face_indices) - 1):
                tri = [face_indices[0], face_indices[i], face_indices[i + 1]]
                lod.facenormals.append(_recipe_face_normal(positions, tri))
                _append_face(tri, len(lod.facenormals) - 1)

    if lod_type in _RECIPE_MASSED_TYPES:
        _recipe_assign_mass(lod, lod_dict, recipe)

    _recipe_build_selections(lod, lod_dict.get("selections", {}))
    for k, v in lod_dict.get("properties", {}).items():
        if not k.startswith("_"):
            lod.properties[str(k)] = str(v)

    if lod_type == "geometry":
        if "autocenter" not in lod.properties:
            lod.properties["autocenter"] = "0"
        if "class" not in lod.properties:
            lod.properties["class"] = "house"
    return lod


def _recipe_build_memory(recipe):
    """Port de build.py:358-392."""
    memory_points = recipe.get("memory_points", [])
    if not memory_points:
        return None
    lod = LOD()
    lod.resolution = _RECIPE_LOD_RESOLUTION["memory"]
    sorted_pts = sorted(memory_points, key=lambda m: m.get("index", 0))
    point_objs = []
    for mp in sorted_pts:
        pt = Point()
        pos = mp["position"]
        pt.coords = (float(pos[0]), float(pos[1]), float(pos[2]))
        pt.flags = 0
        point_objs.append(pt)
        lod.points.append(pt)
    sel_name_to_points = collections.OrderedDict()
    for i, mp in enumerate(sorted_pts):
        for sel_name in mp.get("selections", []):
            sel_name_to_points.setdefault(sel_name, []).append(point_objs[i])
    for sel_name, pts in sel_name_to_points.items():
        sel = Selection(lod.points, lod.faces)
        for p in pts:
            sel.points[p] = 1
        lod.selections[sel_name] = sel
    return lod


# ---------------------------------------------------------------------------
# S2 (F2-12): paridad DEPURADA con dayz-p3d-audit/scripts/audit_p3d.py.
#
# Checks portados (lista cerrada del plan): winding relativo cross-product
# (audit:104-171), Component01 naming/coverage (174-208), autocenter
# (211-219), watertight (222-234), caras degeneradas (237-253), estructura
# Memory (256-307), ejes<->selections (310-330) y paths P:\ en caras
# (333-342). check_required_lods NO se porta (vive en el audit con sus ids
# normalizados); el check de centroide absoluto queda RETIRADO (D8).
#
# Depuracion aplicada respecto al audit original:
#   - ids modernos DayZ: la clase "colision" = geometry/view_geometry/
#     fire_geometry (el slot GeoPhys/2e13 del audit era stale);
#   - autocenter solo se exige en el Geometry LOD (en el audit corria
#     tambien sobre FireGeo por arrastre del bucle GeoPhys-era);
#   - el LOD visual de referencia para winding es el PRIMERO en orden de
#     archivo (el audit usaba el ultimo por sobreescritura accidental);
#   - severidades: CRITICAL->ERROR, WARNING->WARN; los NOTE informativos
#     no se portan, salvo paths P:\ (en la lista del plan) y la rama
#     low-confidence del winding (parte del check portado).
#
# Codigos v1.2.0 (este bloque):
#   ERR_WINDING_INVERTED, WARN_WINDING_MIXED, WARN_WINDING_LOWCONF,
#   ERR_COMPONENT_NAMING, WARN_COMPONENT_NAMING, WARN_COMPONENT_COVERAGE,
#   WARN_AUTOCENTER_MISSING, WARN_NOT_WATERTIGHT, WARN_DEGENERATE_FACES,
#   WARN_MEMORY_POS_CENTER, WARN_MEMORY_BOX_PLACING, ERR_MEMORY_AXIS_POINTS,
#   WARN_MEMORY_AXIS_SHORT, WARN_MEMORY_HAS_FACES,
#   ERR_AXIS_SELECTION_MISSING, WARN_AXIS_SELECTION_EMPTY,
#   WARN_PDRIVE_PATH, WARN_LOD_KIND_UNKNOWN.


def _pct_outward(lod):
    """Port de audit_p3d.check_winding_vs_visual.pct_outward (117-144)."""
    if len(lod.points) == 0 or len(lod.faces) == 0:
        return None
    n = len(lod.points)
    cx = sum(p.coords[0] for p in lod.points) / n
    cy = sum(p.coords[1] for p in lod.points) / n
    cz = sum(p.coords[2] for p in lod.points) / n
    out = 0
    tot = 0
    for face in lod.faces:
        verts = face.vertices
        if len(verts) < 3:
            continue
        v = [vx.point.coords for vx in verts]
        e1 = _v_sub(v[1], v[0])
        e2 = _v_sub(v[2], v[0])
        nx, ny, nz = _v_cross(e1, e2)
        fx = sum(c[0] for c in v) / len(v)
        fy = sum(c[1] for c in v) / len(v)
        fz = sum(c[2] for c in v) / len(v)
        dot = nx * (fx - cx) + ny * (fy - cy) + nz * (fz - cz)
        tot += 1
        if dot > 0:
            out += 1
    if tot == 0:
        return None
    return 100.0 * out / tot


def _pct_normal_agreement(lod):
    r"""F4-01 senal B: % de caras cuyo winding concuerda con su normal
    DECLARADA.

    `cross(e1,e2) . normal_declarada` con AMBOS vectores en el mismo
    espacio. Por eso no depende del handedness: el lio left-handed (DayZ)
    vs right-handed (Three.js) se cancela en el producto, y no hay ningun
    signo que "corregir" segun el motor.

    Es la senal que `_pct_outward` no puede dar: aquella compara contra el
    centroide del LOD, que (a) asume convexidad y (b) es invariante a
    invertir el modelo ENTERO -- por eso el bug Z-up -> Y-up era invisible.

    Devuelve None si ninguna cara es evaluable. Las caras degeneradas y las
    de normal nula NO votan: un check que opina sin datos es peor que uno
    que calla.
    """
    if len(lod.faces) == 0:
        return None
    agree = 0
    tot = 0
    for face in lod.faces:
        verts = face.vertices
        if len(verts) < 3:
            continue
        v = [vx.point.coords for vx in verts]
        cx, cy, cz = _v_cross(_v_sub(v[1], v[0]), _v_sub(v[2], v[0]))
        if cx == 0.0 and cy == 0.0 and cz == 0.0:
            continue
        normal = verts[0].normal
        if normal is None:
            continue
        nx, ny, nz = normal
        if nx == 0.0 and ny == 0.0 and nz == 0.0:
            continue
        dot = cx * nx + cy * ny + cz * nz
        if dot == 0.0:
            continue
        tot += 1
        if dot > 0:
            agree += 1
    if tot == 0:
        return None
    return 100.0 * agree / tot


def _pct_edge_coherence(lod):
    r"""F4-01 senal A: % de aristas compartidas recorridas en sentidos
    opuestos por sus dos caras.

    Puramente topologica: ni centroides, ni normales, ni convexidad. En una
    superficie orientable bien construida el valor es 100%. Localiza ademas
    QUE caras discrepan, cosa que una media global no puede.

    Solo puntua aristas usadas por EXACTAMENTE dos caras; los bordes
    abiertos y las aristas non-manifold son asunto de _check_watertight.
    Devuelve None si no hay ninguna arista compartida que evaluar.
    """
    if len(lod.faces) == 0:
        return None
    use = {}
    for face in lod.faces:
        verts = face.vertices
        n = len(verts)
        if n < 3:
            continue
        for i in range(n):
            a = verts[i].point_index
            b = verts[(i + 1) % n].point_index
            if a == b:
                continue
            key = (a, b) if a < b else (b, a)
            use.setdefault(key, []).append(1 if a < b else -1)
    tot = 0
    good = 0
    for dirs in use.values():
        if len(dirs) != 2:
            continue
        tot += 1
        if dirs[0] != dirs[1]:
            good += 1
    if tot == 0:
        return None
    return 100.0 * good / tot


def _check_winding_absolute(lod, lod_index, kind_label):
    r"""F4-01 (council 2026-08-12): winding ABSOLUTO de un LOD, sin
    compararlo con ningun otro.

    Cierra el falso negativo que motivo el fork: `_check_winding_vs_visual`
    es RELATIVO al Visual, asi que invertir TODOS los LODs dejaba el modelo
    coherente consigo mismo y `validate()` devolvia [] -- justo el estado
    que produce un export Blender Z-up -> Y-up sin invertir el orden de
    vertices.

    Aditivo: codigos nuevos, no toca los de `_check_winding_vs_visual`.
    """
    findings = []
    pct = _pct_normal_agreement(lod)
    if pct is None:
        findings.append(Finding(
            "WARN_WINDING_UNVERIFIABLE", "WARN", lod_index,
            "%s LOD: winding could not be verified - no face has both a "
            "non-degenerate winding and a non-degenerate declared normal."
            % kind_label))
    elif pct < 10.0:
        findings.append(Finding(
            "ERR_WINDING_VS_NORMALS", "ERROR", lod_index,
            "%s LOD winding contradicts its own declared normals (only "
            "%.0f%% agree). Every face is wound backwards while its normal "
            "still points outward: the signature of a Z-up -> Y-up export "
            "that changed handedness without reordering vertices. The "
            "texture will only be visible from INSIDE and raycasts from "
            "outside pass through. Fix: face.vertices.reverse() on every "
            "face of this LOD." % (kind_label, pct)))
    elif pct <= 90.0:
        findings.append(Finding(
            "WARN_WINDING_NORMAL_MISMATCH", "WARN", lod_index,
            "%s LOD: only %.0f%% of faces agree with their own declared "
            "normal - winding is not internally consistent."
            % (kind_label, pct)))
    edge = _pct_edge_coherence(lod)
    if edge is not None and edge < 100.0:
        findings.append(Finding(
            "WARN_WINDING_EDGE_INCOHERENT", "WARN", lod_index,
            "%s LOD: only %.0f%% of shared edges are traversed in opposite "
            "directions by their two faces (100%% expected on an orientable "
            "surface) - neighbouring faces disagree on which side is out."
            % (kind_label, edge)))
    return findings


def _check_winding_vs_visual(lod, lod_index, visual_lod, kind_label):
    """Port depurado de audit_p3d.check_winding_vs_visual (104-171).

    OJO (F4-01): este check es RELATIVO al Visual LOD y se apoya en
    `_pct_outward`, que asume geometria convexa. NO puede detectar una
    inversion global ni distinguir una caja hueca correcta de una rota.
    Se conserva por compatibilidad de codigos; la senal que si discrimina
    es `_check_winding_absolute`.
    """
    findings = []
    col = _pct_outward(lod)
    vis = _pct_outward(visual_lod)
    if col is None or vis is None:
        return findings
    col_uniform = col > 90 or col < 10
    vis_uniform = vis > 90 or vis < 10
    col_dom = "outward" if col >= 50 else "inward"
    vis_dom = "outward" if vis >= 50 else "inward"
    if col_uniform and vis_uniform and col_dom != vis_dom:
        findings.append(Finding(
            "ERR_WINDING_INVERTED", "ERROR", lod_index,
            "%s LOD winding is INVERTED relative to the Visual LOD "
            "(%s=%s %.0f%%-outward vs Visual=%s %.0f%%-outward). Raycasts "
            "from outside pass through -> no collision / no action / no "
            "ballistic hits. Fix: face.vertices.reverse() on every face of "
            "this LOD (do NOT swap vertices[1] and vertices[2]: that "
            "inverts a triangle but turns a quad [0,1,2,3] into [0,2,1,3], "
            "a CROSSED face)."
            % (kind_label, kind_label, col_dom, col, vis_dom, vis)))
    elif not col_uniform:
        findings.append(Finding(
            "WARN_WINDING_MIXED", "WARN", lod_index,
            "%s LOD winding is MIXED (%.0f%%-outward) - not internally "
            "consistent; raycasts will be unreliable."
            % (kind_label, col)))
    elif not vis_uniform:
        findings.append(Finding(
            "WARN_WINDING_LOWCONF", "WARN", lod_index,
            "Visual LOD winding is mixed (%.0f%%-outward) so the relative "
            "winding check for the %s LOD is low-confidence."
            % (vis, kind_label)))
    return findings


def _check_component_naming(lod, lod_index):
    """Port de audit_p3d.check_component_naming (174-191)."""
    findings = []
    sels = list(lod.selections.keys())
    has_correct = "Component01" in sels
    has_lowercase = "component01" in sels
    has_any = any(s.lower().startswith("component") for s in sels)
    if has_lowercase and not has_correct:
        findings.append(Finding(
            "ERR_COMPONENT_NAMING", "ERROR", lod_index,
            "Found 'component01' (lowercase). Engine requires "
            "'Component01' (uppercase C); collision silently fails."))
    elif not has_any:
        findings.append(Finding(
            "ERR_COMPONENT_NAMING", "ERROR", lod_index,
            "No Component selection found. Geometry LOD requires "
            "'Component01' for collision."))
    elif not has_correct:
        found = [s for s in sels if s.lower().startswith("component")]
        findings.append(Finding(
            "WARN_COMPONENT_NAMING", "WARN", lod_index,
            "Component selection %r - verify exact case is 'Component01'."
            % found[0]))
    return findings


def _check_component_coverage(lod, lod_index):
    """Port de audit_p3d.check_component_coverage (194-208)."""
    findings = []
    if "Component01" not in lod.selections:
        return findings
    sel = lod.selections["Component01"]
    if len(sel.points) < len(lod.points):
        findings.append(Finding(
            "WARN_COMPONENT_COVERAGE", "WARN", lod_index,
            "Component01 covers %d/%d vertices; uncovered vertices won't "
            "participate in collision."
            % (len(sel.points), len(lod.points))))
    if len(sel.faces) < len(lod.faces):
        findings.append(Finding(
            "WARN_COMPONENT_COVERAGE", "WARN", lod_index,
            "Component01 covers %d/%d faces; uncovered faces won't "
            "register raycasts." % (len(sel.faces), len(lod.faces))))
    return findings


def _check_autocenter(lod, lod_index):
    """Port de audit_p3d.check_autocenter_prop (211-219), solo Geometry."""
    if "autocenter" not in lod.properties:
        return [Finding(
            "WARN_AUTOCENTER_MISSING", "WARN", lod_index,
            "Missing 'autocenter=0' LOD property. For Inventory_Base items "
            "with autocenter=0 in config.cpp it must ALSO be in the LOD.")]
    return []


def _check_watertight(lod, lod_index):
    """Port de audit_p3d.check_watertight (222-234)."""
    edge_count = {}
    for face in lod.faces:
        pts = [id(v.point) for v in face.vertices]
        for j in range(len(pts)):
            edge = tuple(sorted([pts[j], pts[(j + 1) % len(pts)]]))
            edge_count[edge] = edge_count.get(edge, 0) + 1
    boundary = sum(1 for c in edge_count.values() if c == 1)
    if boundary > 0:
        return [Finding(
            "WARN_NOT_WATERTIGHT", "WARN", lod_index,
            "%d boundary edges - mesh not watertight (has holes)."
            % boundary)]
    return []


def _check_degenerate_faces(lod, lod_index):
    """Port de audit_p3d.check_degenerate_faces (237-253)."""
    degen = 0
    for face in lod.faces:
        verts = face.vertices
        if len(verts) < 3:
            degen += 1
            continue
        v = [vx.point.coords for vx in verts]
        n = _v_cross(_v_sub(v[1], v[0]), _v_sub(v[2], v[0]))
        if _v_norm(n) < 1e-8:
            degen += 1
    if degen > 0:
        return [Finding(
            "WARN_DEGENERATE_FACES", "WARN", lod_index,
            "%d degenerate (zero-area) faces won't register collision."
            % degen)]
    return []


def _check_memory_structure(lod, lod_index):
    """Port de audit_p3d.check_memory_lod (256-307), sin los NOTE."""
    findings = []
    sels = list(lod.selections.keys())
    if "pos center" not in sels:
        findings.append(Finding(
            "WARN_MEMORY_POS_CENTER", "WARN", lod_index,
            "Missing 'pos center' memory point; engine auto-calculates "
            "bounding center (wrong for tall/asymmetric objects)."))
    has_min = "box_placing_min" in sels
    has_max = "box_placing_max" in sels
    if has_min != has_max:
        findings.append(Finding(
            "WARN_MEMORY_BOX_PLACING", "WARN", lod_index,
            "Only one of box_placing_min/max found; both are needed for "
            "hologram placement."))
    if "flag_mast_axis" in lod.selections:
        sel = lod.selections["flag_mast_axis"]
        if len(sel.points) != 2:
            findings.append(Finding(
                "ERR_MEMORY_AXIS_POINTS", "ERROR", lod_index,
                "flag_mast_axis has %d points, MUST have exactly 2 (start "
                "and end of the translation axis)." % len(sel.points)))
        else:
            pts = list(sel.points.keys())
            dy = abs(pts[0].coords[1] - pts[1].coords[1])
            if dy < 0.1:
                findings.append(Finding(
                    "WARN_MEMORY_AXIS_SHORT", "WARN", lod_index,
                    "flag_mast_axis points have only %.3fm Y separation - "
                    "animation travel may be too small." % dy))
    if len(lod.faces) > 0:
        findings.append(Finding(
            "WARN_MEMORY_HAS_FACES", "WARN", lod_index,
            "Memory LOD has %d faces - should have 0 (only single-vertex "
            "points belong here)." % len(lod.faces)))
    return findings


def _check_axis_selections(memory_lod, visual_lod, visual_index):
    """Port de audit_p3d.check_visual_lod (316-330): eje *_axis en Memory
    exige selection homonima (sin sufijo) con vertices en el Visual."""
    findings = []
    vis_sels = visual_lod.selections
    for ms in memory_lod.selections.keys():
        if not ms.endswith("_axis"):
            continue
        anim_name = ms[:-len("_axis")]
        if anim_name not in vis_sels:
            findings.append(Finding(
                "ERR_AXIS_SELECTION_MISSING", "ERROR", visual_index,
                "Memory LOD has %r axis but Visual LOD is missing the %r "
                "selection - animation will silently do nothing."
                % (ms, anim_name)))
        elif len(vis_sels[anim_name].points) == 0:
            findings.append(Finding(
                "WARN_AXIS_SELECTION_EMPTY", "WARN", visual_index,
                "Visual LOD selection %r has 0 vertices - nothing will "
                "animate." % anim_name))
    return findings


def _check_pdrive_faces(lod, lod_index):
    """Port de audit_p3d.check_visual_lod (333-342): paths P:\\ en caras."""
    count = 0
    for face in lod.faces:
        if face.texture and face.texture.upper().startswith("P:\\"):
            count += 1
        if face.material and face.material.upper().startswith("P:\\"):
            count += 1
    if count > 0:
        return [Finding(
            "WARN_PDRIVE_PATH", "WARN", lod_index,
            "%d face texture/material references use absolute P:\\ paths - "
            "they break on distribution (usually OK for MLOD source)."
            % count)]
    return []


def _lod_has_mass_tagg(lod):
    """F3-01: True si el LOD emitira tagg #Mass# al escribir (LL-080).

    Espejo del pseudocodigo dayz-p3d-audit/SKILL.md:548-552. NO usar el
    property LOD.mass como predicado: con masa PARCIAL (mezcla 0.0/None)
    sum() lanza TypeError (R22-P1-01).
    """
    return any(p.mass is not None for p in lod.points)


def _check_mass_only_geometry(lod, lod_index):
    """F3-01 (BUG-021): tagg #Mass# fuera del Geometry LOD -> ERROR.

    Observado in-game en un quad custom: un #Mass# espurio en un LOD
    no-Geometry (aunque todos los valores sean 0.0) hace que binarize/
    AddonBuilder hornee la masa de ESE LOD -> ODOL con CoM=(0,0,0) e
    inercia 0 -> ECE_PLACE_ON_SURFACE spawnea bajo tierra. Spec:
    dayz-p3d-audit/SKILL.md:522-557. Aplica a TODO kind != "geometry",
    incluida resolucion desconocida (kind None, D-S3-3).
    """
    if lod.kind() == "geometry":
        return []
    if not _lod_has_mass_tagg(lod):
        return []
    count = sum(1 for p in lod.points if p.mass is not None)
    return [Finding(
        "ERR_MASS_ONLY_GEOMETRY", "ERROR", lod_index,
        "LOD kind=%s res=%g carries a #Mass# tagg (%d point(s) with "
        "non-None mass) - #Mass# must live ONLY in the Geometry LOD. "
        "binarize bakes THIS LOD's mass -> CoM=(0,0,0), zero inertia, "
        "below-ground spawn. FIX: set point.mass = None (never 0.0); "
        "py3d emits #Mass# if ANY point.mass is not None."
        % (lod.kind() or "unknown", lod.resolution, count))]


class Finding:
    """F1-09: resultado de P3D.validate(). severity: "ERROR" | "WARN"."""

    def __init__(self, code, severity, lod, msg):
        self.code = code
        self.severity = severity
        self.lod = lod  # indice de LOD, o None si es global
        self.msg = msg

    def __repr__(self):
        return "Finding(%r, %r, lod=%r, %r)" % (
            self.code, self.severity, self.lod, self.msg)


class Point:
    def __init__(self, f=None):
        self.coords = (0,0,0)
        self.flags = 0
        self.mass = None
        if f is not None:
            self.read(f)

    def read(self, f):
        self.coords = struct.unpack("fff", f.read(12))
        self.flags = struct.unpack("<L", f.read(4))[0]

    def write(self, f):
        f.write(struct.pack("fff", *self.coords))
        f.write(struct.pack("<L", self.flags))


class Vertex:
    def __init__(self, all_points, all_normals, f=None):
        self.all_points = all_points
        self.all_normals = all_normals
        self.point_index = None
        self.normal_index = None
        self.uv = (0, 0)
        # Additional UV sets keyed by set id (1, 2, ...). Set 0 is `uv`,
        # stored inline in the face record; the other sets only exist in the
        # LOD's #UVSet# tags and are re-emitted by LOD.write in id order.
        self.uv_sets = {}
        if f is not None:
            self.read(f)

    @property
    def point(self):
        return self.all_points[self.point_index]

    @point.setter
    def point(self, value):
        self.point_index = self.all_points.index(value)

    @property
    def normal(self):
        return self.all_normals[self.normal_index]

    @normal.setter
    def normal(self, value):
        self.normal_index = self.all_normals.index(value)

    def read(self, f):
        self.point_index = struct.unpack("<L", f.read(4))[0]
        self.normal_index = struct.unpack("<L", f.read(4))[0]
        self.uv = struct.unpack("ff", f.read(8))

    def write(self, f):
        f.write(struct.pack("<L", self.point_index))
        f.write(struct.pack("<L", self.normal_index))
        f.write(struct.pack("ff", *self.uv))


class Face:
    def __init__(self, all_points, all_normals, f=None):
        self.all_points = all_points
        self.all_normals = all_normals
        self.vertices = []
        self.flags = 0
        self.texture = ""
        self.material = ""
        if f is not None:
            self.read(f)

    def read(self, f):
        num_vertices = struct.unpack("<L", f.read(4))[0]
        assert num_vertices in (3,4)

        self.vertices = [Vertex(self.all_points, self.all_normals, f) for i in range(num_vertices)]

        if num_vertices == 3:
            f.seek(16, 1)

        self.flags = struct.unpack("<L", f.read(4))[0]
        self.texture = _read_asciiz(f)
        self.material = _read_asciiz(f)

    def write(self, f):
        f.write(struct.pack("<L", len(self.vertices)))
        for v in self.vertices:
            v.write(f)
        if len(self.vertices) == 3:
            f.write(b"\0" * 16)
        f.write(struct.pack("<L", self.flags))
        f.write(bytes(self.texture, encoding="utf-8") + b"\0")
        f.write(bytes(self.material, encoding="utf-8") + b"\0")


class Selection:
    def __init__(self, all_points=_REQUIRED, all_faces=_REQUIRED, f=None):
        if all_points is _REQUIRED or all_faces is _REQUIRED:
            # F1-01: upstream's positional signature already made the no-arg
            # form a TypeError; the fork freezes that behaviour with an
            # actionable message instead of a bare signature error.
            raise TypeError(
                "Selection() requires the owning LOD's lists: "
                "Selection(lod.points, lod.faces). Prefer "
                "lod.new_selection(name), which binds and registers the "
                "selection correctly."
            )
        self.all_points = all_points
        self.all_faces = all_faces
        self.points = {}
        self.faces = {}
        if f is not None:
            self.read(f)

    @staticmethod
    def _normalize_weight(value, kind, name):
        """F1-02: validate/normalize a selection weight at write time.

        Accepted: int 0/1, float exactly 0.0/1.0 (coerced to int), float
        strictly between 0 and 1 (upstream fractional encoding). Anything
        else raised upstream as a cryptic late TypeError inside bytes() -
        here it is an early ValueError naming the selection.
        """
        label = "'%s'" % name if name is not None else "<unnamed>"
        if isinstance(value, float) and value in (0.0, 1.0):
            return int(value)
        if isinstance(value, int):  # bool is a valid int subclass here
            if value in (0, 1):
                return value
            raise ValueError(
                "selection %s: invalid %s weight %r - int weights must be "
                "0 or 1" % (label, kind, value))
        if isinstance(value, float):
            if 0.0 < value < 1.0:
                return value
            raise ValueError(
                "selection %s: invalid %s weight %r - float weights must "
                "be strictly between 0 and 1 (or exactly 0.0/1.0, coerced "
                "to int)" % (label, kind, value))
        raise ValueError(
            "selection %s: invalid %s weight %r - expected int 0/1 or "
            "float in (0, 1)" % (label, kind, value))

    def read(self, f):
        num_bytes = struct.unpack("<L", f.read(4))[0]

        data_points = f.read(len(self.all_points))
        data_faces = f.read(len(self.all_faces))

        self.points = {p: (lambda weight: weight if weight <= 1 else 1 - ((weight - 1) / 255))(data_points[i]) for i, p in enumerate(self.all_points) if data_points[i] > 0}
        self.faces = {fa: (lambda weight: weight if weight <= 1 else 1 - ((weight - 1) / 255))(data_faces[i]) for i, fa in enumerate(self.all_faces) if data_faces[i] > 0}

    def write(self, f, name=None):
        label = "'%s'" % name if name is not None else "<unnamed>"
        # F1-02: validate weights up-front (does not mutate user dicts).
        points = {p: self._normalize_weight(w, "point", name)
                  for p, w in self.points.items()}
        faces = {fa: self._normalize_weight(w, "face", name)
                 for fa, w in self.faces.items()}

        # F1-05: keys deben pertenecer POR IDENTIDAD a las listas bindeadas;
        # si no, su peso se serializaria como 0 en silencio (R22-P1-03).
        point_ids = set(map(id, self.all_points))
        face_ids = set(map(id, self.all_faces))
        for p in points:
            if id(p) not in point_ids:
                raise RuntimeError(
                    "selection %s: foreign Point key not present (by "
                    "identity) in the bound all_points - its weight would "
                    "be silently dropped. Did it come from another LOD or "
                    "a rebuilt list?" % label)
        for fa in faces:
            if id(fa) not in face_ids:
                raise RuntimeError(
                    "selection %s: foreign Face key not present (by "
                    "identity) in the bound all_faces - its weight would "
                    "be silently dropped. Did it come from another LOD or "
                    "a rebuilt list?" % label)

        f.write(struct.pack("<L", len(self.all_points) + len(self.all_faces)))

        data_points = [(lambda weight: weight if weight in (1,0) else round((1 - weight) * 255) + 1)(points[p]) if p in points else 0 for p in self.all_points]
        f.write(bytes(data_points))

        data_faces = [(lambda weight: weight if weight in (1,0) else round((1 - weight) * 255) + 1)(faces[fa]) if fa in faces else 0 for fa in self.all_faces]
        f.write(bytes(data_faces))


class LOD:
    def __init__(self, f=None):
        self.version_major = 28
        self.version_minor = 256
        self.resolution = 1.0
        self.points = []
        self.facenormals = []
        self.faces = []
        self.sharp_edges = []
        # Ids of #UVSet# tags belonging to a LOD without faces (Memory,
        # LandContact). There are no face vertices to hang them on, so they
        # are kept here and written back as the bare 4-byte id. Set 0 is
        # always written and is not listed.
        self.faceless_uv_sets = []
        self.properties = collections.OrderedDict()
        self.selections = collections.OrderedDict()
        if f is not None:
            self.read(f)

    @property
    def mass(self):
        masses = [x.mass for x in self.points]
        if len([x for x in masses if x is not None]) == 0:
            return None

        return sum(masses)

    @property
    def num_vertices(self):
        return sum([len(x.vertices) for x in self.faces])

    def uv_set_ids(self):
        """Sorted ids of the UV sets write() emits for this LOD: always 0
        (the uv carried by the face vertices) plus every id found in
        `Vertex.uv_sets` and in `faceless_uv_sets`. Set 0 lives in
        `Vertex.uv`; any other id must be an integer in 1..2**32-1,
        otherwise ValueError.
        """
        ids = set(self.faceless_uv_sets)
        for fa in self.faces:
            for v in fa.vertices:
                ids.update(v.uv_sets)
        for uv_id in ids:
            if isinstance(uv_id, bool) or not isinstance(uv_id, int) \
                    or not 1 <= uv_id <= 0xFFFFFFFF:
                raise ValueError(
                    "Vertex.uv_sets: invalid UV set id %r (set 0 is "
                    "Vertex.uv; other ids must be integers in 1..2**32-1)"
                    % (uv_id,))
        return [0] + sorted(ids)

    def new_selection(self, name):
        """F1-01 helper (fork API): get-or-create a selection correctly
        bound to this LOD's point/face lists and registered under *name*.
        """
        existing = self.selections.get(name)
        if existing is not None:
            return existing
        sel = Selection(self.points, self.faces)
        self.selections[name] = sel
        return sel

    def faces_by_material(self, lower=True):
        """F1-03: dict material -> [Face]. Claves en lower() por defecto
        (DayZ almacena lowercase; el tooling emite UPPER/MixedCase)."""
        out = collections.OrderedDict()
        for fa in self.faces:
            key = fa.material.lower() if lower else fa.material
            out.setdefault(key, []).append(fa)
        return out

    def faces_for_material(self, name):
        """F1-03: caras cuyo material coincide case-insensitive con *name*."""
        want = name.lower()
        return [fa for fa in self.faces if fa.material.lower() == want]

    def set_memory_point(self, name, coords):
        """F1-04 (API NUEVA del fork): upsert de un memory point.

        Contrato real MLOD: punto en el LOD + selection de 1 punto con su
        nombre. Idempotente por nombre: si la selection existe, mueve su
        primer punto a *coords* y COLAPSA la membership a exactamente 1
        (duplicados pre-existentes incluidos); nunca anade entradas
        duplicadas. Los puntos huerfanos que pudiera dejar un duplicado
        colapsado NO se eliminan de lod.points (eliminar puntos
        reindexaria caras/selections ajenas); quedan sin seleccion.
        """
        coords = tuple(coords)
        sel = self.selections.get(name)
        if sel is not None:
            members = [p for p in self.points if id(p) in set(map(id, sel.points))]
            if members:
                keep = members[0]
                keep.coords = coords
                sel.points = {keep: 1}
                sel.faces = {}
                return keep
        p = Point()
        p.coords = coords
        self.points.append(p)
        if sel is None:
            sel = Selection(self.points, self.faces)
            self.selections[name] = sel
        sel.points = {p: 1}
        sel.faces = {}
        return p

    def get_memory_points(self):
        """F1-04: {nombre: coords} de cada selection de exactamente 1 punto
        y 0 caras (la forma canonica de un memory point)."""
        out = collections.OrderedDict()
        for name, sel in self.selections.items():
            if len(sel.points) == 1 and len(sel.faces) == 0:
                p = next(iter(sel.points))
                out[name] = p.coords
        return out

    def kind(self):
        """F2-01: kind canonico DayZ de este LOD, o None si la resolucion
        no es reconocida (p.ej. ids legacy Arma 3 2e13/3e13/7e13 -
        validate() lo reporta como WARN_LOD_KIND_UNKNOWN)."""
        return classify_lod_resolution(self.resolution)

    def bbox(self):
        """F2-02: ((minx,miny,minz), (maxx,maxy,maxz), centro).

        LOD sin puntos -> ValueError (un bbox (0,0,0) silencioso
        enmascara modelos vacios).
        """
        if not self.points:
            raise ValueError("bbox(): LOD has no points")
        xs = [p.coords[0] for p in self.points]
        ys = [p.coords[1] for p in self.points]
        zs = [p.coords[2] for p in self.points]
        lo = (min(xs), min(ys), min(zs))
        hi = (max(xs), max(ys), max(zs))
        center = ((lo[0] + hi[0]) / 2.0, (lo[1] + hi[1]) / 2.0,
                  (lo[2] + hi[2]) / 2.0)
        return lo, hi, center

    def triangulate(self):
        """F2-03: triangulacion fan in-place de los quads (quad -> 2 tris).

        Preserva UVs y normal_index por vertice, remapea la membership de
        TODAS las selections (quad -> sus 2 tris, mismo peso) y no toca
        lod.points/facenormals/sharp_edges (los indices de punto no
        cambian). Mutacion in-place de lod.faces: los bindings de las
        selections (F1-05) siguen validos. Devuelve nº de quads divididos.
        """
        quad_map = {}
        new_faces = []
        split = 0
        for fa in self.faces:
            if len(fa.vertices) != 4:
                new_faces.append(fa)
                continue
            v = fa.vertices
            tris = []
            for idxs in ((0, 1, 2), (0, 2, 3)):
                t = Face(self.points, self.facenormals)
                t.flags = fa.flags
                t.texture = fa.texture
                t.material = fa.material
                for i in idxs:
                    nv = Vertex(self.points, self.facenormals)
                    nv.point_index = v[i].point_index
                    nv.normal_index = v[i].normal_index
                    nv.uv = v[i].uv
                    nv.uv_sets = dict(v[i].uv_sets)
                    t.vertices.append(nv)
                tris.append(t)
            quad_map[id(fa)] = tris
            new_faces.extend(tris)
            split += 1
        if split == 0:
            return 0
        self.faces[:] = new_faces
        for sel in self.selections.values():
            if not sel.faces:
                continue
            remapped = {}
            for fa, w in sel.faces.items():
                for t in quad_map.get(id(fa), (fa,)):
                    remapped[t] = w
            sel.faces = remapped
        return split

    def make_double_sided(self):
        """F3-03: duplica cada cara con orden de vertices invertido y
        normal negada (twins) - para LODs VISUALES (flags, foliage,
        cloth visibles por ambos lados sin shader two-sided).

        Solo kind()=="visual"; otros LODs -> ValueError sin tocar nada
        (double-sided en Geometry/colision rompe la fisica). Los twins
        heredan flags/texture/material y uv (en orden inverso) y la
        membership (mismo peso) de cada selection que contenia la cara
        original. Puntos y sharp_edges no cambian; el pool de normales
        crece solo en negadas nuevas (dedup por igualdad exacta de
        tupla). NO idempotente: dos llamadas cuadruplican. Orden
        garantizado con triangulate(): primero make_double_sided(),
        despues triangulate() (el inverso no se testea). Referencia
        original (make_double_sided.py, outputs 2026-04) perdida;
        contrato fijado por plan S3 2026-06-07. Devuelve el numero de
        caras anadidas.
        """
        kind = self.kind()
        if kind != "visual":
            raise ValueError(
                "make_double_sided(): only visual LODs (kind()=%r)" % kind)
        pool_index = {}
        for idx, n in enumerate(self.facenormals):
            pool_index.setdefault(tuple(n), idx)
        neg_cache = {}

        def negated_index(old_index):
            if old_index in neg_cache:
                return neg_cache[old_index]
            n = self.facenormals[old_index]
            neg = (-n[0], -n[1], -n[2])
            idx = pool_index.get(neg)
            if idx is None:
                self.facenormals.append(neg)
                idx = len(self.facenormals) - 1
                pool_index[neg] = idx
            neg_cache[old_index] = idx
            return idx

        originals = list(self.faces)
        twins = {}
        for face in originals:
            twin = Face(self.points, self.facenormals)
            twin.flags = face.flags
            twin.texture = face.texture
            twin.material = face.material
            for v in reversed(face.vertices):
                tv = Vertex(self.points, self.facenormals)
                tv.point_index = v.point_index
                tv.normal_index = negated_index(v.normal_index)
                tv.uv = v.uv
                tv.uv_sets = dict(v.uv_sets)
                twin.vertices.append(tv)
            self.faces.append(twin)
            twins[id(face)] = twin
        for sel in self.selections.values():
            if not sel.faces:
                continue
            additions = {}
            for fa, w in sel.faces.items():
                tw = twins.get(id(fa))
                if tw is not None:
                    additions[tw] = w
            sel.faces.update(additions)
        return len(originals)

    def set_selection(self, name, face_idx=None, point_idx=None, weight=1):
        """F2-04: define la selection *name* por INDICES (overwrite
        idempotente: reemplaza la membership completa, nunca duplica).

        weight invalido -> ValueError (mismo guard F1-02, validado aqui
        ANTES de mutar). Indice fuera de rango -> IndexError con contexto.
        """
        Selection._normalize_weight(weight, "selection", name)
        face_idx = list(face_idx or ())
        point_idx = list(point_idx or ())
        for i in point_idx:
            if not 0 <= i < len(self.points):
                raise IndexError(
                    "set_selection(%r): point index %d out of range "
                    "(LOD has %d points)" % (name, i, len(self.points)))
        for i in face_idx:
            if not 0 <= i < len(self.faces):
                raise IndexError(
                    "set_selection(%r): face index %d out of range "
                    "(LOD has %d faces)" % (name, i, len(self.faces)))
        sel = self.new_selection(name)
        sel.points = {self.points[i]: weight for i in point_idx}
        sel.faces = {self.faces[i]: weight for i in face_idx}
        return sel

    def set_total_mass(self, kg):
        """F2-05: reparte *kg* uniformemente entre los puntos de ESTE LOD
        (llamalo sobre el Geometry LOD, que es donde el engine lee #Mass#).

        LOD sin puntos o kg negativo -> ValueError.
        """
        kg = float(kg)
        if kg < 0:
            raise ValueError("set_total_mass(): mass must be >= 0")
        if not self.points:
            raise ValueError("set_total_mass(): LOD has no points")
        per_point = kg / len(self.points)
        for p in self.points:
            p.mass = per_point
        return per_point

    def add_proxy(self, path, index=1, origin=(0.0, 0.0, 0.0),
                  rotation=None, scale=0.001, space="raw"):
        """F2-06: anade un proxy MLOD canonico (triangulo inambiguo de
        proxy_frame.py:54-61) como selection 'proxy:<path>.<index %03d>'.

        *rotation*: filas (x, y, z) local->world (identidad si None) -
        identidad == item mostrado upright en espacio personaje (worn).
        Nombre duplicado -> ValueError (sin upsert silencioso de
        geometria). Devuelve el nombre de la selection creada.
        """
        path, index = _validate_proxy_path_index(path, index)
        tri = canonical_proxy_triangle(origin, rotation, scale, space)
        name = "proxy:%s.%03d" % (path, index)
        if PROXY_NAME_RE.match(name) is None:
            raise ValueError(
                "add_proxy: composed name does not match proxy contract"
            )
        if name in self.selections:
            raise ValueError(
                "add_proxy: selection %r already exists - remove it first "
                "or use a different index" % name)
        base = len(self.points)
        for c in tri:
            p = Point()
            p.coords = (float(c[0]), float(c[1]), float(c[2]))
            self.points.append(p)
        R = derive_proxy_frame(tri)[1]
        # normal geometrica del triangulo canonico: y X z = +x local
        self.facenormals.append(tuple(float(c) for c in R[0]))
        ni = len(self.facenormals) - 1
        fa = Face(self.points, self.facenormals)
        fa.flags = 0
        fa.texture = ""
        fa.material = ""
        for i in range(3):
            vx = Vertex(self.points, self.facenormals)
            vx.point_index = base + i
            vx.normal_index = ni
            vx.uv = (0.0, 0.0)
            fa.vertices.append(vx)
        self.faces.append(fa)
        sel = self.new_selection(name)
        sel.points = {self.points[base + i]: 1 for i in range(3)}
        sel.faces = {fa: 1}
        return name

    def _resolve_proxy_anatomy(self, name, exclusive=False):
        match = PROXY_NAME_RE.match(name)
        if not match:
            raise ValueError(
                "proxy %r: name must match proxy:<path>.<index>" % name
            )
        selection = self.selections.get(name)
        if selection is None:
            raise ValueError("proxy %r: selection does not exist" % name)
        if selection.all_points is not self.points or \
                selection.all_faces is not self.faces:
            raise ValueError(
                "proxy %r: selection is not bound to the owning LOD" % name
            )
        if len(selection.points) != 3:
            raise ValueError(
                "proxy %r: selection must contain exactly 3 points" % name
            )
        if len(selection.faces) != 1:
            raise ValueError(
                "proxy %r: selection must contain exactly 1 face" % name
            )
        if any(weight != 1 for weight in selection.points.values()) or \
                any(weight != 1 for weight in selection.faces.values()):
            raise ValueError(
                "proxy %r: selection weights must all equal 1" % name
            )
        point_ids = set(map(id, self.points))
        if any(id(point) not in point_ids for point in selection.points):
            raise ValueError(
                "proxy %r: selection contains a foreign point" % name
            )
        for point in selection.points:
            if sum(point is candidate for candidate in self.points) != 1:
                raise ValueError(
                    "proxy %r: each selected point must occur exactly once "
                    "in the owning LOD" % name
                )
        face = next(iter(selection.faces))
        face_occurrences = sum(face is candidate for candidate in self.faces)
        if face_occurrences == 0:
            raise ValueError(
                "proxy %r: selection contains a foreign face" % name
            )
        if face_occurrences != 1:
            raise ValueError(
                "proxy %r: selected face must occur exactly once in the "
                "owning LOD" % name
            )
        if len(face.vertices) != 3:
            raise ValueError(
                "proxy %r: selected face must be triangular" % name
            )
        for vertex in face.vertices:
            point_index = vertex.point_index
            if isinstance(point_index, bool) or \
                    not isinstance(point_index, int) or \
                    not 0 <= point_index < len(self.points):
                raise ValueError(
                    "proxy %r: selected face has an invalid point index" % name
                )
        face_points = [
            self.points[vertex.point_index] for vertex in face.vertices
        ]
        selected_ids = set(map(id, selection.points))
        if len(set(map(id, face_points))) != 3 or \
                set(map(id, face_points)) != selected_ids:
            raise ValueError(
                "proxy %r: selected face must use exactly the selected points"
                % name
            )
        normal_indices = {vertex.normal_index for vertex in face.vertices}
        if len(normal_indices) != 1:
            raise ValueError(
                "proxy %r: selected face must use one normal" % name
            )
        normal_index = next(iter(normal_indices))
        if isinstance(normal_index, bool) or \
                not isinstance(normal_index, int) or \
                not 0 <= normal_index < len(self.facenormals):
            raise ValueError(
                "proxy %r: selected face has an invalid normal index" % name
            )
        try:
            coords = [
                tuple(float(value) for value in point.coords)
                for point in face_points
            ]
        except (TypeError, ValueError, OverflowError):
            raise ValueError(
                "proxy %r: selected points must have finite 3D coordinates"
                % name
            )
        if any(
            len(coords_value) != 3 or
            any(not math.isfinite(value) for value in coords_value)
            for coords_value in coords
        ):
            raise ValueError(
                "proxy %r: selected points must have finite 3D coordinates"
                % name
            )
        area = _v_norm(
            _v_cross(_v_sub(coords[1], coords[0]),
                     _v_sub(coords[2], coords[0]))
        )
        if area == 0.0:
            raise ValueError(
                "proxy %r: selected face must be non-degenerate" % name
            )
        anchor, raw_frame, ambiguous, angles = derive_proxy_frame(coords)
        try:
            normal = tuple(
                float(value) for value in self.facenormals[normal_index]
            )
        except (TypeError, ValueError, OverflowError):
            raise ValueError(
                "proxy %r: selected face normal must be a finite 3D vector"
                % name
            )
        if len(normal) != 3 or \
                any(not math.isfinite(value) for value in normal):
            raise ValueError(
                "proxy %r: selected face normal must be a finite 3D vector"
                % name
            )
        if _v_norm(_v_sub(normal, raw_frame[0])) > 1e-3:
            raise ValueError(
                "proxy %r: selected face normal does not match its frame"
                % name
            )
        angle_order = sorted(
            range(3),
            key=lambda index: _proxy_angle(
                _v_sub(coords[(index + 1) % 3], coords[index]),
                _v_sub(coords[(index + 2) % 3], coords[index]),
            ),
            reverse=True,
        )
        scale = _v_norm(
            _v_sub(coords[angle_order[1]], coords[angle_order[0]])
        )
        anatomy = {
            "match": match,
            "selection": selection,
            "points": tuple(face_points),
            "face": face,
            "normal_index": normal_index,
            "anchor": anchor,
            "raw_frame": raw_frame,
            "ambiguous": ambiguous,
            "angles_deg": angles,
            "scale": scale,
        }
        if not exclusive:
            return anatomy

        point_indices = {
            index for index, point in enumerate(self.points)
            if id(point) in selected_ids
        }
        for other_face in self.faces:
            if other_face is face:
                continue
            for vertex in other_face.vertices:
                point_index = vertex.point_index
                if isinstance(point_index, bool) or \
                        not isinstance(point_index, int) or \
                        not 0 <= point_index < len(self.points):
                    raise ValueError(
                        "proxy %r: another face has an invalid point index"
                        % name
                    )
                if point_index in point_indices:
                    raise ValueError(
                        "proxy %r: point is shared by another face" % name
                    )
                if vertex.normal_index == normal_index:
                    raise ValueError(
                        "proxy %r: normal is shared by another face" % name
                    )
        for other_name, other_selection in self.selections.items():
            if other_name == name:
                continue
            if other_selection is selection:
                raise ValueError(
                    "proxy %r: selection object is shared by name %r"
                    % (name, other_name)
                )
            if any(id(point) in selected_ids
                   for point in other_selection.points):
                raise ValueError(
                    "proxy %r: point is shared by selection %r"
                    % (name, other_name)
                )
            if any(other_face is face for other_face in other_selection.faces):
                raise ValueError(
                    "proxy %r: face is shared by selection %r"
                    % (name, other_name)
                )
        for edge in self.sharp_edges:
            try:
                first, second = edge
            except (TypeError, ValueError):
                raise ValueError(
                    "proxy %r: LOD contains a malformed sharp edge" % name
                )
            if any(
                isinstance(index, bool) or not isinstance(index, int) or
                not 0 <= index < len(self.points)
                for index in (first, second)
            ):
                raise ValueError(
                    "proxy %r: sharp edge has an invalid point index" % name
                )
            if first in point_indices or second in point_indices:
                raise ValueError(
                    "proxy %r: point is shared by a sharp edge" % name
                )
        anatomy["point_indices"] = point_indices
        return anatomy

    def align_proxy(self, name, origin, rotation=None, scale=0.001,
                    space="raw"):
        """Rewrite one exclusively owned canonical proxy transform in place.

        The three Point objects, selected Face, Selection and owning list
        objects retain their identities. The proxy's exclusive facenormal
        keeps its existing pool index.
        """
        triangle = canonical_proxy_triangle(origin, rotation, scale, space)
        anatomy = self._resolve_proxy_anatomy(name, exclusive=True)
        normal = derive_proxy_frame(triangle)[1][0]

        for point, coords in zip(anatomy["points"], triangle):
            point.coords = tuple(float(value) for value in coords)
        self.facenormals[anatomy["normal_index"]] = tuple(
            float(value) for value in normal
        )
        return name

    def remove_proxy(self, name):
        """Remove one exclusively owned canonical proxy without list rebinding.

        Exactly the proxy selection, triangular face and three selected points
        are removed. The normal pool is intentionally unchanged. Every
        surviving face vertex and sharp-edge point index is validated and
        remapped before the first mutation.
        """
        anatomy = self._resolve_proxy_anatomy(name, exclusive=True)
        remove_indices = anatomy["point_indices"]
        face = anatomy["face"]

        surviving_points = [
            point for index, point in enumerate(self.points)
            if index not in remove_indices
        ]
        surviving_faces = [
            candidate for candidate in self.faces if candidate is not face
        ]
        point_remap = {}
        next_index = 0
        for old_index in range(len(self.points)):
            if old_index not in remove_indices:
                point_remap[old_index] = next_index
                next_index += 1

        vertex_updates = []
        for surviving_face in surviving_faces:
            for vertex in surviving_face.vertices:
                old_index = vertex.point_index
                if old_index not in point_remap:
                    raise ValueError(
                        "proxy %r: surviving face has an invalid point index"
                        % name
                    )
                vertex_updates.append((vertex, point_remap[old_index]))

        sharp_edge_updates = []
        for first, second in self.sharp_edges:
            if first not in point_remap or second not in point_remap:
                raise ValueError(
                    "proxy %r: surviving sharp edge has an invalid point index"
                    % name
                )
            sharp_edge_updates.append(
                (point_remap[first], point_remap[second])
            )

        self.points[:] = surviving_points
        self.faces[:] = surviving_faces
        for vertex, point_index in vertex_updates:
            vertex.point_index = point_index
        self.sharp_edges[:] = sharp_edge_updates
        del self.selections[name]
        return name

    def get_proxies(self, strict=False):
        """F2-06: lista de proxies de este LOD con su frame derivado por
        ANGLE-SORT (proxy_frame.py:38-52).

        Cada entrada: {name, path, index, anchor, frame (filas x,y,z),
        ambiguous, angles_deg}. ambiguous=True => los dos angulos menores
        empatan (triangulo isosceles legacy) y la orientacion derivada
        depende del orden crudo de vertices - re-emite con add_proxy para
        fijarla. Solo selections 'proxy:*' con exactamente 3 puntos.
        """
        out = []
        for name, sel in self.selections.items():
            m = PROXY_NAME_RE.match(name)
            if not m:
                continue
            if strict:
                anatomy = self._resolve_proxy_anatomy(name)
                anchor = anatomy["anchor"]
                R = anatomy["raw_frame"]
                ambiguous = anatomy["ambiguous"]
                deg = anatomy["angles_deg"]
                scale = anatomy["scale"]
            else:
                if len(sel.points) != 3:
                    continue
                ids = set(map(id, sel.points))
                coords = [p.coords for p in self.points if id(p) in ids]
                anchor, R, ambiguous, deg = derive_proxy_frame(coords)
                angle_order = sorted(
                    range(3),
                    key=lambda index: _proxy_angle(
                        _v_sub(coords[(index + 1) % 3], coords[index]),
                        _v_sub(coords[(index + 2) % 3], coords[index]),
                    ),
                    reverse=True,
                )
                scale = _v_norm(
                    _v_sub(coords[angle_order[1]],
                           coords[angle_order[0]])
                )
            raw_frame = [list(row) for row in R]
            out.append({
                "name": name,
                "path": m.group("path"),
                "index": int(m.group("index")),
                "anchor": anchor,
                "frame": raw_frame,
                "raw_frame": [row[:] for row in raw_frame],
                "engine_frame": [
                    list(row) for row in proxy_frame_to_engine(R)
                ],
                "scale": scale,
                "ambiguous": ambiguous,
                "angles_deg": deg,
            })
        return out

    def validate_normals_budget(self, budget=32768, severity="WARN",
                                lod_index=None):
        """F1-07: presupuesto de facenormals por LOD (R22-P2-01).

        WARN por defecto: el umbral 32768 es evidencia LOCAL (LL-028 +
        crash KT Roadkill 2026-05-24), SIN fuente primaria BI confirmada.
        Usa severity="ERROR" solo si tu proyecto lo trata como contrato.
        Metrica exacta: len(lod.facenormals).
        """
        if severity not in ("WARN", "ERROR"):
            raise ValueError("severity must be 'WARN' or 'ERROR'")
        n = len(self.facenormals)
        if n <= budget:
            return []
        return [Finding(
            "WARN_NORMALS_BUDGET", severity, lod_index,
            "LOD has %d facenormals (budget %d; observed crash limit - "
            "local evidence, no confirmed primary source)" % (n, budget))]

    def _scan_findings(self, lod_index):
        """F1-09: escaneo NO-raising de selections y properties."""
        findings = []
        point_ids = set(map(id, self.points))
        face_ids = set(map(id, self.faces))
        for name, sel in self.selections.items():
            if sel.all_points is not self.points or \
                    sel.all_faces is not self.faces:
                findings.append(Finding(
                    "ERR_SELECTION_STALE", "ERROR", lod_index,
                    "selection %r: stale binding (all_points/all_faces are "
                    "not this LOD's current lists)" % name))
                continue
            foreign = [p for p in sel.points if id(p) not in point_ids] + \
                      [fa for fa in sel.faces if id(fa) not in face_ids]
            if foreign:
                findings.append(Finding(
                    "ERR_SELECTION_STALE", "ERROR", lod_index,
                    "selection %r: %d key(s) not present by identity in the "
                    "LOD lists (weight would be silently dropped)"
                    % (name, len(foreign))))
            for kind, mapping in (("point", sel.points), ("face", sel.faces)):
                for w in mapping.values():
                    try:
                        Selection._normalize_weight(w, kind, name)
                    except ValueError as e:
                        findings.append(Finding(
                            "ERR_WEIGHT_RANGE", "ERROR", lod_index, str(e)))
                        break
        for k, v in self.properties.items():
            kb = len(bytes(k, "utf-8"))
            vb = len(bytes(v, "utf-8"))
            if kb >= 63 or vb >= 63:
                if kb > 63 or vb > 63:
                    msg = ("property %r: key/value exceeds 63 utf-8 bytes "
                           "(write will raise - quirk 6 guard)" % k)
                else:
                    msg = ("property %r: key/value is exactly 63 utf-8 "
                           "bytes - fingerprint of silent truncation by "
                           "other tooling (quirk 6)" % k)
                findings.append(Finding(
                    "WARN_PROPERTY_TRUNCATION", "WARN", lod_index, msg))
        return findings

    def read(self, f):
        assert f.read(4) == b"P3DM"

        self.version_major = struct.unpack("<L", f.read(4))[0]
        self.version_minor = struct.unpack("<L", f.read(4))[0]

        num_points = struct.unpack("<L", f.read(4))[0]
        num_facenormals = struct.unpack("<L", f.read(4))[0]
        num_faces = struct.unpack("<L", f.read(4))[0]

        f.seek(4, 1)

        self.points.extend([Point(f) for i in range(num_points)])
        self.facenormals.extend([struct.unpack("fff", f.read(12)) for i in range(num_facenormals)])
        self.faces.extend([Face(self.points, self.facenormals, f) for i in range(num_faces)])

        assert f.read(4) == b"TAGG"

        while True:
            f.seek(1, 1)
            taggname = _read_asciiz(f)

            if taggname[0] != "#":
                self.selections[taggname] = Selection(self.points, self.faces, f)
                continue

            num_bytes = struct.unpack("<L", f.read(4))[0]
            data = f.read(num_bytes)

            if taggname == "#EndOfFile#":
                break

            if taggname == "#SharpEdges#": #untested
                self.sharp_edges.extend([struct.unpack("<LL", data[i*8:i*8+8]) for i in range(int(num_bytes / 8))])
                continue

            if taggname == "#Property#": #untested
                assert num_bytes == 128
                k, v = data[:64], data[64:]

                assert b"\0" in k and b"\0" in v
                k, v = k[:k.index(b"\0")], v[:v.index(b"\0")]

                self.properties[str(k, "utf-8")] = str(v, "utf-8")
                continue

            if taggname == "#Mass#":
                assert num_bytes == 4 * num_points
                for i in range(num_points):
                    self.points[i].mass = struct.unpack("f", data[i*4:i*4+4])[0]
                continue

            if taggname == "#UVSet#":
                self._read_uv_set(data)
                continue

            #if taggname == "#Animation#": #not supported
            #    pass

        self.resolution = struct.unpack("f", f.read(4))[0]

    def _read_uv_set(self, data):
        """Store one #UVSet# payload: a 4-byte set id followed by one (u, v)
        pair per face vertex, in face order.

        Set 0 duplicates the uv already carried by every face vertex and is
        ignored, as upstream does. Any other set is attached to the face
        vertices as `Vertex.uv_sets[id]` so that write() can emit it again;
        in a LOD without faces there is nothing to attach it to, so the id
        alone is kept in `faceless_uv_sets`. A payload whose length does not
        match the faces, or a set id that appears twice, is a corrupt LOD and
        raises instead of being dropped in silence.
        """
        if len(data) < 4:
            raise ValueError(
                "#UVSet#: payload of %d bytes is shorter than the 4-byte "
                "set id" % len(data))
        uv_id = struct.unpack("<L", data[:4])[0]
        if uv_id == 0:
            return
        num_vertices = self.num_vertices
        if num_vertices == 0:
            # No face vertices to attach it to: keep the id alone.
            if uv_id in self.faceless_uv_sets:
                raise ValueError(
                    "#UVSet# id %d appears twice in the same LOD" % uv_id)
            if len(data) != 4:
                raise ValueError(
                    "#UVSet# id %d: payload is %d bytes, expected 4 in a LOD "
                    "without faces" % (uv_id, len(data)))
            self.faceless_uv_sets.append(uv_id)
            return
        expected = 4 + num_vertices * 8
        if len(data) != expected:
            raise ValueError(
                "#UVSet# id %d: payload is %d bytes, expected %d for %d face "
                "vertices" % (uv_id, len(data), expected, num_vertices))
        offset = 4
        for fa in self.faces:
            for v in fa.vertices:
                if uv_id in v.uv_sets:
                    raise ValueError(
                        "#UVSet# id %d appears twice in the same LOD" % uv_id)
                v.uv_sets[uv_id] = struct.unpack("ff", data[offset:offset + 8])
                offset += 8

    def write(self, f):
        f.write(b"P3DM")
        f.write(struct.pack("<L", self.version_major))
        f.write(struct.pack("<L", self.version_minor))

        f.write(struct.pack("<L", len(self.points)))
        f.write(struct.pack("<L", len(self.facenormals)))
        f.write(struct.pack("<L", len(self.faces)))

        f.write(b"\0" * 4)

        for p in self.points:
            p.write(f)
        for fn in self.facenormals:
            f.write(struct.pack("fff", *fn))
        for fa in self.faces:
            fa.write(f)

        f.write(b"TAGG")

        if len(self.sharp_edges) > 0: #untested
            f.write(b"\x01")
            f.write(b"#SharpEdges#\0")
            f.write(struct.pack("<L", len(self.sharp_edges) * 8))
            for se in self.sharp_edges:
                f.write(struct.pack("<LL", *se))

        for k, v in self.selections.items():
            # F1-05: la selection debe seguir bindeada a LAS listas actuales
            # del LOD (reemplazarlas deja la selection stale - R22-P1-03).
            if v.all_points is not self.points or v.all_faces is not self.faces:
                raise RuntimeError(
                    "selection %r: stale binding - its all_points/all_faces "
                    "are not this LOD's current lists (did you replace "
                    "lod.points/lod.faces after creating it?). Re-create it "
                    "with lod.new_selection(name) or "
                    "Selection(lod.points, lod.faces)." % k)
            f.write(b"\x01")
            f.write(bytes(k, "utf-8") + b"\0")
            v.write(f, name=k)

        for k, v in self.properties.items():
            key_bytes = bytes(k, "utf-8")
            value_bytes = bytes(v, "utf-8")
            # F1-06: upstream struct.pack("64s64s") silently truncates
            # anything longer (and a 64-byte value loses its NUL
            # terminator, corrupting the read side). Quirk 6.
            if len(key_bytes) > 63 or len(value_bytes) > 63:
                raise ValueError(
                    "property %r: key and value must each encode to at "
                    "most 63 UTF-8 bytes (64-byte field incl. NUL "
                    "terminator); got key=%d, value=%d bytes"
                    % (k, len(key_bytes), len(value_bytes)))
            f.write(b"\x01")
            f.write(b"#Property#\0")
            f.write(struct.pack("<L", 128))
            f.write(struct.pack("64s64s", key_bytes, value_bytes))

        if self.mass is not None:
            f.write(b"\x01")
            f.write(b"#Mass#\0")
            f.write(struct.pack("<L", len(self.points) * 4))
            for p in self.points:
                f.write(struct.pack("f", p.mass))

        # One #UVSet# per set, in id order. Set 0 is the uv carried by the
        # face vertices; the others come from Vertex.uv_sets, and a vertex
        # that lacks a set present elsewhere in the LOD gets (0, 0), which is
        # what Object Builder assigns to new faces. Object Builder also
        # writes the tag for a LOD without faces (Memory, LandContact), with
        # the 4-byte set id as its whole payload. Upstream omits it there;
        # BI-authored MLOD files carry it, so it is emitted for parity.
        num_vertices = self.num_vertices
        for uv_id in self.uv_set_ids():
            f.write(b"\x01")
            f.write(b"#UVSet#\0")
            f.write(struct.pack("<L", num_vertices * 8 + 4))
            f.write(struct.pack("<L", uv_id))
            for fa in self.faces:
                for v in fa.vertices:
                    if uv_id == 0:
                        uv = v.uv
                    else:
                        uv = v.uv_sets.get(uv_id, (0.0, 0.0))
                    f.write(struct.pack("ff", *uv))

        f.write(b"\x01")
        f.write(b"#EndOfFile#\0")
        f.write(b"\0\0\0\0")

        f.write(struct.pack("f", self.resolution))


class P3D:
    def __init__(self, f=None):
        self.lods = []
        if f is not None:
            self.read(f)

    def read(self, f):
        assert f.read(4) == b"MLOD"

        version = struct.unpack("<L", f.read(4))[0]
        num_lods = struct.unpack("<L", f.read(4))[0]

        self.lods.extend([LOD(f) for i in range(num_lods)])

    def write(self, f):
        f.write(b"MLOD")
        f.write(struct.pack("<L", 257))
        f.write(struct.pack("<L", len(self.lods)))
        for l in self.lods:
            l.write(f)

    def _verify_against(self, reread):
        """F1-08: invariantes estructurales del verify (SEM-INV minimo)."""
        if len(reread.lods) != len(self.lods):
            raise ValueError("verify: LOD count differs")
        for i, (a, b) in enumerate(zip(self.lods, reread.lods)):
            if (len(b.points), len(b.facenormals), len(b.faces)) != \
                    (len(a.points), len(a.facenormals), len(a.faces)):
                raise ValueError("verify: stream counts differ in LOD %d" % i)
            if list(b.selections.keys()) != list(a.selections.keys()):
                raise ValueError("verify: selections differ in LOD %d" % i)
            for name in a.selections:
                sa, sb = a.selections[name], b.selections[name]
                if (len(sb.points), len(sb.faces)) != (len(sa.points), len(sa.faces)):
                    raise ValueError(
                        "verify: selection %r membership differs in LOD %d"
                        % (name, i))
            if dict(b.properties) != dict(a.properties):
                raise ValueError("verify: properties differ in LOD %d" % i)
            if b.uv_set_ids() != a.uv_set_ids():
                raise ValueError("verify: UV sets differ in LOD %d" % i)
            am, bm = a.mass, b.mass
            if (am is None) != (bm is None) or \
                    (am is not None and abs(am - bm) > 1e-3):
                raise ValueError("verify: mass differs in LOD %d" % i)

    def save(self, path, verify=True, backup_dir=None):
        r"""F1-08: escritura atomica verificada (contrato Windows/POSIX).

        Siempre: temp en el MISMO directorio -> flush + os.fsync(fd) ->
        close -> (verify) reopen + parse + invariantes estructurales ->
        backup opcional del archivo previo -> os.replace() atomico.
        Solo POSIX: fsync del directorio tras el replace. En Windows eso
        no es portable y se compensa con la verificacion reopen+parse
        (runbook OneDrive / LL-033: verificar por CONTENIDO, no mtime).
        Si algo falla: raise; el archivo original queda byte-intacto y el
        temp se elimina. R22-P2-03.
        """
        path = os.fspath(path)
        dirpath = os.path.dirname(os.path.abspath(path)) or "."
        base = os.path.basename(path)
        fd, tmp_path = tempfile.mkstemp(prefix=base + ".tmp.", dir=dirpath)
        try:
            with os.fdopen(fd, "wb") as f:
                self.write(f)
                f.flush()
                os.fsync(f.fileno())
            if verify:
                with open(tmp_path, "rb") as f:
                    reread = P3D(f)
                self._verify_against(reread)
            if backup_dir and os.path.exists(path):
                import shutil
                import time
                os.makedirs(backup_dir, exist_ok=True)
                stamp = time.strftime("%Y%m%d_%H%M%S")
                shutil.copy2(path, os.path.join(
                    backup_dir, "%s.bak_%s" % (base, stamp)))
            os.replace(tmp_path, path)
            tmp_path = None
            if hasattr(os, "O_DIRECTORY"):  # POSIX
                dfd = os.open(dirpath, os.O_DIRECTORY)
                try:
                    os.fsync(dfd)
                finally:
                    os.close(dfd)
        finally:
            if tmp_path is not None and os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def get_lod(self, name):
        """F2-01: primer LOD (en orden de archivo) cuyo kind() es *name*.

        Acepta los kinds canonicos ("visual", "shadowvolume", claves de
        LOD_RESOLUTIONS) y los alias del pipeline ("viewgeo", "firegeo",
        "shadow"). Nombre no reconocido -> ValueError; sin match -> None.
        """
        key = LOD_KIND_ALIASES.get(name.lower(), name.lower())
        valid = set(LOD_RESOLUTIONS) | {"visual", "shadowvolume"}
        if key not in valid:
            raise ValueError(
                "get_lod: unknown LOD kind %r (valid: %s)"
                % (name, ", ".join(sorted(valid | set(LOD_KIND_ALIASES)))))
        for lod in self.lods:
            if lod.kind() == key:
                return lod
        return None

    def transform(self, matrix):
        """F3-02: transforma TODO el modelo (in-place) con una matriz 3x3.

        Convencion column-vector: new_i = sum_j matrix[i][j] * old_j.
        Caso primario: py3d.BLENDER_TO_DAYZ (Blender Z-up -> DayZ Y-up,
        (x,y,z) -> (x,z,-y), det=+1).

        Contrato (R25, D-S3-6): permutaciones de ejes / rotaciones /
        reflexiones / escala uniforme = matriz ortogonal x escalar.
        Cualquier otra (shear, escala no uniforme, singular) -> ValueError
        SIN mutar nada.

        Winding (LL-020): det<0 (reflexion) invierte el handedness ->
        face.vertices.reverse() en TODAS las caras de TODOS los LODs (la
        normal geometrica cross-product vuelve a alinearse con la
        declarada M*n). det>0 (rotacion propia) NO invierte.

        Aplica a Point.coords (objetos mutados in-place: identidad
        preservada, selections intactas) y al pool lod.facenormals
        (re-normalizado a unitario; entrada degenerada se conserva).
        NO toca: uv, sharp_edges, properties, selections, flags, mass.
        Memory points y proxies son puntos/caras: se transforman solos.
        Devuelve None.
        """
        m = _validate_transform_matrix(matrix)
        det = _det3(m)
        for lod in self.lods:
            for p in lod.points:
                p.coords = _mat_vec(m, p.coords)
            for i, n in enumerate(lod.facenormals):
                moved = _mat_vec(m, n)
                lod.facenormals[i] = _v_unit(moved, tuple(n))
            if det < 0:
                for face in lod.faces:
                    face.vertices.reverse()
        return None

    def to_dict(self, source_path=None):
        """F2-07 (D7, scoped): Recipe JSON schema v1 del inspector.

        Port 1:1 de p3d_inspector_extract.extract_recipe (extract.py:
        313-423): meta, lods (geometry|wireframe|note por tipo),
        memory_points, axes, bounding_box, referenced_paths. JSON-safe.
        Perdidas del schema documentadas en el bloque _recipe_*.
        """
        recipe = {
            "meta": {
                "source": os.path.basename(source_path) if source_path
                          else "",
                "source_path": source_path or "",
                "version": 1,
                "mode": "audit",
            },
            "lods": [],
            "memory_points": [],
            "axes": {},
            "bounding_box": None,
        }
        gmin = [float("inf")] * 3
        gmax = [float("-inf")] * 3

        for lod in self.lods:
            lod_type = _recipe_lod_type(lod.resolution)
            lod_info = {
                "type": lod_type,
                "resolution": lod.resolution,
                "num_points": len(lod.points),
                "num_faces": len(lod.faces),
                "selections": _recipe_selections(lod),
                "properties": dict(lod.properties),
            }
            if lod_type.startswith("visual"):
                geo = _recipe_visual_geometry(lod)
                lod_info["geometry"] = geo
                for pos in geo["positions"]:
                    for j in range(3):
                        gmin[j] = min(gmin[j], pos[j])
                        gmax[j] = max(gmax[j], pos[j])
            elif lod_type in _RECIPE_WIREFRAME_TYPES:
                lod_info["wireframe"] = _recipe_wireframe(lod)
                if lod_type in ("geometry", "fire_geometry",
                                "view_geometry"):
                    for pos in lod_info["wireframe"]["positions"]:
                        for j in range(3):
                            gmin[j] = min(gmin[j], pos[j])
                            gmax[j] = max(gmax[j], pos[j])
            elif lod_type == "shadow":
                lod_info["wireframe"] = _recipe_wireframe(lod)
            elif lod_type == "memory":
                memory_points, axes = _recipe_memory_data(lod)
                recipe["memory_points"] = memory_points
                recipe["axes"] = axes
                lod_info["note"] = "%d points, %d axes" % (
                    len(memory_points), len(axes))
            recipe["lods"].append(lod_info)

        if gmin[0] != float("inf"):
            recipe["bounding_box"] = {
                "min": gmin,
                "max": gmax,
                "size": [gmax[j] - gmin[j] for j in range(3)],
                "center": [(gmin[j] + gmax[j]) / 2 for j in range(3)],
            }

        all_textures = set()
        all_materials = set()
        for lod_info in recipe["lods"]:
            if "geometry" in lod_info:
                for key in lod_info["geometry"]["material_groups"]:
                    tex, mat = key.split("|", 1)
                    if tex:
                        all_textures.add(tex)
                    if mat:
                        all_materials.add(mat)
        recipe["referenced_paths"] = {
            "textures": sorted(all_textures),
            "materials": sorted(all_materials),
        }
        return recipe

    @classmethod
    def from_dict(cls, recipe):
        """F2-07 (D7, scoped): construye un P3D desde un Recipe v1.

        Port 1:1 de p3d_inspector_build.build_p3d (build.py:486-545) SIN
        el auto-fix de winding (eso queda en el script del inspector; aqui
        solo construccion). Tipos de LOD desconocidos se OMITEN (igual que
        build, que los registra como warning). El Memory LOD se reconstruye
        SIEMPRE desde recipe["memory_points"].
        """
        model = cls()
        for lod_dict in recipe.get("lods", []):
            lod_type = lod_dict.get("type", "unknown")
            if lod_type.startswith("visual"):
                model.lods.append(_recipe_build_visual(lod_dict))
            elif lod_type in _RECIPE_BUILD_WIREFRAME_TYPES:
                model.lods.append(
                    _recipe_build_wireframe(lod_dict, lod_type, recipe))
            # memory: reconstruido abajo; desconocidos: omitidos (scoped)
        mem = _recipe_build_memory(recipe)
        if mem is not None:
            model.lods.append(mem)
        return model

    def _scan_v12_findings(self):
        """F2-12: checks portados del audit (ver bloque de paridad)."""
        findings = []
        visual = None
        visual_index = None
        # F4-01: la referencia es el visual de MENOR resolucion (LOD0, el de
        # mas detalle), no el primero que aparezca en el fichero: el orden de
        # LODs en disco no es normativo y cambiaba el veredicto.
        for i, lod in enumerate(self.lods):
            if lod.kind() == "visual":
                if visual is None or lod.resolution < visual.resolution:
                    visual = lod
                    visual_index = i
        for i, lod in enumerate(self.lods):
            k = lod.kind()
            findings.extend(_check_mass_only_geometry(lod, i))
            if k is None:
                findings.append(Finding(
                    "WARN_LOD_KIND_UNKNOWN", "WARN", i,
                    "unrecognized LOD resolution %g - not a known DayZ id "
                    "(Arma-3-era e13 FireGeo/ViewGeo ids are NOT valid in "
                    "DayZ: use 7e15/6e15)" % lod.resolution))
                continue
            if k == "geometry":
                findings.extend(_check_component_naming(lod, i))
                findings.extend(_check_component_coverage(lod, i))
                findings.extend(_check_autocenter(lod, i))
            if k in _GEOMETRY_CLASS_KINDS:
                findings.extend(_check_watertight(lod, i))
                findings.extend(_check_degenerate_faces(lod, i))
                findings.extend(_check_winding_absolute(lod, i, k))
                if visual is not None and lod is not visual:
                    findings.extend(_check_winding_vs_visual(
                        lod, i, visual, k))
            if k == "memory":
                findings.extend(_check_memory_structure(lod, i))
                if visual is not None:
                    findings.extend(_check_axis_selections(
                        lod, visual, visual_index))
            if k == "visual":
                findings.extend(_check_pdrive_faces(lod, i))
                # F4-01: tambien en el visual, o un modelo SOLO-visual (un
                # prop simple sin LOD de colision) se quedaria sin ninguna
                # comprobacion de winding.
                findings.extend(_check_winding_absolute(lod, i, k))
        return findings

    def validate(self, normals_budget=32768, normals_severity="WARN"):
        r"""Validador v1.2.0.

        Codigos v1.1.0 (F1-09): ERR_SELECTION_STALE, ERR_WEIGHT_RANGE,
        WARN_NORMALS_BUDGET, WARN_PROPERTY_TRUNCATION,
        ERR_UNREADABLE_ROUNDTRIP.
        Codigos v1.2.0 (F2-12, paridad depurada con dayz-p3d-audit; ver
        bloque "_check_*"): ERR_WINDING_INVERTED, WARN_WINDING_MIXED,
        WARN_WINDING_LOWCONF, ERR_COMPONENT_NAMING, WARN_COMPONENT_NAMING,
        WARN_COMPONENT_COVERAGE, WARN_AUTOCENTER_MISSING,
        WARN_NOT_WATERTIGHT, WARN_DEGENERATE_FACES, WARN_MEMORY_POS_CENTER,
        WARN_MEMORY_BOX_PLACING, ERR_MEMORY_AXIS_POINTS,
        WARN_MEMORY_AXIS_SHORT, WARN_MEMORY_HAS_FACES,
        ERR_AXIS_SELECTION_MISSING, WARN_AXIS_SELECTION_EMPTY,
        WARN_PDRIVE_PATH, WARN_LOD_KIND_UNKNOWN.
        Codigos v1.3.0 (F3-01, BUG-021): ERR_MASS_ONLY_GEOMETRY (#Mass#
        en LOD no-Geometry => binarize hornea CoM=(0,0,0); LL-080).

        Devuelve list[Finding]; NO lanza por hallazgos (si por mal uso de
        los parametros). El round-trip en memoria solo se intenta si no
        hay ERRORs previos (los guards de write lanzarian).
        """
        findings = []
        for i, lod in enumerate(self.lods):
            findings.extend(lod._scan_findings(i))
            findings.extend(lod.validate_normals_budget(
                budget=normals_budget, severity=normals_severity,
                lod_index=i))
        findings.extend(self._scan_v12_findings())
        if not any(f.severity == "ERROR" for f in findings):
            import io
            try:
                buf = io.BytesIO()
                self.write(buf)
                buf.seek(0)
                self._verify_against(P3D(buf))
            except Exception as e:
                findings.append(Finding(
                    "ERR_UNREADABLE_ROUNDTRIP", "ERROR", None,
                    "in-memory round-trip failed: %s" % e))
        return findings
