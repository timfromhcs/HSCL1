"""Local API: loopback assumptions, Host/Origin/token checks, status mapping (decision D6)."""

import threading
import time

import pytest
from fastapi.testclient import TestClient

from hcseasymath.api.app import create_app
from hcseasymath.core.engine import execute

TOKEN = "t" * 32
PORT = 8765
BASE = f"http://127.0.0.1:{PORT}"
AUTH = {"Authorization": f"Bearer {TOKEN}"}
BODY = {"expression": "x**3 - 3*x**2 + 2*x", "variable": "x"}
URL = "/api/v1/symbolic/differentiate"


def make(run=execute, **kw):
    app = create_app(token=TOKEN, port=PORT, run=run, **kw)
    return TestClient(app, base_url=BASE)


def test_health_and_capabilities_need_no_token_but_report_real_state():
    c = make()
    h = c.get("/api/v1/health")
    assert h.status_code == 200 and h.json()["status"] == "ok"
    caps = c.get("/api/v1/capabilities").json()
    assert caps["operations"] == ["differentiate"]
    assert caps["engines"]["sympy"]
    assert caps["accelerators"] == {"hcsuda": "not_used"}
    assert caps["limits"]["max_chars"] == 500


def test_a_foreign_host_header_is_rejected_to_stop_dns_rebinding():
    c = make()
    r = c.get("/api/v1/health", headers={"Host": "evil.example:8765"})
    assert r.status_code == 400


@pytest.mark.parametrize("host", ["127.0.0.1:8765", "localhost:8765"])
def test_loopback_names_are_accepted(host):
    assert make().get("/api/v1/health", headers={"Host": host}).status_code == 200


def test_operations_require_the_per_launch_token():
    c = make()
    assert c.post(URL, json=BODY).status_code == 401
    assert c.post(URL, json=BODY, headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert c.post(URL, json=BODY, headers={"Authorization": "Basic abc"}).status_code == 401
    ok = c.post(URL, json=BODY, headers=AUTH)
    assert ok.status_code == 200
    assert ok.json()["result_expression"] == "3*x**2 - 6*x + 2"


def test_a_cross_site_origin_is_refused_even_with_a_valid_token():
    c = make()
    r = c.post(URL, json=BODY, headers={**AUTH, "Origin": "https://evil.example"})
    assert r.status_code == 403
    r = c.post(URL, json=BODY, headers={**AUTH, "Origin": f"http://127.0.0.1:{PORT}"})
    assert r.status_code == 200
    r = c.post(URL, json=BODY, headers={**AUTH, "Origin": "null"})
    assert r.status_code == 403


def test_no_cors_headers_are_ever_sent():
    c = make()
    r = c.options(URL, headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in {k.lower() for k in r.headers}
    r = c.get("/api/v1/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in {k.lower() for k in r.headers}


def test_status_codes_follow_the_result_status():
    c = make()
    bad = c.post(URL, json={"expression": "__import__('os')", "variable": "x"}, headers=AUTH)
    assert bad.status_code == 400 and bad.json()["status"] == "invalid_input"
    lim = c.post(URL, json={"expression": "9**9**9", "variable": "x"}, headers=AUTH)
    assert lim.status_code == 422 and lim.json()["status"] == "resource_limit"


def test_a_failure_never_carries_a_result_expression():
    c = make()
    r = c.post(URL, json={"expression": "x +", "variable": "x"}, headers=AUTH).json()
    assert r["result_expression"] is None


def test_oversized_bodies_are_refused():
    c = make()
    r = c.post(URL, content=b'{"expression": "' + b"x" * 200_000 + b'", "variable": "x"}',
               headers={**AUTH, "Content-Type": "application/json"})
    assert r.status_code == 413


def test_malformed_json_and_wrong_types_are_client_errors():
    c = make()
    assert c.post(URL, content=b"{not json", headers={**AUTH, "Content-Type": "application/json"}).status_code in (400, 422)
    assert c.post(URL, json={"expression": 5, "variable": "x"}, headers=AUTH).status_code == 422


def test_interactive_docs_and_the_schema_are_not_exposed():
    c = make()
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert c.get(path).status_code == 404


def test_concurrency_is_bounded_and_the_excess_gets_429():
    release = threading.Event()

    def slow(request):
        release.wait(5)
        return execute(request)

    c = make(run=slow, max_concurrent=1)
    results = {}

    def first():
        results["first"] = c.post(URL, json=BODY, headers=AUTH).status_code

    t = threading.Thread(target=first)
    t.start()
    time.sleep(0.4)
    assert c.post(URL, json=BODY, headers=AUTH).status_code == 429
    release.set()
    t.join(5)
    assert results["first"] == 200


def test_the_real_isolated_worker_serves_a_request_end_to_end():
    import sys

    if not sys.platform.startswith("linux"):
        pytest.skip("the isolated worker needs Linux resource limits")
    from hcseasymath.jobs.worker import run_isolated

    c = make(run=lambda req: run_isolated(req, timeout_s=30))
    r = c.post(URL, json=BODY, headers=AUTH)
    assert r.status_code == 200 and r.json()["result_expression"] == "3*x**2 - 6*x + 2"
