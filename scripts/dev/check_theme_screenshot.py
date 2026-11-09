#!/usr/bin/env python3
"""Decide from a real screenshot whether Qt widget apps are dark or light.

Visual QA 2026-11-09 found Dolphin and Konsole rendering in Kubuntu's light Breeze palette inside a dark
shell. `hscl doctor` has a `theme` check for the live system; this script is the objective check for the
candidate screenshot, so the fix can be VM-VERIFIED instead of eyeballed.

Usage: check_theme_screenshot.py IMAGE [--box x0,y0,x1,y1] [--expect dark|light]
Exit 0 when the measured theme matches --expect (default dark), 1 otherwise, 2 on a usage error.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image

THRESHOLD = 110.0  # mean luminance (0-255) between dark and light UI
DEFAULT_BOX = (360, 140, 1000, 700)  # the Dolphin/Konsole window area at 1280x800


def luminance(rgb: tuple[int, int, int]) -> float:
    return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]


def mean_luminance(image: Path, box: tuple[int, int, int, int]) -> float:
    img = Image.open(image).convert("RGB")
    crop = img.crop(box)
    pixels = list(crop.getdata())
    return sum(luminance(p) for p in pixels) / len(pixels)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--box", default=",".join(map(str, DEFAULT_BOX)))
    ap.add_argument("--expect", choices=["dark", "light"], default="dark")
    args = ap.parse_args(argv)
    try:
        box = tuple(int(v) for v in args.box.split(","))
    except ValueError:
        print("box must be x0,y0,x1,y1", file=sys.stderr)
        return 2
    if len(box) != 4:
        print("box must have four numbers", file=sys.stderr)
        return 2
    image = Path(args.image)
    if not image.is_file():
        print(f"no such image: {image}", file=sys.stderr)
        return 2
    value = mean_luminance(image, box)  # type: ignore[arg-type]
    measured = "light" if value >= THRESHOLD else "dark"
    print(f"{image.name}: mean luminance {value:.1f} -> {measured} (expected {args.expect})")
    return 0 if measured == args.expect else 1


if __name__ == "__main__":
    raise SystemExit(main())
