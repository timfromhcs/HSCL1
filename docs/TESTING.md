# Testing

## Fast local checks (no VM)

```console
$ python scripts/forge.py check                 # the gate: pytest, WSL changed tests, bash -n, shellcheck,
                                                # secret scan, doc-command parity, QML tests when QML changed
$ python -m pytest tests -q                       # unit + security + handbook + QML-string tests
$ cargo fmt --check && cargo clippy --all-targets -- -D warnings && cargo test
$ python scripts/check-tokens.py                  # design tokens: contrast (WCAG AA) for all themes
$ python scripts/gen_qml_theme.py --check         # Theme.qml in sync with the tokens
```

Since 2026-11-09 `forge check` also runs `scripts/dev/qml-gate.sh` whenever a QML file changed:
`qmltestrunner` over `tests/qml_plugin` and `apps/control-center/tests/qml`, plus `qmllint` on every
shipped QML file (fail on `[syntax]`/`Error:`, warning budget ratcheted at 152). The Qt binaries live
in `/usr/lib/qt6/bin` in WSL even when they are not on `PATH`.

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

### Writing an installer scenario

Calamares runs as a **centred 1104×668 window** since 2026-11-09, not fullscreen. Click coordinates carried over
from the old fullscreen layout land on the wrong button: the scenario clicked (0.883, 0.903) for "Next" and hit
**Cancel**, which opened the "Cancel Installation?" dialog, so the run never left the welcome page.
Measured geometry on a 1280×800 guest (fractions of the screen):

| Control | Pixels | Fraction |
|---|---|---|
| Back | 949, 715 | 0.741, 0.894 |
| Next | 1041, 715 | **0.813, 0.894** |
| Cancel | 1143, 715 | 0.893, 0.894 |
| Language combo | 762, 608 | 0.595, 0.760 |
| "No" in the cancel dialog | 795, 413 | 0.621, 0.516 |
| Partitions: "Erase disk" radio | 293, 170 | 0.229, 0.2125 |
| Partitions: "Manual partitioning" radio | 293, 232 | 0.229, 0.290 |

Re-measure if the window size or the screen resolution changes. `tests/visual/scenarios/installer-walk.json`
clicks through the wizard with the measured coordinates and records one screenshot per page - use it to
re-derive coordinates. Attach a disposable disk (`--disk artifacts/vdisks/walk-40g.qcow2 --disk-size 40G`);
without one Calamares stops on the welcome page with "There is not enough drive space. At least 8 GiB is
required." and a disabled Next button, which is the intended behaviour and not a scenario failure.

`ret` alone does not advance the wizard: it only presses the focused button, and on a blocked page Next is
disabled. Use `ret` to launch the installer from Kickoff, then click.

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
