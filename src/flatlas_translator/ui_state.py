"""UI state and refresh mixin for FL Lingo main window."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QComboBox, QLineEdit, QTableWidgetItem

from .dll_plans import DllStrategy
from .models import RelocalizationStatus, ResourceCatalog
from .path_utils import ci_find
from .stats import summarize_catalog
from .terminology import clear_term_map_cache

_VALID_STYLE = ""
_INVALID_STYLE = "border: 2px solid #c62828;"


class UIStateMixin:
    def _validate_install_path(self, path_str: str) -> str | None:
        """Return None if valid, or an error message string if not."""
        if not path_str:
            return None  # empty is not an error, just not ready
        install_dir = Path(path_str)
        if not install_dir.is_dir():
            return self._tr("validate.no_exe_dir").format(path=path_str)
        exe_dir = ci_find(install_dir, "EXE")
        if exe_dir is None or not exe_dir.is_dir():
            return self._tr("validate.no_exe_dir").format(path=path_str)
        has_dll = any(f.suffix.lower() == ".dll" for f in exe_dir.iterdir() if f.is_file())
        if not has_dll:
            return self._tr("validate.no_dlls").format(path=exe_dir)
        return None

    def _style_path_field(self, edit: QLineEdit, error: str | None) -> None:
        if error:
            edit.setStyleSheet(_INVALID_STYLE)
            edit.setToolTip(error)
        else:
            edit.setStyleSheet(_VALID_STYLE)
            text = edit.text().strip()
            edit.setToolTip(self._tr("validate.ok") if text else "")

    def _is_no_reference_mode(self) -> bool:
        """Return True if the user has selected no-reference mode (simple mode always, or expert with checkbox)."""
        if self._ui_mode == "simple":
            return True
        return hasattr(self, "no_reference_check") and self.no_reference_check.isChecked()

    def _validate_and_style_paths(self) -> bool:
        """Validate all path fields, apply styling, return True if paths are valid for scanning."""
        source_err = self._validate_install_path(self.source_edit.text().strip())
        self._style_path_field(self.source_edit, source_err)
        if hasattr(self, "simple_source_edit"):
            self._style_path_field(self.simple_source_edit, source_err)

        no_ref = self._is_no_reference_mode()

        if no_ref:
            # In no-reference mode, only source must be valid
            target_err = None
        else:
            target_err = self._validate_install_path(self.target_edit.text().strip())
        self._style_path_field(self.target_edit, target_err)
        if hasattr(self, "simple_target_edit") and self.simple_target_edit.isVisible():
            self._style_path_field(self.simple_target_edit, target_err)
        # en_ref is optional
        en_ref_text = ""
        if hasattr(self, "en_ref_edit"):
            en_ref_text = self.en_ref_edit.text().strip()
        en_ref_err = self._validate_install_path(en_ref_text) if en_ref_text else None
        if hasattr(self, "en_ref_edit"):
            self._style_path_field(self.en_ref_edit, en_ref_err)
        if hasattr(self, "simple_en_ref_edit") and self.simple_en_ref_edit.isVisible():
            self._style_path_field(self.simple_en_ref_edit, en_ref_err)
        source_ok = bool(self.source_edit.text().strip()) and source_err is None
        if no_ref:
            return source_ok
        target_ok = bool(self.target_edit.text().strip()) and target_err is None
        return source_ok and target_ok

    def _handle_install_path_change(self, _value: str = "") -> None:
        self._invalidate_audio_progress_cache()
        self._update_action_state()

    def _on_no_reference_toggled(self, state: int) -> None:
        """Show/hide reference install fields based on no-reference checkbox."""
        no_ref = bool(state)
        if hasattr(self, "target_install_label"):
            self.target_install_label.setVisible(not no_ref)
        if hasattr(self, "target_edit"):
            self.target_edit.setVisible(not no_ref)
        if hasattr(self, "browse_target_button"):
            self.browse_target_button.setVisible(not no_ref)
        if hasattr(self, "en_ref_install_label"):
            self.en_ref_install_label.setVisible(not no_ref)
        if hasattr(self, "en_ref_edit"):
            self.en_ref_edit.setVisible(not no_ref)
        if hasattr(self, "browse_en_ref_button"):
            self.browse_en_ref_button.setVisible(not no_ref)
        self._update_action_state()

    def _sync_simple_language_to_expert(self) -> None:
        """Sync language combos from simple mode to expert mode."""
        if hasattr(self, "simple_source_lang_combo"):
            code = self.simple_source_lang_combo.currentData()
            if code:
                self._source_lang_code = code
                self._set_language_combo_value(self.source_lang_edit, code)
        if hasattr(self, "simple_target_lang_combo"):
            code = self.simple_target_lang_combo.currentData()
            if code:
                self._target_lang_code = code
                self._set_language_combo_value(self.target_lang_edit, code)
        self._store_language_pair()

    def _invalidate_audio_progress_cache(self) -> None:
        self._audio_progress_cache_key = None
        self._audio_progress_cache_value = (0, 0, 0)
        self._utf_progress_cache_key = None
        self._utf_progress_cache_value = (0, 0, 0, 0, 0)

    def _audio_progress(self) -> tuple[int, int, int]:
        source_path = self.source_edit.text().strip()
        target_path = self.target_edit.text().strip()
        cache_key = (source_path, target_path)
        if self._audio_progress_cache_key == cache_key:
            return self._audio_progress_cache_value
        if not source_path or not target_path:
            result = (0, 0, 0)
        else:
            source_install = Path(source_path)
            target_install = Path(target_path)
            if not source_install.exists() or not target_install.exists():
                result = (0, 0, 0)
            else:
                progress = self._writer.audio_copy_progress(source_install, target_install)
                result = (progress.total_files, progress.matching_files, progress.differing_files)
        self._audio_progress_cache_key = cache_key
        self._audio_progress_cache_value = result
        return result

    def _utf_audio_progress(self) -> tuple[int, int, int, int, int]:
        """Return (total_files, total_entries, already_de, replaceable, already_mod)."""
        source_path = self.source_edit.text().strip()
        target_path = self.target_edit.text().strip()
        en_ref_path = ""
        if hasattr(self, "en_ref_edit"):
            en_ref_path = self.en_ref_edit.text().strip()
        if not en_ref_path and hasattr(self, "simple_en_ref_edit"):
            en_ref_path = self.simple_en_ref_edit.text().strip()
        cache_key = (source_path, target_path, en_ref_path)
        if self._utf_progress_cache_key == cache_key:
            return self._utf_progress_cache_value
        if not source_path or not target_path or not en_ref_path:
            result = (0, 0, 0, 0, 0)
        else:
            source_install = Path(source_path)
            target_install = Path(target_path)
            en_ref_install = Path(en_ref_path)
            if not source_install.exists() or not target_install.exists() or not en_ref_install.exists():
                result = (0, 0, 0, 0, 0)
            else:
                progress = self._writer.utf_audio_progress(source_install, en_ref_install, target_install)
                result = (progress.total_files, progress.total_entries, progress.already_de, progress.replaceable, progress.already_mod)
        self._utf_progress_cache_key = cache_key
        self._utf_progress_cache_value = result
        return result

    def _apply_ui_mode(self, *, save: bool = True) -> None:
        if hasattr(self, "main_mode_tabs"):
            self.main_mode_tabs.setCurrentIndex(0 if self._ui_mode == "simple" else 1)
        if save:
            self._save_persistent_settings()
        self._refresh_simple_mode()

    def _on_mode_tab_changed(self, index: int) -> None:
        self._ui_mode = "simple" if index == 0 else "expert"
        self._save_persistent_settings()
        self._refresh_simple_mode()

    def _set_ui_mode(self, mode: str, *, save: bool = True) -> None:
        resolved_mode = "expert" if str(mode or "").strip().lower() == "expert" else "simple"
        if self._ui_mode == resolved_mode and save:
            self._apply_ui_mode(save=save)
            return
        self._ui_mode = resolved_mode
        self._apply_ui_mode(save=save)

    def _run_simple_scan(self) -> None:
        self._sync_simple_language_to_expert()
        self._load_source_only_as_paired()

    def _run_expert_scan(self) -> None:
        if hasattr(self, "no_reference_check") and self.no_reference_check.isChecked():
            self._load_source_only_as_paired()
        else:
            self._load_compare_catalog()

    def _refresh_expert_scan_summary(self) -> None:
        if not hasattr(self, "expert_scan_summary_label"):
            return
        if self._paired_catalog is not None:
            stats = summarize_catalog(self._paired_catalog)
            affected_dlls = len({unit.source.dll_name.lower() for unit in self._paired_catalog.units})
            self.expert_scan_summary_label.setText(
                self._tr("expert.scan.summary.ready").format(
                    total=len(self._paired_catalog.units),
                    auto=stats.auto_relocalize,
                    manual=stats.manual_translation,
                    open=stats.mod_only,
                    dlls=affected_dlls,
                )
            )
        else:
            self.expert_scan_summary_label.setText(self._tr("expert.scan.summary.idle"))

    def _refresh_simple_mode(self) -> None:
        if not hasattr(self, "simple_scan_summary_label"):
            return
        source_path = self.source_edit.text().strip()
        target_path = self.target_edit.text().strip()
        self._mirror_line_edit_text("simple_source_edit", source_path)
        self._mirror_line_edit_text("simple_target_edit", target_path)
        if hasattr(self, "en_ref_edit") and hasattr(self, "simple_en_ref_edit"):
            en_ref_path = self.en_ref_edit.text().strip()
            self._mirror_line_edit_text("simple_en_ref_edit", en_ref_path)
        localized, done, skipped, total, _percent, _covered_percent, manual, terminology = self._translation_progress()
        self.simple_progress_chart.set_progress(total=total, localized=localized, done=done, skipped=skipped, manual=manual, terminology=terminology)
        audio_total, audio_ready, audio_open = self._audio_progress()
        utf_files, utf_total, utf_de, utf_repl, utf_mod = self._utf_audio_progress()
        if hasattr(self, "simple_utf_progress_bar"):
            self.simple_utf_progress_bar.setMaximum(max(1, utf_total))
            self.simple_utf_progress_bar.setValue(utf_de if utf_total else 0)
        if hasattr(self, "simple_utf_progress_label"):
            if utf_total == 0:
                self.simple_utf_progress_label.setText(self._tr("progress.utf.none"))
            else:
                self.simple_utf_progress_label.setText(
                    self._tr("progress.utf.text").format(
                        percent=round((utf_de / utf_total) * 100),
                        de=utf_de,
                        total=utf_total,
                        replaceable=utf_repl,
                        mod=utf_mod,
                        files=utf_files,
                    )
                )

        if self._paired_catalog is not None:
            stats = summarize_catalog(self._paired_catalog)
            affected_dlls = len({unit.source.dll_name.lower() for unit in self._paired_catalog.units})
            self.simple_scan_summary_label.setText(
                self._tr("simple.summary.ready").format(
                    total=len(self._paired_catalog.units),
                    auto=stats.auto_relocalize,
                    manual=stats.manual_translation,
                    open=stats.mod_only,
                    dlls=affected_dlls,
                )
            )
        elif self._source_catalog is not None:
            self.simple_scan_summary_label.setText(self._tr("simple.summary.source_loaded"))
        else:
            self.simple_scan_summary_label.setText(self._tr("simple.summary.idle.no_ref"))

        if self._paired_catalog is not None:
            apply_units = self._apply_candidate_units()
            session = self._writer.load_apply_session(self._paired_catalog, units=apply_units) if apply_units else None
            if session is not None and session.pending_dlls:
                self.simple_translate_summary_label.setText(
                    self._tr("simple.translate.resume").format(
                        done=len(session.completed_dlls),
                        total=session.total_dlls,
                    )
                )
            else:
                self.simple_translate_summary_label.setText(
                    self._tr("simple.translate.ready").format(count=len(apply_units))
                )
        elif self._source_catalog is not None:
            self.simple_translate_summary_label.setText(self._tr("simple.summary.source_loaded"))
        else:
            self.simple_translate_summary_label.setText(self._tr("simple.translate.idle"))

        toolchain_state = self._tr("toolchain.available") if self._writer.has_toolchain() else self._tr("simple.translate.no_toolchain")
        self.simple_toolchain_label.setText(f"Resource-Toolchain: {toolchain_state}")

    def _default_install_path_hint(self, role: str) -> str:
        if self._writer.is_windows():
            if role == "source":
                return r"C:\Freelancer Crossfire"
            return r"C:\Users\STAdmin\FLAtlas\FL-Installationen\_FL Fresh Install-deutsch"
        return str(Path.home())

    def _focus_editor_tab(self) -> None:
        if hasattr(self, "root_tabs"):
            self.root_tabs.setCurrentIndex(1)
        if hasattr(self, "editor_tabs"):
            self.editor_tabs.setCurrentIndex(0)
        self._apply_editor_default_filters(force=False)
        self._refresh_table()
        self.table.setFocus()

    def _focus_dll_tab(self) -> None:
        if hasattr(self, "root_tabs"):
            self.root_tabs.setCurrentIndex(1)
        if hasattr(self, "editor_tabs"):
            self.editor_tabs.setCurrentIndex(1)
        self.dll_plan_table.setFocus()

    def _store_language_pair(self) -> None:
        self._source_lang_code = self._combo_language_code(self.source_lang_edit, self._source_lang_code)
        self._target_lang_code = self._combo_language_code(self.target_lang_edit, self._target_lang_code)
        self._set_language_combo_value(self.source_lang_edit, self._source_lang_code)
        self._set_language_combo_value(self.target_lang_edit, self._target_lang_code)
        clear_term_map_cache()
        self._save_persistent_settings()
        self._refresh_terminology_tables()
        self._refresh_footer()

    def _update_action_state(self) -> None:
        has_source = self._source_catalog is not None
        has_comparison = self._paired_catalog is not None
        has_catalog = self._current_catalog() is not None
        has_toolchain = self._writer.has_toolchain()
        can_apply = has_comparison and has_toolchain and not self._apply_active
        paths_valid = self._validate_and_style_paths()
        can_simple_scan = paths_valid and not self._apply_active
        can_audio = paths_valid and not self._apply_active and not self._is_no_reference_mode()
        apply_tooltip = ""
        if not has_comparison:
            apply_tooltip = self._tr("tooltip.apply_disabled_compare")
        elif not has_toolchain:
            apply_tooltip = self._tr("tooltip.apply_disabled_toolchain")
        if hasattr(self, "scan_button"):
            self.scan_button.setEnabled(can_simple_scan)
            self.export_mod_only_button.setEnabled(has_catalog)
            self.export_long_open_button.setEnabled(has_catalog)
            self.import_exchange_button.setEnabled(has_catalog)
            self.remove_imports_button.setEnabled(has_catalog)
            self.translate_all_open_button.setEnabled(has_catalog)
            self.copy_audio_button.setEnabled(can_audio)
            self.merge_utf_button.setEnabled(can_audio)
            self.apply_button.setEnabled(can_apply)
            self.apply_button.setToolTip(apply_tooltip)
        if hasattr(self, "translate_all_button"):
            catalog = self._current_catalog()
            apply_count = sum(
                1 for u in catalog.units
                if u.status in {RelocalizationStatus.AUTO_RELOCALIZE, RelocalizationStatus.MANUAL_TRANSLATION}
            ) if catalog is not None else 0
            self.translate_all_button.setText(
                self._tr("btn.translate_all_count").format(count=apply_count)
                if apply_count
                else self._tr("btn.translate_all")
            )
            self.translate_all_button.setEnabled(can_apply)
            self.translate_all_button.setToolTip(apply_tooltip)
        if hasattr(self, "editing_section_group"):
            self.editing_section_group.setVisible(has_comparison)
        if hasattr(self, "expert_scan_summary_label"):
            self._refresh_expert_scan_summary()
        if hasattr(self, "import_count_label"):
            catalog = self._current_catalog()
            manual_count = sum(1 for u in catalog.units if u.manual_text) if catalog is not None else 0
            self.import_count_label.setText(self._tr("expert.extras.import_count").format(count=manual_count))
        if hasattr(self, "root_tabs"):
            self.root_tabs.setTabEnabled(0, True)
            self.root_tabs.setTabEnabled(1, has_catalog)
        if hasattr(self, "editor_tabs"):
            self.editor_tabs.setTabEnabled(0, has_catalog)
            self.editor_tabs.setTabEnabled(1, has_comparison)
            self.editor_tabs.setTabEnabled(2, has_catalog)
            self.editor_tabs.setTabEnabled(3, has_catalog)
        if hasattr(self, "simple_scan_button"):
            self.simple_scan_button.setEnabled(can_simple_scan)
        if hasattr(self, "simple_translate_button"):
            self.simple_translate_button.setEnabled(can_apply)
            self.simple_translate_button.setToolTip(apply_tooltip)
        if hasattr(self, "simple_auto_translate_button"):
            self.simple_auto_translate_button.setEnabled(has_catalog and not self._apply_active)
        self._refresh_simple_mode()

    def _populate_dll_filter(self, catalog: ResourceCatalog | None) -> None:
        current_text = self.dll_combo.currentText()
        self.dll_combo.blockSignals(True)
        self.dll_combo.clear()
        self.dll_combo.addItem(self._tr("kind.all"))
        if catalog is not None:
            for dll_name in sorted({unit.source.dll_name for unit in catalog.units}):
                self.dll_combo.addItem(dll_name)
        index = max(0, self.dll_combo.findText(current_text))
        self.dll_combo.setCurrentIndex(index)
        self.dll_combo.blockSignals(False)

    def _schedule_search_refresh(self) -> None:
        search_value = self.search_edit.text().strip()
        if len(search_value) == 0:
            self._search_debounce_timer.stop()
            self._refresh_table()
            return
        if len(search_value) < 2:
            return
        self._search_debounce_timer.start(400)

    def _refresh_dll_plan_table(self) -> None:
        self.dll_plan_table.setRowCount(len(self._dll_plans))
        for row, plan in enumerate(self._dll_plans):
            total_units = max(1, plan.source_strings + plan.source_infocards)
            coverage_percent = round((plan.translated_units / total_units) * 100)
            action = (
                self._tr("plan.action.full")
                if plan.strategy == DllStrategy.FULL_REPLACE_SAFE
                else self._tr("plan.action.patch")
                if plan.strategy == DllStrategy.PATCH_REQUIRED
                else self._tr("plan.action.unsafe")
            )
            values = [
                plan.dll_name,
                self._dll_strategy_label(plan.strategy),
                f"{coverage_percent}% ({plan.translated_units}/{total_units})",
                str(plan.translated_units),
                str(plan.mod_only_units),
                str(plan.matched_units),
                action,
            ]
            for column, value in enumerate(values):
                self.dll_plan_table.setItem(row, column, QTableWidgetItem(value))
        self.dll_plan_table.resizeColumnsToContents()

    def _refresh_progress(self) -> None:
        localized, done, skipped, total, _percent, covered_percent, manual, terminology = self._translation_progress()
        self.translation_progress_bar.set_progress(total=total, localized=localized, done=done, skipped=skipped, manual=manual, terminology=terminology)
        if total == 0:
            self.translation_progress_label.setText(self._tr("progress.none"))
        else:
            self.translation_progress_label.setText(
                self._tr("progress.text").format(
                    percent=covered_percent,
                    done=done + terminology + skipped,
                    total=total,
                    localized=localized,
                    available=max(0, done - localized - manual),
                    manual=manual,
                    terminology=terminology,
                    skipped=skipped,
                )
            )
        audio_total, audio_ready, audio_open = self._audio_progress()
        self.audio_progress_bar.setMaximum(max(1, audio_total))
        self.audio_progress_bar.setValue(audio_ready if audio_total else 0)
        if audio_total == 0:
            self.audio_progress_label.setText(self._tr("progress.audio.none"))
        else:
            self.audio_progress_label.setText(
                self._tr("progress.audio.text").format(
                    percent=round((audio_ready / audio_total) * 100),
                    ready=audio_ready,
                    total=audio_total,
                    open=audio_open,
                )
            )

        utf_files, utf_total, utf_de, utf_repl, utf_mod = self._utf_audio_progress()
        if hasattr(self, "utf_progress_bar"):
            self.utf_progress_bar.setMaximum(max(1, utf_total))
            self.utf_progress_bar.setValue(utf_de if utf_total else 0)
        if hasattr(self, "utf_progress_label"):
            if utf_total == 0:
                self.utf_progress_label.setText(self._tr("progress.utf.none"))
            else:
                self.utf_progress_label.setText(
                    self._tr("progress.utf.text").format(
                        percent=round((utf_de / utf_total) * 100),
                        de=utf_de,
                        total=utf_total,
                        replaceable=utf_repl,
                        mod=utf_mod,
                        files=utf_files,
                    )
                )

    def _refresh_toolchain_label(self) -> None:
        toolchain_state = self._tr("toolchain.available") if self._writer.has_toolchain() else self._tr("toolchain.unavailable")
        self.toolchain_label.setText(f"Resource-Toolchain: {toolchain_state}")
        self._refresh_simple_mode()

    def _retitle_combo_items(self) -> None:
        self.kind_combo.setItemText(0, self._tr("kind.all"))
        self.dll_combo.setItemText(0, self._tr("kind.all"))
        self._populate_status_filter()

    def _update_units_header(self) -> None:
        self.table.setHorizontalHeaderLabels(
            [
                self._tr("table.units.kind"),
                self._tr("table.units.dll"),
                self._tr("table.units.local_id"),
                self._tr("table.units.global_id"),
                self._tr("table.units.status"),
                self._tr("table.units.override"),
                self._tr("table.units.changed"),
                self._tr("table.units.preview"),
                self._tr("table.units.old_text"),
            ]
        )

    def _update_dll_plan_headers(self) -> None:
        labels = [
            self._tr("table.plans.dll"),
            self._tr("table.plans.status"),
            self._tr("table.plans.coverage"),
            self._tr("table.plans.ready"),
            self._tr("table.plans.open"),
            self._tr("table.plans.reference"),
            self._tr("table.plans.action"),
        ]
        tooltips = [
            self._tr("dll.tooltip.dll"),
            self._tr("dll.tooltip.status"),
            self._tr("dll.tooltip.coverage"),
            self._tr("dll.tooltip.ready"),
            self._tr("dll.tooltip.open"),
            self._tr("dll.tooltip.reference"),
            self._tr("dll.tooltip.action"),
        ]
        self.dll_plan_table.setHorizontalHeaderLabels(labels)
        for index, tooltip in enumerate(tooltips):
            header_item = self.dll_plan_table.horizontalHeaderItem(index)
            if header_item is not None:
                header_item.setToolTip(tooltip)
