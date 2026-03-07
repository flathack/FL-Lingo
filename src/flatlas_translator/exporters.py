"""Export translation catalogs to portable file formats."""

from __future__ import annotations

import json
from pathlib import Path

from .models import RelocalizationStatus, ResourceCatalog


def export_catalog_json(
    catalog: ResourceCatalog,
    output_path: Path,
    *,
    changed_only: bool = False,
    auto_relocalize_only: bool = False,
) -> Path:
    if changed_only:
        catalog = ResourceCatalog(
            install_dir=catalog.install_dir,
            freelancer_ini=catalog.freelancer_ini,
            units=tuple(unit for unit in catalog.units if unit.is_changed),
        )
    if auto_relocalize_only:
        catalog = ResourceCatalog(
            install_dir=catalog.install_dir,
            freelancer_ini=catalog.freelancer_ini,
            units=tuple(
                unit for unit in catalog.units if unit.status == RelocalizationStatus.AUTO_RELOCALIZE
            ),
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(catalog.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return output_path
