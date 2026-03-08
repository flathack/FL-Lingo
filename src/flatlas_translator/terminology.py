"""Terminology helpers for glossary, suggestions, and skip heuristics."""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
import sys
from pathlib import Path

from .models import RelocalizationStatus, ResourceCatalog, TranslationUnit

_DEFAULT_TERM_TRANSLATIONS: dict[str, str] = {
    "Bartender": "Barkeeper",
    "Bounty Hunters Guild": "Gilde der Kopfgeldjaeger",
    "Equipment Dealer": "Ausruestungshaendler",
    "Liberty Navy": "Liberty Navy",
    "Liberty Police": "Liberty Polizei",
    "Orbital Spa and Cruise": "Orbital Spa and Cruise",
    "Rheinland Military": "Rheinland Militaer",
    "Rheinland Police": "Rheinland Polizei",
    "Ship Dealer": "Schiffshaendler",
    "Universal Shipping": "Universal Shipping",
    "Weapons Dealer": "Waffenhaendler",
}

LOCATION_KEYWORDS: tuple[str, ...] = (
    "Asteroid Field",
    "Asteroid",
    "Base",
    "Battleship",
    "Depot",
    "Dock",
    "Field",
    "Gate",
    "Hole",
    "Jump Gate",
    "Jump Hole",
    "Lane",
    "Nebula",
    "Outpost",
    "Planet",
    "Platform",
    "Prison",
    "Research Station",
    "Shipyard",
    "Station",
    "Store",
    "System",
    "Trade Lane",
)

ROLE_KEYWORDS: tuple[str, ...] = (
    "Administrator",
    "Agent",
    "Bartender",
    "Commander",
    "Dealer",
    "Doctor",
    "Engineer",
    "Guard",
    "Hacker",
    "Mechanic",
    "Merchant",
    "Officer",
    "Pilot",
    "Representative",
    "Scientist",
    "Trader",
)

NON_PERSON_KEYWORDS: tuple[str, ...] = (
    "Guild",
    "Military",
    "Navy",
    "Order",
    "Police",
)

_PERSON_NAME_RE = re.compile(r"^[A-Z][A-Za-z'`-]+(?: [A-Z][A-Za-z'`-]+){1,2}$")
_TERM_MAP_CACHE: dict[str, dict[str, str]] = {}


@dataclass(frozen=True, slots=True)
class GlossaryEntry:
    source_term: str
    target_term: str
    reason: str

    def to_dict(self) -> dict[str, str]:
        return {
            "source_term": self.source_term,
            "target_term": self.target_term,
            "reason": self.reason,
        }


def build_term_map(
    units: tuple[TranslationUnit, ...] | list[TranslationUnit],
    *,
    target_language: str = "de",
) -> dict[str, str]:
    _ = units
    term_map = dict(load_default_term_translations(target_language))
    return dict(sorted(term_map.items(), key=lambda item: (-len(item[0]), item[0].lower())))


def extract_faction_glossary(
    units: tuple[TranslationUnit, ...] | list[TranslationUnit],
    term_map: dict[str, str] | None = None,
    target_language: str = "de",
) -> list[GlossaryEntry]:
    resolved_map = term_map or build_term_map(units, target_language=target_language)
    found_terms: dict[str, GlossaryEntry] = {}
    for unit in units:
        for line in _split_lines(unit.source_text):
            target_term = resolved_map.get(line)
            if target_term and _looks_like_faction_or_role_term(line, target_language):
                found_terms.setdefault(
                    line,
                    GlossaryEntry(
                        source_term=line,
                        target_term=target_term,
                        reason="catalog_term" if target_term != load_default_term_translations(target_language).get(line) else "default_term",
                    ),
                )
    return [found_terms[key] for key in sorted(found_terms)]


def apply_known_term_suggestions(catalog: ResourceCatalog, *, target_language: str = "de") -> ResourceCatalog:
    term_map = build_term_map(catalog.units, target_language=target_language)
    updated_units: list[TranslationUnit] = []
    for unit in catalog.units:
        if unit.status != RelocalizationStatus.MOD_ONLY or unit.manual_text:
            updated_units.append(unit)
            continue
        suggestion = suggest_manual_translation(unit, term_map)
        if not suggestion:
            updated_units.append(unit)
            continue
        updated_units.append(
            TranslationUnit(
                kind=unit.kind,
                source=unit.source,
                source_text=unit.source_text,
                target=unit.target,
                target_text=unit.target_text,
                manual_text=suggestion,
            )
        )
    return ResourceCatalog(
        install_dir=catalog.install_dir,
        freelancer_ini=catalog.freelancer_ini,
        units=tuple(updated_units),
    )


def suggest_manual_translation(unit: TranslationUnit, term_map: dict[str, str]) -> str:
    if unit.status != RelocalizationStatus.MOD_ONLY:
        return ""
    lines = _split_lines(unit.source_text)
    if not lines:
        return ""
    translated_lines: list[str] = []
    changed = False
    for line in lines:
        translated_line = _translate_line_with_terms(line, term_map)
        if translated_line != line:
            translated_lines.append(translated_line)
            changed = True
            continue
        if is_line_non_translatable(line):
            translated_lines.append(line)
            continue
        return ""
    return "\n".join(translated_lines) if changed else ""


def prefill_translation_text(text: str, term_map: dict[str, str]) -> str:
    translated = _normalize_text(text)
    if not translated:
        return ""
    for source_term, target_term in term_map.items():
        translated = translated.replace(source_term, target_term)
    return translated


def _translate_line_with_terms(line: str, term_map: dict[str, str]) -> str:
    normalized = _normalize_text(line)
    if not normalized:
        return ""
    exact_translation = term_map.get(normalized)
    if exact_translation:
        return exact_translation
    colon_translation = _translate_colon_label_line(normalized, term_map)
    if colon_translation:
        return colon_translation
    return prefill_translation_text(normalized, term_map)


def is_unit_skippable(unit: TranslationUnit) -> bool:
    if unit.status != RelocalizationStatus.MOD_ONLY:
        return False
    lines = _split_lines(unit.source_text)
    if not lines:
        return False
    return all(is_line_non_translatable(line) for line in lines)


def is_line_non_translatable(text: str) -> bool:
    normalized = _normalize_text(text)
    if not normalized:
        return False
    if _has_location_keyword(normalized):
        return True
    if _looks_like_person_name(normalized):
        return True
    return False


def _split_lines(text: str) -> list[str]:
    return [line.strip() for line in _normalize_text(text).split("\n") if line.strip()]


def _normalize_text(text: str) -> str:
    return str(text or "").replace("\r\n", "\n").strip()


def _has_location_keyword(text: str) -> bool:
    for keyword in LOCATION_KEYWORDS:
        if text == keyword or text.endswith(f" {keyword}") or text.startswith(f"{keyword} "):
            return True
    return False


def _looks_like_person_name(text: str) -> bool:
    if not _PERSON_NAME_RE.fullmatch(text):
        return False
    words = text.split()
    if any(word in ROLE_KEYWORDS for word in words):
        return False
    if any(word in NON_PERSON_KEYWORDS for word in words):
        return False
    if any(char.isdigit() for char in text):
        return False
    return True


def _looks_like_faction_or_role_term(text: str, target_language: str = "de") -> bool:
    return "Guild" in text or "Police" in text or "Navy" in text or "Dealer" in text or text in load_default_term_translations(target_language)


def _is_term_candidate(source_text: str, target_text: str) -> bool:
    if "\n" in source_text or "\n" in target_text:
        return False
    if "<" in source_text or "<" in target_text:
        return False
    if len(source_text) > 80 or len(target_text) > 80:
        return False
    return True


def load_default_term_translations(language_code: str = "de") -> dict[str, str]:
    normalized_language = _normalize_language_code(language_code)
    cached = _TERM_MAP_CACHE.get(normalized_language)
    if cached is not None:
        return dict(cached)
    _TERM_MAP_CACHE[normalized_language] = _load_term_translations_from_disk(normalized_language)
    return dict(_TERM_MAP_CACHE[normalized_language])


def clear_term_map_cache() -> None:
    _TERM_MAP_CACHE.clear()


def resolve_terminology_file(language_code: str = "de") -> Path:
    normalized_language = _normalize_language_code(language_code)
    for candidate in _terminology_file_candidates(normalized_language):
        if candidate.is_file():
            return candidate
    fallback = _terminology_file_candidates(normalized_language)[0]
    fallback.parent.mkdir(parents=True, exist_ok=True)
    fallback.write_text(
        json.dumps(
            {
                "language": normalized_language,
                "terms": _DEFAULT_TERM_TRANSLATIONS if normalized_language == "de" else {},
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return fallback


def save_term_mapping(
    language_code: str,
    source_term: str,
    target_term: str,
    *,
    preferred_section: str = "misc",
) -> Path:
    source = _normalize_text(source_term)
    target = _normalize_text(target_term)
    if not source or not target:
        raise ValueError("Source and target term must not be empty.")
    terminology_path = resolve_terminology_file(language_code)
    payload = json.loads(terminology_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        payload = {"language": _normalize_language_code(language_code), "terms": {}}
    payload["language"] = _normalize_language_code(language_code)
    terms = payload.get("terms")
    if not isinstance(terms, dict):
        terms = {}
        payload["terms"] = terms
    if not _update_nested_term(terms, source, target):
        bucket_name = preferred_section.strip() or "misc"
        bucket = terms.get(bucket_name)
        if not isinstance(bucket, dict):
            bucket = {}
            terms[bucket_name] = bucket
        bucket[source] = target
    terminology_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    clear_term_map_cache()
    return terminology_path


def _load_term_translations_from_disk(language_code: str) -> dict[str, str]:
    for candidate in _terminology_file_candidates(language_code):
        if not candidate.is_file():
            continue
        payload = json.loads(candidate.read_text(encoding="utf-8"))
        terms = payload.get("terms", {})
        flattened = _flatten_term_sections(terms)
        if flattened:
            return flattened
    return dict(_DEFAULT_TERM_TRANSLATIONS if language_code == "de" else {})


def _terminology_file_candidates(language_code: str) -> list[Path]:
    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        candidates.extend(
            [
                exe_dir / "data" / f"terminology.{language_code}.json",
                exe_dir / "_internal" / "data" / f"terminology.{language_code}.json",
            ]
        )
    project_root = Path(__file__).resolve().parent.parent.parent
    candidates.append(project_root / "data" / f"terminology.{language_code}.json")
    return candidates


def _normalize_language_code(language_code: str) -> str:
    normalized = str(language_code or "de").strip().lower()
    return normalized or "de"


def _translate_colon_label_line(text: str, term_map: dict[str, str]) -> str:
    label, separator, value = text.partition(":")
    if separator != ":":
        return ""
    normalized_label = label.strip()
    if not normalized_label:
        return ""
    translated_label = term_map.get(normalized_label)
    if not translated_label:
        return ""
    return f"{translated_label}:{value}"


def _flatten_term_sections(payload: object) -> dict[str, str]:
    if not isinstance(payload, dict):
        return {}
    flattened: dict[str, str] = {}
    for key, value in payload.items():
        if isinstance(value, dict):
            nested = _flatten_term_sections(value)
            if nested:
                flattened.update(nested)
                continue
        source = str(key).strip()
        target = str(value).strip()
        if source and target and not isinstance(value, dict):
            flattened[source] = target
    return flattened


def _update_nested_term(payload: dict[str, object], source: str, target: str) -> bool:
    for key, value in payload.items():
        if isinstance(value, dict):
            if source in value and not isinstance(value.get(source), dict):
                value[source] = target
                return True
            if _update_nested_term(value, source, target):
                return True
        elif str(key).strip() == source:
            payload[key] = target
            return True
    return False
