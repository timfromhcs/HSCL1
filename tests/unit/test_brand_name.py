"""HSCL1 stands for Hypercharged Supreme Computing Layout 1 (owner decision); the name is stated in every user-facing place and `hscl1` is a program."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LONG = "Hypercharged Supreme Computing Layout 1"
PLACES = [
    "README.md",
    "packages/debian/hscl-branding/os-release.in",
    "packages/debian/hscl-branding/etc/calamares/branding/hscl1/show.qml",
    "apps/control-center/qml/pages/AboutPage.qml",
    "handbook/en/src/introduction.md",
    "handbook/de/src/introduction.md",
    "handbook/fr/src/introduction.md",
    "website/content/en.json",
    "website/content/de.json",
    "website/content/fr.json",
    "docs/BRAND.md",
]


def test_the_full_name_appears_in_every_user_facing_place():
    for rel in PLACES:
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert LONG in text, rel


def test_product_name_is_still_written_hscl1_everywhere_it_is_defined():
    rs = (ROOT / "cli/hscl/src/main.rs").read_text(encoding="utf-8")
    assert 'pub const PRODUCT: &str = "HSCL1";' in rs and f'pub const EXPANSION: &str = "{LONG}";' in rs


def test_hscl1_is_shipped_as_a_program_and_checked_in_the_image():
    assert 'ln -sf hscl "$stage/usr/bin/hscl1"' in (ROOT / "scripts/build-deb.sh").read_text(encoding="utf-8")
    assert "hscl1 program" in (ROOT / "distro/live/verify-image.sh").read_text(encoding="utf-8")
