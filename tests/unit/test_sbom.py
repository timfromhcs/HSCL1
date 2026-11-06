"""SBOM generator: only installed packages, real Cargo.lock, deterministic, honest licence fields."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/gen_sbom.py"
spec = importlib.util.spec_from_file_location("gen_sbom", SCRIPT)
sb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sb)

STATUS = """Package: bash
Status: install ok installed
Architecture: amd64
Version: 5.2.21-2ubuntu4
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Homepage: http://tiswww.case.edu/php/chet/bash/bashtop.html
Description: GNU Bourne Again SHell
 Bash is an sh-compatible command language interpreter.

Package: oldthing
Status: deinstall ok config-files
Architecture: amd64
Version: 1.0

Package: neverinstalled
Status: install ok not-installed
Architecture: amd64
Version: 2.0

Package: libc6
Status: install ok installed
Architecture: amd64
Version: 2.41-6ubuntu1
"""
LOCK = """version = 3

[[package]]
name = "hscl"
version = "0.1.0"

[[package]]
name = "serde"
version = "1.0.200"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "aa11"
"""


def test_only_installed_packages_are_listed():
    names = [f["Package"] for f in sb.parse_dpkg_status(STATUS)]
    assert names == ["bash", "libc6"]


def test_cargo_skips_workspace_crate_and_keeps_checksum():
    pk = sb.cargo_packages(LOCK)
    assert [p["name"] for p in pk] == ["serde"]
    assert pk[0]["checksums"] == [{"algorithm": "SHA256", "checksumValue": "aa11"}]
    assert pk[0]["externalRefs"][0]["referenceLocator"] == "pkg:cargo/serde@1.0.200"


def test_document_is_valid_shaped_deterministic_and_makes_no_licence_claim():
    a = sb.build("HSCL1", "0.1.0", "2026-11-06T00:00:00Z", STATUS, LOCK)
    b = sb.build("HSCL1", "0.1.0", "2026-11-06T00:00:00Z", STATUS, LOCK)
    assert a == b
    assert a["spdxVersion"] == "SPDX-2.3" and a["documentNamespace"].startswith("https://github.com/timfromhcs/HSCL1/sbom/")
    ids = [p["SPDXID"] for p in a["packages"]]
    assert len(ids) == len(set(ids)) == 4  # root + bash + libc6 + serde
    for p in a["packages"]:
        assert p["licenseConcluded"] == "NOASSERTION" and p["licenseDeclared"] == "NOASSERTION"
    rel = {(r["relationshipType"], r["relatedSpdxElement"]) for r in a["relationships"]}
    assert ("DESCRIBES", "SPDXRef-Root") in rel and len([r for r in a["relationships"] if r["relationshipType"] == "CONTAINS"]) == 3


def test_duplicate_package_ids_are_disambiguated_not_dropped():
    dup = STATUS + "\nPackage: bash\nStatus: install ok installed\nArchitecture: amd64\nVersion: 5.2.21-2ubuntu4\n"
    d = sb.build("X", "1", "2026-11-06T00:00:00Z", dup, None)
    ids = [p["SPDXID"] for p in d["packages"]]
    assert len(ids) == len(set(ids)) and sum(1 for p in d["packages"] if p["name"] == "bash") == 2


def test_cli_on_the_real_cargo_lock(tmp_path):
    out = tmp_path / "sbom.json"
    r = subprocess.run([sys.executable, str(SCRIPT), "--name", "HSCL1-cli", "--version", "0.1.0", "--cargo-lock", str(ROOT / "Cargo.lock"),
                        "--created", "2026-11-06T00:00:00Z", "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert len(doc["packages"]) > 20
    assert any(p["name"] == "clap" for p in doc["packages"])


def test_cli_requires_an_input(tmp_path):
    r = subprocess.run([sys.executable, str(SCRIPT), "--name", "x", "--version", "1", "--out", str(tmp_path / "o.json")], capture_output=True, text=True)
    assert r.returncode == 2
