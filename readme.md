# FL Lingo

FL Lingo is a relocalization tool for Freelancer mods.

It is built for the common case where a mod changes a localized Freelancer install back to English. FL Lingo compares a modded game install with a reference install, restores known vanilla text automatically, exports new mod-only text for external translation, imports translated results, and writes localized strings and infocards back into the game.

## What FL Lingo Does

- compares a current game install against a reference install
- detects strings and infocards from Freelancer resource DLLs
- restores known vanilla text automatically where a safe match exists
- exports unknown mod-only entries for external translation
- imports translated exchange files back into the project
- supports manual edits for individual entries
- applies translations back into the game with automatic backups
- analyzes each DLL and chooses the safest write strategy

## Main Use Case

Example:

- current game: Freelancer with an English mod installed
- reference install: clean German Freelancer install

FL Lingo will then:

1. detect texts that can be restored automatically from the German reference
2. identify mod-only entries that have no German equivalent
3. export those entries for external translation
4. import the translated result
5. write the localized result back into the modded game install

## Current Features

- desktop application for Windows
- source and target language selection
- compare current install and reference install
- DLL-level safety analysis
- main workflow for export, import, preview, and apply
- separate editor tab for manual corrections
- progress display for translated and skipped entries
- terminology files per target language
- project save and load via `.FLLingo`
- automatic backup creation before write operations
- backup restore from the app
- update check via GitHub Releases
- UI languages:
  - English
  - German
  - French
  - Spanish
  - Russian
- themes:
  - light
  - dark
  - high contrast

## Supported Data

FL Lingo currently works with the Freelancer resource DLL workflow, including:

- string tables
- infocards / HTML resources
- DLL references from `EXE\freelancer.ini`

Typical relevant files include:

- `InfoCards.dll`
- `MiscText.dll`
- `MiscTextInfo2.dll`
- `NameResources.dll`
- `EquipResources.dll`
- `OfferBribeResources.dll`

## Workflow

### 1. Load the current game

Select the Freelancer install that you actually want to translate.

This is usually:

- your modded game install
- often English because the mod replaced localized text

### 2. Load the reference install

Select a clean install in the language you want to restore.

This is usually:

- a German vanilla Freelancer install

### 3. Compare

FL Lingo pairs entries by DLL and resource ID and classifies them into:

- automatically transferable
- already localized
- manually translated
- mod-only content

### 4. Export mod-only entries

If the mod added new text that does not exist in the reference install, export those entries and translate them externally.

### 5. Import translated entries

Import the translated exchange file back into FL Lingo.

### 6. Apply translations

FL Lingo creates a backup first, then:

- fully replaces safe DLLs
- patches only matching entries where necessary
- keeps unsafe DLLs from being blindly overwritten

## Terminology

FL Lingo supports target-language terminology files.

Current files:

- `data/terminology.de.json`
- `data/terminology.en.json`

The app uses terminology for:

- glossary export
- known term replacement
- mod-only translation suggestions
- consistent faction and role naming

The active terminology file depends on the selected target language.

## Project Files

FL Lingo can save and load full working sessions as:

- `.FLLingo`

A project file stores:

- selected install paths
- selected language pair
- include-infocards option
- paired catalog state
- manual translations
- DLL analysis state

## Safety

FL Lingo modifies Freelancer resource DLLs.

Before applying translations it creates a backup automatically.

You can also restore previous backups from inside the application.

Still recommended:

- test on a copy of the game first
- keep a clean reference install untouched
- verify results on real mods before using it on your main install

## Installation

### Option 1: Run from source

Requirements:

- Python 3.11+
- Windows

Setup:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e .[dev,ui]
```

Run:

```powershell
python launch.py
```

### Option 2: Windows executable

If you use a packaged release, launch the included `FL-Lingo.exe`.

## Development

Project layout:

- `launch.py`: local launcher and central app defaults
- `src/flatlas_translator/ui_app.py`: main desktop UI
- `src/flatlas_translator/catalog.py`: catalog loading and pairing
- `src/flatlas_translator/dll_resources.py`: resource extraction from DLLs
- `src/flatlas_translator/resource_writer.py`: write/apply logic
- `src/flatlas_translator/terminology.py`: terminology and suggestion logic
- `src/flatlas_translator/project_io.py`: `.FLLingo` project format
- `Languages/`: UI translation files
- `data/help/`: HTML help files
- `data/`: terminology and other app data
- `tests/`: automated tests

Run tests:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## Building

Build the Windows executable with:

```powershell
.\scripts\build_windows.ps1
```

## Current Status

FL Lingo is already usable as a desktop tool for:

- comparing installs
- restoring known localized content
- exporting mod-only content
- importing translated content
- editing entries manually
- applying translations back into the game

The main area that still depends heavily on real-world testing is broader validation across different Freelancer mods and resource variations.

## Roadmap

- more real-world testing with large mods
- improve terminology coverage for more languages
- polish UI translations for French, Spanish, and Russian
- expand conflict detection for difficult DLL cases
- improve workflow guidance for first-time users

## Links

- GitHub: https://github.com/flathack/FL-Lingo
- Discord: https://discord.com/invite/RENtMMcc

## Credits

Developed by Aldenmar Odin - flathack.
