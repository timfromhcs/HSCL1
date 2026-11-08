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
    pre = {"hscl1_version": "0.1.0", "image_sha256": sha(b"img-bytes"), "image_bytes": 9, "virtual_bytes": 40 << 30, "credential_scan": "clean", "first_boot": "OEM user setup"}
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
    arts[1].write_bytes(b"bad-bytes")
    with pytest.raises(mr.ReleaseError, match="ISO hash"):
        build(arts)


def test_missing_evidence_is_refused(arts):
    arts[3].unlink()
    with pytest.raises(mr.ReleaseError, match="evidence"):
        build(arts)


def test_placeholders_are_detected():
    with pytest.raises(mr.ReleaseError):
        mr.check_no_placeholders('{"sha256": "GENERATE_FROM_FINAL_ARTIFACT"}', "x")


@pytest.mark.parametrize("field,value", [("git_dirty", None), ("git_dirty", 0),
                                         ("qa_image", True), ("iso_bytes", 1),
                                         ("git_commit", "unknown")])
def test_incomplete_or_false_build_attestations_are_refused_before_writing(arts, field, value):
    manifest = arts[0] / "x.iso.manifest.json"
    data = json.loads(manifest.read_text())
    data[field] = value
    manifest.write_text(json.dumps(data))
    with pytest.raises(mr.ReleaseError):
        build(arts)
    assert not (arts[0] / "out").exists()


@pytest.mark.parametrize("version", ["1.0.0", "../escape", "0.1.0/other", "not-a-version"])
def test_version_cannot_relabel_an_old_image_or_escape_output(arts, version):
    with pytest.raises(mr.ReleaseError):
        mr.build_release(version, arts[1], None, arts[0] / "out", {})
    assert not (arts[0] / "out").exists()


def test_stable_requires_a_complete_readiness_report(arts):
    manifest = arts[0] / "x.iso.manifest.json"
    data = json.loads(manifest.read_text())
    data["version"] = "1.0.0"
    manifest.write_text(json.dumps(data))
    with pytest.raises(mr.ReleaseError, match="readiness"):
        mr.build_release("1.0.0", arts[1], None, arts[0] / "out", {})
    assert not (arts[0] / "out").exists()


def test_placeholder_gap_fails_before_any_release_output(arts):
    with pytest.raises(mr.ReleaseError, match="placeholder"):
        mr.build_release("0.1.0", arts[1], None, arts[0] / "out", {}, ["TODO install"])
    assert not (arts[0] / "out").exists()


def test_evidence_must_be_a_nonempty_regular_file(arts):
    with pytest.raises(mr.ReleaseError, match="evidence"):
        mr.build_release("0.1.0", arts[1], None, arts[0] / "out", {"boot": arts[0]})
    assert not (arts[0] / "out").exists()


@pytest.mark.parametrize("timestamp", [True, "yesterday", "2026-02-30T12:00:00Z", "2026-11-08T12:00:00"])
def test_build_timestamp_must_be_valid_utc(arts, timestamp):
    path = arts[0] / "x.iso.manifest.json"
    data = json.loads(path.read_text())
    data["built_utc"] = timestamp
    path.write_text(json.dumps(data))
    with pytest.raises(mr.ReleaseError, match="timestamp"):
        build(arts)
    assert not (arts[0] / "out").exists()


@pytest.mark.parametrize("version", [None, "0.0.1"])
def test_prebuilt_cannot_be_relabelled_from_another_or_unknown_version(arts, version):
    path = arts[0] / "x.qcow2.manifest.json"
    data = json.loads(path.read_text())
    data["hscl1_version"] = version
    path.write_text(json.dumps(data))
    with pytest.raises(mr.ReleaseError, match="prebuilt.*version"):
        build(arts)
    assert not (arts[0] / "out").exists()


def readiness_fixture(arts):
    manifest = arts[0] / "x.iso.manifest.json"
    data = json.loads(manifest.read_text())
    data["version"] = "1.0.0"
    manifest.write_text(json.dumps(data))
    report = {"schema": "hcs.release-readiness.v1", "version": "1.0.0",
              "iso_sha256": data["iso_sha256"], "git_commit": data["git_commit"],
              "reviewer": "test fixture reviewer",
              "gates": {name: {"status": "PASS", "evidence": [
                  {"path": arts[3].name, "sha256": mr.sha256(arts[3])}]}
                  for name in mr.STABLE_GATES}}
    path = arts[0] / "readiness.json"
    path.write_text(json.dumps(report))
    return path, report


@pytest.mark.parametrize("defect", ["missing_gate", "failed", "skipped", "wrong_iso", "wrong_commit",
                                    "no_reviewer", "no_evidence", "changed_evidence", "missing_evidence"])
def test_stable_readiness_refuses_incomplete_failed_or_unbound_evidence(arts, defect):
    path, report = readiness_fixture(arts)
    if defect == "missing_gate":
        del report["gates"]["vm_install"]
    elif defect in ("failed", "skipped"):
        report["gates"]["vm_install"]["status"] = defect.upper()
    elif defect == "wrong_iso":
        report["iso_sha256"] = "0" * 64
    elif defect == "wrong_commit":
        report["git_commit"] = "0" * 40
    elif defect == "no_reviewer":
        report["reviewer"] = " "
    elif defect == "no_evidence":
        report["gates"]["vm_install"]["evidence"] = []
    elif defect == "changed_evidence":
        arts[3].write_bytes(b"changed")
    elif defect == "missing_evidence":
        arts[3].unlink()
    path.write_text(json.dumps(report))
    with pytest.raises(mr.ReleaseError, match="readiness"):
        mr.build_release("1.0.0", arts[1], None, arts[0] / "out", {}, readiness=path)
    assert not (arts[0] / "out").exists()


def test_stable_records_reviewed_artifact_bound_gate_report(arts):
    path, report = readiness_fixture(arts)
    out = arts[0] / "out"
    mr.build_release("1.0.0", arts[1], None, out, {"boot": arts[3]}, readiness=path)
    manifest = json.loads((out / "build-manifest.json").read_text())
    assert manifest["readiness"] == report
    assert manifest["evidence_sha256"]["boot"] == mr.sha256(arts[3])
    assert manifest["published"] is False and manifest["signed"] is False
    with pytest.raises(mr.ReleaseError, match="never overwritten"):
        mr.build_release("1.0.0", arts[1], None, out, {}, readiness=path)


def test_the_disk_image_is_optional_and_says_so(tmp_path):
    """AGENTS.md 7.1: the VM image is optional and must not delay the verified ISO. The set must then
    record its absence instead of silently omitting it - a consumer reading build-manifest.json has
    to be able to tell "no image was built" from "the key was forgotten"."""
    iso = tmp_path / "y.iso"
    iso.write_bytes(b"iso-bytes")
    (tmp_path / "y.iso.manifest.json").write_text(
        json.dumps(wim.build(iso, "0.1.3-alpha.0", False, "b" * 64, "c" * 40, False)))
    out = tmp_path / "rel"
    files = mr.build_release("0.1.3-alpha.0", iso, None, out, {})
    names = sorted(p.name for p in files)
    assert names == ["HSCL1-0.1.3-alpha.0-amd64.iso", "SHA256SUMS", "build-manifest.json", "release-notes.md"]
    sums = (out / "SHA256SUMS").read_text(encoding="utf-8")
    assert sums.count("\n") == 1 and "amd64.iso" in sums
    man = json.loads((out / "build-manifest.json").read_text(encoding="utf-8"))
    assert man["prebuilt"] is None
    assert "optional" in man["prebuilt_note"].lower()
    notes = (out / "release-notes.md").read_text(encoding="utf-8")
    assert "no disk image" in notes.lower()


def test_gaps_are_written_into_the_notes_and_never_invented(tmp_path):
    """A release set must carry its own "not verified" list: that is the difference between an honest
    pre-release and a claim. Gaps come from the caller (they change per release), and an empty gap is
    refused so a blank bullet cannot appear."""
    iso = tmp_path / "z.iso"
    iso.write_bytes(b"iso-bytes")
    (tmp_path / "z.iso.manifest.json").write_text(
        json.dumps(wim.build(iso, "0.1.3-alpha.0", False, "b" * 64, "c" * 40, False)))
    out = tmp_path / "rel"
    gaps = ["firmware acceptance of the Secure Boot chain (gate G6)",
            "an install run on this exact image"]
    mr.build_release("0.1.3-alpha.0", iso, None, out, {}, gaps)
    notes = (out / "release-notes.md").read_text(encoding="utf-8")
    assert "Not verified in this set" in notes
    for g in gaps:
        assert f"- {g}" in notes
    with pytest.raises(mr.ReleaseError):
        mr.build_release("0.1.3-alpha.0", iso, None, out, {}, ["  "])
