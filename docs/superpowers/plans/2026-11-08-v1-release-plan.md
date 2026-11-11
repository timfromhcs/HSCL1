# HSCL1 v1 execution masterplan — reconciled 2026-11-08

Status: ACTIVE. Root `AGENTS.md` is the release contract. The [ecosystem ledger](2026-11-08-selfheal-masterplan.md) retains P0–P14; this plan makes the OS release track executable. Research acceptance criteria and approval boundaries remain in force.

Later owner authorization (2026-11-08): update/push the owner's related repositories,
explicitly CQ-HECS, ESP-Miner and all their sub-repos. B-P1/repo-write M4 are cleared;
prepare verified feature branches and PRs without re-asking. Preserve CI, no-force,
release and hardware-operation gates. CQ-HECS guard/bridge publication now unblocks
the safe HSCL1 Studio launch path once a reviewed runtime revision is pinned.

[All 27 plans and eight companion contracts](../../PLAN_INDEX.md) are indexed with continuation notes. Historical content is preserved. The pre-existing uncommitted release draft is preserved at [original draft](../../history/2026-11-08-v1-release-plan-original-draft.md). No Qwen Mythos/cloud inference is permitted; optional model assistance must use a verified local backend. No standing automation is implied.

## 1. Measured takeover and previous stopping point

- Fetched `origin/main`: `bbb98dd`; branch `codex/autonomous-wave1`: `d9a6f02`. Main has 0 unique commits, branch has 27. No history rewritten.
- Only open PR: [#37](https://github.com/timfromhcs/HSCL1/pull/37). All 16 checks succeed at d9a6f02; no review threads. Its old title understates NP benchmark, scheduler, math and Miner-schema scope. These checks do not certify takeover changes.
- Preserve existing BUILD_LOG and HCSPNP_BASELINE changes. Baseline audit parts 1–10 are later than the stale ledger.
- Previous source milestone: W2-7 six-operation HCSEASYMATH page, d9a6f02, after MINER-1 schema/ADR work. BUILD_LOG records 244 math tests. Rendered UI/accessibility/Better Design review remains open. Do not reimplement the page.
- NP benchmark slices 1–6 and scheduler rotation exist. Schemas are not a Miner receiver. HCSUDA H3c-3b remains paused.
- Existing 0.1.3 ISO: source `a55e02320f23b0cb74a06d6215688aafb1557690`, SHA256 `fc81ad1d93efeac61904879e9def34e39cdceb982bf7aafc070b34afdd4d1ebb`. Live boot succeeds; recorded exact-image install attempt says `reached_desktop: false`. Earlier installs do not close this gap.
- Secure Boot PE signatures exist; candidate firmware enforcement/in-guest state is unproven. Release signing and physical hardware results remain absent.
- Host: about 20 GiB usable RAM, initially C: 63 GiB / E: 71 GiB free. WSL Ubuntu 26.04.1, QEMU and `/dev/kvm` exist. NAT setup emitted fallback-network warning; verify connectivity before downloads. Existing Linux checkout `~/hscl1-src` is at `2b65013`, not the workbranch head.

## 2. Corrections to the old plan

1. Build a clean candidate before acceptance. Requiring stable v1/tag before candidate VM tests was circular. Changed bytes require new hash-bound evidence.
2. Never relabel an old image. Version, source commit, size, hash, non-QA status and explicit clean-tree attestation must agree. Stable packaging also requires a reviewed readiness report covering all 21 root §14.2 gates.
3. Complete mandatory OS behavior/evidence before optional inference kernels, beyond-NP research, physics or Miner hardware. Preserve their domain gates; do not mark them complete or invent new priorities.
4. `forge check` is a fast tier. Full pytest, Linux, Rust, Qt/QML, dependency audits, math lock and VM gates are distinct. Skips/deselections are not passes.
5. Scope claims to source revision and ISO digest. CLI spec generation is not Podman execution; PE signatures are not firmware proof; API tests are not rendered review.

## 3. Execution batches

### V1-A — baseline and release preflight: TESTED manually; verify MCP unavailable

Owner: current agent. Paths: plans/index, CLAIMS, KNOWN_LIMITATIONS, BUILD_LOG, RELEASE_PROCESS, `scripts/make_release.py`, `tests/unit/test_make_release.py`.

- Preserve inputs and reconcile plans/ledger completed rows.
- Regression-test relabel/path escape, missing clean-tree attestation, QA image, bad size/source identity, premature output and missing stable readiness against original code.
- Require nonempty evidence and SHA256 binding; reject missing/failed/skipped/wrong-artifact stable reports. A named reviewer owns semantic judgment: the assembler validates attestations and hashes, not screenshot meaning.
- Gate: targeted Windows/WSL tests, `forge check --full --strict`, root Rust fmt/clippy/tests, verify tool. Record tool-discovery limitations honestly.

### V1-B — critical feature gap closure: IN PROGRESS (builder lab experiment)

One subsystem per reversible batch; inspect real symbols/call sites first.

- Installer recovery method/instructions, unencrypted `/boot` explanation, explicit final disk confirmation; disposable VM disks only.
- Inspect `hscl lab` existing implementation; complete rootless Podman runtime, digest pinning, explicit workspace/network permissions; demonstrate no home/credential-agent/device leakage. No Kali host APT.
- Safe Tor workflow with fail-closed application behavior. Ephemeral live mode stays experimental until mount/swap/journal/network evidence exists. No Tails equivalence.
- Implement keyboard bindings before shortcut claims; critical installer/security/privacy/recovery EN/DE/FR strings and accessibility gate.
- Installed-system doctor, updates/recovery and AI setup with safe CPU fallback; no unmeasured Vulkan performance claims.
- UI changes retain product theme, Better Design principles/review and rendered evidence. Do not replace existing scaffolds.

### V1-C — clean candidate build: PLANNED, heavy slot

- Recheck base ISO/packages using official primary sources; resolute only, exact package versions/source hashes/signing keys.
- Freeze verified source commit; sync a separate clean Linux checkout on NVMe. Inspect cache/output and physical C: space: WSL filesystem capacity is not host free capacity.
- Existing `scripts/remaster-iso.sh`/`forge build`, image validation, manifest, SBOM and hashes from actual bytes; inert Workshop, signed boot components and hybrid structure preserved.
- Candidate name/version equals manifest; RC clearly marked. A final-version artifact can be staged privately while stable gates remain open.
- No credentials, dirty source or fabricated manifest provenance. Rebuild after minimal defect fixes; never overwrite unrelated artifacts.

### V1-D — exact-image VM/install matrix: PLANNED, heavy slot

- QEMU UEFI and BIOS; Secure Boot enforcement firmware plus guest state; live desktop, installer, keyboard/layout switch, guest network and everyday apps.
- Unencrypted/LUKS2 disposable installs; wrong/correct passphrase, recovery, installed reboot, doctor, update and isolation tests.
- VirtualBox UEFI where required: absent environment is BLOCKED, never passed. Hardware claims restricted to measured devices.
- Capture ISO digest, source, command, firmware/acceleration, result, logs/screenshots and evidence hashes. Investigate existing 0.1.3 failure as reproducer. Old evidence cannot certify candidate bytes.

### V1-E — integrity, review and publication: PLANNED

- Review every §14.2 gate, source offer/licenses/advisories, docs and links. Writing a critical failure into limitations cannot waive it.
- `hcs.release-readiness.v1`: exact version/ISO SHA256/commit, named reviewer, all 21 PASS gates with existing SHA256-bound evidence. Missing/failed/skipped gates block stable; useful incomplete builds remain previews/RCs.
- Distribution gates (uploaded links and production build) need staged/reviewed publication. The local assembler never tags/signs/uploads; it cannot independently prove remote URLs from a report.
- Use owner-controlled signing identity. Cross-repo pushes, device flashing, legal acceptance, physical testing and production permissions retain their existing boundaries.
- Freeze accepted bytes; generate SHA256SUMS/split/join, SBOM/source reference and signature instructions; verify actual release URLs and website metadata. No placeholder downloads or v1 completion claim before all required deliverables.

## 4. Resource/autonomy and handoff

One heavy job: ISO/VM, local inference or HCSUDA. VM disks on inspected NVMe under `C:\AI\vmtest` or explicit Linux build area. No host-disk installer operation. Independent read-only audits may run concurrently.

Every batch: observe diff, hypothesis, smallest patch, targeted/subsystem/full gates, log exact counts/skips/artifacts, update plan/ledger, release lock. Preserve unrelated work. Three meaningful failed remedies need a concrete blocker/reproducer; continue independent work without guessing. Do not create background automations, contact devices or send messages as side effects.

V1-A source checkpoint: `8680e5d`; full Forge 857 passed / 22 skipped, changed WSL 57 passed, separate full WSL 876 passed / 3 skipped, Rust 202 passed. verify MCP cannot discover this suite; that tool result remains ok:false. V1-B builder experiment now proves the existing image digest and restricted run/basic install on Ubuntu WSL only; see [lab probe](../../research/2026-11-08-security-lab-builder-probe.md). Next: make the lab lifecycle/execution and package dependencies real, then test them in an HSCL1 candidate guest; close installer recovery/Privacy/critical-i18n gaps before stable acceptance. v1 remains the objective, not the current status.

### V1-X — local quality audit and harness repair (2026-11-09, source `d817093`)

The fast gate was red on the Windows host (21 failures) for harness reasons, not product logic. Repaired
and now green: `forge check` 6/6 (887 passed, 22 skipped), Rust 245 passed, clippy/fmt clean.

- Full findings: [`docs/QA_FINDINGS_2026-11-09.md`](../../QA_FINDINGS_2026-11-09.md).
- Ordered work: [`docs/AUTONOMOUS_QUEUE.md`](../../AUTONOMOUS_QUEUE.md). Item Q-10 (clean candidate build)
  is the blocking dependency for every `VM-PENDING` row, including the Qt palette fix.
- New open defects that v1 acceptance must close: desktop icon label legibility, duplicate mixed-language
  launcher sections, installer top-bar clipping, stale showcase caption, Qt/QML gate hole, artifact
  identity drift in `CLAIMS.md`.
- Carried forward unchanged: V1-C (clean candidate), V1-D (exact-image VM/install matrix), V1-E
  (integrity/review/publication). No stable claim is made by this section.

### V1 status, 2026-11-11 (measured; stable v1 **not** reached)

This section records where the batches above actually stand. It does not change their acceptance
criteria, and nothing here is a stable-release claim.

| Batch | Status | Evidence | What is still missing |
|---|---|---|---|
| V1-A | **TESTED** | `forge check` green, full CI matrix green on `5bb61ab` (8/8 jobs, including QML), `make_release` regression tests | `verify` MCP still cannot discover this suite; the tool result stays `ok:false` and is recorded as such |
| V1-B | **PARTIAL** | `hscl lab` builds a typed rootless Podman command (digest pinning, `--cap-drop=ALL`, `no-new-privileges`, read-only root, `--network=none` by default, one lab folder); `tests/unit` + guest run cover it. Tor launch refuses a substitute browser. `kglobalshortcutsrc` binds Meta shortcuts. Calamares en/de/fr notes and Control Center `.qm` files are image gates. | No recovery key: the installer sets exactly one passphrase and says so (a documented v1 gap, not an accident). No typed erase confirmation — the summary page is the only confirmation step. No fail-closed **network** policy for Tor, only a refused browser substitute. Accessibility gate is partial (Control Center pinned, installer not). |
| V1-C | **IMPLEMENTED + TESTED for candidates** | `HSCL1-rc11-amd64.iso` on disk; `v0.1.6-alpha.0` built from `13c3215` in a private work dir with `git_dirty: false` | The published image predates later fixes: the installer language pin, the live `LANG`, and the removal of the dead `desktopFont` key. A stable artifact must be built after them. |
| V1-D | **VM-VERIFIED in parts** | UEFI live boots (4 GB, 197 s on 0.1.6), unencrypted and LUKS2 installs with installed-system reboot on rc6-rc11, `qa_report.py` exit 0, 12/12 in-guest tracks on 0.1.6 | No legacy-BIOS profile in the recent runs, VirtualBox is **BLOCKED** (not installed), and Secure Boot is not demonstrated: the ISO carries signed components but no positive Secure-Boot boot exists. |
| V1-E | **PARTIAL** | `v0.1.6-alpha.0` prerelease with 8 assets, LF `SHA256SUMS`, SBOM, manifests and notes; `verify_release_consistency.py` 24 checks incl. GitHub asset digests; `release_publish.py` encodes the draft→upload→publish order | No signing key, so the release is unsigned and says so. No stable v1 tag. The Vercel site was not redeployed for this prerelease. |

Two defects still block a stable claim and are tracked in `docs/AUTONOMOUS_QUEUE.md`:

- **Q-46/Q-61** — the installer is SIGKILLed 2-3 s after a desktop-icon start in roughly one start in
  6-12, with no core and no OOM line; `/usr/bin/hscl-calamares` restarts it inside the first minute so an
  install stays possible. Reproducing it needs 12-24 starts in one boot.
- **Q-66** — two rc10 installs reported "All done" with an empty ESP and an unbootable target. The guard
  (`hscl-verify-esp` as a `shellprocess` after `bootloader`) now fails such an install; the cause is open.
