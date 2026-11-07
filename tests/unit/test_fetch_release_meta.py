"""scripts/fetch_release_meta.py: the website's release data must come from the release, cross-checked (plan D5)."""
import io
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import fetch_release_meta as frm  # noqa: E402


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


def fake_urlopen(_url, timeout=30):
    return FakeResponse(b"x")


def release(assets):
    return {
        "draft": False,
        "tag_name": "v9.9.9-alpha.0",
        "name": "HSCL1 9.9.9",
        "prerelease": True,
        "published_at": "2026-11-06T00:00:00Z",
        "html_url": "https://example.invalid/r",
        "assets": assets,
    }


def asset(name, size=1, url=None):
    return {"name": name, "size": size, "browser_download_url": url or f"https://example.invalid/{name}"}


def test_no_releases_means_no_release_block(monkeypatch):
    monkeypatch.setattr(frm, "gh", lambda *a: json.dumps([{"draft": True}]))
    assert frm.build("o/r") == {"repo": "o/r", "release": None}


def test_consistent_release_carries_hash_and_byte_count(monkeypatch):
    monkeypatch.setattr(frm, "gh", lambda *a: json.dumps([release([asset("SHA256SUMS"), asset("x.iso.part000", 10), asset("x.iso.manifest.json")])]))
    monkeypatch.setattr(frm.urllib.request, "urlopen", lambda url, timeout=30: FakeResponse(b"a" * 64 + b"  x.iso\n"))
    monkeypatch.setattr(frm, "get_json", lambda url: {"iso_sha256": "a" * 64, "iso_bytes": 10})
    data = frm.build("o/r")
    whole = data["release"]["whole_image"]
    assert whole == {"name": "x.iso", "sha256": "a" * 64, "bytes": 10}


def test_hash_mismatch_between_sums_and_manifest_is_an_error(monkeypatch):
    monkeypatch.setattr(frm, "gh", lambda *a: json.dumps([release([asset("SHA256SUMS"), asset("x.iso.part000", 10), asset("x.iso.manifest.json")])]))
    monkeypatch.setattr(frm.urllib.request, "urlopen", lambda url, timeout=30: FakeResponse(b"a" * 64 + b"  x.iso\n"))
    monkeypatch.setattr(frm, "get_json", lambda url: {"iso_sha256": "b" * 64, "iso_bytes": 10})
    with pytest.raises(SystemExit) as e:
        frm.build("o/r")
    assert "integrity" in str(e.value)


def test_part_sizes_must_sum_to_the_manifest_size(monkeypatch):
    monkeypatch.setattr(frm, "gh", lambda *a: json.dumps([release([asset("SHA256SUMS"), asset("x.iso.part000", 4), asset("x.iso.manifest.json")])]))
    monkeypatch.setattr(frm.urllib.request, "urlopen", lambda url, timeout=30: FakeResponse(b"a" * 64 + b"  x.iso\n"))
    monkeypatch.setattr(frm, "get_json", lambda url: {"iso_sha256": "a" * 64, "iso_bytes": 10})
    with pytest.raises(SystemExit) as e:
        frm.build("o/r")
    assert "parts sum" in str(e.value)


def test_check_mode_detects_a_stale_file(tmp_path, monkeypatch):
    monkeypatch.setattr(frm, "build", lambda repo: {"repo": repo, "release": None})
    out = tmp_path / "release.json"
    out.write_text('{"stale": true}\n', encoding="utf-8")
    assert frm.main(["--out", str(out), "--check"]) == 1
    out.write_text(json.dumps({"repo": "timfromhcs/HSCL1", "release": None}, indent=2) + "\n", encoding="utf-8")
    assert frm.main(["--out", str(out), "--check"]) == 0
