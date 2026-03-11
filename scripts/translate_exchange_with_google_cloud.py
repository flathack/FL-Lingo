#!/usr/bin/env python3
"""Translate FL Lingo exchange files with Google Cloud Translation.

This script is intentionally separate from FL Lingo itself.

Setup:
    pip install -U google-cloud-translate
    gcloud auth application-default login
    set GOOGLE_CLOUD_PROJECT=your-project-id

Example:
    python scripts/translate_exchange_with_google_cloud.py ^
        --input build\\long-open-entries-exchange.json ^
        --output build\\long-open-entries-exchange.translated.json ^
        --source-language-code en ^
        --target-language-code de

Notes:
    - Only entries with an empty ``translation_text`` are translated.
    - The script keeps the JSON structure intact and only fills
      ``translation_text``.
    - If an entry contains RDL/XML-like tags, the script conservatively
      translates only ``<TEXT>...</TEXT>`` segments by default.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

try:
    from google.cloud import translate_v3
except ImportError as exc:  # pragma: no cover - runtime guidance only
    raise SystemExit(
        "Missing dependency: google-cloud-translate\n"
        "Install it with:\n"
        "  pip install -U google-cloud-translate"
    ) from exc


DEFAULT_BATCH_SIZE = 32
DEFAULT_RETRIES = 3
TEXT_TAG_PATTERN = re.compile(r"(<TEXT>)(.*?)(</TEXT>)", re.IGNORECASE | re.DOTALL)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Path to the FL Lingo exchange JSON.")
    parser.add_argument("--output", help="Path for the translated output JSON.")
    parser.add_argument(
        "--project-id",
        default=os.environ.get("GOOGLE_CLOUD_PROJECT", ""),
        help="Google Cloud project id. Defaults to GOOGLE_CLOUD_PROJECT.",
    )
    parser.add_argument(
        "--location",
        default="global",
        help="Cloud Translation location. Default: global",
    )
    parser.add_argument(
        "--source-language-code",
        default="en",
        help="BCP-47 source language code. Default: en",
    )
    parser.add_argument(
        "--target-language-code",
        default="de",
        help="BCP-47 target language code. Default: de",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"How many plain text entries to translate per request. Default: {DEFAULT_BATCH_SIZE}",
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
        "--translate-markup-whole",
        action="store_true",
        help=(
            "Translate markup-containing entries as one whole text/html block. "
            "Default behavior is conservative and only translates <TEXT>...</TEXT> segments."
        ),
    )
    return parser.parse_args()


def load_exchange(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"Input file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}") from exc


def output_path_for(input_path: Path, explicit_output: str | None, overwrite: bool) -> Path:
    if overwrite:
        return input_path
    if explicit_output:
        return Path(explicit_output)
    return input_path.with_name(f"{input_path.stem}.translated{input_path.suffix}")


def pending_entries(exchange: dict[str, Any]) -> list[dict[str, Any]]:
    entries = exchange.get("entries")
    if not isinstance(entries, list):
        raise SystemExit("Exchange JSON has no valid 'entries' list.")
    return [
        entry
        for entry in entries
        if isinstance(entry, dict) and not str(entry.get("translation_text", "")).strip()
    ]


def translate_batch(
    client: translate_v3.TranslationServiceClient,
    *,
    parent: str,
    contents: list[str],
    source_language_code: str,
    target_language_code: str,
    mime_type: str,
    retries: int,
) -> list[str]:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            response = client.translate_text(
                request={
                    "parent": parent,
                    "contents": contents,
                    "mime_type": mime_type,
                    "source_language_code": source_language_code,
                    "target_language_code": target_language_code,
                }
            )
            return [item.translated_text for item in response.translations]
        except Exception as exc:  # pragma: no cover - network/runtime
            last_error = exc
            if attempt < retries:
                time.sleep(min(2 * attempt, 5))
    raise SystemExit(f"Google Cloud Translation failed: {last_error}")


def has_markup(text: str) -> bool:
    return "<" in text and ">" in text


def translate_rdl_text_segments(
    client: translate_v3.TranslationServiceClient,
    *,
    parent: str,
    text: str,
    source_language_code: str,
    target_language_code: str,
    retries: int,
) -> str:
    matches = list(TEXT_TAG_PATTERN.finditer(text))
    if not matches:
        return text

    segments = [match.group(2) for match in matches]
    translated_segments = translate_batch(
        client,
        parent=parent,
        contents=segments,
        source_language_code=source_language_code,
        target_language_code=target_language_code,
        mime_type="text/plain",
        retries=retries,
    )

    rebuilt: list[str] = []
    last_end = 0
    for match, translated in zip(matches, translated_segments, strict=True):
        rebuilt.append(text[last_end:match.start()])
        rebuilt.append(match.group(1))
        rebuilt.append(translated)
        rebuilt.append(match.group(3))
        last_end = match.end()
    rebuilt.append(text[last_end:])
    return "".join(rebuilt)


def translate_entries(
    exchange: dict[str, Any],
    *,
    project_id: str,
    location: str,
    source_language_code: str,
    target_language_code: str,
    batch_size: int,
    retries: int,
    translate_markup_whole: bool,
) -> tuple[int, int]:
    if not project_id:
        raise SystemExit(
            "Missing Google Cloud project id.\n"
            "Set GOOGLE_CLOUD_PROJECT or pass --project-id."
        )

    client = translate_v3.TranslationServiceClient()
    parent = f"projects/{project_id}/locations/{location}"
    entries = pending_entries(exchange)
    total = len(entries)
    if total == 0:
        return 0, 0

    translated_count = 0

    plain_entries: list[dict[str, Any]] = []
    markup_entries: list[dict[str, Any]] = []
    for entry in entries:
        text = str(entry.get("source_text", ""))
        if has_markup(text):
            markup_entries.append(entry)
        else:
            plain_entries.append(entry)

    for index in range(0, len(plain_entries), batch_size):
        chunk = plain_entries[index : index + batch_size]
        contents = [str(entry.get("source_text", "")) for entry in chunk]
        translated = translate_batch(
            client,
            parent=parent,
            contents=contents,
            source_language_code=source_language_code,
            target_language_code=target_language_code,
            mime_type="text/plain",
            retries=retries,
        )
        for entry, translated_text in zip(chunk, translated, strict=True):
            entry["translation_text"] = translated_text
            translated_count += 1
        print(f"[plain] {translated_count}/{total}", flush=True)

    for entry in markup_entries:
        text = str(entry.get("source_text", ""))
        if translate_markup_whole:
            translated_text = translate_batch(
                client,
                parent=parent,
                contents=[text],
                source_language_code=source_language_code,
                target_language_code=target_language_code,
                mime_type="text/html",
                retries=retries,
            )[0]
        else:
            translated_text = translate_rdl_text_segments(
                client,
                parent=parent,
                text=text,
                source_language_code=source_language_code,
                target_language_code=target_language_code,
                retries=retries,
            )
        entry["translation_text"] = translated_text
        translated_count += 1
        print(f"[markup] {translated_count}/{total}", flush=True)

    return translated_count, total


def save_exchange(path: Path, exchange: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(exchange, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    output_path = output_path_for(input_path, args.output, args.overwrite)

    exchange = load_exchange(input_path)
    translated_count, total = translate_entries(
        exchange,
        project_id=args.project_id,
        location=args.location,
        source_language_code=args.source_language_code,
        target_language_code=args.target_language_code,
        batch_size=max(1, args.batch_size),
        retries=max(1, args.retries),
        translate_markup_whole=args.translate_markup_whole,
    )
    save_exchange(output_path, exchange)

    print(f"Translated {translated_count} of {total} pending entries.")
    print(f"Wrote output to: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
