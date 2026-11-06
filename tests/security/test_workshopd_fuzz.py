"""Seeded fuzzing of the Workshop daemon's request parser and path allow-list (no extra dependencies, deterministic).

Properties: handle() never raises and always answers with a dict carrying `ok`; validate_put_path() never accepts a path
whose normalised form leaves the allow-list, and never returns a target outside the given root.
"""
import json
import os
import posixpath
import random
from pathlib import Path

import pytest

from test_workshopd import wd  # reuse the loaded module

SEED = 20261106
PIECES = ["..", ".", "", "/", "//", "\x00", "%2e%2e", "usr", "etc", "share", "hscl", "bin", "lib", "‮", "∕", "~", "$HOME", "x" * 300, "\n", " "]
ALLOWED = [p for p in wd.ALLOWED_PREFIXES] + list(wd.ALLOWED_EXACT)


def mutate(rng: random.Random) -> str:
    base = rng.choice(ALLOWED + ["/", "", "/usr/share/hscl", "/etc/passwd"])
    parts = base.split("/")
    for _ in range(rng.randint(0, 4)):
        i = rng.randint(0, len(parts))
        parts.insert(i, rng.choice(PIECES))
    s = "/".join(parts)
    if rng.random() < 0.3:
        s = s.replace("/", rng.choice(["/", "//", "/./", "/../"]), rng.randint(1, 3))
    return s


def test_validate_put_path_never_leaves_the_allow_list(tmp_path):
    rng = random.Random(SEED)
    accepted = 0
    for _ in range(4000):
        p = mutate(rng)
        try:
            target = wd.validate_put_path(p, str(tmp_path))
        except wd.OpError:
            continue
        accepted += 1
        norm = posixpath.normpath(p)
        assert "\x00" not in p and p.startswith("/")
        assert norm in wd.ALLOWED_EXACT or any(norm.startswith(pre.rstrip("/") + "/") or norm == pre.rstrip("/") for pre in wd.ALLOWED_PREFIXES), p
        resolved = Path(os.path.normpath(target))
        assert resolved == tmp_path or tmp_path in resolved.parents, (p, target)
    assert accepted > 0  # the generator must also produce valid paths, or the property would be vacuous


def random_json(rng: random.Random, depth: int = 0):
    kinds = ["null", "bool", "int", "float", "str", "list", "dict"] if depth < 3 else ["null", "bool", "int", "str"]
    k = rng.choice(kinds)
    if k == "null":
        return None
    if k == "bool":
        return rng.random() < 0.5
    if k == "int":
        return rng.choice([0, -1, 2**63, 10**30, rng.randint(-5, 5)])
    if k == "float":
        return rng.choice([0.0, -0.0, 1e308, 3.14])
    if k == "str":
        return rng.choice(["", "status", "put_file", "run_hook", "respin", "../x", "\x00", "A" * 1000, "ä‮"])
    if k == "list":
        return [random_json(rng, depth + 1) for _ in range(rng.randint(0, 3))]
    return {rng.choice(["id", "op", "args", "path", "mode", "name", "content_b64", "x"]): random_json(rng, depth + 1) for _ in range(rng.randint(0, 4))}


def test_handle_never_raises_and_always_answers():
    rng = random.Random(SEED + 1)
    inert = {name: (lambda _a: {}) for name in wd.OPS}  # exercise parsing and dispatch only, not the real handlers
    for _ in range(4000):
        r = rng.random()
        if r < 0.3:
            line = "".join(chr(rng.randint(0, 0x2FF)) for _ in range(rng.randint(0, 60)))
        elif r < 0.6:
            line = json.dumps(random_json(rng))
        else:
            line = json.dumps({"id": random_json(rng), "op": rng.choice(list(wd.OPS) + [random_json(rng)]), "args": random_json(rng)})
        out = wd.handle(line, inert)
        assert isinstance(out, dict) and isinstance(out.get("ok"), bool), line
        json.dumps(out)  # the answer itself must be serialisable


def test_fuzzed_real_ops_with_hostile_args_are_contained(tmp_path, monkeypatch):
    """Real handlers with random arguments: an error or a clean result, never a crash, never a write outside the temp root."""
    rng = random.Random(SEED + 2)
    monkeypatch.setattr(wd, "HOOKS_DIR", str(tmp_path / "hooks"))
    ops = {"put_file": lambda a: wd.op_put_file(a, str(tmp_path)), "run_hook": lambda a: wd.op_run_hook(a, str(tmp_path / "hooks"))}
    before = set(tmp_path.rglob("*"))
    for _ in range(1500):
        args = {k: random_json(rng) for k in rng.sample(["path", "mode", "content_b64", "name", "args", "x"], rng.randint(0, 5))}
        if rng.random() < 0.5:
            args["path"] = mutate(rng)
        out = wd.handle(json.dumps({"id": 1, "op": rng.choice(list(ops)), "args": args}), ops)
        assert isinstance(out["ok"], bool)
    for created in set(tmp_path.rglob("*")) - before:
        assert tmp_path in created.parents
