# Decision records

## ADR-001 Image pipeline: scripted remaster of the official Kubuntu ISO (2026-11-05) - ACCEPTED
Context: AGENTS.md 2.6/7.2 asks for a PoC before committing. Result: the remastered Kubuntu 26.04.1 ISO boots under
UEFI and BIOS to a live Plasma desktop and launches the shipped installer (Calamares). Boot structure is replayed from the
original El Torito/GPT metadata. Secure Boot result pending (see BUILD_LOG).
Decision: keep the remaster pipeline; `livecd-rootfs` and Debian `live-build` remain fallbacks only.
Consequences: every branding change needs an in-image assertion (the first wallpaper patch was silently ineffective).
The installer is Calamares, so branding goes through `/etc/calamares/branding`.

## ADR-002 First stable release is v2.0.0 (2026-11-05) - ACCEPTED (user-directed)
The owner asked for "v2 stable". All AGENTS.md v1.0.0 gates apply to v2.0.0; failing a critical gate yields `v2.0.0-rc.N`.

## ADR-003 VM test host: Windows QEMU + WHPX (2026-11-05) - ACCEPTED
WSL has no /dev/kvm. WHPX boots in ~2 min; it lacks SMM, so Secure Boot tests use TCG.

## ADR-004 One main ISO with an opt-in, inert Workshop (2026-11-05) - ACCEPTED (owner request)
Context: earlier rule "no QA channel in release images" produced two ISOs and slow iteration. The owner wants one ISO with
install, live and QA functions plus an API/MCP for VM screenshots and an in-ISO mode to render the current state into a new
installer ISO ("respin").
Decision: package `hscl-workshop` ships in the main ISO and is **inert by default** (no enabled unit, no socket unit, no TCP
listener, no token baked in). It starts only when a hypervisor provides the virtio port `hscl.qa` / `hscl.api` (udev) or the
user explicitly enables the unit (`sudo systemctl enable --now hscl-workshopd`); the CLI has no workshop subcommand. Its API has a finite operation set (no arbitrary shell), allow-listed paths, a
session token. `verify-image.sh` fails the build if Workshop is enabled or exposes a socket; the ISO manifest attests
`workshop_default: disabled`; `make_release.py` refuses an ISO without that attestation.
Consequences: Workshop is documented in the threat model and limitations; respin output is labelled a development snapshot.
This replaces the earlier "no QA in release" rule.

## ADR-005 Flatpak is an opt-in component, not a default (2026-11-06) - ACCEPTED
Context: Canonical asked the official Ubuntu flavours to stop shipping Flatpak, and Kubuntu 26.04 does not ship it; Flatpak itself
installs cleanly from the archive and works under Plasma 6.6 Wayland. Shipping it by default would both ignore the base
distribution's policy and add a second software source we do not audit.
Decision: the ISO is apt-only. The Control Center offers one explicit switch that installs `flatpak`, adds Flathub and displays the
source/trust of every application. Off by default; documented as opt-in, not as a feature of the base system.
Consequences: no Flatpak app can be a dependency of HSCL1 itself; the website and README must not list Flatpak among default
features; the sandbox claim is only made for apps the user installed themselves.
Refs: <https://lwn.net/Articles/927262/>, <https://itsfoss.com/news/ubuntu-flavor-drops-flatpak/>.

## ADR-006 Tiling presets are HSCL-owned files, KWin does not persist layouts (2026-11-06) - ACCEPTED
Context: KWin's custom tiling editor does not save layouts (KDE bug 466019, CONFIRMED, last activity 2026-10) and layouts are lost on
monitor changes. Promising "saved layouts" would be a claim the desktop cannot keep.
Decision (corrected 2026-11-07): KWin stores tiling per virtual desktop **and per output UUID** (fallback key derived from name+eisaId+model+serial), so a distribution cannot ship a portable `kwinrc` layout - the supported route is a KWin script. The UI says
"apply layout" and documents the re-apply, never "remembered". **Not implemented yet**: no layout presets and no layout subcommand
exist in 0.1.x (tracked as plan W5.5 in `2026-11-06-ux-ai-hardware-expansion.md`), and the docs must not offer one until a VM test
shows the preset applied through a config read.
Consequences: no "layout" entries in the Start menu; the shortcut reference documents only bindings that exist.
Refs: <https://bugs.kde.org/show_bug.cgi?id=466019>.

## ADR-007 Snapshot pinning is build-only (2026-11-06) - ACCEPTED
Context: `snapshot.ubuntu.com` covers `resolute` and `apt --snapshot <id>` works; pinning an installed system would freeze security
updates, which contradicts the "security updates by default" baseline.
Decision: the *build host* pins a snapshot ID (recorded in `build-manifest.json`, gate G21). Installed systems use the live archive
plus `unattended-upgrades` on the security pockets. Overrides for unattended-upgrades live in a file sorting after
`50unattended-upgrades` and `#clear` the shipped origins first.
Consequences: reproducibility is a property of the artefact, not of the user's machine; two builds of one commit can still differ if
the snapshot ID is not recorded - hence the gate.
Refs: <https://ubuntu.com/server/docs/how-to/software/snapshot-service/>,
<https://github.com/mvo5/unattended-upgrades/blob/main/README.md>.

## ADR-008 Trademark wording is enforced by a script (2026-11-06) - ACCEPTED
Context: OffSec's trademark policy requires the first mention to carry the symbol and the sentence "KALI LINUX ™ is a trademark of
OffSec.", forbids abbreviating or combining the mark, and forbids the mark in domain names.
Decision: `docs/TRADEMARKS.md` states the rules; `scripts/check_trademarks.py` scans tracked text files and fails when the
attribution sentence is missing on a file that mentions the mark, when a forbidden pattern appears ("HSCL1 Kali Edition",
"Kali-based HSCL1", a Kali logo file), or when a Tails sentence implies equivalence. Runs in the unit suite and in CI. <!-- trademark-ok: quoted as a forbidden example -->
Consequences: legal review by the owner is still required (F12/F14), but the mechanical part can no longer regress.
Refs: <https://www.kali.org/docs/policy/trademark/>.

## ADR-009 UI capture uses spectacle in background mode (2026-11-06) - ACCEPTED
Context: `grim` cannot capture KWin Wayland sessions; `spectacle` is the supported tool and its background mode is scriptable
(`-b -n -o FILE -d MS -e -S`).
Decision: every automated screenshot (visual gates, docs, website) uses spectacle inside the VM at a fixed resolution with animations
off and a fixed clock; the harness is `scripts/capture_ui.py`, and an image that the harness cannot reproduce is not published.
Consequences: screenshots are tied to the VM image, not to a developer desktop; the comparison baselines must be regenerated when the
image changes.
Refs: <https://forum.endeavouros.com/t/having-problems-to-take-screenshot-on-plasma-wayland/76740>.

## ADR-010 Model bundle ships as GitHub release assets (2026-11-06) - ACCEPTED
Context: GitHub caps a release asset at 2 GiB; the largest planned model is ~1.5 GB quantised; the product rule forbids requiring a
cloud account.
Decision: models are opt-in assets on the same release as the ISO, each with card, licence, sha256 and measured tok/s; the ISO ships
only the < 1 MB NCA checkpoint we trained ourselves. No bucket, no third-party host.
Consequences: a model download follows the same trust path as the ISO (checksum published in `SHA256SUMS`), and "no model weights in
the ISO" stays testable.
