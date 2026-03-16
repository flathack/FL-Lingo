"""External translation service integration for FL Lingo."""

from __future__ import annotations


def translate_text(text: str, source_lang: str, target_lang: str, provider: str = "google") -> str:
    """Translate *text* from *source_lang* to *target_lang* using the specified provider.

    Currently supported providers:
      - ``"google"`` – free Google Translate via *deep-translator* (no API key).

    Returns the translated string, or raises on error.
    """
    if not text.strip():
        return text

    if provider == "google":
        return _translate_google(text, source_lang, target_lang)

    raise ValueError(f"Unknown translation provider: {provider}")


def _translate_google(text: str, source_lang: str, target_lang: str) -> str:
    from deep_translator import GoogleTranslator  # lazy import

    translator = GoogleTranslator(source=source_lang, target=target_lang)
    return translator.translate(text)
