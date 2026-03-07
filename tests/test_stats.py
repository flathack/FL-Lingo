from pathlib import Path

from flatlas_translator.models import ResourceCatalog, ResourceKind, ResourceLocation, TranslationUnit, make_global_id
from flatlas_translator.stats import summarize_catalog


def test_summarize_catalog_counts_matched_and_changed() -> None:
    source = ResourceLocation(
        dll_name="NameResources.dll",
        dll_path=Path("C:/dummy/NameResources.dll"),
        local_id=1,
        slot=1,
        global_id=make_global_id(1, 1),
    )
    target = ResourceLocation(
        dll_name="NameResources.dll",
        dll_path=Path("C:/dummy2/NameResources.dll"),
        local_id=1,
        slot=1,
        global_id=make_global_id(1, 1),
    )
    catalog = ResourceCatalog(
        install_dir=Path("C:/source"),
        freelancer_ini=Path("C:/source/EXE/freelancer.ini"),
        units=(
            TranslationUnit(ResourceKind.STRING, source, "New York", target, "Neu York"),
            TranslationUnit(ResourceKind.STRING, source, "Texas", target, "Texas"),
        ),
    )

    stats = summarize_catalog(catalog, ResourceKind.STRING)

    assert stats.total == 2
    assert stats.matched == 2
    assert stats.changed == 1
    assert stats.auto_relocalize == 1
    assert stats.already_localized == 1
    assert stats.mod_only == 0
