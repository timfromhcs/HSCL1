# `hscl` command line reference

Only implemented commands are listed. `hscl --help` is authoritative. Every command accepts `--json`.

| Command | What it does |
|---|---|
| `hscl version` | product and version |
| `hscl about` | credit and the "not Tails / not official Kali" notice |
| `hscl status` | OS, architecture and security summary |
| `hscl doctor [--full]` | diagnostics; exit code 3 if a check fails |
| `hscl report [--output PATH]` | JSON support report; user/host names, MAC addresses and private IPv4 addresses are redacted; `--output` never overwrites an existing file |
| `hscl system info` | OS, kernel, CPU, memory (identifiers redacted) |
| `hscl security status` | AppArmor, firewall, Secure Boot, LUKS devices, forbidden APT sources |
| `hscl cqhecs status` | is the `hscl-cqhecs` package installed and its runtime ready (runs the launcher's `doctor --json`; read-only, starts nothing, no network) |
| `hscl ai detect` | CPU/RAM/GPU/Vulkan detection (no inference is run) |
| `hscl appearance theme list` | themes from the design tokens; `*` marks the current one |
| `hscl appearance theme show NAME` | tokens of one theme |
| `hscl appearance theme current` | selected theme |
| `hscl appearance theme set NAME [--dry-run]` | back up the previous selection, then apply the Plasma colour scheme and wallpaper |
| `hscl appearance theme restore [--dry-run]` | apply the default `hcs-midnight` |

## Exit codes

| Code | Meaning |
|---|---|
| 0 | success |
| 1 | error (message on stderr) |
| 3 | `hscl doctor` found at least one failing check |

## Safety properties

- Theme names must match `hcs-[a-z0-9-]+` (at most 24 characters) **and** exist in the token file; anything else
  (paths, shell metacharacters, upper case) is rejected before any command runs.
- `appearance theme set` runs only the fixed programs `plasma-apply-colorscheme` and `plasma-apply-wallpaperimage`
  with validated arguments; no shell is involved. If a command fails, the recorded selection is not changed.
- Environment overrides for development: `HSCL_TOKENS` (token file), `HSCL_CONFIG_DIR` (state directory).


## `hscl hw detect` (IMPLEMENTED, unit-tested with fixture trees; VM run pending)

Read-only hardware inventory from `/sys` and `/proc` (no root, no external tool): CPU model/threads/feature flags (`sse4_2 avx avx2 fma avx512f avx512_vnni amx_tile`),
memory, firmware (`uefi`/`bios`, Secure Boot `enabled`/`disabled`/`not_reported` from the EFI variable), PCI devices with class, driver in use and names from the system's
`pci.ids` (numeric IDs when it is missing), and GPUs with render nodes and, for amdgpu, dedicated VRAM and GTT (system RAM the GPU may map), reported separately and never combined.
It also collects the kernel's `modalias` for every device on the pci, usb, platform, acpi and i2c buses (one entry per device, sorted by bus and path in `--json`;
text mode prints the count per bus). Values with control characters or over 512 bytes are dropped and counted (`dropped_modaliases`) instead of being truncated, and
the USB `serial` file is never read - a serial number identifies a device, it does not describe a capability.
`--json` prints the same data. It installs and changes nothing. Driver suggestions and an install action are separate, later steps (PLANNED - no such subcommand
exists yet, so none is offered here).

## `hscl hw suggest` (IMPLEMENTED, unit-tested; VM run pending)

Reads the `Modaliases:` fields of the apt index under `/var/lib/apt/lists` and matches them against the devices'
modaliases (the same mechanism `ubuntu-drivers` uses: debhelper's `dh_modaliases` writes those fields, and each value is
a glob, often vendor-wrapped like `nv(pci:v000010DEd000010C3sv*sd*bc03sc*i*)`). Output: device path, modalias and the
claiming packages with a licence class (proprietary / firmware / unknown - from the index `Section:` and a short,
documented name list; "unknown" is printed rather than guessed).

It **installs nothing**: no apt, no dpkg, no systemctl. Without an apt index it says so ("nothing to suggest") instead of
inventing candidates. `--root DIR` points it at a fixture tree; `--json` prints the devices, the index package count, the
suggestions and the licence classes.

## `hscl lab` (IMPLEMENTED, unit-tested; no container started yet)

See `docs/SECURITY_LAB.md`: `status`, `setup`, `toolsets`, `spec` (prints the exact rootless `podman` command, executes nothing).

## `hscl language` (IMPLEMENTED, unit-tested)

Desktop language configuration and switching (AGENTS.md section 10.3).
HSCL1 supports three Tier-1 languages: English (`en`), Deutsch (`de`), and Français (`fr`).
Language changes apply without reinstalling the OS, without root privileges, and preserve all user data by updating `~/.config/plasma-localerc` and `~/.config/locale.conf`.
Changes take effect on the next user login or desktop session restart.

`hscl language status` inspects the active environment and configuration files.
`hscl language list` displays all supported languages and highlights the currently active selection.
`hscl language set <LANG>` validates the requested language code and safely updates desktop configuration.
`--dry-run` previews file changes without modifying disk state; `--json` outputs structured JSON.

## `hscl privacy` (IMPLEMENTED, unit-tested)

Privacy posture, ephemeral session isolation, fail-closed Tor browser workflows, and official Tails ISO verification (AGENTS.md section 6.5 & 8.2).

`hscl privacy status` checks whether the root filesystem is backed by a volatile RAM overlayfs (`/cow` or tmpfs), verifies that swap is restricted to compressed in-RAM `zram` with swap priority 100 without active persistent disk swap partitions, confirms dumpability protection (`fs.suid_dumpable = 0`), inspects whether internal host disks are unmounted, and checks Tor daemon/browser readiness.

`hscl privacy tor status` reports local Tor SOCKS proxy availability and Tor Browser launcher status.
`hscl privacy tor launch` enforces a strict fail-closed policy: if Tor Browser is not installed or available, it refuses to launch a normal browser or fall back to direct unencrypted egress. `--dry-run` previews the command.

`hscl privacy session explain` outputs a complete architectural breakdown of ephemeral overlayfs behavior, memory isolation, and honest boundaries distinguishing HSCL1 from authentic Tails.

`hscl privacy tails verify` streams and calculates the SHA256 checksum of an official Tails ISO image and checks it against upstream releases.
`hscl privacy tails launch` builds or executes an isolated QEMU/KVM virtual machine launch command with snapshot mode and no host drive mounts.

## `hscl security` (IMPLEMENTED, unit-tested)

Security posture, firewall profiles, AppArmor mandatory access control, disk encryption, and audit reports (AGENTS.md section 6.1, 6.2, 6.3 & 8.2).

`hscl security status` provides an overall posture summary covering AppArmor, UFW firewall, Secure Boot, open LUKS volumes, and forbidden APT repository hygiene.
`hscl security firewall status` inspects UFW service state, incoming/outgoing default policies, and active firewall profile.
`hscl security firewall profile list` lists defined profiles (`standard`, `public-wifi`, `lab`, `privacy`).
`hscl security firewall profile set <NAME>` validates profile names and plans/executes configuration (`--dry-run` previews without root).
`hscl security apparmor status` reports kernel module state and loaded profile counts (enforce vs complain mode).
`hscl security audit [--output PATH]` runs a comprehensive security baseline audit and optionally writes a JSON report (never overwriting existing files).
`hscl security encryption status` checks mapped `CRYPT-LUKS` volumes, crypttab entries, and root disk encryption.
`hscl security recovery check` inspects disaster recovery snapshot directories (`/var/backups/hscl`, Timeshift, snapper).

## `hscl logs` (IMPLEMENTED, unit-tested)

Diagnostic log inspection and bundle collection with automatic redaction (AGENTS.md section 8.2, 8.3 & rule 0.3.8).

`hscl logs show [SERVICE] [--lines N]` inspects recent log output for a service (`system`, `kernel`/`dmesg`, `calamares`/`installer`, `sddm`, `xorg`, or systemd units) with usernames, hostnames, MAC addresses, private IPv4 addresses, and credentials automatically redacted.
`hscl logs collect [--output PATH]` gathers multi-source diagnostic logs into a unified JSON bundle; `--output` never overwrites an existing file.

## `hscl recovery` (IMPLEMENTED, unit-tested)

System recovery posture, snapshot management, and non-destructive configuration reset (AGENTS.md section 8.2 & 8.4).

`hscl recovery status` inspects recovery readiness across active providers (`/var/backups/hscl`, Timeshift, Snapper, Btrfs).
`hscl recovery snapshots list` lists all detected snapshots sorted newest first.
`hscl recovery snapshots create <LABEL> [--dry-run]` creates a timestamped recovery point with configuration manifest (refuses to overwrite).
`hscl recovery config reset [COMPONENT] [--dry-run]` non-destructively resets configuration components (`shortcuts`, `theme`, `all`) to schema-validated defaults while creating timestamped `.bak` safety preserves.

## `hscl dev` (IMPLEMENTED, unit-tested)

Developer workstation environment, setup bundles, Git hygiene, containers, and virtualization (AGENTS.md section 7.1, 7.2 & 8.2).

`hscl dev status` inspects readiness across compilers, Git, Python, Rust, Node, containers, and virtualization.
`hscl dev setup [BUNDLE] [--dry-run]` prepares safe installation plans for curated opt-in bundles (`base`, `python`, `rust`, `containers`, `virt`, `all`).
`hscl dev git doctor` evaluates Git configuration hygiene, identity settings, default branch convention, and commit signing.
`hscl dev container status` verifies rootless Podman readiness, subuid/subgid mapping, and cgroups v2 resource delegation.
`hscl dev vm status` checks KVM hardware acceleration, device permissions, and libvirt hypervisor daemon status.

## `hscl system` (IMPLEMENTED, unit-tested)

System information, package updates, power actions, and services management (AGENTS.md section 8.2 & rule 0.3.7).

`hscl system info` reports redacted OS, kernel, CPU model, threads, and memory metrics.
`hscl system updates [--check|--install] [--dry-run]` provides read-only simulation check or safe upgrade plan.
`hscl system reboot [--dry-run]` requests system restart via systemd/logind APIs.
`hscl system shutdown [--dry-run]` requests clean system poweroff via systemd/logind APIs.
`hscl system lock` locks the active desktop session safely.
`hscl system services [--enabled]` lists system services and their enablement states.


## More commands (rows taken from `--help`; the drift test `cli_doc_lists_every_command` keeps this page complete)

| Command | What it does |
|---|---|
| `hscl overview` | Friendly overview of HSCL1 and where to start (also what `hscl1` with no arguments prints) |
| `hscl dev status` | Developer environment status across compilers, containers, and virtualization |
| `hscl dev setup` | Setup curated opt-in developer bundles with dry-run support |
| `hscl dev git doctor` | Inspect git configuration hygiene, identity, and signing setup |
| `hscl dev container status` | Detailed rootless container readiness, subuids, and cgroups v2 |
| `hscl dev vm status` | Check KVM hardware acceleration, permissions, and hypervisor daemon |
| `hscl recovery status` | Inspect system recovery posture and backup provider readiness |
| `hscl recovery snapshots list` | List all detected recovery snapshots |
| `hscl recovery snapshots create` | Create a timestamped recovery point with system configuration manifest |
| `hscl recovery config reset` | Reset desktop configuration component with safety backup creation |
| `hscl logs show` | Inspect recent log lines for a service with automatic redaction |
| `hscl logs collect` | Collect redacted diagnostic logs into an exportable bundle |
| `hscl security firewall status` | Inspect UFW firewall status, default policies, and active profile |
| `hscl security firewall profile list` | List defined firewall profiles with descriptions and policies |
| `hscl security firewall profile set` | Apply or preview a firewall profile (standard, public-wifi, lab, privacy) |
| `hscl security apparmor status` | Show AppArmor kernel module state and loaded profile counts |
| `hscl security audit` | Comprehensive security posture audit; writes report with --output |
| `hscl security encryption status` | Report open LUKS encrypted volumes and crypttab entries |
| `hscl security recovery check` | Check backup snapshots and disaster recovery readiness |
| `hscl privacy status` | Live privacy posture: ephemeral overlay, memory swap, dump safety, and Tor readiness |
| `hscl privacy tor status` | Check Tor daemon status and Tor Browser availability |
| `hscl privacy tor launch` | Launch Tor Browser with fail-closed protection (no direct-browser fallback) |
| `hscl privacy session explain` | Comprehensive explanation of ephemeral overlayfs, zram memory swap, suid_dumpable, and boundaries vs Tails |
| `hscl privacy tails verify` | Verify an official Tails ISO image file (SHA256 checksum and optional expected hash) |
| `hscl privacy tails launch` | Generate or run an isolated QEMU/KVM launcher for an official Tails ISO (no host storage attached) |
| `hscl language status` | Show current language configuration and active environment |
| `hscl language list` | List supported languages (en, de, fr) |
| `hscl language set` | Set the user desktop language (en, de, fr); `--dry-run` previews without writing |
| `hscl system info` | OS, kernel, CPU, memory (identifiers redacted) |
| `hscl system updates` | Pending APT updates (simulation check or upgrade plan) |
| `hscl system reboot` | Request system reboot (via logind/systemctl) |
| `hscl system shutdown` | Request system shutdown/poweroff (via logind/systemctl) |
| `hscl system lock` | Lock the active desktop session |
| `hscl system services` | List system services and their enablement status |
| `hscl appearance wallpaper list` | Available wallpaper shader presets |
| `hscl appearance wallpaper set` | Apply a wallpaper preset by name |
| `hscl appearance mode` | Show or set desktop color mode. `dark`/`light` also apply the matching HCS colour scheme; `auto` records the preference and leaves the scheme alone |
| `hscl appearance dock position` | Move the HCS dock to another screen edge (bottom, left, right) by scripting the running Plasma panel; the top bar is never moved |
| `hscl miner status` | Local miner configuration and esptool availability. Contacts no device |
| `hscl miner probe` | Read `GET /api/system/info` from a Bitaxe on the local network (read-only) |
| `hscl miner plan` | Size, SHA-256, endpoint and rollback hint for an OTA firmware, without sending it |
| `hscl miner ota` | Send an OTA firmware update; needs `--yes="I am authorized to flash this device"` (private networks only) |
| `hscl miner flash` | USB flashing through `esptool`; same authorization phrase, `--dry-run` prints the argv |
| `hscl miner discover` | Scan a private /24 for AxeOS/Bitaxe miners (read-only, identified by MAC) |
| `hscl miner serve` | Read-only local API over the configured miners: `/v1/health`, `/v1/miners`, `/v1/miner?host=…` |
| `hscl miner series` | Sample one miner N times and write the JSON series (native, replaces the ad-hoc script) |
| `hscl ai model list` | All catalog models with fit information for this machine |
| `hscl ai model recommend` | Models that fit this machine, best first |
| `hscl ai model info` | Details, licence and warning of one model |
| `hscl ai model download` | Download a model (sha256 verified). Abliterated models need --accept-warning |
| `hscl ai model verify` | Re-check size and sha256 of a downloaded model |
| `hscl ai model remove` | Delete a downloaded model file (nothing else) |
| `hscl ai model path` | Show the model storage directory |
| `hscl ai model add` | Add model file to storage or download catalog model |
| `hscl ai setup` | Configure local AI runtime and backend preferences (`--backend`, `--dry-run`) |
| `hscl ai backend list` | Available AI inference backends and hardware compatibility |
| `hscl ai backend set` | Set preferred inference backend (auto, vulkan, cpu, cuda, rocm) |
| `hscl ai storage show` | Show model storage directory and filesystem free space |
| `hscl ai storage set` | Set custom model storage directory path |
| `hscl ai server start` | Start loopback inference server on 127.0.0.1 (`--port`, `--dry-run`) |
| `hscl ai server stop` | Stop active local inference server (`--dry-run`) |
| `hscl ai server status` | Check status, PID, and endpoints of local inference server |
| `hscl ai fit` | Estimate RAM/VRAM for a GGUF file at a context size (reads only the metadata; an estimate, not a measurement) |
| `hscl ai profile` | Hardware-adapted run plan for a model (backend, offload, context, KV cache, threads) |
| `hscl memory status` | RAM, swap, zram devices and the AI budget |
| `hscl memory budget` | Show or set the share of RAM local AI may use (10-90, default 60) |
| `hscl low-vram` | Low-VRAM mode for weak GPUs: caps the desktop effects and makes `ai profile` offload less |
| `hscl wallpaper list` | All presets (system and yours) |
| `hscl wallpaper show` | One preset as JSON |
| `hscl wallpaper create` | Save a preset of your own |
| `hscl wallpaper apply` | Make a preset the wallpaper (low-VRAM mode caps density and speed) |
| `hscl wallpaper delete` | Delete one of your presets |
| `hscl wallpaper export` | Copy a preset to a new file |
| `hscl code list` | Known coding tools, licences and whether they are installed |
| `hscl code install` | Install a tool into your home directory (never system-wide) |
| `hscl code setup` | Write the OpenCode config (local provider + hscl MCP) and the HCS agent notes |
| `hscl code launch` | Start a tool against the local model server (default: opencode). Extra arguments go to the tool after `--` |
| `hscl mcp` | Model Context Protocol server on stdio for local agents (read-only unless --allow-write) |
| `hscl graphics detect` | What was detected and which profile it maps to |
| `hscl graphics apply` | Apply the profile for this machine (skipped when unchanged or locked) |
| `hscl graphics lock` | Never auto-tune again (keeps your manual settings) |
| `hscl graphics unlock` | Allow auto-tuning again |
| `hscl autotune` | Detect this machine and apply every automatic tuning (graphics now; AI profile is shown) |
| `hscl lab status` | Is podman present, is the lab folder there, and which toolsets exist |
| `hscl lab setup` | Create the lab root folder (~/SecurityLabs, mode 0700) |
| `hscl lab toolsets` | List the toolsets and the packages each installs (inside the container only) |
| `hscl lab toolsets list` | List available toolsets and their included packages |
| `hscl lab toolset list` | List available curated security toolsets |
| `hscl lab toolset install` | Install a curated toolset into a lab project container |
| `hscl lab toolset remove` | Remove an installed toolset from a project |
| `hscl lab container list` | List active and stopped lab containers |
| `hscl lab container inspect` | Inspect details and security parameters of a lab container |
| `hscl lab container shell` | Open an interactive shell inside a lab container |
| `hscl lab container stop` | Stop a running lab container cleanly |
| `hscl lab container destroy` | Destroy a lab container and remove its temporary storage |
| `hscl lab vm list` | List disposable lab VM profiles and configurations |
| `hscl lab vm create` | Create a disposable security testing VM profile |
| `hscl lab vm launch` | Launch a disposable lab VM with explicit network boundary |
| `hscl lab vm destroy` | Destroy a disposable lab VM and discard its overlay |
| `hscl lab spec` | Print the exact podman command for a project (nothing is executed) |
| `hscl lab run` | Execute the run phase through the CLI (no shell; requires --yes attestation) |
| `hscl lab install` | Execute the install phase: toolset packages into a local image (attestation required) |
| `hscl lab commit` | Commit the finished install container into the local image (attestation required) |
| `hscl lab destroy` | Destroy this project's containers and local image (attestation required) |
| `hscl completions SHELL` | Print a shell completion script (bash, zsh, fish, elvish, powershell); `hscl1 completions SHELL` completes the `hscl1` name |
| `hscl man --out DIR` | Write roff man pages generated from the same clap tree: `hscl.1`, `hscl1.1` and one `hscl-<command>.1` per top-level command. The package build installs them under `/usr/share/man/man1`; the directory is created, a file at that path is refused |
| `hscl ai serve [MODEL]` | Print the exact `llama-server` command for a local model (host fixed to 127.0.0.1, port 1024 or higher, API key only as a key file, thinking off, K q8_0 / V q4_0, small prompt cache, idle sleep; `--router-dir DIR --models-max 1\|2` for router mode; `--metrics` optional). Nothing is started |
| `hscl ai serve --load-mode MODE` | Pass `--load-mode` (`auto`, `none`, `mmap`, `mlock`, `mmap+mlock`, `dio`). The old `--mmap`/`--no-mmap`/`--mlock` flags were removed upstream; `auto` disables mmap on Vulkan iGPUs, so a shared-memory APU may want `mmap` explicitly |
| `hscl ai serve --kv-in-ram` | Add `-nkvo`: keep the KV cache in system RAM while the weights stay on the GPU. Frees GPU-accessible memory on an APU, costs prefill speed |
| `hscl ai serve --draft-model PATH [--draft-max N]` | Add speculative decoding (`-md`, `--spec-draft-n-max`, default 3): a small draft model that must share the tokenizer, inside the model storage. The gain on this iGPU is unmeasured, so the command only prints it |
