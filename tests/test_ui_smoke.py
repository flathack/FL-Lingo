from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QDialog

from launch import LaunchConfig
from flatlas_translator.models import ResourceCatalog, ResourceKind, ResourceLocation, TranslationUnit, make_global_id
from flatlas_translator.project_io import TranslatorProject, save_project
from flatlas_translator.resource_writer import ApplySessionInfo
from flatlas_translator.ui_app import TranslatorMainWindow


def _make_window(qtbot, monkeypatch, tmp_path: Path) -> TranslatorMainWindow:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    window = TranslatorMainWindow(LaunchConfig())
    qtbot.addWidget(window)
    window.show()
    qtbot.waitUntil(window.isVisible)
    return window


def _location(dll_name: str, local_id: int, *, slot: int = 1) -> ResourceLocation:
    dll_path = Path("/tmp") / dll_name
    return ResourceLocation(
        dll_name=dll_name,
        dll_path=dll_path,
        local_id=local_id,
        slot=slot,
        global_id=make_global_id(slot, local_id),
    )


def _catalog(*units: TranslationUnit) -> ResourceCatalog:
    install_dir = Path("/tmp/fllingo-test")
    return ResourceCatalog(
        install_dir=install_dir,
        freelancer_ini=install_dir / "EXE" / "freelancer.ini",
        units=units,
    )


def test_main_window_starts_in_simple_mode(qtbot, monkeypatch, tmp_path: Path) -> None:
    window = _make_window(qtbot, monkeypatch, tmp_path)

    assert window._ui_mode == "simple"
    assert window.main_mode_stack.currentIndex() == 0
    assert window.simple_mode_button.isChecked()
    assert not window.expert_mode_button.isChecked()
    assert not window.root_tabs.isTabEnabled(1)


def test_mode_switch_to_expert_updates_stack(qtbot, monkeypatch, tmp_path: Path) -> None:
    window = _make_window(qtbot, monkeypatch, tmp_path)

    qtbot.mouseClick(window.expert_mode_button, Qt.LeftButton)
    assert window._ui_mode == "expert"
    assert window.main_mode_stack.currentIndex() == 1
    assert window.expert_mode_button.isChecked()
    assert not window.simple_mode_button.isChecked()


def test_editor_default_filters_show_open_entries(qtbot, monkeypatch, tmp_path: Path) -> None:
    window = _make_window(qtbot, monkeypatch, tmp_path)

    assert window.status_combo.currentData() == "mod_only"
    assert not window.target_only_check.isChecked()
    assert not window.changed_only_check.isChecked()


def test_language_switch_retranslates_ui(qtbot, monkeypatch, tmp_path: Path) -> None:
    window = _make_window(qtbot, monkeypatch, tmp_path)

    window._set_language("de")

    assert window.simple_scan_button.text() == "Scan starten"
    assert window.expert_mode_button.text() == "Expertenmodus"
    assert window.root_tabs.tabText(1) == "Bearbeitung"


def test_action_state_with_source_catalog_enables_workspace_but_not_apply(qtbot, monkeypatch, tmp_path: Path) -> None:
    window = _make_window(qtbot, monkeypatch, tmp_path)
    unit = TranslationUnit(
        kind=ResourceKind.STRING,
        source=_location("resources.dll", 100),
        source_text="Mod text",
    )
    window._source_catalog = _catalog(unit)
    window._populate_dll_filter(window._source_catalog)
    window._refresh_table()
    window._update_action_state()

    assert window.root_tabs.isTabEnabled(1)
    assert window.editor_tabs.isTabEnabled(0)
    assert not window.editor_tabs.isTabEnabled(1)
    assert window.editor_tabs.isTabEnabled(2)
    assert not window.apply_button.isEnabled()
    assert not window.simple_translate_button.isEnabled()
    assert window.compare_button.isEnabled()


def test_action_state_with_paired_catalog_and_toolchain_enables_apply(qtbot, monkeypatch, tmp_path: Path) -> None:
    window = _make_window(qtbot, monkeypatch, tmp_path)
    source = _location("resources.dll", 100)
    target = _location("resources.dll", 100, slot=2)
    paired_unit = TranslationUnit(
        kind=ResourceKind.STRING,
        source=source,
        source_text="English text",
        target=target,
        target_text="Deutscher Text",
    )
    window._source_catalog = _catalog(paired_unit)
    window._paired_catalog = _catalog(paired_unit)
    monkeypatch.setattr(window._writer, "has_toolchain", lambda: True)

    window._populate_dll_filter(window._paired_catalog)
    window._refresh_table()
    window._update_action_state()

    assert window.editor_tabs.isTabEnabled(1)
    assert window.apply_button.isEnabled()
    assert window.simple_translate_button.isEnabled()
    assert window.simple_translate_summary_label.text() == window._tr("simple.translate.ready").format(count=1)
    assert window.simple_scan_summary_label.text() == window._tr("simple.summary.ready").format(
        total=1,
        auto=1,
        manual=0,
        open=0,
        dlls=1,
    )


def test_load_project_path_restores_catalog_and_enables_workspace(qtbot, monkeypatch, tmp_path: Path) -> None:
    window = _make_window(qtbot, monkeypatch, tmp_path)
    source = _location("resources.dll", 100)
    target = _location("resources.dll", 100, slot=2)
    source_unit = TranslationUnit(
        kind=ResourceKind.STRING,
        source=source,
        source_text="English text",
    )
    paired_unit = TranslationUnit(
        kind=ResourceKind.STRING,
        source=source,
        source_text="English text",
        target=target,
        target_text="Deutscher Text",
    )
    source_catalog = _catalog(source_unit)
    target_catalog = _catalog(
        TranslationUnit(
            kind=ResourceKind.STRING,
            source=target,
            source_text="Deutscher Text",
        )
    )
    paired_catalog = _catalog(paired_unit)
    project_path = tmp_path / "smoke.FLLingo"
    save_project(
        TranslatorProject(
            source_install_dir="/tmp/source-game",
            target_install_dir="/tmp/target-game",
            include_infocards=True,
            source_language="en",
            target_language="de",
            source_catalog=source_catalog,
            target_catalog=target_catalog,
            paired_catalog=paired_catalog,
            dll_plans=(),
        ),
        project_path,
    )

    window._load_project_path(project_path)

    assert window._project_path == project_path
    assert window.source_edit.text() == "/tmp/source-game"
    assert window.target_edit.text() == "/tmp/target-game"
    assert window._paired_catalog is not None
    assert window.root_tabs.isTabEnabled(1)
    assert window.editor_tabs.isTabEnabled(1)
    assert window.status_combo.currentData() == "mod_only"
    assert window.table.rowCount() == 0


def test_apply_resume_status_shows_pending_session(qtbot, monkeypatch, tmp_path: Path) -> None:
    window = _make_window(qtbot, monkeypatch, tmp_path)
    source = _location("resources.dll", 100)
    target = _location("resources.dll", 100, slot=2)
    paired_unit = TranslationUnit(
        kind=ResourceKind.STRING,
        source=source,
        source_text="English text",
        target=target,
        target_text="Deutscher Text",
    )
    window._paired_catalog = _catalog(paired_unit)
    session = ApplySessionInfo(
        state_path=tmp_path / "apply-session.json",
        backup_dir=tmp_path / "backup",
        total_dlls=3,
        completed_dlls=("alpha.dll",),
        pending_dlls=("resources.dll", "beta.dll"),
        failed_dll=None,
        last_error=None,
    )
    monkeypatch.setattr(window._writer, "load_apply_session", lambda catalog, units=None: session)

    window._refresh_apply_resume_status()

    assert window.apply_execution_status_label.text() == window._tr("apply.run.resume_available").format(done=1, total=3)
    assert "resources.dll" in window.apply_execution_current_label.text()
    assert window.apply_execution_progress_bar.value() == 33


def test_open_settings_dialog_applies_selected_theme(qtbot, monkeypatch, tmp_path: Path) -> None:
    window = _make_window(qtbot, monkeypatch, tmp_path)

    class _FakeDialog:
        def __init__(self, current_theme: str, parent=None) -> None:
            self.selected_theme = "light"

        def exec(self) -> int:
            return QDialog.Accepted

    window._theme = "dark"
    window._settings_dialog_class = _FakeDialog

    window._open_settings_dialog()

    assert window._theme == "light"
    assert "background: #f5f4ef;" in QApplication.instance().styleSheet()


def test_simple_mode_status_transitions_from_idle_to_loaded(qtbot, monkeypatch, tmp_path: Path) -> None:
    window = _make_window(qtbot, monkeypatch, tmp_path)

    window.source_edit.setText("")
    window.target_edit.setText("")
    window._source_catalog = None
    window._paired_catalog = None
    window._refresh_simple_mode()
    window._update_action_state()
    assert window.simple_scan_summary_label.text() == window._tr("simple.summary.idle")
    assert window.simple_translate_summary_label.text() == window._tr("simple.translate.idle")
    assert not window.simple_scan_button.isEnabled()

    window.source_edit.setText("/tmp/source-game")
    window.target_edit.setText("/tmp/target-game")
    window._source_catalog = _catalog(
        TranslationUnit(
            kind=ResourceKind.STRING,
            source=_location("resources.dll", 100),
            source_text="Open mod text",
        )
    )
    window._paired_catalog = None
    window._refresh_simple_mode()
    window._update_action_state()
    assert window.simple_scan_summary_label.text() == window._tr("simple.summary.source_loaded")
    assert window.simple_translate_summary_label.text() == window._tr("simple.summary.source_loaded")
    assert window.simple_scan_button.isEnabled()
