"""Test child: reports which environment variables it can see."""
import json
import os
import sys

from hcseasymath.jobs.sandbox import apply_limits

apply_limits(memory_bytes=int(sys.argv[1]), cpu_seconds=int(sys.argv[2]))
json.load(sys.stdin)
print(json.dumps({"env_keys": sorted(os.environ)}))
