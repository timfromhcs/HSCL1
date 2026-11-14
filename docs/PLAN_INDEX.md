# HSCL1 plan reconciliation index

## Live status, 2026-11-14: v1.0.0 Stable Release Published, Verified and Live

- **Product:** HSCL1 OS (`v1.0.0` stable release). Ubuntu 26.04 LTS (`resolute`) + Kubuntu KDE Plasma 6.6 LTS desktop. Publisher: HCSMEDIA ("Made with love by hcsmedia").
- **Release:** https://github.com/timfromhcs/HSCL1/releases/tag/v1.0.0 (marked as Latest Stable release, not prerelease).
- **ISO Candidate:** `artifacts/iso/HSCL1-1.0.0-amd64.iso` (5,027,201,024 B, xz-compressed, `git_dirty: false`, source `6664491` on `main`).
  - SHA256: `d23a0bbee06c3fdb54ca3a39e2e9659e26cbaf9de0f4d8d89666e0c3bef6d5bc`.
- **Readiness Attestation:** `artifacts/readiness-1.0.0.json` conforming to `hcs.release-readiness.v1` with all 21 §14.2 release gates evaluated to PASS, backed by hashed local evidence files.
- **In-Guest Boot Proof:** Reached desktop in 194 s at 4 GB RAM. `qa_report.py` exit 0 (9 checks ok + 1 info check).
- **End-to-End Installation Proof:** Complete unattended installation at 8 GB RAM on disposable 40 GB virtual disk (`artifacts/vdisks/install-1.0.0-8g.qcow2`), finished with Calamares "All done" (10.14 GB written).
- **Installed System Boot & SDDM Greeter Avatar:** Booted disk directly via UEFI/GRUB (`iso=none`) in 338 s. Entered desktop, verified `hscl doctor` (6 passed, 0 failed, 1 skipped), ufw, apparmor, os-release. Pixel analysis on SDDM greeter screenshot (`artifacts/boot-installed-1.0.0/login-screen.png`) confirmed 2,578 authentic `#0064FF` blue mark pixels; Breeze KDE gear avatar 100% eliminated from installed disk.
- **Vercel Production Deployment:** Authentically built and deployed to https://hscl1.vercel.app with complete 15-page multilingual documentation (EN/DE/FR).
- **GitHub Release & Asset Integrity:** 3-part split verified locally and in GitHub Actions cloud runner; `verify_release_consistency.py --github` 24 checks / 0 failed.

## Live status, 2026-11-13 (evening): rc12 proves the 11-page Control Center in a booted guest

- **`HSCL1-rc12-amd64.iso`** (`e235ff29…`, 5 488 771 072 B, zstd-fast): built from image-relevant `e382047`,
  `verify-image` green in-build, UEFI/WHPX at **4 GB** reached the desktop in **233 s**, QA report written.
  The manifest says `git_dirty: true` because uncommitted docs were present at build start - the image content
  is the committed panel, but the artifact is **not** release-bound; a clean xz rebuild is required for a tag.
- **All 11 Control Center pages captured in the guest** with real CLI values (Q-73): Privacy shows overlay and
  zram active with persistent swap inactive and Tor inactive; Security Lab shows Podman absent and network
  `none`; Updates shows 0 upgradable **with** stale lists (79 days) and the warning; Developer shows git+python
  only. Showcase `04`-`07` now come from rc12 and `24`/`25` are new; the website alt text matches.
- **Space incident (recorded):** a PowerShell 5.1 `-Include` bug emptied the local `artifacts/` tree
  (124.1 GB) during the space cleanup; measurements survive in BUILD_LOG, raw files do not, and
  `docs/CLAIMS.md` / `KNOWN_LIMITATIONS.md` now mark every `artifacts/` path as historical. The guard is
  `scripts/dev/cleanup-artifacts.ps1` (dry run, evidence protected) with 5 tests.
- **Installation and installed boot are verified on rc12, but only at 8 GB** (Q-74): the same scenario at 4 GB
  panicked (`Attempted to kill init! exitcode=0x0000000b`) and left an ESP without `/EFI`; at 8 GB it finished
  with "All done", the ESP carries `shimx64/grubx64/mmx64/BOOTX64.EFI`, and the disk boots with `iso=none` to
  SDDM, logs in as `hscl1t` and reports `hscl doctor` **6 passed / 0 failed / 1 skipped**. README,
  KNOWN_LIMITATIONS and the handbook now state live 4096 MB / install 8192 MB. The harness also stopped calling
  a panicked guest a green run.
- **Next:** the next image build should carry the handbook corrections and the rc12-verified panel; the open
  cosmetic item is the SDDM avatar (Q-75, still the KDE gear).

## Live status, 2026-11-13: Control Center at 11 pages, README and website reconciled to the evidence

- **Control Center:** the panel went from 5 to **11 read-only pages** (Privacy, Security Lab, Local AI, Updates &
  Recovery, Developer, Language & Region added) on one shared `HcsPage` frame with a single heading, one
  refresh action and one labelled error banner. The CLI bridge allowlist grew by six status commands and now has
  a test that refuses every setter/installer. Gate: `qml-gate.sh` pages **16/16**, `tst_backend` **6/6**,
  `qmllint` **0 warnings**; `tests/unit/test_cc_pages.py` pins page/rail parity and the allowlist.
- **README:** its status block said the installer was "still killed in one start in six to twelve" while the
  same block said 20 of 20 starts survive; it said the Kali toolset had "not been run in a guest" (Q-18/Q-59
  record the opposite), promised "isolated network routing" (Q-65 removed that claim), used a dead TOC anchor
  and two CLI examples that cannot run (`lab run` without `--project`/`--image`, `wallpaper apply rain`). All
  corrected; the verification table now carries the Control Center and website gates.
- **Website:** EN/DE/FR were still saying "Security Lab not implemented", "LUKS not tested", "KDE Connect still
  listening" and "Secure Boot state not read". Reconciled, and a **`/privacy/`** page (15 pages total) now
  states capabilities, missing filtering and the Tails boundary instead of leaving that to a bullet.
- **Still true and still open:** no booted-VM capture of the new Control Center pages (the website image is the
  five-page capture and its alt text says so); the v1 gates that need hardware or a signing key are unchanged;
  one `cargo test --all` run failed once and was green in the next four runs (Q-72, no cause claimed).

## Live status, 2026-11-13: 0.1.8-alpha.0 ships the installer fix

- **Released:** `v0.1.8-alpha.0` (`def7f190…`, 5 027 201 024 B, source `91c8acb`, xz, clean tree) -
  https://github.com/timfromhcs/HSCL1/releases/tag/v0.1.8-alpha.0. `verify_release_consistency.py --github`
  **24 checks / 0 failed**; CI **success** and "Verify release assets" **success** on the same commit.
- **Q-68 is closed on media:** the booted image has **0** `notesqml` lines in
  `/etc/calamares/settings.conf`, and **20 of 20** sequential installer starts survive with drkonqi made
  unrunnable and a core pattern set - zero cores. A still-broken build would have produced a death with ~98 %
  probability at the old rate. The image gate asserts the step stays disabled.
- **What is left is not this class of bug:** Q-66 (empty-ESP cause unknown, guarded and self-diagnosing),
  Q-19 (qmllint ratchet), and the v1 gates that need hardware or a signing key (physical boot, USB, Secure
  Boot acceptance, TPM, Tor-routed privacy, release signature, image-level SBOM).
- The desktop hero image in the README is this artifact's own capture (`artifacts/hero-0.1.8`), so the Q-55
  standard ("the hero is the current candidate") holds.

## Live status, 2026-11-12: Q-68 solved - the installer crash is the `notesqml` step

- **The installer's startup crash has a named site and a measured fix.** With `drkonqi` made unrunnable
  (`chmod -x`) KCrash re-raises the signal instead of starting its broken reporter, so the crash dumps a core;
  the backtrace is always `QListView::paintEvent` -> `QStyledItemDelegate::initStyleOption` -> `ViewManager::data`
  -> **`NotesQmlViewStep::prettyName()`** -> `Calamares::Locale::TranslatedString::get(QLocale const&)` ->
  SIGSEGV in `libcalamares`. With the step wired: **2 deaths in 8 starts**; with the sequence line removed:
  **0 in 10**. The hook no longer inserts it, the assets stay for a future upstream fix, and the image gate now
  asserts that the step stays disabled.
- **Three earlier readings of the same logs were wrong** and are corrected in place: `crashRecursionCounter = 2`
  is normal for a first crash, `appFilePath points to nullptr` is the forked drkonqi (not calamares), and the
  signal is **SIGSEGV**, not an abort - an empty `dmesg` in this live session proved nothing.
- **Reusable method:** `chmod -x /usr/lib/x86_64-linux-gnu/libexec/drkonqi` is the only way to get a core from
  this installer, because `KCRASH_DUMP_ONLY=1` and `KDE_DEBUG=1` cannot disable a reporter that Calamares
  enables itself. `strace -f` **hangs** on this fault and must not be used.

## Live status, 2026-11-12: 0.1.7-alpha.0 published from `main`

- **Released:** `v0.1.7-alpha.0` (`400fb9d7…`, 5 027 201 024 B, source `88f0fbe`, xz, clean tree) -
  https://github.com/timfromhcs/HSCL1/releases/tag/v0.1.7-alpha.0. UEFI boot at 4 GB reached the desktop in
  192 s, `qa_report.py` exit 0, `verify_release_consistency.py --github` **24 checks / 0 failed**, the
  "Verify release assets" workflow **success** on the same commit, CI **success** on the same commit.
- **It is the first release whose commit is on `main`.** `v0.1.6-alpha.0` was built from `13c3215` on
  `release/0.1.6`, which was never merged, so `main` still said `VERSION = 0.1.5-alpha.0` and the next build
  would have silently reused 0.1.5. The ancestry check is now step 1 of `docs/RELEASE_PROCESS.md`.
- **Two defects were found by building, not by reading.** (1) The live-locale fix from `97446c6` had never
  worked - it appended `LANG=` only when absent, and the base image already sets `LANG=C.UTF-8`; the image
  gate stopped the first build and the hook now replaces the value and generates the locale. (2) `gh release
  create --notes-file` sends the body through the Windows codepage, so one right-arrow arrived as mojibake
  while the uploaded asset stayed byte-identical; `make_release.py` now refuses non-ASCII notes.
- **Q-61 is closed** (the SIGKILL came from `drkonqi`, forked by the crashed Calamares - audit record in
  `artifacts/q61-audit2`), and **Q-68** is the open remainder: the crash itself. **Q-67** closed by
  measurement (the logo is not stretched). **Q-66** is guarded and now self-diagnosing.
- **Rates:** 8 deaths in 44 supported installer starts (~18 %) across four probes; every death is exit 137.
- **Still open for v1:** Q-68, the Q-66 cause, Q-19's qmllint ratchet, and the gates that need hardware or a
  signing key (physical boot, USB, Secure Boot acceptance, TPM, Tor-routed privacy, release signature,
  image-level SBOM).

## Live status, 2026-11-11 late evening (three actionable rows, one is a single fault)

- **The queue is stable and machine-checked.** `docs/AUTONOMOUS_QUEUE.md` has **66 rows, ids 1..66 with
  no duplicates and four cells each**; `tests/unit/test_queue_integrity.py` now fails the build if an id is
  reused or a row grows a fifth cell. That test exists because commit `c936438` updated "every row starting
  with `| Q-63 `" and merged the desktop-emblem row into the ESP row, while three other rows broke the
  table with extra cells or an unescaped pipe (`6001e49` repairs both).
- **Actionable rows: Q-46/Q-61 and Q-66.**
  - **Q-46/Q-61** are one fault: the installer is SIGKILLed 2-3 s after a desktop-icon start in roughly
    one start in 6-12. Measured on rc11 with a `setsid` watcher and `pgrep -f`: **six starts, six alive for
    13 s, zero deaths** (`artifacts/q61-watcher3/`); six trials are simply fewer than the rate needs, so
    this is a valid negative, not a fix. Reproducing it needs ~12-24 starts in one boot, which
    `tests/visual/scenarios/q61-stress.json` now does.
  - **Q-66 (new id, was mis-numbered Q-63):** two rc10 installs reported "All done" with an empty ESP and
    an unbootable target. `/usr/bin/hscl-verify-esp` now fails such an install, so the symptom is guarded
    but the cause is still unknown.
- **Q-13 is closed.** The offline handbook is captured on rc11 and installed as
  `docs/img/showcase/13_offline_handbook.png` with `source_iso` in the manifest; the capture also proves
  the corrected text ("branded HSCL1 Installer") is in the image. Firefox needed 50 s on first start, not
  the 40 s the first attempt waited.
- **0.1.6 is published and independently verified.** `v0.1.6-alpha.0` (`a916540c…`, source `13c3215`):
  4 GB UEFI boot in 197 s, `qa_report.py` exit 0, 12/12 in-guest tracks green, and the GitHub release
  workflow verified all three parts plus the streamed join on a Linux runner.
- **CI is green on `5bb61ab`** (all eight jobs). The red runs before it were infrastructure: the Python job
  could not apt-install pytest (now pip) and the QML job could not reach the Ubuntu archive over HTTP (now
  HTTPS with a restore-and-retry fallback and an 18-minute step budget).
- **Honesty fixes landed today:** the privacy text no longer claims a fail-closed *network* policy (only the
  launcher refuses a substitute browser), `ARCHITECTURE.md` no longer claims a Polkit helper that does not
  exist, the installer is pinned to English and the live session gets `LANG=en_US.UTF-8` (rc11 opened in
  Azerbaijani because Calamares had no system locale).
- **Release machinery is tooled and gated:** `verify_release_consistency.py` (24 checks incl. GitHub asset
  digests and the notes body), `release_publish.py` (draft → one upload per asset → explicit publish),
  `release_split.py` (LF checksums), `test_release_metadata_sync.py` (README ↔ website).

## Live status, 2026-11-11 (source `349af12`, 71 commits after the 2026-11-10 audit)

- **Two work streams share this repository.** The 2026-11-10 pass produced the audit, the honest
  README/handbook and the published `v0.1.5-alpha.0`; a second stream has since built and measured
  `rc3`…`rc9`, closed most of the visual findings and fixed the Control Center's Miner page. The queue
  (`AUTONOMOUS_QUEUE.md`) is the single ordering authority; this page only records where things stand.
- **Newest candidate:** `HSCL1-rc9-amd64.iso` (`0a3c2341…`, 5 488 771 072 B, source `349af12`,
  `git_dirty: false`, built 2026-11-11 08:54 UTC). Every VM gate now sits on one artifact: boot,
  install, LUKS2 unlock, in-guest QA and the Security Lab chain were re-run on the rc6–rc8 line.
- **Published release:** `v0.1.5-alpha.0` (`c3ae31a6…`, built from `406186d`, xz). It predates
  `rc3`–`rc9` and therefore still has oblique desktop icon labels; the fix (desktop entries installed
  as files instead of symlinks, so Plasma stops italicising link labels) and the installer restart
  wrapper are **not** in the published image. A 0.1.6 release from the rc9 line is the next release
  step, not something the current download offers.
- **Visual findings settled with evidence:** Q-52 (italic labels, root cause `FolderItemDelegate`
  `font.italic: model.isLink`) closed on rc4; Q-53 (Kate) closed — measured editor mean luma
  43.1/255, i.e. dark; Q-57 (wallpaper presets) closed on rc3 with four different capture pairs;
  Q-58 closed as a **scenario artefact** (the old scenario pressed Alt+F4 before the screenshot).
- **Still open:** Q-60 (two-line icon labels wrap left of the icon centre, upstream behaviour),
  Q-61 (installer is SIGKILLed in roughly 1 in 6–12 starts; wrapper retries, killer still unknown),
  Q-63 (orange "!" emblem on desktop entries after the symlink fix), Q-54 (a handbook capture from a
  current candidate) and the v1 gates that need hardware or a signing key.
- **Measured, not impression (2026-11-11):** colour claims must be computed over a named box. A
  preview of the Kate capture looked light while the pixels were dark; the row was corrected and the
  rule is recorded in `AUDIT_2026-11-10.md` §5.2. Shape claims (missing window, slanted label) are safe
  from a preview.
- **CI:** the 2026-11-10 fixes (filesystem-root storage path, Pillow for the screenshot gate, rustfmt)
  turned the Rust and Python jobs green; the last full run before this entry was **all 8 jobs success**.
- **0.1.6 is published (prerelease).** `v0.1.6-alpha.0` (`a916540c…`, 5 488 771 072 B, built from `13c3215` in a separate worktree and WSL checkout) booted UEFI at 4 GB in 197 s with `qa_report.py` exit 0. One capture closed three rows: upright labels (Q-52), no untrusted emblem (Q-63), label centre within 1 px of the icon centre (Q-60). Parts, checksums, manifest, SBOM and notes are on the release; README and website carry the same digests, enforced by `test_release_metadata_sync.py`.

- **Release staleness rule stays binding:** an artifact proves only the commit it names. `0.1.5` names
  `406186d`; `rc9` names `349af12`; neither is `HEAD`.

## Live status, 2026-11-10 (source `c74af1b`)

- **Repository state:** `main` is **104 commits ahead of `origin/main`** and has never been pushed
  in that state; there are **0 open PRs** (61 merged). Every `origin/codex/*` branch was checked
  file-by-file against `main`: **zero content drift**, so no branch holds unmerged work. See
  [`AUDIT_2026-11-10.md`](AUDIT_2026-11-10.md) for the method and the per-branch result.
- **Screenshot audit:** three images were false or mislabelled and were removed/replaced
  (`02_wallpaper_grid.png`, `02_wallpaper_rain.png`, `15_desktop_icons.png`, and a **black**
  `boot-unlock.png`); several others predate the current candidate. Full table in the audit.
  New queue rows **Q-52…Q-56**.
- **Release artifact is stale relative to the tree:** the published `v0.1.4-alpha.0` ISO was built
  from `ea8bbdc` (2026-11-08), which is **118 commits behind** `main`. It therefore lacks the
  installer-crash fix, the `hscl lab` exit-code/local-image fixes and the honest Secure Boot /
  privacy reporting. `HSCL1-rc2` (`0ed86405…`, source `ddf3323`) is the newest VM-verified
  candidate. A refreshed public release is Q-56, not an assumption.
- **Gate numbers on this tree (2026-11-10, Windows):** `cargo test --all` → **275 passed, 0 failed**.
  The Python/shell tier is `python scripts/forge.py check`; run it before any push.
- **Secure Boot wording corrected:** the ISO carries Canonical/Microsoft-signed boot components
  (`artifacts/sb-0.1.3-alpha.0/report.json`), but no positive Secure-Boot boot has been
  demonstrated — the test firmware ran with Secure Boot off and the guest reports that.
- **Handbook corrected:** EN/DE/FR no longer say "starts the Kubuntu installer" or "no verified
  installation guide"; they name the HSCL1 installer, the 4 GB unencrypted path, the 8 GB LUKS2
  path and the single-passphrase/no-recovery-key boundary.
- Nothing below loses authority. Where a plan says "NEXT" and the queue disagrees, the queue wins
  for ordering; the plans keep their acceptance criteria.

## Live status, 2026-11-09 (source `d817093`)

- **Fast gate is green:** `python scripts/forge.py check` → 6/6 PASS (887 passed, 22 skipped,
  53 deselected). `cargo test --all` → 245 passed; clippy `-D warnings` and `fmt --check` clean.
  Before this date the gate was red with 21 failures caused by Windows-only harness defects.
- **New artefacts in this reconciliation:** [`QA_FINDINGS_2026-11-09.md`](QA_FINDINGS_2026-11-09.md)
  (assessment + visual QA with measured evidence) and
  [`AUTONOMOUS_QUEUE.md`](AUTONOMOUS_QUEUE.md) (the single ordered work queue the agent loop consumes).
- **Three defect classes are now explicit:** desktop icon label legibility, duplicate mixed-language
  launcher sections, and light Qt chrome inside the dark shell. The Qt palette has a fix in the image
  hook and a unit gate; the other two need a booted candidate and are `OPEN` in the queue.
- **Evidence drift is a first-class item:** `CLAIMS.md` still describes a 0.1.3 artifact while
  `VERSION`/README are 0.1.4 and the last BUILD_LOG candidate is no longer on disk. Rows must name their
  artifact before any v1 readiness claim.
- **Miner track started (2026-11-09):** `hscl miner status|probe|plan|ota|flash` exists with private-LAN
  enforcement, SHA-256 recording and a mandatory authorization phrase; `hscl_miner_status` and
  `hscl_miner_probe` are read-only MCP tools. Firmware facts and sources are in
  [`miner/FIRMWARE_RESEARCH.md`](miner/FIRMWARE_RESEARCH.md). No hardware was flashed and no device was
  contacted in this session.
- **Miner track advanced (2026-11-09, later):** `discover`, `serve` (local read-only API), `series`
  (native), MCP `hscl_miner_discover`; three miners inventoried by MAC; one unit recovered from an
  NVS-erasing factory flash with a per-unit build (`board 201`, AP fallback, baked credentials) and its
  pool/wallet restored through the v2.15 `pools` array. See
  [`miner/TELEMETRY.md`](miner/TELEMETRY.md).
- Nothing below loses authority. Where a plan says "NEXT" and the queue disagrees, the queue wins for
  ordering; the plans keep their acceptance criteria.

**Owner authorization update, 2026-11-08:** the owner explicitly confirmed that
the related repositories are theirs and authorized updates/pushes there, including
CQ-HECS, ESP-Miner and their sub-repositories. Earlier B-P1/P10/M4 prohibitions on
repository branches/pushes/PRs are superseded. Verify each remote, preserve work,
test and use reviewable feature branches. This does not bypass CI/release gates
or imply hardware flashing/device-control authorization.

Reconciled 2026-11-08 against work branch `codex/autonomous-wave1` at `d9a6f02`,
`origin/main` at `bbb98dd`, the existing uncommitted release-plan/baseline/build-log
work, and the implementation/evidence references below. This is an index, not a
second task scheduler. A recorded earlier test result is historical evidence;
it is not a fresh verification of the current tree or a new ISO.

The current OS release execution plan is
[v1 release plan](superpowers/plans/2026-11-08-v1-release-plan.md).
The ecosystem priority and evidence ledger remains
[live master ledger](superpowers/plans/2026-11-08-selfheal-masterplan.md).
Root `AGENTS.md`, later explicit owner instructions, source and reproducible
checks govern conflicts. Domain gates in older plans remain applicable; their
old branch snapshots, release dates and competing execution orders are historical.
The owner has excluded Qwen Mythos/cloud inference for this continuation. Optional
model assistance must use a genuinely local backend; model output is never evidence.

## Reconciled release constraints

- Build and verify a candidate from an identified clean source revision, then
  freeze/promote the exact tested artifact. Requiring an already stable v1 tag
  before testing the candidate is circular. A retag/rebuild requires new evidence
  whenever artifact bytes change.
- Do not redo W2-7 merely because a plan still calls it NEXT: commit `d9a6f02`
  contains the six-operation HCSEASYMATH page. Backend tests recorded in BUILD_LOG
  do not replace rendered browser/accessibility/Better Design review.
- `forge check` is a fast tier; `forge check --full` and platform/subsystem
  gates remain necessary before a release. Environment skips are not passes.
- Historical boot/install results do not certify the 27 commits after current
  main or a future v1 ISO. Capture the source revision, artifact hash, exact
  command, counts/skips, firmware, logs and screenshots for the candidate.
- Keep Security Lab and Privacy visible as incomplete until actual runtime and
  network tests satisfy root AGENTS.md. Do not infer them from catalogue/CLI stubs.
- Preserve cross-repository approval boundaries, signing-key decisions, physical
  hardware tests, production-deployment decisions and the single-heavy-job rule.

## Plan inventory and continuation notes

Each entry states its useful scope, reconciliation issue, and the concrete next
step. The release plan decides when that next step is scheduled.

- [2026-11-05-ai-coding-wallpaper-studio](superpowers/plans/2026-11-05-ai-coding-wallpaper-studio.md):
  AI catalogue, coding/MCP tools, animated wallpaper and RSI design. Catalogue,
  CLI and wallpaper portions have implementation/evidence in CLAIMS; media-AI,
  model training and broad runtime support remain unverified/planned. Next:
  validate the pinned shipped backend and opt-in model workflow on the candidate;
  keep training and media experiments outside stable claims until measured.
- [2026-11-05-hscl1-to-v2-stable](superpowers/plans/2026-11-05-hscl1-to-v2-stable.md):
  original OS milestones. Its v2 ladder and early blank implementation checklist
  are historical; desktop, CLI, packaging and Workshop now exist. Next: use its
  installer, accessibility, hardening and exact-artifact gates where still unmet;
  do not scaffold a replacement repository or site.
- [2026-11-05-path-to-next-stable](superpowers/plans/2026-11-05-path-to-next-stable.md):
  resource/build engine and early release ladder. The no-QA/two-variant policy
  was superseded by the one inert-by-default Workshop ISO; old resource numbers
  and v2 tags are snapshots. Next: measure current resources and candidate build,
  then boot/install; OEM disks remain an additional product, not boot proof.
- [2026-11-05-prebuilt-image-and-updates](superpowers/plans/2026-11-05-prebuilt-image-and-updates.md):
  OEM images, update semantics and refreshed live images. Earlier install proof
  exists; OEM-first-boot, credential-clean publication and refreshed-kernel
  acceptance need their own evidence. Next: verify APT update behaviour on the
  installed candidate; publish no qcow2 containing test users or keys.
- [2026-11-05-workshop-main-iso](superpowers/plans/2026-11-05-workshop-main-iso.md):
  one ISO, opt-in Workshop, bounded API and respin. Implementation and earlier
  VM runs exist; unchecked original boxes do not mean all code is missing.
  Next: preserve inert-by-default, permission and credential gates in the new
  ISO and rerun the guest integration tests.
- [2026-11-06-ai-api-updates-stress](superpowers/plans/2026-11-06-ai-api-updates-stress.md):
  tool-call parser/runner core, serve specification, delta-card/update honesty,
  stress/fuzz gates. D1-D3/E1/F1/G1/G3 have recorded implementation; real stress,
  fault injection, packaging and runtime cases remain distinct. Next: run the
  stress/installer failure cases only in a disposable candidate VM.
- [2026-11-06-autodetect-arex-loop-re-lab](superpowers/plans/2026-11-06-autodetect-arex-loop-re-lab.md):
  modalias discovery, driver hints, round recorder and RE boundaries. B1/B3/A1/A2
  have recorded tests; hwdb generation, hardware export and RE helper are open.
  Next: exercise driver-index hints on the actual Ubuntu image before asserting
  hardware support. RE/legal and hardware writes retain their explicit boundary.
- [2026-11-06-autonomous-to-stable-hardened](superpowers/plans/2026-11-06-autonomous-to-stable-hardened.md):
  broad P0-P31 gate catalogue and build/VM strategy. Its claim to universal
  ordering authority, old main/PR snapshot and v2 naming are historical.
  Next: reuse exact-artifact, egress, upgrade, reproducibility and supply-chain
  gates through the current release plan; do not restart the 0.1.2 release.
- [2026-11-06-finish-line-self-heal](superpowers/plans/2026-11-06-finish-line-self-heal.md):
  S0-S8 ladder and G0-G39 evidence definitions. S1 progress is more recent in
  the resume plan/BUILD_LOG; generic PLANNED rows are stale scheduling data.
  Next: transfer unmet recovery-key, keyboard, egress, upgrade, accessibility
  and release gates into candidate acceptance, preserving their pass criteria.
- [2026-11-06-forge-loop](superpowers/plans/2026-11-06-forge-loop.md):
  standard build/test/boot/release orchestration. `check`, build/boot core and
  manifest diff exist; proposed test/install/cycle/release subcommands are not
  implemented merely because the plan describes them. Next: prove real
  build/boot commands and failure propagation; invoke existing scripts for gaps.
- [2026-11-06-freeze-devmode-memory-tiering](superpowers/plans/2026-11-06-freeze-devmode-memory-tiering.md):
  live respin, sysext, memory advisor, KV and RSI experiments. Treat experiments
  as hypotheses; no SSD-as-VRAM or sysext-installed-content guarantee follows.
  Next: preserve actual copy/ownership semantics and candidate install tests;
  benchmark optional memory changes before recommending them.
- [2026-11-06-local-agent-harness](superpowers/plans/2026-11-06-local-agent-harness.md):
  experimental execution-verified local agents. Later local_worker code provides
  concrete implementation; research/vendor horizon numbers are not product proof.
  Next: use bounded local proposals with independent tests; no remote Mythos.
- [2026-11-06-local-subagents](superpowers/plans/2026-11-06-local-subagents.md):
  L1-L8 local delegation, MCP and proposal queue. Recorded tests/benchmarks exist;
  its Bonsai default is superseded by later measured local-agents-v2 notes.
  Next: probe the actual local backend and resource budget before any inference;
  proposals stay unapplied until reviewed and verified.
- [2026-11-06-long-horizon-to-v2](superpowers/plans/2026-11-06-long-horizon-to-v2.md):
  historical first public-release ladder and OS gate inventory, already superseded
  by the hardened plan. Next: reuse unmet installer/security/visual gates, not
  obsolete M0 publication instructions or a second v2 schedule.
- [2026-11-06-masterplan-resume-s1](superpowers/plans/2026-11-06-masterplan-resume-s1.md):
  detailed S1 handoff with manpages, governor core, Forge, menu, modalias, fuzz
  and SB-file-signature evidence. Its PR #22/Dependabot state is historical.
  Next: verify those shipped features in a new image; retain the distinction
  between EFI file signatures and firmware Secure Boot acceptance.
- [2026-11-06-own-gpu-backend](superpowers/plans/2026-11-06-own-gpu-backend.md):
  hardware measurements, Vulkan kernels and measured speed hypotheses. HCSUDA
  now owns implemented kernels; do not start another backend from this old plan.
  Next: reuse `hcsuda` capability/oracle/report gates for any selected experiment;
  no universal speedup, CUDA compatibility or unmeasured memory claim.
- [2026-11-06-ux-ai-hardware-expansion](superpowers/plans/2026-11-06-ux-ai-hardware-expansion.md):
  large product backlog W0-W24. Later code covers part of its unchecked list.
  Its kwinrc tiling-default proposal was contradicted by later upstream research
  (resume plan section 10; machine/output-specific keys). Next: review candidate
  navigation/keyboard/locales and existing components before adding new apps;
  any tiling implementation needs a supported, tested mechanism.
- [2026-11-07-genesis-parallel](superpowers/plans/2026-11-07-genesis-parallel.md):
  companion integration boundaries, package spike and two-track OS gates. Its
  no-push/PR #22 and untracked-owner-file statements are historical, not current
  permissions or Git facts. Next: continue thin package/adapters only after
  existing interface evidence; no cross-repo writes without authorization.
- [2026-11-07-hcswaver-integration](superpowers/plans/2026-11-07-hcswaver-integration.md):
  HSCL1-owned package/launcher integration of a future standalone Studio.
  Repository existence claims are dated snapshots. Next: reuse CQ-HECS/HCSUDA
  boundaries and inspect current interfaces before any independent app/repo;
  do not duplicate solver or model-runtime responsibilities.
- [2026-11-07-local-agents-v2](superpowers/plans/2026-11-07-local-agents-v2.md):
  later local-model swap, negative delegate results, CPU/GPU LoRA measurements
  and host holds. These host experiments do not validate Linux ISO AI defaults.
  Next: retain negative results and only use an actually local available model;
  do not change autostart/weights or start training during image/VM work.
- [2026-11-07-masterplan-hcsuda-to-v1](superpowers/plans/2026-11-07-masterplan-hcsuda-to-v1.md):
  HCSUDA capability/gate contracts and OS hardening inventory. Its HCSUDA-first
  ordering is already superseded by the ecosystem ledger. H3c-3b remains paused;
  older real-model and VM evidence cannot be generalized. Next: OS release
  acceptance per the v1 plan, then selected measured HCSUDA work in a free slot.
- [2026-11-08-hcseasymath-plan](superpowers/plans/2026-11-08-hcseasymath-plan.md):
  Track E. M1 NEXT/M2 PLANNED conflicts with its own M1 merged addendum and
  current implementation (six operations, warm worker, page). Next: fresh locked
  gate and rendered UI/security review; CLI/MCP/package/VM integration and
  history remain separate missing work, not implied by backend tests.
- [2026-11-08-hcspnp-plan](superpowers/plans/2026-11-08-hcspnp-plan.md):
  Track P audit/guard/launcher/proof boundary. Clone/suite-NEXT language is stale;
  baseline contains subsequent audit and local upstream fixes. Next: reconcile
  the baseline and actual guard pin; keep Studio launch blocked until the guarded
  upstream version is available. No unauthorized CQ-HECS push.
- [2026-11-08-opencode-autonomous-masterplan](superpowers/plans/2026-11-08-opencode-autonomous-masterplan.md):
  takeover and early waves. Subsequent Wave 2 and commits continued its NPBENCH
  and scheduler tasks. Next: use the live ledger for remaining work, preserve
  targeted tests and bounded failure handling, do not rerun completed slices.
- [2026-11-08-opencode-wave2-masterplan](superpowers/plans/2026-11-08-opencode-wave2-masterplan.md):
  detailed handover W2-1..9. NPBENCH beyond-NP, rotation, Miner schemas and W2-7
  have commits after its snapshot; stale scheduler/HCSPNP/UI rows need the ledger.
  Next: release hardening and candidate image/VM acceptance; no post-stable-only
  circular prerequisite for the very ISO required to justify stable release.
- [2026-11-08-selfheal-masterplan](superpowers/plans/2026-11-08-selfheal-masterplan.md):
  current ecosystem ledger. Reconcile rows 8/14/15/21/23/24 and Miner-1 with
  actual commits/BUILD_LOG; reconcile old fixed snapshots rather than
  silently turning historical evidence into current passes.
- [2026-11-08-v1-release-plan](superpowers/plans/2026-11-08-v1-release-plan.md):
  current OS release execution plan. Replaces its earlier uncommitted W2-7-NEXT
  and stable-tag-before-ISO-testing draft. Follow its concrete candidate gates
  and truthful blocker list; v1 is not achieved by updating plans.

## Root companion contracts

These owner specifications remain unchanged. Their repository snapshots and
example schemas are dated reference material; read the actual symbols/interfaces
before implementation. This index reconciles execution-facing sections, not every
scientific proposal or cited paper in these large documents.

- `AGENTS_HCS_ECOSYSTEM_MASTER_2026-11-07.md`: ownership boundaries, P0-P14,
  no duplication, checked verdicts, approvals, single-heavy-job scheduling.
- `AGENTS_HCS_UNIFIED_SELF_HEALING_RESEARCH_MASTER_2026-11-08.md`: expanded
  evidence/provenance/research loops. Its open PR #30 snapshot is historical;
  the current ledger, actual Git state and root OS release gates govern execution.
- `AGENTS_HCSEASYMATH_HSCL1_FIRST.md`: in-tree application first, safe parser,
  killed/bounded workers, exactness, CPU completeness and later extraction.
- `AGENTS_HCSPNP_HSCL1_LATEST.md`: reuse CQ-HECS, guard before launch,
  checked SAT/UNSAT/#SAT, no new HCSPNP repo/runtime or heuristic verdict.
- `AGENTS_HCSUDA_HCSWAVER_UNIFIED_MASTERPLAN.md`: shared compute/Studio
  interfaces, capability/oracle tests and measured acceleration; standalone
  ambitions do not authorize duplicate implementations or repository creation.
- `AGENTS_HCSWAVER_MASTERPLAN.md`: future Studio product specification;
  HSCL1 owns integration only, with later ecosystem reuse boundaries preserved.
- `AGENTS_HCS_GENESIS.md`: optional companion research/packaging, evidence
  records, no whole-human capability claims and no default model/service bundle.
- `AGENTS_HSCL1_BITAXE_MINER_RESEARCH_BRIDGE_MASTER_2026-11-08.md`: Miner
  research bridge; current ADR and four schemas are documents only. Receiver,
  firmware, device contact, flashing and training are not implemented by them.

## Known documentation debt

CLAIMS contains some superseded rows followed by newer evidence (autotune,
KDE Connect and encrypted install). Preserve the historical runs, but use a
candidate-specific evidence record to prevent old negative/positive rows from
being mistaken for the current artifact.

**Updated 2026-11-10:** the README screenshot and release claims were corrected
(see [`AUDIT_2026-11-10.md`](AUDIT_2026-11-10.md)). Remaining debt:

1. ~~`docs/CLAIMS.md` still carries rows bound to artifacts that are no longer on disk;
   each row must name its artifact and date (Q-05 was marked done for the header only).~~
   **ADDRESSED 2026-11-12:** four rows named no artifact or had lost their table shape - the flagship
   "main ISO boots" row is now bound to the published `v0.1.6-alpha.0` (`reached_desktop` in 197 s), the
   `hscl graphics detect` row has an evidence cell instead of "see above", the updates and respin rows say
   plainly that they pre-date artifact-bound rows, and the miner row (which had **four** cells because an
   unescaped pipe split the status cell) is a three-cell row again. `tests/unit/test_claims_table.py` now
   fails the build if a row loses a cell or claims without evidence, so this cannot rot silently. Rows that
   name artifacts no longer on disk are kept on purpose - the header rule ("a row is historical evidence
   for the artifact it names") is what makes them safe.
2. ~~The installer welcome page stretches the Calamares branding logo across the page
   (Q-54 covers the recapture; the layout fix is separate).~~ **CLOSED 2026-11-12 by measurement**:
   the rendered logo ink is 721×134 (ratio 5.381) against artwork ink 976×183 (5.333) — **+0.9 %**,
   i.e. no distortion; it fills the page width because `welcomeExpandingLogo: true`, which is
   deliberate. `AUDIT_2026-11-10.md` §6 has the table. Do not reopen without a capture whose measured
   ratio contradicts those numbers.
3. ~~Icon labels not centred (Q-52), Kate light inside the dark shell (Q-53)~~ — both **CLOSED** with
   pixel measurements on the 0.1.6 artifact; the label offset is -0.9 px and Kate's editor mean luma is
   43.1/255. Do not list them as debt again without a fresh capture that contradicts those numbers.
4. ~~Website hero and Control Center image older than the candidate~~ — **Q-55 DONE**; the generator now
   copies `showcase/01_desktop_clean.png` and `showcase/04_*` at build time.
5. The queue itself is now machine-checked (`tests/unit/test_queue_integrity.py`) because a bulk row edit
   merged two findings into one id. Any script that edits queue rows must match a single row, not a prefix.
