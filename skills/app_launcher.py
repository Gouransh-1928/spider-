"""
SPIDER — App Launcher Skill
Opens applications on Windows by name.
"""
import os
import re
import subprocess
from typing import Dict, Optional

import psutil
import pyautogui
from loguru import logger


# Common Windows app paths / commands
APP_REGISTRY: Dict[str, str] = {
    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "google chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "firefox": r"C:\Program Files\Mozilla Firefox\firefox.exe",
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "file explorer": "explorer.exe",
    "explorer": "explorer.exe",
    "vlc": r"C:\Program Files\VideoLAN\VLC\vlc.exe",
    "word": r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
    "excel": r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
    "powerpoint": r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE",
    "vs code": r"C:\Users\hp\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "vscode": r"C:\Users\hp\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "terminal": "wt.exe",
    "cmd": "cmd.exe",
    "powershell": "powershell.exe",
    "spotify": r"C:\Users\hp\AppData\Roaming\Spotify\Spotify.exe",
    "whatsapp": r"C:\Users\hp\AppData\Local\WhatsApp\WhatsApp.exe",
    "telegram": r"C:\Users\hp\AppData\Roaming\Telegram Desktop\Telegram.exe",
    "paint": "mspaint.exe",
    "task manager": "taskmgr.exe",
    "settings": "ms-settings:",
}


class AppLauncher:
    """Opens and closes applications on Windows."""

    def handle(self, user_input: str) -> str:
        """Parse command and launch or close an app."""
        text = user_input.lower()

        if any(w in text for w in ["close", "quit", "exit", "kill"]):
            return self._close_app(text)
        else:
            return self._launch_app(text)

    def _launch_app(self, text: str) -> str:
        """Launch an application."""
        app_name = self._extract_app_name(text)
        if not app_name:
            return "Which app should I open?"

        # Check registry
        app_path = self._find_app(app_name)
        if not app_path:
            return f"I don't know how to open '{app_name}'. You can teach me by adding it to the app registry."

        try:
            if app_path.startswith("ms-"):
                os.startfile(app_path)
            else:
                subprocess.Popen(app_path, shell=True)
            logger.info(f"Launched: {app_name} → {app_path}")
            return f"Opening {app_name}!"
        except Exception as e:
            logger.error(f"Launch error: {e}")
            return f"I tried to open {app_name} but got an error: {e}"

    def _close_app(self, text: str) -> str:
        """Close a running application."""
        app_name = self._extract_app_name(text)
        if not app_name:
            return "Which app should I close?"

        closed = False
        for proc in psutil.process_iter(["name", "pid"]):
            if app_name.lower() in proc.info["name"].lower():
                try:
                    proc.kill()
                    closed = True
                    logger.info(f"Closed process: {proc.info['name']}")
                except Exception:
                    pass

        if closed:
            return f"Closed {app_name}."
        else:
            return f"I couldn't find '{app_name}' running."

    def _extract_app_name(self, text: str) -> Optional[str]:
        """Extract app name from command text."""
        # Remove common command words
        stop_words = ["open", "launch", "start", "close", "quit", "exit", "kill", "app", "the", "please"]
        words = text.lower().split()
        filtered = [w for w in words if w not in stop_words]
        
        if not filtered:
            return None

        # Try 2-word combos first, then single word
        if len(filtered) >= 2:
            two_word = " ".join(filtered[:2])
            if two_word in APP_REGISTRY:
                return two_word

        return filtered[0] if filtered else None

    def _find_app(self, app_name: str) -> Optional[str]:
        """Find the app path from registry."""
        name_lower = app_name.lower()
        
        # Direct match
        if name_lower in APP_REGISTRY:
            return APP_REGISTRY[name_lower]

        # Partial match
        for key, path in APP_REGISTRY.items():
            if name_lower in key or key in name_lower:
                return path

        return None
