"""
Convenience entry point for running the Orbit MCP server directly.
Allows running: `python server.py` or `python -m orbit.server` from the mcp/ directory.
"""
import sys
from pathlib import Path

# Ensure the mcp root is in sys.path
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from orbit.server import app, main

if __name__ == "__main__":
    main()
