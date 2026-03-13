"""Core translation data models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
import re


class ResourceKind(StrEnum):
    STRING = "string"
    INFOCARD = "infocard"


class RelocalizationStatus(StrEnum):
    AUTO_RELOCALIZE = "auto_relocalize"
    ALREADY_LOCALIZED = "already_localized"
    MOD_ONLY = "mod_only"
    MANUAL_TRANSLATION = "manual_translation"


@dataclass(frozen=True, slots=True)
class ResourceLocation:
    dll_name: str
    dll_path: Path
    local_id: int
    slot: int
    global_id: int


@dataclass(frozen=True, slots=True)
class TranslationUnit:
    kind: ResourceKind
    source: ResourceLocation
    source_text: str
    target: ResourceLocation | None = None
    target_text: str = ""
    manual_text: str = ""

    @property
    def has_target(self) -> bool:
        return self.target is not None and bool(self.target_text)

    @property
    def is_changed(self) -> bool:
        replacement = self.replacement_text
        return bool(replacement) and _normalized_compare_text(self.source_text) != _normalized_compare_text(replacement)

    @property
    def replacement_text(self) -> str:
        return _preserve_source_placeholders(self.source_text, self.manual_text or self.target_text or "")

    @property
    def status(self) -> RelocalizationStatus:
        if self.manual_text:
            return RelocalizationStatus.MANUAL_TRANSLATION
        if not self.has_target:
            return RelocalizationStatus.MOD_ONLY
        if _normalized_compare_text(self.source_text) == _normalized_compare_text(self.target_text):
            return RelocalizationStatus.ALREADY_LOCALIZED
        return RelocalizationStatus.AUTO_RELOCALIZE

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": str(self.kind),
            "source": _location_to_dict(self.source),
            "source_text": self.source_text,
            "target": _location_to_dict(self.target),
            "target_text": self.target_text,
            "manual_text": self.manual_text,
            "has_target": self.has_target,
            "is_changed": self.is_changed,
            "status": str(self.status),
        }


@dataclass(frozen=True, slots=True)
class ResourceCatalog:
    install_dir: Path
    freelancer_ini: Path
    units: tuple[TranslationUnit, ...]

    def by_kind(self, kind: ResourceKind) -> list[TranslationUnit]:
        return [unit for unit in self.units if unit.kind == kind]

    def by_dll(self, dll_name: str) -> list[TranslationUnit]:
        name = str(dll_name).lower()
        return [unit for unit in self.units if unit.source.dll_name.lower() == name]

    def by_status(self, status: RelocalizationStatus) -> list[TranslationUnit]:
        return [unit for unit in self.units if unit.status == status]

    def to_dict(self) -> dict[str, object]:
        return {
            "install_dir": self.install_dir.as_posix(),
            "freelancer_ini": self.freelancer_ini.as_posix(),
            "units": [unit.to_dict() for unit in self.units],
        }


def make_global_id(slot: int, local_id: int) -> int:
    return ((int(slot) & 0xFFFF) << 16) | (int(local_id) & 0xFFFF)


def _location_to_dict(location: ResourceLocation | None) -> dict[str, object] | None:
    if location is None:
        return None
    return {
        "dll_name": location.dll_name,
        "dll_path": location.dll_path.as_posix(),
        "local_id": location.local_id,
        "slot": location.slot,
        "global_id": location.global_id,
    }


def _normalized_compare_text(text: str) -> str:
    return str(text or "").replace("\r\n", "\n").replace("\r", "\n")


_PLACEHOLDER_PATTERN = re.compile(r"%[A-Za-z0-9]+")


def _preserve_source_placeholders(source_text: str, replacement_text: str) -> str:
    replacement = str(replacement_text or "")
    if not replacement:
        return ""

    source_tokens = _PLACEHOLDER_PATTERN.findall(str(source_text or ""))
    replacement_tokens = _PLACEHOLDER_PATTERN.findall(replacement)
    if not source_tokens or not replacement_tokens:
        return replacement
    if len(source_tokens) != len(replacement_tokens):
        return replacement
    if [_placeholder_shape(token) for token in source_tokens] != [_placeholder_shape(token) for token in replacement_tokens]:
        return replacement

    token_iter = iter(source_tokens)
    return _PLACEHOLDER_PATTERN.sub(lambda _match: next(token_iter), replacement)


def _placeholder_shape(token: str) -> str:
    return re.sub(r"\d+", "#", str(token or "").lower())
