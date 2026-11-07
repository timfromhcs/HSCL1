#!/usr/bin/env python3
"""Assemble a LOCAL release set from verified artifacts. It never tags, uploads or signs anything.

Usage: make_release.py VERSION --iso ISO [--prebuilt QCOW2] --out DIR [--evidence NAME=PATH ...]

The disk image is optional (AGENTS.md 7.1): without --prebuilt the set contains only the ISO and the manifest says
`prebuilt: null` with a note, so "no image was built" is distinguishable from a forgotten key.

Refuses when: an artifact or its manifest is missing, the ISO does not attest Workshop-disabled-by-default, the prebuilt manifest does not say the
credential scan was clean, a manifest hash does not match the file, or a placeholder string is left anywhere.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

PLACEHOLDERS = ("GENERATE_FROM", "ACTUAL_", "TODO", "TBD", "PLACEHOLDER", "FIXME")


class ReleaseError(Exception):
    pass


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(p: Path) -> dict:
    if not p.is_file():
        raise ReleaseError(f"missing file: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def check_no_placeholders(text: str, what: str) -> None:
    for ph in PLACEHOLDERS:
        if ph in text:
            raise ReleaseError(f"placeholder {ph!r} found in {what}")


def build_release(version: str, iso: Path, prebuilt: Path | None, out: Path,
                  evidence: dict[str, Path]) -> list[Path]:
    iso_m = load(iso.with_name(iso.name + ".manifest.json"))
    pre_m = load(prebuilt.with_name(prebuilt.name + ".manifest.json")) if prebuilt else None
    if iso_m.get("workshop_default") != "disabled":
        raise ReleaseError("the ISO manifest does not attest that Workshop is disabled by default")
    if iso_m.get("iso_sha256") != sha256(iso):
        raise ReleaseError("ISO hash differs from its manifest")
    if pre_m is not None:
        if pre_m.get("credential_scan") != "clean":
            raise ReleaseError("prebuilt image: credential scan is not recorded as clean")
        if pre_m.get("image_sha256") != sha256(prebuilt):
            raise ReleaseError("prebuilt image hash differs from its manifest")
    if iso_m.get("git_dirty"):
        raise ReleaseError("the ISO was built from a dirty git tree")
    for name, path in evidence.items():
        if not path.exists():
            raise ReleaseError(f"evidence {name!r} not found: {path}")

    out.mkdir(parents=True, exist_ok=True)
    iso_name = f"HSCL1-{version}-amd64.iso"
    pre_name = f"HSCL1-{version}-amd64-prebuilt.qcow2"
    shutil.copy2(iso, out / iso_name)
    sums = f"{sha256(out / iso_name)}  {iso_name}\n"
    if prebuilt is not None:
        shutil.copy2(prebuilt, out / pre_name)
        sums += f"{sha256(out / pre_name)}  {pre_name}\n"
    (out / "SHA256SUMS").write_text(sums, encoding="utf-8")
    manifest = {
        "product": "HSCL1", "version": version, "architecture": "amd64",
        "iso": {"file": iso_name, **{k: iso_m[k] for k in ("iso_bytes", "iso_sha256", "git_commit", "built_utc", "base_iso_sha256")}},
        "prebuilt": ({"file": pre_name, **{k: pre_m[k] for k in
                      ("image_bytes", "image_sha256", "virtual_bytes", "first_boot")}}
                     if pre_m is not None else None),
        "prebuilt_note": ("not built for this set; the VM disk image is optional (AGENTS.md 7.1) and its absence is "
                          "recorded here so it cannot be mistaken for a forgotten field")
        if pre_m is None else "",
        "evidence": {k: str(v) for k, v in sorted(evidence.items())},
        "signed": False,
        "published": False,
        "note": "Local release set. Not tagged, signed or uploaded: repository visibility, licence and signing key are undecided.",
    }
    text = json.dumps(manifest, indent=2) + "\n"
    check_no_placeholders(text, "build-manifest.json")
    (out / "build-manifest.json").write_text(text, encoding="utf-8")
    image_line = (
        f"- Prebuilt disk image (qcow2, first boot: {pre_m['first_boot']}): `{pre_name}` "
        f"(sha256 `{pre_m['image_sha256']}`)\n"
        if pre_m is not None
        else "- No disk image in this set: the VM image is optional (AGENTS.md 7.1) and was not built.\n"
    )
    notes = (
        f"# HSCL1 {version} (local pre-release set)\n\n"
        "Pre-alpha. Verified in virtual machines only; not tested on physical hardware.\n\n"
        f"- Live/installer ISO: `{iso_name}` (sha256 `{iso_m['iso_sha256']}`)\n"
        + image_line
        + "- Evidence recorded for this set: " + (", ".join(sorted(evidence)) or "none") + "\n\n"
        "Not signed, not tagged, not uploaded. See `docs/KNOWN_LIMITATIONS.md` for what is not verified.\n"
    )
    check_no_placeholders(notes, "release-notes.md")
    (out / "release-notes.md").write_text(notes, encoding="utf-8")
    names = [iso_name, "SHA256SUMS", "build-manifest.json", "release-notes.md"]
    if pre_m is not None:
        names.insert(1, pre_name)
    return [out / n for n in names]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("version")
    ap.add_argument("--iso", required=True)
    ap.add_argument("--prebuilt", help="optional qcow2 prebuilt image")
    ap.add_argument("--out", required=True)
    ap.add_argument("--evidence", action="append", default=[])
    a = ap.parse_args()
    ev = {}
    for item in a.evidence:
        name, _, path = item.partition("=")
        ev[name] = Path(path)
    try:
        prebuilt = Path(a.prebuilt) if a.prebuilt else None
        files = build_release(a.version, Path(a.iso), prebuilt, Path(a.out), ev)
    except ReleaseError as e:
        print("REFUSED:", e)
        return 1
    for f in files:
        print("wrote", f)
    print("BLOCKED (owner decision needed): tag, signature, GitHub upload, Vercel deployment")
    return 0


if __name__ == "__main__":
    sys.exit(main())
