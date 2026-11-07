import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

import make_lock  # noqa: E402

REPORT = {
    "install": [
        {"metadata": {"name": "Zeta_Pkg", "version": "2.0"},
         "download_info": {"url": "https://x/zeta-2.0-py3-none-any.whl",
                           "archive_info": {"hashes": {"sha256": "b" * 64}}}},
        {"metadata": {"name": "alpha", "version": "1.0"},
         "download_info": {"url": "https://x/alpha-1.0-cp314-cp314-manylinux_2_28_x86_64.whl",
                           "archive_info": {"hashes": {"sha256": "a" * 64}}}},
    ]
}


def test_lock_is_sorted_pinned_and_hashed():
    text = make_lock.lock_from_report(REPORT)
    lines = [l for l in text.splitlines() if l and not l.startswith("#")]
    assert lines[0].startswith("alpha==1.0")
    assert lines[1].startswith("zeta-pkg==2.0")
    assert f"--hash=sha256:{'a' * 64}" in text and f"--hash=sha256:{'b' * 64}" in text


def test_lock_is_deterministic():
    assert make_lock.lock_from_report(REPORT) == make_lock.lock_from_report(json.loads(json.dumps(REPORT)))


def test_a_package_without_a_sha256_is_an_error_not_an_unhashed_line():
    bad = {"install": [{"metadata": {"name": "p", "version": "1"},
                        "download_info": {"url": "https://x/p.whl", "archive_info": {"hashes": {}}}}]}
    try:
        make_lock.lock_from_report(bad)
    except make_lock.LockError as exc:
        assert "p" in str(exc)
    else:
        raise AssertionError("an unhashed package must not be locked")


def test_a_source_distribution_is_refused():
    sdist = {"install": [{"metadata": {"name": "p", "version": "1"},
                          "download_info": {"url": "https://x/p-1.tar.gz",
                                            "archive_info": {"hashes": {"sha256": "c" * 64}}}}]}
    try:
        make_lock.lock_from_report(sdist)
    except make_lock.LockError as exc:
        assert "wheel" in str(exc)
    else:
        raise AssertionError("only wheels may be locked")
