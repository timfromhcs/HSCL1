"""scripts/ts_coverage.py: translation coverage report for Qt .ts files (AGENTS.md 10.2: a release gate must fail on missing translations)."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/ts_coverage.py"

TS = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="{lang}">
<context><name>page</name>
{messages}
</context>
</TS>
"""


def write(tmp_path, lang, rows, name=None):
    msgs = "\n".join(
        f'<message><source>{s}</source><translation{(" type=" + chr(34) + t + chr(34)) if t else ""}>{v}</translation></message>' for s, v, t in rows
    )
    p = tmp_path / (name or f"x_{lang}.ts")
    p.write_text(TS.format(lang=lang, messages=msgs), encoding="utf-8")
    return p


def run(*paths):
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, paths)], capture_output=True, text=True)


def test_complete_file_passes_and_reports_counts(tmp_path):
    p = write(tmp_path, "de", [("Hello", "Hallo", None), ("Bye", "Tschüss", None)])
    r = run(p)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "2/2" in r.stdout and "de" in r.stdout


def test_unfinished_translation_fails(tmp_path):
    p = write(tmp_path, "de", [("Hello", "Hallo", None), ("Bye", "", "unfinished")])
    r = run(p)
    assert r.returncode == 1
    assert "unfinished" in (r.stdout + r.stderr).lower() and "Bye" in (r.stdout + r.stderr)


def test_empty_translation_fails(tmp_path):
    p = write(tmp_path, "fr", [("Hello", "", None)])
    assert run(p).returncode == 1


def test_translation_identical_to_source_fails_for_non_english(tmp_path):
    p = write(tmp_path, "fr", [("Hello", "Hello", None)])
    r = run(p)
    assert r.returncode == 1 and "identical" in (r.stdout + r.stderr).lower()


def test_english_may_be_identical(tmp_path):
    p = write(tmp_path, "en", [("Hello", "Hello", None)])
    assert run(p).returncode == 0


def test_several_files_all_must_pass(tmp_path):
    good = write(tmp_path, "de", [("Hello", "Hallo", None)], "a_de.ts")
    bad = write(tmp_path, "fr", [("Hello", "", "unfinished")], "b_fr.ts")
    assert run(good, bad).returncode == 1


def test_missing_file_is_a_usage_error(tmp_path):
    assert run(tmp_path / "nope.ts").returncode == 2


def test_real_hscl1_translation_files_are_complete():
    r = run(ROOT / "distro/installer/i18n/calamares-hscl1_de.ts", ROOT / "distro/installer/i18n/calamares-hscl1_fr.ts")
    assert r.returncode == 0, r.stdout + r.stderr


def test_quiet_prints_nothing_for_a_complete_file_and_only_problems_otherwise(tmp_path):
    good = write(tmp_path, "de", [("Back", "Zurueck", "")], name="good.ts")
    bad = write(tmp_path, "fr", [("Next", "", "unfinished")], name="bad.ts")
    r = subprocess.run([sys.executable, str(SCRIPT), "--quiet", str(good)], capture_output=True, text=True)
    assert r.returncode == 0 and r.stdout == ""
    r = subprocess.run([sys.executable, str(SCRIPT), "--quiet", str(good), str(bad)], capture_output=True, text=True)
    assert r.returncode == 1
    assert "finished" not in r.stdout and "unfinished: Next" in r.stdout
