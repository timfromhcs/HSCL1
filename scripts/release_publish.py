#!/usr/bin/env python3
"""Publish a release set in the order that actually works, with --dry-run for the cautious.

Learned on 2026-11-11: `gh release create` with all assets in one call creates the release as a *draft*
and only publishes at the end. The 0.1.6 upload stalled twice on a 1.9 GB part, the process was killed,
and the release stayed a draft with an `untagged-...` URL while `gh release view` happily listed the
assets that had arrived. Uploading the parts one at a time and publishing explicitly fixed it.

This script does exactly that, and refuses to run if the set does not pass the consistency checker.

Usage:
  release_publish.py --version 0.1.6-alpha.0 --release-dir artifacts/release-0.1.6-set \
      [--repo owner/name] [--draft-only] [--dry-run] [--skip-verify]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERIFY = ROOT / "scripts" / "verify_release_consistency.py"


def run(cmd: list[str], dry: bool) -> str:
    printable = " ".join(cmd)
    if dry:
        print(f"[dry-run] {printable}")
        return ""
    print(f"$ {printable}", flush=True)
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    if res.returncode != 0:
        print(res.stdout[-2000:], file=sys.stderr)
        print(res.stderr[-2000:], file=sys.stderr)
        raise SystemExit(f"command failed ({res.returncode}): {printable}")
    return res.stdout


def release_state(tag: str, repo: str) -> dict | None:
    res = subprocess.run(
        ["gh", "release", "view", tag, "--repo", repo, "--json", "tagName,isDraft,isPrerelease,url"],
        capture_output=True, text=True, timeout=120,
    )
    if res.returncode != 0:
        return None
    return json.loads(res.stdout)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    ap.add_argument("--release-dir", required=True, type=Path)
    ap.add_argument("--repo", default="timfromhcs/HSCL1")
    ap.add_argument("--title", default=None)
    ap.add_argument("--notes", default=None, help="notes file (default: <release-dir>/release-notes.md)")
    ap.add_argument("--draft-only", action="store_true", help="stop after the upload, leave the release a draft")
    ap.add_argument("--skip-verify", action="store_true", help="skip the consistency checker (not recommended)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    tag = f"v{a.version}"
    d = a.release_dir
    notes = Path(a.notes) if a.notes else d / "release-notes.md"
    title = a.title or f"HSCL1 {a.version}"

    if not d.is_dir():
        raise SystemExit(f"release dir missing: {d}")
    if not notes.is_file():
        raise SystemExit(f"notes file missing: {notes} (a release without notes is not worth publishing)")

    assets = sorted(d.glob(f"HSCL1-{a.version}-amd64.iso.part*")) + sorted(
        p for p in d.iterdir()
        if p.is_file() and (p.suffix in {".json", ".md"} or p.name == "SHA256SUMS")
    )
    seen, ordered = set(), []
    for p in assets:
        if p.name not in seen and p.is_file():
            seen.add(p.name)
            ordered.append(p)

    if not a.skip_verify:
        run([sys.executable, str(VERIFY), "--version", a.version, "--release-dir", str(d)], a.dry_run)

    state = None if a.dry_run else release_state(tag, a.repo)
    if state is not None:
        if not state["isDraft"]:
            raise SystemExit(f"{tag} is already published ({state['url']}); refusing to touch it")
        print(f"{tag} exists as a draft; uploading the missing assets")

    if state is None:
        # NOTE (2026-11-12): `gh release create --notes-file <path>` sends the body through the Windows system
        # codepage, so a non-ASCII character in the notes reaches GitHub as mojibake while the *uploaded asset* of
        # the same file stays byte-identical. v0.1.7-alpha.0 hit this with a single "->". Passing the notes through
        # stdin did not change it. Release notes are therefore ASCII-only, and `make_release.py` refuses a notes
        # file that is not - that is the gate, this comment is the reason.
        run(["gh", "release", "create", tag, "--repo", a.repo, "--draft", "--title", title,
             "--notes-file", str(notes)], a.dry_run)

    # parts first (they are the ones that stall), then the small files: one call each, so a stall is visible
    for p in ordered:
        run(["gh", "release", "upload", tag, str(p), "--repo", a.repo, "--clobber"], a.dry_run)

    if a.draft_only:
        print(f"left as a draft: publish with `gh release edit {tag} --draft=false`")
        return 0

    is_prerelease = "-" in a.version or a.version.startswith("0.")
    edit_cmd = ["gh", "release", "edit", tag, "--repo", a.repo, "--draft=false"]
    if is_prerelease:
        edit_cmd.append("--prerelease")
    else:
        edit_cmd.append("--latest")
    run(edit_cmd, a.dry_run)

    if not a.dry_run:
        final = release_state(tag, a.repo)
        if not final or final["isDraft"]:
            raise SystemExit("release is still a draft after publishing - investigate before reporting success")
        print(f"published: {final['url']}")
        run([sys.executable, str(VERIFY), "--version", a.version, "--release-dir", str(d),
             "--github", a.repo], False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
