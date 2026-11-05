# Contributing to HSCL1

Thank you for helping. HSCL1 has one rule above all: **nothing is called working until it was run.** Say in every change what you
actually executed (unit test, VM, hardware). `docs/CLAIMS.md` is the single table of what is verified and how.

## Setup

- Rust (stable, pinned by `rust-toolchain.toml`), Python 3.10+, `shellcheck`, `pytest`.
- Optional: Qt 6 (`qt6-declarative-dev`, `qml6-module-qttest`) for the QML tests, `mdbook` for the handbook.
- The image build and VM tests run on an Ubuntu 26.04 builder with QEMU; see [`docs/BUILDING.md`](docs/BUILDING.md) and
  [`docs/TESTING.md`](docs/TESTING.md). The development loop (`scripts/workshop/*`) lets you push changes into a running VM and
  re-create an ISO without a full rebuild.

## Before you open a pull request

```console
$ cargo fmt --all -- --check && cargo clippy --all-targets -- -D warnings && cargo test --all
$ python -m pytest tests -q
$ shellcheck -S warning scripts/*.sh distro/live/*.sh packages/debian/*/build.sh
```

CI runs the same checks (`.github/workflows/ci.yml`). Do not skip or weaken a test to get a green run; if a test depends on the
environment, skip it narrowly with a stated reason.

## Rules that protect users

- No secrets, tokens, VM disks, ISOs or personal data in Git.
- No telemetry. No silent network calls. Optional diagnostics must be opt-in and local-first.
- Privileged operations go through the reviewed helper/allow-lists, never through free-form shell text.
- Security Lab tools stay in containers/VMs; the host never gets Kali repositories. HSCL1 is not Tails and makes no anonymity claim.
- Accessibility is a feature: keyboard path, accessible names, contrast, reduced motion, EN/DE/FR strings.
- Third-party code and models keep their licences; add them to `docs/LICENSES.md` with source and licence before shipping.

## Commits

Small, reversible, descriptive (`feat(area): ...`, `fix(area): ...`, `docs: ...`, `test: ...`). Never force-push shared branches.

## Licence

By contributing you agree that your contribution is licensed under **GPL-3.0-or-later** (see `LICENSE`).
