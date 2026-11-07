"""Test child: tries to allocate far more memory than its limit."""
import json
import sys

from hcseasymath.jobs.sandbox import apply_limits

apply_limits(memory_bytes=int(sys.argv[1]), cpu_seconds=int(sys.argv[2]))
json.load(sys.stdin)
try:
    hog = bytearray(2 * 1024 * 1024 * 1024)  # 2 GiB, far above the test limit
    print(json.dumps({"survived": len(hog)}))
except MemoryError:
    sys.exit(75)  # same mapping as hcseasymath.jobs.child
