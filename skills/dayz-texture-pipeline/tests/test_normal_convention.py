#!/usr/bin/env python3
"""Fixtures of known convention for scripts/normal_convention.py.

One synthetic height field (pits whose albedo is darker, as dirt collects in hollows) is
encoded twice: as a DirectX (Y-) normal map and as an OpenGL (Y+) one. Generated in the test,
so no third-party texture ships with the Pack. Needs numpy and Pillow; without them the module
skips (the CI runner installs pytest only).

Run: python -m pytest skills/dayz-texture-pipeline/tests -q
"""
import json
import math
import sys
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
Image = pytest.importorskip("PIL.Image")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import normal_convention as nc  # noqa: E402

SIZE = 96


def _height() -> "np.ndarray":
    """Deterministic pits: no random generator, so the fixture is the same on every numpy."""
    rows, cols = np.mgrid[0:SIZE, 0:SIZE].astype(np.float64)
    h = np.zeros((SIZE, SIZE))
    for i in range(36):
        cy = (i * 37 % 89) + 4.0
        cx = (i * 53 % 83) + 6.0
        sigma = 2.5 + (i % 4)
        h -= np.exp(-((rows - cy) ** 2 + (cols - cx) ** 2) / (2.0 * sigma ** 2))
    return h


def _normal_map(h: "np.ndarray", convention: str) -> "Image.Image":
    dh_dcol = np.gradient(h, axis=1)
    dh_drow = np.gradient(h, axis=0)
    k = 4.0
    nx = -k * dh_dcol
    # DirectX: +Y points down the rows; OpenGL: +Y points up, so the row slope keeps its sign.
    ny = -k * dh_drow if convention == "DirectX" else k * dh_drow
    nz = np.ones_like(nx)
    length = np.sqrt(nx ** 2 + ny ** 2 + nz ** 2)
    rgb = np.stack([nx / length, ny / length, nz / length], axis=-1)
    return Image.fromarray(np.round((rgb + 1.0) * 0.5 * 255.0).astype(np.uint8), "RGB")


def _albedo(h: "np.ndarray") -> "Image.Image":
    span = h.max() - h.min()
    grey = 0.25 + 0.6 * (h - h.min()) / span          # hollows darker
    rgb = np.stack([grey * 0.9, grey, grey * 0.8], axis=-1)
    return Image.fromarray(np.round(rgb * 255.0).astype(np.uint8), "RGB")


@pytest.fixture(scope="module")
def maps():
    h = _height()
    return {
        "DirectX": _normal_map(h, "DirectX"),
        "OpenGL": _normal_map(h, "OpenGL"),
        "albedo": _albedo(h),
        "flat_albedo": Image.new("RGB", (SIZE, SIZE), (140, 140, 140)),
    }


@pytest.mark.parametrize("convention", ["DirectX", "OpenGL"])
def test_known_convention_is_read_back(maps, convention):
    result = nc.detect(maps[convention], maps["albedo"])
    assert result["verdict"] == convention, result
    # the red channel calibrates: across a pit d(nx)/dx falls where the albedo is dark.
    # Both readings are strong on this fixture (about 0.75); a green derivative taken along the
    # wrong axis still keeps the sign here but drops to about 0.14, so the bound is 0.5.
    assert result["corr_red"] < -0.5, result
    assert abs(result["corr_green"]) > 0.5, result
    assert result["pixels_with_detail"] > SIZE * SIZE // 10


@pytest.mark.parametrize("convention", ["DirectX", "OpenGL"])
def test_dark_ridges_instead_of_dark_hollows_keep_the_verdict(maps, convention):
    # the red channel calibrates the sign: an albedo darker on the ridges flips both correlations
    inverted = Image.fromarray(255 - np.asarray(maps["albedo"]), "RGB")
    result = nc.detect(maps[convention], inverted)
    assert result["verdict"] == convention, result
    assert result["corr_red"] > 0.1, result


def test_flat_albedo_is_inconclusive_not_directx(maps):
    # no hollow signal: both correlations are undefined. The contributed script read NaN as DirectX.
    result = nc.detect(maps["DirectX"], maps["flat_albedo"])
    assert result["verdict"] == "INCONCLUSIVE", result
    assert not math.isfinite(result["corr_green"])


def test_inverting_green_only_negates_the_green_correlation(maps):
    # why an inverted-green run is no control: it cannot disagree with the original reading
    arr = np.asarray(maps["DirectX"]).copy()
    arr[:, :, 1] = 255 - arr[:, :, 1]
    flipped = nc.detect(Image.fromarray(arr, "RGB"), maps["albedo"])
    original = nc.detect(maps["DirectX"], maps["albedo"])
    assert flipped["corr_green"] == pytest.approx(-original["corr_green"], abs=0.02)
    assert flipped["corr_red"] == pytest.approx(original["corr_red"], abs=1e-12)


def test_cli_exit_codes_and_json(maps, tmp_path, capsys):
    paths = {}
    for name in ("DirectX", "OpenGL", "albedo", "flat_albedo"):
        paths[name] = tmp_path / ("%s.png" % name)
        maps[name].save(paths[name])
    small = tmp_path / "small.png"
    maps["albedo"].resize((SIZE // 2, SIZE // 2)).save(small)

    for convention in ("DirectX", "OpenGL"):
        code = nc.main(["--normal", str(paths[convention]), "--albedo", str(paths["albedo"]), "--json"])
        out = json.loads(capsys.readouterr().out)
        assert code == 0 and out["verdict"] == convention, out

    assert nc.main(["--normal", str(paths["DirectX"]), "--albedo", str(paths["flat_albedo"])]) == 2
    assert "INCONCLUSIVE" in capsys.readouterr().out
    assert nc.main(["--normal", str(paths["DirectX"]), "--albedo", str(small)]) == 1
    assert "differ in size" in capsys.readouterr().err


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
