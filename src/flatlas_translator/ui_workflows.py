"""Workflow and dialog mixin for FL Lingo main window."""

from __future__ import annotations

import json
import re
import ssl
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
from .localization import resolve_help_file
from .mod_overrides import apply_mod_overrides
from .models import RelocalizationStatus, ResourceCatalog, ResourceKind, TranslationUnit
from .project_io import PROJECT_FILE_EXTENSION, load_project, project_signature, save_project
from .terminology import apply_known_term_suggestions, clear_term_map_cache, resolve_terminology_file
from .translation_exchange import export_long_open_exchange, export_mod_only_exchange, import_exchange


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
        _localized, done, skipped, total, _percent, covered_percent = self._translation_progress()
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

    def _set_language(self, language_code: str) -> None:
        new_lang = str(language_code or "").strip().lower()
        if new_lang == self._lang:
            return
        self._lang = new_lang
        self._save_persistent_settings()
        self._retranslate_ui()
        self._set_status(self._tr("status.language_changed"))

    @staticmethod
    def _normalize_version_tuple(version_text: str) -> tuple[int, ...]:
        parts = re.findall(r"\d+", str(version_text or ""))
        return tuple(int(part) for part in parts)

    def _fetch_latest_release_info(self) -> tuple[bool, dict[str, str] | None, str]:
        req = urlrequest.Request(
            self._latest_release_api,
            headers={"Accept": "application/vnd.github+json", "User-Agent": "FL-Lingo-Updater"},
        )

        def _api_try(context=None) -> dict[str, str] | None:
            with urlrequest.urlopen(req, timeout=12.0, context=context) as resp:
                payload = json.loads(resp.read().decode("utf-8", errors="replace"))
            if isinstance(payload, dict) and str(payload.get("tag_name", "")).strip():
                return {
                    "tag_name": str(payload.get("tag_name", "")).strip(),
                    "html_url": str(payload.get("html_url", "")).strip() or self._repo_url,
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

    def _handle_update_result(self, info: dict[str, str], *, manual: bool) -> None:
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
        self._show_update_available_dialog(latest_tag, latest_url, manual=manual)

    def _show_update_available_dialog(self, latest_tag: str, latest_url: str, *, manual: bool) -> None:
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Information)
        dialog.setWindowTitle(self._tr("updates.title"))
        dialog.setText(
            self._tr("updates.available").format(
                current=self._config.app_version,
                latest=latest_tag,
            )
        )
        dialog.setInformativeText(self._tr("updates.available_info"))
        open_button = dialog.addButton(self._tr("updates.open_release"), QMessageBox.AcceptRole)
        dialog.addButton(QMessageBox.Close)
        dialog.exec()
        if dialog.clickedButton() is open_button:
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
        try:
            help_path = resolve_help_file(self._lang if self._lang in ("de", "en") else "en")
            help_html = help_path.read_text(encoding="utf-8")
        except Exception as exc:
            self._show_error(self._tr("error.help_open_failed").format(error=exc))
            return
        dialog = QDialog(self)
        dialog.setWindowTitle(self._tr("dialog.help.title"))
        dialog.resize(980, 760)
        layout = QVBoxLayout(dialog)
        browser = QTextBrowser(dialog)
        browser.setOpenExternalLinks(True)
        browser.setHtml(help_html)
        layout.addWidget(browser)
        buttons = QDialogButtonBox(QDialogButtonBox.Close, dialog)
        buttons.rejected.connect(dialog.reject)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)
        dialog.exec()

    def _run_with_progress(self, title: str, label: str, callback):
        progress = QProgressDialog(label, "", 0, 0, self)
        progress.setWindowTitle(title)
        progress.setCancelButton(None)
        progress.setMinimumDuration(0)
        progress.setAutoClose(True)
        progress.setAutoReset(True)
        progress.show()
        QApplication.processEvents()
        try:
            return callback()
        finally:
            progress.close()
