"""
SPIDER — Core Brain
Ollama LLM orchestrator with skill dispatch, memory integration,
and retry logic for task execution.
"""
import json
import re
from typing import Any, Dict, List, Optional, Tuple

import requests
from loguru import logger

from config.loader import CONFIG
from core.context import ConversationContext
from core.memory import SpiderMemory
from voice.language import detect_language, get_response_language_instruction


# ─── Skill registry ───────────────────────────────────────────────────────────
# Maps intent keywords to skill modules (imported lazily to avoid circular deps)
SKILL_INTENTS = {
    # File management
    "create folder": "file_manager",
    "create directory": "file_manager",
    "delete folder": "file_manager",
    "delete file": "file_manager",
    "rename": "file_manager",
    "move file": "file_manager",
    "copy file": "file_manager",
    "open file": "file_manager",
    "open folder": "file_manager",
    "list files": "file_manager",
    "show files": "file_manager",

    # App control
    "open app": "app_launcher",
    "launch": "app_launcher",
    "start": "app_launcher",
    "close app": "app_launcher",

    # System control
    "volume": "system_control",
    "brightness": "system_control",
    "screenshot": "system_control",
    "shutdown": "system_control",
    "restart": "system_control",
    "lock": "system_control",

    # Web search
    "search": "web_search",
    "find": "web_search",
    "look up": "web_search",
    "google": "web_search",
    "what is": "web_search",
    "tell me about": "web_search",

    # Code writing
    "write code": "code_writer",
    "create script": "code_writer",
    "code for": "code_writer",
    "program": "code_writer",
    "make a function": "code_writer",

    # Resume
    "update resume": "resume_updater",
    "update my resume": "resume_updater",
    "resume": "resume_updater",

    # Phone control
    "unlock phone": "phone_skills",
    "open on my phone": "phone_skills",
    "phone": "phone_skills",
    "call": "phone_skills",
    "send message": "phone_skills",
    "play": "phone_skills",
}


class SpiderBrain:
    """
    The core intelligence of SPIDER.
    Uses Groq API (or Ollama fallback) to understand commands and dispatch skills.
    """

    def __init__(self):
        cfg = CONFIG["brain"]
        self.provider = cfg.get("provider", "groq")
        self.model = cfg["model"]
        self.groq_api_key = cfg.get("groq_api_key", "")
        self.ollama_url = cfg.get("ollama_url", "http://localhost:11434")
        self.temperature = cfg["temperature"]
        self.max_tokens = cfg["max_tokens"]
        self.system_prompt = cfg["system_prompt"]

        self.memory = SpiderMemory()
        self.context = ConversationContext()
        self._skills_cache: Dict[str, Any] = {}

        logger.info(f"Brain initialized. Provider: {self.provider}, Model: {self.model}")

    def process(self, user_input: str) -> str:
        """
        Main entry point: process a user command.
        1. Detects intent and language
        2. Retrieves relevant memories
        3. Dispatches to a skill if needed
        4. Falls through to LLM conversation
        5. Stores the turn in memory
        """
        if not user_input or not user_input.strip():
            return "Hmm, I didn't catch that. Could you say that again?"

        # Detect language
        lang = detect_language(user_input)
        lang_instruction = get_response_language_instruction(lang)

        # Detect skill intent
        skill_name = self._detect_skill(user_input)

        # Retrieve relevant long-term memories
        memory_context = self.memory.format_context_for_llm(user_input)

        # Build the full prompt
        system = self._build_system_prompt(lang_instruction, memory_context)

        # If a skill is detected, try to execute it
        skill_result = None
        if skill_name:
            skill_result = self._execute_skill(skill_name, user_input)

        # Build response via LLM
        if skill_result:
            # Tell LLM what the skill did and ask it to narrate naturally
            augmented_input = (
                f"The user said: '{user_input}'\n"
                f"I executed the skill '{skill_name}' and got this result:\n{skill_result}\n\n"
                f"Now reply to the user naturally, confirming what was done."
            )
            response = self._ask_llm(augmented_input, system)
        else:
            response = self._ask_llm(user_input, system)

        # Store turn in memory
        self.context.add_user(user_input)
        self.context.add_assistant(response)
        self.memory.remember_conversation(user_input, response)

        return response

    def _detect_skill(self, text: str) -> Optional[str]:
        """Detect which skill to use based on keywords in the user's input."""
        text_lower = text.lower()
        for keyword, skill in SKILL_INTENTS.items():
            if keyword in text_lower:
                return skill
        return None

    def _execute_skill(self, skill_name: str, user_input: str) -> Optional[str]:
        """Import and execute the appropriate skill."""
        try:
            if skill_name == "file_manager":
                from skills.file_manager import FileManager
                skill = self._get_skill("file_manager", FileManager)
                return skill.handle(user_input)

            elif skill_name == "app_launcher":
                from skills.app_launcher import AppLauncher
                skill = self._get_skill("app_launcher", AppLauncher)
                return skill.handle(user_input)

            elif skill_name == "system_control":
                from skills.system_control import SystemControl
                skill = self._get_skill("system_control", SystemControl)
                return skill.handle(user_input)

            elif skill_name == "web_search":
                from skills.web_search import WebSearch
                skill = self._get_skill("web_search", WebSearch)
                return skill.handle(user_input)

            elif skill_name == "code_writer":
                from skills.code_writer import CodeWriter
                skill = self._get_skill("code_writer", CodeWriter)
                return skill.handle(user_input)

            elif skill_name == "resume_updater":
                from skills.resume_updater import ResumeUpdater
                skill = self._get_skill("resume_updater", ResumeUpdater)
                return skill.handle(user_input)

            elif skill_name == "phone_skills":
                from phone.phone_skills import PhoneSkills
                skill = self._get_skill("phone_skills", PhoneSkills)
                return skill.handle(user_input)

        except Exception as e:
            logger.error(f"Skill '{skill_name}' execution error: {e}")
            return f"Error executing skill: {e}"

        return None

    def _get_skill(self, name: str, skill_class):
        """Cache skill instances."""
        if name not in self._skills_cache:
            self._skills_cache[name] = skill_class()
        return self._skills_cache[name]

    def _ask_llm(self, user_input: str, system_prompt: str) -> str:
        """Send a prompt to Groq API or Ollama and return the response."""
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self.context.get_messages())
        messages.append({"role": "user", "content": user_input})

        if self.provider == "groq":
            return self._ask_groq(messages)
        else:
            return self._ask_ollama(messages)

    def _ask_groq(self, messages: List[Dict[str, str]]) -> str:
        """Query Groq API endpoint."""
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            # Fallback to Ollama if configured or return error
            return f"Groq API error: {e}"

    def _ask_ollama(self, messages: List[Dict[str, str]]) -> str:
        """Query local Ollama instance."""
        try:
            response = requests.post(
                f"{self.ollama_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": self.temperature,
                        "num_predict": self.max_tokens,
                    },
                },
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            return data["message"]["content"].strip()
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            return f"I encountered an error: {e}"

    def _build_system_prompt(self, lang_instruction: str, memory_context: str) -> str:
        """Build the full system prompt with language and memory context."""
        parts = [self.system_prompt.strip(), f"\n{lang_instruction}"]
        if memory_context:
            parts.append(f"\n{memory_context}")
        return "\n".join(parts)

    def check_ollama(self) -> bool:
        """Check LLM connection status (Groq or Ollama)."""
        if self.provider == "groq":
            if not self.groq_api_key:
                logger.warning("Groq API key missing in settings.yaml!")
                return False
            logger.info(f"Groq provider ready with model '{self.model}'.")
            return True
        else:
            try:
                r = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
                r.raise_for_status()
                models = [m["name"] for m in r.json().get("models", [])]
                if not any(self.model in m for m in models):
                    logger.warning(f"Model '{self.model}' not found in Ollama.")
                    return False
                logger.info(f"Ollama OK. Model '{self.model}' available.")
                return True
            except Exception as e:
                logger.error(f"Ollama check failed: {e}")
                return False
