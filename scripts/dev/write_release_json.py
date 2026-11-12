"""Write website/data/release.json for the set that is about to be published.

Every value comes from the release directory itself (names, sizes, hashes) - nothing is guessed. `published_at`
is deliberately left out here and filled in by `scripts/fetch_release_meta.py` from the real GitHub release
after the upload, so the committed file ends up derived from GitHub rather than from this script.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERSION = sys.argv[1] if len(sys.argv) > 1 else "0.1.7-alpha.0"
TAG = f"v{VERSION}"
REPO = "timfromhcs/HSCL1"
SET = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "artifacts" / f"release-{VERSION}-set"

sums = {}
for line in (SET / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
    if line.strip():
        digest, name = line.split("  ", 1)
        sums[name.strip()] = digest.strip()

iso_name = f"HSCL1-{VERSION}-amd64.iso"
assert iso_name in sums, f"{iso_name} not in SHA256SUMS"

assets = []
for path in sorted(SET.iterdir()):
    if path.name in {"dpkg-status"}:
        continue
    if path.suffix == ".iso":
        continue  # the whole image is not uploaded; only the parts are
    assets.append({
        "name": path.name,
        "size": path.stat().st_size,
        "url": f"https://github.com/{REPO}/releases/download/{TAG}/{path.name}",
    })

doc = {
    "repo": REPO,
    "release": {
        "tag": TAG,
        "name": f"HSCL1 {VERSION}",
        "prerelease": True,
        "url": f"https://github.com/{REPO}/releases/tag/{TAG}",
        "assets": assets,
        "whole_image": {
            "name": iso_name,
            "sha256": sums[iso_name],
            "bytes": (SET / iso_name).stat().st_size,
        },
    },
}
out = ROOT / "website" / "data" / "release.json"
out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
print(f"wrote {out} with {len(assets)} assets; iso {sums[iso_name][:12]}. {(SET / iso_name).stat().st_size} B")
