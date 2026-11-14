"""The installed login screen must show the HSCL1 mark, not the KDE gear (Q-44/Q-75).

Measured on rc12 (2026-11-13): the greeter showed the HSCL1 background with the account name but the stock KDE
avatar, because nothing writes an AccountsService entry for the user the installer creates. Pointing `Icon` at
`/home/<user>/.face.icon` does not fix it either - the installed home is 0750 and the greeter runs as `sddm`.
This gate pins the wiring: helper, module, exec order and the world-readable brand asset.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "packages/debian/hscl-branding/usr/bin/hscl-seed-avatar"
CONF = ROOT / "packages/debian/hscl-branding/etc/calamares/modules/hscl_seed_avatar.conf"
HOOK = ROOT / "distro/live/hooks/010-hscl-defaults.sh"
GATE = ROOT / "distro/live/verify-image.sh"


def test_the_helper_points_at_a_world_readable_brand_file():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "icon=/usr/share/hscl/brand/hscl1-mark-256.png" in text
    assert 'echo "Icon=$icon"' in text
    # The permission trap must stay documented: .face.icon inside a 0750 home is unreadable for the greeter.
    assert "0750" in text and "sddm" in text


def test_the_helper_only_touches_human_accounts():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "$uid\" -ge 1000" in text
    assert "$uid\" -lt 60000" in text
    assert "/var/lib/AccountsService/users" in text
    assert "/usr/share/sddm/faces" in text


def test_the_helper_is_posix_sh_without_bashisms():
    text = SCRIPT.read_text(encoding="utf-8")
    assert text.startswith("#!/bin/sh")
    for bashism in ("[[", "function ", "local ", "let "):
        assert bashism not in text, f"{bashism} is not POSIX sh"


def test_the_module_edits_the_target_and_names_the_helper():
    conf = CONF.read_text(encoding="utf-8")
    assert "dontChroot: false" in conf, "the entry must be written inside the installed system"
    assert '"/usr/bin/hscl-seed-avatar"' in conf
    assert "Q-44" in conf and "Q-75" in conf


def test_the_sequence_runs_the_seed_right_after_users():
    hook = HOOK.read_text(encoding="utf-8")
    assert "s|^  - displaymanager$|  - shellprocess@hscl_seed_avatar\\n  - displaymanager|" in hook, (
        "the exec anchor must be displaymanager: `- users` appears in show and exec, so anchoring on it would "
        "patch both lists"
    )
    assert "hscl_seed_avatar.conf" in hook


def test_the_image_gate_checks_the_wiring():
    text = GATE.read_text(encoding="utf-8")
    for line in (
        "installer seeds the login avatar",
        "avatar shellprocess config",
        "avatar step follows users",
        "brand avatar is readable",
        "SDDM theme face is the HSCL1 mark",
        "SDDM default face is the HSCL1 mark",
    ):
        assert line in text, line


def test_the_brand_file_the_helper_references_is_generated_by_the_package():
    """`HS Climate mark 256` must really be produced; the helper silently exits 0 when it is missing."""
    gen = (ROOT / "scripts/gen_brand.py").read_text(encoding="utf-8")
    assert "hscl1-mark-{variant}" in gen or "hscl1-mark-" in gen
    assert "256" in gen, "the 256 px variant the helper uses must be part of the generator's sizes"
    build = (ROOT / "packages/debian/hscl-branding/build.sh").read_text(encoding="utf-8")
    assert "gen_brand.py" in build
