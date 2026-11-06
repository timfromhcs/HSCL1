"""The HSCL1 live session starter replaces the upstream one, which showed a blocking "Try or Install Kubuntu" prompt (owner report 2026-11-06)."""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "packages/debian/hscl-branding"
STARTER = PKG / "usr/libexec/start-kubuntu-live-env"


def code_lines(text):
    return [line for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]


def test_starter_never_runs_the_upstream_prompt():
    code = "\n".join(code_lines(STARTER.read_text(encoding="utf-8")))
    assert "kubuntu-installer-prompt" not in code
    assert re.search(r"^startplasma-wayland$", code, re.M)


def test_starter_keeps_the_oem_branch_and_session_environment():
    text = STARTER.read_text(encoding="utf-8")
    assert "oem-config/enable=true" in text
    assert "calamares-launch-oem" in text
    for var in ("XDG_SESSION_CLASS", "XDG_SESSION_DESKTOP", "DESKTOP_SESSION", "QT_QPA_PLATFORMTHEME"):
        assert f'export {var}=' in text


def test_starter_is_a_valid_bash_script():
    # script text on stdin: a path would break where "bash" is WSL's launcher and cannot read Windows paths
    # bytes, not text: text mode would translate newlines to CRLF on Windows and bash rejects the CRs
    r = subprocess.run(["bash", "-n"], input=STARTER.read_bytes(), capture_output=True)
    assert r.returncode == 0, r.stderr.decode("utf-8", "replace")


def test_divert_is_paired_in_preinst_and_postrm():
    pre = (PKG / "DEBIAN/preinst").read_text(encoding="utf-8")
    post = (PKG / "DEBIAN/postrm").read_text(encoding="utf-8")
    target = "/usr/libexec/start-kubuntu-live-env"
    assert f"--divert {target}.kubuntu --add {target}" in pre
    assert f"--remove {target}" in post


def test_image_gate_checks_the_starter():
    gate = (ROOT / "distro/live/verify-image.sh").read_text(encoding="utf-8")
    assert "live starter does not run the prompt" in gate
    assert "original live starter diverted" in gate
