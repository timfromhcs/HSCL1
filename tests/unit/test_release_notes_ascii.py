"""Release notes must be ASCII, because `gh` mangles non-ASCII in the release body on Windows.

On v0.1.7-alpha.0 a single right-arrow in `release-notes.md` reached GitHub as mojibake while the uploaded
asset of the same file was byte-identical - so the artefact was fine and only the release body was wrong. The
consistency checker caught it, but only after the release was public. The rule is now a gate at assembly time.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import make_release  # noqa: E402


def test_ascii_notes_pass():
    make_release.check_ascii("plain notes, with - and ... and 100 %", "release-notes.md")


def test_a_single_non_ascii_character_is_refused_and_named():
    with pytest.raises(make_release.ReleaseError) as err:
        make_release.check_ascii("sender kill(pid=1, SIGKILL) \u2192 victim", "release-notes.md")
    message = str(err.value)
    assert "U+2192" in message, "the error must name the codepoint so it can be found"
    assert "release-notes.md" in message


def test_the_gate_is_wired_into_assembly():
    text = (ROOT / "scripts/make_release.py").read_text(encoding="utf-8")
    assert 'check_ascii(notes, "release-notes.md")' in text, "the check must run where the notes are written"
