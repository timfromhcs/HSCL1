"""Test child: records its pid, then never finishes."""
import json
import os
import sys
import time

from hcseasymath.jobs.sandbox import apply_limits

apply_limits(memory_bytes=int(sys.argv[1]), cpu_seconds=int(sys.argv[2]))
req = json.load(sys.stdin)
with open(req["pid_file"], "w") as fh:
    fh.write(str(os.getpid()))
time.sleep(600)
