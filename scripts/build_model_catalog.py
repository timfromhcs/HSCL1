#!/usr/bin/env python3
"""Build ai/catalog/models.json from ai/catalog/sources.json using the Hugging Face API (needs network).

For each source the single-file GGUF matching `quant` is looked up in the repo tree: exact file name, size and the LFS sha256
come from the API; the licence comes from the model card metadata. An optional `mmproj` file (vision projector) is recorded.
Entries without exactly one matching file are reported and skipped. Nothing is downloaded.

Usage: build_model_catalog.py [--offline-check]   (--offline-check only validates the committed models.json)
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "ai/catalog/sources.json"
OUT = ROOT / "ai/catalog/models.json"
API = "https://huggingface.co/api/models/"
WARNING = ("Community-derived 'abliterated' model: refusal behaviour was removed by the community, not by the base publisher. "
           "Quality and safety are not guaranteed; you are responsible for how you use it.")
REQUIRED = ("id", "repo", "file", "size_bytes", "sha256", "quant", "tier", "role", "variant", "base_model", "licence", "mtp", "min_ram_gb", "warning")


def get(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "hscl1-catalog-builder"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def pick(tree: list[dict], quant: str) -> dict | None:
    cands = [f for f in tree if f.get("path", "").endswith(".gguf") and f["path"].endswith(f"{quant}.gguf")
             and "mmproj" not in f["path"] and "-of-" not in f["path"]]
    return cands[0] if len(cands) == 1 else None


def build() -> list[dict]:
    out, skipped = [], []
    for s in json.loads(SRC.read_text(encoding="utf-8"))["models"]:
        tree = get(f"{API}{s['repo']}/tree/main")
        info = get(f"{API}{s['repo']}")
        f = pick(tree, s["quant"])
        if f is None or not (f.get("lfs") or {}).get("oid"):
            skipped.append(s["id"])
            continue
        mm = next((t for t in tree if "mmproj" in t.get("path", "") and t["path"].endswith("Q8_0.gguf")), None)
        entry = {
            "id": s["id"], "repo": s["repo"], "file": f["path"], "size_bytes": f["size"], "sha256": f["lfs"]["oid"],
            "quant": s["quant"], "tier": s["tier"], "role": s["role"], "variant": s["variant"], "base_model": s["base_model"],
            "licence": (info.get("cardData") or {}).get("license", "unknown"), "mtp": s["mtp"], "min_ram_gb": s["min_ram_gb"],
            "warning": WARNING if s["variant"] == "abliterated" else "",
            "source_url": f"https://huggingface.co/{s['repo']}",
        }
        if mm:
            entry["mmproj"] = {"file": mm["path"], "size_bytes": mm["size"], "sha256": mm["lfs"]["oid"]}
        out.append(entry)
    if skipped:
        print("skipped (no single matching GGUF with an LFS hash):", ", ".join(skipped), file=sys.stderr)
    return out


def validate(models: list[dict]) -> list[str]:
    bad = []
    seen = set()
    for m in models:
        for k in REQUIRED:
            if k not in m:
                bad.append(f"{m.get('id')}: missing {k}")
        if m.get("id") in seen:
            bad.append(f"duplicate id {m.get('id')}")
        seen.add(m.get("id"))
        if len(str(m.get("sha256", ""))) != 64:
            bad.append(f"{m.get('id')}: sha256 must be 64 hex chars")
        if not str(m.get("file", "")).endswith(".gguf"):
            bad.append(f"{m.get('id')}: only GGUF files are allowed")
        if m.get("variant") == "abliterated" and not m.get("warning"):
            bad.append(f"{m.get('id')}: abliterated entries need the warning text")
        if m.get("licence") in (None, "", "unknown"):
            bad.append(f"{m.get('id')}: licence unknown")
    return bad


def main() -> int:
    if "--offline-check" in sys.argv:
        problems = validate(json.loads(OUT.read_text(encoding="utf-8"))["models"])
        print("catalog OK" if not problems else "\n".join(problems))
        return 1 if problems else 0
    models = build()
    problems = validate(models)
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    OUT.write_text(json.dumps({"schema": 1, "generated_from": "Hugging Face API", "models": models}, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {OUT} ({len(models)} models)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
