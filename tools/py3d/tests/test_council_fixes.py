"""Tests de la correctiva del council 2026-08-12 (3 defectos CRITICOS).

Cada test se escribio para fallar ANTES del fix correspondiente:

  FIX-1  _read_asciiz colgaba el proceso ante EOF sin NUL (heredado de
         upstream 7acd58b). El test lleva timeout propio: si el fix no esta,
         falla por timeout en vez de colgar la suite entera.
  FIX-2  el mensaje de ERR_WINDING_INVERTED recomendaba "swap vertices[1]
         and vertices[2]", que invierte un triangulo pero CRUZA un quad.
  FIX-3  el check de winding era relativo al Visual LOD y basado en el
         centroide (asume convexidad): con TODOS los LODs invertidos todo
         era coherente entre si y validate() devolvia [].
"""

import io
import threading

import pytest

import py3d

from builders import build_cube_lod


# --------------------------------------------------------------- helpers

def _invert_winding(lod):
    """Invierte el orden de vertices SIN tocar las normales declaradas.

    Es exactamente lo que produce el export Blender Z-up -> DayZ Y-up: el
    handedness cambia, el winding queda invertido y las facenormals siguen
    apuntando hacia fuera.
    """
    for fa in lod.faces:
        fa.vertices.reverse()


def _model_visual_plus_geometry(invert_all=False):
    model = py3d.P3D()
    vis = build_cube_lod(py3d, resolution=1.0)
    geo = build_cube_lod(py3d, resolution=1.0e13,
                         selection_name="Component01",
                         mass_per_point=25.0,
                         properties=(("autocenter", "0"), ("class", "house")),
                         texture="", material="")
    if invert_all:
        _invert_winding(vis)
        _invert_winding(geo)
    model.lods += [vis, geo]
    return model


def _codes(model):
    return [f.code for f in model.validate()]


# ------------------------------------------------------------- FIX-1

def test_asciiz_sin_nul_lanza_en_vez_de_colgar():
    """EOF sin NUL debe lanzar. Con timeout: si cuelga, el test falla."""
    box = {}

    def target():
        try:
            py3d._read_asciiz(io.BytesIO(b"NO_NUL_HASTA_EOF"))
            box["res"] = "returned"
        except Exception as exc:
            box["res"] = type(exc).__name__

    t = threading.Thread(target=target, daemon=True)
    t.start()
    t.join(5.0)

    assert not t.is_alive(), (
        "_read_asciiz sigue colgado tras 5s con un asciiz sin NUL: el bucle "
        "'while b\"\\0\" not in bts' no termina porque read() devuelve b'' "
        "indefinidamente en EOF")
    assert box.get("res") not in (None, "returned"), (
        "_read_asciiz devolvio en vez de lanzar ante un asciiz sin NUL")


def test_asciiz_valido_sigue_funcionando():
    """El fix no puede cambiar el camino feliz (contrato con upstream)."""
    assert py3d._read_asciiz(io.BytesIO(b"hola\0resto")) == "hola"
    assert py3d._read_asciiz(io.BytesIO(b"\0")) == ""
    # cadena mas larga que el bloque de 1024 bytes
    largo = b"x" * 3000 + b"\0"
    assert py3d._read_asciiz(io.BytesIO(largo)) == "x" * 3000


# ------------------------------------------------------------- FIX-2

def test_mensaje_de_winding_no_recomienda_el_swap_que_cruza_quads():
    """El correctivo canonico es reverse(); el swap cruza los quads."""
    model = py3d.P3D()
    vis = build_cube_lod(py3d, resolution=1.0)
    geo = build_cube_lod(py3d, resolution=1.0e13,
                         selection_name="Component01",
                         properties=(("autocenter", "0"), ("class", "house")),
                         texture="", material="")
    _invert_winding(geo)          # solo el de colision -> inconsistencia real
    model.lods += [vis, geo]

    msgs = [f.msg for f in model.validate() if "WINDING" in f.code]
    assert msgs, "no se emitio ningun finding de winding en el caso inverso"
    for msg in msgs:
        # El predicado busca la RECOMENDACION imperativa ("Fix: swap ..."),
        # no cualquier mencion: el mensaje corregido nombra el swap justo
        # para desaconsejarlo, y eso es deseable.
        assert "Fix: swap vertices" not in msg, (
            "el mensaje sigue recomendando el swap de vertices[1]/[2], que "
            "en un quad [0,1,2,3] produce [0,2,1,3] (cara CRUZADA, no "
            "invertida): %r" % msg)
    assert any("reverse()" in m for m in msgs), (
        "ningun mensaje de winding recomienda face.vertices.reverse(), que "
        "es el correctivo valido para cualquier cardinalidad")


# ------------------------------------------------------------- FIX-3

def test_inversion_global_de_todos_los_lods_se_detecta():
    """El falso negativo que motivo el fork: todo invertido == silencio.

    Con el check relativo al Visual, invertir TODOS los LODs deja el modelo
    coherente consigo mismo y validate() devolvia [].
    """
    codes = _codes(_model_visual_plus_geometry(invert_all=True))
    winding = [c for c in codes if "WINDING" in c]
    assert winding, (
        "modelo con TODOS los LODs invertidos (bug Blender Z-up -> Y-up) no "
        "produjo ningun finding de winding; codes=%r" % codes)


def test_modelo_sano_no_produce_falso_positivo_de_winding():
    """Contra-prueba: el instrumento tiene que poder decir que si."""
    codes = _codes(_model_visual_plus_geometry(invert_all=False))
    errores = [c for c in codes if "WINDING" in c and c.startswith("ERR")]
    assert not errores, (
        "modelo sano marcado con ERROR de winding: %r (codes=%r)"
        % (errores, codes))


def test_la_senal_de_normal_declarada_distingue_ambos_sentidos():
    """La señal B por separado: 100% en el sano, 0% en el invertido.

    Es el test que separa una direccion de la otra. Con el predicado viejo
    (centroide) ambos casos dan lo mismo, porque un modelo enteramente
    invertido es internamente coherente.
    """
    sano = build_cube_lod(py3d, resolution=1.0)
    invertido = build_cube_lod(py3d, resolution=1.0)
    _invert_winding(invertido)

    pct_sano = py3d._pct_normal_agreement(sano)
    pct_inv = py3d._pct_normal_agreement(invertido)

    assert pct_sano == pytest.approx(100.0), (
        "cubo sano deberia dar 100%% de acuerdo winding<->normal declarada, "
        "dio %r" % pct_sano)
    assert pct_inv == pytest.approx(0.0), (
        "cubo con winding invertido deberia dar 0%%, dio %r" % pct_inv)


def test_coherencia_de_aristas_en_malla_cerrada():
    """La señal A: en una malla cerrada bien construida, cada arista
    compartida se recorre en sentidos opuestos por sus dos caras."""
    cubo = build_cube_lod(py3d, resolution=1.0)
    assert py3d._pct_edge_coherence(cubo) == pytest.approx(100.0)
