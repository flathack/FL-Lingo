import json
from pathlib import Path

from flatlas_translator.models import ResourceCatalog, ResourceKind, ResourceLocation, TranslationUnit, make_global_id
from flatlas_translator.translation_exchange import (
    LONG_TEXT_MIN_LENGTH,
    export_all_translated,
    export_long_open_exchange,
    export_mod_only_exchange,
    import_exchange,
    update_manual_translation,
)


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


def test_export_long_open_exchange_exports_only_long_open_entries(tmp_path: Path) -> None:
    long_text = "A" * (LONG_TEXT_MIN_LENGTH + 5)
    short_text = "Short open text"
    long_skippable = "#\n" * LONG_TEXT_MIN_LENGTH
    catalog = ResourceCatalog(
        install_dir=Path("C:/source"),
        freelancer_ini=Path("C:/source/EXE/freelancer.ini"),
        units=(
            _unit(long_text, local_id=20),
            _unit(short_text, local_id=21),
            _unit(long_skippable, local_id=22),
            _unit("Matched ref", target_text="Deutscher Text", local_id=23, with_target=True),
        ),
    )

    report = export_long_open_exchange(catalog, tmp_path / "long-open.json")
    data = json.loads(report.output_path.read_text(encoding="utf-8"))

    assert report.exported_entries == 1
    assert report.skipped_entries == 1
    assert data["entries"][0]["source_text"] == long_text
    assert data["metadata"]["exported_entries"] == 1
    assert data["metadata"]["skipped_entries"] == 1


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


def test_update_manual_translation_sets_translation_source() -> None:
    catalog = ResourceCatalog(
        install_dir=Path("C:/source"),
        freelancer_ini=Path("C:/source/EXE/freelancer.ini"),
        units=(_unit("Custom text"),),
    )

    updated = update_manual_translation(
        catalog,
        kind="string",
        dll_name="CustomMod.dll",
        local_id=5,
        manual_text="Übersetzt",
        translation_source="auto_translate",
    )
    cleared = update_manual_translation(
        updated,
        kind="string",
        dll_name="CustomMod.dll",
        local_id=5,
        manual_text="",
        translation_source="auto_translate",
    )

    assert updated.units[0].translation_source == "auto_translate"
    assert updated.units[0].status.name == "MANUAL_TRANSLATION"
    assert cleared.units[0].translation_source == ""
    assert cleared.units[0].status.name == "MOD_ONLY"


def test_export_all_translated_exports_translated_entries(tmp_path: Path) -> None:
    catalog = ResourceCatalog(
        install_dir=Path("C:/source"),
        freelancer_ini=Path("C:/source/EXE/freelancer.ini"),
        units=(
            _unit("Open text", local_id=1),
            _unit("Auto text", target_text="Auto Übersetzung", local_id=2, with_target=True),
            _unit("Manual text", manual_text="Manuelle Übersetzung", local_id=3),
            _unit("Both", target_text="Ref", manual_text="Manuell", local_id=4, with_target=True),
        ),
    )
    report = export_all_translated(catalog, tmp_path / "all.json")
    data = json.loads(report.output_path.read_text(encoding="utf-8"))

    assert report.exported_entries == 3
    assert len(data["entries"]) == 3
    assert data["entries"][0]["translation_text"] == "Auto Übersetzung"
    assert data["entries"][1]["translation_text"] == "Manuelle Übersetzung"
    assert data["entries"][2]["translation_text"] == "Manuell"
    assert data["metadata"]["type"] == "all-translated"


def test_export_all_translated_roundtrips_through_import(tmp_path: Path) -> None:
    catalog = ResourceCatalog(
        install_dir=Path("C:/source"),
        freelancer_ini=Path("C:/source/EXE/freelancer.ini"),
        units=(
            _unit("Open text", local_id=1),
            _unit("Has ref", target_text="Ref Text", local_id=2, with_target=True),
            _unit("Manual", manual_text="Mein Text", local_id=3),
        ),
    )
    export_path = tmp_path / "all.json"
    export_all_translated(catalog, export_path)

    # Import into a fresh catalog (same structure, no translations)
    fresh = ResourceCatalog(
        install_dir=Path("C:/new"),
        freelancer_ini=Path("C:/new/EXE/freelancer.ini"),
        units=(
            _unit("Open text", local_id=1),
            _unit("Has ref", local_id=2),
            _unit("Manual", local_id=3),
        ),
    )
    merged = import_exchange(fresh, export_path)

    assert merged.units[0].manual_text == ""
    assert merged.units[1].manual_text == "Ref Text"
    assert merged.units[2].manual_text == "Mein Text"
