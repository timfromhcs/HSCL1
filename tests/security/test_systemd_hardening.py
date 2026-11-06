"""Every HSCL1-owned system unit carries the baseline of sandbox options that cannot break its function.

Deliberately NOT required for the Workshop daemon: ProtectSystem/NoNewPrivileges (it writes into /usr on request and runs
root hooks); that is why it stays inert unless a hypervisor provides the virtio port. Recorded in docs/THREAT_MODEL.md.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UNITS = sorted(ROOT.glob("packages/debian/*/usr/lib/systemd/system/*.service")) + sorted((ROOT / "distro/security/systemd").glob("*.service"))
BASELINE = {
    "ProtectKernelModules": "yes", "ProtectControlGroups": "yes", "LockPersonality": "yes",
    "RestrictRealtime": "yes", "SystemCallArchitectures": "native", "ProtectHostname": "yes",
}


def service_section(path):
    out, inside = {}, False
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("["):
            inside = line == "[Service]"
        elif inside and "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            out[k] = v
    return out


def test_units_were_found():
    assert len(UNITS) >= 4


def test_every_unit_has_the_sandbox_baseline():
    for u in UNITS:
        sec = service_section(u)
        for k, v in BASELINE.items():
            assert sec.get(k) == v, f"{u.name}: {k} should be {v}, is {sec.get(k)!r}"
