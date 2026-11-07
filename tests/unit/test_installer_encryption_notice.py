"""Found 2026-11-07 in the LUKS install run: the installer never says that /boot stays unencrypted (AGENTS.md 6.3 wants it explained).
The image switches Calamares' built-in message on and the image gate checks the CONFIG VALUE only. Seen on the dev2 image: the message does not show
in the automatic erase+encrypt path, so these tests do not prove that users are told (that remains open, see INSTALLER_FACTS.md)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOK = (ROOT / "distro/live/hooks/010-hscl-defaults.sh").read_text(encoding="utf-8")
GATE = (ROOT / "distro/live/verify-image.sh").read_text(encoding="utf-8")


def test_hook_switches_on_the_not_encrypted_boot_message():
    assert "modules/partition.conf" in HOOK
    assert "showNotEncryptedBootMessage: true" in HOOK


def test_image_gate_checks_the_message_is_on():
    assert "installer: warns that /boot is not encrypted" in GATE
    assert "^showNotEncryptedBootMessage: true$" in GATE


def test_the_unencrypted_boot_partition_is_still_the_only_unencrypted_one():
    """The message is only honest while exactly /boot is excluded from encryption (INSTALLER_FACTS.md)."""
    facts = (ROOT / "docs/INSTALLER_FACTS.md").read_text(encoding="utf-8")
    assert "noEncrypt: true" in facts and facts.count("noEncrypt: true") == 1
