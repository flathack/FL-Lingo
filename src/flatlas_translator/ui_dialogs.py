"""Reusable dialogs for the FL Lingo UI."""

from __future__ import annotations

from typing import Any, Callable

import queue
import threading
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QGroupBox,
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


class TranslationRulesDialog(QDialog):
    """Dialog for configuring translation skip/filter rules."""

    def __init__(
        self,
        rules: "TranslationRules",
        tr: Callable[[str], str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        from .translation_rules import TranslationRules as _TR  # noqa: F811
        self._tr = tr
        self.setWindowTitle(tr("rules.dialog_title"))
        self.setMinimumWidth(560)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)

        # --- Skip rules ---
        skip_group = QGroupBox(tr("rules.group_skip"))
        skip_layout = QVBoxLayout(skip_group)

        self.skip_location_check = QCheckBox(tr("rules.skip_location_keywords"))
        self.skip_location_check.setChecked(rules.skip_location_keywords)
        skip_layout.addWidget(self.skip_location_check)

        self.skip_person_check = QCheckBox(tr("rules.skip_person_names"))
        self.skip_person_check.setChecked(rules.skip_person_names)
        skip_layout.addWidget(self.skip_person_check)

        self.skip_symbolic_check = QCheckBox(tr("rules.skip_symbolic_numeric"))
        self.skip_symbolic_check.setChecked(rules.skip_symbolic_numeric)
        skip_layout.addWidget(self.skip_symbolic_check)

        self.skip_ships_check = QCheckBox(tr("rules.skip_ship_names"))
        self.skip_ships_check.setChecked(rules.skip_ship_names)
        skip_layout.addWidget(self.skip_ships_check)

        layout.addWidget(skip_group)

        # --- Term rules ---
        term_group = QGroupBox(tr("rules.group_terms"))
        term_layout = QVBoxLayout(term_group)

        self.skip_single_word_check = QCheckBox(tr("rules.skip_single_word_prose"))
        self.skip_single_word_check.setChecked(rules.skip_single_word_terms_in_prose)
        term_layout.addWidget(self.skip_single_word_check)

        term_grid = QGridLayout()
        term_grid.addWidget(QLabel(tr("rules.term_max_length")), 0, 0)
        self.term_max_spin = QSpinBox()
        self.term_max_spin.setRange(1, 9999)
        self.term_max_spin.setValue(rules.term_candidate_max_length)
        term_grid.addWidget(self.term_max_spin, 0, 1)

        term_grid.addWidget(QLabel(tr("rules.pattern_min_length")), 1, 0)
        self.pattern_min_spin = QSpinBox()
        self.pattern_min_spin.setRange(0, 9999)
        self.pattern_min_spin.setValue(rules.pattern_min_source_length)
        term_grid.addWidget(self.pattern_min_spin, 1, 1)

        term_layout.addLayout(term_grid)
        layout.addWidget(term_group)

        # --- Info (non-configurable rules) ---
        info_group = QGroupBox(tr("rules.group_info"))
        info_layout = QVBoxLayout(info_group)
        info_label = QLabel(tr("rules.info_text"))
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #8b95a7;")
        info_layout.addWidget(info_label)
        layout.addWidget(info_group)

        # --- buttons ---
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.result_rules: _TR | None = None

    def _accept(self) -> None:
        from .translation_rules import TranslationRules
        self.result_rules = TranslationRules(
            skip_location_keywords=self.skip_location_check.isChecked(),
            skip_person_names=self.skip_person_check.isChecked(),
            skip_symbolic_numeric=self.skip_symbolic_check.isChecked(),
            skip_ship_names=self.skip_ships_check.isChecked(),
            skip_single_word_terms_in_prose=self.skip_single_word_check.isChecked(),
            term_candidate_max_length=self.term_max_spin.value(),
            pattern_min_source_length=self.pattern_min_spin.value(),
        )
        self.accept()


class BulkTranslatePanel(QWidget):
    """Embeddable panel for bulk auto-translation with pause/resume and progress."""

    def __init__(
        self,
        tr: Callable[[str], str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._tr = tr
        self._translate_fn: Callable[[str, str, str], str] | None = None
        self._source_lang = ""
        self._target_lang = ""
        self._units: list[Any] = []
        self._save_progress_fn: Callable[[list[Any]], None] | None = None
        self._open_rules_callback: Callable[[], None] | None = None
        self._paused = True
        self._done = 0
        self._current_index = 0
        self._translated_units: list[Any] = []
        self._log_entries: list[tuple[str, str, str]] = []
        self._translate_times: list[float] = []
        self._result_queue: queue.Queue = queue.Queue()
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._worker_thread: threading.Thread | None = None
        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._poll_results)
        self._populated = False

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

        self.info_label = QLabel("")
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

        # --- skip / available info + rules link ---
        self._skip_row = QHBoxLayout()
        self.skip_info_label = QLabel("")
        self.skip_info_label.setStyleSheet("color: #8b95a7;")
        self._skip_row.addWidget(self.skip_info_label)
        self.rules_link = QPushButton(tr("dialog.bulk_open_rules"))
        self.rules_link.setFlat(True)
        self.rules_link.setCursor(Qt.PointingHandCursor)
        self.rules_link.setStyleSheet("color: #3daee9; text-decoration: underline; border: none; padding: 0;")
        self.rules_link.clicked.connect(self._on_rules_clicked)
        self.rules_link.setVisible(False)
        self._skip_row.addWidget(self.rules_link)
        self._skip_row.addStretch(1)
        layout.addLayout(self._skip_row)

        # --- progress ---
        self.bulk_progress_bar = QProgressBar()
        self.bulk_progress_bar.setMinimum(0)
        self.bulk_progress_bar.setMaximum(1)
        self.bulk_progress_bar.setValue(0)
        self.bulk_progress_bar.setTextVisible(True)
        layout.addWidget(self.bulk_progress_bar)

        self.bulk_progress_label = QLabel("")
        layout.addWidget(self.bulk_progress_label)

        self.eta_label = QLabel("")
        self.eta_label.setStyleSheet("color: #8b95a7;")
        layout.addWidget(self.eta_label)

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

        # --- status label (for pause/finish messages) ---
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        # --- buttons ---
        btn_row = QHBoxLayout()
        self.preview_button = QPushButton(tr("dialog.bulk_preview"))
        self.preview_button.clicked.connect(self._on_preview)
        self.start_button = QPushButton(tr("dialog.bulk_start"))
        self.start_button.clicked.connect(self._on_start)
        self.pause_button = QPushButton(tr("dialog.bulk_pause"))
        self.pause_button.clicked.connect(self._on_pause)
        self.pause_button.setEnabled(False)
        btn_row.addStretch(1)
        btn_row.addWidget(self.preview_button)
        btn_row.addWidget(self.start_button)
        btn_row.addWidget(self.pause_button)
        layout.addLayout(btn_row)

        # Disable actions until populated
        self.preview_button.setEnabled(False)
        self.start_button.setEnabled(False)

    def populate(
        self,
        total_open: int,
        translate_fn: Callable[[str, str, str], str],
        source_lang: str,
        target_lang: str,
        units: list[Any],
        save_progress_fn: Callable[[list[Any]], None],
        log_entries: list[tuple[str, str, str]] | None = None,
        skipped_count: int = 0,
        open_rules_callback: Callable[[], None] | None = None,
    ) -> None:
        """Load new data into the panel and reset state."""
        self.stop_and_save()
        self._translate_fn = translate_fn
        self._source_lang = source_lang
        self._target_lang = target_lang
        self._units = units
        self._save_progress_fn = save_progress_fn
        self._open_rules_callback = open_rules_callback
        self._paused = True
        self._done = 0
        self._current_index = 0
        self._translated_units = []
        self._log_entries = list(log_entries) if log_entries else []
        self._translate_times = []

        self.info_label.setText(self._tr("dialog.bulk_info").format(count=total_open))

        skip_info_parts: list[str] = []
        if skipped_count > 0:
            skip_info_parts.append(self._tr("dialog.bulk_skipped").format(skipped=skipped_count))
        skip_info_parts.append(self._tr("dialog.bulk_available").format(available=total_open))
        self.skip_info_label.setText("  ".join(skip_info_parts))
        self.rules_link.setVisible(open_rules_callback is not None)

        self.bulk_progress_bar.setMaximum(max(total_open, 1))
        self.bulk_progress_bar.setValue(0)
        self.bulk_progress_label.setText(self._tr("dialog.bulk_progress").format(done=0, total=total_open))
        self.eta_label.setText("")
        self.status_label.setText("")

        self.result_table.setRowCount(0)
        for ref, old, new in self._log_entries:
            self._append_table_row(ref, old, new)

        self.preview_button.setEnabled(True)
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.min_length_spin.setEnabled(True)
        self._populated = True

    def _on_rules_clicked(self) -> None:
        if self._open_rules_callback is not None:
            self._open_rules_callback()

    # --- helpers ---

    def _insert_table_row(self, ref: str, source: str, target: str) -> None:
        """Insert a row without scrolling (caller handles scroll after batch)."""
        row = self.result_table.rowCount()
        self.result_table.insertRow(row)
        self.result_table.setItem(row, 0, QTableWidgetItem(ref))
        src_item = QTableWidgetItem(source.replace("\n", " ")[:200])
        src_item.setToolTip(source)
        self.result_table.setItem(row, 1, src_item)
        tgt_item = QTableWidgetItem(target.replace("\n", " ")[:200])
        tgt_item.setToolTip(target)
        self.result_table.setItem(row, 2, tgt_item)

    def _append_table_row(self, ref: str, source: str, target: str) -> None:
        """Insert a row and scroll to bottom (used by populate/preview)."""
        self._insert_table_row(ref, source, target)
        self.result_table.scrollToBottom()

    @property
    def log_entries(self) -> list[tuple[str, str, str]]:
        """Return accumulated log entries for persistence across reopens."""
        return list(self._log_entries)

    @property
    def filtered_units(self) -> list[Any]:
        min_len = self.min_length_spin.value()
        return [u for u in self._units if len(u.source_text.strip()) >= min_len]

    def _on_preview(self) -> None:
        """Show all entries that would be translated — runs in a background thread."""
        units = self.filtered_units
        min_len = self.min_length_spin.value()
        total = len(units)
        self.result_table.setRowCount(0)
        self.bulk_progress_bar.setMaximum(max(total, 1))
        self.bulk_progress_bar.setValue(0)
        self.eta_label.setText("")
        self.preview_button.setEnabled(False)
        self.start_button.setEnabled(False)

        self._stop_event.clear()
        preview_queue: queue.Queue = queue.Queue()

        def _build_preview() -> None:
            for i, unit in enumerate(units):
                if self._stop_event.is_set():
                    return
                ref = f"{unit.source.dll_name}:{unit.source.local_id}"
                preview_queue.put((i, ref, unit.source_text))
            preview_queue.put(None)  # sentinel

        thread = threading.Thread(target=_build_preview, daemon=True)
        thread.start()

        def _poll_preview() -> None:
            batch = 0
            while batch < 200:
                try:
                    item = preview_queue.get_nowait()
                except queue.Empty:
                    break
                if item is None:
                    preview_timer.stop()
                    self.result_table.setUpdatesEnabled(True)
                    self.result_table.scrollToBottom()
                    self.info_label.setText(
                        self._tr("dialog.bulk_preview_info").format(count=total, min_len=min_len)
                    )
                    self.status_label.setText(
                        self._tr("dialog.bulk_preview_info").format(count=total, min_len=min_len)
                    )
                    self.preview_button.setEnabled(True)
                    self.start_button.setEnabled(True)
                    return
                i, ref, source_text = item
                row = self.result_table.rowCount()
                self.result_table.insertRow(row)
                self.result_table.setItem(row, 0, QTableWidgetItem(ref))
                src_item = QTableWidgetItem(source_text.replace("\n", " ")[:200])
                src_item.setToolTip(source_text)
                self.result_table.setItem(row, 1, src_item)
                self.result_table.setItem(row, 2, QTableWidgetItem(""))
                self.bulk_progress_bar.setValue(i + 1)
                batch += 1

        self.result_table.setUpdatesEnabled(False)
        preview_timer = QTimer(self)
        preview_timer.setInterval(30)
        preview_timer.timeout.connect(_poll_preview)
        self._preview_timer = preview_timer
        preview_timer.start()

    def _on_start(self) -> None:
        units = self.filtered_units
        if not units:
            self.status_label.setText(self._tr("dialog.bulk_no_entries"))
            return
        self._units_to_process = units
        self._current_index = 0
        self._done = 0
        self._translate_times = []
        total = len(units)
        self.bulk_progress_bar.setMaximum(total)
        self.bulk_progress_bar.setValue(0)
        self.bulk_progress_label.setText(self._tr("dialog.bulk_progress").format(done=0, total=total))
        self.eta_label.setText("")
        self.start_button.setEnabled(False)
        self.preview_button.setEnabled(False)
        self.min_length_spin.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.status_label.setText("")
        self._paused = False
        self._stop_event.clear()
        self._pause_event.clear()
        self._worker_thread = threading.Thread(target=self._translate_worker, daemon=True)
        self._worker_thread.start()
        self._timer.start()

    _CONCURRENT_REQUESTS = 3  # parallel API requests (balance speed vs. rate-limit risk)

    def _translate_worker(self) -> None:
        """Background thread: translates units in parallel batches."""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from .translator_service import translate_text_batch

        units = self._units_to_process
        batch_char_limit = 4500

        # --- Phase 1: pre-build all batches, emit skips immediately ---
        all_batches: list[tuple[list, list[str], list[int]]] = []
        idx = 0
        while idx < len(units):
            batch_units: list = []
            batch_texts: list[str] = []
            batch_indices: list[int] = []
            batch_chars = 0
            while idx < len(units):
                unit = units[idx]
                source_text = unit.source_text
                if not source_text.strip():
                    ref = f"{unit.source.dll_name}:{unit.source.local_id}"
                    self._result_queue.put(("skip", idx, unit, ref, "", "", 0.0))
                    idx += 1
                    continue
                text_len = len(source_text)
                if batch_chars + text_len > batch_char_limit and batch_units:
                    break
                batch_units.append(unit)
                batch_texts.append(source_text)
                batch_indices.append(idx)
                batch_chars += text_len
                idx += 1
            if batch_texts:
                all_batches.append((batch_units, batch_texts, batch_indices))

        # --- Phase 2: translate batches with parallelism ---
        bi = 0
        n_workers = self._CONCURRENT_REQUESTS
        with ThreadPoolExecutor(max_workers=n_workers) as pool:
            while bi < len(all_batches):
                if self._stop_event.is_set():
                    return
                # Handle pause
                while self._pause_event.is_set():
                    if self._stop_event.is_set():
                        return
                    time.sleep(0.1)

                # Submit a chunk of concurrent batches
                chunk_end = min(bi + n_workers, len(all_batches))
                t0 = time.monotonic()
                futures = {}
                for ci in range(bi, chunk_end):
                    b_units, b_texts, b_indices = all_batches[ci]
                    fut = pool.submit(
                        translate_text_batch, b_texts,
                        self._source_lang, self._target_lang,
                    )
                    futures[fut] = (b_units, b_texts, b_indices)

                total_texts_in_chunk = sum(len(v[1]) for v in futures.values())

                for fut in as_completed(futures):
                    b_units, b_texts, b_indices = futures[fut]
                    elapsed = time.monotonic() - t0
                    per_unit = elapsed / max(total_texts_in_chunk, 1)
                    try:
                        translated_list = fut.result()
                        for j, (b_unit, src, result) in enumerate(
                            zip(b_units, b_texts, translated_list)
                        ):
                            ref = f"{b_unit.source.dll_name}:{b_unit.source.local_id}"
                            if isinstance(result, Exception):
                                self._result_queue.put(
                                    ("error", b_indices[j], b_unit, ref, src, str(result), per_unit)
                                )
                            else:
                                self._result_queue.put(
                                    ("ok", b_indices[j], b_unit, ref, src, result, per_unit)
                                )
                    except Exception as exc:
                        for j, (b_unit, src) in enumerate(zip(b_units, b_texts)):
                            ref = f"{b_unit.source.dll_name}:{b_unit.source.local_id}"
                            self._result_queue.put(
                                ("error", b_indices[j], b_unit, ref, src, str(exc), per_unit)
                            )

                bi = chunk_end

        self._result_queue.put(("done", 0, None, "", "", "", 0.0))

    _POLL_MAX_PER_TICK = 20  # max results to process per timer tick

    def _poll_results(self) -> None:
        """Main-thread timer: drain result queue and update UI."""
        if not hasattr(self, "_units_to_process"):
            return
        total = len(self._units_to_process)
        processed = 0
        table = self.result_table
        table.setUpdatesEnabled(False)
        try:
            while processed < self._POLL_MAX_PER_TICK:
                try:
                    item = self._result_queue.get_nowait()
                except queue.Empty:
                    break
                status, idx, unit, ref, source_text, result_text, elapsed = item
                if status == "done":
                    table.setUpdatesEnabled(True)
                    table.scrollToBottom()
                    self._timer.stop()
                    self.pause_button.setEnabled(False)
                    self.start_button.setEnabled(False)
                    self._save_progress_fn(self._translated_units)
                    self.status_label.setText(self._tr("dialog.bulk_finished"))
                    return
                self._current_index = idx + 1
                if status == "skip":
                    continue
                processed += 1
                self._translate_times.append(elapsed)
                if status == "ok":
                    self._done += 1
                    self._translated_units.append((unit, result_text))
                    entry = (ref, source_text, result_text)
                else:
                    entry = (ref, source_text, f"\u274c {result_text}")
                self._log_entries.append(entry)
                self._insert_table_row(*entry)
        finally:
            table.setUpdatesEnabled(True)
        if processed > 0:
            table.scrollToBottom()
            self.bulk_progress_bar.setValue(self._current_index)
            self.bulk_progress_label.setText(self._tr("dialog.bulk_progress").format(done=self._done, total=total))
            self._update_eta()

    def _on_pause(self) -> None:
        if self._paused:
            # resume
            self._paused = False
            self._pause_event.clear()
            self.pause_button.setText(self._tr("dialog.bulk_pause"))
            self.status_label.setText("")
            self._timer.start()
        else:
            # pause
            self._paused = True
            self._pause_event.set()
            self._timer.stop()
            # Drain any remaining items from queue before saving
            self._poll_results()
            self.pause_button.setText(self._tr("dialog.bulk_resume"))
            self.status_label.setText(self._tr("dialog.bulk_paused"))
            self._save_progress_fn(self._translated_units)
            self.status_label.setText(self._tr("dialog.bulk_saved"))

    def stop_and_save(self) -> None:
        """Stop any running translation and save progress."""
        self._stop_translation()
        if self._translated_units and self._save_progress_fn is not None:
            self._save_progress_fn(self._translated_units)

    def _stop_translation(self) -> None:
        """Signal worker thread to stop and wait for it."""
        self._stop_event.set()
        self._pause_event.clear()
        self._timer.stop()
        if hasattr(self, "_preview_timer"):
            self._preview_timer.stop()
        if self._worker_thread is not None and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2.0)
            self._worker_thread = None

    def _format_eta(self, remaining_seconds: float) -> str:
        """Format remaining seconds into a human-readable string."""
        remaining = int(remaining_seconds)
        if remaining < 60:
            return self._tr("dialog.bulk_eta_seconds").format(seconds=remaining)
        minutes, secs = divmod(remaining, 60)
        if minutes < 60:
            return self._tr("dialog.bulk_eta_minutes").format(minutes=minutes, seconds=secs)
        hours, minutes = divmod(minutes, 60)
        return self._tr("dialog.bulk_eta_hours").format(hours=hours, minutes=minutes)

    def _update_eta(self) -> None:
        """Calculate and display estimated time remaining."""
        if not self._translate_times or not hasattr(self, "_units_to_process"):
            self.eta_label.setText("")
            return
        avg_time = sum(self._translate_times) / len(self._translate_times)
        remaining = len(self._units_to_process) - self._current_index
        eta_seconds = avg_time * remaining
        self.eta_label.setText(self._format_eta(eta_seconds))


