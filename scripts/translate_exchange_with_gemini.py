#!/usr/bin/env python3
"""Translate FL Lingo exchange files with the Google Gemini API.

This script is intentionally separate from FL Lingo itself.

Setup:
    pip install -U google-genai
    set GEMINI_API_KEY=your_key_here

Example:
    python scripts/translate_exchange_with_gemini.py ^
        --input build\\long-open-entries-exchange.json ^
        --output build\\long-open-entries-exchange.translated.json ^
        --target-language German

Notes:
    - Only entries with an empty ``translation_text`` are sent for translation.
    - The script keeps the JSON structure intact and only fills ``translation_text``.
    - XML/RDL tags inside ``source_text`` must be preserved by the model.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, TypedDict

try:
    from google import genai
    from google.genai import types
except ImportError as exc:  # pragma: no cover - runtime guidance only
    raise SystemExit(
        "Missing dependency: google-genai\n"
        "Install it with:\n"
        "  pip install -U google-genai"
    ) from exc


DEFAULT_MODEL = "gemini-2.0-flash"
DEFAULT_BATCH_SIZE = 8
DEFAULT_RETRIES = 3


class TranslationResult(TypedDict):
    index: int
    translation_text: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Path to the FL Lingo exchange JSON.")
    parser.add_argument("--output", help="Path for the translated output JSON.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Gemini model to use. Default: {DEFAULT_MODEL}")
    parser.add_argument(
        "--target-language",
        default="German",
        help="Human-readable target language name for the prompt. Default: German",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"How many entries to translate per request. Default: {DEFAULT_BATCH_SIZE}",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=DEFAULT_RETRIES,
        help=f"Retries per batch on API failure. Default: {DEFAULT_RETRIES}",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite the input file instead of creating a separate output file.",
    )
    parser.add_argument(
        "--only-empty",
        action="store_true",
        default=True,
        help="Translate only entries with an empty translation_text (default behavior).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input).resolve()
    if not input_path.is_file():
        raise SystemExit(f"Input file not found: {input_path}")

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("Environment variable GEMINI_API_KEY is not set.")

    output_path = resolve_output_path(input_path, args.output, overwrite=args.overwrite)
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    entries = payload.get("entries", [])
    if not isinstance(entries, list):
        raise SystemExit("Invalid exchange file: 'entries' must be a list.")

    glossary = payload.get("glossary", [])
    translatable_indexes = collect_translatable_indexes(entries)
    if not translatable_indexes:
        print("No empty translation_text entries found.")
        output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return 0

    client = genai.Client(api_key=api_key)
    batches = chunked(translatable_indexes, max(1, int(args.batch_size)))
    total = len(translatable_indexes)
    translated = 0

    for batch_number, batch_indexes in enumerate(batches, start=1):
        batch_entries = [entries[index] for index in batch_indexes]
        results = translate_batch(
            client=client,
            model=args.model,
            batch_entries=batch_entries,
            batch_indexes=batch_indexes,
            glossary=glossary,
            target_language=args.target_language,
            retries=max(1, int(args.retries)),
        )
        for item in results:
            index = int(item["index"])
            translation_text = str(item["translation_text"]).strip()
            if 0 <= index < len(entries) and translation_text:
                entries[index]["translation_text"] = translation_text
        translated += len(batch_indexes)
        print(f"[{batch_number}/{len(batches)}] translated {translated}/{total} entries")

    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Written: {output_path}")
    return 0


def resolve_output_path(input_path: Path, output_arg: str | None, *, overwrite: bool) -> Path:
    if overwrite:
        return input_path
    if output_arg:
        return Path(output_arg).resolve()
    return input_path.with_name(f"{input_path.stem}.translated{input_path.suffix}")


def collect_translatable_indexes(entries: list[dict[str, Any]]) -> list[int]:
    indexes: list[int] = []
    for index, entry in enumerate(entries):
        source_text = str(entry.get("source_text", "") or "").strip()
        translation_text = str(entry.get("translation_text", "") or "").strip()
        if not source_text:
            continue
        if translation_text:
            continue
        indexes.append(index)
    return indexes


def chunked(items: list[int], size: int) -> list[list[int]]:
    return [items[pos : pos + size] for pos in range(0, len(items), size)]


def translate_batch(
    *,
    client: genai.Client,
    model: str,
    batch_entries: list[dict[str, Any]],
    batch_indexes: list[int],
    glossary: list[dict[str, Any]],
    target_language: str,
    retries: int,
) -> list[TranslationResult]:
    prompt = build_prompt(
        batch_entries=batch_entries,
        batch_indexes=batch_indexes,
        glossary=glossary,
        target_language=target_language,
    )
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    response_mime_type="application/json",
                    response_schema=list[TranslationResult],
                ),
            )
            data = json.loads(response.text)
            if not isinstance(data, list):
                raise ValueError("Model did not return a JSON array.")
            return normalize_results(data, expected_indexes=batch_indexes)
        except Exception as exc:  # pragma: no cover - network/API path
            last_error = exc
            if attempt >= retries:
                break
            time.sleep(min(8, 1.5 * attempt))
    raise RuntimeError(f"Gemini batch translation failed after {retries} attempts: {last_error}")


def build_prompt(
    *,
    batch_entries: list[dict[str, Any]],
    batch_indexes: list[int],
    glossary: list[dict[str, Any]],
    target_language: str,
) -> str:
    glossary_lines: list[str] = []
    for item in glossary[:120]:
        source_term = str(item.get("source_term", "")).strip()
        target_term = str(item.get("target_term", "")).strip()
        if source_term and target_term:
            glossary_lines.append(f"- {source_term} => {target_term}")

    payload_entries = []
    for index, entry in zip(batch_indexes, batch_entries, strict=True):
        payload_entries.append(
            {
                "index": index,
                "dll_name": entry.get("dll_name", ""),
                "kind": entry.get("kind", ""),
                "source_text": entry.get("source_text", ""),
                "suggested_text": entry.get("suggested_text", ""),
            }
        )

    rules = [
        f"Translate the source_text values into {target_language}.",
        "Return only a JSON array of objects with: index, translation_text.",
        "Preserve XML, RDL, HTML, and tag structure exactly.",
        "Do not change IDs, order, dll_name, or any JSON structure outside translation_text.",
        "Use the glossary consistently when a glossary term appears.",
        "Keep names of people unchanged unless there is a clear established localized form in the glossary.",
        "If a text is already partially localized in suggested_text, you may use it as a hint, but improve it if needed.",
        "Do not explain anything. Do not wrap the JSON in markdown.",
    ]

    parts = [
        "You are translating FL Lingo exchange entries for Freelancer mod relocalization.",
        "Rules:",
        *[f"{idx}. {rule}" for idx, rule in enumerate(rules, start=1)],
    ]
    if glossary_lines:
        parts.append("\nGlossary hints:")
        parts.extend(glossary_lines)
    parts.append("\nEntries:")
    parts.append(json.dumps(payload_entries, ensure_ascii=False, indent=2))
    return "\n".join(parts)


def normalize_results(data: list[Any], *, expected_indexes: list[int]) -> list[TranslationResult]:
    expected = set(expected_indexes)
    normalized: list[TranslationResult] = []
    seen: set[int] = set()
    for item in data:
        if not isinstance(item, dict):
            continue
        try:
            index = int(item.get("index"))
        except Exception:
            continue
        if index not in expected or index in seen:
            continue
        translation_text = str(item.get("translation_text", "") or "").strip()
        normalized.append({"index": index, "translation_text": translation_text})
        seen.add(index)
    missing = expected - seen
    if missing:
        raise ValueError(f"Missing translation results for indexes: {sorted(missing)}")
    return normalized


if __name__ == "__main__":
    raise SystemExit(main())
