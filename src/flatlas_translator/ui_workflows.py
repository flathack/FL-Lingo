"""Workflow and dialog mixin for FL Lingo main window."""

from __future__ import annotations

import json
import os
import re
import shutil
import ssl
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from urllib import request as urlrequest

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QLabel,
    QMessageBox,
    QProgressDialog,
    QTextBrowser,
    QVBoxLayout,
)

from .catalog import pair_catalogs
from .dll_plans import DllStrategy, build_dll_plans
from .exporters import export_catalog_json
from .localization import LANGUAGE_OPTIONS, resolve_languages_dir
from .mod_overrides import apply_mod_overrides
from .models import RelocalizationStatus, ResourceCatalog, ResourceKind, TranslationUnit
from .project_io import PROJECT_FILE_EXTENSION, load_project, project_signature, save_project
from .terminology import apply_known_term_suggestions, clear_term_map_cache, resolve_terminology_file
from .translation_exchange import export_all_translated, export_long_open_exchange, export_mod_only_exchange, import_exchange


class UIWorkflowMixin:
    def _resolve_source_and_reference_installs(self) -> tuple[Path, Path] | None:
        source_install = Path(self.source_edit.text().strip())
        reference_install = Path(self.target_edit.text().strip())
        if not source_install.exists():
            self._show_error(self._tr("error.source_missing").format(path=source_install))
            return None
        if not reference_install.exists():
            self._show_error(self._tr("error.target_missing").format(path=reference_install))
            return None
        return source_install, reference_install

    def _export_visible_json(self) -> None:
        catalog = self._current_catalog()
        if catalog is None:
            self._show_error(self._tr("error.load_first"))
            return
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            self._tr("dialog.export_visible"),
            str(Path.cwd() / "build" / "translator-export.json"),
            "JSON Files (*.json)",
        )
        if not output_path:
            return
        export_catalog = ResourceCatalog(catalog.install_dir, catalog.freelancer_ini, tuple(self._visible_units))
        try:
            self._run_with_progress(
                self._tr("dialog.progress_title"),
                self._tr("progress.export_visible"),
                lambda: export_catalog_json(export_catalog, Path(output_path)),
            )
        except Exception as exc:
            self._show_error(self._tr("error.export_failed").format(error=exc))
            return
        if self._lang == "en":
            self._set_status(f"{len(self._visible_units)} entries exported: {output_path}")
        else:
            self._set_status(f"{len(self._visible_units)} Einträge exportiert: {output_path}")

    def _save_project_file(self) -> bool:
        if self._current_catalog() is None:
            self._show_error(self._tr("error.load_first"))
            return False
        if self._project_path is not None:
            return self._save_project_to_path(self._project_path)
        return self._save_project_file_as()

    def _save_project_file_as(self) -> bool:
        if self._current_catalog() is None:
            self._show_error(self._tr("error.load_first"))
            return False
        self._store_language_pair()
        default_path = self._project_path or (Path.cwd() / "build" / f"translator-project{PROJECT_FILE_EXTENSION}")
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            self._tr("dialog.project_save_as"),
            str(default_path),
            f"FL Lingo Project (*{PROJECT_FILE_EXTENSION})",
        )
        if not output_path:
            return False
        output_path = self._ensure_project_extension(output_path)
        return self._save_project_to_path(Path(output_path))

    def _save_project_to_path(self, output_path: Path) -> bool:
        try:
            self._run_with_progress(
                self._tr("dialog.progress_title"),
                self._tr("progress.save_project"),
                lambda: save_project(self._current_project(), Path(output_path)),
            )
        except Exception as exc:
            self._show_error(self._tr("error.project_save_failed").format(error=exc))
            return False
        self._project_path = Path(output_path)
        self._saved_project_signature = self._current_project_signature()
        self._set_status(self._tr("status.project_saved").format(path=output_path))
        self._refresh_project_status()
        return True

    def _load_project_file(self) -> None:
        if not self._confirm_unsaved_changes():
            return
        input_path, _ = QFileDialog.getOpenFileName(
            self,
            self._tr("dialog.project_load"),
            str(self._project_path.parent if self._project_path is not None else (Path.cwd() / "build")),
            f"FL Lingo Project (*{PROJECT_FILE_EXTENSION})",
        )
        if not input_path:
            return
        self._load_project_path(Path(input_path))

    def _new_project_file(self) -> None:
        if not self._confirm_unsaved_changes():
            return
        self._reset_session_state()
        self._set_status(self._tr("status.project_new"))

    def _rebuild_project_file(self) -> None:
        if not self._confirm_unsaved_changes():
            return
        reply = QMessageBox.question(
            self,
            self._tr("dialog.rebuild_title"),
            self._tr("dialog.rebuild_message"),
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        if reply != QMessageBox.Yes:
            return
        self._store_language_pair()
        self._source_catalog = None
        self._target_catalog = None
        self._paired_catalog = None
        self._dll_plans = []
        self._visible_units = []
        self._saved_project_signature = None
        self._refresh_dll_plan_table()
        self._populate_dll_filter(None)
        self._refresh_table()
        self._load_source_catalog()
        if self.target_edit.text().strip():
            self._load_compare_catalog()
        self._set_status(self._tr("status.project_rebuilt"))

    def _ensure_project_extension(self, output_path: str) -> str:
        path = str(output_path or "").strip()
        if not path:
            return path
        if path.lower().endswith(PROJECT_FILE_EXTENSION.lower()):
            return path
        return f"{path}{PROJECT_FILE_EXTENSION}"

    def _load_project_path(self, input_path: Path) -> None:
        try:
            project = self._run_with_progress(
                self._tr("dialog.progress_title"),
                self._tr("progress.load_project"),
                lambda: load_project(Path(input_path)),
            )
        except Exception as exc:
            self._show_error(self._tr("error.project_load_failed").format(error=exc))
            return

        self._project_path = Path(input_path)
        self.source_edit.setText(project.source_install_dir)
        self.target_edit.setText(project.target_install_dir)
        if project.en_ref_install_dir:
            if hasattr(self, "en_ref_edit"):
                self.en_ref_edit.setText(project.en_ref_install_dir)
            if hasattr(self, "simple_en_ref_edit"):
                self.simple_en_ref_edit.setText(project.en_ref_install_dir)
        self.include_infocards_check.setChecked(project.include_infocards)
        self._source_lang_code = self._normalize_lang_code(project.source_language, self._source_lang_code)
        self._target_lang_code = self._normalize_lang_code(project.target_language, self._target_lang_code)
        self._set_language_combo_value(self.source_lang_edit, self._source_lang_code)
        self._set_language_combo_value(self.target_lang_edit, self._target_lang_code)
        self._source_catalog = project.source_catalog
        self._target_catalog = project.target_catalog
        self._paired_catalog = (
            apply_mod_overrides(
                apply_known_term_suggestions(project.paired_catalog, target_language=self._target_lang_code)
            )
            if project.paired_catalog is not None
            else None
        )
        self._dll_plans = list(project.dll_plans)
        self._apply_editor_default_filters(force=True)
        self._saved_project_signature = self._current_project_signature()
        self._refresh_mod_override_entries()
        self._refresh_old_text_backup_options()
        self._populate_dll_filter(self._current_catalog())
        self._refresh_dll_plan_table()
        self._refresh_table()
        self._refresh_footer()
        self._save_persistent_settings()
        self._update_action_state()
        self._set_status(self._tr("status.project_loaded").format(path=input_path))
        self._refresh_project_status()

    def _try_restore_last_project(self, input_path: Path) -> None:
        if not Path(input_path).is_file():
            self._project_path = None
            self._startup_last_project_path = None
            self._save_persistent_settings()
            return
        self._load_project_path(Path(input_path))

    def _build_apply_preview(self, units: list[TranslationUnit]) -> str:
        by_dll: dict[str, dict[str, int | str]] = {}
        plan_by_name = {plan.dll_name: plan for plan in self._dll_plans}
        for unit in units:
            bucket = by_dll.setdefault(
                unit.source.dll_name,
                {"units": 0, "strings": 0, "infocards": 0, "action": self._tr("plan.action.patch")},
            )
            bucket["units"] = int(bucket["units"]) + 1
            if unit.kind == ResourceKind.STRING:
                bucket["strings"] = int(bucket["strings"]) + 1
            else:
                bucket["infocards"] = int(bucket["infocards"]) + 1
            plan = plan_by_name.get(unit.source.dll_name)
            if plan is not None:
                if plan.strategy == DllStrategy.FULL_REPLACE_SAFE:
                    bucket["action"] = self._tr("plan.action.full")
                elif plan.strategy == DllStrategy.NOT_SAFE:
                    bucket["action"] = self._tr("plan.action.unsafe")
        lines = []
        for dll_name in sorted(by_dll):
            bucket = by_dll[dll_name]
            lines.append(
                f"{dll_name}: {bucket['action']} | units={bucket['units']} | strings={bucket['strings']} | infocards={bucket['infocards']}"
            )
        return "\n".join(lines)

    def _restore_backup(self) -> None:
        install_dir = Path(self.source_edit.text().strip())
        if not install_dir.exists():
            self._show_error(self._tr("error.source_missing").format(path=install_dir))
            return
        backups = self._writer.list_backups(install_dir)
        if not backups:
            self._show_error(self._tr("error.no_backups"))
            return
        selected_dir = QFileDialog.getExistingDirectory(
            self,
            self._tr("dialog.restore_backup"),
            str(backups[0]),
        )
        if not selected_dir:
            return
        backup_dir = Path(selected_dir)
        reply = QMessageBox.question(
            self,
            self._tr("dialog.restore_backup"),
            self._tr("dialog.restore_confirm").format(path=backup_dir),
        )
        if reply != QMessageBox.Yes:
            return
        try:
            restored = self._writer.restore_backup(install_dir, backup_dir)
        except Exception as exc:
            self._show_error(self._tr("error.restore_failed").format(error=exc))
            return
        QMessageBox.information(
            self,
            self._tr("dialog.restore_backup"),
            self._tr("dialog.restore_success").format(count=len(restored), path=backup_dir),
        )
        self._set_status(self._tr("status.backup_restored").format(path=backup_dir))
        if self._source_catalog is not None:
            self._load_source_catalog()
            if self._target_catalog is not None:
                self._load_compare_catalog()

    def _install_file_association(self) -> None:
        try:
            script_path = self._writer.install_file_association()
        except Exception as exc:
            self._show_error(self._tr("error.file_assoc_failed").format(error=exc))
            return
        QMessageBox.information(
            self,
            self._tr("dialog.file_assoc"),
            self._tr("dialog.file_assoc_done").format(path=script_path),
        )
        self._set_status(self._tr("status.file_assoc_done"))

    def _confirm_unsaved_changes(self) -> bool:
        if not self._is_project_dirty():
            return True
        reply = QMessageBox.question(
            self,
            self._tr("dialog.unsaved_title"),
            self._tr("dialog.unsaved_message"),
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Save,
        )
        if reply == QMessageBox.Save:
            return self._save_project_file()
        if reply == QMessageBox.Discard:
            return True
        return False

    def _export_mod_only_exchange(self) -> None:
        catalog = self._current_catalog()
        if catalog is None:
            self._show_error(self._tr("error.load_first"))
            return
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            self._tr("btn.export_mod_only"),
            str(Path.cwd() / "build" / "open-entries-exchange.json"),
            "JSON Files (*.json)",
        )
        if not output_path:
            return
        try:
            report = self._run_with_progress(
                self._tr("dialog.progress_title"),
                self._tr("progress.export_open"),
                lambda: export_mod_only_exchange(catalog, Path(output_path), target_language=self._target_lang_code),
            )
        except Exception as exc:
            self._show_error(self._tr("error.export_mod_only_failed").format(error=exc))
            return
        self._set_status(
            self._tr("status.export_mod_only").format(
                exported=report.exported_entries,
                skipped=report.skipped_entries,
                glossary=report.glossary_entries,
            )
            + f": {output_path}"
        )

    def _export_long_open_exchange(self) -> None:
        catalog = self._current_catalog()
        if catalog is None:
            self._show_error(self._tr("error.load_first"))
            return
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            self._tr("btn.export_long_open"),
            str(Path.cwd() / "build" / "long-open-entries-exchange.json"),
            "JSON Files (*.json)",
        )
        if not output_path:
            return
        try:
            report = self._run_with_progress(
                self._tr("dialog.progress_title"),
                self._tr("progress.export_long_open"),
                lambda: export_long_open_exchange(catalog, Path(output_path), target_language=self._target_lang_code),
            )
        except Exception as exc:
            self._show_error(self._tr("error.export_long_open_failed").format(error=exc))
            return
        self._set_status(
            self._tr("status.export_long_open").format(
                exported=report.exported_entries,
                skipped=report.skipped_entries,
                glossary=report.glossary_entries,
            )
            + f": {output_path}"
        )

    def _export_all_translated(self) -> None:
        catalog = self._current_catalog()
        if catalog is None:
            self._show_error(self._tr("error.load_first"))
            return
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            self._tr("btn.export_all_translated"),
            str(Path.cwd() / "build" / "all-translated-exchange.json"),
            "JSON Files (*.json)",
        )
        if not output_path:
            return
        try:
            report = self._run_with_progress(
                self._tr("dialog.progress_title"),
                self._tr("progress.export_all_translated"),
                lambda: export_all_translated(catalog, Path(output_path)),
            )
        except Exception as exc:
            self._show_error(self._tr("error.export_all_translated_failed").format(error=exc))
            return
        self._set_status(
            self._tr("status.export_all_translated").format(exported=report.exported_entries)
            + f": {output_path}"
        )

    def _import_translation_exchange(self) -> None:
        catalog = self._current_catalog()
        if catalog is None:
            self._show_error(self._tr("error.load_first"))
            return
        input_path, _ = QFileDialog.getOpenFileName(
            self,
            self._tr("btn.import_exchange"),
            str(Path.cwd() / "build"),
            "JSON Files (*.json)",
        )
        if not input_path:
            return
        try:
            merged = self._run_with_progress(
                self._tr("dialog.progress_title"),
                self._tr("progress.import_translation"),
                lambda: import_exchange(catalog, Path(input_path)),
            )
        except Exception as exc:
            self._show_error(self._tr("error.import_failed").format(error=exc))
            return
        merged = apply_mod_overrides(apply_known_term_suggestions(merged, target_language=self._target_lang_code))
        if self._paired_catalog is not None:
            self._paired_catalog = merged
        else:
            self._source_catalog = merged
        self._refresh_mod_override_entries()
        self._refresh_table()
        manual_count = sum(1 for unit in merged.units if unit.status == RelocalizationStatus.MANUAL_TRANSLATION)
        if self._lang == "en":
            self._set_status(f"{manual_count} manual translations loaded: {input_path}")
        else:
            self._set_status(f"{manual_count} manuelle Übersetzungen geladen: {input_path}")

    def _copy_reference_audio_files(self) -> None:
        resolved = self._resolve_source_and_reference_installs()
        if resolved is None:
            return
        source_install, reference_install = resolved
        candidates = self._writer.list_audio_copy_candidates(source_install, reference_install)
        if not candidates:
            self._show_error(self._tr("error.no_audio_candidates"))
            return
        reply = QMessageBox.question(
            self,
            self._tr("dialog.copy_audio_title"),
            self._tr("dialog.copy_audio_offer").format(
                count=len(candidates),
                backup=self._writer.backup_root(source_install),
            ),
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Yes,
        )
        if reply != QMessageBox.Yes:
            return
        self._copy_reference_audio_candidates(source_install, reference_install, candidates)

    def _copy_reference_audio_candidates(
        self,
        source_install: Path,
        reference_install: Path,
        candidates,
        *,
        backup_dir: Path | None = None,
    ) -> int:
        try:
            report = self._run_with_progress(
                self._tr("dialog.copy_audio_title"),
                self._tr("progress.copy_audio"),
                lambda: self._writer.copy_reference_audio(
                    source_install,
                    reference_install,
                    candidates=tuple(candidates),
                    backup_dir=backup_dir,
                ),
            )
        except Exception as exc:
            self._show_error(self._tr("error.audio_copy_failed").format(error=exc))
            return 0
        QMessageBox.information(
            self,
            self._tr("dialog.copy_audio_title"),
            self._tr("dialog.copy_audio_success").format(
                count=len(report.copied_files),
                backup=report.backup_dir,
            ),
        )
        self._invalidate_audio_progress_cache()
        self._set_status(self._tr("status.audio_copied").format(count=len(report.copied_files)))
        return len(report.copied_files)

    def _merge_utf_audio_files(self) -> None:
        resolved = self._resolve_source_and_reference_installs()
        if resolved is None:
            return
        source_install, reference_install = resolved

        # Use en_ref_edit if available; otherwise ask via dialog
        en_ref_path = ""
        if hasattr(self, "en_ref_edit"):
            en_ref_path = self.en_ref_edit.text().strip()
        if not en_ref_path and hasattr(self, "simple_en_ref_edit"):
            en_ref_path = self.simple_en_ref_edit.text().strip()
        if not en_ref_path:
            en_ref_path = QFileDialog.getExistingDirectory(
                self,
                self._tr("dialog.merge_utf_audio_en_ref"),
                str(source_install.parent),
            )
        if not en_ref_path:
            return
        reference_en = Path(en_ref_path)

        candidates = self._writer.list_utf_audio_merge_candidates(
            source_install, reference_en, reference_install,
        )
        if not candidates:
            self._show_error(self._tr("error.no_utf_merge_candidates"))
            return

        total_replaceable = sum(c.replaceable_count for c in candidates)
        reply = QMessageBox.question(
            self,
            self._tr("dialog.merge_utf_audio_title"),
            self._tr("dialog.merge_utf_audio_offer").format(
                count=len(candidates),
                replaceable=total_replaceable,
                backup=self._writer.backup_root(source_install),
            ),
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Yes,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            report = self._run_with_progress(
                self._tr("dialog.merge_utf_audio_title"),
                self._tr("progress.merge_utf_audio"),
                lambda: self._writer.merge_utf_audio(
                    source_install, reference_en, reference_install,
                    candidates=candidates,
                ),
            )
        except Exception as exc:
            self._show_error(self._tr("error.utf_merge_failed").format(error=exc))
            return

        QMessageBox.information(
            self,
            self._tr("dialog.merge_utf_audio_title"),
            self._tr("dialog.merge_utf_audio_success").format(
                files=len(report.merged_files),
                replaced=report.total_replaced,
                kept=report.total_kept,
                backup=report.backup_dir,
            ),
        )
        self._set_status(self._tr("status.utf_merge_done").format(
            replaced=report.total_replaced,
            files=len(report.merged_files),
        ))

    def _assemble_patch_bundle(self) -> None:
        resolved = self._resolve_source_and_reference_installs()
        if resolved is None:
            return
        source_install, reference_install = resolved
        dll_paths = tuple(
            sorted(
                {unit.source.dll_path for unit in self._apply_candidate_units()},
                key=lambda path: path.name.lower(),
            )
        )
        audio_candidates = self._writer.list_audio_copy_candidates(source_install, reference_install)

        output_path = QFileDialog.getExistingDirectory(
            self,
            self._tr("dialog.assemble_patch_title"),
            str(Path.cwd() / "build" / "patch-package"),
        )
        if not output_path:
            return
        try:
            report = self._run_with_progress(
                self._tr("dialog.assemble_patch_title"),
                self._tr("progress.assemble_patch"),
                lambda: self._writer.assemble_install_patch(
                    source_install,
                    Path(output_path),
                    dll_paths=dll_paths,
                    audio_candidates=audio_candidates,
                ),
            )
        except RuntimeError as exc:
            message = str(exc)
            if "No files available" in message:
                self._show_error(self._tr("error.no_patch_files"))
            else:
                self._show_error(self._tr("error.patch_assemble_failed").format(error=exc))
            return
        except Exception as exc:
            self._show_error(self._tr("error.patch_assemble_failed").format(error=exc))
            return
        QMessageBox.information(
            self,
            self._tr("dialog.assemble_patch_title"),
            self._tr("dialog.assemble_patch_success").format(
                count=len(report.copied_files),
                path=report.output_dir,
                manifest=report.manifest_path,
            ),
        )
        self._set_status(self._tr("status.patch_assembled").format(path=report.output_dir))

    def _apply_target_to_install(self) -> None:
        if self._apply_active:
            return
        catalog = self._paired_catalog
        if catalog is None:
            self._show_error(self._tr("error.compare_first"))
            return
        if not self._writer.has_toolchain():
            self._show_error(self._tr("error.toolchain_missing"))
            return
        catalog = self._catalog_with_selected_old_text_overrides(catalog)
        units = [
            unit
            for unit in catalog.units
            if unit.status in {RelocalizationStatus.AUTO_RELOCALIZE, RelocalizationStatus.MANUAL_TRANSLATION}
        ]
        if not units:
            self._show_error(self._tr("error.no_apply_units"))
            return
        session = self._writer.load_apply_session(catalog, units=units)
        preview_box = QMessageBox(self)
        preview_box.setIcon(QMessageBox.Question)
        preview_box.setWindowTitle(self._tr("dialog.apply_preview"))
        _localized, done, skipped, total, _percent, covered_percent, _manual, _terminology = self._translation_progress()
        confirm_key = "dialog.apply_confirm_resume" if session is not None and session.pending_dlls else "dialog.apply_confirm"
        confirm_payload = {
            "count": len(units),
            "covered_percent": covered_percent,
            "covered": done + skipped,
            "total": total,
        }
        if session is not None and session.pending_dlls:
            confirm_payload.update(
                {
                    "next_dll": session.pending_dlls[0],
                    "done": len(session.completed_dlls),
                    "dll_total": session.total_dlls,
                }
            )
        preview_box.setText(self._tr(confirm_key).format(**confirm_payload))
        preview_box.setDetailedText(self._build_apply_preview(units))
        preview_box.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        preview_box.setDefaultButton(QMessageBox.Yes)
        reply = preview_box.exec()
        if reply != QMessageBox.Yes:
            return
        self._start_apply_worker(catalog, units)

    def _install_toolchain(self) -> None:
        try:
            script_path = self._writer.launch_toolchain_installer()
        except Exception as exc:
            self._show_error(self._tr("error.toolchain_start_failed").format(error=exc))
            return
        QMessageBox.information(self, self._tr("dialog.toolchain_title"), self._tr("dialog.toolchain_started").format(path=script_path))
        self._set_status(self._tr("status.toolchain_started"))
        self.toolchain_label.setText(f"Resource-Toolchain: {self._tr('status.toolchain_started')}")

    def _open_terminology_file(self) -> None:
        try:
            terminology_path = resolve_terminology_file(self._target_lang_code)
            clear_term_map_cache()
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(terminology_path))):
                raise RuntimeError(f"Could not open file: {terminology_path}")
        except Exception as exc:
            self._show_error(self._tr("error.terminology_open_failed").format(error=exc))
            return
        self._set_status(self._tr("status.terminology_opened").format(path=terminology_path))

    def _open_settings_dialog(self) -> None:
        dialog = self._settings_dialog_class(self._theme, self)
        if dialog.exec() != QDialog.Accepted:
            return
        self._theme = dialog.selected_theme
        self._save_persistent_settings()
        self._apply_theme()
        self._retranslate_ui()
        self._set_status(self._tr("status.settings_applied"))

    def _open_translation_rules_dialog(self) -> None:
        from .ui_dialogs import TranslationRulesDialog
        from .translation_rules import set_active_rules

        rules = getattr(self, "_translation_rules", None)
        if rules is None:
            from .translation_rules import TranslationRules
            rules = TranslationRules()
        dlg = TranslationRulesDialog(rules, self._tr, parent=self)
        if dlg.exec() != QDialog.Accepted or dlg.result_rules is None:
            return
        self._translation_rules = dlg.result_rules
        # Reload ship names with current source path
        source_path = self.source_edit.text().strip() if hasattr(self, "source_edit") else ""
        if source_path:
            self._translation_rules.load_ship_name_ids(Path(source_path))
        set_active_rules(self._translation_rules)
        self._save_persistent_settings()
        self._refresh_table()
        self._update_action_state()
        self._set_status(self._tr("status.settings_applied"))

    def _set_language(self, language_code: str) -> None:
        new_lang = str(language_code or "").strip().lower()
        if new_lang == self._lang:
            return
        self._lang = new_lang
        self._save_persistent_settings()
        self._retranslate_ui()
        self._set_status(self._tr("status.language_changed"))
        self._offer_ui_auto_translate(new_lang)

    # ---- UI auto-translation -------------------------------------------------

    _UI_TRANSLATE_THRESHOLD = 100  # strings needed to count as "translated"

    def _has_real_translation(self, lang: str) -> bool:
        """Return True if *lang* has significantly more strings than the EN fallback."""
        from .ui_strings import STRINGS
        en = STRINGS.get("en", {})
        current = STRINGS.get(lang, {})
        diff = sum(1 for k, v in current.items() if en.get(k) != v)
        return diff >= self._UI_TRANSLATE_THRESHOLD

    def _offer_ui_auto_translate(self, lang: str) -> None:
        """If *lang* has no real translation, ask the user and translate via Google."""
        if lang == "en":
            return
        if self._has_real_translation(lang):
            return
        label = lang
        for code, name in LANGUAGE_OPTIONS:
            if code == lang:
                label = name
                break
        reply = QMessageBox.question(
            self,
            self._tr("dialog.auto_ui_translate_title"),
            self._tr("dialog.auto_ui_translate_body").format(language=label),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply != QMessageBox.Yes:
            return
        self._run_ui_auto_translate(lang)

    def _run_ui_auto_translate(self, target_lang: str) -> None:
        """Translate all EN UI strings into *target_lang* using GoogleTranslator."""
        from .ui_strings import STRINGS
        from .translator_service import translate_text

        en_strings = STRINGS.get("en", {})
        keys = list(en_strings.keys())
        total = len(keys)
        if total == 0:
            return

        progress = QProgressDialog(
            self._tr("dialog.auto_ui_progress").format(done=0, total=total),
            self._tr("btn.cancel"),
            0,
            total,
            self,
        )
        progress.setWindowTitle(self._tr("dialog.auto_ui_translate_title"))
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)

        translated: dict[str, str] = {}
        errors = 0
        for i, key in enumerate(keys):
            if progress.wasCanceled():
                break
            source_text = en_strings[key]
            if not source_text.strip():
                translated[key] = source_text
            else:
                try:
                    translated[key] = translate_text(source_text, "en", target_lang)
                except Exception:
                    translated[key] = source_text
                    errors += 1
            progress.setValue(i + 1)
            progress.setLabelText(
                self._tr("dialog.auto_ui_progress").format(done=i + 1, total=total)
            )
            QApplication.processEvents()

        progress.close()

        if not translated:
            return

        # Merge into STRINGS
        if target_lang not in STRINGS:
            STRINGS[target_lang] = dict(en_strings)
        STRINGS[target_lang].update(translated)

        # Persist to Languages/ dir
        try:
            lang_dir = resolve_languages_dir()
            lang_dir.mkdir(parents=True, exist_ok=True)
            out_file = lang_dir / f"ui.{target_lang}.json"
            out_file.write_text(
                json.dumps(translated, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass  # non-critical, strings are in memory already

        self._retranslate_ui()
        status = self._tr("status.ui_auto_translated").format(
            count=len(translated), errors=errors
        )
        self._set_status(status)

    @staticmethod
    def _normalize_version_tuple(version_text: str) -> tuple[int, ...]:
        parts = re.findall(r"\d+", str(version_text or ""))
        return tuple(int(part) for part in parts)

    def _fetch_latest_release_info(self) -> tuple[bool, dict[str, object] | None, str]:
        req = urlrequest.Request(
            self._latest_release_api,
            headers={"Accept": "application/vnd.github+json", "User-Agent": "FL-Lingo-Updater"},
        )

        def _api_try(context=None) -> dict[str, object] | None:
            with urlrequest.urlopen(req, timeout=12.0, context=context) as resp:
                payload = json.loads(resp.read().decode("utf-8", errors="replace"))
            if isinstance(payload, dict) and str(payload.get("tag_name", "")).strip():
                assets_raw = payload.get("assets") or []
                assets = []
                if isinstance(assets_raw, list):
                    for a in assets_raw:
                        if isinstance(a, dict):
                            name = str(a.get("name", "")).strip()
                            url = str(a.get("browser_download_url", "")).strip()
                            if name and url:
                                assets.append({"name": name, "browser_download_url": url})
                return {
                    "tag_name": str(payload.get("tag_name", "")).strip(),
                    "html_url": str(payload.get("html_url", "")).strip() or self._repo_url,
                    "assets": assets,
                }
            return None

        try:
            info = _api_try()
            if info is not None:
                return True, info, ""
        except Exception:
            pass

        try:
            insecure_ctx = ssl._create_unverified_context()
            info = _api_try(context=insecure_ctx)
            if info is not None:
                return True, info, ""
        except Exception:
            pass

        try:
            fallback_req = urlrequest.Request(
                self._latest_release_url,
                headers={"User-Agent": "FL-Lingo-Updater"},
            )
            try:
                resp = urlrequest.urlopen(fallback_req, timeout=12.0)
            except Exception:
                insecure_ctx = ssl._create_unverified_context()
                resp = urlrequest.urlopen(fallback_req, timeout=12.0, context=insecure_ctx)
            with resp:
                final_url = str(resp.geturl() or "").strip()
            match = re.search(r"/releases/tag/([^/?#]+)", final_url)
            if match:
                return True, {"tag_name": match.group(1).strip(), "html_url": final_url}, ""
        except Exception as exc:
            return False, None, self._tr("error.update_check_failed").format(error=exc)

        return False, None, self._tr("error.update_check_failed").format(error=self._tr("updates.version_parse_failed"))

    def _check_for_updates_manual(self) -> None:
        self._set_status(self._tr("status.update_check_started"))
        ok, info, error = self._fetch_latest_release_info()
        if not ok or info is None:
            self._show_error(error)
            return
        self._handle_update_result(info, manual=True)

    def _startup_update_check(self) -> None:
        ok, info, _error = self._fetch_latest_release_info()
        if ok and info is not None:
            self._handle_update_result(info, manual=False)

    def _handle_update_result(self, info: dict[str, object], *, manual: bool) -> None:
        latest_tag = str(info.get("tag_name", "") or "").strip()
        latest_url = str(info.get("html_url", "") or "").strip() or self._repo_url
        current = self._normalize_version_tuple(self._config.app_version)
        latest = self._normalize_version_tuple(latest_tag)
        if not latest:
            if manual:
                QMessageBox.information(self, self._tr("updates.title"), self._tr("updates.version_parse_failed"))
            return
        if latest <= current:
            if manual:
                QMessageBox.information(
                    self,
                    self._tr("updates.title"),
                    self._tr("updates.up_to_date").format(version=self._config.app_version),
                )
            return
        suppressed_tag = str(self._settings.value("updates/suppressed_tag", "") or "").strip().lower()
        if (not manual) and suppressed_tag == latest_tag.lower():
            return
        self._show_update_available_dialog(latest_tag, latest_url, info=info, manual=manual)

    # ------------------------------------------------------------------
    # Self-update helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_packaged_windows_release() -> bool:
        """Return True when running as a frozen PyInstaller .exe on Windows."""
        return getattr(sys, "frozen", False) and sys.platform == "win32"

    @staticmethod
    def _select_release_asset(assets: list[dict[str, str]]) -> dict[str, str] | None:
        """Pick the best asset from a GitHub release for Windows self-update.

        Preference order:
        1. .zip whose name contains 'windows' or 'win'
        2. Any .zip
        3. .exe whose name contains 'setup' / 'install' / 'windows'
        """
        zips_win = [a for a in assets if a["name"].lower().endswith(".zip") and re.search(r"win|windows", a["name"], re.I)]
        if zips_win:
            return zips_win[0]
        zips_any = [a for a in assets if a["name"].lower().endswith(".zip")]
        if zips_any:
            return zips_any[0]
        exes = [a for a in assets if a["name"].lower().endswith(".exe") and re.search(r"setup|install|win", a["name"], re.I)]
        if exes:
            return exes[0]
        return None

    def _download_url_to_file(self, url: str, dest: Path, *, progress_cb=None) -> None:
        """Download *url* to *dest*, calling *progress_cb(percent)* periodically."""
        req = urlrequest.Request(url, headers={"User-Agent": "FL-Lingo-Updater"})
        try:
            resp = urlrequest.urlopen(req, timeout=120)
        except Exception:
            ctx = ssl._create_unverified_context()
            resp = urlrequest.urlopen(req, timeout=120, context=ctx)
        with resp:
            total = int(resp.headers.get("Content-Length", 0) or 0)
            downloaded = 0
            block_size = 1 << 16  # 64 KiB
            with open(dest, "wb") as fh:
                while True:
                    chunk = resp.read(block_size)
                    if not chunk:
                        break
                    fh.write(chunk)
                    downloaded += len(chunk)
                    if progress_cb and total > 0:
                        progress_cb(int(downloaded * 100 / total))

    def _start_frozen_windows_self_update(self, info: dict[str, object]) -> None:
        """Download the release asset, extract if needed, launch the updater, and quit."""
        assets = info.get("assets") or []
        asset = self._select_release_asset(assets)
        if asset is None:
            QMessageBox.warning(self, self._tr("updates.title"), self._tr("updates.no_asset"))
            return

        download_url = asset["browser_download_url"]
        asset_name = asset["name"]
        timestamp = int(time.time())
        temp_dir = Path(tempfile.gettempdir())

        archive_path = temp_dir / f"fllingo_update_{timestamp}_{asset_name}"

        # Show a progress dialog while downloading
        self._set_status(self._tr("status.update_downloading"))
        progress = QProgressDialog(self._tr("updates.download_progress").format(percent=0), "", 0, 100, self)
        progress.setWindowTitle(self._tr("updates.title"))
        progress.setCancelButton(None)
        progress.setMinimumDuration(0)
        progress.setAutoClose(True)
        progress.show()
        QApplication.processEvents()

        def _update_progress(pct: int) -> None:
            progress.setValue(pct)
            progress.setLabelText(self._tr("updates.download_progress").format(percent=pct))
            QApplication.processEvents()

        try:
            self._download_url_to_file(download_url, archive_path, progress_cb=_update_progress)
        except Exception as exc:
            progress.close()
            QMessageBox.critical(self, self._tr("updates.title"), self._tr("updates.download_failed").format(error=exc))
            return
        progress.close()

        # Determine mode
        is_zip = asset_name.lower().endswith(".zip")
        mode = "zip" if is_zip else "installer"
        extract_root: Path | None = None

        if is_zip:
            extract_root = temp_dir / f"fllingo_update_extract_{timestamp}"
            try:
                with zipfile.ZipFile(archive_path, "r") as zf:
                    zf.extractall(extract_root)
            except Exception as exc:
                QMessageBox.critical(self, self._tr("updates.title"), self._tr("updates.extract_failed").format(error=exc))
                return

        # Resolve paths
        exe_path = Path(sys.executable).resolve()
        install_root = exe_path.parent
        updater_name = "FLLingoUpdater.exe"
        updater_exe = install_root / updater_name
        if not updater_exe.exists():
            updater_exe = install_root / "_internal" / updater_name

        # Build the command that launches the updater after a short delay
        cmd_parts = [
            f'"{updater_exe}"',
            f"--mode {mode}",
            f"--wait-pid {os.getpid()}",
            f'--install-root "{install_root}"',
            f'--archive-path "{archive_path}"',
            f'--exe-path "{exe_path}"',
        ]
        if extract_root is not None:
            cmd_parts.append(f'--extract-root "{extract_root}"')

        cmd_script = temp_dir / f"fllingo_update_{timestamp}.cmd"
        cmd_script.write_text(
            "@echo off\n"
            f"timeout /t 2 /nobreak >nul\n"
            f"{' '.join(cmd_parts)}\n"
            f"del \"%~f0\"\n",
            encoding="utf-8",
        )

        CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            subprocess.Popen(
                ["cmd.exe", "/c", str(cmd_script)],
                creationflags=CREATE_NO_WINDOW,
                close_fds=True,
            )
        except Exception as exc:
            QMessageBox.critical(self, self._tr("updates.title"), self._tr("updates.launch_failed"))
            return

        self._set_status(self._tr("status.update_installing"))
        from PySide6.QtCore import QTimer
        QTimer.singleShot(150, QApplication.instance().quit)

    def _show_update_available_dialog(self, latest_tag: str, latest_url: str, *, info: dict[str, object] | None = None, manual: bool) -> None:
        can_self_update = self._is_packaged_windows_release() and info is not None and self._select_release_asset(info.get("assets") or []) is not None

        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Information)
        dialog.setWindowTitle(self._tr("updates.title"))
        dialog.setText(
            self._tr("updates.available").format(
                current=self._config.app_version,
                latest=latest_tag,
            )
        )
        if can_self_update:
            dialog.setInformativeText(self._tr("updates.available_info_install"))
        else:
            dialog.setInformativeText(self._tr("updates.available_info"))
        install_button = None
        if can_self_update:
            install_button = dialog.addButton(self._tr("updates.install_update"), QMessageBox.YesRole)
        open_button = dialog.addButton(self._tr("updates.open_release"), QMessageBox.AcceptRole)
        dialog.addButton(QMessageBox.Close)
        dialog.exec()
        clicked = dialog.clickedButton()
        if clicked is install_button and info is not None:
            self._settings.setValue("updates/suppressed_tag", "")
            self._start_frozen_windows_self_update(info)
            return
        if clicked is open_button:
            QDesktopServices.openUrl(QUrl(latest_url))
            self._settings.setValue("updates/suppressed_tag", "")
            return
        if not manual:
            self._settings.setValue("updates/suppressed_tag", latest_tag)

    def _show_about_dialog(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(self._tr("dialog.about.title"))
        dialog.resize(520, 320)
        layout = QVBoxLayout(dialog)
        body = QLabel(
            self._tr("dialog.about.body").format(
                version=self._config.app_version,
                developed_by=self._config.developed_by,
                github=self._repo_url,
                discord=self._discord_url,
            )
        )
        body.setWordWrap(True)
        body.setTextFormat(Qt.RichText)
        body.setOpenExternalLinks(True)
        layout.addWidget(body)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)
        dialog.exec()

    def _show_help_dialog(self) -> None:
        help_urls = {
            "de": "https://github.com/flathack/FL-Lingo/wiki/Hilfe-%E2%80%90-DE",
            "en": "https://github.com/flathack/FL-Lingo/wiki/Help-%E2%80%90-EN",
        }
        lang = self._lang if self._lang in help_urls else "en"
        url = help_urls[lang]
        QDesktopServices.openUrl(QUrl(url))

    def _run_with_progress(self, title: str, label: str, callback):
        progress = QProgressDialog(label, "", 0, 0, self)
        progress.setWindowTitle(title)
        progress.setCancelButton(None)
        progress.setMinimumDuration(0)
        progress.setAutoClose(True)
        progress.setAutoReset(True)
        progress.show()
        if hasattr(self, "global_progress_bar"):
            self.global_progress_bar.setVisible(True)
        QApplication.processEvents()
        try:
            return callback()
        finally:
            progress.close()
            if hasattr(self, "global_progress_bar"):
                self.global_progress_bar.setVisible(False)

    # ------------------------------------------------------------------
    # Troubleshooting: Fix XML Tags  (3-step workflow)
    # ------------------------------------------------------------------

    def _run_fix_xml_scan(self) -> None:
        """Step 1 – scan DLLs for broken line endings in RT_HTML infocards."""
        source_dir = self.source_edit.text().strip() if hasattr(self, "source_edit") else ""
        initial_dir = str(Path(source_dir) / "EXE") if source_dir and Path(source_dir).is_dir() else ""
        exe_dir = QFileDialog.getExistingDirectory(
            self,
            self._tr("troubleshoot.fix_xml.select_dir"),
            initial_dir,
        )
        if not exe_dir:
            return

        exe_path = Path(exe_dir)
        self.fix_xml_scan_result_label.setText(self._tr("troubleshoot.fix_xml.scan_running"))
        self.fix_xml_repair_button.setEnabled(False)
        self.fix_xml_apply_button.setEnabled(False)
        self.fix_xml_repair_result_label.setText("")
        self.fix_xml_apply_result_label.setText("")
        QApplication.processEvents()

        try:
            scan_results = self._writer.scan_xml_line_endings(exe_path)
        except Exception as exc:
            self.fix_xml_scan_result_label.setText(
                self._tr("troubleshoot.fix_xml.scan_error").format(error=str(exc))
            )
            self._set_status(self._tr("status.operation_failed"))
            return

        total_broken = sum(len(v) for v in scan_results.values())
        if total_broken == 0:
            self.fix_xml_scan_result_label.setText(self._tr("troubleshoot.fix_xml.scan_ok"))
            self._set_status(self._tr("troubleshoot.fix_xml.scan_ok"))
            return

        self._fix_xml_exe_dir = exe_path
        self._fix_xml_scan_results = scan_results
        self.fix_xml_scan_result_label.setText(
            self._tr("troubleshoot.fix_xml.scan_result").format(
                count=total_broken, dlls=len(scan_results),
            )
        )
        self.fix_xml_repair_button.setEnabled(True)
        self._set_status(
            self._tr("troubleshoot.fix_xml.scan_result").format(
                count=total_broken, dlls=len(scan_results),
            )
        )

    def _run_fix_xml_repair(self) -> None:
        """Step 2 – verify scan results and save the project."""
        scan_results = getattr(self, "_fix_xml_scan_results", None)
        if not scan_results:
            return

        self.fix_xml_repair_button.setEnabled(False)
        self.fix_xml_progress_bar.setVisible(True)
        self.fix_xml_progress_bar.setValue(50)
        QApplication.processEvents()

        total_fixed = sum(len(v) for v in scan_results.values())

        # save project
        if self._project_path is not None:
            self._save_project_file()

        self.fix_xml_progress_bar.setValue(100)
        self.fix_xml_repair_result_label.setText(
            self._tr("troubleshoot.fix_xml.repair_done").format(count=total_fixed)
        )
        self.fix_xml_apply_button.setEnabled(True)
        self._set_status(
            self._tr("troubleshoot.fix_xml.repair_done").format(count=total_fixed)
        )

    def _run_fix_xml_apply(self) -> None:
        """Step 3 – write corrected resources to the DLL files."""
        exe_dir = getattr(self, "_fix_xml_exe_dir", None)
        scan_results = getattr(self, "_fix_xml_scan_results", None)
        if not scan_results or exe_dir is None:
            return

        self.fix_xml_apply_button.setEnabled(False)
        self.fix_xml_progress_bar.setValue(0)
        self.fix_xml_progress_bar.setVisible(True)
        QApplication.processEvents()

        try:
            total_fixed = 0
            total_dlls = 0

            def _on_progress(info: dict) -> None:
                nonlocal total_fixed, total_dlls
                total_fixed = info["total_fixed"]
                total_dlls += 1
                pct = int(total_dlls / len(scan_results) * 100)
                self.fix_xml_progress_bar.setValue(min(pct, 100))
                QApplication.processEvents()

            fixed, dlls, backup_dir = self._writer.repair_xml_line_endings(
                exe_dir, progress_callback=_on_progress,
            )

            self.fix_xml_progress_bar.setValue(100)
            self.fix_xml_apply_result_label.setText(
                self._tr("troubleshoot.fix_xml.apply_done").format(
                    count=fixed, dlls=dlls, backup=backup_dir,
                )
            )
            self._set_status(
                self._tr("troubleshoot.fix_xml.apply_done").format(
                    count=fixed, dlls=dlls, backup=backup_dir,
                )
            )
        except Exception as exc:
            self.fix_xml_apply_result_label.setText(
                self._tr("troubleshoot.fix_xml.apply_error").format(error=str(exc))
            )
            self._set_status(self._tr("status.operation_failed"))

