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
    load_default_term_translations,
    prefill_translation_text,
    resolve_terminology_file,
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


def test_prefill_translation_text_replaces_known_terms_inside_text() -> None:
    term_map = {
        "Bounty Hunters Guild": "Gilde der Kopfgeldjaeger",
        "Equipment Dealer": "Ausruestungshaendler",
    }

    translated = prefill_translation_text("Bounty Hunters Guild\nEquipment Dealer\nJohn Fahrenheit", term_map)

    assert translated == "Gilde der Kopfgeldjaeger\nAusruestungshaendler\nJohn Fahrenheit"


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
