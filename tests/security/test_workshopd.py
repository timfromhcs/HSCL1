"""hscl-workshopd: closed operation set, path allow-list, symlink/traversal rejection, safe error handling."""
import base64
import importlib.util
import io
import json
import os
import stat
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "packages/debian/hscl-workshop/usr/lib/hscl/workshop/hscl_workshopd.py"
spec = importlib.util.spec_from_file_location("hscl_workshopd", SRC)
wd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wd)


def b64(b: bytes) -> str:
    return base64.b64encode(b).decode()


def call(op, args=None, ops=None, rid=1):
    return wd.handle(json.dumps({"id": rid, "op": op, "args": args or {}}), ops)


def test_unknown_and_malformed_requests_are_errors_not_crashes():
    assert call("rm_rf")["ok"] is False
    assert wd.handle("not json")["ok"] is False
    assert wd.handle("[1,2]")["ok"] is False
    assert wd.handle(json.dumps({"op": "status", "args": "x"}))["ok"] is False
    assert wd.handle("x" * (wd.MAX_LINE_BYTES + 1))["error"] == "request too large"


def test_there_is_no_generic_command_operation():
    forbidden = {"exec", "shell", "run", "cmd", "command", "system", "sh", "bash", "eval"}
    assert not forbidden & set(wd.OPS)
    assert set(wd.OPS) == {"status", "doctor", "report", "screenshot", "put_file", "run_hook", "restart_shell", "respin"}


@pytest.mark.parametrize("bad", [
    "relative/path", "/etc/passwd", "/usr/share/hscl/../../etc/passwd", "/usr//share/hscl/x", "/usr/share/hscl/\x00x",
    "/usr/share/wallpapers/Kubuntu/x", "/etc/shadow", "/root/.ssh/authorized_keys", "/usr/bin/bash", "/usr/bin/hscl-evil", "/usr/lib/systemd/system/x.service", "/usr/lib/hscl/../x",
])
def test_paths_outside_the_allow_list_are_rejected(bad, tmp_path):
    with pytest.raises(wd.OpError):
        wd.validate_put_path(bad, str(tmp_path))


def test_allowed_put_file_writes_atomically_with_requested_mode(tmp_path):
    r = wd.op_put_file({"path": "/usr/share/hscl/brand/x.svg", "content_b64": b64(b"<svg/>"), "mode": "0644"}, str(tmp_path))
    f = tmp_path / "usr/share/hscl/brand/x.svg"
    assert f.read_bytes() == b"<svg/>" and r["bytes"] == 6
    assert not list(tmp_path.rglob("*.hscl-tmp"))
    if os.name == "posix":
        assert stat.S_IMODE(f.stat().st_mode) == 0o644


def test_bad_mode_base64_and_size_are_rejected(tmp_path):
    base = {"path": "/usr/share/hscl/a", "content_b64": b64(b"x")}
    with pytest.raises(wd.OpError):
        wd.op_put_file({**base, "mode": "4755"}, str(tmp_path))
    with pytest.raises(wd.OpError):
        wd.op_put_file({**base, "content_b64": "!!!not-base64"}, str(tmp_path))
    with pytest.raises(wd.OpError):
        wd.op_put_file({**base, "content_b64": b64(b"x" * (wd.MAX_FILE_BYTES + 1))}, str(tmp_path))


@pytest.mark.skipif(os.name != "posix", reason="symlinks need POSIX")
def test_symlink_components_are_rejected(tmp_path):
    (tmp_path / "usr/share").mkdir(parents=True)
    (tmp_path / "outside").mkdir()
    (tmp_path / "usr/share/hscl").symlink_to(tmp_path / "outside")
    with pytest.raises(wd.OpError, match="symlink"):
        wd.op_put_file({"path": "/usr/share/hscl/evil", "content_b64": b64(b"x")}, str(tmp_path))
    assert not (tmp_path / "outside/evil").exists()


@pytest.mark.parametrize("name", ["../x", "a b", "a;b", "UPPER", "", "-x", "x" * 60, "a/b"])
def test_hook_names_are_validated(name):
    with pytest.raises(wd.OpError):
        wd.op_run_hook({"name": name}, "/nonexistent")


@pytest.mark.skipif(os.name != "posix", reason="needs /bin/sh")
def test_hook_runs_only_regular_files_from_the_hooks_dir(tmp_path):
    (tmp_path / "ok.sh").write_text("echo hello; exit 3\n")
    r = wd.op_run_hook({"name": "ok.sh"}, str(tmp_path))
    assert r["exit"] == 3 and "hello" in r["stdout"]
    (tmp_path / "link").symlink_to(tmp_path / "ok.sh")
    with pytest.raises(wd.OpError):
        wd.op_run_hook({"name": "link"}, str(tmp_path))
    with pytest.raises(wd.OpError):
        wd.op_run_hook({"name": "missing"}, str(tmp_path))


def test_handler_bug_does_not_kill_the_daemon():
    def boom(_a):
        raise RuntimeError("secret internal detail")
    r = call("x", ops={"x": boom})
    assert r["ok"] is False and "secret" not in r["error"]


def test_serve_speaks_line_delimited_json_with_hello():
    req = (json.dumps({"id": 7, "op": "status"}) + "\n" + "\n" + json.dumps({"id": 8, "op": "nope"}) + "\n").encode()
    out = io.BytesIO()
    wd.serve(io.BytesIO(req), out, ops={"status": lambda a: {"fine": True}})
    lines = [json.loads(x) for x in out.getvalue().decode().splitlines()]
    assert lines[0]["hello"] == "hscl-workshopd"
    assert lines[1] == {"id": 7, "ok": True, "result": {"fine": True}}
    assert lines[2]["ok"] is False and lines[2]["id"] == 8


@pytest.mark.parametrize("ok", ["/usr/bin/hscl", "/usr/lib/hscl/workshop/hscl-respin", "/etc/hscl/x.toml", "/var/lib/hscl/workshop/debs/a.deb", "/usr/share/doc/hscl-handbook/en/x.html"])
def test_hscl_owned_paths_are_allowed(ok, tmp_path):
    assert wd.validate_put_path(ok, str(tmp_path))


def test_oversized_reply_is_replaced_by_an_error_not_written():
    """A reply the host cannot take in time would wedge the virtio port; the daemon refuses to send more than MAX_REPLY_BYTES."""
    big = {"huge": lambda a: {"blob": "x" * (wd.MAX_REPLY_BYTES + 10)}, "small": lambda a: {"ok": 1}}
    rin = io.BytesIO(b'{"id":1,"op":"huge","args":{}}\n{"id":2,"op":"small","args":{}}\n')
    out = io.BytesIO()
    wd.serve(rin, out, big)
    lines = out.getvalue().decode().splitlines()
    first, second = json.loads(lines[1]), json.loads(lines[2])
    assert first["ok"] is False and "reply too large" in first["error"] and first["id"] == 1
    assert second["ok"] is True and second["id"] == 2
    assert all(len(l) < wd.MAX_REPLY_BYTES for l in lines)
