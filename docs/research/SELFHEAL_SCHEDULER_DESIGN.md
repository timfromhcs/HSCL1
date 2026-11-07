# Durable self-heal scheduler: design note (ledger row 8)

Status: **PLANNED** (design only, no code). Source: Unified Master section 21 and the lock rules in 20. Today's 2-minute ping is a Claude Code session job; it dies with the session and is not this scheduler.

## Contract
- One **tick** = one short, bounded process. It decides, starts at most one unit of work, records the outcome and exits. No daemon.
- Unprivileged. Never root, never a system service. State lives in a per-user directory (`%LOCALAPPDATA%\hscl-selfheal` on Windows, `$XDG_STATE_HOME/hscl-selfheal` elsewhere), never in the repository.
- **Global lock** (exclusive file create, with owner PID, start time and a stale-after limit): a second tick that finds a live lock exits at once with `skipped: locked`.
- **Heavy-job lock** (separate file): VM, local model and long solver runs take it; a tick that needs it while held records `deferred`. This enforces "one heavy thing at a time".
- **Wall timeout** below the tick interval (interval 120 s, tick limit 90 s); the worker is killed as a process tree on expiry and the tick records `timeout`.
- **Dry-run first**: `--dry-run` prints the chosen row and command and writes nothing but the log line. Real mode is opt-in per row.
- State file (JSON, written atomically via temp file + rename): last tick time, last row, outcome, consecutive failures per row. Three failures on one row set it `BLOCKED` and the tick stops picking it (three-attempt rule).
- Log: append-only JSON lines with timestamp, row, command, exit code, duration. No environment dump, no secrets, command lines pass the existing secret scan.

## What a tick may run
Only rows of the live ledger marked safe-for-tick (read-only checks, `forge check`, report generation). Anything that edits the repository, pushes, opens a PR or merges is **not** tick work: it stays in an interactive agent session with its lock line.

## Tests planned (before any real mode)
1. Two ticks started together: exactly one runs. 2. Stale lock older than the limit is taken over, a fresh one is not. 3. A worker that sleeps past the timeout is killed and recorded. 4. Held heavy lock gives `deferred`. 5. Third consecutive failure marks the row `BLOCKED`. 6. Dry-run leaves the state file unchanged. 7. Corrupt state file: tick refuses and reports, does not overwrite.

## Open
- Windows Task Scheduler vs `cron` entry: a user-level entry only; choice is the owner's. - Where tick output is surfaced (log file only, or a `hscl` status line). Both need owner review before enabling anything.
