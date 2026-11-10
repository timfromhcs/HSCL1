"""The VM harness must report a crashed guest instead of a quiet run."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import qemu_boot_test as q  # noqa: E402


def _png(path: Path, colour: tuple[int, int, int]) -> None:
    from PIL import Image

    Image.new("RGB", (320, 200), colour).save(path)


def test_a_purple_screenshot_is_reported(tmp_path: Path):
    _png(tmp_path / "l09.png", (119, 41, 83))
    _png(tmp_path / "l01.png", (20, 22, 30))
    suspects = q.panic_suspects(tmp_path)
    assert len(suspects) == 1
    assert "l09.png" in suspects[0]


def test_a_healthy_run_reports_nothing(tmp_path: Path):
    _png(tmp_path / "l01.png", (20, 22, 30))
    _png(tmp_path / "l02.png", (240, 240, 240))
    assert q.panic_suspects(tmp_path) == []


def test_the_summary_keeps_the_key_out_of_a_healthy_result(tmp_path: Path):
    """The key is only added when something is suspect, so existing result.json consumers stay unaffected."""
    _png(tmp_path / "a.png", (20, 22, 30))
    result = {"reached_desktop": True}
    suspects = q.panic_suspects(tmp_path)
    if suspects:
        result["panic_suspects"] = suspects
    text = json.dumps(result)
    assert "panic_suspects" not in text
