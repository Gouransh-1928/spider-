"""
SPIDER — Text-to-Speech (TTS) Speaker
Uses edge-tts for Microsoft Neural female voice.
"""
import asyncio
import os
import tempfile
from pathlib import Path

import edge_tts
import pygame
from loguru import logger

from config.loader import CONFIG


class Speaker:
    """SPIDER's voice output — female neutral American accent via edge-tts."""

    def __init__(self):
        self.voice = CONFIG["voice"]["tts_voice"]
        self.rate = CONFIG["voice"]["tts_rate"]
        self.volume = CONFIG["voice"]["tts_volume"]
        pygame.mixer.init()
        logger.info(f"Speaker initialized. Voice: {self.voice}")

    def speak(self, text: str) -> None:
        """
        Convert text to speech and play it.
        Runs async edge-tts in a sync context.
        """
        logger.info(f"SPIDER says: {text}")
        print(f"\n🕷️  SPIDER: {text}\n")

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._speak_async(text))
        except Exception as e:
            logger.error(f"TTS error: {e}")
            # Fallback: just print
            print(f"[TTS FALLBACK] {text}")
        finally:
            loop.close()

    async def _speak_async(self, text: str) -> None:
        """Async TTS generation and playback."""
        communicate = edge_tts.Communicate(
            text=text,
            voice=self.voice,
            rate=self.rate,
            volume=self.volume,
        )

        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            await communicate.save(tmp_path)
            self._play_audio(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    def _play_audio(self, audio_path: str) -> None:
        """Play audio file using pygame."""
        try:
            pygame.mixer.music.load(audio_path)
            pygame.mixer.music.play()
            # Wait until finished
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
        finally:
            try:
                pygame.mixer.music.unload()
            except Exception:
                pass

    def __del__(self):
        try:
            pygame.mixer.quit()
        except Exception:
            pass
