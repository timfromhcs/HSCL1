"""RSI guard: patterns, branch rule, human override, and a real git round trip (an agent branch touching a test must fail)."""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import protected_paths as pp  # noqa: E402

CFG = pp.load_config()


def test_config_protects_the_judges():
    hits = pp.protected_hits(
        ["tests/unit/test_x.py", ".github/workflows/ci.yml", "distro/live/verify-image.sh", "scripts/forge.py", "docs/CLAIMS.md", "README.md", "cli/hscl/src/main.rs"],
        CFG["protected"])
    assert hits == [".github/workflows/ci.yml", "distro/live/verify-image.sh", "docs/CLAIMS.md", "scripts/forge.py", "tests/unit/test_x.py"]


def test_the_guard_protects_itself():
    assert pp.protected_hits(["scripts/protected_paths.py", "scripts/protected_paths.json"], CFG["protected"]) == [
        "scripts/protected_paths.json", "scripts/protected_paths.py"]


def test_pattern_semantics():
    rx = pp.compile_pattern("tests/**")
    assert rx.match("tests/a.py") and rx.match("tests/unit/deep/b.py") and not rx.match("tests")
    assert not pp.compile_pattern("tests/*").match("tests/unit/b.py")      # one segment only
    assert pp.compile_pattern("**/x.sh").match("x.sh") and pp.compile_pattern("**/x.sh").match("a/b/x.sh")
    assert not pp.compile_pattern("a.b").match("axb")                       # dots are literal


def test_branch_rule():
    assert pp.guarded_branch("rsi/variant-3", CFG["branch_prefixes"])
    assert pp.guarded_branch("agent/fix", CFG["branch_prefixes"])
    assert not pp.guarded_branch("codex/hscl1-v1", CFG["branch_prefixes"])


def run_git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def make_repo(tmp_path, branch, files):
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    (repo / "scripts" / "protected_paths.json").write_text((ROOT / "scripts/protected_paths.json").read_text(encoding="utf-8"), encoding="utf-8")
    (repo / "tests").mkdir()
    (repo / "tests" / "t.py").write_text("assert True\n", encoding="utf-8")
    (repo / "src.txt").write_text("a\n", encoding="utf-8")
    run_git(repo, "init", "-q", "-b", "main")
    run_git(repo, "config", "user.email", "t@example.invalid")
    run_git(repo, "config", "user.name", "t")
    run_git(repo, "add", "-A")
    run_git(repo, "commit", "-q", "-m", "base")
    run_git(repo, "checkout", "-q", "-b", branch)
    for rel, text in files.items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    run_git(repo, "add", "-A")
    run_git(repo, "commit", "-q", "-m", "change")
    return repo


def run_tool(repo, *extra, env=None):
    e = dict(os.environ)
    e.pop("HSCL_PROTECTED_OK", None)
    e.update(env or {})
    return subprocess.run([sys.executable, str(ROOT / "scripts/protected_paths.py"), "--repo", str(repo), "--base", "main", "--head", "HEAD", *extra],
                          capture_output=True, text=True, env=e)


def test_agent_branch_changing_a_test_fails(tmp_path):
    repo = make_repo(tmp_path, "rsi/v1", {"tests/t.py": "assert False  # weakened\n"})
    r = run_tool(repo)
    assert r.returncode == 1 and "tests/t.py" in r.stdout


def test_agent_branch_changing_only_source_passes(tmp_path):
    repo = make_repo(tmp_path, "rsi/v2", {"src.txt": "b\n"})
    assert run_tool(repo).returncode == 0


def test_human_override_allows_the_change(tmp_path):
    repo = make_repo(tmp_path, "rsi/v3", {"tests/t.py": "assert 1 == 1\n"})
    assert run_tool(repo, env={"HSCL_PROTECTED_OK": "1"}).returncode == 0


def test_normal_branch_reports_but_does_not_fail(tmp_path):
    repo = make_repo(tmp_path, "codex/feature", {"tests/t.py": "assert 2 == 2\n"})
    r = run_tool(repo, "--json")
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["guarded"] is False and data["protected_files_changed"] == ["tests/t.py"]


def test_unknown_base_is_a_usage_error(tmp_path):
    repo = make_repo(tmp_path, "rsi/v4", {"src.txt": "c\n"})
    r = subprocess.run([sys.executable, str(ROOT / "scripts/protected_paths.py"), "--repo", str(repo), "--base", "no-such-ref"], capture_output=True, text=True)
    assert r.returncode == 2


def test_ci_wires_the_guard_without_script_injection():
    import yaml
    wf = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
    steps = wf["jobs"]["python-and-shell"]["steps"]
    guard = next(s for s in steps if "RSI guard" in s.get("name", ""))
    assert "scripts/protected_paths.py" in guard["run"]
    assert "github.head_ref" not in guard["run"] and "github.base_ref" not in guard["run"]   # attacker-controlled names only via env
    assert guard["env"]["HEAD_REF"] == "${{ github.head_ref }}"
    assert "startsWith(github.head_ref, 'rsi/')" in guard["if"]
    checkout = steps[0]
    assert checkout["with"]["fetch-depth"] == 0                                           # merge-base needs history
