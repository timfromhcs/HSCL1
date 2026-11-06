# HSCL1 finish-line plan: from `dd1630e` to everything the owner asked, with honest gates and a self-healing loop

> **For the autonomous agent (and the next session).** This file is the execution contract for the work after
> `docs/superpowers/plans/2026-11-06-autonomous-to-stable-hardened.md` (master v4, P0-P31). It does not replace the master plan:
> it fixes the **starting position**, defines the **fastest safe order**, and gives **one gate per step**. When the two disagree,
> the master plan wins on scope and this file wins on order and evidence. Status words: PLANNED, IMPLEMENTED, TESTED,
> VM-VERIFIED, HARDWARE-VERIFIED, EXPERIMENTAL, BLOCKED, UNVERIFIED. A box is ticked only with the evidence named next to it.

Written: 2026-11-06 (evening, after the 0.1.2 release attempt stopped mid-packaging).

---

## 0. Starting position (measured, not remembered)

| Fact | Evidence |
|---|---|
| Branch `codex/hscl1-v1`, HEAD `dd1630e`, worktree clean, **everything pushed**: `HEAD == origin/codex/hscl1-v1` | `git status -sb`, `git rev-parse` |
| `origin/main` = `d8f6533` (merge of PR #21). `dd1630e` (master plan v4) is **pushed but not merged into `main`** | `git log origin/main..HEAD` = 1 commit |
| Local `main` is 88 commits behind `origin/main` (stale local ref only; nothing lost) | `git branch -vv` |
| Published releases: `v0.1.0-alpha.0` (notes carry a defect warning), `v0.1.1-alpha.0` (parts + SHA256SUMS + manifest + CLI SBOM; cloud merge green) | GitHub releases |
| **`0.1.2-alpha.0` is built and fully verified but NOT published**: ISO `5 026 480 128` B, sha256 `53d1218d4926d5722c06ea41682b928e7cec6fa912fe4accc6f7ba4f7c401e71`, clean clone at `d8f6533`, `git_dirty: false`, all image gates green (boot 119 s; 3 x 28/28 e2e; fresh LUKS2 install; installed boot 0 errors, `/` = `0:0 755`) | `artifacts/release-run/status.json`, `artifacts/iso/*.manifest.json`, `artifacts/rel-*` |
| **Where the last agent stopped:** the release orchestrator reached phase `package` twice. First attempt failed on a path bug (`release-split.sh` was called with a path the Windows bash could not resolve). Second attempt started at 20:09 and wrote only 2 of 4 parts before the session ended. `package -> draft -> verify_digests -> publish -> cloud` never ran | `artifacts/release-run/run.log`, `artifacts/release-0.1.2-alpha.0/` (incomplete parts) |
| Linux test gate at HEAD: **265 passed, 0 failed** in 30.7 s (WSL clone at ext4, `~/hscl1-src`) | this session, `python3 -m pytest tests -q` |
| Windows-host test gate at HEAD: 238 passed, **11 failed**, 16 skipped. All 11 are the same environment defect: `shutil.which("bash")` resolves to the WSL launcher `C:\WINDOWS\system32\bash.EXE`, which eats backslashes in Windows paths. They pass under Git Bash and in CI. This is a **gate-parity bug on the dev host**, not a product defect | `tests/unit/test_handbook_launcher.py`, `test_hcscoder.py`, `test_workshop_evidence.py`, `tests/security/test_baseline_script.py` |
| Open Dependabot PRs: #1 checkout 4.2.2 -> 7.0.1, #2 upload-artifact 4.6.2 -> 7.0.2, #3 sha2 0.11, #4 thiserror 2. All rebased and green; a merge attempt was denied by the session policy (not retried) | GitHub PR list |
| Build lab intact: WSL `~/hscl1-build` (upstream Kubuntu 26.04.1 ISO cached, `out/` with older dev ISOs), `~/hscl1-src` ext4 clone, QEMU 11.x on Windows (`C:\Program Files\qemu`), `/dev/kvm` present in WSL | this session |
| Resources at start: 92.9 GB free on `E:`, 12.1 GB free RAM, `.wslconfig` 6 GB / 6 CPUs / 8 GB swap | `Get-PSDrive`, `Get-CimInstance`, `.wslconfig` |

**Resume point in one sentence:** finish `0.1.2-alpha.0` packaging/publish (the artefact is already proven), merge the plan commit into `main`, then run the sprint ladder below.

---

## 1. What "everything the owner wants" means (scope inventory)

Two sources, both binding: `AGENTS.md` (product contract, §14.2 and §20 = v1.0.0 definition of done) and the owner requests recorded in
master v4 (P26-P31) and the older plans (P28 carry-over). The finish line is **not** "code exists"; it is "implemented, tested, and
proven at the level the claim needs" or "explicitly owned by the owner and listed as a gap in the release notes".

### 1.1 Requirement -> status -> what proves it

| # | Owner requirement (source) | Status today | Gate that will prove it |
|---|---|---|---|
| R1 | Hybrid live/installer ISO, boots UEFI (+BIOS if base allows), desktop, installer (AGENTS 7, 14.2) | VM-VERIFIED UEFI; BIOS/H1 untested | G2 boot gate, G2b USB/BIOS |
| R2 | Installed system boots; LUKS2 unlock; no keyfile; `/` root-owned (AGENTS 6.3, 14.2) | VM-VERIFIED (0.1.1, 0.1.2) | G4, G5 |
| R3 | Secure Boot state tested and documented (AGENTS 6, 14.2) | **Not done** (no Secure Boot run) | G6 secure-boot run + written result |
| R4 | Branding: HSCL1 everywhere, no upstream logos/prompts (P12, P29) | Boot splash, live start, GRUB text, installer, SDDM partly done; **brand v2 surfaces open** | G9 brand drift test, G10 VM screenshots + OCR |
| R5 | Desktop shell: top bar, dock, launcher, tiling, shortcuts (AGENTS 4.2) | Plasma defaults exist; shortcut map partly real | G11 shortcut/keybinding test in VM |
| R6 | Control Center with real state (AGENTS 4.2, P7.1, P31.5) | QML pages exist; not all wired | G11 control-center page tests + screenshots |
| R7 | `hscl` CLI contract (AGENTS 8) | Core commands real; man pages/completions/CLI docs missing (P30.3/30.4) | G12 CLI doc drift test + man page gate |
| R8 | Welcome/first-run app, language, no cloud account (AGENTS 11, P29.3, P30.6) | Planned (W23.1) | G10 screenshot + launch smoke |
| R9 | EN/DE/FR critical strings (AGENTS 10) | Handbook + website have DE/FR; installer/desktop audit open | G13 translation coverage gate |
| R10 | Security baseline: firewall, AppArmor, no listeners, hardening (AGENTS 6.2, P3) | Firewall/KDE Connect/`/` fixes VM-verified; measured report open | G14 hardening report (Lynis/OpenSCAP/systemd) |
| R11 | Security Lab: rootless Podman, Kali digest, no host repo (AGENTS 6.6, P4) | Spec generator TESTED; **no container ever started**, podman not in image | G15 lab runtime gate (VM) |
| R12 | Privacy: Tor workflow, Tails launcher, no false claims (AGENTS 6.5, P5) | Planned | G16 Tor status/egress gate |
| R13 | No silent telemetry / documented egress (AGENTS rule 9, P18) | **Not measured** | G17 idle pcap + allow-list |
| R14 | Local AI: detect, CPU fallback, Vulkan verified, model storage (AGENTS 9, P6) | CPU path verified on WSL; GPU/Vulkan open | G18 `hscl ai` smoke in VM + V3 host bench |
| R15 | Updates/recovery story (AGENTS 6, P19, P23) | Update check real; HSCL1 package updates undecided | G19 upgrade-persistence test, G20 update decision doc |
| R16 | Reproducibility statement (AGENTS 18.2, P8) | Not done | G21 double build + diff statement |
| R17 | SBOM, checksums, signature/limits, attestation (AGENTS 6.7, P9) | CLI SBOM + checksums + cloud verify; ISO SBOM/attestation open | G22 full SBOM + attestation verify |
| R18 | Website EN/DE/FR with real download data (AGENTS 12) | Builds and tests; **not deployed** (owner decision) | G23 build + link check; deploy = owner |
| R19 | README/docs match the artefact, commands executed (AGENTS 13, P13) | Good but stale in places | G24 doc-command test |
| R20 | Legal: GPL source offer, trademark position (AGENTS 19, P22) | **Absent** | G25 SOURCE_OFFER in ISO + review list |
| R21 | Menus, preinstalled policy, apps (P30) | Open | G26 menu cache + PACKAGES.md |
| R22 | Wallpaper/GPU/VRAM governor + Ui/UX (P31) | Wallpaper effects exist; governor open | G27 governor tests + measured VM run |
| R23 | Virtual hardware lab V0-V7 (P26) | Open | G28 V0 fixtures + V1 profiles; V3/V6 owner |
| R24 | Matrix bridge vs CPU baseline (P27) | Open | G29 baselines + kernel ladder verdict |
| R25 | Dev loop: `forge check/build/boot/diff`, pre-push (P11) | `check` only | G30 forge subcommands with tests |
| R26 | Release gates of AGENTS §14.2/§20 | Partial, documented in KNOWN_LIMITATIONS | G31 gate audit table at release time |

### 1.2 Owner-only items (never guessed, never faked)

Physical-hardware boot (V6), trademark/legal review of the Ubuntu-derivative position, maintainer signing keys, native-speaker
review of DE/FR security/privacy strings, production website deployment, repository settings (immutable releases, secret scanning,
branch rules), changing inherited network defaults (NTP/mirrors/update checks), and any write to a physical disk.
These are **not** blockers for the sprints below; each release notes them as a gap until the owner acts.

---

## 2. Fastest safe path (the order is the plan)

The measured bottleneck is not coding; it is **image build + VM gates** (~3.5 min cached build, ~2 min boot, ~3 x 3 min e2e,
~18 min LUKS install, ~12 min installed boot) and host memory (one build **or** one VM at a time). So:

- **Batch host-only work** (code + unit tests + docs) while nothing else runs.
- **One image build per sprint**, never per fix.
- **One VM gate batch per image**, all gates on the same artefact.
- **Publish one prerelease per sprint** from the proven artefact (draft -> digest verify -> publish -> cloud merge).
- **Research tracks (P25-P27)** run only in gaps and never block an OS release; they have their own stop rules.

### Sprint ladder

| Sprint | Content | Entry | Exit (gate) | Est. |
|---|---|---|---|---|
| **S0 Recover** | finish 0.1.2 packaging + publish; merge plan into `main`; fix Windows test parity | artefacts already verified | release URL + cloud run green; `main` contains the plan; host pytest 0 failed | 1-2 h |
| **S1 Host-only build-up** | brand v2 generator + all surfaces from one SVG; man pages/completions + CLI docs drift; `docs/PACKAGES.md` generator; menu file; governor parsers/state machine (Rust); forge `build/boot/diff`; doc-command test | S0 | G9, G12, G26a, G27a, G30 green; WSL pytest 265+; no image needed | 1 session |
| **S2 Brand + shell image** | build one image with S1 changes; verify-image + boot + 28+ e2e + screenshots; visual QA 1366x768/1920x1080 | S1 | G1-G3, G9b, G10, G11; release 0.1.3-alpha.0 | 1 session |
| **S3 Evidence release** | P18 egress pcap + decisions; P19 upgrade persistence; P20 DE/FR LUKS unlock; P22 SOURCE_OFFER; OCR banned-string gate | S2 | G13, G17, G19, G25; release 0.1.4-alpha.0 | 1 session |
| **S4 Hardening + supply chain** | Lynis/OpenSCAP/systemd report on the booted image; full ISO SBOM + grype; double build + reproducibility statement; attestation job | S3 | G14, G21, G22; release 0.2.0-beta.0 | 1-2 sessions |
| **S5 Product shell** | welcome app, Control Center real pages, KRunner allow-list, handbook DE/FR, governor service + page, wallpaper v2 (ribbons) | S4 | G10, G11, G27; release 0.3.0-beta.0 | 2 sessions |
| **S6 Modes** | Security Lab runtime (podman, Kali digest pinned, VM run); privacy Tor/Tails workflow; local AI packages | S5 | G15, G16, G18; release 0.4.0-beta.0 | 2 sessions |
| **S7 Harden + gate audit** | Secure Boot run, BIOS/USB boot, plain install, fault injection, measured boot time, §20 audit | S6 | G6, G2b, G31; release 0.9.0-rc.1 | 2 sessions |
| **S8 Stable** | all §20 gates ticked or gaps written; docs/README/website; owner items listed; `v1.0.0` | S7 + owner items or documented gaps | release `v1.0.0` | 1 session |
| **P-track (parallel)** | P25 levers (B0/L1-L4), P27 matrix bridge (M0-M5), P26 lab levels | anytime, no image/VM conflict | G28, G29 or a published negative result | continuous |

Rule: **never start a sprint by building.** Start by writing the failing test or the gate that the sprint must satisfy.

---

## 3. Gates (exact command, pass criterion, evidence path)

`ROOT=E:\hcslinux222`, `SRC=~/hscl1-src` (ext4 clone), `OUT=~/hscl1-build/out`. Every gate writes to `artifacts/<gate>-<stamp>/`.

### G0 - Host/Linux test gate (every commit)
```bash
wsl -d Ubuntu -e bash -lc "cd ~/hscl1-src && git fetch -q origin && git reset --hard -q origin/codex/hscl1-v1 && python3 -m pytest tests -q"
python scripts/forge.py check --strict
```
Pass: `0 failed`, no `FAIL`, no unexplained `SKIPPED`; forge summary under `artifacts/forge/<stamp>/`.

### G0b - Windows-host parity (new in S0)
```bash
python -m pytest tests -q
```
Pass: same failure count as CI, or the POSIX-only tests are skipped **with an explicit reason** and are still executed in WSL by G0.
Never a green run that hides a red Linux test.

### G1 - Image build gate
```bash
wsl -d Ubuntu -e bash -lc "cd ~/hscl1-src && git rev-parse HEAD && ! git status --porcelain | grep -q . && scripts/remaster-iso.sh --out ~/hscl1-build/out/HSCL1-<ver>-amd64.iso --force"
```
Pass: exit 0, `verify-image: all checks passed`, manifest `git_dirty: false` at the expected commit, ISO sha256 printed.
Also prove from the finished ISO (not from the build tree): initrd md5, `/.disk/info` prefix `HSCL1`.

### G2 - Boot gate
```bash
python scripts/qemu_boot_test.py <iso> artifacts/boot-<ver> --firmware uefi --interval 4 --timeout 300
```
Pass: `reached_desktop: true`, screenshot of the real desktop, elapsed time recorded (target <= 180 s; current 90-150 s).

### G3 - In-guest e2e gate (3 runs)
```bash
python scripts/workshop/e2e_cli.py <iso> artifacts/e2e-<ver>-run<n>
```
Pass: `errors` empty and `checks_run >= 28` (raise the minimum whenever a check is added) in 3 consecutive runs.

### G4 - Install gate (disposable disk only)
```bash
python scripts/qemu_boot_test.py <iso> artifacts/install-<ver> --firmware uefi --try-live --dismiss-welcome \
  --disk artifacts/install-<ver>/disk.qcow2 --steps tests/visual/scenarios/install-luks.json --timeout 3600
```
Pass: exit 0, `i13-after-done.png` present, every scenario screenshot present, target disk is a qcow2 in `artifacts/`.

### G5 - Installed-system LUKS gate
```bash
python scripts/workshop/e2e_luks_boot.py artifacts/install-<ver>/disk.qcow2 artifacts/luksboot-<ver> \
  luks-marker-4711-hscl1 hscl1-test-pass-2026 wrong-pass-xyz artifacts/probe-boot-keyfile.json
```
Pass: wrong passphrase rejected, correct one unlocks, login + desktop, `errors` empty, `system_tree_owner` starts `0:0 755 /`,
no `WARN` from ufw, no keyfile, marker passphrase absent from logs.

### G6 - Secure Boot gate (new)
```bash
# OVMF with Microsoft keys from the QEMU install; record `mokutil --sb-state` / efivars in the guest
python scripts/qemu_boot_test.py <iso> artifacts/sb-<ver> --firmware uefi-secureboot --interval 4 --timeout 300
```
Pass: either boots and `SecureBoot=1` is recorded, or the exact failure is documented and the release says "Secure Boot not supported
by this image"; never a silent claim.

### G9 - Brand generator gate
```bash
python scripts/gen_brand.py --check          # generator output == committed assets
python -m pytest tests/unit/test_brand.py -q
```
Pass: no drift; every committed asset byte-identical to generator output; small/large/mono cuts for 16..512 px + ICO;
contrast >= 3:1 for the mark and >= 4.5:1 for the word on its background.

### G10 - Visual + content gate
- Screenshot set: boot splash, GRUB, SDDM, Plasma splash, desktop, launcher, Control Center, installer pages, welcome app,
  lock screen, at 1366x768 and 1920x1080.
- `python scripts/ocr_gate.py artifacts/visual-<ver>` (S3) with a reviewed allow-list.
Pass: no banned string outside the allow-list; no clipped text; keyboard focus visible.

### G11 - Shell/shortcut/Control Center gate
In-guest: `kreadconfig6` reads each documented shortcut; `kgendesignerplugin`? no - use `kwriteconfig6`/`kreadconfig6` and
`qdbus6 org.kde.kglobalaccel` to prove each binding; Control Center pages driven by `hscl ... --json` fixtures;
`kbuildsycoca6` exits 0; launcher categories listed from the menu cache.
Pass: every shortcut in `docs/CLI.md`/handbook exists and fires its action; no fake buttons.

### G12 - CLI documentation gate
```bash
python scripts/gen_cli_docs.py --check   # docs/CLI.md == `hscl --help` tree
man -w hscl hscl1                        # inside the image
```
Pass: drift test green, man pages + bash/zsh/fish completions installed by the package.

### G13 - Translation gate
```bash
python scripts/check_translations.py --critical   # installer, security, privacy, recovery strings
```
Pass: 100 % of critical strings in en/de/fr; longer DE/FR strings do not clip at 1366x768 (linked screenshot).

### G14 - Measured hardening gate
On the booted image: Lynis `hardening_index`, OpenSCAP CIS workstation profile, `systemd-analyze security` for every HSCL1 unit,
kernel-hardening-checker. Pass: report stored with the image sha256 and a regression baseline; scores are never marketing numbers.

### G15 - Security Lab gate
In the VM: `podman info` rootless, pull the pinned Kali digest, `hscl lab setup`, container runs with no host home, no docker socket,
no privileged flag, host-only network by default; `hscl lab destroy` removes only the project.
Pass: all of the above + host APT has no Kali repo (existing image check stays).

### G16 - Privacy/Tor gate
`hscl privacy tor status` reports the real state; with Tor unavailable the Tor-bound workflow fails closed (no direct egress);
Tails ISO verify path rejects a tampered file.
Pass: pcap shows no non-Tor egress from the privacy workflow.

### G17 - Egress audit gate
QEMU user-net with `-object filter-dump` (pcap): idle live 15 min, idle installed 15 min, first boot with network.
Pass: every observed host is on the reviewed allow-list or has a written decision; unknown hosts fail the gate.

### G19 - Upgrade persistence gate
`apt-get install --reinstall` of the packages that own our edited files + unattended-upgrade dry run in the VM; then re-run G1 image
checks. Pass: branding still applied or re-applied; no conffile prompt failure.

### G21 - Reproducibility gate
Two builds with `SOURCE_DATE_EPOCH`, compare ISO hashes, squashfs contents, package list. Pass: either identical hashes or a written
three-level diff and the exact reason; the word "reproducible" only with matching hashes.

### G22 - Supply chain gate
Full rootfs SBOM (`var/lib/dpkg/status`) + `grype` scan + `actions/attest` + documented `gh attestation verify`.
Pass: no unmitigated critical/high finding without a written acceptance; SBOM attached to the release.

### G25 - Legal gate
`docs/SOURCE_OFFER.md` in the ISO and as an asset; package list with versions; `docs/LICENSES.md` from copyright files.
Pass: the offer is present in the artefact and the owner review item is listed.

### G27 - Governor gate
Unit tests on sysfs/fdinfo fixtures; state-machine tests with fake inputs; VM measurement before/after (CPU and VRAM/GTT with spread).
Pass: still-fallback takes over when a window covers the desktop / AI model loads; CPU drop measured; reversible; user can disable.

### G30 - Forge gate
`forge check|build|boot|diff` each has a test and a real run on this host; a skipped step fails `--strict` except a documented
environment skip.

### G31 - Release gate audit
A table in the release PR that walks AGENTS §14.2 + §20 line by line with evidence links; every unticked line is in the release notes.

---

## 4. Self-healing loop (binding)

```
OBSERVE    run the gate; record command, exit code, timestamp, artefact path under artifacts/<task>/
CLASSIFY   code | test | harness | environment/capacity | upstream | flaky | missing feature | GATE BUG
HYPOTHESIS one falsifiable sentence + the observation that would disprove it
EXPERIMENT cheapest discriminating experiment: unit < hot-patch in live VM < layer image < dev image < release build
FIX        smallest patch at the root cause + a test that fails without it (mutation check: revert the fix, see the test fail)
VERIFY     targeted -> subsystem -> G0 -> the real artefact (G1-G5) when the claim is about the image
RECORD     CLAIMS.md + BUILD_LOG.md + commit after an explicit exit-code check + push + PR + merge on green CI
```
Limits: at most **3 attempts per distinct failure**, then BLOCKED with evidence and the next cheapest experiment.
Never: skip/weaken a test, lower a threshold, disable AppArmor/firewall/Secure Boot/encryption/sandbox, delete user data, or retry a
code defect blindly. A flaky result is repeated 3 times before it is called flaky. A GATE BUG is fixed before the product bug it hid
and gets its own test.

**Ersatzwege when a gate is stuck** (try in this order, record the choice):
- Build reaped for memory -> reduce `HSCL_SQUASH_PROCS` (3 -> 2), `HSCL_SQUASH_MEM=384M`, `wsl --shutdown` before VMs, retry once.
- Build fails on network -> use the cached upstream ISO; do not re-download without checksum.
- VM boot slow (>300 s) -> 4 vCPU / 4 GB profile, `-accel whpx`, no other VM; record the number, never hide it.
- Upload stalls -> retry per-asset with `gh release upload --clobber`; never re-create a release that already has assets.
- A claim cannot be proven on this machine -> downgrade the claim in code/docs and make it an owner item.

---

## 5. Release train (honest labels)

| Version | Entry gate | Content |
|---|---|---|
| 0.1.2-alpha.0 | already verified (G1-G5 on `53d1218d...`) | rebrand round (splash, live start, GRUB, installer, live identity), `/` ownership fix, KDE Connect off, forge check |
| 0.1.3-alpha.0 | S2 green | brand v2 all surfaces, man pages/completions, CLI docs drift, PACKAGES.md, menu file, Windows test parity |
| 0.1.4-alpha.0 | S3 green | egress audit + decisions, upgrade persistence, DE/FR unlock, SOURCE_OFFER, OCR gate |
| 0.2.0-beta.0 | S4 green | measured hardening report, full SBOM + scan, reproducibility statement, attestation |
| 0.3.0-beta.0 | S5 green | welcome app, Control Center real pages, KRunner, handbook DE/FR, governor + wallpaper v2 |
| 0.4.0-beta.0 | S6 green | Security Lab runtime, privacy workflow, local AI packages |
| 0.9.0-rc.1 | S7 green | Secure Boot/BIOS/USB, plain install, fault injection, §20 audit |
| 1.0.0 | S8 + owner items or written gaps | stable |

Every release: draft -> verify GitHub digests -> publish as prerelease -> cloud verify+merge workflow green -> website data updated
(local commit; production deploy only on owner instruction).

---

## 6. Progress ledger (update after every gate)

| Sprint | State | Evidence | Next action |
|---|---|---|---|
| S0 | IN PROGRESS | packaging+publish running; Windows 254 passed/16 skipped -> now 9 skips (release split/join moved to WSL), Linux 270 passed/0 skipped; plan v5 + SOTA scan committed | publish 0.1.2, merge PR |
| S1 | PLANNED | PACKAGES.md generated + drift gate done; ledger report done | brand v2 + CLI docs drift + governor units + A/C1 |
| S2 | PLANNED | - | image + VM gates + 0.1.3 |
| S3 | PLANNED | - | egress/upgrade/keyboard/legal |
| S4 | PLANNED | - | hardening + supply chain |
| S5 | PLANNED | - | welcome/control center/governor |
| S6 | PLANNED | - | lab/privacy/AI |
| S7 | PLANNED | - | secure boot + rc |
| S8 | PLANNED | - | 1.0.0 |
| P25/P26/P27 | PLANNED | - | baselines first, stop rules apply |

**Delegation reality (2026-11-06, measured):** `system-one-jev` answers in ~1.5 ms but returned `p_true=0.45` for a statement that was
true, so it is not a gate; `subagent.*` fails at session start with "the compaction request cannot be reduced further" while
`llama-server` is up (context 32768, output limit lowered to 2048 - no effect without a service restart); `localai-gateway.chat`
(`qwen3-4b`, `duo`) works and is the usable delegation path until the subagent harness is fixed.

---

## 7. Definition of done for this plan

1. Every R-row in §1.1 is either **VM-VERIFIED/TESTED with linked evidence** or explicitly **owner-blocked and written into
   `docs/KNOWN_LIMITATIONS.md` and the release notes**.
2. Every gate G0-G31 exists as an executable command with a test of the gate itself (mutation-checked), and runs in CI or in the
   documented local loop.
3. One published release per sprint with real assets, verified digests, and an honest "not verified" list.
4. `main` is the source of truth; every sprint lands through a PR with green CI; nothing is force-pushed.
5. The plan and `docs/BUILD_LOG.md` let a fresh session resume in under five minutes without asking what happened.

---

# v5 addendum (2026-11-06, owner request): cheaper execution, SOTA build/QA, shipping our own models

Owner asked for six upgrades. Each becomes a numbered track with its own gates, so "we improved it" is a measurement, not a claim.

## 8. Track A - Delegation and token economy (binding for every remaining sprint)

**Rule:** expensive reasoning is a budget. Triage is System 1 (OpenJev, <2 ms), mechanical work is a subagent, judgement is the
main agent. Writing more code is cheap; re-reading a 4 000-line log is not.

| Job | Tool | Why |
|---|---|---|
| yes/no gate check ("is the tree dirty", "did the digest match") | `jev_noul` | calibrated boolean, no tokens |
| pick one of N (compressor, profile, next sprint) | `jev_choice` | discrete decision with probabilities |
| triage a failure into a class | `jev_route_subagent` | routes object -> agent |
| rubric a diff (security/UI/tests/complexity) | `jev_score` | cheap pre-review before the real gate |
| mechanical repo survey, path inventory, "which files mention X" | `explore` subagent | local model, no cloud tokens |
| draft a first-pass doc section / changelog | `general` subagent | then human-grade edit |
| Playwright/DOM evidence collection | `qa-tester` subagent | runs the harness |
| design-token pass on a page | `ui-ux-specialist` subagent | better-design rules |

**Trust rule:** a local 1.5B subagent answer is a *hint*, never evidence. Anything a subagent states about the repo is confirmed with
`grep`/`rg`/`git` before it lands in code, docs or a claim. (The 16 skipped Windows tests and the `bash_kind()` Linux bug in this
session are exactly the class of thing a subagent "confirms" wrongly.)

**Token budget per sprint:** context reads capped at 200 lines per call and 2 files before a plan; logs always filtered
(`Select-Object -Last N`, `--json` + `jq`, `rg -c`) instead of dumped; independent tool calls batched in one block; no re-reading a
file that was read earlier in the same session without a reason.

**Ledger:** `artifacts/auto-loop/ledger.jsonl` - one line per delegated call (`ts`, `tool`, `job`, `tokens_est`, `outcome`). Reviewed at
every sprint boundary; a subagent that produced a wrong answer twice is dropped from that job class.

## 9. Track B - Train in-flight, ship a model (HSCL1 AI bundle)

Local RSI already exists (`lora_train_session`, `lora_merge_adapter`, `lora_auto_rsi_cycle`). New: it runs **between sprints**, and a
validated artefact ships with the release.

Pipeline (each step has a gate):

1. **Harvest** - session trajectories from `opencode.db` + the gate logs of the finished sprint.
2. **Filter** - drop anything containing a secret, a token, a personal path, an email, a private key, or a host name. Redaction runs
   before training, not after; the filter has a test with planted secrets (must remove 100 %).
3. **Distil** - turn each fixed-failure into an SFT pair (symptom, cause, patch, proof). Only pairs whose gate actually went red->green.
4. **Train** - LoRA r=8, alpha=16 on the current base; deterministic seed; manifest records base hash, dataset hash, hyper-params.
5. **Eval** - held-out set of 40 routing/classification/boolean tasks; report accuracy per class, not a single number. A model that does
   not beat the previous generation on the held-out set is **not** shipped (version stays, note in BUILD_LOG).
6. **Package** - merge -> GGUF f16 -> `Q4_K_M` quantise (`llama-quantize`), `sha256`, model card, license + NOTICE, provenance
   (base model, dataset source = this repo + our logs), size, measured tok/s on the 680M.
7. **Ship** - as a release asset `hcsl1-assistant-<ver>-q4_k_m.gguf` (+ card + card license) and as a catalog entry in
   `ai/model-catalog/`, **not** inside the ISO (ISO stays under ~5.5 GB; weights are opt-in downloads).
8. **Report** - honest scope in the model card: a 1.5B model does routing, classification, short completions, offline; it is not a
   competent coding assistant for HSCL1 itself. No claim of "our AI builds the OS".

Licensing constraint (checked, not assumed): the Qwen2.5-Coder base is Apache-2.0, so a merged derivative may be redistributed with the
licence, a NOTICE of modification, and the upstream attribution. If the base changes to a non-redistributable model, the bundle is
withdrawn - the catalog must carry the licence per entry and `hscl ai model add` must show it before download.
Owner item: none, unless we later host weights somewhere other than our own releases.

## 10. Track C - ISO build/update speed (measure first, then cut the constant)

Measured starting point: `mksquashfs 4.7.5`, `-comp xz -Xbcj x86 -b 128K -processors 3 -mem 512M`, rootfs reuse by overlayfs, no
package cache, full `xorriso` assembly every time, ~5.0 GB output.

Work items, each with a before/after number recorded in `artifacts/build-bench/<date>.json`:

- **C1 Compression bake-off** (G32): zstd-15 / zstd-19 / xz-6 / xz-9, `-processors 6`, same tree. Pick by *wall time AND size*:
  release target = smallest size within +0 % of current; dev target = fastest under 3 min. Expectation from published benchmarks
  (MaskRay 2025, Redpill Linpro 2024): zstd-19 is within ~6 % of xz-6 size at comparable per-thread speed but scales better with
  threads, so the win is in `-processors`, not in the algorithm. Do not assume - measure.
- **C2 Package and rootfs caches**: keep `/var/cache/apt/archives` and the unsquashed rootfs keyed by the package manifest hash; a build
  with an unchanged base manifest must not re-download or re-unpack (target: no network except our own .debs).
- **C3 Incremental HCS layer**: build only the changed `hscl-*` .deb; `dpkg-deb -b` per package, skip unchanged ones by content hash.
- **C4 XORRISO delta**: reuse the extracted ISO tree (`iso/`) across builds; only `filesystem.squashfs`/`.size`, `md5sum.txt`, the
  manifest and `grub.cfg` change. Measure xorriso time separately from squash time so the next optimisation targets the real cost.
- **C5 Split-ISO release path**: keep the 1500 MiB split for GitHub's 2 GiB cap, but generate **zsync** metadata (Ubuntu ships
  `.zsync` for its ISOs) so a user updating 0.1.2 -> 0.1.3 downloads only changed blocks. Gate: `zsync` of the previous ISO against the
  new one must fetch < 25 % of the file and reconstruct a byte-identical ISO (`sha256` match).
- **C6 Budget guard**: the build prints `unpack / packages / squash / xorriso / total`; a regression of >20 % on any stage fails the
  benchmark gate and is investigated before the next release.
- **C7 Considered and rejected for v1** (documented, not silently dropped): Ubuntu `livecd-rootfs`/`isobuild` and `livefs-editor`
  (canonical, but a rewrite of the pipeline and it builds *from* an official livefs - evaluate again at 1.0 if build time or Secure Boot
  forced our hand); OSTree/casync image updates (0.09 MB deltas exist, but they replace APT - a 2.x project); debdelta (unmaintained).

## 11. Track D - Update channel and API hygiene

- **D1 APT is the source of truth**; pockets only `resolute`, `-updates`, `-security`; no PPA, no Kali, no interim release.
- **D2 Snapshot pinning option**: `hscl system updates --pin` can point APT at a dated snapshot for a reproducible reinstall; default
  stays the live security pocket (snapshot.ubuntu.com availability to be verified, then documented).
- **D3 Unattended security updates** offered in onboarding, off by default, with a visible "restart required" state; verified in the VM
  by installing a downgraded package and observing the upgrade path.
- **D4 `hscl system updates --check/--install` contract**: `--json` schema (`{updates:[{name,from,to,security}],count,reboot_required}`),
  stable exit codes, never `apt autoremove` without showing the set, never `curl | bash`.
- **D5 Release metadata API**: `website/data/release.json` generated from the GitHub API with ETag caching and one authenticated call per
  run (rate-limit safe), plus a copy in the ISO (`/usr/share/hscl/release.json`) so the system and the site tell the same story.
- **D6 Asset verification**: every download path verifies `sha256` from the signed manifest before use; `hscl doctor` reports drift.
- **D7 Delta downloads for users**: `.zsync` per C5, documented on the download page; signature still verified after reconstruction.

## 12. Track E - Screenshot/MCP runs and visual QA (SOTA, deterministic)

Problem today: visual evidence is ad hoc (manual screenshots), so "no rendered evidence" is a permanent risk in CLAIMS.

- **E1 Deterministic capture harness** (G33): QEMU boots the ISO with `-rtc base=2026-01-01T00:00:00`, a fixed resolution
  (1366x768 and 1920x1080 runs), animations set to instant, a fixed wallpaper, and clock seconds hidden. Capture via the in-guest
  `hscl-qa` path, extended to write PNGs to a **virtio-9p share** (`-virtfs local,path=artifacts/visual/<sha>,mount_tag=hsclshots`) so
  files land on the host without SSH, serial streaming or base64.
- **E2 Screen set**: splash, login, desktop, start menu, control center overview, appearance, security, lab, privacy, files, terminal,
  plus the two resolutions and `de`/`fr` variants of the ones with the longest strings.
- **E3 Comparison**: perceptual diff (pixelmatch via Node, or ImageMagick `compare -metric SSIM` when Node is absent) against committed
  baselines; thresholds in the gate file; output `diff.png` + `diff.json` + an `index.html` gallery. Unintended diff = red gate.
  Baseline updates are an explicit commit (`--update-baselines`) with the reason in the message.
- **E4 Website visual tests**: Playwright `toHaveScreenshot()` with committed baselines, fixed fonts, `maxDiffPixelRatio`, run in the
  same container locally and in CI (grey-noise-free); `reg-suit`-style git baseline storage is what Playwright already does - no vendor.
- **E5 MCP usage**: `playwright`/`chrome-devtools` MCP for live DOM+console evidence on the website and control-center web views; the
  ISO desktop is captured by E1. MCP calls are batched and their outputs filtered, per Track A.
- **E6 Accessibility in the same pass**: axe-core on every website page, and in the VM: focus-ring visible, 200 % scale, reduced motion,
  EN/DE/FR string fit.

## 13. Track F - Open questions to close (research queue, in priority order)

Each is one line of evidence so the answer can be audited later.

1. Secure Boot with a remastered Kubuntu ISO - does the shim/GRUB/kernel chain still validate? (G6; QEMU OVMF + MS keys + `mokutil`)
2. Does casper support multiple squashfs layers (would make C3 trivial)? If not, stay with single-layer + caches.
3. `zsync` availability on the build host and behind GitHub release downloads (Range requests) - verify before promising C5.
4. Snapshot pinning: `snapshot.ubuntu.com` coverage for `resolute`, and how to pin without breaking security updates.
5. `unattended-upgrades` behaviour on 26.04 (config path, reboot-required signalling, apt-listchanges interaction).
6. KWin/Wayland capture API on Plasma 6.6: `org.kde.KWin.ScreenShot2` vs `spectacle --background` - determinism under
   fractional scaling.
7. Calamares version in `resolute` + offline install (do the packages we need exist on the ISO without a network?).
8. Flatpak: is it in the base ISO, and does the sandbox actually work under Plasma 6.6 Wayland?
9. virtio-9p vs virtiofs under WSL2 QEMU for E1 (perf + does the guest mount it without root at boot?).
10. GitHub API without a token in CI: which calls are rate-limited and what must be cached/conditional.
11. Model hosting: GitHub release assets (2 GiB cap) vs a separate bucket - decide before B7, respecting "no cloud account required".
12. Trained-model provenance/licence text for an Apache-2.0 derivative (NOTICE wording) - legal review is an owner item.
13. Evaluation set design that is not self-flattering (held-out, no leakage from training trajectories).
14. Kali/Tails trademark wording audit (`Kali tools in isolated containers`, `Tails ISO launcher`) - owner legal review.
15. Hardware compatibility matrix - owner hardware; until then `HARDWARE-VERIFIED` stays empty.
16. Egress/telemetry audit method (`nftables` counters + tcpdump on the vNIC during a full session) - defines what "no telemetry" proves.
17. Crash reporting without telemetry: local-only journal export + opt-in upload design.
18. Delta/atomic update roadmap: is OSTree (or btrfs snapshots + `apt`) the 2.x answer, and what does it cost in installer complexity?
19. Website production deploy - owner decision, never autonomous.
20. DE/FR native-speaker review - owner procurement; until then the translation gate proves *coverage*, not *quality*.
21. WebGPU in the shipped QtWebEngine/Chromium on Plasma 6.6 - available or not? Determines whether the NCA demo uses WebGPU, WebGL or
    an ONNX-WASM CPU kernel (measure, do not assume).
22. ONNX Runtime Web (WASM SIMD + threads) throughput on the 680M for a 4k-parameter NCA at 512x512 - if it cannot hold 30 FPS, the
    demo renders at 256x256 and says so.
23. llama.cpp GBNF support in the shipped build (grammar parameter over `/v1/chat/completions` or only `llama-server --grammar`) - decides
    whether Game Studio constrains during decoding or validates after generation.
24. Licence/provenance of any pre-trained demo checkpoint - default is "train it ourselves" (G2) to avoid the question entirely.

## 13b. Track G - Neural Lab: neural games, LLM-written artefacts, premade models, custom workspace

Research basis: `docs/research/2026-11-06-sota-scan.md` (GameNGen/Genie 3 are TPU/hosted-scale; NCA is the shippable end; small models
serve schema-filling, not free-form program synthesis). Everything below must run **offline on the 680M + CPU** and be honest about it.

- **G1 Scope guard.** No "neural game engine" claim. A toy next-frame predictor is labelled *toy*. The demos are labelled with their
  measured FPS on this hardware, not a marketing number.
- **G2 Three demos that really run** (all offline, deterministic seed, no network):
  1. **NCA playground** - a ~4k-parameter neural cellular automaton (5x5 conv, 12-16 channels) that grows/repairs a pattern; ONNX or
     hand-written JS/WebGL kernel; trained by us (`scripts/train_nca.py`) so there is no checkpoint licence question; model < 1 MB.
  2. **Tiny-net trainer** - 2-D classification playground (TensorFlow-Playground-class), showing loss/decision boundary live.
  3. **Frame-predictor toy** - 64x64, one simple game (grid/catch), predicts the next frame from input; exposes the drift/failure after
     a few seconds instead of hiding it. Explicit "this is not GameNGen" caption.
- **G3 Game Studio (`hscl neurallab play new "<prompt>"`)** - the LLM never writes a program from scratch:
  1. prompt -> **game spec JSON** under a GBNF grammar (template, palette, entities, difficulty, win condition, title);
  2. a vetted offline **template runtime** (snake, breakout, maze, platformer-lite) renders it to one self-contained HTML file;
  3. smoke-check in an isolated renderer (canvas non-blank, no console error, deterministic seed);
  4. file lands in `~/Projects/NeuralLab/games/<slug>.html`, listed by `hscl neurallab play list`.
  If the model is absent or the spec fails validation, the command says so and offers the template without AI; it never pretends.
- **G4 Custom workspace** - package `hscl-neurallab` installs `~/Projects/NeuralLab/{models,games,specs,notebooks}` scaffolding (never
  overwriting existing files), desktop entries under *Neural Lab*, and a localhost-only viewer (`127.0.0.1`, no LAN bind by default).
- **G5 Premade models** - `hcsl ai model add hcsl-route | hcsl-chat | hcsl-nca` with card, licence, sha256, size, measured tok/s; each
  is opt-in and lands in the user-chosen model store (Track B step 6-7). Nothing is bundled in the ISO beyond the tiny NCA weights.
- **G6 Generated code is untrusted** - anything the model writes that is *code* (not a spec) runs only inside the rootless container
  sandbox: no host FS, no network, read-only mounts, wall-clock limit. Never `sudo`, never auto-install, never auto-run on login.
- **G7 Licence hygiene for demos** - no ripped assets; palettes/sprites generated or CC0; each demo carries its own licence line and
  the asset provenance in `NOTICE`.

Gates:

| Gate | Command (sketch) | Pass criterion | Evidence |
|---|---|---|---|
| G42 neural demos | `tests/visual/test_neural_demos.py` (headless Chromium) | 3 demos load offline, render >= 30 frames, no console error, FPS recorded | `artifacts/neural/<sha>/` |
| G43 game spec | `tests/unit/test_game_spec.py` + `hscl neurallab play new --dry-run` | 20 prompts -> 20 schema-valid specs (GBNF), 20 rendered files, 0 network calls | test output + rendered files |
| G44 workspace | `tests/unit/test_neurallab_init.py` | idempotent init, never overwrites, works offline, `hscl doctor` sees it | test output |
| G45 sandbox | `tests/security/test_codegen_sandbox.py` | hostile snippet cannot read host FS, cannot reach network, cannot escalate | test output |
| G46 demo licences | `scripts/check_assets.py` | every asset has provenance + licence, no third-party trademark/art | `assets/provenance.json` |

## 14. New gates

| Gate | Command (sketch) | Pass criterion | Evidence |
|---|---|---|---|
| G32 build benchmark | `scripts/bench-build.sh --variants zstd15,zstd19,xz6` | table written, chosen variant documented, no stage regresses >20 % | `artifacts/build-bench/*.json` |
| G33 visual capture | `make visual` (QEMU + 9p) | 12+ screens at 2 resolutions, all PNGs non-blank, `diff.json` present | `artifacts/visual/<sha>/` |
| G34 visual diff | `tests/visual/run_diff.py` | SSIM >= threshold vs baseline or an approved baseline change | `diff.png`, `index.html` |
| G35 website visual | `npm run test:visual` | Playwright baselines match, 3 locales, mobile+desktop | `website/test-results/` |
| G36 zsync delta | `zsyncmake` + `zsync` round-trip | reconstructed ISO hash identical, transfer < 25 % | `artifacts/delta/*.json` |
| G37 update contract | `tests/integration/test_updates.py` | `--json` schema valid, exit codes stable, no autoremove without listing | test output |
| G38 delegation ledger | `python scripts/ledger_report.py` | every sprint boundary has entries; no unconfirmed subagent claim in docs | `artifacts/auto-loop/ledger.jsonl` |
| G39 model provenance | `scripts/model_release_check.py <gguf>` | card + licence + NOTICE + sha256 + eval report present, secret scan clean | `release/model/` |
| G40 training hygiene | `tests/unit/test_training_filter.py` | planted secrets/paths/emails removed 100 %, gate pairs only | test output |
| G41 build-time budget | `scripts/bench-build.sh --check` | total build <= budget in `artifacts/build-bench/budget.json` | json |

## 15. Sprint ladder update

| Sprint | adds |
|---|---|
| S0 | publish 0.1.2, merge plan, host parity (done) |
| S1 | brand v2, CLI docs drift, PACKAGES.md, governor units **+ A (delegation), B-step1 (harvest+filter), C1/C2** |
| S2 | image + VM gates, 0.1.3 **+ C3/C4, E1/E2 first captures** |
| S3 | egress/upgrade/keyboard/legal **+ D1-D4, F1/F4 answers** |
| S4 | hardening + supply chain **+ C5/C6 (zsync), D5/D6** |
| S5 | welcome/control center/governor **+ E3-E6 visual gates, B-step2-5, G2 (demos)** |
| S6 | lab/privacy/AI **+ B-step6-8 (ship model), G39/G40, G3/G4 (studio + workspace)** |
| S7 | secure boot + rc **+ G32-G46 all green in CI** |
| S8 | 1.0.0 **+ ledger + benchmark report in release notes** |
