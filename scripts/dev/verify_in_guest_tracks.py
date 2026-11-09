#!/usr/bin/env python3
"""Automated in-guest verification of all HSCL1 core tracks (L, K, C, B, S, D, R, DEV, SYS, APP, AI, LAB)."""
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
        echo "=== HSCL PRIVACY STATUS ==="
        /usr/bin/hscl privacy status || true
        echo "=== HSCL PRIVACY STATUS (JSON) ==="
        /usr/bin/hscl --json privacy status || true
        echo "=== HSCL PRIVACY SESSION EXPLAIN ==="
        /usr/bin/hscl privacy session explain || true
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

        # 5. Track S: Security Posture, Firewall Profiles, AppArmor, Encryption
        print("\n--- Testing Track S (Security CLI subcommands) ---", flush=True)
        cmd_security = """
        echo "=== HSCL SECURITY STATUS ==="
        /usr/bin/hscl security status
        echo "=== HSCL SECURITY FIREWALL STATUS (JSON) ==="
        /usr/bin/hscl --json security firewall status
        echo "=== HSCL SECURITY FIREWALL PROFILES ==="
        /usr/bin/hscl security firewall profile list
        echo "=== HSCL SECURITY APPARMOR STATUS ==="
        /usr/bin/hscl security apparmor status
        echo "=== HSCL SECURITY ENCRYPTION STATUS ==="
        /usr/bin/hscl security encryption status
        echo "=== HSCL SECURITY RECOVERY CHECK ==="
        /usr/bin/hscl security recovery check
        """
        r_sec = run_cmd(vm, cmd_security)
        report["tracks"]["track_s_security"] = {
            "exit": r_sec.get("exit"),
            "stdout": r_sec.get("stdout"),
            "stderr": r_sec.get("stderr"),
            "success": r_sec.get("exit") == 0,
        }

        # 6. Track D: Diagnostic Logs & Redaction
        print("\n--- Testing Track D (Logs inspection and collection) ---", flush=True)
        cmd_logs = """
        echo "=== HSCL LOGS SHOW (SYSTEM) ==="
        /usr/bin/hscl logs show --lines 10
        echo "=== HSCL LOGS SHOW (KERNEL) ==="
        /usr/bin/hscl --json logs show kernel --lines 5
        echo "=== HSCL LOGS COLLECT ==="
        /usr/bin/hscl logs collect --output /tmp/guest_diag_bundle.json
        test -f /tmp/guest_diag_bundle.json
        """
        r_logs = run_cmd(vm, cmd_logs)
        report["tracks"]["track_d_logs"] = {
            "exit": r_logs.get("exit"),
            "stdout": r_logs.get("stdout"),
            "stderr": r_logs.get("stderr"),
            "success": r_logs.get("exit") == 0,
        }

        # 7. Track R: Recovery CLI
        print("\n--- Testing Track R (Recovery status and snapshots) ---", flush=True)
        cmd_recovery = """
        echo "=== HSCL RECOVERY STATUS ==="
        /usr/bin/hscl recovery status
        echo "=== HSCL RECOVERY SNAPSHOTS LIST (JSON) ==="
        /usr/bin/hscl --json recovery snapshots list
        """
        r_rec = run_cmd(vm, cmd_recovery)
        report["tracks"]["track_r_recovery"] = {
            "exit": r_rec.get("exit"),
            "stdout": r_rec.get("stdout"),
            "stderr": r_rec.get("stderr"),
            "success": r_rec.get("exit") == 0,
        }

        # 8. Track DEV: Developer Environment
        print("\n--- Testing Track DEV (Developer status and git hygiene) ---", flush=True)
        cmd_dev = """
        echo "=== HSCL DEV STATUS ==="
        /usr/bin/hscl dev status
        echo "=== HSCL DEV GIT DOCTOR ==="
        /usr/bin/hscl dev git doctor || true
        """
        r_dev = run_cmd(vm, cmd_dev)
        report["tracks"]["track_dev"] = {
            "exit": r_dev.get("exit"),
            "stdout": r_dev.get("stdout"),
            "stderr": r_dev.get("stderr"),
            "success": r_dev.get("exit") == 0,
        }

        # 9. Track SYS: System Information and Services
        print("\n--- Testing Track SYS (System info and services) ---", flush=True)
        cmd_sys = """
        echo "=== HSCL SYSTEM INFO ==="
        /usr/bin/hscl system info
        echo "=== HSCL SYSTEM SERVICES (ENABLED) ==="
        /usr/bin/hscl --json system services --enabled
        """
        r_sys = run_cmd(vm, cmd_sys)
        report["tracks"]["track_sys_system"] = {
            "exit": r_sys.get("exit"),
            "stdout": r_sys.get("stdout"),
            "stderr": r_sys.get("stderr"),
            "success": r_sys.get("exit") == 0,
        }

        # 10. Track APP: Appearance, Wallpaper and Layout
        print("\n--- Testing Track APP (Appearance mode, dock and wallpapers) ---", flush=True)
        cmd_app = """
        echo "=== HSCL APPEARANCE MODE ==="
        /usr/bin/hscl appearance mode
        echo "=== HSCL APPEARANCE DOCK POSITION (DRY-RUN) ==="
        /usr/bin/hscl appearance dock position bottom --dry-run
        echo "=== HSCL APPEARANCE WALLPAPER LIST ==="
        /usr/bin/hscl appearance wallpaper list
        """
        r_app = run_cmd(vm, cmd_app)
        report["tracks"]["track_app_appearance"] = {
            "exit": r_app.get("exit"),
            "stdout": r_app.get("stdout"),
            "stderr": r_app.get("stderr"),
            "success": r_app.get("exit") == 0,
        }

        # 11. Track AI: Local AI Detection and Storage
        print("\n--- Testing Track AI (AI detect, backend and storage) ---", flush=True)
        cmd_ai = """
        echo "=== HSCL AI DETECT ==="
        /usr/bin/hscl ai detect
        echo "=== HSCL AI BACKEND LIST ==="
        /usr/bin/hscl ai backend list
        echo "=== HSCL AI STORAGE SHOW ==="
        /usr/bin/hscl ai storage show
        """
        r_ai = run_cmd(vm, cmd_ai)
        report["tracks"]["track_ai_tooling"] = {
            "exit": r_ai.get("exit"),
            "stdout": r_ai.get("stdout"),
            "stderr": r_ai.get("stderr"),
            "success": r_ai.get("exit") == 0,
        }

        # 12. Track LAB: Security Lab Toolsets and Isolation
        print("\n--- Testing Track LAB (Toolsets, containers, and VM profiles) ---", flush=True)
        cmd_lab = """
        echo "=== HSCL LAB TOOLSETS LIST ==="
        /usr/bin/hscl lab toolsets list
        echo "=== HSCL LAB CONTAINER LIST ==="
        /usr/bin/hscl lab container list
        echo "=== HSCL LAB VM LIST ==="
        /usr/bin/hscl lab vm list
        """
        r_lab = run_cmd(vm, cmd_lab)
        report["tracks"]["track_lab_expansion"] = {
            "exit": r_lab.get("exit"),
            "stdout": r_lab.get("stdout"),
            "stderr": r_lab.get("stderr"),
            "success": r_lab.get("exit") == 0,
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
