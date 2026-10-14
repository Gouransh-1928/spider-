"""
SPIDER — Speech-to-Text Listener
Uses faster-whisper for local, multilingual (Hindi + English) speech recognition.
"""
import io
import queue
import threading
import wave
from typing import Optional

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from loguru import logger

from config.loader import CONFIG


class Listener:
    """Local STT listener using faster-whisper — supports Hindi, English, Hinglish."""

    def __init__(self):
        cfg = CONFIG["voice"]
        self.sample_rate = cfg["sample_rate"]
        self.channels = cfg["channels"]
        self.silence_threshold = cfg["silence_threshold"]
        self.max_seconds = cfg["max_record_seconds"]
        self.language = cfg["stt_language"]  # "auto" or "hi" or "en"

        model_size = cfg["stt_model"]
        logger.info(f"Loading Whisper model: {model_size} (this may take a moment on first run)")
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        logger.info("Whisper model loaded.")

    def listen(self) -> Optional[str]:
        """
        Record from microphone until silence, then transcribe.
        Returns transcribed text or None on error.
        """
        logger.info("Listening...")
        print("🎤 Listening... (speak now)")

        try:
            audio_data = self._record_until_silence()
            if audio_data is None or len(audio_data) == 0:
                return None

            text = self._transcribe(audio_data)
            if text:
                logger.info(f"Heard: {text}")
                print(f"👤 You: {text}")
            return text

        except Exception as e:
            logger.error(f"Listener error: {e}")
            return None

    def _record_until_silence(self) -> Optional[np.ndarray]:
        """Record audio from microphone until silence is detected."""
        audio_queue = queue.Queue()
        frames = []
        silence_frames = 0
        speaking_started = False
        
        # Calculate silence threshold in frames
        block_size = 1024
        silence_blocks = int((self.silence_threshold / 1000) * self.sample_rate / block_size)
        max_blocks = int(self.max_seconds * self.sample_rate / block_size)
        
        def callback(indata, frame_count, time_info, status):
            audio_queue.put(indata.copy())

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="float32",
            blocksize=block_size,
            callback=callback,
        ):
            block_count = 0
            while block_count < max_blocks:
                try:
                    block = audio_queue.get(timeout=1.0)
                    rms = np.sqrt(np.mean(block**2))

                    if rms > 0.01:  # Speech detected
                        speaking_started = True
                        silence_frames = 0
                        frames.append(block)
                    elif speaking_started:
                        frames.append(block)
                        silence_frames += 1
                        if silence_frames >= silence_blocks:
                            break
                    
                    block_count += 1
                except queue.Empty:
                    if speaking_started:
                        break

        if not frames:
            return None

        return np.concatenate(frames, axis=0).flatten()

    def _transcribe(self, audio: np.ndarray) -> Optional[str]:
        """Transcribe audio array to text using faster-whisper."""
        try:
            # Convert float32 to int16 for whisper
            audio_int16 = (audio * 32768).astype(np.int16)
            audio_float = audio_int16.astype(np.float32) / 32768.0

            lang = None if self.language == "auto" else self.language
            segments, info = self.model.transcribe(
                audio_float,
                language=lang,
                beam_size=5,
                vad_filter=True,
            )

            text = " ".join(seg.text.strip() for seg in segments).strip()
            detected_lang = info.language
            logger.info(f"Detected language: {detected_lang} (confidence: {info.language_probability:.2f})")
            
            return text if text else None

        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return None
