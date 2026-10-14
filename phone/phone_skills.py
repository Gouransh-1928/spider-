"""
SPIDER — Phone Skills
Natural language interface to ADB phone control.
"""
import re
from typing import Optional

from loguru import logger
from phone.adb_bridge import ADBBridge


class PhoneSkills:
    """
    Translates natural language phone commands to ADB actions.
    """

    def __init__(self):
        self.adb = ADBBridge()
        self._connected = False

    def handle(self, user_input: str) -> str:
        """Parse and execute a phone command."""
        # Ensure connected
        if not self._connected:
            ok, msg = self.adb.connect()
            if not ok:
                return f"Phone not connected. {msg}"
            self._connected = True

        text = user_input.lower()

        # Unlock
        if "unlock" in text and "phone" in text:
            pin = re.search(r'pin\s+(\d+)', text)
            return self.adb.unlock_screen(pin.group(1) if pin else None)

        # YouTube
        elif "youtube" in text or "play" in text:
            query = self._extract_after(text, ["play", "search", "youtube"])
            if query:
                return self.adb.play_youtube(query)
            return self.adb.open_app_by_name("youtube")

        # Open app
        elif "open" in text:
            app = self._extract_app_name(text)
            if app:
                return self.adb.open_app_by_name(app)
            return "Which app should I open on your phone?"

        # Call
        elif "call" in text:
            number = re.search(r'[\+\d][\d\s\-]{7,}', text)
            if number:
                return self.adb.make_call(number.group().replace(" ", ""))
            return "Please say the phone number to call."

        # SMS
        elif "send" in text and ("message" in text or "sms" in text or "text" in text):
            match = re.search(r'(?:send|text)\s+(.+?)\s+(?:to|saying)\s+(.+)', text, re.IGNORECASE)
            if match:
                message = match.group(1).strip()
                recipient = match.group(2).strip()
                return self.adb.send_sms(recipient, message)
            return "Please say: 'Send [message] to [number or contact]'"

        # Screenshot
        elif "screenshot" in text or "screen shot" in text:
            return self.adb.take_screenshot()

        # Volume
        elif "volume up" in text:
            steps = self._extract_number(text) or 3
            return self.adb.volume_up(steps)

        elif "volume down" in text:
            steps = self._extract_number(text) or 3
            return self.adb.volume_down(steps)

        # Battery
        elif "battery" in text:
            return self.adb.get_battery()

        # Home / Back
        elif "go home" in text or "home button" in text:
            return self.adb.press_home()

        elif "go back" in text or "back button" in text:
            return self.adb.press_back()

        else:
            return (
                "I can control your phone! Try:\n"
                "• Unlock my phone\n"
                "• Open WhatsApp on my phone\n"
                "• Play [song] on YouTube\n"
                "• Call [number]\n"
                "• Check battery\n"
                "• Take a screenshot of my phone"
            )

    def _extract_app_name(self, text: str) -> Optional[str]:
        """Extract app name from 'open [app] on my phone'."""
        match = re.search(r'open\s+(.+?)(?:\s+on\s+my\s+phone|$)', text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    def _extract_after(self, text: str, keywords: list) -> Optional[str]:
        """Extract text after a keyword."""
        for kw in keywords:
            if kw in text:
                idx = text.find(kw) + len(kw)
                result = text[idx:].strip()
                # Remove "on youtube", "my phone" suffixes
                result = re.sub(r'\s+(on youtube|on my phone|song|video)$', '', result, flags=re.IGNORECASE)
                return result.strip() if result else None
        return None

    def _extract_number(self, text: str) -> Optional[int]:
        """Extract a number from text."""
        match = re.search(r'\b(\d+)\b', text)
        return int(match.group(1)) if match else None
