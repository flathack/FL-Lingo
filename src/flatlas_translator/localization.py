"""Helpers for loading UI translations from disk."""

from __future__ import annotations

import json
import sys
from pathlib import Path


LANGUAGE_OPTIONS: tuple[tuple[str, str], ...] = (
    ("en", "English"),
    ("de", "Deutsch"),
    ("fr", "Francais"),
    ("es", "Espanol"),
    ("ru", "Russkiy"),
)


def resolve_languages_dir() -> Path:
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        for candidate in (
            exe_dir / "Languages",
            exe_dir / "_internal" / "Languages",
        ):
            if candidate.is_dir():
                return candidate
        return exe_dir / "Languages"
    return Path(__file__).resolve().parent.parent.parent / "Languages"


def resolve_help_file(language_code: str) -> Path:
    normalized = _normalize_language_code(language_code)
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        for candidate in (
            exe_dir / "data" / "help" / f"help.{normalized}.html",
            exe_dir / "_internal" / "data" / "help" / f"help.{normalized}.html",
        ):
            if candidate.is_file():
                return candidate
        return exe_dir / "data" / "help" / f"help.{normalized}.html"
    return Path(__file__).resolve().parent.parent.parent / "data" / "help" / f"help.{normalized}.html"


def load_ui_translations(fallback_strings: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
    languages_dir = resolve_languages_dir()
    loaded: dict[str, dict[str, str]] = {lang: dict(strings) for lang, strings in fallback_strings.items()}
    if not languages_dir.is_dir():
        return loaded
    for language_code, _label in LANGUAGE_OPTIONS:
        file_path = languages_dir / f"ui.{language_code}.json"
        if not file_path.is_file():
            continue
        payload = json.loads(file_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            loaded[language_code] = {str(key): str(value) for key, value in payload.items()}
    return loaded


def _normalize_language_code(language_code: str) -> str:
    normalized = str(language_code or "en").strip().lower()
    return normalized or "en"
