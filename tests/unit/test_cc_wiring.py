"""Control Center wiring: pages must receive the context property under a name that does not shadow their own property."""
import re
from pathlib import Path

CC = Path(__file__).resolve().parents[2] / "apps/control-center"


def test_main_does_not_bind_backend_to_itself():
    main = (CC / "qml/Main.qml").read_text(encoding="utf-8")
    assert not re.search(r"backend:\s*backend\b", main), "self-binding: page.backend would stay null"
    assert main.count("backend: cli") == 4


def test_cpp_exposes_the_same_context_property():
    assert 'QStringLiteral("cli")' in (CC / "src/main.cpp").read_text(encoding="utf-8")
