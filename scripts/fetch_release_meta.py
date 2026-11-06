#!/usr/bin/env python3
"""Write website/data/release.json from the REAL GitHub releases of this repository (via `gh`). Never invents values.

Usage: fetch_release_meta.py [--repo OWNER/NAME] [--out FILE] [--check]

The newest non-draft release is used. The whole-image SHA-256 is read from the release's SHA256SUMS asset (the line for the
file without `.part`). If there is no release, the file says {"release": null} and the site shows "Release not published yet".

Integrity: the hash in SHA256SUMS must equal `iso_sha256` in the release's manifest asset, and the sum of the part sizes must
equal `iso_bytes`. A site that shows numbers the artefact does not have is worse than no site, so a mismatch is an error
(exit 3) instead of a silent write.

`--check` writes nothing and exits 1 when the committed file is stale - the same drift gate the other generated docs use.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ATTEMPTS = 3
BACKOFF_S = (1, 3)


def gh(*args: str) -> str:
    """Run gh with a bounded retry for transient network/5xx failures (never retries a 404)."""
    last = ""
    for attempt in range(ATTEMPTS):
        r = subprocess.run(["gh", *args], capture_output=True, text=True)
        if r.returncode == 0:
            return r.stdout
        last = (r.stderr or r.stdout).strip()
        if "not found" in last.lower() or "404" in last:
            break
        if attempt < ATTEMPTS - 1:
            time.sleep(BACKOFF_S[min(attempt, len(BACKOFF_S) - 1)])
    raise SystemExit(f"gh {' '.join(args)} failed: {last}")


def get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as f:  # noqa: S310 - https URL of our own release
        return json.loads(f.read().decode())


def build(repo: str) -> dict:
    rels = [r for r in json.loads(gh("api", f"repos/{repo}/releases")) if not r["draft"]]
    if not rels:
        return {"repo": repo, "release": None}

    r = rels[0]
    assets = [{"name": x["name"], "size": x["size"], "url": x["browser_download_url"]} for x in r["assets"]]
    by_name = {a["name"]: a for a in assets}
    whole = None
    if "SHA256SUMS" in by_name:
        with urllib.request.urlopen(by_name["SHA256SUMS"]["url"], timeout=30) as f:  # noqa: S310
            for line in f.read().decode().splitlines():
                h, _, name = line.partition(" ")
                name = name.strip().lstrip("*")
                if name and ".part" not in name:
                    whole = {"name": name, "sha256": h}

    manifest_name = next((n for n in by_name if n.endswith(".manifest.json")), None)
    if manifest_name and whole:
        manifest = get_json(by_name[manifest_name]["url"])
        if manifest.get("iso_sha256") and manifest["iso_sha256"] != whole["sha256"]:
            raise SystemExit(
                f"integrity: SHA256SUMS says {whole['sha256']} but {manifest_name} says {manifest['iso_sha256']}"
            )
        parts = [a for n, a in by_name.items() if ".iso.part" in n]
        if manifest.get("iso_bytes") and parts and sum(p["size"] for p in parts) != manifest["iso_bytes"]:
            raise SystemExit(
                f"integrity: parts sum to {sum(p['size'] for p in parts)} B but the manifest says {manifest['iso_bytes']} B"
            )
        whole = {**whole, "bytes": manifest.get("iso_bytes")} if whole else whole

    return {
        "repo": repo,
        "release": {
            "tag": r["tag_name"],
            "name": r["name"],
            "prerelease": r["prerelease"],
            "published_at": r["published_at"],
            "url": r["html_url"],
            "assets": assets,
            "whole_image": whole,
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="timfromhcs/HSCL1")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[1] / "website/data/release.json"))
    ap.add_argument("--check", action="store_true", help="fail if the committed file is out of date")
    a = ap.parse_args(argv)

    data = build(a.repo)
    text = json.dumps(data, indent=2) + "\n"
    out = Path(a.out)
    if a.check:
        current = out.read_text(encoding="utf-8") if out.exists() else ""
        if current != text:
            print(f"{out} is stale: run python scripts/fetch_release_meta.py", file=sys.stderr)
            return 1
        print(f"{out} is current")
        return 0
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"wrote {out}: " + (data["release"]["tag"] if data["release"] else "no release"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
