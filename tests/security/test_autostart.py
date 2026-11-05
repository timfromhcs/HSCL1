"""Login autostart: hardware autotune is on, KDE Connect (listener on *:1716) is off by default."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def entry(path):
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def test_autotune_runs_at_login_and_is_not_forced():
    e = entry(ROOT / "packages/debian/hscl-desktop/etc/xdg/autostart/hscl-autotune.desktop")
    assert e["Exec"] == "hscl autotune"  # no --force: unchanged hardware and a user lock must stay untouched
    assert e["OnlyShowIn"].startswith("KDE")
    assert e.get("Hidden", "false") != "true"


def test_kdeconnect_daemon_hidden_by_default():
    e = entry(ROOT / "packages/debian/hscl-security/etc/xdg/autostart/org.kde.kdeconnect.daemon.desktop")
    assert e["Hidden"] == "true"


def test_kdeconnect_file_is_diverted_not_overwritten():
    """kdeconnect owns the file; without a dpkg diversion the image build fails ('trying to overwrite')."""
    d = ROOT / "packages/debian/hscl-security/DEBIAN"
    path = "/etc/xdg/autostart/org.kde.kdeconnect.daemon.desktop"
    pre = (d / "preinst").read_text(encoding="utf-8")
    post = (d / "postrm").read_text(encoding="utf-8")
    assert f"--add {path}" in pre and "--package hscl-security" in pre
    assert f"--remove {path}" in post


def test_kdeconnect_dbus_activation_is_diverted_and_stubbed():
    """VM run: the tray applet D-Bus-activates kdeconnectd even with a hidden autostart, so the service file must be stubbed."""
    base = ROOT / "packages/debian/hscl-security"
    svc = "/usr/share/dbus-1/services/org.kde.kdeconnect.service"
    stub = (base / svc.lstrip("/")).read_text(encoding="utf-8")
    assert "Exec=/bin/false" in stub and "Name=org.kde.kdeconnect" in stub
    assert f"--add {svc}" in (base / "DEBIAN/preinst").read_text(encoding="utf-8")
    assert f"--remove {svc}" in (base / "DEBIAN/postrm").read_text(encoding="utf-8")
