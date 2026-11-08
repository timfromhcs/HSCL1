# Release process

What runs where, what the scripts refuse to do, and which steps are the owner's. Everything below was
read from the scripts in `scripts/` on 2026-11-07; if a script changes, this page has to change with it
(the doc-command gate only checks `hscl ...` invocations, not these).

## Rules that never bend

- **A release is built from a commit, never from a dirty tree.** `scripts/remaster-iso.sh` stamps
  `git_commit` and `git_dirty` into `<iso>.manifest.json`; `forge build` refuses to start when
  `git status --porcelain` is not empty.
- **The artefact proves itself.** Every claim in the release notes needs a file under `artifacts/` that was
  produced from the very ISO being published - boot screenshots, the in-guest report, the install log.
- **Nothing is published by an agent.** Tagging, signing, `gh release upload` and the production website
  deploy are owner steps. The scripts stop and say so (`make_release.py` prints
  `BLOCKED (owner decision needed)`).
- **No placeholder in a release.** `make_release.py` refuses the set if `GENERATE_FROM`, `ACTUAL_`, `TODO`,
  `TBD`, `PLACEHOLDER` or `FIXME` appears in any manifest or in the notes - the template in AGENTS.md
  Appendix B is a schema, not a value.

## Steps

1. **Version**: write the version into `VERSION` (single source; the Rust crate inherits it via the
   workspace `version.workspace = true`, and the ISO build reads `VERSION`). A dev image built before the
   bump carries the old string - harmless for content validation, not acceptable for the release artefact.
2. **Gates** (see `docs/TESTING.md` for the exact commands): `forge check --strict` green on the Windows
   host **and** in WSL, `cargo test`, `cargo clippy -D warnings`, `cargo fmt --check`, then the image gates
   on the exact artefact: build (`forge build`), boot (`forge boot`, UEFI; BIOS and Secure Boot as separate
   runs), in-guest checks (`scripts/workshop/e2e_cli.py`), install into a disposable qcow2, installed-system
   boot, LUKS2 unlock.
3. **Evidence bundle**: `scripts/make_release.py VERSION --iso ISO [--prebuilt QCOW2] --out DIR
   --evidence NAME=PATH ...`. It refuses when an artifact or manifest is missing, when the ISO does not
   attest `workshop_default: disabled`, when the prebuilt manifest does not record a clean credential scan,
   or when a manifest hash does not match the file. Output: ISO, qcow2, `SHA256SUMS`,
   `build-manifest.json`, `release-notes.md`.
4. **Split for upload**: `scripts/release-split.sh` cuts the ISO into parts below the GitHub asset limit;
   `scripts/release-join.sh` reassembles them, and the digest check proves the parts reproduce the ISO.
5. **Owner**: create the tag on the release commit, sign `SHA256SUMS` with the maintainer key, create the
   GitHub release (prerelease until AGENTS.md §20 is complete), upload the assets, run the cloud verify and
   merge workflow, then update the website download metadata and deploy.

## Honest labels

The version's suffix decides what may be claimed: `alpha` for a working preview with a documented "not
verified" list, `beta` once the modes (lab, privacy, local AI) are in the image, `rc` once Secure Boot,
BIOS/USB boot and fault injection are measured, and `1.0.0`/`2.0.0` only when every gate in AGENTS.md §14.2
is satisfied with evidence. A critical gap cannot be waived by writing it into limitations:
use a preview or RC while a required gate is incomplete.

## Release preflight and stable readiness

The assembler rejects version/path manipulation, relabelling an older image, missing or non-boolean
clean-tree/non-QA attestations, size/hash mismatch and incomplete source identity. Evidence must be
nonempty regular files; output directories must be empty. Validation failures occur before copying
the image. Preview assembly is not boot/install certification: it retains caller evidence and gaps.

Stable versions with major >= 1 require `--readiness REPORT.json`. The report is a reviewed attestation,
not an automated interpretation of screenshots or logs. It has `schema: hcs.release-readiness.v1`,
the exact `version`, `iso_sha256`, `git_commit`, a nonempty `reviewer`, and `gates` containing exactly
these 21 identifiers, in AGENTS.md §14.2 order:

`iso_build`, `artifact_manifest`, `uefi_boot`, `secure_boot_status`, `live_desktop`, `installer_start`,
`vm_install`, `installed_reboot`, `luks2`, `desktop_components`, `critical_i18n`, `doctor`, `apt_sources`,
`lab_isolation`, `privacy_claims`, `vulnerabilities`, `release_docs`, `supply_chain`, `release_links`,
`website_build`, `limitations`.

Each gate must contain `status: PASS` and a nonempty `evidence` list of objects with `path` and `sha256`.
Paths resolve relative to the report file (absolute paths also work). Every file must exist, be
nonempty and match its digest. Missing, failed or skipped gates are refused; `--gap` cannot override
stable gates. The report and general evidence hashes are recorded in `build-manifest.json`.
The reviewer must inspect underlying results and confirm that they belong to the specified artifact;
hash validation alone cannot establish their truth. Distribution gates require actual staged-upload
and website-build evidence; local assembly does not independently verify remote URLs or publish.
Preview/RC packaging remains possible without a stable report and must disclose incomplete gates.

Build a clean candidate before acceptance; never require a stable tag before its own VM tests.
If bytes change on rebuilding, rerun affected exact-artifact gates. See the
[current v1 execution plan](superpowers/plans/2026-11-08-v1-release-plan.md).

## What is still missing here

- No documented signing-key rotation (owner holds the key).
- The website download metadata is updated by hand from the release; there is no automation that reads the
  GitHub release yet.
- `forge release` (plan section 5 of the forge loop) is still not implemented - the steps above are run
  manually or by the release orchestrator used for 0.1.2.
