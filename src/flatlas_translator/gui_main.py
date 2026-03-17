"""GUI entry point."""

from __future__ import annotations

from dataclasses import dataclass

try:
    from .ui_app import run
except ImportError:
    from flatlas_translator.ui_app import run


@dataclass(frozen=True, slots=True)
class AppConfig:
    app_title: str = "FL Lingo"
    app_version: str = "0.1.3"
    developed_by: str = "Developed by Aldenmar Odin - flathack"
    default_language: str = "en"
    default_theme: str = "dark"
    default_source_language: str = "en"
    default_target_language: str = "de"
    startup_project_path: str | None = None


def main(config: AppConfig | None = None) -> int:
    return run(config or AppConfig())


if __name__ == "__main__":
    raise SystemExit(main())
