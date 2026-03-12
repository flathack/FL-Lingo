import sys
from pathlib import Path
import tempfile

import pytest

from flatlas_translator.models import ResourceCatalog, ResourceKind, ResourceLocation, TranslationUnit, make_global_id
from flatlas_translator.resource_writer import AudioCopyCandidate, ResourceWriter


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


def test_restore_backup_can_restore_nested_audio_files() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        install_dir = root / "Freelancer"
        audio_dir = install_dir / "DATA" / "AUDIO" / "DIALOGUE" / "JUNI"
        audio_dir.mkdir(parents=True)
        target_audio = audio_dir / "line.wav"
        target_audio.write_text("english", encoding="utf-8")

        backup_dir = ResourceWriter.backup_root(install_dir) / "20260101-120000"
        nested_backup = backup_dir / "DATA" / "AUDIO" / "DIALOGUE" / "JUNI"
        nested_backup.mkdir(parents=True)
        (nested_backup / "line.wav").write_text("deutsch", encoding="utf-8")

        restored = ResourceWriter.restore_backup(install_dir, backup_dir)

        assert restored == (target_audio,)
        assert target_audio.read_text(encoding="utf-8") == "deutsch"


def test_list_audio_copy_candidates_detects_changed_and_missing_voice_files() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        install_dir = root / "Current"
        reference_dir = root / "Reference"
        current_audio = install_dir / "DATA" / "AUDIO" / "DIALOGUE" / "JUNI"
        reference_audio = reference_dir / "DATA" / "AUDIO" / "DIALOGUE" / "JUNI"
        current_audio.mkdir(parents=True)
        reference_audio.mkdir(parents=True)
        (current_audio / "same.wav").write_text("same", encoding="utf-8")
        (reference_audio / "same.wav").write_text("same", encoding="utf-8")
        (current_audio / "changed.wav").write_text("english", encoding="utf-8")
        (reference_audio / "changed.wav").write_text("deutsch", encoding="utf-8")
        (reference_audio / "missing.wav").write_text("neu", encoding="utf-8")

        candidates = ResourceWriter().list_audio_copy_candidates(install_dir, reference_dir)

        assert [candidate.relative_path.as_posix() for candidate in candidates] == [
            "DATA/AUDIO/DIALOGUE/JUNI/changed.wav",
            "DATA/AUDIO/DIALOGUE/JUNI/missing.wav",
        ]


def test_copy_reference_audio_writes_files_and_backups_existing_targets() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        install_dir = root / "Current"
        reference_dir = root / "Reference"
        current_audio = install_dir / "DATA" / "AUDIO" / "DIALOGUE" / "JUNI"
        reference_audio = reference_dir / "DATA" / "AUDIO" / "DIALOGUE" / "JUNI"
        current_audio.mkdir(parents=True)
        reference_audio.mkdir(parents=True)
        target_file = current_audio / "changed.wav"
        target_file.write_text("english", encoding="utf-8")
        (reference_audio / "changed.wav").write_text("deutsch", encoding="utf-8")
        (reference_audio / "missing.wav").write_text("neu", encoding="utf-8")

        report = ResourceWriter().copy_reference_audio(install_dir, reference_dir)

        assert sorted(path.name for path in report.copied_files) == ["changed.wav", "missing.wav"]
        assert sorted(path.name for path in report.created_files) == ["missing.wav"]
        assert target_file.read_text(encoding="utf-8") == "deutsch"
        assert (current_audio / "missing.wav").read_text(encoding="utf-8") == "neu"
        assert (report.backup_dir / "DATA" / "AUDIO" / "DIALOGUE" / "JUNI" / "changed.wav").read_text(encoding="utf-8") == "english"


def test_audio_copy_progress_reports_matching_and_open_files() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        install_dir = root / "Current"
        reference_dir = root / "Reference"
        current_audio = install_dir / "DATA" / "AUDIO" / "DIALOGUE" / "JUNI"
        reference_audio = reference_dir / "DATA" / "AUDIO" / "DIALOGUE" / "JUNI"
        current_audio.mkdir(parents=True)
        reference_audio.mkdir(parents=True)
        (current_audio / "same.wav").write_text("same", encoding="utf-8")
        (reference_audio / "same.wav").write_text("same", encoding="utf-8")
        (current_audio / "changed.wav").write_text("english", encoding="utf-8")
        (reference_audio / "changed.wav").write_text("deutsch", encoding="utf-8")

        progress = ResourceWriter().audio_copy_progress(install_dir, reference_dir)

        assert progress.total_files == 2
        assert progress.matching_files == 1
        assert progress.differing_files == 1


def test_assemble_install_patch_copies_dlls_audio_and_manifest() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        install_dir = root / "Current"
        output_dir = root / "Patch"
        dll_path = install_dir / "EXE" / "NameResources.dll"
        audio_path = install_dir / "DATA" / "AUDIO" / "DIALOGUE" / "JUNI" / "line.wav"
        dll_path.parent.mkdir(parents=True)
        audio_path.parent.mkdir(parents=True)
        dll_path.write_text("dll-data", encoding="utf-8")
        audio_path.write_text("audio-data", encoding="utf-8")

        report = ResourceWriter().assemble_install_patch(
            install_dir,
            output_dir,
            dll_paths=(dll_path,),
            audio_candidates=(
                AudioCopyCandidate(
                    relative_path=Path("DATA/AUDIO/DIALOGUE/JUNI/line.wav"),
                    source_path=audio_path,
                    target_path=audio_path,
                ),
            ),
        )

        assert (output_dir / "EXE" / "NameResources.dll").read_text(encoding="utf-8") == "dll-data"
        assert (output_dir / "DATA" / "AUDIO" / "DIALOGUE" / "JUNI" / "line.wav").read_text(encoding="utf-8") == "audio-data"
        assert report.manifest_path.is_file()
        assert "EXE/NameResources.dll" in report.manifest_path.read_text(encoding="utf-8")


def test_rc_escape_uses_rc_compatible_quotes() -> None:
    escaped = ResourceWriter._rc_escape('At the scene it read "Alaska - Omega-11 - Dublin".')
    assert '\\"' not in escaped
    assert '""Alaska - Omega-11 - Dublin""' in escaped
    assert ResourceWriter._rc_escape("Schubdüse") == "Schubd\\u00FCse"


def test_rc_escape_toolchain_preserves_unicode_characters() -> None:
    escaped = ResourceWriter._rc_escape_toolchain('Barrager-Geschützturm "Alpha"')
    assert '""Alpha""' in escaped
    assert "\\xFC" in escaped
    assert "Geschützturm" not in escaped
    assert "\\u00FC" not in escaped


def test_rc_escape_toolchain_uses_cp1252_bytes_for_smart_punctuation() -> None:
    escaped = ResourceWriter._rc_escape_toolchain("Jun’ko… Ende")
    assert "\\x92" in escaped
    assert "\\x85" in escaped


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


@pytest.mark.skipif(sys.platform.startswith("win"), reason="Linux/macOS-only behavior")
def test_windows_only_installer_actions_fail_cleanly_on_non_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    writer = ResourceWriter()

    monkeypatch.setattr(ResourceWriter, "_resource_toolchain_commands", staticmethod(lambda: None))

    assert writer.has_toolchain() is False

    with pytest.raises(RuntimeError, match="Windows"):
        ResourceWriter.launch_toolchain_installer()

    with pytest.raises(RuntimeError, match="Windows"):
        ResourceWriter.install_file_association()


@pytest.mark.skipif(sys.platform.startswith("win"), reason="Linux/macOS-only behavior")
def test_has_toolchain_uses_non_windows_resource_toolchain(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ResourceWriter, "_resource_toolchain_commands", staticmethod(lambda: object()))
    assert ResourceWriter().has_toolchain() is True
