#!/usr/bin/env python3
"""Bounded verify-patch loop for local models (plan L, task L3).

The model proposes whole-file blocks (`FILE: path` + a fenced block). Blocks are applied to a throwaway COPY of the tree; the
caller's test command decides. Failures are fed back for at most `max_rounds` rounds. The real tree is never modified: the result
carries a unified diff for the caller to review and apply. Protected files (tests) and anything outside the editable list are
refused. The model's output is data, never executed except through the test command the caller chose (no shell).
"""
from __future__ import annotations

import difflib
import hashlib
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable, Sequence

IGNORE = shutil.ignore_patterns(".git", "node_modules", "target", "artifacts", "__pycache__", ".venv", ".pytest_cache")
MAX_TREE_BYTES = 50 * 1024 * 1024
MAX_DIFF = 20000
BLOCK_RE = re.compile(r"^FILE:[ \t]*(\S[^\n]*?)[ \t]*\n```[^\n]*\n(.*?)^```[ \t]*$", re.M | re.S)

SYSTEM = (
    "You are a precise coding subagent. Answer only with complete replacement files, one block per file, in exactly this form:\n"
    "FILE: relative/path.py\n```python\n<entire new file content>\n```\n"
    "Do not edit test files. Do not explain."
)


@dataclass
class Result:
    ok: bool
    rounds: int
    diff: str
    last_output: str
    reason: str


def _tree_size(root: Path) -> int:
    total = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in {".git", "node_modules", "target", "artifacts", "__pycache__", ".venv", ".pytest_cache"}]
        for f in filenames:
            try:
                total += (Path(dirpath) / f).lstat().st_size
            except OSError:
                pass
    return total


def _norm(path: str) -> str | None:
    """Return a clean relative POSIX path or None when it could leave the tree."""
    p = path.strip().replace("\\", "/")
    if not p or p.startswith("/") or ":" in p:
        return None
    parts = PurePosixPath(p).parts
    if any(x in ("..", "") for x in parts):
        return None
    return str(PurePosixPath(*parts))


def _cap(text: str, limit: int) -> str:
    return text if len(text) <= limit else "[...]" + text[-limit:]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""


def _prompt(task: str, root: Path, files: Sequence[str]) -> str:
    parts = [f"Task: {task}", "", "Editable files (current content):"]
    for f in files:
        p = root / f
        body = p.read_text(encoding="utf-8", errors="replace") if p.is_file() else "(does not exist yet)\n"
        parts.append(f"FILE: {f}\n```\n{body}```")
    return "\n".join(parts)


def _apply(blocks: list[tuple[str, str]], tmp: Path, editable: set[str], protected: set[str]) -> list[str]:
    """Validate every block first; write nothing unless all are acceptable. Returns refusal messages."""
    problems = []
    for raw, _ in blocks:
        rel = _norm(raw)
        if rel is None:
            problems.append(f"refused: path escapes the tree: {raw!r}")
        elif rel in protected:
            problems.append(f"refused: protected file: {rel}")
        elif rel not in editable:
            problems.append(f"refused: not editable: {rel}")
        elif (tmp / rel).is_symlink():
            problems.append(f"refused: symlink target: {rel}")
    if problems:
        return problems
    for raw, body in blocks:
        rel = _norm(raw)
        assert rel is not None
        dest = tmp / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(body, encoding="utf-8", newline="\n")
    return []


def run_task(
    chat: Callable[[list[dict]], str],
    workdir: Path,
    files: Sequence[str],
    task: str,
    test_cmd: Sequence[str],
    max_rounds: int = 3,
    timeout_s: int = 120,
    protected: Sequence[str] = (),
    max_output: int = 8000,
    history: str = "window",
) -> Result:
    """history="window" (default): the chat shows the task, only the model's LATEST answer and the latest failure, so the context stays
    constant from round 2 on (round 2 is exactly what "full" sends). history="full": every answer and failure stays in the chat.
    A first attempt at a stateless "last" mode re-sent the same prompt each round; the deterministic model then repeated its wrong
    answer word for word (word_count: 0 of 6 solved versus 6 of 6 with the chat history) and was removed."""
    if history not in ("window", "full"):
        raise ValueError(f"history must be 'window' or 'full', got {history!r}")
    workdir = Path(workdir).resolve()
    editable = {n for n in (_norm(f) for f in files) if n}
    prot = {n for n in (_norm(f) for f in protected) if n}
    if _tree_size(workdir) > MAX_TREE_BYTES:
        return Result(False, 0, "", "tree too large to copy", "tree_too_large")
    with tempfile.TemporaryDirectory(prefix="hscl-local-") as td:
        tmp = Path(td) / "tree"
        shutil.copytree(workdir, tmp, symlinks=True, ignore=IGNORE)
        originals = {f: (workdir / f).read_text(encoding="utf-8", errors="replace") if (workdir / f).is_file() else "" for f in editable}
        prot_hashes = {f: _sha(tmp / f) for f in prot}
        messages: list[dict] = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": _prompt(task, tmp, sorted(editable))}]
        last = ""
        previous_answer: str | None = None
        for n in range(1, max_rounds + 1):
            answer = chat(list(messages))  # a copy: the client must not be able to alter the loop's history
            messages.append({"role": "assistant", "content": answer})
            blocks = BLOCK_RE.findall(answer or "")
            if not blocks:
                last = "no FILE block found in your answer; reply with FILE blocks only"
            else:
                problems = _apply(blocks, tmp, editable, prot)
                if problems:
                    last = "; ".join(problems)
                else:
                    try:
                        cp = subprocess.run(list(test_cmd), cwd=tmp, capture_output=True, timeout=timeout_s, shell=False)
                        out = (cp.stdout + cp.stderr).decode("utf-8", errors="replace")
                        last = _cap(out, max_output)
                        if cp.returncode == 0:
                            changed = [f for f in prot if _sha(tmp / f) != prot_hashes[f]]
                            if changed:
                                return Result(False, n, "", f"protected files changed during tests: {changed}", "protected_modified")
                            return Result(True, n, _diff(originals, tmp), last, "green")
                    except subprocess.TimeoutExpired as e:
                        partial = ((e.stdout or b"") + (e.stderr or b"")).decode("utf-8", errors="replace")
                        last = _cap(f"timeout after {timeout_s}s\n{partial}", max_output)
            feedback = f"The tests did not pass (round {n} of {max_rounds}). Output:\n{last}\nReply again with corrected FILE blocks."
            if previous_answer is not None and answer.strip() == previous_answer.strip():
                feedback += "\nYour answer is identical to your previous answer and failed again: change your approach."
            previous_answer = answer
            messages.append({"role": "user", "content": feedback})
            if history == "window" and len(messages) > 4:
                messages = messages[:2] + messages[-2:]  # system, task, latest answer, latest failure
        return Result(False, max_rounds, "", last, "max_rounds")


def _diff(originals: dict[str, str], tmp: Path) -> str:
    chunks = []
    for rel, old in sorted(originals.items()):
        p = tmp / rel
        new = p.read_text(encoding="utf-8", errors="replace") if p.is_file() else ""
        if new != old:
            chunks.extend(difflib.unified_diff(old.splitlines(True), new.splitlines(True), f"a/{rel}", f"b/{rel}"))
    return _cap("".join(chunks), MAX_DIFF)
