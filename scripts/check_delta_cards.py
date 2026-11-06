#!/usr/bin/env python3
"""Gate for abliterated models (plan E1): every abliterated model in `ai/catalog/models.json` needs a delta card in
`ai/catalog/delta-cards.json` that says honestly whether anything was measured, and none of them may appear in the image sources.

A delta card records how much a refusal-removed model differs from its stock parent: refusal rate, how often it calls a tool although
no tool fits ("tool over-call", measured on a published card as 142 vs 95 of 330 cases), and KL divergence to the stock model.
`measured_by` is `own` (evidence file under docs/), `third-party` (https URL, one author's measurement) or `none` (nothing measured:
all numbers null). Nothing is invented: `none` is a valid, visible state and is counted as "unmeasured" in the report.

Usage: python scripts/check_delta_cards.py [--root DIR] [--report]      Exit codes: 0 = ok, 1 = problems found.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
from pathlib import Path

REQUIRED_FIELDS = ("measured_by", "refusal_rate", "tool_overcall_rate", "kl_vs_stock", "date", "source", "note")
MEASURED_BY = ("own", "third-party", "none")
SHIP_DIRS = ("distro", "packages")
MAX_SCAN_BYTES = 1_000_000


def is_abliterated(m: dict) -> bool:
    text = " ".join(str(m.get(k, "")) for k in ("id", "variant", "warning")).lower()
    return any(w in text for w in ("abliterat", "heretic", "uncensor"))


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def _number(v: object) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _card_errors(root: Path, mid: str, c: dict) -> list[str]:
    errs = [f"{mid}: missing field {f}" for f in REQUIRED_FIELDS if f not in c]
    if errs:
        return errs
    mb = c["measured_by"]
    if mb not in MEASURED_BY:
        return [f"{mid}: measured_by must be one of {MEASURED_BY}, got {mb!r}"]
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(c["date"])):
            raise ValueError
        datetime.date.fromisoformat(c["date"])
    except ValueError:
        errs.append(f"{mid}: date must be YYYY-MM-DD, got {c['date']!r}")
    nums = {"refusal_rate": (0.0, 1.0), "tool_overcall_rate": (0.0, 1.0), "kl_vs_stock": (0.0, float("inf"))}
    if mb == "none":
        errs += [f"{mid}: {k} must be null when nothing was measured" for k in nums if c[k] is not None]
        return errs
    for k, (lo, hi) in nums.items():
        v = c[k]
        if not _number(v) or not lo <= v <= hi:
            errs.append(f"{mid}: {k} must be a number in [{lo}, {hi}] when measured, got {v!r}")
    src = str(c["source"])
    if mb == "own":
        p = Path(src)
        if not src.startswith("docs/") or ".." in p.parts or not (root / p).is_file():
            errs.append(f"{mid}: source must be an existing evidence file under docs/, got {src!r}")
    elif not src.startswith("https://"):
        errs.append(f"{mid}: source of a third-party measurement must be an https URL, got {src!r}")
    return errs


def _shipped_hits(root: Path, tokens: dict[str, set[str]]) -> list[str]:
    hits = []
    for d in SHIP_DIRS:
        base = root / d
        if not base.is_dir():
            continue
        for dirpath, _dirs, files in os.walk(base):
            for f in files:
                p = Path(dirpath) / f
                try:
                    if p.stat().st_size > MAX_SCAN_BYTES:
                        continue
                    text = p.read_bytes().decode("utf-8", errors="ignore")
                except OSError:
                    continue
                for mid, toks in tokens.items():
                    if any(t and t in text for t in toks):
                        hits.append(f"{mid}: ships in the image sources ({p.relative_to(root).as_posix()})")
    return hits


def check(root: Path) -> list[str]:
    root = Path(root)
    models = (_load(root / "ai/catalog/models.json") or {}).get("models", [])
    cards = (_load(root / "ai/catalog/delta-cards.json") or {}).get("cards", {})
    abl = {m["id"]: m for m in models if is_abliterated(m)}
    errs: list[str] = []
    for mid in sorted(abl):
        if mid not in cards:
            errs.append(f"{mid}: no delta card in ai/catalog/delta-cards.json")
        else:
            errs += _card_errors(root, mid, cards[mid])
    errs += [f"{cid}: card for an id that is not an abliterated catalog model" for cid in sorted(cards) if cid not in abl]
    errs += _shipped_hits(root, {mid: {mid, str(m.get("file", ""))} for mid, m in abl.items()})
    return errs


def report(root: Path) -> dict:
    root = Path(root)
    models = (_load(root / "ai/catalog/models.json") or {}).get("models", [])
    cards = (_load(root / "ai/catalog/delta-cards.json") or {}).get("cards", {})
    ids = [m["id"] for m in models if is_abliterated(m)]
    out = {"abliterated": len(ids), "own": 0, "third-party": 0, "unmeasured": 0}
    for mid in ids:
        mb = cards.get(mid, {}).get("measured_by", "none")
        out["unmeasured" if mb == "none" else mb] += 1
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--report", action="store_true", help="also print how many abliterated models are measured")
    a = ap.parse_args(argv)
    errs = check(a.root)
    for e in errs:
        print(f"delta-cards: {e}")
    if a.report:
        r = report(a.root)
        print(f"abliterated models: {r['abliterated']}; measured by us: {r['own']}; third-party only: {r['third-party']}; unmeasured: {r['unmeasured']}")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
