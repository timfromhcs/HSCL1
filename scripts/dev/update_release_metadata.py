"""Update README + showcase manifest for 0.1.7-alpha.0 (release metadata must match the artifact)."""
import json
import shutil
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
ISO = "HSCL1-0.1.7-alpha.0-amd64.iso"
SHA = "400fb9d7aca53ef4f2b4926fb26732e0cd987b6363fc0f9800e2591d8e951df0"
BYTES = 5027201024
SRC = "88f0fbe"
PARTS = [
    ("c78f680c29cf368ba7f4f66e4646d1627c3298e90af8efccbbf28d951cfaeb37", "part000"),
    ("22eb74303c06bf7b03c822ec328e1b9423899913ce064d8d165f3a220b6d8a6e", "part001"),
    ("c388802749e9ab50ba3d7aee923467e93adf505d5dcd4024ee88e47709f5db15", "part002"),
]

# --- hero capture: the fresh 0.1.7 desktop, not a 0.1.6 image -------------------------------
src_png = ROOT / "artifacts/boot-0.1.7-uefi/desktop-final.png"
dst_png = ROOT / "docs/img/showcase/01_desktop_clean.png"
shutil.copyfile(src_png, dst_png)
im = Image.open(dst_png).convert("RGB")
colors = len({px for px in im.getdata()})
print(f"hero capture: {dst_png.stat().st_size} bytes, {colors} colours, {im.size}")

manifest_path = ROOT / "docs/img/showcase/manifest.json"
entries = json.loads(manifest_path.read_text(encoding="utf-8"))
for e in entries:
    if e["filename"] == "01_desktop_clean.png":
        e.update({
            "bytes": dst_png.stat().st_size,
            "colors": colors,
            "size": list(im.size),
            "description": (
                "Clean HSCL1 live desktop on the 0.1.7 artifact: upright desktop labels, no untrusted "
                "emblem, HCS top bar, centred floating dock, Midnight wallpaper"
            ),
            "source_iso": f"{ISO} sha256 {SHA[:8]}",
        })
manifest_path.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")

# --- README ---------------------------------------------------------------------------------
readme = ROOT / "README.md"
lines = readme.read_text(encoding="utf-8").splitlines(keepends=True)

replaced: list[str] = []


def swap(marker: str, new: str) -> None:
    hits = [i for i, ln in enumerate(lines) if marker in ln]
    assert len(hits) == 1, f"marker {marker!r} found {len(hits)} times"
    lines[hits[0]] = new
    replaced.append(marker)


swap(
    "release-0.1.6--alpha.0-blue.svg",
    '[![Release](https://img.shields.io/badge/release-0.1.7--alpha.0-blue.svg)]'
    '(https://github.com/timfromhcs/HSCL1/releases/tag/v0.1.7-alpha.0)\n',
)
swap(
    'alt="HSCL1 0.1.6-alpha.0 live desktop',
    '<img src="docs/img/showcase/01_desktop_clean.png" alt="HSCL1 0.1.7-alpha.0 live desktop '
    '(KDE Plasma 6.6 LTS, Top Bar, Dock, Midnight Theme) - real capture from QEMU 9.2.0 with WHPX" width="940">\n',
)
swap(
    "*HSCL1 0.1.6-alpha.0 running live in QEMU/WHPX",
    "*HSCL1 0.1.7-alpha.0 running live in QEMU/WHPX - clean first boot with HCS top status bar, "
    "centered floating dock, and Midnight theme.*\n",
)
swap(
    "> **Status: Pre-Alpha (`0.1.6-alpha.0`).**",
    "> **Status: Pre-Alpha (`0.1.7-alpha.0`).**\n",
)
swap(
    "> HSCL1 is verified **in virtual machines only**",
    f"> HSCL1 is verified **in virtual machines only** (UEFI and BIOS firmware under QEMU 9.2.0 with WHPX / "
    f"KVM acceleration). The current artifact is `{ISO}` (`{SHA[:8]}.`, {BYTES:,} B, built from `{SRC}`, xz, "
    f"clean tree): UEFI boot at **4 GB** reached the desktop in **192 s** and `scripts/qa_report.py` exits 0 "
    f"(9 checks ok, one `info` line about Secure Boot). Verified in QEMU:\n",
)
swap("--iso \"path\\to\\HSCL1-0.1.6-alpha.0-amd64.iso\"", '  --iso "path\\to\\HSCL1-0.1.7-alpha.0-amd64.iso" `\n')
swap("-cdrom HSCL1-0.1.6-alpha.0-amd64.iso \\", "  -cdrom HSCL1-0.1.7-alpha.0-amd64.iso \\\n")
swap(
    "| **Remastered Live/Installer ISO** |",
    f"| **Remastered Live/Installer ISO** | `VM-VERIFIED` | `{ISO}` (`{SHA[:8]}.`, source `{SRC}`, xz): live "
    f"desktop at 4 GB under UEFI (QEMU+WHPX) in 192 s, `qa_report.py` exit 0 with 9 checks; "
    f"[`docs/img/showcase/01_desktop_clean.png`](docs/img/showcase/01_desktop_clean.png) is this artifact's "
    f"own capture |\n",
)
swap(
    "> **`v0.1.6-alpha.0` is the current prerelease**",
    f"> **`v0.1.7-alpha.0` is the current prerelease** (ISO `{SHA[:8]}.`, {BYTES:,} bytes, built from `{SRC}`, "
    f"xz). It supersedes `v0.1.6-alpha.0` (`a916540c.`), whose release commit was never merged into `main` - "
    f"0.1.7 is the first release built from a commit that is on `main`, and it carries the Q-61 finding "
    f"(the installer's SIGKILL comes from drkonqi), the corrected `KCRASH_DUMP_ONLY` claim, the ESP guard's "
    f"diagnostics and the live-locale fix.\n",
)
swap("gh release download v0.1.6-alpha.0 --repo timfromhcs/HSCL1", "$ gh release download v0.1.7-alpha.0 --repo timfromhcs/HSCL1\n")
swap("### Release Checksums (v0.1.6-alpha.0)", "### Release Checksums (v0.1.7-alpha.0)\n")
for digest, part in PARTS:
    swap(f"HSCL1-0.1.6-alpha.0-amd64.iso.{part}", f"{digest}  {ISO}.{part}\n")
swap("a916540c44d27529107c599ff58dbad95fb3292270814b7832d06ef5ebe5e94d  HSCL1-0.1.6", f"{SHA}  {ISO}\n")

# the "not rebuilt for 0.1.6" note is now one release further behind
for i, ln in enumerate(lines):
    if "not rebuilt for 0.1.6;" in ln:
        lines[i] = ln.replace("not rebuilt for 0.1.6;", "not rebuilt for 0.1.6 or 0.1.7;")
        replaced.append("not rebuilt for 0.1.6")

# German and French status lines carry the same token as the English one
text = "".join(lines).replace("(`0.1.6-alpha.0`)", "(`0.1.7-alpha.0`)")
readme.write_text(text, encoding="utf-8", newline="\n")
print(f"README: {len(replaced)} edits")
