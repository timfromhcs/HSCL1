"""tools/hcs_hold.py: host hold flag shared by the gateway, autostart.ps1 and the local delegate."""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools" / "hcs_hold.py"


def run(args, hold_file, **kw):
    env = {**os.environ, "HCS_HOLD_FILE": str(hold_file)}
    return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True, env=env, **kw)


def test_set_status_clear(tmp_path):
    f = tmp_path / "hold.json"
    assert run(["status"], f).stdout.strip() == "no hold"
    r = run(["set", "lora training", "--pid", str(os.getpid())], f)
    assert r.returncode == 0 and "lora training" in r.stdout
    st = json.loads(run(["status"], f).stdout)
    assert st["reason"] == "lora training" and st["pid"] == os.getpid()
    assert run(["clear"], f).stdout.strip() == "cleared"
    assert run(["status"], f).stdout.strip() == "no hold"


def test_a_dead_owner_is_not_a_hold(tmp_path):
    f = tmp_path / "hold.json"
    f.write_text(json.dumps({"reason": "x", "pid": 2**22 + 99}), encoding="utf-8")
    assert run(["status"], f).stdout.strip() == "no hold"


def test_run_holds_exactly_while_the_command_runs_and_passes_its_exit_code(tmp_path):
    f = tmp_path / "hold.json"
    probe = f"import json,sys; d=json.load(open(r'{f}')); sys.exit(7 if d['reason']=='build' else 1)"
    r = run(["run", "build", "--", sys.executable, "-c", probe], f)
    assert r.returncode == 7  # the child saw the hold file while it ran
    assert not f.exists()  # and it is gone afterwards


def test_run_refuses_when_the_host_is_already_on_hold(tmp_path):
    f = tmp_path / "hold.json"
    f.write_text(json.dumps({"reason": "vm", "pid": os.getpid()}), encoding="utf-8")
    r = run(["run", "build", "--", sys.executable, "-c", "pass"], f)
    assert r.returncode == 3 and "already on hold" in r.stderr
    assert f.exists()  # the other holder's flag is untouched
