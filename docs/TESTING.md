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
| `--qa-out FILE` | attach the `hscl.qa` virtio port; the guest report from the Workshop evidence runner (`packages/debian/hscl-workshop/usr/lib/hscl/workshop/evidence.sh`, started by the udev rule when the port exists) is written to FILE |

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

### End-to-end install and installed-system boot

```console
# 1) install onto a disposable disk (never a real one)
$ python scripts/qemu_boot_test.py artifacts/iso/HSCL1-...-amd64.iso artifacts/install-e2e \
    --firmware uefi --accel whpx --mem 6144 --smp 4 \
    --disk artifacts/vdisks/install-e2e.qcow2 --disk-size 40G \
    --try-live --dismiss-welcome --steps tests/visual/scenarios/install-normal-kickoff.json --timeout 5400

# 2) boot that disk instead of the ISO (iso = the literal string "none")
$ python scripts/qemu_boot_test.py none artifacts/boot-installed \
    --firmware uefi --accel whpx --mem 4096 --smp 4 \
    --disk artifacts/vdisks/install-e2e.qcow2 --login-password 'the password typed in the installer'

# 3) encrypted install: add --unlock-passphrase (and optionally --unlock-first-wrong)
```

`install-normal-kickoff.json` installs unencrypted; ticking "Encrypt system" is a separate run because it
adds a passphrase prompt at every boot.

### Checking a run for a crashed guest

A dead guest looks like "no screenshots changed". `scripts/dev/detect_panic.py DIR` reads every PNG and flags
frames dominated by Ubuntu's panic purple (#772953), then exits 1 so a loop can stop:

```console
$ python scripts/dev/detect_panic.py artifacts/install-luks-final
checked 14 screenshot(s)
PANIC-LIKE: artifacts/install-luks-final/l09-before-finish.png (98% panic purple)
```

Two install runs died that way on 2026-11-10 (`KERNEL PANIC! Attempted to kill init! exitcode=0x0000000b`).
The detector is a colour heuristic, not a console read: it finds the symptom, not the cause.

### Open the terminal with Ctrl+Alt+T, not through the launcher

Measured 2026-11-10: one install run typed the whole `sudo -b /usr/bin/calamares-launch-normal` line into
**KRunner** because the launcher's search result was not there yet when `ret` arrived - the screenshot showed
`o;olesudo -b …` as a web-search query and the installer never started. Every scenario now opens Konsole with
`{"keys": ["ctrl", "alt", "t"]}`, which the image binds (`org.kde.konsole.desktop _launch=Meta+Return\tCtrl+Alt+T`)
and which needs no search.

### Start the installer through the same wrapper the desktop icon uses

The desktop entry runs `/usr/bin/hscl-calamares`, which sets `QT_QUICK_BACKEND=software`, `LIBGL_ALWAYS_SOFTWARE=1`
and `KCRASH_DUMP_ONLY=1`, then watches the exit code: a signal death within the first 60 s is restarted (up to
three times), a normal exit or a late crash is passed through. Scenarios that started `calamares-launch-normal`
directly therefore tested a different code path than a user clicking the icon. `install-terminal.json`,
`install-luks.json` and `luks-probe.json` type `sudo -b /usr/bin/hscl-calamares`. The two rc3 installs recorded on
2026-11-11 predate this change and used the upstream launcher; BUILD_LOG says so.

### Probing the installer: kill the wrapper, not just Calamares

The wrapper restarts the wizard, so `pkill -f 'calamares -D8'` between probe starts looks like a crash (SIGTERM,
exit 143) and inflates every restart count - measured 2026-11-11 on rc5, where 9 of 9 restarts were the probe's
own kills. Kill the wrapper first, then the app:

```text
sudo pkill -f hscl-calamares; sudo pkill -f 'calamares -D8'; sudo pkill -f drkonqi
```

and count real faults from the wrapper's own log, not from a screenshot of the wizard:
`grep -c 'exit 137' /tmp/hscl-calamares.log` (SIGKILL). A restart that arrives too early gets Calamares' exit 87
("another instance"), which the wrapper retries after 5 s.

### One command per checkpoint

Typing the next step while a long command still runs corrupts both: on 2026-11-10 a scenario typed
`hscl lab spec …` while `apt-get install podman` was still executing, the terminal interleaved apt's output with
the typed line, and the shell ended up running `ls`. Screenshots looked plausible, the command did not.

Write the whole chain into **one** typed command that logs to files, then read the log:

```text
( sudo apt-get install -y podman; hscl lab setup; hscl lab spec … > /tmp/spec.log 2>&1;
  hscl lab install … > /tmp/inst.log 2>&1; echo INSTALL_EXIT=$? >> /tmp/inst.log ) > /tmp/all.log 2>&1;
kdialog --title lab --msgbox "$(tail -3 /tmp/spec.log; echo ---; tail -6 /tmp/inst.log)"
```

`tests/visual/scenarios/lab-kali-onecmd.json` follows that shape. A `kdialog` at the end is readable in a
screenshot even when the installer or another window covers the terminal.

The live session has **no apt lists until `apt-get update` runs**: `apt-get install -y podman`
answers `E: Unable to locate package podman` (measured 2026-11-10). Always update first and log it
separately (`> /tmp/apt.log`), otherwise the failure only surfaces later as a confusing product error.

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

### Test order is pinned

`pytest-randomly` is installed, so a plain `pytest tests` shuffles the order on every run. On 2026-11-10 three
consecutive gate runs failed on **three different** WSL-backed tests (`palette_hook_sandbox`,
`workshop_evidence`, `hcscoder`), each of which passes standalone and in a fixed order. `scripts/forge.py`
therefore passes `-p no:randomly`: the gate is reproducible, and a real failure shows up every time instead of
one time in three. The underlying order dependence is still unexplained and tracked in
[AUTONOMOUS_QUEUE](AUTONOMOUS_QUEUE.md).

## Reproducing the installer startup kill (Q-46/Q-61)

The fault: Calamares dies 2-3 s after a desktop-icon start in roughly one start in 6-12, with no core
dump and no OOM line, and `/usr/bin/hscl-calamares` restarts it inside the first minute.

Three method errors were made before a usable procedure existed, so do it this way:

1. **Measure one boot at a time, sequentially.** Calamares holds a single-instance lock and exits 87,
   which the wrapper retries. Repeated double-clicks on the icon therefore do **not** create additional
   starts - a `pgrep -c` that rises and stays constant is one process tree (about five processes), not
   five installers. Start → observe ~20 s → stop → repeat is the only measurement that counts starts.
2. **Run the watcher with `setsid`.** Closing Konsole sends SIGHUP to its children and the log stops
   three seconds in.
3. **Do not let the watcher match itself.** `pgrep -f calamares` matches the shell whose command line
   contains the word; use a bracket pattern (`pgrep -cf "[c]alamares"`), which does not match its own
   literal text, and log the PID list, not only a count.

`tests/visual/scenarios/q61-seq.json` implements 12 sequential starts in one boot through the same
wrapper the desktop icon uses, and prints `/tmp/probe.log` plus `/tmp/hscl-calamares.log` at the end.
`tests/visual/scenarios/q61-count.json` is the counter-example that proved the single-instance lock
(five identical PIDs across four more clicks) and should be kept: it is the evidence for rule 1.

4. **Read the result out of the guest through the `hscl.qa` port, not off a screenshot.** The
   screenshot-based runs (`q61-seq2`, `q61-seq3`) wasted two boots: every start puts an installer
   window in front of Konsole, the scenario's `esc` presses do nothing in a terminal, and the log was
   never on screen when the shutter fired - the final capture showed a running wizard instead of
   `== starts ==`. `scripts/qemu_boot_test.py --qa-out FILE` attaches a virtio serial port named
   `hscl.qa` whose host side is a plain file, so the probe can append text to
   `/dev/virtio-ports/hscl.qa` and the host reads it afterwards. Prefix every line (`Q61| ...`) so it
   stays separable from the `hscl-workshop-evidence` report, which writes to the same port on boot.
   `tests/visual/scenarios/q61-vport.json` does this for three start contexts
   (`hscl-calamares`, `calamares-launch-normal`, the `calamares` binary) and also records, per start,
   the byte count of that start's own stdout - that is the control sample which separates "never
   started" from "started and was killed".

The rule behind all four: a measurement that needs a human to read a screen is not repeatable, and one
that cannot separate "did not start" from "died" has no denominator.

## Release and audit tooling (no VM)

These were written after real mistakes and are the cheapest way to catch the same class again:

| Tool | What it proves | Cost |
|---|---|---|
| `scripts/verify_release_consistency.py --version V --release-dir DIR [--github owner/repo]` | ISO hash vs `SHA256SUMS` and its manifest, every part hash, that the parts rejoin to the ISO, LF-only checksums, notes without placeholders, SBOM present, README and website quote the same digests, GitHub's recorded asset digests and the published notes body | hashes the set (minutes for 5 GB) |
| `scripts/release_publish.py --version V --release-dir DIR [--dry-run]` | the upload order that survives a stall: draft first, one `gh release upload --clobber` per asset, then an explicit `--draft=false --prerelease`, then a check that it is really published | `--dry-run` prints the plan, no network |
| `scripts/release_split.py IMAGE OUTDIR [PART_MIB]` | parts plus an LF `SHA256SUMS` (the CRLF bug of 2026-11-11 made every published checksum line fail on Linux) | seconds, no 9p |
| `python -m pytest tests/unit/test_release_metadata_sync.py` | README checksums and `website/data/release.json` describe the same release | instant |
| `scripts/dev/verify_in_guest_tracks.py --iso ISO --mem 4096 --out DIR` | the twelve in-guest tracks in one boot | ~15 min and an exclusive host |
| `scripts/dev/probe_installer_kill.py --iso ISO` | **superseded**: it launched from a non-interactive hook, where the installer never starts (`launched=0` in both contexts), so it cannot answer Q-61. Kept only as a record of that design error | ~10 min and an **exclusive** host |
| `tests/visual/scenarios/q61-vport.json` via `qemu_boot_test.py --qa-out` | the current Q-61 probe: 8 sequential starts in each of three contexts, per-start alive count and own-output byte count, wrapper log and journal lines, all read from the `hscl.qa` port | ~20 min and an **exclusive** host |
| `scripts/dev/tick.ps1 -Seconds 90` | a bounded background heartbeat that prints the next actionable queue row; it completes so the agent is woken | free |

Two rules that came out of these:

1. **A hash file that was never consumed on the target platform is not verified.** A local parser with
   `str.strip()` accepted the CRLF checksums that made `sha256sum -c` fail on Linux; the cloud runner
   caught it. The checker now rejects any CR byte before parsing.
2. **A draft is not a release.** `gh release create` publishes only at the end; an interrupted upload
   leaves an `untagged-...` URL that `gh release view` still reports with assets. Always finish with
   `--draft=false` and assert `isDraft == false`.

## Evidence rules

Status words (`TESTED`, `VM-VERIFIED`, …) follow AGENTS.md §0.4 and are recorded in `docs/BUILD_LOG.md` with the
command, date and artefact path. Screenshots and ISOs live under `artifacts/` and are not committed.
