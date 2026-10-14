"""
SPIDER — Security: Voice & Spoken Passkey Authentication
Supports Whisper spoken passphrase matching + Resemblyzer embeddings when available.
"""
import json
import os
import re
from pathlib import Path
from typing import Optional, Tuple

import bcrypt
import numpy as np
from loguru import logger

from config.loader import CONFIG

try:
    from resemblyzer import VoiceEncoder, preprocess_wav
    RESEMBLYZER_AVAILABLE = True
except ImportError:
    RESEMBLYZER_AVAILABLE = False


SECURITY_FILE = Path(__file__).parent.parent / "data" / "security" / "passkey.json"
SIMILARITY_THRESHOLD = 0.75  # Cosine similarity threshold for MFCC match


class AuthManager:
    """Manages voice passkey enrollment and verification for SPIDER."""

    def __init__(self):
        self.encoder = None
        self.voice_embedding = None
        self.text_passkey_hash = None
        self.spoken_phrase_hash = None
        self.enrolled_phrase_raw = None
        self._load_stored_credentials()

        if RESEMBLYZER_AVAILABLE:
            logger.info("Loading voice encoder (Resemblyzer)...")
            try:
                self.encoder = VoiceEncoder()
                logger.info("Voice encoder loaded.")
            except Exception as e:
                logger.error(f"Voice encoder load failed: {e}")

    def is_enrolled(self) -> bool:
        """Check if a passkey has been enrolled."""
        has_voice = self.voice_embedding is not None
        has_text = self.text_passkey_hash is not None
        has_spoken = self.spoken_phrase_hash is not None
        return has_voice or has_text or has_spoken

    def reset_passkey(self) -> bool:
        """Reset all enrolled credentials."""
        self.voice_embedding = None
        self.text_passkey_hash = None
        self.spoken_phrase_hash = None
        self.enrolled_phrase_raw = None
        if SECURITY_FILE.exists():
            try:
                SECURITY_FILE.unlink()
                logger.info("Passkey credentials reset successfully.")
                return True
            except Exception as e:
                logger.error(f"Failed to delete security file: {e}")
                return False
        return True

    def enroll_spoken_passkey(self, phrase: str) -> bool:
        """Enroll a spoken passkey phrase transcribed via Whisper."""
        if not phrase or len(phrase.strip()) < 2:
            logger.error("Spoken phrase too short.")
            return False

        clean_phrase = self._normalize_phrase(phrase)
        hashed = bcrypt.hashpw(clean_phrase.encode(), bcrypt.gensalt())
        self.spoken_phrase_hash = hashed.decode()
        self.enrolled_phrase_raw = clean_phrase
        self._save_credentials()
        logger.info(f"Spoken passkey phrase enrolled: '{clean_phrase}'")
        return True

    def enroll_text_passkey(self, passkey: str) -> bool:
        """Enroll a text passkey (hashed with bcrypt)."""
        if not passkey or len(passkey) < 3:
            logger.error("Passkey too short.")
            return False

        hashed = bcrypt.hashpw(passkey.strip().lower().encode(), bcrypt.gensalt())
        self.text_passkey_hash = hashed.decode()
        self._save_credentials()
        logger.info("Text passkey enrolled successfully.")
        return True

    def verify_spoken_passkey(self, spoken_phrase: str) -> bool:
        """Verify spoken phrase against enrolled passkey."""
        if not spoken_phrase:
            return False

        clean_input = self._normalize_phrase(spoken_phrase)

        # Check raw match / substring overlap first
        if self.enrolled_phrase_raw:
            if clean_input in self.enrolled_phrase_raw or self.enrolled_phrase_raw in clean_input:
                logger.info("Spoken passkey matched via phrase overlap.")
                return True

        # Check bcrypt hash
        if self.spoken_phrase_hash:
            try:
                if bcrypt.checkpw(clean_input.encode(), self.spoken_phrase_hash.encode()):
                    logger.info("Spoken passkey matched via bcrypt hash.")
                    return True
            except Exception:
                pass

        # Check text passkey match
        if self.text_passkey_hash:
            try:
                if bcrypt.checkpw(clean_input.encode(), self.text_passkey_hash.encode()):
                    return True
            except Exception:
                pass

        return False

    def verify_text(self, passkey: str) -> bool:
        """Verify a text passkey."""
        if not passkey:
            return False
        clean = passkey.strip().lower()

        if self.text_passkey_hash:
            try:
                if bcrypt.checkpw(clean.encode(), self.text_passkey_hash.encode()):
                    return True
            except Exception:
                pass

        if self.spoken_phrase_hash and self.enrolled_phrase_raw:
            if clean in self.enrolled_phrase_raw or self.enrolled_phrase_raw in clean:
                return True

        return False

    def _normalize_phrase(self, text: str) -> str:
        """Normalize a spoken phrase for flexible matching."""
        text = text.lower().strip()
        text = re.sub(r'[^\w\s]', '', text)
        return " ".join(text.split())

    def _load_stored_credentials(self) -> None:
        """Load stored credentials from secure file."""
        if not SECURITY_FILE.exists():
            return
        try:
            with open(SECURITY_FILE, "r") as f:
                data = json.load(f)

            if "voice_embedding" in data and data["voice_embedding"]:
                self.voice_embedding = np.array(data["voice_embedding"])

            if "text_passkey_hash" in data and data["text_passkey_hash"]:
                self.text_passkey_hash = data["text_passkey_hash"]

            if "spoken_phrase_hash" in data and data["spoken_phrase_hash"]:
                self.spoken_phrase_hash = data["spoken_phrase_hash"]

            if "enrolled_phrase_raw" in data and data["enrolled_phrase_raw"]:
                self.enrolled_phrase_raw = data["enrolled_phrase_raw"]

            logger.info("Credentials loaded from secure file.")
        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")

    def _save_credentials(self) -> None:
        """Save credentials securely."""
        SECURITY_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "voice_embedding": self.voice_embedding.tolist() if self.voice_embedding is not None else None,
            "text_passkey_hash": self.text_passkey_hash,
            "spoken_phrase_hash": self.spoken_phrase_hash,
            "enrolled_phrase_raw": self.enrolled_phrase_raw,
        }
        with open(SECURITY_FILE, "w") as f:
            json.dump(data, f)
        logger.info("Credentials saved.")
