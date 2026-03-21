"""Main window for the FL Lingo desktop application."""

from __future__ import annotations

import os
import queue
import sys
import threading
from pathlib import Path
from typing import Any

from PySide6.QtCore import QSettings, QTimer
from PySide6.QtGui import QAction, QCloseEvent, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QMainWindow,
    QMessageBox,
    QMenu,
)

from .localization import LANGUAGE_OPTIONS
from .catalog import CatalogLoader
from .dll_plans import DllRelocalizationPlan, DllStrategy
from .mod_overrides import ModOverrideEntry
from .models import RelocalizationStatus, ResourceCatalog, TranslationUnit
from .resource_writer import ApplyReport, ResourceWriter
from .stats import summarize_catalog
from .terminology import list_pattern_entries, list_terminology_entries
from .translation_exchange import update_manual_translation
from .ui_builders import UIBuildMixin
from .ui_chrome import UIChromeMixin
from .ui_dialogs import SettingsDialog
from .ui_editor import UIEditorMixin
from .ui_session import UISessionMixin
from .ui_state import UIStateMixin
from .ui_themes import THEMES
from .ui_workflows import UIWorkflowMixin
from .ui_strings import (
    DISCORD_INVITE_URL,
    GITHUB_LATEST_RELEASE_API,
    GITHUB_LATEST_RELEASE_URL,
    GITHUB_REPO_URL,
    STRINGS,
)

class TranslatorMainWindow(UIBuildMixin, UIStateMixin, UIEditorMixin, UISessionMixin, UIWorkflowMixin, UIChromeMixin, QMainWindow):
    def __init__(self, config: Any = None) -> None:
        super().__init__()
        self._config = config or _DefaultConfig()
        self._lang = str(getattr(self._config, "default_language", "de") or "de").lower()
        self._available_languages = set(STRINGS)
        if self._lang not in STRINGS:
            self._lang = "de"
        self._ui_mode = str(getattr(self._config, "default_mode", "simple") or "simple").lower()
        if self._ui_mode not in {"simple", "expert"}:
            self._ui_mode = "simple"
        self._theme = str(getattr(self._config, "default_theme", "light") or "light").lower()
        if self._theme not in THEMES:
            self._theme = "light"
        self._source_lang_code = self._normalize_lang_code(getattr(self._config, "default_source_language", "en"), "en")
        self._target_lang_code = self._normalize_lang_code(getattr(self._config, "default_target_language", "de"), "de")
        self._startup_last_project_path: Path | None = None
        self._settings = self._create_settings()
        self._settings_dialog_class = SettingsDialog
        self._repo_url = GITHUB_REPO_URL
        self._discord_url = DISCORD_INVITE_URL
        self._latest_release_api = GITHUB_LATEST_RELEASE_API
        self._latest_release_url = GITHUB_LATEST_RELEASE_URL
        self._load_persistent_settings()
        self._loader = CatalogLoader()
        self._writer = ResourceWriter()
        self._source_catalog: ResourceCatalog | None = None
        self._target_catalog: ResourceCatalog | None = None
        self._paired_catalog: ResourceCatalog | None = None
        self._dll_plans: list[DllRelocalizationPlan] = []
        self._visible_units: list[TranslationUnit] = []
        self._project_path: Path | None = None
        self._saved_project_signature: str | None = None
        self._apply_thread: threading.Thread | None = None
        self._apply_queue: queue.Queue[dict[str, Any]] = queue.Queue()
        self._apply_poll_timer = QTimer(self)
        self._apply_poll_timer.timeout.connect(self._poll_apply_queue)
        self._search_debounce_timer = QTimer(self)
        self._search_debounce_timer.setSingleShot(True)
        self._search_debounce_timer.timeout.connect(self._refresh_table)
        self._apply_active = False
        self._auto_translate_all = False
        self._apply_report: ApplyReport | None = None
        self._apply_error: str | None = None
        self._audio_progress_cache_key: tuple[str, str] | None = None
        self._audio_progress_cache_value: tuple[int, int, int] = (0, 0, 0)
        self._utf_progress_cache_key: tuple[str, str, str] | None = None
        self._utf_progress_cache_value: tuple[int, int, int, int, int] = (0, 0, 0, 0, 0)
        self._old_text_backup_dir: Path | None = None
        self._old_text_lookup: dict[tuple[str, str, int], str] = {}
        self._mod_override_entries: list[ModOverrideEntry] = []
        self._setup_ui()
        self._apply_editor_default_filters(force=True)
        startup_project = getattr(self._config, "startup_project_path", None)
        if startup_project:
            self._load_project_path(Path(str(startup_project)))
        elif self._startup_last_project_path is not None:
            self._try_restore_last_project(self._startup_last_project_path)

    @staticmethod
    def _create_settings() -> QSettings:
        xdg_config_home = str(os.environ.get("XDG_CONFIG_HOME", "") or "").strip()
        if xdg_config_home:
            settings_dir = Path(xdg_config_home) / "FLAtlas"
            settings_dir.mkdir(parents=True, exist_ok=True)
            return QSettings(str(settings_dir / "FLAtlas-Translator.ini"), QSettings.IniFormat)
        return QSettings("FLAtlas", "FLAtlas-Translator")

    def _resolve_app_icon(self) -> QIcon | None:
        candidates: list[Path] = []
        if getattr(sys, "frozen", False):
            exe_dir = Path(sys.executable).resolve().parent
            candidates.extend(
                [
                    exe_dir / "images" / "FLLingo-JuniIcon-Clean.png",
                    exe_dir / "_internal" / "images" / "FLLingo-JuniIcon-Clean.png",
                    exe_dir / "images" / "FLLingo-JuniIcon-Clean.ico",
                    exe_dir / "_internal" / "images" / "FLLingo-JuniIcon-Clean.ico",
                ]
            )
        project_root = Path(__file__).resolve().parent.parent.parent
        candidates.extend(
            [
                project_root / "images" / "FLLingo-JuniIcon-Clean.png",
                project_root / "images" / "FLLingo-JuniIcon-Clean.ico",
                project_root / "images" / "FLLingo-JuniIcon.png",
                project_root / "images" / "FLLingo-Icon.png",
                project_root / "images" / "FLLingo-Icon.ico",
            ]
        )
        for candidate in candidates:
            if candidate.is_file():
                return QIcon(str(candidate))
        return None

    def _tr(self, key: str) -> str:
        current = STRINGS.get(self._lang, STRINGS["en"])
        return current.get(key, STRINGS["en"].get(key, key))

    def _normalize_lang_code(self, value: Any, fallback: str) -> str:
        normalized = str(value or fallback).strip().lower()
        return normalized or fallback

    def _set_language_combo_value(self, combo: QComboBox, language_code: str) -> None:
        code = self._normalize_lang_code(language_code, "de")
        index = combo.findData(code)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _combo_language_code(self, combo: QComboBox, fallback: str) -> str:
        current = combo.currentData()
        if current is None:
            return self._normalize_lang_code(fallback, fallback)
        return self._normalize_lang_code(current, fallback)

    def _status_text(self, status: RelocalizationStatus) -> str:
        return self._tr(f"status.{status}")

    def _dll_strategy_label(self, strategy: DllStrategy) -> str:
        if strategy == DllStrategy.FULL_REPLACE_SAFE:
            return self._tr("plan.strategy.full")
        if strategy == DllStrategy.PATCH_REQUIRED:
            return self._tr("plan.strategy.patch")
        return self._tr("plan.strategy.unsafe")

    def _populate_status_filter(self) -> None:
        current_data = self.status_combo.currentData()
        self.status_combo.blockSignals(True)
        self.status_combo.clear()
        self.status_combo.addItem(self._tr("kind.all"), None)
        for status in (
            RelocalizationStatus.AUTO_RELOCALIZE,
            RelocalizationStatus.ALREADY_LOCALIZED,
            RelocalizationStatus.MANUAL_TRANSLATION,
            RelocalizationStatus.TERMINOLOGY_TRANSLATION,
            RelocalizationStatus.MOD_ONLY,
        ):
            self.status_combo.addItem(self._status_text(status), str(status))
        index = self.status_combo.findData(current_data)
        self.status_combo.setCurrentIndex(index if index >= 0 else 0)
        self.status_combo.blockSignals(False)

class _DefaultConfig:
    app_title = "FL Lingo"
    app_version = "0.2.1"
    developed_by = "Developed by Aldenmar Odin - flathack"
    default_language = "en"
    default_theme = "light"
    default_source_language = "en"
    default_target_language = "de"


def run(config: Any = None) -> int:
    app = QApplication.instance() or QApplication([])
    window = TranslatorMainWindow(config)
    window.show()
    return app.exec()
