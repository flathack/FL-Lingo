"""Catalog summary helpers."""

from __future__ import annotations

from dataclasses import dataclass

from .models import RelocalizationStatus, ResourceCatalog, ResourceKind
from .terminology import is_unit_skippable


@dataclass(frozen=True, slots=True)
class CatalogStats:
    total: int
    matched: int
    changed: int
    auto_relocalize: int
    already_localized: int
    mod_only: int
    manual_translation: int
    skipped_mod_only: int


@dataclass(frozen=True, slots=True)
class TranslationProgress:
    total: int
    localized: int
    done: int
    skipped: int

    @property
    def done_percent(self) -> int:
        return 0 if self.total == 0 else round((self.done / self.total) * 100)

    @property
    def covered_percent(self) -> int:
        covered = self.done + self.skipped
        return 0 if self.total == 0 else round((covered / self.total) * 100)


def summarize_catalog(catalog: ResourceCatalog, kind: ResourceKind | None = None) -> CatalogStats:
    units = catalog.units if kind is None else tuple(unit for unit in catalog.units if unit.kind == kind)
    return CatalogStats(
        total=len(units),
        matched=sum(1 for unit in units if unit.target is not None),
        changed=sum(1 for unit in units if unit.is_changed),
        auto_relocalize=sum(1 for unit in units if unit.status == RelocalizationStatus.AUTO_RELOCALIZE),
        already_localized=sum(1 for unit in units if unit.status == RelocalizationStatus.ALREADY_LOCALIZED),
        mod_only=sum(1 for unit in units if unit.status == RelocalizationStatus.MOD_ONLY),
        manual_translation=sum(1 for unit in units if unit.status == RelocalizationStatus.MANUAL_TRANSLATION),
        skipped_mod_only=sum(1 for unit in units if is_unit_skippable(unit)),
    )


def calculate_translation_progress(catalog: ResourceCatalog) -> TranslationProgress:
    units = catalog.units
    localized = sum(
        1
        for unit in units
        if unit.status == RelocalizationStatus.ALREADY_LOCALIZED
    )
    done = sum(
        1
        for unit in units
        if unit.status
        in {
            RelocalizationStatus.ALREADY_LOCALIZED,
            RelocalizationStatus.AUTO_RELOCALIZE,
            RelocalizationStatus.MANUAL_TRANSLATION,
        }
    )
    skipped = sum(1 for unit in units if is_unit_skippable(unit))
    return TranslationProgress(total=len(units), localized=localized, done=done, skipped=skipped)
