from pathlib import Path

from flatlas_translator.models import (
    RelocalizationStatus,
    ResourceKind,
    ResourceLocation,
    TranslationUnit,
    make_global_id,
)


def _location() -> ResourceLocation:
    return ResourceLocation(
        dll_name="NameResources.dll",
        dll_path=Path("C:/dummy/NameResources.dll"),
        local_id=1,
        slot=1,
        global_id=make_global_id(1, 1),
    )


def test_translation_unit_statuses() -> None:
    location = _location()

    auto_unit = TranslationUnit(ResourceKind.STRING, location, "New York", location, "Neu York")
    same_unit = TranslationUnit(ResourceKind.STRING, location, "Texas", location, "Texas")
    mod_unit = TranslationUnit(ResourceKind.STRING, location, "Custom Mod Text")

    assert auto_unit.status == RelocalizationStatus.AUTO_RELOCALIZE
    assert same_unit.status == RelocalizationStatus.ALREADY_LOCALIZED
    assert mod_unit.status == RelocalizationStatus.MOD_ONLY
