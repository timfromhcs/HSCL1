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
import datetime
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

PLACEHOLDERS = ("GENERATE_FROM", "ACTUAL_", "TODO", "TBD", "PLACEHOLDER", "FIXME")

# AGENTS.md 14.2, in order. These are reviewed attestations backed by hashed
# local evidence, not a replacement for executing the underlying VM/security gates.
STABLE_GATES = (
    "iso_build", "artifact_manifest", "uefi_boot", "secure_boot_status",
    "live_desktop", "installer_start", "vm_install", "installed_reboot",
    "luks2", "desktop_components", "critical_i18n", "doctor",
    "apt_sources", "lab_isolation", "privacy_claims", "vulnerabilities",
    "release_docs", "supply_chain", "release_links", "website_build", "limitations",
)
VERSION_RE = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?")


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
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError) as e:
        raise ReleaseError(f"invalid JSON file: {p}: {e}") from e
    if not isinstance(data, dict):
        raise ReleaseError(f"expected JSON object: {p}")
    return data


def check_no_placeholders(text: str, what: str) -> None:
    for ph in PLACEHOLDERS:
        if ph in text:
            raise ReleaseError(f"placeholder {ph!r} found in {what}")


def validate_readiness(path: Path | None, version: str, iso_m: dict) -> dict:
    if path is None:
        raise ReleaseError("stable release requires --readiness with all AGENTS.md 14.2 gates")
    report = load(path)
    check_no_placeholders(json.dumps(report), "readiness")
    for key, value in (("schema", "hcs.release-readiness.v1"), ("version", version),
                       ("iso_sha256", iso_m["iso_sha256"]), ("git_commit", iso_m["git_commit"])):
        if report.get(key) != value:
            raise ReleaseError(f"readiness {key} differs from the release artifact")
    if not isinstance(report.get("reviewer"), str) or not report["reviewer"].strip():
        raise ReleaseError("readiness requires a named reviewer")
    gates = report.get("gates")
    if not isinstance(gates, dict) or set(gates) != set(STABLE_GATES):
        raise ReleaseError("readiness must contain exactly the 21 stable gates")
    for name in STABLE_GATES:
        gate = gates[name]
        if not isinstance(gate, dict) or gate.get("status") != "PASS":
            raise ReleaseError(f"readiness gate {name}: not PASS")
        items = gate.get("evidence")
        if not isinstance(items, list) or not items:
            raise ReleaseError(f"readiness gate {name}: missing evidence")
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get("path"), str) or not item["path"]:
                raise ReleaseError(f"readiness gate {name}: invalid evidence entry")
            evidence_path = path.parent / item["path"]
            if not evidence_path.is_file() or evidence_path.stat().st_size == 0:
                raise ReleaseError(f"readiness gate {name}: evidence is not a nonempty file")
            if item.get("sha256") != sha256(evidence_path):
                raise ReleaseError(f"readiness gate {name}: evidence hash differs")
    return report


def build_release(version: str, iso: Path, prebuilt: Path | None, out: Path,
                  evidence: dict[str, Path], gaps: list[str] | None = None,
                  readiness: Path | None = None) -> list[Path]:
    match = VERSION_RE.fullmatch(version)
    if match is None:
        raise ReleaseError("invalid release version (expected numeric major.minor.patch with optional prerelease)")
    stable = int(match[1]) >= 1 and match[4] is None
    gaps = [g.strip() for g in (gaps or [])]
    if any(not g for g in gaps):
        raise ReleaseError("an empty gap line would render a blank bullet; drop it instead")
    check_no_placeholders("\n".join(gaps), "release gaps")
    iso_m = load(iso.with_name(iso.name + ".manifest.json"))
    pre_m = load(prebuilt.with_name(prebuilt.name + ".manifest.json")) if prebuilt else None
    check_no_placeholders(json.dumps(iso_m), "ISO manifest")
    if iso_m.get("version") != version:
        raise ReleaseError("requested version differs from the ISO manifest version; rebuild instead of relabelling")
    if iso_m.get("product") != "HSCL1" or iso_m.get("qa_image") is not False:
        raise ReleaseError("expected an HSCL1 release image, not a QA image")
    if iso_m.get("git_dirty") is not False:
        raise ReleaseError("the ISO was built from a dirty git tree or has no explicit clean-tree attestation")
    if not re.fullmatch(r"[0-9a-f]{40}", str(iso_m.get("git_commit", ""))):
        raise ReleaseError("ISO manifest requires a full git commit")
    if not re.fullmatch(r"[0-9a-f]{64}", str(iso_m.get("base_iso_sha256", ""))):
        raise ReleaseError("ISO manifest requires base hash")
    timestamp = iso_m.get("built_utc")
    if not isinstance(timestamp, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", timestamp):
        raise ReleaseError("ISO manifest requires a UTC build timestamp")
    try:
        datetime.datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as e:
        raise ReleaseError("ISO manifest has an invalid build timestamp") from e
    if not iso.is_file() or iso_m.get("iso_bytes") != iso.stat().st_size or iso.stat().st_size == 0:
        raise ReleaseError("ISO size differs from its manifest or artifact is missing/empty")
    if iso_m.get("workshop_default") != "disabled":
        raise ReleaseError("the ISO manifest does not attest that Workshop is disabled by default")
    if iso_m.get("iso_sha256") != sha256(iso):
        raise ReleaseError("ISO hash differs from its manifest")
    if pre_m is not None:
        check_no_placeholders(json.dumps(pre_m), "prebuilt manifest")
        if pre_m.get("hscl1_version") != version:
            raise ReleaseError("prebuilt image version differs from the requested release version")
        if not prebuilt.is_file() or pre_m.get("image_bytes") != prebuilt.stat().st_size:
            raise ReleaseError("prebuilt image size differs from its manifest")
        if not pre_m.get("first_boot") or not isinstance(pre_m.get("virtual_bytes"), int):
            raise ReleaseError("prebuilt image requires first_boot and virtual_bytes")
        if pre_m.get("credential_scan") != "clean":
            raise ReleaseError("prebuilt image: credential scan is not recorded as clean")
        if pre_m.get("image_sha256") != sha256(prebuilt):
            raise ReleaseError("prebuilt image hash differs from its manifest")
    for name, path in evidence.items():
        check_no_placeholders(name + str(path), "evidence")
        if not path.is_file() or path.stat().st_size == 0:
            raise ReleaseError(f"evidence {name!r} not found: {path}")
    readiness_report = validate_readiness(readiness, version, iso_m) if stable or readiness else None
    if stable and gaps:
        raise ReleaseError("stable release cannot waive gates with --gap; use a prerelease")
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise ReleaseError("output directory must be empty; existing release files are never overwritten")

    out.mkdir(parents=True, exist_ok=True)
    iso_name = f"HSCL1-{version}-amd64.iso"
    pre_name = f"HSCL1-{version}-amd64-prebuilt.qcow2"
    shutil.copy2(iso, out / iso_name)
    sums = f"{sha256(out / iso_name)}  {iso_name}\n"
    if prebuilt is not None:
        shutil.copy2(prebuilt, out / pre_name)
        sums += f"{sha256(out / pre_name)}  {pre_name}\n"
    (out / "SHA256SUMS").write_text(sums, encoding="utf-8", newline="\n")
    manifest = {
        "product": "HSCL1", "version": version, "architecture": "amd64",
        "iso": {"file": iso_name, **{k: iso_m[k] for k in ("iso_bytes", "iso_sha256", "git_commit", "built_utc", "base_iso_sha256")}},
        "prebuilt": ({"file": pre_name, **{k: pre_m[k] for k in
                      ("hscl1_version", "image_bytes", "image_sha256", "virtual_bytes", "first_boot")}}
                     if pre_m is not None else None),
        "prebuilt_note": ("not built for this set; the VM disk image is optional (AGENTS.md 7.1) and its absence is "
                          "recorded here so it cannot be mistaken for a forgotten field")
        if pre_m is None else "",
        "evidence": {k: str(v) for k, v in sorted(evidence.items())},
        "signed": False,
        "published": False,
        "readiness": readiness_report,
        "evidence_sha256": {k: sha256(v) for k, v in sorted(evidence.items())},
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
        f"# HSCL1 {version} (local {'stable candidate' if stable else 'pre-release'} set)\n\n"
        + ("Stable gate attestations validated; publication and signing are separate steps.\n\n" if stable else
           "Preview assembly does not certify boot or installation. See the supplied evidence and gaps.\n\n")
        + f"- Live/installer ISO: `{iso_name}` (sha256 `{iso_m['iso_sha256']}`)\n"
        + image_line
        + "- Evidence recorded for this set: " + (", ".join(sorted(evidence)) or "none") + "\n\n"
        + ("## Not verified in this set\n\n" + "".join(f"- {g}\n" for g in gaps) + "\n" if gaps else "")
        + "Not signed. Tagging and upload are separate, owner-run steps; this set was assembled locally. See `docs/KNOWN_LIMITATIONS.md` for what is not verified.\n"
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
    ap.add_argument("--readiness", type=Path, help="reviewed, artifact-bound report required for stable 1.x+; see docs/RELEASE_PROCESS.md")
    ap.add_argument("--gap", action="append", default=[],
                    help="one line for the \"not verified\" list in the release notes; repeatable")
    a = ap.parse_args()
    ev = {}
    for item in a.evidence:
        name, _, path = item.partition("=")
        ev[name] = Path(path)
    try:
        prebuilt = Path(a.prebuilt) if a.prebuilt else None
        files = build_release(a.version, Path(a.iso), prebuilt, Path(a.out), ev, a.gap, a.readiness)
    except ReleaseError as e:
        print("REFUSED:", e)
        return 1
    for f in files:
        print("wrote", f)
    print("BLOCKED (owner decision needed): tag, signature, GitHub upload, Vercel deployment")
    return 0


if __name__ == "__main__":
    sys.exit(main())
