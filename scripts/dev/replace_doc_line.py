"""Replace a whole line identified by a unique ASCII marker (the repo's docs use non-ASCII we must not retype)."""
import sys
from pathlib import Path

path, marker, replacement_file = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
new = replacement_file.read_text(encoding="utf-8").rstrip("\n")
lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
hits = [i for i, ln in enumerate(lines) if marker in ln]
assert len(hits) == 1, f"{path}: marker {marker!r} found {len(hits)} times"
old = lines[hits[0]]
lines[hits[0]] = new + ("\n" if old.endswith("\n") else "")
path.write_text("".join(lines), encoding="utf-8", newline="\n")
print(f"{path}: line {hits[0] + 1} replaced ({len(old)} -> {len(new) + 1} chars)")
