# Durable self-heal scheduler: design note (ledger rows 8, 15, 22)

Status: **IMPLEMENTED + TESTED (unit)**. `scripts/selfheal/tick.py` exists, 22 unit tests green on Windows and WSL,
and the rotation added in W2-4 is measured (6 of 6 mutations killed). Source: Unified Master section 21 and the lock
rules in 20. Today's 2-minute ping in an agent session is a different mechanism; it dies with the session and is not
this scheduler. Nothing is registered with Windows Task Scheduler or cron - that stays an owner decision (below).

## Contract
- One **tick** = one short, bounded process. It decides, starts at most one unit of work, records the outcome and exits. No daemon.
- Unprivileged. Never root, never a system service. State lives in a per-user directory (`%LOCALAPPDATA%\hscl-selfheal` on Windows, `$XDG_STATE_HOME/hscl-selfheal` elsewhere), never in the repository.
- **Global lock** (exclusive file create, with owner PID, start time and a stale-after limit): a second tick that finds a live lock exits at once with `skipped: locked`.
- **Heavy-job lock** (separate file): VM, local model and long solver runs take it; a tick that needs it while held records `deferred`. This enforces "one heavy thing at a time".
- **Wall timeout** below the tick interval (interval 120 s, tick limit 90 s); the worker is killed as a process tree on expiry and the tick records `timeout`.
- **Dry-run first**: `--dry-run` prints the chosen row and command and writes nothing but the log line. Real mode is opt-in per row.
- State file (JSON, written atomically via temp file + rename): last tick time, last row, outcome, consecutive failures per row. Three failures on one row set it `BLOCKED` and the tick stops picking it (three-attempt rule).
- Log: append-only JSON lines with timestamp, row, command, exit code, duration. No environment dump, no secrets, command lines pass the existing secret scan.

## Rotation (W2-4, added 2026-11-08)

Before W2-4 the chooser was `next(r for r in rows if not blocked)`: with two rows only the first could ever run, so
the rows file was effectively a list of one. The rule is now **round-robin over the live rows in file order**:

1. The row **after** `state["last_row"]` comes first; the rest follow in file order and wrap around.
2. A row marked `blocked` is left out of the rotation entirely (it stays blocked; nothing unblocks it automatically).
3. A **heavy** row whose heavy slot is busy is **skipped, not chosen**: the rotation continues to the next candidate,
   so a busy heavy slot cannot idle a tick while a light row is available. If every live row is heavy and the slot is
   busy, the tick records `deferred` with the first heavy row and does not advance - the next tick retries it.
4. `last_row` unknown (fresh state, or a rows file that changed) starts the rotation at the top of the file, so a
   first tick behaves exactly like the old first-fit choice.
5. **Dry-run does not advance the pointer.** Two dry runs in a row report the same row, which is the honest answer to
   "what would the next real tick run". Dry-run reads the heavy lock file to *predict* a deferral instead of taking
   the lock, so it stays side-effect free.

Consequences that are intended and must not be "fixed" later:

- **The three-attempt rule now spans three rotations.** With `[bad, good]`, `bad` fails on ticks 1, 3 and 5 and is
  blocked at the third attempt; `good` runs in between. This is better for transient failures (a flaky row gets a
  later retry instead of three back-to-back strikes) and it is what the rotation test asserts.
- **`idle` and `deferred` mean different things.** `idle` = no live row at all (everything blocked, or an empty rows
  file). `deferred` = live rows exist but every one of them needs a heavy slot that is taken. The exit code is 0 for
  both, and the log line records which happened.

## What a tick may run
Only rows of the live ledger marked safe-for-tick (read-only checks, `forge check`, report generation). Anything that edits the repository, pushes, opens a PR or merges is **not** tick work: it stays in an interactive agent session with its lock line.

## Tests (all green)
1. Two ticks started together: exactly one runs. 2. Stale lock older than the limit is taken over, a fresh one is not. 3. A worker that sleeps past the timeout is killed and recorded. 4. Held heavy lock gives `deferred`. 5. Third consecutive failure marks the row `BLOCKED`. 6. Dry-run leaves the state file unchanged. 7. Corrupt state file: tick refuses and reports, does not overwrite.
Plus the W2-4 rotation group: every row gets a turn and the sequence wraps; an unknown `last_row` starts at the top; a
blocked row is skipped; a busy heavy slot does not idle a tick when a light row is due; a heavy row does run and
releases its lock; dry-run reports the next row twice without advancing; dry-run predicts a deferral by reading the
heavy lock. `python -m pytest tests/unit/test_selfheal_tick.py` -> **22 passed** on Windows and in WSL.

## Not done / owner decisions
- **Windows Task Scheduler vs `cron` entry**: a user-level entry only; the choice is the owner's. Nothing is registered.
- Where tick output is surfaced (log file only, or a `hscl` status line). Both need owner review before enabling anything.
- There is no fairness guarantee across *runs of the agent session*; the rotation only orders rows within the scheduler.
