"""Reusable dialogs for the FL Lingo UI."""

from __future__ import annotations

from typing import Any, Callable

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .ui_themes import THEMES


class SettingsDialog(QDialog):
    def __init__(self, current_theme: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        current_language = getattr(parent, "_lang", "de") if parent is not None else "de"
        self.setWindowTitle("Einstellungen" if current_language == "de" else "Settings")
        self.selected_theme = current_theme

        layout = QVBoxLayout(self)
        grid = QGridLayout()

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(sorted(THEMES.keys()))
        self.theme_combo.setCurrentText(current_theme if current_theme in THEMES else "light")

        grid.addWidget(QLabel("Theme"), 0, 0)
        grid.addWidget(self.theme_combo, 0, 1)
        layout.addLayout(grid)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _accept(self) -> None:
        self.selected_theme = self.theme_combo.currentText()
        self.accept()


# Available translator providers: (internal_key, display_label)
TRANSLATOR_PROVIDERS = [
    ("google", "Google Translate (deep-translator)"),
]


class TranslatorSettingsDialog(QDialog):
    """Dialog for selecting the translator provider and entering an API key."""

    def __init__(
        self,
        current_provider: str,
        current_api_key: str,
        tr: Any,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._tr = tr
        self.selected_provider = current_provider
        self.selected_api_key = current_api_key

        self.setWindowTitle(tr("dialog.api_key_title"))
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        grid = QGridLayout()

        # Provider dropdown
        grid.addWidget(QLabel(tr("dialog.api_key_provider_label")), 0, 0)
        self.provider_combo = QComboBox()
        for _key, label in TRANSLATOR_PROVIDERS:
            self.provider_combo.addItem(label, _key)
        idx = next(
            (i for i, (k, _) in enumerate(TRANSLATOR_PROVIDERS) if k == current_provider),
            0,
        )
        self.provider_combo.setCurrentIndex(idx)
        grid.addWidget(self.provider_combo, 0, 1)

        # API key
        from PySide6.QtWidgets import QLineEdit

        grid.addWidget(QLabel(tr("dialog.api_key_label")), 1, 0)
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setText(current_api_key)
        grid.addWidget(self.api_key_edit, 1, 1)

        layout.addLayout(grid)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _accept(self) -> None:
        self.selected_provider = self.provider_combo.currentData()
        self.selected_api_key = self.api_key_edit.text().strip()
        self.accept()


class BulkTranslateDialog(QDialog):
    """Modal dialog for bulk auto-translation with pause/resume and progress."""

    def __init__(
        self,
        total_open: int,
        tr: Callable[[str], str],
        translate_fn: Callable[[str, str, str], str],
        source_lang: str,
        target_lang: str,
        units: list[Any],
        save_progress_fn: Callable[[list[Any]], None],
        log_entries: list[tuple[str, str, str]] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._tr = tr
        self._translate_fn = translate_fn
        self._source_lang = source_lang
        self._target_lang = target_lang
        self._units = units
        self._save_progress_fn = save_progress_fn
        self._paused = True
        self._done = 0
        self._current_index = 0
        self._translated_units: list[Any] = []
        self._log_entries: list[tuple[str, str, str]] = list(log_entries) if log_entries else []
        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._translate_next)

        self.setWindowTitle(tr("dialog.bulk_translate_title"))
        self.setMinimumSize(720, 480)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)

        # --- config area ---
        config_row = QHBoxLayout()
        config_row.addWidget(QLabel(tr("dialog.bulk_min_length_label")))
        self.min_length_spin = QSpinBox()
        self.min_length_spin.setRange(0, 10000)
        self.min_length_spin.setValue(50)
        self.min_length_spin.setSuffix(" " + tr("dialog.bulk_chars_suffix"))
        config_row.addWidget(self.min_length_spin)
        config_row.addStretch(1)
        layout.addLayout(config_row)

        info_text = tr("dialog.bulk_info").format(count=total_open)
        self.info_label = QLabel(info_text)
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

        # --- progress ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(total_open)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        self.progress_label = QLabel(tr("dialog.bulk_progress").format(done=0, total=total_open))
        layout.addWidget(self.progress_label)

        # --- result table (old text | new text) ---
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(3)
        self.result_table.setHorizontalHeaderLabels([
            "DLL / ID",
            tr("dialog.bulk_col_source"),
            tr("dialog.bulk_col_target"),
        ])
        self.result_table.horizontalHeader().setStretchLastSection(True)
        self.result_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.result_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.result_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.result_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.result_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.result_table.verticalHeader().setVisible(False)
        layout.addWidget(self.result_table, 1)

        # Restore previous log entries
        for ref, old, new in self._log_entries:
            self._append_table_row(ref, old, new)

        # --- status label (for pause/finish messages) ---
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        # --- buttons ---
        btn_row = QHBoxLayout()
        self.start_button = QPushButton(tr("dialog.bulk_start"))
        self.start_button.clicked.connect(self._on_start)
        self.pause_button = QPushButton(tr("dialog.bulk_pause"))
        self.pause_button.clicked.connect(self._on_pause)
        self.pause_button.setEnabled(False)
        self.close_button = QPushButton(tr("dialog.bulk_close"))
        self.close_button.clicked.connect(self._on_close)
        btn_row.addStretch(1)
        btn_row.addWidget(self.start_button)
        btn_row.addWidget(self.pause_button)
        btn_row.addWidget(self.close_button)
        layout.addLayout(btn_row)

    # --- helpers ---

    def _append_table_row(self, ref: str, source: str, target: str) -> None:
        row = self.result_table.rowCount()
        self.result_table.insertRow(row)
        self.result_table.setItem(row, 0, QTableWidgetItem(ref))
        src_item = QTableWidgetItem(source.replace("\n", " ")[:200])
        src_item.setToolTip(source)
        self.result_table.setItem(row, 1, src_item)
        tgt_item = QTableWidgetItem(target.replace("\n", " ")[:200])
        tgt_item.setToolTip(target)
        self.result_table.setItem(row, 2, tgt_item)
        self.result_table.scrollToBottom()

    @property
    def log_entries(self) -> list[tuple[str, str, str]]:
        """Return accumulated log entries for persistence across reopens."""
        return list(self._log_entries)

    @property
    def filtered_units(self) -> list[Any]:
        min_len = self.min_length_spin.value()
        return [u for u in self._units if len(u.source_text.strip()) >= min_len]

    def _on_start(self) -> None:
        units = self.filtered_units
        if not units:
            self.status_label.setText(self._tr("dialog.bulk_no_entries"))
            return
        self._units_to_process = units
        self._current_index = 0
        self._done = 0
        total = len(units)
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(0)
        self.progress_label.setText(self._tr("dialog.bulk_progress").format(done=0, total=total))
        self.start_button.setEnabled(False)
        self.min_length_spin.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.status_label.setText("")
        self._paused = False
        self._timer.start()

    def _on_pause(self) -> None:
        if self._paused:
            # resume
            self._paused = False
            self.pause_button.setText(self._tr("dialog.bulk_pause"))
            self.status_label.setText("")
            self._timer.start()
        else:
            # pause
            self._paused = True
            self._timer.stop()
            self.pause_button.setText(self._tr("dialog.bulk_resume"))
            self.status_label.setText(self._tr("dialog.bulk_paused"))
            self._save_progress_fn(self._translated_units)
            self.status_label.setText(self._tr("dialog.bulk_saved"))

    def _on_close(self) -> None:
        self._timer.stop()
        if self._translated_units:
            self._save_progress_fn(self._translated_units)
        self.accept()

    def _translate_next(self) -> None:
        if self._paused:
            return
        units = self._units_to_process
        total = len(units)
        if self._current_index >= total:
            self._timer.stop()
            self.pause_button.setEnabled(False)
            self.start_button.setEnabled(False)
            self._save_progress_fn(self._translated_units)
            self.status_label.setText(self._tr("dialog.bulk_finished"))
            return
        unit = units[self._current_index]
        self._current_index += 1
        source_text = unit.source_text
        if not source_text.strip():
            self.progress_bar.setValue(self._current_index)
            self.progress_label.setText(self._tr("dialog.bulk_progress").format(done=self._done, total=total))
            return
        ref = f"{unit.source.dll_name}:{unit.source.local_id}"
        try:
            translated = self._translate_fn(source_text, self._source_lang, self._target_lang)
        except Exception as exc:
            entry = (ref, source_text, f"\u274c {exc}")
            self._log_entries.append(entry)
            self._append_table_row(*entry)
            self.progress_bar.setValue(self._current_index)
            self.progress_label.setText(self._tr("dialog.bulk_progress").format(done=self._done, total=total))
            return
        self._done += 1
        self._translated_units.append((unit, translated))
        entry = (ref, source_text, translated)
        self._log_entries.append(entry)
        self._append_table_row(*entry)
        self.progress_bar.setValue(self._current_index)
        self.progress_label.setText(self._tr("dialog.bulk_progress").format(done=self._done, total=total))

    def closeEvent(self, event) -> None:  # noqa: N802
        self._timer.stop()
        if self._translated_units:
            self._save_progress_fn(self._translated_units)
        super().closeEvent(event)
