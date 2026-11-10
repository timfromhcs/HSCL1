"""The installer must run with software rendering.

Measured 2026-11-10 on `HSCL1-rc2` (4 GB, UEFI, QEMU std VGA): `KCrash: Application 'calamares' crashing`
appeared right after `Got 4 requirements`, while the first Qt Quick view was being built
(`qrc:/ui/MainPage.qml`), and KCrash then SIGKILLed the process, so the installer vanished without touching the
disk. The same image installed correctly on the next attempt - a graphics-stack race. The wrapper sets
`QT_QUICK_BACKEND=software`.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WRAPPER = ROOT / "packages/debian/hscl-branding/usr/bin/hscl-calamares"
HOOK = ROOT / "distro/live/hooks/010-hscl-defaults.sh"
GATE = ROOT / "distro/live/verify-image.sh"


def test_the_wrapper_forces_software_rendering_and_delegates():
    text = WRAPPER.read_text(encoding="utf-8")
    assert "QT_QUICK_BACKEND=software" in text
    assert "export QT_QUICK_BACKEND=software" in text
    assert "exec /usr/bin/calamares-launch-normal" in text, "it must delegate, not reimplement the launcher"


def test_the_desktop_entry_is_patched_to_the_wrapper():
    text = HOOK.read_text(encoding="utf-8")
    assert "s#^Exec=sudo /usr/bin/calamares-launch-normal$#Exec=sudo /usr/bin/hscl-calamares#" in text


def test_the_image_gate_checks_the_wrapper():
    text = GATE.read_text(encoding="utf-8")
    assert "installer runs the software-render wrapper" in text
    assert "installer wrapper exists" in text


def test_the_wrapper_is_executable_in_the_index():
    """The repo has a gate for shebang files; this keeps the new one from tripping it."""
    import subprocess

    out = subprocess.run(
        ["git", "ls-files", "-s", str(WRAPPER.relative_to(ROOT))],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT), check=False,
    )
    mode = out.stdout.split(" ", 1)[0] if out.stdout else ""
    assert mode in {"100755", ""}, f"tracked as {mode}; run git update-index --chmod=+x"
