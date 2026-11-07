# Building HSCL1

The image build runs on an **Ubuntu 26.04 builder** (a WSL2 distro or a VM). VM tests can run on the same machine; on
Windows the fast path is native QEMU with WHPX (see [`TESTING.md`](TESTING.md)).

## Requirements

- Linux x86_64 builder, 16 GB RAM recommended, at least 40 GB free disk (the script checks).
- `sudo` (used only for `unsquashfs`/`chroot`/`mksquashfs` on a script-owned work directory; no host disk is touched).
- Packages: run `scripts/bootstrap-build-host.sh`. Also needs Rust (see `rust-toolchain.toml`) and mdBook
  (`cargo install mdbook --locked --version 0.4.52`).

## Steps

```console
$ scripts/fetch-base-iso.sh                       # downloads and verifies kubuntu-26.04.1-desktop-amd64.iso
$ scripts/remaster-iso.sh --out ~/hscl1-build/out/HSCL1-0.1.3-alpha.0-amd64.iso --fast
```

- `--fast` uses quick zstd compression (development); omit it for the xz release compression.
- One output: the main ISO (live + installer + opt-in Workshop tools). `verify-image.sh` fails the build if Workshop is enabled or
  exposes a socket.
- `--force` is required to overwrite an existing output file.

What the script does: verifies the base ISO checksum, builds the `hscl` binary and the HSCL1 `.deb` packages
(`packages/debian/*`), unpacks the live root filesystem, installs the packages with `dpkg`, runs the hooks in
`distro/live/hooks`, then runs `distro/live/verify-image.sh`, which **fails the build if any branding or package check
fails**. Only then does it re-squash the filesystem and rebuild the ISO, replaying the upstream boot structure
(El Torito + GPT) so the signed boot chain is preserved.

## Packages

| Package | Purpose |
|---|---|
| `hscl-base` | `hscl` CLI, release marker |
| `hscl-branding` | logos, wallpapers, colour schemes, os-release/issue/About, Calamares branding |
| `hscl-desktop` | HCS Hybrid Desktop layout (top bar, dock) and look-and-feel |
| `hscl-security` | sysctl hardening, first-boot firewall service |
| `hscl-handbook` | offline handbook (EN/DE/FR) and launcher |
| `hscl-control-center` | Qt 6 / QML Control Center |
| `hscl-workshop` | opt-in Workshop: evidence channel, VM API, respin (inert by default) |

Each package is a tree under `packages/debian/<name>`; an optional `build.sh` generates files (it receives `STAGE`,
`ROOT`, `VERSION`). Generated files are never committed.

## Reproducibility

Not bit-for-bit reproducible yet: squashfs timestamps and package build times differ between runs. The base ISO is pinned
by upstream checksum; manifests are generated from the finished image in the release process.

## Build engine and resources

- The unpacked base filesystem is cached in `work/pristine` (keyed by the base ISO checksum) and customised through an
  overlayfs, so a repeat build skips the unpack and never modifies the cache.
- `mksquashfs` runs with `-processors $(nproc) -mem 1G`.
- The script refuses to start with less than `HSCL_MIN_FREE_MB` (default 3000) MB of available memory; the VM harness refuses
  with less than VM size + 1.5 GB. On a 20 GB Windows host keep WSL at about 10 GB (`~/.wslconfig`: `memory=10GB`,
  `[experimental] autoMemoryReclaim=gradual`).
