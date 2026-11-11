#!/usr/bin/env python3
"""Verify that a release set, the README, the website metadata and (optionally) GitHub agree.

This exists because the repository has already shipped drift of exactly this kind: a README that
named a superseded ISO, parts whose hashes were never re-checked after a copy, and a website whose
download metadata pointed at an older tag. Nothing here publishes anything; it only compares what is
on disk, in the docs and on GitHub, and exits non-zero when they disagree.

Usage:
  verify_release_consistency.py --version 0.1.5-alpha.0 --release-dir artifacts/release-0.1.5-set
  ... [--readme README.md] [--website website/data/release.json] [--github owner/repo]

Exit codes: 0 all checks passed or skipped, 1 at least one FAIL, 2 usage error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

PLACEHOLDERS = ("GENERATE_FROM", "ACTUAL_", "TODO", "TBD", "PLACEHOLDER", "FIXME")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
CHUNK = 8 * 1024 * 1024


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def read_sums(path: Path) -> dict[str, str]:
    sums: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        digest, _, name = line.partition("  ")
        sums[name.strip()] = digest.strip()
    return sums


class Report:
    def __init__(self) -> None:
        self.rows: list[tuple[str, str, str]] = []
        self.failed = 0

    def ok(self, check: str, detail: str = "") -> None:
        self.rows.append(("OK", check, detail))

    def fail(self, check: str, detail: str) -> None:
        self.rows.append(("FAIL", check, detail))
        self.failed += 1

    def skip(self, check: str, detail: str) -> None:
        self.rows.append(("SKIP", check, detail))

    def render(self) -> None:
        width = max(len(r[1]) for r in self.rows) if self.rows else 10
        for status, check, detail in self.rows:
            print(f"{status:4}  {check:<{width}}  {detail}")
        print(f"\n{len(self.rows)} checks, {self.failed} failed")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", required=True, help="release version, e.g. 0.1.5-alpha.0")
    ap.add_argument("--release-dir", required=True, type=Path)
    ap.add_argument("--readme", type=Path, default=Path("README.md"))
    ap.add_argument("--website", type=Path, default=Path("website/data/release.json"))
    ap.add_argument("--github", help="owner/repo: also compare the uploaded asset digests")
    args = ap.parse_args(argv)

    d: Path = args.release_dir
    if not d.is_dir():
        print(f"release dir missing: {d}", file=sys.stderr)
        return 2

    r = Report()
    iso = d / f"HSCL1-{args.version}-amd64.iso"
    manifest = d / f"{iso.name}.manifest.json"
    sums_file = d / "SHA256SUMS"
    notes = d / "release-notes.md"
    build_manifest = d / "build-manifest.json"
    sbom = next(iter(sorted(d.glob("SBOM*.spdx.json"))), None)

    for f in (iso, manifest, sums_file, notes, build_manifest):
        if not f.is_file():
            r.fail("set complete", f"missing {f.name}")
    if r.failed:
        r.render()
        return 1

    iso_hash = sha256(iso)
    sums = read_sums(sums_file)

    # LF-only: `sha256sum -c` on Linux reads a trailing \r as part of the file name and rejects every
    # line. The 0.1.5 and 0.1.6 releases shipped CRLF while a lenient parser saw nothing wrong
    # (2026-11-11), so this check exists before anything is parsed.
    sums_raw = sums_file.read_bytes()
    cr = sums_raw.count(b"\r")
    if cr:
        r.fail("checksum line endings", f"{cr} CR bytes: SHA256SUMS must be LF-only")
    else:
        r.ok("checksum line endings", "LF only")

    # --- the ISO itself -----------------------------------------------------
    r.ok("iso hash", f"{iso.name} {iso_hash[:12]}…") if sums.get(iso.name) == iso_hash else r.fail(
        "iso hash", f"SHA256SUMS says {sums.get(iso.name)}, file is {iso_hash}")

    m = json.loads(manifest.read_text(encoding="utf-8"))
    (r.ok("manifest version", m.get("version", "")) if m.get("version") == args.version
     else r.fail("manifest version", f"manifest {m.get('version')} != {args.version}"))
    (r.ok("manifest hash", m.get("iso_sha256", "")[:12] + "…") if m.get("iso_sha256") == iso_hash
     else r.fail("manifest hash", f"manifest {m.get('iso_sha256')} != {iso_hash}"))
    (r.ok("manifest size", str(m.get("iso_bytes"))) if m.get("iso_bytes") == iso.stat().st_size
     else r.fail("manifest size", f"manifest {m.get('iso_bytes')} != {iso.stat().st_size}"))
    commit = str(m.get("git_commit", ""))
    (r.ok("manifest commit", commit[:12]) if re.fullmatch(r"[0-9a-f]{40}", commit)
     else r.fail("manifest commit", f"not a 40-hex commit: {commit!r}"))
    (r.ok("manifest clean tree", "git_dirty=false") if m.get("git_dirty") is False
     else r.fail("manifest clean tree", f"git_dirty={m.get('git_dirty')!r}"))
    (r.ok("workshop stays opt-in", "disabled") if m.get("workshop_default") == "disabled"
     else r.fail("workshop stays opt-in", f"workshop_default={m.get('workshop_default')!r}"))

    # --- the parts ----------------------------------------------------------
    parts = sorted(n for n in sums if ".part" in n)
    if not parts:
        r.fail("parts present", "SHA256SUMS lists no .part files")
    else:
        missing = [p for p in parts if not (d / p).is_file()]
        (r.ok("parts present", f"{len(parts)} parts") if not missing
         else r.fail("parts present", f"missing: {', '.join(missing)}"))
        if not missing:
            bad = [p for p in parts if sha256(d / p) != sums[p]]
            (r.ok("part hashes", f"{len(parts)} match") if not bad
             else r.fail("part hashes", f"mismatch: {', '.join(bad)}"))
            cat = hashlib.sha256()
            for p in parts:
                with (d / p).open("rb") as f:
                    for block in iter(lambda: f.read(CHUNK), b""):
                        cat.update(block)
            (r.ok("parts rejoin to the iso", cat.hexdigest()[:12] + "…") if cat.hexdigest() == iso_hash
             else r.fail("parts rejoin to the iso", f"{cat.hexdigest()} != {iso_hash}"))

    # --- notes, build manifest, sbom ---------------------------------------
    note_text = notes.read_text(encoding="utf-8")
    found = [t for t in PLACEHOLDERS if t in note_text]
    (r.ok("notes without placeholders") if not found else r.fail("notes without placeholders", ", ".join(found)))
    (r.ok("notes name the artifact") if iso_hash in note_text
     else r.fail("notes name the artifact", "the ISO sha256 is not in release-notes.md"))
    bm = json.loads(build_manifest.read_text(encoding="utf-8"))
    bm_hash = bm.get("iso_sha256") or (bm.get("iso") or {}).get("sha256") if isinstance(bm, dict) else None
    (r.ok("build manifest hash") if bm_hash in (None, iso_hash)
     else r.fail("build manifest hash", f"{bm_hash} != {iso_hash}"))
    if sbom is None:
        r.fail("sbom present", "no SBOM*.spdx.json in the release dir")
    else:
        doc = json.loads(sbom.read_text(encoding="utf-8"))
        (r.ok("sbom present", f"{sbom.name}, {len(doc.get('packages', []))} packages")
         if doc.get("spdxVersion") else r.fail("sbom present", "not an SPDX document"))

    # --- README -------------------------------------------------------------
    if args.readme.is_file():
        text = args.readme.read_text(encoding="utf-8")
        (r.ok("readme names the iso hash") if iso_hash in text
         else r.fail("readme names the iso hash", f"{iso_hash[:12]}… not found in {args.readme}"))
        missing = [p for p in parts if sums.get(p, "") not in text]
        (r.ok("readme lists every part hash") if not missing
         else r.fail("readme lists every part hash", f"missing: {', '.join(missing)}"))
        (r.ok("readme names the version") if args.version in text
         else r.fail("readme names the version", args.version))
    else:
        r.skip("readme checks", f"{args.readme} not found")

    # --- website ------------------------------------------------------------
    if args.website.is_file():
        web = json.loads(args.website.read_text(encoding="utf-8")).get("release") or {}
        tag = str(web.get("tag", ""))
        (r.ok("website tag", tag) if tag == f"v{args.version}"
         else r.fail("website tag", f"{tag} != v{args.version}"))
        whole = (web.get("whole_image") or {}).get("sha256")
        (r.ok("website iso hash") if whole == iso_hash
         else r.fail("website iso hash", f"{whole} != {iso_hash}"))
        names = {a.get("name") for a in web.get("assets", [])}
        missing = [p for p in parts if p not in names]
        (r.ok("website lists every part") if not missing
         else r.fail("website lists every part", f"missing: {', '.join(missing)}"))
    else:
        r.skip("website checks", f"{args.website} not found")

    # --- GitHub (optional) ---------------------------------------------------
    if args.github:
        try:
            out = subprocess.run(
                ["gh", "api", f"repos/{args.github}/releases/tags/v{args.version}",
                 "--jq", ".assets[] | \"\\(.name) \\(.digest)\""],
                capture_output=True, text=True, check=True, timeout=120,
            ).stdout
            remote = {}
            for line in out.splitlines():
                name, _, digest = line.partition(" ")
                remote[name] = digest.removeprefix("sha256:")
            bad = [p for p in parts if remote.get(p) != sums.get(p)]
            (r.ok("github part digests", f"{len(parts)} match") if not bad
             else r.fail("github part digests", f"mismatch: {', '.join(bad)}"))
            (r.ok("github sums asset") if remote.get("SHA256SUMS") else r.fail("github sums asset", "SHA256SUMS not uploaded"))
            # The published notes are what users read. They drifted once (the generator still claimed
            # "not tagged, not uploaded" after publishing), so compare them with the local file.
            body = subprocess.run(
                ["gh", "api", f"repos/{args.github}/releases/tags/v{args.version}", "--jq", ".body"],
                capture_output=True, text=True, check=True, timeout=120,
            ).stdout
            local_notes = notes.read_text(encoding="utf-8")
            if " ".join(body.split()) == " ".join(local_notes.split()):
                r.ok("github release notes", "identical to release-notes.md")
            else:
                r.fail("github release notes", "the published body differs from release-notes.md")
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            r.skip("github checks", f"gh unavailable: {e}")

    r.render()
    return 0 if r.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
