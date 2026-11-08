"""Test engine for the warm worker: records its pid, then never finishes."""
import os
import time


def execute(request):
    with open(request["pid_file"], "w") as fh:
        fh.write(str(os.getpid()))
    time.sleep(600)
