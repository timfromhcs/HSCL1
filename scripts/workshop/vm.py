"""VM manager for HSCL1 development: start/stop QEMU, screenshots and input over QMP, guest RPC over a virtio port.

Local only: QMP and the guest API port are bound to 127.0.0.1 (random ports); nothing is exposed to the network.
"""
from __future__ import annotations

import base64
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import qemu_boot_test as q  # noqa: E402  (reuses Qmp, ppm_to_png, send_keys, type_text, click, double_click)

OVMF_LINUX = "/usr/share/OVMF"


HELLO_WAIT_S = 60.0  # how long to wait for the guest daemon's hello before sending the first request anyway


class VmError(Exception):
    pass


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def build_command(iso: str | None, disk: str | None, memory_mb: int, firmware: str, qmp_port: int, api_port: int,
                  workdir: Path, smp: int = 4) -> list[str]:
    win = os.name == "nt"
    if win:
        qdir = Path(os.environ.get("QEMU_DIR", r"C:\Program Files\qemu"))
        exe, accel, cpu = str(qdir / "qemu-system-x86_64.exe"), "whpx,kernel-irqchip=off", "qemu64,+ssse3,+sse4.1,+sse4.2,+popcnt,+avx2"
    else:
        kvm = os.access("/dev/kvm", os.W_OK)
        exe, accel, cpu = "qemu-system-x86_64", "kvm" if kvm else "tcg,thread=multi", "host" if kvm else "max"
    cmd = [exe, "-machine", "q35", "-accel", accel, "-cpu", cpu, "-m", str(memory_mb), "-smp", str(smp), "-display", "none",
           "-vga", "std", "-device", "usb-ehci", "-device", "usb-kbd", "-device", "usb-tablet",
           "-audiodev", "none,id=a0", "-device", "intel-hda", "-device", "hda-duplex,audiodev=a0",
           "-netdev", "user,id=n0", "-device", "virtio-net-pci,netdev=n0",
           "-qmp", f"tcp:127.0.0.1:{qmp_port},server=on,wait=off", "-no-reboot",
           "-device", "virtio-serial-pci",
           "-chardev", f"socket,id=api,host=127.0.0.1,port={api_port},server=on,wait=off",
           "-device", "virtserialport,chardev=api,name=hscl.api"]
    if iso:
        cmd += ["-drive", f"file={iso},media=cdrom,readonly=on", "-boot", "d"]
    else:
        cmd += ["-boot", "c"]
    if disk:
        cmd += ["-drive", f"file={disk},if=virtio,format=qcow2"]
    if firmware == "uefi":
        if win:
            code, vars_src = qdir / "share" / "edk2-x86_64-code.fd", qdir / "share" / "edk2-i386-vars.fd"
        else:
            code, vars_src = Path(OVMF_LINUX) / "OVMF_CODE_4M.fd", Path(OVMF_LINUX) / "OVMF_VARS_4M.fd"
        vars_copy = workdir / "OVMF_VARS.fd"
        shutil.copy(vars_src, vars_copy)
        cmd += ["-drive", f"if=pflash,format=raw,readonly=on,file={code}", "-drive", f"if=pflash,format=raw,file={vars_copy}"]
    return cmd


class Vm:
    def __init__(self, name: str, proc: subprocess.Popen, qmp_port: int, api_port: int, workdir: Path):
        self.name, self.proc, self.qmp_port, self.api_port, self.workdir = name, proc, qmp_port, api_port, workdir
        self.qmp = q.Qmp(f"tcp:127.0.0.1:{qmp_port}")
        self._rpc = None
        self._rid = 0

    @property
    def running(self) -> bool:
        return self.proc.poll() is None

    # ---- display and input (QMP)
    def screenshot_png(self) -> bytes:
        ppm = self.workdir / "shot.ppm"
        r = self.qmp.cmd("screendump", filename=str(ppm))
        if "error" in r or not ppm.exists():
            raise VmError("screendump failed")
        png, _w, _h, _rgb = q.ppm_to_png(ppm.read_bytes())
        ppm.unlink()
        return png

    def keys(self, keys: list[str]) -> None:
        q.send_keys(self.qmp, keys)

    def type(self, text: str) -> None:
        q.type_text(self.qmp, text)

    def click(self, fx: float, fy: float, double: bool = False) -> None:
        (q.double_click if double else q.click)(self.qmp, fx, fy)

    # ---- guest RPC (virtio port hscl.api via 127.0.0.1)
    #
    # One persistent TCP connection per VM, never closed or re-sent once the guest has spoken. Reason (QEMU issue 4672 and the QGA
    # protocol notes): a guest write to a virtio-serial port that cannot be flushed to the host chardev in one call throttles the
    # port; if the host side closes meanwhile, the guest write can hang forever and later clients are stuck too. The old code opened a
    # new connection per call and re-sent the request every 3 s, which produced exactly that pattern (the Workshop daemon "stopped
    # answering" after a few calls, at a different check each run).
    def _close_rpc(self) -> None:
        if self._rpc is not None:
            try:
                self._rpc[0].close()
            except OSError:
                pass
            self._rpc = None

    def _read_line(self, sock: socket.socket, buf: bytearray, deadline: float) -> bytes | None:
        """Next complete line from the guest, or None on timeout. A timeout never closes the connection."""
        while True:
            i = buf.find(b"\n")
            if i >= 0:
                line = bytes(buf[:i])
                del buf[: i + 1]
                return line
            left = deadline - time.time()
            if left <= 0:
                return None
            sock.settimeout(min(left, 5.0))
            try:
                chunk = sock.recv(65536)
            except socket.timeout:
                continue
            if not chunk:
                raise ConnectionError("host end of the guest port was closed")
            buf.extend(chunk)

    def _ensure_rpc(self, deadline: float) -> tuple:
        """Connected socket plus read buffer. QEMU serves ONE client per socket chardev and only notices that a client went away
        while the guest port is open, so a connection that is dropped before the guest daemon has started stays 'connected' inside
        QEMU and later connections pile up in the listen backlog until the port refuses everything. Therefore: connect once, never
        close because of silence, only retry while the connect itself fails."""
        if self._rpc is not None:
            return self._rpc
        last: Exception | None = None
        while time.time() < deadline:
            try:
                sock = socket.create_connection(("127.0.0.1", self.api_port), timeout=5)
            except OSError as e:
                last = e
                time.sleep(2)
                continue
            self._rpc = (sock, bytearray())
            return self._rpc
        raise VmError(f"guest API port not reachable: {last}")

    def rpc(self, op: str, args: dict | None = None, timeout: float = 120) -> dict:
        """One request over the persistent connection, sent exactly once; stale replies (older ids) are skipped."""
        self._rid += 1
        rid = self._rid
        payload = (json.dumps({"id": rid, "op": op, "args": args or {}}) + chr(10)).encode()
        deadline = time.time() + timeout
        last: Exception | None = None
        while time.time() < deadline:
            try:
                sock, buf = self._ensure_rpc(deadline)
                if not getattr(self, "_heard", False):
                    # the daemon writes a hello line as soon as it has opened the port while we are connected; wait for it. Only a
                    # daemon that never says hello (older image) gets the request without it, after HELLO_WAIT_S, on the same connection.
                    line = self._read_line(sock, buf, min(deadline, time.time() + HELLO_WAIT_S))
                    if line is not None:
                        self._heard = True
                        if not json.loads(line).get("hello"):
                            buf[:0] = line + chr(10).encode()  # a reply, not a hello: process it below
                sock.settimeout(30)
                sock.sendall(payload)
                while True:
                    line = self._read_line(sock, buf, deadline)
                    if line is None:
                        break  # deadline: never re-send, never reconnect
                    msg = json.loads(line)
                    if msg.get("hello"):
                        continue
                    if msg.get("id") == rid:
                        self._heard = True
                        if not msg.get("ok"):
                            raise VmError(f"guest error: {msg.get('error')}")
                        return msg["result"]
                break
            except (ConnectionError, OSError) as e:
                last = e
                self._close_rpc()  # the host end really closed (QEMU quit or crashed): reconnect on the next loop turn
                time.sleep(1)
        raise VmError(f"no answer from the guest Workshop daemon within {timeout:.0f}s (booted with hscl-workshop? {last})")

    def stop(self) -> None:
        self._close_rpc()
        try:
            self.qmp.cmd("quit")
        except Exception:  # noqa: BLE001
            pass
        try:
            self.proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            self.proc.kill()


class VmManager:
    def __init__(self, base_dir: Path | None = None, mem_guard: bool = True):
        self.vms: dict[str, Vm] = {}
        self.base = base_dir or Path(tempfile.gettempdir()) / "hscl-workshop"
        self.mem_guard = mem_guard

    def start(self, name: str, iso: str | None, disk: str | None, memory_mb: int = 4096, firmware: str = "uefi") -> Vm:
        if name in self.vms and self.vms[name].running:
            raise VmError(f"VM {name!r} is already running")
        if firmware not in ("uefi", "bios"):
            raise VmError("firmware must be uefi or bios")
        if not 1024 <= memory_mb <= 16384:
            raise VmError("memory_mb must be between 1024 and 16384")
        for label, p in (("iso", iso), ("disk", disk)):
            if p and not Path(p).exists() and not (label == "disk" and p.endswith(".qcow2")):
                raise VmError(f"{label} not found: {p}")
        if disk and not disk.endswith(".qcow2"):
            raise VmError("disk must be a .qcow2 file (disposable test disks only)")
        if self.mem_guard:
            have, need = q.free_memory_mb(), memory_mb + 1500
            if have < need:
                raise VmError(f"refusing to start: {have} MB free, need {need} MB. Close apps or run 'wsl --shutdown'.")
        if disk and not Path(disk).exists():
            img = str(Path(os.environ.get("QEMU_DIR", r"C:\Program Files\qemu")) / "qemu-img.exe") if os.name == "nt" else "qemu-img"
            subprocess.run([img, "create", "-f", "qcow2", disk, "40G"], check=True, capture_output=True)
        workdir = self.base / name
        workdir.mkdir(parents=True, exist_ok=True)
        qmp_port, api_port = free_port(), free_port()
        cmd = build_command(iso, disk, memory_mb, firmware, qmp_port, api_port, workdir)
        proc = subprocess.Popen(cmd, stdout=open(workdir / "qemu.log", "wb"), stderr=subprocess.STDOUT)
        try:
            vm = Vm(name, proc, qmp_port, api_port, workdir)
        except Exception:
            proc.kill()
            raise
        self.vms[name] = vm
        return vm

    def get(self, name: str) -> Vm:
        vm = self.vms.get(name)
        if vm is None or not vm.running:
            raise VmError(f"no running VM named {name!r}")
        return vm

    def stop(self, name: str) -> None:
        self.get(name).stop()
        del self.vms[name]

    def stop_all(self) -> None:
        for n in list(self.vms):
            try:
                self.vms[n].stop()
            finally:
                self.vms.pop(n, None)

    def list(self) -> list[dict]:
        return [{"name": n, "running": v.running, "api_port": v.api_port} for n, v in self.vms.items()]


def b64_file(path: str) -> str:
    return base64.b64encode(Path(path).read_bytes()).decode()
