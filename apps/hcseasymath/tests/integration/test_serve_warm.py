"""`serve --warm`: same contract over HTTP, measured latency, and no process left behind."""

import json
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from test_serve import BACKEND, call

pytestmark = pytest.mark.skipif(
    not sys.platform.startswith("linux"), reason="gate runs on Linux (WSL/CI)"
)

BODY = {"expression": "x**3 - 3*x**2 + 2*x", "variable": "x"}


def start(*extra):
    env = {"PYTHONPATH": BACKEND, "PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"}
    proc = subprocess.Popen(
        [sys.executable, "-m", "hcseasymath", "serve", "--port", "0", *extra],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, text=True,
    )
    return proc, json.loads(proc.stdout.readline())


def timed_post(info):
    start_t = time.perf_counter()
    status, text, _ = call(info, "/api/v1/symbolic/differentiate", BODY)
    return status, json.loads(text), time.perf_counter() - start_t


def zygotes():
    out = subprocess.run(["pgrep", "-f", "hcseasymath.jobs.zygote"], capture_output=True, text=True).stdout
    return set(out.split())


def test_warm_server_answers_like_the_cold_one_and_is_faster():
    before = zygotes()
    cold, cold_info = start()
    warm, warm_info = start("--warm")
    try:
        timed_post(cold_info)
        timed_post(warm_info)  # first request of each, whatever it costs
        cs, cres, ct = timed_post(cold_info)
        ws, wres, wt = timed_post(warm_info)
        assert cs == ws == 200
        for key in ("status", "result_expression", "run_id", "input_digest", "exactness"):
            assert cres[key] == wres[key]
        print(f"\nlatency through HTTP: cold {ct * 1000:.0f} ms, warm {wt * 1000:.0f} ms")
        assert wt < ct
    finally:
        for p in (cold, warm):
            p.send_signal(signal.SIGINT)
        for p in (cold, warm):
            p.wait(timeout=20)
    time.sleep(0.3)
    assert zygotes() - before == set(), "a zygote outlived the server"


def test_cold_stays_the_default():
    proc, info = start()
    try:
        timed_post(info)
        kids = subprocess.run(["pgrep", "-P", str(proc.pid), "-f", "hcseasymath.jobs.zygote"],
                              capture_output=True, text=True).stdout.split()
        assert kids == [], "the default server must not start a zygote"
        s = subprocess.run([sys.executable, "-m", "hcseasymath", "serve", "--help"],
                           capture_output=True, text=True, env={"PYTHONPATH": BACKEND, "PATH": "/usr/bin:/bin"})
        assert "--warm" in s.stdout
    finally:
        proc.send_signal(signal.SIGINT)
        proc.wait(timeout=20)
