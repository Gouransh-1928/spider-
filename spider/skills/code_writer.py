"""
SPIDER — Code Writer Skill
Generates code using Ollama, writes it to files, runs it, and retries if it fails.
"""
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional, Tuple

import requests
from loguru import logger

from config.loader import CONFIG


class CodeWriter:
    """
    AI-powered code generation with retry logic.
    SPIDER writes code, runs it, captures errors, and tries again until it works.
    """

    MAX_RETRIES = 3
    OLLAMA_URL = CONFIG["brain"].get("ollama_url", "http://localhost:11434")
    MODEL = CONFIG["brain"]["model"]

    # Language → file extension + run command
    LANGUAGE_MAP = {
        "python": (".py", [sys.executable, "{file}"]),
        "javascript": (".js", ["node", "{file}"]),
        "node": (".js", ["node", "{file}"]),
        "bash": (".sh", ["bash", "{file}"]),
        "powershell": (".ps1", ["powershell", "-File", "{file}"]),
    }

    def handle(self, user_input: str) -> str:
        """Generate code, save it, optionally run it."""
        lang = self._detect_language(user_input)
        description = self._extract_description(user_input)
        save_location = self._extract_save_location(user_input)

        logger.info(f"Code writer: lang={lang}, description={description[:60]}")

        code = self._generate_code(description, lang)
        if not code:
            return "I couldn't generate the code. Please try again."

        # Save the file
        file_path = self._save_code(code, lang, description, save_location)
        if not file_path:
            return "I generated the code but couldn't save it."

        # Run the code if it's Python (and user didn't say "don't run")
        if lang == "python" and "don't run" not in user_input.lower() and "do not run" not in user_input.lower():
            run_result = self._run_with_retry(file_path, code, description, lang)
            return (
                f"I wrote the code and saved it to:\n{file_path}\n\n"
                f"Run result:\n{run_result}"
            )

        return f"Done! Code saved to:\n{file_path}\n\nHere's what I wrote:\n```{lang}\n{code}\n```"

    def _generate_code(self, description: str, language: str = "python", error: str = None) -> Optional[str]:
        """Ask LLM (Groq or Ollama) to generate code."""
        prompt = f"Write {language} code for the following task:\n{description}"
        if error:
            prompt += f"\n\nThe previous attempt had this error:\n{error}\n\nPlease fix the code."

        prompt += "\n\nReturn ONLY the raw code, no explanations, no markdown fences."

        provider = CONFIG["brain"].get("provider", "groq")
        model = CONFIG["brain"]["model"]

        try:
            if provider == "groq":
                url = "https://api.groq.com/openai/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {CONFIG['brain'].get('groq_api_key', '')}",
                    "Content-Type": "application/json",
                }
                payload = {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 2000,
                }
                response = requests.post(url, headers=headers, json=payload, timeout=60)
                response.raise_for_status()
                raw = response.json()["choices"][0]["message"]["content"].strip()
            else:
                response = requests.post(
                    f"{CONFIG['brain']['ollama_url']}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.3, "num_predict": 2000},
                    },
                    timeout=90,
                )
                response.raise_for_status()
                raw = response.json()["response"].strip()

            # Strip markdown code fences if present
            raw = re.sub(r'^```\w*\n?', '', raw)
            raw = re.sub(r'\n?```$', '', raw)
            return raw.strip()

        except Exception as e:
            logger.error(f"Code generation error: {e}")
            return None

    def _run_with_retry(
        self, file_path: Path, code: str, description: str, lang: str
    ) -> str:
        """Run the code; if it fails, regenerate and retry."""
        for attempt in range(1, self.MAX_RETRIES + 1):
            logger.info(f"Running code (attempt {attempt}/{self.MAX_RETRIES}): {file_path}")
            success, output, error = self._run_code(file_path, lang)

            if success:
                return f"✅ Success on attempt {attempt}!\n{output}"

            logger.warning(f"Attempt {attempt} failed. Error:\n{error}")

            if attempt < self.MAX_RETRIES:
                # Regenerate with error context
                new_code = self._generate_code(description, lang, error=error)
                if new_code:
                    self._save_code(new_code, lang, description, file_path.parent, file_path.name)
                    code = new_code
                else:
                    break

        return f"❌ Code failed after {self.MAX_RETRIES} attempts.\nLast error:\n{error}"

    def _run_code(self, file_path: Path, lang: str) -> Tuple[bool, str, str]:
        """Execute code and capture output."""
        ext, cmd_template = self.LANGUAGE_MAP.get(lang, (".py", [sys.executable, "{file}"]))
        cmd = [c.replace("{file}", str(file_path)) for c in cmd_template]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                return True, result.stdout[:1000], ""
            else:
                return False, result.stdout[:500], result.stderr[:500]
        except subprocess.TimeoutExpired:
            return False, "", "Code execution timed out (30s)."
        except Exception as e:
            return False, "", str(e)

    def _save_code(
        self,
        code: str,
        lang: str,
        description: str,
        location: Optional[Path] = None,
        filename: Optional[str] = None,
    ) -> Optional[Path]:
        """Save code to a file."""
        ext, _ = self.LANGUAGE_MAP.get(lang, (".py", None))

        if not filename:
            # Generate filename from description
            safe_name = re.sub(r'[^\w\s]', '', description[:30]).strip().replace(' ', '_').lower()
            filename = f"spider_{safe_name}{ext}"

        save_dir = location or Path.home() / "Desktop"
        save_dir.mkdir(parents=True, exist_ok=True)
        file_path = save_dir / filename

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(code)
            logger.info(f"Code saved: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Code save error: {e}")
            return None

    def _detect_language(self, text: str) -> str:
        """Detect the programming language from user input."""
        text_lower = text.lower()
        if "javascript" in text_lower or "js" in text_lower or "node" in text_lower:
            return "javascript"
        if "bash" in text_lower or "shell script" in text_lower:
            return "bash"
        if "powershell" in text_lower:
            return "powershell"
        return "python"  # Default

    def _extract_description(self, text: str) -> str:
        """Extract the task description from the command."""
        # Remove command words
        text = re.sub(r'^(write|create|make|generate|code for|write code for|script for)\s+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\s+(and save|save it|on desktop|in documents).*$', '', text, flags=re.IGNORECASE)
        return text.strip()

    def _extract_save_location(self, text: str) -> Optional[Path]:
        """Extract where to save the code."""
        text_lower = text.lower()
        if "desktop" in text_lower:
            return Path.home() / "Desktop"
        if "documents" in text_lower:
            return Path.home() / "Documents"
        if "downloads" in text_lower:
            return Path.home() / "Downloads"
        return None
