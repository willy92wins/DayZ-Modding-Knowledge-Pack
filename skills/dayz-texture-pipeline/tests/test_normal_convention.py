#!/usr/bin/env python3
"""Fixtures of known convention for scripts/normal_convention.py.

Synthetic height fields encoded as DirectX (Y-) and as OpenGL (Y+) normal maps, with an albedo
built from the same heights. Generated in the test, so no third-party texture ships with the
Pack. Needs numpy and Pillow; without them the module skips (the CI runner installs pytest only).

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


def _encode(dh_dcol: "np.ndarray", dh_drow: "np.ndarray", convention: str, k: float = 4.0) -> "Image.Image":
    nx = -k * dh_dcol
    # DirectX: +Y points down the rows; OpenGL: +Y points up, so the row slope keeps its sign.
    ny = -k * dh_drow if convention == "DirectX" else k * dh_drow
    nz = np.ones_like(nx)
    length = np.sqrt(nx ** 2 + ny ** 2 + nz ** 2)
    rgb = np.stack([nx / length, ny / length, nz / length], axis=-1)
    return Image.fromarray(np.round((rgb + 1.0) * 0.5 * 255.0).astype(np.uint8), "RGB")


def _normal_map(h: "np.ndarray", convention: str) -> "Image.Image":
    return _encode(np.gradient(h, axis=1), np.gradient(h, axis=0), convention)


def _grey(g: "np.ndarray") -> "Image.Image":
    return Image.fromarray(np.round(np.stack([g * 0.9, g, g * 0.8], axis=-1) * 255.0).astype(np.uint8), "RGB")


def _albedo(h: "np.ndarray") -> "Image.Image":
    return _grey(0.25 + 0.6 * (h - h.min()) / (h.max() - h.min()))     # hollows darker


def _ribs(size: int = 128):
    """Ribs whose amplitude grows down the image: across a hollow the surface curves one way
    along x and the other way along y (the counter-example of R21 round 1, analytic slopes)."""
    rows, cols = np.mgrid[0:size, 0:size].astype(np.float64)
    omega = 2.0 * np.pi * 3 / size
    beta = 4.0 / (size - 1)
    amplitude = np.exp(4.0 * (rows / (size - 1) - 0.5))
    h = np.cos(omega * cols) * amplitude
    dh_dcol = -omega * np.sin(omega * cols) * amplitude
    dh_drow = beta * np.cos(omega * cols) * amplitude
    return h, dh_dcol, dh_drow


@pytest.fixture(scope="module")
def maps():
    h = _height()
    rows, cols = np.mgrid[0:SIZE, 0:SIZE].astype(np.float64)
    return {
        "DirectX": _normal_map(h, "DirectX"),
        "OpenGL": _normal_map(h, "OpenGL"),
        "albedo": _albedo(h),
        "flat_albedo": Image.new("RGB", (SIZE, SIZE), (140, 140, 140)),
        # a pattern with no relation to the heights: finite, weak correlations
        "weak_albedo": _grey(0.5 + 0.3 * np.sin(1.7 * cols + 2.3 * rows)),
    }


@pytest.mark.parametrize("convention", ["DirectX", "OpenGL"])
def test_known_convention_is_read_back(maps, convention):
    result = nc.detect(maps[convention], maps["albedo"])
    assert result["verdict"] == convention, result
    assert result["albedo_verdict"] == convention and result["curl_verdict"] == convention, result
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


@pytest.mark.parametrize("convention", ["DirectX", "OpenGL"])
def test_opposite_curvatures_make_the_albedo_reading_lie_and_the_verdict_abstain(convention):
    h, dh_dcol, dh_drow = _ribs()
    result = nc.detect(_encode(dh_dcol, dh_drow, convention), _albedo(h))
    wrong = "OpenGL" if convention == "DirectX" else "DirectX"
    # the albedo reading alone is wrong here, with strong correlations ...
    assert result["albedo_verdict"] == wrong, result
    assert abs(result["corr_red"]) > 0.5 and abs(result["corr_green"]) > 0.3, result
    # ... the curl reading is right, and the two disagreeing is never a verdict
    assert result["curl_verdict"] == convention, result
    assert result["verdict"] == "INCONCLUSIVE", result


@pytest.mark.parametrize("convention", ["DirectX", "OpenGL"])
def test_a_sum_of_x_and_y_profiles_leaves_the_curl_reading_without_signal(convention):
    # h = f(col) + g(row) has no mixed derivative, so both curl residuals are equal noise
    rows, cols = np.mgrid[0:SIZE, 0:SIZE].astype(np.float64)
    omega = 2.0 * np.pi * 4 / SIZE
    h = np.cos(omega * cols) + np.cos(omega * rows)
    result = nc.detect(_normal_map(h, convention), _albedo(h))
    assert result["albedo_verdict"] == convention, result
    assert result["curl_verdict"] == "INCONCLUSIVE", result
    assert result["verdict"] == "INCONCLUSIVE", result


def test_weak_albedo_correlations_are_inconclusive(maps):
    result = nc.detect(maps["DirectX"], maps["weak_albedo"])
    assert math.isfinite(result["corr_red"]) and math.isfinite(result["corr_green"]), result
    assert max(abs(result["corr_red"]), abs(result["corr_green"])) < nc.MIN_CORR, result
    assert result["albedo_verdict"] == "INCONCLUSIVE", result
    assert result["verdict"] == "INCONCLUSIVE", result


def test_flat_albedo_is_inconclusive_not_directx(maps):
    # no hollow signal: both correlations are undefined. The contributed script read NaN as DirectX.
    result = nc.detect(maps["OpenGL"], maps["flat_albedo"])
    assert result["verdict"] == "INCONCLUSIVE", result
    assert not math.isfinite(result["corr_green"])
    assert result["curl_verdict"] == "OpenGL", result


def test_inverting_green_only_negates_the_green_correlation(maps):
    # why an inverted-green run is no control: it cannot disagree with the original reading
    arr = np.asarray(maps["DirectX"]).copy()
    arr[:, :, 1] = 255 - arr[:, :, 1]
    flipped = nc.detect(Image.fromarray(arr, "RGB"), maps["albedo"])
    original = nc.detect(maps["DirectX"], maps["albedo"])
    assert flipped["corr_green"] == pytest.approx(-original["corr_green"], abs=0.02)
    assert flipped["corr_red"] == pytest.approx(original["corr_red"], abs=1e-12)
    assert flipped["curl_residual_directx"] == pytest.approx(original["curl_residual_opengl"], rel=0.05)


def _strict_json(text):
    def refuse(token):
        raise ValueError("non-JSON number %s" % token)
    return json.loads(text, parse_constant=refuse)


def test_cli_exit_codes_and_json(maps, tmp_path, capsys):
    paths = {}
    for name in ("DirectX", "OpenGL", "albedo", "flat_albedo"):
        paths[name] = tmp_path / ("%s.png" % name)
        maps[name].save(paths[name])
    small = tmp_path / "small.png"
    maps["albedo"].resize((SIZE // 2, SIZE // 2)).save(small)

    for convention in ("DirectX", "OpenGL"):
        code = nc.main(["--normal", str(paths[convention]), "--albedo", str(paths["albedo"]), "--json"])
        out = _strict_json(capsys.readouterr().out)
        assert code == 0 and out["verdict"] == convention, out

    code = nc.main(["--normal", str(paths["DirectX"]), "--albedo", str(paths["flat_albedo"]), "--json"])
    out = _strict_json(capsys.readouterr().out)       # undefined numbers are null, never NaN
    assert code == 2 and out["verdict"] == "INCONCLUSIVE" and out["corr_red"] is None, out
    assert nc.main(["--normal", str(paths["DirectX"]), "--albedo", str(paths["flat_albedo"])]) == 2
    assert "INCONCLUSIVE" in capsys.readouterr().out
    assert nc.main(["--normal", str(paths["DirectX"]), "--albedo", str(small)]) == 1
    assert "differ in size" in capsys.readouterr().err


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
