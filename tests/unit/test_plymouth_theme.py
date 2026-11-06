import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_generated_theme(tmp_path):
    subprocess.run([sys.executable, str(ROOT / "scripts/gen_plymouth.py"), str(tmp_path)], check=True, capture_output=True)
    frames = sorted(tmp_path.glob("throbber-*.png"))
    assert len(frames) == 32
    for f in frames:
        d = f.read_bytes()
        assert d[:8] == bytes([137, 80, 78, 71, 13, 10, 26, 10])
        assert struct.unpack(">II", d[16:24]) == (218, 119)
    assert len({f.read_bytes() for f in frames}) > 8, "the ring must pulse (frames differ)"
    desc = (tmp_path / "hscl1-logo.plymouth").read_text(encoding="utf-8")
    assert "ModuleName=two-step" in desc and "ImageDir=/usr/share/plymouth/themes/hscl1-logo" in desc
    assert "kubuntu" not in desc.lower()
    assert "Name=HSCL1 Logo" in desc


def test_postinst_is_wired():
    post = (ROOT / "packages/debian/hscl-branding/DEBIAN/postinst").read_text(encoding="utf-8")
    assert "update-alternatives --set default.plymouth" in post
    assert "hscl1-logo.plymouth" in post
    assert "gen_plymouth.py" in (ROOT / "packages/debian/hscl-branding/build.sh").read_text(encoding="utf-8")
    rm = (ROOT / "packages/debian/hscl-branding/DEBIAN/postrm").read_text(encoding="utf-8")
    assert "update-alternatives --remove default.plymouth" in rm
