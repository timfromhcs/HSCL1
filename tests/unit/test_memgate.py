"""Plan L, Task L2: free-RAM gate before starting a local model."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "local_worker"))
import memgate  # noqa: E402


def test_allows_when_free_covers_model_kv_and_reserve():
    assert memgate.can_start(model_mb=3000, kv_mb=500, free_mb=6500) is True  # exactly model + kv + 3000


def test_refuses_one_megabyte_below_the_limit():
    assert memgate.can_start(model_mb=3000, kv_mb=500, free_mb=6499) is False


def test_reserve_is_configurable():
    assert memgate.can_start(model_mb=1000, kv_mb=0, free_mb=1500, reserve_mb=500) is True
    assert memgate.can_start(model_mb=1000, kv_mb=0, free_mb=1499, reserve_mb=500) is False


@pytest.mark.parametrize("bad", [(-1, 0, 100), (100, -1, 100), (100, 0, -1)])
def test_negative_inputs_are_rejected(bad):
    with pytest.raises(ValueError):
        memgate.can_start(*bad)


def test_decide_reports_why():
    d = memgate.decide(model_mb=9000, kv_mb=800, free_mb=8000)
    assert d["ok"] is False and d["needed_mb"] == 12800 and d["free_mb"] == 8000 and "short by 4800" in d["reason"]
    assert memgate.decide(model_mb=100, kv_mb=0, free_mb=10000)["ok"] is True


def test_parse_meminfo_available_kib():
    text = "MemTotal: 20000000 kB\nMemFree: 1000 kB\nMemAvailable: 8388608 kB\n"
    assert memgate.parse_meminfo(text) == 8192


def test_parse_meminfo_without_available_raises():
    with pytest.raises(ValueError):
        memgate.parse_meminfo("MemTotal: 1 kB\n")


def test_free_mb_returns_a_plausible_number_on_this_machine():
    v = memgate.free_mb()
    assert isinstance(v, int) and 100 < v < 4_000_000
