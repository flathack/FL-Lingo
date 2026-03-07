"""Catalog summary helpers."""

from __future__ import annotations

from dataclasses import dataclass

from .models import RelocalizationStatus, ResourceCatalog, ResourceKind


@dataclass(frozen=True, slots=True)
class CatalogStats:
    total: int
    matched: int
    changed: int
    auto_relocalize: int
    already_localized: int
    mod_only: int
    manual_translation: int


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
    )
