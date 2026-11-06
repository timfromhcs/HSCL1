#!/usr/bin/env python3
"""Write website/data/release.json from the REAL GitHub releases of this repository (via `gh`). Never invents values.

Usage: fetch_release_meta.py [--repo OWNER/NAME] [--out FILE]
The newest non-draft release is used. The whole-image SHA-256 is read from the release's SHA256SUMS asset (the line for the
file without `.part`). If there is no release, the file says {"release": null} and the site shows "Release not published yet".
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.request
from pathlib import Path


def gh(*args: str) -> str:
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="timfromhcs/HSCL1")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[1] / "website/data/release.json"))
    a = ap.parse_args()
    rels = [r for r in json.loads(gh("api", f"repos/{a.repo}/releases")) if not r["draft"]]
    if not rels:
        data = {"repo": a.repo, "release": None}
    else:
        r = rels[0]
        assets = [{"name": x["name"], "size": x["size"], "url": x["browser_download_url"]} for x in r["assets"]]
        whole = None
        sums = next((x for x in assets if x["name"] == "SHA256SUMS"), None)
        if sums:
            with urllib.request.urlopen(sums["url"], timeout=30) as f:  # noqa: S310 - https URL of our own release
                for line in f.read().decode().splitlines():
                    h, _, name = line.partition(" ")
                    name = name.strip().lstrip("*")
                    if name and ".part" not in name:
                        whole = {"name": name, "sha256": h}
        data = {"repo": a.repo, "release": {"tag": r["tag_name"], "name": r["name"], "prerelease": r["prerelease"],
                "published_at": r["published_at"], "url": r["html_url"], "assets": assets, "whole_image": whole}}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {a.out}: " + (data["release"]["tag"] if data["release"] else "no release"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
