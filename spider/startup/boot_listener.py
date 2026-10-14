"""
SPIDER — Startup Boot Listener
Runs on Windows login. Plays a startup sound, asks if SPIDER should start,
then handles voice passkey authentication.
"""
import sys
import io
import time
from pathlib import Path

# Ensure UTF-8 output encoding for Windows legacy console
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from loguru import logger
from rich.console import Console
from rich.panel import Panel

console = Console()


def setup_logging():
    from config.loader import CONFIG
    log_path = CONFIG["logging"]["log_file"]
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    logger.add(log_path, rotation="10 MB", level=CONFIG["logging"]["level"])


def run_startup():
    """Main startup sequence for SPIDER."""
    setup_logging()

    console.print(Panel.fit(
        "[bold red]🕷️  S P I D E R[/bold red]\n"
        "[dim]Personal AI Assistant[/dim]",
        border_style="red",
    ))
    console.print()

    # Import here to allow fast startup display
    from voice.speaker import Speaker
    from voice.listener import Listener
    from security.auth import AuthManager

    speaker = Speaker()
    listener = Listener()
    auth = AuthManager()

    # Check for reset flag
    if "--reset" in sys.argv or "-r" in sys.argv:
        auth.reset_passkey()
        console.print("[yellow]🔄 Passkey reset requested! Starting fresh enrollment...[/yellow]")

    # ── Step 1: Ask to start ─────────────────────────────────────────────────
    speaker.speak("SPIDER online. Should I start the AI system?")
    console.print("[yellow]Say 'yes' or 'start' to activate, or press Enter.[/yellow]")

    response = listener.listen()
    if response is None:
        # Fallback to text
        response = console.input("[bold]> [/bold]").strip().lower()

    if not response or not any(w in response.lower() for w in ["yes", "start", "haan", "chalao", "activate"]):
        speaker.speak("Alright, I'll stay on standby. Say 'Hey SPIDER' to wake me up anytime.")
        console.print("[dim]SPIDER standing by. Wake word: 'Hey SPIDER'[/dim]")
        _start_background_wake_word(speaker, listener, auth)
        return

    # ── Step 2: Passkey Authentication ───────────────────────────────────────
    if not auth.is_enrolled():
        _first_time_setup(speaker, listener, auth)
    else:
        _authenticate(speaker, listener, auth)


def _authenticate(speaker, listener, auth):
    """Verify the user's spoken voice passkey or text input."""
    from config.loader import CONFIG
    max_attempts = CONFIG["security"]["max_auth_attempts"]

    speaker.speak("Please say your voice passkey to authenticate.")

    for attempt in range(max_attempts):
        console.print("[cyan]🎤 Listening for your voice passkey...[/cyan]")
        spoken = listener.listen()

        if spoken:
            if auth.verify_spoken_passkey(spoken):
                speaker.speak("Authentication successful! Welcome back. SPIDER is now active.")
                _run_main_loop(speaker, listener)
                return

        remaining = max_attempts - attempt - 1
        if remaining > 0:
            speaker.speak(f"Voice passkey not matched. {remaining} attempts remaining.")
            fallback = console.input("[yellow]Enter text passkey (or press Enter to try voice again): [/yellow]").strip()
            if fallback and auth.verify_text(fallback):
                speaker.speak("Authentication successful! SPIDER is active.")
                _run_main_loop(speaker, listener)
                return

    speaker.speak("Authentication failed. SPIDER is locking down.")
    console.print("[red]❌ Authentication failed. Run 'python reset_passkey.py' to reset your passkey.[/red]")
    sys.exit(1)


def _first_time_setup(speaker, listener, auth):
    """First-time passkey enrollment using Whisper STT voice passkey."""
    from rich.console import Console
    console = Console()

    console.print(Panel("[bold green]First Time Setup — Voice Passkey Enrollment[/bold green]"))
    speaker.speak(
        "Welcome! Let's set up your voice passkey. "
        "Please speak your secret passphrase now."
    )

    console.print("[cyan]🎤 Listening... (speak your secret voice passkey)[/cyan]")
    phrase = listener.listen()

    if not phrase:
        speaker.speak("I didn't hear anything. Please type a text passkey in the terminal.")
        passkey = console.input("[bold]Set your text passkey: [/bold]").strip()
        auth.enroll_text_passkey(passkey)
        speaker.speak("Passkey saved successfully!")
        _run_main_loop(speaker, listener)
        return

    auth.enroll_spoken_passkey(phrase)
    auth.enroll_text_passkey(phrase)
    speaker.speak(f"Got it! Your voice passkey is enrolled as: {phrase}. Let's get started!")
    _run_main_loop(speaker, listener)


def _run_main_loop(speaker, listener):
    """Start the main SPIDER conversation loop."""
    from core.brain import SpiderBrain
    from config.loader import CONFIG

    brain = SpiderBrain()

    # Check Ollama
    if not brain.check_ollama():
        speaker.speak(
            "Warning: I can't connect to my brain model. "
            "Please open a terminal and run: ollama serve"
        )

    speaker.speak(
        "I am SPIDER, your personal AI assistant. "
        "I'm ready to help you. What would you like me to do?"
    )

    from rich.console import Console
    console = Console()

    while True:
        try:
            console.print("\n[green]🕷️  SPIDER is listening...[/green]")
            user_input = listener.listen()

            if not user_input:
                continue

            # Exit commands
            if any(cmd in user_input.lower() for cmd in ["goodbye spider", "bye spider", "shutdown spider", "stop spider"]):
                speaker.speak("Goodbye! SPIDER going to sleep. Say 'Hey SPIDER' to wake me up.")
                break

            # Process command
            console.print(f"[dim]Processing: {user_input}[/dim]")
            response = brain.process(user_input)
            speaker.speak(response)

        except KeyboardInterrupt:
            speaker.speak("SPIDER shutting down. Goodbye!")
            break
        except Exception as e:
            logger.error(f"Main loop error: {e}")
            speaker.speak("I had a small issue. Let me try again.")


def _start_background_wake_word(speaker, listener, auth):
    """Run wake word detection in background when in standby mode."""
    from voice.wake_word import WakeWordDetector

    def on_wake():
        speaker.speak("Hey! SPIDER awake. Say your passkey.")
        _authenticate(speaker, listener, auth)

    detector = WakeWordDetector(on_detected=on_wake)
    detector.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        detector.stop()


if __name__ == "__main__":
    run_startup()
