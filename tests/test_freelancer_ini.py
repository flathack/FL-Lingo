from pathlib import Path

from flatlas_translator.freelancer_ini import load_resource_dlls, parse_resource_dll_names


def test_parse_resource_dll_names_deduplicates_and_ignores_comments(tmp_path: Path) -> None:
    ini_path = tmp_path / "freelancer.ini"
    ini_path.write_text(
        """
        [Resources]
        DLL = InfoCards.dll ; comment
        DLL = EquipResources.dll, NORMAL
        DLL = resources_vanilla.dll
        DLL = InfoCards.dll
        """,
        encoding="utf-8",
    )

    result = parse_resource_dll_names(ini_path)

    assert result == ["InfoCards.dll", "EquipResources.dll"]


def test_load_resource_dlls_includes_supplemental_ui_dll_when_present(tmp_path: Path) -> None:
    install_dir = tmp_path / "Freelancer"
    exe_dir = install_dir / "EXE"
    exe_dir.mkdir(parents=True)
    ini_path = exe_dir / "freelancer.ini"
    ini_path.write_text(
        """
        [Resources]
        DLL = InfoCards.dll
        """,
        encoding="utf-8",
    )
    (exe_dir / "InfoCards.dll").write_text("", encoding="utf-8")
    (exe_dir / "resources.dll").write_text("", encoding="utf-8")

    _ini, resources = load_resource_dlls(install_dir)

    assert [resource.dll_name for resource in resources] == ["InfoCards.dll", "resources.dll"]
