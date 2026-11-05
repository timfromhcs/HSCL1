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
