#!/usr/bin/env python3
"""Validate design tokens: required keys present and WCAG AA contrast (4.5:1) for text on surfaces."""
import json, sys, pathlib

REQUIRED = ["surface-0","surface-1","surface-2","surface-glass","text-primary","text-secondary","text-muted",
            "text-inverse","accent","accent-hover","accent-pressed","accent-soft","success","warning","danger",
            "info","border-subtle","border-strong","focus-ring"]

def lum(hexc):
    h = hexc.lstrip("#")[:6]
    r, g, b = (int(h[i:i+2], 16) / 255 for i in (0, 2, 4))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)

def ratio(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)

def main(path):
    data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    bad = []
    for name, t in data["themes"].items():
        for k in REQUIRED:
            if k not in t:
                bad.append(f"{name}: missing {k}")
        for fg in ("text-primary", "text-secondary", "text-muted"):
            for bg in ("surface-0", "surface-1", "surface-2"):
                if fg in t and bg in t and ratio(t[fg], t[bg]) < 4.5:
                    bad.append(f"{name}: {fg} on {bg} = {ratio(t[fg], t[bg]):.2f} < 4.5")
        for sem in ("success", "warning", "danger", "info", "accent"):
            if sem in t and ratio(t[sem], t["surface-1"]) < 3.0:
                bad.append(f"{name}: {sem} on surface-1 = {ratio(t[sem], t['surface-1']):.2f} < 3.0 (UI component minimum)")
    for b in bad:
        print("FAIL", b)
    print("tokens OK" if not bad else f"{len(bad)} problem(s)")
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "themes/tokens/tokens.json"))
