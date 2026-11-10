"""The panic detector must flag a purple crash frame and stay quiet on real UI screenshots."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/dev/detect_panic.py"


def _png(path: Path, colour: tuple[int, int, int], size: tuple[int, int] = (160, 100)) -> Path:
    from PIL import Image

    Image.new("RGB", size, colour).save(path)
    return path


def _run(*paths: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, paths)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def test_a_purple_frame_is_flagged(tmp_path: Path):
    _png(tmp_path / "l09-before-finish.png", (119, 41, 83))
    res = _run(tmp_path)
    assert res.returncode == 1, res.stdout + res.stderr
    assert "PANIC-LIKE" in res.stdout
    assert "l09-before-finish.png" in res.stdout


def test_a_dark_desktop_is_not_flagged(tmp_path: Path):
    _png(tmp_path / "desktop.png", (14, 17, 23))
    _png(tmp_path / "welcome.png", (240, 240, 240))
    res = _run(tmp_path)
    assert res.returncode == 0, res.stdout + res.stderr
    assert "PANIC-LIKE" not in res.stdout


def test_a_mixed_frame_stays_below_the_threshold(tmp_path: Path):
    """A real UI screenshot is dark with content; only a mostly uniform panic frame should trip the threshold."""
    from PIL import Image, ImageDraw

    im = Image.new("RGB", (1280, 800), (20, 22, 30))
    draw = ImageDraw.Draw(im)
    draw.rectangle([0, 0, 1279, 120], fill=(119, 41, 83))  # a purple banner, 15 % of the frame
    path = tmp_path / "banner.png"
    im.save(path)
    res = _run(tmp_path)
    assert res.returncode == 0, res.stdout + res.stderr
