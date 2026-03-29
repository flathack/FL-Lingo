"""External translation service integration for FL Lingo."""

from __future__ import annotations

import re

_BATCH_SEPARATOR = "\n\n[FLSEP]\n\n"
_BATCH_SPLIT_RE = re.compile(r"\s*\[FLSEP\]\s*")
_MAX_BATCH_CHARS = 4500

# RDL / XML protection: only translate inner text of <TEXT> nodes.
_RDL_DETECT_RE = re.compile(r"<RDL\b", re.IGNORECASE)
_RDL_TEXT_NODE_RE = re.compile(
    r"(<TEXT\b[^>]*>)(.*?)(</TEXT>)", re.IGNORECASE | re.DOTALL
)


def _is_rdl_text(text: str) -> bool:
    return bool(_RDL_DETECT_RE.search(text))


def _translate_rdl_aware(
    text: str, source_lang: str, target_lang: str, provider: str
) -> str:
    """Translate only the text content inside <TEXT> nodes, preserving RDL structure."""
    segments: list[str] = []

    def _collect(m: re.Match[str]) -> str:
        idx = len(segments)
        segments.append(m.group(2))
        return f"{m.group(1)}{{{{FLRDL_{idx}}}}}{m.group(3)}"

    protected = _RDL_TEXT_NODE_RE.sub(_collect, text)

    if not segments:
        return text

    translated_segments: list[str] = []
    for seg in segments:
        if not seg.strip():
            translated_segments.append(seg)
            continue
        if provider == "google":
            translated_segments.append(_translate_google(seg, source_lang, target_lang))
        else:
            raise ValueError(f"Unknown translation provider: {provider}")

    result = protected
    for i, translated in enumerate(translated_segments):
        result = result.replace(f"{{{{FLRDL_{i}}}}}", translated)
    return result


def _require_translated_text(value: object) -> str:
    if value is None:
        raise ValueError("Translation service returned no text.")
    if not isinstance(value, str):
        raise TypeError(f"Translation service returned {type(value).__name__}, expected str.")
    return value


def translate_text(text: str, source_lang: str, target_lang: str, provider: str = "google") -> str:
    """Translate *text* from *source_lang* to *target_lang* using the specified provider.

    Currently supported providers:
      - ``"google"`` – free Google Translate via *deep-translator* (no API key).

    RDL/XML infocard content is detected automatically: only the text inside
    ``<TEXT>`` nodes is translated while the surrounding XML structure is
    preserved unchanged.

    Returns the translated string, or raises on error.
    """
    if not text.strip():
        return text

    if _is_rdl_text(text):
        return _translate_rdl_aware(text, source_lang, target_lang, provider)

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

    RDL/XML infocard texts are handled individually so that only the inner
    ``<TEXT>`` content is translated while the XML structure stays intact.

    Returns a list matching the input order.  Each element is either the
    translated string or an ``Exception`` if that text failed.
    """
    # --- Pre-process: separate RDL texts from plain texts ---
    results: list[str | Exception] = [""] * len(texts)
    plain_indices: list[int] = []
    plain_texts: list[str] = []

    for i, text in enumerate(texts):
        if _is_rdl_text(text):
            try:
                results[i] = _translate_rdl_aware(text, source_lang, target_lang, provider)
            except Exception as exc:
                results[i] = exc
        else:
            plain_indices.append(i)
            plain_texts.append(text)

    if not plain_texts:
        return results

    # --- Batch-translate the plain (non-RDL) texts ---
    if provider == "google":
        plain_results = _translate_google_batch(plain_texts, source_lang, target_lang)
    else:
        plain_results = []
        for text in plain_texts:
            try:
                plain_results.append(translate_text(text, source_lang, target_lang, provider))
            except Exception as exc:
                plain_results.append(exc)

    for idx, result in zip(plain_indices, plain_results):
        results[idx] = result

    return results


def _translate_google(text: str, source_lang: str, target_lang: str) -> str:
    from deep_translator import GoogleTranslator  # lazy import

    translator = GoogleTranslator(source=source_lang, target=target_lang)
    return _require_translated_text(translator.translate(text))


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
                results[indices[0]] = _require_translated_text(translator.translate(batch_texts[0]))
            except Exception as exc:
                results[indices[0]] = exc
            continue

        combined = _BATCH_SEPARATOR.join(batch_texts)
        try:
            translated = _require_translated_text(translator.translate(combined))
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
                    results[idx] = _require_translated_text(translator.translate(text))
                except Exception as exc:
                    results[idx] = exc

    return results
