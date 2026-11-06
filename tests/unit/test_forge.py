"""forge check: step plan, secret scanner, bash -n gate (with a deliberately broken script), strict handling of skipped steps."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import forge  # noqa: E402


def test_plan_has_the_expected_steps_and_skips_shellcheck_without_wsl():
    steps = forge.plan_check(ROOT, have_wsl=False)
    names = [s.name for s in steps]
    assert names == ["pytest", "bash -n", "shellcheck (WSL)", "secret scan"]
    sc = steps[2]
    assert sc.argv is None and "WSL" in sc.skip_reason


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
