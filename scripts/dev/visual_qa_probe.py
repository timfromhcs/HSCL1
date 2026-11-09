"""Visual-QA probe: crop regions and measure label contrast from real screenshots."""

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts" / "visual-qa"
OUT.mkdir(parents=True, exist_ok=True)


def relative_luminance(rgb):
    def ch(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (ch(x) for x in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = relative_luminance(a), relative_luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def region_stats(img, box, name):
    crop = img.crop(box).convert("RGB")
    crop.save(OUT / f"{name}.png")
    px = list(crop.getdata())
    # brightest and darkest pixel = text vs background extremes
    bright = max(px, key=relative_luminance)
    dark = min(px, key=relative_luminance)
    ratio = contrast(bright, dark)
    avg = tuple(sum(c[i] for c in px) // len(px) for i in range(3))
    print(f"{name}: box={box} avg={avg} brightest={bright} darkest={dark} contrast={ratio:.2f}:1")
    return ratio


shots = ROOT / "docs" / "img" / "showcase"

desktop = Image.open(shots / "01_desktop_clean.png")
print("size:", desktop.size)
region_stats(desktop, (14, 30, 110, 150), "desktop-label-control-center")
region_stats(desktop, (118, 30, 220, 150), "desktop-label-handbook")
region_stats(desktop, (240, 30, 320, 140), "desktop-label-install")
region_stats(desktop, (0, 0, 1280, 33), "top-bar")
region_stats(desktop, (370, 745, 910, 790), "dock")

cc = Image.open(shots / "06_control_center_security.png")
region_stats(cc, (335, 385, 1170, 590), "cc-health-card")
region_stats(cc, (335, 145, 1170, 330), "cc-status-card")

inst = Image.open(shots / "11_installer_welcome.png")
region_stats(inst, (0, 34, 190, 130), "installer-sidebar-logo")
