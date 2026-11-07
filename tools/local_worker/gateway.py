#!/usr/bin/env python3
"""Client for the local OpenAI-compatible gateway (plan L, task L4).

Loopback only (plain http to 127.0.0.1, localhost or ::1; never a proxy), thinking switched off two ways (`/no_think` soft switch
and `chat_template_kwargs.enable_thinking=false`), `<think>` blocks stripped, one retry with a doubled token budget when the answer
comes back empty (the failure measured on 2026-11-06: thinking ate all 400 tokens), stable error codes. The API key, if any, is read
from the environment variable LOCAL_AI_KEY only.
"""
from __future__ import annotations

import copy
import json
import os
import re
import urllib.error
import urllib.request
from typing import Callable, Mapping
from urllib.parse import urlsplit

DEFAULT_URL = "http://127.0.0.1:8090/v1"
LOOPBACK = {"127.0.0.1", "localhost", "::1"}
THINK_RE = re.compile(r"<think>.*?</think>", re.S)


class GatewayError(Exception):
    def __init__(self, code: str, message: str = ""):
        super().__init__(f"{code}: {message}" if message else code)
        self.code = code


def _check_url(url: str) -> str:
    parts = urlsplit(url)
    if parts.scheme != "http" or "@" in parts.netloc or parts.hostname not in LOOPBACK:
        raise ValueError(f"base_url must be plain http to a loopback address, got {url!r}")
    return url.rstrip("/")


def _http_post(url: str, payload: dict, headers: dict, timeout: float) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", **headers}, method="POST")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # never route loopback traffic through a proxy
    try:
        with opener.open(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise GatewayError(f"http_{e.code}", e.reason if isinstance(e.reason, str) else "") from e
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        raise GatewayError("unavailable", str(e)) from e
    except json.JSONDecodeError as e:
        raise GatewayError("bad_response", "not JSON") from e


def _clean(text: str) -> str:
    text = THINK_RE.sub("", text or "")
    if "<think>" in text:  # unclosed: the model never finished thinking
        text = text.split("<think>", 1)[0]
    return text.strip()


def chat(
    messages: list[dict],
    model: str,
    max_tokens: int = 1024,
    temperature: float = 0.2,
    base_url: str = DEFAULT_URL,
    timeout: float = 600,
    post: Callable[[str, dict, dict, float], dict] = _http_post,
    env: Mapping[str, str] | None = None,
) -> str:
    base = _check_url(base_url)
    env = os.environ if env is None else env
    headers = {"Authorization": f"Bearer {env['LOCAL_AI_KEY']}"} if env.get("LOCAL_AI_KEY") else {}
    msgs = copy.deepcopy(messages)
    for m in reversed(msgs):
        if m.get("role") == "user":
            if not m["content"].rstrip().endswith("/no_think"):
                m["content"] = m["content"].rstrip() + "\n/no_think"
            break
    budget = max_tokens
    for attempt in range(2):
        payload = {
            "model": model,
            "messages": msgs,
            "max_tokens": budget,
            "temperature": temperature,
            "chat_template_kwargs": {"enable_thinking": False},
        }
        resp = post(f"{base}/chat/completions", payload, headers, timeout)
        try:
            content = resp["choices"][0]["message"].get("content") or ""
        except (KeyError, IndexError, TypeError, AttributeError) as e:
            raise GatewayError("bad_response", "no choices[0].message") from e
        text = _clean(content)
        if text:
            return text
        budget = max_tokens * 2
    raise GatewayError("empty", "the model returned no usable content after one retry")
