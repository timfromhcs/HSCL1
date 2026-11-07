"""Worker child: read one JSON request on stdin, write one JSON result on stdout.

Exit code 75 means "ran out of a resource" (memory); the parent maps it to the
``resource_limit`` status. Anything else non-zero is an internal error.
"""

from __future__ import annotations

import json
import sys

EXIT_RESOURCE = 75
MAX_REQUEST_BYTES = 64 * 1024


def main() -> int:
    from .sandbox import apply_limits

    apply_limits(memory_bytes=int(sys.argv[1]), cpu_seconds=int(sys.argv[2]))
    try:
        raw = sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1)
        if len(raw) > MAX_REQUEST_BYTES:
            print(json.dumps({"_child_error": "request too large"}))
            return 2
        request = json.loads(raw)
        from ..core.engine import execute  # imported after the limits are in force

        sys.stdout.write(json.dumps(execute(request)))
        return 0
    except MemoryError:
        return EXIT_RESOURCE
    except (ValueError, UnicodeDecodeError):
        print(json.dumps({"_child_error": "request is not valid JSON"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
