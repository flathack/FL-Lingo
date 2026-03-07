"""Minimal desktop app for browsing and exporting Freelancer translation units."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .catalog import CatalogLoader, pair_catalogs
from .dll_plans import DllRelocalizationPlan, DllStrategy, build_dll_plans
from .exporters import export_catalog_json
from .models import RelocalizationStatus, ResourceCatalog, ResourceKind, TranslationUnit
from .resource_writer import ApplyReport, ResourceWriter
from .stats import summarize_catalog


class TranslatorMainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._loader = CatalogLoader()
        self._writer = ResourceWriter()
        self._source_catalog: ResourceCatalog | None = None
        self._target_catalog: ResourceCatalog | None = None
        self._paired_catalog: ResourceCatalog | None = None
        self._dll_plans: list[DllRelocalizationPlan] = []
        self._visible_units: list[TranslationUnit] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setWindowTitle("FLAtlas Translator")
        self.resize(1440, 900)

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        layout.addWidget(self._build_paths_group())
        layout.addWidget(self._build_filters_group())
        layout.addWidget(self._build_dll_plan_group())
        layout.addWidget(self._build_main_splitter(), 1)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self._set_status("Aktuelle Mod-Installation laden und dann gegen die deutsche Referenz vergleichen.")

    def _build_paths_group(self) -> QGroupBox:
        group = QGroupBox("Installationen")
        grid = QGridLayout(group)

        self.source_edit = QLineEdit(r"C:\Users\STAdmin\Downloads\_FL Fresh Install-englisch")
        self.target_edit = QLineEdit(r"C:\Users\STAdmin\Downloads\_FL Fresh Install-deutsch")

        browse_source = QPushButton("Ordner...")
        browse_source.clicked.connect(lambda: self._pick_directory(self.source_edit))
        browse_target = QPushButton("Ordner...")
        browse_target.clicked.connect(lambda: self._pick_directory(self.target_edit))

        self.include_infocards_check = QCheckBox("Infocards einbeziehen")
        self.include_infocards_check.setChecked(True)

        load_source = QPushButton("Aktuelle Installation laden")
        load_source.clicked.connect(self._load_source_catalog)
        compare_btn = QPushButton("Mit Deutsch vergleichen")
        compare_btn.clicked.connect(self._load_compare_catalog)
        export_btn = QPushButton("Sichtbares JSON exportieren")
        export_btn.clicked.connect(self._export_visible_json)
        export_auto_btn = QPushButton("Auto-DE JSON exportieren")
        export_auto_btn.clicked.connect(self._export_auto_json)
        apply_btn = QPushButton("Deutsch anwenden")
        apply_btn.clicked.connect(self._apply_german_to_install)
        toolchain_btn = QPushButton("Toolchain installieren")
        toolchain_btn.clicked.connect(self._install_toolchain)

        grid.addWidget(QLabel("Aktuelle Mod-Installation"), 0, 0)
        grid.addWidget(self.source_edit, 0, 1)
        grid.addWidget(browse_source, 0, 2)
        grid.addWidget(load_source, 0, 3)

        grid.addWidget(QLabel("Deutsche Referenzinstallation"), 1, 0)
        grid.addWidget(self.target_edit, 1, 1)
        grid.addWidget(browse_target, 1, 2)
        grid.addWidget(compare_btn, 1, 3)

        actions = QHBoxLayout()
        actions.addWidget(self.include_infocards_check)
        actions.addStretch(1)
        actions.addWidget(toolchain_btn)
        actions.addWidget(apply_btn)
        actions.addWidget(export_auto_btn)
        actions.addWidget(export_btn)
        grid.addLayout(actions, 2, 0, 1, 4)
        return group

    def _build_dll_plan_group(self) -> QGroupBox:
        group = QGroupBox("DLL-Analyse")
        layout = QVBoxLayout(group)

        self.dll_plan_table = QTableWidget(0, 8)
        self.dll_plan_table.setHorizontalHeaderLabels(
            [
                "DLL",
                "Strategie",
                "Strings aktuell/DE",
                "Infocards aktuell/DE",
                "Auto-DE",
                "Mod-only",
                "Gematcht",
                "Aktion",
            ]
        )
        self.dll_plan_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.dll_plan_table.setSelectionMode(QTableWidget.SingleSelection)
        self.dll_plan_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.dll_plan_table.verticalHeader().setVisible(False)
        self.dll_plan_table.itemSelectionChanged.connect(self._sync_dll_filter_from_plan_table)
        layout.addWidget(self.dll_plan_table)
        return group

    def _build_filters_group(self) -> QGroupBox:
        group = QGroupBox("Filter")
        row = QHBoxLayout(group)

        self.kind_combo = QComboBox()
        self.kind_combo.addItems(["alle", "string", "infocard"])
        self.kind_combo.currentIndexChanged.connect(self._refresh_table)

        self.dll_combo = QComboBox()
        self.dll_combo.addItem("alle")
        self.dll_combo.currentIndexChanged.connect(self._refresh_table)

        self.status_combo = QComboBox()
        self.status_combo.addItems(
            ["alle", "auto_relocalize", "already_localized", "mod_only"]
        )
        self.status_combo.currentIndexChanged.connect(self._refresh_table)

        self.target_only_check = QCheckBox("Nur Eintraege mit DE-Referenz")
        self.target_only_check.setChecked(True)
        self.target_only_check.stateChanged.connect(self._refresh_table)

        self.changed_only_check = QCheckBox("Nur geaenderte")
        self.changed_only_check.setChecked(True)
        self.changed_only_check.stateChanged.connect(self._refresh_table)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Suche in aktuellem oder deutschem Text")
        self.search_edit.textChanged.connect(self._refresh_table)

        row.addWidget(QLabel("Typ"))
        row.addWidget(self.kind_combo)
        row.addWidget(QLabel("DLL"))
        row.addWidget(self.dll_combo)
        row.addWidget(QLabel("Status"))
        row.addWidget(self.status_combo)
        row.addWidget(self.target_only_check)
        row.addWidget(self.changed_only_check)
        row.addWidget(QLabel("Suche"))
        row.addWidget(self.search_edit, 1)
        return group

    def _build_main_splitter(self) -> QSplitter:
        splitter = QSplitter(Qt.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)

        self.summary_label = QLabel("Noch kein Katalog geladen.")
        self.summary_label.setWordWrap(True)
        left_layout.addWidget(self.summary_label)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Typ", "DLL", "Local ID", "Global ID", "Status", "Geaendert", "Vorschau aktuell"]
        )
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self._update_preview)
        left_layout.addWidget(self.table, 1)

        right = QWidget()
        right_layout = QVBoxLayout(right)

        self.detail_label = QLabel("Keine Auswahl.")
        self.detail_label.setWordWrap(True)
        right_layout.addWidget(self.detail_label)

        self.source_preview = QTextEdit()
        self.source_preview.setReadOnly(True)
        self.target_preview = QTextEdit()
        self.target_preview.setReadOnly(True)

        source_box = QGroupBox("Aktueller Text")
        source_layout = QVBoxLayout(source_box)
        source_layout.addWidget(self.source_preview)

        target_box = QGroupBox("Deutscher Referenztext")
        target_layout = QVBoxLayout(target_box)
        target_layout.addWidget(self.target_preview)

        right_layout.addWidget(source_box, 1)
        right_layout.addWidget(target_box, 1)

        toolchain_state = "verfuegbar" if self._writer.has_toolchain() else "nicht verfuegbar"
        self.toolchain_label = QLabel(f"Resource-Toolchain: {toolchain_state}")
        self.toolchain_label.setWordWrap(True)
        right_layout.addWidget(self.toolchain_label)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([900, 500])
        return splitter

    def _pick_directory(self, line_edit: QLineEdit) -> None:
        start_dir = line_edit.text().strip() or str(Path.home())
        directory = QFileDialog.getExistingDirectory(self, "Freelancer-Installation waehlen", start_dir)
        if directory:
            line_edit.setText(directory)

    def _load_source_catalog(self) -> None:
        source_dir = Path(self.source_edit.text().strip())
        if not source_dir.exists():
            self._show_error(f"Source path does not exist:\n{source_dir}")
            return
        try:
            self._with_busy_cursor(
                lambda: setattr(
                    self,
                    "_source_catalog",
                    self._loader.load_catalog(
                        source_dir,
                        include_infocards=self.include_infocards_check.isChecked(),
                    ),
                )
            )
        except Exception as exc:
            self._show_error(f"Aktuelle Installation konnte nicht geladen werden:\n{exc}")
            return

        self._paired_catalog = None
        self._target_catalog = None
        self._dll_plans = []
        self._refresh_dll_plan_table()
        self._populate_dll_filter(self._source_catalog)
        self._refresh_table()
        self._set_status(f"Aktuelle Installation geladen: {source_dir}")

    def _load_compare_catalog(self) -> None:
        if self._source_catalog is None:
            self._load_source_catalog()
            if self._source_catalog is None:
                return

        target_dir = Path(self.target_edit.text().strip())
        if not target_dir.exists():
            self._show_error(f"Deutscher Referenzpfad existiert nicht:\n{target_dir}")
            return
        try:
            target_catalog: ResourceCatalog | None = None

            def _load() -> None:
                nonlocal target_catalog
                target_catalog = self._loader.load_catalog(
                    target_dir,
                    include_infocards=self.include_infocards_check.isChecked(),
                )

            self._with_busy_cursor(_load)
            assert target_catalog is not None
            self._target_catalog = target_catalog
            self._paired_catalog = pair_catalogs(self._source_catalog, target_catalog)
            self._dll_plans = build_dll_plans(self._source_catalog, self._paired_catalog, target_catalog)
        except Exception as exc:
            self._show_error(f"Vergleich mit deutscher Referenz fehlgeschlagen:\n{exc}")
            return

        self._refresh_dll_plan_table()
        self._populate_dll_filter(self._paired_catalog)
        self._refresh_table()
        self._set_status(f"Vergleich mit deutscher Referenz geladen: {target_dir}")

    def _current_catalog(self) -> ResourceCatalog | None:
        return self._paired_catalog or self._source_catalog

    def _populate_dll_filter(self, catalog: ResourceCatalog | None) -> None:
        current_text = self.dll_combo.currentText()
        self.dll_combo.blockSignals(True)
        self.dll_combo.clear()
        self.dll_combo.addItem("alle")
        if catalog is not None:
            for dll_name in sorted({unit.source.dll_name for unit in catalog.units}):
                self.dll_combo.addItem(dll_name)
        index = max(0, self.dll_combo.findText(current_text))
        self.dll_combo.setCurrentIndex(index)
        self.dll_combo.blockSignals(False)

    def _refresh_table(self) -> None:
        catalog = self._current_catalog()
        if catalog is None:
            self.table.setRowCount(0)
            self.summary_label.setText("Noch kein Katalog geladen.")
            self._refresh_dll_plan_table()
            self.source_preview.clear()
            self.target_preview.clear()
            self.detail_label.setText("Keine Auswahl.")
            return

        units = list(catalog.units)
        kind_value = self.kind_combo.currentText()
        dll_value = self.dll_combo.currentText()
        search_value = self.search_edit.text().strip().lower()

        if kind_value != "alle":
            selected_kind = ResourceKind(kind_value)
            units = [unit for unit in units if unit.kind == selected_kind]
        if dll_value != "alle":
            units = [unit for unit in units if unit.source.dll_name == dll_value]
        status_value = self.status_combo.currentText()
        if status_value != "alle":
            selected_status = RelocalizationStatus(status_value)
            units = [unit for unit in units if unit.status == selected_status]
        if self.target_only_check.isChecked():
            units = [unit for unit in units if unit.target is not None]
        if self.changed_only_check.isChecked():
            units = [unit for unit in units if unit.is_changed]
        if search_value:
            units = [
                unit
                for unit in units
                if search_value in unit.source_text.lower() or search_value in unit.target_text.lower()
            ]

        self._visible_units = units
        self.table.setRowCount(len(units))
        for row, unit in enumerate(units):
            preview = " ".join(unit.source_text.split())
            values = [
                str(unit.kind),
                unit.source.dll_name,
                str(unit.source.local_id),
                str(unit.source.global_id),
                str(unit.status),
                "ja" if unit.is_changed else "nein",
                preview[:120],
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.UserRole, row)
                self.table.setItem(row, column, item)

        self.table.resizeColumnsToContents()
        self._update_summary(catalog, units)
        if units:
            self.table.selectRow(0)
        else:
            self.source_preview.clear()
            self.target_preview.clear()
            self.detail_label.setText("Keine Auswahl.")

    def _refresh_dll_plan_table(self) -> None:
        self.dll_plan_table.setRowCount(len(self._dll_plans))
        for row, plan in enumerate(self._dll_plans):
            action = (
                "DE-DLL komplett kopieren"
                if plan.strategy == DllStrategy.FULL_REPLACE_SAFE
                else "nur passende Eintraege patchen"
                if plan.strategy == DllStrategy.PATCH_REQUIRED
                else "nicht automatisch ersetzen"
            )
            values = [
                plan.dll_name,
                plan.strategy_label,
                f"{plan.source_strings}/{plan.target_strings}",
                f"{plan.source_infocards}/{plan.target_infocards}",
                str(plan.auto_relocalize_units),
                str(plan.mod_only_units),
                str(plan.matched_units),
                action,
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                self.dll_plan_table.setItem(row, column, item)
        self.dll_plan_table.resizeColumnsToContents()

    def _sync_dll_filter_from_plan_table(self) -> None:
        row = self.dll_plan_table.currentRow()
        if row < 0 or row >= len(self._dll_plans):
            return
        dll_name = self._dll_plans[row].dll_name
        index = self.dll_combo.findText(dll_name)
        if index >= 0:
            self.dll_combo.setCurrentIndex(index)

    def _update_summary(self, catalog: ResourceCatalog, visible_units: list[TranslationUnit]) -> None:
        total = len(catalog.units)
        visible = len(visible_units)
        strings = summarize_catalog(catalog, ResourceKind.STRING)
        infocards = summarize_catalog(catalog, ResourceKind.INFOCARD)
        self.summary_label.setText(
            " | ".join(
                [
                    f"Sichtbar {visible}/{total}",
                    f"DLL komplett ersetzbar {sum(1 for plan in self._dll_plans if plan.strategy == DllStrategy.FULL_REPLACE_SAFE)}",
                    f"DLL teilweise {sum(1 for plan in self._dll_plans if plan.strategy == DllStrategy.PATCH_REQUIRED)}",
                    f"DLL unsicher {sum(1 for plan in self._dll_plans if plan.strategy == DllStrategy.NOT_SAFE)}",
                    f"Strings auto {strings.auto_relocalize}, schon DE {strings.already_localized}, mod-only {strings.mod_only}",
                    f"Infocards auto {infocards.auto_relocalize}, schon DE {infocards.already_localized}, mod-only {infocards.mod_only}",
                ]
            )
        )

    def _update_preview(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._visible_units):
            self.detail_label.setText("Keine Auswahl.")
            self.source_preview.clear()
            self.target_preview.clear()
            return

        unit = self._visible_units[row]
        self.detail_label.setText(
            " | ".join(
                [
                    f"Kind: {unit.kind}",
                    f"Status: {unit.status}",
                    f"DLL: {unit.source.dll_name}",
                    f"Local ID: {unit.source.local_id}",
                    f"Global ID: {unit.source.global_id}",
                    f"DE Referenz: {'ja' if unit.target else 'nein'}",
                    f"Geaendert: {'ja' if unit.is_changed else 'nein'}",
                ]
            )
        )
        self.source_preview.setPlainText(unit.source_text)
        self.target_preview.setPlainText(unit.target_text)

    def _export_visible_json(self) -> None:
        catalog = self._current_catalog()
        if catalog is None:
            self._show_error("Bitte zuerst eine Installation laden.")
            return
        output_path, _selected = QFileDialog.getSaveFileName(
            self,
            "Sichtbaren Datensatz exportieren",
            str(Path.cwd() / "build" / "translator-export.json"),
            "JSON Files (*.json)",
        )
        if not output_path:
            return

        export_catalog = ResourceCatalog(
            install_dir=catalog.install_dir,
            freelancer_ini=catalog.freelancer_ini,
            units=tuple(self._visible_units),
        )
        try:
            export_catalog_json(export_catalog, Path(output_path))
        except Exception as exc:
            self._show_error(f"JSON-Export fehlgeschlagen:\n{exc}")
            return
        self._set_status(f"{len(self._visible_units)} Eintraege exportiert: {output_path}")

    def _export_auto_json(self) -> None:
        catalog = self._current_catalog()
        if catalog is None:
            self._show_error("Bitte zuerst eine Installation laden.")
            return
        output_path, _selected = QFileDialog.getSaveFileName(
            self,
            "Auto-DE Datensatz exportieren",
            str(Path.cwd() / "build" / "auto-relocalize-de.json"),
            "JSON Files (*.json)",
        )
        if not output_path:
            return
        try:
            export_catalog_json(
                catalog,
                Path(output_path),
                auto_relocalize_only=True,
            )
        except Exception as exc:
            self._show_error(f"Auto-DE Export fehlgeschlagen:\n{exc}")
            return
        auto_count = sum(1 for unit in catalog.units if unit.status == RelocalizationStatus.AUTO_RELOCALIZE)
        self._set_status(f"{auto_count} Auto-DE Eintraege exportiert: {output_path}")

    def _apply_german_to_install(self) -> None:
        catalog = self._paired_catalog
        if catalog is None:
            self._show_error("Bitte zuerst mit der deutschen Referenz vergleichen.")
            return
        if not self._writer.has_toolchain():
            self._show_error(
                "Keine Resource-Toolchain gefunden.\nBitte zuerst 'Toolchain installieren' ausfuehren."
            )
            return
        units = [unit for unit in self._visible_units if unit.status == RelocalizationStatus.AUTO_RELOCALIZE]
        if not units:
            self._show_error("Keine automatisch rueckuebersetzbaren Eintraege in der aktuellen Ansicht.")
            return

        apply_count = len(units)
        reply = QMessageBox.question(
            self,
            "Deutsch anwenden",
            (
                f"Es werden {apply_count} Eintraege in der aktuellen Installation durch deutsche Texte ersetzt.\n"
                "Vorher wird automatisch ein Backup der betroffenen DLLs angelegt.\n\n"
                "Fortfahren?"
            ),
        )
        if reply != QMessageBox.Yes:
            return

        try:
            report: ApplyReport | None = None

            def _apply() -> None:
                nonlocal report
                report = self._writer.apply_german_relocalization(
                    catalog,
                    units=units,
                    dll_plans=self._dll_plans,
                )

            self._with_busy_cursor(_apply)
            assert report is not None
        except Exception as exc:
            self._show_error(f"Rueckuebersetzung fehlgeschlagen:\n{exc}")
            return

        QMessageBox.information(
            self,
            "Deutsch anwenden",
            (
                f"Rueckuebersetzung abgeschlossen.\n\n"
                f"Ersetzte Eintraege: {report.replaced_units}\n"
                f"Geschriebene DLLs: {len(report.written_files)}\n"
                f"Backup: {report.backup_dir}"
            ),
        )
        self._set_status(
            f"Deutsch angewendet: {report.replaced_units} Eintraege, Backup unter {report.backup_dir}"
        )
        self._load_source_catalog()
        self._load_compare_catalog()

    def _install_toolchain(self) -> None:
        try:
            script_path = self._writer.launch_toolchain_installer()
        except Exception as exc:
            self._show_error(f"Toolchain-Installer konnte nicht gestartet werden:\n{exc}")
            return
        QMessageBox.information(
            self,
            "Toolchain installieren",
            (
                "Der Toolchain-Installer wurde gestartet.\n\n"
                f"Skript: {script_path}\n"
                "Nach der Installation die App neu starten oder erneut vergleichen."
            ),
        )
        self._set_status("Toolchain-Installer gestartet.")
        self.toolchain_label.setText("Resource-Toolchain: Installation gestartet")

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

    def _show_error(self, message: str) -> None:
        QMessageBox.critical(self, "FLAtlas Translator", message)
        self._set_status("Vorgang fehlgeschlagen.")

    def _set_status(self, message: str) -> None:
        self.status_bar.showMessage(message, 10000)


def run() -> int:
    app = QApplication.instance() or QApplication([])
    window = TranslatorMainWindow()
    window.show()
    return app.exec()
