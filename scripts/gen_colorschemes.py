#!/usr/bin/env python3
"""Generate KDE colour schemes (HCS<Name>.colors) from the design tokens (single source of truth).

Usage: gen_colorschemes.py OUTDIR
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def rgb(h: str) -> str:
    h = h.lstrip("#")[:6]
    return f"{int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)}"


def scheme_name(theme_id: str) -> str:
    return "HCS" + theme_id[len("hcs-"):].capitalize()


def view(t: dict, bg: str, alt: str, fg_inactive: str = "text-secondary", hover: str = "accent-hover") -> dict:
    return {
        "BackgroundNormal": rgb(t[bg]), "BackgroundAlternate": rgb(t[alt]),
        "ForegroundNormal": rgb(t["text-primary"]), "ForegroundInactive": rgb(t[fg_inactive]),
        "ForegroundActive": rgb(t["accent"]), "ForegroundLink": rgb(t["info"]), "ForegroundVisited": rgb(t["text-muted"]),
        "ForegroundNegative": rgb(t["danger"]), "ForegroundNeutral": rgb(t["warning"]), "ForegroundPositive": rgb(t["success"]),
        "DecorationFocus": rgb(t["focus-ring"]), "DecorationHover": rgb(t[hover]),
    }


def sections(t: dict, theme_id: str) -> dict[str, dict]:
    sel = view(t, "accent", "accent-pressed")
    sel.update({"ForegroundNormal": rgb(t["text-inverse"]), "ForegroundInactive": rgb(t["text-inverse"]),
                "ForegroundActive": rgb(t["text-inverse"]), "ForegroundLink": rgb(t["text-inverse"]),
                "ForegroundVisited": rgb(t["text-inverse"]), "DecorationFocus": rgb(t["focus-ring"])})
    return {
        "ColorEffects:Disabled": {"Color": rgb(t["surface-1"]), "ColorAmount": "0", "ColorEffect": "0", "ContrastAmount": "0.65", "ContrastEffect": "1", "IntensityAmount": "0.1", "IntensityEffect": "2"},
        "ColorEffects:Inactive": {"ChangeSelectionColor": "true", "Color": rgb(t["surface-0"]), "ColorAmount": "0.025", "ColorEffect": "2", "ContrastAmount": "0.1", "ContrastEffect": "2", "Enable": "false", "IntensityAmount": "0", "IntensityEffect": "0"},
        "Colors:Button": view(t, "surface-2", "surface-1"),
        "Colors:Complementary": view(t, "surface-0", "surface-1"),
        "Colors:Header": view(t, "surface-0", "surface-1"),
        "Colors:Header][Inactive": view(t, "surface-0", "surface-1"),
        "Colors:Selection": sel,
        "Colors:Tooltip": view(t, "surface-2", "surface-1"),
        "Colors:View": view(t, "surface-0", "surface-1"),
        "Colors:Window": view(t, "surface-1", "surface-0"),
        "General": {"ColorScheme": scheme_name(theme_id), "Name": "HCS " + theme_id[len("hcs-"):].capitalize(), "AccentColor": rgb(t["accent"]), "shadeSortColumn": "true"},
        "KDE": {"contrast": "4"},
        "WM": {"activeBackground": rgb(t["surface-0"]), "activeForeground": rgb(t["text-primary"]),
               "inactiveBackground": rgb(t["surface-1"]), "inactiveForeground": rgb(t["text-muted"])},
    }


def render(t: dict, theme_id: str) -> str:
    out = []
    for name, kv in sections(t, theme_id).items():
        out.append(f"[{name}]")
        out += [f"{k}={v}" for k, v in kv.items()]
        out.append("")
    return "\n".join(out)


def main(outdir: str) -> int:
    tokens = json.loads((ROOT / "themes/tokens/tokens.json").read_text(encoding="utf-8"))
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    for theme_id, t in tokens["themes"].items():
        (out / f"{scheme_name(theme_id)}.colors").write_text(render(t, theme_id), encoding="utf-8")
    print(f"wrote {len(tokens['themes'])} colour schemes to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
