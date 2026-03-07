from pathlib import Path

from flatlas_translator.models import ResourceCatalog, ResourceKind, ResourceLocation, TranslationUnit, make_global_id
from flatlas_translator.resource_writer import ResourceWriter


def _location(dll_name: str, local_id: int) -> ResourceLocation:
    return ResourceLocation(
        dll_name=dll_name,
        dll_path=Path(f"C:/dummy/{dll_name}"),
        local_id=local_id,
        slot=1,
        global_id=make_global_id(1, local_id),
    )


def test_apply_german_relocalization_requires_auto_units() -> None:
    writer = ResourceWriter()
    unit = TranslationUnit(ResourceKind.STRING, _location("NameResources.dll", 1), "Custom Mod Text")
    catalog = ResourceCatalog(
        install_dir=Path("C:/source"),
        freelancer_ini=Path("C:/source/EXE/freelancer.ini"),
        units=(unit,),
    )

    try:
        writer.apply_german_relocalization(catalog)
    except RuntimeError as exc:
        assert "auto_relocalize" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError for missing auto_relocalize units")
