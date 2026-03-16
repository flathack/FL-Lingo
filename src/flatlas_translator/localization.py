"""Helpers for loading UI translations from disk."""

from __future__ import annotations

import json
import sys
from pathlib import Path


LANGUAGE_OPTIONS: tuple[tuple[str, str], ...] = (
    ("en", "English"),
    ("de", "Deutsch"),
    ("fr", "Français"),
    ("es", "Español"),
    ("ru", "Русский"),
    ("af", "Afrikaans"),
    ("sq", "Shqip"),
    ("am", "አማርኛ"),
    ("ar", "العربية"),
    ("hy", "Հայերեն"),
    ("az", "Azərbaycan"),
    ("eu", "Euskara"),
    ("be", "Беларуская"),
    ("bn", "বাংলা"),
    ("bs", "Bosanski"),
    ("bg", "Български"),
    ("ca", "Català"),
    ("ceb", "Cebuano"),
    ("zh-CN", "中文 (简体)"),
    ("zh-TW", "中文 (繁體)"),
    ("co", "Corsu"),
    ("hr", "Hrvatski"),
    ("cs", "Čeština"),
    ("da", "Dansk"),
    ("nl", "Nederlands"),
    ("eo", "Esperanto"),
    ("et", "Eesti"),
    ("fi", "Suomi"),
    ("fy", "Frysk"),
    ("gl", "Galego"),
    ("ka", "ქართული"),
    ("el", "Ελληνικά"),
    ("gu", "ગુજરાતી"),
    ("ht", "Kreyòl Ayisyen"),
    ("ha", "Hausa"),
    ("haw", "ʻŌlelo Hawaiʻi"),
    ("he", "עברית"),
    ("hi", "हिन्दी"),
    ("hmn", "Hmong"),
    ("hu", "Magyar"),
    ("is", "Íslenska"),
    ("ig", "Igbo"),
    ("id", "Bahasa Indonesia"),
    ("ga", "Gaeilge"),
    ("it", "Italiano"),
    ("ja", "日本語"),
    ("jw", "Basa Jawa"),
    ("kn", "ಕನ್ನಡ"),
    ("kk", "Қазақ"),
    ("km", "ភាសាខ្មែរ"),
    ("rw", "Kinyarwanda"),
    ("ko", "한국어"),
    ("ku", "Kurdî"),
    ("ky", "Кыргызча"),
    ("lo", "ລາວ"),
    ("la", "Latina"),
    ("lv", "Latviešu"),
    ("lt", "Lietuvių"),
    ("lb", "Lëtzebuergesch"),
    ("mk", "Македонски"),
    ("mg", "Malagasy"),
    ("ms", "Bahasa Melayu"),
    ("ml", "മലയാളം"),
    ("mt", "Malti"),
    ("mi", "Te Reo Māori"),
    ("mr", "मराठी"),
    ("mn", "Монгол"),
    ("my", "မြန်မာ"),
    ("ne", "नेपाली"),
    ("no", "Norsk"),
    ("ny", "Chichewa"),
    ("or", "ଓଡ଼ିଆ"),
    ("ps", "پښتو"),
    ("fa", "فارسی"),
    ("pl", "Polski"),
    ("pt", "Português"),
    ("pa", "ਪੰਜਾਬੀ"),
    ("ro", "Română"),
    ("sm", "Gagana Sāmoa"),
    ("gd", "Gàidhlig"),
    ("sr", "Српски"),
    ("st", "Sesotho"),
    ("sn", "Shona"),
    ("sd", "سنڌي"),
    ("si", "සිංහල"),
    ("sk", "Slovenčina"),
    ("sl", "Slovenščina"),
    ("so", "Soomaali"),
    ("su", "Basa Sunda"),
    ("sw", "Kiswahili"),
    ("sv", "Svenska"),
    ("tl", "Tagalog"),
    ("tg", "Тоҷикӣ"),
    ("ta", "தமிழ்"),
    ("tt", "Татар"),
    ("te", "తెలుగు"),
    ("th", "ไทย"),
    ("tr", "Türkçe"),
    ("tk", "Türkmen"),
    ("uk", "Українська"),
    ("ur", "اردو"),
    ("ug", "ئۇيغۇرچە"),
    ("uz", "Oʻzbek"),
    ("vi", "Tiếng Việt"),
    ("cy", "Cymraeg"),
    ("xh", "isiXhosa"),
    ("yi", "ייִדיש"),
    ("yo", "Yorùbá"),
    ("zu", "isiZulu"),
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
    english_fallback = dict(fallback_strings.get("en", {}))
    loaded: dict[str, dict[str, str]] = {
        language_code: dict(english_fallback) for language_code, _label in LANGUAGE_OPTIONS
    }
    for lang, strings in fallback_strings.items():
        loaded[lang] = dict(english_fallback)
        loaded[lang].update(strings)
    if not languages_dir.is_dir():
        return loaded
    for language_code, _label in LANGUAGE_OPTIONS:
        file_path = languages_dir / f"ui.{language_code}.json"
        if not file_path.is_file():
            continue
        payload = json.loads(file_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            merged = dict(loaded.get(language_code, {}))
            merged.update({str(key): str(value) for key, value in payload.items()})
            loaded[language_code] = merged
    return loaded


def _normalize_language_code(language_code: str) -> str:
    normalized = str(language_code or "en").strip().lower()
    return normalized or "en"
