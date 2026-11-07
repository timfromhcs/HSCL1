#!/usr/bin/env python3
"""Generate dequantisation fixtures for hcsuda-io from the official `gguf` package.

The blocks are synthetic (seeded random bytes with valid half-float scales), so no
model weights are copied into the repository. The expected values come from
`gguf.quants.dequantize`, an implementation independent of the Rust code under test.

    python -m venv venv && venv/bin/pip install gguf numpy
    venv/bin/python hcsuda/tools/gen_dequant_fixtures.py hcsuda/crates/hcsuda-io/tests/fixtures
"""
import sys
from pathlib import Path

import numpy as np
from gguf import GGMLQuantizationType as T
from gguf.quants import dequantize

# type -> (block bytes, elements per block, [(byte offset of an f16 scale)])
SPEC = {
    "q8_0": (T.Q8_0, 34, 32, [0]),
    "q4_0": (T.Q4_0, 18, 32, [0]),
    "q4_k": (T.Q4_K, 144, 256, [0, 2]),
    "q6_k": (T.Q6_K, 210, 256, [208]),
}
BLOCKS = 6


def main(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(20261107)
    for name, (ty, bsize, nelem, scales) in SPEC.items():
        raw = rng.integers(0, 256, size=(BLOCKS, bsize), dtype=np.uint8)
        for b in range(BLOCKS):
            for off in scales:
                val = np.float16(rng.uniform(0.002, 0.05)).view(np.uint16)
                raw[b, off : off + 2] = np.frombuffer(val.tobytes(), dtype=np.uint8)
        expected = dequantize(raw.reshape(-1), ty).astype("<f4").reshape(-1)
        assert expected.size == BLOCKS * nelem and np.isfinite(expected).all()
        (out / f"{name}.bin").write_bytes(raw.tobytes())
        (out / f"{name}.f32").write_bytes(expected.tobytes())
        print(name, raw.size, "bytes ->", expected.size, "floats")

    # f16 / bf16 / f32 pass-through fixtures
    vals = (rng.standard_normal(64) * 3).astype("<f4")
    (out / "f32.bin").write_bytes(vals.tobytes())
    (out / "f32.f32").write_bytes(vals.tobytes())
    h = vals.astype("<f2")
    (out / "f16.bin").write_bytes(h.tobytes())
    (out / "f16.f32").write_bytes(h.astype("<f4").tobytes())
    bf_bits = (vals.view("<u4") >> 16).astype("<u2")
    (out / "bf16.bin").write_bytes(bf_bits.tobytes())
    bf_f32 = (bf_bits.astype("<u4") << 16).view("<f4")
    (out / "bf16.f32").write_bytes(bf_f32.tobytes())
    print("f32/f16/bf16 written")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
