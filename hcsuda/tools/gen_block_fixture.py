#!/usr/bin/env python3
"""Fixture for the tiny transformer block: seeded random weights + NumPy forward pass.

The NumPy code below is written independently of the Rust reference it checks
(different language, different loop structure, whole-tensor operations).

    python hcsuda/tools/gen_block_fixture.py hcsuda/crates/hcsuda-core/tests/fixtures/block
"""
import sys
from pathlib import Path

import numpy as np

T, D, HEADS, FFN = 6, 32, 4, 64
EPS, ROPE_BASE = 1e-5, 10000.0
HD = D // HEADS


def rmsnorm(x, g):
    ms = (x * x).mean(axis=-1, keepdims=True)
    return x / np.sqrt(ms + EPS) * g


def rope(x):  # x: [T, HD], split-half layout, positions 0..T-1
    half = HD // 2
    pos = np.arange(T, dtype=np.float64)[:, None]
    inv = ROPE_BASE ** (-2.0 * np.arange(half, dtype=np.float64) / HD)
    ang = pos * inv[None, :]
    c, s = np.cos(ang).astype(np.float32), np.sin(ang).astype(np.float32)
    a, b = x[:, :half], x[:, half:]
    return np.concatenate([a * c - b * s, a * s + b * c], axis=1)


def forward(p):
    x = p["x"]
    h = rmsnorm(x, p["g1"])
    q, k, v = h @ p["wq"], h @ p["wk"], h @ p["wv"]
    ctx = np.zeros_like(q)
    mask = np.triu(np.full((T, T), -np.inf, dtype=np.float32), k=1)
    for hh in range(HEADS):
        sl = slice(hh * HD, (hh + 1) * HD)
        qh, kh = rope(q[:, sl]), rope(k[:, sl])
        scores = qh @ kh.T / np.float32(np.sqrt(HD)) + mask
        scores = scores - scores.max(axis=-1, keepdims=True)
        w = np.exp(scores)
        w = w / w.sum(axis=-1, keepdims=True)
        ctx[:, sl] = w @ v[:, sl]
    x1 = x + ctx @ p["wo"]
    h2 = rmsnorm(x1, p["g2"])
    gate, up = h2 @ p["wg"], h2 @ p["wu"]
    act = gate / (1.0 + np.exp(-gate)) * up
    return (x1 + act @ p["wd"]).astype(np.float32)


def main(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(20261107)

    def mat(r, c):
        return (rng.standard_normal((r, c)) * 0.2).astype(np.float32)

    p = {
        "x": (rng.standard_normal((T, D))).astype(np.float32),
        "g1": (1.0 + 0.1 * rng.standard_normal(D)).astype(np.float32),
        "g2": (1.0 + 0.1 * rng.standard_normal(D)).astype(np.float32),
        "wq": mat(D, D), "wk": mat(D, D), "wv": mat(D, D), "wo": mat(D, D),
        "wg": mat(D, FFN), "wu": mat(D, FFN), "wd": mat(FFN, D),
    }
    y = forward(p)
    assert np.isfinite(y).all()
    for name, arr in {**p, "out": y}.items():
        (out / f"{name}.f32").write_bytes(np.ascontiguousarray(arr, dtype="<f4").tobytes())
    print("wrote", len(p) + 1, "files; out[0,:4] =", y[0, :4])


if __name__ == "__main__":
    main(Path(sys.argv[1]))
