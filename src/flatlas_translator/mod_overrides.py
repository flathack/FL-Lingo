"""Persistent mod-specific translation override helpers."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from .models import ResourceCatalog, TranslationUnit

MOD_OVERRIDES_FORMAT = "fl-lingo-mod-overrides"
MOD_OVERRIDES_FILENAME = "mod-overrides.json"


@dataclass(frozen=True, slots=True)
class ModOverrideEntry:
    kind: str
    dll_name: str
    local_id: int
    mode: str
    override_text: str = ""
    source_text: str = ""

    def key(self) -> tuple[str, str, int]:
        return (self.kind, self.dll_name.lower(), int(self.local_id))

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "dll_name": self.dll_name,
            "local_id": int(self.local_id),
            "mode": self.mode,
            "override_text": self.override_text,
            "source_text": self.source_text,
        }


def resolve_mod_overrides_file(install_dir: Path) -> Path:
    return Path(install_dir) / MOD_OVERRIDES_FILENAME


def list_mod_overrides(install_dir: Path) -> list[ModOverrideEntry]:
    path = resolve_mod_overrides_file(install_dir)
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(payload, dict):
        return []
    entries = payload.get("entries", [])
    if not isinstance(entries, list):
        return []
    result: list[ModOverrideEntry] = []
    for item in entries:
        if not isinstance(item, dict):
            continue
        result.append(
            ModOverrideEntry(
                kind=str(item.get("kind", "") or ""),
                dll_name=str(item.get("dll_name", "") or ""),
                local_id=int(item.get("local_id", 0) or 0),
                mode=str(item.get("mode", "") or ""),
                override_text=str(item.get("override_text", "") or ""),
                source_text=str(item.get("source_text", "") or ""),
            )
        )
    result.sort(key=lambda entry: (entry.dll_name.lower(), entry.kind, int(entry.local_id)))
    return result


def save_mod_override(install_dir: Path, entry: ModOverrideEntry) -> Path:
    path = resolve_mod_overrides_file(install_dir)
    by_key = {item.key(): item for item in list_mod_overrides(install_dir)}
    by_key[entry.key()] = entry
    _write_mod_overrides(path, list(by_key.values()))
    return path


def delete_mod_override(install_dir: Path, *, kind: str, dll_name: str, local_id: int) -> Path:
    path = resolve_mod_overrides_file(install_dir)
    remaining = [
        entry
        for entry in list_mod_overrides(install_dir)
        if entry.key() != (str(kind), str(dll_name).lower(), int(local_id))
    ]
    _write_mod_overrides(path, remaining)
    return path


def apply_mod_overrides(
    catalog: ResourceCatalog,
    *,
    original_text_lookup: dict[tuple[str, str, int], str] | None = None,
) -> ResourceCatalog:
    entries = list_mod_overrides(catalog.install_dir)
    if not entries:
        return catalog
    by_key = {entry.key(): entry for entry in entries}
    updated_units: list[TranslationUnit] = []
    for unit in catalog.units:
        unit_key = (str(unit.kind), unit.source.dll_name.lower(), int(unit.source.local_id))
        entry = by_key.get(unit_key)
        if entry is None:
            updated_units.append(unit)
            continue
        manual_text = _resolve_override_text(
            unit,
            entry,
            original_text_lookup=original_text_lookup,
        )
        updated_units.append(
            TranslationUnit(
                kind=unit.kind,
                source=unit.source,
                source_text=unit.source_text,
                target=unit.target,
                target_text=unit.target_text,
                manual_text=manual_text,
                translation_source=unit.translation_source,
            )
        )
    return ResourceCatalog(
        install_dir=catalog.install_dir,
        freelancer_ini=catalog.freelancer_ini,
        units=tuple(updated_units),
    )


def _resolve_override_text(
    unit: TranslationUnit,
    entry: ModOverrideEntry,
    *,
    original_text_lookup: dict[tuple[str, str, int], str] | None = None,
) -> str:
    if entry.mode != "keep_original":
        return str(entry.override_text or "").strip()

    unit_key = (str(unit.kind), unit.source.dll_name.lower(), int(unit.source.local_id))
    if original_text_lookup is not None:
        lookup_text = str(original_text_lookup.get(unit_key, "") or "").strip()
        if lookup_text:
            return lookup_text

    saved_source_text = str(entry.source_text or "").strip()
    if saved_source_text:
        return saved_source_text
    return unit.source_text


def _write_mod_overrides(path: Path, entries: list[ModOverrideEntry]) -> None:
    payload = {
        "format": MOD_OVERRIDES_FORMAT,
        "version": 1,
        "entries": [entry.to_dict() for entry in sorted(entries, key=lambda item: (item.dll_name.lower(), item.kind, int(item.local_id)))],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
