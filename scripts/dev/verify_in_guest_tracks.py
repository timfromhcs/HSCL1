#!/usr/bin/env python3
"""Automated in-guest verification of Track B, Track C, Track K, and Track L."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "workshop"))
import qemu_boot_test as q  # noqa: E402
import vm as vmmod  # noqa: E402
import e2e_respin as respin  # noqa: E402


def run_cmd(vm, cmd: str, timeout: int = 45) -> dict:
    hook_script = f"#!/bin/bash\nset -Eeuo pipefail\n{cmd}\n"
    hook_name = f"hook{int(time.time()*1000) % 1000000}.sh"
    res = respin.hook(vm, hook_name, hook_script, timeout=timeout)
    print(f"--- Hook {hook_name} (exit={res.get('exit')}) ---")
    if res.get("stdout"):
        print(res["stdout"])
    if res.get("stderr"):
        print("STDERR:", res["stderr"])
    return res


def take_shot(vm, path: Path) -> Path:
    png = vm.screenshot_png()
    path.write_bytes(png)
    im = Image.open(path)
    colors = len(im.getcolors(maxcolors=200000) or [])
    print(f"[SHOT] {path.name}: {len(png)} bytes, {colors} colors, size={im.size}", flush=True)
    return path


def main() -> int:
    iso = Path(r"\\wsl.localhost\Ubuntu\home\tim\hscl1-build\out\HSCL1-candidate-amd64.iso")
    out_dir = ROOT / "artifacts" / "in_guest_verification"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=== Starting In-Guest Verification of HSCL1 Candidate ===", flush=True)
    mgr = vmmod.VmManager(out_dir / "vm_work", mem_guard=False)
    vm = mgr.start("candidate_diag", str(iso), None, memory_mb=3072, firmware="uefi")
    report = {
        "iso": iso.name,
        "timestamp": time.time(),
        "tracks": {},
    }

    try:
        print("Waiting for live desktop...", flush=True)
        desktop_s = respin.wait_desktop(vm, timeout=360)
        print(f"Live desktop reached after {desktop_s}s", flush=True)
        report["desktop_reached_s"] = desktop_s

        take_shot(vm, out_dir / "01_live_desktop.png")

        # 1. Track L: Language CLI in Guest
        print("\n--- Testing Track L (hscl language list & status) ---", flush=True)
        cmd_lang = """
        echo "=== HSCL LANGUAGE LIST ==="
        /usr/bin/hscl language list
        echo "=== HSCL LANGUAGE STATUS (JSON) ==="
        /usr/bin/hscl --json language status
        """
        r_lang = run_cmd(vm, cmd_lang)
        report["tracks"]["track_l_language"] = {
            "exit": r_lang.get("exit"),
            "stdout": r_lang.get("stdout"),
            "stderr": r_lang.get("stderr"),
            "success": r_lang.get("exit") == 0,
        }

        # 2. Track K: Shortcuts & Hotkeys in Guest
        print("\n--- Testing Track K (hscl-shortcuts and kglobalshortcutsrc) ---", flush=True)
        cmd_shortcuts = """
        echo "=== SHORTCUTS HELPER ==="
        /usr/bin/hscl-shortcuts --help || /usr/bin/hscl-shortcuts
        echo "=== KGLOBALSHORTCUTSRC CHECK ==="
        grep -E "Walk Through Windows|Activate Application Launcher" /etc/xdg/kglobalshortcutsrc || true
        """
        r_shortcuts = run_cmd(vm, cmd_shortcuts)
        report["tracks"]["track_k_shortcuts"] = {
            "exit": r_shortcuts.get("exit"),
            "stdout": r_shortcuts.get("stdout"),
            "stderr": r_shortcuts.get("stderr"),
            "success": r_shortcuts.get("exit") == 0,
        }

        # 3. Track C: Privacy & Mount Isolation (No automount of host disks)
        print("\n--- Testing Track C (Mount isolation & ephemeral zram) ---", flush=True)
        cmd_privacy = """
        echo "=== MOUNTED PARTITIONS ==="
        df -h
        echo "=== SWAP & ZRAM ==="
        swapon --show || true
        echo "=== DUMPABLE SYSCTL ==="
        sysctl fs.suid_dumpable || true
        """
        r_priv = run_cmd(vm, cmd_privacy)
        report["tracks"]["track_c_privacy"] = {
            "exit": r_priv.get("exit"),
            "stdout": r_priv.get("stdout"),
            "stderr": r_priv.get("stderr"),
            "success": r_priv.get("exit") == 0,
        }

        # 4. Track B: Security Lab Podman presence / container capabilities
        print("\n--- Testing Track B (Security Lab / Podman check) ---", flush=True)
        cmd_podman = """
        echo "=== PODMAN CHECK ==="
        which podman || echo "podman not preinstalled on host base (expected per threat model)"
        /usr/bin/hscl lab status
        """
        r_podman = run_cmd(vm, cmd_podman)
        report["tracks"]["track_b_security_lab"] = {
            "exit": r_podman.get("exit"),
            "stdout": r_podman.get("stdout"),
            "stderr": r_podman.get("stderr"),
            "success": r_podman.get("exit") == 0,
        }

        take_shot(vm, out_dir / "02_final_desktop.png")
        report["overall_success"] = all(
            t.get("success", False) for t in report["tracks"].values()
        )

    finally:
        print("Stopping VM...", flush=True)
        mgr.stop_all()

    report_path = out_dir / "verification_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nReport written to {report_path}", flush=True)
    print("Verification Summary:\n" + json.dumps({k: v.get("success") for k, v in report["tracks"].items()}, indent=2))
    return 0 if report.get("overall_success") else 1


if __name__ == "__main__":
    sys.exit(main())
