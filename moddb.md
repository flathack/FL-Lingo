# FL Lingo — Relocalization Tool for Freelancer Mods

Many Freelancer mods ship with English-only texts. FL Lingo helps mod authors and players translate mod-specific content into other languages — quickly, safely, and without manual DLL editing.

## How it works

FL Lingo compares a modded Freelancer installation against a clean reference install in the target language. Texts that exist in both are automatically matched and reused. New texts added by the mod are flagged for translation — either manually, via JSON import, or through the built-in auto-translator (Google Translate).

All translations are written back into the mod's resource DLLs with automatic backup. Nothing is changed until you say so.

## Features

- **Automatic matching** — Identifies mod texts that already have known translations and reuses them instantly.
- **Mod-only detection** — Highlights new texts added by the mod that need translation.
- **Built-in auto-translate** — Translate open entries via Google Translate in batches, with pause/resume support.
- **Terminology system** — Define term mappings (e.g. "Battleship" → "Schlachtschiff") for consistent translations across the mod.
- **JSON import/export** — Export open entries for external translation tools or translators, then import the results.
- **Safe DLL writing** — Patches resource DLLs using LLVM tools with automatic backup before every write.
- **Audio & voice support** — Copy localized voice files and merge translated voice lines into UTF files.
- **Project files** — Save your entire work session as a `.FLLingo` project and resume later.
- **Two modes** — Simple Mode for a quick three-step workflow, Expert Mode for full control over filters, DLL analysis, and terminology.

## Supported content

- String tables (`RT_STRING`) and infocards (`RT_HTML`) from all resource DLLs referenced by `freelancer.ini`
- Commonly affected: `InfoCards.dll`, `MiscText.dll`, `NameResources.dll`, `EquipResources.dll`, and others

## Compatibility

Works with any Freelancer mod that uses standard resource DLLs — tested with Crossfire, Discovery, FreelancerHD+, and others.

## Download

Grab the latest `FL-Lingo.exe` from [GitHub Releases](https://github.com/flathack/FL-Lingo/releases/latest) — no installation required.

## Links

- [GitHub](https://github.com/flathack/FL-Lingo)
- [Documentation (EN)](https://github.com/flathack/FL-Lingo/wiki/Help-%E2%80%90-EN)
- [Dokumentation (DE)](https://github.com/flathack/FL-Lingo/wiki/Hilfe-%E2%80%90-DE)
- [Discord](https://discord.com/invite/RENtMMcc)

*Developed by Aldenmar Odin — flathack*
