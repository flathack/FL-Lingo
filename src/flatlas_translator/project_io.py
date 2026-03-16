"""Save and load FL Lingo project files."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .dll_plans import DllRelocalizationPlan, build_dll_plans
from .models import ResourceCatalog, ResourceKind, ResourceLocation, TranslationUnit

PROJECT_FILE_EXTENSION = ".FLLingo"
PROJECT_FILE_FORMAT = "fl-lingo-project"


@dataclass(frozen=True, slots=True)
class TranslatorProject:
    source_install_dir: str
    target_install_dir: str
    include_infocards: bool
    source_language: str
    target_language: str
    source_catalog: ResourceCatalog | None
    target_catalog: ResourceCatalog | None
    paired_catalog: ResourceCatalog | None
    dll_plans: tuple[DllRelocalizationPlan, ...]
    en_ref_install_dir: str = ""


def save_project(project: TranslatorProject, output_path: Path) -> Path:
    payload = _project_payload(project)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return output_path


def load_project(input_path: Path) -> TranslatorProject:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    if payload.get("format") != PROJECT_FILE_FORMAT:
        raise ValueError("Unsupported project file format.")

    source_catalog = _catalog_from_dict(payload.get("source_catalog"))
    target_catalog = _catalog_from_dict(payload.get("target_catalog"))
    paired_catalog = _catalog_from_dict(payload.get("paired_catalog"))
    dll_plans = _rebuild_dll_plans(source_catalog, paired_catalog, target_catalog)

    return TranslatorProject(
        source_install_dir=str(payload.get("source_install_dir", "") or ""),
        target_install_dir=str(payload.get("target_install_dir", "") or ""),
        include_infocards=bool(payload.get("include_infocards", True)),
        source_language=str(payload.get("source_language", "en") or "en"),
        target_language=str(payload.get("target_language", "de") or "de"),
        source_catalog=source_catalog,
        target_catalog=target_catalog,
        paired_catalog=paired_catalog,
        dll_plans=dll_plans,
        en_ref_install_dir=str(payload.get("en_ref_install_dir", "") or ""),
    )


def project_signature(project: TranslatorProject) -> str:
    return json.dumps(_project_payload(project), sort_keys=True, ensure_ascii=False)


def _rebuild_dll_plans(
    source_catalog: ResourceCatalog | None,
    paired_catalog: ResourceCatalog | None,
    target_catalog: ResourceCatalog | None,
) -> tuple[DllRelocalizationPlan, ...]:
    if source_catalog is None or paired_catalog is None or target_catalog is None:
        return ()
    return tuple(build_dll_plans(source_catalog, paired_catalog, target_catalog))


def _project_payload(project: TranslatorProject) -> dict[str, object]:
    return {
        "format": PROJECT_FILE_FORMAT,
        "version": 1,
        "source_install_dir": project.source_install_dir,
        "target_install_dir": project.target_install_dir,
        "en_ref_install_dir": project.en_ref_install_dir,
        "include_infocards": bool(project.include_infocards),
        "source_language": project.source_language,
        "target_language": project.target_language,
        "source_catalog": _catalog_to_dict(project.source_catalog),
        "target_catalog": _catalog_to_dict(project.target_catalog),
        "paired_catalog": _catalog_to_dict(project.paired_catalog),
    }


def _catalog_to_dict(catalog: ResourceCatalog | None) -> dict[str, object] | None:
    return None if catalog is None else catalog.to_dict()


def _catalog_from_dict(payload: object) -> ResourceCatalog | None:
    if not isinstance(payload, dict):
        return None
    units = tuple(_unit_from_dict(item) for item in list(payload.get("units", [])))
    return ResourceCatalog(
        install_dir=Path(str(payload.get("install_dir", ""))),
        freelancer_ini=Path(str(payload.get("freelancer_ini", ""))),
        units=units,
    )


def _unit_from_dict(payload: object) -> TranslationUnit:
    if not isinstance(payload, dict):
        raise ValueError("Invalid unit payload.")
    return TranslationUnit(
        kind=ResourceKind(str(payload.get("kind", "string"))),
        source=_location_from_dict(payload.get("source")),
        source_text=str(payload.get("source_text", "") or ""),
        target=_location_from_dict(payload.get("target")),
        target_text=str(payload.get("target_text", "") or ""),
        manual_text=str(payload.get("manual_text", "") or ""),
        translation_source=str(payload.get("translation_source", "") or ""),
    )


def _location_from_dict(payload: object) -> ResourceLocation | None:
    if payload is None:
        return None
    if not isinstance(payload, dict):
        raise ValueError("Invalid location payload.")
    return ResourceLocation(
        dll_name=str(payload.get("dll_name", "") or ""),
        dll_path=Path(str(payload.get("dll_path", "") or "")),
        local_id=int(payload.get("local_id", 0)),
        slot=int(payload.get("slot", 0)),
        global_id=int(payload.get("global_id", 0)),
    )
