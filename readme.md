# Welcome to the FL Lingo Wiki

**FL Lingo** is a relocalization tool for Freelancer mods. Many Freelancer mods ship with English-only texts — FL Lingo helps translate the mod-specific content into other languages by comparing a modded installation against a clean reference install and writing the results safely back into the mod's resource DLLs.

---

## Help / Documentation

| Language | Link |
|----------|------|
| **English** | [Help — EN](https://github.com/flathack/FL-Lingo/wiki/Help-%E2%80%90-EN) |
| **Deutsch** | [Hilfe — DE](https://github.com/flathack/FL-Lingo/wiki/Hilfe-%E2%80%90-DE) |

---

## Quick Links

- [Latest Release](https://github.com/flathack/FL-Lingo/releases/latest) — Download the Windows executable or source package
- [Issues](https://github.com/flathack/FL-Lingo/issues) — Report bugs or request features
- [Discord](https://discord.com/invite/RENtMMcc) — Community support and discussion

---

## What FL Lingo Does

1. **Scans** a modded Freelancer installation and a clean reference install side by side.
2. **Matches** mod-specific resource entries automatically — texts that exist in both installations are identified and reused.
3. **Highlights** mod-only entries (new texts added by the mod) that need manual or external translation.
4. **Writes** the finished translations back into the mod's resource DLLs with automatic backup.

Supports `RT_STRING` (string tables) and `RT_HTML` (infocards) across all resource DLLs referenced by `freelancer.ini`.

---

## Getting Started

### Windows Executable

Download `FL-Lingo.exe` from the [latest release](https://github.com/flathack/FL-Lingo/releases/latest) and run it — no installation required.

### From Source

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows
# source .venv/bin/activate    # Linux/macOS
python -m pip install -e .[all]
python launch.py
```

**Requirements:** Python 3.11+, PySide6 ≥ 6.6

---

## Two Modes

| Mode | Best for |
|------|----------|
| **Simple Mode** | Quick three-step workflow: pick folders → scan → translate. |
| **Expert Mode** | Full editor with filters, DLL analysis, terminology, bulk translation, import/export, and project management. |

For a complete walkthrough of every feature, see the [English Help](https://github.com/flathack/FL-Lingo/wiki/Help-%E2%80%90-EN) or the [German Help (Hilfe)](https://github.com/flathack/FL-Lingo/wiki/Hilfe-%E2%80%90-DE).

---

*FL Lingo — Developed by Aldenmar Odin — flathack*
