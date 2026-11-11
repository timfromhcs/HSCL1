"""Desktop entry labels must not be symlinks, because Plasma italicises link labels.

Measured 2026-11-10/11: every capture shows "HSCL1 Control Center" and "HSCL1 Handbook" in italics. It is not
the font (`Fonts desktopFont` is pinned to Noto Sans, which the image ships 314 files of): Plasma's
`FolderItemDelegate.qml` line 380 is `font.italic: (main.model?.isLink ?? false)`, and both desktop entries were
installed as symlinks. The hook now installs real copies; this test keeps a symlink from creeping back in.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / "distro/live/hooks/010-hscl-defaults.sh"
GATE = ROOT / "distro/live/verify-image.sh"


def test_the_hook_installs_real_desktop_files():
    text = HOOK.read_text(encoding="utf-8")
    assert 'install -m 0644 "$ROOTFS/usr/share/applications/$entry.desktop"' in text
    for line in text.splitlines():
        if line.strip().startswith("ln -s"):
            assert "skel/Desktop" not in line, f"desktop entry symlinked again: {line.strip()}"


def test_the_hook_removes_a_previous_link_before_copying():
    text = HOOK.read_text(encoding="utf-8")
    removal = [line for line in text.splitlines() if line.strip().startswith("rm -f") and "skel/Desktop" in line]
    assert removal, "no removal of the old desktop symlinks"
    joined = " ".join(removal)
    assert "hscl-handbook.desktop" in joined and "hscl-control-center.desktop" in joined


def test_the_image_gate_rejects_symlinked_entries():
    text = GATE.read_text(encoding="utf-8")
    assert "live desktop: handbook entry" in text
    assert "live desktop: control-center entry" in text
    assert "! test -L" in text


def test_the_hook_names_the_reason():
    text = HOOK.read_text(encoding="utf-8")
    assert "font.italic: model.isLink" in text, "the measured cause must stay documented next to the fix"
