"""The live session must get a locale it can actually use, not just a variable that claims one.

History: commit 97446c6 added `LANG="en_US.UTF-8"` to `/etc/default/locale` by *appending* it only when no
`LANG=` line existed. The base image already ships `LANG=C.UTF-8`, so the append never happened - and the
image gate added with it then failed the first build that ran (0.1.7, 2026-11-12). Nothing else noticed,
because no test exercised the hook's locale branch.

Two things are pinned here: the value is *replaced*, and the locale is *generated*. A variable pointing at a
locale that was never built makes the session fall back to C with a "cannot change locale" warning, which is
worse than saying nothing. The end-to-end proof is the image gate on a real build, not this file.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / "distro/live/hooks/010-hscl-defaults.sh"
GATE = ROOT / "distro/live/verify-image.sh"


def test_the_hook_replaces_an_existing_lang_instead_of_appending():
    text = HOOK.read_text(encoding="utf-8")
    assert re.search(r"""sed -i 's\|\^LANG=\.\*\|LANG="en_US\.UTF-8"\|'""", text), (
        "the hook must rewrite an existing LANG= line; appending only when it is absent does nothing on the "
        "base image, which already sets LANG=C.UTF-8"
    )
    # and it must still handle a file that has no LANG= at all
    assert """printf 'LANG="en_US.UTF-8"\\n' >> "$locale_file\"""" in text


def test_the_hook_generates_the_locale_and_fails_loudly_when_it_cannot():
    text = HOOK.read_text(encoding="utf-8")
    assert "locale-gen en_US.UTF-8" in text, "the locale must be generated, not only named"
    assert 'chroot "$ROOTFS" locale-gen' in text, "it must run inside the target root, not on the build host"
    assert "would fall back to C" in text, "a failed locale-gen needs a message that names the consequence"
    assert "exit 1" in text, "a failed locale-gen must fail the build"


def test_the_image_gate_proves_the_locale_exists_not_only_the_variable():
    text = GATE.read_text(encoding="utf-8")
    assert 'check "live locale is set"' in text
    assert 'check "live locale is generated"' in text, (
        "without this the gate passes while the session has no en_US.UTF-8 to use"
    )
    assert "locale -a" in text, "the gate must ask the target what locales it has"
