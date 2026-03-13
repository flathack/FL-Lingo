from pathlib import Path

from flatlas_translator.mod_overrides import (
    ModOverrideEntry,
    apply_mod_overrides,
    delete_mod_override,
    list_mod_overrides,
    resolve_mod_overrides_file,
    save_mod_override,
)
from flatlas_translator.models import ResourceCatalog, ResourceKind, ResourceLocation, TranslationUnit, make_global_id


def _location(dll_name: str, local_id: int) -> ResourceLocation:
    return ResourceLocation(
        dll_name=dll_name,
        dll_path=Path(f"C:/dummy/{dll_name}"),
        local_id=local_id,
        slot=1,
        global_id=make_global_id(1, local_id),
    )


def test_save_and_list_mod_overrides(tmp_path: Path) -> None:
    install_dir = tmp_path / "mod"
    save_mod_override(
        install_dir,
        ModOverrideEntry(
            kind="string",
            dll_name="resources.dll",
            local_id=907,
            mode="keep_original",
            source_text="This is a gun hard point.",
        ),
    )

    path = resolve_mod_overrides_file(install_dir)
    assert path.is_file()
    entries = list_mod_overrides(install_dir)
    assert len(entries) == 1
    assert entries[0].mode == "keep_original"


def test_apply_mod_overrides_sets_manual_text_for_keep_and_custom(tmp_path: Path) -> None:
    install_dir = tmp_path / "mod"
    save_mod_override(
        install_dir,
        ModOverrideEntry(
            kind="string",
            dll_name="resources.dll",
            local_id=907,
            mode="keep_original",
            source_text="Renamed by mod",
        ),
    )
    save_mod_override(
        install_dir,
        ModOverrideEntry(
            kind="string",
            dll_name="resources.dll",
            local_id=908,
            mode="custom_text",
            override_text="Eigener deutscher Text",
            source_text="Custom source",
        ),
    )
    catalog = ResourceCatalog(
        install_dir=install_dir,
        freelancer_ini=install_dir / "EXE" / "freelancer.ini",
        units=(
            TranslationUnit(ResourceKind.STRING, _location("resources.dll", 907), "Renamed by mod"),
            TranslationUnit(ResourceKind.STRING, _location("resources.dll", 908), "Custom source"),
        ),
    )

    updated = apply_mod_overrides(catalog)

    assert updated.units[0].manual_text == "Renamed by mod"
    assert updated.units[1].manual_text == "Eigener deutscher Text"


def test_apply_mod_overrides_uses_backup_lookup_for_keep_original(tmp_path: Path) -> None:
    install_dir = tmp_path / "mod"
    save_mod_override(
        install_dir,
        ModOverrideEntry(
            kind="string",
            dll_name="resources.dll",
            local_id=907,
            mode="keep_original",
            source_text="Renamed by mod",
        ),
    )
    catalog = ResourceCatalog(
        install_dir=install_dir,
        freelancer_ini=install_dir / "EXE" / "freelancer.ini",
        units=(
            TranslationUnit(ResourceKind.STRING, _location("resources.dll", 907), "Renamed by mod"),
        ),
    )

    updated = apply_mod_overrides(
        catalog,
        original_text_lookup={("string", "resources.dll", 907): "This is a gun or missile hard point."},
    )

    assert updated.units[0].manual_text == "This is a gun or missile hard point."


def test_apply_mod_overrides_falls_back_to_saved_source_text(tmp_path: Path) -> None:
    install_dir = tmp_path / "mod"
    save_mod_override(
        install_dir,
        ModOverrideEntry(
            kind="string",
            dll_name="resources.dll",
            local_id=907,
            mode="keep_original",
            source_text="Saved original text",
        ),
    )
    catalog = ResourceCatalog(
        install_dir=install_dir,
        freelancer_ini=install_dir / "EXE" / "freelancer.ini",
        units=(
            TranslationUnit(ResourceKind.STRING, _location("resources.dll", 907), "Current mod rename"),
        ),
    )

    updated = apply_mod_overrides(catalog, original_text_lookup={})

    assert updated.units[0].manual_text == "Saved original text"


def test_delete_mod_override_removes_entry(tmp_path: Path) -> None:
    install_dir = tmp_path / "mod"
    save_mod_override(
        install_dir,
        ModOverrideEntry(
            kind="string",
            dll_name="resources.dll",
            local_id=907,
            mode="keep_original",
        ),
    )

    delete_mod_override(install_dir, kind="string", dll_name="resources.dll", local_id=907)

    assert list_mod_overrides(install_dir) == []
