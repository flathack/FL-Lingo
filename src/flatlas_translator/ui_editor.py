"""Editor, preview, and terminology helpers for FL Lingo."""

from __future__ import annotations

from PySide6.QtWidgets import QTableWidgetItem, QTextEdit

from .dll_plans import DllStrategy
from .models import ResourceCatalog, ResourceKind, TranslationUnit
from .stats import summarize_catalog
from .terminology import list_pattern_entries, list_terminology_entries, save_replacement_pattern, save_term_mapping
from .translation_exchange import update_manual_translation


class UIEditorMixin:
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
