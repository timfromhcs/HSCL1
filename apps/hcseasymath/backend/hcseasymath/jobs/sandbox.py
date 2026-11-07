"""Resource limits applied by a worker child to itself, before it imports anything heavy.

Doing this in the child (not with ``preexec_fn`` in the parent) keeps the parent free of
the fork-in-a-threaded-process hazards that ``subprocess`` documents for ``preexec_fn``.
POSIX only; the gate for this module runs on Linux (WSL or CI).
"""

from __future__ import annotations

import resource


def apply_limits(*, memory_bytes: int, cpu_seconds: int) -> None:
    """Cap address space, CPU time and open files; disable core dumps."""
    resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 1))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
