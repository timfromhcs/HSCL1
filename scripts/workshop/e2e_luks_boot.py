#!/usr/bin/env python3
"""Boot an INSTALLED, LUKS2-encrypted disk (no ISO): unlock at the boot prompt (wrong passphrase first), log in, then check inside the guest.

Usage: e2e_luks_boot.py DISK.qcow2 OUTDIR PASSPHRASE LOGIN_PASSWORD [WRONG_PASSPHRASE]
Writes OUTDIR/luks-boot.json (every check with exit code and output, plus the secret-scan result) and screenshots of each stage.
Disposable test disks only. The passphrase is a unique marker so that a leak into logs can be found by grep.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import e2e_cli  # noqa: E402  (the standard in-guest check set)
import e2e_respin as base  # noqa: E402
import vm as vmmod  # noqa: E402

CHECKS = {
    "lsblk": "lsblk -f -o NAME,FSTYPE,LABEL,MOUNTPOINTS",
    "findmnt": "findmnt -n -o TARGET,SOURCE,FSTYPE,OPTIONS / /boot /boot/efi",
    "luks_dump": "for d in $(blkid -t TYPE=crypto_LUKS -o device); do echo \"== $d\"; cryptsetup luksDump $d | grep -E 'Version|Cipher|PBKDF|Key Slot|Keyslots|^  [0-9]+:|Digests'; done",
    "crypttab": "cat /etc/crypttab",
    "initrd_keyfile_gate": "n=0; for f in /boot/initrd.img-*; do echo \"== $f\"; lsinitramfs $f | grep -i -E 'keyfile|cryptroot|crypttab'; n=$((n+1)); done; echo \"initrds=$n\"; echo '== keyfile hits (must be empty):'; for f in /boot/initrd.img-*; do lsinitramfs $f | grep -i keyfile; done",
    "keyfile_in_root": "ls -l /crypto_keyfile.bin 2>&1; stat -c '%a %U' /crypto_keyfile.bin 2>&1",
    "boot_has_no_keyfile": "ls -la /boot | head -20; find /boot -iname '*keyfile*' 2>/dev/null; echo 'find done'",
    "swap": "swapon --show; cat /proc/swaps",
    "secret_scan": "grep -r -a -l 'luks-marker-4711' /var/log /var/lib /etc /root /home /boot /tmp 2>/dev/null | head -20; echo 'scan done'",
    "journal_secret": "journalctl -b --no-pager 2>/dev/null | grep -c 'luks-marker-4711'; true",
    "system_tree_owner": "stat -c '%u:%g %a %n' / /etc /usr /var /boot /home; ufw status | head -2",
    "os_release": "grep -E '^(NAME|VERSION|HSCL1_VERSION)=' /usr/lib/os-release",
    "installed_not_live": "cat /proc/cmdline | cut -c1-200; test -e /cdrom/casper && echo LIVE || echo INSTALLED",
}



def png_pixel(png: bytes, fx: float, fy: float) -> tuple[int, int, int]:
    """Pixel at a fractional position of an 8-bit RGB/RGBA PNG (standard library only; all five filter types)."""
    import struct
    import zlib

    assert png[:8] == bytes([137, 80, 78, 71, 13, 10, 26, 10]), "not a PNG"
    pos, idat, w = 8, b"", 0
    h = ct = 0
    while pos < len(png):
        n, typ = struct.unpack(">I4s", png[pos:pos + 8])
        body = png[pos + 8:pos + 8 + n]
        if typ == b"IHDR":
            w, h, depth, ct = struct.unpack(">IIBB", body[:10])
            assert depth == 8 and ct in (2, 6), "unsupported PNG format"
        elif typ == b"IDAT":
            idat += body
        pos += 12 + n
    bpp = 3 if ct == 2 else 4
    raw = zlib.decompress(idat)
    stride = w * bpp
    prev = bytearray(stride)
    rows = []
    for y in range(h):
        f = raw[y * (stride + 1)]
        cur = bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        for i in range(stride):
            a_ = cur[i - bpp] if i >= bpp else 0
            b_ = prev[i]
            c_ = prev[i - bpp] if i >= bpp else 0
            if f == 1:
                cur[i] = (cur[i] + a_) & 255
            elif f == 2:
                cur[i] = (cur[i] + b_) & 255
            elif f == 3:
                cur[i] = (cur[i] + ((a_ + b_) >> 1)) & 255
            elif f == 4:
                pa, pb, pc = abs(b_ - c_), abs(a_ - c_), abs(a_ + b_ - 2 * c_)
                pr = a_ if pa <= pb and pa <= pc else (b_ if pb <= pc else c_)
                cur[i] = (cur[i] + pr) & 255
        rows.append(cur)
        prev = cur
    x, y = min(w - 1, int(w * fx)), min(h - 1, int(h * fy))
    o = x * bpp
    return rows[y][o], rows[y][o + 1], rows[y][o + 2]


def _unlock_field_visible(png: bytes) -> bool:
    """True when the Plymouth passphrase field (dark-grey box, centre, ~70% down) is on screen."""
    r, g, b = png_pixel(png, 0.5, 0.70)
    return 40 <= r <= 80 and 40 <= g <= 80 and 40 <= b <= 80


def main() -> int:
    disk, out, passphrase, login_pw = sys.argv[1], Path(sys.argv[2]), sys.argv[3], sys.argv[4]
    wrong = sys.argv[5] if len(sys.argv) > 5 else None
    extra = json.loads(Path(sys.argv[6]).read_text(encoding="utf-8")) if len(sys.argv) > 6 else {}
    only_extra = len(sys.argv) > 7 and sys.argv[7] == "--only-extra"
    out.mkdir(parents=True, exist_ok=True)
    report: dict = {"disk": Path(disk).name, "stages": [], "checks": {}}
    mgr = vmmod.VmManager(out / "vm")
    vm = mgr.start("luks", None, disk, 4096, "uefi")
    t0 = time.time()

    def shot(name: str) -> None:
        try:
            (out / f"{name}.png").write_bytes(vm.screenshot_png())
        except Exception as e:  # noqa: BLE001
            report["stages"].append({"shot": name, "error": str(e)})
        else:
            report["stages"].append({"shot": name, "t": round(time.time() - t0)})

    try:
        time.sleep(75)  # firmware + GRUB + initramfs; the prompt ignores keystrokes typed before it is ready
        shot("1-unlock-prompt")
        if wrong:
            vm.type(wrong + chr(10))
            time.sleep(14)
            shot("2-after-wrong-passphrase")
        for attempt in range(3):  # retype only if the unlock field is still showing (keystrokes can be lost while it initialises)
            vm.type(passphrase + chr(10))
            time.sleep(20)
            if not _unlock_field_visible(vm.screenshot_png()):
                break
            report["stages"].append({"unlock_retry": attempt + 1})
        shot("3-after-correct-passphrase")
        # wait for the login screen (screen no longer dark), then log in
        end = time.time() + 600
        while time.time() < end:
            time.sleep(10)
            png = vm.screenshot_png()
            if len(png) > 60000:  # a drawn login screen compresses far larger than the dark boot stages
                break
        time.sleep(15)
        shot("4-login-screen")
        vm.type(login_pw + chr(10))
        report["desktop_after_s"] = base.wait_desktop(vm)
        shot("5-desktop")
        report["status"] = vm.rpc("status", timeout=240)
        for name, cmd in {**({} if only_extra else CHECKS), **extra}.items():
            try:
                r = base.hook(vm, f"luks-{name.replace('_', '-')}.sh", f"({cmd}) 2>&1 | head -c 6000; echo; echo \"__exit=$?\"" + chr(10), timeout=180)
                report["checks"][name] = {"hook_exit": r["exit"], "output": r["stdout"][-3500:]}
            except Exception as e:  # noqa: BLE001
                report["checks"][name] = {"error": f"{type(e).__name__}: {e}"}
        # the standard 23 in-guest checks on the installed system
        report["standard_checks"] = {}
        user = (report["status"] or {}).get("session_user") or "kubuntu"
        report["session_user"] = user
        for name, cmd in ({} if only_extra else {k: v.replace("{USER}", user) for k, v in e2e_cli.CHECKS.items()}).items():
            try:
                r = base.hook(vm, f"std-{name.replace('_', '-')}.sh", f"({cmd}) 2>&1 | head -c 6000; echo; echo \"__exit=$?\"" + chr(10), timeout=180)
                report["standard_checks"][name] = {"hook_exit": r["exit"], "output": r["stdout"][-2500:]}
            except Exception as e:  # noqa: BLE001
                report["standard_checks"][name] = {"error": f"{type(e).__name__}: {e}"}
    finally:
        (out / "luks-boot.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
        mgr.stop_all()
    bad = [k for k, v in {**report["checks"], **report.get("standard_checks", {})}.items() if "error" in v]
    print(json.dumps({"desktop_after_s": report.get("desktop_after_s"), "errors": bad}))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
