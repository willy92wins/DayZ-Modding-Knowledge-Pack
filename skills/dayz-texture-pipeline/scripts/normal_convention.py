#!/usr/bin/env python3
"""Tell an OpenGL (Y+) normal map from a DirectX (Y-) one by measurement, not by eye.

DayZ `_nohq` is DirectX/Y- (SKILL.md rule 3). A source map of unknown convention is
otherwise a guess, and a wrong guess turns every groove into a ridge.

Method (the same arithmetic as the contributed `normal_convencion.py`, see Provenance):
across a groove (a valley) the surface normals converge.
  - Red, X: +U is right in both conventions, so d(nx)/dx < 0 when a valley is crossed left
    to right.
  - Green, Y: in OpenGL +Y is +V, up in the image, so walking down the rows d(ny)/dy > 0
    (the opposite sign to red); in DirectX +Y points down and the sign equals red's.
The grooves are found in the albedo: dirt collects in hollows, so a pixel darker than its
blurred surroundings (a high-pass of the albedo) marks a hollow. The red channel calibrates
the sign of that hollow signal; the green channel decides. Same sign: DirectX. Opposite
sign: OpenGL. Either correlation weaker than --min-corr (or undefined, as with a flat
albedo): INCONCLUSIVE, never a guess.

What it does NOT check: inverting the green channel of the same map only negates the green
correlation, so it always flips the verdict and is no control. The controls are maps of
known convention (tests/test_normal_convention.py). The method also assumes the albedo is
darker in the hollows; on a clean albedo it reports INCONCLUSIVE.

Input: 8-bit PNG (or any format Pillow reads) of the same size. Convert a `.paa` first with
DayZ Tools ImageToPAA; a `_nohq` name makes it write the RGB normal.

Usage:
  python normal_convention.py --normal heater_Normal.png --albedo heater_BaseColor.png [--json]
Exit: 0 = a verdict (DirectX or OpenGL), 2 = INCONCLUSIVE, 1 = bad input.

Provenance: adapted from LFPowerGrid_dev `assets/heater/normal_convencion.py` (commit
a4c6e29, 2026-09-21), written by the Pack owner with Claude, contributed through pipeline
ticket fb-20260921-164248-a140. MIT, like the rest of the Pack. Changes: command-line paths
instead of fixed ones, a non-finite correlation is INCONCLUSIVE (the original read NaN as
DirectX), a size check, and JSON output; the arithmetic is unchanged.
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
MIN_CORR = 0.02     # weaker correlations are INCONCLUSIVE


def _corr(a: np.ndarray, b: np.ndarray, mask: np.ndarray) -> float:
    a, b = a[mask], b[mask]
    a = a - a.mean()
    b = b - b.mean()
    denom = math.sqrt(float((a * a).sum()) * float((b * b).sum()))
    if denom == 0.0:
        return float("nan")
    return float((a * b).sum() / denom)


def detect(normal_img: Image.Image, albedo_img: Image.Image, *, blur_radius: float = BLUR_RADIUS,
           detail_min: float = DETAIL_MIN, luma_min: float = LUMA_MIN, min_corr: float = MIN_CORR) -> dict:
    """Return the verdict and the numbers behind it. Raises ValueError on mismatched sizes."""
    if normal_img.size != albedo_img.size:
        raise ValueError("normal map %s and albedo %s differ in size" % (normal_img.size, albedo_img.size))
    nrm = np.asarray(normal_img.convert("RGB")).astype(np.float64) / 255.0
    alb_rgb = albedo_img.convert("RGB")
    alb = np.asarray(alb_rgb).astype(np.float64) / 255.0

    nx = nrm[:, :, 0] * 2.0 - 1.0
    ny = nrm[:, :, 1] * 2.0 - 1.0
    luma = 0.2126 * alb[:, :, 0] + 0.7152 * alb[:, :, 1] + 0.0722 * alb[:, :, 2]
    smooth = np.asarray(alb_rgb.convert("L").filter(ImageFilter.GaussianBlur(blur_radius))).astype(np.float64) / 255.0
    hollow = smooth - luma            # > 0 where the pixel is darker than its surroundings

    dnx_dx = np.gradient(nx, axis=1)
    dny_dy = np.gradient(ny, axis=0)

    mask = ((np.abs(nx) + np.abs(ny)) > detail_min) & (luma > luma_min)
    red = _corr(dnx_dx, hollow, mask) if mask.any() else float("nan")
    green = _corr(dny_dy, hollow, mask) if mask.any() else float("nan")

    if not (math.isfinite(red) and math.isfinite(green)) or abs(red) < min_corr or abs(green) < min_corr:
        verdict = "INCONCLUSIVE"
    elif (red > 0) == (green > 0):
        verdict = "DirectX"
    else:
        verdict = "OpenGL"
    return {
        "verdict": verdict,
        "corr_red": red,
        "corr_green": green,
        "pixels_with_detail": int(mask.sum()),
        "pixels_total": int(mask.size),
        "min_corr": min_corr,
    }


def _fmt(value: float) -> str:
    return "%+.4f" % value if math.isfinite(value) else "undefined"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="OpenGL (Y+) or DirectX (Y-) normal map, measured.")
    parser.add_argument("--normal", required=True, help="tangent-space normal map (RGB)")
    parser.add_argument("--albedo", required=True, help="albedo/base colour of the same UV layout")
    parser.add_argument("--min-corr", type=float, default=MIN_CORR, help="weakest correlation that counts (default 0.02)")
    parser.add_argument("--json", action="store_true", help="print the result as JSON")
    args = parser.parse_args(argv)
    try:
        with Image.open(args.normal) as normal_img, Image.open(args.albedo) as albedo_img:
            result = detect(normal_img, albedo_img, min_corr=args.min_corr)
    except (OSError, ValueError) as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        share = 100.0 * result["pixels_with_detail"] / max(result["pixels_total"], 1)
        print("pixels with detail: %d of %d (%.1f %%)" % (result["pixels_with_detail"], result["pixels_total"], share))
        print("corr(d nx/dx, hollow) = %s   <- calibrates the sign" % _fmt(result["corr_red"]))
        print("corr(d ny/dy, hollow) = %s" % _fmt(result["corr_green"]))
        if result["verdict"] == "DirectX":
            print("VERDICT: DirectX (Y-) -> already DayZ's convention; keep the green channel")
        elif result["verdict"] == "OpenGL":
            print("VERDICT: OpenGL (Y+) -> INVERT the green channel for DayZ")
        else:
            print("VERDICT: INCONCLUSIVE (a correlation is weaker than %.3f or undefined)" % result["min_corr"])
    return 2 if result["verdict"] == "INCONCLUSIVE" else 0


if __name__ == "__main__":
    sys.exit(main())
