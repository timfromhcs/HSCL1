# Security Lab (status: IMPLEMENTED + unit-tested; **not yet run in a VM**, podman is not in the image yet)

Authorized testing only. Kali tools run **only inside rootless containers** (later: disposable VMs); the host never gets Kali or Debian repositories.
HSCL1 is not an official Kali product.

## What exists

`hscl lab` builds a rootless `podman` command from typed options and prints it. It **never runs a shell** and has **no field** for `--privileged`,
host network/PID/IPC, devices, extra capabilities or arbitrary mounts. Execution through the CLI is deliberately not wired up yet: it comes after the
VM run (plan P4.3) proves the commands work.

```console
$ hscl lab status                                   # podman installed? lab folder? toolsets
$ hscl lab setup                                    # creates ~/SecurityLabs (mode 0700)
$ hscl lab toolsets                                 # basic: nmap tcpdump tshark whois bind9-dnsutils netcat-openbsd
$ hscl lab spec --project web1 --image docker.io/kalilinux/kali-rolling@sha256:<64 hex> [--workspace ~/SecurityLabs/web1] [--network none|outbound]
$ hscl lab spec --project web1 --image ... --phase install     # toolset into a local image
$ hscl lab spec --project web1 --phase commit|destroy
```

## Rules enforced in code (`cli/hscl/src/lab.rs`, 11 unit tests incl. a seeded fuzz of 20000 workspace strings)

- The image must be pinned by **sha256 digest**; a tag alone is refused; `--pull=never` (pulling is a separate, explicit step).
- **Run phase:** `--cap-drop=ALL` (no capability added), `--security-opt=no-new-privileges`, `--read-only` with small noexec tmpfs for `/tmp` and `/run`,
  `--network=none` unless `outbound` (rootless user-mode networking, never the host namespace), memory/CPU/PID limits.
- **One optional mount:** a folder strictly below `~/SecurityLabs`, mounted at `/work` with `nosuid,nodev`. Refused: `..`, `//`, `:` and `,` (volume-option smuggling),
  NUL/newlines, hidden or credential-bearing names (`.ssh`, `.gnupg`, `.config`, ...), the root itself, system directories, symlinks.
- **Install phase** (official Kali images ship without tools, without systemd): writable root, network on, only `CHOWN DAC_OVERRIDE FOWNER SETUID SETGID`
  (what apt needs to drop to `_apt`; namespaced by the rootless user namespace - a hypothesis to be confirmed in P4.3), no host folder, packages only from
  the toolset allow-list. The result is committed as `localhost/hscl-lab-<project>:latest`.
- `destroy` removes only that project's containers and local image; it never touches lab folders or other projects.

## Not done / open

- Podman and its dependencies are not in the image (measured 2026-11-06); plan P4.0.
- The pinned Kali digest has not been recorded yet (P4.1); the examples above use a placeholder.
- No container has been started by HSCL1 yet; whether apt works with the restricted capability set is open (plan question 3).
- Disposable VM profiles, GUI tools, wireless/USB work: not implemented.
