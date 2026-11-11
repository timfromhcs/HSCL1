"""README checksums and website release metadata must describe the same release.

They did not once: the README described `v0.1.4-alpha.0` while the website data had already moved, and
the same class of drift is easy to reintroduce by hand. This test needs no ISO and no network, so it
can run in the normal unit tier: it parses the checksum block from the README and compares it with
`website/data/release.json`.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
README = (ROOT / "README.md").read_text(encoding="utf-8")
WEBSITE = json.loads((ROOT / "website/data/release.json").read_text(encoding="utf-8"))

HASH_LINE = re.compile(r"^([0-9a-f]{64})\s+(HSCL1-\S+-amd64\.iso(?:\.part\d+)?)\s*$", re.MULTILINE)


def readme_hashes() -> dict[str, str]:
    return {name: digest for digest, name in HASH_LINE.findall(README)}


def release() -> dict:
    rel = WEBSITE.get("release") or {}
    assert rel, "website/data/release.json carries no release object"
    return rel


def test_the_readme_publishes_at_least_one_iso_hash():
    assert readme_hashes(), "README lists no ISO checksums"


def test_the_readme_iso_hash_matches_the_website():
    rel = release()
    name = f"HSCL1-{rel['tag'].removeprefix('v')}-amd64.iso"
    hashes = readme_hashes()
    assert name in hashes, f"README does not list {name}; it lists {sorted(hashes)}"
    assert hashes[name] == rel["whole_image"]["sha256"], "README and website quote different ISO digests"


def test_every_part_in_the_readme_is_a_website_asset():
    asset_names = {a.get("name") for a in release().get("assets", [])}
    parts = {n for n in readme_hashes() if ".part" in n}
    assert parts, "README lists no split parts"
    missing = parts - asset_names
    assert not missing, f"README advertises parts the website does not list: {sorted(missing)}"


def test_the_readme_version_matches_the_website_tag():
    rel = release()
    version = rel["tag"].removeprefix("v")
    assert f"HSCL1-{version}-amd64.iso" in readme_hashes()
    # the download instructions must name the same tag, not an older one
    assert f"gh release download {rel['tag']}" in README, f"README download steps do not use {rel['tag']}"
