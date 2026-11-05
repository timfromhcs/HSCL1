"""APT source policy: only signed Ubuntu 'resolute' pockets; no Kali/Debian/PPA/trusted=yes."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ALLOWED_SUITES = {"resolute", "resolute-updates", "resolute-security", "resolute-backports"}
ALLOWED_HOSTS = {"archive.ubuntu.com", "security.ubuntu.com", "repo.hcs.invalid"}  # last one: reserved for a future signed HCS repo
FORBIDDEN = re.compile(r"kali|debian|ppa\.launchpad|launchpadcontent|\[trusted=yes\]|trusted:\s*yes|allow-insecure", re.I)


def stanzas(text: str):
    for block in re.split(r"\n\s*\n", text.strip()):
        fields = {}
        for line in block.splitlines():
            if line.startswith("#") or ":" not in line:
                continue
            k, v = line.split(":", 1)
            fields[k.strip().lower()] = v.strip()
        if fields:
            yield fields


def violations(text: str) -> list[str]:
    bad = []
    if FORBIDDEN.search("\n".join(l for l in text.splitlines() if not l.lstrip().startswith("#"))):
        bad.append("forbidden source keyword")
    for s in stanzas(text):
        host = re.sub(r"^https?://([^/]+).*$", r"\1", s.get("uris", ""))
        if host not in ALLOWED_HOSTS:
            bad.append(f"host not allowed: {host}")
        for suite in s.get("suites", "").split():
            if suite not in ALLOWED_SUITES:
                bad.append(f"suite not allowed: {suite}")
        if "signed-by" not in s:
            bad.append("missing Signed-By")
    return bad


def test_shipped_policy_is_clean():
    text = (ROOT / "distro/base/apt/hscl-sources.sources").read_text(encoding="utf-8")
    assert violations(text) == []


def test_detects_bad_sources():
    kali = "Types: deb\nURIs: http://http.kali.org/kali\nSuites: kali-rolling\nComponents: main\nSigned-By: /x.gpg\n"
    assert violations(kali)
    unsigned = "Types: deb\nURIs: http://archive.ubuntu.com/ubuntu/\nSuites: resolute\nComponents: main\n"
    assert "missing Signed-By" in violations(unsigned)
    interim = "Types: deb\nURIs: http://archive.ubuntu.com/ubuntu/\nSuites: resolute-proposed questing\nComponents: main\nSigned-By: /x.gpg\n"
    assert any("suite not allowed" in v for v in violations(interim))
    trusted = "Types: deb\nURIs: http://archive.ubuntu.com/ubuntu/\nSuites: resolute\nComponents: main\nSigned-By: /x.gpg\n# x\nTrusted: yes\n"
    assert violations(trusted)


if __name__ == "__main__":
    sys.exit(0)
