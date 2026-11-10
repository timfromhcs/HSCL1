"""The dark/light screenshot check must actually discriminate, not just print a number.

Used to turn the 2026-11-09 visual finding ("Dolphin/Konsole are light inside a dark shell") into a
mechanical gate for the next candidate: `scripts/dev/check_theme_screenshot.py` returns 0 when the
measured theme matches the expectation.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Pillow is needed to synthesise the probe images. CI installs python3-pil; a developer machine
# without it skips this gate instead of failing collection (the 2026-11-10 CI run errored here).
pytest.importorskip("PIL", reason="Pillow is required for the screenshot luminance gate")

from PIL import Image  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "dev"))

import check_theme_screenshot as check  # noqa: E402


def solid(path: Path, rgb: tuple[int, int, int]) -> Path:
    Image.new("RGB", (200, 120), rgb).save(path)
    return path


def test_a_light_ui_measures_light_and_a_dark_ui_measures_dark(tmp_path):
    light = solid(tmp_path / "light.png", (250, 250, 250))
    dark = solid(tmp_path / "dark.png", (20, 24, 32))
    box = "0,0,200,120"
    assert check.main([str(light), "--box", box, "--expect", "light"]) == 0
    assert check.main([str(dark), "--box", box, "--expect", "dark"]) == 0
    assert check.main([str(light), "--box", box, "--expect", "dark"]) == 1


def test_missing_image_or_bad_box_is_a_usage_error(tmp_path):
    assert check.main([str(tmp_path / "nope.png")]) == 2
    ok = solid(tmp_path / "ok.png", (10, 10, 10))
    assert check.main([str(ok), "--box", "1,2,3"]) == 2
    assert check.main([str(ok), "--box", "a,b,c,d"]) == 2
