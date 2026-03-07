"""Export and import external translation exchange files."""

from __future__ import annotations

import json
from pathlib import Path

from .models import RelocalizationStatus, ResourceCatalog, TranslationUnit


def export_mod_only_exchange(catalog: ResourceCatalog, output_path: Path) -> Path:
    entries = []
    for unit in catalog.units:
        if unit.status != RelocalizationStatus.MOD_ONLY:
            continue
        entries.append(
            {
                "kind": str(unit.kind),
                "dll_name": unit.source.dll_name,
                "local_id": unit.source.local_id,
                "global_id": unit.source.global_id,
                "source_text": unit.source_text,
                "translation_text": "",
            }
        )
    payload = {
        "format": "flatlas-translator-exchange",
        "version": 1,
        "entries": entries,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return output_path


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
        merged_units.append(
            TranslationUnit(
                kind=unit.kind,
                source=unit.source,
                source_text=unit.source_text,
                target=unit.target,
                target_text=unit.target_text,
                manual_text=manual_text,
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
