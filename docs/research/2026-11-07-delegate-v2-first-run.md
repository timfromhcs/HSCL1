# Delegate v2: first real runs (2026-11-07)

Two things were run for real on this PC (Ryzen 7 7735HS, 20 GB shared RAM, Bonsai-9B MTP server on :8080 started by `autostart.ps1`).

## 1. Smart autostart (`~/.config/opencode/autostart.ps1`, not in this repo)
Started through the stack tool with the VM stopped and no model loaded. Log: `profile=full free=10,8GB battery=False ctx=32768 t=8/16`, server online after 13 s, process priority `AboveNormal` (was `High`), resident 3.5 GB once working. So the profile choice by free RAM works on the machine it was written for; the lower profiles (`mid`, `lean`, `defer`) were **not** exercised.

## 2. `local_code` through the v2 server code (stdio driver, one task, VM stopped)
- Task: implement `scripts/ts_coverage.py` against 8 tests (one file, several behaviours), model `jev-1.5b`, up to 4 rounds.
- Outcome: `ok: false`, `max_rounds`, **397 s**, 4 of 8 tests still failing, empty diff returned. The v2 gate and the single-flight lock did not get in the way (`isError: false`, lock file removed).
- Host while it ran: CPU 66-100 %, 5.6 GB free, llama-server 3.7 GB; nothing else heavy.
- Reading: the small server solves tiny tasks (earlier benchmark 10/10 at 10.6 s per task) but not a task with several behaviours in four rounds. The delegate's contract (`ok: false` means escalate) is the right behaviour; the task was then written by the cloud model and verified by the same tests. In `rsi-capture` this is one session with the local failure as a tool event and a verified pair marked as cloud-teacher output (28 pairs now, not a local success).

## Not measured
Whether a larger `max_rounds`, a smaller task split, or another model would have solved it; time per round; the `mid`/`lean`/`defer` autostart profiles; the host gate refusing in practice (covered by unit tests only); anything about diffusion models or vision towers on this machine.
