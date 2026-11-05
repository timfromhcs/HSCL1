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
