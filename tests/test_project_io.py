import json
from pathlib import Path

from flatlas_translator.catalog import pair_catalogs
from flatlas_translator.project_io import PROJECT_FILE_FORMAT, TranslatorProject, load_project, project_signature, save_project
from flatlas_translator.models import ResourceCatalog, ResourceKind, ResourceLocation, TranslationUnit, make_global_id


def _location(dll_name: str, local_id: int, root: str) -> ResourceLocation:
    return ResourceLocation(
        dll_name=dll_name,
        dll_path=Path(f"{root}/{dll_name}"),
        local_id=local_id,
        slot=1,
        global_id=make_global_id(1, local_id),
    )


def test_save_project_writes_manual_edits_and_metadata(tmp_path: Path) -> None:
    source = _location("NameResources.dll", 1, "C:/source")
    target = _location("NameResources.dll", 1, "C:/target")
    source_catalog = ResourceCatalog(
        install_dir=Path("C:/source"),
        freelancer_ini=Path("C:/source/EXE/freelancer.ini"),
        units=(TranslationUnit(ResourceKind.STRING, source, "New York"),),
    )
    target_catalog = ResourceCatalog(
        install_dir=Path("C:/target"),
        freelancer_ini=Path("C:/target/EXE/freelancer.ini"),
        units=(TranslationUnit(ResourceKind.STRING, target, "Neu York"),),
    )
    paired_catalog = ResourceCatalog(
        install_dir=Path("C:/source"),
        freelancer_ini=Path("C:/source/EXE/freelancer.ini"),
        units=(TranslationUnit(ResourceKind.STRING, source, "New York", target, "Neu York", "Meine Version"),),
    )
    project = TranslatorProject(
        source_install_dir="C:/source",
        target_install_dir="C:/target",
        include_infocards=True,
        source_language="en",
        target_language="de",
        source_catalog=source_catalog,
        target_catalog=target_catalog,
        paired_catalog=paired_catalog,
        dll_plans=(),
    )

    output_path = save_project(project, tmp_path / "translator-project.FLLingo")
    data = json.loads(output_path.read_text(encoding="utf-8"))

    assert data["format"] == PROJECT_FILE_FORMAT
    assert data["source_language"] == "en"
    assert data["target_language"] == "de"
    assert data["paired_catalog"]["units"][0]["manual_text"] == "Meine Version"


def test_load_project_restores_catalogs_and_rebuilds_dll_plans(tmp_path: Path) -> None:
    source = _location("NameResources.dll", 1, "C:/source")
    target = _location("NameResources.dll", 1, "C:/target")
    source_catalog = ResourceCatalog(
        install_dir=Path("C:/source"),
        freelancer_ini=Path("C:/source/EXE/freelancer.ini"),
        units=(TranslationUnit(ResourceKind.STRING, source, "New York"),),
    )
    target_catalog = ResourceCatalog(
        install_dir=Path("C:/target"),
        freelancer_ini=Path("C:/target/EXE/freelancer.ini"),
        units=(TranslationUnit(ResourceKind.STRING, target, "Neu York"),),
    )
    paired_catalog = pair_catalogs(source_catalog, target_catalog)
    save_project(
        TranslatorProject(
            source_install_dir="C:/source",
            target_install_dir="C:/target",
            include_infocards=False,
            source_language="en",
            target_language="fr",
            source_catalog=source_catalog,
            target_catalog=target_catalog,
            paired_catalog=paired_catalog,
            dll_plans=(),
        ),
        tmp_path / "translator-project.FLLingo",
    )

    loaded = load_project(tmp_path / "translator-project.FLLingo")

    assert loaded.source_install_dir == "C:/source"
    assert loaded.target_install_dir == "C:/target"
    assert loaded.include_infocards is False
    assert loaded.target_language == "fr"
    assert loaded.paired_catalog is not None
    assert loaded.paired_catalog.units[0].target_text == "Neu York"
    assert len(loaded.dll_plans) == 1


def test_project_signature_changes_when_manual_text_changes() -> None:
    source = _location("NameResources.dll", 1, "C:/source")
    base = TranslatorProject(
        source_install_dir="C:/source",
        target_install_dir="C:/target",
        include_infocards=True,
        source_language="en",
        target_language="de",
        source_catalog=None,
        target_catalog=None,
        paired_catalog=ResourceCatalog(
            install_dir=Path("C:/source"),
            freelancer_ini=Path("C:/source/EXE/freelancer.ini"),
            units=(TranslationUnit(ResourceKind.STRING, source, "A", manual_text=""),),
        ),
        dll_plans=(),
    )
    changed = TranslatorProject(
        source_install_dir=base.source_install_dir,
        target_install_dir=base.target_install_dir,
        include_infocards=base.include_infocards,
        source_language=base.source_language,
        target_language=base.target_language,
        source_catalog=base.source_catalog,
        target_catalog=base.target_catalog,
        paired_catalog=ResourceCatalog(
            install_dir=Path("C:/source"),
            freelancer_ini=Path("C:/source/EXE/freelancer.ini"),
            units=(TranslationUnit(ResourceKind.STRING, source, "A", manual_text="B"),),
        ),
        dll_plans=(),
    )

    assert project_signature(base) != project_signature(changed)


def test_load_project_normalizes_null_bulk_translate_log_entries(tmp_path: Path) -> None:
    payload = {
        "format": PROJECT_FILE_FORMAT,
        "version": 1,
        "source_install_dir": "C:/source",
        "target_install_dir": "C:/target",
        "include_infocards": True,
        "source_language": "en",
        "target_language": "de",
        "source_catalog": None,
        "target_catalog": None,
        "paired_catalog": None,
        "bulk_translate_log": [["resources.dll:1", None, "Hallo"], [None, "Hello", None], ["skip-me"]],
    }
    project_path = tmp_path / "translator-project.FLLingo"
    project_path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = load_project(project_path)

    assert loaded.bulk_translate_log == (
        ("resources.dll:1", "", "Hallo"),
        ("", "Hello", ""),
    )
