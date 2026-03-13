"""UI state and refresh mixin for FL Lingo main window."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QComboBox, QLineEdit, QTableWidgetItem

from .dll_plans import DllStrategy
from .models import ResourceCatalog
from .stats import summarize_catalog
from .terminology import clear_term_map_cache


class UIStateMixin:
    def _handle_install_path_change(self, _value: str = "") -> None:
        self._invalidate_audio_progress_cache()
        self._update_action_state()

    def _invalidate_audio_progress_cache(self) -> None:
        self._audio_progress_cache_key = None
        self._audio_progress_cache_value = (0, 0, 0)

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

    def _apply_ui_mode(self, *, save: bool = True) -> None:
        if hasattr(self, "simple_mode_button"):
            self.simple_mode_button.setChecked(self._ui_mode == "simple")
        if hasattr(self, "expert_mode_button"):
            self.expert_mode_button.setChecked(self._ui_mode == "expert")
        if hasattr(self, "main_mode_stack"):
            self.main_mode_stack.setCurrentIndex(0 if self._ui_mode == "simple" else 1)
        if save:
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
        self._load_compare_catalog()

    def _refresh_simple_mode(self) -> None:
        if not hasattr(self, "simple_scan_summary_label"):
            return
        source_path = self.source_edit.text().strip()
        target_path = self.target_edit.text().strip()
        self._mirror_line_edit_text("simple_source_edit", source_path)
        self._mirror_line_edit_text("simple_target_edit", target_path)
        localized, done, skipped, total, _percent, _covered_percent = self._translation_progress()
        self.simple_progress_chart.set_progress(total=total, localized=localized, done=done, skipped=skipped)
        audio_total, audio_ready, audio_open = self._audio_progress()
        if hasattr(self, "simple_audio_progress_bar"):
            self.simple_audio_progress_bar.setMaximum(max(1, audio_total))
            self.simple_audio_progress_bar.setValue(audio_ready if audio_total else 0)
        if hasattr(self, "simple_audio_progress_label"):
            if audio_total == 0:
                self.simple_audio_progress_label.setText(self._tr("progress.audio.none"))
            else:
                self.simple_audio_progress_label.setText(
                    self._tr("progress.audio.text").format(
                        percent=round((audio_ready / audio_total) * 100),
                        ready=audio_ready,
                        total=audio_total,
                        open=audio_open,
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
            self.simple_scan_summary_label.setText(self._tr("simple.summary.idle"))

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
        can_simple_scan = bool(self.source_edit.text().strip()) and bool(self.target_edit.text().strip()) and not self._apply_active
        can_audio = bool(self.source_edit.text().strip()) and bool(self.target_edit.text().strip()) and not self._apply_active
        apply_tooltip = ""
        if not has_comparison:
            apply_tooltip = self._tr("tooltip.apply_disabled_compare")
        elif not has_toolchain:
            apply_tooltip = self._tr("tooltip.apply_disabled_toolchain")
        if hasattr(self, "compare_button"):
            self.compare_button.setEnabled(has_source)
            self.export_button.setEnabled(has_catalog)
            self.export_mod_only_button.setEnabled(has_catalog)
            self.export_long_open_button.setEnabled(has_catalog)
            self.import_exchange_button.setEnabled(has_catalog)
            self.copy_audio_button.setEnabled(can_audio)
            self.assemble_patch_button.setEnabled(can_audio)
            self.apply_button.setEnabled(can_apply)
            self.apply_button.setToolTip(apply_tooltip)
        if hasattr(self, "primary_apply_button"):
            self.primary_apply_button.setEnabled(can_apply)
            self.primary_apply_button.setToolTip(apply_tooltip)
        if hasattr(self, "main_export_button"):
            self.main_export_button.setEnabled(has_catalog)
            self.main_long_export_button.setEnabled(has_catalog)
            self.main_import_button.setEnabled(has_catalog)
            self.main_copy_audio_button.setEnabled(can_audio)
            self.main_patch_button.setEnabled(can_audio)
            self.main_apply_button.setEnabled(can_apply)
            self.main_apply_button.setToolTip(apply_tooltip)
        if hasattr(self, "root_tabs"):
            self.root_tabs.setTabEnabled(0, True)
            self.root_tabs.setTabEnabled(1, has_catalog)
        if hasattr(self, "editor_tabs"):
            self.editor_tabs.setTabEnabled(0, has_catalog)
            self.editor_tabs.setTabEnabled(1, has_comparison)
            self.editor_tabs.setTabEnabled(2, has_catalog)
        if hasattr(self, "simple_scan_button"):
            self.simple_scan_button.setEnabled(can_simple_scan)
        if hasattr(self, "simple_translate_button"):
            self.simple_translate_button.setEnabled(can_apply)
            self.simple_translate_button.setToolTip(apply_tooltip)
        if hasattr(self, "simple_audio_copy_check"):
            self.simple_audio_copy_check.setEnabled(can_audio)
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
        localized, done, skipped, total, _percent, covered_percent = self._translation_progress()
        self.translation_progress_bar.set_progress(total=total, localized=localized, done=done, skipped=skipped)
        if total == 0:
            self.translation_progress_label.setText(self._tr("progress.none"))
        else:
            self.translation_progress_label.setText(
                self._tr("progress.text").format(
                    percent=covered_percent,
                    done=done + skipped,
                    total=total,
                    localized=localized,
                    available=max(0, done - localized),
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
                self._tr("table.units.changed"),
                self._tr("table.units.preview"),
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
