from pathlib import Path

from flatlas_translator.catalog import pair_catalogs
from flatlas_translator.dll_plans import DllStrategy, build_dll_plans
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


def test_build_dll_plans_marks_full_replace_when_id_sets_match() -> None:
    source = ResourceCatalog(
        install_dir=Path("C:/source"),
        freelancer_ini=Path("C:/source/EXE/freelancer.ini"),
        units=(
            _unit(ResourceKind.STRING, "NameResources.dll", 1, "New York"),
            _unit(ResourceKind.STRING, "NameResources.dll", 2, "Texas"),
        ),
    )
    target = ResourceCatalog(
        install_dir=Path("C:/target"),
        freelancer_ini=Path("C:/target/EXE/freelancer.ini"),
        units=(
            _unit(ResourceKind.STRING, "NameResources.dll", 1, "Neu York"),
            _unit(ResourceKind.STRING, "NameResources.dll", 2, "Texas"),
        ),
    )
    paired = pair_catalogs(source, target)

    plans = build_dll_plans(source, paired, target)

    assert plans[0].strategy == DllStrategy.FULL_REPLACE_SAFE


def test_build_dll_plans_marks_patch_when_auto_relocalize_exists_but_sets_differ() -> None:
    source = ResourceCatalog(
        install_dir=Path("C:/source"),
        freelancer_ini=Path("C:/source/EXE/freelancer.ini"),
        units=(
            _unit(ResourceKind.STRING, "OfferBribeResources.dll", 1, "English A"),
            _unit(ResourceKind.STRING, "OfferBribeResources.dll", 99, "Mod Only"),
        ),
    )
    target = ResourceCatalog(
        install_dir=Path("C:/target"),
        freelancer_ini=Path("C:/target/EXE/freelancer.ini"),
        units=(_unit(ResourceKind.STRING, "OfferBribeResources.dll", 1, "Deutsch A"),),
    )
    paired = pair_catalogs(source, target)

    plans = build_dll_plans(source, paired, target)

    assert plans[0].strategy == DllStrategy.PATCH_REQUIRED


def test_build_dll_plans_marks_not_safe_when_no_german_match_exists() -> None:
    source = ResourceCatalog(
        install_dir=Path("C:/source"),
        freelancer_ini=Path("C:/source/EXE/freelancer.ini"),
        units=(_unit(ResourceKind.STRING, "CustomMod.dll", 5, "Only Mod Text"),),
    )
    target = ResourceCatalog(
        install_dir=Path("C:/target"),
        freelancer_ini=Path("C:/target/EXE/freelancer.ini"),
        units=(),
    )
    paired = pair_catalogs(source, target)

    plans = build_dll_plans(source, paired, target)

    assert plans[0].strategy == DllStrategy.NOT_SAFE


def test_build_dll_plans_counts_translated_units_per_dll() -> None:
    source = ResourceCatalog(
        install_dir=Path("C:/source"),
        freelancer_ini=Path("C:/source/EXE/freelancer.ini"),
        units=(
            _unit(ResourceKind.STRING, "InfoCards.dll", 1, "Same"),
            _unit(ResourceKind.STRING, "InfoCards.dll", 2, "English Text"),
            _unit(ResourceKind.STRING, "InfoCards.dll", 3, "Mod Only"),
            _unit(ResourceKind.STRING, "InfoCards.dll", 4, "Manual Source"),
        ),
    )
    target = ResourceCatalog(
        install_dir=Path("C:/target"),
        freelancer_ini=Path("C:/target/EXE/freelancer.ini"),
        units=(
            _unit(ResourceKind.STRING, "InfoCards.dll", 1, "Same"),
            _unit(ResourceKind.STRING, "InfoCards.dll", 2, "Deutscher Text"),
            _unit(ResourceKind.STRING, "InfoCards.dll", 4, "Noch nicht manuell"),
        ),
    )
    paired = pair_catalogs(source, target)
    paired = ResourceCatalog(
        install_dir=paired.install_dir,
        freelancer_ini=paired.freelancer_ini,
        units=tuple(
            TranslationUnit(
                kind=unit.kind,
                source=unit.source,
                source_text=unit.source_text,
                target=unit.target,
                target_text=unit.target_text,
                manual_text="Manuell gesetzt" if unit.source.local_id == 4 else unit.manual_text,
            )
            for unit in paired.units
        ),
    )

    plans = build_dll_plans(source, paired, target)

    assert plans[0].translated_units == 3
