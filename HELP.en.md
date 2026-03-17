# FL Lingo — Help

**Version:** 0.2.0
**Developed by:** Aldenmar Odin — flathack  
**GitHub:** [github.com/flathack/FL-Lingo](https://github.com/flathack/FL-Lingo)  
**Discord:** [discord.com/invite/RENtMMcc](https://discord.com/invite/RENtMMcc)

---

## Table of Contents

1. [What is FL Lingo?](#1-what-is-fl-lingo)
2. [Installation and Launch](#2-installation-and-launch)
3. [The Two Modes](#3-the-two-modes)
4. [Simple Mode — Quick Start](#4-simple-mode--quick-start)
5. [Expert Mode — Overview](#5-expert-mode--overview)
   - [Preparation](#51-preparation)
   - [Scan](#52-scan)
   - [Editing](#53-editing)
   - [Extras (Import / Export / Auto-Translate)](#54-extras-import--export--auto-translate)
   - [Translate (Apply)](#55-translate-apply)
6. [The Editor Workspace](#6-the-editor-workspace)
   - [Filters](#61-filters)
   - [Source and Target Text Preview](#62-source-and-target-text-preview)
   - [Manual Editing](#63-manual-editing)
7. [DLL Analysis](#7-dll-analysis)
8. [Terminology and Patterns](#8-terminology-and-patterns)
9. [Mod Overrides](#9-mod-overrides)
10. [Export and Import for External Translation](#10-export-and-import-for-external-translation)
11. [Automatic Translation (Bulk Translate)](#11-automatic-translation-bulk-translate)
12. [Project Files (.FLLingo)](#12-project-files-fllingo)
13. [Backups and Recovery](#13-backups-and-recovery)
14. [Updates](#14-updates)
15. [Menu Bar](#15-menu-bar)
16. [Status Values and Progress](#16-status-values-and-progress)
17. [Settings](#17-settings)
18. [Languages and Themes](#18-languages-and-themes)
19. [Safety Notes](#19-safety-notes)
20. [Frequently Asked Questions (FAQ)](#20-frequently-asked-questions-faq)
21. [Troubleshooting](#21-troubleshooting)
22. [Technical Details](#22-technical-details)

---

## 1. What is FL Lingo?

FL Lingo is a relocalization tool for Freelancer mods. Many Freelancer mods ship with English-only texts — FL Lingo helps translate the mod-specific content into other languages, typically German.

**The three core tasks:**

1. **Find reference texts:** FL Lingo compares a mod installation with a clean reference installation and automatically identifies which mod texts correspond to known reference texts and can be reused.
2. **Identify mod-specific texts:** New texts that only exist in the mod are marked as "open" and can be translated externally or manually.
3. **Write back:** FL Lingo safely writes the finished translations back into the mod's resource DLLs — with automatic backup.

**Supported resource types:**

- String tables (`RT_STRING`) from resource DLLs
- Infocards / HTML resources (`RT_HTML`) from resource DLLs
- DLL references are detected via `EXE\freelancer.ini`

**Commonly affected files:**

- `InfoCards.dll`, `MiscText.dll`, `MiscTextInfo2.dll`
- `NameResources.dll`, `EquipResources.dll`
- `OfferBribeResources.dll` and others

---

## 2. Installation and Launch

### Option A: Windows Executable (recommended)

Download the latest release from [GitHub Releases](https://github.com/flathack/FL-Lingo/releases) and run `FL-Lingo.exe`.

### Option B: From Source

**Requirements:** Python 3.11+

```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Activate (Linux/macOS)
source .venv/bin/activate

# Install
python -m pip install -U pip
python -m pip install -e .[all]

# Launch
python launch.py
```

### Open a project file directly

```bash
python launch.py path/to/project.FLLingo
```

---

## 3. The Two Modes

FL Lingo offers two user interfaces that can be toggled in the top toolbar:

| Mode | Description |
|------|-------------|
| **Simple Mode** | Guided three-column workflow: Choose folders → Scan → Translate. Ideal for the standard use case. |
| **Expert Mode** | Full access to the editor, filters, DLL analysis, terminology, import/export, and project management. |

---

## 4. Simple Mode — Quick Start

Simple Mode guides you through the entire process in three columns:

### Column 1: Folder Selection

| Field | Description |
|-------|-------------|
| **Mod Installation** | The Freelancer folder with the installed mod (usually English). |
| **Freelancer Installation** | A clean reference installation in the target language (e.g. German). |
| **English Vanilla Installation** *(optional)* | An English original installation — required for voice line merging (UTF voice files). |

### Column 2: Scan

Click **"Start Scan"** to load and compare both installations. Afterwards you'll see:

- A pie chart showing translation progress
- Audio progress (which German voice files are already present)
- Voice line progress (UTF voice lines)
- A summary with entries, automatic matches, and open texts

### Column 3: Translate

After the scan you can:

- **Apply translation:** Writes all available translations into the mod installation.
- **Copy audio too:** Additionally copies German voice files from the reference (checkbox).

---

## 5. Expert Mode — Overview

Expert Mode shows five sequential sections on the start page:

### 5.1 Preparation

| Element | Description |
|---------|-------------|
| **Game with Mod / current game** | Path to the mod installation. |
| **Reference installation / comparison game** | Path to the clean reference installation. |
| **English Vanilla Installation** *(optional)* | Path for voice merging. |
| **Source language / Target language** | Set the language pair (e.g. en → de). |
| **Install toolchain** | Installs the LLVM resource tools needed for patching DLLs. |

### 5.2 Scan

| Element | Description |
|---------|-------------|
| **Start Scan** | Loads the mod installation and automatically compares it with the reference. |
| **Include Infocards** | When active, multi-line infocards are also included in the scan. |

After the scan, a summary appears: total entries, automatic matches, manual translations, open entries, and affected DLLs.

### 5.3 Editing

This section only becomes visible after a successful scan. It contains a link to the **Editor Workspace** ("Open Translations" tab), where individual entries can be manually edited.

### 5.4 Extras (Import / Export / Auto-Translate)

| Button | Description |
|--------|-------------|
| **Export open entries** | Exports all open entries as JSON for external translation. |
| **Export long open texts** | Exports only long open texts (e.g. infocards) as JSON. |
| **Import translation** | Imports an externally translated JSON file and adopts the texts as manual translations. |
| **Remove imported texts** | Removes all manually imported translations. |
| **Auto-translate all open** | Opens the Bulk Translate dialog for automatic translation of all open entries via Translator API. |

Each button has a **?** icon next to it that shows an explanation on click or hover.

### 5.5 Translate (Apply)

| Button | Description |
|--------|-------------|
| **Translate text** | Writes the available translations into the mod DLLs. |
| **Copy German audio** | Copies German voice files from the reference into the mod installation. |
| **Merge German voice lines** | Replaces unchanged English voice lines in UTF files with German equivalents. |
| **Translate all** *(large green button)* | Performs text translation, audio copy, and voice line merge all at once. |

Below these appear:

- **Translation progress:** Segmented progress bar + audio and voice progress.
- **Translation run:** Live status during DLL writing with current DLL name, progress bar, and entry log.

---

## 6. The Editor Workspace

In the **"Open Translations"** tab you'll find the core editor with table, filters, and preview area.

### 6.1 Filters

The filter bar at the top allows you to narrow down the entry table. Each filter has a **?** icon with an explanation.

| Filter | Description |
|--------|-------------|
| **Type** *(Kind)* | Filter by String or Infocard. |
| **DLL** | Filter by a specific resource DLL. |
| **Status** | Filter by status: automatic, manual, open, etc. |
| **Target only** | Shows only entries that have a reference translation. |
| **Changed only** | Shows only entries that differ from the original. |
| **Search** | Full-text search across source text and target text. |

Above the table, the **Old Text Source** can also be selected — this allows using a previous backup as the comparison text.

### 6.2 Source and Target Text Preview

The detail view on the right shows:

| Area | Description |
|------|-------------|
| **Source text** *(upper)* | The current text from the mod installation. Read-only. Right-click offers terminology options. |
| **Target text / Reference text** *(lower)* | The text from the reference or the manual translation. Directly editable. |

### 6.3 Manual Editing

Below the target text field there are three action buttons (each with **?** help):

| Button | Description |
|--------|-------------|
| **Translate** | Translates the source text via an external translator (e.g. Google Translate) and writes the result into the target text. |
| **Reset manual change** | Resets the manual translation for this entry back to the original text. |
| **Save change** | Saves the manual change in the target text field as a translation for this entry. |

**Right-click context menu** on the source or target text also offers:

- Use selection as source term
- Use selection as target term
- Save mapping for selection
- Create mod override (keep original or with custom text)

---

## 7. DLL Analysis

In the **"DLL Analysis"** tab, FL Lingo shows an overview for each affected DLL:

| Column | Description |
|--------|-------------|
| **DLL** | Name of the resource DLL. |
| **Status** | Fully covered, partially open, or limited coverage only. |
| **Coverage** | Proportion of entries that are automatically or manually translated. |
| **Ready** | Entries that FL Lingo can apply directly. |
| **Open** | Entries that still need to be translated. |
| **With Reference** | Entries with a matching counterpart in the reference installation. |
| **Action** | The recommended action when applying (full patch, partial patch, manual review). |

**DLL writing strategies:**

| Strategy | Meaning |
|----------|---------|
| **Fully covered** | All entries from the reference present — safe full patch. |
| **Partially covered** | Some entries match, others are open — only matched entries are patched. |
| **Limited coverage** | Low automatic coverage — manual review recommended. |

---

## 8. Terminology and Patterns

In the **"Terminology"** tab you manage language-specific terminology mappings and pattern rules.

### Terminology Mapping

Map source terms to target terms here (e.g. "Battleship" → "Schlachtschiff"). FL Lingo uses these mappings for:

- Glossary export
- Known term replacement
- Translation suggestions for open entries
- Consistent naming of factions, locations, and roles

| Field | Description |
|-------|-------------|
| **Source term** | The original term. |
| **Target term** | The desired translation. |
| **Use selection** | Fills the fields from the current text selection. |
| **Save mapping** | Saves the mapping to the active terminology file. |

### Pattern Rules

Pattern rules automatically replace recurring text patterns.

| Field | Description |
|-------|-------------|
| **Pattern source** | The search pattern. |
| **Pattern target** | The replacement text. |
| **Save pattern** | Saves the pattern rule. |
| **Reload lists** | Reloads terminology and patterns from disk. |

**Terminology files:**

- `data/terminology.de.json` — German terminology
- `data/terminology.en.json` — English terminology

The active file depends on the selected target language.

---

## 9. Mod Overrides

In the **"Mod Overrides"** tab you can specify for individual entries that FL Lingo should keep the original mod text or use a custom text — regardless of what the reference says.

| Button | Description |
|--------|-------------|
| **Reload overrides** | Reloads the override data from disk. |
| **Delete selected override** | Removes the selected override entry. |

Overrides can also be created via the **right-click context menu** in the editor.

---

## 10. Export and Import for External Translation

FL Lingo supports a JSON-based workflow for external translation:

### Export

1. **Export open entries:** Exports all entries with "Mod-Only" status (no reference match) as a JSON file.
2. **Export long open texts:** Exports only long open texts (e.g. infocards) — useful for separate processing.
3. **Export visible JSON:** Exports the currently filtered/visible table as JSON.

### Import

- **Import translation:** Imports an externally translated JSON file. The texts are adopted as manual translations.
- **Remove imported texts:** Resets all manually imported translations.

The JSON file format contains per entry:
- DLL name and resource ID
- Original text (source text)
- Placeholder for the translated text

---

## 11. Automatic Translation (Bulk Translate)

Via the **"Auto-translate all open"** button, a dialog opens where open entries can be translated via an external Translator API.

### Usage

1. **Set minimum length:** Filters out short entries (e.g. only translate texts with 50+ characters).
2. **Preview:** Shows all entries to be translated and their count before the translation starts.
3. **Start:** Begins the automatic translation.
4. **Pause / Resume:** Pauses the process at any time. Progress so far is preserved.
5. **Close:** Closes the dialog. Already translated entries are saved in the project.

The result table shows for each entry:
- DLL/ID reference
- Old text (source text)
- New text (translation)

### Configure Translator API

Via **Settings → Translator API…** you can configure the translation provider and optionally an API key.

| Setting | Description |
|---------|-------------|
| **Provider** | Currently supported: Google Translate (via `deep-translator`). |
| **API key** | Not required for free Google Translate. Optional for other providers or higher rate limits. |

---

## 12. Project Files (.FLLingo)

FL Lingo can save and load complete work sessions as `.FLLingo` project files.

**A project file stores:**

- Selected installation paths
- Language pair (source and target language)
- Infocards option
- Paired catalog state
- Manual translations
- DLL analysis state

**File association:** Via **File → Associate .FLLingo…** the file extension can be registered so that project files open FL Lingo on double-click.

### Project Actions (File menu)

| Action | Description |
|--------|-------------|
| **Load project** | Open an existing `.FLLingo` file. |
| **New project** | Start an empty project. |
| **Rebuild project** | Recreate project from game data (manual edits will be lost). |
| **Save project** | Save current state. |
| **Save project as** | Save under a new name. |

---

## 13. Backups and Recovery

FL Lingo automatically creates a backup of affected DLL files before every write operation.

| Function | Description |
|----------|-------------|
| **Automatic backup** | Every "Translate" operation backs up the original DLLs. |
| **Restore backup** | Via **File → Restore Backup…** a previous state can be restored. |
| **Apply-Resume** | If a translation run is interrupted, it can be resumed next time. |

---

## 14. Updates

FL Lingo automatically checks for new versions on startup (after ~1 second) via GitHub Releases.

### Automatic Update Check

- Can be disabled (via environment variable `FLATLAS_DISABLE_STARTUP_UPDATE_CHECK=1`).
- Previously dismissed versions will not be shown again.

### Manual Update Check

Via **Help → Check for Updates…** you can check manually at any time.

### Install Update (Windows Executable)

When FL Lingo is running as a packaged `.exe` and a matching update package is available:

1. Click **"Install Update"** in the update dialog.
2. The update is downloaded (with progress indicator).
3. The updater (`FLLingoUpdater.exe`) takes over: waits for app to close → copies new files → restarts FL Lingo.

If automatic updating is not possible, you can open the GitHub page via **"Open Release"** and download the update manually.

---

## 15. Menu Bar

### File

| Entry | Description |
|-------|-------------|
| Load game | Load mod installation into the catalog. |
| Compare with reference | Compare loaded source against reference. |
| Load project / New project / Rebuild | Project management. |
| Save project / Save as | Save work. |
| Restore backup | Restore a previous DLL state. |
| Associate .FLLingo | Set up file association. |
| Export visible JSON | Export filtered table as JSON. |
| Export open entries / Long texts | Export for external translation. |
| Import translation | Import external translation. |
| Copy German audio | Copy voice files. |
| Merge German voice lines | Merge UTF voice files. |
| Build patch | Create a distributable patch folder. |
| Translate text | Write translations into DLLs. |

### View

| Entry | Description |
|-------|-------------|
| Show DLL analysis | Switch to the DLL tab. |
| Show entries | Switch to the entries tab. |

### Settings

| Entry | Description |
|-------|-------------|
| Appearance | Choose theme (light, dark, high contrast). |
| Open terminology | Open terminology file in external editor. |
| Install toolchain | Install LLVM tools. |
| Translator API | Configure translator provider and API key. |

### Language

Switches the UI language: English, German, French, Spanish, Russian.

### Help

| Entry | Description |
|-------|-------------|
| Check for updates | Checks GitHub for new releases. |
| Open help | Opens the built-in HTML help window. |
| About FL Lingo | Shows version, developer, and links. |

---

## 16. Status Values and Progress

### Entry Status

| Status | Color | Meaning |
|--------|-------|---------|
| **Already localized** | 🟣 Purple | The source text already matches the reference. |
| **Auto-applicable** | 🟢 Green | The reference text differs — ready to apply. |
| **Manually translated** | 🟢 Green | User or imported translation available. |
| **Mod-Only** | ⚪ Gray | No reference match found — must be translated manually or externally. |
| **Skipped** | 🟡 Yellow | Placeholders, numbers, proper names — intentionally not translated. |

### Progress Indicators

| Indicator | Format |
|-----------|--------|
| **Translation progress** | Percent · processed/total entries · already localized · ready to apply · skipped |
| **Audio progress** | Percent · existing/total German voice files · open |
| **Voice line progress** | Percent German · DE/total · replaceable · mod-modified · files |

### Progress Bar Legend

- **Purple** = already translated in-game
- **Green** = ready to apply
- **Yellow** = intentionally skipped
- **Gray** = open

---

## 17. Settings

### Appearance

Via **Settings → Appearance** the theme can be selected.

### Translator API

Via **Settings → Translator API** the translator is configured:

- **Provider:** Google Translate (via `deep-translator`)
- **API key:** Optional, not required for free Google Translate.

### Environment Variables

| Variable | Effect |
|----------|--------|
| `FLATLAS_DISABLE_STARTUP_UPDATE_CHECK=1` | Disables the automatic update check on startup. |
| `FLATLAS_TOOLCHAIN_DIR` | Sets the path to the external resource toolchain (LLVM tools). |

---

## 18. Languages and Themes

### UI Languages

| Language | Coverage |
|----------|----------|
| **German** | Full |
| **English** | Full |
| **French** | Partial (core labels, menus, updates) |
| **Spanish** | Partial |
| **Russian** | Partial (transliterated) |

The language is switched via the **Language** menu and applied immediately at runtime.

### Themes

| Theme | Description |
|-------|-------------|
| **light** | Light background |
| **dark** | Dark background (default) |
| **high contrast** | High contrast for better readability |

---

## 19. Safety Notes

FL Lingo modifies Freelancer resource DLLs. A backup is automatically created before every write operation.

**Recommendations:**

- Test on a **copy** of the game first.
- Keep a clean reference installation **unchanged**.
- Verify results with actual mods before applying to your main installation.
- Use **Backup Restore** if something doesn't look right.

---

## 20. Frequently Asked Questions (FAQ)

### What is the "reference installation"?

A clean, unmodified Freelancer installation in the target language (e.g. a German vanilla installation). FL Lingo uses it as a source for known translations.

### Do I need the English vanilla installation?

Only optionally — it is needed for voice line merging (UTF voice lines). English voice lines in the mod are compared with German ones from the reference and replaced.

### What does "Mod-Only" mean?

An entry that exists in the mod but has no counterpart in the reference installation. These texts were newly added by the mod and must be translated manually or externally.

### Can I interrupt and resume the process?

Yes. Both the apply run and bulk translation can be paused and resumed next time. Progress is saved in the project.

### What happens when FL Lingo classifies a DLL as "unsafe"?

FL Lingo does not overwrite the DLL blindly. Instead, manual review is recommended. Only confirmed entries are patched.

### Can I correct my own translations?

Yes. In the editor tab you can directly edit the target text and save it as a manual translation via **"Save change"**.

### What does "Build patch" do?

It creates a distributable folder with all modified DLLs and a manifest — useful if you want to share your translation as a patch.

---

## 21. Troubleshooting

### "No resource toolchain found"

FL Lingo requires LLVM resource tools (`llvm-rc`, `llvm-windres`) for patching DLLs. Install them via **Settings → Install toolchain** or set the environment variable `FLATLAS_TOOLCHAIN_DIR`.

### "deep-translator is not installed"

Automatic translation requires the Python package `deep-translator`. Install it with:

```bash
pip install deep-translator
```

With the Windows executable it is already included.

### Update check fails

Check your internet connection. FL Lingo tries three fallback methods (API with TLS, API without TLS verification, URL redirect parsing). For firewall issues, the check can be retried manually via **Help → Check for Updates**.

### Translation is not applied

Make sure that:
1. Both installations are loaded and compared.
2. The resource toolchain is available.
3. At least one DLL is "ready" or "partially covered".

---

## 22. Technical Details

### Project Structure

| File / Folder | Purpose |
|---------------|---------|
| `launch.py` | Entry point and central app defaults |
| `src/flatlas_translator/ui_app.py` | Main window |
| `src/flatlas_translator/ui_builders.py` | Widget and page construction |
| `src/flatlas_translator/ui_state.py` | UI state and refresh logic |
| `src/flatlas_translator/ui_editor.py` | Editor and terminology interactions |
| `src/flatlas_translator/ui_workflows.py` | Import/export, project, help, and update workflows |
| `src/flatlas_translator/ui_session.py` | Session, catalog, and apply controller |
| `src/flatlas_translator/ui_chrome.py` | Window title, retranslate, status, footer |
| `src/flatlas_translator/ui_strings.py` | Built-in UI texts and URLs |
| `src/flatlas_translator/catalog.py` | Catalog building and pairing |
| `src/flatlas_translator/dll_resources.py` | Resource extraction from DLLs |
| `src/flatlas_translator/resource_writer.py` | Write/apply logic |
| `src/flatlas_translator/terminology.py` | Terminology and suggestions |
| `src/flatlas_translator/project_io.py` | `.FLLingo` project format |
| `Languages/` | UI translation files (partial overrides) |
| `data/help/` | HTML help files |
| `data/` | Terminology and app data |
| `tests/` | Automated tests |
| `fllingo_updater.py` | Standalone updater script (→ `FLLingoUpdater.exe`) |

### Dependencies

| Package | Purpose |
|---------|---------|
| `PySide6 ≥ 6.6` | GUI framework (Qt6) |
| `pefile ≥ 2023.2.7` | Read resource DLLs |
| `deep-translator ≥ 1.11` | External translation API |

### Platform Status

| Platform | Status |
|----------|--------|
| **Windows** | Full: comparison, export/import, DLL patching, audio copy, voice merge |
| **Linux** | Full: same workflow as Windows, including DLL writing |

### Running Tests

```bash
# All tests
python -m pytest

# GUI smoke tests (headless)
QT_QPA_PLATFORM=offscreen python -m pytest tests/test_ui_smoke.py
```

---

*FL Lingo — Developed by Aldenmar Odin — flathack*
