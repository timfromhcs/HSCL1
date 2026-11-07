#!/usr/bin/env python3
"""forge - one control for the HSCL1 patch/build/test loop (standard library only). Spec: docs/superpowers/plans/2026-11-06-forge-loop.md

Implemented now:  check              local pre-push gate (tests, changed tests again under Linux in WSL, bash -n, ShellCheck in WSL, secret scan)
                  build              remaster the ISO inside the WSL source tree (clean tree required) and print its manifest
                  boot ISO           run the QEMU boot harness and summarise result.json
                  diff A B           compare two ISO manifests field by field
Planned:          test, install, cycle, release (see the plan; they are NOT implemented and not listed in --help)

Rules: print what will run first; stop on the first failure; a skipped step is reported as SKIPPED and makes `check --strict` fail;
write artifacts/forge/<run>/summary.json; --dry-run only prints the steps.
"""
from __future__ import annotations

import argparse
import json
import os
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


def changed_paths(root: Path = ROOT) -> list[str]:
    """Every file that differs from the upstream branch (or HEAD when there is none) plus untracked ones, sorted, repo-relative."""
    def git(*a: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", str(root), *a], capture_output=True, text=True, errors="replace")

    base = "@{u}" if git("rev-parse", "--abbrev-ref", "@{u}").returncode == 0 else "HEAD"
    names = set(git("diff", "--name-only", base).stdout.splitlines())
    names |= set(git("ls-files", "--others", "--exclude-standard").stdout.splitlines())
    return sorted(n for n in names if (root / n).is_file())


def changed_test_files(root: Path = ROOT) -> list[str]:
    """Test files that differ from the upstream branch (or HEAD when there is none) plus untracked ones, sorted, repo-relative."""
    return [n for n in changed_paths(root) if re.fullmatch(r"tests/.*test_[^/]*\.py", n)]


def posix(path: str | Path) -> str:
    """Path as the WSL bash sees it (/mnt/<drive>/...), leaving an already-POSIX path alone."""
    text = str(path)
    if text.startswith("/") or text.startswith("~"):
        return text
    p = Path(text).resolve()
    return "/mnt/" + p.drive[0].lower() + "/" + p.as_posix()[3:] if p.drive else p.as_posix()


def wsl_prefix() -> list[str]:
    """Command prefix for WSL steps; `FORGE_WSL` overrides it so tests can run a stand-in.

    Split with `posix=False` on purpose: a Windows override such as
    `C:\\Python313\\python.exe C:\\tmp\\fake_wsl.py` keeps its backslashes instead of losing them the
    way POSIX word splitting would.
    """
    raw = os.environ.get("FORGE_WSL")
    if not raw:
        return ["wsl", "-d", "Ubuntu", "--"]
    return [t.strip('"').strip("'") for t in shlex.split(raw, posix=False)]


def _no_shell_metacharacters(value: str, what: str) -> str:
    for bad in ("'", '"', "$", "`", ";"):
        if bad in value:
            raise SystemExit(f"forge: {what} must not contain quotes, $, ` or ; ({value!r})")
    return value


def plan_build(src: str, out: str, fast: bool = False, force: bool = True) -> list[Step]:
    """Three steps: is the tree clean, build it, show the manifest the build wrote.

    The clean-tree preflight is what keeps a release artifact tied to a commit: the remaster records
    `git_dirty`, and a dirty tree would silently produce an ISO nobody can rebuild from a tag.
    """
    src_q = _no_shell_metacharacters(src, "source directory")
    out_q = _no_shell_metacharacters(out, "output path")
    flags = " ".join(f for f, on in (("--fast", fast), ("--force", force)) if on)
    pre = Step("preflight (clean source tree)", [
        *wsl_prefix(), "bash", "-lc",
        'cd ' + src_q + ' && git rev-parse --short HEAD && test -z "$(git status --porcelain)"',
    ])
    remaster = Step("remaster", [
        *wsl_prefix(), "bash", "-lc",
        f"cd {src_q} && scripts/remaster-iso.sh --out {out_q} {flags}".strip(),
    ])
    # Quoted as one shell word, so the JSON path can never be split or interpreted by bash.
    probe = (
        "import json;m=json.load(open('" + out_q + ".manifest.json'));"
        "print('sha256', m['iso_sha256'], 'dirty', m['git_dirty'], 'version', m['version'])"
    )
    manifest = Step("manifest", [
        *wsl_prefix(), "bash", "-lc",
        "cd " + shlex.quote(src_q) + " && python3 -c " + shlex.quote(probe),
    ])
    return [pre, remaster, manifest]


def plan_boot(iso: str, out: str, harness: str | Path | None = None, firmware: str = "uefi",
              secure_boot: bool = False, live: bool = False) -> list[Step]:
    """`live` clicks through the live prompt and closes the Welcome window, so the evidence ends on
    the desktop instead of the boot menu (the harness options `--try-live --dismiss-welcome`)."""
    harness = harness or (ROOT / "scripts" / "qemu_boot_test.py")
    argv = [sys.executable, str(harness), str(iso), str(out), "--firmware", firmware]
    if secure_boot:
        argv.append("--secure-boot")
    if live:
        argv += ["--try-live", "--dismiss-welcome"]
    return [Step("boot", argv)]


def manifest_for(path: str | Path) -> Path:
    """`X.iso` -> `X.iso.manifest.json`; anything else is taken as a manifest path itself."""
    p = Path(path)
    if p.suffix.lower() == ".iso":
        return p.with_name(p.name + ".manifest.json")
    return p


DIFF_FIELDS = ("version", "git_commit", "git_dirty", "qa_image", "base_iso_sha256", "iso_bytes",
               "iso_sha256", "workshop_default")


def iso_diff(a: Path, b: Path) -> list[tuple[str, object, object]]:
    """Field-by-field difference of two build manifests (the fields a reviewer actually checks)."""
    da = json.loads(a.read_text(encoding="utf-8"))
    db = json.loads(b.read_text(encoding="utf-8"))
    keys = [k for k in DIFF_FIELDS if k in da or k in db]
    keys += sorted((set(da) | set(db)) - set(keys) - {"product", "artifact", "base", "built_utc"})
    return [(k, da.get(k), db.get(k)) for k in keys if da.get(k) != db.get(k)]


def plan_check(root: Path = ROOT, have_wsl: bool | None = None, changed: list[str] | None = None, full: bool = False) -> list[Step]:
    have_wsl = wsl_available() if have_wsl is None else have_wsl
    if changed is None:
        paths = changed_paths(root)
        changed = [n for n in paths if re.fullmatch(r"tests/.*test_[^/]*\.py", n)]
    else:
        paths = list(changed)
    app_changed = any(p.startswith("apps/hcseasymath/") for p in paths)
    pytest_argv = [sys.executable, "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider"]
    if not full:
        pytest_argv += ["-m", "not slow"]  # the slow tier runs with --full and in CI
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
    # HCSEASYMATH needs Python 3.14 (the OS interpreter), so its gate runs under WSL Ubuntu from a hash-locked venv.
    # Omitted entirely when the app is untouched: a SKIPPED step would fail `check --strict` for unrelated work.
    if app_changed:
        name = "hcseasymath (WSL)"
        if not have_wsl:
            steps.append(Step(name, None, skip_reason="WSL Ubuntu not available"))
        else:
            steps.append(Step(name, ["wsl", "-d", "Ubuntu", "--", "bash", "-lc",
                                     f"cd {shlex.quote(posix)} && bash scripts/hcseasymath_gate.sh"]))
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
    steps = plan_check(full=args.full)
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


def cmd_build(args: argparse.Namespace) -> int:
    steps = plan_build(args.src, args.out, args.fast, args.force)
    print("forge build will run:")
    for st in steps:
        print(f"  - {st.name}: {' '.join(st.argv)}")
    if args.dry_run:
        print("dry run: nothing executed")
        return 0
    for st in steps:
        res = run_step(st)
        print(f"[{res.status:7}] {st.name} ({res.seconds:.1f}s) {res.detail if res.status != 'PASS' else ''}")
        if res.status != "PASS":
            print("forge build: FAILED")
            return 1
    print("forge build: OK")
    return 0


def cmd_boot(args: argparse.Namespace) -> int:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for st in plan_boot(args.iso, args.out, args.harness, args.firmware, args.secure_boot, args.live):
        res = run_step(st)
        print(f"[{res.status:7}] {st.name} ({res.seconds:.1f}s) {res.detail if res.status != 'PASS' else ''}")
    result_path = out / "result.json"
    if not result_path.is_file():
        print(f"forge boot: no result.json in {out} - the harness did not get far enough")
        return 1
    # The harness writes `reached_desktop`, `elapsed_s` and `shots` (scripts/qemu_boot_test.py).
    # The first version of this function guessed other key names and called a booted guest "not booted".
    result = json.loads(result_path.read_text(encoding="utf-8"))
    shots = result.get("shots") or []
    booted = bool(result.get("reached_desktop"))
    match = result.get("desktop_final_wallpaper_match")
    print(f"booted: {'yes' if booted else 'not booted'}; {result.get('elapsed_s', '?')} s; "
          f"{len(shots)} screenshot(s); firmware {result.get('firmware', args.firmware)}"
          + (f"; final wallpaper match {match}" if match is not None else ""))
    print(f"evidence: {result_path}")
    return 0 if booted else 1


def cmd_diff(args: argparse.Namespace) -> int:
    a, b = manifest_for(args.a), manifest_for(args.b)
    for p in (a, b):
        if not p.is_file():
            print(f"forge diff: manifest not found: {p}")
            return 2
    diffs = iso_diff(a, b)
    if args.json:
        print(json.dumps([{"field": k, "a": x, "b": y} for k, x, y in diffs], indent=2))
        return 0
    if not diffs:
        print("no differences in the compared fields")
        return 0
    print(f"differences between {a.name} and {b.name}:")
    for key, x, y in diffs:
        print(f"  {key}: {x!r} -> {y!r}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="forge", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="remaster the ISO in the WSL source tree")
    b.add_argument("--src", default="~/hscl1-src", help="WSL checkout to build from (must be clean)")
    b.add_argument("--out", default="~/hscl1-build/out/HSCL1-dev-amd64.iso", help="ISO path inside WSL")
    b.add_argument("--fast", action="store_true", help="pass --fast to the remaster (lower compression)")
    b.add_argument("--no-force", dest="force", action="store_false", help="refuse to overwrite an existing ISO")
    b.add_argument("--dry-run", action="store_true", help="print the steps only")
    b.set_defaults(func=cmd_build)
    bo = sub.add_parser("boot", help="run the QEMU boot harness on an ISO")
    bo.add_argument("iso")
    bo.add_argument("--out", required=True, help="evidence directory")
    bo.add_argument("--harness", help="boot harness (default scripts/qemu_boot_test.py)")
    bo.add_argument("--firmware", choices=["uefi", "bios"], default="uefi")
    bo.add_argument("--secure-boot", action="store_true")
    bo.add_argument("--live", action="store_true", help="click through the live prompt and close the Welcome window")
    bo.set_defaults(func=cmd_boot)
    d = sub.add_parser("diff", help="compare two build manifests (or ISOs with a .manifest.json)")
    d.add_argument("a")
    d.add_argument("b")
    d.add_argument("--json", action="store_true")
    d.set_defaults(func=cmd_diff)
    c = sub.add_parser("check", help="local pre-push gate")
    c.add_argument("--dry-run", action="store_true", help="print the steps only")
    c.add_argument("--full", action="store_true", help="also run the tests marked slow (CI always does)")
    c.add_argument("--strict", action="store_true", help="a SKIPPED step fails the gate")
    c.set_defaults(func=cmd_check)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
