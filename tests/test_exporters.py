import json
from pathlib import Path

from flatlas_translator.exporters import export_catalog_json
from flatlas_translator.models import (
    RelocalizationStatus,
    ResourceCatalog,
    ResourceKind,
    ResourceLocation,
    TranslationUnit,
    make_global_id,
)


def test_export_catalog_json_writes_units(tmp_path: Path) -> None:
    location = ResourceLocation(
        dll_name="NameResources.dll",
        dll_path=Path("C:/dummy/NameResources.dll"),
        local_id=1,
        slot=1,
        global_id=make_global_id(1, 1),
    )
    catalog = ResourceCatalog(
        install_dir=Path("C:/source"),
        freelancer_ini=Path("C:/source/EXE/freelancer.ini"),
        units=(TranslationUnit(kind=ResourceKind.STRING, source=location, source_text="New York"),),
    )

    output_path = export_catalog_json(catalog, tmp_path / "catalog.json")
    data = json.loads(output_path.read_text(encoding="utf-8"))

    assert data["install_dir"] == "C:/source"
    assert data["units"][0]["source"]["dll_name"] == "NameResources.dll"
    assert data["units"][0]["status"] == str(RelocalizationStatus.MOD_ONLY)


def test_export_catalog_json_can_filter_changed_only(tmp_path: Path) -> None:
    source = ResourceLocation(
        dll_name="NameResources.dll",
        dll_path=Path("C:/dummy/NameResources.dll"),
        local_id=1,
        slot=1,
        global_id=make_global_id(1, 1),
    )
    target = ResourceLocation(
        dll_name="NameResources.dll",
        dll_path=Path("C:/dummy-de/NameResources.dll"),
        local_id=1,
        slot=1,
        global_id=make_global_id(1, 1),
    )
    catalog = ResourceCatalog(
        install_dir=Path("C:/source"),
        freelancer_ini=Path("C:/source/EXE/freelancer.ini"),
        units=(
            TranslationUnit(ResourceKind.STRING, source, "New York", target, "Neu York"),
            TranslationUnit(ResourceKind.STRING, source, "Texas", target, "Texas"),
        ),
    )

    output_path = export_catalog_json(catalog, tmp_path / "changed.json", changed_only=True)
    data = json.loads(output_path.read_text(encoding="utf-8"))

    assert len(data["units"]) == 1
    assert data["units"][0]["target_text"] == "Neu York"


def test_export_catalog_json_can_filter_auto_relocalize_only(tmp_path: Path) -> None:
    source = ResourceLocation(
        dll_name="NameResources.dll",
        dll_path=Path("C:/dummy/NameResources.dll"),
        local_id=1,
        slot=1,
        global_id=make_global_id(1, 1),
    )
    target = ResourceLocation(
        dll_name="NameResources.dll",
        dll_path=Path("C:/dummy-de/NameResources.dll"),
        local_id=1,
        slot=1,
        global_id=make_global_id(1, 1),
    )
    catalog = ResourceCatalog(
        install_dir=Path("C:/source"),
        freelancer_ini=Path("C:/source/EXE/freelancer.ini"),
        units=(
            TranslationUnit(ResourceKind.STRING, source, "New York", target, "Neu York"),
            TranslationUnit(ResourceKind.STRING, source, "Texas", target, "Texas"),
            TranslationUnit(ResourceKind.STRING, source, "Mod only"),
        ),
    )

    output_path = export_catalog_json(
        catalog,
        tmp_path / "auto.json",
        auto_relocalize_only=True,
    )
    data = json.loads(output_path.read_text(encoding="utf-8"))

    assert len(data["units"]) == 1
    assert data["units"][0]["status"] == str(RelocalizationStatus.AUTO_RELOCALIZE)
