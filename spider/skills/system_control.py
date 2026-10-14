"""
SPIDER — System Control Skill
Controls volume, brightness, screenshots, lock, shutdown, restart.
"""
import subprocess
import time
from typing import Optional

import pyautogui
import psutil
from loguru import logger

try:
    import win32api
    import win32con
    import win32gui
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    logger.warning("pywin32 not installed. Some system controls unavailable.")


class SystemControl:
    """Controls Windows system settings via commands."""

    def handle(self, user_input: str) -> str:
        """Parse and execute system control command."""
        text = user_input.lower()

        if "volume" in text:
            return self._handle_volume(text)
        elif "screenshot" in text or "screen capture" in text:
            return self._take_screenshot()
        elif "brightness" in text:
            return self._handle_brightness(text)
        elif "shutdown" in text or "shut down" in text:
            return self._shutdown()
        elif "restart" in text or "reboot" in text:
            return self._restart()
        elif "lock" in text and "phone" not in text:
            return self._lock_screen()
        elif "sleep" in text:
            return self._sleep()
        else:
            return "I can control volume, brightness, take screenshots, lock, shutdown, or restart. What do you need?"

    def _handle_volume(self, text: str) -> str:
        """Control system volume."""
        if any(w in text for w in ["mute", "silent", "off"]):
            pyautogui.press("volumemute")
            return "Volume muted."
        elif "up" in text or "increase" in text or "louder" in text:
            steps = self._extract_number(text) or 5
            for _ in range(steps):
                pyautogui.press("volumeup")
            return f"Volume increased by {steps} steps."
        elif "down" in text or "decrease" in text or "lower" in text or "quieter" in text:
            steps = self._extract_number(text) or 5
            for _ in range(steps):
                pyautogui.press("volumedown")
            return f"Volume decreased by {steps} steps."
        elif "max" in text or "full" in text or "100" in text:
            for _ in range(50):
                pyautogui.press("volumeup")
            return "Volume set to maximum."
        elif "min" in text or "zero" in text or "0" in text:
            for _ in range(50):
                pyautogui.press("volumedown")
            return "Volume set to minimum."
        return "You can say: volume up, volume down, mute, max volume."

    def _handle_brightness(self, text: str) -> str:
        """Control screen brightness (Windows PowerShell method)."""
        if "up" in text or "increase" in text:
            level = min(100, (self._get_brightness() or 50) + 20)
        elif "down" in text or "decrease" in text:
            level = max(0, (self._get_brightness() or 50) - 20)
        else:
            level = self._extract_number(text) or 70

        try:
            script = f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,{level})"
            subprocess.run(["powershell", "-Command", script], capture_output=True)
            return f"Brightness set to {level}%."
        except Exception as e:
            logger.error(f"Brightness control error: {e}")
            return f"Couldn't change brightness: {e}"

    def _get_brightness(self) -> Optional[int]:
        """Get current brightness level."""
        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness"],
                capture_output=True, text=True,
            )
            return int(result.stdout.strip())
        except Exception:
            return None

    def _take_screenshot(self) -> str:
        """Take a screenshot and save it to Desktop."""
        from pathlib import Path
        import datetime

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = Path.home() / "Desktop" / f"screenshot_{timestamp}.png"
        try:
            screenshot = pyautogui.screenshot()
            screenshot.save(str(filename))
            logger.info(f"Screenshot saved: {filename}")
            return f"Screenshot saved to your Desktop as 'screenshot_{timestamp}.png'!"
        except Exception as e:
            return f"Couldn't take screenshot: {e}"

    def _shutdown(self) -> str:
        """Shutdown the computer."""
        subprocess.run(["shutdown", "/s", "/t", "10"])
        return "Shutting down in 10 seconds. Say 'cancel shutdown' to abort."

    def _restart(self) -> str:
        """Restart the computer."""
        subprocess.run(["shutdown", "/r", "/t", "10"])
        return "Restarting in 10 seconds."

    def _lock_screen(self) -> str:
        """Lock the Windows screen."""
        if WIN32_AVAILABLE:
            import ctypes
            ctypes.windll.user32.LockWorkStation()
        else:
            subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])
        return "Screen locked."

    def _sleep(self) -> str:
        """Put the computer to sleep."""
        subprocess.run(["powercfg", "/hibernate", "off"], capture_output=True)
        subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
        return "Going to sleep. Goodnight!"

    def _extract_number(self, text: str) -> Optional[int]:
        """Extract a number from text."""
        import re
        match = re.search(r'\b(\d+)\b', text)
        return int(match.group(1)) if match else None
