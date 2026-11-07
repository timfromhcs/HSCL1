# Genesis research ledger (sources checked, append only)

| Date | Question | Source | Result | Status |
|---|---|---|---|---|
| 2026-11-07 | Default Python on Ubuntu 26.04 | packages.ubuntu.com `python3-defaults` (resolute) | 3.14.3-0ubuntu2 | ANSWERED |
| 2026-11-07 | Wheels for numpy/qiskit on CPython 3.14 manylinux | `pip download --only-binary=:all:` | all present, 62 MB | ANSWERED (measured) |
| 2026-11-07 | CQ-HECS 5.0.0 release assets and hashes | `gh release view v5.0.0`, `sha256sums.txt` | wheel 373,941 B, hash matches our pin | ANSWERED |
| 2026-11-07 | Is python3-venv in the base image | `dpkg-query --admindir` on the pristine root | no | ANSWERED (measured) |
| 2026-11-07 | CQ-HECS CLI health probe | real run of the 5.0.0 wheel | `version` is a subcommand, `--version` is not an option | ANSWERED (measured) |
| 2026-11-07 | Calamares recovery-key module | web search (one round) | none found; `luksbootkeyfile` adds a keyfile slot | PARTIAL (no confirming source for a custom step) |
