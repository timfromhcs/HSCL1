"""Brand generator tests: SVG hygiene, deterministic output, raster sanity."""
import json
import re
import struct
import sys
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import gen_brand as gb  # noqa: E402

TOKENS = json.loads((ROOT / "themes/tokens/tokens.json").read_text(encoding="utf-8"))
ALLOWED = {c[:7].lower() for t in TOKENS["themes"].values() for c in t.values() if isinstance(c, str) and c.startswith("#")} | {"#000000"}


def test_svgs_are_clean_and_token_coloured():
    files = gb.build_svgs(TOKENS)
    assert len(files) == 9
    for name, text in files.items():
        root = ET.fromstring(text)
        assert root.tag.endswith("svg"), name
        assert "href" not in text and "<text" not in text and "<image" not in text, name
        assert root.attrib["role"] == "img" and root.attrib["aria-label"] == "HSCL1"
        for colour in re.findall(r'fill="(#[0-9a-fA-F]{6})"', text):
            assert colour.lower() in ALLOWED, (name, colour)
    mark = ET.fromstring(files["hscl1-mark-dark.svg"]).attrib["viewBox"].split()
    assert mark[2] == mark[3]


def test_generation_is_deterministic():
    assert gb.build_svgs(TOKENS) == gb.build_svgs(TOKENS)


def test_ring_has_opposite_windings():
    outer, inner = gb.mark_ring()
    assert gb.area(outer) > 0 > gb.area(inner)


def _decode(png: bytes):
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    w, h = struct.unpack(">II", png[16:24])
    pos, idat = 8, b""
    while pos < len(png):
        n = struct.unpack(">I", png[pos:pos + 4])[0]
        if png[pos + 4:pos + 8] == b"IDAT":
            idat += png[pos + 8:pos + 8 + n]
        pos += 12 + n
    raw = zlib.decompress(idat)
    return w, h, raw, w * 4 + 1


def test_raster_mark_has_transparent_corners_and_opaque_ring():
    accent = TOKENS["themes"]["hcs-midnight"]["accent"][:7]
    png = gb.render_layers(128, 128, 256, 256, [(accent, gb.mark_ring())])
    w, h, raw, stride = _decode(png)
    px = lambda x, y: raw[y * stride + 1 + x * 4: y * stride + 1 + x * 4 + 4]  # noqa: E731
    assert px(1, 1)[3] == 0                      # corner transparent
    assert px(64, 64)[3] == 0                    # inside the ring is empty
    assert px(18, 64)[3] == 255                  # left vertical edge of the ring is fully inked
    assert tuple(px(18, 64)[:3]) == gb.hex_rgb(accent)


def test_ico_contains_requested_sizes():
    data = gb.ico({16: b"x" * 4, 32: b"y" * 4})
    assert struct.unpack("<HHH", data[:6]) == (0, 1, 2)


def test_wordmark_is_five_glyphs_wide_enough():
    shapes, width = gb.wordmark_shapes()
    assert width > 300 and len(shapes) > 20
    assert all(gb.area(s) > 0 for s in shapes)
