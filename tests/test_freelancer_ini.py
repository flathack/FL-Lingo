from pathlib import Path

from flatlas_translator.freelancer_ini import parse_resource_dll_names


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
