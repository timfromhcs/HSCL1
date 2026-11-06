#!/usr/bin/env python3
"""Generate an SPDX 2.3 JSON SBOM from REAL package data: a dpkg status file and/or a Cargo.lock.

Usage: gen_sbom.py --name NAME --version VERSION [--dpkg-status FILE] [--cargo-lock FILE] [--created ISO8601] --out FILE

- dpkg: only packages with status "install ok installed" are listed (name, version, architecture, maintainer, homepage, purl).
- cargo: every locked crate (name, version, registry checksum when present, purl); the workspace crate itself has no source line and is skipped.
- Licences are NOT read from the packages: every `licenseConcluded`/`licenseDeclared` is NOASSERTION. That is the honest state; do not
  describe this SBOM as a licence audit.
- Deterministic: the same inputs and `--created` give byte-identical output (the document namespace is derived from the content hash).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote


def spdx_id(prefix: str, name: str, version: str, arch: str = "") -> str:
    return "SPDXRef-" + prefix + "-" + re.sub(r"[^A-Za-z0-9.-]", "-", f"{name}-{version}{('-' + arch) if arch else ''}")


def parse_dpkg_status(text: str) -> list[dict]:
    out = []
    for block in re.split(r"\n\s*\n", text.strip()):
        f: dict[str, str] = {}
        key = None
        for line in block.splitlines():
            if line[:1] in (" ", "\t") and key:
                continue  # continuation lines (description bodies) are not needed
            if ":" in line:
                key, _, val = line.partition(":")
                f[key.strip()] = val.strip()
        if f.get("Package") and f.get("Version") and f.get("Status", "").endswith("installed") and f["Status"].split()[-1] == "installed":
            out.append(f)
    return sorted(out, key=lambda p: (p["Package"], p.get("Architecture", ""), p["Version"]))


def deb_package(f: dict) -> dict:
    name, ver, arch = f["Package"], f["Version"], f.get("Architecture", "")
    pkg = {
        "SPDXID": spdx_id("deb", name, ver, arch), "name": name, "versionInfo": ver,
        "downloadLocation": "NOASSERTION", "filesAnalyzed": False,
        "licenseConcluded": "NOASSERTION", "licenseDeclared": "NOASSERTION", "copyrightText": "NOASSERTION",
        "externalRefs": [{"referenceCategory": "PACKAGE-MANAGER", "referenceType": "purl",
                          "referenceLocator": f"pkg:deb/ubuntu/{quote(name)}@{quote(ver)}" + (f"?arch={arch}" if arch else "")}],
    }
    if f.get("Maintainer"):
        pkg["supplier"] = "Organization: " + f["Maintainer"]
    if f.get("Homepage"):
        pkg["homepage"] = f["Homepage"]
    return pkg


def cargo_packages(text: str) -> list[dict]:
    out = []
    for p in tomllib.loads(text).get("package", []):
        if "source" not in p:
            continue
        pkg = {
            "SPDXID": spdx_id("cargo", p["name"], p["version"]), "name": p["name"], "versionInfo": p["version"],
            "downloadLocation": f"https://crates.io/crates/{p['name']}/{p['version']}", "filesAnalyzed": False,
            "licenseConcluded": "NOASSERTION", "licenseDeclared": "NOASSERTION", "copyrightText": "NOASSERTION",
            "externalRefs": [{"referenceCategory": "PACKAGE-MANAGER", "referenceType": "purl",
                              "referenceLocator": f"pkg:cargo/{p['name']}@{p['version']}"}],
        }
        if p.get("checksum"):
            pkg["checksums"] = [{"algorithm": "SHA256", "checksumValue": p["checksum"]}]
        out.append(pkg)
    return sorted(out, key=lambda p: (p["name"], p["versionInfo"]))


def build(name: str, version: str, created: str, deb_text: str | None, cargo_text: str | None) -> dict:
    pkgs: list[dict] = []
    if deb_text is not None:
        pkgs += [deb_package(f) for f in parse_dpkg_status(deb_text)]
    if cargo_text is not None:
        pkgs += cargo_packages(cargo_text)
    seen: dict[str, int] = {}
    for p in pkgs:  # SPDXIDs must be unique: disambiguate a (rare) duplicate instead of dropping a package
        n = seen.get(p["SPDXID"], 0)
        seen[p["SPDXID"]] = n + 1
        if n:
            p["SPDXID"] += f"-dup{n}"
    root = {"SPDXID": "SPDXRef-Root", "name": name, "versionInfo": version, "downloadLocation": "NOASSERTION", "filesAnalyzed": False,
            "licenseConcluded": "NOASSERTION", "licenseDeclared": "NOASSERTION", "copyrightText": "NOASSERTION"}
    body = {"packages": [root, *pkgs]}
    digest = hashlib.sha256(json.dumps([name, version, [(p["SPDXID"], p["versionInfo"]) for p in pkgs]]).encode()).hexdigest()
    return {
        "spdxVersion": "SPDX-2.3", "dataLicense": "CC0-1.0", "SPDXID": "SPDXRef-DOCUMENT", "name": f"{name}-{version}",
        "documentNamespace": f"https://github.com/timfromhcs/HSCL1/sbom/{name}-{version}-{digest[:16]}",
        "creationInfo": {"created": created, "creators": ["Tool: hscl-gen-sbom"],
                         "comment": "Package inventory only. Licences are NOASSERTION; this is not a licence audit."},
        **body,
        "relationships": [{"spdxElementId": "SPDXRef-DOCUMENT", "relationshipType": "DESCRIBES", "relatedSpdxElement": "SPDXRef-Root"}]
        + [{"spdxElementId": "SPDXRef-Root", "relationshipType": "CONTAINS", "relatedSpdxElement": p["SPDXID"]} for p in pkgs],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--version", required=True)
    ap.add_argument("--dpkg-status")
    ap.add_argument("--cargo-lock")
    ap.add_argument("--created", default=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    if not a.dpkg_status and not a.cargo_lock:
        print("need --dpkg-status and/or --cargo-lock", file=sys.stderr)
        return 2
    deb = Path(a.dpkg_status).read_text(encoding="utf-8", errors="replace") if a.dpkg_status else None
    cargo = Path(a.cargo_lock).read_text(encoding="utf-8") if a.cargo_lock else None
    doc = build(a.name, a.version, a.created, deb, cargo)
    Path(a.out).write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {a.out}: {len(doc['packages']) - 1} packages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
