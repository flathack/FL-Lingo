"""Export and import external translation exchange files."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from .models import RelocalizationStatus, ResourceCatalog, TranslationUnit
from .terminology import build_term_map, extract_faction_glossary, is_unit_skippable, prefill_translation_text

LONG_TEXT_MIN_LENGTH = 180


@dataclass(frozen=True, slots=True)
class ExchangeExportReport:
    output_path: Path
    exported_entries: int
    skipped_entries: int
    glossary_entries: int


def export_mod_only_exchange(
    catalog: ResourceCatalog,
    output_path: Path,
    *,
    target_language: str = "de",
) -> ExchangeExportReport:
    return _export_exchange(
        catalog,
        output_path,
        target_language=target_language,
        entry_filter=lambda unit: True,
    )


def export_long_open_exchange(
    catalog: ResourceCatalog,
    output_path: Path,
    *,
    target_language: str = "de",
    min_length: int = LONG_TEXT_MIN_LENGTH,
) -> ExchangeExportReport:
    return _export_exchange(
        catalog,
        output_path,
        target_language=target_language,
        entry_filter=lambda unit: len(str(unit.source_text or "")) >= int(min_length),
    )


def export_all_translated(
    catalog: ResourceCatalog,
    output_path: Path,
) -> ExchangeExportReport:
    """Export every unit that already has a translation (auto, manual, or reference)."""
    entries: list[dict[str, object]] = []
    for unit in catalog.units:
        text = unit.manual_text or unit.target_text
        if not text or not str(text).strip():
            continue
        entries.append(
            {
                "kind": str(unit.kind),
                "dll_name": unit.source.dll_name,
                "local_id": unit.source.local_id,
                "global_id": unit.source.global_id,
                "source_text": unit.source_text,
                "translation_text": text,
                "translation_source": unit.translation_source,
            }
        )
    payload = {
        "format": "flatlas-translator-exchange",
        "version": 2,
        "metadata": {
            "type": "all-translated",
            "exported_entries": len(entries),
            "skipped_entries": 0,
            "glossary_entries": 0,
        },
        "glossary": [],
        "entries": entries,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return ExchangeExportReport(
        output_path=output_path,
        exported_entries=len(entries),
        skipped_entries=0,
        glossary_entries=0,
    )


def _export_exchange(
    catalog: ResourceCatalog,
    output_path: Path,
    *,
    target_language: str,
    entry_filter,
) -> ExchangeExportReport:
    entries = []
    mod_only_units: list[TranslationUnit] = []
    skipped_entries = 0
    term_map = build_term_map(catalog.units, target_language=target_language)
    for unit in catalog.units:
        if unit.status != RelocalizationStatus.MOD_ONLY:
            continue
        if not entry_filter(unit):
            continue
        mod_only_units.append(unit)
        if is_unit_skippable(unit):
            skipped_entries += 1
            continue
        suggested_text = prefill_translation_text(unit.source_text, term_map)
        entries.append(
            {
                "kind": str(unit.kind),
                "dll_name": unit.source.dll_name,
                "local_id": unit.source.local_id,
                "global_id": unit.source.global_id,
                "source_text": unit.source_text,
                "translation_text": suggested_text if suggested_text != unit.source_text else "",
                "suggested_text": suggested_text if suggested_text != unit.source_text else "",
            }
        )
    glossary = [
        entry.to_dict()
        for entry in extract_faction_glossary(mod_only_units, term_map, target_language=target_language)
    ]
    payload = {
        "format": "flatlas-translator-exchange",
        "version": 2,
        "metadata": {
            "exported_entries": len(entries),
            "skipped_entries": skipped_entries,
            "glossary_entries": len(glossary),
        },
        "glossary": glossary,
        "entries": entries,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return ExchangeExportReport(
        output_path=output_path,
        exported_entries=len(entries),
        skipped_entries=skipped_entries,
        glossary_entries=len(glossary),
    )


def import_exchange(catalog: ResourceCatalog, input_path: Path) -> ResourceCatalog:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    entries = payload.get("entries", [])
    translations = {
        _exchange_key(entry): str(entry.get("translation_text", "") or "").strip()
        for entry in entries
        if str(entry.get("translation_text", "") or "").strip()
    }
    merged_units: list[TranslationUnit] = []
    for unit in catalog.units:
        manual_text = translations.get(_unit_key(unit), unit.manual_text)
        source = "import" if _unit_key(unit) in translations and manual_text != unit.manual_text else unit.translation_source
        merged_units.append(
            TranslationUnit(
                kind=unit.kind,
                source=unit.source,
                source_text=unit.source_text,
                target=unit.target,
                target_text=unit.target_text,
                manual_text=manual_text,
                translation_source=source if manual_text else "",
            )
        )
    return ResourceCatalog(
        install_dir=catalog.install_dir,
        freelancer_ini=catalog.freelancer_ini,
        units=tuple(merged_units),
    )


def update_manual_translation(
    catalog: ResourceCatalog,
    *,
    kind: str,
    dll_name: str,
    local_id: int,
    manual_text: str,
    translation_source: str = "",
) -> ResourceCatalog:
    normalized_manual_text = str(manual_text or "").replace("\r\n", "\n")
    merged_units: list[TranslationUnit] = []
    for unit in catalog.units:
        if _unit_key(unit) == (str(kind), str(dll_name).lower(), int(local_id)):
            merged_units.append(
                TranslationUnit(
                    kind=unit.kind,
                    source=unit.source,
                    source_text=unit.source_text,
                    target=unit.target,
                    target_text=unit.target_text,
                    manual_text=normalized_manual_text,
                    translation_source=translation_source if normalized_manual_text else "",
                )
            )
            continue
        merged_units.append(unit)
    return ResourceCatalog(
        install_dir=catalog.install_dir,
        freelancer_ini=catalog.freelancer_ini,
        units=tuple(merged_units),
    )


def _unit_key(unit: TranslationUnit) -> tuple[str, str, int]:
    return (str(unit.kind), unit.source.dll_name.lower(), int(unit.source.local_id))


def _exchange_key(entry: dict) -> tuple[str, str, int]:
    return (
        str(entry.get("kind", "")),
        str(entry.get("dll_name", "")).lower(),
        int(entry.get("local_id", 0)),
    )
