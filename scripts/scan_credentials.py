#!/usr/bin/env python3
"""Scan an unpacked/mounted root filesystem for credentials that must not ship in a prebuilt image.

Usage: scan_credentials.py ROOT [--allow-user NAME ...] [--secret TEXT ...]
Exit 0 only when nothing is found. Findings are printed one per line (no secret values are printed).

Checks: login accounts with a usable password hash, home directories of non-allowed users, SSH host/user keys,
authorized_keys, a non-empty machine-id, and any literal --secret strings in installer/log/config locations.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

LOCKED = ("", "*", "!", "!!", "x")
NOLOGIN = ("nologin", "false")
SECRET_DIRS = ("var/log", "root", "etc", "var/lib/AccountsService", "home")


def passwd_users(root: Path) -> list[tuple[str, int, str, str]]:
    out = []
    p = root / "etc/passwd"
    if p.exists():
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            f = line.split(":")
            if len(f) >= 7:
                out.append((f[0], int(f[2]) if f[2].isdigit() else -1, f[5], f[6]))
    return out


def shadow_hashes(root: Path) -> dict[str, str]:
    p = root / "etc/shadow"
    out = {}
    if p.exists():
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            f = line.split(":")
            if len(f) >= 2:
                out[f[0]] = f[1]
    return out


def scan(root: Path, allow_users: set[str], secrets: list[str]) -> list[str]:
    findings: list[str] = []
    hashes = shadow_hashes(root)
    for name, uid, home, shell in passwd_users(root):
        human = uid >= 1000 and uid < 65534
        if human and name not in allow_users:
            findings.append(f"login account present: {name} (uid {uid})")
        h = hashes.get(name, "*")
        usable = h not in LOCKED and not h.startswith("!") and not h.startswith("*")
        if usable and name not in allow_users:
            findings.append(f"account with a password hash: {name}")
    home = root / "home"
    if home.is_dir():
        for d in sorted(p for p in home.iterdir() if p.is_dir()):
            if d.name not in allow_users:
                findings.append(f"home directory of a non-allowed user: {d.name}")
            if (d / ".ssh").exists():
                findings.append(f"ssh directory in home: {d.name}")
    if (root / "root/.ssh").exists():
        findings.append("ssh directory in /root")
    ssh = root / "etc/ssh"
    if ssh.is_dir():
        for k in ssh.glob("ssh_host_*"):
            findings.append(f"ssh host key present: {k.name}")
    mid = root / "etc/machine-id"
    if mid.exists() and mid.read_text(encoding="utf-8", errors="replace").strip() not in ("", "uninitialized"):
        findings.append("machine-id is set (must be generated on first boot)")
    needles = [s.encode() for s in secrets if s]
    if needles:
        for d in SECRET_DIRS:
            base = root / d
            if not base.exists():
                continue
            for f in base.rglob("*"):
                try:
                    if f.is_file() and not f.is_symlink() and f.stat().st_size < 5_000_000:
                        data = f.read_bytes()
                        if any(n in data for n in needles):
                            findings.append(f"secret string found in /{f.relative_to(root).as_posix()}")
                except OSError:
                    continue
    return findings


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--allow-user", action="append", default=[])
    ap.add_argument("--secret", action="append", default=[])
    a = ap.parse_args()
    root = Path(a.root)
    if not (root / "etc").is_dir():
        print(f"FAIL {root} does not look like a root filesystem")
        return 2
    findings = scan(root, set(a.allow_user), a.secret)
    for f in findings:
        print("FAIL", f)
    print("credential scan: clean" if not findings else f"credential scan: {len(findings)} finding(s)")
    return 0 if not findings else 1


if __name__ == "__main__":
    sys.exit(main())
