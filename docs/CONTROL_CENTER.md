# Control Center

The HSCL1 Control Center is a Qt 6 / QML application (`apps/control-center`) that renders **live** values
from the `hscl` CLI. It is not a mock and it is not a second implementation of system logic: every value on
screen comes from a CLI call with `--json`, and every call passes through one allowlist.

```
Main.qml (rail + StackLayout)
   └─ pages/<Name>Page.qml      one page per area, built on components/HcsPage.qml
        └─ Fetcher.qml         one CLI request, exposed as `result` / `error`
             └─ CliBackend      C++ allowlist, QProcess, JSON parse (no shell)
```

## Pages (11)

| Page | CLI source | Kind |
|---|---|---|
| Overview | `system info`, `security status`, `doctor` | read-only |
| Appearance | `appearance theme list`, `appearance theme set <id> [--dry-run]` | one write action, previewable |
| Security | `security status`, `doctor` | read-only |
| Privacy | `privacy status` | read-only |
| Security Lab | `lab status` | read-only |
| Local AI | `ai detect` | read-only |
| Updates & Recovery | `system updates --check`, `recovery status` | read-only |
| Developer | `dev status` | read-only |
| Language & Region | `language status` | read-only |
| Miner | `miner status`, `miner probe <host>` | read-only |
| About | `version` | read-only |

The only state-changing request is **Appearance → Apply**, and it is offered next to a **Preview** that runs
the same command with `--dry-run`. Everything else stays in the terminal, where the command can ask for the
attestation phrase (the `lab` subcommands), a confirmation or `sudo`.

## The allowlist is the security boundary

`CliBackend::isAllowed` accepts a finite list of argument vectors. It rejects anything else before a process
is started, and it appends `--json` itself. Consequences:

* no shell, no string concatenation, no user-supplied path or option;
* `miner probe <host>` validates the host with `^[A-Za-z0-9][A-Za-z0-9.-]{0,63}$`;
* `appearance theme set` validates the theme id with `^hcs-[a-z0-9]+(-[a-z0-9]+)*$`;
* **setters and installers are not reachable**: `system updates --install`, `lab run`, `lab toolset install`,
  `dev setup`, `language set`, `recovery snapshots create` and `privacy tor` are all refused.

Two gates keep it honest:

```console
# every static request in a page must be on the allowlist
$ python -m pytest tests/unit/test_cc_pages.py -q
# the allowlist itself, in C++
$ bash scripts/dev/qml-gate.sh        # builds and runs tests/cpp/tst_backend.cpp
```

## One page frame

`components/HcsPage.qml` owns the scroll container, the single page heading (`Accessible.Heading` with a
name), the one-line description, the refresh button and the error banner. A page supplies `title`,
`subtitle`, its `Fetcher`s and `Card`s, and sets `error` from the fetchers. This is what keeps 11 pages
consistent: the heading level, the spacing rhythm, the error wording and the refresh affordance cannot drift
per page. `tests/unit/test_cc_accessibility.py` fails if a page draws its own heading.

## Accessibility

* every control has an `Accessible.name` that says *what* it acts on (`Apply HCS Nord`, not `Apply`);
* every page title is a heading with a name, set once in `HcsPage.qml`;
* the navigation rail is a keyboard list (`Accessible.PageTab`), reachable with Tab and driven by the arrow
  keys; `tests/qml/tst_pages.qml` covers it;
* there is no animation at all, so `prefers-reduced-motion` is honoured by construction;
* the window minimum is 800×520, the rail is 270 px wide and elides only as a last resort; `Row2` lets a long
  row label wrap instead of clipping it (measured with the German `Sicherungsordner vorhanden`), and a page
  title wraps to two lines before it elides.

## Typography

`themes/tokens/tokens.json` names **Inter** as the UI family and `Theme.qml` mirrors it. Until 2026-11-13 that
token was dead: nothing applied it, so the panel used the platform font. `main.cpp` now sets the application
font to Inter **when the family is installed** and keeps the platform font otherwise. No font is bundled, so a
missing family cannot break the UI; the ISO ships the distribution's UI font.

## Languages

Every user-visible string is a `qsTr()` literal. `i18n/hscl-cc_de.ts` and `hscl-cc_fr.ts` must carry a
non-empty translation for every source string; `tests/unit/test_cc_i18n.py` fails otherwise. Regenerate the
catalogues after adding a string:

```console
$ lupdate apps/control-center/qml -ts apps/control-center/i18n/hscl-cc_de.ts apps/control-center/i18n/hscl-cc_fr.ts -locations none -no-obsolete
```

Then fill the new entries (lrelease compiles them at package build time).

## Adding a page

1. Confirm the CLI command exists, is read-only and supports `--json`: read its `--help`, then run it.
2. Add the vector to `CliBackend::isAllowed` (and to `tst_backend.cpp`, including a rejected variant).
3. Write `pages/<Name>Page.qml` as an `HcsPage` with `title`, `subtitle`, fetchers and cards.
4. Register the type in `qml/qmldir` and add the page to `Main.qml` **and** to `pageTitles` in the same order.
5. Add the strings to both `.ts` files.
6. Extend `tests/qml/tst_pages.qml` with a mock answer and an assertion on a *distinctive* value, so a
   constant would fail.
7. Run `bash scripts/dev/qml-gate.sh` and `python -m pytest tests/unit/test_cc_pages.py tests/unit/test_cc_i18n.py tests/unit/test_cc_accessibility.py -q`.

## What is not there

* **No display, network, user, application or update-installation page.** Those need commands that write
  system state; building a button now would either fake the action or need a privileged helper that does not
  exist yet.
* **No Flatpak switch.** The base image does not ship Flatpak; `docs/KNOWN_LIMITATIONS.md` used to imply a
  switch in this panel and has been corrected.
* **No root path.** The panel runs unprivileged and never asks for a password. Any future privileged action
  must go through a narrow Polkit action with validated arguments, not through a wider allowlist.
* **No booted-VM screenshot of the six newest pages yet.** They are covered by the QML suite, lint and a
  rendered check: the app was built and run under Xvfb with a fake `hscl` that prints the real JSON shapes, and
  all 11 pages were photographed in English and four in German (`artifacts/cc-render-2026-11-13/`, ignored by
  git). That proves layout and translation fit, **not** that the pages match a booted guest - the CLI answers
  in those images are mocked, so they are not showcase material.
