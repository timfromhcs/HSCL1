"""Plan L, Task L4: loopback-only gateway client with thinking off, one retry on empty output, clear error codes."""
import json
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "local_worker"))
import gateway  # noqa: E402


def reply(content, finish="stop"):
    return {"choices": [{"message": {"content": content}, "finish_reason": finish}]}


class FakePost:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, url, payload, headers, timeout):
        self.calls.append((url, payload, headers))
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


MSGS = [{"role": "system", "content": "be brief"}, {"role": "user", "content": "write code"}]


@pytest.mark.parametrize(
    "url",
    ["http://192.168.1.2:8090/v1", "https://127.0.0.1:8090/v1", "http://127.0.0.1.evil.com/v1", "http://example.com/v1", "ftp://127.0.0.1/v1", "http://user@127.0.0.1@evil.com/v1"],
)
def test_only_plain_loopback_urls_are_accepted(url):
    with pytest.raises(ValueError, match="loopback"):
        gateway.chat(MSGS, "qwen3-4b", base_url=url, post=FakePost(reply("x")))


@pytest.mark.parametrize("url", ["http://127.0.0.1:8090/v1", "http://localhost:8090/v1", "http://[::1]:8090/v1"])
def test_loopback_urls_are_accepted(url):
    assert gateway.chat(MSGS, "qwen3-4b", base_url=url, post=FakePost(reply("ok"))) == "ok"


def test_payload_turns_thinking_off_without_mutating_the_callers_messages():
    post = FakePost(reply("ok"))
    gateway.chat(MSGS, "qwen3-4b", max_tokens=300, temperature=0.1, post=post, env={})
    url, payload, headers = post.calls[0]
    assert url == "http://127.0.0.1:8090/v1/chat/completions"
    assert payload["model"] == "qwen3-4b" and payload["max_tokens"] == 300 and payload["temperature"] == 0.1
    assert payload["chat_template_kwargs"] == {"enable_thinking": False}
    assert payload["messages"][-1]["content"].endswith("/no_think")
    assert MSGS[-1]["content"] == "write code"  # caller's list untouched
    assert "Authorization" not in headers


def test_api_key_comes_only_from_the_environment():
    post = FakePost(reply("ok"))
    gateway.chat(MSGS, "m", post=post, env={"LOCAL_AI_KEY": "k123"})
    assert post.calls[0][2]["Authorization"] == "Bearer k123"


def test_empty_content_cut_by_length_is_retried_once_with_a_bigger_budget():
    post = FakePost(reply("", "length"), reply("code"))
    assert gateway.chat(MSGS, "m", max_tokens=200, post=post, env={}) == "code"
    assert post.calls[1][1]["max_tokens"] == 400


def test_empty_after_retry_raises_with_code_empty():
    with pytest.raises(gateway.GatewayError) as e:
        gateway.chat(MSGS, "m", post=FakePost(reply(""), reply("   ")), env={})
    assert e.value.code == "empty"


def test_think_blocks_are_stripped_and_unclosed_think_counts_as_empty():
    assert gateway.chat(MSGS, "m", post=FakePost(reply("<think>hmm</think>\nanswer")), env={}) == "answer"
    with pytest.raises(gateway.GatewayError) as e:
        gateway.chat(MSGS, "m", post=FakePost(reply("<think>never closed"), reply("<think>still")), env={})
    assert e.value.code == "empty"


def test_http_errors_and_unreachable_server_have_stable_codes():
    with pytest.raises(gateway.GatewayError) as e:
        gateway.chat(MSGS, "m", post=FakePost(gateway.GatewayError("http_500", "boom")), env={})
    assert e.value.code == "http_500"
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()  # nothing listens on this port any more
    with pytest.raises(gateway.GatewayError) as e:
        gateway.chat(MSGS, "m", base_url=f"http://127.0.0.1:{port}/v1", env={}, timeout=2)
    assert e.value.code == "unavailable"


def test_round_trip_against_a_real_loopback_server():
    seen = {}

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            seen["body"] = body
            data = json.dumps(reply("hello from stub")).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        out = gateway.chat(MSGS, "qwen3-4b", base_url=f"http://127.0.0.1:{srv.server_port}/v1", env={}, timeout=5)
    finally:
        srv.shutdown()
    assert out == "hello from stub" and seen["body"]["model"] == "qwen3-4b"
