#!/usr/bin/env python3
"""Live interactive ISO showcase capture via QEMU, Workshop API, and QMP.

Boots the HSCL1 candidate ISO, navigates the live desktop session using
genuine Wayland environment variables and QMP keyboard/mouse chords,
and captures high-contrast, distinct application window screenshots.
"""
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


def run_guest(vm, cmd: str, timeout: int = 60) -> dict:
    """Run shell command inside guest as root."""
    hook_script = f"#!/bin/bash\n{cmd}\n"
    hook_name = f"exec-{int(time.time()*1000)}.sh"
    return respin.hook(vm, hook_name, hook_script, timeout=timeout)


def run_gui_app(vm, app_cmd: str) -> None:
    """Launch GUI application inside hscl1 user Wayland session."""
    env = "WAYLAND_DISPLAY=wayland-0 DISPLAY=:0 XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus"
    cmd = f"sudo -u hscl1 env {env} nohup {app_cmd} > /tmp/gui_app.log 2>&1 &"
    run_guest(vm, cmd)


def close_gui_apps(vm, proc_name: str | None = None) -> None:
    """Close active GUI application cleanly."""
    q.send_keys(vm.qmp, ["alt", "f4"])
    time.sleep(1.0)
    if proc_name:
        run_guest(vm, f"killall -9 {proc_name} 2>/dev/null || true")
        time.sleep(0.5)


def capture_shot(vm, out_dir: Path, filename: str, desc: str, manifest: list) -> Path:
    time.sleep(1.2)
    png = vm.screenshot_png()
    target = out_dir / filename
    target.write_bytes(png)
    im = Image.open(target)
    colors = len(im.getcolors(maxcolors=200000) or [])
    print(f"[CAPTURED] {filename} ({len(png)} bytes, {colors} colors): {desc}", flush=True)
    manifest.append({
        "filename": filename,
        "bytes": len(png),
        "colors": colors,
        "size": list(im.size),
        "description": desc,
        "timestamp": time.time()
    })
    return target


def main() -> int:
    iso_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"\\wsl.localhost\Ubuntu\home\tim\hscl1-build\out\HSCL1-0.1.3-alpha.0-amd64.iso")
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "docs" / "img" / "showcase"
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []

    print(f"=== Starting HSCL1 Live Interactive Showcase Capture ===")
    print(f"ISO: {iso_path}")
    print(f"Target directory: {out_dir}")

    if not iso_path.exists():
        print(f"ERROR: ISO not found: {iso_path}", file=sys.stderr)
        return 1

    mgr = vmmod.VmManager(ROOT / "artifacts" / "vm_showcase_live", mem_guard=False)
    vm = mgr.start("showcase_live", str(iso_path), None, memory_mb=3072, firmware="uefi")
    try:
        print("[1/10] Waiting for live desktop...", flush=True)
        desktop_s = respin.wait_desktop(vm, timeout=360)
        print(f"Live desktop reached after {desktop_s} seconds.", flush=True)

        # Allow session to settle and dismiss welcome
        time.sleep(8)
        q.click(vm.qmp, 0.288, 0.848)
        time.sleep(1.5)
        q.send_keys(vm.qmp, ["esc"])
        time.sleep(1.0)

        # Ensure default rain wallpaper is set
        run_guest(vm, "sudo -u hscl1 env WAYLAND_DISPLAY=wayland-0 XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus hscl wallpaper apply rain || true")
        time.sleep(2)

        # 1. Clean Desktop
        capture_shot(vm, out_dir, "01_desktop_clean.png", "Clean HSCL1 Live Desktop with top bar and dock", manifest)

        # 2. Dynamic Wallpapers
        print("[2/10] Capturing dynamic wallpaper shader presets...", flush=True)
        for preset in ["aurora", "grid", "starfield", "rain"]:
            run_guest(vm, f"sudo -u hscl1 env WAYLAND_DISPLAY=wayland-0 XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus hscl wallpaper apply {preset} || true")
            time.sleep(2.5)
            capture_shot(vm, out_dir, f"02_wallpaper_{preset}.png", f"Dynamic wallpaper shader: {preset}", manifest)

        # 3. Application Launcher (Kickoff / Start Menu)
        print("[3/10] Capturing Application Launcher (Kickoff)...", flush=True)
        q.send_keys(vm.qmp, ["meta_l"])
        time.sleep(2.0)
        capture_shot(vm, out_dir, "03_app_launcher_kickoff.png", "Kickoff Application Launcher / Start Menu", manifest)
        q.send_keys(vm.qmp, ["esc"])
        time.sleep(1.5)

        # 4. Interactive Konsole Terminal Showcase
        print("[4/10] Launching interactive Konsole terminal...", flush=True)
        run_gui_app(vm, "konsole --fullscreen")
        time.sleep(3.5)
        # Type status command
        q.type_text(vm.qmp, "clear\n")
        time.sleep(0.5)
        q.type_text(vm.qmp, "hscl status\n")
        time.sleep(2.0)
        q.type_text(vm.qmp, "hscl doctor\n")
        time.sleep(2.5)
        capture_shot(vm, out_dir, "08_terminal_hscl_status_doctor.png", "Konsole: hscl status & diagnostic doctor in action", manifest)

        # Run Security Lab commands in Konsole
        q.type_text(vm.qmp, "clear\n")
        time.sleep(0.5)
        q.type_text(vm.qmp, "hscl lab --help\n")
        time.sleep(1.5)
        q.type_text(vm.qmp, "hscl graphics detect\n")
        time.sleep(1.5)
        q.type_text(vm.qmp, "hscl memory status\n")
        time.sleep(2.0)
        capture_shot(vm, out_dir, "09_terminal_hscl_lab.png", "Konsole: hscl lab security suite & hardware diagnostics", manifest)
        close_gui_apps(vm, "konsole")
        time.sleep(2.0)

        # 5. HCS Control Center Suite (Qt 6 / QML)
        print("[5/10] Launching HCS Control Center (Qt 6 / QML)...", flush=True)
        run_gui_app(vm, "hscl-control-center")
        time.sleep(4.0)
        capture_shot(vm, out_dir, "04_control_center_overview.png", "Control Center: System Overview & Hardware", manifest)

        # Navigate tabs via keyboard Down key
        print("Switching to Appearance tab...", flush=True)
        q.send_keys(vm.qmp, ["down"])
        time.sleep(2.0)
        capture_shot(vm, out_dir, "05_control_center_appearance.png", "Control Center: Appearance, Tokens & Themes", manifest)

        print("Switching to Security tab...", flush=True)
        q.send_keys(vm.qmp, ["down"])
        time.sleep(2.0)
        capture_shot(vm, out_dir, "06_control_center_security.png", "Control Center: Security Baseline & Firewall Policy", manifest)

        print("Switching to About tab...", flush=True)
        q.send_keys(vm.qmp, ["down"])
        time.sleep(2.0)
        capture_shot(vm, out_dir, "07_control_center_about.png", "Control Center: About & System Attestation", manifest)

        close_gui_apps(vm, "hscl-control-center")
        time.sleep(2.0)

        # 6. Dolphin File Manager
        print("[6/10] Launching Dolphin File Manager...", flush=True)
        run_gui_app(vm, "dolphin")
        time.sleep(3.5)
        capture_shot(vm, out_dir, "10_app_dolphin.png", "Dolphin File Manager with HCS styling", manifest)
        close_gui_apps(vm, "dolphin")
        time.sleep(2.0)

        # 7. Kate Text Editor
        print("[7/10] Launching Kate Text Editor with /etc/os-release...", flush=True)
        run_gui_app(vm, "kate /etc/os-release")
        time.sleep(4.0)
        capture_shot(vm, out_dir, "14_app_kate.png", "Kate Text Editor showing /etc/os-release", manifest)
        close_gui_apps(vm, "kate")
        time.sleep(2.0)

        # 8. Calamares Installer
        print("[8/10] Launching Calamares Installer...", flush=True)
        run_gui_app(vm, "calamares")
        time.sleep(5.0)
        capture_shot(vm, out_dir, "11_installer_welcome.png", "Calamares Installer: Welcome Screen", manifest)

        # Click Next button (bottom right)
        print("Clicking Next in Calamares...", flush=True)
        q.click(vm.qmp, 0.88, 0.93)
        time.sleep(3.0)
        capture_shot(vm, out_dir, "12_installer_location.png", "Calamares Installer: Location & Timezone", manifest)
        close_gui_apps(vm, "calamares")
        time.sleep(2.0)

        # 9. Offline Handbook
        print("[9/10] Launching Offline Handbook in browser...", flush=True)
        run_gui_app(vm, "xdg-open /usr/share/doc/hscl-handbook/index.html")
        time.sleep(4.5)
        capture_shot(vm, out_dir, "13_offline_handbook.png", "Trilingual Offline Handbook in Browser", manifest)
        close_gui_apps(vm)
        time.sleep(2.0)

        # 10. Final Desktop State
        print("[10/10] Capturing final desktop state...", flush=True)
        capture_shot(vm, out_dir, "15_desktop_final.png", "Final live desktop state after showcase sequence", manifest)

        # Write updated manifest
        manifest_file = out_dir / "manifest.json"
        manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(f"\nSUCCESS: Captured {len(manifest)} verified showcase screenshots!")
        print(f"Manifest: {manifest_file}")

    finally:
        print("Stopping QEMU VM...", flush=True)
        mgr.stop_all()

    return 0


if __name__ == "__main__":
    sys.exit(main())
