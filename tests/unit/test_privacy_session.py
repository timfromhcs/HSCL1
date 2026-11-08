"""Tests for Privacy Session specification, threat model boundaries, and ephemeral live configuration."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_threat_model_explicitly_disclaims_tails_and_anonymity():
    tm = (ROOT / "docs/THREAT_MODEL.md").read_text(encoding="utf-8")
    assert "Tails-equivalent" in tm
    assert "Anonymity guarantees" in tm or "anonymity guarantees" in tm.lower()
    assert "forensic invisibility" in tm


def test_known_limitations_privacy_mode_is_honest():
    kl = (ROOT / "docs/KNOWN_LIMITATIONS.md").read_text(encoding="utf-8")
    assert "| Privacy mode | PLANNED |" in kl
    assert "not Tails" in kl
    assert "no anonymity claim" in kl


def test_live_memory_and_ephemeral_storage_configuration():
    zram = (ROOT / "packages/debian/hscl-memory/etc/systemd/zram-generator.conf").read_text(encoding="utf-8")
    assert "zram-size = min(ram / 2, 8192)" in zram
    assert "compression-algorithm = zstd" in zram
    assert "swap-priority = 100" in zram

    swappiness = (ROOT / "packages/debian/hscl-memory/etc/sysctl.d/91-hscl-memory.conf").read_text(encoding="utf-8")
    assert "vm.swappiness = 100" in swappiness

    sysctl = (ROOT / "distro/security/sysctl.d/90-hscl.conf").read_text(encoding="utf-8")
    assert "fs.suid_dumpable = 0" in sysctl


def test_casper_overlay_defaults_preserve_ephemeral_state():
    hook = (ROOT / "distro/live/hooks/010-hscl-defaults.sh").read_text(encoding="utf-8")
    assert "overlay" in hook.lower()

    verify = (ROOT / "distro/live/verify-image.sh").read_text(encoding="utf-8")
    assert "casper.conf keeps FLAVOUR unset" in verify
