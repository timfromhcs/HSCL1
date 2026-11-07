"""Plan F1: user-facing text must not claim atomic / immutable updates or booting into a snapshot (HSCL1 updates with APT; the base
Ubuntu archive has no grub-btrfs, so boot-into-snapshot does not exist). Explicit negations are allowed."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import check_update_claims as cu  # noqa: E402


def write(root: Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


@pytest.mark.parametrize(
    "line",
    [
        "HSCL1 ships atomic updates.",
        "Updates are Atomic and safe.",
        "You can boot into a snapshot after a failed update.",
        "Booting into snapshot is supported.",
        "The system is immutable.",
        "Das System hat atomare Updates.",
        "Un système immuable avec des mises à jour atomiques.",
        "Ein unveränderliches Basissystem.",
    ],
)
def test_affirmative_claims_are_flagged(tmp_path, line):
    write(tmp_path, "README.md", line + "\n")
    errs = cu.check(tmp_path)
    assert errs and errs[0].startswith("README.md:1"), errs


@pytest.mark.parametrize(
    "line",
    [
        "Updates are not atomic; they use APT.",
        "Booting into a snapshot is not available (no grub-btrfs).",
        "We never claim an immutable system.",
        "There is no immutable root.",
        "Updates are NOT atomic.",
        "Die Updates sind nicht atomar.",
        "Es gibt kein unveränderliches System.",
        "Les mises à jour ne sont pas atomiques.",
        "Il n'y a pas de système immuable.",
        "Without atomic updates, a power cut can leave packages half installed.",
        "There are no immutable images, nor booting into a snapshot.",
        "Neither atomic updates nor booting into a snapshot exist.",
    ],
)
def test_explicit_negations_are_allowed(tmp_path, line):
    write(tmp_path, "docs/INSTALLATION.md", line + "\n")
    assert cu.check(tmp_path) == []


def test_unrelated_words_do_not_match(tmp_path):
    write(tmp_path, "README.md", "Atomically small steps. The atom model. Immutably typed.\nA snapshot of the disk image is a file.\n")
    assert cu.check(tmp_path) == []


def test_research_plans_and_dependencies_are_not_scanned(tmp_path):
    for rel in ("docs/research/x.md", "docs/superpowers/plans/p.md", "website/node_modules/m/readme.md", "website/dist/index.html", "target/x.md"):
        write(tmp_path, rel, "bootc gives atomic immutable updates; boot into a snapshot.\n")
    assert cu.check(tmp_path) == []


def test_website_content_is_scanned(tmp_path):
    write(tmp_path, "website/content/en.json", '{"hero": "Immutable by design"}\n')
    write(tmp_path, "website/src/pages/index.astro", "<p>Atomic updates</p>\n")
    errs = cu.check(tmp_path)
    assert len(errs) == 2 and all("website/" in e for e in errs)


def test_message_has_file_line_and_the_matched_text(tmp_path):
    write(tmp_path, "docs/CLI.md", "ok line\nThis is an immutable image.\n")
    assert cu.check(tmp_path) == ["docs/CLI.md:2: unbacked update claim 'immutable' - say what is true or negate it explicitly"]


def test_the_real_repository_makes_no_unbacked_update_claims():
    assert cu.check(ROOT) == []


def test_cli_exit_codes(tmp_path, capsys):
    write(tmp_path, "README.md", "Atomic updates.\n")
    assert cu.main(["--root", str(tmp_path)]) == 1
    assert "unbacked update claim" in capsys.readouterr().out
    write(tmp_path, "README.md", "Updates are not atomic.\n")
    assert cu.main(["--root", str(tmp_path)]) == 0


def test_the_gate_really_scans_the_user_facing_files_of_this_repository():
    """A gate that scans nothing would report 'no claims' forever."""
    files = {p.relative_to(ROOT).as_posix() for p in cu._files(ROOT)}
    assert "README.md" in files
    assert any(f.startswith("docs/") and f.endswith(".md") for f in files)
    assert any(f.startswith("website/") for f in files)
    assert not any(f.startswith(("docs/research/", "docs/superpowers/", "website/node_modules/")) for f in files)
    assert len(files) > 20, len(files)
