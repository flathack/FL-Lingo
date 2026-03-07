# FLAtlas Translator

## Overview
FLAtlas Translator is a translation tool for Microsoft Freelancer (2003). The goal of the project is to read the language resources used by Freelancer, extract translatable content from the referenced `.dll` files, and write translated versions back either into a Freelancer installation or into a mod-compatible output.

Freelancer stores relevant resource `.dll` files in the `EXE` directory. These files are referenced through `Freelancer.ini` via the `resources` entries. Those `.dll` files contain the strings and infocards that need to be translated.

## Project Goal
The tool should make it possible to:

- load an English Freelancer installation as the source
- choose a target language or an existing target-language Freelancer installation as reference
- extract strings and infocards from the relevant resource `.dll` files
- preview and validate the translation result before writing files
- create backups before changing original game files
- save translated output either directly into Freelancer or as a mod/package

## Scope For V1
Version 1 should stay focused on the core workflow:

- source language: English Freelancer installation
- target: one selected target language or one selected target-language installation
- platform focus: Windows first
- input source: `Freelancer.ini` and referenced resource `.dll` files
- output: translated `.dll` files with backup support
- UI: basic desktop interface for selecting source, target, categories, preview, and export

Linux support can be considered later, but it should not be treated as a guaranteed V1 target unless the `.dll` handling workflow is confirmed to work reliably there.

## Planned Features
- Automatic detection of relevant resource `.dll` files from `Freelancer.ini`
- Extraction of translatable strings and infocards
- Category-based navigation for translation content
- Preview of source and target text before export
- Translation statistics and progress display
- Backup of original files before writing changes
- Export directly into a Freelancer installation or as a mod-friendly output
- Validation to reduce broken references or invalid resource writes

## User Workflow
1. The program starts and opens the main interface.
2. The user selects the English Freelancer installation.
3. The user selects a target language or a target-language Freelancer installation.
4. The tool reads `Freelancer.ini` and loads the referenced resource `.dll` files.
5. The user navigates through translation categories such as system objects, equipment, infocards, and HUD or menu texts.
6. The tool shows a preview of the extracted content and translation statistics.
7. The original files are backed up automatically.
8. The translation output is generated.
9. The result is written either into the selected Freelancer installation or exported as a mod/package.
10. A progress bar and status messages show the current operation state.

## Application Layout
- Left side: sidebar with navigation buttons
- Right side: translation workspace with tabs for categories such as system objects, equipment, infocards, and Freelancer HUD or menu texts
- Top: standard menu bar with application actions
- Help menu: Help, Check for Updates, About
- Footer: Developed by Aldenmar Odin - flathack - Version 0.1.0 - Discord link - GitHub link

## Technical Direction
- Language: Python
- Primary platform: Windows
- Source data: Freelancer installation, `Freelancer.ini`, resource `.dll` files
- Core requirement: reliable read and write support for Freelancer resource `.dll` files
- Packaging: `pyproject.toml` with `src` layout
- First executable interface: CLI for validating install detection and DLL extraction
- Planned UI layer: desktop app on top of the tested core modules

## Current Repository Structure
- `pyproject.toml`: project metadata and dependencies
- `src/flatlas_translator/freelancer_ini.py`: Freelancer installation and resource DLL discovery
- `src/flatlas_translator/dll_resources.py`: string table extraction from resource DLLs
- `src/flatlas_translator/models.py`: translation unit data model
- `src/flatlas_translator/catalog.py`: catalog loading and source-target pairing
- `src/flatlas_translator/exporters.py`: export translation datasets as JSON
- `src/flatlas_translator/cli.py`: CLI entry point for early validation
- `src/flatlas_translator/stats.py`: summary metrics for matched and changed entries
- `src/flatlas_translator/ui_app.py`: desktop app for loading, comparing, filtering, and exporting units
- `src/flatlas_translator/gui_main.py`: GUI entry point
- `scripts/build_windows.ps1`: Windows build script for PyInstaller
- `run_translator.bat`: local launcher for the desktop app
- `src/flatlas_translator/ui_app.py`: future UI entry point placeholder
- `tests/`: initial parser tests

## Local Setup
Create a virtual environment and install the project in editable mode:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e .[dev]
```

If UI work starts, install the optional UI dependency set:

```powershell
python -m pip install -e .[dev,ui]
```

For the current test app in this repository, the local `.venv` already needs `PySide6` and `pyinstaller`.

## CLI Prototype
The repository now includes a small validation CLI:

```powershell
flatlas-translator "C:\Path\To\Freelancer" --dump
```

This command currently verifies:

- `freelancer.ini` detection
- parsing of `[Resources]` DLL entries
- resolution of resource DLL file paths
- extraction of string table entries from discovered DLLs
- creation of translation units with stable IDs and DLL metadata
- optional JSON export for later UI or translation workflow usage

Optional flags:

- `--include-infocards`: also reads `RT_HTML` entries used for infocards
- `--compare-dir <path>`: compares discovered DLL entry counts against a second Freelancer installation
- `--paired-only`: when comparing, only prints DLLs with at least one matched target entry
- `--export-json <path>`: exports the loaded catalog or paired compare catalog as JSON
- `--changed-only`: when exporting a paired catalog, only keeps entries whose target text differs from source

## Desktop Test App
The repository now also includes a first desktop test application.

Start it locally:

```powershell
.\run_translator.bat
```

Or directly:

```powershell
.\.venv\Scripts\python.exe -m flatlas_translator.gui_main
```

Current desktop features:

- load a source Freelancer installation
- optionally load a target installation for comparison
- filter by kind, DLL, matched state, changed state, and search text
- inspect source and target text side by side
- export the currently visible dataset as JSON

## Windows Build
Build the Windows test executable with:

```powershell
.\scripts\build_windows.ps1
```

Expected output:

- `dist\FLAtlas-Translator\FLAtlas-Translator.exe`

## Existing Resources
Parts of the required functionality already exist in the FLAtlas 2D/3D Editor project:

- functions for reading `.dll` files
- functions for writing `.dll` files
- existing project knowledge about Freelancer file structure and resource handling

Reference installations currently available:

- German installation: `C:\Users\STAdmin\Downloads\_FL Fresh Install-deutsch`
- English installation: `C:\Users\STAdmin\Downloads\_FL Fresh Install-englisch`

These should be used to validate extraction, comparison, backup, and output workflows early.

## Open Questions
- Which exact `.dll` files are required for a complete translation workflow?
- Are normal strings and infocards stored in the same structure, or do they require separate handling?
- Will V1 support manual translation only, or also import from existing translated installations?
- What should the mod export format look like?
- How should version differences between Freelancer installations be detected and handled?
- What validation is required to prevent broken or incompatible output files?

## Development Priorities
1. Reuse and isolate existing `.dll` read/write logic from FLAtlas.
2. Verify the new CLI against the English and German reference installations.
3. Expand the compare workflow from entry matching to editable translation datasets.
4. Define the internal data model for translation entries.
5. Implement backup, preview, validation, and export workflow.
6. Build the desktop UI around the confirmed core logic.

## Project Status
This project is currently in planning and concept phase. The README defines the intended direction and the first realistic implementation scope for V1.
