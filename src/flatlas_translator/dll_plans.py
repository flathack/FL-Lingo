"""DLL-level relocalization planning."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from .models import RelocalizationStatus, ResourceCatalog, ResourceKind, TranslationUnit


class DllStrategy(StrEnum):
    FULL_REPLACE_SAFE = "full_replace_safe"
    PATCH_REQUIRED = "patch_required"
    NOT_SAFE = "not_safe"


@dataclass(frozen=True, slots=True)
class DllRelocalizationPlan:
    dll_name: str
    source_dll_path: Path
    target_dll_path: Path | None
    strategy: DllStrategy
    source_strings: int
    target_strings: int
    source_infocards: int
    target_infocards: int
    matched_units: int
    auto_relocalize_units: int
    mod_only_units: int

    @property
    def strategy_label(self) -> str:
        if self.strategy == DllStrategy.FULL_REPLACE_SAFE:
            return "komplett auf Deutsch ersetzbar"
        if self.strategy == DllStrategy.PATCH_REQUIRED:
            return "nur teilweise rueckuebersetzbar"
        return "nicht sicher ersetzbar"


def build_dll_plans(
    source_catalog: ResourceCatalog,
    paired_catalog: ResourceCatalog,
    target_catalog: ResourceCatalog,
) -> list[DllRelocalizationPlan]:
    source_units_by_dll = _group_units_by_dll(source_catalog.units)
    paired_units_by_dll = _group_units_by_dll(paired_catalog.units)
    target_units_by_dll = _group_units_by_dll(target_catalog.units)

    all_dll_names = sorted(source_units_by_dll)
    plans: list[DllRelocalizationPlan] = []
    for dll_name in all_dll_names:
        source_units = source_units_by_dll.get(dll_name, [])
        paired_units = paired_units_by_dll.get(dll_name, [])
        target_units = target_units_by_dll.get(dll_name, [])

        source_path = source_units[0].source.dll_path if source_units else Path(dll_name)
        target_path = target_units[0].source.dll_path if target_units else None

        source_strings = _count_kind(source_units, ResourceKind.STRING)
        target_strings = _count_kind(target_units, ResourceKind.STRING)
        source_infocards = _count_kind(source_units, ResourceKind.INFOCARD)
        target_infocards = _count_kind(target_units, ResourceKind.INFOCARD)
        matched_units = sum(1 for unit in paired_units if unit.target is not None)
        auto_units = sum(1 for unit in paired_units if unit.status == RelocalizationStatus.AUTO_RELOCALIZE)
        mod_only_units = sum(1 for unit in paired_units if unit.status == RelocalizationStatus.MOD_ONLY)

        source_ids = _id_set(source_units)
        target_ids = _id_set(target_units)
        exact_match = bool(target_units) and source_ids == target_ids

        if exact_match:
            strategy = DllStrategy.FULL_REPLACE_SAFE
        elif auto_units > 0:
            strategy = DllStrategy.PATCH_REQUIRED
        else:
            strategy = DllStrategy.NOT_SAFE

        plans.append(
            DllRelocalizationPlan(
                dll_name=dll_name,
                source_dll_path=source_path,
                target_dll_path=target_path,
                strategy=strategy,
                source_strings=source_strings,
                target_strings=target_strings,
                source_infocards=source_infocards,
                target_infocards=target_infocards,
                matched_units=matched_units,
                auto_relocalize_units=auto_units,
                mod_only_units=mod_only_units,
            )
        )
    return plans


def _group_units_by_dll(units: tuple[TranslationUnit, ...]) -> dict[str, list[TranslationUnit]]:
    grouped: dict[str, list[TranslationUnit]] = {}
    for unit in units:
        grouped.setdefault(unit.source.dll_name, []).append(unit)
    return grouped


def _count_kind(units: list[TranslationUnit], kind: ResourceKind) -> int:
    return sum(1 for unit in units if unit.kind == kind)


def _id_set(units: list[TranslationUnit]) -> set[tuple[str, int]]:
    return {(str(unit.kind), unit.source.local_id) for unit in units}
