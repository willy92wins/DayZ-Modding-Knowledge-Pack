"""S1A: guards F1-01 (Selection ctor), F1-02 (weights), F1-06 (properties)."""

import io

import pytest

from builders import build_cube_p3d
from helpers import read_p3d, write_bytes


# ---- F1-01 / Q1 -------------------------------------------------------------

def test_q1_neg_selection_noargs_raises_actionable(fork):
    """Q1-NEG: Selection() sin args -> TypeError con mensaje guia."""
    with pytest.raises(TypeError) as ei:
        fork.Selection()
    msg = str(ei.value)
    assert "lod.points" in msg and "new_selection" in msg


def test_q1_neg_upstream_parity(upstream):
    """Paridad documental: upstream tambien rechaza el no-arg (firma posicional)."""
    with pytest.raises(TypeError):
        upstream.Selection()


def test_q1_pos_factory_registers_and_roundtrips(fork):
    """Q1-POS: new_selection bindea, registra y sobrevive write->read."""
    p3d = build_cube_p3d(fork)
    lod = p3d.lods[0]
    sel = lod.new_selection("lf_extra")
    assert lod.selections["lf_extra"] is sel
    assert sel.all_points is lod.points and sel.all_faces is lod.faces
    sel.faces[lod.faces[0]] = 1
    sel.faces[lod.faces[2]] = 1
    # get-or-create: segunda llamada devuelve la MISMA selection
    assert lod.new_selection("lf_extra") is sel

    reread = read_p3d(fork, write_bytes(p3d))
    rl = reread.lods[0]
    assert "lf_extra" in rl.selections
    got = sorted(rl.faces.index(fa) for fa in rl.selections["lf_extra"].faces)
    assert got == [0, 2]
    assert len(rl.selections["lf_extra"].points) == 0


# ---- F1-02 / W --------------------------------------------------------------

def test_w_pos_weights_normalized(fork):
    """W-POS: {1, 1.0, 0.5} -> round-trip con 1.0 coercionado y 0.5 fraccional."""
    p3d = build_cube_p3d(fork)
    lod = p3d.lods[0]
    sel = lod.new_selection("lf_weights")
    sel.faces[lod.faces[0]] = 1
    sel.faces[lod.faces[1]] = 1.0
    sel.faces[lod.faces[2]] = 0.5

    reread = read_p3d(fork, write_bytes(p3d))
    rl = reread.lods[0]
    rsel = rl.selections["lf_weights"]
    by_idx = {rl.faces.index(fa): w for fa, w in rsel.faces.items()}
    assert by_idx[0] == 1 and by_idx[1] == 1
    assert abs(by_idx[2] - 0.5) <= 1.0 / 255 + 1e-9
    # el dict del usuario NO se muta
    assert sel.faces[lod.faces[1]] == 1.0


@pytest.mark.parametrize("bad", [1.5, -0.25, 2, "x", None])
def test_w_neg_invalid_weight_early_valueerror(fork, bad):
    """W-NEG: weight invalido -> ValueError temprano nombrando la selection."""
    p3d = build_cube_p3d(fork)
    lod = p3d.lods[0]
    sel = lod.new_selection("lf_bad")
    sel.faces[lod.faces[0]] = bad
    with pytest.raises(ValueError) as ei:
        write_bytes(p3d)
    msg = str(ei.value)
    assert "lf_bad" in msg and repr(bad) in msg


def test_w_upstream_crashes_late_and_cryptic(upstream):
    """Documenta el claim del plan: upstream revienta TARDE con TypeError
    criptico (bytes() sobre float) para el weight 1.0 — el fork lo convierte
    en exito (coercion) y los invalidos en ValueError temprano."""
    p3d = build_cube_p3d(upstream)
    lod = p3d.lods[0]
    sel = upstream.Selection(lod.points, lod.faces)
    sel.faces[lod.faces[0]] = 1.0
    lod.selections["lf_up"] = sel
    with pytest.raises(TypeError):
        write_bytes(p3d)


# ---- F1-06 / PROP -----------------------------------------------------------

def test_prop_pos_63_bytes_roundtrip_exact(fork):
    """PROP-POS: valor de 63 bytes -> round-trip exacto."""
    p3d = build_cube_p3d(fork)
    lod = p3d.lods[0]
    v63 = "v" * 63
    lod.properties["lodnoshadow"] = v63
    reread = read_p3d(fork, write_bytes(p3d))
    assert reread.lods[0].properties["lodnoshadow"] == v63


@pytest.mark.parametrize("key,value", [
    ("class", "x" * 70),     # valor largo
    ("k" * 64, "house"),     # clave larga
    ("class", "y" * 64),     # 64 exactos: perderia el NUL terminator
])
def test_prop_neg_over_63_bytes_raises(fork, key, value):
    """PROP-NEG: clave/valor >=64 bytes utf-8 -> ValueError (antes truncaba)."""
    p3d = build_cube_p3d(fork)
    p3d.lods[0].properties[key] = value
    with pytest.raises(ValueError) as ei:
        write_bytes(p3d)
    assert "63" in str(ei.value)


def test_prop_upstream_corrupts_silently_on_write(upstream):
    """Documenta Quirk 6 (comportamiento REAL verificado): upstream ESCRIBE
    sin quejarse un property >63 bytes (struct '64s' trunca y pierde el NUL
    terminator) y el .p3d resultante ya NI SIQUIERA es re-legible — el read
    revienta en el assert del NUL. Corrupcion silenciosa en write, fallo
    diferido en read: exactamente lo que el guard F1-06 del fork impide."""
    p3d = build_cube_p3d(upstream)
    p3d.lods[0].properties["class"] = "x" * 70
    data = write_bytes(p3d)  # upstream no se queja
    with pytest.raises(AssertionError):
        read_p3d(upstream, data)  # el output esta corrupto
