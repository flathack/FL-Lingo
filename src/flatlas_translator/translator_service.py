"""External translation service integration for FL Lingo."""

from __future__ import annotations

import re

_BATCH_SEPARATOR = "\n\n[FLSEP]\n\n"
_BATCH_SPLIT_RE = re.compile(r"\s*\[FLSEP\]\s*")
_MAX_BATCH_CHARS = 4500


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


def translate_text_batch(
    texts: list[str],
    source_lang: str,
    target_lang: str,
    provider: str = "google",
) -> list[str | Exception]:
    """Translate multiple texts by concatenating into batched API requests.

    Groups texts into sub-batches respecting the character limit, concatenates
    them with a separator, and translates each sub-batch in a single request.
    Falls back to individual translation when the separator is not preserved.

    Returns a list matching the input order.  Each element is either the
    translated string or an ``Exception`` if that text failed.
    """
    if provider == "google":
        return _translate_google_batch(texts, source_lang, target_lang)

    # Fallback for other providers: translate individually
    results: list[str | Exception] = []
    for text in texts:
        try:
            results.append(translate_text(text, source_lang, target_lang, provider))
        except Exception as exc:
            results.append(exc)
    return results


def _translate_google(text: str, source_lang: str, target_lang: str) -> str:
    from deep_translator import GoogleTranslator  # lazy import

    translator = GoogleTranslator(source=source_lang, target=target_lang)
    return translator.translate(text)


def _translate_google_batch(
    texts: list[str],
    source_lang: str,
    target_lang: str,
) -> list[str | Exception]:
    from deep_translator import GoogleTranslator

    translator = GoogleTranslator(source=source_lang, target=target_lang)
    results: list[str | Exception] = [""] * len(texts)

    # Group texts into sub-batches that fit the character limit
    sub_batches: list[list[int]] = []
    current_indices: list[int] = []
    current_chars = 0

    for i, text in enumerate(texts):
        added = len(text) + (len(_BATCH_SEPARATOR) if current_indices else 0)
        if current_chars + added > _MAX_BATCH_CHARS and current_indices:
            sub_batches.append(current_indices)
            current_indices = [i]
            current_chars = len(text)
        else:
            current_indices.append(i)
            current_chars += added
    if current_indices:
        sub_batches.append(current_indices)

    for indices in sub_batches:
        batch_texts = [texts[i] for i in indices]

        if len(batch_texts) == 1:
            try:
                results[indices[0]] = translator.translate(batch_texts[0])
            except Exception as exc:
                results[indices[0]] = exc
            continue

        combined = _BATCH_SEPARATOR.join(batch_texts)
        try:
            translated = translator.translate(combined)
        except Exception as exc:
            for idx in indices:
                results[idx] = exc
            continue

        parts = _BATCH_SPLIT_RE.split(translated)
        if len(parts) == len(batch_texts):
            for idx, part in zip(indices, parts):
                results[idx] = part.strip()
        else:
            # Separator was not preserved – fall back to individual calls
            for idx, text in zip(indices, batch_texts):
                try:
                    results[idx] = translator.translate(text)
                except Exception as exc:
                    results[idx] = exc

    return results
