#!/usr/bin/env python3
"""Generate the original HSCL1 Midnight wallpaper (pure stdlib, deterministic).

Colours come from themes/tokens/tokens.json so the wallpaper follows the design tokens.
Usage: gen-wallpaper.py OUT.png [WIDTH HEIGHT [THEME]]   (THEME defaults to hcs-midnight)
"""
import json, math, struct, sys, zlib, pathlib

def hex_rgb(h):
    h = h.lstrip("#")[:6]
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

def mix(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))

def render(w, h, tok):
    bg0, bg1, acc = hex_rgb(tok["surface-0"]), hex_rgb(tok["surface-2"]), hex_rgb(tok["accent"])
    rows = []
    cx, cy = w * 0.72, h * 0.30      # accent glow
    cx2, cy2 = w * 0.18, h * 0.85    # soft secondary glow
    rmax = math.hypot(w, h) * 0.55
    for y in range(h):
        row = bytearray([0])  # PNG filter type 0
        for x in range(w):
            base = mix(bg0, bg1, y / (h - 1))
            g1 = max(0.0, 1 - math.hypot(x - cx, y - cy) / rmax) ** 2.2 * 0.55
            g2 = max(0.0, 1 - math.hypot(x - cx2, y - cy2) / (rmax * 0.8)) ** 2.4 * 0.30
            c = mix(mix(base, acc, g1), acc, g2)
            # tiny ordered dither to avoid banding, deterministic
            d = ((x * 7 + y * 13) % 4 - 1.5) * 0.4
            row += bytes(max(0, min(255, int(v + d))) for v in c)
        rows.append(bytes(row))
    raw = b"".join(rows)
    def chunk(t, data):
        c = struct.pack(">I", len(data)) + t + data
        return c + struct.pack(">I", zlib.crc32(t + data) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))

if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1])
    w = int(sys.argv[2]) if len(sys.argv) > 2 else 1920
    h = int(sys.argv[3]) if len(sys.argv) > 3 else 1080
    tok_path = pathlib.Path(__file__).resolve().parent.parent / "themes/tokens/tokens.json"
    theme = sys.argv[4] if len(sys.argv) > 4 else "hcs-midnight"
    tok = json.loads(tok_path.read_text(encoding="utf-8"))["themes"][theme]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(render(w, h, tok))
    print(f"wrote {out} ({w}x{h})")
