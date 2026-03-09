"""Minimal desktop app for browsing and exporting Freelancer translation units."""

from __future__ import annotations

import json
import os
import queue
import re
import ssl
import sys
import threading
from urllib import request as urlrequest
from pathlib import Path
from typing import Any

from PySide6.QtCore import QSettings, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QColor, QCloseEvent, QCursor, QDesktopServices, QIcon, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
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
    QMenu,
    QProgressDialog,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .localization import LANGUAGE_OPTIONS, load_ui_translations, resolve_help_file
from .catalog import CatalogLoader, pair_catalogs
from .dll_plans import DllRelocalizationPlan, DllStrategy, build_dll_plans
from .exporters import export_catalog_json
from .models import RelocalizationStatus, ResourceCatalog, ResourceKind, TranslationUnit
from .project_io import PROJECT_FILE_EXTENSION, TranslatorProject, load_project, project_signature, save_project
from .resource_writer import ApplyReport, ResourceWriter
from .stats import calculate_translation_progress, summarize_catalog
from .terminology import (
    apply_known_term_suggestions,
    clear_term_map_cache,
    is_unit_skippable,
    list_pattern_entries,
    list_terminology_entries,
    resolve_terminology_file,
    save_replacement_pattern,
    save_term_mapping,
)
from .translation_exchange import export_long_open_exchange, export_mod_only_exchange, import_exchange, update_manual_translation

DISCORD_INVITE_URL = "https://discord.com/invite/RENtMMcc"
GITHUB_REPO_URL = "https://github.com/flathack/FL-Lingo"
GITHUB_LATEST_RELEASE_API = "https://api.github.com/repos/flathack/FL-Lingo/releases/latest"
GITHUB_LATEST_RELEASE_URL = "https://github.com/flathack/FL-Lingo/releases/latest"

STRINGS = {
    "de": {
        "status.start": "Aktuelles Spiel laden und dann gegen die Referenzinstallation vergleichen.",
        "group.installs": "Installationen",
        "group.workflow": "Arbeitsablauf",
        "group.main_actions": "Import / Export fuer externe Uebersetzung",
        "group.apply_execution": "Uebersetzungsdurchlauf",
        "group.filters": "Filter",
        "group.dll_analysis": "DLL-Analyse",
        "group.project": "Projektstatus",
        "group.progress": "Uebersetzungsfortschritt",
        "label.source_install": "Spiel mit Mod / aktuelles Spiel",
        "label.target_install": "Referenzinstallation / Vergleichsspiel",
        "label.source_language": "Quellsprache",
        "label.target_language": "Zielsprache",
        "tooltip.source_language": "Sprache der Installation links.",
        "tooltip.target_language": "Sprache der Referenzinstallation rechts und der aktiven Terminologie.",
        "btn.browse": "Ordner...",
        "check.infocards": "Infocards einbeziehen",
        "btn.load_source": "Spiel laden",
        "btn.compare": "Mit Referenz vergleichen",
        "btn.export_visible": "Sichtbares JSON exportieren",
        "btn.export_mod_only": "Offene Eintraege exportieren",
        "btn.export_long_open": "Lange offene Texte exportieren",
        "btn.import_exchange": "Uebersetzung importieren",
        "btn.apply_target": "Uebersetzung durchfuehren",
        "btn.install_toolchain": "Toolchain installieren",
        "kind.all": "alle",
        "label.kind": "Typ",
        "label.status": "Status",
        "label.search": "Suche",
        "check.target_only": "Nur Eintraege mit Zielreferenz",
        "check.changed_only": "Nur geaenderte",
        "search.placeholder": "Suche in Quell- oder Zieltext",
        "table.units.kind": "Typ",
        "table.units.dll": "DLL",
        "table.units.local_id": "Local ID",
        "table.units.global_id": "Global ID",
        "table.units.status": "Status",
        "table.units.changed": "Geaendert",
        "table.units.preview": "Vorschau aktuell",
        "table.plans.dll": "DLL",
        "table.plans.status": "Status",
        "table.plans.coverage": "Uebersetzungsstand",
        "table.plans.ready": "Bereit",
        "table.plans.open": "Offen",
        "table.plans.reference": "Mit Referenz",
        "table.plans.action": "Vorgehen",
        "dll.legend": "Legende: Datei = betroffene Ressourcendatei | Status = wie gut diese DLL bereits ueber die Referenzsprache abgedeckt ist | Uebersetzungsstand = bereits verfuegbare oder anwendbare Eintraege im Verhaeltnis zur Gesamtmenge | Bereit = schon in Zielsprache, automatisch uebernehmbar oder manuell uebersetzt | Offen = noch fehlende Eintraege | Mit Referenz = Eintraege mit Gegenstueck in der Referenzinstallation | Vorgehen = was FL Lingo beim Anwenden mit dieser DLL macht.",
        "dll.tooltip.dll": "Name der betroffenen Ressourcen-DLL.",
        "dll.tooltip.status": "Einschaetzung, ob diese DLL komplett abgedeckt, teilweise offen oder nur begrenzt automatisch nutzbar ist.",
        "dll.tooltip.coverage": "Anteil der Eintraege, die schon verfuegbar, automatisch uebernehmbar oder manuell uebersetzt sind.",
        "dll.tooltip.ready": "Eintraege, die FL Lingo bereits direkt anwenden kann.",
        "dll.tooltip.open": "Eintraege, die weiterhin offen sind und noch uebersetzt werden muessen.",
        "dll.tooltip.reference": "Eintraege mit passendem Gegenstueck in der Referenzinstallation.",
        "dll.tooltip.action": "Die empfohlene Aktion fuer diese DLL beim Anwenden der Uebersetzungen.",
        "preview.current": "Quelltext",
        "preview.reference": "Zieltext / Referenztext",
        "workflow.help": "Reihenfolge: 1. Aktuelles Spiel laden, 2. Referenzinstallation vergleichen, 3. Offene Eintraege exportieren oder im Editor bearbeiten, 4. Uebersetzungen anwenden.",
        "workflow.step1": "1. Spiel mit Mod / aktuelles Spiel waehlen und laden",
        "workflow.step2": "2. Referenzinstallation / Vergleichsspiel waehlen und vergleichen",
        "workflow.step3": "3. Offene Eintraege direkt bearbeiten oder exportieren/importieren",
        "workflow.step4": "4. Vorschau pruefen und Uebersetzungen anwenden",
        "tab.start": "Startseite",
        "tab.main": "Hauptworkflow",
        "tab.editor": "Uebersetzung",
        "tab.dlls": "DLL-Analyse",
        "tab.terminology": "Terminologie",
        "main.help": "Hauptworkflow fuer FL Lingo: offene Eintraege exportieren, extern uebersetzen, Uebersetzung importieren, danach Vorschau pruefen und anwenden.",
        "main.step.export": "A. Offene Eintraege exportieren",
        "main.step.import": "B. Uebersetzung importieren",
        "main.step.apply": "C. Uebersetzungen anwenden",
        "main.note": "Der manuelle Editor ist optional und liegt im separaten Tab 'Editor'.",
        "editor.help": "Hier werden standardmaessig nur fehlende Uebersetzungen angezeigt. Bereits uebersetzte Eintraege kannst du ueber die Filter wieder einblenden.",
        "editor.missing": "Fehlende Uebersetzungen: {count}",
        "editor.missing_detail": "Offene Eintraege ohne manuelle Uebersetzung: {count}",
        "group.terminology_map": "Terminologie-Mapping",
        "group.terminology_manage": "Terminologie und Pattern-Verwaltung",
        "label.term_source": "Quellbegriff",
        "label.term_target": "Zielbegriff",
        "label.pattern_source": "Pattern Quelle",
        "label.pattern_target": "Pattern Ziel",
        "btn.term_from_selection": "Aus Auswahl uebernehmen",
        "btn.term_save": "Mapping speichern",
        "btn.pattern_save": "Pattern speichern",
        "btn.terminology_reload": "Listen neu laden",
        "table.terms.section": "Bereich",
        "table.terms.source": "Quelle",
        "table.terms.target": "Ziel",
        "table.patterns.section": "Bereich",
        "table.patterns.source": "Pattern",
        "table.patterns.target": "Ersetzung",
        "preview.edit_hint": "Direkt editierbar fuer manuelle Uebersetzungen oder Korrekturen.",
        "btn.save_edit": "Aenderung speichern",
        "btn.reset_edit": "Manuelle Aenderung zuruecksetzen",
        "toolchain.available": "verfuegbar",
        "toolchain.unavailable": "nicht verfuegbar",
        "detail.none": "Keine Auswahl.",
        "summary.none": "Noch kein Katalog geladen.",
        "project.none": "Kein Projekt geladen",
        "project.info": "{name} | {dirty}",
        "progress.none": "Noch kein Katalog geladen.",
        "progress.text": "{percent}% | {done}/{total} Eintraege abgedeckt | {localized} bereits im Spiel uebersetzt | {available} sofort anwendbar | {skipped} uebersprungen",
        "progress.legend": "Lila = bereits im Spiel uebersetzt | Gruen = sofort anwendbar | Gelb = bewusst uebersprungen",
        "apply.run.idle": "Bereit. Noch keine laufende Uebersetzung.",
        "apply.run.resume_available": "Fortsetzung verfuegbar: {done}/{total} DLLs abgeschlossen.",
        "apply.run.running": "Laufend: {done}/{total} DLLs abgeschlossen.",
        "apply.run.completed": "Abgeschlossen: {done}/{total} DLLs verarbeitet.",
        "apply.run.failed": "Abgebrochen bei {dll}. Fortschritt wurde gespeichert und kann spaeter fortgesetzt werden.",
        "apply.run.current_dll": "Aktuelle DLL: {dll} ({action})",
        "apply.run.current_lines": "Aktuelle Eintraege:\n{lines}",
        "apply.run.copy": "komplett ersetzen",
        "apply.run.patch": "patchen",
        "apply.run.none": "Noch keine Eintraege aktiv.",
        "project.saved": "gespeichert",
        "project.unsaved": "nicht gespeichert",
        "plan.action.full": "Ziel-DLL komplett kopieren",
        "plan.action.patch": "fertige Eintraege anwenden",
        "plan.action.unsafe": "manuell pruefen",
        "plan.strategy.full": "Komplett mit Referenz abgedeckt",
        "plan.strategy.patch": "Teilweise abgedeckt, Rest offen",
        "plan.strategy.unsafe": "Nur begrenzt automatisch nutzbar",
        "menu.file": "Datei",
        "menu.view": "Ansicht",
        "menu.settings": "Einstellungen",
        "menu.help": "Hilfe",
        "menu.language": "Language",
        "menuitem.focus_dll": "DLL-Analyse fokussieren",
        "menuitem.focus_units": "Eintragsliste fokussieren",
        "menuitem.appearance": "Darstellung...",
        "menuitem.open_terminology": "Terminologie oeffnen...",
        "menuitem.term_source_from_selection": "Auswahl als Quellbegriff verwenden",
        "menuitem.term_target_from_selection": "Auswahl als Zielbegriff verwenden",
        "menuitem.term_save_from_selection": "Mapping fuer Auswahl speichern",
        "menuitem.check_updates": "Auf Updates pruefen...",
        "menuitem.help_contents": "Hilfe oeffnen...",
        "menuitem.about": "Ueber",
        "menuitem.project_load": "Projekt laden...",
        "menuitem.project_new": "Neues Projekt",
        "menuitem.project_rebuild": "Projekt neu aufbauen",
        "menuitem.project_save": "Projekt speichern...",
        "menuitem.project_save_as": "Projekt speichern unter...",
        "menuitem.restore_backup": "Backup wiederherstellen...",
        "menuitem.file_assoc": ".FLLingo verknuepfen...",
        "status.loaded_source": "Quellinstallation geladen: {path}",
        "status.loaded_compare": "Referenz geladen: {path}",
        "status.project_saved": "Projekt gespeichert: {path}",
        "status.project_loaded": "Projekt geladen: {path}",
        "status.project_new": "Neues Projekt gestartet.",
        "status.project_rebuilt": "Projekt neu aufgebaut.",
        "status.settings_applied": "Einstellungen angewendet.",
        "status.language_changed": "Sprache gewechselt.",
        "status.toolchain_started": "Toolchain-Installer gestartet.",
        "status.terminology_opened": "Terminologie geoeffnet: {path}",
        "status.terminology_saved": "Terminologie-Mapping gespeichert: {source} -> {target}",
        "status.pattern_saved": "Pattern gespeichert: {source} -> {target}",
        "status.term_source_selected": "Quellbegriff aus Auswahl uebernommen.",
        "status.term_target_selected": "Zielbegriff aus Auswahl uebernommen.",
        "status.update_check_started": "Update-Pruefung gestartet.",
        "status.operation_failed": "Vorgang fehlgeschlagen.",
        "error.source_missing": "Quellpfad existiert nicht:\n{path}",
        "error.load_source_failed": "Quellinstallation konnte nicht geladen werden:\n{error}",
        "error.target_missing": "Pfad der Referenzinstallation existiert nicht:\n{path}",
        "error.compare_failed": "Vergleich mit der Referenzinstallation fehlgeschlagen:\n{error}",
        "error.load_first": "Bitte zuerst eine Installation laden.",
        "error.compare_first": "Bitte zuerst mit der Referenzinstallation vergleichen.",
        "error.toolchain_missing": "Keine Resource-Toolchain gefunden.\nBitte zuerst 'Toolchain installieren' ausfuehren.",
        "tooltip.apply_disabled_toolchain": "Es wurde keine unterstuetzte Resource-Toolchain gefunden. Installiere LLVM-Tools oder setze FLATLAS_TOOLCHAIN_DIR.",
        "tooltip.apply_disabled_compare": "Lade zuerst ein aktuelles Spiel und eine Referenzinstallation, damit die Uebersetzung angewendet werden kann.",
        "error.no_apply_units": "Im aktuellen Projekt gibt es keine automatisch oder manuell anwendbaren Eintraege.",
        "error.export_failed": "JSON-Export fehlgeschlagen:\n{error}",
        "error.export_mod_only_failed": "Export offener Eintraege fehlgeschlagen:\n{error}",
        "error.import_failed": "Import fehlgeschlagen:\n{error}",
        "error.apply_failed": "Uebersetzungen konnten nicht angewendet werden:\n{error}",
        "error.toolchain_start_failed": "Toolchain-Installer konnte nicht gestartet werden:\n{error}",
        "error.project_save_failed": "Projekt konnte nicht gespeichert werden:\n{error}",
        "error.project_load_failed": "Projekt konnte nicht geladen werden:\n{error}",
        "error.file_assoc_failed": "Dateizuordnung konnte nicht eingerichtet werden:\n{error}",
        "error.terminology_open_failed": "Terminologie-Datei konnte nicht geoeffnet werden:\n{error}",
        "error.term_mapping_empty": "Quell- und Zielbegriff muessen ausgefuellt sein.",
        "error.pattern_mapping_empty": "Pattern-Quelle und Pattern-Ziel muessen ausgefuellt sein.",
        "error.term_mapping_save_failed": "Terminologie-Mapping konnte nicht gespeichert werden:\n{error}",
        "error.pattern_mapping_save_failed": "Pattern konnte nicht gespeichert werden:\n{error}",
        "error.update_check_failed": "Update-Pruefung fehlgeschlagen:\n{error}",
        "dialog.export_visible": "Sichtbaren Datensatz exportieren",
        "dialog.project_save": "Projekt speichern",
        "dialog.project_save_as": "Projekt speichern unter",
        "dialog.progress_title": "Bitte warten",
        "progress.load_source": "Spielinstallation wird geladen...",
        "progress.compare": "Referenzinstallation wird verglichen...",
        "progress.export_visible": "Sichtbare Eintraege werden exportiert...",
        "progress.export_open": "Offene Eintraege werden exportiert...",
        "progress.export_long_open": "Lange offene Texte werden exportiert...",
        "progress.import_translation": "Uebersetzungsdatei wird importiert...",
        "progress.save_project": "Projekt wird gespeichert...",
        "progress.load_project": "Projekt wird geladen...",
        "dialog.project_load": "Projekt laden",
        "dialog.file_assoc": ".FLLingo verknuepfen",
        "dialog.file_assoc_done": "Dateizuordnung eingerichtet.\n\n{path}",
        "dialog.unsaved_title": "Ungespeicherte Aenderungen",
        "dialog.unsaved_message": "Es gibt ungespeicherte Aenderungen im aktuellen Projekt.\n\nVor dem Fortfahren speichern?",
        "dialog.rebuild_title": "Projekt neu aufbauen",
        "dialog.rebuild_message": "Das Projekt wird nur aus den aktuellen Spieldaten neu aufgebaut.\n\nManuelle Uebersetzungen, importierte Aenderungen und andere nicht aus dem Spiel geladene Projektanpassungen gehen dabei verloren.\n\nFortfahren?",
        "dialog.apply_title": "Uebersetzungen anwenden",
        "dialog.apply_confirm": "Es werden {count} Eintraege ersetzt. Vorher wird ein Backup angelegt.\n\nAbdeckung aktuell: {covered_percent}% ({covered}/{total} Eintraege sind bereits lila, gruen oder gelb)\n\nFortfahren?",
        "dialog.apply_confirm_resume": "Es werden {count} Eintraege ersetzt. Vorher wird ein Backup angelegt oder eine vorhandene Sitzung fortgesetzt.\n\nAbdeckung aktuell: {covered_percent}% ({covered}/{total} Eintraege sind bereits lila, gruen oder gelb)\n\nEs kann bei DLL {next_dll} weitergemacht werden. Bereits fertig: {done}/{dll_total} DLLs.\n\nFortfahren?",
        "dialog.apply_preview": "Anwenden-Vorschau",
        "dialog.apply_progress_title": "Uebersetzungen anwenden",
        "dialog.apply_progress_copy": "Bearbeite {current}/{total}: {dll} wird komplett ersetzt...",
        "dialog.apply_progress_patch": "Bearbeite {current}/{total}: {dll} wird gepatcht...",
        "dialog.restore_backup": "Backup wiederherstellen",
        "dialog.restore_confirm": "Backup wiederherstellen und aktuelle DLLs ueberschreiben?\n\n{path}",
        "dialog.apply_success": "Uebersetzungen abgeschlossen.\n\nErsetzte Eintraege: {count}\nGeschriebene DLLs: {dlls}\nBackup: {backup}",
        "dialog.restore_success": "Backup wiederhergestellt.\n\nDLLs: {count}\nQuelle: {path}",
        "dialog.toolchain_title": "Toolchain installieren",
        "dialog.toolchain_started": "Installer gestartet:\n{path}",
        "dialog.about.title": "Ueber FL Lingo",
        "dialog.about.body": "<h2>FL Lingo</h2><p>Ein Relocalization-Tool fuer Freelancer-Mods. Es vergleicht eine modifizierte Installation mit einer Referenzinstallation, stellt bekannte Texte automatisch wieder her und unterstuetzt den Export/Import fuer externe Uebersetzungen.</p><p><b>Version:</b> {version}<br><b>{developed_by}</b></p><p><a href=\"{github}\">GitHub Repository</a><br><a href=\"{discord}\">Discord Server</a></p>",
        "dialog.help.title": "FL Lingo Hilfe",
        "error.help_open_failed": "Die Hilfe-Datei konnte nicht geladen werden:\n{error}",
        "footer.html": "{developed_by} - Version {version} - <a href=\"{discord}\">Discord Server</a> - <a href=\"{github}\">GitHub Repository</a>",
        "updates.title": "Updates",
        "updates.up_to_date": "FL Lingo ist aktuell. Installierte Version: {version}",
        "updates.available": "Ein Update ist verfuegbar.\n\nInstalliert: {current}\nNeu: {latest}",
        "updates.available_info": "Moechtest du die Release-Seite auf GitHub oeffnen?",
        "updates.open_release": "Release oeffnen",
        "updates.version_parse_failed": "Die Release-Version konnte nicht ausgewertet werden.",
        "status.manual_saved": "Manuelle Uebersetzung gespeichert.",
        "status.manual_reset": "Manuelle Uebersetzung zurueckgesetzt.",
        "status.backup_restored": "Backup wiederhergestellt: {path}",
        "status.file_assoc_done": ".FLLingo verknuepft.",
        "error.select_entry": "Bitte zuerst einen Eintrag auswaehlen.",
        "error.no_backups": "Keine Backups fuer diese Installation gefunden.",
        "error.restore_failed": "Backup konnte nicht wiederhergestellt werden:\n{error}",
        "summary.visible": "Sichtbar {visible}/{total}",
        "summary.full": "DLL komplett ersetzbar {count}",
        "summary.patch": "DLL teilweise {count}",
        "summary.unsafe": "DLL unsicher {count}",
        "summary.strings": "Strings auto {auto}, manuell {manual}, schon Ziel {localized}, mod-only {mod_only}",
        "summary.infocards": "Infocards auto {auto}, manuell {manual}, schon Ziel {localized}, mod-only {mod_only}",
        "detail.kind": "Typ",
        "detail.status": "Status",
        "detail.reference": "Zielreferenz",
        "detail.manual": "Manuell",
        "detail.changed": "Geaendert",
        "status.auto_relocalize": "Automatisch uebernehmbar",
        "status.already_localized": "Bereits in Zielsprache",
        "status.manual_translation": "Manuell uebersetzt",
        "status.mod_only": "Nur Mod-Inhalt",
        "status.export_mod_only": "{exported} offene Eintraege exportiert | {skipped} uebersprungen | Glossar {glossary}",
        "status.export_long_open": "{exported} lange offene Texte exportiert | {skipped} uebersprungen | Glossar {glossary}",
        "error.export_long_open_failed": "Export langer offener Texte fehlgeschlagen:\n{error}",
        "yes": "ja",
        "no": "nein",
    },
    "en": {
        "status.start": "Load the current game and compare it against the reference install.",
        "group.installs": "Installs",
        "group.workflow": "Workflow",
        "group.main_actions": "Import / Export for External Translation",
        "group.apply_execution": "Translation Run",
        "group.filters": "Filters",
        "group.dll_analysis": "DLL Analysis",
        "group.project": "Project Status",
        "group.progress": "Translation Progress",
        "label.source_install": "Game with mod / current game",
        "label.target_install": "Reference install / comparison game",
        "label.source_language": "Source language",
        "label.target_language": "Target language",
        "tooltip.source_language": "Language of the install on the left.",
        "tooltip.target_language": "Language of the reference install on the right and the active terminology.",
        "btn.browse": "Browse...",
        "check.infocards": "Include infocards",
        "btn.load_source": "Load game",
        "btn.compare": "Compare with reference",
        "btn.export_visible": "Export visible JSON",
        "btn.export_mod_only": "Export open entries",
        "btn.export_long_open": "Export long open texts",
        "btn.import_exchange": "Import translation",
        "btn.apply_target": "Run translation",
        "btn.install_toolchain": "Install toolchain",
        "kind.all": "all",
        "label.kind": "Kind",
        "label.status": "Status",
        "label.search": "Search",
        "check.target_only": "Only entries with target reference",
        "check.changed_only": "Changed only",
        "search.placeholder": "Search in source or target text",
        "table.units.kind": "Kind",
        "table.units.dll": "DLL",
        "table.units.local_id": "Local ID",
        "table.units.global_id": "Global ID",
        "table.units.status": "Status",
        "table.units.changed": "Changed",
        "table.units.preview": "Current preview",
        "table.plans.dll": "DLL",
        "table.plans.status": "Status",
        "table.plans.coverage": "Coverage",
        "table.plans.ready": "Ready",
        "table.plans.open": "Open",
        "table.plans.reference": "With reference",
        "table.plans.action": "Action",
        "dll.legend": "Legend: File = affected resource DLL | Status = how well the DLL is already covered by the reference language | Coverage = ready entries compared to all entries in that DLL | Ready = already in target language, auto-transferable, or manually translated | Open = entries still missing a translation | With reference = entries with a matching counterpart in the reference install | Action = what FL Lingo will do with this DLL when applying changes.",
        "dll.tooltip.dll": "Name of the affected resource DLL.",
        "dll.tooltip.status": "Assessment of whether this DLL is fully covered, partially open, or only limited in what can be applied automatically.",
        "dll.tooltip.coverage": "Share of entries already available, auto-transferable, or manually translated.",
        "dll.tooltip.ready": "Entries FL Lingo can already apply directly.",
        "dll.tooltip.open": "Entries still missing a translation.",
        "dll.tooltip.reference": "Entries with a matching counterpart in the reference install.",
        "dll.tooltip.action": "The recommended action FL Lingo will perform for this DLL.",
        "preview.current": "Source text",
        "preview.reference": "Target / reference text",
        "workflow.help": "Recommended order: 1. Load the current game, 2. Compare with the reference install, 3. Edit open entries directly or export/import them, 4. Review preview and apply translations.",
        "workflow.step1": "1. Choose and load the game with mod / current game",
        "workflow.step2": "2. Choose the reference install / comparison game and compare",
        "workflow.step3": "3. Edit open entries directly or use export/import",
        "workflow.step4": "4. Review the preview and apply translations",
        "tab.start": "Start Page",
        "tab.main": "Main Workflow",
        "tab.editor": "Translation",
        "tab.dlls": "DLL Analysis",
        "tab.terminology": "Terminology",
        "main.help": "Primary FL Lingo workflow: export open entries, translate externally, import the translation, then review and apply.",
        "main.step.export": "A. Export open entries",
        "main.step.import": "B. Import translation",
        "main.step.apply": "C. Apply translations",
        "main.note": "The manual editor is optional and lives in the separate 'Editor' tab.",
        "editor.help": "This tab defaults to missing translations only. You can bring translated entries back with the filters.",
        "editor.missing": "Missing translations: {count}",
        "editor.missing_detail": "Open entries without manual translation: {count}",
        "group.terminology_map": "Terminology Mapping",
        "group.terminology_manage": "Terminology and Pattern Management",
        "label.term_source": "Source term",
        "label.term_target": "Target term",
        "label.pattern_source": "Pattern source",
        "label.pattern_target": "Pattern target",
        "btn.term_from_selection": "Use selection",
        "btn.term_save": "Save mapping",
        "btn.pattern_save": "Save pattern",
        "btn.terminology_reload": "Reload lists",
        "table.terms.section": "Section",
        "table.terms.source": "Source",
        "table.terms.target": "Target",
        "table.patterns.section": "Section",
        "table.patterns.source": "Pattern",
        "table.patterns.target": "Replacement",
        "preview.edit_hint": "Directly editable for manual translations or corrections.",
        "btn.save_edit": "Save edit",
        "btn.reset_edit": "Reset manual edit",
        "toolchain.available": "available",
        "toolchain.unavailable": "not available",
        "detail.none": "No selection.",
        "summary.none": "No catalog loaded.",
        "project.none": "No project loaded",
        "project.info": "{name} | {dirty}",
        "progress.none": "No catalog loaded yet.",
        "progress.text": "{percent}% | {done}/{total} entries covered | {localized} already translated in-game | {available} ready to apply | {skipped} skipped",
        "progress.legend": "Purple = already translated in-game | Green = ready to apply | Yellow = intentionally skipped",
        "apply.run.idle": "Ready. No translation run is active.",
        "apply.run.resume_available": "Resume available: {done}/{total} DLLs already completed.",
        "apply.run.running": "Running: {done}/{total} DLLs completed.",
        "apply.run.completed": "Completed: {done}/{total} DLLs processed.",
        "apply.run.failed": "Stopped at {dll}. Progress was saved and can be resumed later.",
        "apply.run.current_dll": "Current DLL: {dll} ({action})",
        "apply.run.current_lines": "Current entries:\n{lines}",
        "apply.run.copy": "full replace",
        "apply.run.patch": "patch",
        "apply.run.none": "No active entries yet.",
        "project.saved": "saved",
        "project.unsaved": "unsaved",
        "plan.action.full": "copy target DLL",
        "plan.action.patch": "apply ready entries",
        "plan.action.unsafe": "review manually",
        "plan.strategy.full": "Fully covered by reference",
        "plan.strategy.patch": "Partially covered, some open",
        "plan.strategy.unsafe": "Limited automatic coverage",
        "menu.file": "File",
        "menu.view": "View",
        "menu.settings": "Settings",
        "menu.help": "Help",
        "menu.language": "Language",
        "menuitem.focus_dll": "Focus DLL analysis",
        "menuitem.focus_units": "Focus entries",
        "menuitem.appearance": "Appearance...",
        "menuitem.open_terminology": "Open terminology...",
        "menuitem.term_source_from_selection": "Use selection as source term",
        "menuitem.term_target_from_selection": "Use selection as target term",
        "menuitem.term_save_from_selection": "Save mapping for selection",
        "menuitem.check_updates": "Check for updates...",
        "menuitem.help_contents": "Open help...",
        "menuitem.about": "About",
        "menuitem.project_load": "Load project...",
        "menuitem.project_new": "New project",
        "menuitem.project_rebuild": "Rebuild project",
        "menuitem.project_save": "Save project...",
        "menuitem.project_save_as": "Save project as...",
        "menuitem.restore_backup": "Restore backup...",
        "menuitem.file_assoc": "Associate .FLLingo...",
        "status.loaded_source": "Loaded source install: {path}",
        "status.loaded_compare": "Loaded reference install: {path}",
        "status.project_saved": "Project saved: {path}",
        "status.project_loaded": "Project loaded: {path}",
        "status.project_new": "Started a new project.",
        "status.project_rebuilt": "Project rebuilt.",
        "status.settings_applied": "Settings applied.",
        "status.language_changed": "Language changed.",
        "status.toolchain_started": "Toolchain installer started.",
        "status.terminology_opened": "Opened terminology: {path}",
        "status.terminology_saved": "Terminology mapping saved: {source} -> {target}",
        "status.pattern_saved": "Pattern saved: {source} -> {target}",
        "status.term_source_selected": "Source term copied from selection.",
        "status.term_target_selected": "Target term copied from selection.",
        "status.update_check_started": "Started update check.",
        "status.operation_failed": "Operation failed.",
        "error.source_missing": "Source path does not exist:\n{path}",
        "error.load_source_failed": "Source install could not be loaded:\n{error}",
        "error.target_missing": "Reference install path does not exist:\n{path}",
        "error.compare_failed": "Comparison with reference install failed:\n{error}",
        "error.load_first": "Load an install first.",
        "error.compare_first": "Compare against the reference install first.",
        "error.toolchain_missing": "No resource toolchain found.\nRun 'Install toolchain' first.",
        "tooltip.apply_disabled_toolchain": "No supported resource toolchain was found. Install LLVM tools or set FLATLAS_TOOLCHAIN_DIR.",
        "tooltip.apply_disabled_compare": "Load a current game and a reference install first so translations can be applied.",
        "error.no_apply_units": "There are no automatically or manually applicable entries in the current project.",
        "error.export_failed": "JSON export failed:\n{error}",
        "error.export_mod_only_failed": "Open entry export failed:\n{error}",
        "error.import_failed": "Import failed:\n{error}",
        "error.apply_failed": "Applying translations failed:\n{error}",
        "error.toolchain_start_failed": "Toolchain installer could not be started:\n{error}",
        "error.project_save_failed": "Project could not be saved:\n{error}",
        "error.project_load_failed": "Project could not be loaded:\n{error}",
        "error.file_assoc_failed": "File association could not be configured:\n{error}",
        "error.terminology_open_failed": "Terminology file could not be opened:\n{error}",
        "error.term_mapping_empty": "Source term and target term must be filled in.",
        "error.pattern_mapping_empty": "Pattern source and target must be filled in.",
        "error.term_mapping_save_failed": "Terminology mapping could not be saved:\n{error}",
        "error.pattern_mapping_save_failed": "Pattern could not be saved:\n{error}",
        "error.update_check_failed": "Update check failed:\n{error}",
        "dialog.export_visible": "Export visible dataset",
        "dialog.project_save": "Save project",
        "dialog.project_save_as": "Save project as",
        "dialog.progress_title": "Please wait",
        "progress.load_source": "Loading game install...",
        "progress.compare": "Comparing reference install...",
        "progress.export_visible": "Exporting visible entries...",
        "progress.export_open": "Exporting open entries...",
        "progress.export_long_open": "Exporting long open texts...",
        "progress.import_translation": "Importing translation file...",
        "progress.save_project": "Saving project...",
        "progress.load_project": "Loading project...",
        "dialog.project_load": "Load project",
        "dialog.file_assoc": "Associate .FLLingo",
        "dialog.file_assoc_done": "File association configured.\n\n{path}",
        "dialog.unsaved_title": "Unsaved changes",
        "dialog.unsaved_message": "There are unsaved changes in the current project.\n\nSave before continuing?",
        "dialog.rebuild_title": "Rebuild project",
        "dialog.rebuild_message": "The project will be rebuilt only from the current game data.\n\nManual translations, imported changes, and other project edits that do not come from the game data will be lost.\n\nContinue?",
        "dialog.apply_title": "Apply translations",
        "dialog.apply_confirm": "{count} entries will be replaced. A backup is created first.\n\nCurrent coverage: {covered_percent}% ({covered}/{total} entries are already purple, green, or yellow)\n\nContinue?",
        "dialog.apply_confirm_resume": "{count} entries will be replaced. A backup is created first or an existing session will be resumed.\n\nCurrent coverage: {covered_percent}% ({covered}/{total} entries are already purple, green, or yellow)\n\nIt can continue at DLL {next_dll}. Already completed: {done}/{dll_total} DLLs.\n\nContinue?",
        "dialog.apply_preview": "Apply preview",
        "dialog.apply_progress_title": "Apply translations",
        "dialog.apply_progress_copy": "Processing {current}/{total}: replacing {dll}...",
        "dialog.apply_progress_patch": "Processing {current}/{total}: patching {dll}...",
        "dialog.restore_backup": "Restore backup",
        "dialog.restore_confirm": "Restore this backup and overwrite current DLLs?\n\n{path}",
        "dialog.apply_success": "Translations finished.\n\nReplaced entries: {count}\nWritten DLLs: {dlls}\nBackup: {backup}",
        "dialog.restore_success": "Backup restored.\n\nDLLs: {count}\nSource: {path}",
        "dialog.toolchain_title": "Install toolchain",
        "dialog.toolchain_started": "Installer started:\n{path}",
        "dialog.about.title": "About FL Lingo",
        "dialog.about.body": "<h2>FL Lingo</h2><p>A relocalization tool for Freelancer mods. It compares a modded game install with a reference install, restores known text automatically, and supports export/import for external translation workflows.</p><p><b>Version:</b> {version}<br><b>{developed_by}</b></p><p><a href=\"{github}\">GitHub Repository</a><br><a href=\"{discord}\">Discord Server</a></p>",
        "dialog.help.title": "FL Lingo Help",
        "error.help_open_failed": "The help file could not be loaded:\n{error}",
        "footer.html": "{developed_by} - Version {version} - <a href=\"{discord}\">Join Discord Server</a> - <a href=\"{github}\">GitHub Repository</a>",
        "updates.title": "Updates",
        "updates.up_to_date": "FL Lingo is up to date. Installed version: {version}",
        "updates.available": "An update is available.\n\nInstalled: {current}\nLatest: {latest}",
        "updates.available_info": "Do you want to open the release page on GitHub?",
        "updates.open_release": "Open release",
        "updates.version_parse_failed": "The release version could not be parsed.",
        "status.manual_saved": "Manual translation saved.",
        "status.manual_reset": "Manual translation reset.",
        "status.backup_restored": "Backup restored: {path}",
        "status.file_assoc_done": ".FLLingo associated.",
        "error.select_entry": "Select an entry first.",
        "error.no_backups": "No backups found for this install.",
        "error.restore_failed": "Backup could not be restored:\n{error}",
        "summary.visible": "Visible {visible}/{total}",
        "summary.full": "DLL full replace {count}",
        "summary.patch": "DLL partial {count}",
        "summary.unsafe": "DLL unsafe {count}",
        "summary.strings": "Strings auto {auto}, manual {manual}, already target {localized}, mod-only {mod_only}",
        "summary.infocards": "Infocards auto {auto}, manual {manual}, already target {localized}, mod-only {mod_only}",
        "detail.kind": "Kind",
        "detail.status": "Status",
        "detail.reference": "Target reference",
        "detail.manual": "Manual",
        "detail.changed": "Changed",
        "status.auto_relocalize": "Auto transferable",
        "status.already_localized": "Already in target language",
        "status.manual_translation": "Manually translated",
        "status.mod_only": "Mod-only content",
        "status.export_mod_only": "{exported} open entries exported | {skipped} skipped | glossary {glossary}",
        "status.export_long_open": "{exported} long open texts exported | {skipped} skipped | glossary {glossary}",
        "error.export_long_open_failed": "Long open text export failed:\n{error}",
        "yes": "yes",
        "no": "no",
    },
}

STRINGS["fr"] = dict(STRINGS["en"]) | {
    "group.installs": "Installations",
    "group.workflow": "Flux",
    "group.main_actions": "Flux Principal",
    "group.filters": "Filtres",
    "group.dll_analysis": "Analyse DLL",
    "group.project": "Etat du Projet",
    "group.progress": "Progression de Traduction",
    "label.source_install": "Jeu actuel / jeu avec mod",
    "label.target_install": "Installation de reference / jeu de comparaison",
    "label.source_language": "Langue source",
    "label.target_language": "Langue cible",
    "btn.browse": "Parcourir...",
    "btn.load_source": "Charger le jeu",
    "btn.compare": "Comparer avec la reference",
    "btn.import_exchange": "Importer la traduction",
    "btn.apply_target": "Appliquer les traductions",
    "menu.file": "Fichier",
    "menu.view": "Affichage",
    "menu.settings": "Parametres",
    "menu.help": "Aide",
    "menuitem.project_load": "Charger le projet...",
    "menuitem.project_new": "Nouveau projet",
    "menuitem.project_save": "Enregistrer le projet...",
    "menuitem.open_terminology": "Ouvrir la terminologie...",
    "menuitem.check_updates": "Verifier les mises a jour...",
    "menuitem.about": "A propos",
    "status.language_changed": "Langue changee.",
    "updates.title": "Mises a jour",
    "updates.up_to_date": "FL Lingo est a jour. Version installee : {version}",
    "updates.available": "Une mise a jour est disponible.\n\nInstallee : {current}\nDerniere : {latest}",
    "updates.open_release": "Ouvrir la release",
}

STRINGS["es"] = dict(STRINGS["en"]) | {
    "group.installs": "Instalaciones",
    "group.workflow": "Flujo",
    "group.main_actions": "Flujo Principal",
    "group.filters": "Filtros",
    "group.dll_analysis": "Analisis DLL",
    "group.project": "Estado del Proyecto",
    "group.progress": "Progreso de Traduccion",
    "label.source_install": "Juego actual / juego con mod",
    "label.target_install": "Instalacion de referencia / juego de comparacion",
    "label.source_language": "Idioma de origen",
    "label.target_language": "Idioma de destino",
    "btn.browse": "Buscar...",
    "btn.load_source": "Cargar juego",
    "btn.compare": "Comparar con referencia",
    "btn.import_exchange": "Importar traduccion",
    "btn.apply_target": "Aplicar traducciones",
    "menu.file": "Archivo",
    "menu.view": "Ver",
    "menu.settings": "Configuracion",
    "menu.help": "Ayuda",
    "menuitem.project_load": "Cargar proyecto...",
    "menuitem.project_new": "Nuevo proyecto",
    "menuitem.project_save": "Guardar proyecto...",
    "menuitem.open_terminology": "Abrir terminologia...",
    "menuitem.check_updates": "Buscar actualizaciones...",
    "menuitem.about": "Acerca de",
    "status.language_changed": "Idioma cambiado.",
    "updates.title": "Actualizaciones",
    "updates.up_to_date": "FL Lingo esta actualizado. Version instalada: {version}",
    "updates.available": "Hay una actualizacion disponible.\n\nInstalada: {current}\nUltima: {latest}",
    "updates.open_release": "Abrir release",
}

STRINGS["ru"] = dict(STRINGS["en"]) | {
    "group.installs": "Ustanovki",
    "group.workflow": "Rabochiy protsess",
    "group.main_actions": "Osnovnoy protsess",
    "group.filters": "Filtry",
    "group.dll_analysis": "Analiz DLL",
    "group.project": "Status proekta",
    "group.progress": "Progress perevoda",
    "label.source_install": "Tekushchaya igra / igra s modom",
    "label.target_install": "Referensnaya ustanovka / igra dlya sravneniya",
    "label.source_language": "Yazyk istochnika",
    "label.target_language": "Tselevoy yazyk",
    "btn.browse": "Obzor...",
    "btn.load_source": "Zagruzit igru",
    "btn.compare": "Sravnit s etalonom",
    "btn.import_exchange": "Importirovat perevod",
    "btn.apply_target": "Primenit perevody",
    "menu.file": "Fail",
    "menu.view": "Vid",
    "menu.settings": "Nastroyki",
    "menu.help": "Pomoshch",
    "menuitem.project_load": "Zagruzit proekt...",
    "menuitem.project_new": "Novyy proekt",
    "menuitem.project_save": "Sohranit proekt...",
    "menuitem.open_terminology": "Otkryt terminologiyu...",
    "menuitem.check_updates": "Proverit obnovleniya...",
    "menuitem.about": "O programme",
    "status.language_changed": "Yazyk izmenen.",
    "updates.title": "Obnovleniya",
    "updates.up_to_date": "FL Lingo aktualen. Ustanovlennaya versiya: {version}",
    "updates.available": "Dostupno obnovlenie.\n\nUstanovleno: {current}\nNovaya versiya: {latest}",
    "updates.open_release": "Otkryt release",
}

STRINGS = load_ui_translations(STRINGS)

THEMES = {
    "light": """
        QWidget { background: #f5f4ef; color: #1f1a17; }
        QMainWindow, QDialog { background: #f5f4ef; }
        QLineEdit, QTextEdit, QComboBox, QTableWidget {
            background: #fffdf8;
            color: #1f1a17;
            border: 1px solid #c9c0b3;
            selection-background-color: #d97841;
            selection-color: #ffffff;
        }
        QLineEdit:hover, QTextEdit:hover, QComboBox:hover, QTableWidget:hover {
            border: 1px solid #d97841;
        }
        QPushButton {
            background: #1f5c5c;
            color: #ffffff;
            border: 1px solid #1f5c5c;
            border-radius: 6px;
            padding: 6px 10px;
        }
        QPushButton:hover {
            background: #267171;
            border-color: #d97841;
        }
        QPushButton:pressed {
            background: #184a4a;
            border-color: #b85e2c;
            padding-top: 7px;
            padding-bottom: 5px;
        }
        QPushButton:disabled {
            background: #97a4a4;
            color: #e7ecec;
            border-color: #97a4a4;
        }
        QTabWidget::pane, QGroupBox {
            border: 1px solid #c9c0b3;
            margin-top: 10px;
        }
        QMenuBar {
            background: #ece4d7;
            color: #1f1a17;
            border-bottom: 1px solid #c9c0b3;
        }
        QMenuBar::item {
            background: transparent;
            padding: 6px 10px;
            margin: 1px 2px;
            border-radius: 4px;
        }
        QMenuBar::item:selected {
            background: #f7efe3;
            color: #103c52;
        }
        QMenuBar::item:pressed {
            background: #d97841;
            color: #ffffff;
        }
        QMenu {
            background: #fffdf8;
            color: #1f1a17;
            border: 1px solid #c9c0b3;
        }
        QMenu::item {
            padding: 6px 24px 6px 12px;
        }
        QMenu::item:selected {
            background: #d97841;
            color: #ffffff;
        }
        QTabBar::tab {
            background: #e8e0d4;
            color: #1f1a17;
            border: 1px solid #c9c0b3;
            border-bottom: none;
            padding: 7px 12px;
            margin-right: 2px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
        }
        QTabBar::tab:hover {
            background: #f3ebdf;
            color: #103c52;
        }
        QTabBar::tab:selected {
            background: #fffdf8;
            color: #103c52;
            border-color: #d97841;
        }
        QComboBox::drop-down {
            border: none;
            width: 22px;
        }
        QCheckBox:hover, QGroupBox:hover {
            color: #103c52;
        }
        QTableWidget::item:selected {
            background: #d97841;
            color: #ffffff;
        }
        QHeaderView::section:hover {
            background: #efe6d9;
            color: #103c52;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 4px;
        }
    """,
    "dark": """
        QWidget { background: #1f2329; color: #e6edf3; }
        QLineEdit, QTextEdit, QComboBox, QTableWidget {
            background: #2d333b;
            color: #e6edf3;
            border: 1px solid #444c56;
        }
        QLineEdit:hover, QTextEdit:hover, QComboBox:hover, QTableWidget:hover {
            border: 1px solid #58a6ff;
        }
        QPushButton {
            background: #2f81f7;
            color: white;
            border: 1px solid #2f81f7;
            border-radius: 6px;
            padding: 6px 10px;
        }
        QPushButton:hover {
            background: #4493f8;
            border-color: #79c0ff;
        }
        QPushButton:pressed {
            background: #1f6feb;
            border-color: #1f6feb;
            padding-top: 7px;
            padding-bottom: 5px;
        }
        QPushButton:disabled {
            background: #4b5563;
            color: #c9d1d9;
            border-color: #4b5563;
        }
        QTabBar::tab {
            background: #2d333b;
            color: #c9d1d9;
            border: 1px solid #444c56;
            border-bottom: none;
            padding: 7px 12px;
            margin-right: 2px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
        }
        QTabBar::tab:hover {
            background: #343b43;
            color: #ffffff;
        }
        QTabBar::tab:selected {
            background: #1f2329;
            color: #79c0ff;
            border-color: #58a6ff;
        }
        QComboBox::drop-down {
            border: none;
            width: 22px;
        }
        QCheckBox:hover, QGroupBox:hover {
            color: #79c0ff;
        }
        QTableWidget::item:selected {
            background: #2f81f7;
            color: #ffffff;
        }
        QHeaderView::section:hover {
            background: #343b43;
            color: #ffffff;
        }
        QGroupBox {
            border: 1px solid #444c56;
            margin-top: 10px;
        }
        QMenuBar {
            background: #161b22;
            color: #e6edf3;
            border-bottom: 1px solid #30363d;
        }
        QMenuBar::item {
            background: transparent;
            padding: 6px 10px;
            margin: 1px 2px;
            border-radius: 4px;
        }
        QMenuBar::item:selected {
            background: #30363d;
            color: #ffffff;
        }
        QMenuBar::item:pressed {
            background: #2f81f7;
            color: #ffffff;
        }
        QMenu {
            background: #1f2329;
            color: #e6edf3;
            border: 1px solid #444c56;
        }
        QMenu::item {
            padding: 6px 24px 6px 12px;
        }
        QMenu::item:selected {
            background: #2f81f7;
            color: #ffffff;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 4px;
        }
    """,
    "high_contrast": """
        QWidget { background: #000000; color: #ffffff; }
        QMainWindow, QDialog { background: #000000; }
        QLineEdit, QTextEdit, QComboBox, QTableWidget {
            background: #000000;
            color: #ffffff;
            border: 2px solid #ffff00;
            selection-background-color: #00ffff;
            selection-color: #000000;
        }
        QLineEdit:hover, QTextEdit:hover, QComboBox:hover, QTableWidget:hover {
            border: 2px solid #00ffff;
        }
        QPushButton {
            background: #ffff00;
            color: #000000;
            border: 2px solid #ffffff;
            padding: 6px 10px;
            font-weight: bold;
            border-radius: 6px;
        }
        QPushButton:hover {
            background: #00ffff;
            color: #000000;
            border-color: #ffff00;
        }
        QPushButton:pressed {
            background: #ff8c00;
            color: #000000;
            border-color: #ffffff;
            padding-top: 7px;
            padding-bottom: 5px;
        }
        QPushButton:disabled {
            background: #666666;
            color: #ffffff;
            border: 2px solid #999999;
        }
        QLabel, QCheckBox, QGroupBox, QTabBar::tab {
            color: #ffffff;
        }
        QMenuBar {
            background: #000000;
            color: #ffffff;
            border-bottom: 2px solid #ffffff;
        }
        QMenuBar::item {
            background: transparent;
            padding: 6px 10px;
            margin: 1px 2px;
        }
        QMenuBar::item:selected {
            background: #00ffff;
            color: #000000;
        }
        QMenuBar::item:pressed {
            background: #ffff00;
            color: #000000;
        }
        QMenu {
            background: #000000;
            color: #ffffff;
            border: 2px solid #ffffff;
        }
        QMenu::item {
            padding: 6px 24px 6px 12px;
        }
        QMenu::item:selected {
            background: #00ffff;
            color: #000000;
        }
        QTabBar::tab {
            background: #000000;
            border: 2px solid #ffffff;
            border-bottom: none;
            padding: 7px 12px;
            margin-right: 2px;
        }
        QTabBar::tab:hover {
            background: #00ffff;
            color: #000000;
            border-color: #ffff00;
        }
        QTabBar::tab:selected {
            background: #ffff00;
            color: #000000;
            border-color: #ffffff;
        }
        QComboBox::drop-down {
            border: none;
            width: 22px;
        }
        QCheckBox:hover, QGroupBox:hover {
            color: #00ffff;
        }
        QTableWidget::item:selected {
            background: #00ffff;
            color: #000000;
        }
        QTabWidget::pane, QGroupBox {
            border: 2px solid #ffffff;
            margin-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 4px;
        }
        QHeaderView::section {
            background: #000000;
            color: #ffffff;
            border: 1px solid #ffff00;
        }
        QHeaderView::section:hover {
            background: #00ffff;
            color: #000000;
        }
    """,
}


class SegmentedProgressBar(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._total = 0
        self._localized = 0
        self._done = 0
        self._skipped = 0
        self._segments = 20
        self.setMinimumHeight(24)

    def set_progress(self, *, total: int, localized: int, done: int, skipped: int) -> None:
        self._total = max(0, int(total))
        self._localized = max(0, int(localized))
        self._done = max(0, int(done))
        self._skipped = max(0, int(skipped))
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)

        rect = self.rect().adjusted(0, 0, -1, -1)
        if rect.width() <= 0 or rect.height() <= 0:
            return

        painter.fillRect(rect, QColor("#d8d8d8"))
        total = self._total if self._total > 0 else 1
        localized_ratio = min(1.0, self._localized / total)
        covered_ratio = min(1.0, (self._done + self._skipped) / total)
        done_ratio = min(covered_ratio, self._done / total)
        segment_gap = 2
        segment_width = max(4, int((rect.width() - ((self._segments - 1) * segment_gap)) / self._segments))
        for index in range(self._segments):
            x = rect.x() + index * (segment_width + segment_gap)
            width = segment_width if index < self._segments - 1 else rect.right() - x + 1
            segment_rect = rect.adjusted(x - rect.x(), 0, -(rect.right() - (x + width - 1)), 0)
            segment_start = index / self._segments
            segment_end = (index + 1) / self._segments
            if segment_end <= localized_ratio:
                color = QColor("#A855F7")
            elif segment_end <= done_ratio:
                color = QColor("#4CAF50")
            elif segment_end <= covered_ratio:
                color = QColor("#E3B341")
            else:
                color = QColor("#C7CCD4")
            painter.fillRect(segment_rect.adjusted(0, 0, -1, 0), color)
        painter.setPen(QPen(QColor("#707070"), 1))
        painter.drawRect(rect)
        painter.end()


class TranslatorMainWindow(QMainWindow):
    def __init__(self, config: Any = None) -> None:
        super().__init__()
        self._config = config or _DefaultConfig()
        self._lang = str(getattr(self._config, "default_language", "de") or "de").lower()
        if self._lang not in STRINGS:
            self._lang = "de"
        self._theme = str(getattr(self._config, "default_theme", "light") or "light").lower()
        if self._theme not in THEMES:
            self._theme = "light"
        self._source_lang_code = self._normalize_lang_code(getattr(self._config, "default_source_language", "en"), "en")
        self._target_lang_code = self._normalize_lang_code(getattr(self._config, "default_target_language", "de"), "de")
        self._startup_last_project_path: Path | None = None
        self._settings = QSettings("FLAtlas", "FLAtlas-Translator")
        self._load_persistent_settings()
        self._loader = CatalogLoader()
        self._writer = ResourceWriter()
        self._source_catalog: ResourceCatalog | None = None
        self._target_catalog: ResourceCatalog | None = None
        self._paired_catalog: ResourceCatalog | None = None
        self._dll_plans: list[DllRelocalizationPlan] = []
        self._visible_units: list[TranslationUnit] = []
        self._project_path: Path | None = None
        self._saved_project_signature: str | None = None
        self._apply_thread: threading.Thread | None = None
        self._apply_queue: queue.Queue[dict[str, Any]] = queue.Queue()
        self._apply_poll_timer = QTimer(self)
        self._apply_poll_timer.timeout.connect(self._poll_apply_queue)
        self._search_debounce_timer = QTimer(self)
        self._search_debounce_timer.setSingleShot(True)
        self._search_debounce_timer.timeout.connect(self._refresh_table)
        self._apply_active = False
        self._apply_report: ApplyReport | None = None
        self._apply_error: str | None = None
        self._setup_ui()
        self._apply_editor_default_filters(force=True)
        startup_project = getattr(self._config, "startup_project_path", None)
        if startup_project:
            self._load_project_path(Path(str(startup_project)))
        elif self._startup_last_project_path is not None:
            self._try_restore_last_project(self._startup_last_project_path)

    def _resolve_app_icon(self) -> QIcon | None:
        candidates: list[Path] = []
        if getattr(sys, "frozen", False):
            exe_dir = Path(sys.executable).resolve().parent
            candidates.extend(
                [
                    exe_dir / "images" / "FLLingo-JuniIcon-Clean.png",
                    exe_dir / "_internal" / "images" / "FLLingo-JuniIcon-Clean.png",
                    exe_dir / "images" / "FLLingo-JuniIcon-Clean.ico",
                    exe_dir / "_internal" / "images" / "FLLingo-JuniIcon-Clean.ico",
                ]
            )
        project_root = Path(__file__).resolve().parent.parent.parent
        candidates.extend(
            [
                project_root / "images" / "FLLingo-JuniIcon-Clean.png",
                project_root / "images" / "FLLingo-JuniIcon-Clean.ico",
                project_root / "images" / "FLLingo-JuniIcon.png",
                project_root / "images" / "FLLingo-Icon.png",
                project_root / "images" / "FLLingo-Icon.ico",
            ]
        )
        for candidate in candidates:
            if candidate.is_file():
                return QIcon(str(candidate))
        return None

    def _tr(self, key: str) -> str:
        current = STRINGS.get(self._lang, STRINGS["en"])
        return current.get(key, STRINGS["en"].get(key, key))

    def _normalize_lang_code(self, value: Any, fallback: str) -> str:
        normalized = str(value or fallback).strip().lower()
        return normalized or fallback

    def _set_language_combo_value(self, combo: QComboBox, language_code: str) -> None:
        code = self._normalize_lang_code(language_code, "de")
        index = combo.findData(code)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _combo_language_code(self, combo: QComboBox, fallback: str) -> str:
        current = combo.currentData()
        if current is None:
            return self._normalize_lang_code(fallback, fallback)
        return self._normalize_lang_code(current, fallback)

    def _status_text(self, status: RelocalizationStatus) -> str:
        return self._tr(f"status.{status}")

    def _dll_strategy_label(self, strategy: DllStrategy) -> str:
        if strategy == DllStrategy.FULL_REPLACE_SAFE:
            return self._tr("plan.strategy.full")
        if strategy == DllStrategy.PATCH_REQUIRED:
            return self._tr("plan.strategy.patch")
        return self._tr("plan.strategy.unsafe")

    def _populate_status_filter(self) -> None:
        current_data = self.status_combo.currentData()
        self.status_combo.blockSignals(True)
        self.status_combo.clear()
        self.status_combo.addItem(self._tr("kind.all"), None)
        for status in (
            RelocalizationStatus.AUTO_RELOCALIZE,
            RelocalizationStatus.ALREADY_LOCALIZED,
            RelocalizationStatus.MANUAL_TRANSLATION,
            RelocalizationStatus.MOD_ONLY,
        ):
            self.status_combo.addItem(self._status_text(status), str(status))
        index = self.status_combo.findData(current_data)
        self.status_combo.setCurrentIndex(index if index >= 0 else 0)
        self.status_combo.blockSignals(False)

    def _apply_editor_default_filters(self, *, force: bool = False) -> None:
        desired_status = str(RelocalizationStatus.MOD_ONLY)
        current_status = self.status_combo.currentData()
        if (not force) and current_status not in (None, desired_status):
            return
        self.status_combo.blockSignals(True)
        self.target_only_check.blockSignals(True)
        self.changed_only_check.blockSignals(True)
        status_index = self.status_combo.findData(desired_status)
        if status_index >= 0:
            self.status_combo.setCurrentIndex(status_index)
        self.target_only_check.setChecked(False)
        self.changed_only_check.setChecked(False)
        self.status_combo.blockSignals(False)
        self.target_only_check.blockSignals(False)
        self.changed_only_check.blockSignals(False)

    def _missing_translation_count(self) -> int:
        catalog = self._current_catalog()
        if catalog is None:
            return 0
        return sum(
            1
            for unit in catalog.units
            if unit.status == RelocalizationStatus.MOD_ONLY
            and not str(unit.manual_text or "").strip()
            and not is_unit_skippable(unit)
        )

    def _refresh_editor_status(self) -> None:
        if not hasattr(self, "editor_missing_label"):
            return
        count = self._missing_translation_count()
        self.editor_help_label.setText(self._tr("editor.help"))
        self.editor_missing_label.setText(self._tr("editor.missing").format(count=count))
        self.editor_missing_detail_label.setText(self._tr("editor.missing_detail").format(count=count))

    def _apply_candidate_units(self) -> list[TranslationUnit]:
        catalog = self._paired_catalog
        if catalog is None:
            return []
        return [
            unit
            for unit in catalog.units
            if unit.status in {RelocalizationStatus.AUTO_RELOCALIZE, RelocalizationStatus.MANUAL_TRANSLATION}
        ]

    def _set_apply_buttons_enabled(self, enabled: bool) -> None:
        for name in ("primary_apply_button", "main_apply_button", "apply_button"):
            button = getattr(self, name, None)
            if button is not None:
                button.setEnabled(enabled)

    def _refresh_apply_resume_status(self) -> None:
        if not hasattr(self, "apply_execution_status_label") or self._apply_active:
            return
        catalog = self._paired_catalog
        units = self._apply_candidate_units()
        session = self._writer.load_apply_session(catalog, units=units) if catalog is not None and units else None
        if session is not None and session.pending_dlls:
            self.apply_execution_status_label.setText(
                self._tr("apply.run.resume_available").format(
                    done=len(session.completed_dlls),
                    total=session.total_dlls,
                )
            )
            next_dll = session.pending_dlls[0]
            action = self._tr("apply.run.patch")
            self.apply_execution_current_label.setText(
                self._tr("apply.run.current_dll").format(dll=next_dll, action=action)
            )
            percent = int((len(session.completed_dlls) / max(1, session.total_dlls)) * 100)
            self.apply_execution_progress_bar.setValue(percent)
            if session.last_error:
                self.apply_execution_lines.setPlainText(session.last_error)
            else:
                self.apply_execution_lines.setPlainText("")
        else:
            self.apply_execution_status_label.setText(self._tr("apply.run.idle"))
            self.apply_execution_current_label.setText(self._tr("apply.run.none"))
            self.apply_execution_progress_bar.setValue(0)
            self.apply_execution_lines.setPlainText("")

    def _start_apply_worker(self, catalog: ResourceCatalog, units: list[TranslationUnit]) -> None:
        session = self._writer.load_apply_session(catalog, units=units)
        total_dlls = max(1, len({unit.source.dll_name.lower() for unit in units}))
        completed_dlls = len(session.completed_dlls) if session is not None else 0
        self._apply_active = True
        self._apply_report = None
        self._apply_error = None
        self._set_apply_buttons_enabled(False)
        self.apply_execution_progress_bar.setValue(int((completed_dlls / total_dlls) * 100))
        self.apply_execution_status_label.setText(self._tr("apply.run.running").format(done=completed_dlls, total=total_dlls))
        self.apply_execution_current_label.setText(self._tr("apply.run.none"))
        self.apply_execution_lines.setPlainText("")
        while not self._apply_queue.empty():
            try:
                self._apply_queue.get_nowait()
            except queue.Empty:
                break

        def _worker() -> None:
            try:
                report = self._writer.apply_german_relocalization(
                    catalog,
                    units=units,
                    dll_plans=self._dll_plans,
                    progress_callback=lambda event: self._apply_queue.put({"type": "progress", "event": event}),
                )
                self._apply_queue.put({"type": "success", "report": report})
            except Exception as exc:
                self._apply_queue.put({"type": "error", "error": str(exc)})
            finally:
                self._apply_queue.put({"type": "finished"})

        self._apply_thread = threading.Thread(target=_worker, daemon=True)
        self._apply_thread.start()
        self._apply_poll_timer.start(100)

    def _poll_apply_queue(self) -> None:
        saw_finished = False
        while True:
            try:
                payload = self._apply_queue.get_nowait()
            except queue.Empty:
                break
            kind = str(payload.get("type", "") or "")
            if kind == "progress":
                self._handle_apply_progress_event(payload.get("event", {}))
            elif kind == "success":
                self._apply_report = payload.get("report")
            elif kind == "error":
                self._apply_error = str(payload.get("error", "") or "")
            elif kind == "finished":
                saw_finished = True

        if not saw_finished:
            return

        if self._apply_thread is not None:
            self._apply_thread.join(timeout=0.1)
        self._apply_poll_timer.stop()
        self._apply_active = False
        self._apply_thread = None
        self._set_apply_buttons_enabled(True)

        if self._apply_error:
            failed_dll = "?"
            catalog = self._paired_catalog
            units = self._apply_candidate_units()
            session = self._writer.load_apply_session(catalog, units=units) if catalog is not None and units else None
            if session is not None and session.failed_dll:
                failed_dll = session.failed_dll
            self.apply_execution_status_label.setText(self._tr("apply.run.failed").format(dll=failed_dll))
            self._show_error(self._tr("error.apply_failed").format(error=self._apply_error))
            self._refresh_apply_resume_status()
            return

        report = self._apply_report
        if report is None:
            self._refresh_apply_resume_status()
            return
        total_dlls = max(1, len({unit.source.dll_name.lower() for unit in self._apply_candidate_units()}))
        self.apply_execution_status_label.setText(
            self._tr("apply.run.completed").format(done=total_dlls, total=total_dlls)
        )
        self.apply_execution_progress_bar.setValue(100)
        QMessageBox.information(
            self,
            self._tr("dialog.apply_title"),
            self._tr("dialog.apply_success").format(
                count=report.replaced_units,
                dlls=len(report.written_files),
                backup=report.backup_dir,
            ),
        )
        if self._lang == "en":
            self._set_status(f"Applied {self._target_lang_code}: {report.replaced_units} entries, backup at {report.backup_dir}")
        else:
            self._set_status(f"{self._target_lang_code} angewendet: {report.replaced_units} Eintraege, Backup unter {report.backup_dir}")
        self._load_source_catalog()
        self._load_compare_catalog()

    def _handle_apply_progress_event(self, event: Any) -> None:
        if not isinstance(event, dict):
            return
        total = max(1, int(event.get("total", 1) or 1))
        current = max(1, int(event.get("current", 1) or 1))
        completed = max(0, int(event.get("completed", 0) or 0))
        phase = str(event.get("phase", "") or "")
        dll_name = str(event.get("dll_name", "") or "")
        action_key = "apply.run.copy" if str(event.get("action", "") or "") == "copy" else "apply.run.patch"
        display_done = completed if phase == "done" else min(total, completed + 1)
        percent = int((display_done / total) * 100)
        self.apply_execution_progress_bar.setValue(percent)
        self.apply_execution_status_label.setText(
            self._tr("apply.run.running").format(done=display_done, total=total)
        )
        self.apply_execution_current_label.setText(
            self._tr("apply.run.current_dll").format(dll=dll_name, action=self._tr(action_key))
        )
        preview_lines = list(event.get("preview_lines", []) or [])
        if preview_lines:
            self.apply_execution_lines.setPlainText(
                self._tr("apply.run.current_lines").format(lines="\n".join(preview_lines))
            )
        else:
            self.apply_execution_lines.setPlainText("")

    def _load_persistent_settings(self) -> None:
        saved_language = str(self._settings.value("ui/language", self._lang) or self._lang).lower()
        saved_theme = str(self._settings.value("ui/theme", self._theme) or self._theme).lower()
        saved_source_language = self._normalize_lang_code(self._settings.value("translation/source_language", self._source_lang_code), self._source_lang_code)
        saved_target_language = self._normalize_lang_code(self._settings.value("translation/target_language", self._target_lang_code), self._target_lang_code)
        saved_project_path = str(self._settings.value("project/last_path", "") or "").strip()
        if saved_language in STRINGS:
            self._lang = saved_language
        if saved_theme in THEMES:
            self._theme = saved_theme
        self._source_lang_code = saved_source_language
        self._target_lang_code = saved_target_language
        self._startup_last_project_path = Path(saved_project_path) if saved_project_path else None

    def _save_persistent_settings(self) -> None:
        self._settings.setValue("ui/language", self._lang)
        self._settings.setValue("ui/theme", self._theme)
        self._settings.setValue("translation/source_language", self._source_lang_code)
        self._settings.setValue("translation/target_language", self._target_lang_code)
        self._settings.setValue("project/last_path", str(self._project_path) if self._project_path is not None else "")

    def _apply_theme(self) -> None:
        app = QApplication.instance()
        if app is None:
            return
        app.setStyleSheet(THEMES.get(self._theme, THEMES["light"]))

    def _setup_ui(self) -> None:
        self._refresh_window_title()
        icon = self._resolve_app_icon()
        if icon is not None:
            self.setWindowIcon(icon)
            app = QApplication.instance()
            if app is not None:
                app.setWindowIcon(icon)
        self.resize(1440, 900)
        self._apply_theme()
        self._setup_menu_bar()

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

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

        act_import_exchange = QAction(self._tr("btn.import_exchange"), self)
        act_import_exchange.triggered.connect(self._import_translation_exchange)
        file_menu.addAction(act_import_exchange)

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

        self._language_actions: dict[str, QAction] = {}
        language_labels = dict(LANGUAGE_OPTIONS)
        for code, label in LANGUAGE_OPTIONS:
            if code not in STRINGS:
                continue
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

    def _build_paths_group(self) -> QGroupBox:
        self.paths_group = QGroupBox(self._tr("group.installs"))
        grid = QGridLayout(self.paths_group)

        self.source_edit = QLineEdit()
        self.target_edit = QLineEdit()
        self.source_edit.setPlaceholderText(self._default_install_path_hint("source"))
        self.target_edit.setPlaceholderText(self._default_install_path_hint("target"))
        self.source_lang_label = QLabel(self._tr("label.source_language"))
        self.target_lang_label = QLabel(self._tr("label.target_language"))
        self.source_lang_edit = QComboBox()
        for code, label in LANGUAGE_OPTIONS:
            self.source_lang_edit.addItem(f"{code} - {label}", code)
        self._set_language_combo_value(self.source_lang_edit, self._source_lang_code)
        self.source_lang_edit.currentIndexChanged.connect(lambda _value: self._store_language_pair())
        self.target_lang_edit = QComboBox()
        for code, label in LANGUAGE_OPTIONS:
            self.target_lang_edit.addItem(f"{code} - {label}", code)
        self._set_language_combo_value(self.target_lang_edit, self._target_lang_code)
        self.target_lang_edit.currentIndexChanged.connect(lambda _value: self._store_language_pair())

        self.browse_source_button = QPushButton(self._tr("btn.browse"))
        self.browse_source_button.clicked.connect(lambda: self._pick_directory(self.source_edit))
        self.browse_target_button = QPushButton(self._tr("btn.browse"))
        self.browse_target_button.clicked.connect(lambda: self._pick_directory(self.target_edit))

        self.include_infocards_check = QCheckBox(self._tr("check.infocards"))
        self.include_infocards_check.setChecked(True)

        self.load_source_button = QPushButton(self._tr("btn.load_source"))
        self.load_source_button.clicked.connect(self._load_source_catalog)
        self.compare_button = QPushButton(self._tr("btn.compare"))
        self.compare_button.clicked.connect(self._load_compare_catalog)
        self.export_button = QPushButton(self._tr("btn.export_visible"))
        self.export_button.clicked.connect(self._export_visible_json)
        self.export_mod_only_button = QPushButton(self._tr("btn.export_mod_only"))
        self.export_mod_only_button.clicked.connect(self._export_mod_only_exchange)
        self.export_long_open_button = QPushButton(self._tr("btn.export_long_open"))
        self.export_long_open_button.clicked.connect(self._export_long_open_exchange)
        self.import_exchange_button = QPushButton(self._tr("btn.import_exchange"))
        self.import_exchange_button.clicked.connect(self._import_translation_exchange)
        self.apply_button = QPushButton(self._tr("btn.apply_target"))
        self.apply_button.clicked.connect(self._apply_target_to_install)
        self.toolchain_button = QPushButton(self._tr("btn.install_toolchain"))
        self.toolchain_button.clicked.connect(self._install_toolchain)
        self.toolchain_button.setEnabled(self._writer.is_windows())

        self.source_install_label = QLabel(self._tr("label.source_install"))
        self.target_install_label = QLabel(self._tr("label.target_install"))

        grid.addWidget(self.source_install_label, 0, 0)
        grid.addWidget(self.source_edit, 0, 1)
        grid.addWidget(self.browse_source_button, 0, 2)
        grid.addWidget(self.load_source_button, 0, 3)
        grid.addWidget(self.source_lang_label, 0, 4)
        grid.addWidget(self.source_lang_edit, 0, 5)

        grid.addWidget(self.target_install_label, 1, 0)
        grid.addWidget(self.target_edit, 1, 1)
        grid.addWidget(self.browse_target_button, 1, 2)
        grid.addWidget(self.compare_button, 1, 3)
        grid.addWidget(self.target_lang_label, 1, 4)
        grid.addWidget(self.target_lang_edit, 1, 5)
        self.source_lang_edit.setToolTip(self._tr("tooltip.source_language"))
        self.target_lang_edit.setToolTip(self._tr("tooltip.target_language"))

        actions = QHBoxLayout()
        actions.addWidget(self.include_infocards_check)
        actions.addStretch(1)
        actions.addWidget(self.toolchain_button)
        actions.addWidget(self.import_exchange_button)
        actions.addWidget(self.export_long_open_button)
        actions.addWidget(self.export_mod_only_button)
        actions.addWidget(self.export_button)
        grid.addLayout(actions, 3, 0, 1, 6)
        return self.paths_group

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

    def _build_main_navigation(self) -> QTabWidget:
        self.root_tabs = QTabWidget()
        self.root_tabs.addTab(self._build_start_page(), self._tr("tab.start"))
        self.root_tabs.addTab(self._build_editor_workspace_page(), self._tr("tab.editor"))
        return self.root_tabs

    def _build_start_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(self._build_paths_group())
        layout.addWidget(self._build_progress_group())
        layout.addWidget(self._build_main_workflow_page(), 1)
        layout.addWidget(self._build_apply_execution_group())
        self.primary_apply_button = QPushButton(self._tr("btn.apply_target"))
        self.primary_apply_button.clicked.connect(self._apply_target_to_install)
        self.primary_apply_button.setMinimumHeight(56)
        self.primary_apply_button.setStyleSheet(
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
        layout.addWidget(self.primary_apply_button)
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
        self.apply_execution_lines.setMinimumHeight(130)
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
        layout.addWidget(self.editor_tabs)
        return page

    def _build_main_workflow_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.main_actions_group = QGroupBox(self._tr("group.main_actions"))
        group_layout = QVBoxLayout(self.main_actions_group)
        action_row = QHBoxLayout()
        self.main_export_button = QPushButton(self._tr("btn.export_mod_only"))
        self.main_export_button.clicked.connect(self._export_mod_only_exchange)
        self.main_long_export_button = QPushButton(self._tr("btn.export_long_open"))
        self.main_long_export_button.clicked.connect(self._export_long_open_exchange)
        self.main_import_button = QPushButton(self._tr("btn.import_exchange"))
        self.main_import_button.clicked.connect(self._import_translation_exchange)
        self.main_apply_button = QPushButton(self._tr("btn.apply_target"))
        self.main_apply_button.clicked.connect(self._apply_target_to_install)
        action_row.addWidget(self.main_export_button)
        action_row.addWidget(self.main_long_export_button)
        action_row.addWidget(self.main_import_button)
        action_row.addStretch(1)
        group_layout.addLayout(action_row)
        layout.addWidget(self.main_actions_group)
        self.workflow_summary_label = QLabel(self._tr("summary.none"))
        self.workflow_summary_label.setWordWrap(True)
        layout.addWidget(self.workflow_summary_label)
        layout.addStretch(1)
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
        layout.addWidget(self.translation_progress_bar)
        layout.addWidget(self.translation_progress_label)
        layout.addWidget(self.translation_progress_legend_label)
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

        row.addWidget(self.kind_label)
        row.addWidget(self.kind_combo)
        row.addWidget(QLabel("DLL"))
        row.addWidget(self.dll_combo)
        row.addWidget(self.status_label)
        row.addWidget(self.status_combo)
        row.addWidget(self.target_only_check)
        row.addWidget(self.changed_only_check)
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

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            [
                self._tr("table.units.kind"),
                self._tr("table.units.dll"),
                self._tr("table.units.local_id"),
                self._tr("table.units.global_id"),
                self._tr("table.units.status"),
                self._tr("table.units.changed"),
                self._tr("table.units.preview"),
            ]
        )
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
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
        self.reset_edit_button = QPushButton(self._tr("btn.reset_edit"))
        self.reset_edit_button.clicked.connect(self._reset_manual_edit)
        edit_actions.addStretch(1)
        edit_actions.addWidget(self.reset_edit_button)
        edit_actions.addWidget(self.save_edit_button)
        target_layout.addLayout(edit_actions)

        right_layout.addWidget(source_box, 1)
        right_layout.addWidget(target_box, 1)

        toolchain_state = self._tr("toolchain.available") if self._writer.has_toolchain() else self._tr("toolchain.unavailable")
        self.toolchain_label = QLabel(f"Resource-Toolchain: {toolchain_state}")
        self.toolchain_label.setWordWrap(True)
        right_layout.addWidget(self.toolchain_label)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([900, 500])
        return splitter

    def _pick_directory(self, line_edit: QLineEdit) -> None:
        start_dir = line_edit.text().strip() or str(Path.home())
        directory = QFileDialog.getExistingDirectory(self, self._tr("group.installs"), start_dir)
        if directory:
            line_edit.setText(directory)

    def _default_install_path_hint(self, role: str) -> str:
        if self._writer.is_windows():
            if role == "source":
                return r"C:\Users\STAdmin\Downloads\_FL Fresh Install-englisch"
            return r"C:\Users\STAdmin\Downloads\_FL Fresh Install-deutsch"
        return str(Path.home())

    def _focus_editor_tab(self) -> None:
        if hasattr(self, "root_tabs"):
            self.root_tabs.setCurrentIndex(1)
        if hasattr(self, "editor_tabs"):
            self.editor_tabs.setCurrentIndex(0)
        self._apply_editor_default_filters(force=False)
        self._refresh_table()
        self.table.setFocus()

    def _focus_dll_tab(self) -> None:
        if hasattr(self, "root_tabs"):
            self.root_tabs.setCurrentIndex(1)
        if hasattr(self, "editor_tabs"):
            self.editor_tabs.setCurrentIndex(1)
        self.dll_plan_table.setFocus()

    def _store_language_pair(self) -> None:
        self._source_lang_code = self._combo_language_code(self.source_lang_edit, self._source_lang_code)
        self._target_lang_code = self._combo_language_code(self.target_lang_edit, self._target_lang_code)
        self._set_language_combo_value(self.source_lang_edit, self._source_lang_code)
        self._set_language_combo_value(self.target_lang_edit, self._target_lang_code)
        clear_term_map_cache()
        self._save_persistent_settings()
        self._refresh_terminology_tables()
        self._refresh_footer()

    def _load_source_catalog(self) -> None:
        source_dir = Path(self.source_edit.text().strip())
        if not source_dir.exists():
            self._show_error(self._tr("error.source_missing").format(path=source_dir))
            return
        self._store_language_pair()
        try:
            self._run_with_progress(
                self._tr("dialog.progress_title"),
                self._tr("progress.load_source"),
                lambda: self._with_busy_cursor(
                    lambda: setattr(
                        self,
                        "_source_catalog",
                        self._loader.load_catalog(
                            source_dir,
                            include_infocards=self.include_infocards_check.isChecked(),
                        ),
                    )
                ),
            )
        except Exception as exc:
            self._show_error(self._tr("error.load_source_failed").format(error=exc))
            return

        self._paired_catalog = None
        self._target_catalog = None
        self._dll_plans = []
        self._saved_project_signature = None
        self._apply_editor_default_filters(force=True)
        self._refresh_dll_plan_table()
        self._populate_dll_filter(self._source_catalog)
        self._refresh_table()
        self._update_action_state()
        self._set_status(self._tr("status.loaded_source").format(path=source_dir))

    def _load_compare_catalog(self) -> None:
        if self._source_catalog is None:
            self._load_source_catalog()
            if self._source_catalog is None:
                return

        target_dir = Path(self.target_edit.text().strip())
        if not target_dir.exists():
            self._show_error(self._tr("error.target_missing").format(path=target_dir))
            return
        self._store_language_pair()
        try:
            target_catalog: ResourceCatalog | None = None

            def _load() -> None:
                nonlocal target_catalog
                target_catalog = self._loader.load_catalog(target_dir, include_infocards=self.include_infocards_check.isChecked())

            self._run_with_progress(
                self._tr("dialog.progress_title"),
                self._tr("progress.compare"),
                lambda: self._with_busy_cursor(_load),
            )
            assert target_catalog is not None
            self._target_catalog = target_catalog
            self._paired_catalog = apply_known_term_suggestions(
                pair_catalogs(self._source_catalog, target_catalog),
                target_language=self._target_lang_code,
            )
            self._dll_plans = build_dll_plans(self._source_catalog, self._paired_catalog, target_catalog)
        except Exception as exc:
            self._show_error(self._tr("error.compare_failed").format(error=exc))
            return

        self._apply_editor_default_filters(force=True)
        self._refresh_dll_plan_table()
        self._populate_dll_filter(self._paired_catalog)
        self._refresh_table()
        self._saved_project_signature = None
        self._update_action_state()
        self._set_status(self._tr("status.loaded_compare").format(path=target_dir))

    def _current_catalog(self) -> ResourceCatalog | None:
        return self._paired_catalog or self._source_catalog

    def _selected_unit(self) -> TranslationUnit | None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._visible_units):
            return None
        return self._visible_units[row]

    def _unit_key(self, unit: TranslationUnit) -> tuple[str, str, int]:
        return (str(unit.kind), unit.source.dll_name.lower(), int(unit.source.local_id))

    def _replace_current_catalog(self, catalog: ResourceCatalog) -> None:
        if self._paired_catalog is not None:
            self._paired_catalog = catalog
        else:
            self._source_catalog = catalog
        self._update_action_state()

    def _select_unit_by_key(self, key: tuple[str, str, int]) -> None:
        for row, unit in enumerate(self._visible_units):
            if self._unit_key(unit) == key:
                self.table.selectRow(row)
                return

    def _current_project(self) -> TranslatorProject:
        return TranslatorProject(
            source_install_dir=self.source_edit.text().strip(),
            target_install_dir=self.target_edit.text().strip(),
            include_infocards=self.include_infocards_check.isChecked(),
            source_language=self._source_lang_code,
            target_language=self._target_lang_code,
            source_catalog=self._source_catalog,
            target_catalog=self._target_catalog,
            paired_catalog=self._paired_catalog,
            dll_plans=tuple(self._dll_plans),
        )

    def _reset_session_state(self) -> None:
        self._project_path = None
        self._saved_project_signature = None
        self._source_catalog = None
        self._target_catalog = None
        self._paired_catalog = None
        self._dll_plans = []
        self._visible_units = []
        self.include_infocards_check.setChecked(True)
        self._apply_editor_default_filters(force=True)
        self._populate_dll_filter(None)
        self._refresh_dll_plan_table()
        self._refresh_table()
        self._refresh_footer()
        self._save_persistent_settings()
        self._update_action_state()

    def _manual_entry_count(self) -> int:
        catalog = self._current_catalog()
        if catalog is None:
            return 0
        return sum(1 for unit in catalog.units if unit.status == RelocalizationStatus.MANUAL_TRANSLATION)

    def _translation_progress(self) -> tuple[int, int, int, int, int, int]:
        catalog = self._current_catalog()
        if catalog is None:
            return (0, 0, 0, 0, 0, 0)
        progress = calculate_translation_progress(catalog)
        return (
            progress.localized,
            progress.done,
            progress.skipped,
            progress.total,
            progress.done_percent,
            progress.covered_percent,
        )

    def _update_action_state(self) -> None:
        has_source = self._source_catalog is not None
        has_comparison = self._paired_catalog is not None
        has_catalog = self._current_catalog() is not None
        has_toolchain = self._writer.has_toolchain()
        can_apply = has_comparison and has_toolchain and not self._apply_active
        apply_tooltip = ""
        if not has_comparison:
            apply_tooltip = self._tr("tooltip.apply_disabled_compare")
        elif not has_toolchain:
            apply_tooltip = self._tr("tooltip.apply_disabled_toolchain")
        if hasattr(self, "compare_button"):
            self.compare_button.setEnabled(has_source)
            self.export_button.setEnabled(has_catalog)
            self.export_mod_only_button.setEnabled(has_catalog)
            self.export_long_open_button.setEnabled(has_catalog)
            self.import_exchange_button.setEnabled(has_catalog)
            self.apply_button.setEnabled(can_apply)
            self.apply_button.setToolTip(apply_tooltip)
        if hasattr(self, "primary_apply_button"):
            self.primary_apply_button.setEnabled(can_apply)
            self.primary_apply_button.setToolTip(apply_tooltip)
        if hasattr(self, "main_export_button"):
            self.main_export_button.setEnabled(has_catalog)
            self.main_long_export_button.setEnabled(has_catalog)
            self.main_import_button.setEnabled(has_catalog)
            self.main_apply_button.setEnabled(can_apply)
            self.main_apply_button.setToolTip(apply_tooltip)
        if hasattr(self, "root_tabs"):
            self.root_tabs.setTabEnabled(0, True)
            self.root_tabs.setTabEnabled(1, has_catalog)
        if hasattr(self, "editor_tabs"):
            self.editor_tabs.setTabEnabled(0, has_catalog)
            self.editor_tabs.setTabEnabled(1, has_comparison)
            self.editor_tabs.setTabEnabled(2, has_catalog)

    def _current_project_signature(self) -> str | None:
        if self._current_catalog() is None:
            return None
        return project_signature(self._current_project())

    def _is_project_dirty(self) -> bool:
        current_signature = self._current_project_signature()
        if current_signature is None:
            return False
        if self._saved_project_signature is None:
            return True
        return current_signature != self._saved_project_signature

    def _populate_dll_filter(self, catalog: ResourceCatalog | None) -> None:
        current_text = self.dll_combo.currentText()
        self.dll_combo.blockSignals(True)
        self.dll_combo.clear()
        self.dll_combo.addItem(self._tr("kind.all"))
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
            self.summary_label.setText(self._tr("summary.none"))
            self.workflow_summary_label.setText(self._tr("summary.none"))
            self._refresh_dll_plan_table()
            self.source_preview.clear()
            self.target_preview.clear()
            self.detail_label.setText(self._tr("detail.none"))
            self._refresh_project_status()
            self._refresh_progress()
            self._refresh_editor_status()
            self._refresh_apply_resume_status()
            return

        units = list(catalog.units)
        if self.kind_combo.currentText() != self._tr("kind.all"):
            units = [unit for unit in units if unit.kind == ResourceKind(self.kind_combo.currentText())]
        if self.dll_combo.currentText() != self._tr("kind.all"):
            units = [unit for unit in units if unit.source.dll_name == self.dll_combo.currentText()]
        if self.status_combo.currentData() is not None:
            units = [unit for unit in units if unit.status == RelocalizationStatus(str(self.status_combo.currentData()))]
        if self.target_only_check.isChecked():
            units = [unit for unit in units if unit.target is not None]
        if self.changed_only_check.isChecked():
            units = [unit for unit in units if unit.is_changed]

        search_value = self.search_edit.text().strip().lower()
        if search_value and len(search_value) >= 2:
            units = [unit for unit in units if search_value in unit.source_text.lower() or search_value in unit.replacement_text.lower()]

        self._visible_units = units
        self.table.setRowCount(len(units))
        for row, unit in enumerate(units):
            values = [
                str(unit.kind),
                unit.source.dll_name,
                str(unit.source.local_id),
                str(unit.source.global_id),
                self._status_text(unit.status),
                self._tr("yes") if unit.is_changed else self._tr("no"),
                " ".join(unit.source_text.split())[:120],
            ]
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))

        self.table.resizeColumnsToContents()
        self._update_summary(catalog, units)
        if units:
            self.table.selectRow(0)
        else:
            self.source_preview.clear()
            self.target_preview.clear()
            self.detail_label.setText(self._tr("detail.none"))
        self._refresh_project_status()
        self._refresh_progress()
        self._refresh_editor_status()
        self._refresh_apply_resume_status()

    def _schedule_search_refresh(self) -> None:
        search_value = self.search_edit.text().strip()
        if len(search_value) == 0:
            self._search_debounce_timer.stop()
            self._refresh_table()
            return
        if len(search_value) < 2:
            return
        self._search_debounce_timer.start(400)

    def _refresh_dll_plan_table(self) -> None:
        self.dll_plan_table.setRowCount(len(self._dll_plans))
        for row, plan in enumerate(self._dll_plans):
            total_units = max(1, plan.source_strings + plan.source_infocards)
            coverage_percent = round((plan.translated_units / total_units) * 100)
            action = (
                self._tr("plan.action.full")
                if plan.strategy == DllStrategy.FULL_REPLACE_SAFE
                else self._tr("plan.action.patch")
                if plan.strategy == DllStrategy.PATCH_REQUIRED
                else self._tr("plan.action.unsafe")
            )
            values = [
                plan.dll_name,
                self._dll_strategy_label(plan.strategy),
                f"{coverage_percent}% ({plan.translated_units}/{total_units})",
                str(plan.translated_units),
                str(plan.mod_only_units),
                str(plan.matched_units),
                action,
            ]
            for column, value in enumerate(values):
                self.dll_plan_table.setItem(row, column, QTableWidgetItem(value))
        self.dll_plan_table.resizeColumnsToContents()

    def _sync_dll_filter_from_plan_table(self) -> None:
        row = self.dll_plan_table.currentRow()
        if row < 0 or row >= len(self._dll_plans):
            return
        index = self.dll_combo.findText(self._dll_plans[row].dll_name)
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

    def _export_visible_json(self) -> None:
        catalog = self._current_catalog()
        if catalog is None:
            self._show_error(self._tr("error.load_first"))
            return
        output_path, _ = QFileDialog.getSaveFileName(self, self._tr("dialog.export_visible"), str(Path.cwd() / "build" / "translator-export.json"), "JSON Files (*.json)")
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
            self._set_status(f"{len(self._visible_units)} Eintraege exportiert: {output_path}")

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
            apply_known_term_suggestions(project.paired_catalog, target_language=self._target_lang_code)
            if project.paired_catalog is not None
            else None
        )
        self._dll_plans = list(project.dll_plans)
        self._apply_editor_default_filters(force=True)
        self._saved_project_signature = self._current_project_signature()
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
        merged = apply_known_term_suggestions(merged, target_language=self._target_lang_code)
        if self._paired_catalog is not None:
            self._paired_catalog = merged
        else:
            self._source_catalog = merged
        self._refresh_table()
        manual_count = sum(1 for unit in merged.units if unit.status == RelocalizationStatus.MANUAL_TRANSLATION)
        if self._lang == "en":
            self._set_status(f"{manual_count} manual translations loaded: {input_path}")
        else:
            self._set_status(f"{manual_count} manuelle Uebersetzungen geladen: {input_path}")

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
        dialog = SettingsDialog(self._theme, self)
        if dialog.exec() != QDialog.Accepted:
            return
        self._theme = dialog.selected_theme
        self._save_persistent_settings()
        self._apply_theme()
        self._retranslate_ui()
        self._set_status(self._tr("status.settings_applied"))

    def _set_language(self, language_code: str) -> None:
        new_lang = str(language_code or "").strip().lower()
        if new_lang not in STRINGS or new_lang == self._lang:
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
            GITHUB_LATEST_RELEASE_API,
            headers={"Accept": "application/vnd.github+json", "User-Agent": "FL-Lingo-Updater"},
        )

        def _api_try(context=None) -> dict[str, str] | None:
            with urlrequest.urlopen(req, timeout=12.0, context=context) as resp:
                payload = json.loads(resp.read().decode("utf-8", errors="replace"))
            if isinstance(payload, dict) and str(payload.get("tag_name", "")).strip():
                return {
                    "tag_name": str(payload.get("tag_name", "")).strip(),
                    "html_url": str(payload.get("html_url", "")).strip() or GITHUB_REPO_URL,
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
                GITHUB_LATEST_RELEASE_URL,
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
        latest_url = str(info.get("html_url", "") or "").strip() or GITHUB_REPO_URL
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
                github=GITHUB_REPO_URL,
                discord=DISCORD_INVITE_URL,
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

    def _retranslate_ui(self) -> None:
        self.menuBar().clear()
        self._setup_menu_bar()
        self._refresh_window_title()
        self.paths_group.setTitle(self._tr("group.installs"))
        self.progress_group.setTitle(self._tr("group.progress"))
        self.main_actions_group.setTitle(self._tr("group.main_actions"))
        self.apply_execution_group.setTitle(self._tr("group.apply_execution"))
        self.filters_group.setTitle(self._tr("group.filters"))
        self.dll_group.setTitle(self._tr("group.dll_analysis"))
        self.editor_help_label.setText(self._tr("editor.help"))
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
        self.apply_button.setText(self._tr("btn.apply_target"))
        self.primary_apply_button.setText(self._tr("btn.apply_target"))
        self.toolchain_button.setText(self._tr("btn.install_toolchain"))
        self.main_export_button.setText(self._tr("btn.export_mod_only"))
        self.main_long_export_button.setText(self._tr("btn.export_long_open"))
        self.main_import_button.setText(self._tr("btn.import_exchange"))
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
        self.root_tabs.setTabText(1, self._tr("tab.editor"))
        self.editor_tabs.setTabText(0, self._tr("tab.editor"))
        self.editor_tabs.setTabText(1, self._tr("tab.dlls"))
        self.editor_tabs.setTabText(2, self._tr("tab.terminology"))
        self._retitle_combo_items()
        self._update_units_header()
        self._update_dll_plan_headers()
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

    def _refresh_window_title(self, project_name: str | None = None) -> None:
        resolved_project_name = project_name or (
            self._project_path.name if self._project_path is not None else self._tr("project.none")
        )
        project_state = self._tr("project.unsaved") if self._is_project_dirty() else self._tr("project.saved")
        project_info = self._tr("project.info").format(name=resolved_project_name, dirty=project_state)
        self.setWindowTitle(f"{self._config.app_title} v{self._config.app_version} | {project_info}")

    def _refresh_progress(self) -> None:
        localized, done, skipped, total, _percent, covered_percent = self._translation_progress()
        self.translation_progress_bar.set_progress(total=total, localized=localized, done=done, skipped=skipped)
        if total == 0:
            self.translation_progress_label.setText(self._tr("progress.none"))
            return
        self.translation_progress_label.setText(
            self._tr("progress.text").format(
                percent=covered_percent,
                done=done + skipped,
                total=total,
                localized=localized,
                available=max(0, done - localized),
                skipped=skipped,
            )
        )

    def _refresh_toolchain_label(self) -> None:
        toolchain_state = self._tr("toolchain.available") if self._writer.has_toolchain() else self._tr("toolchain.unavailable")
        self.toolchain_label.setText(f"Resource-Toolchain: {toolchain_state}")

    def _retitle_combo_items(self) -> None:
        self.kind_combo.setItemText(0, self._tr("kind.all"))
        self.dll_combo.setItemText(0, self._tr("kind.all"))
        self._populate_status_filter()

    def _update_units_header(self) -> None:
        self.table.setHorizontalHeaderLabels(
            [
                self._tr("table.units.kind"),
                self._tr("table.units.dll"),
                self._tr("table.units.local_id"),
                self._tr("table.units.global_id"),
                self._tr("table.units.status"),
                self._tr("table.units.changed"),
                self._tr("table.units.preview"),
            ]
        )

    def _update_dll_plan_headers(self) -> None:
        labels = [
            self._tr("table.plans.dll"),
            self._tr("table.plans.status"),
            self._tr("table.plans.coverage"),
            self._tr("table.plans.ready"),
            self._tr("table.plans.open"),
            self._tr("table.plans.reference"),
            self._tr("table.plans.action"),
        ]
        tooltips = [
            self._tr("dll.tooltip.dll"),
            self._tr("dll.tooltip.status"),
            self._tr("dll.tooltip.coverage"),
            self._tr("dll.tooltip.ready"),
            self._tr("dll.tooltip.open"),
            self._tr("dll.tooltip.reference"),
            self._tr("dll.tooltip.action"),
        ]
        self.dll_plan_table.setHorizontalHeaderLabels(labels)
        for index, tooltip in enumerate(tooltips):
            header_item = self.dll_plan_table.horizontalHeaderItem(index)
            if header_item is not None:
                header_item.setToolTip(tooltip)

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
        QMessageBox.critical(self, self._config.app_title, message)
        self._set_status(self._tr("status.operation_failed"))

    def _set_status(self, message: str) -> None:
        self.status_bar.showMessage(message, 10000)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._confirm_unsaved_changes():
            event.accept()
            return
        event.ignore()


class _DefaultConfig:
    app_title = "FL Lingo"
    app_version = "0.1.0"
    developed_by = "Developed by Aldenmar Odin - flathack"
    default_language = "en"
    default_theme = "light"
    default_source_language = "en"
    default_target_language = "de"


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


def run(config: Any = None) -> int:
    app = QApplication.instance() or QApplication([])
    window = TranslatorMainWindow(config)
    window.show()
    return app.exec()
