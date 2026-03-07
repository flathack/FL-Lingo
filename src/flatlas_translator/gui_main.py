"""GUI entry point."""

from __future__ import annotations

try:
    from .ui_app import run
except ImportError:
    from flatlas_translator.ui_app import run


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
