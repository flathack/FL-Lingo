from __future__ import annotations

from pathlib import Path

from flatlas_translator.localization import load_ui_translations, resolve_help_file, resolve_languages_dir


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
