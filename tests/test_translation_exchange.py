import json
from pathlib import Path

from flatlas_translator.models import ResourceCatalog, ResourceKind, ResourceLocation, TranslationUnit, make_global_id
from flatlas_translator.translation_exchange import export_mod_only_exchange, import_exchange, update_manual_translation


def _unit(
    text: str,
    *,
    manual_text: str = "",
    target_text: str = "",
    local_id: int = 5,
    with_target: bool = False,
) -> TranslationUnit:
    location = ResourceLocation(
        dll_name="CustomMod.dll",
        dll_path=Path("C:/dummy/CustomMod.dll"),
        local_id=local_id,
        slot=1,
        global_id=make_global_id(1, local_id),
    )
    return TranslationUnit(
        kind=ResourceKind.STRING,
        source=location,
        source_text=text,
        target=location if with_target else None,
        target_text=target_text,
        manual_text=manual_text,
    )


def test_export_mod_only_exchange_exports_only_mod_only_entries(tmp_path: Path) -> None:
    catalog = ResourceCatalog(
        install_dir=Path("C:/source"),
        freelancer_ini=Path("C:/source/EXE/freelancer.ini"),
        units=(
            _unit("Custom text", local_id=5),
            _unit("Planet Manhattan", local_id=7),
            _unit("Bounty Hunters Guild", local_id=8),
            _unit("Bounty Hunters Guild", target_text="Gilde der Kopfgeldjaeger", local_id=9, with_target=True),
            _unit("Equipment Dealer", target_text="Ausruestungshaendler", local_id=10, with_target=True),
            _unit("German ref", target_text="Deutscher Text", local_id=6, with_target=True),
        ),
    )

    report = export_mod_only_exchange(catalog, tmp_path / "exchange.json")
    data = json.loads(report.output_path.read_text(encoding="utf-8"))

    assert len(data["entries"]) == 2
    assert data["entries"][0]["source_text"] == "Custom text"
    assert data["entries"][1]["source_text"] == "Bounty Hunters Guild"
    assert data["entries"][1]["translation_text"] == "Gilde der Kopfgeldjaeger"
    assert report.exported_entries == 2
    assert report.skipped_entries == 1
    assert data["metadata"]["skipped_entries"] == 1
    assert data["glossary"][0]["source_term"] == "Bounty Hunters Guild"
    assert data["glossary"][0]["target_term"] == "Gilde der Kopfgeldjaeger"


def test_import_exchange_applies_manual_text_to_matching_units(tmp_path: Path) -> None:
    catalog = ResourceCatalog(
        install_dir=Path("C:/source"),
        freelancer_ini=Path("C:/source/EXE/freelancer.ini"),
        units=(_unit("Custom text"),),
    )
    exchange_path = tmp_path / "exchange.json"
    exchange_path.write_text(
        json.dumps(
            {
                "format": "flatlas-translator-exchange",
                "version": 1,
                "entries": [
                    {
                        "kind": "string",
                        "dll_name": "CustomMod.dll",
                        "local_id": 5,
                        "translation_text": "Benutzer Uebersetzung",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    merged = import_exchange(catalog, exchange_path)

    assert merged.units[0].manual_text == "Benutzer Uebersetzung"


def test_update_manual_translation_sets_and_clears_manual_text() -> None:
    catalog = ResourceCatalog(
        install_dir=Path("C:/source"),
        freelancer_ini=Path("C:/source/EXE/freelancer.ini"),
        units=(_unit("Custom text", manual_text="Alt"),),
    )

    updated = update_manual_translation(
        catalog,
        kind="string",
        dll_name="CustomMod.dll",
        local_id=5,
        manual_text="Neu",
    )
    cleared = update_manual_translation(
        updated,
        kind="string",
        dll_name="CustomMod.dll",
        local_id=5,
        manual_text="",
    )

    assert updated.units[0].manual_text == "Neu"
    assert cleared.units[0].manual_text == ""
