"""
SPIDER — Quick System Test
Verifies all components can be imported and Ollama is reachable.
Run: python tests/test_spider.py
"""
import sys
import io
from pathlib import Path

# Ensure UTF-8 output encoding for Windows legacy console
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.table import Table

console = Console()


def test_imports():
    """Test that all modules import correctly."""
    results = []

    modules = [
        ("Config Loader", "config.loader", "CONFIG"),
        ("Memory", "core.memory", "SpiderMemory"),
        ("Context", "core.context", "ConversationContext"),
        ("Brain", "core.brain", "SpiderBrain"),
        ("Speaker (TTS)", "voice.speaker", "Speaker"),
        ("Listener (STT)", "voice.listener", "Listener"),
        ("Wake Word", "voice.wake_word", "WakeWordDetector"),
        ("Language", "voice.language", "detect_language"),
        ("Auth", "security.auth", "AuthManager"),
        ("File Manager", "skills.file_manager", "FileManager"),
        ("App Launcher", "skills.app_launcher", "AppLauncher"),
        ("System Control", "skills.system_control", "SystemControl"),
        ("Web Search", "skills.web_search", "WebSearch"),
        ("Code Writer", "skills.code_writer", "CodeWriter"),
        ("Resume Updater", "skills.resume_updater", "ResumeUpdater"),
        ("ADB Bridge", "phone.adb_bridge", "ADBBridge"),
        ("Phone Skills", "phone.phone_skills", "PhoneSkills"),
    ]

    for name, module, attr in modules:
        try:
            mod = __import__(module, fromlist=[attr])
            getattr(mod, attr)
            results.append((name, "✅ OK", "green"))
        except Exception as e:
            results.append((name, f"❌ {e}", "red"))

    return results


def test_llm():
    """Test LLM connection (Groq API or Ollama)."""
    from config.loader import CONFIG
    import requests

    provider = CONFIG["brain"].get("provider", "groq")
    model = CONFIG["brain"]["model"]

    if provider == "groq":
        key = CONFIG["brain"].get("groq_api_key", "")
        if not key:
            return "❌ Groq API Key Missing", "Set groq_api_key in settings.yaml", "red"
        try:
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"model": model, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5},
                timeout=10,
            )
            r.raise_for_status()
            return "✅ Connected (Groq API)", f"Model '{model}' active & fast", "green"
        except Exception as e:
            return "❌ Groq API Connection Error", str(e), "red"
    else:
        try:
            url = CONFIG["brain"].get("ollama_url", "http://localhost:11434")
            r = requests.get(f"{url}/api/tags", timeout=5)
            r.raise_for_status()
            models = [m["name"] for m in r.json().get("models", [])]
            if any(model in m for m in models):
                return "✅ Connected (Ollama)", f"Model '{model}' available", "green"
            else:
                return "⚠️  Connected", f"Model '{model}' NOT found. Run: ollama pull {model}", "yellow"
        except Exception as e:
            return "❌ Not connected", f"Start Ollama: run 'ollama serve'. Error: {e}", "red"


def main():
    console.print("\n[bold red]🕷️  SPIDER — System Test[/bold red]\n")

    # Import tests
    console.print("[bold]Testing Module Imports...[/bold]")
    results = test_imports()
    
    table = Table(show_header=True, header_style="bold")
    table.add_column("Module", style="cyan")
    table.add_column("Status")

    for name, status, color in results:
        table.add_row(name, f"[{color}]{status}[/{color}]")

    console.print(table)

    # LLM test
    console.print("\n[bold]Testing Brain LLM Connection...[/bold]")
    status, detail, color = test_llm()
    console.print(f"LLM Provider: [{color}]{status}[/{color}]")
    console.print(f"  {detail}")

    # Summary
    failures = sum(1 for _, s, _ in results if "❌" in s)
    console.print(f"\n[bold]Results: {len(results) - failures}/{len(results)} modules OK[/bold]")
    
    if failures == 0:
        console.print("\n[bold green]✅ SPIDER is ready! Run: python main.py[/bold green]")
    else:
        console.print(f"\n[bold yellow]⚠️  {failures} module(s) have issues.[/bold yellow]")


if __name__ == "__main__":
    main()
