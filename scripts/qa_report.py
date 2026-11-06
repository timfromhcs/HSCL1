#!/usr/bin/env python3
"""Parse and evaluate the guest report written by the hscl-qa package (see packages/debian/hscl-qa).

Usage: qa_report.py REPORT.txt [--profile live]     exit 0 only if every check passes
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


def parse(text: str) -> dict[str, str]:
    """Split "== name ==" sections into {name: body}. Raises ValueError when the report is incomplete."""
    sections: dict[str, str] = {}
    current = None
    buf: list[str] = []
    for line in text.splitlines():
        m = re.fullmatch(r"== (.+) ==", line)
        if m:
            if current is not None:
                sections[current] = "\n".join(buf).strip()
            current, buf = m.group(1), []
        else:
            buf.append(line)
    if current is not None:
        sections[current] = "\n".join(buf).strip()
    if "end" not in sections:
        raise ValueError("report is incomplete: missing '== end =='")
    return sections


@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""


def kv(body: str) -> dict[str, str]:
    return dict(l.split("=", 1) for l in body.splitlines() if "=" in l)


def evaluate(sections: dict[str, str], profile: str = "live") -> list[Check]:
    checks: list[Check] = []

    def add(name: str, ok: bool, detail: str = "") -> None:
        checks.append(Check(name, bool(ok), detail))

    osr = kv(sections.get("os-release", "").replace('"', ""))
    add("os-release NAME is HSCL1", osr.get("NAME") == "HSCL1", osr.get("NAME", "missing"))
    add("os-release keeps ID=ubuntu", osr.get("ID") == "ubuntu", osr.get("ID", "missing"))
    meta = kv(sections.get("hscl-qa", ""))
    add("desktop session running", meta.get("plasmashell_user", "none") != "none", meta.get("plasmashell_user", "missing"))
    try:
        json.loads(sections.get("hscl-status", ""))
        add("hscl status emits valid JSON", True)
    except json.JSONDecodeError as e:
        add("hscl status emits valid JSON", False, str(e))
    try:
        doc = json.loads(sections.get("hscl-doctor", ""))
        add("hscl doctor emits valid JSON", "checks" in doc or "failed" in doc, "keys=%s" % sorted(doc))
    except json.JSONDecodeError as e:
        add("hscl doctor emits valid JSON", False, str(e))
    add("kernel.kptr_restrict = 2", "kernel.kptr_restrict = 2" in sections.get("sysctl", ""), sections.get("sysctl", "")[:80])
    add("firewall baseline active", "Status: active" in sections.get("ufw", ""), sections.get("ufw", "")[:60])
    add("no failed hscl units", "hscl" not in sections.get("failed-units", ""), sections.get("failed-units", "")[:80])
    lnf = sections.get("user-lookandfeel", "")
    add("default look-and-feel is HCS", lnf == "org.hcs.hscl1.desktop", lnf or "missing")
    return checks


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("report")
    ap.add_argument("--profile", default="live")
    a = ap.parse_args()
    try:
        secs = parse(Path(a.report).read_text(encoding="utf-8", errors="replace"))
    except (ValueError, OSError) as e:
        print("FAIL", e)
        return 2
    checks = evaluate(secs, a.profile)
    for c in checks:
        print(("ok   " if c.ok else "FAIL ") + c.name + ("" if c.ok else f"  [{c.detail}]"))
    sb = secs.get("secure-boot", "").strip().replace("\n", " ")
    print(f"info secure-boot: {sb or 'not reported'}")
    return 0 if all(c.ok for c in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
