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


def test_security_baseline_unit_has_the_measured_strict_sandbox():
    """VM measurement 2026-11-06: these options took the exposure of hscl-security-baseline from 7.6 to 2.5 and ufw still worked."""
    sec = service_section(ROOT / "distro/security/systemd/hscl-security-baseline.service")
    assert sec["ProtectSystem"] == "strict" and sec["StateDirectory"] == "hscl"
    assert sec["PrivateDevices"] == "yes" and sec["MemoryDenyWriteExecute"] == "yes"
    caps = set(sec["CapabilityBoundingSet"].split())
    assert caps == {"CAP_NET_ADMIN", "CAP_NET_RAW", "CAP_DAC_OVERRIDE", "CAP_FOWNER", "CAP_CHOWN"}
    rw = sec["ReadWritePaths"].split()
    assert all(p.startswith("-/") for p in rw), "every path must be optional (leading '-')"
    assert "-/etc/default/ufw" in rw  # `ufw enable` writes ENABLED=yes there (found by the VM run)
    assert "/etc/ufw" in sec["ReadWritePaths"] and not any(p.rstrip("/") in ("-/usr", "-/etc", "-/") for p in rw)
