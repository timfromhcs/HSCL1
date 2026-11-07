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


def test_the_submenus_are_named_in_english_german_and_french():
    root = ET.fromstring(MENU.read_text(encoding="utf-8"))
    top = root.find("Menu")
    assert top is not None
    langs = {n.get("{http://www.w3.org/XML/1998/namespace}lang") or "C" for n in top.findall("Name")}
    assert {"C", "de", "fr"} <= langs, langs


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
    """A <Directory> names a .directory file that supplies the section icon/comment. A dangling
    reference is silent in a launcher, so it is checked: either the file is shipped here or the
    element is absent (the <Name> then comes from this menu file alone)."""
    root = ET.fromstring(MENU.read_text(encoding="utf-8"))
    refs = [d.text for d in root.iter("Directory") if d.text]
    missing = [r for r in refs if not (MENU.parent / r).is_file()]
    assert not missing, f"<Directory> without a shipped file: {missing}"
