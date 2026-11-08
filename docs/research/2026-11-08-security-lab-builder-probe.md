# Security Lab builder probe — 2026-11-08

Status: TESTED on the Ubuntu 26.04.1 WSL build host only. Not VM-VERIFIED on HSCL1 and not part of a stable-release guarantee. The CLI still prints specifications; it does not execute containers.

## Source and upstream references

`cli/hscl/src/lab.rs` and `main.rs` at d9a6f02 generate the commands; unchanged by release-preflight commit 8680e5d. Specs were obtained using the actual CLI via `cargo run -q -p hscl -- --json lab spec` with the existing digest in `containers/kali/image.pin`.

Official guidance: [Kali Podman images](https://www.kali.org/docs/containers/using-kali-podman-images/) and [Podman rootless documentation](https://docs.podman.io/en/stable/markdown/podman.1.html). Container package installation remains inside Kali; the build host uses only Ubuntu resolute packages.

## Actual experiment and evidence

Evidence directory: `artifacts/lab-builder-20261108/` (local, not tracked). No host folder, SSH agent, device or credential store was mounted. No network attack/scan was run. Container networking was enabled only for official package retrieval during tool installation.

- Builder packages: Ubuntu podman 5.7.0+ds2-3build1, uidmap, slirp4netns, later passt 0.0~git20260120.386b5f5-1. About 107 MB installed. `podman info` reports rootless=true, amd64, cgroup v2/systemd. Initial root mount propagation warning is retained in `info.stderr`.
- Package defaults enabled netavark DHCP proxy units. These newly introduced units were disabled/stopped. `podman.socket`, `netavark-dhcp-proxy.socket` and `.service` all report disabled/inactive. No autostart is required for this experiment.
- `pull.log` and `image-inspect.json`: exact multiarch digest `sha256:7997e0581c4f5c185cfe6773d5cae8fcc7c6b79798726ccaabf843af4bcd2013` pulled successfully; amd64 child `sha256:73915d5d54833d498f52fd200960126be4a2dbdcc110d75d70839c4ef155ed03` also matches the pin comments. This proves digest agreement, not an additional publisher-signature guarantee.
- `run-spec.json`, `probe.py`, `isolation-probe.json`: generated run argv used with only interactive/TTY allocation removed for a headless probe, replacing the default shell with a fixed diagnostic script. Exit 0: CapEff=0000000000000000, NoNewPrivs=1, interface list only lo, no route entries, write to `/etc` refused. All generated memory/CPU/PID restrictions retained. No host mount in this run. Container root is user-namespaced; it is not host root.
- `install-spec.json`, `install-result.json`: first exact generated install failed with exit 127 because `pasta` was missing. No privilege/network-boundary weakening was used.
- After installing Ubuntu `passt`, `podman start --attach hscl-lab-install-v1-probe` executed that same created container; `install-attempt2.log` and `install-container-inspect.json` show exit 0, no mounts and Privileged=false. The basic allow-listed packages installed with only CHOWN/DAC_OVERRIDE/FOWNER/SETUID/SETGID; no CAP_SETFCAP was added. The nmap package emitted its setcap-refused warning, retained in the log. Packet capture/raw networking functionality is not established by installation.

## Conclusions and remaining acceptance

The existing restricted argv can run on this builder and install a basic tool group after its network helper dependency is present. Keep the tested digest; do not float a latest tag. A future dependency/package definition must include the helper and preserve inert service defaults.

Still open: explicit workspace bind test, resource-limit inspection, local-image commit/digest lifecycle, real tool behavior under no-capability defaults, safe CLI execution, image packaging and actual HSCL1 live/installed VM tests. None of these is inferred from this experiment. Privacy workflow and Secure Boot gates are unrelated and remain open.
