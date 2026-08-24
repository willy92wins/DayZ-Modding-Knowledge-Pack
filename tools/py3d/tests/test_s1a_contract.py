"""S1A: contrato D4 — CANON-IDENT (nivel 1) y SEM-INV (nivel 2)."""

import io

import pytest

from builders import build_cube_p3d, build_icosphere_p3d, build_multilod_p3d
from helpers import assert_sem_inv, read_p3d, sha256, write_bytes

CANONICAL = [
    ("cube", build_cube_p3d),
    ("icosphere", build_icosphere_p3d),
    ("multilod", build_multilod_p3d),
]
IDS = [c[0] for c in CANONICAL]


@pytest.mark.parametrize("name,builder", CANONICAL, ids=IDS)
def test_canon_ident(fork, upstream, name, builder):
    """CANON-IDENT: mismo modelo, bytes identicos fork vs upstream."""
    fork_bytes = write_bytes(builder(fork))
    up_bytes = write_bytes(builder(upstream))
    assert len(fork_bytes) == len(up_bytes)
    assert sha256(fork_bytes) == sha256(up_bytes)


@pytest.mark.parametrize("name,builder", CANONICAL, ids=IDS)
def test_sem_inv(fork, name, builder):
    """SEM-INV: write -> reopen -> invariantes semanticos completos."""
    assert_sem_inv(fork, builder(fork))


@pytest.mark.parametrize("name,builder", CANONICAL, ids=IDS)
def test_sem_inv_second_roundtrip_stable(fork, name, builder):
    """SEM-INV: tras el primer round-trip, write(read(x)) == x (estabilidad)."""
    d1 = write_bytes(builder(fork))
    d2 = write_bytes(read_p3d(fork, d1))
    assert d1 == d2


def test_fixture_files_roundtrip(fork, tmp_path):
    """make_fixtures genera .p3d legibles que cumplen SEM-INV desde disco."""
    import make_fixtures
    out = make_fixtures.main(str(tmp_path))
    import os
    for name, builder in CANONICAL:
        path = os.path.join(out, name + ".p3d")
        with open(path, "rb") as f:
            data = f.read()
        assert data[:4] == b"MLOD"
        assert_sem_inv(fork, builder(fork), data=data)
