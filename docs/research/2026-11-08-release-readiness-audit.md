# Release readiness audit — 2026-11-08

Scope: local repository, release scripts, workflow configuration and recorded local artifacts. Read-only code audit; no image was built, VM started, container launched, release published or external model contacted for this audit. Documentation reconciliation is not new test evidence.

## Source and artifact boundary

- Source snapshot: `codex/autonomous-wave1` at `d9a6f02`, whose change exposes six HCSEASYMATH operations in the one-page UI.
- Local release set: `artifacts/release-0.1.3-alpha.0/build-manifest.json` records commit `a55e02320f23b0cb74a06d6215688aafb1557690`, build time `2026-11-07T09:28:26Z`, ISO size 5026742272 bytes and SHA-256 `fc81ad1d93efeac61904879e9def34e39cdceb982bf7aafc070b34afdd4d1ebb`. The audit read the recorded digest; it did not recompute the 5 GB ISO hash.
- That set records `signed: false`, `published: false`, and no prebuilt disk image. Its release notes leave installation on the exact ISO, Secure Boot firmware acceptance, brand/shortcut audit and physical hardware unverified.
- `artifacts/forge/boot-0.1.3-alpha.0/result.json`: UEFI, Secure Boot not requested, `reached_desktop: true`.
- `artifacts/install-0.1.3-alpha.0/result.json`: `reached_desktop: false`. This is a failed desktop-reaching attempt, not evidence that installation completed. Earlier successful installation/LUKS runs do not close the exact-image gap.
- `artifacts/sb-0.1.3-alpha.0/report.json`: Microsoft/Canonical PE signers in shim, GRUB and kernel. It contains no firmware acceptance result or in-guest Secure Boot state.

## Existing test evidence and limits

`artifacts/forge/20261108-135735/summary.json` records 773 Python tests passed, 22 skipped and 53 deselected, plus passing bash syntax, ShellCheck and secret scan steps. Its WSL changed-test step was skipped because no changed tests were found. `artifacts/forge/20261108-134544/summary.json` additionally records the hash-locked HCSEASYMATH gate with 244 passed and one warning. These are historical recorded results, not a newly executed verification or complete platform/release gate.

## Concrete release-engineering findings

1. `scripts/make_release.py`, `build_release`: a missing `git_dirty` is accepted by a truthiness check. Require the explicit boolean `False` and validate required manifest fields/types.
2. The requested release version is not matched to the ISO manifest version; an older ISO can be renamed as a newer release. Bind output identity to the artifact manifest and reject QA images for release use.
3. Evidence is optional; supplied paths are checked only for existence. Failure JSON, directories and unrelated files satisfy that check. A stable release needs typed, successful evidence tied to the exact ISO hash and source commit, with required gates distinct from optional preview attachments.
4. `1.0.0` receives no stronger validation than a preview. A limitations entry cannot waive a critical gate in `AGENTS.md` section 14.2. Until a complete stable gate exists, fail closed for stable assembly rather than infer readiness from a version string.
5. Placeholder validation happens after the output ISO is copied. Preflight all refusals before creating output, and avoid leaving a partial bundle presented as usable output.
6. `.github/workflows/release.yml` checks out the workflow revision, not explicitly the release tag, before running the split/join verifier. Record and justify the trusted verifier revision or pin it to the intended release source so verification is reproducible.

The existing `tests/unit/test_make_release.py` tests dirty=true, hash mismatch, missing evidence and placeholders, but not the missing-dirty, version-mismatch, failed-evidence or stable-readiness cases above. These findings are source observations, not newly executed exploit demonstrations.

## Plan corrections

Prioritize release artifact identity and exact-image installation/boot evidence over optional HCSUDA/benchmark research. Keep old image claims separate from current source features. Reconcile the historical autotune, KDE Connect and HCSEASYMATH rows in `docs/CLAIMS.md`, and distinguish the tested `hscl lab` spec generator from a real runtime in `docs/KNOWN_LIMITATIONS.md`.

The next meaningful release cycle is: fail-closed assembler checks; clean source checkpoint; build a candidate; boot and install that exact artifact on disposable disks; collect installed-system and encryption/recovery evidence; close critical localization/security/documentation gates; only then assemble/sign/publish stable artifacts under the applicable authorization. No v1 status is awarded by this audit.

## Follow-up resolution in this continuation

The findings above describe the audited d9a6f02 implementation. Commit `8680e5d` now rejects incomplete/nonboolean clean-tree attestation, QA images, version relabeling (including the prebuilt manifest hscl1_version), invalid timestamps, wrong size/hash/source identity, non-file evidence and nonempty output directories. Stable 1.x+ additionally requires the reviewed 21-gate artifact-bound report; the reviewer still must interpret real results. All refusal preflights run before copying normal immutable inputs. The assembler does not claim to interpret arbitrary preview evidence as successful VM tests.

New release regressions were red before the patches and now number 37 passing on both Windows and WSL. Full Forge and full WSL evidence is in BUILD_LOG. This is source/tooling progress, not a newly verified image. The workflow verifier revision finding remains open. Separately, the actual local Security Lab digest/run/install experiment is documented in `2026-11-08-security-lab-builder-probe.md`; it does not close HSCL1 guest/runtime gates.
