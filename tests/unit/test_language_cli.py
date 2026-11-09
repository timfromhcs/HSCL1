"""Tests for `hscl language` CLI (AGENTS.md section 10.3)."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def find_hscl_binary() -> Path | None:
    debug_bin = ROOT / "target" / "debug" / ("hscl.exe" if os.name == "nt" else "hscl")
    if debug_bin.is_file():
        return debug_bin
    which = shutil.which("hscl")
    if which:
        return Path(which)
    return None


@pytest.fixture
def hscl_bin() -> Path:
    b = find_hscl_binary()
    if b is None:
        pytest.skip("hscl binary not compiled in target/debug")
    return b


def test_language_list_text_and_json(hscl_bin: Path):
    res = subprocess.run([str(hscl_bin), "language", "list"], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT))
    assert res.returncode == 0
    assert "en" in res.stdout
    assert "de" in res.stdout
    assert "fr" in res.stdout
    assert "English" in res.stdout
    assert "Deutsch" in res.stdout
    assert "Français" in res.stdout

    res_j = subprocess.run([str(hscl_bin), "--json", "language", "list"], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT))
    assert res_j.returncode == 0
    data = json.loads(res_j.stdout)
    assert "languages" in data
    ids = [item["id"] for item in data["languages"]]
    assert ids == ["en", "de", "fr"]


def test_language_status_json(hscl_bin: Path, tmp_path: Path):
    env = os.environ.copy()
    env["HSCL_CONFIG_DIR"] = str(tmp_path)
    res = subprocess.run([str(hscl_bin), "--json", "language", "status"], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT), env=env)
    assert res.returncode == 0
    data = json.loads(res.stdout)
    assert data["supported"] == ["en", "de", "fr"]
    assert "plasma_localerc" in data
    assert "locale_conf" in data
    assert data["plasma_localerc_exists"] is False
    assert data["locale_conf_exists"] is False


def test_language_set_dry_run(hscl_bin: Path, tmp_path: Path):
    env = os.environ.copy()
    env["HSCL_CONFIG_DIR"] = str(tmp_path)
    res = subprocess.run(
        [str(hscl_bin), "--json", "language", "set", "de", "--dry-run"],
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        cwd=str(ROOT),
        env=env,
    )
    assert res.returncode == 0
    data = json.loads(res.stdout)
    assert data["dry_run"] is True
    assert data["lang"] == "de"
    assert data["locale"] == "de_DE.UTF-8"
    assert not (tmp_path / "plasma-localerc").exists()
    assert not (tmp_path / "locale.conf").exists()


def test_language_set_applies_and_updates_status(hscl_bin: Path, tmp_path: Path):
    env = os.environ.copy()
    env["HSCL_CONFIG_DIR"] = str(tmp_path)
    res = subprocess.run(
        [str(hscl_bin), "--json", "language", "set", "fr"],
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        cwd=str(ROOT),
        env=env,
    )
    assert res.returncode == 0
    data = json.loads(res.stdout)
    assert data["applied"] == "fr"
    assert data["locale"] == "fr_FR.UTF-8"
    assert len(data["files_written"]) == 2

    p_path = tmp_path / "plasma-localerc"
    l_path = tmp_path / "locale.conf"
    assert p_path.is_file()
    assert l_path.is_file()

    p_content = p_path.read_text(encoding="utf-8")
    assert "LANG=fr_FR.UTF-8" in p_content
    assert "LANGUAGE=fr_FR:fr:en_US" in p_content

    # Now verify that `hscl language status` detects "fr"
    res_st = subprocess.run(
        [str(hscl_bin), "--json", "language", "status"],
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        cwd=str(ROOT),
        env=env,
    )
    assert res_st.returncode == 0
    st_data = json.loads(res_st.stdout)
    assert st_data["current"] == "fr"
    assert st_data["current_name"] == "Français"
    assert st_data["plasma_localerc_exists"] is True


def test_language_set_invalid(hscl_bin: Path, tmp_path: Path):
    env = os.environ.copy()
    env["HSCL_CONFIG_DIR"] = str(tmp_path)
    res = subprocess.run(
        [str(hscl_bin), "language", "set", "es"],
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        cwd=str(ROOT),
        env=env,
    )
    assert res.returncode != 0
    assert "unsupported language 'es'" in res.stderr
