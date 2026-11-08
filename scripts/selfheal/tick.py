#!/usr/bin/env python3
"""Durable self-heal scheduler: one bounded tick (ledger row 8, docs/research/SELFHEAL_SCHEDULER_DESIGN.md).

A tick decides, starts at most one unit of work, records the outcome and exits. No daemon, never root,
state in a per-user directory outside the repository. Real mode is opt-in (`--execute`); the default is a dry run.

    python scripts/selfheal/tick.py [--rows scripts/selfheal/rows.json] [--state-dir DIR] [--execute]

Only read-only rows belong in the rows file: anything that edits the repository, pushes, opens a PR or merges is not tick work.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

TICK_LIMIT_S = 90.0      # below the 120 s interval
STALE_AFTER_S = 300.0    # a lock older than this is taken over
MAX_FAILURES = 3
_SECRET_SHAPED = re.compile(r"(?i)(token|secret|passw(or)?d|api[_-]?key|bearer)\s*[=:]\s*\S{6,}")


class RowError(ValueError):
    """A rows file entry that must never be executed."""


class StateCorrupt(Exception):
    pass


def default_state_dir() -> Path:
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    else:
        base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "hscl-selfheal"


def validate_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    for r in rows:
        rid, argv = r.get("id"), r.get("argv")
        if not isinstance(rid, str) or not rid:
            raise RowError("a row needs a non-empty string 'id'")
        if rid in seen:
            raise RowError(f"duplicate row id '{rid}'")
        seen.add(rid)
        if not isinstance(argv, list) or not argv or not all(isinstance(a, str) for a in argv):
            raise RowError(f"row '{rid}': 'argv' must be a non-empty list of strings (no shell text)")
        if any(_SECRET_SHAPED.search(a) for a in argv):
            raise RowError(f"row '{rid}': an argument looks like a secret; rows never carry credentials")
    return rows


class _Lock:
    """Exclusive-create lock file with owner pid, start time and a stale-after limit."""

    def __init__(self, path: Path, stale_after: float, now: Callable[[], float]) -> None:
        self.path, self.stale_after, self.now, self.held = path, stale_after, now, False

    def _read(self) -> dict[str, Any] | None:
        try:
            data = json.loads(self.path.read_text("utf-8"))
            return data if isinstance(data, dict) else {}
        except FileNotFoundError:
            return None
        except (OSError, ValueError):
            return {}

    def _create(self) -> bool:
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            return False
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump({"pid": os.getpid(), "started": self.now()}, fh)
        return True

    def acquire(self) -> bool:
        if self._create():
            self.held = True
            return True
        info = self._read()
        if info is None:  # vanished between the two calls: try once more
            self.held = self._create()
            return self.held
        started = info.get("started")
        stale = not isinstance(started, (int, float)) or self.now() - started > self.stale_after
        if not stale:
            return False
        # Take over atomically: only one contender can rename the stale file away.
        claim = self.path.with_name(f"{self.path.name}.stale.{os.getpid()}")
        try:
            os.rename(self.path, claim)
        except OSError:
            return False
        try:
            moved = json.loads(claim.read_text("utf-8"))
        except (OSError, ValueError):
            moved = {}
        if moved.get("started") != started:  # we moved somebody's fresh lock: put it back, do not run
            try:
                os.rename(claim, self.path)
            except OSError:
                pass
            return False
        claim.unlink(missing_ok=True)
        self.held = self._create()
        return self.held

    def held_by_other(self) -> bool:
        info = self._read()
        if info is None:
            return False
        started = info.get("started")
        return isinstance(started, (int, float)) and self.now() - started <= self.stale_after

    def release(self) -> None:
        if self.held:
            self.path.unlink(missing_ok=True)
            self.held = False


def _kill_tree(proc: subprocess.Popen[bytes]) -> None:
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True, check=False)
    else:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass


def _worker_env() -> dict[str, str]:
    env = {"PATH": os.environ.get("PATH", ""), "LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1"}
    for name in ("SYSTEMROOT", "SystemRoot", "TEMP", "TMP", "HOME", "USERPROFILE"):
        if name in os.environ:  # needed for the interpreter and git to start; no credentials among them
            env[name] = os.environ[name]
    return env


class Tick:
    def __init__(
        self, *, state_dir: Path, rows: list[dict[str, Any]], tick_limit: float = TICK_LIMIT_S,
        stale_after: float = STALE_AFTER_S, now: Callable[[], float] = time.time, cwd: Path | None = None,
    ) -> None:
        self.dir = Path(state_dir)
        self.rows = validate_rows(rows)
        self.tick_limit, self.now, self.cwd = tick_limit, now, cwd
        self.glock = _Lock(self.dir / "global.lock", stale_after, now)
        self.hlock = _Lock(self.dir / "heavy.lock", stale_after, now)

    # -- files -------------------------------------------------------------------------------
    def _load_state(self) -> dict[str, Any]:
        path = self.dir / "state.json"
        if not path.exists():
            return {"rows": {}}
        try:
            data = json.loads(path.read_text("utf-8"))
        except (OSError, ValueError) as exc:
            raise StateCorrupt(str(exc)) from exc
        if not isinstance(data, dict) or not isinstance(data.get("rows", {}), dict):
            raise StateCorrupt("unexpected shape")
        data.setdefault("rows", {})
        return data

    def _save_state(self, state: dict[str, Any]) -> None:
        fd, tmp = tempfile.mkstemp(prefix="state.", suffix=".tmp", dir=self.dir)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2, sort_keys=True)
        os.replace(tmp, self.dir / "state.json")

    def _log(self, **fields: Any) -> None:
        with open(self.dir / "tick.log.jsonl", "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": round(self.now(), 3), **fields}, sort_keys=True) + "\n")

    # -- the tick ----------------------------------------------------------------------------
    def run(self, *, dry_run: bool = True) -> dict[str, Any]:
        self.dir.mkdir(parents=True, exist_ok=True)
        if dry_run:
            return self._decide(None, dry_run=True)
        if not self.glock.acquire():
            res = {"outcome": "skipped: locked", "row": None}
            self._log(row=None, outcome=res["outcome"])
            return res
        try:
            return self._decide(self.glock, dry_run=False)
        finally:
            self.glock.release()

    def _decide(self, _held: _Lock | None, *, dry_run: bool) -> dict[str, Any]:
        try:
            state = self._load_state()
        except StateCorrupt as exc:
            res = {"outcome": "refused: corrupt state", "row": None}
            self._log(row=None, outcome=res["outcome"], detail=str(exc)[:120])
            return res
        chosen = next((r for r in self.rows if not state["rows"].get(r["id"], {}).get("blocked")), None)
        if chosen is None:
            res = {"outcome": "idle", "row": None}
            self._log(row=None, outcome="idle")
            return res
        rid, argv = chosen["id"], chosen["argv"]
        if dry_run:
            res = {"outcome": "dry-run", "row": rid, "argv": argv}
            self._log(row=rid, argv=argv, outcome="dry-run")
            return res
        heavy = bool(chosen.get("heavy"))
        if heavy and not self.hlock.acquire():
            res = {"outcome": "deferred", "row": rid}
            self._log(row=rid, argv=argv, outcome="deferred")
            return res
        try:
            outcome, code, seconds = self._execute(argv)
        finally:
            if heavy:
                self.hlock.release()
        entry = state["rows"].setdefault(rid, {"failures": 0})
        if outcome == "ok":
            entry["failures"], entry["blocked"] = 0, False
        else:
            entry["failures"] = int(entry.get("failures", 0)) + 1
            if entry["failures"] >= MAX_FAILURES:
                entry["blocked"] = True
                outcome = "blocked"
        state.update(last_tick=round(self.now(), 3), last_row=rid, last_outcome=outcome)
        self._save_state(state)
        self._log(row=rid, argv=argv, outcome=outcome, exit=code, seconds=round(seconds, 3))
        return {"outcome": outcome, "row": rid, "exit": code}

    def _execute(self, argv: list[str]) -> tuple[str, int | None, float]:
        started = time.monotonic()
        try:
            proc = subprocess.Popen(
                argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                env=_worker_env(), cwd=self.cwd, close_fds=True,
                **({"start_new_session": True} if os.name != "nt" else {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}),
            )
        except OSError:
            return "failed", None, time.monotonic() - started
        try:
            code = proc.wait(timeout=self.tick_limit)
        except subprocess.TimeoutExpired:
            _kill_tree(proc)
            proc.wait()
            return "timeout", None, time.monotonic() - started
        _kill_tree(proc)  # no stray grandchildren after a normal exit
        return ("ok" if code == 0 else "failed"), code, time.monotonic() - started


def load_rows(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text("utf-8"))
    return validate_rows(data["rows"] if isinstance(data, dict) else data)


def main(argv: list[str] | None = None) -> int:
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rows", type=Path, default=here / "rows.json")
    ap.add_argument("--state-dir", type=Path, default=None)
    ap.add_argument("--execute", action="store_true", help="real mode; without it the tick only prints what it would do")
    args = ap.parse_args(argv)
    try:
        rows = load_rows(args.rows)
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({"outcome": "refused: bad rows file", "detail": str(exc)[:200]}))
        return 2
    result = Tick(state_dir=args.state_dir or default_state_dir(), rows=rows, cwd=here.parents[1]).run(dry_run=not args.execute)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["outcome"] in ("ok", "dry-run", "idle", "skipped: locked", "deferred") else 1


if __name__ == "__main__":
    raise SystemExit(main())
