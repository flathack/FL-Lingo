import json
from pathlib import Path

from flatlas_translator.models import ResourceCatalog, ResourceKind, ResourceLocation, TranslationUnit, make_global_id
from flatlas_translator import terminology
from flatlas_translator.terminology import (
    apply_known_term_suggestions,
    build_term_map,
    clear_term_map_cache,
    extract_faction_glossary,
    is_line_non_translatable,
    is_unit_skippable,
    list_pattern_entries,
    load_replacement_patterns,
    load_default_term_translations,
    prefill_translation_text,
    resolve_terminology_file,
    save_replacement_pattern,
    save_term_mapping,
)


def _unit(text: str, *, local_id: int = 1, target_text: str = "", with_target: bool = False) -> TranslationUnit:
    source = ResourceLocation(
        dll_name="CustomMod.dll",
        dll_path=Path("C:/dummy/CustomMod.dll"),
        local_id=local_id,
        slot=1,
        global_id=make_global_id(1, local_id),
    )
    return TranslationUnit(
        kind=ResourceKind.STRING,
        source=source,
        source_text=text,
        target=source if with_target else None,
        target_text=target_text,
    )


def test_line_non_translatable_for_locations_and_person_names_only() -> None:
    assert is_line_non_translatable("Bounty Hunters Guild") is False
    assert is_line_non_translatable("Rochester Station") is True
    assert is_line_non_translatable("Planet Manhattan") is True
    assert is_line_non_translatable("John Fahrenheit") is True
    assert is_line_non_translatable("Equipment Dealer") is False
    assert is_line_non_translatable("#") is True
    assert is_line_non_translatable("6/0") is True
    assert is_line_non_translatable("10700") is True


def test_unit_skippable_only_when_all_lines_are_non_translatable() -> None:
    assert is_unit_skippable(_unit("Planet Manhattan\nJohn Fahrenheit")) is True
    assert is_unit_skippable(_unit("Bounty Hunters Guild\nJohn Fahrenheit", local_id=2)) is False


def test_extract_faction_glossary_collects_known_factions_from_catalog_terms() -> None:
    catalog = ResourceCatalog(
        install_dir=Path("C:/source"),
        freelancer_ini=Path("C:/source/EXE/freelancer.ini"),
        units=(
            _unit("Bounty Hunters Guild", local_id=1, target_text="Gilde der Kopfgeldjaeger", with_target=True),
            _unit("Bounty Hunters Guild\nJohn Fahrenheit", local_id=2),
            _unit("Planet Manhattan", local_id=3),
        ),
    )

    glossary = extract_faction_glossary(catalog.units, build_term_map(catalog.units, target_language="de"), target_language="de")

    assert len(glossary) == 1
    assert glossary[0].source_term == "Bounty Hunters Guild"
    assert glossary[0].target_term == "Gilde der Kopfgeldjaeger"


def test_apply_known_term_suggestions_translates_structured_npc_entry() -> None:
    catalog = ResourceCatalog(
        install_dir=Path("C:/source"),
        freelancer_ini=Path("C:/source/EXE/freelancer.ini"),
        units=(
            _unit("Bounty Hunters Guild", local_id=1, target_text="Gilde der Kopfgeldjaeger", with_target=True),
            _unit("Equipment Dealer", local_id=2, target_text="Ausruestungshaendler", with_target=True),
            _unit("Bounty Hunters Guild\nEquipment Dealer\nJohn Fahrenheit", local_id=3),
        ),
    )

    updated = apply_known_term_suggestions(catalog)

    assert updated.units[2].manual_text == "Gilde der Kopfgeldjaeger\nAusruestungshaendler\nJohn Fahrenheit"


def test_apply_known_term_suggestions_translates_known_terms_inside_composite_npc_line() -> None:
    catalog = ResourceCatalog(
        install_dir=Path("C:/source"),
        freelancer_ini=Path("C:/source/EXE/freelancer.ini"),
        units=(
            _unit("Blood Dragons\nShogun Base Equipment Dealer\nRikyu Asari", local_id=11),
        ),
    )

    updated = apply_known_term_suggestions(catalog)

    assert updated.units[0].manual_text == "Blutdrachen\nShogun Base Ausruestungshaendler\nRikyu Asari"


def test_prefill_translation_text_replaces_known_terms_inside_text() -> None:
    term_map = {
        "Bounty Hunters Guild": "Gilde der Kopfgeldjaeger",
        "Equipment Dealer": "Ausruestungshaendler",
    }

    translated = prefill_translation_text("Bounty Hunters Guild\nEquipment Dealer\nJohn Fahrenheit", term_map)

    assert translated == "Gilde der Kopfgeldjaeger\nAusruestungshaendler\nJohn Fahrenheit"


def test_prefill_translation_text_translates_colon_labels_without_touching_values() -> None:
    term_map = {
        "Armor": "Panzerung",
        "Cargo Holds": "Laderaum",
        "Additional Equipment": "Zusatzausruestung",
    }

    translated = prefill_translation_text(
        "Armor: 10700\nCargo Holds: 100\nAdditional Equipment: M, CM, CD/T",
        term_map,
    )

    assert translated == "Panzerung: 10700\nLaderaum: 100\nZusatzausruestung: M, CM, CD/T"


def test_prefill_translation_text_applies_pattern_replacements() -> None:
    translated = prefill_translation_text(
        "Power Generator MK I\nPolice Licence",
        {"Police": "Polizei"},
        patterns=load_replacement_patterns("de"),
    )

    assert "Energiegenerator MK I" in translated
    assert "Polizei Lizenz" in translated


def test_prefill_translation_text_applies_story_phrase_replacements() -> None:
    translated = prefill_translation_text(
        "Our scientists don't know what it is exactly and how it does work.",
        {},
        patterns=load_replacement_patterns("de"),
    )

    assert translated == "Unsere Wissenschaftler wissen nicht genau, was es ist und wie es funktioniert."


def test_prefill_translation_text_translates_rdl_text_nodes_conservatively() -> None:
    translated = prefill_translation_text(
        (
            '<?xml version="1.0" encoding="UTF-16"?><RDL><PUSH/>'
            "<TEXT>DIAMETER: 4,821 km</TEXT>"
            "<PARA/>"
            "<TEXT>Whatever atmosphere may have once been present has evaporated into space over the millennia.</TEXT>"
            "<PARA/>"
            "<TEXT>Tanyer is a hot, dry world warmed by internal volcanic processes.</TEXT>"
            "<POP/></RDL>"
        ),
        load_default_term_translations("de"),
        patterns=load_replacement_patterns("de"),
    )

    assert "<TEXT>DURCHMESSER: 4,821 km</TEXT>" in translated
    assert "Welche Atmosphaere auch immer einst vorhanden war, ist im Laufe der Jahrtausende ins All entwichen." in translated
    assert "internal volcanic processes" in translated


def test_apply_known_term_suggestions_translates_ship_info_labels_before_colon() -> None:
    catalog = ResourceCatalog(
        install_dir=Path("C:/source"),
        freelancer_ini=Path("C:/source/EXE/freelancer.ini"),
        units=(
            _unit(
                "Guns/Turrets: 6/0\n"
                "Armor: 10700\n"
                "Cargo Holds: 100\n"
                "Max Batteries/NanoBots: 100/100\n"
                "Optimal Weapon Class: 8\n"
                "Max. Weapon Class: 10\n"
                "Additional Equipment: M, CM, CD/T",
                local_id=12,
            ),
        ),
    )

    updated = apply_known_term_suggestions(catalog)

    assert updated.units[0].manual_text == (
        "Geschuetze/Tuerme: 6/0\n"
        "Panzerung: 10700\n"
        "Laderaum: 100\n"
        "Max Batterien/Nanobots: 100/100\n"
        "Optimale Waffenklasse: 8\n"
        "Max. Waffenklasse: 10\n"
        "Zusatzausruestung: M, CM, CD/T"
    )


def test_apply_known_term_suggestions_translates_named_clouds_fields_and_class_labels() -> None:
    catalog = ResourceCatalog(
        install_dir=Path("C:/source"),
        freelancer_ini=Path("C:/source/EXE/freelancer.ini"),
        units=(
            _unit("the Aquarius Cloud", local_id=20),
            _unit("the Vorgha Field", local_id=21),
            _unit("Class: Eden", local_id=22),
        ),
    )

    updated = apply_known_term_suggestions(catalog)

    assert updated.units[0].manual_text == "die Aquarius-Wolke"
    assert updated.units[1].manual_text == "das Vorgha-Feld"
    assert updated.units[2].manual_text == "Klasse: Eden"


def test_load_default_term_translations_from_file(tmp_path: Path, monkeypatch) -> None:
    terminology_path = tmp_path / "terminology.de.json"
    terminology_path.write_text(
        json.dumps(
            {
                "language": "de",
                "terms": {
                    "factions": {"Bounty Hunters Guild": "Kopfgeldjaeger-Gilde"},
                    "roles": {"Equipment Dealer": "Ausruestungshaendler"},
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(terminology, "_terminology_file_candidates", lambda language_code: [terminology_path])
    clear_term_map_cache()

    loaded = load_default_term_translations("de")

    assert loaded["Bounty Hunters Guild"] == "Kopfgeldjaeger-Gilde"
    assert loaded["Equipment Dealer"] == "Ausruestungshaendler"
    clear_term_map_cache()


def test_resolve_terminology_file_uses_language_specific_name(tmp_path: Path, monkeypatch) -> None:
    expected = tmp_path / "terminology.fr.json"
    monkeypatch.setattr(terminology, "_terminology_file_candidates", lambda language_code: [tmp_path / f"terminology.{language_code}.json"])
    clear_term_map_cache()

    resolved = resolve_terminology_file("fr")

    assert resolved == expected
    assert resolved.is_file()


def test_save_term_mapping_updates_or_adds_term_in_file(tmp_path: Path, monkeypatch) -> None:
    terminology_path = tmp_path / "terminology.de.json"
    terminology_path.write_text(
        json.dumps(
            {
                "language": "de",
                "terms": {
                    "factions": {"Blood Dragons": "Blutdrachen"},
                    "misc": {},
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(terminology, "_terminology_file_candidates", lambda language_code: [terminology_path])
    clear_term_map_cache()

    save_term_mapping("de", "Blood Dragons", "Die Blutdrachen")
    save_term_mapping("de", "Golden Crysanthenums", "Goldene Chrysanthemen")

    payload = json.loads(terminology_path.read_text(encoding="utf-8"))
    assert payload["terms"]["factions"]["Blood Dragons"] == "Die Blutdrachen"
    assert payload["terms"]["misc"]["Golden Crysanthenums"] == "Goldene Chrysanthemen"


def test_save_replacement_pattern_adds_pattern_in_file(tmp_path: Path, monkeypatch) -> None:
    terminology_path = tmp_path / "terminology.de.json"
    terminology_path.write_text(
        json.dumps(
            {
                "language": "de",
                "terms": {"misc": {}},
                "patterns": {"generic": {"Scanner": "Scanner"}},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(terminology, "_terminology_file_candidates", lambda language_code: [terminology_path])
    clear_term_map_cache()

    save_replacement_pattern("de", "Power Generator", "Energiegenerator")
    patterns = list_pattern_entries("de")
    payload = json.loads(terminology_path.read_text(encoding="utf-8"))

    assert any(pattern.source_text == "Power Generator" and pattern.target_text == "Energiegenerator" for pattern in patterns)
    assert payload["patterns"]["generic"]["Power Generator"] == "Energiegenerator"
