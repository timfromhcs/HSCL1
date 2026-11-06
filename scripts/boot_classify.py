#!/usr/bin/env python3
"""Classify a boot log (QEMU serial console or captured text) into a failure class with the first thing to check.

Why: three boot failures of the rebuilt live image (missing BOOT=casper, missing initrd mapping, a blocking prompt) were first read from
screenshots. A serial log plus this classifier names the cause in one line.

Usage: boot_classify.py LOGFILE [--json]
Exit codes: 0 no failure marker found, 1 at least one failure class matched, 2 usage/IO error.
The classifier only looks for markers; "no marker" is NOT proof of a good boot (the desktop check stays with the screenshot gate).
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Rule:
    name: str
    pattern: re.Pattern
    hint: str


def _r(name: str, pattern: str, hint: str) -> Rule:
    return Rule(name, re.compile(pattern, re.IGNORECASE), hint)


# Order matters only for reporting; every matching rule is reported.
RULES: tuple[Rule, ...] = (
    _r("initramfs-shell", r"\(initramfs\)|Gave up waiting for root|ALERT!\s+/dev/\S+ does not exist|BusyBox v[\d.]+ .*built-in shell",
       "the initrd could not mount the root: check conf/conf.d/default-boot-to-casper.conf (BOOT=casper) and that the medium is attached"),
    _r("casper-no-medium", r"Unable to find a (medium|live file ?system)|casper.*(cannot|could not) find",
       "casper found no live medium: check the CD is attached, /casper/filesystem.squashfs exists, md5/layer settings, boot=casper on the command line"),
    _r("kernel-panic", r"Kernel panic - not syncing|end Kernel panic|BUG: unable to handle|Oops: [0-9a-f]+",
       "kernel panic: read the lines before it (VFS: unable to mount root, init not found, missing module in the initrd)"),
    _r("init-failed", r"No working init found|Failed to execute /init|run-init: .*(No such file|not found)",
       "init missing or broken in the rootfs after switch_root: check squashfs content and architecture"),
    _r("emergency-mode", r"You are in emergency mode|Welcome to emergency mode|Cannot open access to console, the root account is locked",
       "systemd dropped to emergency mode: look for the failed unit or mount just above (journal on the serial console)"),
    _r("dependency-failed", r"Dependency failed for ",
       "a systemd unit failed with dependents: the unit named in the line, then its journal"),
    _r("sddm-failed", r"sddm(\[\d+\])?: .*(failed|error|crash)|Failed to start Simple Desktop Display Manager|sddm\.service: Failed",
       "display manager failed: SDDM theme (QML error), session file, or the live session starter"),
    _r("session-starter-failed", r"start-kubuntu-live-env.*(not found|No such file|Permission denied)",
       "the live session starter is missing or not executable: check the divert and exec bit"),
    _r("plymouth-failed", r"plymouthd.*(failed|segfault|error)|Failed to load theme|plymouth: .*(not found|failed)",
       "boot splash daemon problem: theme descriptor and ImageDir, frames present in the initrd"),
    _r("squashfs-error", r"SQUASHFS error|squashfs: .*(error|corrupt)|Unable to read .*squashfs",
       "squashfs read error: image corrupt or truncated copy; compare the ISO hash"),
    _r("oom", r"Out of memory: Killed process|oom-kill:",
       "the guest ran out of memory: raise the VM memory or look at what grew"),
)


def classify(text: str) -> list[dict]:
    """Return one entry per matching rule: class, first matching line (trimmed), line number, hint."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    found: list[dict] = []
    for rule in RULES:
        for no, line in enumerate(lines, 1):
            if rule.pattern.search(line):
                found.append({"class": rule.name, "line": no, "evidence": line.strip()[:200], "hint": rule.hint})
                break
    return found


def detect_hang(last_output_age_s: float, screen_unchanged_s: float, limit_s: float = 120.0) -> dict | None:
    """A hang is silence on the serial console AND an unchanged screen for longer than the limit."""
    if last_output_age_s > limit_s and screen_unchanged_s > limit_s:
        return {"class": "hang", "line": 0, "evidence": f"no serial output for {last_output_age_s:.0f}s and unchanged screen for {screen_unchanged_s:.0f}s",
                "hint": "boot is stuck: read the last serial lines and the final screenshot; check for a blocking prompt"}
    return None


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 2
    try:
        text = open(argv[0], encoding="utf-8", errors="replace").read()
    except OSError as e:
        print(f"cannot read {argv[0]}: {e}", file=sys.stderr)
        return 2
    found = classify(text)
    if "--json" in argv:
        print(json.dumps(found, indent=2))
    elif found:
        for f in found:
            print(f"{f['class']}: line {f['line']}: {f['evidence']}\n  -> {f['hint']}")
    else:
        print("no failure marker found (this is not proof of a good boot)")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
