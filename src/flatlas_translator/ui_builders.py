"""UI builder mixin for FL Lingo main window."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction
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
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QStyle,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .localization import LANGUAGE_OPTIONS
from .ui_widgets import CircularProgressChart, SegmentedProgressBar


class UIBuildMixin:
    def _setup_ui(self) -> None:
        self._refresh_window_title()
        icon = self._resolve_app_icon()
        if icon is not None:
            self.setWindowIcon(icon)
            app = QApplication.instance()
            if app is not None:
                app.setWindowIcon(icon)
        self.resize(1040, 720)
        self._apply_theme()
        self._setup_menu_bar()

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        self.global_progress_bar = QProgressBar()
        self.global_progress_bar.setMinimum(0)
        self.global_progress_bar.setMaximum(0)
        self.global_progress_bar.setTextVisible(False)
        self.global_progress_bar.setFixedHeight(4)
        self.global_progress_bar.setVisible(False)
        layout.addWidget(self.global_progress_bar)

        layout.addWidget(self._build_main_navigation(), 1)
        layout.addWidget(self._build_footer())

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self._update_action_state()
        self._set_status(self._tr("status.start"))
        QTimer.singleShot(1200, self._startup_update_check)

    def _setup_menu_bar(self) -> None:
        menu = self.menuBar()
        if not sys.platform.startswith("darwin"):
            menu.setNativeMenuBar(False)
        windows_only = self._writer.is_windows()

        file_menu = menu.addMenu(self._tr("menu.file"))
        view_menu = menu.addMenu(self._tr("menu.view"))
        settings_menu = menu.addMenu(self._tr("menu.settings"))
        language_menu = menu.addMenu(self._tr("menu.language"))
        help_menu = menu.addMenu(self._tr("menu.help"))

        act_load_source = QAction(self._tr("btn.load_source"), self)
        act_load_source.triggered.connect(self._load_source_catalog)
        file_menu.addAction(act_load_source)

        act_compare = QAction(self._tr("btn.compare"), self)
        act_compare.triggered.connect(self._load_compare_catalog)
        file_menu.addAction(act_compare)

        file_menu.addSeparator()

        act_project_load = QAction(self._tr("menuitem.project_load"), self)
        act_project_load.triggered.connect(self._load_project_file)
        file_menu.addAction(act_project_load)

        act_project_new = QAction(self._tr("menuitem.project_new"), self)
        act_project_new.triggered.connect(self._new_project_file)
        file_menu.addAction(act_project_new)

        act_project_rebuild = QAction(self._tr("menuitem.project_rebuild"), self)
        act_project_rebuild.triggered.connect(self._rebuild_project_file)
        file_menu.addAction(act_project_rebuild)

        act_project_save = QAction(self._tr("menuitem.project_save"), self)
        act_project_save.triggered.connect(self._save_project_file)
        file_menu.addAction(act_project_save)

        act_project_save_as = QAction(self._tr("menuitem.project_save_as"), self)
        act_project_save_as.triggered.connect(self._save_project_file_as)
        file_menu.addAction(act_project_save_as)

        act_restore_backup = QAction(self._tr("menuitem.restore_backup"), self)
        act_restore_backup.triggered.connect(self._restore_backup)
        file_menu.addAction(act_restore_backup)

        act_file_assoc = QAction(self._tr("menuitem.file_assoc"), self)
        act_file_assoc.triggered.connect(self._install_file_association)
        act_file_assoc.setEnabled(windows_only)
        file_menu.addAction(act_file_assoc)

        act_export_visible = QAction(self._tr("btn.export_visible"), self)
        act_export_visible.triggered.connect(self._export_visible_json)
        file_menu.addAction(act_export_visible)

        act_export_mod_only = QAction(self._tr("btn.export_mod_only"), self)
        act_export_mod_only.triggered.connect(self._export_mod_only_exchange)
        file_menu.addAction(act_export_mod_only)

        act_export_long_open = QAction(self._tr("btn.export_long_open"), self)
        act_export_long_open.triggered.connect(self._export_long_open_exchange)
        file_menu.addAction(act_export_long_open)

        act_export_all_translated = QAction(self._tr("btn.export_all_translated"), self)
        act_export_all_translated.triggered.connect(self._export_all_translated)
        file_menu.addAction(act_export_all_translated)

        act_import_exchange = QAction(self._tr("btn.import_exchange"), self)
        act_import_exchange.triggered.connect(self._import_translation_exchange)
        file_menu.addAction(act_import_exchange)

        act_copy_audio = QAction(self._tr("menuitem.copy_audio"), self)
        act_copy_audio.triggered.connect(self._copy_reference_audio_files)
        file_menu.addAction(act_copy_audio)

        act_merge_utf = QAction(self._tr("menuitem.merge_utf_audio"), self)
        act_merge_utf.triggered.connect(self._merge_utf_audio_files)
        file_menu.addAction(act_merge_utf)

        act_assemble_patch = QAction(self._tr("menuitem.assemble_patch"), self)
        act_assemble_patch.triggered.connect(self._assemble_patch_bundle)
        file_menu.addAction(act_assemble_patch)

        file_menu.addSeparator()
        act_apply = QAction(self._tr("btn.apply_target"), self)
        act_apply.triggered.connect(self._apply_target_to_install)
        file_menu.addAction(act_apply)

        act_focus_dll = QAction(self._tr("menuitem.focus_dll"), self)
        act_focus_dll.triggered.connect(self._focus_dll_tab)
        view_menu.addAction(act_focus_dll)

        act_focus_units = QAction(self._tr("menuitem.focus_units"), self)
        act_focus_units.triggered.connect(self._focus_editor_tab)
        view_menu.addAction(act_focus_units)

        act_settings = QAction(self._tr("menuitem.appearance"), self)
        act_settings.triggered.connect(self._open_settings_dialog)
        settings_menu.addAction(act_settings)

        act_open_terminology = QAction(self._tr("menuitem.open_terminology"), self)
        act_open_terminology.triggered.connect(self._open_terminology_file)
        settings_menu.addAction(act_open_terminology)

        act_toolchain = QAction(self._tr("btn.install_toolchain"), self)
        act_toolchain.triggered.connect(self._install_toolchain)
        act_toolchain.setEnabled(windows_only)
        settings_menu.addAction(act_toolchain)

        act_translator_settings = QAction(self._tr("menuitem.translator_settings"), self)
        act_translator_settings.triggered.connect(self._open_translator_settings)
        settings_menu.addAction(act_translator_settings)

        self._language_actions: dict[str, QAction] = {}
        for code, label in LANGUAGE_OPTIONS:
            act_language = QAction(f"{code} - {label}", self)
            act_language.setCheckable(True)
            act_language.setChecked(code == self._lang)
            act_language.triggered.connect(lambda checked, c=code: self._set_language(c))
            language_menu.addAction(act_language)
            self._language_actions[code] = act_language

        act_check_updates = QAction(self._tr("menuitem.check_updates"), self)
        act_check_updates.triggered.connect(self._check_for_updates_manual)
        help_menu.addAction(act_check_updates)

        act_help_contents = QAction(self._tr("menuitem.help_contents"), self)
        act_help_contents.triggered.connect(self._show_help_dialog)
        help_menu.addAction(act_help_contents)

        act_about = QAction(self._tr("menuitem.about"), self)
        act_about.triggered.connect(self._show_about_dialog)
        help_menu.addAction(act_about)

    def _make_help_button(self, help_key: str) -> QPushButton:
        """Create a small help-icon button that shows help text on hover and click."""
        btn = QPushButton()
        style = self.style()
        if style is not None:
            btn.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_TitleBarContextHelpButton))
        btn.setFixedSize(22, 22)
        btn.setStyleSheet(
            "QPushButton { border: none; background: transparent; padding: 0; }"
            "QPushButton:hover { background: #364152; border-radius: 11px; }"
        )
        help_text = self._tr(help_key)
        btn.setToolTip(help_text)
        btn.clicked.connect(lambda: QMessageBox.information(self, self._tr("help.title"), help_text))
        return btn

    def _build_preparation_section(self) -> QGroupBox:
        self.preparation_group = QGroupBox(self._tr("expert.section.preparation"))
        layout = QVBoxLayout(self.preparation_group)

        help_row = QHBoxLayout()
        help_row.addWidget(self._make_help_button("expert.help.preparation"))
        prep_help_label = QLabel(self._tr("expert.help.preparation"))
        prep_help_label.setWordWrap(True)
        prep_help_label.setStyleSheet("color: #8b95a7;")
        help_row.addWidget(prep_help_label, 1)
        layout.addLayout(help_row)

        toolchain_row = QHBoxLayout()
        self.toolchain_button = QPushButton(self._tr("btn.install_toolchain"))
        self.toolchain_button.clicked.connect(self._install_toolchain)
        self.toolchain_button.setEnabled(self._writer.is_windows())
        self.toolchain_button.setToolTip(self._tr("tooltip.toolchain"))
        self.toolchain_label = QLabel("")
        self.toolchain_label.setWordWrap(True)
        toolchain_row.addWidget(self._make_help_button("tooltip.toolchain"))
        toolchain_row.addWidget(self.toolchain_button)
        toolchain_row.addWidget(self.toolchain_label, 1)
        layout.addLayout(toolchain_row)

        grid = QGridLayout()
        self.source_edit = QLineEdit()
        self.target_edit = QLineEdit()
        self.en_ref_edit = QLineEdit()
        self.source_edit.setPlaceholderText(self._default_install_path_hint("source"))
        self.target_edit.setPlaceholderText(self._default_install_path_hint("target"))
        self.en_ref_edit.setPlaceholderText(self._tr("simple.en_vanilla_hint"))
        self.en_ref_edit.setClearButtonEnabled(True)
        self.source_edit.textChanged.connect(lambda value: self._mirror_line_edit_text("simple_source_edit", value))
        self.target_edit.textChanged.connect(lambda value: self._mirror_line_edit_text("simple_target_edit", value))
        self.en_ref_edit.textChanged.connect(lambda value: self._mirror_line_edit_text("simple_en_ref_edit", value))
        self.source_edit.textChanged.connect(self._handle_install_path_change)
        self.target_edit.textChanged.connect(self._handle_install_path_change)

        self.browse_source_button = QPushButton(self._tr("btn.browse"))
        self.browse_source_button.clicked.connect(lambda: self._pick_directory(self.source_edit))
        self.browse_source_button.setToolTip(self._tr("tooltip.browse"))
        self.browse_target_button = QPushButton(self._tr("btn.browse"))
        self.browse_target_button.clicked.connect(lambda: self._pick_directory(self.target_edit))
        self.browse_target_button.setToolTip(self._tr("tooltip.browse"))
        self.browse_en_ref_button = QPushButton(self._tr("btn.browse"))
        self.browse_en_ref_button.clicked.connect(lambda: self._pick_directory(self.en_ref_edit))
        self.browse_en_ref_button.setToolTip(self._tr("tooltip.browse"))

        self.source_lang_label = QLabel(self._tr("label.source_language"))
        self.target_lang_label = QLabel(self._tr("label.target_language"))
        self.source_lang_edit = QComboBox()
        for code, label in LANGUAGE_OPTIONS:
            self.source_lang_edit.addItem(f"{code} - {label}", code)
        self._set_language_combo_value(self.source_lang_edit, self._source_lang_code)
        self.source_lang_edit.currentIndexChanged.connect(lambda _value: self._store_language_pair())
        self.source_lang_edit.setToolTip(self._tr("tooltip.source_language"))
        self.target_lang_edit = QComboBox()
        for code, label in LANGUAGE_OPTIONS:
            self.target_lang_edit.addItem(f"{code} - {label}", code)
        self._set_language_combo_value(self.target_lang_edit, self._target_lang_code)
        self.target_lang_edit.currentIndexChanged.connect(lambda _value: self._store_language_pair())
        self.target_lang_edit.setToolTip(self._tr("tooltip.target_language"))

        self.source_install_label = QLabel(self._tr("label.source_install"))
        self.target_install_label = QLabel(self._tr("label.target_install"))
        self.en_ref_install_label = QLabel(self._tr("label.en_vanilla_install"))

        grid.addWidget(self.source_install_label, 0, 0)
        grid.addWidget(self.source_edit, 0, 1)
        grid.addWidget(self.browse_source_button, 0, 2)
        grid.addWidget(self.source_lang_label, 0, 3)
        grid.addWidget(self.source_lang_edit, 0, 4)

        grid.addWidget(self.target_install_label, 1, 0)
        grid.addWidget(self.target_edit, 1, 1)
        grid.addWidget(self.browse_target_button, 1, 2)
        grid.addWidget(self.target_lang_label, 1, 3)
        grid.addWidget(self.target_lang_edit, 1, 4)

        grid.addWidget(self.en_ref_install_label, 2, 0)
        grid.addWidget(self.en_ref_edit, 2, 1)
        grid.addWidget(self.browse_en_ref_button, 2, 2)

        layout.addLayout(grid)
        self._refresh_toolchain_label()
        return self.preparation_group

    def _build_scan_section(self) -> QGroupBox:
        self.scan_section_group = QGroupBox(self._tr("expert.section.scan"))
        layout = QVBoxLayout(self.scan_section_group)

        help_row = QHBoxLayout()
        help_row.addWidget(self._make_help_button("expert.help.scan"))
        scan_help_label = QLabel(self._tr("expert.help.scan"))
        scan_help_label.setWordWrap(True)
        scan_help_label.setStyleSheet("color: #8b95a7;")
        help_row.addWidget(scan_help_label, 1)
        layout.addLayout(help_row)

        scan_row = QHBoxLayout()
        self.scan_button = QPushButton(self._tr("btn.scan"))
        self.scan_button.setMinimumHeight(40)
        self.scan_button.clicked.connect(self._run_expert_scan)
        self.scan_button.setToolTip(self._tr("tooltip.scan"))
        self.include_infocards_check = QCheckBox(self._tr("check.infocards"))
        self.include_infocards_check.setChecked(True)
        self.include_infocards_check.setToolTip(self._tr("tooltip.include_infocards"))
        scan_row.addWidget(self._make_help_button("tooltip.scan"))
        scan_row.addWidget(self.scan_button)
        scan_row.addWidget(self.include_infocards_check)
        scan_row.addStretch(1)
        layout.addLayout(scan_row)

        self.expert_scan_summary_label = QLabel(self._tr("expert.scan.summary.idle"))
        self.expert_scan_summary_label.setWordWrap(True)
        layout.addWidget(self.expert_scan_summary_label)
        return self.scan_section_group

    def _build_editing_section(self) -> QGroupBox:
        self.editing_section_group = QGroupBox(self._tr("expert.section.editing"))
        layout = QVBoxLayout(self.editing_section_group)

        help_row = QHBoxLayout()
        help_row.addWidget(self._make_help_button("expert.help.editing"))
        editing_help_label = QLabel(self._tr("expert.help.editing"))
        editing_help_label.setWordWrap(True)
        editing_help_label.setStyleSheet("color: #8b95a7;")
        help_row.addWidget(editing_help_label, 1)
        layout.addLayout(help_row)

        btn_row = QHBoxLayout()
        self.editing_link_button = QPushButton(self._tr("expert.editing.link"))
        self.editing_link_button.clicked.connect(self._focus_editor_tab)
        self.editing_link_button.setToolTip(self._tr("tooltip.editing_link"))
        btn_row.addWidget(self._make_help_button("tooltip.editing_link"))
        btn_row.addWidget(self.editing_link_button)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        self.editing_section_group.setVisible(False)
        return self.editing_section_group

    def _build_extras_section(self) -> QGroupBox:
        self.extras_section_group = QGroupBox(self._tr("expert.section.extras"))
        layout = QVBoxLayout(self.extras_section_group)

        help_row = QHBoxLayout()
        help_row.addWidget(self._make_help_button("expert.help.extras"))
        extras_help_label = QLabel(self._tr("expert.help.extras"))
        extras_help_label.setWordWrap(True)
        extras_help_label.setStyleSheet("color: #8b95a7;")
        help_row.addWidget(extras_help_label, 1)
        layout.addLayout(help_row)

        btn_row = QHBoxLayout()
        self.export_mod_only_button = QPushButton(self._tr("btn.export_mod_only"))
        self.export_mod_only_button.clicked.connect(self._export_mod_only_exchange)
        self.export_mod_only_button.setToolTip(self._tr("tooltip.export_mod_only"))
        self.export_long_open_button = QPushButton(self._tr("btn.export_long_open"))
        self.export_long_open_button.clicked.connect(self._export_long_open_exchange)
        self.export_long_open_button.setToolTip(self._tr("tooltip.export_long_open"))
        self.import_exchange_button = QPushButton(self._tr("btn.import_exchange"))
        self.import_exchange_button.clicked.connect(self._import_translation_exchange)
        self.import_exchange_button.setToolTip(self._tr("tooltip.import_exchange"))
        self.remove_imports_button = QPushButton(self._tr("expert.extras.remove_imports"))
        self.remove_imports_button.clicked.connect(self._remove_imported_translations)
        self.remove_imports_button.setToolTip(self._tr("tooltip.remove_imports"))
        self.export_all_translated_button = QPushButton(self._tr("btn.export_all_translated"))
        self.export_all_translated_button.clicked.connect(self._export_all_translated)
        self.export_all_translated_button.setToolTip(self._tr("tooltip.export_all_translated"))
        self.translate_all_open_button = QPushButton(self._tr("btn.translate_all_open"))
        self.translate_all_open_button.clicked.connect(self._translate_all_open_entries)
        self.translate_all_open_button.setToolTip(self._tr("tooltip.translate_all_open"))

        btn_row.addWidget(self._make_help_button("tooltip.export_mod_only"))
        btn_row.addWidget(self.export_mod_only_button)
        btn_row.addWidget(self._make_help_button("tooltip.export_long_open"))
        btn_row.addWidget(self.export_long_open_button)
        btn_row.addWidget(self._make_help_button("tooltip.import_exchange"))
        btn_row.addWidget(self.import_exchange_button)
        btn_row.addWidget(self._make_help_button("tooltip.remove_imports"))
        btn_row.addWidget(self.remove_imports_button)
        btn_row.addWidget(self._make_help_button("tooltip.export_all_translated"))
        btn_row.addWidget(self.export_all_translated_button)
        btn_row.addWidget(self._make_help_button("tooltip.translate_all_open"))
        btn_row.addWidget(self.translate_all_open_button)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        self.import_count_label = QLabel(self._tr("expert.extras.import_count").format(count=0))
        self.import_count_label.setWordWrap(True)
        layout.addWidget(self.import_count_label)
        return self.extras_section_group

    def _build_translate_section(self) -> QGroupBox:
        self.translate_section_group = QGroupBox(self._tr("expert.section.translate"))
        layout = QVBoxLayout(self.translate_section_group)

        help_row = QHBoxLayout()
        help_row.addWidget(self._make_help_button("expert.help.translate"))
        translate_help_label = QLabel(self._tr("expert.help.translate"))
        translate_help_label.setWordWrap(True)
        translate_help_label.setStyleSheet("color: #8b95a7;")
        help_row.addWidget(translate_help_label, 1)
        layout.addLayout(help_row)

        btn_row = QHBoxLayout()
        self.apply_button = QPushButton(self._tr("btn.translate_text"))
        self.apply_button.clicked.connect(self._apply_target_to_install)
        self.apply_button.setToolTip(self._tr("tooltip.translate_text"))
        self.copy_audio_button = QPushButton(self._tr("btn.copy_audio"))
        self.copy_audio_button.clicked.connect(self._copy_reference_audio_files)
        self.copy_audio_button.setToolTip(self._tr("tooltip.copy_audio"))
        self.merge_utf_button = QPushButton(self._tr("btn.merge_utf_audio"))
        self.merge_utf_button.clicked.connect(self._merge_utf_audio_files)
        self.merge_utf_button.setToolTip(self._tr("tooltip.merge_utf"))

        btn_row.addWidget(self._make_help_button("tooltip.translate_text"))
        btn_row.addWidget(self.apply_button)
        btn_row.addWidget(self._make_help_button("tooltip.copy_audio"))
        btn_row.addWidget(self.copy_audio_button)
        btn_row.addWidget(self._make_help_button("tooltip.merge_utf"))
        btn_row.addWidget(self.merge_utf_button)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        self.translate_all_button = QPushButton(self._tr("btn.translate_all"))
        self.translate_all_button.clicked.connect(self._translate_all)
        self.translate_all_button.setToolTip(self._tr("tooltip.translate_all"))
        self.translate_all_button.setMinimumHeight(48)
        self.translate_all_button.setStyleSheet(
            "QPushButton {"
            " background-color: #20c05c;"
            " color: #ffffff;"
            " font-size: 18px;"
            " font-weight: 700;"
            " border: 2px solid #83ffb0;"
            " border-radius: 10px;"
            " padding: 10px 20px;"
            "}"
            "QPushButton:hover {"
            " background-color: #28d267;"
            " border-color: #b8ffd0;"
            "}"
            "QPushButton:pressed {"
            " background-color: #179949;"
            "}"
            "QPushButton:disabled {"
            " background-color: #6a7a70;"
            " color: #d7d7d7;"
            " border-color: #89958d;"
            "}"
        )
        layout.addWidget(self.translate_all_button)

        # --- terminology checkbox ---
        term_row = QHBoxLayout()
        term_row.addWidget(self._make_help_button("tooltip.include_terminology"))
        self.include_terminology_check = QCheckBox(self._tr("check.include_terminology"))
        self.include_terminology_check.setChecked(True)
        self.include_terminology_check.setToolTip(self._tr("tooltip.include_terminology"))
        term_row.addWidget(self.include_terminology_check)
        term_row.addStretch(1)
        layout.addLayout(term_row)

        layout.addWidget(self._build_progress_group())
        layout.addWidget(self._build_apply_execution_group())
        return self.translate_section_group

    def _build_dll_plan_group(self) -> QGroupBox:
        self.dll_group = QGroupBox(self._tr("group.dll_analysis"))
        layout = QVBoxLayout(self.dll_group)

        self.dll_plan_table = QTableWidget(0, 6)
        self.dll_plan_table.setHorizontalHeaderLabels(
            [
                self._tr("table.plans.dll"),
                self._tr("table.plans.status"),
                self._tr("table.plans.coverage"),
                self._tr("table.plans.ready"),
                self._tr("table.plans.open"),
                self._tr("table.plans.reference"),
                self._tr("table.plans.action"),
            ]
        )
        self.dll_plan_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.dll_plan_table.setSelectionMode(QTableWidget.SingleSelection)
        self.dll_plan_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.dll_plan_table.verticalHeader().setVisible(False)
        self.dll_plan_table.itemSelectionChanged.connect(self._sync_dll_filter_from_plan_table)
        layout.addWidget(self.dll_plan_table)
        self.dll_legend_label = QLabel(self._tr("dll.legend"))
        self.dll_legend_label.setWordWrap(True)
        layout.addWidget(self.dll_legend_label)
        self._update_dll_plan_headers()
        return self.dll_group

    def _build_main_navigation(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        mode_row = QHBoxLayout()
        self.mode_switch_label = QLabel(f"{self._tr('mode.simple')} / {self._tr('mode.expert')}")
        self.mode_switch_label.setStyleSheet("color: #8b95a7;")
        mode_row.addWidget(self.mode_switch_label)
        self.simple_mode_button = QPushButton(self._tr("mode.simple"))
        self.simple_mode_button.setCheckable(True)
        self.simple_mode_button.clicked.connect(lambda checked=False: self._set_ui_mode("simple"))
        self.expert_mode_button = QPushButton(self._tr("mode.expert"))
        self.expert_mode_button.setCheckable(True)
        self.expert_mode_button.clicked.connect(lambda checked=False: self._set_ui_mode("expert"))
        mode_row.addWidget(self.simple_mode_button)
        mode_row.addWidget(self.expert_mode_button)
        mode_row.addStretch(1)
        layout.addLayout(mode_row)

        self.main_mode_stack = QStackedWidget()
        self.main_mode_stack.addWidget(self._build_simple_mode_page())
        self.root_tabs = QTabWidget()
        self.root_tabs.addTab(self._build_start_page(), self._tr("tab.start"))
        self.root_tabs.addTab(self._build_editor_workspace_page(), self._tr("tab.workspace"))
        self.root_tabs.addTab(self._build_troubleshoot_page(), self._tr("tab.troubleshoot"))
        self.main_mode_stack.addWidget(self.root_tabs)
        layout.addWidget(self.main_mode_stack, 1)
        self._apply_ui_mode(save=False)
        return page

    def _build_simple_mode_page(self) -> QWidget:
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setSpacing(14)

        self.simple_paths_group = QGroupBox(self._tr("simple.group.paths"))
        paths_layout = QVBoxLayout(self.simple_paths_group)
        paths_layout.setContentsMargins(12, 14, 12, 12)
        paths_layout.setSpacing(10)
        self.simple_paths_help_label = QLabel(self._tr("simple.paths.help"))
        self.simple_paths_help_label.setWordWrap(True)
        self.simple_paths_help_label.setStyleSheet("color: #8b95a7;")
        self.simple_paths_help_label.setMinimumHeight(52)
        self.simple_source_label = QLabel(self._tr("simple.label.mod_install"))
        self.simple_source_edit = QLineEdit()
        self.simple_source_edit.setPlaceholderText(self._default_install_path_hint("source"))
        self.simple_source_edit.setClearButtonEnabled(True)
        self.simple_source_edit.textChanged.connect(lambda value: self._mirror_line_edit_text("source_edit", value))
        self.simple_source_edit.textChanged.connect(self._handle_install_path_change)
        self.simple_source_browse_button = QPushButton(self._tr("btn.browse"))
        self.simple_source_browse_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.simple_source_browse_button.clicked.connect(lambda: self._pick_directory(self.simple_source_edit))
        self.simple_target_label = QLabel(self._tr("simple.label.reference_install"))
        self.simple_target_edit = QLineEdit()
        self.simple_target_edit.setPlaceholderText(self._default_install_path_hint("target"))
        self.simple_target_edit.setClearButtonEnabled(True)
        self.simple_target_edit.textChanged.connect(lambda value: self._mirror_line_edit_text("target_edit", value))
        self.simple_target_edit.textChanged.connect(self._handle_install_path_change)
        self.simple_target_browse_button = QPushButton(self._tr("btn.browse"))
        self.simple_target_browse_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.simple_target_browse_button.clicked.connect(lambda: self._pick_directory(self.simple_target_edit))
        self.simple_en_ref_label = QLabel(self._tr("simple.label.en_vanilla_install"))
        self.simple_en_ref_edit = QLineEdit()
        self.simple_en_ref_edit.setPlaceholderText(self._tr("simple.en_vanilla_hint"))
        self.simple_en_ref_edit.setClearButtonEnabled(True)
        self.simple_en_ref_edit.textChanged.connect(lambda value: self._mirror_line_edit_text("en_ref_edit", value))
        self.simple_en_ref_browse_button = QPushButton(self._tr("btn.browse"))
        self.simple_en_ref_browse_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.simple_en_ref_browse_button.clicked.connect(lambda: self._pick_directory(self.simple_en_ref_edit))
        source_row = QHBoxLayout()
        source_row.setSpacing(8)
        source_row.addWidget(self.simple_source_edit, 1)
        source_row.addWidget(self.simple_source_browse_button)
        target_row = QHBoxLayout()
        target_row.setSpacing(8)
        target_row.addWidget(self.simple_target_edit, 1)
        target_row.addWidget(self.simple_target_browse_button)
        en_ref_row = QHBoxLayout()
        en_ref_row.setSpacing(8)
        en_ref_row.addWidget(self.simple_en_ref_edit, 1)
        en_ref_row.addWidget(self.simple_en_ref_browse_button)
        paths_layout.addWidget(self.simple_paths_help_label)
        paths_layout.addSpacing(4)
        paths_layout.addWidget(self.simple_source_label)
        paths_layout.addLayout(source_row)
        paths_layout.addSpacing(8)
        paths_layout.addWidget(self.simple_target_label)
        paths_layout.addLayout(target_row)
        paths_layout.addSpacing(8)
        paths_layout.addWidget(self.simple_en_ref_label)
        paths_layout.addLayout(en_ref_row)
        paths_layout.addStretch(1)

        self.simple_scan_group = QGroupBox(self._tr("simple.group.scan"))
        scan_layout = QVBoxLayout(self.simple_scan_group)
        scan_layout.setContentsMargins(12, 14, 12, 12)
        scan_layout.setSpacing(10)
        self.simple_scan_help_label = QLabel(self._tr("simple.scan.help"))
        self.simple_scan_help_label.setWordWrap(True)
        self.simple_scan_help_label.setStyleSheet("color: #8b95a7;")
        self.simple_scan_help_label.setMinimumHeight(52)
        self.simple_scan_button = QPushButton(self._tr("simple.btn.scan"))
        self.simple_scan_button.setMinimumHeight(44)
        self.simple_scan_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.simple_scan_button.clicked.connect(self._run_simple_scan)
        self.simple_progress_chart = CircularProgressChart()
        self.simple_progress_chart.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.simple_progress_chart.setFixedHeight(180)
        self.simple_scan_summary_label = QLabel(self._tr("simple.summary.idle"))
        self.simple_scan_summary_label.setWordWrap(True)
        self.simple_scan_summary_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.simple_progress_legend_label = QLabel(self._tr("progress.legend"))
        self.simple_progress_legend_label.setWordWrap(True)
        self.simple_progress_legend_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.simple_audio_progress_label = QLabel(self._tr("progress.audio.none"))
        self.simple_audio_progress_label.setWordWrap(True)
        self.simple_audio_progress_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.simple_audio_progress_bar = QProgressBar()
        self.simple_audio_progress_bar.setMinimum(0)
        self.simple_audio_progress_bar.setMaximum(100)
        self.simple_audio_progress_bar.setValue(0)
        self.simple_utf_progress_label = QLabel(self._tr("progress.utf.none"))
        self.simple_utf_progress_label.setWordWrap(True)
        self.simple_utf_progress_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.simple_utf_progress_bar = QProgressBar()
        self.simple_utf_progress_bar.setMinimum(0)
        self.simple_utf_progress_bar.setMaximum(100)
        self.simple_utf_progress_bar.setValue(0)
        scan_layout.addWidget(self.simple_scan_help_label)
        scan_layout.addSpacing(4)
        scan_layout.addWidget(self.simple_scan_button)
        scan_layout.addWidget(self.simple_progress_chart, 0, Qt.AlignHCenter)
        scan_layout.addWidget(self.simple_progress_legend_label)
        scan_layout.addWidget(self.simple_audio_progress_label)
        scan_layout.addWidget(self.simple_audio_progress_bar)
        scan_layout.addWidget(self.simple_utf_progress_label)
        scan_layout.addWidget(self.simple_utf_progress_bar)
        scan_layout.addWidget(self.simple_scan_summary_label)
        scan_layout.addStretch(1)

        self.simple_translate_group = QGroupBox(self._tr("simple.group.translate"))
        translate_layout = QVBoxLayout(self.simple_translate_group)
        translate_layout.setContentsMargins(12, 14, 12, 12)
        translate_layout.setSpacing(10)
        self.simple_translate_help_label = QLabel(self._tr("simple.translate.help"))
        self.simple_translate_help_label.setWordWrap(True)
        self.simple_translate_help_label.setStyleSheet("color: #8b95a7;")
        self.simple_translate_help_label.setMinimumHeight(52)
        self.simple_translate_button = QPushButton(self._tr("btn.apply_target"))
        self.simple_translate_button.setMinimumHeight(44)
        self.simple_translate_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.simple_translate_button.clicked.connect(self._apply_target_to_install)
        self.simple_audio_copy_check = QCheckBox(self._tr("simple.audio_copy"))
        self.simple_audio_copy_check.setChecked(True)
        self.simple_toolchain_label = QLabel("")
        self.simple_toolchain_label.setWordWrap(True)
        self.simple_toolchain_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.simple_translate_summary_label = QLabel(self._tr("simple.translate.idle"))
        self.simple_translate_summary_label.setWordWrap(True)
        self.simple_translate_summary_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.simple_status_label = QLabel(self._tr("simple.status").format(message=self._tr("status.start")))
        self.simple_status_label.setWordWrap(True)
        self.simple_status_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        translate_layout.addWidget(self.simple_translate_help_label)
        translate_layout.addSpacing(4)
        translate_layout.addWidget(self.simple_translate_button)
        translate_layout.addWidget(self.simple_audio_copy_check)
        translate_layout.addWidget(self.simple_toolchain_label)
        translate_layout.addWidget(self.simple_translate_summary_label)
        translate_layout.addStretch(1)
        translate_layout.addWidget(self.simple_status_label)

        self.simple_paths_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.simple_scan_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.simple_translate_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(self.simple_paths_group, 1)
        layout.addWidget(self.simple_scan_group, 1)
        layout.addWidget(self.simple_translate_group, 1)
        return page

    def _build_start_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.addWidget(self._build_preparation_section())
        content_layout.addWidget(self._build_scan_section())
        content_layout.addWidget(self._build_editing_section())
        content_layout.addWidget(self._build_extras_section())
        content_layout.addWidget(self._build_translate_section())
        content_layout.addStretch(1)
        scroll.setWidget(content)
        layout.addWidget(scroll)
        return page

    def _build_apply_execution_group(self) -> QGroupBox:
        self.apply_execution_group = QGroupBox(self._tr("group.apply_execution"))
        layout = QVBoxLayout(self.apply_execution_group)
        self.apply_execution_status_label = QLabel(self._tr("apply.run.idle"))
        self.apply_execution_status_label.setWordWrap(True)
        self.apply_execution_progress_bar = QProgressBar()
        self.apply_execution_progress_bar.setMinimum(0)
        self.apply_execution_progress_bar.setMaximum(100)
        self.apply_execution_progress_bar.setValue(0)
        self.apply_execution_current_label = QLabel(self._tr("apply.run.none"))
        self.apply_execution_current_label.setWordWrap(True)
        self.apply_execution_lines = QTextEdit()
        self.apply_execution_lines.setReadOnly(True)
        self.apply_execution_lines.setMinimumHeight(90)
        self.apply_execution_lines.setPlaceholderText(self._tr("apply.run.none"))
        layout.addWidget(self.apply_execution_status_label)
        layout.addWidget(self.apply_execution_progress_bar)
        layout.addWidget(self.apply_execution_current_label)
        layout.addWidget(self.apply_execution_lines)
        self._refresh_apply_resume_status()
        return self.apply_execution_group

    def _build_editor_workspace_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.editor_tabs = QTabWidget()
        self.editor_tabs.addTab(self._build_editor_page(), self._tr("tab.editor"))
        self.editor_tabs.addTab(self._build_dll_plan_group(), self._tr("tab.dlls"))
        self.editor_tabs.addTab(self._build_terminology_page(), self._tr("tab.terminology"))
        self.editor_tabs.addTab(self._build_mod_overrides_page(), self._tr("tab.mod_overrides"))
        layout.addWidget(self.editor_tabs)
        return page

    def _build_editor_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.editor_help_label = QLabel(self._tr("editor.help"))
        self.editor_help_label.setWordWrap(True)
        self.editor_missing_label = QLabel("")
        self.editor_missing_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #c62828;")
        self.editor_missing_detail_label = QLabel("")
        self.editor_missing_detail_label.setWordWrap(True)
        layout.addWidget(self.editor_help_label)
        layout.addWidget(self.editor_missing_label)
        layout.addWidget(self.editor_missing_detail_label)
        backup_row = QHBoxLayout()
        self.old_text_source_label = QLabel(self._tr("editor.old_text_source"))
        self.old_text_backup_combo = QComboBox()
        self.old_text_backup_combo.currentIndexChanged.connect(self._handle_old_text_backup_changed)
        backup_row.addWidget(self._make_help_button("tooltip.old_text_source"))
        backup_row.addWidget(self.old_text_source_label)
        backup_row.addWidget(self.old_text_backup_combo, 1)
        layout.addLayout(backup_row)
        layout.addWidget(self._build_filters_group())
        layout.addWidget(self._build_main_splitter(), 1)
        self._refresh_editor_status()
        return page

    def _build_terminology_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(self._build_terminology_mapping_group())
        layout.addWidget(self._build_terminology_management_group(), 1)
        return page

    def _build_mod_overrides_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.mod_overrides_help_label = QLabel(self._tr("mod_overrides.help"))
        self.mod_overrides_help_label.setWordWrap(True)
        layout.addWidget(self.mod_overrides_help_label)
        action_row = QHBoxLayout()
        self.mod_overrides_reload_button = QPushButton(self._tr("btn.mod_overrides_reload"))
        self.mod_overrides_reload_button.clicked.connect(self._refresh_mod_override_entries)
        self.mod_overrides_delete_button = QPushButton(self._tr("btn.mod_overrides_delete"))
        self.mod_overrides_delete_button.clicked.connect(self._delete_selected_mod_override)
        action_row.addWidget(self.mod_overrides_reload_button)
        action_row.addWidget(self.mod_overrides_delete_button)
        action_row.addStretch(1)
        layout.addLayout(action_row)
        self.mod_overrides_table = QTableWidget(0, 6)
        self.mod_overrides_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.mod_overrides_table.setSelectionMode(QTableWidget.SingleSelection)
        self.mod_overrides_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.mod_overrides_table.verticalHeader().setVisible(False)
        layout.addWidget(self.mod_overrides_table, 1)
        return page

    def _build_troubleshoot_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        content = QWidget()
        content_layout = QVBoxLayout(content)

        self.troubleshoot_help_label = QLabel(self._tr("troubleshoot.help"))
        self.troubleshoot_help_label.setWordWrap(True)
        self.troubleshoot_help_label.setStyleSheet("color: #8b95a7;")
        content_layout.addWidget(self.troubleshoot_help_label)
        content_layout.addSpacing(12)

        # ── Fix XML Tags ────────────────────────────────
        self.fix_xml_group = QGroupBox(self._tr("troubleshoot.fix_xml.title"))
        fix_xml_layout = QVBoxLayout(self.fix_xml_group)
        fix_xml_layout.setContentsMargins(12, 14, 12, 12)
        fix_xml_layout.setSpacing(10)
        self.fix_xml_help_label = QLabel(self._tr("troubleshoot.fix_xml.help"))
        self.fix_xml_help_label.setWordWrap(True)
        self.fix_xml_help_label.setStyleSheet("color: #8b95a7;")
        fix_xml_layout.addWidget(self.fix_xml_help_label)

        # Step 1: Scan
        self.fix_xml_scan_button = QPushButton(self._tr("troubleshoot.fix_xml.scan_btn"))
        self.fix_xml_scan_button.setMinimumHeight(36)
        self.fix_xml_scan_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.fix_xml_scan_button.clicked.connect(self._run_fix_xml_scan)
        fix_xml_layout.addWidget(self.fix_xml_scan_button)

        self.fix_xml_scan_result_label = QLabel("")
        self.fix_xml_scan_result_label.setWordWrap(True)
        fix_xml_layout.addWidget(self.fix_xml_scan_result_label)

        # Step 2: Repair (fix data in project)
        self.fix_xml_repair_button = QPushButton(self._tr("troubleshoot.fix_xml.repair_btn"))
        self.fix_xml_repair_button.setMinimumHeight(36)
        self.fix_xml_repair_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.fix_xml_repair_button.setEnabled(False)
        self.fix_xml_repair_button.clicked.connect(self._run_fix_xml_repair)
        fix_xml_layout.addWidget(self.fix_xml_repair_button)

        self.fix_xml_progress_bar = QProgressBar()
        self.fix_xml_progress_bar.setMinimum(0)
        self.fix_xml_progress_bar.setMaximum(100)
        self.fix_xml_progress_bar.setValue(0)
        self.fix_xml_progress_bar.setVisible(False)
        fix_xml_layout.addWidget(self.fix_xml_progress_bar)

        self.fix_xml_repair_result_label = QLabel("")
        self.fix_xml_repair_result_label.setWordWrap(True)
        fix_xml_layout.addWidget(self.fix_xml_repair_result_label)

        # Step 3: Apply to DLLs
        self.fix_xml_apply_button = QPushButton(self._tr("troubleshoot.fix_xml.apply_btn"))
        self.fix_xml_apply_button.setMinimumHeight(36)
        self.fix_xml_apply_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.fix_xml_apply_button.setEnabled(False)
        self.fix_xml_apply_button.clicked.connect(self._run_fix_xml_apply)
        fix_xml_layout.addWidget(self.fix_xml_apply_button)

        self.fix_xml_apply_result_label = QLabel("")
        self.fix_xml_apply_result_label.setWordWrap(True)
        fix_xml_layout.addWidget(self.fix_xml_apply_result_label)

        content_layout.addWidget(self.fix_xml_group)
        content_layout.addStretch(1)
        scroll.setWidget(content)
        layout.addWidget(scroll)
        return page

    def _build_terminology_mapping_group(self) -> QGroupBox:
        self.terminology_map_group = QGroupBox(self._tr("group.terminology_map"))
        layout = QGridLayout(self.terminology_map_group)
        self.term_source_label = QLabel(self._tr("label.term_source"))
        self.term_target_label = QLabel(self._tr("label.term_target"))
        self.term_source_edit = QLineEdit()
        self.term_target_edit = QLineEdit()
        self.term_from_selection_button = QPushButton(self._tr("btn.term_from_selection"))
        self.term_from_selection_button.clicked.connect(self._fill_term_from_selection)
        self.term_save_button = QPushButton(self._tr("btn.term_save"))
        self.term_save_button.clicked.connect(self._save_terminology_mapping)
        layout.addWidget(self.term_source_label, 0, 0)
        layout.addWidget(self.term_source_edit, 0, 1)
        layout.addWidget(self.term_from_selection_button, 0, 2)
        layout.addWidget(self.term_target_label, 1, 0)
        layout.addWidget(self.term_target_edit, 1, 1)
        layout.addWidget(self.term_save_button, 1, 2)
        return self.terminology_map_group

    def _build_terminology_management_group(self) -> QGroupBox:
        self.terminology_manage_group = QGroupBox(self._tr("group.terminology_manage"))
        layout = QGridLayout(self.terminology_manage_group)
        self.pattern_source_label = QLabel(self._tr("label.pattern_source"))
        self.pattern_target_label = QLabel(self._tr("label.pattern_target"))
        self.pattern_source_edit = QLineEdit()
        self.pattern_target_edit = QLineEdit()
        self.pattern_save_button = QPushButton(self._tr("btn.pattern_save"))
        self.pattern_save_button.clicked.connect(self._save_pattern_mapping)
        self.terminology_reload_button = QPushButton(self._tr("btn.terminology_reload"))
        self.terminology_reload_button.clicked.connect(self._refresh_terminology_tables)

        self.term_table = QTableWidget(0, 3)
        self.term_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.term_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.term_table.setSelectionMode(QTableWidget.SingleSelection)
        self.term_table.verticalHeader().setVisible(False)
        self.term_table.itemSelectionChanged.connect(self._use_selected_term_row)

        self.pattern_table = QTableWidget(0, 3)
        self.pattern_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.pattern_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.pattern_table.setSelectionMode(QTableWidget.SingleSelection)
        self.pattern_table.verticalHeader().setVisible(False)
        self.pattern_table.itemSelectionChanged.connect(self._use_selected_pattern_row)

        layout.addWidget(self.pattern_source_label, 0, 0)
        layout.addWidget(self.pattern_source_edit, 0, 1)
        layout.addWidget(self.terminology_reload_button, 0, 2)
        layout.addWidget(self.pattern_target_label, 1, 0)
        layout.addWidget(self.pattern_target_edit, 1, 1)
        layout.addWidget(self.pattern_save_button, 1, 2)
        layout.addWidget(self.term_table, 2, 0, 1, 3)
        layout.addWidget(self.pattern_table, 3, 0, 1, 3)
        self._refresh_terminology_tables()
        return self.terminology_manage_group

    def _build_footer(self) -> QWidget:
        footer = QWidget()
        layout = QVBoxLayout(footer)
        layout.setContentsMargins(0, 0, 0, 0)
        self.footer_label = QLabel("")
        self.footer_label.setTextFormat(Qt.RichText)
        self.footer_label.setOpenExternalLinks(True)
        self.footer_label.setWordWrap(True)
        self.footer_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.footer_label.setStyleSheet("color: #9aa0a6; padding-top: 2px;")
        layout.addWidget(self.footer_label)
        self._refresh_footer()
        return footer

    def _build_progress_group(self) -> QGroupBox:
        self.progress_group = QGroupBox(self._tr("group.progress"))
        layout = QVBoxLayout(self.progress_group)
        self.translation_progress_bar = SegmentedProgressBar()
        self.translation_progress_label = QLabel("")
        self.translation_progress_label.setWordWrap(True)
        self.translation_progress_legend_label = QLabel(self._tr("progress.legend"))
        self.translation_progress_legend_label.setWordWrap(True)
        self.audio_progress_label = QLabel(self._tr("progress.audio.none"))
        self.audio_progress_label.setWordWrap(True)
        self.audio_progress_bar = QProgressBar()
        self.audio_progress_bar.setMinimum(0)
        self.audio_progress_bar.setMaximum(100)
        self.audio_progress_bar.setValue(0)
        self.utf_progress_label = QLabel(self._tr("progress.utf.none"))
        self.utf_progress_label.setWordWrap(True)
        self.utf_progress_bar = QProgressBar()
        self.utf_progress_bar.setMinimum(0)
        self.utf_progress_bar.setMaximum(100)
        self.utf_progress_bar.setValue(0)
        layout.addWidget(self.translation_progress_bar)
        layout.addWidget(self.translation_progress_label)
        layout.addWidget(self.translation_progress_legend_label)
        layout.addWidget(self.audio_progress_label)
        layout.addWidget(self.audio_progress_bar)
        layout.addWidget(self.utf_progress_label)
        layout.addWidget(self.utf_progress_bar)
        self._refresh_progress()
        return self.progress_group

    def _build_filters_group(self) -> QGroupBox:
        self.filters_group = QGroupBox(self._tr("group.filters"))
        row = QHBoxLayout(self.filters_group)

        self.kind_combo = QComboBox()
        self.kind_combo.addItems([self._tr("kind.all"), "string", "infocard"])
        self.kind_combo.currentIndexChanged.connect(self._refresh_table)

        self.dll_combo = QComboBox()
        self.dll_combo.addItem(self._tr("kind.all"))
        self.dll_combo.currentIndexChanged.connect(self._refresh_table)

        self.status_combo = QComboBox()
        self._populate_status_filter()
        self.status_combo.currentIndexChanged.connect(self._refresh_table)

        self.target_only_check = QCheckBox(self._tr("check.target_only"))
        self.target_only_check.setChecked(True)
        self.target_only_check.stateChanged.connect(self._refresh_table)

        self.changed_only_check = QCheckBox(self._tr("check.changed_only"))
        self.changed_only_check.setChecked(True)
        self.changed_only_check.stateChanged.connect(self._refresh_table)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(self._tr("search.placeholder"))
        self.search_edit.textChanged.connect(self._schedule_search_refresh)

        self.kind_label = QLabel(self._tr("label.kind"))
        self.status_label = QLabel(self._tr("label.status"))
        self.search_label = QLabel(self._tr("label.search"))

        row.addWidget(self._make_help_button("tooltip.filter_kind"))
        row.addWidget(self.kind_label)
        row.addWidget(self.kind_combo)
        row.addWidget(QLabel("DLL"))
        row.addWidget(self.dll_combo)
        row.addWidget(self._make_help_button("tooltip.filter_status"))
        row.addWidget(self.status_label)
        row.addWidget(self.status_combo)
        row.addWidget(self._make_help_button("tooltip.filter_target_only"))
        row.addWidget(self.target_only_check)
        row.addWidget(self._make_help_button("tooltip.filter_changed_only"))
        row.addWidget(self.changed_only_check)
        row.addWidget(self._make_help_button("tooltip.filter_search"))
        row.addWidget(self.search_label)
        row.addWidget(self.search_edit, 1)
        return self.filters_group

    def _build_main_splitter(self) -> QSplitter:
        splitter = QSplitter(Qt.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        self.summary_label = QLabel(self._tr("summary.none"))
        self.summary_label.setWordWrap(True)
        left_layout.addWidget(self.summary_label)

        self.table = QTableWidget(0, 9)
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
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_unit_table_context_menu)
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self._update_preview)
        left_layout.addWidget(self.table, 1)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        self.detail_label = QLabel(self._tr("detail.none"))
        self.detail_label.setWordWrap(True)
        right_layout.addWidget(self.detail_label)

        self.source_preview = QTextEdit()
        self.source_preview.setReadOnly(True)
        self.source_preview.setContextMenuPolicy(Qt.CustomContextMenu)
        self.source_preview.customContextMenuRequested.connect(self._show_source_preview_context_menu)
        self.target_preview = QTextEdit()
        self.target_preview.setReadOnly(False)
        self.target_preview.setContextMenuPolicy(Qt.CustomContextMenu)
        self.target_preview.customContextMenuRequested.connect(self._show_target_preview_context_menu)

        self.source_preview_group = QGroupBox(self._tr("preview.current"))
        source_box = self.source_preview_group
        source_layout = QVBoxLayout(source_box)
        source_layout.addWidget(self.source_preview)

        self.target_preview_group = QGroupBox(self._tr("preview.reference"))
        target_box = self.target_preview_group
        target_layout = QVBoxLayout(target_box)
        target_layout.addWidget(self.target_preview)
        self.target_edit_hint = QLabel(self._tr("preview.edit_hint"))
        self.target_edit_hint.setWordWrap(True)
        target_layout.addWidget(self.target_edit_hint)
        edit_actions = QHBoxLayout()
        self.save_edit_button = QPushButton(self._tr("btn.save_edit"))
        self.save_edit_button.clicked.connect(self._save_manual_edit)
        self.save_edit_button.setToolTip(self._tr("tooltip.save_edit"))
        self.reset_edit_button = QPushButton(self._tr("btn.reset_edit"))
        self.reset_edit_button.clicked.connect(self._reset_manual_edit)
        self.reset_edit_button.setToolTip(self._tr("tooltip.reset_edit"))
        self.translate_entry_button = QPushButton(self._tr("btn.translate_entry"))
        self.translate_entry_button.clicked.connect(self._translate_selected_entry)
        self.translate_entry_button.setToolTip(self._tr("tooltip.translate_entry"))
        edit_actions.addStretch(1)
        edit_actions.addWidget(self._make_help_button("tooltip.translate_entry"))
        edit_actions.addWidget(self.translate_entry_button)
        edit_actions.addWidget(self._make_help_button("tooltip.reset_edit"))
        edit_actions.addWidget(self.reset_edit_button)
        edit_actions.addWidget(self._make_help_button("tooltip.save_edit"))
        edit_actions.addWidget(self.save_edit_button)
        target_layout.addLayout(edit_actions)

        right_layout.addWidget(source_box, 1)

        self.translator_progress_bar = QProgressBar()
        self.translator_progress_bar.setMinimum(0)
        self.translator_progress_bar.setMaximum(0)
        self.translator_progress_bar.setTextVisible(False)
        self.translator_progress_bar.setFixedHeight(6)
        self.translator_progress_bar.setVisible(False)
        right_layout.addWidget(self.translator_progress_bar)

        right_layout.addWidget(target_box, 1)

        toolchain_state = self._tr("toolchain.available") if self._writer.has_toolchain() else self._tr("toolchain.unavailable")
        self.toolchain_label = QLabel(f"Resource-Toolchain: {toolchain_state}")
        self.toolchain_label.setWordWrap(True)
        right_layout.addWidget(self.toolchain_label)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([620, 360])
        return splitter
