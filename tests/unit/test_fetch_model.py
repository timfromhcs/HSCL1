"""Plan L, Task L1: model fetcher verifies SHA-256 against the host's published digest and stays inside the allowed root."""
import hashlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "local_worker"))
import fetch_model  # noqa: E402

DATA = b"gguf-bytes-" * 1000
SHA = hashlib.sha256(DATA).hexdigest()


def api_ok(url):
    assert url == "https://huggingface.co/api/models/prism-ml/x-gguf/tree/main"
    return [
        {"type": "file", "path": "README.md", "size": 10},
        {"type": "file", "path": "m.gguf", "size": len(DATA), "lfs": {"oid": SHA, "size": len(DATA)}},
    ]


def chunks(data, start=0, step=700):
    def fn(url, start_byte):
        assert url == "https://huggingface.co/prism-ml/x-gguf/resolve/main/m.gguf"
        rest = data[start_byte:]
        return iter([rest[i : i + step] for i in range(0, len(rest), step)])

    return fn


def test_expected_sha256_reads_lfs_oid():
    assert fetch_model.expected_sha256("prism-ml/x-gguf", "m.gguf", api_get=api_ok) == SHA


def test_expected_sha256_refuses_a_file_without_lfs_digest():
    with pytest.raises(ValueError, match="digest"):
        fetch_model.expected_sha256("prism-ml/x-gguf", "README.md", api_get=api_ok)
    with pytest.raises(ValueError, match="not found"):
        fetch_model.expected_sha256("prism-ml/x-gguf", "nope.gguf", api_get=api_ok)


def test_fetch_keeps_a_file_with_matching_hash(tmp_path):
    p = fetch_model.fetch("prism-ml/x-gguf", "m.gguf", tmp_path, allowed_root=tmp_path, api_get=api_ok, download=chunks(DATA))
    assert p == tmp_path / "m.gguf" and p.read_bytes() == DATA
    assert not (tmp_path / "m.gguf.part").exists()


def test_fetch_deletes_and_raises_on_hash_mismatch(tmp_path):
    with pytest.raises(ValueError, match="sha256 mismatch"):
        fetch_model.fetch("prism-ml/x-gguf", "m.gguf", tmp_path, allowed_root=tmp_path, api_get=api_ok, download=chunks(b"evil" * 2000))
    assert not (tmp_path / "m.gguf").exists() and not (tmp_path / "m.gguf.part").exists()


def test_existing_verified_file_is_not_downloaded_again(tmp_path):
    (tmp_path / "m.gguf").write_bytes(DATA)

    def boom(url, start):
        raise AssertionError("must not download")

    assert fetch_model.fetch("prism-ml/x-gguf", "m.gguf", tmp_path, allowed_root=tmp_path, api_get=api_ok, download=boom).read_bytes() == DATA


def test_partial_download_resumes_from_the_part_file(tmp_path):
    (tmp_path / "m.gguf.part").write_bytes(DATA[:3000])
    starts = []
    inner = chunks(DATA)

    def spy(url, start):
        starts.append(start)
        return inner(url, start)

    fetch_model.fetch("prism-ml/x-gguf", "m.gguf", tmp_path, allowed_root=tmp_path, api_get=api_ok, download=spy)
    assert starts == [3000] and (tmp_path / "m.gguf").read_bytes() == DATA


def test_destination_outside_the_allowed_root_is_refused(tmp_path):
    with pytest.raises(ValueError, match="allowed root"):
        fetch_model.fetch("prism-ml/x-gguf", "m.gguf", tmp_path / "other", allowed_root=tmp_path / "models", api_get=api_ok, download=chunks(DATA))


@pytest.mark.parametrize("name", ["../m.gguf", "a/b.gguf", "m.gguf.exe", "m gguf", ""])
def test_bad_file_names_are_refused(tmp_path, name):
    with pytest.raises(ValueError, match="file name"):
        fetch_model.fetch("prism-ml/x-gguf", name, tmp_path, allowed_root=tmp_path, api_get=api_ok, download=chunks(DATA))


@pytest.mark.parametrize("repo", ["", "a", "a/b/c", "../x", "a/b;rm", "https://x/y"])
def test_bad_repo_ids_are_refused(tmp_path, repo):
    with pytest.raises(ValueError, match="repo"):
        fetch_model.fetch(repo, "m.gguf", tmp_path, allowed_root=tmp_path, api_get=api_ok, download=chunks(DATA))
