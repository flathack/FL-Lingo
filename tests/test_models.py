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


def test_translation_unit_normalizes_line_endings_for_status_and_change() -> None:
    location = _location()
    unit = TranslationUnit(
        ResourceKind.INFOCARD,
        location,
        "<?xml version=\"1.0\"?>\n<RDL><TEXT>Test</TEXT></RDL>",
        location,
        "<?xml version=\"1.0\"?>\r\n<RDL><TEXT>Test</TEXT></RDL>",
    )

    assert unit.status == RelocalizationStatus.ALREADY_LOCALIZED
    assert unit.is_changed is False


def test_replacement_text_preserves_source_placeholders() -> None:
    location = _location()
    unit = TranslationUnit(
        ResourceKind.STRING,
        location,
        "You could stand to have a better reputation with %F0v1 for %d0 credits.",
        location,
        "Sie koennten einen besseren Ruf bei %F0v5 fuer %d0 Credits brauchen.",
    )

    assert unit.replacement_text == "Sie koennten einen besseren Ruf bei %F0v1 fuer %d0 Credits brauchen."
