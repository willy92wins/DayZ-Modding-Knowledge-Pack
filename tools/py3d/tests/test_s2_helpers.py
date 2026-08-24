"""S2: F2-01 (constantes LOD/kind/get_lod), F2-02 (bbox), F2-03
(triangulate), F2-04 (set_selection), F2-05 (set_total_mass)."""

import pytest

from builders import (build_cube_lod, build_cube_p3d, build_multilod_p3d,
                      build_multilod_v2_p3d)
from helpers import read_p3d, write_bytes


# ---- LOD-POS / LOD-NEG (F2-01) -----------------------------------------------

def test_lod_pos_get_lod_four_kinds(fork):
    """LOD-POS: multi-LOD -> get_lod x4 devuelve el LOD correcto."""
    p3d = build_multilod_v2_p3d(fork)
    assert p3d.get_lod("geometry").resolution == 1.0e13
    assert p3d.get_lod("memory").resolution == 1.0e15
    assert p3d.get_lod("view_geometry").resolution == 6.0e15
    assert p3d.get_lod("fire_geometry").resolution == 7.0e15
    # alias del pipeline
    assert p3d.get_lod("viewgeo") is p3d.get_lod("view_geometry")
    assert p3d.get_lod("firegeo") is p3d.get_lod("fire_geometry")
    assert p3d.get_lod("visual").resolution == 1.0
    kinds = [lod.kind() for lod in p3d.lods]
    assert kinds == ["visual", "geometry", "view_geometry",
                     "fire_geometry", "memory"]


def test_lod_pos_kind_tolerance_and_shadow(fork):
    """Tolerancia relativa unica + familia shadowvolume."""
    lod = fork.LOD()
    lod.resolution = 1.04e13  # dentro del 5%
    assert lod.kind() == "geometry"
    lod.resolution = 10010.0  # ShadowVolume nivel 10
    assert lod.kind() == "shadowvolume"
    lod.resolution = 2.0  # nivel de detalle visual
    assert lod.kind() == "visual"


def test_lod_neg_unknown_and_legacy_arma(fork):
    """LOD-NEG: 5.5e14 -> kind()=None + WARN en validate(); los ids
    legacy Arma 3 de la familia e13 tampoco clasifican (anti-drift)."""
    p3d = build_cube_p3d(fork)
    p3d.lods[0].resolution = 5.5e14
    assert p3d.lods[0].kind() is None
    fs = p3d.validate()
    assert [f.code for f in fs] == ["WARN_LOD_KIND_UNKNOWN"]
    assert fs[0].severity == "WARN" and fs[0].lod == 0
    for legacy in (2.0e13, 3.0e13, 7.0e13):
        assert fork.classify_lod_resolution(legacy) is None
    assert p3d.get_lod("memory") is None  # sin match -> None
    with pytest.raises(ValueError):
        p3d.get_lod("geophys")  # kind inexistente -> ValueError


# ---- BBOX-POS / BBOX-NEG (F2-02) ---------------------------------------------

def test_bbox_pos_unit_cube(fork):
    """BBOX-POS: cubo unidad -> min/max/center exactos (tambien tras
    round-trip f32)."""
    p3d = build_cube_p3d(fork)
    lo, hi, center = p3d.lods[0].bbox()
    assert lo == (-0.5, -0.5, -0.5)
    assert hi == (0.5, 0.5, 0.5)
    assert center == (0.0, 0.0, 0.0)
    reread = read_p3d(fork, write_bytes(p3d))
    assert reread.lods[0].bbox() == (lo, hi, center)


def test_bbox_neg_empty_lod(fork):
    """BBOX-NEG: LOD vacio -> ValueError."""
    with pytest.raises(ValueError, match="no points"):
        fork.LOD().bbox()


# ---- TRI-POS (F2-03) ---------------------------------------------------------

def test_tri_pos_cube_with_selection(fork):
    """TRI-POS: cubo 6 quads + selection de 3 quads -> 12 tris, la
    selection pasa a 6 tris, UVs == num_vertices, sharp_edges intactos."""
    p3d = build_cube_p3d(fork)
    lod = p3d.lods[0]
    lod.sharp_edges = [(0, 1), (2, 3)]
    lod.set_selection("half", face_idx=[0, 1, 2], weight=0.5)
    quad0_uvs = [v.uv for v in lod.faces[0].vertices]
    quad0_tex = lod.faces[0].texture

    assert lod.triangulate() == 6
    assert len(lod.faces) == 12
    assert all(len(fa.vertices) == 3 for fa in lod.faces)
    # membership remapeada: 3 quads -> 6 tris, mismo peso fraccional
    half = lod.selections["half"]
    assert len(half.faces) == 6
    assert all(w == 0.5 for w in half.faces.values())
    # Component01 cubria los 6 quads -> 12 tris
    assert len(lod.selections["Component01"].faces) == 12
    # UVs preservadas por vertice (fan 0,1,2 / 0,2,3 del quad 0)
    assert [v.uv for v in lod.faces[0].vertices] == \
        [quad0_uvs[0], quad0_uvs[1], quad0_uvs[2]]
    assert [v.uv for v in lod.faces[1].vertices] == \
        [quad0_uvs[0], quad0_uvs[2], quad0_uvs[3]]
    assert lod.faces[0].texture == lod.faces[1].texture == quad0_tex
    assert lod.sharp_edges == [(0, 1), (2, 3)]
    assert lod.triangulate() == 0  # idempotente: ya no hay quads

    # el resultado escribe y re-lee con membership intacta
    reread = read_p3d(fork, write_bytes(p3d))
    rlod = reread.lods[0]
    assert len(rlod.faces) == 12
    assert rlod.num_vertices == 36  # entradas #UVSet# = num_vertices
    assert len(rlod.selections["half"].faces) == 6
    got = sorted(rlod.selections["half"].faces.values())
    assert all(abs(w - 0.5) < 0.51 / 255 for w in got)


# ---- SETSEL-POS / SETSEL-NEG (F2-04) -----------------------------------------

def test_setsel_pos_idempotent_overwrite(fork):
    """SETSEL-POS: set_selection x2 mismo nombre -> overwrite, no duplica."""
    p3d = build_cube_p3d(fork)
    lod = p3d.lods[0]
    lod.set_selection("zone", face_idx=[0, 1], point_idx=[0, 1, 2])
    lod.set_selection("zone", face_idx=[5], point_idx=[7])
    assert list(lod.selections).count("zone") == 1
    sel = lod.selections["zone"]
    assert len(sel.faces) == 1 and len(sel.points) == 1
    assert lod.faces[5] in sel.faces and lod.points[7] in sel.points
    reread = read_p3d(fork, write_bytes(p3d))
    rsel = reread.lods[0].selections["zone"]
    assert len(rsel.faces) == 1 and len(rsel.points) == 1


def test_setsel_neg_bad_weight_and_index(fork):
    """SETSEL-NEG: weight 2.0 -> ValueError (guard F1-02); indice fuera
    de rango -> IndexError. Sin mutacion parcial."""
    p3d = build_cube_p3d(fork)
    lod = p3d.lods[0]
    with pytest.raises(ValueError, match="weight"):
        lod.set_selection("bad", face_idx=[0], weight=2.0)
    with pytest.raises(ValueError):
        lod.set_selection("bad", face_idx=[0], weight="x")
    with pytest.raises(IndexError, match="out of range"):
        lod.set_selection("bad", point_idx=[99])
    assert "bad" not in lod.selections


# ---- MASS-POS (F2-05) --------------------------------------------------------

def test_mass_pos_total_on_geometry(fork):
    """MASS-POS: set_total_mass(200) -> suma 200 +-1e-3 sobre los puntos
    del Geometry LOD, y sobrevive al round-trip (#Mass#)."""
    p3d = build_multilod_v2_p3d(fork)
    geo = p3d.get_lod("geometry")
    geo.set_total_mass(200.0)
    assert abs(geo.mass - 200.0) < 1e-3
    assert all(abs(p.mass - 25.0) < 1e-6 for p in geo.points)
    reread = read_p3d(fork, write_bytes(p3d))
    assert abs(reread.get_lod("geometry").mass - 200.0) < 1e-3
    with pytest.raises(ValueError):
        fork.LOD().set_total_mass(10)
    with pytest.raises(ValueError):
        geo.set_total_mass(-1)


def test_s1_multilod_sigue_limpio(fork):
    """Regresion: el fixture S1 sigue dando validate() == [] tras F2-12."""
    assert build_multilod_p3d(fork).validate() == []
