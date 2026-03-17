"""Editor, preview, and terminology helpers for FL Lingo."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication, QInputDialog, QMenu, QMessageBox, QTableWidgetItem, QTextEdit

from .dll_plans import DllStrategy
from .mod_overrides import ModOverrideEntry, delete_mod_override, save_mod_override
from .models import RelocalizationStatus, ResourceCatalog, ResourceKind, TranslationUnit
from .stats import summarize_catalog
from .terminology import list_pattern_entries, list_terminology_entries, save_replacement_pattern, save_term_mapping
from .translation_exchange import update_manual_translation


class UIEditorMixin:
    def _old_text_for_unit(self, unit: TranslationUnit) -> str:
        key = (str(unit.kind), unit.source.dll_name.lower(), int(unit.source.local_id))
        return self._old_text_lookup.get(key, unit.source_text)

    def _refresh_mod_overrides_table(self) -> None:
        if not hasattr(self, "mod_overrides_table"):
            return
        self.mod_overrides_table.setHorizontalHeaderLabels(
            [
                self._tr("table.mod_overrides.kind"),
                self._tr("table.mod_overrides.dll"),
                self._tr("table.mod_overrides.local_id"),
                self._tr("table.mod_overrides.mode"),
                self._tr("table.mod_overrides.override_text"),
                self._tr("table.mod_overrides.source_text"),
            ]
        )
        self.mod_overrides_table.setRowCount(len(self._mod_override_entries))
        for row, entry in enumerate(self._mod_override_entries):
            mode_label = self._tr("mod_overrides.mode.keep") if entry.mode == "keep_original" else self._tr("mod_overrides.mode.custom")
            values = [
                entry.kind,
                entry.dll_name,
                str(entry.local_id),
                mode_label,
                " ".join(str(entry.override_text or "").split())[:120],
                " ".join(str(entry.source_text or "").split())[:120],
            ]
            for col, value in enumerate(values):
                self.mod_overrides_table.setItem(row, col, QTableWidgetItem(value))
        self.mod_overrides_table.resizeColumnsToContents()

    def _update_summary(self, catalog: ResourceCatalog, visible_units: list[TranslationUnit]) -> None:
        total = len(catalog.units)
        visible = len(visible_units)
        strings = summarize_catalog(catalog, ResourceKind.STRING)
        infocards = summarize_catalog(catalog, ResourceKind.INFOCARD)
        self.summary_label.setText(
            " | ".join(
                [
                    self._tr("summary.visible").format(visible=visible, total=total),
                    self._tr("summary.full").format(count=sum(1 for plan in self._dll_plans if plan.strategy == DllStrategy.FULL_REPLACE_SAFE)),
                    self._tr("summary.patch").format(count=sum(1 for plan in self._dll_plans if plan.strategy == DllStrategy.PATCH_REQUIRED)),
                    self._tr("summary.unsafe").format(count=sum(1 for plan in self._dll_plans if plan.strategy == DllStrategy.NOT_SAFE)),
                    self._tr("summary.strings").format(auto=strings.auto_relocalize, manual=strings.manual_translation, localized=strings.already_localized, mod_only=strings.mod_only),
                    self._tr("summary.infocards").format(auto=infocards.auto_relocalize, manual=infocards.manual_translation, localized=infocards.already_localized, mod_only=infocards.mod_only),
                ]
            )
        )
        if hasattr(self, "workflow_summary_label"):
            self.workflow_summary_label.setText(self.summary_label.text())

    def _update_preview(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._visible_units):
            self.detail_label.setText(self._tr("detail.none"))
            self.source_preview.clear()
            self.target_preview.clear()
            return
        unit = self._visible_units[row]
        self.detail_label.setText(
            " | ".join(
                [
                    f"{self._tr('detail.kind')}: {unit.kind}",
                    f"{self._tr('detail.status')}: {self._status_text(unit.status)}",
                    f"DLL: {unit.source.dll_name}",
                    f"Local ID: {unit.source.local_id}",
                    f"Global ID: {unit.source.global_id}",
                    f"{self._tr('detail.reference')}: {self._tr('yes') if unit.target else self._tr('no')}",
                    f"{self._tr('detail.manual')}: {self._tr('yes') if bool(unit.manual_text) else self._tr('no')}",
                    f"{self._tr('detail.changed')}: {self._tr('yes') if unit.is_changed else self._tr('no')}",
                ]
            )
        )
        self.source_preview.setPlainText(unit.source_text)
        self.target_preview.setPlainText(unit.replacement_text)

    def _fill_term_from_selection(self) -> None:
        selected_text = self.source_preview.textCursor().selectedText().replace("\u2029", "\n").strip()
        if not selected_text:
            selected_text = self.target_preview.textCursor().selectedText().replace("\u2029", "\n").strip()
        if not selected_text:
            unit = self._selected_unit()
            if unit is not None and "\n" not in unit.source_text.strip():
                selected_text = unit.source_text.strip()
        if selected_text:
            self.term_source_edit.setText(selected_text)

    def _selected_preview_text(self, preview: QTextEdit) -> str:
        return preview.textCursor().selectedText().replace("\u2029", "\n").strip()

    def _use_term_source_text(self, selected_text: str) -> None:
        source_term = selected_text.strip()
        if not source_term:
            return
        self.term_source_edit.setText(source_term)
        self._set_status(self._tr("status.term_source_selected"))

    def _use_term_target_text(self, selected_text: str) -> None:
        target_term = selected_text.strip()
        if not target_term:
            return
        self.term_target_edit.setText(target_term)
        self._set_status(self._tr("status.term_target_selected"))

    def _save_term_mapping_from_selection(self, selected_text: str) -> None:
        self._use_term_source_text(selected_text)
        self._save_terminology_mapping()

    def _show_source_preview_context_menu(self, position) -> None:
        menu = self.source_preview.createStandardContextMenu()
        selected_text = self._selected_preview_text(self.source_preview)
        if selected_text and "\n" not in selected_text:
            menu.addSeparator()
            use_action = menu.addAction(self._tr("menuitem.term_source_from_selection"))
            use_action.triggered.connect(lambda checked=False, text=selected_text: self._use_term_source_text(text))
            if self.term_target_edit.text().strip():
                save_action = menu.addAction(self._tr("menuitem.term_save_from_selection"))
                save_action.triggered.connect(
                    lambda checked=False, text=selected_text: self._save_term_mapping_from_selection(text)
                )
        menu.exec(self.source_preview.mapToGlobal(position))

    def _show_target_preview_context_menu(self, position) -> None:
        menu = self.target_preview.createStandardContextMenu()
        selected_text = self._selected_preview_text(self.target_preview)
        if selected_text and "\n" not in selected_text:
            menu.addSeparator()
            use_action = menu.addAction(self._tr("menuitem.term_target_from_selection"))
            use_action.triggered.connect(lambda checked=False, text=selected_text: self._use_term_target_text(text))
        menu.exec(self.target_preview.mapToGlobal(position))

    def _show_unit_table_context_menu(self, position) -> None:
        row = self.table.rowAt(position.y())
        if row >= 0:
            self.table.selectRow(row)
        unit = self._selected_unit()
        if unit is None:
            return
        menu = QMenu(self.table)
        keep_action = menu.addAction(self._tr("menuitem.mod_override_keep"))
        keep_action.triggered.connect(lambda checked=False, selected_unit=unit: self._save_mod_override_keep(selected_unit))
        custom_action = menu.addAction(self._tr("menuitem.mod_override_custom"))
        custom_action.triggered.connect(lambda checked=False, selected_unit=unit: self._save_mod_override_custom(selected_unit))
        if self._find_mod_override_entry(unit) is not None:
            menu.addSeparator()
            remove_action = menu.addAction(self._tr("menuitem.mod_override_remove"))
            remove_action.triggered.connect(lambda checked=False, selected_unit=unit: self._remove_mod_override_for_unit(selected_unit))
        menu.exec(self.table.viewport().mapToGlobal(position))

    def _find_mod_override_entry(self, unit: TranslationUnit) -> ModOverrideEntry | None:
        key = (str(unit.kind), unit.source.dll_name.lower(), int(unit.source.local_id))
        return next((entry for entry in self._mod_override_entries if entry.key() == key), None)

    def _save_mod_override_keep(self, unit: TranslationUnit) -> None:
        catalog = self._current_catalog()
        if catalog is None:
            return
        path = save_mod_override(
            catalog.install_dir,
            ModOverrideEntry(
                kind=str(unit.kind),
                dll_name=unit.source.dll_name,
                local_id=int(unit.source.local_id),
                mode="keep_original",
                source_text=unit.source_text,
            ),
        )
        self._reload_current_catalog_after_override()
        self._set_status(self._tr("status.mod_override_saved").format(path=path))

    def _save_mod_override_custom(self, unit: TranslationUnit) -> None:
        catalog = self._current_catalog()
        if catalog is None:
            return
        text, accepted = QInputDialog.getMultiLineText(
            self,
            self._tr("dialog.mod_override_custom_title"),
            self._tr("dialog.mod_override_custom_label"),
            unit.replacement_text or unit.source_text,
        )
        if not accepted:
            return
        cleaned = str(text or "").strip()
        if not cleaned:
            self._show_error(self._tr("error.mod_override_empty"))
            return
        path = save_mod_override(
            catalog.install_dir,
            ModOverrideEntry(
                kind=str(unit.kind),
                dll_name=unit.source.dll_name,
                local_id=int(unit.source.local_id),
                mode="custom_text",
                override_text=cleaned,
                source_text=unit.source_text,
            ),
        )
        self._reload_current_catalog_after_override()
        self._set_status(self._tr("status.mod_override_saved").format(path=path))

    def _remove_mod_override_for_unit(self, unit: TranslationUnit) -> None:
        catalog = self._current_catalog()
        if catalog is None:
            return
        path = delete_mod_override(
            catalog.install_dir,
            kind=str(unit.kind),
            dll_name=unit.source.dll_name,
            local_id=int(unit.source.local_id),
        )
        self._reload_current_catalog_after_override()
        self._set_status(self._tr("status.mod_override_removed").format(path=path))

    def _delete_selected_mod_override(self) -> None:
        if not hasattr(self, "mod_overrides_table"):
            return
        row = self.mod_overrides_table.currentRow()
        if row < 0 or row >= len(self._mod_override_entries):
            return
        entry = self._mod_override_entries[row]
        catalog = self._current_catalog()
        install_dir = catalog.install_dir if catalog is not None else self._backup_host_install_dir()
        if install_dir is None:
            return
        path = delete_mod_override(
            install_dir,
            kind=entry.kind,
            dll_name=entry.dll_name,
            local_id=entry.local_id,
        )
        self._reload_current_catalog_after_override()
        self._set_status(self._tr("status.mod_override_removed").format(path=path))

    def _reload_current_catalog_after_override(self) -> None:
        self._refresh_after_mod_override_change()

    def _save_terminology_mapping(self) -> None:
        source_term = self.term_source_edit.text().strip()
        target_term = self.term_target_edit.text().strip()
        if not source_term or not target_term:
            self._show_error(self._tr("error.term_mapping_empty"))
            return
        try:
            save_term_mapping(self._target_lang_code, source_term, target_term)
        except Exception as exc:
            self._show_error(self._tr("error.term_mapping_save_failed").format(error=exc))
            return
        self._refresh_terminology_tables()
        self._set_status(self._tr("status.terminology_saved").format(source=source_term, target=target_term))

    def _save_pattern_mapping(self) -> None:
        source_text = self.pattern_source_edit.text().strip()
        target_text = self.pattern_target_edit.text().strip()
        if not source_text or not target_text:
            self._show_error(self._tr("error.pattern_mapping_empty"))
            return
        try:
            save_replacement_pattern(self._target_lang_code, source_text, target_text)
        except Exception as exc:
            self._show_error(self._tr("error.pattern_mapping_save_failed").format(error=exc))
            return
        self._refresh_terminology_tables()
        self._set_status(self._tr("status.pattern_saved").format(source=source_text, target=target_text))

    def _refresh_terminology_tables(self) -> None:
        if not hasattr(self, "term_table"):
            return
        term_rows = list_terminology_entries(self._target_lang_code)
        self.term_table.setRowCount(len(term_rows))
        self.term_table.setHorizontalHeaderLabels(
            [
                self._tr("table.terms.section"),
                self._tr("table.terms.source"),
                self._tr("table.terms.target"),
            ]
        )
        for row, (section, source, target) in enumerate(term_rows):
            for col, value in enumerate((section, source, target)):
                self.term_table.setItem(row, col, QTableWidgetItem(value))
        self.term_table.resizeColumnsToContents()

        pattern_rows = list_pattern_entries(self._target_lang_code)
        self.pattern_table.setRowCount(len(pattern_rows))
        self.pattern_table.setHorizontalHeaderLabels(
            [
                self._tr("table.patterns.section"),
                self._tr("table.patterns.source"),
                self._tr("table.patterns.target"),
            ]
        )
        for row, pattern in enumerate(pattern_rows):
            values = (pattern.section, pattern.source_text, pattern.target_text)
            for col, value in enumerate(values):
                self.pattern_table.setItem(row, col, QTableWidgetItem(value))
        self.pattern_table.resizeColumnsToContents()

    def _use_selected_term_row(self) -> None:
        if not hasattr(self, "term_table"):
            return
        row = self.term_table.currentRow()
        if row < 0:
            return
        source_item = self.term_table.item(row, 1)
        target_item = self.term_table.item(row, 2)
        if source_item is not None:
            self.term_source_edit.setText(source_item.text())
        if target_item is not None:
            self.term_target_edit.setText(target_item.text())

    def _use_selected_pattern_row(self) -> None:
        if not hasattr(self, "pattern_table"):
            return
        row = self.pattern_table.currentRow()
        if row < 0:
            return
        source_item = self.pattern_table.item(row, 1)
        target_item = self.pattern_table.item(row, 2)
        if source_item is not None:
            self.pattern_source_edit.setText(source_item.text())
        if target_item is not None:
            self.pattern_target_edit.setText(target_item.text())

    def _save_manual_edit(self) -> None:
        unit = self._selected_unit()
        catalog = self._current_catalog()
        if unit is None or catalog is None:
            self._show_error(self._tr("error.select_entry"))
            return
        updated_catalog = update_manual_translation(
            catalog,
            kind=str(unit.kind),
            dll_name=unit.source.dll_name,
            local_id=unit.source.local_id,
            manual_text=self.target_preview.toPlainText(),
            translation_source="manual",
        )
        selected_key = self._unit_key(unit)
        self._replace_current_catalog(updated_catalog)
        self._refresh_table()
        self._select_unit_by_key(selected_key)
        self._set_status(self._tr("status.manual_saved"))

    def _reset_manual_edit(self) -> None:
        unit = self._selected_unit()
        catalog = self._current_catalog()
        if unit is None or catalog is None:
            self._show_error(self._tr("error.select_entry"))
            return
        updated_catalog = update_manual_translation(
            catalog,
            kind=str(unit.kind),
            dll_name=unit.source.dll_name,
            local_id=unit.source.local_id,
            manual_text="",
        )
        selected_key = self._unit_key(unit)
        self._replace_current_catalog(updated_catalog)
        self._refresh_table()
        self._select_unit_by_key(selected_key)
        self._set_status(self._tr("status.manual_reset"))

    # ---- External translator integration ----

    def _translate_selected_entry(self) -> None:
        """Translate the currently selected source text and write it into the target preview."""
        unit = self._selected_unit()
        catalog = self._current_catalog()
        if unit is None or catalog is None:
            self._show_error(self._tr("error.select_entry"))
            return
        source_text = unit.source_text
        if not source_text.strip():
            return
        try:
            from .translator_service import translate_text
        except ImportError:
            self._show_error(self._tr("error.translate_not_available"))
            return
        source_lang = self._source_lang_code
        target_lang = self._target_lang_code
        self.translator_progress_bar.setMaximum(0)
        self.translator_progress_bar.setVisible(True)
        if hasattr(self, "global_progress_bar"):
            self.global_progress_bar.setVisible(True)
        QApplication.processEvents()
        try:
            translated = translate_text(source_text, source_lang, target_lang)
        except Exception as exc:
            self.translator_progress_bar.setVisible(False)
            if hasattr(self, "global_progress_bar"):
                self.global_progress_bar.setVisible(False)
            self._set_status(self._tr("status.translate_entry_failed").format(error=exc))
            return
        self.translator_progress_bar.setVisible(False)
        if hasattr(self, "global_progress_bar"):
            self.global_progress_bar.setVisible(False)
        self.target_preview.setPlainText(translated)
        self._set_status(self._tr("status.translate_entry_done"))

    def _translate_all_open_entries(self) -> None:
        """Populate the bulk-translate tab and switch to it."""
        catalog = self._current_catalog()
        if catalog is None:
            self._show_error(self._tr("error.load_first"))
            return
        try:
            from .translator_service import translate_text
        except ImportError:
            self._show_error(self._tr("error.translate_not_available"))
            return
        from .terminology import is_unit_skippable

        include_terminology = getattr(self, 'include_terminology_check', None)
        if include_terminology is not None and include_terminology.isChecked():
            all_open_units = [u for u in catalog.units if u.status in (RelocalizationStatus.MOD_ONLY, RelocalizationStatus.TERMINOLOGY_TRANSLATION)]
        else:
            all_open_units = [u for u in catalog.units if u.status == RelocalizationStatus.MOD_ONLY]
        total_before_skip = len(all_open_units)
        open_units = [u for u in all_open_units if not is_unit_skippable(u)]
        skipped_count = total_before_skip - len(open_units)
        if not open_units:
            self._set_status(self._tr("status.translate_all_open_done").format(count=0))
            return

        def save_progress(translated_pairs: list) -> None:
            cat = self._current_catalog()
            if cat is None:
                return
            for unit, text in translated_pairs:
                cat = update_manual_translation(
                    cat,
                    kind=str(unit.kind),
                    dll_name=unit.source.dll_name,
                    local_id=unit.source.local_id,
                    manual_text=text,
                    translation_source="auto_translate",
                )
            self._replace_current_catalog(cat)
            self._refresh_table()
            self._update_action_state()
            self._save_project_file()

        prev_log = getattr(self, "_bulk_translate_log", None) or []
        # Read any log entries accumulated in the panel from a previous session
        if hasattr(self, "bulk_translate_panel") and self.bulk_translate_panel._populated:
            prev_log = self.bulk_translate_panel.log_entries
        self.bulk_translate_panel.populate(
            total_open=len(open_units),
            translate_fn=translate_text,
            source_lang=self._source_lang_code,
            target_lang=self._target_lang_code,
            units=open_units,
            save_progress_fn=save_progress,
            log_entries=prev_log,
            skipped_count=skipped_count,
            open_rules_callback=self._open_translation_rules_dialog,
        )
        self.main_mode_tabs.setCurrentIndex(2)

    def _open_translator_settings(self) -> None:
        """Show dialog for translator provider selection and API key."""
        from .ui_dialogs import TranslatorSettingsDialog

        current_key = getattr(self, "_translator_api_key", "") or ""
        current_provider = getattr(self, "_translator_provider", "google") or "google"
        dlg = TranslatorSettingsDialog(
            current_provider=current_provider,
            current_api_key=current_key,
            tr=self._tr,
            parent=self,
        )
        if dlg.exec():
            self._translator_api_key = dlg.selected_api_key
            self._translator_provider = dlg.selected_provider
            self._settings.setValue("translator/api_key", self._translator_api_key)
            self._settings.setValue("translator/provider", self._translator_provider)
