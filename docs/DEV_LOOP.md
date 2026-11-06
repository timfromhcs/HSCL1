# Development loop (builder, VM tests, harness)

Short reference for the autonomous loop. The plan is `docs/superpowers/plans/2026-11-06-autonomous-to-stable-hardened.md`.

## Resource policy (the host reaped two builds when this was ignored)

- Host 19.8 GB RAM; `~/.wslconfig`: `memory=8GB`, `swap=8GB`, `processors=6`.
- Never run an image build and a VM at the same time. Order: build in WSL -> copy the ISO out -> `wsl --shutdown` -> VM test.
- Build from a WSL-local clone, not from `/mnt/e` (9p overhead, NTFS reports 0777):
  `git clone --branch codex/hscl1-v1 /mnt/e/hcslinux222 ~/hscl1-src` once, then `git pull /mnt/e/hcslinux222 codex/hscl1-v1`.
- Before a heavy step: >= 9 GB free host memory and no leftover `qemu`/`vmmem`. After it: `wsl --shutdown`.
- A job stopped by the host is recorded, never restarted blindly.

## Commands

```console
$ wsl -d Ubuntu -- bash -lc 'cd ~/hscl1-src && scripts/remaster-iso.sh --out ~/hscl1-build/out/NAME.iso --fast --force'
$ python scripts/workshop/e2e_cli.py artifacts/iso/NAME.iso artifacts/e2e-NAME      # 23 in-guest checks over the Workshop API
$ python scripts/workshop/e2e_probe.py ISO OUTDIR COMMANDS.json                     # read-only diagnostics in the guest
$ python -m pytest tests -q                                                         # on Linux also runs the tests Windows skips
```

## Harness guarantees (`scripts/workshop/vm.py`)

- One persistent TCP connection to the guest port per VM; each request is sent once; stale replies are ignored.
- Before the guest has ever answered, a short retry is allowed (daemon still starting); afterwards the connection is never closed or re-sent
  (that pattern wedges a throttled virtio-serial port, QEMU issue 4672).
- On the first failing check `e2e_cli.py` stores a screenshot and a `status` re-poll in the report (`first_error`).

## Guest daemon guarantees (`hscl_workshopd.py`)

- Non-blocking port I/O; a reply the host does not drain within 20 s makes the daemon close and reopen the port (counted in `status.port`).
- Replies larger than 4 MiB are replaced by an error.

## Round log (propose - measure - reflect - revise)
Every fix attempt on a gate is one round: `python scripts/round_log.py TASK N --score tests_passed=132 --score clippy_warnings=0 --action "..." --reflection "..."` appends to `artifacts/auto-loop/rounds.jsonl` (secrets and personal absolute paths are refused, text is capped at 2000 characters, round numbers must increase per task). `python scripts/round_report.py --key tests_passed` prints best round, delta and `stalled`; exit code 3 means three rounds without a new best value: write a BLOCKER in `docs/BUILD_LOG.md` instead of a fourth retry. Pattern credit: AREX-2 (BAAI) test-time reflection loop; only the loop shape is used, no model.

## Linux parity in `forge check` (added 2026-11-06)
`python scripts/forge.py check` now also runs the test files that changed (against the upstream branch, plus untracked ones) a second time under Linux in WSL (`pytest (WSL, changed tests)`). CI is Linux; four CI-only failures in one day (exec bit three times, one Windows-only path normalization in a test) were invisible to the Windows-only run. The step is reported as SKIPPED when WSL is missing or no test file changed, and `check --strict` fails on a skip.
