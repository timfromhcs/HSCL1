"""Test child: writes far more output than the worker will accept."""
import json
import sys

from hcseasymath.jobs.sandbox import apply_limits

apply_limits(memory_bytes=int(sys.argv[1]), cpu_seconds=int(sys.argv[2]))
json.load(sys.stdin)
chunk = "x" * 65536
for _ in range(400):  # about 26 MB
    sys.stdout.write(chunk)
    sys.stdout.flush()
