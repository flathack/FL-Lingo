from pathlib import Path
import tempfile

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


def test_list_backups_and_restore_backup() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        install_dir = root / "Freelancer"
        exe_dir = install_dir / "EXE"
        exe_dir.mkdir(parents=True)
        target_dll = exe_dir / "NameResources.dll"
        target_dll.write_text("current", encoding="utf-8")

        backup_dir = ResourceWriter.backup_root(install_dir) / "20260101-120000"
        backup_dir.mkdir(parents=True)
        (backup_dir / "NameResources.dll").write_text("backup", encoding="utf-8")

        backups = ResourceWriter.list_backups(install_dir)
        restored = ResourceWriter.restore_backup(install_dir, backup_dir)

        assert backups == [backup_dir]
        assert restored == (target_dll,)
        assert target_dll.read_text(encoding="utf-8") == "backup"
