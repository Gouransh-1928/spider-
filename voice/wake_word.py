"""
SPIDER — Wake Word Detection
Listens continuously for "Hey SPIDER" using openwakeword.
Falls back to keyword matching if model not available.
"""
import queue
import threading
from typing import Callable, Optional

import numpy as np
import sounddevice as sd
from loguru import logger

from config.loader import CONFIG

try:
    import openwakeword
    from openwakeword.model import Model as WakeWordModel
    OPENWAKEWORD_AVAILABLE = True
except ImportError:
    OPENWAKEWORD_AVAILABLE = False
    logger.warning("openwakeword not installed. Using keyword fallback.")


class WakeWordDetector:
    """
    Listens for the wake phrase "Hey SPIDER".
    Primary: openwakeword neural model
    Fallback: faster-whisper keyword spotting
    """

    def __init__(self, on_detected: Callable = None):
        self.wake_word = CONFIG["voice"]["wake_word"].lower()
        self.on_detected = on_detected
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self.sample_rate = CONFIG["voice"]["sample_rate"]

        if OPENWAKEWORD_AVAILABLE:
            logger.info("Initializing openwakeword model...")
            try:
                self.wake_model = WakeWordModel(
                    wakeword_models=["hey_jarvis"],  # closest to "hey spider"
                    enable_speex_noise_suppression=False,
                    inference_framework="onnx",
                )
                self.use_openwakeword = True
                logger.info("openwakeword model loaded.")
            except Exception as e:
                logger.warning(f"openwakeword model load failed: {e}. Using fallback.")
                self.use_openwakeword = False
        else:
            self.use_openwakeword = False

    def start(self) -> None:
        """Start wake word detection in a background thread."""
        self.running = True
        self._thread = threading.Thread(target=self._detect_loop, daemon=True)
        self._thread.start()
        logger.info(f"Wake word detector started. Listening for: '{self.wake_word}'")

    def stop(self) -> None:
        """Stop wake word detection."""
        self.running = False
        if self._thread:
            self._thread.join(timeout=2)
        logger.info("Wake word detector stopped.")

    def _detect_loop(self) -> None:
        """Background loop — streams mic audio and checks for wake word."""
        audio_queue = queue.Queue()
        chunk_size = 1280  # 80ms at 16kHz

        def callback(indata, frames, time_info, status):
            audio_queue.put(indata.copy())

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="int16",
            blocksize=chunk_size,
            callback=callback,
        ):
            logger.info("🕷️  SPIDER is listening for wake word...")
            while self.running:
                try:
                    chunk = audio_queue.get(timeout=1.0)
                    chunk_flat = chunk.flatten()

                    if self.use_openwakeword:
                        detected = self._check_openwakeword(chunk_flat)
                    else:
                        detected = False  # Fallback handled externally

                    if detected:
                        logger.info("Wake word detected!")
                        if self.on_detected:
                            self.on_detected()
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"Wake word loop error: {e}")

    def _check_openwakeword(self, audio_chunk: np.ndarray) -> bool:
        """Check if wake word is present in audio chunk."""
        try:
            predictions = self.wake_model.predict(audio_chunk)
            # Check all wakeword scores
            for model_name, score in predictions.items():
                if score > 0.5:  # Confidence threshold
                    return True
        except Exception as e:
            logger.debug(f"openwakeword prediction error: {e}")
        return False

    def wait_for_wake_word_text(self, text: str) -> bool:
        """
        Fallback: check if transcribed text contains the wake word.
        Used when openwakeword is not available.
        """
        return self.wake_word in text.lower()
