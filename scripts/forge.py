#!/usr/bin/env python3
"""forge - one control for the HSCL1 patch/build/test loop (standard library only). Spec: docs/superpowers/plans/2026-11-06-forge-loop.md

Implemented now:  check   local pre-push gate (tests, changed tests again under Linux in WSL, bash -n, ShellCheck in WSL, secret scan)
Planned:          build, boot, test, install, diff, cycle, release (see the plan; they are NOT implemented and not listed in --help)

Rules: print what will run first; stop on the first failure; a skipped step is reported as SKIPPED and makes `check --strict` fail;
write artifacts/forge/<run>/summary.json; --dry-run only prints the steps.
"""
from __future__ import annotations

import argparse
import json
import re
import shlex
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SHELL_GLOBS = ("scripts/*.sh", "distro/live/*.sh", "distro/live/hooks/*.sh", "packages/debian/*/build.sh",
               "packages/debian/*/DEBIAN/preinst", "packages/debian/*/DEBIAN/postinst", "packages/debian/*/DEBIAN/prerm",
               "packages/debian/*/DEBIAN/postrm", "packages/debian/hscl-branding/usr/libexec/start-kubuntu-live-env")

# Same patterns as a reviewer would grep for; deliberately narrow so a hit is almost always real.
SECRET_PATTERNS = (
    ("private key block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("AWS access key id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("generic bearer secret assignment", re.compile(r"(?i)\b(api[_-]?key|secret|token|passwd|password)\b\s*[:=]\s*['\"][A-Za-z0-9/+_\-]{24,}['\"]")),
)
SECRET_SKIP_SUFFIX = (".png", ".jpg", ".ico", ".svg", ".gz", ".xz", ".zst", ".lock", ".pyc", ".gguf", ".iso", ".qcow2")


@dataclass
class Step:
    name: str
    argv: list[str] | None = None        # None: handled in Python (see run_step)
    skip_reason: str | None = None


@dataclass
class Result:
    name: str
    status: str                          # PASS | FAIL | SKIPPED
    seconds: float = 0.0
    detail: str = ""


@dataclass
class Report:
    results: list[Result] = field(default_factory=list)

    def ok(self, strict: bool) -> bool:
        return all(r.status == "PASS" or (r.status == "SKIPPED" and not strict) for r in self.results)


def tracked_files(root: Path = ROOT) -> list[str]:
    out = subprocess.run(["git", "-C", str(root), "ls-files", "-z"], capture_output=True, check=True).stdout
    return [p for p in out.decode("utf-8").split("\0") if p]


def scan_text_for_secrets(text: str) -> list[str]:
    return [label for label, rx in SECRET_PATTERNS if rx.search(text)]


def scan_repo_for_secrets(root: Path = ROOT) -> list[tuple[str, str]]:
    hits: list[tuple[str, str]] = []
    for rel in tracked_files(root):
        if rel.lower().endswith(SECRET_SKIP_SUFFIX) or rel.startswith(("tests/", "artifacts/")):
            continue  # tests contain deliberate fake secrets; artifacts are not tracked
        p = root / rel
        try:
            if p.stat().st_size > 2_000_000:
                continue
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for label in scan_text_for_secrets(text):
            hits.append((rel, label))
    return hits


def shell_files(root: Path = ROOT) -> list[str]:
    seen: list[str] = []
    for pattern in SHELL_GLOBS:
        for p in sorted(root.glob(pattern)):
            rel = p.relative_to(root).as_posix()
            if rel not in seen:
                seen.append(rel)
    return seen


def wsl_available() -> bool:
    if not shutil.which("wsl"):
        return False
    r = subprocess.run(["wsl", "-d", "Ubuntu", "--", "true"], capture_output=True)
    return r.returncode == 0


def changed_test_files(root: Path = ROOT) -> list[str]:
    """Test files that differ from the upstream branch (or HEAD when there is none) plus untracked ones, sorted, repo-relative."""
    def git(*a: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", str(root), *a], capture_output=True, text=True, errors="replace")

    base = "@{u}" if git("rev-parse", "--abbrev-ref", "@{u}").returncode == 0 else "HEAD"
    names = set(git("diff", "--name-only", base).stdout.splitlines())
    names |= set(git("ls-files", "--others", "--exclude-standard").stdout.splitlines())
    return sorted(n for n in names if re.fullmatch(r"tests/.*test_[^/]*\.py", n) and (root / n).is_file())


def plan_check(root: Path = ROOT, have_wsl: bool | None = None, changed: list[str] | None = None) -> list[Step]:
    have_wsl = wsl_available() if have_wsl is None else have_wsl
    changed = changed_test_files(root) if changed is None else changed
    pytest_argv = [sys.executable, "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider"]
    try:
        import xdist  # noqa: F401
        pytest_argv += ["-n", "auto"]
    except ImportError:
        pass
    steps = [Step("pytest", pytest_argv), Step("bash -n", None), Step("secret scan", None)]
    files = shell_files(root)
    posix = "/mnt/" + root.drive[0].lower() + "/" + root.as_posix()[3:] if root.drive else str(root)
    if have_wsl:
        steps.insert(2, Step("shellcheck (WSL)", ["wsl", "-d", "Ubuntu", "--", "bash", "-lc",
                                                  f"cd '{posix}' && shellcheck -S warning {' '.join(files)}"]))
    else:
        steps.insert(2, Step("shellcheck (WSL)", None, skip_reason="WSL Ubuntu not available"))
    # Linux run of the changed tests: CI is Linux, and Windows-only passes hid exec-bit and path problems (2026-11-06).
    name = "pytest (WSL, changed tests)"
    if not have_wsl:
        steps.insert(1, Step(name, None, skip_reason="WSL Ubuntu not available"))
    elif not changed:
        steps.insert(1, Step(name, None, skip_reason="no changed test files"))
    else:
        quoted = " ".join(shlex.quote(f) for f in changed)
        steps.insert(1, Step(name, ["wsl", "-d", "Ubuntu", "--", "bash", "-lc",
                                    f"cd {shlex.quote(posix)} && python3 -m pytest -q -p no:cacheprovider {quoted}"]))
    return steps


def run_step(step: Step, root: Path = ROOT) -> Result:
    t0 = time.time()
    if step.skip_reason:
        return Result(step.name, "SKIPPED", 0.0, step.skip_reason)
    if step.name == "bash -n":
        bad = []
        for rel in shell_files(root):
            r = subprocess.run(["bash", "-n"], input=(root / rel).read_bytes(), capture_output=True)  # bytes: no CRLF translation on Windows
            if r.returncode != 0:
                bad.append(f"{rel}: {r.stderr.decode('utf-8', 'replace').strip()[:120]}")
        return Result(step.name, "FAIL" if bad else "PASS", time.time() - t0, "; ".join(bad))
    if step.name == "secret scan":
        hits = scan_repo_for_secrets(root)
        return Result(step.name, "FAIL" if hits else "PASS", time.time() - t0, "; ".join(f"{p} ({label})" for p, label in hits))
    assert step.argv, step.name
    r = subprocess.run(step.argv, cwd=root, capture_output=True, text=True, errors="replace")
    tail = (r.stdout + r.stderr).strip().splitlines()[-3:]
    return Result(step.name, "PASS" if r.returncode == 0 else "FAIL", time.time() - t0, " | ".join(tail)[:400])


def cmd_check(args: argparse.Namespace) -> int:
    steps = plan_check()
    print("forge check will run:")
    for s in steps:
        print(f"  - {s.name}" + (f"  (SKIPPED: {s.skip_reason})" if s.skip_reason else ""))
    if args.dry_run:
        return 0
    report = Report()
    for s in steps:
        res = run_step(s)
        report.results.append(res)
        print(f"[{res.status:7}] {res.name} ({res.seconds:.1f}s) {res.detail if res.status != 'PASS' else ''}")
        if res.status == "FAIL":
            break  # stop on the first failure
    out = ROOT / "artifacts" / "forge" / time.strftime("%Y%m%d-%H%M%S")
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps([r.__dict__ for r in report.results], indent=2), encoding="utf-8")
    ok = report.ok(args.strict)
    print("forge check:", "OK" if ok else "FAILED", f"(summary: {out / 'summary.json'})")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="forge", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="local pre-push gate")
    c.add_argument("--dry-run", action="store_true", help="print the steps only")
    c.add_argument("--strict", action="store_true", help="a SKIPPED step fails the gate")
    c.set_defaults(func=cmd_check)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
