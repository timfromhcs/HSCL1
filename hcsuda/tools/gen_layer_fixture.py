#!/usr/bin/env python3
"""Fixture for the Qwen3-style decoder layer: GQA, QK-norm, GGUF [out, in] weight layout.

Independent NumPy implementation (whole-tensor operations) of the layer that
`hcsuda_core::transformer::layer_forward` implements.

    python hcsuda/tools/gen_layer_fixture.py hcsuda/crates/hcsuda-core/tests/fixtures/layer
"""
import sys
from pathlib import Path

import numpy as np

T, DIM, QH, KVH, HD, FFN = 5, 32, 4, 2, 16, 48
EPS, BASE = 1e-6, 5_000_000.0
GROUP = QH // KVH


def rms(x, g):
    return x / np.sqrt((x * x).mean(axis=-1, keepdims=True) + EPS) * g


def rope(x):  # [T, heads, HD], split-half pairs (i, i + HD/2)
    half = HD // 2
    pos = np.arange(T, dtype=np.float64)[:, None]
    inv = BASE ** (-2.0 * np.arange(half, dtype=np.float64) / HD)
    ang = pos * inv[None, :]
    c = np.cos(ang).astype(np.float32)[:, None, :]
    s = np.sin(ang).astype(np.float32)[:, None, :]
    a, b = x[..., :half], x[..., half:]
    return np.concatenate([a * c - b * s, a * s + b * c], axis=-1)


def forward(p):
    x = p["x"]
    h = rms(x, p["attn_norm"])
    # GGUF layout: weight is [out, in]; y = x @ W.T
    q = (h @ p["wq"].T).reshape(T, QH, HD)
    k = (h @ p["wk"].T).reshape(T, KVH, HD)
    v = (h @ p["wv"].T).reshape(T, KVH, HD)
    q, k = rms(q, p["q_norm"]), rms(k, p["k_norm"])
    q, k = rope(q), rope(k)
    mask = np.triu(np.full((T, T), -np.inf, dtype=np.float32), k=1)
    ctx = np.zeros((T, QH, HD), dtype=np.float32)
    for hh in range(QH):
        kv = hh // GROUP
        sc = q[:, hh] @ k[:, kv].T / np.float32(np.sqrt(HD)) + mask
        sc = sc - sc.max(axis=-1, keepdims=True)
        w = np.exp(sc)
        w = w / w.sum(axis=-1, keepdims=True)
        ctx[:, hh] = w @ v[:, kv]
    x1 = x + ctx.reshape(T, QH * HD) @ p["wo"].T
    h2 = rms(x1, p["ffn_norm"])
    gate, up = h2 @ p["wg"].T, h2 @ p["wu"].T
    act = gate / (1.0 + np.exp(-gate)) * up
    return (x1 + act @ p["wd"].T).astype(np.float32)


def main(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(20261108)

    def mat(o, i):  # [out, in]
        return (rng.standard_normal((o, i)) * 0.2).astype(np.float32)

    p = {
        "x": rng.standard_normal((T, DIM)).astype(np.float32),
        "attn_norm": (1.0 + 0.1 * rng.standard_normal(DIM)).astype(np.float32),
        "ffn_norm": (1.0 + 0.1 * rng.standard_normal(DIM)).astype(np.float32),
        "q_norm": (1.0 + 0.1 * rng.standard_normal(HD)).astype(np.float32),
        "k_norm": (1.0 + 0.1 * rng.standard_normal(HD)).astype(np.float32),
        "wq": mat(QH * HD, DIM), "wk": mat(KVH * HD, DIM), "wv": mat(KVH * HD, DIM),
        "wo": mat(DIM, QH * HD),
        "wg": mat(FFN, DIM), "wu": mat(FFN, DIM), "wd": mat(DIM, FFN),
    }
    y = forward(p)
    assert np.isfinite(y).all()
    for name, arr in {**p, "out": y}.items():
        (out / f"{name}.f32").write_bytes(np.ascontiguousarray(arr, dtype="<f4").tobytes())
    print("wrote", len(p) + 1, "files; out[0,:4] =", y[0, :4])


if __name__ == "__main__":
    main(Path(sys.argv[1]))
