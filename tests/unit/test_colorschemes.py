"""Colour schemes derive from tokens and keep WCAG AA contrast for their key pairs."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import gen_colorschemes as gc  # noqa: E402

TOKENS = json.loads((ROOT / "themes/tokens/tokens.json").read_text(encoding="utf-8"))


def lum(c: str) -> float:
    r, g, b = (int(x) / 255 for x in c.split(","))
    f = lambda v: v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4  # noqa: E731
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def ratio(a: str, b: str) -> float:
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_every_theme_gets_a_scheme_with_all_sections():
    for theme_id, t in TOKENS["themes"].items():
        secs = gc.sections(t, theme_id)
        for needed in ("Colors:Window", "Colors:View", "Colors:Button", "Colors:Selection", "Colors:Tooltip", "General", "WM"):
            assert needed in secs, (theme_id, needed)
        text = gc.render(t, theme_id)
        assert f"ColorScheme={gc.scheme_name(theme_id)}" in text


def test_colour_values_are_rgb_triplets():
    for theme_id, t in TOKENS["themes"].items():
        for name, kv in gc.sections(t, theme_id).items():
            for k, v in kv.items():
                if re.fullmatch(r"\d+,\d+,\d+", v):
                    assert all(0 <= int(x) <= 255 for x in v.split(",")), (theme_id, name, k)


def test_text_and_selection_contrast_is_aa():
    for theme_id, t in TOKENS["themes"].items():
        s = gc.sections(t, theme_id)
        for sec in ("Colors:Window", "Colors:View", "Colors:Button", "Colors:Tooltip"):
            assert ratio(s[sec]["ForegroundNormal"], s[sec]["BackgroundNormal"]) >= 4.5, (theme_id, sec)
        assert ratio(s["Colors:Selection"]["ForegroundNormal"], s["Colors:Selection"]["BackgroundNormal"]) >= 4.5, theme_id
