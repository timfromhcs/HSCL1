"""The pinned Kali image reference must satisfy the same rule the Rust generator enforces (name@sha256:<64 hex>), and stay a registry digest, not a tag."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PIN = ROOT / "containers/kali/image.pin"
REF = re.compile(r"^[a-z0-9./_:-]+@sha256:[0-9a-f]{64}$")


def active_lines():
    return [l.strip() for l in PIN.read_text(encoding="utf-8").splitlines() if l.strip() and not l.lstrip().startswith("#")]


def test_pin_is_a_single_digest_reference_to_the_official_image():
    lines = active_lines()
    assert len(lines) == 1, lines
    assert REF.match(lines[0]), lines[0]
    assert lines[0].startswith("docker.io/kalilinux/kali-rolling@sha256:")  # official image only, never a third-party namesake


def test_pin_records_source_and_scopes_the_measured_pull_to_the_builder():
    text = PIN.read_text(encoding="utf-8")
    assert "hub.docker.com/v2/repositories/kalilinux/kali-rolling" in text and "2026-11-06" in text
    assert "2026-11-08" in text and "pulled and inspect-verified" in text
    assert "builder only" in text and "not HSCL1 guest/ISO proof" in text
    evidence = ROOT / "docs/research/2026-11-08-security-lab-builder-probe.md"
    report = evidence.read_text(encoding="utf-8")
    assert active_lines()[0].split("@", 1)[1] in report
    assert "pull.log" in report and "image-inspect.json" in report
    assert "HSCL1 guest/runtime still open" in (ROOT / "docs/SECURITY_LAB.md").read_text(encoding="utf-8")
