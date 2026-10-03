#!/usr/bin/env python3
"""Tell an OpenGL (Y+) normal map from a DirectX (Y-) one by measurement, not by eye.

DayZ `_nohq` is DirectX/Y- (SKILL.md rule 3). A source map of unknown convention is
otherwise a guess, and a wrong guess turns every groove into a ridge.

Two independent readings; the verdict needs both to agree, otherwise INCONCLUSIVE.

1. Albedo reading (the contributed `normal_convencion.py`, arithmetic unchanged, see
   Provenance): across a groove (a valley) the surface normals converge.
     - Red, X: +U is right in both conventions, so d(nx)/dx < 0 when a valley is crossed
       left to right.
     - Green, Y: in OpenGL +Y is +V, up in the image, so walking down the rows d(ny)/dy > 0
       (the opposite sign to red); in DirectX +Y points down and the sign equals red's.
   The grooves are found in the albedo: dirt collects in hollows, so a pixel darker than its
   blurred surroundings (a high-pass of the albedo) marks a hollow. The red channel calibrates
   the sign of that hollow signal; the green channel decides. It assumes the hollows curve the
   same way along both axes (pits, or grooves in both directions): on a surface whose
   curvature has opposite signs along the two axes the green correlation follows the geometry,
   not the convention, and the reading is wrong with strong correlations (R21 round 1).
2. Curl reading (added in review, no albedo): the slopes of a height field have no curl. With
   p = -nx/nz and q = ny/nz, d(p)/d(row) - d(q)/d(col) is ~0 under OpenGL and
   d(p)/d(row) + d(q)/d(col) is ~0 under DirectX. The smaller median residual wins if it is
   below CURL_RATIO times the other.

What it does NOT check: inverting the green channel of the same map only negates the green
correlation and swaps the two curl residuals, so it always flips the verdict and is no control.
The controls are maps of known convention (tests/test_normal_convention.py). A map that is not
a height field's slopes (painted, hand-edited, heavily compressed) can leave the curl reading
inconclusive.

Input: 8-bit PNG (or any format Pillow reads) of the same size. Convert a `.paa` first with
DayZ Tools ImageToPAA; a `_nohq` name makes it write the RGB normal.

Usage:
  python normal_convention.py --normal heater_Normal.png --albedo heater_BaseColor.png [--json]
Exit: 0 = both readings agree (DirectX or OpenGL), 2 = INCONCLUSIVE, 1 = bad input.

Provenance: the albedo reading is adapted from LFPowerGrid_dev `assets/heater/normal_convencion.py`
(commit a4c6e29, 2026-09-21), written by the Pack owner with Claude, contributed through
pipeline ticket fb-20260921-164248-a140. MIT, like the rest of the Pack. Changes: command-line
paths instead of fixed ones, a non-finite correlation is INCONCLUSIVE (the original read NaN as
DirectX), a size check, JSON output (null for undefined numbers), and the curl reading with the
agreement rule, added after a cross-family review found a confident wrong verdict.
"""
from __future__ import annotations

import argparse
import json
import math
import sys

import numpy as np
from PIL import Image, ImageFilter

DETAIL_MIN = 0.04   # |nx| + |ny| above which the normal map carries detail
LUMA_MIN = 0.02     # albedo floor: skips the atlas background
BLUR_RADIUS = 6     # Gaussian radius of the albedo's low-pass, in pixels
MIN_CORR = 0.02     # weaker albedo correlations are INCONCLUSIVE
NZ_MIN = 0.2        # floor for nz when normals are turned into slopes
CURL_RATIO = 0.8    # the smaller curl residual must be below this times the other

DIRECTX, OPENGL, INCONCLUSIVE = "DirectX", "OpenGL", "INCONCLUSIVE"


def _corr(a: np.ndarray, b: np.ndarray, mask: np.ndarray) -> float:
    a, b = a[mask], b[mask]
    a = a - a.mean()
    b = b - b.mean()
    denom = math.sqrt(float((a * a).sum()) * float((b * b).sum()))
    if denom == 0.0:
        return float("nan")
    return float((a * b).sum() / denom)


def _albedo_reading(nx, ny, albedo_img, blur_radius, detail_min, luma_min, min_corr) -> dict:
    alb_rgb = albedo_img.convert("RGB")
    alb = np.asarray(alb_rgb).astype(np.float64) / 255.0
    luma = 0.2126 * alb[:, :, 0] + 0.7152 * alb[:, :, 1] + 0.0722 * alb[:, :, 2]
    smooth = np.asarray(alb_rgb.convert("L").filter(ImageFilter.GaussianBlur(blur_radius))).astype(np.float64) / 255.0
    hollow = smooth - luma            # > 0 where the pixel is darker than its surroundings

    dnx_dx = np.gradient(nx, axis=1)
    dny_dy = np.gradient(ny, axis=0)

    mask = ((np.abs(nx) + np.abs(ny)) > detail_min) & (luma > luma_min)
    red = _corr(dnx_dx, hollow, mask) if mask.any() else float("nan")
    green = _corr(dny_dy, hollow, mask) if mask.any() else float("nan")

    if not (math.isfinite(red) and math.isfinite(green)) or abs(red) < min_corr or abs(green) < min_corr:
        verdict = INCONCLUSIVE
    elif (red > 0) == (green > 0):
        verdict = DIRECTX
    else:
        verdict = OPENGL
    return {"verdict": verdict, "corr_red": red, "corr_green": green, "pixels": int(mask.sum())}


def _curl_reading(nx, ny, nz, detail_min, curl_ratio) -> dict:
    nz = np.clip(nz, NZ_MIN, None)
    p = -nx / nz                       # dh/dcol in both conventions
    q = ny / nz                        # dh/drow under OpenGL, -dh/drow under DirectX
    dp_drow = np.gradient(p, axis=0)
    dq_dcol = np.gradient(q, axis=1)
    mask = (np.abs(nx) + np.abs(ny)) > detail_min
    if not mask.any():
        return {"verdict": INCONCLUSIVE, "residual_directx": float("nan"), "residual_opengl": float("nan")}
    res_opengl = float(np.median(np.abs(dp_drow - dq_dcol)[mask]))
    res_directx = float(np.median(np.abs(dp_drow + dq_dcol)[mask]))
    if res_directx < curl_ratio * res_opengl:
        verdict = DIRECTX
    elif res_opengl < curl_ratio * res_directx:
        verdict = OPENGL
    else:
        verdict = INCONCLUSIVE
    return {"verdict": verdict, "residual_directx": res_directx, "residual_opengl": res_opengl}


def detect(normal_img: Image.Image, albedo_img: Image.Image, *, blur_radius: float = BLUR_RADIUS,
           detail_min: float = DETAIL_MIN, luma_min: float = LUMA_MIN, min_corr: float = MIN_CORR,
           curl_ratio: float = CURL_RATIO) -> dict:
    """Return the verdict and the numbers behind it. Raises ValueError on mismatched sizes."""
    if normal_img.size != albedo_img.size:
        raise ValueError("normal map %s and albedo %s differ in size" % (normal_img.size, albedo_img.size))
    nrm = np.asarray(normal_img.convert("RGB")).astype(np.float64) / 255.0
    nx = nrm[:, :, 0] * 2.0 - 1.0
    ny = nrm[:, :, 1] * 2.0 - 1.0
    nz = nrm[:, :, 2] * 2.0 - 1.0

    albedo = _albedo_reading(nx, ny, albedo_img, blur_radius, detail_min, luma_min, min_corr)
    curl = _curl_reading(nx, ny, nz, detail_min, curl_ratio)
    if albedo["verdict"] == curl["verdict"] and albedo["verdict"] != INCONCLUSIVE:
        verdict = albedo["verdict"]
    else:
        verdict = INCONCLUSIVE
    return {
        "verdict": verdict,
        "albedo_verdict": albedo["verdict"],
        "curl_verdict": curl["verdict"],
        "corr_red": albedo["corr_red"],
        "corr_green": albedo["corr_green"],
        "pixels_with_detail": albedo["pixels"],
        "pixels_total": int(nx.size),
        "curl_residual_directx": curl["residual_directx"],
        "curl_residual_opengl": curl["residual_opengl"],
        "min_corr": min_corr,
        "curl_ratio": curl_ratio,
    }


def _json_safe(result: dict) -> dict:
    return {k: (None if isinstance(v, float) and not math.isfinite(v) else v) for k, v in result.items()}


def _fmt(value: float) -> str:
    return "%+.4f" % value if math.isfinite(value) else "undefined"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="OpenGL (Y+) or DirectX (Y-) normal map, measured.")
    parser.add_argument("--normal", required=True, help="tangent-space normal map (RGB)")
    parser.add_argument("--albedo", required=True, help="albedo/base colour of the same UV layout")
    parser.add_argument("--min-corr", type=float, default=MIN_CORR, help="weakest albedo correlation that counts (default 0.02)")
    parser.add_argument("--json", action="store_true", help="print the result as JSON (undefined numbers are null)")
    args = parser.parse_args(argv)
    try:
        with Image.open(args.normal) as normal_img, Image.open(args.albedo) as albedo_img:
            result = detect(normal_img, albedo_img, min_corr=args.min_corr)
    except (OSError, ValueError) as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(_json_safe(result), indent=2, allow_nan=False))
    else:
        share = 100.0 * result["pixels_with_detail"] / max(result["pixels_total"], 1)
        print("pixels with detail: %d of %d (%.1f %%)" % (result["pixels_with_detail"], result["pixels_total"], share))
        print("albedo reading: corr(d nx/dx, hollow) = %s (calibrates the sign), corr(d ny/dy, hollow) = %s -> %s"
              % (_fmt(result["corr_red"]), _fmt(result["corr_green"]), result["albedo_verdict"]))
        print("curl reading: median residual DirectX %s, OpenGL %s -> %s"
              % (_fmt(result["curl_residual_directx"]), _fmt(result["curl_residual_opengl"]), result["curl_verdict"]))
        if result["verdict"] == DIRECTX:
            print("VERDICT: DirectX (Y-) -> already DayZ's convention; keep the green channel")
        elif result["verdict"] == OPENGL:
            print("VERDICT: OpenGL (Y+) -> INVERT the green channel for DayZ")
        else:
            print("VERDICT: INCONCLUSIVE (the two readings do not agree on a convention)")
    return 2 if result["verdict"] == INCONCLUSIVE else 0


if __name__ == "__main__":
    sys.exit(main())
