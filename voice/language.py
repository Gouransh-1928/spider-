"""
SPIDER — Language Detection
Detects whether input is Hindi, English, or Hinglish (mixed).
Also formats SPIDER's multilingual responses.
"""
import re
from typing import Literal

from loguru import logger

try:
    from langdetect import detect, detect_langs, LangDetectException
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False
    logger.warning("langdetect not installed. Defaulting to English.")

# Common Hinglish indicator words (devanagari + transliteration)
HINDI_INDICATORS = {
    "kya", "hai", "haan", "nahi", "theek", "acha", "bahut", "mujhe",
    "mera", "tera", "tum", "aap", "yeh", "woh", "kar", "karo", "bolo",
    "chalao", "kholo", "band", "suno", "dekho", "batao", "lao",
    "abhi", "jaldi", "thoda", "zyada", "sirf", "bas", "phir",
}

LanguageCode = Literal["en", "hi", "hinglish"]


def detect_language(text: str) -> LanguageCode:
    """
    Detect the language of the input text.
    Returns: 'en', 'hi', or 'hinglish'
    """
    if not text or not text.strip():
        return "en"

    # Check for Devanagari script → definitely Hindi
    if re.search(r'[\u0900-\u097F]', text):
        return "hi"

    # Check for Hinglish indicators in Latin script
    words = set(text.lower().split())
    hindi_word_count = len(words.intersection(HINDI_INDICATORS))
    
    if hindi_word_count >= 2:
        return "hinglish"
    elif hindi_word_count == 1:
        # Borderline — try langdetect
        if LANGDETECT_AVAILABLE:
            try:
                langs = detect_langs(text)
                for lang in langs:
                    if lang.lang == "hi" and lang.prob > 0.3:
                        return "hinglish"
            except LangDetectException:
                pass

    # Use langdetect for pure English vs Hindi detection
    if LANGDETECT_AVAILABLE:
        try:
            lang = detect(text)
            if lang == "hi":
                return "hi"
        except LangDetectException:
            pass

    return "en"


def get_response_language_instruction(detected_lang: LanguageCode) -> str:
    """
    Returns instruction for the LLM on what language/style to reply in.
    """
    instructions = {
        "en": (
            "Reply in English. Be natural and conversational."
        ),
        "hi": (
            "Reply in Hindi (Devanagari script is fine, or Roman Hindi). "
            "Be natural and friendly. You can mix a few English technical terms."
        ),
        "hinglish": (
            "Reply in a natural Hinglish mix — blend Hindi and English casually, "
            "the way young Indians naturally speak. Example: 'Haan bilkul! "
            "Main aapke liye yeh folder create kar deta hoon.' "
            "Don't force either language; let it flow naturally."
        ),
    }
    return instructions.get(detected_lang, instructions["en"])
