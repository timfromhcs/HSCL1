"""Measurement tool: sample Windows performance counters (typeperf CSV) for CPU, GPU engines, GPU memory and free RAM, and summarise.
The pure parsing/summary logic is tested with fixtures; one integration test runs the real typeperf on Windows."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "local_worker"))
import sysmon  # noqa: E402

HEADER = (
    '"(PDH-CSV 4.0)",'
    '"\\\\HOST\\GPU Engine(pid_123_luid_0x0_0x0000_phys_0_eng_0_engtype_3D)\\Utilization Percentage",'
    '"\\\\HOST\\GPU Engine(pid_123_luid_0x0_0x0000_phys_0_eng_1_engtype_Compute_0)\\Utilization Percentage",'
    '"\\\\HOST\\GPU Engine(pid_123_luid_0x0_0x0000_phys_0_eng_2_engtype_Compute_0)\\Utilization Percentage",'
    '"\\\\HOST\\GPU Process Memory(pid_123_luid_0x0_0x0000_phys_0)\\Shared Usage",'
    '"\\\\HOST\\GPU Process Memory(pid_123_luid_0x0_0x0000_phys_0)\\Local Usage",'
    '"\\\\HOST\\Processor Information(_Total)\\% Processor Utility",'
    '"\\\\HOST\\Memory\\Available MBytes"'
)
MB = 1048576


def row(ts, v3d, c1, c2, shared_mb, local_mb, cpu, avail):
    f = lambda x: '" "' if x is None else f'"{x}"'  # noqa: E731
    return f'"{ts}",{f(v3d)},{f(c1)},{f(c2)},{f(None if shared_mb is None else shared_mb * MB)},{f(None if local_mb is None else local_mb * MB)},{f(cpu)},{f(avail)}'


CSV = "\n".join(
    [
        HEADER,
        row("11/07/2026 00:50:01.000", 10, 30, 20, 2600, 25, 40.0, 8000),
        row("11/07/2026 00:50:02.000", 12, 50, 10, 2650, 26, 60.0, 7900),
        row("11/07/2026 00:50:03.000", None, 70, 0, 2700, 25, 80.0, 7800),
        row("11/07/2026 00:50:04.000", 11, 40, 40, 2700, 25, 100.0, 7700),
    ]
)


def test_parse_strips_the_host_and_keeps_blank_values_as_none():
    p = sysmon.parse_typeperf_csv(CSV)
    assert len(p["rows"]) == 4 and len(p["columns"]) == 7
    assert p["columns"][0].startswith("\\GPU Engine(pid_123") and "HOST" not in p["columns"][0]
    assert p["rows"][2]["values"][0] is None
    assert p["rows"][0]["values"][3] == 2600 * MB


def test_parse_ignores_the_trailing_status_lines_of_typeperf():
    text = CSV + '\n\nExiting, please wait...\nThe command completed successfully.\n'
    assert len(sysmon.parse_typeperf_csv(text)["rows"]) == 4


def test_gpu_engines_are_grouped_by_engine_type_and_summed_per_sample():
    s = sysmon.summarize(sysmon.parse_typeperf_csv(CSV))
    comp = s["gpu_engine_utilization"]["Compute_0"]
    # per sample: 30+20, 50+10, 70+0, 40+40 -> 50, 60, 70, 80
    assert comp["median"] == 65 and comp["max"] == 80 and comp["mean"] == 65
    d3 = s["gpu_engine_utilization"]["3D"]
    assert d3["max"] == 12 and d3["samples"] == 3, "a blank sample is skipped, not counted as zero"


def test_cpu_ram_and_gpu_memory_are_summarised_in_mb():
    s = sysmon.summarize(sysmon.parse_typeperf_csv(CSV))
    assert s["cpu_utility"]["median"] == 70 and s["cpu_utility"]["max"] == 100
    assert s["ram_available_mb"]["min"] == 7700 and s["ram_available_mb"]["median"] == 7850
    assert s["gpu_memory_mb"]["shared"]["max"] == 2700 and s["gpu_memory_mb"]["local"]["max"] == 26
    assert s["samples"] == 4 and s["duration_s"] == 3.0


def test_percentile_uses_nearest_rank():
    assert sysmon.stats([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])["p95"] == 10
    assert sysmon.stats([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])["median"] == 5.5
    assert sysmon.stats([])["samples"] == 0


def test_counter_list_is_built_for_one_pid_and_rejects_non_integers():
    c = sysmon.counters_for_pid(4242)
    assert "\\GPU Engine(pid_4242*)\\Utilization Percentage" in c
    assert "\\GPU Process Memory(pid_4242*)\\Shared Usage" in c
    assert "\\Memory\\Available MBytes" in c and "\\Processor Information(_Total)\\% Processor Utility" in c
    for bad in ("4242", "1;calc", -1, True, None):
        with pytest.raises(ValueError):
            sysmon.counters_for_pid(bad)


def test_balance_reports_how_evenly_cpu_and_gpu_are_loaded():
    s = sysmon.summarize(sysmon.parse_typeperf_csv(CSV))
    b = sysmon.balance(s)
    # cpu median 70 %, busiest gpu engine median 65 % -> ratio 65/70
    assert b["cpu_median"] == 70 and b["gpu_median"] == 65
    assert b["ratio_min_over_max"] == pytest.approx(65 / 70, abs=0.01)
    assert sysmon.balance({"cpu_utility": {"median": 0}, "gpu_engine_utilization": {}})["ratio_min_over_max"] == 0.0


@pytest.mark.skipif(not sys.platform.startswith("win"), reason="typeperf exists on Windows only")
def test_real_typeperf_sampling_of_cpu_and_memory_works(tmp_path):
    out = sysmon.sample_system(seconds=3)
    assert out["samples"] >= 2 and out["cpu_utility"]["samples"] >= 2
    assert out["ram_available_mb"]["min"] > 100


# ---- localized Windows (the owner's machine is German: "\Memory\Available MBytes" does not exist there) ----

EN = {"Memory": 4, "Available MBytes": 24, "Processor Information": 1500, "% Processor Utility": 1501}
LOCAL = {4: "Arbeitsspeicher", 24: "Verfügbare MB", 1500: "Prozessorinformationen", 1501: "% Prozessorauslastung"}


def test_counter_paths_are_translated_to_the_local_language_by_index():
    assert sysmon.localize_counter(r"\Memory\Available MBytes", EN, LOCAL) == "\Arbeitsspeicher\Verfügbare MB"
    assert sysmon.localize_counter(r"\Processor Information(_Total)\% Processor Utility", EN, LOCAL) == "\Prozessorinformationen(_Total)\% Prozessorauslastung"


def test_instance_names_gpu_counters_and_unknown_names_stay_untouched():
    gpu = r"\GPU Engine(pid_42*)\Utilization Percentage"
    assert sysmon.localize_counter(gpu, EN, LOCAL) == gpu  # GPU counters are not localized on Windows
    assert sysmon.localize_counter(r"\Memory\Something New", EN, LOCAL) == "\Arbeitsspeicher\Something New"
    assert sysmon.localize_counter("not a counter path", EN, LOCAL) == "not a counter path"


def test_an_english_system_maps_every_name_to_itself():
    same = {i: n for n, i in EN.items()}
    assert sysmon.localize_counter(r"\Memory\Available MBytes", EN, same) == r"\Memory\Available MBytes"


@pytest.mark.skipif(not sys.platform.startswith("win"), reason="Perflib registry data exists on Windows only")
def test_real_perflib_tables_contain_the_names_the_monitor_needs():
    en, local = sysmon.perflib_tables()
    for name in ("Memory", "Available MBytes", "Processor Information", "% Processor Utility"):
        assert name in en, name
        assert en[name] in local


def test_localized_column_names_are_mapped_back_to_english_for_the_summary():
    local_path = "\Prozessorinformationen(_Total)\% Prozessorauslastung"
    assert sysmon.delocalize_counter(local_path, EN, LOCAL) == r"\Processor Information(_Total)\% Processor Utility"
    assert sysmon.delocalize_counter("\Arbeitsspeicher\Verfügbare MB", EN, LOCAL) == r"\Memory\Available MBytes"
    gpu = r"\GPU Engine(pid_1_engtype_3D)\Utilization Percentage"
    assert sysmon.delocalize_counter(gpu, EN, LOCAL) == gpu


def test_delocalize_resolves_a_shared_local_name_to_the_index_with_an_english_twin():
    """On the real German system 1081 of 4774 localised counter names belong to more than one index; 'Verfuegbare MB' is
    index 1382 (Memory, has an English twin) and 1824 (no English name). The last one must not win the reverse lookup."""
    en = {"Memory": 4, "Something Else": 900, "Available MBytes": 1382}
    local = {4: "Arbeitsspeicher", 900: "Etwas anderes", 1382: "Verfügbare MB", 1824: "Verfügbare MB"}
    assert sysmon.delocalize_counter("\\Arbeitsspeicher\\Verfügbare MB", en, local) == r"\Memory\Available MBytes"


def test_localize_prefers_a_counter_index_that_has_a_local_twin():
    """The symmetric direction: an English counter name whose index has no local name must stay English instead of being
    translated with the wrong entry (the object name is still translated)."""
    en = {"Memory": 4, "Available MBytes": 1824}
    local = {4: "Arbeitsspeicher", 1382: "Verfügbare MB"}
    assert sysmon.localize_counter("\\Memory\\Available MBytes", en, local) == "\\Arbeitsspeicher\\Available MBytes"


@pytest.mark.skipif(not sys.platform.startswith("win"), reason="Perflib registry data exists on Windows only")
def test_real_perflib_round_trip_resolves_the_memory_counter():
    en, local = sysmon.perflib_tables()
    sent = sysmon.localize_counter("\\Memory\\Available MBytes", en, local)
    assert sysmon.delocalize_counter(sent, en, local) == "\\Memory\\Available MBytes"


def test_summary_works_on_a_german_header_after_delocalizing():
    german = CSV.replace("Processor Information", "Prozessorinformationen").replace("% Processor Utility", "% Prozessorauslastung").replace(r"\Memory\Available MBytes", "\\Arbeitsspeicher\\Verfügbare MB")
    parsed = sysmon.parse_typeperf_csv(german)
    parsed["columns"] = [sysmon.delocalize_counter(c, EN, LOCAL) for c in parsed["columns"]]
    s = sysmon.summarize(parsed)
    assert s["cpu_utility"]["median"] == 70 and s["ram_available_mb"]["min"] == 7700
