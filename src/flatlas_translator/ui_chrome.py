"""Window chrome and UI retranslation helpers for FL Lingo."""

from __future__ import annotations

from .ui_strings import DISCORD_INVITE_URL, GITHUB_REPO_URL


class UIChromeMixin:
    @staticmethod
    def _safe_format(template: str, **values: object) -> str:
        try:
            return str(template).format(**values)
        except Exception:
            fallback = "{name} | {dirty}"
            try:
                return fallback.format(**values)
            except Exception:
                return str(values.get("name", ""))

    def _retranslate_ui(self) -> None:
        self.menuBar().clear()
        self._setup_menu_bar()
        self._refresh_window_title()
        self.simple_paths_group.setTitle(self._tr("simple.group.paths"))
        self.simple_scan_group.setTitle(self._tr("simple.group.scan"))
        self.simple_translate_group.setTitle(self._tr("simple.group.translate"))
        self.mode_switch_label.setText(f"{self._tr('mode.simple')} / {self._tr('mode.expert')}")
        self.simple_mode_button.setText(self._tr("mode.simple"))
        self.expert_mode_button.setText(self._tr("mode.expert"))
        self.simple_paths_help_label.setText(self._tr("simple.paths.help"))
        self.simple_scan_help_label.setText(self._tr("simple.scan.help"))
        self.simple_translate_help_label.setText(self._tr("simple.translate.help"))
        self.simple_source_label.setText(self._tr("simple.label.mod_install"))
        self.simple_target_label.setText(self._tr("simple.label.reference_install"))
        self.simple_source_browse_button.setText(self._tr("btn.browse"))
        self.simple_target_browse_button.setText(self._tr("btn.browse"))
        self.simple_scan_button.setText(self._tr("simple.btn.scan"))
        self.simple_progress_legend_label.setText(self._tr("progress.legend"))
        self.simple_translate_button.setText(self._tr("btn.apply_target"))
        self.simple_audio_copy_check.setText(self._tr("simple.audio_copy"))
        self.paths_group.setTitle(self._tr("group.installs"))
        self.simple_scan_summary_label.setText(self._tr("simple.summary.idle"))
        self.progress_group.setTitle(self._tr("group.progress"))
        self.main_actions_group.setTitle(self._tr("group.main_actions"))
        self.apply_execution_group.setTitle(self._tr("group.apply_execution"))
        self.filters_group.setTitle(self._tr("group.filters"))
        self.dll_group.setTitle(self._tr("group.dll_analysis"))
        self.editor_help_label.setText(self._tr("editor.help"))
        self.old_text_source_label.setText(self._tr("editor.old_text_source"))
        self.mod_overrides_help_label.setText(self._tr("mod_overrides.help"))
        self.mod_overrides_reload_button.setText(self._tr("btn.mod_overrides_reload"))
        self.mod_overrides_delete_button.setText(self._tr("btn.mod_overrides_delete"))
        self.terminology_map_group.setTitle(self._tr("group.terminology_map"))
        self.terminology_manage_group.setTitle(self._tr("group.terminology_manage"))
        self.term_source_label.setText(self._tr("label.term_source"))
        self.term_target_label.setText(self._tr("label.term_target"))
        self.pattern_source_label.setText(self._tr("label.pattern_source"))
        self.pattern_target_label.setText(self._tr("label.pattern_target"))
        self.term_from_selection_button.setText(self._tr("btn.term_from_selection"))
        self.term_save_button.setText(self._tr("btn.term_save"))
        self.pattern_save_button.setText(self._tr("btn.pattern_save"))
        self.terminology_reload_button.setText(self._tr("btn.terminology_reload"))
        self.source_install_label.setText(self._tr("label.source_install"))
        self.target_install_label.setText(self._tr("label.target_install"))
        self.source_lang_label.setText(self._tr("label.source_language"))
        self.target_lang_label.setText(self._tr("label.target_language"))
        self.browse_source_button.setText(self._tr("btn.browse"))
        self.browse_target_button.setText(self._tr("btn.browse"))
        self.source_lang_edit.setToolTip(self._tr("tooltip.source_language"))
        self.target_lang_edit.setToolTip(self._tr("tooltip.target_language"))
        self.include_infocards_check.setText(self._tr("check.infocards"))
        self.load_source_button.setText(self._tr("btn.load_source"))
        self.compare_button.setText(self._tr("btn.compare"))
        self.export_button.setText(self._tr("btn.export_visible"))
        self.export_mod_only_button.setText(self._tr("btn.export_mod_only"))
        self.export_long_open_button.setText(self._tr("btn.export_long_open"))
        self.import_exchange_button.setText(self._tr("btn.import_exchange"))
        self.copy_audio_button.setText(self._tr("btn.copy_audio"))
        self.assemble_patch_button.setText(self._tr("btn.assemble_patch"))
        self.apply_button.setText(self._tr("btn.apply_target"))
        self.primary_apply_button.setText(self._tr("btn.apply_target"))
        self.toolchain_button.setText(self._tr("btn.install_toolchain"))
        self.main_export_button.setText(self._tr("btn.export_mod_only"))
        self.main_long_export_button.setText(self._tr("btn.export_long_open"))
        self.main_import_button.setText(self._tr("btn.import_exchange"))
        self.main_copy_audio_button.setText(self._tr("btn.copy_audio"))
        self.main_patch_button.setText(self._tr("btn.assemble_patch"))
        self.kind_label.setText(self._tr("label.kind"))
        self.status_label.setText(self._tr("label.status"))
        self.search_label.setText(self._tr("label.search"))
        self.target_only_check.setText(self._tr("check.target_only"))
        self.changed_only_check.setText(self._tr("check.changed_only"))
        self.search_edit.setPlaceholderText(self._tr("search.placeholder"))
        self.source_preview_group.setTitle(self._tr("preview.current"))
        self.target_preview_group.setTitle(self._tr("preview.reference"))
        self.target_edit_hint.setText(self._tr("preview.edit_hint"))
        self.translation_progress_legend_label.setText(self._tr("progress.legend"))
        self.dll_legend_label.setText(self._tr("dll.legend"))
        self.save_edit_button.setText(self._tr("btn.save_edit"))
        self.reset_edit_button.setText(self._tr("btn.reset_edit"))
        self.root_tabs.setTabText(0, self._tr("tab.start"))
        self.root_tabs.setTabText(1, self._tr("tab.workspace"))
        self.editor_tabs.setTabText(0, self._tr("tab.editor"))
        self.editor_tabs.setTabText(1, self._tr("tab.dlls"))
        self.editor_tabs.setTabText(2, self._tr("tab.terminology"))
        self.editor_tabs.setTabText(3, self._tr("tab.mod_overrides"))
        self._retitle_combo_items()
        self._refresh_old_text_backup_options()
        self._update_units_header()
        self._update_dll_plan_headers()
        self._refresh_mod_overrides_table()
        self._refresh_dll_plan_table()
        self._refresh_table()
        self._refresh_toolchain_label()
        self._refresh_project_status()
        self._refresh_progress()
        self._refresh_editor_status()
        self._refresh_terminology_tables()
        self._refresh_apply_resume_status()
        self._refresh_footer()
        self._update_action_state()
        self._set_status(self._tr("status.start"))

    def _refresh_footer(self) -> None:
        self.footer_label.setText(
            self._tr("footer.html").format(
                developed_by=self._config.developed_by,
                version=self._config.app_version,
                github=GITHUB_REPO_URL,
                discord=DISCORD_INVITE_URL,
            )
        )

    def _refresh_project_status(self) -> None:
        project_name = self._project_path.name if self._project_path is not None else self._tr("project.none")
        self._refresh_window_title(project_name)

    def _refresh_window_title(self, project_name: str | None = None) -> None:
        resolved_project_name = project_name or (
            self._project_path.name if self._project_path is not None else self._tr("project.none")
        )
        project_state = self._tr("project.unsaved") if self._is_project_dirty() else self._tr("project.saved")
        project_info = self._safe_format(self._tr("project.info"), name=resolved_project_name, dirty=project_state)
        self.setWindowTitle(f"{self._config.app_title} v{self._config.app_version} | {project_info}")

    def _show_error(self, message: str) -> None:
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.critical(self, self._config.app_title, message)
        self._set_status(self._tr("status.operation_failed"))

    def _set_status(self, message: str) -> None:
        self.status_bar.showMessage(message, 10000)
        if hasattr(self, "simple_status_label"):
            self.simple_status_label.setText(self._tr("simple.status").format(message=message))
