"""Update README + showcase manifest for 0.1.8-alpha.0 (release metadata must match the artifact)."""
import json
import shutil
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
VERSION = "0.1.8-alpha.0"
OLD = "0.1.7-alpha.0"
ISO = f"HSCL1-{VERSION}-amd64.iso"
SET = ROOT / "artifacts" / "release-0.1.8-set"

sums = {}
for line in (SET / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
    if line.strip():
        digest, name = line.split("  ", 1)
        sums[name.strip()] = digest.strip()
SHA = sums[ISO]
BYTES = (SET / ISO).stat().st_size
SRC = "91c8acb"

# --- hero capture: the fresh 0.1.8 desktop ------------------------------------------------------
src_png = ROOT / "artifacts/hero-0.1.8/desktop-final.png"
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
                "Clean HSCL1 live desktop on the 0.1.8 artifact: upright desktop labels, no untrusted "
                "emblem, HCS top bar, centred floating dock, Midnight wallpaper"
            ),
            "source_iso": f"{ISO} sha256 {SHA[:8]}",
        })
manifest_path.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")

# --- README ------------------------------------------------------------------------------------
readme = ROOT / "README.md"
lines = readme.read_text(encoding="utf-8").splitlines(keepends=True)
replaced: list[str] = []


def swap(marker: str, new: str) -> None:
    hits = [i for i, ln in enumerate(lines) if marker in ln]
    assert len(hits) == 1, f"marker {marker!r} found {len(hits)} times"
    lines[hits[0]] = new
    replaced.append(marker)


swap(
    "release-0.1.7--alpha.0-blue.svg",
    f'[![Release](https://img.shields.io/badge/release-{VERSION.replace("-alpha.0", "--alpha.0")}-blue.svg)]'
    f'(https://github.com/timfromhcs/HSCL1/releases/tag/v{VERSION})\n',
)
swap(
    f'alt="HSCL1 {OLD} live desktop',
    f'<img src="docs/img/showcase/01_desktop_clean.png" alt="HSCL1 {VERSION} live desktop '
    f'(KDE Plasma 6.6 LTS, Top Bar, Dock, Midnight Theme) - real capture from QEMU 9.2.0 with WHPX" width="940">\n',
)
swap(
    f"*HSCL1 {OLD} running live in QEMU/WHPX",
    f"*HSCL1 {VERSION} running live in QEMU/WHPX - clean first boot with HCS top status bar, "
    f"centered floating dock, and Midnight theme.*\n",
)
swap(f"> **Status: Pre-Alpha (`{OLD}`).**", f"> **Status: Pre-Alpha (`{VERSION}`).**\n")
swap(
    "> HSCL1 is verified **in virtual machines only**",
    f"> HSCL1 is verified **in virtual machines only** (UEFI and BIOS firmware under QEMU 9.2.0 with WHPX / "
    f"KVM acceleration). The current artifact is `{ISO}` (`{SHA[:8]}.`, {BYTES:,} B, built from `{SRC}`, xz, "
    f"clean tree): UEFI boot at **4 GB** reached the desktop and `scripts/qa_report.py` exits 0 (9 checks ok, "
    f"one `info` line about Secure Boot), and **20 of 20 sequential installer starts survive**. Verified in "
    f"QEMU:\n",
)
swap(f'--iso "path\\to\\HSCL1-{OLD}-amd64.iso"', f'  --iso "path\\to\\{ISO}" `\n')
swap(f"-cdrom HSCL1-{OLD}-amd64.iso \\", f"  -cdrom {ISO} \\\n")
swap(
    "| **Remastered Live/Installer ISO** |",
    f"| **Remastered Live/Installer ISO** | `VM-VERIFIED` | `{ISO}` (`{SHA[:8]}.`, source `{SRC}`, xz): live "
    f"desktop at 4 GB under UEFI (QEMU+WHPX), `qa_report.py` exit 0 with 9 checks, `verify-image` green "
    f"including `installer notes step stays disabled (Q-68)`; "
    f"[`docs/img/showcase/01_desktop_clean.png`](docs/img/showcase/01_desktop_clean.png) is this artifact's "
    f"own capture |\n",
)
swap(
    f"> **`v{OLD}` is the current prerelease**",
    f"> **`v{VERSION}` is the current prerelease** (ISO `{SHA[:8]}.`, {BYTES:,} bytes, built from `{SRC}`, "
    f"xz). It supersedes `v0.1.7-alpha.0` (`400fb9d7.`) and **fixes the installer's startup crash**: the "
    f"`notesqml` step segfaulted while the progress tree painted its name (`NotesQmlViewStep::prettyName()` "
    f"-> `TranslatedString::get()`), the step is out of the sequence, and 20 of 20 starts now survive with a "
    f"core pattern set. The release notes carry the backtrace.\n",
)
swap(f"gh release download v{OLD} --repo timfromhcs/HSCL1", f"$ gh release download v{VERSION} --repo timfromhcs/HSCL1\n")
swap(f"### Release Checksums (v{OLD})", f"### Release Checksums (v{VERSION})\n")
for name, digest in sorted(sums.items()):
    if name == ISO:
        continue
    swap(f"HSCL1-{OLD}-amd64.iso.{name.rsplit('.', 1)[-1]}", f"{digest}  {name}\n")
swap("400fb9d7aca53ef4f2b4926fb26732e0cd987b6363fc0f9800e2591d8e951df0  HSCL1", f"{SHA}  {ISO}\n")

for i, ln in enumerate(lines):
    if "not rebuilt for 0.1.6 or 0.1.7;" in ln:
        lines[i] = ln.replace("not rebuilt for 0.1.6 or 0.1.7;", "not rebuilt for 0.1.6, 0.1.7 or 0.1.8;")
        replaced.append("not rebuilt for")

text = "".join(lines).replace(f"(`{OLD}`)", f"(`{VERSION}`)")
readme.write_text(text, encoding="utf-8", newline="\n")
print(f"README: {len(replaced)} edits; ISO {SHA[:12]}. {BYTES} B")
