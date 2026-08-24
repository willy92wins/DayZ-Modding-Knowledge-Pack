"""S2: F2-06 (proxies, frame angle-sort de dayz-proxy-align) y
F2-07 (Recipe JSON v1 scoped al inspector, D7)."""

import json

import pytest

from builders import (add_proxy_triangle, build_cube_p3d,
                      build_multilod_v2_p3d)
from helpers import read_p3d, write_bytes


# 90 grados alrededor de Y: filas x,y,z local->world
ROT_Y90 = ((0.0, 0.0, -1.0), (0.0, 1.0, 0.0), (1.0, 0.0, 0.0))


# ---- PROXY-POS (F2-06) -------------------------------------------------------

def test_proxy_pos_roundtrip_exact(fork):
    """PROXY-POS: add_proxy -> save -> get_proxies: path/index exactos,
    anchor == f32(origin), frame == R (tolerancia f32), inambiguo."""
    p3d = build_multilod_v2_p3d(fork)
    vis = p3d.get_lod("visual")
    origin = (0.25, 0.5, -0.75)
    name = vis.add_proxy("\\dz\\weapons\\attachments\\suppressor",
                         index=2, origin=origin, rotation=ROT_Y90)
    assert name == "proxy:\\dz\\weapons\\attachments\\suppressor.002"

    reread = read_p3d(fork, write_bytes(p3d))
    proxies = reread.get_lod("visual").get_proxies()
    # el fixture v2 ya trae el proxy legacy flag.001 + el nuevo
    byname = {p["name"]: p for p in proxies}
    got = byname[name]
    assert got["path"] == "\\dz\\weapons\\attachments\\suppressor"
    assert got["index"] == 2
    assert got["ambiguous"] is False
    for j in range(3):
        assert abs(got["anchor"][j] - origin[j]) < 1e-6
        for k in range(3):
            assert abs(got["frame"][j][k] - ROT_Y90[j][k]) < 1e-3


def test_proxy_identity_frame_and_duplicate(fork):
    """Frame identidad por defecto; nombre duplicado -> ValueError."""
    p3d = build_cube_p3d(fork)
    lod = p3d.lods[0]
    lod.add_proxy("\\dz\\data\\proxies\\flag", index=1)
    got = lod.get_proxies()[0]
    ident = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
    for j in range(3):
        assert abs(got["anchor"][j]) < 1e-9
        for k in range(3):
            assert abs(got["frame"][j][k] - ident[j][k]) < 1e-6
    assert got["ambiguous"] is False
    with pytest.raises(ValueError, match="already exists"):
        lod.add_proxy("\\dz\\data\\proxies\\flag", index=1)


def test_proxy_legacy_isosceles_is_ambiguous(fork):
    """El triangulo isosceles legacy (90/45/45) DEBE marcar ambiguous=True
    (proxy_frame.py: empate de angulos -> frame dependiente del orden)."""
    p3d = build_cube_p3d(fork)
    add_proxy_triangle(fork, p3d.lods[0], "proxy:\\dz\\old\\style.001")
    got = p3d.lods[0].get_proxies()[0]
    assert got["ambiguous"] is True


def test_proxy_derive_canonical_inverse(fork):
    """derive_proxy_frame(canonical_proxy_triangle(a, R)) == (a, R)."""
    anchor = (1.0, 2.0, 3.0)
    tri = fork.canonical_proxy_triangle(anchor, ROT_Y90)
    got_anchor, R, ambiguous, deg = fork.derive_proxy_frame(tri)
    assert not ambiguous
    assert deg[0] > deg[1] > deg[2]  # tres angulos distintos
    for j in range(3):
        assert abs(got_anchor[j] - anchor[j]) < 1e-9
        for k in range(3):
            assert abs(R[j][k] - ROT_Y90[j][k]) < 1e-9


# ---- RECIPE-IDEM (F2-07) -----------------------------------------------------

def _deep_equal(a, b, tol=1e-6, path="$"):
    if isinstance(a, dict) and isinstance(b, dict):
        assert set(a) == set(b), "%s: claves %r != %r" % (path, set(a), set(b))
        for k in a:
            _deep_equal(a[k], b[k], tol, "%s.%s" % (path, k))
    elif isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        assert len(a) == len(b), "%s: len %d != %d" % (path, len(a), len(b))
        for i, (x, y) in enumerate(zip(a, b)):
            _deep_equal(x, y, tol, "%s[%d]" % (path, i))
    elif isinstance(a, float) or isinstance(b, float):
        assert abs(float(a) - float(b)) <= tol, "%s: %r != %r" % (path, a, b)
    else:
        assert a == b, "%s: %r != %r" % (path, a, b)


def test_recipe_idem_multilod_v2(fork):
    """RECIPE-IDEM (contrato D7 = lo que extract/build hacen HOY):

    - PUNTO FIJO: to_dict(from_dict(d)) se estabiliza tras UNA vuelta
      (el visual re-emite su pool de vertices deduplicado (pt,normal,uv);
      la segunda vuelta es deep-equal +-1e-6, igual que el inspector);
    - los LODs NO visuales (wireframe) y el Memory son estables YA en la
      primera vuelta, igual que memory_points/axes/referenced_paths.
    """
    p3d = build_multilod_v2_p3d(fork)
    d1 = p3d.to_dict(source_path="multilod_v2.p3d")
    json.dumps(d1)  # JSON-safe
    d2 = fork.P3D.from_dict(d1).to_dict(source_path="multilod_v2.p3d")
    d3 = fork.P3D.from_dict(d2).to_dict(source_path="multilod_v2.p3d")
    _deep_equal(d2, d3)
    # estabilidad primera-vuelta de todo lo que no es el pool del visual
    _deep_equal(d1["lods"][1:], d2["lods"][1:])
    _deep_equal(d1["memory_points"], d2["memory_points"])
    _deep_equal(d1["axes"], d2["axes"])
    _deep_equal(d1["bounding_box"], d2["bounding_box"])
    assert d1["referenced_paths"] == d2["referenced_paths"]
    # y el P3D reconstruido es un MLOD valido y limpio
    p2 = fork.P3D.from_dict(d2)
    reread = read_p3d(fork, write_bytes(p2))
    # Decision 2026-06-07 (plan S3 v2, D-S3-8): from_dict conserva la
    # politica de masa de build.py VERBATIM (geometry + fire_geometry, D7)
    # -> el rebuilt dispara ERR_MASS_ONLY_GEOMETRY (LL-080) POR DISENO.
    # Pin EXACTO: si la politica cambia, este assert falla y la decision
    # se revisita conscientemente. Cualquier otro ERROR invalida el MLOD.
    errors = [f for f in reread.validate() if f.severity == "ERROR"]
    assert [f.code for f in errors] == ["ERR_MASS_ONLY_GEOMETRY"]


def test_recipe_schema_v1_shape(fork):
    """El recipe cumple el shape del schema v1 del inspector."""
    p3d = build_multilod_v2_p3d(fork)
    d = p3d.to_dict(source_path="/x/y/multilod_v2.p3d")
    assert d["meta"] == {"source": "multilod_v2.p3d",
                         "source_path": "/x/y/multilod_v2.p3d",
                         "version": 1, "mode": "audit"}
    types = [l["type"] for l in d["lods"]]
    assert types == ["visual_1", "geometry", "view_geometry",
                     "fire_geometry", "memory"]
    vis = d["lods"][0]
    geo_keys = {"positions", "normals", "uvs", "material_groups"}
    assert set(vis["geometry"]) == geo_keys
    assert len(vis["geometry"]["positions"]) == \
        len(vis["geometry"]["normals"]) == len(vis["geometry"]["uvs"])
    wf = d["lods"][1]["wireframe"]
    assert set(wf) == {"positions", "edges", "faces"}
    assert len(wf["positions"]) == 8 and len(wf["faces"]) == 6
    assert len(wf["edges"]) == 12  # aristas unicas del cubo
    names = {mp["label"] for mp in d["memory_points"]}
    assert "pos center" in names and "box_placing_min" in names
    assert d["bounding_box"] is not None
    assert d["referenced_paths"]["textures"] == ["lf\\data\\stone_co.paa"]
    assert d["referenced_paths"]["materials"] == ["lf\\data\\stone.rvmat"]
    # memory point de 2 selections-1-punto cada una: sin axes (extract
    # solo detecta selections de exactamente 2 puntos)
    assert d["axes"] == {}


def test_recipe_from_dict_mass_policy(fork):
    """from_dict reasigna masa con la politica de build (perdida scoped
    del schema v1): heuristica por densidad ('stone' -> 2600 kg/m3 sobre
    bbox 1 m3 del cubo Geometry)."""
    p3d = build_multilod_v2_p3d(fork)
    d = p3d.to_dict()
    p2 = fork.P3D.from_dict(d)
    geo = p2.get_lod("geometry")
    assert abs(geo.mass - 2600.0) < 1e-6  # NO los 200 originales: scoped
    # override por meta
    d["meta"]["point_mass_default"] = 12.5
    p3 = fork.P3D.from_dict(d)
    assert abs(p3.get_lod("geometry").mass - 12.5 * 8) < 1e-6


def test_recipe_axes_two_point_selection(fork):
    """Una selection de Memory con exactamente 2 puntos produce un axis
    en el recipe (port de extract 292-308)."""
    p3d = build_multilod_v2_p3d(fork)
    mem = p3d.get_lod("memory")
    mem.set_selection("door_axis",
                      point_idx=[0, 1])  # 2 puntos existentes
    d = p3d.to_dict()
    assert "door_axis" in d["axes"]
    ax = d["axes"]["door_axis"]
    assert ax["point_indices"] == [0, 1]
    assert len(ax["points"]) == 2 and ax["length"] > 0
