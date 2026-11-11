"""The release consistency checker must fail on the drift it was written for.

It exists because the repository already shipped a README naming a superseded ISO and website
metadata pointing at an older tag. These tests build a tiny but complete release set in tmp_path and
then break one thing at a time; `main()` must return 1 for each break and 0 for the intact set.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import verify_release_consistency as vrc  # noqa: E402

VERSION = "9.9.9-alpha.0"
ISO = f"HSCL1-{VERSION}-amd64.iso"


def build_set(tmp: Path) -> dict[str, Path]:
    rel = tmp / "set"
    rel.mkdir()
    iso = rel / ISO
    iso.write_bytes(b"iso-bytes-" * 100)
    digest = hashlib.sha256(iso.read_bytes()).hexdigest()

    part = rel / f"{ISO}.part000"
    part.write_bytes(iso.read_bytes())

    (rel / "SHA256SUMS").write_text(
        f"{digest}  {ISO}\n{digest}  {part.name}\n", encoding="utf-8", newline="\n")
    (rel / f"{ISO}.manifest.json").write_text(json.dumps({
        "version": VERSION, "iso_sha256": digest, "iso_bytes": iso.stat().st_size,
        "git_commit": "a" * 40, "git_dirty": False, "workshop_default": "disabled",
    }), encoding="utf-8")
    (rel / "release-notes.md").write_text(f"# HSCL1 {VERSION}\n\n- ISO: {digest}\n", encoding="utf-8")
    (rel / "build-manifest.json").write_text(json.dumps({"iso_sha256": digest}), encoding="utf-8")
    (rel / "SBOM-hscl-cli.spdx.json").write_text(json.dumps({"spdxVersion": "SPDX-2.3", "packages": []}), encoding="utf-8")

    readme = tmp / "README.md"
    readme.write_text(f"Release {VERSION}\n{digest}  {ISO}\n{digest}  {part.name}\n", encoding="utf-8")

    website = tmp / "release.json"
    website.write_text(json.dumps({"release": {
        "tag": f"v{VERSION}", "whole_image": {"sha256": digest},
        "assets": [{"name": ISO}, {"name": part.name}],
    }}), encoding="utf-8")
    return {"rel": rel, "readme": readme, "website": website}


def run(paths: dict[str, Path]) -> int:
    return vrc.main([
        "--version", VERSION,
        "--release-dir", str(paths["rel"]),
        "--readme", str(paths["readme"]),
        "--website", str(paths["website"]),
    ])


def test_a_consistent_set_passes(tmp_path, capsys):
    assert run(build_set(tmp_path)) == 0
    assert "0 failed" in capsys.readouterr().out


def test_a_tampered_part_fails(tmp_path, capsys):
    paths = build_set(tmp_path)
    (paths["rel"] / f"{ISO}.part000").write_bytes(b"different")
    assert run(paths) == 1
    assert "part hashes" in capsys.readouterr().out


def test_readme_missing_the_part_hash_fails(tmp_path, capsys):
    paths = build_set(tmp_path)
    paths["readme"].write_text("nothing useful here\n", encoding="utf-8")
    assert run(paths) == 1
    out = capsys.readouterr().out
    assert "readme names the iso hash" in out and "FAIL" in out


def test_stale_website_tag_fails(tmp_path, capsys):
    paths = build_set(tmp_path)
    data = json.loads(paths["website"].read_text(encoding="utf-8"))
    data["release"]["tag"] = "v0.0.1-alpha.0"
    paths["website"].write_text(json.dumps(data), encoding="utf-8")
    assert run(paths) == 1
    assert "website tag" in capsys.readouterr().out


def test_a_dirty_tree_manifest_fails(tmp_path, capsys):
    paths = build_set(tmp_path)
    manifest = paths["rel"] / f"{ISO}.manifest.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["git_dirty"] = True
    manifest.write_text(json.dumps(data), encoding="utf-8")
    assert run(paths) == 1
    assert "manifest clean tree" in capsys.readouterr().out


def test_crlf_checksums_fail(tmp_path, capsys):
    """The published 0.1.5/0.1.6 SHA256SUMS were CRLF and unverifiable on Linux (2026-11-11)."""
    paths = build_set(tmp_path)
    sums = paths["rel"] / "SHA256SUMS"
    sums.write_bytes(sums.read_bytes().replace(b"\n", b"\r\n"))
    assert run(paths) == 1
    out = capsys.readouterr().out
    assert "checksum line endings" in out and "CR bytes" in out
