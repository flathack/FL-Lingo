from __future__ import annotations

from pathlib import Path

import launch


def test_format_startup_error_includes_restore_hint() -> None:
    try:
        raise ValueError("bad saved state")
    except ValueError as exc:
        message = launch._format_startup_error(exc)

    assert "could not start" in message
    assert "automatic project restore" in message
    assert "bad saved state" in message
    assert "ValueError" in message


def test_main_catches_startup_exception(monkeypatch) -> None:
    shown_messages: list[str] = []

    def _raise(config: launch.LaunchConfig) -> int:
        raise RuntimeError(f"broken: {Path(config.startup_project_path or '').name}")

    monkeypatch.setattr(launch, "_run_gui", _raise)
    monkeypatch.setattr(launch, "_show_startup_error", shown_messages.append)
    monkeypatch.setattr(launch.sys, "argv", ["launch.py", "broken.FLLingo"])

    result = launch.main()

    assert result == 1
    assert len(shown_messages) == 1
    assert "broken.FLLingo" in shown_messages[0]
    assert "RuntimeError" in shown_messages[0]