"""forge check: step plan, secret scanner, bash -n gate (with a deliberately broken script), strict handling of skipped steps."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import forge  # noqa: E402


def test_plan_has_the_expected_steps_and_skips_shellcheck_without_wsl():
    steps = forge.plan_check(ROOT, have_wsl=False, changed=["tests/unit/test_x.py"])
    names = [s.name for s in steps]
    assert names == ["pytest", "pytest (WSL, changed tests)", "bash -n", "shellcheck (WSL)", "secret scan"]
    assert steps[1].argv is None and "WSL" in steps[1].skip_reason
    sc = steps[3]
    assert sc.argv is None and "WSL" in sc.skip_reason


def test_changed_tests_step_runs_the_changed_files_under_linux():
    """Four CI-only failures on 2026-11-06 (exec bit x3, a Windows-only path normalization) came from tests that only ran on Windows."""
    steps = forge.plan_check(ROOT, have_wsl=True, changed=["tests/unit/test_a.py", "tests/unit/test b.py"])
    st = next(s for s in steps if s.name == "pytest (WSL, changed tests)")
    cmd = st.argv[-1]
    assert st.argv[:4] == ["wsl", "-d", "Ubuntu", "--"] and "python3 -m pytest" in cmd
    assert "tests/unit/test_a.py" in cmd and "'tests/unit/test b.py'" in cmd


def test_changed_tests_step_is_skipped_when_no_test_file_changed():
    st = next(s for s in forge.plan_check(ROOT, have_wsl=True, changed=[]) if s.name == "pytest (WSL, changed tests)")
    assert st.argv is None and "no changed test files" in st.skip_reason


def test_changed_test_files_finds_modified_and_untracked_tests_only(tmp_path):
    def git(*a):
        subprocess.run(["git", *a], cwd=tmp_path, check=True, capture_output=True)

    git("init", "-q")
    git("config", "user.email", "t@example.invalid")
    git("config", "user.name", "t")
    (tmp_path / "tests" / "unit").mkdir(parents=True)
    (tmp_path / "tests" / "unit" / "test_a.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "tests" / "unit" / "test_b.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "tests" / "conftest.py").write_text("x = 1\n", encoding="utf-8")
    git("add", "-A")
    git("commit", "-qm", "init")
    (tmp_path / "tests" / "unit" / "test_a.py").write_text("x = 2\n", encoding="utf-8")  # modified
    (tmp_path / "tests" / "unit" / "test_new.py").write_text("x = 1\n", encoding="utf-8")  # untracked
    (tmp_path / "tests" / "conftest.py").write_text("x = 2\n", encoding="utf-8")  # changed but not a test file
    (tmp_path / "notes.txt").write_text("n\n", encoding="utf-8")
    assert forge.changed_test_files(tmp_path) == ["tests/unit/test_a.py", "tests/unit/test_new.py"]


def test_plan_with_wsl_builds_a_shellcheck_command_for_the_known_scripts():
    steps = forge.plan_check(ROOT, have_wsl=True)
    sc = next(s for s in steps if s.name.startswith("shellcheck"))
    cmd = sc.argv[-1]
    assert "shellcheck -S warning" in cmd and "scripts/remaster-iso.sh" in cmd and "distro/live/verify-image.sh" in cmd


def test_skipped_step_fails_only_in_strict_mode():
    rep = forge.Report([forge.Result("a", "PASS"), forge.Result("b", "SKIPPED", detail="x")])
    assert rep.ok(strict=False) is True
    assert rep.ok(strict=True) is False
    assert forge.Report([forge.Result("a", "FAIL")]).ok(strict=False) is False


def test_secret_patterns_detect_real_looking_secrets_and_ignore_prose():
    token = "gh" + "p_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"   # assembled so this file itself is not a hit
    assert "GitHub token" in forge.scan_text_for_secrets(f"export X={token}")
    key = "-----BEGIN " + "OPENSSH PRIVATE KEY-----"
    assert "private key block" in forge.scan_text_for_secrets(key)
    assert forge.scan_text_for_secrets("password = 'hunter2'") == []          # too short to be a real secret
    assert forge.scan_text_for_secrets("the token budget is large") == []


def test_repo_itself_has_no_secret_hits():
    assert forge.scan_repo_for_secrets(ROOT) == []


def make_tree(tmp_path, body):
    tmp_path.mkdir()
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "t.sh").write_bytes(body)
    return tmp_path


def test_bash_gate_passes_a_valid_script(tmp_path):
    good = make_tree(tmp_path / "good", b"#!/bin/bash\necho ok\n")
    assert forge.run_step(forge.Step("bash -n"), good).status == "PASS"


def test_bash_gate_fails_a_broken_script(tmp_path):
    # mutation check: the gate must go red on a script with a missing fi
    bad = make_tree(tmp_path / "bad", b"#!/bin/bash\nif true; then\n  echo unclosed\n")
    res = forge.run_step(forge.Step("bash -n"), bad)
    assert res.status == "FAIL" and "t.sh" in res.detail


def test_dry_run_prints_steps_and_exits_zero():
    r = subprocess.run([sys.executable, str(ROOT / "scripts/forge.py"), "check", "--dry-run"], capture_output=True, text=True)
    assert r.returncode == 0
    assert "pytest" in r.stdout and "secret scan" in r.stdout


def test_help_lists_only_implemented_commands():
    r = subprocess.run([sys.executable, str(ROOT / "scripts/forge.py"), "--help"], capture_output=True, text=True)
    assert "check" in r.stdout
    for planned in ("build", "release", "cycle"):
        assert planned not in r.stdout.split("positional arguments:")[-1], planned
