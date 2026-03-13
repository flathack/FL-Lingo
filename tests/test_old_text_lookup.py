from pathlib import Path

from flatlas_translator.models import ResourceCatalog, ResourceKind, ResourceLocation, TranslationUnit, make_global_id
from flatlas_translator.ui_session import UISessionMixin


def _location(dll_name: str, local_id: int) -> ResourceLocation:
    return ResourceLocation(
        dll_name=dll_name,
        dll_path=Path(f"C:/dummy/{dll_name}"),
        local_id=local_id,
        slot=1,
        global_id=make_global_id(1, local_id),
    )


class _StubStringReader:
    def read_strings(self, dll_path: Path) -> dict[int, str]:
        assert dll_path.name == "resources.dll"
        return {907: "Old English text from backup"}


class _StubHtmlReader:
    def read_html_resources(self, dll_path: Path) -> dict[int, str]:
        return {}


def test_build_old_text_lookup_reads_matching_backup_dll(monkeypatch) -> None:
    backup_dir = Path("C:/backup")
    catalog = ResourceCatalog(
        install_dir=Path("C:/mod"),
        freelancer_ini=Path("C:/mod/EXE/freelancer.ini"),
        units=(
            TranslationUnit(
                kind=ResourceKind.STRING,
                source=_location("resources.dll", 907),
                source_text="Current translated text",
            ),
        ),
    )

    monkeypatch.setattr(Path, "is_file", lambda self: str(self).lower().endswith("resources.dll"))

    lookup = UISessionMixin._build_old_text_lookup(
        catalog,
        backup_dir,
        string_reader=_StubStringReader(),
        html_reader=_StubHtmlReader(),
    )

    assert lookup == {
        ("string", "resources.dll", 907): "Old English text from backup",
    }
