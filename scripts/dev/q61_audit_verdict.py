"""Extract the Q-61 verdict from the audit probe's port dump (artifacts/q61-audit2/port.txt).

The probe loads an audit rule on kill(2)/tgkill(2) and starts Calamares 12 times; a death is visible as
an exit status of 137 in the wrapper, and the audit record names the process that sent the SIGKILL.
"""

import re
import sys
from pathlib import Path

port = Path(sys.argv[1] if len(sys.argv) > 1 else "artifacts/q61-audit2/port.txt")
text = port.read_bytes().decode("utf-8", "replace")

print("=== per-start result ===")
for line in text.splitlines():
    if line.startswith("Q61| start"):
        print(line)

SYSCALL = re.compile(r"syscall=(\d+) success=(\w+) exit=(-?\d+) a0=([0-9a-f]+) a1=([0-9a-f]+) a2=([0-9a-f]+)")
SENDER = re.compile(r'ppid=(\d+) pid=(\d+) auid=(\d+).*?comm="([^"]*)" exe="([^"]*)"')
VICTIM = re.compile(r'opid=(\d+) oauid=\d+ ouid=\d+ oses=\d+ obj=unconfined ocomm="([^"]*)"')

print("\n=== SIGKILL events and their senders ===")
for block in text.split("----"):
    if 'key="q61kill"' not in block:
        continue
    call, who = SYSCALL.search(block), SENDER.search(block)
    if not call or not who:
        continue
    _, ok, _, a0, a1, _ = call.groups()
    if int(a1, 16) != 9:
        continue
    ppid, pid, _, comm, exe = who.groups()
    print(f"  sender {comm} (pid {pid}, ppid {ppid}, {exe}) kill(pid={int(a0, 16)}, SIGKILL) success={ok}")
    for vpid, vcomm in VICTIM.findall(block):
        print(f"      victim pid {vpid} comm={vcomm}")
