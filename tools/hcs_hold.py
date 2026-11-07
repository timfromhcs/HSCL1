#!/usr/bin/env python3
"""Host hold flag for heavy jobs (LoRA training, builds, VMs): while it is set, the LocalAI gateway, the Windows autostart script and the
local delegate load nothing and restart nothing. Same file format as the gateway's `localai_gateway/hold.py`.

  hcs_hold.py status
  hcs_hold.py set "reason" [--pid N]
  hcs_hold.py clear
  hcs_hold.py run "reason" -- COMMAND [ARGS...]    hold for exactly as long as COMMAND runs; exit code is COMMAND's

The hold names its owner process; a hold whose owner is gone is stale and ignored everywhere, so a crash can not block the machine.
`set` and `run` also ask a running gateway (127.0.0.1:8090) to unload its idle models; that call is best effort.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

GATEWAY = "http://127.0.0.1:8090"


def hold_path() -> Path:
    env = os.environ.get("HCS_HOLD_FILE")
    if env:
        return Path(env)
    return Path(r"C:\AI\state\hold.json") if sys.platform.startswith("win") else Path.home() / ".hcs" / "hold.json"


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform.startswith("win"):
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH", "/FO", "CSV"], capture_output=True, text=True, errors="replace").stdout
        return f'"{pid}"' in out
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def read_hold(path: Path | None = None) -> dict | None:
    try:
        data = json.loads((path or hold_path()).read_text(encoding="utf-8"))
        pid = int(data["pid"])
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return {"reason": str(data.get("reason", "heavy job")), "pid": pid, "since": data.get("since")} if pid_alive(pid) else None


def set_hold(reason: str, pid: int, path: Path | None = None) -> None:
    p = path or hold_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps({"reason": reason[:200], "pid": pid, "since": time.time()}), encoding="utf-8")
    os.replace(tmp, p)


def clear_hold(path: Path | None = None) -> bool:
    try:
        (path or hold_path()).unlink()
        return True
    except FileNotFoundError:
        return False


def ask_gateway_to_unload() -> None:
    try:
        req = urllib.request.Request(GATEWAY + "/v1/unload", data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=3).read()
    except Exception:  # no gateway running is the normal case during a hold
        pass


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in {"status", "set", "clear", "run"}:
        print(__doc__)
        return 2
    cmd = argv[0]
    if cmd == "status":
        h = read_hold()
        print(json.dumps(h) if h else "no hold")
        return 0
    if cmd == "clear":
        print("cleared" if clear_hold() else "no hold")
        return 0
    if len(argv) < 2:
        print("a reason is required", file=sys.stderr)
        return 2
    reason = argv[1]
    if cmd == "set":
        pid = int(argv[argv.index("--pid") + 1]) if "--pid" in argv else os.getppid()
        set_hold(reason, pid)
        ask_gateway_to_unload()
        print(f"hold set by pid {pid}: {reason}")
        return 0
    if "--" not in argv:
        print("usage: hcs_hold.py run REASON -- COMMAND [ARGS...]", file=sys.stderr)
        return 2
    command = argv[argv.index("--") + 1:]
    if not command:
        print("no command after --", file=sys.stderr)
        return 2
    existing = read_hold()
    if existing:
        print(f"refusing to start: host already on hold ({existing['reason']}, pid {existing['pid']})", file=sys.stderr)
        return 3
    set_hold(reason, os.getpid())
    ask_gateway_to_unload()
    try:
        return subprocess.call(command)
    finally:
        clear_hold()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
