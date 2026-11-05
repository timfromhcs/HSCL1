"""Release assembly refuses unverified or placeholder-bearing input."""
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import make_release as mr  # noqa: E402
import write_iso_manifest as wim  # noqa: E402


def sha(b):
    return hashlib.sha256(b).hexdigest()


@pytest.fixture()
def arts(tmp_path):
    iso = tmp_path / "x.iso"
    iso.write_bytes(b"iso-bytes")
    img = tmp_path / "x.qcow2"
    img.write_bytes(b"img-bytes")
    iso_m = wim.build(iso, "0.1.0", False, "b" * 64, "c" * 40, False)
    (tmp_path / "x.iso.manifest.json").write_text(json.dumps(iso_m))
    pre = {"image_sha256": sha(b"img-bytes"), "image_bytes": 9, "virtual_bytes": 40 << 30, "credential_scan": "clean", "first_boot": "OEM user setup"}
    (tmp_path / "x.qcow2.manifest.json").write_text(json.dumps(pre))
    ev = tmp_path / "evidence.png"
    ev.write_bytes(b"png")
    return tmp_path, iso, img, ev


def build(arts, **kw):
    tmp, iso, img, ev = arts
    return mr.build_release("0.1.0", iso, img, tmp / "out", {"boot": ev})


def test_happy_path_writes_sums_manifest_notes(arts):
    files = build(arts)
    names = {f.name for f in files}
    assert {"SHA256SUMS", "build-manifest.json", "release-notes.md"} <= names
    sums = (arts[0] / "out/SHA256SUMS").read_text()
    assert sha(b"iso-bytes") in sums and sha(b"img-bytes") in sums
    m = json.loads((arts[0] / "out/build-manifest.json").read_text())
    assert m["signed"] is False and m["published"] is False


def test_iso_without_workshop_attestation_is_refused(arts):
    tmp = arts[0]
    m = json.loads((tmp / "x.iso.manifest.json").read_text())
    m["workshop_default"] = "enabled"
    (tmp / "x.iso.manifest.json").write_text(json.dumps(m))
    with pytest.raises(mr.ReleaseError, match="Workshop"):
        build(arts)


def test_dirty_tree_is_refused(arts):
    tmp = arts[0]
    m = json.loads((tmp / "x.iso.manifest.json").read_text())
    m["git_dirty"] = True
    (tmp / "x.iso.manifest.json").write_text(json.dumps(m))
    with pytest.raises(mr.ReleaseError, match="dirty"):
        build(arts)


def test_unclean_credential_scan_is_refused(arts):
    tmp = arts[0]
    m = json.loads((tmp / "x.qcow2.manifest.json").read_text())
    m["credential_scan"] = "not run"
    (tmp / "x.qcow2.manifest.json").write_text(json.dumps(m))
    with pytest.raises(mr.ReleaseError, match="credential scan"):
        build(arts)


def test_hash_mismatch_is_refused(arts):
    arts[1].write_bytes(b"tampered")
    with pytest.raises(mr.ReleaseError, match="ISO hash"):
        build(arts)


def test_missing_evidence_is_refused(arts):
    arts[3].unlink()
    with pytest.raises(mr.ReleaseError, match="evidence"):
        build(arts)


def test_placeholders_are_detected():
    with pytest.raises(mr.ReleaseError):
        mr.check_no_placeholders('{"sha256": "GENERATE_FROM_FINAL_ARTIFACT"}', "x")
