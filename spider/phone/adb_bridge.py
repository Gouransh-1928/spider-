"""
SPIDER — ADB Bridge
Controls Android phone via Android Debug Bridge (ADB) over USB.
"""
import re
import subprocess
import time
from typing import List, Optional, Tuple

from loguru import logger

from config.loader import CONFIG


class ADBBridge:
    """
    Python wrapper around ADB commands for controlling Android phone.
    Requires ADB installed and USB debugging enabled on the phone.
    """

    def __init__(self):
        self.adb = CONFIG["phone"]["adb_path"]
        self.device_serial = CONFIG["phone"]["device_serial"]
        self._device_cmd = []

    def connect(self) -> Tuple[bool, str]:
        """Check ADB connection and detect device."""
        try:
            result = self._run(["devices"])
            lines = result.stdout.strip().split("\n")[1:]  # Skip header
            devices = [l.split("\t")[0] for l in lines if "device" in l and "offline" not in l]

            if not devices:
                return False, (
                    "No Android device found. Please:\n"
                    "1. Connect phone via USB\n"
                    "2. Enable USB Debugging (Settings → Developer Options → USB Debugging)\n"
                    "3. Tap 'Allow' on your phone when prompted"
                )

            self.device_serial = devices[0]
            self._device_cmd = ["-s", self.device_serial]
            logger.info(f"Phone connected: {self.device_serial}")
            return True, f"Phone connected: {self.device_serial}"

        except FileNotFoundError:
            return False, (
                "ADB not found. Please install Android Platform Tools:\n"
                "Download from: https://developer.android.com/studio/releases/platform-tools\n"
                "And add it to your PATH."
            )
        except Exception as e:
            return False, f"ADB error: {e}"

    def is_connected(self) -> bool:
        """Check if a device is currently connected."""
        connected, _ = self.connect()
        return connected

    def unlock_screen(self, pin: str = None) -> str:
        """Wake up and unlock the phone screen."""
        # Wake screen
        self._shell("input keyevent 224")  # KEYCODE_WAKEUP
        time.sleep(0.5)
        # Swipe up to unlock
        self._shell("input swipe 540 1500 540 500")
        time.sleep(0.5)

        if pin:
            # Type the PIN
            self._shell(f"input text {pin}")
            self._shell("input keyevent 66")  # ENTER
            return "Screen unlocked with PIN."

        return "Screen woken up and swipe gesture sent. If you have a PIN, say: 'unlock phone with PIN [your pin]'"

    def open_app(self, package_name: str) -> str:
        """Open an app by package name."""
        result = self._shell(f"monkey -p {package_name} -c android.intent.category.LAUNCHER 1")
        if "Events injected" in result:
            return f"Opened {package_name}"
        return f"Couldn't open {package_name}"

    def open_app_by_name(self, app_name: str) -> str:
        """Try to open an app by common name."""
        package = ANDROID_PACKAGES.get(app_name.lower())
        if not package:
            return f"I don't know the package name for '{app_name}'. Known apps: {', '.join(ANDROID_PACKAGES.keys())}"
        return self.open_app(package)

    def play_youtube(self, query: str) -> str:
        """Open YouTube and search for a video."""
        search_url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
        result = self._shell(f'am start -a android.intent.action.VIEW -d "{search_url}"')
        return f"Opening YouTube and searching for: {query}"

    def send_sms(self, phone_number: str, message: str) -> str:
        """Open SMS composer with pre-filled message."""
        result = self._shell(
            f'am start -a android.intent.action.SENDTO '
            f'-d sms:{phone_number} --es sms_body "{message}" --ez exit_on_sent true'
        )
        return f"SMS composer opened for {phone_number}."

    def make_call(self, phone_number: str) -> str:
        """Make a phone call."""
        result = self._shell(f'am start -a android.intent.action.CALL -d tel:{phone_number}')
        return f"Calling {phone_number}..."

    def take_screenshot(self) -> str:
        """Take a screenshot on the phone."""
        remote_path = "/sdcard/spider_screenshot.png"
        local_path = str(__import__("pathlib").Path.home() / "Desktop" / "phone_screenshot.png")
        self._shell(f"screencap -p {remote_path}")
        result = self._run(["pull", remote_path, local_path])
        if result.returncode == 0:
            return f"Phone screenshot saved to: {local_path}"
        return "Couldn't take screenshot."

    def volume_up(self, steps: int = 3) -> str:
        """Increase phone volume."""
        for _ in range(steps):
            self._shell("input keyevent 24")  # KEYCODE_VOLUME_UP
        return f"Phone volume increased by {steps} steps."

    def volume_down(self, steps: int = 3) -> str:
        """Decrease phone volume."""
        for _ in range(steps):
            self._shell("input keyevent 25")  # KEYCODE_VOLUME_DOWN
        return f"Phone volume decreased by {steps} steps."

    def get_battery(self) -> str:
        """Get phone battery level."""
        result = self._shell("dumpsys battery | grep level")
        match = re.search(r'level: (\d+)', result)
        level = match.group(1) if match else "unknown"
        return f"Phone battery is at {level}%."

    def type_text(self, text: str) -> str:
        """Type text on the phone."""
        # Escape spaces for ADB
        escaped = text.replace(" ", "%s")
        self._shell(f"input text {escaped}")
        return f"Typed: {text}"

    def press_back(self) -> str:
        """Press the back button."""
        self._shell("input keyevent 4")
        return "Back button pressed."

    def press_home(self) -> str:
        """Press the home button."""
        self._shell("input keyevent 3")
        return "Home button pressed."

    def _shell(self, command: str) -> str:
        """Run an ADB shell command."""
        result = self._run(["shell"] + command.split())
        return result.stdout.strip() if result else ""

    def _run(self, args: List[str]) -> subprocess.CompletedProcess:
        """Run an ADB command."""
        cmd = [self.adb] + self._device_cmd + args
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode != 0 and result.stderr:
            logger.debug(f"ADB stderr: {result.stderr}")
        return result


# Common Android app package names
ANDROID_PACKAGES = {
    "whatsapp": "com.whatsapp",
    "youtube": "com.google.android.youtube",
    "chrome": "com.android.chrome",
    "gmail": "com.google.android.gm",
    "maps": "com.google.android.apps.maps",
    "google maps": "com.google.android.apps.maps",
    "spotify": "com.spotify.music",
    "instagram": "com.instagram.android",
    "twitter": "com.twitter.android",
    "x": "com.twitter.android",
    "facebook": "com.facebook.katana",
    "snapchat": "com.snapchat.android",
    "telegram": "org.telegram.messenger",
    "netflix": "com.netflix.mediaclient",
    "amazon": "in.amazon.mShop.android.shopping",
    "flipkart": "com.flipkart.android",
    "phonepe": "com.phonepe.app",
    "gpay": "com.google.android.apps.nbu.paisa.user",
    "paytm": "net.one97.paytm",
    "camera": "android.hardware.camera",
    "gallery": "com.google.android.apps.photos",
    "photos": "com.google.android.apps.photos",
    "settings": "com.android.settings",
    "play store": "com.android.vending",
}
