"""Normalise a text file to ASCII, reporting what was replaced (the release notes must be ASCII)."""
import sys
from pathlib import Path

MAP = {
    0x2192: "->",
    0x2190: "<-",
    0x2014: "-",
    0x2013: "-",
    0x2026: "...",
    0x2018: "'",
    0x2019: "'",
    0x201C: '"',
    0x201D: '"',
    0x00A0: " ",
    0x00D7: "x",
    0x00A7: "section ",
}

for name in sys.argv[1:]:
    p = Path(name)
    text = p.read_text(encoding="utf-8")
    found: dict[str, int] = {}
    for ch in text:
        if ord(ch) > 127:
            found[ch] = found.get(ch, 0) + 1
            text = text.replace(ch, MAP.get(ord(ch), "?"))
    p.write_text(text, encoding="utf-8", newline="\n")
    left = sorted({c for c in text if ord(c) > 127})
    print(f"{name}: replaced {[(f'U+{ord(c):04X}', n) for c, n in found.items()]}; remaining non-ASCII: {left}")
