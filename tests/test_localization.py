from __future__ import annotations

import json
from pathlib import Path

from flatlas_translator.localization import load_ui_translations, resolve_help_file, resolve_languages_dir
from flatlas_translator.ui_strings import STRINGS


def test_load_ui_translations_reads_language_files() -> None:
    fallback = {
        "en": {"hello": "Hello"},
        "de": {"hello": "Hallo"},
    }
    loaded = load_ui_translations(fallback)
    assert "en" in loaded
    assert "de" in loaded
    assert "fr" in loaded
    assert loaded["en"]["menu.help"] == "Help"
    assert loaded["de"]["menu.help"] == "Hilfe"


def test_resolve_languages_dir_exists() -> None:
    languages_dir = resolve_languages_dir()
    assert languages_dir.is_dir()
    assert (languages_dir / "ui.en.json").is_file()


def test_resolve_help_file_prefers_language_and_has_fallback_files() -> None:
    assert resolve_help_file("en") == Path(resolve_help_file("en"))
    assert resolve_help_file("de").is_file()


def test_external_ui_language_files_only_override_known_keys() -> None:
    languages_dir = resolve_languages_dir()
    for path in languages_dir.glob("ui.*.json"):
        lang = path.stem.split(".")[-1]
        overrides = json.loads(path.read_text())
        assert lang in STRINGS, f"unexpected language file: {path.name}"
        assert set(overrides).issubset(STRINGS[lang]), f"unknown translation keys in {path.name}"
        assert all(isinstance(value, str) for value in overrides.values()), f"non-string values in {path.name}"
