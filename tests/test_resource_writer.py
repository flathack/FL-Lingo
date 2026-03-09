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


def test_rc_escape_uses_rc_compatible_quotes() -> None:
    escaped = ResourceWriter._rc_escape('At the scene it read "Alaska - Omega-11 - Dublin".')
    assert '\\"' not in escaped
    assert '""Alaska - Omega-11 - Dublin""' in escaped
    assert ResourceWriter._rc_escape("Schubdüse") == "Schubd\\u00FCse"


def test_load_apply_session_matches_signature() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        install_dir = root / "Freelancer"
        exe_dir = install_dir / "EXE"
        exe_dir.mkdir(parents=True)
        dll_path = exe_dir / "NameResources.dll"
        dll_path.write_text("dummy", encoding="utf-8")

        unit = TranslationUnit(
            ResourceKind.STRING,
            ResourceLocation(
                dll_name="NameResources.dll",
                dll_path=dll_path,
                local_id=1,
                slot=1,
                global_id=make_global_id(1, 1),
            ),
            "Police",
            target=ResourceLocation(
                dll_name="NameResources.dll",
                dll_path=dll_path,
                local_id=1,
                slot=1,
                global_id=make_global_id(1, 1),
            ),
            target_text="Polizei",
        )
        catalog = ResourceCatalog(
            install_dir=install_dir,
            freelancer_ini=exe_dir / "freelancer.ini",
            units=(unit,),
        )
        writer = ResourceWriter()
        signature = writer._apply_signature((unit,))
        backup_dir = writer.backup_root(install_dir) / "20260101-120000"
        backup_dir.mkdir(parents=True)
        writer._save_apply_state_payload(
            writer.apply_state_path(install_dir),
            {
                "signature": signature,
                "backup_dir": str(backup_dir),
                "completed_dlls": ["nameresources.dll"],
                "failed_dll": None,
                "last_error": None,
            },
        )

        session = writer.load_apply_session(catalog)
        assert session is not None
        assert session.completed_dlls == ("nameresources.dll",)
        assert session.pending_dlls == ()
