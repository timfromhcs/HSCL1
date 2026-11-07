"""scripts/sb_evidence.py: the PE certificate-table reader that Secure Boot evidence rests on.

The parsing is tested against hand-built PE headers here, because a wrong offset would silently
report "no signature" on a signed file - the kind of error that turns a gate into a rubber stamp.
The end-to-end run against a real ISO happens in the build lab and is recorded in docs/BUILD_LOG.md.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import sb_evidence  # noqa: E402


def make_pe(pe32_plus: bool = True, security_offset: int = 0, security_size: int = 0) -> bytes:
    """Minimal PE image with one data directory filled in (index 4 = certificate table)."""
    e_lfanew = 0x80
    header = bytearray(e_lfanew + 24 + 240)
    header[0:2] = b"MZ"
    struct.pack_into("<I", header, 0x3C, e_lfanew)
    header[e_lfanew : e_lfanew + 4] = b"PE\0\0"
    coff = e_lfanew + 4
    struct.pack_into("<H", header, coff + 2, 1)  # NumberOfSections
    struct.pack_into("<H", header, coff + 16, 240)  # SizeOfOptionalHeader
    opt = coff + 20
    struct.pack_into("<H", header, opt, 0x20B if pe32_plus else 0x10B)
    dirs_at = opt + (112 if pe32_plus else 96)
    struct.pack_into("<II", header, dirs_at + 4 * 8, security_offset, security_size)
    return bytes(header)


def test_no_mz_header_is_not_a_pe():
    assert sb_evidence.pe_certificate_table(b"not a pe at all") is None


def test_a_pe_without_a_signature_reports_none():
    assert sb_evidence.pe_certificate_table(make_pe(security_offset=0, security_size=0)) is None


def test_a_pe32_plus_image_reports_offset_and_size():
    data = make_pe(True, security_offset=0x200, security_size=0x400) + b"\0" * 0x800
    assert sb_evidence.pe_certificate_table(data) == (0x200, 0x400)


def test_a_pe32_image_uses_the_shorter_optional_header():
    """PE32 and PE32+ place the data directory at different offsets; mixing them up reads garbage."""
    data = make_pe(False, security_offset=0x100, security_size=0x200) + b"\0" * 0x400
    assert sb_evidence.pe_certificate_table(data) == (0x100, 0x200)


def test_a_truncated_header_is_none_not_a_panic():
    for cut in (0, 10, 0x40, 0x82, 0x100):
        sb_evidence.pe_certificate_table(make_pe()[:cut])


def test_an_absurd_certificate_size_is_rejected():
    data = make_pe(True, security_offset=0x200, security_size=0xFFFFFF00) + b"\0" * 0x400
    assert sb_evidence.pe_certificate_table(data) is None


def test_the_component_list_covers_shim_grub_and_kernel_in_both_spellings():
    """Ubuntu media ship EFI/boot/bootx64.efi; assuming BOOTX64.EFI reported "NOT PRESENT" on the
    real 0.1.2 ISO (2026-11-07) although the shim was there."""
    flat = [name for group in sb_evidence.BOOT_FILES for name in group]
    assert any(n.endswith("BOOTX64.EFI") for n in flat) and any(n.endswith("bootx64.efi") for n in flat)
    assert any("grubx64.efi" in n.lower() for n in flat)
    assert any(n.lower().endswith("vmlinuz") for n in flat)
    assert len(sb_evidence.BOOT_FILES) == 3
