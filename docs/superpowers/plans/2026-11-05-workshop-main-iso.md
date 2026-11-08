# One main ISO: Live + Installer + Workshop (QA, API/MCP, respin) + full HCS look

> **Reconciled 2026-11-08:** The current OS release execution plan is
> [v1 release plan](2026-11-08-v1-release-plan.md); ecosystem priorities and evidence
> remain in the [live master ledger](2026-11-08-selfheal-masterplan.md).
> See [the per-plan audit](../../PLAN_INDEX.md) for current continuation notes.
> Older snapshots, release ladders and competing next-task orders below are historical;
> preserve the domain specifications and gates. Root `AGENTS.md` and later owner
> instructions govern conflicts. Model assistance for this continuation is local only;
> no Qwen Mythos/cloud inference.


> Executed autonomously, slice by slice, each with tests/evidence in `docs/BUILD_LOG.md`. AGENTS.md wins on conflict.
> Supersedes the two-variant (release/QA) build of the previous plan: there is **one main ISO**.

**Goal:** a single ISO that boots as a live desktop, installs to disk, and carries an opt-in **Workshop** toolset: guest evidence
(QA), a VM API + MCP server for screenshots/keys/files, and a **respin** mode that renders the current live state into a new
installer ISO - so development iterations from here to v2 take minutes, not a full rebuild. Plus the full HCS look: logo,
backgrounds, a "number rain" animated wallpaper, boot/login/installer branding.

## Decisions (ADR-004, to be recorded in `docs/DECISIONS.md`)

| # | Decision | Why |
|---|---|---|
| D1 | The QA channel moves into the main ISO as part of `hscl-workshop`. This **replaces** the earlier rule "no QA in release". | Owner request (2026-11-05): one ISO with install, live and QA functions. |
| D2 | Workshop is **inert by default**: no service runs, nothing listens, no network socket exists, unless the user enables it (boot menu entry "Workshop mode", or `sudo hscl workshop enable`) or a hypervisor provides the virtio port `hscl.api`. | AGENTS.md 0.3: no silent telemetry/remote control, no unnecessary listeners. |
| D3 | Transport is **virtio-serial (`hscl.api`) and a root-owned unix socket**; there is **no TCP listener**. Every request carries a token that exists only in the live session or in `/etc/hscl/workshop.token` (mode 0600). | A VM host channel is not reachable from the network. |
| D4 | The API has a **finite operation set** (no arbitrary shell): `status`, `doctor`, `report`, `screenshot`, `put_file` (allow-listed directories only), `run_hook` (allow-listed hook directory), `restart_shell`, `respin`. | AGENTS.md 0.3 rule 7 (no arbitrary command execution as root from UI/API). |
| D5 | Respin needs a writable target (second disk or share), refuses RAM/tmpfs targets, refuses to run unless the session is live (`boot=casper`), and never writes to a disk that holds a mounted filesystem other than its target. | Data safety. |
| D6 | Installed systems get the same package but Workshop stays disabled, token-protected and documented; THREAT_MODEL and KNOWN_LIMITATIONS state exactly what it can do. | Honesty requirement. |
| D7 | The animated rain wallpaper is the HCS default for the live/installed desktop but is **never required**: it honours KDE's animation setting (`AnimationDurationFactor=0` -> static), and a static HSCL1 Midnight wallpaper stays one click away. | Accessibility (reduced motion). |

## Slices (in order)

### S0 - Housekeeping
- [ ] ADR-004 in `docs/DECISIONS.md`; THREAT_MODEL "Workshop" section (assets, abuse cases, residual risk); KNOWN_LIMITATIONS row.
- [ ] Rename package `hscl-qa` -> `hscl-workshop` (keep the evidence runner); remove the QA/release split from `remaster-iso.sh` (`--variants` stays only as a dev switch; default builds the single main ISO); `make_release.py` replaces `qa_image` with the attested `workshop_default: disabled`; `verify-image.sh` asserts D2 (service not enabled, no socket unit enabled, no TCP listener configured).

### S1 - Guest side: `hscl-workshopd` + `hscl workshop`
- [ ] Python daemon (stdlib only, runs from `/usr/lib/hscl/workshop/hscl-workshopd`), activated by a systemd unit with `ConditionPathExists=/dev/virtio-ports/hscl.api` or by `hscl workshop enable`; line-delimited JSON-RPC 2.0 over the port; token check; operation set of D4; every path validated against allow-lists, symlinks rejected, size cap.
- [ ] Unit tests (host-side, with a fake transport): bad token, unknown op, path traversal, symlink escape, oversize, allow-listed `put_file`, `run_hook` name validation.
- [ ] `hscl workshop status|enable|disable|evidence|screenshot` in the Rust CLI (calls the same code paths; tests with fixtures).
- [ ] Screenshot op: session user's `spectacle -b -n -o FILE` (Wayland-safe), returned as base64; fallback documented.

### S2 - Respin (render the live state to a new installer ISO)
- [ ] `hscl-respin` (shell, shellcheck-clean): detects the boot ISO device from `/proc/cmdline` + `/cdrom`, snapshots the merged live root with `mksquashfs -mem 512M -e <excludes>` (excludes: `/proc /sys /dev /run /tmp /cdrom /target /home/*/.cache /var/cache /var/log /var/lib/apt/lists/*`, the output dir, the live user's volatile state, workshop token), regenerates `md5sum.txt`, replays the boot structure with `xorriso -indev <iso> -boot_image any replay`, writes `<out>/HSCL1-respin-<date>.iso` + `.sha256`.
- [ ] Safety tests: refuses non-live sessions, refuses tmpfs targets, refuses when free space < estimate, refuses a target that is the boot device; secrets scrub (shell history, token, `/home/*/.config/hscl/workshop*`, SSH keys) with a unit test over a fake tree.
- [ ] VM proof: boot the main ISO with a 30 GB scratch disk, push a changed wallpaper via the API, respin, boot the **new ISO** and screenshot the change. Status VM-VERIFIED only if the second ISO boots and shows the change.

### S3 - Host side: VM API + MCP server
- [ ] `scripts/workshop/vm.py`: VM manager (start with WHPX/KVM/TCG, memory guard, UEFI/BIOS, disks, virtio ports `hscl.qa`/`hscl.api` as unix sockets or TCP-localhost on Windows, QMP: screenshot, keys, text, click, power); `scripts/workshop/client.py`: guest RPC client.
- [ ] `scripts/workshop_mcp.py`: MCP server over stdio (initialize, tools/list, tools/call) exposing `vm_start`, `vm_stop`, `vm_screenshot` (returns an image), `vm_keys`, `vm_type`, `vm_click`, `guest_status`, `guest_doctor`, `guest_push`, `guest_hook`, `guest_respin`, `vm_list`. Local-only, no network port.
- [ ] Tests: protocol conformance with a scripted stdio client; every tool has a schema; invalid arguments are rejected; the memory guard blocks `vm_start` when memory is low.
- [ ] `.mcp.json` in the repo registering the server (project scope).

### S4 - Full HCS look
- [ ] **Number rain wallpaper**: a Plasma 6 wallpaper plugin `org.hcs.hscl1.rain` (QML, Canvas-free: bounded set of `Text` columns with falling hex/binary glyphs and the `HSCL1` mark fading in), token colours (accent on surface-0), config: speed, density, glyph set, "static when animations are off"; QML test instantiates it, verifies columns/animations stop when `animationsEnabled` is false; a CPU budget check in the VM (idle CPU of plasmashell under rain below a stated limit, else lower default density).
- [ ] Lock screen and SDDM use the rain/static HCS look; Calamares slideshow gets an animated logo slide.
- [ ] GRUB theme (HSCL1 menu background + logo) in the ISO and the installed system; Plymouth theme `hscl1` (logo, subtle pulse, progress); each asserted in the image by `verify-image.sh`.
- [ ] Brand pack: icon theme additions for the remaining launchers, wordmark in the About page, animated logo (SVG/QML) in Welcome.
- [ ] Harness: desktop detection no longer relies on the static wallpaper (top-bar + dock + non-black test) so animation does not break `reached_desktop`.

### S5 - Main ISO build and full re-verification
- [ ] One build of the main ISO on the cached overlay engine (memory-guarded); manifest says `workshop_default: disabled`.
- [ ] VM matrix: UEFI boot; live desktop with rain; Workshop inert check (no listener, no unit active) **without** the virtio port; with the port: `hscl.api` status/screenshot/put_file/run_hook; respin proof (S2); normal install to qcow2 + boot from disk + login + guest report (installed Workshop disabled); screenshots of the new look.
- [ ] Update BUILD_LOG/README/handbook (Workshop chapter EN/DE/FR, command-tested), release set via `make_release.py`.

## Review focus

- A reachable control channel in a shipped image -> D2/D3 enforced by tests and by a VM check that lists listening sockets with Workshop off.
- `put_file`/`run_hook` as a root escalation path -> allow-lists, symlink rejection, hook directory owned by root and read-only to the live user, no argument interpolation into a shell.
- Respin leaks secrets (token, history, keys) into a distributable ISO -> scrub list + test; respin output is flagged "development snapshot" in its manifest and volume label.
- Animation drains CPU in VMs/low-end machines or ignores reduced motion -> D7, density default tuned from a measurement.
- Respin ISO boots only on the machine that built it -> boot structure replayed from the source ISO; proof by booting the result.
