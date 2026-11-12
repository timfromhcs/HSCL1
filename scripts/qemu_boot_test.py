#!/usr/bin/env python3
"""Boot an HSCL1 ISO in QEMU, take periodic screenshots over QMP and report evidence.

Evidence produced in OUTDIR: screenshots (PNG), qemu.log, result.json.
Success heuristic: the screen matches a render of the HSCL1 Midnight wallpaper (desktop reached with the
HSCL1 default wallpaper); the Kubuntu welcome screen is detected separately and never counts as success. Screenshots must still be reviewed by a human/agent; this is a smoke gate,
not proof of usability.

Disposable resources only: a read-only ISO and an optional throwaway qcow2 created inside OUTDIR.
"""
import argparse, json, os, shutil, socket, struct, subprocess, sys, time, zlib
from pathlib import Path

OVMF = "/usr/share/OVMF"


def ppm_to_png(ppm: bytes):
    """Convert a binary P6 PPM to (png_bytes, width, height, rgb_bytes)."""
    parts = ppm.split(b"\n", 3)
    assert parts[0] == b"P6", "unexpected screendump format"
    w, h = map(int, parts[1].split())
    data = parts[3]
    raw = b"".join(b"\x00" + data[y * w * 3:(y + 1) * w * 3] for y in range(h))

    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))
    return png, w, h, data


def wallpaper_reference(w: int, h: int) -> bytes:
    """Render the HSCL1 Midnight wallpaper at the screen size (same code as the packaged wallpaper)."""
    import importlib.util, io
    spec = importlib.util.spec_from_file_location("genwp", Path(__file__).with_name("gen-wallpaper.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    tok = json.loads((Path(__file__).resolve().parent.parent / "themes/tokens/tokens.json").read_text(encoding="utf-8"))["themes"]["hcs-midnight"]
    png = mod.render(w, h, tok)
    # decode our own PNG (filter 0, RGB8) back to raw RGB
    idat = b""
    pos = 8
    while pos < len(png):
        ln = struct.unpack(">I", png[pos:pos + 4])[0]
        typ = png[pos + 4:pos + 8]
        if typ == b"IDAT":
            idat += png[pos + 8:pos + 8 + ln]
        pos += 12 + ln
    raw = zlib.decompress(idat)
    stride = w * 3 + 1
    return b"".join(raw[y * stride + 1:(y + 1) * stride] for y in range(h))


def wallpaper_similarity(rgb: bytes, ref: bytes, w: int, h: int) -> float:
    """1.0 = screen region matches the wallpaper; compares sampled pixels outside the bottom panel/top bar.
    Desktop icons/widgets cover only a few pixels, so a median-ish tolerant fraction is used."""
    ok = tot = 0
    for y in range(60, h - 70, 9):
        for x in range(0, w, 9):
            i = (y * w + x) * 3
            d = abs(rgb[i] - ref[i]) + abs(rgb[i + 1] - ref[i + 1]) + abs(rgb[i + 2] - ref[i + 2])
            tot += 1
            ok += d <= 40
    return ok / max(tot, 1)


def looks_like_desktop(rgb: bytes, w: int, h: int) -> bool:
    """Plasma desktop with the HCS top bar: a dark band at the top with a few bright pixels (clock, tray icons) and a
    non-black screen. Independent of the (animated) wallpaper."""
    band_h = max(8, int(h * 0.04))
    total = bright = dark = 0
    for y in range(2, band_h, 2):
        for x in range(0, w, 2):
            i = (y * w + x) * 3
            lum = (rgb[i] + rgb[i + 1] + rgb[i + 2]) // 3
            total += 1
            bright += lum > 170
            dark += lum < 60
    mid_lum = sum(rgb[(h // 2 * w + x) * 3] for x in range(0, w, 16)) / max(1, len(range(0, w, 16)))
    return total > 0 and dark / total > 0.6 and bright >= 25 and mid_lum > 3


def looks_like_welcome(rgb: bytes, w: int, h: int) -> bool:
    """Kubuntu live welcome: dark-blue full screen with a bright centre logo. Used only to click 'Try'."""
    hits = tot = 0
    for y in range(0, h, 11):
        for x in range(0, w, 11):
            i = (y * w + x) * 3
            tot += 1
            hits += rgb[i + 2] > rgb[i] + 6 and rgb[i + 2] < 140
    return hits / max(tot, 1) > 0.8


def free_memory_mb() -> int:
    """Physical memory available to start a VM, in MB (Windows: GlobalMemoryStatusEx, Linux: /proc/meminfo)."""
    if os.name == "nt":
        import ctypes

        class MS(ctypes.Structure):
            _fields_ = [("l", ctypes.c_ulong), ("load", ctypes.c_ulong), ("tp", ctypes.c_ulonglong), ("ap", ctypes.c_ulonglong),
                        ("tpf", ctypes.c_ulonglong), ("apf", ctypes.c_ulonglong), ("tv", ctypes.c_ulonglong), ("av", ctypes.c_ulonglong),
                        ("ae", ctypes.c_ulonglong)]
        m = MS()
        m.l = ctypes.sizeof(MS)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        return int(m.ap // (1024 * 1024))
    for line in open("/proc/meminfo"):
        if line.startswith("MemAvailable"):
            return int(line.split()[1]) // 1024
    return 1 << 30


def click(qmp, fx: float, fy: float) -> None:
    """Left-click at fractional screen coordinates (usb-tablet absolute axes 0..32767)."""
    qmp.cmd("input-send-event", events=[
        {"type": "abs", "data": {"axis": "x", "value": int(fx * 32767)}},
        {"type": "abs", "data": {"axis": "y", "value": int(fy * 32767)}}])
    time.sleep(0.4)
    for down in (True, False):
        qmp.cmd("input-send-event", events=[{"type": "btn", "data": {"button": "left", "down": down}}])
        time.sleep(0.15)


def double_click(qmp, fx: float, fy: float) -> None:
    qmp.cmd("input-send-event", events=[
        {"type": "abs", "data": {"axis": "x", "value": int(fx * 32767)}},
        {"type": "abs", "data": {"axis": "y", "value": int(fy * 32767)}}])
    time.sleep(0.5)
    for down in (True, False, True, False):  # two clicks well inside the double-click interval
        qmp.cmd("input-send-event", events=[{"type": "btn", "data": {"button": "left", "down": down}}])
        time.sleep(0.05)


QCODES = {" ": "spc", "-": "minus", ".": "dot", ",": "comma", "/": "slash", "\n": "ret", "\t": "tab",
          ";": "semicolon", "'": "apostrophe", "=": "equal", "\\": "backslash", "[": "bracket_left", "]": "bracket_right", "`": "grave_accent"}
# US layout: characters typed with Shift held, mapped to the unshifted key (older versions dropped ; | : and friends silently)
SHIFTED = {"|": "backslash", ":": "semicolon", '"': "apostrophe", "_": "minus", "+": "equal", "?": "slash", "<": "comma", ">": "dot",
           "{": "bracket_left", "}": "bracket_right", "~": "grave_accent", "!": "1", "@": "2", "#": "3", "$": "4", "%": "5", "^": "6",
           "&": "7", "*": "8", "(": "9", ")": "0"}


def send_keys(qmp, keys) -> None:
    """Press and release a chord such as ["alt", "f2"] or ["meta_l", "k"] (QEMU qcodes)."""
    qmp.cmd("send-key", keys=[{"type": "qcode", "data": k} for k in keys], **{"hold-time": 80})
    time.sleep(0.3)


def type_text(qmp, text: str) -> None:
    for ch in text:
        if ch.isupper():
            send_keys(qmp, ["shift", ch.lower()])
        elif ch in SHIFTED:
            send_keys(qmp, ["shift", SHIFTED[ch]])
        else:
            send_keys(qmp, [QCODES.get(ch, ch)])


def run_steps(qmp, out: Path, steps: list, ref, result: dict, proc=None) -> None:
    """Scenario steps: {"wait": s} {"keys": [..]} {"type": "text"} {"click": [fx, fy]} {"dclick": [fx, fy]} {"shot": "name"}."""
    shots = result.setdefault("scenario_shots", [])
    result["_disk"] = result.get("_disk", "")
    for st in steps:
        if "wait" in st:
            end, sign = time.time() + float(st["wait"]), 1
            while time.time() < end:  # keep the guest awake: a tiny mouse move every few seconds
                time.sleep(min(8.0, max(0.0, end - time.time())))
                qmp.cmd("input-send-event", events=[{"type": "rel", "data": {"axis": "x", "value": sign}}])
                sign = -sign
        elif "wait_disk_idle" in st:
            cfg = st["wait_disk_idle"]  # {"idle": seconds without writes, "max": seconds}
            disk = Path(result["_disk"])
            t_end, last, last_change = time.time() + float(cfg.get("max", 2400)), None, time.time()
            sign = 1
            while time.time() < t_end:
                time.sleep(8)
                qmp.cmd("input-send-event", events=[{"type": "rel", "data": {"axis": "x", "value": sign}}])
                sign = -sign
                cur = (disk.stat().st_size, disk.stat().st_mtime)
                if cur != last:
                    last, last_change = cur, time.time()
                elif time.time() - last_change >= float(cfg.get("idle", 120)):
                    break
            result["disk_idle_after_s"] = round(time.time() - last_change)
            print("disk idle for", result["disk_idle_after_s"], "s", flush=True)
        elif "keys" in st:
            send_keys(qmp, st["keys"])
        elif "type" in st:
            type_text(qmp, st["type"])
        elif "click" in st:
            click(qmp, *st["click"])
        elif "dclick" in st:
            double_click(qmp, *st["dclick"])
        elif "wait_exit" in st:  # wait for the VM to power off by itself (e.g. after the installer's "Restart")
            t_end = time.time() + float(st["wait_exit"])
            while proc is not None and proc.poll() is None and time.time() < t_end:
                time.sleep(2)
            result["vm_exited"] = proc is not None and proc.poll() is not None
            print("vm exited:", result["vm_exited"], flush=True)
            if result["vm_exited"]:
                return
        elif "shot" in st:
            g = grab(qmp, out, st["shot"])
            shots.append(st["shot"] if g else st["shot"] + " (failed)")
            print("scenario shot:", st["shot"], flush=True)
        else:
            raise ValueError(f"unknown scenario step: {st}")


def grab(qmp, out: Path, name: str):
    ppm = out / (name + ".ppm")
    r = qmp.cmd("screendump", filename=str(ppm))
    if "error" in r or not ppm.exists():
        return None
    png, w, h, rgb = ppm_to_png(ppm.read_bytes())
    ppm.unlink()
    (out / (name + ".png")).write_bytes(png)
    return w, h, rgb


class Qmp:
    def __init__(self, path: str):
        # "tcp:HOST:PORT" (Windows QEMU) or a unix socket path
        tcp = path.startswith("tcp:")
        for _ in range(150):
            try:
                if tcp:
                    host, port = path[4:].rsplit(":", 1)
                    self.s = socket.create_connection((host, int(port)), timeout=60)
                else:
                    self.s = socket.socket(socket.AF_UNIX)
                    self.s.connect(path)
                break
            except OSError:
                time.sleep(0.2)
        else:
            raise RuntimeError("QMP socket never appeared")
        self.f = self.s.makefile("rw")
        self.f.readline()
        self.cmd("qmp_capabilities")

    def cmd(self, name, **args):
        self.f.write(json.dumps({"execute": name, "arguments": args}) + "\n")
        self.f.flush()
        while True:
            line = json.loads(self.f.readline())
            if "return" in line or "error" in line:
                return line


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("iso")
    ap.add_argument("outdir")
    ap.add_argument("--firmware", choices=["uefi", "bios"], default="uefi")
    ap.add_argument("--secure-boot", action="store_true", help="UEFI Secure Boot with Microsoft keys enrolled (OVMF ms variant)")
    ap.add_argument("--try-live", action="store_true", help="click 'Try' on the live welcome screen once")
    ap.add_argument("--dismiss-welcome", action="store_true", help="after the desktop is reached, click Skip on the Plasma Welcome Center and capture desktop-final.png")
    ap.add_argument("--launch-installer", action="store_true", help="after --dismiss-welcome, double-click the Install icon and capture installer-*.png (no disk is attached; nothing is written)")
    ap.add_argument("--qa-out", help="attach a virtio port hscl.qa and write the guest report (hscl-qa package) to this file")
    ap.add_argument("--steps", help="JSON scenario file run after the desktop is reached (see tests/visual/scenarios)")
    ap.add_argument("--disk", help="attach this qcow2 as the only virtio disk (created when missing; disposable test disks only)")
    ap.add_argument("--disk-size", default="40G", help="size for a newly created --disk")
    ap.add_argument("--login-password", help="installed-system boot: after --boot-wait seconds type this password at the login screen (single user preselected)")
    ap.add_argument("--boot-wait", type=int, default=75)
    ap.add_argument("--unlock-passphrase", help="encrypted install: type this LUKS passphrase at the boot prompt (screenshots before and after)")
    ap.add_argument("--unlock-first-wrong", help="type this WRONG passphrase first and capture the rejection before the correct one")
    ap.add_argument("--unlock-at", type=int, default=50, help="seconds after start until the passphrase prompt is expected")
    ap.add_argument("--no-mem-guard", action="store_true", help="start even when free memory is low (not recommended)")
    ap.add_argument("--accel", help="override accelerator (kvm|whpx|tcg)")
    ap.add_argument("--qmp-port", type=int, default=0,
                    help="QMP TCP port (Windows QEMU only); 0 picks a free port so two harness runs "
                         "(or another agent's VM) never collide on 4444")
    ap.add_argument("--mem", type=int, default=4096)
    ap.add_argument("--smp", type=int, default=4)
    ap.add_argument("--timeout", type=int, default=2400)
    ap.add_argument("--interval", type=int, default=45)
    ap.add_argument("--width", type=int, default=1366)
    ap.add_argument("--height", type=int, default=768)
    a = ap.parse_args()

    need = a.mem + 1500
    have = free_memory_mb()
    if not a.no_mem_guard and have < need:
        print(f"refusing to start: {have} MB free, need {need} MB (VM {a.mem} MB + 1.5 GB headroom). "
              "Close apps or run 'wsl --shutdown'; --no-mem-guard overrides.")
        return 3
    out = Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)
    win = os.name == "nt"
    kvm = (not win) and os.access("/dev/kvm", os.W_OK)
    if win:
        qdir = Path(os.environ.get("QEMU_DIR", r"C:\Program Files\qemu"))
        qemu_bin = str(qdir / "qemu-system-x86_64.exe")
        accel = a.accel or "whpx,kernel-irqchip=off"
        cpu = "qemu64,+ssse3,+sse4.1,+sse4.2,+popcnt,+avx2" if accel.startswith("whpx") else "max"
        if a.qmp_port <= 0:
            # Ask the OS for a free port instead of assuming 4444. Two harness runs (or another
            # agent's VM on the same host) raced for 4444 on 2026-11-10; QEMU then died with
            # "Failed to find an available port" and the QMP client timed out.
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                probe.bind(("127.0.0.1", 0))
                a.qmp_port = probe.getsockname()[1]
        qmp_arg = "tcp:127.0.0.1:%d,server=on,wait=off" % a.qmp_port
        qmp_path = "tcp:127.0.0.1:%d" % a.qmp_port
    else:
        qemu_bin = "qemu-system-x86_64"
        accel = a.accel or ("kvm" if kvm else "tcg,thread=multi")
        cpu = "host" if kvm else "max"
        qmp_arg = f"unix:{out}/qmp.sock,server=on,wait=off"
        qmp_path = str(out / "qmp.sock")
    machine = "q35,smm=on" if a.secure_boot else "q35"
    cmd = [qemu_bin, "-machine", machine, "-accel", accel, "-cpu", cpu,
           "-m", str(a.mem), "-smp", str(a.smp), "-display", "none", "-vga", "std",
           "-device", "usb-ehci", "-device", "usb-kbd", "-device", "usb-tablet",
           "-audiodev", "none,id=a0", "-device", "intel-hda", "-device", "hda-duplex,audiodev=a0",
           "-netdev", "user,id=n0", "-device", "virtio-net-pci,netdev=n0",
           *([] if a.iso == "none" else ["-drive", f"file={a.iso},media=cdrom,readonly=on"]),
           "-boot", "c" if a.iso == "none" else "d", "-qmp", qmp_arg, "-no-reboot"]
    if a.disk:
        disk = Path(a.disk)
        if not disk.exists():
            img = str(qdir / "qemu-img.exe") if win else "qemu-img"
            subprocess.run([img, "create", "-f", "qcow2", str(disk), a.disk_size], check=True, capture_output=True)
        if disk.suffix != ".qcow2":
            raise SystemExit("--disk must be a .qcow2 file (disposable test disks only)")
        cmd += ["-drive", f"file={disk},if=virtio,format=qcow2"]
    if a.qa_out:
        qa_path = str(Path(a.qa_out).resolve()).replace("\\", "/")
        cmd += ["-device", "virtio-serial-pci", "-chardev", f"file,id=qa,path={qa_path}",
                "-device", "virtserialport,chardev=qa,name=hscl.qa"]
    if a.firmware == "uefi":
        vars_copy = out / "OVMF_VARS.fd"
        if win:
            code = str(qdir / "share" / ("edk2-x86_64-secure-code.fd" if a.secure_boot else "edk2-x86_64-code.fd"))
            vars_src = str(qdir / "share" / "edk2-i386-vars.fd")
            if a.secure_boot:
                # Secure Boot only proves anything when the firmware carries the Microsoft key database. QEMU for
                # Windows ships only the empty variables template, so a plain --secure-boot run there boots a
                # firmware that has the SecureBoot variable but an empty db/KEK: nothing is validated, the shim is
                # accepted because there is no policy, and the run would prove nothing while looking green.
                # Point HSCL_OVMF_VARS_MS at an enrolled template (Ubuntu: /usr/share/OVMF/OVMF_VARS_4M.ms.fd).
                ms_vars = os.environ.get("HSCL_OVMF_VARS_MS")
                if ms_vars and Path(ms_vars).is_file():
                    vars_src = ms_vars
                    print(f"secure boot: using enrolled key database from {ms_vars}", flush=True)
                else:
                    print("warning: --secure-boot without HSCL_OVMF_VARS_MS - the firmware key database is empty, "
                          "so this run does NOT prove that the signed boot chain is accepted", flush=True)
                cmd += ["-global", "driver=cfi.pflash01,property=secure,value=on"]
        elif a.secure_boot:
            code, vars_src = f"{OVMF}/OVMF_CODE_4M.secboot.fd", f"{OVMF}/OVMF_VARS_4M.ms.fd"
            cmd += ["-global", "driver=cfi.pflash01,property=secure,value=on"]
        else:
            code, vars_src = f"{OVMF}/OVMF_CODE_4M.fd", f"{OVMF}/OVMF_VARS_4M.fd"
        shutil.copy(vars_src, vars_copy)
        cmd += ["-drive", f"if=pflash,format=raw,readonly=on,file={code}",
                "-drive", f"if=pflash,format=raw,file={vars_copy}"]
    log = open(out / "qemu.log", "wb")
    t0 = time.time()
    proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)
    result = {"_disk": a.disk or "", "firmware": a.firmware, "secure_boot_requested": a.secure_boot, "accel": accel, "iso": os.path.basename(a.iso), "shots": [], "reached_desktop": False}
    try:
        qmp = Qmp(qmp_path)
        if a.unlock_passphrase:
            # encrypted installed system: the initramfs asks for the LUKS passphrase before the login screen exists
            time.sleep(a.unlock_at)
            grab(qmp, out, "unlock-prompt")
            if a.unlock_first_wrong:
                type_text(qmp, a.unlock_first_wrong)
                send_keys(qmp, ["ret"])
                time.sleep(12)
                grab(qmp, out, "unlock-after-wrong")
            type_text(qmp, a.unlock_passphrase)
            send_keys(qmp, ["ret"])
            print("typed the unlock passphrase", flush=True)
            time.sleep(8)
            grab(qmp, out, "unlock-after-correct")
        if a.login_password:
            # wait until the screen is no longer black (login screen drawn), then let the greeter settle
            t_login = time.time() + max(a.boot_wait, 300)
            while time.time() < t_login:
                time.sleep(10)
                g = grab(qmp, out, "login-screen")
                if g and sum(g[2][::997]) / max(1, len(g[2][::997])) > 25:
                    break
            time.sleep(12)
            grab(qmp, out, "login-screen")
            type_text(qmp, a.login_password)
            send_keys(qmp, ["ret"])
            print("typed password at the login screen", flush=True)
        streak, n, ref, ref_size, clicked = 0, 0, None, None, False
        while time.time() - t0 < a.timeout and proc.poll() is None:
            time.sleep(a.interval)
            n += 1
            ppm = out / f"shot-{n:03d}.ppm"
            r = qmp.cmd("screendump", filename=str(ppm))
            if "error" in r or not ppm.exists():
                continue
            png, w, h, rgb = ppm_to_png(ppm.read_bytes())
            ppm.unlink()
            (out / f"shot-{n:03d}.png").write_bytes(png)
            if ref is None or ref_size != (w, h):  # firmware/boot stages switch resolution
                ref, ref_size = wallpaper_reference(w, h), (w, h)
            frac = wallpaper_similarity(rgb, ref, w, h)
            welcome = looks_like_welcome(rgb, w, h)
            if a.try_live and welcome and not clicked and frac < 0.5:
                # absolute tablet coordinates 0..32767; 'Try' button centre is about (27%, 80%)
                qmp.cmd("input-send-event", events=[
                    {"type": "abs", "data": {"axis": "x", "value": int(0.27 * 32767)}},
                    {"type": "abs", "data": {"axis": "y", "value": int(0.80 * 32767)}}])
                time.sleep(0.5)
                for down in (True, False):
                    qmp.cmd("input-send-event", events=[{"type": "btn", "data": {"button": "left", "down": down}}])
                    time.sleep(0.2)
                clicked = True
                print("clicked 'Try' on welcome screen", flush=True)
            result["shots"].append({"n": n, "t": round(time.time() - t0), "wallpaper_match": round(frac, 3), "welcome_screen": welcome, "size": [w, h]})
            print(f"[{round(time.time() - t0):5d}s] shot-{n:03d} {w}x{h} wallpaper_match={frac:.2f} welcome={welcome}", flush=True)
            streak = streak + 1 if (frac > 0.4 or looks_like_desktop(rgb, w, h)) else 0
            qmp.cmd("input-send-event", events=[{"type": "rel", "data": {"axis": "x", "value": 1}}])  # keep the session awake (no dimming)
            if streak >= 2:
                result["reached_desktop"] = True
                if a.dismiss_welcome:
                    click(qmp, 0.288, 0.848)  # "Skip" button of the Welcome Center
                    time.sleep(4)
                    g = grab(qmp, out, "desktop-final")
                    if g:
                        result["desktop_final_wallpaper_match"] = round(wallpaper_similarity(g[2], ref, g[0], g[1]), 3)
                        print("desktop-final wallpaper_match=%.2f" % result["desktop_final_wallpaper_match"], flush=True)
                if a.steps:
                    run_steps(qmp, out, json.loads(Path(a.steps).read_text(encoding="utf-8")), ref, result, proc)
                if a.launch_installer:
                    double_click(qmp, 0.135, 0.05)  # "Install ..." desktop icon
                    for k in range(1, 7):
                        time.sleep(20)
                        grab(qmp, out, f"installer-{k}")
                    result["installer_shots"] = 6
                break
    finally:
        try:
            qmp.cmd("quit")
        except Exception:
            pass
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
        result["elapsed_s"] = round(time.time() - t0)
        result.pop("_disk", None)
        (out / "result.json").write_text(json.dumps(result, indent=2))
        # A dead guest is easy to miss: screenshots simply stop changing. Check for the panic colour so a
        # crashed run is called a crash in the summary, not a quiet success.
        suspects = panic_suspects(out)
        if suspects:
            result["panic_suspects"] = suspects
            (out / "result.json").write_text(json.dumps(result, indent=2))
            print(f"WARNING: {len(suspects)} screenshot(s) look like a kernel panic: {suspects}", flush=True)
    print(json.dumps({k: v for k, v in result.items() if k != "shots"}))
    return 0 if result["reached_desktop"] else 1


def panic_suspects(out: Path) -> list[str]:
    """Run the standalone detector on `out`; returns [] when it is missing or finds nothing."""
    detector = Path(__file__).resolve().parent / "dev" / "detect_panic.py"
    if not detector.is_file():
        return []
    try:
        r = subprocess.run(
            [sys.executable, str(detector), str(out)],
            capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
        )
    except OSError:
        return []
    return [line.split("PANIC-LIKE:", 1)[1].strip() for line in r.stdout.splitlines() if line.startswith("PANIC-LIKE:")]


if __name__ == "__main__":
    sys.exit(main())
