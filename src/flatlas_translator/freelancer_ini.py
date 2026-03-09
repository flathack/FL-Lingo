"""Helpers to locate and parse Freelancer resource DLL entries."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .path_utils import ci_resolve


RESOURCE_SECTION = "resources"
IGNORED_DLLS = {"resources_vanilla.dll"}
SUPPLEMENTAL_UI_DLLS = ("resources.dll",)


@dataclass(frozen=True, slots=True)
class ResourceDll:
    ini_path: Path
    dll_name: str
    dll_path: Path


def find_freelancer_ini(install_dir: Path) -> Path:
    candidates = [
        install_dir / "EXE" / "freelancer.ini",
        install_dir / "exe" / "freelancer.ini",
        install_dir / "Freelancer.ini",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"Could not find freelancer.ini under {install_dir}")


def parse_resource_dll_names(freelancer_ini: Path) -> list[str]:
    text = freelancer_ini.read_text(encoding="utf-8", errors="ignore")
    current_section = ""
    dll_names: list[str] = []
    seen: set[str] = set()

    for raw_line in text.splitlines():
        line = raw_line.split(";", 1)[0].strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            current_section = line[1:-1].strip().lower()
            continue
        if current_section != RESOURCE_SECTION:
            continue
        if "=" not in line:
            continue
        key, value = [part.strip() for part in line.split("=", 1)]
        if key.lower() != "dll":
            continue
        dll_name = value.split(",", 1)[0].strip().strip("\"'")
        if not dll_name:
            continue
        normalized = dll_name.replace("\\", "/").lower()
        if normalized in IGNORED_DLLS or normalized in seen:
            continue
        seen.add(normalized)
        dll_names.append(dll_name)

    return dll_names


def resolve_dll_path(freelancer_ini: Path, dll_name: str) -> Path | None:
    clean_name = str(dll_name or "").strip().strip("\"'")
    if not clean_name:
        return None

    ini_dir = freelancer_ini.parent
    base_roots = [ini_dir, ini_dir.parent, ini_dir.parent.parent]
    normalized = clean_name.replace("\\", "/")

    for base in base_roots:
        if not base or not base.exists():
            continue
        candidate = ci_resolve(base, normalized)
        if candidate and candidate.is_file():
            return candidate

    direct = Path(normalized)
    if direct.is_file():
        return direct
    return None


def load_resource_dlls(install_dir: Path) -> tuple[Path, list[ResourceDll]]:
    freelancer_ini = find_freelancer_ini(install_dir)
    resources: list[ResourceDll] = []
    seen: set[str] = set()

    for dll_name in parse_resource_dll_names(freelancer_ini):
        dll_path = resolve_dll_path(freelancer_ini, dll_name)
        if dll_path is None:
            continue
        seen.add(dll_path.name.lower())
        resources.append(ResourceDll(ini_path=freelancer_ini, dll_name=dll_name, dll_path=dll_path))

    exe_dir = freelancer_ini.parent
    for dll_name in SUPPLEMENTAL_UI_DLLS:
        if dll_name.lower() in seen:
            continue
        dll_path = ci_resolve(exe_dir, dll_name)
        if dll_path is None or not dll_path.is_file():
            continue
        resources.append(ResourceDll(ini_path=freelancer_ini, dll_name=dll_name, dll_path=dll_path))
        seen.add(dll_name.lower())

    return freelancer_ini, resources
