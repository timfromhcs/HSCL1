"""hscl-cqhecs enters the ISO only with its image gates (Genesis plan B1: small shell, nothing running, no runtime baked in)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REMASTER = (ROOT / "scripts/remaster-iso.sh").read_text(encoding="utf-8")
GATE = (ROOT / "distro/live/verify-image.sh").read_text(encoding="utf-8")


def test_the_package_is_built_into_the_image():
    line = next(l for l in REMASTER.splitlines() if l.startswith("for p in hscl-branding"))
    assert "hscl-cqhecs" in line.replace(";", " ").split()


def test_image_gate_checks_presence_and_executable_launcher():
    for name in ("cq-hecs launcher installed", "cq-hecs desktop entry", "cq-hecs runtime manifest"):
        assert name in GATE, name
    assert "usr/bin/hscl-cqhecs" in GATE and "usr/share/hscl/cqhecs/requirements-cp314.txt" in GATE


def test_image_gate_checks_nothing_runs_and_no_runtime_is_baked_in():
    for name in ("cq-hecs: no autostart entry", "cq-hecs: no systemd unit", "cq-hecs: no runtime or wheels in the image"):
        assert name in GATE, name
    assert "/opt/hscl/venvs" in GATE and "*.whl" in GATE
