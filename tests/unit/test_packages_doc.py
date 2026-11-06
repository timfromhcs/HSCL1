"""docs/PACKAGES.md must be generated from the real control files (no hand-written drift)."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/gen_packages_doc.py"


def run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, cwd=ROOT)


def test_doc_is_current():
    r = run("--check")
    assert r.returncode == 0, r.stdout + r.stderr


def test_every_control_file_is_represented():
    sys.path.insert(0, str(ROOT / "scripts"))
    import gen_packages_doc as g  # noqa: PLC0415

    rows = g.collect()
    controls = sorted(p for p in (ROOT / "packages/debian").glob("*/DEBIAN/control"))
    assert len(rows) == len(controls) >= 8
    for row in rows:
        assert row["package"].startswith("hscl-")
        assert row["version"]
        assert len(row["purpose"]) > 10, row
    doc = (ROOT / "docs/PACKAGES.md").read_text(encoding="utf-8")
    for row in rows:
        assert f"`{row['package']}`" in doc


def test_versions_are_the_build_placeholder():
    """The release version comes from VERSION at build time; a hard-coded one would silently ship stale."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import gen_packages_doc as g  # noqa: PLC0415

    for row in g.collect():
        assert row["version"] == "0.0.0", f"{row['package']} hard-codes version {row['version']}"


def test_purpose_uses_the_synopsis_not_the_long_text():
    sys.path.insert(0, str(ROOT / "scripts"))
    import gen_packages_doc as g  # noqa: PLC0415

    assert g.purpose("Short line.\n Long second line") == "Short line"
    assert g.purpose("A | pipe") == "A \\| pipe"
