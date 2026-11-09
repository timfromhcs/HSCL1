"""G26a: the shipped XDG menu file is valid, uses registered categories and is bilingual.

The menu file decides where applications appear in the launcher. A typo in a category name or an
empty submenu is invisible until someone boots the image, so it is checked here instead: XML well
formed, every Include category from the freedesktop registered main categories, no empty submenu,
and an English name plus a German and a French one.
"""
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MENU = ROOT / "packages/debian/hscl-branding/etc/xdg/menus/applications-merged/hscl1.menu"

# https://specifications.freedesktop.org/menu-spec/latest/apa.html (main categories)
MAIN_CATEGORIES = {
    "AudioVideo", "Audio", "Video", "Development", "Education", "Game", "Graphics",
    "Network", "Office", "Science", "Settings", "System", "Utility",
}


def _menus(node):
    """Every <Menu> element with its direct name and include categories."""
    for menu in node.findall("Menu"):
        names = {n.get("{http://www.w3.org/XML/1998/namespace}lang") or "C": (n.text or "")
                 for n in menu.findall("Name")}
        cats = [c.text or "" for inc in menu.findall("Include") for c in inc.findall("Category")]
        yield menu, names, cats
        yield from _menus(menu)


def test_the_menu_file_exists_and_is_well_formed_xml():
    assert MENU.is_file(), f"missing {MENU}"
    ET.fromstring(MENU.read_text(encoding="utf-8"))


def test_every_include_uses_a_registered_main_category():
    root = ET.fromstring(MENU.read_text(encoding="utf-8"))
    bad = []
    for menu, names, cats in _menus(root):
        unknown = [c for c in cats if c not in MAIN_CATEGORIES]
        if unknown:
            bad.append((names.get("C", "?"), unknown))
    assert not bad, f"unknown categories (a launcher would show an empty entry): {bad}"


def test_no_submenu_is_empty_or_duplicated():
    root = ET.fromstring(MENU.read_text(encoding="utf-8"))
    names = []
    for menu, names_by_lang, cats in _menus(root):
        language = names_by_lang.get("C", "")
        assert language, f"a submenu without an English name: {menu.attrib}"
        assert cats, f"submenu {language!r} has no Include/categories (it would be empty)"
        names.append(language)
    assert len(names) == len(set(names)), f"duplicate submenu names: {names}"


def test_submenus_carry_only_the_default_name():
    """Localised <Name xml:lang> children stopped KDE from merging our sections with the base menu, so
    the launcher listed "Development" next to "Développement" (visual QA 2026-11-09). Translated titles
    belong in the .directory files."""
    root = ET.fromstring(MENU.read_text(encoding="utf-8"))
    offenders = []
    for menu, names_by_lang, _ in _menus(root):
        extra = set(names_by_lang) - {"C"}
        if extra:
            offenders.append((names_by_lang.get("C", "?"), sorted(extra)))
    assert not offenders, f"localised <Name> entries break menu merging: {offenders}"


DIRECTORIES = ROOT / "packages/debian/hscl-branding/usr/share/desktop-directories"


def test_every_section_references_a_localised_directory_file():
    root = ET.fromstring(MENU.read_text(encoding="utf-8"))
    refs = [d.text for d in root.iter("Directory") if d.text]
    assert refs, "sections must reference .directory files for their translated titles"
    for ref in refs:
        path = DIRECTORIES / ref
        assert path.is_file(), f"missing {path}"
        text = path.read_text(encoding="utf-8")
        assert "Type=Directory" in text
        for lang in ("Name=", "Name[de]=", "Name[fr]="):
            assert lang in text, f"{ref}: missing {lang}"
        assert "Icon=" in text, f"{ref}: a section without an icon"


def test_the_three_modes_are_not_invented_as_menu_sections():
    """AGENTS 4.2 lists Security Lab and Privacy sections, but they have no desktop entries yet -
    an empty section would be a button that does nothing. Only real <Name> elements count; the
    comment in the file may of course explain why they are missing."""
    root = ET.fromstring(MENU.read_text(encoding="utf-8"))
    titles = {n.text or "" for menu, _, _ in _menus(root)
              for n in menu.findall("Name")}
    for later in ("Security Lab", "Privacy"):
        assert later not in titles, f"{later} has no desktop entries yet and must not be offered"


def test_any_directory_reference_points_at_a_shipped_file():
    """A <Directory> names a .directory file from $XDG_DATA_DIRS/desktop-directories (not from the menu
    directory). A dangling reference is silent in a launcher, so it is checked against the package."""
    root = ET.fromstring(MENU.read_text(encoding="utf-8"))
    refs = [d.text for d in root.iter("Directory") if d.text]
    missing = [r for r in refs if not (DIRECTORIES / r).is_file()]
    assert not missing, f"<Directory> without a shipped file: {missing}"


def test_the_package_rebuilds_the_ksycoca_cache_after_installing_the_menu():
    """G26a follow-up from the 2026-11-07 research: Plasma reads applications-merged because
    startplasma sets XDG_MENU_PREFIX=plasma- and the base menu carries <DefaultMergeDirs/>, but the
    cache is only rebuilt when kbuildsycoca6 runs. Without it a freshly installed section can be
    missing until the next login, which looks exactly like a broken menu file."""
    post = ROOT / "packages/debian/hscl-branding/DEBIAN/postinst"
    text = post.read_text(encoding="utf-8")
    assert "kbuildsycoca6 --noincremental" in text, "postinst must rebuild the menu cache"
    assert "command -v kbuildsycoca6" in text, "the call must be guarded: kbuildsycoca6 is not always installed"
    # Rebuilding as root would create root-owned caches in the wrong place; the call has to run as a user.
    assert "runuser" in text or "su " in text, "must not create a root-owned ksysca cache"
    # Uninstall must not leave the section behind in the cache either.
    postrm = ROOT / "packages/debian/hscl-branding/DEBIAN/postrm"
    assert "kbuildsycoca6 --noincremental" in postrm.read_text(encoding="utf-8")
