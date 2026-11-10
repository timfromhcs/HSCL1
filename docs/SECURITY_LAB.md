# Security Lab (specification TESTED; builder experiment TESTED; HSCL1 guest/runtime still open)

Authorized testing only. Kali tools run **only inside rootless containers** (later: disposable VMs); the host never gets Kali or Debian repositories.
HSCL1 is not an official Kali product.

## What exists

`hscl lab` builds a rootless `podman` command from typed options. It **never runs a shell** and has **no field** for `--privileged`,
host network/PID/IPC, devices, extra capabilities or arbitrary mounts. CLI execution subcommands (`run`, `install`, `commit`, `destroy`)
require the explicit `--yes="I am authorized to test this target"` attestation, check podman availability, and execute commands directly via argv without a shell.
In-guest integration inside an HSCL1 VM remains open (plan P4.3).

```console
$ hscl lab status                                   # podman installed? lab folder? toolsets
$ hscl lab setup                                    # creates ~/SecurityLabs (mode 0700)
$ hscl lab toolsets                                 # basic: nmap tcpdump tshark whois bind9-dnsutils netcat-openbsd
$ hscl lab spec --project web1 --image docker.io/kalilinux/kali-rolling@sha256:<64 hex> [--workspace ~/SecurityLabs/web1] [--network none|outbound]
$ hscl lab spec --project web1 --image ... --phase install     # toolset into a local image
$ hscl lab spec --project web1 --phase commit|destroy
```

## Rules enforced in code (`cli/hscl/src/lab.rs`, 11 unit tests incl. a seeded fuzz of 20000 workspace strings)

- The image must be pinned by **sha256 digest**; a tag alone is refused; `--pull=never` (pulling is a separate, explicit step). **Exception since 2026-11-10:** a
  **local** image (`localhost/<name>:<tag>`) is accepted, because `hscl lab commit` produces exactly that name and a local image has no digest until it is pushed.
  Without the exception the documented install → commit → run chain could not be finished; measured in the guest, where `hscl lab run --image
  localhost/hscl-lab-demo:latest` was the only way to reach the tools the install phase had added. Remote tags stay refused (`docker.io/...:latest`).
- **Run phase:** `--cap-drop=ALL` (no capability added), `--security-opt=no-new-privileges`, `--read-only` with small noexec tmpfs for `/tmp` and `/run`,
  `--network=none` unless `outbound` (rootless user-mode networking, never the host namespace), memory/CPU/PID limits.
- **One optional mount:** a folder strictly below `~/SecurityLabs`, mounted at `/work` with `nosuid,nodev`. Refused: `..`, `//`, `:` and `,` (volume-option smuggling),
  NUL/newlines, hidden or credential-bearing names (`.ssh`, `.gnupg`, `.config`, ...), the root itself, system directories, symlinks.
- **Install phase** (official Kali images ship without tools, without systemd): writable root, network on, only `CHOWN DAC_OVERRIDE FOWNER SETUID SETGID`
  (what apt needs to drop to `_apt`; namespaced by the rootless user namespace - a hypothesis to be confirmed in P4.3), no host folder, packages only from
  the toolset allow-list. The result is committed as `localhost/hscl-lab-<project>:latest`.
- `destroy` removes only that project's containers and local image; it never touches lab folders or other projects.

## Not done / open

- Podman and its dependencies are not in the image (measured 2026-11-06); plan P4.0. **Update 2026-11-10:**
  rootless Podman 5.7.0 works in the live guest once installed by hand (`ROOTLESS_OK`,
  `Host.Security.Rootless=true`, `/etc/subuid`+`/etc/subgid` present); shipping it stays opt-in.
- `containers/kali/image.pin` records a digest; pull/inspect now agree on the WSL builder (2026-11-08). The example above remains notation, not a literal image reference. **Upstream drift 2026-11-10:** re-resolving `kalilinux/kali-rolling:latest` through the registry API returned a newer index, `sha256:6ec743d9fc5cd397451eeddeff3869bcfab5de9bd5dec5b1f34cbfbd80313073` (amd64 child `sha256:5cc5e418c51098ae3c48f9a1d5b3bc74a508588900765a3964259da783652b03`). The pin deliberately stays at the **pull-verified** digest; `tests/unit/test_lab_pin.py` fails if the pinned digest has no matching pull evidence, so a bump cannot silently ship an untested image.
- The generated restricted run and basic-toolset install were exercised rootlessly on the builder, not inside an HSCL1 guest. See [builder probe](research/2026-11-08-security-lab-builder-probe.md). In-guest image integration and VM evidence remain open (HSCL1 guest/runtime still open).
- The Ubuntu Podman package installed without recommendations needs a user-mode network helper: default networking failed until `passt` supplied `pasta`. Include that dependency in the eventual lab package; never work around this by selecting host networking or rootful Podman.
- Disposable VM profiles, GUI tools, wireless/USB work: not implemented.
