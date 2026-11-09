"""Accessibility: every text/surface token pair in every HCS theme meets WCAG AA (4.5:1).

AGENTS.md 4.1 requires sufficient contrast and 10.2 forbids shipping unreadable UI. The tokens are the
single source of truth, so the check belongs here: a future palette edit that dips below AA fails the
gate instead of shipping.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
THEMES = json.loads((ROOT / "themes/tokens/tokens.json").read_text(encoding="utf-8"))["themes"]

FOREGROUNDS = ("text-primary", "text-secondary", "text-muted", "accent")
SURFACES = ("surface-0", "surface-1", "surface-2")


def luminance(color: str) -> float:
    h = color.lstrip("#")[:6]
    channels = [int(h[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def test_every_text_pair_meets_wcag_aa():
    failures = []
    for name, tokens in THEMES.items():
        for fg in FOREGROUNDS:
            for bg in SURFACES:
                ratio = contrast(tokens[fg], tokens[bg])
                if ratio < 4.5:
                    failures.append((name, fg, bg, round(ratio, 2)))
    assert not failures, failures


def test_selected_text_is_readable_on_the_accent():
    for name, tokens in THEMES.items():
        ratio = contrast(tokens["text-inverse"], tokens["accent"])
        assert ratio >= 4.5, (name, round(ratio, 2))


def test_the_palette_actually_varies_between_themes():
    """A copy-paste mistake that made every theme identical would still pass the contrast check."""
    first = THEMES["hcs-midnight"]
    others = {k: v for k, v in THEMES.items() if k != "hcs-midnight"}
    assert others
    for name, tokens in others.items():
        assert tokens["surface-0"] != first["surface-0"], name
