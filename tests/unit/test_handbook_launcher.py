"""hscl-handbook launcher picks the handbook language from the locale (sh, run via bash).

Runs on Linux CI, in WSL and with Git Bash on Windows through tests/shellutil.py.
"""
from pathlib import Path

import pytest

import shellutil

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "packages/debian/hscl-handbook/usr/bin/hscl-handbook"
pytestmark = pytest.mark.skipif(not shellutil.usable(), reason="needs a POSIX shell (native bash or WSL)")


@pytest.fixture()
def docs(tmp_path):
    for lang in ("en", "de", "fr"):
        (tmp_path / lang).mkdir()
        (tmp_path / lang / "index.html").write_text("x")
        (tmp_path / lang / "cli.html").write_text("x")
    return tmp_path


def run(docs, lang, *args):
    return shellutil.run_script(
        SCRIPT,
        *args,
        env_overrides={
            "HSCL_HANDBOOK_DIR": docs,
            "HSCL_OPEN": "echo",
            "LANG": lang,
            "LC_ALL": None,
            "LC_MESSAGES": None,
        },
    )


@pytest.mark.parametrize("loc,lang", [("de_DE.UTF-8", "de"), ("fr_FR.UTF-8", "fr"), ("en_US.UTF-8", "en"), ("ja_JP.UTF-8", "en"), ("C", "en")])
def test_language_selection(docs, loc, lang):
    r = run(docs, loc)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip().replace("\\", "/").endswith(f"/{lang}/index.html")


def test_topic_page_and_unknown_topic(docs):
    assert run(docs, "de_DE.UTF-8", "cli").stdout.strip().replace("\\", "/").endswith("/de/cli.html")
    assert run(docs, "de_DE.UTF-8", "nope").stdout.strip().replace("\\", "/").endswith("/de/index.html")


def test_missing_handbook_is_an_error(tmp_path):
    r = run(tmp_path, "en_US.UTF-8")
    assert r.returncode == 1 and "not found" in r.stderr
