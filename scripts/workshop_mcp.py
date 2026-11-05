#!/usr/bin/env python3
"""Entry point: python scripts/workshop_mcp.py  (MCP over stdio)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "workshop"))
from mcp_server import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
