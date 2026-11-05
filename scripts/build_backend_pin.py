#!/usr/bin/env python3
"""Pin the llama.cpp release used by HSCL1: tag, asset names, sizes and sha256 digests from the GitHub release API.

Usage: build_backend_pin.py [TAG]     (default: the newest bNNNN tag with Ubuntu CPU and Vulkan assets)
Writes ai/backends/llama.json. Needs network. The digests come from GitHub; the smoke test re-verifies every download.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "ai/backends/llama.json"
API = "https://api.github.com/repos/ggml-org/llama.cpp/releases"
WANT = {"cpu": "bin-ubuntu-x64.tar.gz", "vulkan": "bin-ubuntu-vulkan-x64.tar.gz"}


def get(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "hscl1-pin-builder", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def pick_release(tag: str | None) -> dict:
    if tag:
        return get(f"{API}/tags/{tag}")
    for r in get(f"{API}?per_page=15"):
        if r["tag_name"].startswith("b") and any(a["name"].endswith(WANT["cpu"]) for a in r["assets"]):
            return r
    raise SystemExit("no suitable release found")


def main() -> int:
    rel = pick_release(sys.argv[1] if len(sys.argv) > 1 else None)
    assets = {}
    for key, suffix in WANT.items():
        a = next((x for x in rel["assets"] if x["name"].endswith(suffix) and "cudart" not in x["name"]), None)
        if a is None or not str(a.get("digest", "")).startswith("sha256:"):
            raise SystemExit(f"{key}: asset or sha256 digest missing in {rel['tag_name']}")
        assets[key] = {"name": a["name"], "size_bytes": a["size"], "sha256": a["digest"].split(":", 1)[1],
                       "url": a["browser_download_url"]}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"schema": 1, "project": "ggml-org/llama.cpp", "licence": "MIT", "tag": rel["tag_name"],
                               "published": rel["published_at"], "assets": assets}, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"pinned {rel['tag_name']} -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
