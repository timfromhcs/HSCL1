# HSCL1 plan reconciliation index

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

1. `docs/CLAIMS.md` still carries rows bound to artifacts that are no longer on disk;
   each row must name its artifact and date (Q-05 was marked done for the header only).
2. The installer welcome page stretches the Calamares branding logo across the page
   (Q-54 covers the recapture; the layout fix is separate).
3. Desktop icon labels are not centred under their icons (Q-52), and Kate renders with a
   light palette inside the dark shell (Q-53).
4. The website hero and Control Center image are older than the current candidate (Q-55).
