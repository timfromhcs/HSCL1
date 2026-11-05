"""Baseline sysctl file: exact hardening values, nothing that weakens the kernel."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FILE = ROOT / "distro/security/sysctl.d/90-hscl.conf"

REQUIRED = {
    "kernel.kptr_restrict": {"2"},
    "kernel.dmesg_restrict": {"1"},
    "kernel.unprivileged_bpf_disabled": {"1"},
    "kernel.yama.ptrace_scope": {"1", "2", "3"},
    "fs.protected_symlinks": {"1"},
    "fs.protected_hardlinks": {"1"},
    "fs.suid_dumpable": {"0"},
    "net.ipv4.conf.all.rp_filter": {"1", "2"},
    "net.ipv4.conf.all.accept_redirects": {"0"},
    "net.ipv4.conf.all.send_redirects": {"0"},
    "net.ipv4.tcp_syncookies": {"1"},
}
FORBIDDEN_KEYS = re.compile(r"randomize_va_space|mmap_min_addr|nospec|mitigations|ptrace_scope\s*=\s*0|ip_forward")


def parse():
    out = {}
    for line in FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            k, v = (x.strip() for x in line.split("=", 1))
            assert k not in out, f"duplicate key {k}"
            out[k] = v
    return out


def test_required_hardening_values_present():
    s = parse()
    for key, allowed in REQUIRED.items():
        assert s.get(key) in allowed, f"{key}={s.get(key)!r} not in {allowed}"


def test_nothing_weakens_the_kernel():
    text = "\n".join(l for l in FILE.read_text(encoding="utf-8").splitlines() if not l.strip().startswith("#"))
    assert not FORBIDDEN_KEYS.search(text)
