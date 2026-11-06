"""Visible-branding fixes found by the content scan of the 0.1.2-alpha.0 candidate (hook edits and their image gates must stay paired)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOK = (ROOT / "distro/live/hooks/010-hscl-defaults.sh").read_text(encoding="utf-8")
GATE = (ROOT / "distro/live/verify-image.sh").read_text(encoding="utf-8")


def test_installer_has_no_upstream_donate_link():
    assert "showDonateUrl: false" in HOOK
    assert "installer: no upstream donate link" in GATE


def test_upstream_website_launchers_are_removed_from_the_menu():
    for name in ("org.kubuntu.web.home.desktop", "org.kfocus.web.howtos.desktop"):
        assert name in HOOK and name in GATE


REMASTER = (ROOT / "scripts/remaster-iso.sh").read_text(encoding="utf-8")


def test_casper_conf_is_not_patched_by_the_hook():
    # r5 (FLAVOUR set in casper.conf) failed to boot: "cow format specified as overlay and no support found"
    code = [line for line in HOOK.splitlines() if not line.lstrip().startswith("#")]
    assert not any("casper.conf" in line for line in code)
    assert "casper.conf keeps FLAVOUR unset" in GATE
    assert "casper.conf is not patched for the live user" in GATE


def test_live_user_comes_from_disk_info_on_the_medium():
    # casper: first word of /cdrom/.disk/info, lower-cased, becomes FLAVOUR, hence USERNAME and HOST
    assert "/.disk/info" in REMASTER and "-map \"$disk_info\" /.disk/info" in REMASTER
    assert "printf 'HSCL1 %s" in REMASTER
    assert "./.disk/info" in REMASTER and "md5sum.txt .disk/info update failed" in REMASTER   # md5sum.txt lists it and must follow
    assert "the ISO does not contain the HSCL1 .disk/info" in REMASTER                    # proof from the finished ISO
    assert REMASTER.index("-map \"$disk_info\" /.disk/info") < REMASTER.index("disk-info.check")



def test_plymouth_animation_does_not_overlap_the_message_line():
    gen = (ROOT / "scripts/gen_plymouth.py").read_text(encoding="utf-8")
    assert "\nVerticalAlignment=.58\n" in gen
