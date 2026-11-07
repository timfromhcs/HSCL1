#!/usr/bin/env python3
"""Evidence for the Secure Boot chain of a built ISO (research question F1, gate G6 preparation).

What this can and cannot do: it proves, from the **finished ISO**, that each boot component is a PE
image carrying an Authenticode certificate table, and it prints the signer of each one. It does not
boot anything: Secure Boot acceptance is decided by firmware during a boot, which is the G6 VM test
(OVMF with the Microsoft keys). A file can be signed and still rejected, and an unsigned file can
still boot with Secure Boot off - so this script reports facts, never a "Secure Boot works" verdict.

Why it matters: a remaster changes filesystem.squashfs and the initrd. Canonical documents that
neither of those is signature-checked (firmware -> Microsoft-signed shim -> Canonical-signed GRUB ->
signed kernel), so the chain *should* survive a remaster. "Should" is not evidence; this script says
what the shipped files actually carry.

Usage: scripts/sb_evidence.py ISO --out DIR [--json]
Extraction uses xorriso (no root, no mount). Requires openssl for the signer names.
"""
from __future__ import annotations

import argparse
import json
import shutil
import struct
import subprocess
import sys
from pathlib import Path

# The files the firmware and GRUB validate, in boot order. Each entry lists the spellings that
# occur in the wild: Ubuntu media use lowercase `EFI/boot/bootx64.efi`, other builders uppercase it,
# and the remaster keeps whatever the base ISO had - so the reader must not assume one casing.
BOOT_FILES = [
    ("EFI/BOOT/BOOTX64.EFI", "EFI/boot/bootx64.efi"),  # the shim (Microsoft-signed)
    ("EFI/boot/grubx64.efi", "EFI/BOOT/GRUBX64.EFI"),  # GRUB, signed by Canonical
    ("casper/vmlinuz", "CASPER/VMLINUZ"),  # the kernel GRUB launches
]
# Present on Ubuntu media and part of the MOK flow; reported, not gated.
OPTIONAL_FILES = [("EFI/boot/mmx64.efi", "EFI/BOOT/MMX64.EFI")]


def pe_certificate_table(data: bytes) -> tuple[int, int] | None:
    """(file offset, size) of the Authenticode certificate table, or None.

    Parses the PE headers only: MZ -> e_lfanew -> "PE\\0\\0" -> COFF header -> optional header ->
    data directory index 4 (IMAGE_DIRECTORY_ENTRY_SECURITY). That entry is special: its "address"
    is a file offset, not an RVA.
    """
    if len(data) < 0x40 or data[:2] != b"MZ":
        return None
    e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
    if e_lfanew + 24 > len(data) or data[e_lfanew : e_lfanew + 4] != b"PE\0\0":
        return None
    coff = e_lfanew + 4
    number_of_sections = struct.unpack_from("<H", data, coff + 2)[0]
    size_of_optional_header = struct.unpack_from("<H", data, coff + 16)[0]
    opt = coff + 20
    if opt + 2 > len(data):
        return None
    magic = struct.unpack_from("<H", data, opt)[0]
    dirs_at = opt + (96 if magic == 0x10B else 112)  # PE32 vs PE32+
    security = dirs_at + 4 * 8
    if security + 8 > opt + size_of_optional_header or security + 8 > len(data):
        return None
    offset, size = struct.unpack_from("<II", data, security)
    if offset == 0 or size == 0 or offset + size > len(data) * 2:
        return None  # no signature, or the size field is nonsense
    return offset, size


def signers(pe: bytes, table: tuple[int, int]) -> list[str]:
    """Common names of the certificates in the PKCS#7 blob, via openssl (no ASN.1 parser here)."""
    offset, size = table
    if not shutil.which("openssl"):
        return []
    blob = pe[offset : offset + size]
    # WIN_CERTIFICATE: dwLength, wRevision, wCertificateType, then the PKCS#7 DER
    if len(blob) < 8:
        return []
    length = struct.unpack_from("<I", blob, 0)[0]
    der = blob[8:length] if 8 < length <= len(blob) else blob[8:]
    r = subprocess.run(["openssl", "pkcs7", "-inform", "DER", "-print_certs", "-noout"],
                       input=der, capture_output=True)
    if r.returncode != 0:
        return []
    out = []
    for line in r.stdout.decode("utf-8", "replace").splitlines():
        line = line.strip()
        if line.upper().startswith("SUBJECT="):
            subject = line.split("=", 1)[1]
            cn = [p.split("=", 1)[1] for p in subject.split(",") if p.strip().startswith("CN=")]
            out.append(cn[0] if cn else subject)
    return out


def extract(iso: Path, member: str, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["xorriso", "-osirrox", "on", "-indev", str(iso),
                        "-extract", f"/{member}", str(dest)],
                       capture_output=True, text=True)
    return r.returncode == 0 and dest.is_file()


def evidence(iso: Path, out: Path) -> dict:
    """One record per boot component: present, PE, certificate table, signers."""
    out.mkdir(parents=True, exist_ok=True)
    records = []
    entries = [(names, True) for names in BOOT_FILES] + [(names, False) for names in OPTIONAL_FILES]
    for names, required in entries:
        record = {"member": names[0], "required": required, "present": False, "pe": False,
                  "cert_table": None, "signers": []}
        for member in names:
            dest = out / member.replace("/", "_")
            if extract(iso, member, dest):
                data = dest.read_bytes()
                record["member"] = member
                record["present"] = True
                record["bytes"] = len(data)
                if table := pe_certificate_table(data):
                    record["pe"] = True
                    record["cert_table"] = {"offset": table[0], "size": table[1]}
                    record["signers"] = signers(data, table)
                else:
                    record["pe"] = data[:2] == b"MZ"
                break
        records.append(record)
    return {"iso": str(iso), "iso_bytes": iso.stat().st_size, "components": records}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("iso")
    ap.add_argument("--out", required=True, help="directory for the extracted files and report.json")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    iso = Path(args.iso)
    if not iso.is_file():
        print(f"no such ISO: {iso}", file=sys.stderr)
        return 2
    if not shutil.which("xorriso"):
        print("xorriso is required to read the ISO without root", file=sys.stderr)
        return 2
    result = evidence(iso, Path(args.out))
    (Path(args.out) / "report.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"ISO {iso.name} ({result['iso_bytes']} bytes)")
        for c in result["components"]:
            if not c["present"]:
                print(f"  {c['member']}: NOT PRESENT")
            elif not c["cert_table"]:
                print(f"  {c['member']}: no certificate table ({c['bytes']} bytes)")
            else:
                who = ", ".join(c["signers"]) or "signer not readable"
                print(f"  {c['member']}: signed by {who} ({c['cert_table']['size']} bytes of PKCS#7)")
        print(f"evidence: {Path(args.out) / 'report.json'}")
        print("Reminder: this says what the files carry, not whether the firmware accepts them - that is gate G6.")
    required = [c for c in result["components"] if c["required"]]
    return 0 if all(c["cert_table"] for c in required) else 1


if __name__ == "__main__":
    sys.exit(main())
