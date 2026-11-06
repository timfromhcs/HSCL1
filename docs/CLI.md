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
`--json` prints the same data. It installs and changes nothing. Driver suggestions (`hscl hw suggest`) and the install action are separate, later steps.

## `hscl lab` (IMPLEMENTED, unit-tested; no container started yet)

See `docs/SECURITY_LAB.md`: `status`, `setup`, `toolsets`, `spec` (prints the exact rootless `podman` command, executes nothing).


## More commands (rows taken from `--help`; the drift test `cli_doc_lists_every_command` keeps this page complete)

| Command | What it does |
|---|---|
| `hscl overview` | Friendly overview of HSCL1 and where to start (also what `hscl1` with no arguments prints) |
| `hscl system updates` | Pending APT updates (read-only simulation; installs nothing) |
| `hscl ai model list` | All catalog models with fit information for this machine |
| `hscl ai model recommend` | Models that fit this machine, best first |
| `hscl ai model info` | Details, licence and warning of one model |
| `hscl ai model download` | Download a model (sha256 verified). Abliterated models need --accept-warning |
| `hscl ai model verify` | Re-check size and sha256 of a downloaded model |
| `hscl ai model remove` | Delete a downloaded model file (nothing else) |
| `hscl ai model path` | Show the model storage directory |
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
| `hscl lab spec` | Print the exact podman command for a project (nothing is executed) |
| `hscl completions SHELL` | Print a shell completion script (bash, zsh, fish, elvish, powershell); `hscl1 completions SHELL` completes the `hscl1` name |
| `hscl ai serve [MODEL]` | Print the exact `llama-server` command for a local model (host fixed to 127.0.0.1, port 1024 or higher, API key only as a key file, thinking off, K q8_0 / V q4_0, small prompt cache, idle sleep; `--router-dir DIR --models-max 1\|2` for router mode; `--metrics` optional). Nothing is started |
