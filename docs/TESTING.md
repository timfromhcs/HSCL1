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

## Stress and fault gate (disposable VM only)

`scripts/stress_vm.sh [--out DIR]` runs `stress-ng --klog-check --metrics-brief`, `fio` (4k randrw, 1 GiB file,
70 % read) and `memtester 256M 1`, and writes `artifacts/stress/<UTC stamp>/summary.json` plus one log per tool.

The script refuses to run (exit 2) unless **both** `HSCL_IN_DISPOSABLE_VM=1` is set and the marker file
`/etc/hscl-vm-marker` exists; the VM harness writes that marker into a guest it booted for the purpose. `fio` writes a
1 GiB file, so the script also refuses with less than 3 GiB free. A failing or missing tool still produces the summary
and exits 1 - the JSON is evidence, not a success badge.

```bash
# inside the disposable guest only
HSCL_IN_DISPOSABLE_VM=1 scripts/stress_vm.sh --out /tmp/stress
```

Tests (fake `stress-ng`/`fio`/`memtester` on `PATH`, no real load):
`python -m pytest tests/unit/test_stress_vm.py -q`.

## Evidence rules

Status words (`TESTED`, `VM-VERIFIED`, …) follow AGENTS.md §0.4 and are recorded in `docs/BUILD_LOG.md` with the
command, date and artefact path. Screenshots and ISOs live under `artifacts/` and are not committed.
