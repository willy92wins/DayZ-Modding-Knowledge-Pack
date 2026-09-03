"""S5 (F1-10/F1-11): fidelidad del bloque TAGG en round-trip.

Dos tags que el codec descartaba silenciosamente:

* ``#UVSet#`` con id != 0. El lector los ignoraba por completo y el escritor
  emitia siempre exactamente uno (id 0, derivado de ``Vertex.uv``), asi que
  un modelo con segundo canal UV lo perdia al releer y guardar.
* ``#Selected#`` (estado de seleccion del editor de Object Builder). No se
  leia ni se escribia nunca.

Ademas el escritor omitia ``#UVSet#`` cuando el LOD no tenia caras, asi que
los LOD point-only (Memory, LandContact) salian sin ningun tag especial.

Evidencia del formato (ficheros MLOD de BI, NO versionados aqui - politica
D6, los tests usan fixtures sinteticos):

  WeaponSpecialLODs.p3d  LOD0 resolution : #UVSet#[id=0] + #UVSet#[id=1]
  InfectedSpecialLODs.p3d LOD1 Memory     : #UVSet#[id=0, 4 bytes], 0 caras
  WeaponSpecialLODs.p3d  LOD1 Geometry   : #Selected#[14 b] = 8 pts + 6 caras

Nota sobre el ORDEN de los tags: NO es contractual. Los dos ficheros de BI
citados arriba discrepan entre si (uno emite #UVSet# al final, el otro al
principio), asi que estos tests comprueban presencia, id y tamano, nunca
posicion.
"""

import io
import struct

import pytest  # noqa: F401

from builders import build_cube_lod, build_memory_lod, build_multilod_p3d
from helpers import f32, read_p3d, write_bytes


def tagg_blocks(data, lod_index=0):
    """[(nombre, payload)] del bloque TAGG de un LOD, en orden de fichero."""
    f = io.BytesIO(data)
    assert f.read(4) == b"MLOD"
    _version, num_lods = struct.unpack("<LL", f.read(8))
    assert lod_index < num_lods
    for current in range(num_lods):
        assert f.read(4) == b"P3DM"
        _major, _minor, num_points, num_normals, num_faces, _flags = \
            struct.unpack("<6L", f.read(24))
        f.seek(num_points * 16 + num_normals * 12, 1)
        for _ in range(num_faces):
            struct.unpack("<L", f.read(4))
            f.seek(68, 1)  # 4 vertices * 16 bytes + face flags
            for _ in range(2):  # texture, material (asciiz)
                while f.read(1) != b"\0":
                    pass
        assert f.read(4) == b"TAGG"
        blocks = []
        while True:
            f.seek(1, 1)  # active byte
            name = b""
            while True:
                c = f.read(1)
                if c == b"\0":
                    break
                name += c
            name = name.decode("utf-8")
            size = struct.unpack("<L", f.read(4))[0]
            payload = f.read(size)
            if name == "#EndOfFile#":
                break
            blocks.append((name, payload))
        f.seek(4, 1)  # resolution
        if current == lod_index:
            return blocks
    raise AssertionError("unreachable")


def uv_sets(blocks):
    """{id: [(u, v), ...]} de todos los tags #UVSet# del bloque."""
    out = {}
    for name, payload in blocks:
        if name != "#UVSet#":
            continue
        uv_id = struct.unpack("<L", payload[:4])[0]
        out[uv_id] = [struct.unpack("<ff", payload[i*8+4:i*8+12])
                      for i in range(int((len(payload) - 4) / 8))]
    return out


def selected_payloads(blocks):
    return [p for n, p in blocks if n == "#Selected#"]


# --------------------------------------------------------------- F1-10 UV sets

def test_point_only_lod_still_writes_uvset_id0(fork):
    """Un Memory LOD (0 caras) emite #UVSet# con payload de 4 bytes.

    Es lo que hacen los MLOD de BI; omitirlo dejaba el LOD sin ningun tag
    especial y estructuralmente distinto de cualquier referencia vanilla.
    """
    p3d = fork.P3D()
    p3d.lods.append(build_memory_lod(
        fork, [("aimpoint", (0.0, 0.0, 0.0)), ("muzzle", (0.0, 1.0, 0.0))]))

    blocks = tagg_blocks(write_bytes(p3d))

    assert uv_sets(blocks) == {0: []}
    payload = [p for n, p in blocks if n == "#UVSet#"][0]
    assert len(payload) == 4


def test_extra_uv_set_survives_round_trip(fork):
    """El canal UV id=1 sobrevive read -> write con sus valores intactos."""
    p3d = fork.P3D()
    lod = build_cube_lod(fork)
    p3d.lods.append(lod)
    loops = lod.num_vertices
    uv1 = [(i * 0.01, i * 0.02) for i in range(loops)]
    lod.extra_uv_sets[1] = uv1

    once = write_bytes(p3d)
    reread = read_p3d(fork, once)
    twice = write_bytes(reread)

    want = [(f32(u), f32(v)) for u, v in uv1]
    assert reread.lods[0].extra_uv_sets[1] == want
    assert uv_sets(tagg_blocks(twice))[1] == want
    assert once == twice, "round-trip debe ser byte-identico"


def test_uv_set_0_is_not_duplicated_into_extra(fork):
    """El id 0 leido del fichero no se duplica en extra_uv_sets.

    Vertex.uv sigue siendo la fuente de verdad del canal 0; guardarlo
    tambien en extra_uv_sets emitiria el tag dos veces.
    """
    p3d = fork.P3D()
    p3d.lods.append(build_cube_lod(fork))

    reread = read_p3d(fork, write_bytes(p3d))

    assert reread.lods[0].extra_uv_sets == {}
    assert list(uv_sets(tagg_blocks(write_bytes(reread)))) == [0]


def test_extra_uv_set_is_resized_to_current_loop_count(fork):
    """Si la geometria cambio tras leer, el canal extra se ajusta al nuevo
    numero de loops en vez de emitir un tag de tamano invalido."""
    p3d = fork.P3D()
    lod = build_cube_lod(fork)
    p3d.lods.append(lod)
    lod.extra_uv_sets[1] = [(0.5, 0.5)] * 3  # deliberadamente corto

    got = uv_sets(tagg_blocks(write_bytes(p3d)))[1]

    assert len(got) == lod.num_vertices
    assert got[:3] == [(0.5, 0.5)] * 3
    assert got[3:] == [(0.0, 0.0)] * (lod.num_vertices - 3)


def test_canon_divergence_is_only_point_only_uvset(fork, upstream):
    """La ruptura de CANON-IDENT en `multilod` es exactamente esta y nada mas.

    F1-10 aparta deliberadamente el fork de upstream, asi que la divergencia
    se fija aqui en lugar de relajar test_s1a_contract.test_canon_ident: el
    unico delta permitido es un tag #UVSet# de 4 bytes en cada LOD sin caras.
    Cualquier otra diferencia (bytes de mas en un LOD con caras, tags
    reordenados, tamanos distintos) hace fallar este test.
    """
    fork_bytes = write_bytes(build_multilod_p3d(fork))
    up_bytes = write_bytes(build_multilod_p3d(upstream))

    num_lods = struct.unpack("<L", fork_bytes[8:12])[0]
    assert struct.unpack("<L", up_bytes[8:12])[0] == num_lods

    point_only = 0
    for i in range(num_lods):
        mine = tagg_blocks(fork_bytes, i)
        theirs = tagg_blocks(up_bytes, i)
        if any(n == "#UVSet#" and len(p) == 4 for n, p in mine):
            point_only += 1
            # El unico bloque de mas es ese UV set vacio.
            assert [b for b in mine if b != ("#UVSet#", b"\0" * 4)] == theirs
        else:
            assert mine == theirs

    assert point_only == 1, "el fixture multilod trae exactamente un Memory LOD"
    # 1 byte active + len("#UVSet#\0") + 4 de tamano + 4 de payload = 17.
    assert len(fork_bytes) - len(up_bytes) == point_only * 17


# -------------------------------------------------------------- F1-11 Selected

def test_selected_tag_survives_round_trip(fork):
    """#Selected# se conserva con su payload exacto si la geometria no cambio."""
    p3d = fork.P3D()
    lod = build_cube_lod(fork)
    p3d.lods.append(lod)
    want = len(lod.points) + len(lod.faces)
    payload = bytes(range(want))
    lod.selected = payload

    once = write_bytes(p3d)
    reread = read_p3d(fork, once)

    assert reread.lods[0].selected == payload
    assert selected_payloads(tagg_blocks(once)) == [payload]
    assert once == write_bytes(reread), "round-trip debe ser byte-identico"


def test_selected_tag_absent_when_never_set(fork):
    """Un LOD construido desde cero no inventa el tag."""
    p3d = fork.P3D()
    p3d.lods.append(build_cube_lod(fork))

    assert selected_payloads(tagg_blocks(write_bytes(p3d))) == []


def test_stale_selected_is_regenerated_at_correct_size(fork):
    """Si el LOD se redimensiono tras leer, el payload viejo NO se reemite.

    El tamano de #Selected# es contractual (points + faces); escribir uno
    obsoleto desincroniza al lector para el resto del bloque TAGG.
    """
    p3d = fork.P3D()
    lod = build_cube_lod(fork)
    p3d.lods.append(lod)
    lod.selected = b"\xff" * (len(lod.points) + len(lod.faces))

    # La geometria crece bajo el tag. Se anade un punto suelto en vez de
    # quitar uno: quitarlo dejaria caras y selections apuntando a un punto
    # ausente, que es un fallo distinto (guard F1-05, ya cubierto por
    # test_s1b_stale_save) y enmascararia lo que se quiere comprobar aqui.
    extra = fork.Point()
    extra.coords = (2.0, 2.0, 2.0)
    lod.points.append(extra)

    payloads = selected_payloads(tagg_blocks(write_bytes(p3d)))
    want = len(lod.points) + len(lod.faces)
    assert payloads == [b"\0" * want]
    assert read_p3d(fork, write_bytes(p3d)).lods[0].selected == b"\0" * want
