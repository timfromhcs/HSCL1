"""One-shot repair for cross-platform test-harness defects (Windows host).

Fixes, without touching product code:
- `_find_hscl()` helpers that preferred the Linux ELF `target/debug/hscl`
  before `hscl.exe` on Windows (WinError 193: not a valid Win32 application).
- `subprocess.run(..., text=True)` calls that decoded UTF-8 output with the
  Windows ANSI code page (mojibake, UnicodeDecodeError in assertions).

Idempotent: running twice changes nothing.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UNIT = ROOT / "tests" / "unit"

OLD_CANDIDATES = """    candidates = [
        root / "target" / "debug" / "hscl",
        root / "target" / "debug" / "hscl.exe",
        root / "target" / "release" / "hscl",
        root / "target" / "release" / "hscl.exe",
    ]"""

NEW_CANDIDATES = """    exe = "hscl.exe" if os.name == "nt" else "hscl"
    candidates = [
        root / "target" / "debug" / exe,
        root / "target" / "release" / exe,
    ]"""

FINDER_FILES = ["test_ai_cli.py", "test_appearance_cli.py", "test_dev_cli.py", "test_system_cli.py"]

ENCODING_FILES = [
    "test_ai_cli.py",
    "test_appearance_cli.py",
    "test_dev_cli.py",
    "test_system_cli.py",
    "test_language_cli.py",
    "test_logs_cli.py",
    "test_privacy_cli.py",
    "test_recovery_cli.py",
    "test_security_cli.py",
    "test_security_lab_cli.py",
    "test_hscl_mcp.py",
]

OLD_TEXT = "text=True"
NEW_TEXT = 'text=True, encoding="utf-8", errors="replace"'


def patch_finder(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if OLD_CANDIDATES not in text:
        return False
    if "\nimport os\n" not in text:
        text = text.replace("\nimport json\n", "\nimport json\nimport os\n", 1)
    text = text.replace(OLD_CANDIDATES, NEW_CANDIDATES)
    path.write_text(text, encoding="utf-8")
    return True


def patch_encoding(path: Path) -> int:
    original = path.read_text(encoding="utf-8")
    # Protect already-patched calls, then patch the bare ones.
    text = original.replace(NEW_TEXT, "\x00ENCODED\x00")
    patched = text.count(OLD_TEXT)
    if patched:
        text = text.replace(OLD_TEXT, NEW_TEXT)
    text = text.replace("\x00ENCODED\x00", NEW_TEXT)
    if text != original:
        path.write_text(text, encoding="utf-8")
    return patched


def main() -> int:
    changed = 0
    for name in FINDER_FILES:
        if patch_finder(UNIT / name):
            print(f"finder fixed: {name}")
            changed += 1
    for name in ENCODING_FILES:
        n = patch_encoding(UNIT / name)
        if n:
            print(f"utf-8 decode: {name} ({n} calls)")
            changed += 1

    workshop = UNIT / "test_workshop_evidence.py"
    body = workshop.read_text(encoding="utf-8")
    if "text = out.read_text()" in body:
        body = body.replace("text = out.read_text()", 'text = out.read_text(encoding="utf-8", errors="replace")')
        workshop.write_text(body, encoding="utf-8")
        print("utf-8 decode: test_workshop_evidence.py (1 read)")
        changed += 1

    print("changed files:", changed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
