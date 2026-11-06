"""Workshop daemon port I/O: reads and writes through non-blocking fds, and a write the host never drains times out (QEMU issue 4672).

Uses os.pipe/select, so it runs on Linux (CI) and is skipped on Windows checkouts (select() works only on sockets there).
"""
import os
import sys
import threading
import time

import pytest

from test_workshopd import wd

pytestmark = pytest.mark.skipif(sys.platform.startswith("win"), reason="select() on pipes needs POSIX (Linux CI runs this)")


def nb_pipe():
    r, w = os.pipe()
    os.set_blocking(r, False)
    os.set_blocking(w, False)
    return r, w


def test_reader_returns_whole_lines_and_eof():
    r, w = nb_pipe()
    reader = wd.FdReader(r)
    os.write(w, b'{"a":1}\n{"b"')
    assert reader.readline() == b'{"a":1}\n'
    t = threading.Timer(0.2, lambda: (os.write(w, b':2}\n'), os.close(w)))
    t.start()
    assert reader.readline() == b'{"b":2}\n'
    assert reader.readline() == b""  # EOF after the writer closed
    t.join()
    os.close(r)


def test_writer_times_out_when_nobody_drains_the_pipe():
    r, w = nb_pipe()
    writer = wd.TimedWriter(w, timeout=0.5)
    before = wd.PORT_STATS["write_timeouts"]
    t0 = time.monotonic()
    with pytest.raises(wd.WriteTimeout):
        writer.write(b"x" * (4 * 1024 * 1024))  # far more than a pipe holds
    assert 0.4 <= time.monotonic() - t0 < 5
    assert wd.PORT_STATS["write_timeouts"] == before + 1
    os.close(r)
    os.close(w)


def test_writer_completes_when_the_reader_drains_slowly():
    r, w = nb_pipe()
    got = bytearray()
    stop = threading.Event()

    def drain():
        os.set_blocking(r, True)
        while len(got) < 600_000 and not stop.is_set():
            got.extend(os.read(r, 4096))
            time.sleep(0.0005)

    th = threading.Thread(target=drain)
    th.start()
    wd.TimedWriter(w, timeout=20).write(b"y" * 600_000)
    th.join(timeout=20)
    stop.set()
    assert len(got) == 600_000
    os.close(r)
    os.close(w)


def test_serve_over_pipes_answers_a_request_and_reports_port_stats():
    (rin, win), (rout, wout) = nb_pipe(), nb_pipe()
    os.write(win, b'{"id":7,"op":"status","args":{}}\n')
    os.close(win)
    wd.serve(wd.FdReader(rin), wd.TimedWriter(wout), {"status": lambda a: {"port": dict(wd.PORT_STATS)}})
    out = os.read(rout, 65536).decode().splitlines()
    assert out[0].startswith('{"hello"') and '"id": 7' in out[1] and '"write_timeouts"' in out[1]
    for fd in (rin, rout, wout):
        os.close(fd)
