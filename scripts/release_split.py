"""Split a large image into GitHub-sized parts and write SHA256SUMS, natively on Windows.

Why this exists: scripts/release-split.sh is correct but was run through /mnt/e (9p) from WSL and
managed ~4 MB/s on 2026-11-10, i.e. ~20 minutes for a 4.8 GB image. This does the same job with
plain buffered file IO and hashlib, and reproduces the same output contract:

    OUTDIR/<IMAGE>.part000, .part001, ...          (PART_MIB each, last one short)
    OUTDIR/SHA256SUMS                              one line per part + one for the whole image

Usage: python scripts/release_split.py IMAGE OUTDIR [PART_MIB]
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

CHUNK = 8 * 1024 * 1024


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def main(argv: list[str]) -> int:
    if len(argv) < 3 or len(argv) > 4:
        print(__doc__.strip().splitlines()[-1], file=sys.stderr)
        return 2
    image = Path(argv[1])
    outdir = Path(argv[2])
    part_mib = int(argv[3]) if len(argv) == 4 else 1900
    if not image.is_file():
        print(f"missing image: {image}", file=sys.stderr)
        return 2
    if not 1 <= part_mib <= 1950:
        print("PART_MIB must be 1..1950 (GitHub's per-file limit is 2 GiB)", file=sys.stderr)
        return 2
    outdir.mkdir(parents=True, exist_ok=True)
    existing = list(outdir.glob(f"{image.name}.part*"))
    if existing:
        print(f"refusing to overwrite {len(existing)} existing part(s) in {outdir}", file=sys.stderr)
        return 2

    part_bytes = part_mib * 1024 * 1024
    parts: list[Path] = []
    with image.open("rb") as src:
        index = 0
        while True:
            block = src.read(part_bytes)
            if not block:
                break
            target = outdir / f"{image.name}.part{index:03d}"
            target.write_bytes(block)
            parts.append(target)
            print(f"wrote {target.name} ({len(block)} bytes)")
            index += 1
    if not parts:
        print("image is empty", file=sys.stderr)
        return 2

    lines = [f"{sha256_of(p)}  {p.name}" for p in parts]
    lines.append(f"{sha256_of(image)}  {image.name}")
    # newline="\n" is not cosmetic: on Windows the default would write CRLF, and `sha256sum -c` on Linux
    # then treats the "\r" as part of the file name and fails every line. The 0.1.5 and 0.1.6 releases
    # shipped that way until a cloud verifier step caught it (2026-11-11).
    (outdir / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {len(parts)} part(s) and {outdir / 'SHA256SUMS'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
