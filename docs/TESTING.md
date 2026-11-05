# Testing

## Fast local checks (no VM)

```console
$ python -m pytest tests -q                       # unit + security + handbook + QML-string tests
$ cargo fmt --check && cargo clippy --all-targets -- -D warnings && cargo test
$ python scripts/check-tokens.py                  # design tokens: contrast (WCAG AA) for all themes
$ python scripts/gen_qml_theme.py --check         # Theme.qml in sync with the tokens
```

Control Center (C++ and QML, needs the Qt 6 dev packages on the builder):

```console
$ cmake -S apps/control-center -B build/cc -G Ninja && cmake --build build/cc && ctest --test-dir build/cc --output-on-failure
```

Shell scripts: `shellcheck -S warning scripts/*.sh distro/live/*.sh distro/live/hooks/*.sh packages/debian/*/build.sh`.

## VM tests

`scripts/qemu_boot_test.py ISO OUTDIR [options]` boots an ISO, takes screenshots over QMP and writes `result.json`.

| Option | Meaning |
|---|---|
| `--firmware uefi\|bios` | firmware |
| `--secure-boot` | OVMF Secure-Boot firmware with Microsoft keys (needs TCG: WHPX has no SMM) |
| `--try-live --dismiss-welcome` | click "Try", close the Plasma Welcome Center, capture `desktop-final.png` |
| `--launch-installer` | double-click the installer icon and capture `installer-N.png` (no disk attached; nothing is written) |
| `--steps FILE.json` | run a scenario (`tests/visual/scenarios/*.json`): keys, text, clicks, named screenshots |
| `--qa-out FILE` | attach the `hscl.qa` virtio port; the guest report (from `hscl-qa`) is written to FILE |

Accelerators: Windows host → native QEMU with WHPX (`winget install SoftwareFreedomConservancy.QEMU`); Linux with
`/dev/kvm` → KVM; otherwise TCG (about 5× slower). Unix sockets do not work on `/mnt/...` drives under WSL: write the
output directory inside the WSL home.

Evaluate a guest report: `python scripts/qa_report.py REPORT.txt` (exit 0 only if all checks pass).

## Evidence rules

Status words (`TESTED`, `VM-VERIFIED`, …) follow AGENTS.md §0.4 and are recorded in `docs/BUILD_LOG.md` with the
command, date and artefact path. Screenshots and ISOs live under `artifacts/` and are not committed.
