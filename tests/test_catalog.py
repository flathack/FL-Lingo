from pathlib import Path

from flatlas_translator.catalog import pair_catalogs
from flatlas_translator.models import ResourceCatalog, ResourceKind, ResourceLocation, TranslationUnit, make_global_id


def _unit(kind: ResourceKind, dll_name: str, local_id: int, text: str) -> TranslationUnit:
    location = ResourceLocation(
        dll_name=dll_name,
        dll_path=Path(f"C:/dummy/{dll_name}"),
        local_id=local_id,
        slot=1,
        global_id=make_global_id(1, local_id),
    )
    return TranslationUnit(kind=kind, source=location, source_text=text)


def test_pair_catalogs_matches_by_kind_dll_and_local_id() -> None:
    source = ResourceCatalog(
        install_dir=Path("C:/source"),
        freelancer_ini=Path("C:/source/EXE/freelancer.ini"),
        units=(
            _unit(ResourceKind.STRING, "NameResources.dll", 1, "New York"),
            _unit(ResourceKind.INFOCARD, "InfoCards.dll", 3, "<RDL>Source</RDL>"),
        ),
    )
    target = ResourceCatalog(
        install_dir=Path("C:/target"),
        freelancer_ini=Path("C:/target/EXE/freelancer.ini"),
        units=(
            _unit(ResourceKind.STRING, "NameResources.dll", 1, "New York"),
            _unit(ResourceKind.INFOCARD, "InfoCards.dll", 3, "<RDL>Ziel</RDL>"),
        ),
    )

    paired = pair_catalogs(source, target)

    assert paired.units[0].target_text == "New York"
    assert paired.units[1].target_text == "<RDL>Ziel</RDL>"


def test_pair_catalogs_leaves_missing_targets_empty() -> None:
    source = ResourceCatalog(
        install_dir=Path("C:/source"),
        freelancer_ini=Path("C:/source/EXE/freelancer.ini"),
        units=(_unit(ResourceKind.STRING, "NameResources.dll", 2, "Texas"),),
    )
    target = ResourceCatalog(
        install_dir=Path("C:/target"),
        freelancer_ini=Path("C:/target/EXE/freelancer.ini"),
        units=(),
    )

    paired = pair_catalogs(source, target)

    assert paired.units[0].target is None
    assert paired.units[0].target_text == ""
