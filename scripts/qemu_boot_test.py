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


def looks_like_welcome(rgb: bytes, w: int, h: int) -> bool:
    """Kubuntu live welcome: dark-blue full screen with a bright centre logo. Used only to click 'Try'."""
    hits = tot = 0
    for y in range(0, h, 11):
        for x in range(0, w, 11):
            i = (y * w + x) * 3
            tot += 1
            hits += rgb[i + 2] > rgb[i] + 6 and rgb[i + 2] < 140
    return hits / max(tot, 1) > 0.8


class Qmp:
    def __init__(self, path: str):
        self.s = socket.socket(socket.AF_UNIX)
        for _ in range(100):
            try:
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
    ap.add_argument("--mem", type=int, default=4096)
    ap.add_argument("--smp", type=int, default=4)
    ap.add_argument("--timeout", type=int, default=2400)
    ap.add_argument("--interval", type=int, default=45)
    ap.add_argument("--width", type=int, default=1366)
    ap.add_argument("--height", type=int, default=768)
    a = ap.parse_args()

    out = Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)
    kvm = os.access("/dev/kvm", os.W_OK)
    accel = "kvm" if kvm else "tcg,thread=multi"
    machine = "q35,smm=on" if a.secure_boot else "q35"
    cmd = ["qemu-system-x86_64", "-machine", machine, "-accel", accel, "-cpu", "host" if kvm else "max",
           "-m", str(a.mem), "-smp", str(a.smp), "-display", "none", "-vga", "std",
           "-device", "usb-ehci", "-device", "usb-kbd", "-device", "usb-tablet",
           "-audiodev", "none,id=a0", "-device", "intel-hda", "-device", "hda-duplex,audiodev=a0",
           "-netdev", "user,id=n0", "-device", "virtio-net-pci,netdev=n0",
           "-drive", f"file={a.iso},media=cdrom,readonly=on",
           "-boot", "d", "-qmp", f"unix:{out}/qmp.sock,server=on,wait=off", "-no-reboot"]
    if a.firmware == "uefi":
        vars_copy = out / "OVMF_VARS.fd"
        if a.secure_boot:
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
    result = {"firmware": a.firmware, "secure_boot_requested": a.secure_boot, "accel": accel, "iso": os.path.basename(a.iso), "shots": [], "reached_desktop": False}
    try:
        qmp = Qmp(str(out / "qmp.sock"))
        streak, n, ref, clicked = 0, 0, None, False
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
            if ref is None:
                ref = wallpaper_reference(w, h)
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
            streak = streak + 1 if frac > 0.6 else 0
            if streak >= 2:
                result["reached_desktop"] = True
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
        (out / "result.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k != "shots"}))
    return 0 if result["reached_desktop"] else 1


if __name__ == "__main__":
    sys.exit(main())
