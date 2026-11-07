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
3. **Evidence bundle**: `scripts/make_release.py VERSION --iso ISO --prebuilt QCOW2 --out DIR
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
is ticked or the gap is written into `docs/KNOWN_LIMITATIONS.md` and the release notes.

## What is still missing here

- No documented signing-key rotation (owner holds the key).
- The website download metadata is updated by hand from the release; there is no automation that reads the
  GitHub release yet.
- `forge release` (plan section 5 of the forge loop) is still not implemented - the steps above are run
  manually or by the release orchestrator used for 0.1.2.
