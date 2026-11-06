#!/usr/bin/env python3
"""Generate the HSCL1 Plymouth throbber frames and theme descriptor (pure stdlib, deterministic).

The two-step theme animates `throbber-0001.png` .. `throbber-0032.png` (218x119, transparent). Each frame is the HSCL1 lockup (mark +
wordmark) whose ring pulses between a dim and the full accent colour. The generic password-dialog artwork (entry, bullet, lock,
keyboard) is NOT generated here: the image hook copies it from the base theme (it carries no brand).

Usage: gen_plymouth.py OUTDIR
Writes OUTDIR/throbber-0001..0032.png, OUTDIR/hscl1-logo.plymouth, OUTDIR/watermark.png (1x1 transparent), OUTDIR/progress-00.png.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_brand as gb  # noqa: E402

W, H, FRAMES = 218, 119, 32
DESCRIPTOR = """[Plymouth Theme]
Name=HSCL1 Logo
Description=HSCL1 boot splash: the HSCL1 lockup with a pulsing ring (original artwork, GPL-3.0-or-later). Password dialog artwork from the base theme (fonts kept: the initramfs hook copies them for exactly these names).
ModuleName=two-step

[two-step]
Font=Ubuntu 12
TitleFont=Ubuntu Light 30
ImageDir=/usr/share/plymouth/themes/hscl1-logo
DialogHorizontalAlignment=.5
DialogVerticalAlignment=.725
TitleHorizontalAlignment=.5
TitleVerticalAlignment=.382
HorizontalAlignment=.5
VerticalAlignment=.65
WatermarkHorizontalAlignment=.5
WatermarkVerticalAlignment=.96
Transition=none
TransitionDuration=0.0
BackgroundStartColor=0x0b0f17
BackgroundEndColor=0x0b0f17
ProgressBarBackgroundColor=0x303846
ProgressBarForegroundColor=0xe6ecf5
DialogClearsFirmwareBackground=false
MessageBelowAnimation=true

[boot-up]
UseEndAnimation=false
UseFirmwareBackground=false

[shutdown]
UseEndAnimation=false
UseFirmwareBackground=false

[reboot]
UseEndAnimation=false
UseFirmwareBackground=false

[updates]
SuppressMessages=true
ProgressBarShowPercentComplete=true
UseProgressBar=true
_Title=Installing Updates...
_SubTitle=Do not turn off your computer

[system-upgrade]
SuppressMessages=true
ProgressBarShowPercentComplete=true
UseProgressBar=true
_Title=Upgrading System...
_SubTitle=Do not turn off your computer

[firmware-upgrade]
SuppressMessages=true
ProgressBarShowPercentComplete=true
UseProgressBar=true
_Title=Upgrading Firmware...
_SubTitle=Do not turn off your computer
"""


def mix(a: str, b: str, k: float) -> str:
    ra, rb = gb.hex_rgb(a), gb.hex_rgb(b)
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * k) for x, y in zip(ra, rb))


def frame(i: int, accent: str, text: str) -> bytes:
    k = 0.35 + 0.65 * (0.5 - 0.5 * math.cos(2 * math.pi * i / FRAMES))  # ring brightness 35%..100%
    layers, lw, lh = gb.lockup_layers(mix("#0b0f17", accent, k), text)
    scale = min((W - 8) / lw, (H - 8) / lh)
    pw, ph = round(lw * scale), round(lh * scale)
    logo = gb.render_layers(pw, ph, lw, lh, layers)
    # centre the rendered lockup on the W x H transparent canvas
    import struct
    import zlib
    raw = zlib.decompress(b"".join(_idat(logo)))
    rows_in = [raw[y * (pw * 4 + 1) + 1:(y + 1) * (pw * 4 + 1)] for y in range(ph)]
    canvas = [bytearray(W * 4) for _ in range(H)]
    ox, oy = (W - pw) // 2, (H - ph) // 2
    for y in range(ph):
        canvas[oy + y][ox * 4:(ox + pw) * 4] = rows_in[y]
    del struct
    return gb.png_rgba(W, H, canvas)


def _idat(png: bytes):
    import struct
    pos = 8
    while pos < len(png):
        n, t = struct.unpack(">I4s", png[pos:pos + 8])
        if t == b"IDAT":
            yield png[pos + 8:pos + 8 + n]
        pos += 12 + n


def main() -> int:
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    tokens = json.loads((gb.ROOT / "themes/tokens/tokens.json").read_text(encoding="utf-8"))
    accent, text = gb.palettes(tokens)["dark"]
    for i in range(FRAMES):
        (out / f"throbber-{i + 1:04d}.png").write_bytes(frame(i, accent, text))
    blank = gb.png_rgba(1, 1, [bytearray(4)])
    (out / "watermark.png").write_bytes(blank)
    (out / "progress-00.png").write_bytes(blank)
    (out / "hscl1-logo.plymouth").write_text(DESCRIPTOR, encoding="utf-8")
    print(f"wrote {FRAMES} frames + descriptor to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
