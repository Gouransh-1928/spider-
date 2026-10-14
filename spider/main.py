"""
SPIDER — Main Entry Point
Start SPIDER directly from here.
"""
import os
import sys
import io
from pathlib import Path

# Silence HuggingFace symlink warning on Windows
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

# Ensure UTF-8 output encoding for Windows legacy console
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Ensure project root is on path
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from startup.boot_listener import run_startup

if __name__ == "__main__":
    run_startup()
