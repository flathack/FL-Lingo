"""Session, catalog, and apply controller mixin for FL Lingo main window."""

from __future__ import annotations

import queue
import threading
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QApplication, QFileDialog, QLineEdit, QMessageBox, QTableWidgetItem

from .catalog import pair_catalogs
from .dll_resources import DllHtmlResourceReader, DllStringTableReader
from .dll_plans import build_dll_plans
from .mod_overrides import apply_mod_overrides, list_mod_overrides
from .models import RelocalizationStatus, ResourceCatalog, ResourceKind, TranslationUnit
from .project_io import TranslatorProject, project_signature
from .stats import calculate_translation_progress
from .terminology import apply_known_term_suggestions, is_unit_skippable
from .ui_themes import THEMES


class UISessionMixin:
    def _translate_all(self) -> None:
        """Run text translation, then auto-copy audio and auto-merge UTF."""
        self._auto_translate_all = True
        self._apply_target_to_install()

    def _remove_imported_translations(self) -> None:
        """Remove all manually imported translations from the current catalog."""
        catalog = self._paired_catalog or self._source_catalog
        if catalog is None:
            return
        manual_count = sum(1 for u in catalog.units if u.manual_text)
        if manual_count == 0:
            return
        reply = QMessageBox.question(
            self,
            self._tr("dialog.remove_imports_title"),
            self._tr("dialog.remove_imports_confirm").format(count=manual_count),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        cleared_units = tuple(
            TranslationUnit(
                kind=u.kind,
                source=u.source,
                source_text=u.source_text,
                target=u.target,
                target_text=u.target_text,
                manual_text="",
            )
            for u in catalog.units
        )
        cleared = ResourceCatalog(
            install_dir=catalog.install_dir,
            freelancer_ini=catalog.freelancer_ini,
            units=cleared_units,
        )
        if self._paired_catalog is not None:
            self._paired_catalog = cleared
        else:
            self._source_catalog = cleared
        self._refresh_table()
        self._update_action_state()
        self._set_status(self._tr("status.imports_removed").format(count=manual_count))

    def _refresh_mod_override_entries(self) -> None:
        install_dir = self._backup_host_install_dir()
        if install_dir is None or not install_dir.exists():
            self._mod_override_entries = []
        else:
            self._mod_override_entries = list_mod_overrides(install_dir)
        if hasattr(self, "mod_overrides_table"):
            self._refresh_mod_overrides_table()

    def _refresh_after_mod_override_change(self) -> None:
        selected_unit = self._selected_unit()
        selected_key = self._unit_key(selected_unit) if selected_unit is not None else None
        previous_override_keys = {entry.key() for entry in self._mod_override_entries}
        self._refresh_mod_override_entries()
        current_override_keys = {entry.key() for entry in self._mod_override_entries}
        override_reset_keys = previous_override_keys | current_override_keys
        if self._source_catalog is not None:
            self._source_catalog = self._catalog_with_mod_overrides_reapplied(
                self._source_catalog,
                override_reset_keys=override_reset_keys,
            )
        if self._paired_catalog is not None:
            self._paired_catalog = self._catalog_with_mod_overrides_reapplied(
                self._paired_catalog,
                override_reset_keys=override_reset_keys,
            )
        if (
            self._source_catalog is not None
            and self._paired_catalog is not None
            and self._target_catalog is not None
        ):
            self._dll_plans = build_dll_plans(self._source_catalog, self._paired_catalog, self._target_catalog)
        self._refresh_dll_plan_table()
        self._refresh_table()
        if selected_key is not None:
            self._select_unit_by_key(selected_key)
        self._update_action_state()

    def _catalog_with_selected_old_text_overrides(self, catalog: ResourceCatalog) -> ResourceCatalog:
        return apply_mod_overrides(catalog, original_text_lookup=self._old_text_lookup)

    def _catalog_with_mod_overrides_reapplied(
        self,
        catalog: ResourceCatalog,
        *,
        override_reset_keys: set[tuple[str, str, int]],
    ) -> ResourceCatalog:
        base_units: list[TranslationUnit] = []
        for unit in catalog.units:
            unit_key = (str(unit.kind), unit.source.dll_name.lower(), int(unit.source.local_id))
            base_units.append(
                TranslationUnit(
                    kind=unit.kind,
                    source=unit.source,
                    source_text=unit.source_text,
                    target=unit.target,
                    target_text=unit.target_text,
                    manual_text="" if unit_key in override_reset_keys else unit.manual_text,
                )
            )
        base_catalog = ResourceCatalog(
            install_dir=catalog.install_dir,
            freelancer_ini=catalog.freelancer_ini,
            units=tuple(base_units),
        )
        return apply_mod_overrides(base_catalog)

    def _backup_host_install_dir(self) -> Path | None:
        if self._source_catalog is not None:
            return self._source_catalog.install_dir
        source_text = self.source_edit.text().strip()
        return Path(source_text) if source_text else None

    def _refresh_old_text_backup_options(self) -> None:
        if not hasattr(self, "old_text_backup_combo"):
            return
        install_dir = self._backup_host_install_dir()
        backups = self._writer.list_backups(install_dir) if install_dir is not None and install_dir.exists() else []
        current_data = self.old_text_backup_combo.currentData()
        self.old_text_backup_combo.blockSignals(True)
        self.old_text_backup_combo.clear()
        self.old_text_backup_combo.addItem(self._tr("editor.old_text_current"), "")
        for backup_dir in backups:
            self.old_text_backup_combo.addItem(backup_dir.name, str(backup_dir))
        index = self.old_text_backup_combo.findData(current_data)
        self.old_text_backup_combo.setCurrentIndex(index if index >= 0 else 0)
        self.old_text_backup_combo.setEnabled(self._current_catalog() is not None)
        self.old_text_backup_combo.blockSignals(False)
        self._load_old_text_backup_lookup()

    def _handle_old_text_backup_changed(self) -> None:
        self._load_old_text_backup_lookup()
        self._refresh_table()

    def _load_old_text_backup_lookup(self) -> None:
        if not hasattr(self, "old_text_backup_combo"):
            return
        selected = str(self.old_text_backup_combo.currentData() or "").strip()
        self._old_text_backup_dir = Path(selected) if selected else None
        catalog = self._current_catalog()
        if catalog is None or self._old_text_backup_dir is None:
            self._old_text_lookup = {}
            return
        self._old_text_lookup = self._build_old_text_lookup(
            catalog,
            self._old_text_backup_dir,
            string_reader=DllStringTableReader(),
            html_reader=DllHtmlResourceReader(),
        )

    @staticmethod
    def _build_old_text_lookup(
        catalog: ResourceCatalog,
        backup_dir: Path,
        *,
        string_reader: DllStringTableReader,
        html_reader: DllHtmlResourceReader,
    ) -> dict[tuple[str, str, int], str]:
        lookup: dict[tuple[str, str, int], str] = {}
        requested: dict[str, set[tuple[str, int]]] = {}
        for unit in catalog.units:
            requested.setdefault(unit.source.dll_name.lower(), set()).add((str(unit.kind), int(unit.source.local_id)))

        for dll_name, keys in requested.items():
            backup_path = Path(backup_dir) / Path(dll_name).name
            if not backup_path.is_file():
                continue
            string_map = string_reader.read_strings(backup_path)
            info_map = html_reader.read_html_resources(backup_path)
            for kind, local_id in keys:
                if kind == str(ResourceKind.STRING):
                    text = string_map.get(local_id)
                else:
                    text = info_map.get(local_id)
                if text:
                    lookup[(kind, dll_name, local_id)] = text
        return lookup

    def _apply_editor_default_filters(self, *, force: bool = False) -> None:
        desired_status = str(RelocalizationStatus.MOD_ONLY)
        current_status = self.status_combo.currentData()
        if (not force) and current_status not in (None, desired_status):
            return
        self.status_combo.blockSignals(True)
        self.target_only_check.blockSignals(True)
        self.changed_only_check.blockSignals(True)
        status_index = self.status_combo.findData(desired_status)
        if status_index >= 0:
            self.status_combo.setCurrentIndex(status_index)
        self.target_only_check.setChecked(False)
        self.changed_only_check.setChecked(False)
        self.status_combo.blockSignals(False)
        self.target_only_check.blockSignals(False)
        self.changed_only_check.blockSignals(False)

    def _missing_translation_count(self) -> int:
        catalog = self._current_catalog()
        if catalog is None:
            return 0
        return sum(
            1
            for unit in catalog.units
            if unit.status == RelocalizationStatus.MOD_ONLY
            and not str(unit.manual_text or "").strip()
            and not is_unit_skippable(unit)
        )

    def _refresh_editor_status(self) -> None:
        if not hasattr(self, "editor_missing_label"):
            return
        count = self._missing_translation_count()
        self.editor_help_label.setText(self._tr("editor.help"))
        self.editor_missing_label.setText(self._tr("editor.missing").format(count=count))
        self.editor_missing_detail_label.setText(self._tr("editor.missing_detail").format(count=count))

    def _apply_candidate_units(self) -> list[TranslationUnit]:
        catalog = self._paired_catalog
        if catalog is None:
            return []
        return [
            unit
            for unit in catalog.units
            if unit.status in {RelocalizationStatus.AUTO_RELOCALIZE, RelocalizationStatus.MANUAL_TRANSLATION}
        ]

    def _set_apply_buttons_enabled(self, enabled: bool) -> None:
        for name in ("translate_all_button", "apply_button", "simple_translate_button"):
            button = getattr(self, name, None)
            if button is not None:
                button.setEnabled(enabled)

    def _refresh_apply_resume_status(self) -> None:
        if not hasattr(self, "apply_execution_status_label") or self._apply_active:
            return
        catalog = self._paired_catalog
        units = self._apply_candidate_units()
        session = self._writer.load_apply_session(catalog, units=units) if catalog is not None and units else None
        if session is not None and session.pending_dlls:
            self.apply_execution_status_label.setText(
                self._tr("apply.run.resume_available").format(
                    done=len(session.completed_dlls),
                    total=session.total_dlls,
                )
            )
            next_dll = session.pending_dlls[0]
            action = self._tr("apply.run.patch")
            self.apply_execution_current_label.setText(
                self._tr("apply.run.current_dll").format(dll=next_dll, action=action)
            )
            percent = int((len(session.completed_dlls) / max(1, session.total_dlls)) * 100)
            self.apply_execution_progress_bar.setValue(percent)
            if session.last_error:
                self.apply_execution_lines.setPlainText(session.last_error)
            else:
                self.apply_execution_lines.setPlainText("")
        else:
            self.apply_execution_status_label.setText(self._tr("apply.run.idle"))
            self.apply_execution_current_label.setText(self._tr("apply.run.none"))
            self.apply_execution_progress_bar.setValue(0)
            self.apply_execution_lines.setPlainText("")

    def _start_apply_worker(self, catalog: ResourceCatalog, units: list[TranslationUnit]) -> None:
        session = self._writer.load_apply_session(catalog, units=units)
        total_dlls = max(1, len({unit.source.dll_name.lower() for unit in units}))
        completed_dlls = len(session.completed_dlls) if session is not None else 0
        self._apply_active = True
        self._apply_report = None
        self._apply_error = None
        self._set_apply_buttons_enabled(False)
        self.apply_execution_progress_bar.setValue(int((completed_dlls / total_dlls) * 100))
        self.apply_execution_status_label.setText(self._tr("apply.run.running").format(done=completed_dlls, total=total_dlls))
        self.apply_execution_current_label.setText(self._tr("apply.run.none"))
        self.apply_execution_lines.setPlainText("")
        while not self._apply_queue.empty():
            try:
                self._apply_queue.get_nowait()
            except queue.Empty:
                break

        def _worker() -> None:
            try:
                report = self._writer.apply_german_relocalization(
                    catalog,
                    units=units,
                    dll_plans=self._dll_plans,
                    progress_callback=lambda event: self._apply_queue.put({"type": "progress", "event": event}),
                )
                self._apply_queue.put({"type": "success", "report": report})
            except Exception as exc:
                self._apply_queue.put({"type": "error", "error": str(exc)})
            finally:
                self._apply_queue.put({"type": "finished"})

        self._apply_thread = threading.Thread(target=_worker, daemon=True)
        self._apply_thread.start()
        self._apply_poll_timer.start(100)

    def _poll_apply_queue(self) -> None:
        saw_finished = False
        while True:
            try:
                payload = self._apply_queue.get_nowait()
            except queue.Empty:
                break
            kind = str(payload.get("type", "") or "")
            if kind == "progress":
                self._handle_apply_progress_event(payload.get("event", {}))
            elif kind == "success":
                self._apply_report = payload.get("report")
            elif kind == "error":
                self._apply_error = str(payload.get("error", "") or "")
            elif kind == "finished":
                saw_finished = True

        if not saw_finished:
            return

        if self._apply_thread is not None:
            self._apply_thread.join(timeout=0.1)
        self._apply_poll_timer.stop()
        self._apply_active = False
        self._apply_thread = None
        self._set_apply_buttons_enabled(True)

        if self._apply_error:
            failed_dll = "?"
            catalog = self._paired_catalog
            units = self._apply_candidate_units()
            session = self._writer.load_apply_session(catalog, units=units) if catalog is not None and units else None
            if session is not None and session.failed_dll:
                failed_dll = session.failed_dll
            self.apply_execution_status_label.setText(self._tr("apply.run.failed").format(dll=failed_dll))
            self._show_error(self._tr("error.apply_failed").format(error=self._apply_error))
            self._refresh_apply_resume_status()
            return

        report = self._apply_report
        if report is None:
            self._refresh_apply_resume_status()
            return
        total_dlls = max(1, len({unit.source.dll_name.lower() for unit in self._apply_candidate_units()}))
        self.apply_execution_status_label.setText(
            self._tr("apply.run.completed").format(done=total_dlls, total=total_dlls)
        )
        self.apply_execution_progress_bar.setValue(100)
        QMessageBox.information(
            self,
            self._tr("dialog.apply_title"),
            self._tr("dialog.apply_success").format(
                count=report.replaced_units,
                dlls=len(report.written_files),
                backup=report.backup_dir,
            ),
        )
        if self._lang == "en":
            self._set_status(f"Applied {self._target_lang_code}: {report.replaced_units} entries, backup at {report.backup_dir}")
        else:
            self._set_status(f"{self._target_lang_code} angewendet: {report.replaced_units} Einträge, Backup unter {report.backup_dir}")
        resolved = self._resolve_source_and_reference_installs()
        if resolved is not None:
            source_install, reference_install = resolved
            audio_candidates = self._writer.list_audio_copy_candidates(source_install, reference_install)
            if audio_candidates:
                auto_copy_audio = (
                    getattr(self, "_auto_translate_all", False)
                    or (
                        hasattr(self, "simple_audio_copy_check")
                        and self._ui_mode == "simple"
                        and self.simple_audio_copy_check.isChecked()
                    )
                )
                if auto_copy_audio:
                    self._copy_reference_audio_candidates(
                        source_install,
                        reference_install,
                        audio_candidates,
                        backup_dir=report.backup_dir,
                    )
                else:
                    reply = QMessageBox.question(
                        self,
                        self._tr("dialog.copy_audio_title"),
                        self._tr("dialog.copy_audio_offer").format(
                            count=len(audio_candidates),
                            backup=report.backup_dir,
                        ),
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes,
                    )
                    if reply == QMessageBox.Yes:
                        self._copy_reference_audio_candidates(
                            source_install,
                            reference_install,
                            audio_candidates,
                            backup_dir=report.backup_dir,
                        )

            # Auto-merge UTF voice lines when EN vanilla path is available
            en_ref_path = ""
            if hasattr(self, "simple_en_ref_edit"):
                en_ref_path = self.simple_en_ref_edit.text().strip()
            if not en_ref_path and hasattr(self, "en_ref_edit"):
                en_ref_path = self.en_ref_edit.text().strip()
            if en_ref_path:
                reference_en = Path(en_ref_path)
                if reference_en.exists():
                    try:
                        utf_candidates = self._writer.list_utf_audio_merge_candidates(
                            source_install, reference_en, reference_install,
                        )
                        if utf_candidates:
                            auto_merge = (
                                getattr(self, "_auto_translate_all", False)
                                or (
                                    hasattr(self, "simple_audio_copy_check")
                                    and self._ui_mode == "simple"
                                    and self.simple_audio_copy_check.isChecked()
                                )
                            )
                            if auto_merge:
                                utf_report = self._run_with_progress(
                                    self._tr("dialog.merge_utf_audio_title"),
                                    self._tr("progress.merge_utf_audio"),
                                    lambda: self._writer.merge_utf_audio(
                                        source_install, reference_en, reference_install,
                                        candidates=utf_candidates,
                                        backup_dir=report.backup_dir,
                                    ),
                                )
                                self._set_status(self._tr("status.utf_merge_done").format(
                                    replaced=utf_report.total_replaced,
                                    files=len(utf_report.merged_files),
                                ))
                            else:
                                total_replaceable = sum(c.replaceable_count for c in utf_candidates)
                                reply = QMessageBox.question(
                                    self,
                                    self._tr("dialog.merge_utf_audio_title"),
                                    self._tr("dialog.merge_utf_audio_offer").format(
                                        count=len(utf_candidates),
                                        replaceable=total_replaceable,
                                        backup=report.backup_dir,
                                    ),
                                    QMessageBox.Yes | QMessageBox.No,
                                    QMessageBox.Yes,
                                )
                                if reply == QMessageBox.Yes:
                                    utf_report = self._run_with_progress(
                                        self._tr("dialog.merge_utf_audio_title"),
                                        self._tr("progress.merge_utf_audio"),
                                        lambda: self._writer.merge_utf_audio(
                                            source_install, reference_en, reference_install,
                                            candidates=utf_candidates,
                                            backup_dir=report.backup_dir,
                                        ),
                                    )
                                    self._set_status(self._tr("status.utf_merge_done").format(
                                        replaced=utf_report.total_replaced,
                                        files=len(utf_report.merged_files),
                                    ))
                    except Exception:
                        pass
        self._auto_translate_all = False
        self._load_source_catalog()
        self._load_compare_catalog()

    def _handle_apply_progress_event(self, event: Any) -> None:
        if not isinstance(event, dict):
            return
        total = max(1, int(event.get("total", 1) or 1))
        completed = max(0, int(event.get("completed", 0) or 0))
        phase = str(event.get("phase", "") or "")
        dll_name = str(event.get("dll_name", "") or "")
        action_key = "apply.run.copy" if str(event.get("action", "") or "") == "copy" else "apply.run.patch"
        display_done = completed if phase == "done" else min(total, completed + 1)
        percent = int((display_done / total) * 100)
        self.apply_execution_progress_bar.setValue(percent)
        self.apply_execution_status_label.setText(
            self._tr("apply.run.running").format(done=display_done, total=total)
        )
        self.apply_execution_current_label.setText(
            self._tr("apply.run.current_dll").format(dll=dll_name, action=self._tr(action_key))
        )
        preview_lines = list(event.get("preview_lines", []) or [])
        if preview_lines:
            self.apply_execution_lines.setPlainText(
                self._tr("apply.run.current_lines").format(lines="\n".join(preview_lines))
            )
        else:
            self.apply_execution_lines.setPlainText("")

    def _load_persistent_settings(self) -> None:
        saved_language = str(self._settings.value("ui/language", self._lang) or self._lang).lower()
        saved_mode = str(self._settings.value("ui/mode", self._ui_mode) or self._ui_mode).lower()
        saved_theme = str(self._settings.value("ui/theme", self._theme) or self._theme).lower()
        saved_source_language = self._normalize_lang_code(
            self._settings.value("translation/source_language", self._source_lang_code),
            self._source_lang_code,
        )
        saved_target_language = self._normalize_lang_code(
            self._settings.value("translation/target_language", self._target_lang_code),
            self._target_lang_code,
        )
        saved_project_path = str(self._settings.value("project/last_path", "") or "").strip()
        if saved_language in self._available_languages:
            self._lang = saved_language
        if saved_mode in {"simple", "expert"}:
            self._ui_mode = saved_mode
        if saved_theme in THEMES:
            self._theme = saved_theme
        self._source_lang_code = saved_source_language
        self._target_lang_code = saved_target_language
        self._startup_last_project_path = Path(saved_project_path) if saved_project_path else None
        self._translator_api_key = str(self._settings.value("translator/api_key", "") or "").strip()
        self._translator_provider = str(self._settings.value("translator/provider", "google") or "google").strip()

    def _save_persistent_settings(self) -> None:
        self._settings.setValue("ui/language", self._lang)
        self._settings.setValue("ui/mode", self._ui_mode)
        self._settings.setValue("ui/theme", self._theme)
        self._settings.setValue("translation/source_language", self._source_lang_code)
        self._settings.setValue("translation/target_language", self._target_lang_code)
        self._settings.setValue("project/last_path", str(self._project_path) if self._project_path is not None else "")

    def _apply_theme(self) -> None:
        app = QApplication.instance()
        if app is None:
            return
        app.setStyleSheet(THEMES.get(self._theme, THEMES["light"]))

    def _pick_directory(self, line_edit: QLineEdit) -> None:
        start_dir = line_edit.text().strip() or str(Path.home())
        directory = QFileDialog.getExistingDirectory(self, self._tr("group.installs"), start_dir)
        if directory:
            line_edit.setText(directory)

    def _mirror_line_edit_text(self, attribute_name: str, value: str) -> None:
        widget = getattr(self, attribute_name, None)
        if widget is None or not isinstance(widget, QLineEdit):
            return
        if widget.text() == value:
            return
        widget.blockSignals(True)
        widget.setText(value)
        widget.blockSignals(False)

    def _load_source_catalog(self) -> None:
        source_dir = Path(self.source_edit.text().strip())
        if not source_dir.exists():
            self._show_error(self._tr("error.source_missing").format(path=source_dir))
            return
        self._store_language_pair()
        try:
            self._run_with_progress(
                self._tr("dialog.progress_title"),
                self._tr("progress.load_source"),
                lambda: self._with_busy_cursor(
                    lambda: setattr(
                        self,
                        "_source_catalog",
                        apply_mod_overrides(
                            self._loader.load_catalog(
                                source_dir,
                                include_infocards=self.include_infocards_check.isChecked(),
                            )
                        ),
                    )
                ),
            )
        except Exception as exc:
            self._show_error(self._tr("error.load_source_failed").format(error=exc))
            return

        self._paired_catalog = None
        self._target_catalog = None
        self._dll_plans = []
        self._saved_project_signature = None
        self._old_text_lookup = {}
        self._invalidate_audio_progress_cache()
        self._apply_editor_default_filters(force=True)
        self._refresh_mod_override_entries()
        self._refresh_old_text_backup_options()
        self._refresh_dll_plan_table()
        self._populate_dll_filter(self._source_catalog)
        self._refresh_table()
        self._update_action_state()
        self._set_status(self._tr("status.loaded_source").format(path=source_dir))

    def _load_compare_catalog(self) -> None:
        if self._source_catalog is None:
            self._load_source_catalog()
            if self._source_catalog is None:
                return

        target_dir = Path(self.target_edit.text().strip())
        if not target_dir.exists():
            self._show_error(self._tr("error.target_missing").format(path=target_dir))
            return
        self._store_language_pair()
        try:
            target_catalog: ResourceCatalog | None = None

            def _load() -> None:
                nonlocal target_catalog
                target_catalog = self._loader.load_catalog(
                    target_dir,
                    include_infocards=self.include_infocards_check.isChecked(),
                )

            self._run_with_progress(
                self._tr("dialog.progress_title"),
                self._tr("progress.compare"),
                lambda: self._with_busy_cursor(_load),
            )
            assert target_catalog is not None
            self._target_catalog = target_catalog
            self._paired_catalog = apply_mod_overrides(
                apply_known_term_suggestions(
                    pair_catalogs(self._source_catalog, target_catalog),
                    target_language=self._target_lang_code,
                )
            )
            self._dll_plans = build_dll_plans(self._source_catalog, self._paired_catalog, target_catalog)
        except Exception as exc:
            self._show_error(self._tr("error.compare_failed").format(error=exc))
            return

        self._invalidate_audio_progress_cache()
        self._apply_editor_default_filters(force=True)
        self._refresh_mod_override_entries()
        self._refresh_old_text_backup_options()
        self._refresh_dll_plan_table()
        self._populate_dll_filter(self._paired_catalog)
        self._refresh_table()
        self._saved_project_signature = None
        self._update_action_state()
        self._set_status(self._tr("status.loaded_compare").format(path=target_dir))

    def _current_catalog(self) -> ResourceCatalog | None:
        return self._paired_catalog or self._source_catalog

    def _selected_unit(self) -> TranslationUnit | None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._visible_units):
            return None
        return self._visible_units[row]

    def _unit_key(self, unit: TranslationUnit) -> tuple[str, str, int]:
        return (str(unit.kind), unit.source.dll_name.lower(), int(unit.source.local_id))

    def _replace_current_catalog(self, catalog: ResourceCatalog) -> None:
        if self._paired_catalog is not None:
            self._paired_catalog = catalog
        else:
            self._source_catalog = catalog
        self._update_action_state()

    def _select_unit_by_key(self, key: tuple[str, str, int]) -> None:
        for row, unit in enumerate(self._visible_units):
            if self._unit_key(unit) == key:
                self.table.selectRow(row)
                return

    def _current_project(self) -> TranslatorProject:
        return TranslatorProject(
            source_install_dir=self.source_edit.text().strip(),
            target_install_dir=self.target_edit.text().strip(),
            include_infocards=self.include_infocards_check.isChecked(),
            source_language=self._source_lang_code,
            target_language=self._target_lang_code,
            source_catalog=self._source_catalog,
            target_catalog=self._target_catalog,
            paired_catalog=self._paired_catalog,
            dll_plans=tuple(self._dll_plans),
        )

    def _reset_session_state(self) -> None:
        self._project_path = None
        self._saved_project_signature = None
        self._source_catalog = None
        self._target_catalog = None
        self._paired_catalog = None
        self._dll_plans = []
        self._visible_units = []
        self._old_text_backup_dir = None
        self._old_text_lookup = {}
        self._mod_override_entries = []
        self.include_infocards_check.setChecked(True)
        self._invalidate_audio_progress_cache()
        self._apply_editor_default_filters(force=True)
        self._refresh_mod_override_entries()
        self._refresh_old_text_backup_options()
        self._populate_dll_filter(None)
        self._refresh_dll_plan_table()
        self._refresh_table()
        self._refresh_footer()
        self._save_persistent_settings()
        self._update_action_state()

    def _manual_entry_count(self) -> int:
        catalog = self._current_catalog()
        if catalog is None:
            return 0
        return sum(1 for unit in catalog.units if unit.status == RelocalizationStatus.MANUAL_TRANSLATION)

    def _translation_progress(self) -> tuple[int, int, int, int, int, int]:
        catalog = self._current_catalog()
        if catalog is None:
            return (0, 0, 0, 0, 0, 0)
        progress = calculate_translation_progress(catalog)
        return (
            progress.localized,
            progress.done,
            progress.skipped,
            progress.total,
            progress.done_percent,
            progress.covered_percent,
        )

    def _current_project_signature(self) -> str | None:
        if self._current_catalog() is None:
            return None
        return project_signature(self._current_project())

    def _is_project_dirty(self) -> bool:
        current_signature = self._current_project_signature()
        if current_signature is None:
            return False
        if self._saved_project_signature is None:
            return True
        return current_signature != self._saved_project_signature

    def _refresh_table(self) -> None:
        catalog = self._current_catalog()
        if catalog is None:
            self.table.setRowCount(0)
            self.summary_label.setText(self._tr("summary.none"))
            self._refresh_dll_plan_table()
            self.source_preview.clear()
            self.target_preview.clear()
            self.detail_label.setText(self._tr("detail.none"))
            self._refresh_project_status()
            self._refresh_progress()
            self._refresh_editor_status()
            self._refresh_apply_resume_status()
            self._refresh_simple_mode()
            return

        units = list(catalog.units)
        if self.kind_combo.currentText() != self._tr("kind.all"):
            units = [unit for unit in units if unit.kind == ResourceKind(self.kind_combo.currentText())]
        if self.dll_combo.currentText() != self._tr("kind.all"):
            units = [unit for unit in units if unit.source.dll_name == self.dll_combo.currentText()]
        if self.status_combo.currentData() is not None:
            units = [unit for unit in units if unit.status == RelocalizationStatus(str(self.status_combo.currentData()))]
        if self.target_only_check.isChecked():
            units = [unit for unit in units if unit.target is not None]
        if self.changed_only_check.isChecked():
            units = [unit for unit in units if unit.is_changed]

        search_value = self.search_edit.text().strip().lower()
        if search_value and len(search_value) >= 2:
            units = [
                unit
                for unit in units
                if search_value in unit.source_text.lower()
                or search_value in self._old_text_for_unit(unit).lower()
                or search_value in unit.replacement_text.lower()
            ]

        self._visible_units = units
        self.table.setRowCount(len(units))
        for row, unit in enumerate(units):
            has_override = self._find_mod_override_entry(unit) is not None
            values = [
                str(unit.kind),
                unit.source.dll_name,
                str(unit.source.local_id),
                str(unit.source.global_id),
                self._status_text(unit.status),
                "YES" if has_override else "NO",
                self._tr("yes") if unit.is_changed else self._tr("no"),
                " ".join(unit.source_text.split())[:120],
                " ".join(self._old_text_for_unit(unit).split())[:120],
            ]
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))

        self.table.resizeColumnsToContents()
        self._update_summary(catalog, units)
        if units:
            self.table.selectRow(0)
        else:
            self.source_preview.clear()
            self.target_preview.clear()
            self.detail_label.setText(self._tr("detail.none"))
        self._refresh_project_status()
        self._refresh_progress()
        self._refresh_editor_status()
        self._refresh_apply_resume_status()
        self._refresh_simple_mode()

    def _sync_dll_filter_from_plan_table(self) -> None:
        row = self.dll_plan_table.currentRow()
        if row < 0 or row >= len(self._dll_plans):
            return
        index = self.dll_combo.findText(self._dll_plans[row].dll_name)
        if index >= 0:
            self.dll_combo.setCurrentIndex(index)

    def _with_busy_cursor(self, callback) -> None:
        app = QApplication.instance()
        if app is None:
            callback()
            return
        app.setOverrideCursor(QCursor(Qt.WaitCursor))
        try:
            callback()
        finally:
            app.restoreOverrideCursor()
