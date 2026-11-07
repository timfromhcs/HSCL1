#!/usr/bin/env bash
# Stress and fault tools for a DISPOSABLE HSCL1 test VM only (plan G1).
#
# Why the interlock: stress-ng, fio and memtester deliberately push CPU, memory and I/O to their
# limits. Running them on a working machine risks data (fio writes 1 GiB), thermal faults and a
# frozen desktop, and a crash there would look like a product defect. Both conditions below must
# hold: HSCL_IN_DISPOSABLE_VM=1 in the environment AND an existing marker file (created by the VM
# harness when it boots a throwaway guest). The marker path is overridable only so tests can point
# at a fixture; the automation sets it from the harness, never from user input.
#
# Evidence: artifacts/stress/<stamp>/summary.json plus one log per tool. A failing or missing tool
# still produces the summary and makes the script exit non-zero - the run is evidence, not a demo.
#
# Usage: scripts/stress_vm.sh [--out DIR] [--help]
# Needs: python3 (JSON), coreutils; optional `timeout` for a hard per-tool limit.
# Env:   HSCL_IN_DISPOSABLE_VM=1 (mandatory), HSCL_VM_MARKER (default /etc/hscl-vm-marker),
#        HSCL_STRESS_SECONDS (default 120), HSCL_STRESS_FIO_SECONDS (default 60),
#        HSCL_STRESS_TOOL_TIMEOUT (default 900)
set -Eeuo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
out=""
marker="${HSCL_VM_MARKER:-/etc/hscl-vm-marker}"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
stress_seconds="${HSCL_STRESS_SECONDS:-120}"
fio_seconds="${HSCL_STRESS_FIO_SECONDS:-60}"
tool_timeout="${HSCL_STRESS_TOOL_TIMEOUT:-900}"

usage() {
  cat <<'EOF'
scripts/stress_vm.sh - stress-ng + fio + memtester inside a disposable VM, evidence as JSON.

Refuses to run unless HSCL_IN_DISPOSABLE_VM=1 and the marker file exists (/etc/hscl-vm-marker
unless HSCL_VM_MARKER points somewhere else).

  --out DIR   write logs and summary.json there (default artifacts/stress/<UTC stamp>)
  --help      this text

Exit: 0 all tools ok, 1 at least one tool failed or is missing, 2 refused (not a disposable VM).
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --out) [ $# -ge 2 ] || { echo "--out needs a directory" >&2; exit 2; }; out="$2"; shift 2 ;;
    --help|-h) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [ "${HSCL_IN_DISPOSABLE_VM:-}" != "1" ]; then
  echo "refusing: HSCL_IN_DISPOSABLE_VM=1 is not set." >&2
  echo "This script stresses CPU, RAM and disk and must only run in a throwaway VM." >&2
  echo "See docs/TESTING.md (stress gate) for how the VM harness sets it." >&2
  exit 2
fi
if [ ! -f "$marker" ] || [ ! -r "$marker" ]; then
  echo "refusing: the disposable-VM marker file '$marker' is missing or unreadable." >&2
  echo "The VM harness writes it on boot; a normal host never has it." >&2
  exit 2
fi
# python3 is the interpreter on the image; Git Bash on a Windows dev host may only provide `python`,
# so accept whichever one actually runs (the Microsoft Store `python3` alias exits 49 and is skipped).
py=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import json' >/dev/null 2>&1; then
    py="$candidate"
    break
  fi
done
[ -n "$py" ] || { echo "a working python3 (or python) is required to write summary.json" >&2; exit 2; }

[ -n "$out" ] || out="$root/artifacts/stress/$stamp"
mkdir -p "$out"

# 1 GiB for fio plus logs; refuse rather than fill the guest's disk.
free_kb="$(df -Pk "$out" | awk 'NR == 2 {print $4}')"
if [ -n "$free_kb" ] && [ "$free_kb" -lt 3145728 ]; then
  echo "refusing: less than 3 GiB free on the target filesystem ($free_kb KiB)." >&2
  exit 2
fi

records="$out/.records.tsv"
: >"$records"
overall="ok"

# run_tool NAME TIMEOUT_SECONDS -- argv...
run_tool() {
  local name="$1" limit="$2"; shift 2
  [ "${1:-}" = "--" ] && shift
  local log="$out/$name.log" start end status exit_code duration
  start="$(date -u +%s)"
  printf '### %s %s\n' "$name" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >"$log"
  if ! command -v "$1" >/dev/null 2>&1; then
    printf 'missing: %s is not installed\n' "$1" >>"$log"
    records_line "$name" "missing" "" "$start" "$log" "not installed"
    overall="failed"
    return 0
  fi
  exit_code=0
  if command -v timeout >/dev/null 2>&1; then
    timeout --kill-after=30 "$limit" "$@" >>"$log" 2>&1 || exit_code=$?
  else
    "$@" >>"$log" 2>&1 || exit_code=$?
  fi
  end="$(date -u +%s)"
  duration="$((end - start))"
  status="ok"
  [ "$exit_code" -eq 0 ] || status="failed"
  [ "$exit_code" -eq 0 ] || overall="failed"
  records_line "$name" "$status" "$exit_code" "$start" "$log" "$duration" "$@"
}

records_line() {
  local name="$1" status="$2" exit_code="$3" start="$4" log="$5" duration="$6"; shift 6
  # argv is space-joined: every argument this script passes is a flag or a path without spaces.
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$name" "$status" "$exit_code" "$start" "$duration" "$log" "$*" >>"$records"
}

virt="unknown"
for f in /sys/class/dmi/id/product_name /sys/class/dmi/id/sys_vendor; do
  if [ -r "$f" ]; then virt="$(tr -d '\n' <"$f")"; break; fi
done

run_tool stress-ng "$tool_timeout" -- \
  stress-ng --klog-check --metrics-brief --timeout "$stress_seconds"s --cpu 4 --vm 2 --vm-bytes 256M
run_tool fio "$tool_timeout" -- \
  fio --name=hscl-randrw --filename="$out/fio-target.img" --size=1G --rw=randrw \
    --rwmixread=70 --bs=4k --iodepth=16 --ioengine=psync --direct=1 --time_based \
    --runtime="$fio_seconds" --group_reporting
run_tool memtester "$tool_timeout" -- memtester 256M 1

HSCL_STRESS_JSON="$out/summary.json" \
HSCL_STRESS_RECORDS="$records" \
HSCL_STRESS_STAMP="$stamp" \
HSCL_STRESS_MARKER="$marker" \
HSCL_STRESS_VIRT="$virt" \
HSCL_STRESS_OVERALL="$overall" \
HSCL_STRESS_SECONDS="$stress_seconds" \
HSCL_STRESS_FIO_SECONDS="$fio_seconds" \
"$py" - <<'PY'
import json, os, platform, shutil

def rd(path, fallback=""):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read().strip()
    except OSError:
        return fallback

tests = []
with open(os.environ["HSCL_STRESS_RECORDS"], encoding="utf-8") as fh:
    for line in fh:
        line = line.rstrip("\n")
        if not line:
            continue
        name, status, code, start, duration, log, *rest = line.split("\t")
        tests.append({
            "name": name,
            "status": status,
            "exit": int(code) if code.strip() else None,
            "started_utc": int(start) if start.strip() else None,
            "duration_s": int(duration) if duration.strip().isdigit() else None,
            "log": log,
            "argv": rest[0].split() if rest and rest[0].strip() else [],
        })

mem_kb = 0
for line in rd("/proc/meminfo").splitlines():
    if line.startswith("MemTotal:"):
        mem_kb = int(line.split()[1])

summary = {
    "tool": "stress_vm.sh",
    "stamp_utc": os.environ["HSCL_STRESS_STAMP"],
    "disposable_vm": True,
    "marker": os.environ["HSCL_STRESS_MARKER"],
    "dmi": os.environ["HSCL_STRESS_VIRT"],
    "host": {
        "kernel": platform.release(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
        "mem_total_mb": round(mem_kb / 1024) if mem_kb else None,
        "free_disk_mb": round(shutil.disk_usage(os.path.dirname(os.environ["HSCL_STRESS_JSON"])).free / 1048576),
    },
    "parameters": {
        "stress_seconds": int(os.environ["HSCL_STRESS_SECONDS"]),
        "fio_seconds": int(os.environ["HSCL_STRESS_FIO_SECONDS"]),
    },
    "overall": os.environ["HSCL_STRESS_OVERALL"],
    "tests": tests,
}
with open(os.environ["HSCL_STRESS_JSON"], "w", encoding="utf-8") as fh:
    json.dump(summary, fh, indent=2)
    fh.write("\n")
PY
rm -f "$records" "$out/fio-target.img"

echo "stress run: $overall (evidence: $out/summary.json)"
"$py" - "$out/summary.json" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as fh:
    summary = json.load(fh)
for t in summary["tests"]:
    print("  %s: %s" % (t["name"], t["status"]))
PY

[ "$overall" = "ok" ] && exit 0
exit 1
