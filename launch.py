from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path


APP_VERSION = "0.1.0"
DEVELOPED_BY = "Developed by Aldenmar Odin - flathack"
APP_TITLE = "FLAtlas Translator"
DEFAULT_LANGUAGE = "de"
DEFAULT_THEME = "light"
DEFAULT_SOURCE_LANGUAGE = "en"
DEFAULT_TARGET_LANGUAGE = "de"


@dataclass(frozen=True, slots=True)
class LaunchConfig:
    app_title: str = APP_TITLE
    app_version: str = APP_VERSION
    developed_by: str = DEVELOPED_BY
    default_language: str = DEFAULT_LANGUAGE
    default_theme: str = DEFAULT_THEME
    default_source_language: str = DEFAULT_SOURCE_LANGUAGE
    default_target_language: str = DEFAULT_TARGET_LANGUAGE


def main() -> int:
    project_root = Path(__file__).resolve().parent
    src_dir = project_root / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    from flatlas_translator.gui_main import main as gui_main

    return gui_main(LaunchConfig())


if __name__ == "__main__":
    raise SystemExit(main())
