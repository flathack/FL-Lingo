from __future__ import annotations

import os
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path

os.environ.setdefault("QT_LOGGING_RULES", "qt.text.font.db=false;qt.qpa.fonts=false")


APP_VERSION = "0.2.2"
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


def _run_gui(config: LaunchConfig) -> int:
    from flatlas_translator.gui_main import main as gui_main

    return gui_main(config)


def _format_startup_error(exc: BaseException) -> str:
    detail = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)).strip()
    return (
        "FL Lingo could not start because an unexpected error occurred.\n\n"
        "If this happened during automatic project restore, the last opened .FLLingo project may contain invalid saved state.\n\n"
        f"{detail}"
    )


def _show_startup_error(message: str) -> None:
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox

        app = QApplication.instance()
        owns_app = app is None
        if app is None:
            app = QApplication([])
        box = QMessageBox(QMessageBox.Critical, APP_TITLE, message)
        box.setWindowTitle(APP_TITLE)
        box.setTextInteractionFlags(box.textInteractionFlags())
        box.exec()
        if owns_app:
            app.quit()
        return
    except Exception:
        pass

    if os.name == "nt":
        try:
            import ctypes

            ctypes.windll.user32.MessageBoxW(None, message, APP_TITLE, 0x10)
            return
        except Exception:
            pass

    print(message, file=sys.stderr)


def main() -> int:
    project_root = Path(__file__).resolve().parent
    src_dir = project_root / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    startup_project_path = None
    if len(sys.argv) > 1:
        candidate = Path(sys.argv[1]).expanduser()
        startup_project_path = str(candidate)
    config = LaunchConfig(startup_project_path=startup_project_path)
    try:
        return _run_gui(config)
    except Exception as exc:
        _show_startup_error(_format_startup_error(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
