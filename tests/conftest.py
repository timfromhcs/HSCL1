"""Make `tests/` helper modules importable from every test module (there is no tests/__init__.py)."""

from __future__ import annotations

import sys
from pathlib import Path

_TESTS = Path(__file__).resolve().parent
if str(_TESTS) not in sys.path:
    sys.path.insert(0, str(_TESTS))


# Files whose tests each take seconds (subprocess builds, benchmark runs, VM stress harness). Measured 2026-11-07: together about 220 s of a
# 463 s suite. `forge check` skips them by default (-m "not slow"); `forge check --full` and CI run everything.
SLOW_FILES = {"test_local_bench.py", "test_release_split_join.py", "test_stress_vm.py", "test_pkg_cqhecs.py"}


def pytest_collection_modifyitems(items):
    import pytest

    for item in items:
        if Path(str(item.fspath)).name in SLOW_FILES:
            item.add_marker(pytest.mark.slow)
