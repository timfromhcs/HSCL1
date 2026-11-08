#!/usr/bin/env python3
"""Automated ISO showcase capture via QEMU, Workshop API, and QMP.

Boots the HSCL1 candidate ISO, connects to the guest Workshop API, systematically
launches every core application and desktop feature, and captures high-resolution
PNG screenshots for documentation and verification evidence.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "workshop"))
import qemu_boot_test as q  # noqa: E402
import vm as vmmod  # noqa: E402
import e2e_respin as respin  # noqa: E402


def run_guest(vm, cmd: str, user: str = "hscl1", timeout: int = 60) -> dict:
    """Run shell command inside live guest session."""
    env = "WAYLAND_DISPLAY=wayland-0 DISPLAY=:0 XDG_RUNTIME_DIR=/run/user/1000"
    if user == "root":
        full_cmd = f"({cmd}) 2>&1"
    else:
        full_cmd = f"su - {user} -c '{env} ({cmd})' 2>&1"
    hook_script = f"#!/bin/bash\n{full_cmd}\n"
    hook_name = f"exec-{int(time.time()*1000)}.sh"
    return respin.hook(vm, hook_name, hook_script, timeout=timeout)


def capture(vm, out_dir: Path, filename: str, desc: str, manifest: list) -> Path:
    time.sleep(1.5)
    png = vm.screenshot_png()
    target = out_dir / filename
    target.write_bytes(png)
    print(f"[CAPTURED] {filename} ({len(png)} bytes): {desc}", flush=True)
    manifest.append({
        "filename": filename,
        "bytes": len(png),
        "description": desc,
        "timestamp": time.time()
    })
    return target


def main() -> int:
    iso_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"\\wsl.localhost\Ubuntu\home\tim\hscl1-build\out\HSCL1-0.1.3-alpha.0-amd64.iso")
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "artifacts" / "screenshots-showcase"
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []

    print(f"=== Starting HSCL1 Showcase Capture ===")
    print(f"ISO: {iso_path}")
    print(f"Output: {out_dir}")

    if not iso_path.exists():
        print(f"ERROR: ISO not found: {iso_path}", file=sys.stderr)
        return 1

    mgr = vmmod.VmManager(out_dir / "vm_work", mem_guard=False)
    vm = mgr.start("showcase", str(iso_path), None, memory_mb=3072, firmware="uefi")
    try:
        print("[1/10] Waiting for live desktop...", flush=True)
        desktop_s = respin.wait_desktop(vm, timeout=360)
        print(f"Live desktop reached after {desktop_s} seconds.", flush=True)

        # Allow desktop session to stabilize
        time.sleep(10)
        # Dismiss any lingering welcome/first-run dialogs
        q.click(vm.qmp, 0.288, 0.848)
        time.sleep(2)
        q.send_keys(vm.qmp, ["esc"])
        time.sleep(1)

        # 1. Clean Desktop
        capture(vm, out_dir, "01_desktop_clean.png", "Clean HSCL1 Live Desktop with top bar and dock", manifest)

        # 2. Dynamic Wallpapers
        print("[2/10] Capturing dynamic wallpaper shader presets...", flush=True)
        for preset in ["rain", "aurora", "grid", "starfield"]:
            run_guest(vm, f"hscl wallpaper apply {preset}")
            time.sleep(2.5)
            capture(vm, out_dir, f"02_wallpaper_{preset}.png", f"Dynamic wallpaper shader: {preset}", manifest)

        # Restore default rain wallpaper
        run_guest(vm, "hscl wallpaper apply rain")
        time.sleep(2)

        # 3. Application Launcher (Kickoff / Start Menu)
        print("[3/10] Capturing Application Launcher...", flush=True)
        q.send_keys(vm.qmp, ["meta_l"])
        time.sleep(2)
        capture(vm, out_dir, "03_app_launcher_kickoff.png", "Kickoff Application Launcher / Start Menu", manifest)
        q.send_keys(vm.qmp, ["esc"])
        time.sleep(1)

        # 4. HCS Control Center Suite
        print("[4/10] Launching HCS Control Center (Qt 6 / QML)...", flush=True)
        run_guest(vm, "hscl-control-center &")
        time.sleep(4)
        capture(vm, out_dir, "04_control_center_overview.png", "Control Center: System Overview & Hardware", manifest)

        # Navigate through Control Center tabs (sidebar clicks)
        q.click(vm.qmp, 0.12, 0.35)  # Appearance tab
        time.sleep(2)
        capture(vm, out_dir, "05_control_center_appearance.png", "Control Center: Appearance, Tokens & Themes", manifest)

        q.click(vm.qmp, 0.12, 0.45)  # Security tab
        time.sleep(2)
        capture(vm, out_dir, "06_control_center_security.png", "Control Center: Security Baseline & Firewall Policy", manifest)

        q.click(vm.qmp, 0.12, 0.70)  # About tab
        time.sleep(2)
        capture(vm, out_dir, "07_control_center_about.png", "Control Center: About & System Attestation", manifest)

        # Close Control Center
        q.send_keys(vm.qmp, ["alt", "f4"])
        time.sleep(2)

        # 5. Terminal Showcase: hscl CLI suite
        print("[5/10] Launching Konsole with hscl commands...", flush=True)
        run_guest(vm, "konsole --hold -e bash -c 'hscl status; echo; hscl doctor; echo; hscl memory status; exec bash' &")
        time.sleep(3.5)
        capture(vm, out_dir, "08_terminal_hscl_status_doctor.png", "Konsole: hscl status, doctor & memory status", manifest)

        # Run hscl lab inside terminal
        q.type_text(vm.qmp, "hscl lab --help\n")
        time.sleep(2)
        capture(vm, out_dir, "09_terminal_hscl_lab.png", "Konsole: hscl lab isolated container suite", manifest)

        # Close Konsole
        q.send_keys(vm.qmp, ["alt", "f4"])
        time.sleep(2)

        # 6. Dolphin File Manager
        print("[6/10] Launching Dolphin File Manager...", flush=True)
        run_guest(vm, "dolphin &")
        time.sleep(3.5)
        capture(vm, out_dir, "10_app_dolphin.png", "Dolphin File Manager with HCS styling", manifest)
        q.send_keys(vm.qmp, ["alt", "f4"])
        time.sleep(2)

        # 7. Calamares Installer
        print("[7/10] Launching Calamares Installer...", flush=True)
        run_guest(vm, "calamares &")
        time.sleep(4.5)
        capture(vm, out_dir, "11_installer_welcome.png", "Calamares Installer: Welcome Screen", manifest)

        # Click Next to show language/location
        q.click(vm.qmp, 0.88, 0.93)
        time.sleep(2.5)
        capture(vm, out_dir, "12_installer_location.png", "Calamares Installer: Location & Timezone", manifest)
        q.send_keys(vm.qmp, ["alt", "f4"])
        time.sleep(2)

        # 8. Offline Handbook
        print("[8/10] Launching Offline Handbook...", flush=True)
        run_guest(vm, "xdg-open /usr/share/doc/hscl-handbook/index.html || true")
        time.sleep(3.5)
        capture(vm, out_dir, "13_offline_handbook.png", "Trilingual Offline Handbook in Browser", manifest)
        q.send_keys(vm.qmp, ["alt", "f4"])
        time.sleep(2)

        # 9. Kate Text Editor
        print("[9/10] Launching Kate Text Editor...", flush=True)
        run_guest(vm, "kate &")
        time.sleep(3)
        capture(vm, out_dir, "14_app_kate.png", "Kate Text Editor with HCS syntax theme", manifest)
        q.send_keys(vm.qmp, ["alt", "f4"])
        time.sleep(2)

        # 10. Final Clean State
        print("[10/10] Capturing final session state...", flush=True)
        capture(vm, out_dir, "15_desktop_final.png", "Final live desktop state after showcase sequence", manifest)

        # Write manifest
        manifest_file = out_dir / "manifest.json"
        manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(f"\nSUCCESS: Captured {len(manifest)} screenshots in {out_dir}")
        print(f"Manifest written to: {manifest_file}")

    finally:
        print("Stopping QEMU VM...", flush=True)
        mgr.stop_all()

    return 0


if __name__ == "__main__":
    sys.exit(main())
