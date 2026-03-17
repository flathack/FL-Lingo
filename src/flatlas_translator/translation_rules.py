"""Configurable translation rules that control which strings are skipped."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtCore import QSettings


@dataclass
class TranslationRules:
    """All user-configurable translation skip/filter rules."""

    # --- skip rules (checkboxes) ---
    skip_location_keywords: bool = True
    skip_person_names: bool = True
    skip_symbolic_numeric: bool = True
    skip_ship_names: bool = True

    # --- term rules ---
    skip_single_word_terms_in_prose: bool = True
    term_candidate_max_length: int = 80
    pattern_min_source_length: int = 20

    # --- cached ship name global IDs ---
    _ship_name_ids: set[int] = field(default_factory=set, repr=False, compare=False)

    # ---- persistence ---------------------------------------------------------

    _SETTINGS_PREFIX = "rules/"

    _BOOL_KEYS = (
        "skip_location_keywords",
        "skip_person_names",
        "skip_symbolic_numeric",
        "skip_ship_names",
        "skip_single_word_terms_in_prose",
    )
    _INT_KEYS = (
        ("term_candidate_max_length", 1, 9999),
        ("pattern_min_source_length", 0, 9999),
    )

    def save(self, settings: QSettings) -> None:
        for key in self._BOOL_KEYS:
            settings.setValue(self._SETTINGS_PREFIX + key, getattr(self, key))
        for key, _lo, _hi in self._INT_KEYS:
            settings.setValue(self._SETTINGS_PREFIX + key, getattr(self, key))

    @classmethod
    def load(cls, settings: QSettings) -> TranslationRules:
        rules = cls()
        for key in cls._BOOL_KEYS:
            val = settings.value(cls._SETTINGS_PREFIX + key)
            if val is not None:
                setattr(rules, key, str(val).lower() in ("true", "1", "yes"))
        for key, lo, hi in cls._INT_KEYS:
            val = settings.value(cls._SETTINGS_PREFIX + key)
            if val is not None:
                try:
                    setattr(rules, key, max(lo, min(hi, int(val))))
                except (ValueError, TypeError):
                    pass
        return rules

    # ---- ship name helpers ---------------------------------------------------

    def load_ship_name_ids(self, install_dir: Path | None) -> None:
        """Parse shiparch.ini under *install_dir* and populate _ship_name_ids."""
        self._ship_name_ids = set()
        if install_dir is None:
            return
        candidates = [
            install_dir / "DATA" / "SHIPS" / "shiparch.ini",
            install_dir / "data" / "ships" / "shiparch.ini",
        ]
        ini_path: Path | None = None
        for c in candidates:
            if c.is_file():
                ini_path = c
                break
        if ini_path is None:
            return
        try:
            text = ini_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return
        for raw_line in text.splitlines():
            line = raw_line.split(";", 1)[0].strip()
            if not line or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip().lower() != "ids_name":
                continue
            try:
                self._ship_name_ids.add(int(value.strip()))
            except ValueError:
                continue

    def is_ship_name_id(self, global_id: int) -> bool:
        return global_id in self._ship_name_ids


# Module-level default instance (replaced at runtime via load)
_active_rules = TranslationRules()


def get_active_rules() -> TranslationRules:
    return _active_rules


def set_active_rules(rules: TranslationRules) -> None:
    global _active_rules
    _active_rules = rules
