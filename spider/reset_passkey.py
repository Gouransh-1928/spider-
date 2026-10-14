"""
SPIDER — Reset Passkey Tool
Resets the enrolled voice and text passkeys.
Usage: python reset_passkey.py
"""
import sys
import io
from pathlib import Path

# Ensure UTF-8 output encoding for Windows legacy console
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from security.auth import AuthManager

if __name__ == "__main__":
    auth = AuthManager()
    if auth.reset_passkey():
        print("✅ SPIDER passkey reset successfully!")
        print("   The next time you launch main.py, SPIDER will prompt you for fresh voice enrollment.")
    else:
        print("❌ Failed to reset passkey.")
