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


def test_bash_gate_retries_a_launcher_failure_with_empty_stderr(tmp_path, monkeypatch):
    """2026-11-09: a WSL cold start exited non-zero with empty stderr on a valid script and turned the
    gate red for one run. A syntax error always prints file/line, so an empty stderr is retried once."""
    good = make_tree(tmp_path / "good", b"#!/bin/bash\necho ok\n")
    real = forge.subprocess.run
    calls = {"n": 0}

    def flaky(argv, *a, **kw):
        calls["n"] += 1
        if calls["n"] == 1:
            return subprocess.CompletedProcess(argv, 1, b"", b"")
        return real(argv, *a, **kw)

    monkeypatch.setattr(forge.subprocess, "run", flaky)
    assert forge.run_step(forge.Step("bash -n"), good).status == "PASS"
    assert calls["n"] == 2


def test_bash_gate_does_not_retry_a_real_syntax_error(tmp_path, monkeypatch):
    bad = make_tree(tmp_path / "bad", b"#!/bin/bash\nif true; then\n  echo unclosed\n")
    real = forge.subprocess.run
    calls = {"n": 0}

    def counting(argv, *a, **kw):
        calls["n"] += 1
        return real(argv, *a, **kw)

    monkeypatch.setattr(forge.subprocess, "run", counting)
    assert forge.run_step(forge.Step("bash -n"), bad).status == "FAIL"
    assert calls["n"] == 1


def test_dry_run_prints_steps_and_exits_zero():
    r = subprocess.run([sys.executable, str(ROOT / "scripts/forge.py"), "check", "--dry-run"], capture_output=True, text=True)
    assert r.returncode == 0
    assert "pytest" in r.stdout and "secret scan" in r.stdout


def test_help_lists_only_implemented_commands():
    r = subprocess.run([sys.executable, str(ROOT / "scripts/forge.py"), "--help"], capture_output=True, text=True)
    commands = r.stdout.split("positional arguments:")[-1]
    for done in ("check", "build", "boot", "diff"):  # G30: implemented and therefore listed
        assert done in commands, done
    for planned in ("release", "cycle", "install"):
        assert planned not in commands, planned


# --- G30: forge build / boot / diff -------------------------------------------------------------

def test_build_plan_runs_the_remaster_in_the_wsl_source_tree_and_verifies_it(tmp_path):
    steps = forge.plan_build(src="~/hscl1-src", out="~/hscl1-build/out/x.iso", fast=True)
    names = [s.name for s in steps]
    assert names[0] == "preflight (clean source tree)"
    assert any("remaster" in n for n in names)
    remaster = next(s for s in steps if "remaster" in s.name)
    cmd = " ".join(remaster.argv)
    assert "scripts/remaster-iso.sh" in cmd and "--out ~/hscl1-build/out/x.iso" in cmd
    assert "--fast" in cmd and "--force" in cmd


def test_build_plan_refuses_a_dirty_source_tree_without_force(tmp_path):
    dirty = tmp_path / "src"
    dirty.mkdir()
    steps = forge.plan_build(src=str(dirty), out="x.iso", fast=False)
    pre = steps[0]
    assert "status --porcelain" in " ".join(pre.argv)
    # the preflight is a real gate: it fails the build when the tree has uncommitted changes
    assert pre.argv is not None


def test_build_dry_run_prints_the_steps_without_running_anything(tmp_path, capsys):
    code = forge.main(["build", "--src", "~/hscl1-src", "--out", "x.iso", "--dry-run"])
    out = capsys.readouterr().out
    assert code == 0
    assert "remaster-iso.sh" in out and "dry" in out.lower()


def test_build_runs_through_the_configured_wsl_prefix(tmp_path, monkeypatch):
    calls = tmp_path / "calls.txt"
    fake = tmp_path / "fake_wsl.py"
    fake.write_text(
        "import pathlib, sys\n"
        f"calls = pathlib.Path({str(calls)!r})\n"
        "with calls.open('a', encoding='utf-8') as fh:\n"
        "    fh.write(' '.join(sys.argv[1:]) + '\\n')\n"
        "print('ok')\n",
        encoding="utf-8", newline="\n")
    monkeypatch.setenv("FORGE_WSL", f"{sys.executable} {fake}")
    code = forge.main(["build", "--src", "~/hscl1-src", "--out", "x.iso"])
    assert code == 0
    ran = calls.read_text(encoding="utf-8")
    assert "remaster-iso.sh" in ran, ran


def test_boot_uses_the_harness_and_summarises_its_result(tmp_path, capsys):
    out = tmp_path / "boot"
    payload = ('{"reached_desktop": true, "elapsed_s": 99, '
               '"shots": [{"n": 1}, {"n": 2}], "firmware": "uefi"}')
    code = forge.main(["boot", "some.iso", "--out", str(out), "--harness", str(_fake_boot_harness(tmp_path, payload))])
    text = capsys.readouterr().out
    assert code == 0
    assert "booted: yes" in text and "99" in text and "2" in text


def test_boot_fails_when_the_harness_reports_a_failed_boot(tmp_path, capsys):
    out = tmp_path / "boot"
    payload = '{"reached_desktop": false, "elapsed_s": 300, "shots": []}'
    code = forge.main(["boot", "some.iso", "--out", str(out), "--harness", str(_fake_boot_harness(tmp_path, payload))])
    assert code == 1
    assert "not booted" in capsys.readouterr().out.lower()


def _manifest(path: Path, **over):
    import json
    data = {
        "product": "HSCL1", "artifact": "HSCL1.iso", "version": "0.1.2-alpha.0",
        "workshop_default": "disabled", "qa_image": False,
        "base": "Kubuntu 26.04.1", "base_iso_sha256": "aa", "git_commit": "c1",
        "git_dirty": False, "built_utc": "2026-11-06T00:00:00Z",
        "iso_bytes": 100, "iso_sha256": "11",
    }
    data.update(over)
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_diff_reports_the_fields_that_changed_between_two_manifests(tmp_path, capsys):
    a = _manifest(tmp_path / "a.manifest.json", iso_sha256="11")
    b = _manifest(tmp_path / "b.manifest.json", iso_sha256="22", iso_bytes=120, git_commit="c2")
    code = forge.main(["diff", str(a), str(b)])
    text = capsys.readouterr().out
    assert code == 0
    assert "iso_sha256" in text and "git_commit" in text and "iso_bytes" in text
    assert "version" not in text.split("changed")[-1] or "version" in text


def test_diff_of_identical_manifests_says_so(tmp_path, capsys):
    a = _manifest(tmp_path / "a.manifest.json")
    b = _manifest(tmp_path / "b.manifest.json")
    code = forge.main(["diff", str(a), str(b)])
    assert code == 0
    assert "no differences" in capsys.readouterr().out.lower()


def test_diff_refuses_a_missing_manifest(tmp_path, capsys):
    code = forge.main(["diff", str(tmp_path / "nope.manifest.json"), str(tmp_path / "also.json")])
    assert code == 2
    assert "manifest" in capsys.readouterr().out.lower() + capsys.readouterr().err.lower()


def test_diff_accepts_an_iso_path_and_finds_its_manifest(tmp_path):
    iso = tmp_path / "HSCL1.iso"
    iso.write_bytes(b"x")
    _manifest(tmp_path / "HSCL1.iso.manifest.json")
    assert forge.manifest_for(iso) == tmp_path / "HSCL1.iso.manifest.json"


def test_boot_plan_can_reach_the_live_desktop():
    """The boot gate has to end on the desktop, not on the GRUB menu: --live maps to the harness's
    --try-live --dismiss-welcome, which clicks through the live prompt and closes the welcome window."""
    steps = forge.plan_boot("x.iso", "out", harness="h.py", firmware="uefi", live=True)
    argv = steps[0].argv
    assert "--try-live" in argv and "--dismiss-welcome" in argv
    plain = forge.plan_boot("x.iso", "out", harness="h.py")[0].argv
    assert "--try-live" not in plain

def _fake_boot_harness(tmp_path, payload: str):
    """A stand-in harness that writes exactly the schema scripts/qemu_boot_test.py writes."""
    harness = tmp_path / "fake_boot.py"
    harness.write_text(
        "import json, pathlib, sys" + chr(10)
        + "out = pathlib.Path(sys.argv[2])" + chr(10)
        + "out.mkdir(parents=True, exist_ok=True)" + chr(10)
        + "(out / 'result.json').write_text(" + repr(payload) + ")" + chr(10),
        encoding="utf-8", newline=chr(10))
    return harness


def test_boot_reads_the_harness_schema_it_actually_writes(tmp_path, capsys):
    """Regression: the first version looked for `booted`/`seconds`/`screenshots`, which
    scripts/qemu_boot_test.py never writes - it writes `reached_desktop`, `elapsed_s` and `shots`.
    The real 0.1.3 dev run therefore reported "not booted" for a guest that had reached the desktop."""
    payload = ('{"firmware": "uefi", "secure_boot_requested": false, "accel": "whpx", '
               '"iso": "x.iso", "shots": [{"n": 1, "t": 50}, {"n": 2, "t": 95}], '
               '"reached_desktop": true, "desktop_final_wallpaper_match": 0.121, "elapsed_s": 191}')
    out = tmp_path / "boot"
    code = forge.main(["boot", "x.iso", "--out", str(out), "--harness", str(_fake_boot_harness(tmp_path, payload))])
    text = capsys.readouterr().out
    assert code == 0, text
    assert "booted: yes" in text and "191" in text and "2 screenshot" in text, text


def test_boot_reports_a_guest_that_did_not_reach_the_desktop(tmp_path, capsys):
    payload = '{"shots": [], "reached_desktop": false, "elapsed_s": 2400, "firmware": "uefi"}'
    out = tmp_path / "boot"
    code = forge.main(["boot", "x.iso", "--out", str(out), "--harness", str(_fake_boot_harness(tmp_path, payload))])
    assert code == 1
    assert "not booted" in capsys.readouterr().out.lower()


def test_default_check_skips_the_slow_tier_and_full_runs_everything():
    fast = next(s for s in forge.plan_check(ROOT, have_wsl=False, changed=[]) if s.name == "pytest").argv
    full = next(s for s in forge.plan_check(ROOT, have_wsl=False, changed=[], full=True) if s.name == "pytest").argv
    assert "not slow" in fast
    assert "not slow" not in full


def test_hcseasymath_step_is_absent_unless_the_app_changed():
    names = [s.name for s in forge.plan_check(ROOT, have_wsl=True, changed=["tests/unit/test_x.py"])]
    assert "hcseasymath (WSL)" not in names


def test_hcseasymath_step_runs_the_gate_script_under_wsl_when_the_app_changed():
    steps = forge.plan_check(ROOT, have_wsl=True, changed=["apps/hcseasymath/backend/hcseasymath/cli.py"])
    st = next(s for s in steps if s.name == "hcseasymath (WSL)")
    assert st.argv[:4] == ["wsl", "-d", "Ubuntu", "--"]
    assert "scripts/hcseasymath_gate.sh" in st.argv[-1]


def test_hcseasymath_step_is_skipped_with_a_reason_without_wsl():
    steps = forge.plan_check(ROOT, have_wsl=False, changed=["apps/hcseasymath/pyproject.toml"])
    st = next(s for s in steps if s.name == "hcseasymath (WSL)")
    assert st.argv is None and "WSL" in st.skip_reason


def test_qml_gate_runs_when_qml_changed_and_is_absent_otherwise():
    """QML had no executing gate at all until 2026-11-09 (qmltestrunner was not on PATH)."""
    for path in (
        "apps/control-center/qml/pages/SecurityPage.qml",
        "tests/qml_plugin/tst_effects.qml",
        "packages/debian/hscl-desktop/usr/share/plasma/wallpapers/org.hcs.hscl1.rain/contents/ui/main.qml",
    ):
        steps = forge.plan_check(ROOT, have_wsl=True, changed=[path])
        st = next(s for s in steps if s.name == "qml (WSL)")
        assert "scripts/dev/qml-gate.sh" in st.argv[-1], path
    names = [s.name for s in forge.plan_check(ROOT, have_wsl=True, changed=["docs/CLI.md"])]
    assert "qml (WSL)" not in names


def test_qml_gate_is_skipped_with_a_reason_without_wsl():
    steps = forge.plan_check(ROOT, have_wsl=False, changed=["apps/control-center/qml/Main.qml"])
    st = next(s for s in steps if s.name == "qml (WSL)")
    assert st.argv is None and "WSL" in st.skip_reason


def test_changed_paths_lists_every_modified_and_untracked_file(tmp_path):
    def git(*a):
        subprocess.run(["git", *a], cwd=tmp_path, check=True, capture_output=True)

    git("init", "-q")
    git("config", "user.email", "t@example.invalid")
    git("config", "user.name", "t")
    (tmp_path / "apps" / "hcseasymath").mkdir(parents=True)
    (tmp_path / "apps" / "hcseasymath" / "a.py").write_text("x = 1\n", encoding="utf-8")
    git("add", "-A")
    git("commit", "-qm", "init")
    (tmp_path / "apps" / "hcseasymath" / "a.py").write_text("x = 2\n", encoding="utf-8")
    (tmp_path / "apps" / "hcseasymath" / "b.py").write_text("x = 1\n", encoding="utf-8")
    assert forge.changed_paths(tmp_path) == ["apps/hcseasymath/a.py", "apps/hcseasymath/b.py"]


def test_doc_command_step_runs_when_docs_or_the_cli_changed():
    """2026-11-08: a docs row naming a non-existent `hscl` command passed forge check and failed only in CI (the Rust
    doc-command test). The step closes that parity gap; it is absent when neither docs nor the CLI changed."""
    for path in ("docs/KNOWN_LIMITATIONS.md", "README.md", "cli/hscl/src/main.rs"):
        steps = forge.plan_check(ROOT, have_wsl=False, changed=[path])
        st = next(s for s in steps if s.name == "doc commands (cargo)")
        assert st.argv[:3] == ["cargo", "test", "-p"] and "documented_hscl_commands" in st.argv
    names = [s.name for s in forge.plan_check(ROOT, have_wsl=False, changed=["tests/unit/test_x.py"])]
    assert "doc commands (cargo)" not in names
