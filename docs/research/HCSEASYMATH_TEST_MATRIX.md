# HCSEASYMATH test matrix (planned gates)

Gate IDs extend the existing `L*`/`C*` scheme without replacing it. A gate exists when its command exists and a test of the gate itself exists.

| ID | Gate | Command (WSL Ubuntu 26.04, Python 3.14) | Pass | Milestone |
|---|---|---|---|---|
| E1 | Unit + property | `python -m pytest apps/hcseasymath/tests -q` | 0 failed, skips with reason | M1 |
| E2 | Hostile input corpus | `pytest apps/hcseasymath/tests/security -q` | every hostile input refused, none executed, process alive | M1 |
| E3 | Lock reproducibility | `pip install --require-hashes --only-binary=:all: -r lock` in a fresh venv, then `pip check` | exit 0 | M1 |
| E4 | API end to end | start app, call `/api/v1/health` and the derivative endpoint, stop | derivative equals `3*x**2 - 6*x + 2`, no listener after stop | M1 |
| E5 | Host/Origin/token | requests with foreign Host or Origin or no token | 4xx | M1 |
| E6 | Exactness contract | differentiate/integrate/solve corpus vs independent references (numeric sampling, SciPy) | within declared tolerance; `unresolved` is never reported `ok` | M2 |
| E7 | ODE convergence | `y' = -k y` vs exact solution, tolerance sweep | error decreases with tolerance; both abs and rel error recorded | M3 |
| E8 | CLI/MCP | `hscl math ...` tests, MCP allow-list tests | typed, no shell-shaped argument accepted | M6 |
| E9 | Package | build `hscl-hcseasymath` with `scripts/build-deb.sh`, install/remove in a disposable rootfs | no autostart, data retained on removal | M9 |
| E10 | Image + VM | `verify-image.sh` pair checks, boot, in-guest smoke | all pass on the exact dev ISO | M10 |
