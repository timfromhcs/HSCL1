#!/usr/bin/env python3
"""End-to-end proof of the development loop: update a live VM through the Workshop API, respin it to a new installer ISO,
boot that ISO and check the update is there.

Usage: e2e_respin.py ISO OUTDIR            (Windows host with QEMU+WHPX and a WSL distro, or Linux with QEMU)
Evidence: OUTDIR/report.json, screenshots, OUTDIR/respun.iso (+ sha256).
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "workshop"))
sys.path.insert(0, str(ROOT / "scripts"))
import qemu_boot_test as q  # noqa: E402
import vm as vmmod  # noqa: E402


def rgb_shot(vm):
    ppm = vm.workdir / "p.ppm"
    vm.qmp.cmd("screendump", filename=str(ppm))
    png, w, h, rgb = q.ppm_to_png(ppm.read_bytes())
    ppm.unlink()
    return png, w, h, rgb


def wait_desktop(vm, timeout=480):
    t0, streak, clicked = time.time(), 0, False
    while time.time() - t0 < timeout:
        time.sleep(10)
        _png, w, h, rgb = rgb_shot(vm)
        if q.looks_like_welcome(rgb, w, h) and not q.looks_like_desktop(rgb, w, h) and not clicked:
            q.click(vm.qmp, 0.27, 0.80)
            clicked = True
        streak = streak + 1 if q.looks_like_desktop(rgb, w, h) else 0
        if streak >= 2:
            time.sleep(5)
            q.click(vm.qmp, 0.288, 0.848)  # skip the Plasma Welcome Center if it is open
            time.sleep(3)
            return round(time.time() - t0)
    raise SystemExit("desktop not reached")


def put(vm, guest_path: str, data: bytes, mode: str = "0644"):
    return vm.rpc("put_file", {"path": guest_path, "mode": mode, "content_b64": base64.b64encode(data).decode()})


def hook(vm, name: str, script: str, timeout=900):
    put(vm, f"/usr/lib/hscl/workshop/hooks/{name}", script.encode(), "0755")
    return vm.rpc("run_hook", {"name": name, "timeout": timeout}, timeout=timeout + 60)


def bootstrap(vm) -> dict:
    """Push the current Workshop tools into a VM booted from an older ISO. Hooks run arbitrary root shell by design
    (they are files the VM owner supplies), so this works even when the old daemon's allow-list is too narrow."""
    base = ROOT / "packages/debian/hscl-workshop/usr/lib/hscl/workshop"
    lines = ["set -e"]
    for name, mode in (("hscl-respin", "0755"), ("hscl_workshopd.py", "0755")):
        b64 = base64.b64encode((base / name).read_bytes()).decode()
        dst = f"/usr/lib/hscl/workshop/{name}"
        lines.append(f"printf '%s' '{b64}' | base64 -d > {dst}.new && chmod {mode[1:]} {dst}.new && mv {dst}.new {dst}")
    lines.append("echo bootstrapped")
    return hook(vm, "bootstrap.sh", chr(10).join(lines) + chr(10))


def wsl_path(p: Path) -> str:
    return subprocess.run(["wsl", "-d", "Ubuntu", "--", "wslpath", "-a", "-u", str(p)], capture_output=True, text=True).stdout.strip() if os.name == "nt" else str(p)


def sh(cmd: str) -> subprocess.CompletedProcess:
    argv = ["wsl", "-d", "Ubuntu", "--", "bash", "-c", cmd] if os.name == "nt" else ["bash", "-c", cmd]
    return subprocess.run(argv, capture_output=True, text=True)


def main() -> int:
    iso, out = sys.argv[1], Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    report: dict = {}
    proof = f"hscl-respin-proof-{uuid.uuid4()}"
    scratch = out / "scratch.qcow2"
    scratch.unlink(missing_ok=True)

    mgr = vmmod.VmManager(out / "vm")
    # ---- phase 1: update a live VM through the API and respin it
    vm = mgr.start("one", iso, str(scratch), 4096, "uefi")
    try:
        report["desktop_after_s"] = wait_desktop(vm)
        report["status"] = vm.rpc("status", timeout=180)
        report["bootstrap"] = bootstrap(vm)["stdout"].strip()
        report["diag"] = hook(vm, "diag.sh", "cat /proc/cmdline; echo; ls /cdrom | head; echo; findmnt -no SOURCE,FSTYPE /cdrom; lsblk -dno NAME,SIZE | head\n")["stdout"][-900:]
        put(vm, "/usr/share/hscl/respin-proof.txt", proof.encode())
        h = hook(vm, "mkout.sh", "set -e\nmkfs.ext4 -q -F -L hscl-out /dev/vdb\nmkdir -p /mnt/out\nmount /dev/vdb /mnt/out\nfindmnt -no SOURCE,FSTYPE /mnt/out\n")
        report["mkout"] = h
        t0 = time.time()
        r = vm.rpc("respin", {"out_dir": "/mnt/out"}, timeout=3600)
        report["respin"] = {"exit": r["exit"], "stdout": r["stdout"][-600:], "stderr": r["stderr"][-600:], "seconds": round(time.time() - t0)}
        if r["exit"] != 0:
            raise SystemExit("respin failed: " + json.dumps(report["respin"]))
        report["ls_out"] = hook(vm, "lsout.sh", "ls -la /mnt/out; sync\n")["stdout"][-600:]
    finally:
        (out / "report.json").write_text(json.dumps(report, indent=1))
        mgr.stop_all()

    # ---- extract the respun ISO from the scratch disk (WSL loop mount, read-only)
    raw = "/home/tim/hscl1-build/scratch.raw" if os.name == "nt" else str(out / "scratch.raw")
    dst = wsl_path(out)
    cmd = (f"set -e; qemu-img convert -O raw '{wsl_path(scratch)}' '{raw}'; mkdir -p /tmp/hscl-x; sudo mount -o loop,ro '{raw}' /tmp/hscl-x; "
           f"ls /tmp/hscl-x; cp /tmp/hscl-x/HSCL1-respin-*.iso '{dst}/respun.iso'; cp /tmp/hscl-x/HSCL1-respin-*.iso.manifest.json '{dst}/respun.manifest.json'; "
           f"sudo umount /tmp/hscl-x; rm -f '{raw}'")
    e = sh(cmd)
    report["extract"] = {"rc": e.returncode, "out": e.stdout[-300:], "err": e.stderr[-300:]}
    respun = out / "respun.iso"
    if e.returncode != 0 or not respun.exists():
        (out / "report.json").write_text(json.dumps(report, indent=1))
        raise SystemExit("could not extract the respun ISO")
    h = hashlib.sha256()
    with respun.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    report["respun_iso"] = {"bytes": respun.stat().st_size, "sha256": h.hexdigest()}
    scratch.unlink(missing_ok=True)

    # ---- phase 2: boot the respun ISO and look for the proof
    mgr2 = vmmod.VmManager(out / "vm2")
    vm2 = mgr2.start("two", str(respun), None, 4096, "uefi")
    try:
        report["respun_desktop_after_s"] = wait_desktop(vm2)
        report["respun_status"] = vm2.rpc("status", timeout=180)
        cat = hook(vm2, "check.sh", "cat /usr/share/hscl/respin-proof.txt\n")
        report["proof_found"] = cat["stdout"].strip() == proof
        (out / "respun-desktop.png").write_bytes(rgb_shot(vm2)[0])
    finally:
        (out / "report.json").write_text(json.dumps(report, indent=1))
        mgr2.stop_all()
    print(json.dumps({k: report[k] for k in ("desktop_after_s", "respun_desktop_after_s", "proof_found", "respun_iso")}, indent=1))
    return 0 if report.get("proof_found") else 1


if __name__ == "__main__":
    sys.exit(main())
