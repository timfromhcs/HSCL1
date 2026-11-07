"""``python -m hcseasymath`` : ``doctor`` and ``serve``. No background service, no autostart."""

from __future__ import annotations

import argparse
import importlib.metadata as md
import json
import platform
import secrets
import socket
import sys

from . import __version__

PACKAGES = ("sympy", "numpy", "scipy", "fastapi", "pydantic", "uvicorn")


def doctor(as_json: bool) -> int:
    info = {
        "app": "hcseasymath",
        "version": __version__,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": {p: md.version(p) for p in PACKAGES},
        "accelerators": {"hcsuda": "not_used"},
        "isolated_worker": "supported" if sys.platform.startswith("linux") else "unsupported_platform",
        "listens": False,
    }
    if as_json:
        print(json.dumps(info, indent=2, sort_keys=True))
    else:
        print(f"hcseasymath {info['version']} on Python {info['python']} ({info['platform']})")
        for name, ver in info["packages"].items():
            print(f"  {name:10} {ver}")
        print(f"  isolated worker: {info['isolated_worker']}; accelerators: HCSUDA not used")
    return 0


def serve(port: int) -> int:
    import uvicorn

    from .api.app import create_app

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", port))
    sock.listen(16)
    bound = sock.getsockname()[1]
    token = secrets.token_urlsafe(32)
    app = create_app(token=token, port=bound)
    # The launcher reads this single line; the token is shown to the user who started the app.
    print(json.dumps({"url": f"http://127.0.0.1:{bound}/", "token": token}), flush=True)
    config = uvicorn.Config(app, log_level="warning", access_log=False, server_header=False)
    uvicorn.Server(config).run(sockets=[sock])
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hcseasymath")
    sub = parser.add_subparsers(dest="command", required=True)
    d = sub.add_parser("doctor", help="report versions and capabilities; opens no listener")
    d.add_argument("--json", action="store_true")
    s = sub.add_parser("serve", help="run the loopback API until stopped")
    s.add_argument("--port", type=int, default=0, help="0 picks a free port")
    args = parser.parse_args(argv)
    if args.command == "doctor":
        return doctor(args.json)
    return serve(args.port)


if __name__ == "__main__":
    raise SystemExit(main())
