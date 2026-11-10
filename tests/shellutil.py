"""Run POSIX scripts from tests on any dev host (Linux, macOS, Windows with Git Bash or WSL).

Why this exists: `shutil.which("bash")` on Windows resolves to the WSL launcher
(`C:\\WINDOWS\\system32\\bash.EXE`). That launcher eats backslashes in Windows paths, and it
overrides variables such as `LANG`/`LC_ALL` regardless of `WSLENV`, so tests that pass a Windows
path or an env override failed on the dev host while passing in CI. This helper detects the bash
flavour, converts paths, and passes overrides through `wsl.exe -e env` so they actually reach the
guest. The same test therefore runs everywhere instead of being skipped: a test that is skipped on
one host is not evidence on that host.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

BASH = shutil.which("bash")
WSL = shutil.which("wsl")
_KIND: str | None = None

_WIN_PATH = re.compile(r"^[A-Za-z]:[\\/]")


def bash_kind() -> str:
    """'native' (Git Bash/MSYS/Cygwin/posix), 'wsl' (Windows WSL launcher) or 'none'."""
    global _KIND
    if _KIND is not None:
        return _KIND
    if BASH is None:
        _KIND = "none"
        return _KIND
    if sys.platform != "win32":
        # On a real POSIX host `uname -s` also says Linux; only the Windows launcher is WSL.
        _KIND = "native"
        return _KIND
    try:
        r = subprocess.run([BASH, "-c", "uname -s"], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        _KIND = "none"
        return _KIND
    name = (r.stdout or "").strip()
    if r.returncode != 0 or not name:
        _KIND = "none"
    elif name.startswith("Linux"):
        _KIND = "wsl"
    else:
        _KIND = "native"
    return _KIND


def usable() -> bool:
    return bash_kind() in ("native", "wsl")


def to_bash_path(path: str | os.PathLike[str]) -> str:
    """Path string the detected bash can open: /mnt/c/... for WSL, forward slashes for Git Bash."""
    kind = bash_kind()
    text = os.fspath(path)
    if kind == "wsl" and text.startswith("/") and not text.startswith("//"):
        return text
    p = Path(path).resolve()
    if kind == "wsl":
        drive = p.drive.rstrip(":").lower()
        return "/mnt/" + drive + p.as_posix()[2:]
    if sys.platform == "win32":
        return p.as_posix()
    return str(p)


_GUEST_PATH: str | None = None


def guest_path() -> str:
    """The PATH the guest gets from interop (needed when a test overrides PATH)."""
    global _GUEST_PATH
    if _GUEST_PATH is None:
        r = subprocess.run(
            [WSL or BASH, "-e", "bash", "-c", 'printf %s "$PATH"'],
            capture_output=True,
            text=True,
            timeout=30,
        )
        _GUEST_PATH = (r.stdout or "").strip() or "/usr/local/bin:/usr/bin:/bin"
    return _GUEST_PATH


def _env_value(value: object, name: str = "") -> str:
    text = str(value)
    if bash_kind() != "wsl":
        return text
    if name.upper() == "PATH":
        # Callers can already have constructed a guest PATH. Resolving it through
        # Windows Path turns /mnt/c/... into E:/mnt/c/... and hides their tools.
        if text.startswith("/") and ";" not in text:
            return text
        # Windows PATH list -> colon-separated POSIX paths (the fake binaries live on the host drive),
        # then the guest PATH so `bash`, `sh` and coreutils stay reachable.
        parts = [p for p in text.split(";") if p]
        converted = ":".join(to_bash_path(p) for p in parts)
        return f"{converted}:{guest_path()}"
    if _WIN_PATH.match(text):
        return to_bash_path(text)
    return text


def _wsl_command(overrides: dict[str, object | None], script: str, args: list[str]) -> list[str]:
    """wsl.exe -e env [-u NAME] [NAME=VALUE] bash SCRIPT ARGS.

    Going through `env` is what makes overrides such as LANG stick: the interop layer resets that
    variable for the login environment, but never for a program it was asked to exec directly.
    """
    env_args: list[str] = []
    assignments: list[str] = []
    for name in sorted(overrides):
        value = overrides[name]
        if value is None:
            # env(1) only accepts options before the NAME=VALUE assignments
            env_args += ["-u", name]
        else:
            assignments.append(f"{name}={_env_value(value, name)}")
    launcher = WSL or BASH
    return [launcher, "-e", "env", *env_args, *assignments, "bash", script, *args]


_ENV_MISSING = re.compile(r"^env: '?(?P<name>[^':\n]+)'?: No such file or directory", re.MULTILINE)


def _raise_if_missing_executable(result: subprocess.CompletedProcess, argv: list[str]) -> None:
    """Translate WSL's missing-executable result into the native FileNotFoundError contract.

    A POSIX host raises `FileNotFoundError` from `subprocess.run` when `argv[0]` is absent. Under
    WSL the Windows-side launch succeeds and `env(1)` inside the guest reports the miss as exit
    code 127, so callers that catch `FileNotFoundError` to mean "tool not installed" would silently
    see a failed run instead. Only env's own message is translated: a command that exits 127 by
    itself keeps its exit code.
    """
    if result.returncode != 127 or not argv:
        return
    for match in _ENV_MISSING.finditer(result.stderr or ""):
        if match.group("name") == argv[0]:
            raise FileNotFoundError(2, "No such file or directory", argv[0])


def run_command(
    argv: list[str],
    *,
    env_overrides: dict[str, object | None] | None = None,
    timeout: int = 120,
) -> subprocess.CompletedProcess:
    """Run a POSIX command (shellcheck, awk, ...) with the detected bash environment.

    Paths inside `argv` are the caller's responsibility (use `to_bash_path`); overrides are converted
    the same way `run_script` does and, under WSL, passed through `env` so they are not reset.
    A missing executable raises `FileNotFoundError` on every host, as it does natively.
    """
    kind = bash_kind()
    if kind == "none":
        raise RuntimeError("no usable bash (native or WSL) found")
    raw = dict(env_overrides or {})
    if kind == "wsl":
        env_args: list[str] = []
        assignments: list[str] = []
        for name in sorted(raw):
            value = raw[name]
            if value is None:
                env_args += ["-u", name]
            else:
                assignments.append(f"{name}={_env_value(value, name)}")
        result = subprocess.run(
            [WSL or BASH, "-e", "env", *env_args, *assignments, *argv],
            capture_output=True, text=True, timeout=timeout,
        )
        _raise_if_missing_executable(result, argv)
        return skip_if_shell_broken(result)
    env = {**os.environ}
    for key, value in raw.items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = _env_value(value, key)
    return subprocess.run(argv, capture_output=True, text=True, env=env, timeout=timeout)


def run_script(
    script: str | os.PathLike[str],
    *args: object,
    env_overrides: dict[str, object | None] | None = None,
    timeout: int = 120,
    input_text: str | None = None,
) -> subprocess.CompletedProcess:
    """Run a shell script with the detected bash. Overrides are passed into WSL explicitly.

    A value of None removes the variable from the child environment.
    """
    kind = bash_kind()
    if kind == "none":
        raise RuntimeError("no usable bash (native or WSL) found")
    raw = dict(env_overrides or {})
    target = to_bash_path(script)
    argv = [str(a) for a in args]
    if kind == "wsl":
        cmd = _wsl_command(raw, target, argv)
        env = None
    else:
        env = {**os.environ}
        for key, value in raw.items():
            if value is None:
                env.pop(key, None)
            else:
                env[key] = _env_value(value, key)
        cmd = [BASH, target, *argv]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
        input=input_text,
    )
    # Only a WSL launcher can half-start; a native bash that fails keeps failing.
    return skip_if_shell_broken(result) if kind == "wsl" else result


# A WSL launcher that is starting up (or half-up after a `wsl --shutdown`) prints one of these instead of running
# the script. Measured 2026-11-10: three handbook-launcher tests failed in a gate run while the same tests skip
# standalone; the shell was reachable at collection time but broke before the script ran. WSL writes its own
# launcher errors as **UTF-16** into the pipe ("Ein Verbindungsversuch ... github.com/microsoft/WSL/issues"), so the
# text is normalised before matching.
_WSL_BROKEN = (
    "WslRegisterDistribution",
    "Catastrophic failure",
    "UtilBindVsock",
    "getaddrinfo",
    "wsl: ",
    "WSL/issues",
    "networkingMode",
    "Verbindungsversuch",
    "The system cannot find the file",
    "Cannot connect to the WSL",
)


def _normalise_launcher_text(text: str) -> str:
    if "\x00" in text:
        try:
            text = text.encode("latin-1", "ignore").decode("utf-16-le", "ignore")
        except (UnicodeError, LookupError):
            pass
        text = text.replace("\x00", "")
    return text


def skip_if_shell_broken(result: subprocess.CompletedProcess) -> subprocess.CompletedProcess:
    """Skip the caller when the shell itself failed, instead of asserting on its error text.

    Only launcher-level failures are turned into skips: a script that ran and returned non-zero keeps failing.
    The check looks at the output even for returncode 0, because WSL's launcher can report success while printing
    its own failure text instead of running the script.
    """
    text = _normalise_launcher_text(f"{result.stdout or ''}{result.stderr or ''}")
    if any(marker in text for marker in _WSL_BROKEN):
        import pytest

        first = text.strip().splitlines()[0][:140] if text.strip() else "no output"
        pytest.skip(f"shell unavailable: {first}")
    return result

