"""Build translation catalogs from Freelancer resource DLLs."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from .dll_resources import DllHtmlResourceReader, DllStringTableReader
from .freelancer_ini import ResourceDll, load_resource_dlls
from .models import ResourceCatalog, ResourceKind, ResourceLocation, TranslationUnit, make_global_id


class CatalogLoader:
    """Load translation units from a Freelancer installation."""

    def __init__(
        self,
        *,
        string_reader: DllStringTableReader | None = None,
        html_reader: DllHtmlResourceReader | None = None,
    ) -> None:
        self._string_reader = string_reader or DllStringTableReader()
        self._html_reader = html_reader or DllHtmlResourceReader()

    def load_catalog(self, install_dir: Path, *, include_infocards: bool = True) -> ResourceCatalog:
        freelancer_ini, resources = load_resource_dlls(install_dir)
        units: list[TranslationUnit] = []

        for slot, resource in enumerate(resources, start=1):
            units.extend(self._load_string_units(resource, slot))
            if include_infocards:
                units.extend(self._load_infocard_units(resource, slot))

        units.sort(key=lambda unit: (unit.source.dll_name.lower(), unit.kind, unit.source.local_id))
        return ResourceCatalog(
            install_dir=Path(install_dir),
            freelancer_ini=freelancer_ini,
            units=tuple(units),
        )

    def _load_string_units(self, resource: ResourceDll, slot: int) -> Iterable[TranslationUnit]:
        for local_id, text in self._string_reader.read_strings(resource.dll_path).items():
            yield TranslationUnit(
                kind=ResourceKind.STRING,
                source=_make_location(resource, slot, local_id),
                source_text=text,
            )

    def _load_infocard_units(self, resource: ResourceDll, slot: int) -> Iterable[TranslationUnit]:
        for local_id, text in self._html_reader.read_html_resources(resource.dll_path).items():
            yield TranslationUnit(
                kind=ResourceKind.INFOCARD,
                source=_make_location(resource, slot, local_id),
                source_text=text,
            )


def pair_catalogs(source: ResourceCatalog, target: ResourceCatalog) -> ResourceCatalog:
    """Attach target-side matches by kind, DLL name, and local resource ID."""
    target_index = {
        _catalog_key(unit.kind, unit.source.dll_name, unit.source.local_id): unit
        for unit in target.units
    }
    paired_units: list[TranslationUnit] = []
    for unit in source.units:
        target_unit = target_index.get(_catalog_key(unit.kind, unit.source.dll_name, unit.source.local_id))
        paired_units.append(
            TranslationUnit(
                kind=unit.kind,
                source=unit.source,
                source_text=unit.source_text,
                target=target_unit.source if target_unit else None,
                target_text=target_unit.source_text if target_unit else "",
            )
        )
    return ResourceCatalog(
        install_dir=source.install_dir,
        freelancer_ini=source.freelancer_ini,
        units=tuple(paired_units),
    )


def _catalog_key(kind: ResourceKind, dll_name: str, local_id: int) -> tuple[str, str, int]:
    return (str(kind), str(dll_name).lower(), int(local_id))


def _make_location(resource: ResourceDll, slot: int, local_id: int) -> ResourceLocation:
    return ResourceLocation(
        dll_name=resource.dll_name,
        dll_path=resource.dll_path,
        local_id=int(local_id),
        slot=int(slot),
        global_id=make_global_id(slot, local_id),
    )
