"""Fase 04a: ciclo de vida estricto de proxies MLOD."""

import math
import re

import pytest

from builders import build_cube_p3d
from helpers import read_p3d, write_bytes


IDENTITY = (
    (1.0, 0.0, 0.0),
    (0.0, 1.0, 0.0),
    (0.0, 0.0, 1.0),
)
ENGINE_CORRECTION = (
    (-1.0, 0.0, 0.0),
    (0.0, 0.0, 1.0),
    (0.0, 1.0, 0.0),
)
ROT_Y90 = (
    (0.0, 0.0, -1.0),
    (0.0, 1.0, 0.0),
    (1.0, 0.0, 0.0),
)


def _matrix_close(actual, expected, tolerance=1e-9):
    for row_actual, row_expected in zip(actual, expected):
        assert tuple(row_actual) == pytest.approx(
            tuple(row_expected), abs=tolerance
        )


def _lod_snapshot(lod):
    point_index = {id(point): index for index, point in enumerate(lod.points)}
    face_index = {id(face): index for index, face in enumerate(lod.faces)}
    return {
        "points": [
            (tuple(point.coords), point.flags, point.mass)
            for point in lod.points
        ],
        "facenormals": [tuple(normal) for normal in lod.facenormals],
        "faces": [
            (
                tuple(
                    (vertex.point_index, vertex.normal_index, tuple(vertex.uv))
                    for vertex in face.vertices
                ),
                face.flags,
                face.texture,
                face.material,
            )
            for face in lod.faces
        ],
        "sharp_edges": list(lod.sharp_edges),
        "properties": list(lod.properties.items()),
        "selections": [
            (
                name,
                tuple(
                    sorted(
                        (point_index[id(point)], weight)
                        for point, weight in selection.points.items()
                    )
                ),
                tuple(
                    sorted(
                        (face_index[id(face)], weight)
                        for face, weight in selection.faces.items()
                    )
                ),
                selection.all_points is lod.points,
                selection.all_faces is lod.faces,
            )
            for name, selection in lod.selections.items()
        ],
    }


def _proxy_objects(lod, name):
    selection = lod.selections[name]
    face = next(iter(selection.faces))
    points = tuple(lod.points[vertex.point_index] for vertex in face.vertices)
    normal_index = face.vertices[0].normal_index
    return selection, face, points, normal_index


def _add_unrelated_triangle_after_proxy(fork, lod):
    base = len(lod.points)
    for coords in (
        (10.0, 0.0, 0.0),
        (10.0, 1.0, 0.0),
        (10.0, 0.0, 1.0),
    ):
        point = fork.Point()
        point.coords = coords
        lod.points.append(point)
    lod.facenormals.append((1.0, 0.0, 0.0))
    normal_index = len(lod.facenormals) - 1
    face = fork.Face(lod.points, lod.facenormals)
    for point_index in range(base, base + 3):
        vertex = fork.Vertex(lod.points, lod.facenormals)
        vertex.point_index = point_index
        vertex.normal_index = normal_index
        vertex.uv = (0.0, 0.0)
        face.vertices.append(vertex)
    lod.faces.append(face)
    selection = lod.new_selection("after_proxy")
    selection.points = {lod.points[index]: 1 for index in range(base, base + 3)}
    selection.faces = {face: 1}
    lod.sharp_edges.append((base, base + 2))
    return selection, face, tuple(lod.points[base:base + 3])


def test_proxy_frame_conversion_uses_involutive_dayz_correction(fork):
    """Rompe si raw↔engine omite o aplica por el lado incorrecto P'."""
    assert fork.PROXY_ENGINE_CORRECTION == ENGINE_CORRECTION
    _matrix_close(fork.proxy_frame_to_engine(IDENTITY), ENGINE_CORRECTION)
    _matrix_close(fork.proxy_frame_from_engine(IDENTITY), ENGINE_CORRECTION)
    _matrix_close(
        fork.proxy_frame_from_engine(fork.proxy_frame_to_engine(ROT_Y90)),
        ROT_Y90,
    )
    _matrix_close(
        fork.proxy_frame_to_engine(fork.proxy_frame_from_engine(ROT_Y90)),
        ROT_Y90,
    )


@pytest.mark.parametrize(
    "rotation",
    [
        ((1.0, 0.0), (0.0, 1.0)),
        ((2.0, 0.0, 0.0), (0.0, 2.0, 0.0), (0.0, 0.0, 2.0)),
        ((1.0, 0.25, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        ((-1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        ((math.nan, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
    ],
)
def test_canonical_proxy_triangle_rejects_invalid_rotation(fork, rotation):
    """Rompe si una matriz no-rotación puede llegar a geometría proxy."""
    with pytest.raises(ValueError, match="rotation"):
        fork.canonical_proxy_triangle((0.0, 0.0, 0.0), rotation=rotation)


@pytest.mark.parametrize("scale", [0.0, -0.001, math.nan, math.inf, 1e-50])
def test_canonical_proxy_triangle_rejects_invalid_or_f32_degenerate_scale(
    fork, scale
):
    """Rompe si el scale produce un triángulo nulo tras serializar float32."""
    with pytest.raises(ValueError, match="scale"):
        fork.canonical_proxy_triangle((0.0, 0.0, 0.0), scale=scale)


@pytest.mark.parametrize(
    ("path", "index", "error_type", "message"),
    [
        ("", 1, ValueError, "path"),
        ("\\lf\\bad\0path", 1, ValueError, "NUL"),
        ("\\lf\\proxy.p3d", 1, ValueError, "p3d"),
        ("\\lf\\PROXY.P3D", 1, ValueError, "p3d"),
        ("\\lf\\proxy", True, TypeError, "index"),
        ("\\lf\\proxy", 1.0, TypeError, "index"),
        ("\\lf\\proxy", 0, ValueError, "index"),
        ("\\lf\\proxy", -1, ValueError, "index"),
    ],
)
def test_add_proxy_rejects_bad_path_or_index_without_mutation(
    fork, path, index, error_type, message
):
    """Rompe si la validación ocurre después de tocar listas del LOD."""
    lod = build_cube_p3d(fork).lods[0]
    before = _lod_snapshot(lod)
    with pytest.raises(error_type, match=message):
        lod.add_proxy(path, index=index)
    assert _lod_snapshot(lod) == before


@pytest.mark.parametrize(
    ("rotation", "scale"),
    [
        (((-1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)), 0.001),
        (IDENTITY, 0.0),
        (IDENTITY, math.nan),
    ],
)
def test_add_proxy_rejects_bad_transform_without_mutation(
    fork, rotation, scale
):
    """Rompe si un transform inválido deja puntos/normales/caras parciales."""
    lod = build_cube_p3d(fork).lods[0]
    before = _lod_snapshot(lod)
    with pytest.raises(ValueError):
        lod.add_proxy(
            "\\lf\\proxy",
            index=1,
            rotation=rotation,
            scale=scale,
        )
    assert _lod_snapshot(lod) == before


def test_raw_default_keeps_legacy_triangle_and_frame_descriptor(fork):
    """Rompe si 1.4.0 cambia el significado del positional raw de 1.3.0."""
    triangle = fork.canonical_proxy_triangle(
        (1.0, 2.0, 3.0),
        ROT_Y90,
        0.01,
    )
    assert triangle == [
        [1.0, 2.0, 3.0],
        [1.0, 2.01, 3.0],
        [1.02, 2.0, 3.0],
    ]
    lod = build_cube_p3d(fork).lods[0]
    lod.add_proxy(
        "\\lf\\raw",
        3,
        (1.0, 2.0, 3.0),
        ROT_Y90,
        0.01,
    )
    descriptor = lod.get_proxies()[0]
    _matrix_close(descriptor["frame"], ROT_Y90, tolerance=1e-9)


def test_get_proxies_exposes_both_frames_and_scale(fork):
    """Rompe si el descriptor confunde raw con engine o pierde la escala."""
    lod = build_cube_p3d(fork).lods[0]
    name = lod.add_proxy(
        "\\lf\\raw",
        index=4,
        origin=(0.25, -0.5, 0.75),
        rotation=ROT_Y90,
        scale=0.025,
    )
    descriptor = {item["name"]: item for item in lod.get_proxies()}[name]
    expected_engine = (
        (0.0, 0.0, 1.0),
        (1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
    )
    _matrix_close(descriptor["frame"], ROT_Y90)
    _matrix_close(descriptor["raw_frame"], ROT_Y90)
    _matrix_close(descriptor["engine_frame"], expected_engine)
    assert descriptor["scale"] == pytest.approx(0.025, abs=1e-12)


def test_engine_space_identity_roundtrips_as_engine_identity(fork):
    """Rompe si add_proxy aplica la corrección DayZ cero o dos veces."""
    lod = build_cube_p3d(fork).lods[0]
    name = lod.add_proxy(
        "\\lf\\engine",
        index=1,
        rotation=IDENTITY,
        scale=0.01,
        space="engine",
    )
    descriptor = {item["name"]: item for item in lod.get_proxies()}[name]
    _matrix_close(descriptor["raw_frame"], ENGINE_CORRECTION)
    _matrix_close(descriptor["engine_frame"], IDENTITY)


def test_proxy_descriptors_survive_save_reload(fork):
    """Rompe si los campos nuevos dependen de objetos en memoria no serializados."""
    p3d = build_cube_p3d(fork)
    lod = p3d.lods[0]
    name = lod.add_proxy(
        "\\lf\\roundtrip",
        index=12,
        origin=(0.5, -0.25, 1.25),
        rotation=ROT_Y90,
        scale=0.02,
    )
    reread = read_p3d(fork, write_bytes(p3d))
    descriptor = {
        item["name"]: item for item in reread.lods[0].get_proxies(strict=True)
    }[name]
    assert descriptor["anchor"] == pytest.approx((0.5, -0.25, 1.25), abs=1e-6)
    _matrix_close(descriptor["raw_frame"], ROT_Y90, tolerance=1e-3)
    assert descriptor["scale"] == pytest.approx(0.02, abs=1e-6)


@pytest.mark.parametrize(
    "mutation",
    [
        "four_points",
        "no_face",
        "wrong_face_points",
        "fractional_weight",
        "invalid_point_index",
        "nonfinite_coords",
        "nonfinite_normal",
        "normal_mismatch",
        "degenerate",
    ],
)
def test_strict_enumeration_rejects_each_malformed_proxy(fork, mutation):
    """Rompe si strict=True filtra anatomía mala como el modo legacy."""
    lod = build_cube_p3d(fork).lods[0]
    name = lod.add_proxy("\\lf\\strict", index=1)
    selection = lod.selections[name]
    if mutation == "four_points":
        selection.points[lod.points[0]] = 1
        assert lod.get_proxies() == []
    elif mutation == "no_face":
        selection.faces = {}
        assert len(lod.get_proxies()) == 1
    elif mutation == "wrong_face_points":
        proxy_point = next(iter(selection.points))
        del selection.points[proxy_point]
        selection.points[lod.points[0]] = 1
        assert len(lod.get_proxies()) == 1
    elif mutation == "fractional_weight":
        first = next(iter(selection.points))
        selection.points[first] = 0.5
        assert len(lod.get_proxies()) == 1
    elif mutation == "invalid_point_index":
        next(iter(selection.faces)).vertices[0].point_index = -1
    elif mutation == "nonfinite_coords":
        next(iter(selection.points)).coords = (math.nan, 0.0, 0.0)
    elif mutation == "nonfinite_normal":
        normal_index = next(iter(selection.faces)).vertices[0].normal_index
        lod.facenormals[normal_index] = (math.nan, 0.0, 0.0)
    elif mutation == "normal_mismatch":
        normal_index = next(iter(selection.faces)).vertices[0].normal_index
        lod.facenormals[normal_index] = (0.0, 1.0, 0.0)
    else:
        for index, point in enumerate(selection.points):
            point.coords = (float(index), 0.0, 0.0)
    with pytest.raises(ValueError, match=re.escape(repr(name))):
        lod.get_proxies(strict=True)


def test_align_proxy_mutates_only_exclusive_geometry_in_place(fork):
    """Rompe si align recrea objetos/bindings o toca anatomia no relacionada."""
    lod = build_cube_p3d(fork).lods[0]
    lod.sharp_edges[:] = [(0, 1), (2, 3)]
    name = lod.add_proxy("\\lf\\aligned", index=7)
    selection, face, points, normal_index = _proxy_objects(lod, name)

    owning_lists = (
        id(lod.points),
        id(lod.facenormals),
        id(lod.faces),
        id(lod.selections),
    )
    counts = (
        len(lod.points),
        len(lod.facenormals),
        len(lod.faces),
        len(lod.selections),
    )
    unrelated = {
        "points": tuple(
            (id(point), tuple(point.coords), point.flags, point.mass)
            for point in lod.points[:-3]
        ),
        "normals": tuple(lod.facenormals[:normal_index]),
        "faces": tuple(id(item) for item in lod.faces if item is not face),
        "sharp_edges": tuple(lod.sharp_edges),
        "component_points": tuple(lod.selections["Component01"].points),
        "component_faces": tuple(lod.selections["Component01"].faces),
    }

    result = lod.align_proxy(
        name,
        origin=(0.25, -0.5, 0.75),
        rotation=IDENTITY,
        scale=0.02,
        space="engine",
    )

    assert result == name
    assert lod.selections[name] is selection
    assert next(iter(selection.faces)) is face
    assert tuple(lod.points[v.point_index] for v in face.vertices) == points
    assert face.vertices[0].normal_index == normal_index
    assert all(v.normal_index == normal_index for v in face.vertices)
    assert (
        id(lod.points),
        id(lod.facenormals),
        id(lod.faces),
        id(lod.selections),
    ) == owning_lists
    assert (
        len(lod.points),
        len(lod.facenormals),
        len(lod.faces),
        len(lod.selections),
    ) == counts
    assert tuple(
        (id(point), tuple(point.coords), point.flags, point.mass)
        for point in lod.points[:-3]
    ) == unrelated["points"]
    assert tuple(lod.facenormals[:normal_index]) == unrelated["normals"]
    assert tuple(id(item) for item in lod.faces if item is not face) == \
        unrelated["faces"]
    assert tuple(lod.sharp_edges) == unrelated["sharp_edges"]
    assert tuple(lod.selections["Component01"].points) == \
        unrelated["component_points"]
    assert tuple(lod.selections["Component01"].faces) == \
        unrelated["component_faces"]

    descriptor = {
        item["name"]: item for item in lod.get_proxies(strict=True)
    }[name]
    assert descriptor["anchor"] == pytest.approx((0.25, -0.5, 0.75))
    _matrix_close(descriptor["engine_frame"], IDENTITY)
    assert descriptor["scale"] == pytest.approx(0.02)


def test_aligned_proxy_descriptor_survives_save_reload(fork):
    """Rompe si align solo actualiza estado que MLOD no serializa."""
    p3d = build_cube_p3d(fork)
    lod = p3d.lods[0]
    name = lod.add_proxy("\\lf\\persist-align", index=8)
    lod.align_proxy(
        name,
        origin=(-0.25, 0.75, 1.5),
        rotation=ROT_Y90,
        scale=0.015,
    )

    reread = read_p3d(fork, write_bytes(p3d))
    descriptor = {
        item["name"]: item
        for item in reread.lods[0].get_proxies(strict=True)
    }[name]
    assert descriptor["anchor"] == pytest.approx(
        (-0.25, 0.75, 1.5), abs=1e-6
    )
    _matrix_close(descriptor["raw_frame"], ROT_Y90, tolerance=1e-3)
    assert descriptor["scale"] == pytest.approx(0.015, abs=1e-6)


@pytest.mark.parametrize(
    "sharing",
    [
        "point_face",
        "point_selection",
        "face_selection",
        "normal_face",
        "sharp_edge",
    ],
)
def test_align_proxy_rejects_shared_anatomy_atomically(fork, sharing):
    """Rompe si align puede modificar datos que otro objeto tambien posee."""
    lod = build_cube_p3d(fork).lods[0]
    name = lod.add_proxy("\\lf\\shared", index=1)
    selection, face, points, normal_index = _proxy_objects(lod, name)
    proxy_point_index = lod.points.index(points[0])

    if sharing == "point_face":
        lod.faces[0].vertices[0].point_index = proxy_point_index
    elif sharing == "point_selection":
        lod.selections["Component01"].points[points[0]] = 1
    elif sharing == "face_selection":
        lod.selections["Component01"].faces[face] = 1
    elif sharing == "normal_face":
        lod.faces[0].vertices[0].normal_index = normal_index
    else:
        lod.sharp_edges.append((0, proxy_point_index))

    before = _lod_snapshot(lod)
    with pytest.raises(ValueError, match="shared"):
        lod.align_proxy(
            name,
            origin=(1.0, 2.0, 3.0),
            rotation=ROT_Y90,
            scale=0.01,
        )
    assert _lod_snapshot(lod) == before


@pytest.mark.parametrize(
    ("name", "origin", "rotation", "scale", "space", "message"),
    [
        ("proxy:\\lf\\missing.001", (0.0, 0.0, 0.0), IDENTITY, 0.001,
         "raw", "does not exist"),
        ("not-a-proxy", (0.0, 0.0, 0.0), IDENTITY, 0.001,
         "raw", "name"),
        ("proxy:\\lf\\align.001", (math.nan, 0.0, 0.0), IDENTITY, 0.001,
         "raw", "anchor"),
        ("proxy:\\lf\\align.001", (0.0, 0.0, 0.0), IDENTITY, 0.0,
         "raw", "scale"),
        ("proxy:\\lf\\align.001", (0.0, 0.0, 0.0), IDENTITY, 0.001,
         "world", "space"),
    ],
)
def test_align_proxy_rejects_invalid_input_without_mutation(
    fork, name, origin, rotation, scale, space, message
):
    """Rompe si la validacion de align sucede despues de la primera escritura."""
    lod = build_cube_p3d(fork).lods[0]
    lod.add_proxy("\\lf\\align", index=1)
    before = _lod_snapshot(lod)
    with pytest.raises(ValueError, match=message):
        lod.align_proxy(
            name,
            origin=origin,
            rotation=rotation,
            scale=scale,
            space=space,
        )
    assert _lod_snapshot(lod) == before


def test_remove_proxy_deletes_exact_anatomy_and_remaps_survivors(fork):
    """Rompe si remove deja indices colgantes o reemplaza listas/bindings."""
    lod = build_cube_p3d(fork).lods[0]
    name = lod.add_proxy("\\lf\\remove", index=9)
    proxy_selection, proxy_face, proxy_points, _normal_index = \
        _proxy_objects(lod, name)
    unrelated_selection, unrelated_face, unrelated_points = \
        _add_unrelated_triangle_after_proxy(fork, lod)

    owning_lists = (
        id(lod.points),
        id(lod.facenormals),
        id(lod.faces),
        id(lod.selections),
        id(lod.sharp_edges),
    )
    counts = (
        len(lod.points),
        len(lod.facenormals),
        len(lod.faces),
        len(lod.selections),
    )
    component = lod.selections["Component01"]
    component_points = tuple(component.points)
    component_faces = tuple(component.faces)
    normal_pool = tuple(lod.facenormals)

    result = lod.remove_proxy(name)

    assert result == name
    assert name not in lod.selections
    assert proxy_selection not in lod.selections.values()
    assert proxy_face not in lod.faces
    assert all(point not in lod.points for point in proxy_points)
    assert (
        id(lod.points),
        id(lod.facenormals),
        id(lod.faces),
        id(lod.selections),
        id(lod.sharp_edges),
    ) == owning_lists
    assert (
        len(lod.points),
        len(lod.facenormals),
        len(lod.faces),
        len(lod.selections),
    ) == (counts[0] - 3, counts[1], counts[2] - 1, counts[3] - 1)
    assert tuple(lod.facenormals) == normal_pool

    assert lod.selections["after_proxy"] is unrelated_selection
    assert next(iter(unrelated_selection.faces)) is unrelated_face
    assert tuple(unrelated_selection.points) == unrelated_points
    assert [vertex.point_index for vertex in unrelated_face.vertices] == \
        [8, 9, 10]
    assert tuple(lod.points[index] for index in (8, 9, 10)) == \
        unrelated_points
    assert lod.sharp_edges == [(8, 10)]
    assert lod.selections["Component01"] is component
    assert tuple(component.points) == component_points
    assert tuple(component.faces) == component_faces
    assert all(
        selection.all_points is lod.points and selection.all_faces is lod.faces
        for selection in lod.selections.values()
    )
    assert lod.get_proxies(strict=True) == []


def test_removed_proxy_stays_removed_after_save_reload(fork):
    """Rompe si remove solo limpia objetos Python pero no el MLOD persistido."""
    p3d = build_cube_p3d(fork)
    lod = p3d.lods[0]
    name = lod.add_proxy("\\lf\\persist-remove", index=2)
    _add_unrelated_triangle_after_proxy(fork, lod)
    lod.remove_proxy(name)

    reread = read_p3d(fork, write_bytes(p3d))
    assert reread.lods[0].get_proxies(strict=True) == []
    assert len(reread.lods[0].points) == 11
    assert len(reread.lods[0].faces) == 7
    assert reread.lods[0].sharp_edges == [(8, 10)]


def test_remove_proxy_remaps_a_surviving_proxy_for_later_strict_use(fork):
    """Rompe si el primer remove invalida indices del siguiente proxy."""
    lod = build_cube_p3d(fork).lods[0]
    first = lod.add_proxy("\\lf\\first", index=1)
    second = lod.add_proxy(
        "\\lf\\second",
        index=2,
        origin=(1.0, 2.0, 3.0),
        scale=0.01,
    )

    assert lod.remove_proxy(first) == first
    descriptors = {
        item["name"]: item for item in lod.get_proxies(strict=True)
    }
    assert set(descriptors) == {second}
    assert descriptors[second]["anchor"] == pytest.approx((1.0, 2.0, 3.0))
    assert lod.remove_proxy(second) == second
    assert lod.get_proxies(strict=True) == []


@pytest.mark.parametrize(
    "sharing",
    [
        "point_face",
        "point_selection",
        "face_selection",
        "normal_face",
        "sharp_edge",
    ],
)
def test_remove_proxy_rejects_shared_anatomy_atomically(fork, sharing):
    """Rompe si remove borra anatomia que tambien pertenece a otro objeto."""
    lod = build_cube_p3d(fork).lods[0]
    name = lod.add_proxy("\\lf\\shared-remove", index=1)
    selection, face, points, normal_index = _proxy_objects(lod, name)
    proxy_point_index = lod.points.index(points[0])

    if sharing == "point_face":
        lod.faces[0].vertices[0].point_index = proxy_point_index
    elif sharing == "point_selection":
        lod.selections["Component01"].points[points[0]] = 1
    elif sharing == "face_selection":
        lod.selections["Component01"].faces[face] = 1
    elif sharing == "normal_face":
        lod.faces[0].vertices[0].normal_index = normal_index
    else:
        lod.sharp_edges.append((0, proxy_point_index))

    before = _lod_snapshot(lod)
    with pytest.raises(ValueError, match="shared"):
        lod.remove_proxy(name)
    assert _lod_snapshot(lod) == before


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("invalid_face_index", "invalid point index"),
        ("malformed_edge", "malformed sharp edge"),
        ("invalid_edge_index", "invalid point index"),
        ("selection_alias", "shared"),
        ("duplicate_point_slot", "exactly once"),
        ("duplicate_face_slot", "exactly once"),
    ],
)
def test_remove_proxy_validates_complete_remap_plan_before_mutation(
    fork, mutation, message
):
    """Rompe si un target de remap invalido provoca una eliminacion parcial."""
    lod = build_cube_p3d(fork).lods[0]
    name = lod.add_proxy("\\lf\\atomic-remove", index=1)
    selection, face, points, _normal_index = _proxy_objects(lod, name)

    if mutation == "invalid_face_index":
        lod.faces[0].vertices[0].point_index = len(lod.points)
    elif mutation == "malformed_edge":
        lod.sharp_edges.append((0, 1, 2))
    elif mutation == "invalid_edge_index":
        lod.sharp_edges.append((0, len(lod.points)))
    elif mutation == "selection_alias":
        lod.selections["alias"] = selection
    elif mutation == "duplicate_point_slot":
        lod.points.append(points[0])
    else:
        lod.faces.append(face)

    before = _lod_snapshot(lod)
    with pytest.raises(ValueError, match=message):
        lod.remove_proxy(name)
    assert _lod_snapshot(lod) == before


@pytest.mark.parametrize(
    ("name", "message"),
    [
        ("not-a-proxy", "name"),
        ("proxy:\\lf\\missing.001", "does not exist"),
    ],
)
def test_remove_proxy_rejects_invalid_name_without_mutation(
    fork, name, message
):
    """Rompe si validar el nombre sucede despues de tocar el LOD."""
    lod = build_cube_p3d(fork).lods[0]
    lod.add_proxy("\\lf\\remove", index=1)
    before = _lod_snapshot(lod)
    with pytest.raises(ValueError, match=message):
        lod.remove_proxy(name)
    assert _lod_snapshot(lod) == before
