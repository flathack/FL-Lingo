from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path


APP_VERSION = "0.1.2"
DEVELOPED_BY = "Developed by Aldenmar Odin - flathack"
APP_TITLE = "FL Lingo"
DEFAULT_LANGUAGE = "en"
DEFAULT_THEME = "dark"
DEFAULT_SOURCE_LANGUAGE = "en"
DEFAULT_TARGET_LANGUAGE = "de"


@dataclass(frozen=True, slots=True)
class LaunchConfig:
    app_title: str = APP_TITLE
    app_version: str = APP_VERSION
    developed_by: str = DEVELOPED_BY
    default_language: str = DEFAULT_LANGUAGE
    default_theme: str = DEFAULT_THEME
    # default_source_language: str = DEFAULT_SOURCE_LANGUAGE
    default_target_language: str = DEFAULT_TARGET_LANGUAGE
    startup_project_path: str | None = None


def main() -> int:
    project_root = Path(__file__).resolve().parent
    src_dir = project_root / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    from flatlas_translator.gui_main import main as gui_main

    startup_project_path = None
    if len(sys.argv) > 1:
        candidate = Path(sys.argv[1]).expanduser()
        startup_project_path = str(candidate)

    return gui_main(LaunchConfig(startup_project_path=startup_project_path))


if __name__ == "__main__":
    raise SystemExit(main())
