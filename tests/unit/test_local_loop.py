"""Plan L, Task L3: bounded verify-patch loop. The model proposes whole-file blocks, tests decide."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "local_worker"))
import loop  # noqa: E402

GOOD = '''def parse_score(s):
    out = {}
    for part in s.split(","):
        if "=" not in part:
            raise ValueError("missing =")
        k, v = part.split("=", 1)
        try:
            out[k] = int(v)
        except ValueError:
            out[k] = float(v)
    return out
'''
BAD = GOOD.replace("int(v)", "float(v)")  # the real bug the 4B model made: ints become floats

CHECK = '''import sys
sys.path.insert(0, ".")
from impl import parse_score
r = parse_score("a=1,b=2.5")
assert type(r["a"]) is int, "a must be int"
assert type(r["b"]) is float, "b must be float"
try:
    parse_score("nokey")
except ValueError:
    pass
else:
    raise SystemExit("ValueError expected")
print("ok")
'''


@pytest.fixture
def proj(tmp_path):
    (tmp_path / "impl.py").write_text("def parse_score(s):\n    raise NotImplementedError\n", encoding="utf-8")
    (tmp_path / "check.py").write_text(CHECK, encoding="utf-8")
    return tmp_path


def block(path, text):
    return f"FILE: {path}\n```python\n{text}```\n"


class Script:
    def __init__(self, *answers):
        self.answers = list(answers)
        self.calls = []

    def __call__(self, messages):
        self.calls.append(messages)
        return self.answers.pop(0) if self.answers else ""


def go(proj, chat, **kw):
    return loop.run_task(chat, proj, ["impl.py"], "implement parse_score", [sys.executable, "check.py"], protected=["check.py"], **kw)


def test_green_in_round_one_and_original_tree_is_untouched(proj):
    r = go(proj, Script(block("impl.py", GOOD)))
    assert r.ok and r.rounds == 1 and r.reason == "green"
    assert "+        try:" in r.diff
    assert "NotImplementedError" in (proj / "impl.py").read_text(encoding="utf-8")  # worker never writes into the real tree


def test_failure_output_is_fed_back_and_round_two_can_succeed(proj):
    chat = Script(block("impl.py", BAD), block("impl.py", GOOD))
    r = go(proj, chat)
    assert r.ok and r.rounds == 2
    assert "a must be int" in chat.calls[1][-1]["content"]


def test_stops_at_the_round_budget(proj):
    r = go(proj, Script(block("impl.py", BAD), block("impl.py", BAD), block("impl.py", BAD), block("impl.py", GOOD)), max_rounds=3)
    assert not r.ok and r.rounds == 3 and r.reason == "max_rounds"


def test_empty_answer_is_a_failed_round_not_a_success(proj):
    r = go(proj, Script("", block("impl.py", GOOD)))
    assert r.ok and r.rounds == 2


def test_answer_without_file_blocks_is_a_failed_round(proj):
    chat = Script("I fixed it, trust me.", block("impl.py", GOOD))
    r = go(proj, chat)
    assert r.ok and r.rounds == 2 and "no FILE block" in chat.calls[1][-1]["content"]


@pytest.mark.parametrize("bad_path", ["../evil.py", "/etc/evil.py", "C:/evil.py", "sub/../../evil.py"])
def test_paths_outside_the_tree_are_refused(proj, bad_path):
    r = go(proj, Script(block(bad_path, "x = 1\n")), max_rounds=1)
    assert not r.ok and "refused" in r.last_output
    assert not (proj.parent / "evil.py").exists()


def test_files_not_in_the_editable_list_are_refused(proj):
    r = go(proj, Script(block("other.py", "x = 1\n")), max_rounds=1)
    assert not r.ok and "not editable" in r.last_output


def test_editing_a_protected_test_file_is_refused_even_if_it_would_pass(proj):
    r = go(proj, Script(block("check.py", 'print("ok")\n')), max_rounds=1)
    assert not r.ok and r.reason == "max_rounds" and "protected" in r.last_output
    assert (proj / "check.py").read_text(encoding="utf-8") == CHECK


def test_hanging_tests_are_killed(proj):
    (proj / "check.py").write_text("import time\ntime.sleep(30)\n", encoding="utf-8")
    r = go(proj, Script(block("impl.py", GOOD)), max_rounds=1, timeout_s=1)
    assert not r.ok and "timeout" in r.last_output


def test_test_output_is_capped(proj):
    (proj / "check.py").write_text('print("x" * 2_000_000)\nraise SystemExit(1)\n', encoding="utf-8")
    r = go(proj, Script(block("impl.py", GOOD)), max_rounds=1, max_output=4000)
    assert len(r.last_output) <= 4200


def test_symlink_targets_are_not_followed(proj, tmp_path_factory):
    outside = tmp_path_factory.mktemp("outside") / "secret.py"
    outside.write_text("keep\n", encoding="utf-8")
    try:
        (proj / "impl.py").unlink()
        (proj / "impl.py").symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not permitted on this platform/user (narrow skip; Linux CI runs it)")
    r = go(proj, Script(block("impl.py", GOOD)), max_rounds=1)
    assert outside.read_text(encoding="utf-8") == "keep\n"
    assert not r.ok


# ---- context management (owner request 2026-11-06: less memory per round) ----

def test_default_window_keeps_the_context_constant_from_round_two_on(proj):
    chat = Script(block("impl.py", BAD), block("impl.py", BAD), block("impl.py", BAD), block("impl.py", BAD))
    go(proj, chat, max_rounds=4)
    sizes = [sum(len(m["content"]) for m in call) for call in chat.calls]
    assert [len(c) for c in chat.calls] == [2, 4, 4, 4], "system, task, ONLY the latest answer, latest feedback"
    assert sizes[3] <= sizes[2] * 1.15 and sizes[2] <= sizes[1] * 1.15, sizes


def test_window_round_two_prompt_is_identical_to_the_full_history_prompt(proj, tmp_path_factory):
    """Regression for the discarded 'last' mode (2026-11-06): it re-sent the task and the file as a fresh message, so the model saw
    the same prompt again and repeated its answer word for word (word_count: 0 of 6 solved, versus 6 of 6 with the chat history).
    The window must show round 2 exactly like the full history does: system, task, the model's own answer, the failure."""
    a = Script(block("impl.py", BAD), block("impl.py", GOOD))
    b = Script(block("impl.py", BAD), block("impl.py", GOOD))
    go(proj, a, history="window")
    other = tmp_path_factory.mktemp("proj2")
    (other / "impl.py").write_text("def parse_score(s):\n    raise NotImplementedError\n", encoding="utf-8")
    (other / "check.py").write_text(CHECK, encoding="utf-8")
    go(other, b, history="full")
    import re as _re

    def clean(call):
        # the traceback inside the feedback names the random temp directory (hscl-local-<random>); everything else must be identical
        return _re.sub(r"hscl-local-\w+", "TMP", json.dumps(call))

    assert clean(a.calls[1]) == clean(b.calls[1])
    assert "TMP" in clean(a.calls[1]), "the normalization must actually have something to normalize, or the test proves nothing"


def test_a_word_for_word_repeated_answer_is_called_out_in_the_feedback(proj):
    chat = Script(block("impl.py", BAD), block("impl.py", BAD), block("impl.py", GOOD))
    go(proj, chat, max_rounds=3)
    assert "identical" not in chat.calls[1][-1]["content"]  # first failure: nothing repeated yet
    third = chat.calls[2][-1]["content"]
    assert "identical to your previous answer" in third and "change your approach" in third


def test_window_shows_the_models_latest_answer_and_the_latest_failure(proj):
    chat = Script(block("impl.py", BAD), block("impl.py", GOOD))
    go(proj, chat)
    second = chat.calls[1]
    assert [m["role"] for m in second] == ["system", "user", "assistant", "user"]
    assert "out[k] = float(v)" in second[2]["content"], "the model must see its own previous answer"
    assert "a must be int" in second[3]["content"] and "round 1 of 3" in second[3]["content"]


def test_the_discarded_last_mode_is_no_longer_accepted(proj):
    with pytest.raises(ValueError, match="history"):
        go(proj, Script(block("impl.py", GOOD)), history="last")


def test_full_mode_still_grows_the_history(proj):
    chat = Script(block("impl.py", BAD), block("impl.py", BAD), block("impl.py", BAD))
    go(proj, chat, max_rounds=3, history="full")
    assert [len(c) for c in chat.calls] == [2, 4, 6]


def test_unknown_history_mode_is_rejected(proj):
    with pytest.raises(ValueError, match="history"):
        go(proj, Script(block("impl.py", GOOD)), history="everything")
