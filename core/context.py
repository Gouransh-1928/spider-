"""
SPIDER — Session Context Manager
Maintains the current conversation history (short-term memory).
"""
from collections import deque
from typing import List, Dict, Any

from config.loader import CONFIG


class ConversationContext:
    """
    Manages short-term conversation context for the current session.
    Keeps the last N turns in memory for LLM context window.
    """

    def __init__(self):
        max_turns = CONFIG["brain"]["max_tokens"] // 200  # Rough estimate
        self.max_turns = CONFIG["memory"]["max_short_term_turns"]
        self._history: deque = deque(maxlen=self.max_turns * 2)  # user + assistant pairs

    def add_user(self, text: str) -> None:
        self._history.append({"role": "user", "content": text})

    def add_assistant(self, text: str) -> None:
        self._history.append({"role": "assistant", "content": text})

    def get_messages(self) -> List[Dict[str, str]]:
        """Return conversation history as list of message dicts."""
        return list(self._history)

    def clear(self) -> None:
        self._history.clear()

    def to_text(self) -> str:
        """Format history as readable text for LLM context."""
        lines = []
        for msg in self._history:
            prefix = "User" if msg["role"] == "user" else "SPIDER"
            lines.append(f"{prefix}: {msg['content']}")
        return "\n".join(lines)

    def __len__(self) -> int:
        return len(self._history)
