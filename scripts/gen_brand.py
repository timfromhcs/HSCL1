#!/usr/bin/env python3
"""Generate the original HSCL1 logo family (pure stdlib, deterministic).

The mark is a hexagonal ring around a geometric "1"; the wordmark "HSCL1" is built from stroked
polylines (outlined, no font dependency). Colours come from themes/tokens/tokens.json.

Usage: gen_brand.py OUTDIR [--sizes 16,32,48,64,128,256,512,1024]
Writes: SVG (mark/wordmark/lockup x dark|light|mono), mark PNGs, favicon.ico, wordmark PNG.
"""
from __future__ import annotations

import argparse
import json
import math
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
Point = tuple[float, float]
Poly = list[Point]


def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")[:6]
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


# ---------------------------------------------------------------- geometry
def area(p: Poly) -> float:
    return 0.5 * sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p)))


def oriented(p: Poly, positive: bool = True) -> Poly:
    return p if (area(p) > 0) == positive else p[::-1]


def hexagon(cx: float, cy: float, r: float) -> Poly:
    return [(cx + r * math.cos(math.radians(-90 + 60 * k)), cy + r * math.sin(math.radians(-90 + 60 * k))) for k in range(6)]


def stroke(path: list[Point], w: float) -> list[Poly]:
    """Convert a polyline into positively oriented quads (union under non-zero fill) with round-ish joins."""
    out: list[Poly] = []
    h = w / 2
    for (x0, y0), (x1, y1) in zip(path, path[1:]):
        dx, dy = x1 - x0, y1 - y0
        n = math.hypot(dx, dy)
        if n == 0:
            continue
        ux, uy = dx / n, dy / n
        nx, ny = -uy * h, ux * h
        # extend by half width at both ends: square caps that also seal joins on dense arcs
        ex, ey = ux * h * 0.0, uy * h * 0.0
        out.append(oriented([(x0 - ex + nx, y0 - ey + ny), (x1 + ex + nx, y1 + ey + ny),
                             (x1 + ex - nx, y1 + ey - ny), (x0 - ex - nx, y0 - ey - ny)]))
    # round joins/caps: a small disc at every vertex closes the outer wedge gaps between quads
    for px, py in path:
        out.append(oriented([(px + h * math.cos(math.radians(30 * k)), py + h * math.sin(math.radians(30 * k))) for k in range(12)]))
    return out


def arc(cx: float, cy: float, rx: float, ry: float, a0: float, a1: float, step: float = 3.0) -> list[Point]:
    n = max(2, int(abs(a1 - a0) / step))
    return [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * i / n)), cy + ry * math.sin(math.radians(a0 + (a1 - a0) * i / n)))
            for i in range(n + 1)]


def rect(x0: float, y0: float, x1: float, y1: float) -> Poly:
    return oriented([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])


# ---------------------------------------------------------------- shapes (256 x 256 mark grid)
def mark_ring() -> list[Poly]:
    return [oriented(hexagon(128, 128, 116)), oriented(hexagon(128, 128, 92), positive=False)]


def mark_one() -> list[Poly]:
    stem = rect(120, 70, 146, 186)
    foot = rect(98, 166, 168, 186)
    flag = oriented([(120, 70), (120, 102), (92, 118), (92, 92)])
    return [stem, foot, flag]


def wordmark_shapes(w: float = 15.0, cap: float = 100.0) -> tuple[list[Poly], float]:
    """Return outlined 'HSCL1' polygons with the top-left of the cap box at (0,0) and the total width."""
    shapes: list[Poly] = []
    x = 0.0
    gap = 26.0
    half = w / 2

    def vbar(px: float, y0: float, y1: float) -> Poly:
        return rect(px - half, y0, px + half, y1)

    # H
    hw = 72.0
    shapes += [vbar(x + half, 0, cap), vbar(x + hw - half, 0, cap), rect(x + half, cap / 2 - half, x + hw - half, cap / 2 + half)]
    x += hw + gap
    # S (two stacked arcs)
    r = cap / 4 - half / 2
    sw = 2 * r
    top = arc(x + sw / 2, half + r, r, r, -30, -270)
    bot = arc(x + sw / 2, cap - half - r, r, r, -90, 150)
    shapes += stroke(top + bot, w)
    x += sw + w + gap
    # C
    rx, ry = 38.0, cap / 2 - half
    shapes += stroke(arc(x + rx + half, cap / 2, rx, ry, -42, -318), w)
    x += 2 * rx + w + gap
    # L
    lw = 54.0
    shapes += [vbar(x + half, 0, cap), rect(x + half, cap - w, x + lw, cap)]
    x += lw + gap
    # 1
    shapes += [vbar(x + 34, 0, cap), *stroke([(x + 34, half), (x + 6, 26)], w)]
    x += 34 + half
    return shapes, x


# ---------------------------------------------------------------- SVG
def path_d(polys: list[Poly]) -> str:
    return " ".join("M" + " L".join(f"{px:.2f},{py:.2f}" for px, py in p) + " Z" for p in polys)


def svg_doc(w: float, h: float, layers: list[tuple[str, list[Poly]]], title: str) -> str:
    body = "".join(f'<path fill="{c}" fill-rule="nonzero" d="{path_d(p)}"/>' for c, p in layers)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:g} {h:g}" role="img" aria-label="{title}">'
            f"<title>{title}</title>{body}</svg>\n")


def palettes(tokens: dict) -> dict[str, tuple[str, str]]:
    mid, light = tokens["themes"]["hcs-midnight"], tokens["themes"]["hcs-light"]
    return {"dark": (mid["accent"][:7], mid["text-primary"][:7]),
            "light": (light["accent-pressed"][:7], light["text-primary"][:7]),
            "mono": ("#000000", "#000000")}


def build_svgs(tokens: dict) -> dict[str, str]:
    files: dict[str, str] = {}
    wm, wm_w = wordmark_shapes()
    for variant, (accent, text) in palettes(tokens).items():
        files[f"hscl1-mark-{variant}.svg"] = svg_doc(256, 256, [(accent, mark_ring()), (text, mark_one())], "HSCL1")
        pad = 8.0
        files[f"hscl1-wordmark-{variant}.svg"] = svg_doc(wm_w + 2 * pad, 100 + 2 * pad, [(text, [[(px + pad, py + pad) for px, py in s] for s in wm])], "HSCL1")
        scale = 100 / 256
        m = [[(px * scale, py * scale) for px, py in s] for s in mark_ring()]
        o = [[(px * scale, py * scale) for px, py in s] for s in mark_one()]
        off = 100 + 28
        lock = [[(px + off + pad, py + pad) for px, py in s] for s in wm]
        files[f"hscl1-lockup-{variant}.svg"] = svg_doc(off + wm_w + 2 * pad, 100 + 2 * pad,
                                                      [(accent, [[(px + pad, py + pad) for px, py in s] for s in m]),
                                                       (text, [[(px + pad, py + pad) for px, py in s] for s in o]),
                                                       (text, lock)], "HSCL1")
    return files


# ---------------------------------------------------------------- rasteriser (non-zero, supersampled)
def coverage(polys: list[Poly], w: int, h: int, sx: float, sy: float, ss: int = 4) -> list[bytearray]:
    """Alpha mask rows (0..255) for polygons given in source units scaled by sx, sy."""
    edges = []
    for p in polys:
        pts = [(x * sx * ss, y * sy * ss) for x, y in p]
        for i in range(len(pts)):
            (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % len(pts)]
            if y0 != y1:
                edges.append((min(y0, y1), max(y0, y1), x0, y0, x1, y1, 1 if y1 > y0 else -1))
    edges.sort()
    acc = [[0] * w for _ in range(h)]
    active: list[tuple] = []
    ei = 0
    for row in range(h * ss):
        yc = row + 0.5
        while ei < len(edges) and edges[ei][0] <= yc:
            active.append(edges[ei])
            ei += 1
        active = [e for e in active if e[1] > yc]
        xs = sorted((e[2] + (yc - e[3]) * (e[4] - e[2]) / (e[5] - e[3]), e[6]) for e in active)
        wind = 0
        line = acc[row // ss]
        for i, (xv, d) in enumerate(xs[:-1]):
            wind += d
            if wind != 0:
                a, b = max(0.0, xv), min(w * ss, xs[i + 1][0])
                if b <= a:
                    continue
                ia, ib = int(a), int(b)
                for cx in range(ia // ss, min(w - 1, ib // ss) + 1):
                    lo, hi = max(a, cx * ss), min(b, (cx + 1) * ss)
                    if hi > lo:
                        line[cx] += (hi - lo)
    return [bytearray(min(255, int(v / (ss * ss) * 255 + 0.5)) for v in r) for r in acc]


def png_rgba(w: int, h: int, rgba: list[bytearray]) -> bytes:
    raw = b"".join(b"\x00" + bytes(r) for r in rgba)

    def chunk(t: bytes, d: bytes) -> bytes:
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


def render_layers(w: int, h: int, units_w: float, units_h: float, layers: list[tuple[str, list[Poly]]]) -> bytes:
    rows = [bytearray(w * 4) for _ in range(h)]
    sx, sy = w / units_w, h / units_h
    for color, polys in layers:
        r, g, b = hex_rgb(color)
        mask = coverage(polys, w, h, sx, sy)
        for y in range(h):
            dst, m = rows[y], mask[y]
            for x in range(w):
                a = m[x]
                if not a:
                    continue
                i = x * 4
                da = dst[i + 3]
                oa = a + da * (255 - a) // 255
                if oa:
                    for k, c in enumerate((r, g, b)):
                        dst[i + k] = (c * a + dst[i + k] * da * (255 - a) // 255) // oa
                dst[i + 3] = oa
    return png_rgba(w, h, rows)


def ico(pngs: dict[int, bytes]) -> bytes:
    head = struct.pack("<HHH", 0, 1, len(pngs))
    off = 6 + 16 * len(pngs)
    entries, blobs = b"", b""
    for size, data in sorted(pngs.items()):
        entries += struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(data), off + len(blobs))
        blobs += data
    return head + entries + blobs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("outdir")
    ap.add_argument("--sizes", default="16,32,48,64,128,256,512")
    a = ap.parse_args()
    out = Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)
    tokens = json.loads((ROOT / "themes/tokens/tokens.json").read_text(encoding="utf-8"))
    for name, text in build_svgs(tokens).items():
        (out / name).write_text(text, encoding="utf-8")
    accent, text = palettes(tokens)["dark"]
    sizes = [int(s) for s in a.sizes.split(",")]
    pngs: dict[int, bytes] = {}
    for s in sizes:
        pngs[s] = render_layers(s, s, 256, 256, [(accent, mark_ring()), (text, mark_one())])
        (out / f"hscl1-mark-{s}.png").write_bytes(pngs[s])
    (out / "favicon.ico").write_bytes(ico({s: pngs[s] for s in (16, 32, 48, 256) if s in pngs}))
    wm, wm_w = wordmark_shapes()
    pad = 8.0
    wmw, wmh = wm_w + 2 * pad, 100 + 2 * pad
    wpx = 1024
    (out / "hscl1-wordmark-dark.png").write_bytes(render_layers(wpx, round(wpx * wmh / wmw), wmw, wmh, [(text, [[(px + pad, py + pad) for px, py in s] for s in wm])]))
    print(f"wrote {len(list(out.iterdir()))} files to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
