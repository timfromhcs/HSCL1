"""Guest typing: every printable ASCII character maps to a QEMU qcode chord (older versions silently dropped ; | : and others)."""
import string
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import qemu_boot_test as q  # noqa: E402

QCODE_NAMES = set(string.ascii_lowercase) | set(string.digits) | {
    "spc", "minus", "dot", "comma", "slash", "ret", "tab", "semicolon", "apostrophe", "equal", "backslash", "bracket_left", "bracket_right",
    "grave_accent", "shift"}


class FakeQmp:
    def __init__(self):
        self.chords = []

    def cmd(self, name, **kw):
        assert name == "send-key"
        self.chords.append([k["data"] for k in kw["keys"]])
        return {}


def typed(text, monkeypatch):
    monkeypatch.setattr(q.time, "sleep", lambda s: None)
    qmp = FakeQmp()
    q.type_text(qmp, text)
    return qmp.chords


def test_every_printable_ascii_character_produces_a_known_chord(monkeypatch):
    for ch in string.printable.replace("\r", "").replace("\x0b", "").replace("\x0c", ""):
        chords = typed(ch, monkeypatch)
        assert len(chords) == 1, repr(ch)
        assert set(chords[0]) <= QCODE_NAMES, (repr(ch), chords)


def test_known_symbols_use_shift_plus_the_right_base_key(monkeypatch):
    assert typed("|", monkeypatch) == [["shift", "backslash"]]
    assert typed(":", monkeypatch) == [["shift", "semicolon"]]
    assert typed(";", monkeypatch) == [["semicolon"]]
    assert typed("_", monkeypatch) == [["shift", "minus"]]
    assert typed("$", monkeypatch) == [["shift", "4"]]
    assert typed("A", monkeypatch) == [["shift", "a"]]
    assert typed("a;b", monkeypatch) == [["a"], ["semicolon"], ["b"]]
