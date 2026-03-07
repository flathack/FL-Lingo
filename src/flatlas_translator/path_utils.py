"""Case-insensitive path helpers for Freelancer installs on Windows."""

from __future__ import annotations

from pathlib import Path


def ci_find(base: Path, name: str) -> Path | None:
    if not base.exists() or not base.is_dir():
        return None
    target = str(name).strip().lower()
    for child in base.iterdir():
        if child.name.lower() == target:
            return child
    return None


def ci_resolve(base: Path, rel_path: str) -> Path | None:
    current = Path(base)
    for part in str(rel_path or "").replace("\\", "/").split("/"):
        segment = part.strip()
        if not segment or segment == ".":
            continue
        if segment == "..":
            parent = current.parent
            if parent == current:
                return None
            current = parent
            continue
        current = ci_find(current, segment) or Path()
        if not current:
            return None
    return current if current.exists() else None

