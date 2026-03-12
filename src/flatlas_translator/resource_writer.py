"""Write Freelancer resource DLLs for relocalization output."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import filecmp
import os
import shutil
import subprocess
import sys
import time
import json
import hashlib
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .dll_resources import DllHtmlResourceReader, DllStringTableReader
from .dll_plans import DllRelocalizationPlan, DllStrategy
from .models import RelocalizationStatus, ResourceCatalog, ResourceKind


@dataclass(frozen=True, slots=True)
class ApplyReport:
    backup_dir: Path
    written_files: tuple[Path, ...]
    replaced_units: int
    resumed: bool = False


@dataclass(frozen=True, slots=True)
class ApplySessionInfo:
    state_path: Path
    backup_dir: Path
    total_dlls: int
    completed_dlls: tuple[str, ...]
    pending_dlls: tuple[str, ...]
    failed_dll: str | None = None
    last_error: str | None = None


@dataclass(frozen=True, slots=True)
class AudioCopyCandidate:
    relative_path: Path
    source_path: Path
    target_path: Path


@dataclass(frozen=True, slots=True)
class AudioCopyReport:
    backup_dir: Path
    copied_files: tuple[Path, ...]
    created_files: tuple[Path, ...]
    candidates: tuple[AudioCopyCandidate, ...]


@dataclass(frozen=True, slots=True)
class PatchAssemblyReport:
    output_dir: Path
    copied_files: tuple[Path, ...]
    manifest_path: Path


@dataclass(frozen=True, slots=True)
class AudioCopyProgress:
    total_files: int
    matching_files: int
    differing_files: int


class ResourceWriter:
    AUDIO_DIALOGUE_ROOT = Path("DATA") / "AUDIO" / "DIALOGUE"

    def __init__(
        self,
        *,
        string_reader: DllStringTableReader | None = None,
        html_reader: DllHtmlResourceReader | None = None,
    ) -> None:
        self._string_reader = string_reader or DllStringTableReader()
        self._html_reader = html_reader or DllHtmlResourceReader()

    @staticmethod
    def is_windows() -> bool:
        return sys.platform.startswith("win")

    def has_toolchain(self) -> bool:
        return self.is_windows() or (self._resource_toolchain_commands() is not None)

    @staticmethod
    def backup_root(install_dir: Path) -> Path:
        return Path(install_dir) / "FLAtlas-Translator-Backups"

    @staticmethod
    def apply_state_path(install_dir: Path) -> Path:
        return ResourceWriter.backup_root(install_dir) / "apply-session.json"

    @staticmethod
    def list_backups(install_dir: Path) -> list[Path]:
        root = ResourceWriter.backup_root(install_dir)
        if not root.is_dir():
            return []
        return sorted((path for path in root.iterdir() if path.is_dir()), reverse=True)

    @staticmethod
    def restore_backup(install_dir: Path, backup_dir: Path) -> tuple[Path, ...]:
        install_dir = Path(install_dir)
        backup_dir = Path(backup_dir)
        if not install_dir.is_dir():
            raise FileNotFoundError(f"Install dir not found: {install_dir}")
        if not backup_dir.is_dir():
            raise FileNotFoundError(f"Backup dir not found: {backup_dir}")
        written_files: list[Path] = []
        for backup_path in sorted(path for path in backup_dir.rglob("*") if path.is_file()):
            rel_path = backup_path.relative_to(backup_dir)
            if rel_path.parent == Path(".") and backup_path.suffix.lower() == ".dll":
                target_path = install_dir / "EXE" / backup_path.name
            else:
                target_path = install_dir / rel_path
            if not target_path.parent.is_dir():
                target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup_path, target_path)
            written_files.append(target_path)
        if not written_files:
            raise RuntimeError("Backup does not contain any restorable files.")
        return tuple(written_files)

    def list_audio_copy_candidates(
        self,
        install_dir: Path,
        reference_install_dir: Path,
    ) -> tuple[AudioCopyCandidate, ...]:
        install_dir = Path(install_dir)
        reference_install_dir = Path(reference_install_dir)
        candidates: list[AudioCopyCandidate] = []
        for source_path in self._reference_audio_files(reference_install_dir):
            relative_path = source_path.relative_to(reference_install_dir)
            target_path = install_dir / relative_path
            if target_path.is_file() and filecmp.cmp(str(source_path), str(target_path), shallow=False):
                continue
            candidates.append(
                AudioCopyCandidate(
                    relative_path=relative_path,
                    source_path=source_path,
                    target_path=target_path,
                )
            )
        return tuple(candidates)

    def audio_copy_progress(self, install_dir: Path, reference_install_dir: Path) -> AudioCopyProgress:
        install_dir = Path(install_dir)
        reference_install_dir = Path(reference_install_dir)
        reference_files = self._reference_audio_files(reference_install_dir)
        if not reference_files:
            return AudioCopyProgress(total_files=0, matching_files=0, differing_files=0)
        differing_files = 0
        for source_path in reference_files:
            relative_path = source_path.relative_to(reference_install_dir)
            target_path = install_dir / relative_path
            if target_path.is_file() and filecmp.cmp(str(source_path), str(target_path), shallow=False):
                continue
            differing_files += 1
        total_files = len(reference_files)
        return AudioCopyProgress(
            total_files=total_files,
            matching_files=max(0, total_files - differing_files),
            differing_files=differing_files,
        )

    def copy_reference_audio(
        self,
        install_dir: Path,
        reference_install_dir: Path,
        *,
        candidates: tuple[AudioCopyCandidate, ...] | None = None,
        backup_dir: Path | None = None,
    ) -> AudioCopyReport:
        install_dir = Path(install_dir)
        chosen = tuple(candidates or self.list_audio_copy_candidates(install_dir, reference_install_dir))
        if not chosen:
            raise RuntimeError("No differing reference voice files found.")
        resolved_backup_dir = Path(backup_dir) if backup_dir is not None else self._make_backup_dir(install_dir, None)
        copied_files: list[Path] = []
        created_files: list[Path] = []
        for candidate in chosen:
            target_path = install_dir / candidate.relative_path
            if target_path.exists():
                backup_path = resolved_backup_dir / candidate.relative_path
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                if not backup_path.exists():
                    shutil.copy2(target_path, backup_path)
            else:
                created_files.append(target_path)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(candidate.source_path, target_path)
            copied_files.append(target_path)
        return AudioCopyReport(
            backup_dir=resolved_backup_dir,
            copied_files=tuple(copied_files),
            created_files=tuple(created_files),
            candidates=chosen,
        )

    def assemble_install_patch(
        self,
        install_dir: Path,
        output_dir: Path,
        *,
        dll_paths: tuple[Path, ...] | None = None,
        audio_candidates: tuple[AudioCopyCandidate, ...] | None = None,
    ) -> PatchAssemblyReport:
        install_dir = Path(install_dir)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        planned_files: dict[str, tuple[Path, Path]] = {}
        for dll_path in tuple(dll_paths or ()):
            resolved_dll = Path(dll_path)
            rel_path = self._relative_install_path(install_dir, resolved_dll)
            if not resolved_dll.is_file():
                continue
            planned_files[rel_path.as_posix().lower()] = (resolved_dll, rel_path)

        for candidate in tuple(audio_candidates or ()):
            current_path = install_dir / candidate.relative_path
            if not current_path.is_file():
                continue
            planned_files[candidate.relative_path.as_posix().lower()] = (current_path, candidate.relative_path)

        if not planned_files:
            raise RuntimeError("No files available for patch assembly.")

        copied_files: list[Path] = []
        for _key, (source_path, rel_path) in sorted(planned_files.items(), key=lambda item: item[1][1].as_posix().lower()):
            destination_path = output_dir / rel_path
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, destination_path)
            copied_files.append(destination_path)

        manifest_path = output_dir / "FLAtlas-Translator-Patch.json"
        manifest = {
            "format": "flatlas-translator-patch",
            "version": 1,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "install_dir": str(install_dir),
            "files": [path.relative_to(output_dir).as_posix() for path in copied_files],
        }
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        return PatchAssemblyReport(
            output_dir=output_dir,
            copied_files=tuple(copied_files),
            manifest_path=manifest_path,
        )

    def load_apply_session(self, catalog: ResourceCatalog, *, units=None) -> ApplySessionInfo | None:
        selected_units = list(units if units is not None else catalog.units)
        apply_units = [
            unit
            for unit in selected_units
            if unit.status in (RelocalizationStatus.AUTO_RELOCALIZE, RelocalizationStatus.MANUAL_TRANSLATION)
        ]
        if not apply_units:
            return None
        batches = self._build_dll_batches(apply_units)
        if not batches:
            return None
        signature = self._apply_signature(apply_units)
        state_path = self.apply_state_path(catalog.install_dir)
        payload = self._load_apply_state_payload(state_path)
        if payload is None:
            return None
        if str(payload.get("signature", "") or "") != signature:
            return None
        backup_dir = Path(str(payload.get("backup_dir", "") or ""))
        if not backup_dir.is_dir():
            return None
        completed = tuple(str(item).lower() for item in list(payload.get("completed_dlls", [])))
        completed_set = set(completed)
        ordered_names = tuple(dll_path.name.lower() for dll_path, _bucket in batches)
        pending = tuple(name for name in ordered_names if name not in completed_set)
        return ApplySessionInfo(
            state_path=state_path,
            backup_dir=backup_dir,
            total_dlls=len(ordered_names),
            completed_dlls=completed,
            pending_dlls=pending,
            failed_dll=str(payload.get("failed_dll", "") or "") or None,
            last_error=str(payload.get("last_error", "") or "") or None,
        )

    def apply_german_relocalization(
        self,
        catalog: ResourceCatalog,
        *,
        units=None,
        dll_plans: list[DllRelocalizationPlan] | None = None,
        backup_root: Path | None = None,
        progress_callback=None,
    ) -> ApplyReport:
        selected_units = list(units if units is not None else catalog.units)
        apply_units = [
            unit
            for unit in selected_units
            if unit.status in (RelocalizationStatus.AUTO_RELOCALIZE, RelocalizationStatus.MANUAL_TRANSLATION)
        ]
        if not apply_units:
            raise RuntimeError("No auto_relocalize entries available to write.")
        if not self.has_toolchain():
            raise RuntimeError(
                "No supported resource toolchain found. Install LLVM or MSVC resource tools first."
            )

        batches = self._build_dll_batches(apply_units)
        if not batches:
            raise RuntimeError("No DLL batches available to write.")
        signature = self._apply_signature(apply_units)
        session = self.load_apply_session(catalog, units=apply_units)
        resumed = session is not None
        backup_dir = session.backup_dir if session is not None else self._make_backup_dir(catalog.install_dir, backup_root)
        completed_dlls = set(session.completed_dlls if session is not None else ())
        state_path = self.apply_state_path(catalog.install_dir)
        self._save_apply_state_payload(
            state_path,
            {
                "signature": signature,
                "backup_dir": str(backup_dir),
                "completed_dlls": sorted(completed_dlls),
                "failed_dll": None,
                "last_error": None,
            },
        )

        written_files: list[Path] = []
        plan_by_name = {plan.dll_name: plan for plan in list(dll_plans or [])}
        total_dlls = len(batches)
        for index, (dll_path, bucket) in enumerate(batches, start=1):
            dll_name = dll_path.name
            dll_key = dll_name.lower()
            if dll_key in completed_dlls:
                continue
            plan = plan_by_name.get(dll_name)
            current_strings = self._string_reader.read_strings(dll_path)
            current_infos = self._html_reader.read_html_resources(dll_path)
            current_strings.update(bucket["strings"])
            current_infos.update(bucket["infos"])

            backup_path = backup_dir / dll_path.name
            if not backup_path.is_file():
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dll_path, backup_path)

            action = "patch"
            if (
                plan is not None
                and plan.strategy == DllStrategy.FULL_REPLACE_SAFE
                and plan.target_dll_path is not None
                and plan.target_dll_path.is_file()
            ):
                action = "copy"

            if progress_callback is not None:
                progress_callback(
                    {
                        "phase": "start",
                        "current": index,
                        "total": total_dlls,
                        "dll_name": dll_name,
                        "action": action,
                        "preview_lines": self._preview_lines_for_bucket(bucket),
                        "completed": len(completed_dlls),
                        "resumed": resumed,
                    }
                )

            if action == "copy":
                shutil.copy2(plan.target_dll_path, dll_path)
                written_files.append(dll_path)
            else:
                ok, error = self._write_resource_dll_entries(dll_path, current_strings, current_infos)
                if not ok:
                    shutil.copy2(backup_path, dll_path)
                    self._save_apply_state_payload(
                        state_path,
                        {
                            "signature": signature,
                            "backup_dir": str(backup_dir),
                            "completed_dlls": sorted(completed_dlls),
                            "failed_dll": dll_name,
                            "last_error": error,
                        },
                    )
                    raise RuntimeError(f"Failed to write {dll_path.name}: {error}")
                written_files.append(dll_path)

            completed_dlls.add(dll_key)
            self._save_apply_state_payload(
                state_path,
                {
                    "signature": signature,
                    "backup_dir": str(backup_dir),
                    "completed_dlls": sorted(completed_dlls),
                    "failed_dll": None,
                    "last_error": None,
                },
            )
            if progress_callback is not None:
                progress_callback(
                    {
                        "phase": "done",
                        "current": index,
                        "total": total_dlls,
                        "dll_name": dll_name,
                        "action": action,
                        "preview_lines": self._preview_lines_for_bucket(bucket),
                        "completed": len(completed_dlls),
                        "resumed": resumed,
                    }
                )
        self._clear_apply_state(state_path)

        return ApplyReport(
            backup_dir=backup_dir,
            written_files=tuple(written_files),
            replaced_units=len(apply_units),
            resumed=resumed,
        )

    @staticmethod
    def install_script_candidates() -> list[Path]:
        project_root = Path(__file__).resolve().parent.parent.parent
        candidates = [
            project_root / "scripts" / "install_ids_toolchain_windows.cmd",
            project_root / "scripts" / "install_fllingo_file_association.cmd",
        ]
        if getattr(sys, "frozen", False):
            exe_dir = Path(sys.executable).resolve().parent
            candidates.extend(
                [
                    exe_dir / "scripts" / "install_ids_toolchain_windows.cmd",
                    exe_dir / "scripts" / "install_fllingo_file_association.cmd",
                    exe_dir / "_internal" / "scripts" / "install_ids_toolchain_windows.cmd",
                    exe_dir / "_internal" / "scripts" / "install_fllingo_file_association.cmd",
                ]
            )
        return [path for path in candidates if path.exists()]

    @staticmethod
    def launch_toolchain_installer() -> Path:
        if not ResourceWriter.is_windows():
            raise RuntimeError("Toolchain installer is only available on Windows.")
        script_path = next((path for path in ResourceWriter.install_script_candidates() if path.name == "install_ids_toolchain_windows.cmd"), None)
        if script_path is None:
            raise FileNotFoundError("Toolchain installer script not found.")
        subprocess.Popen(["cmd.exe", "/c", str(script_path)], cwd=str(script_path.parent))
        return script_path

    @staticmethod
    def install_file_association() -> Path:
        if not ResourceWriter.is_windows():
            raise RuntimeError("File association setup is only available on Windows.")
        script_path = next((path for path in ResourceWriter.install_script_candidates() if path.name == "install_fllingo_file_association.cmd"), None)
        if script_path is None:
            raise FileNotFoundError("File association installer script not found.")
        subprocess.Popen(["cmd.exe", "/c", str(script_path)], cwd=str(script_path.parent))
        return script_path

    @staticmethod
    def _make_backup_dir(install_dir: Path, backup_root: Path | None) -> Path:
        base = backup_root or ResourceWriter.backup_root(install_dir)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        path = base / stamp
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def _load_apply_state_payload(state_path: Path) -> dict[str, object] | None:
        if not state_path.is_file():
            return None
        try:
            payload = json.loads(state_path.read_text(encoding="utf-8"))
        except Exception:
            return None
        if not isinstance(payload, dict):
            return None
        return payload

    @staticmethod
    def _save_apply_state_payload(state_path: Path, payload: dict[str, object]) -> None:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        envelope = {
            "format": "fl-lingo-apply-session",
            "version": 1,
            **payload,
        }
        state_path.write_text(json.dumps(envelope, indent=2, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def _clear_apply_state(state_path: Path) -> None:
        try:
            state_path.unlink(missing_ok=True)
        except Exception:
            pass

    @staticmethod
    def _apply_signature(units) -> str:
        parts = []
        for unit in sorted(units, key=lambda item: (item.source.dll_name.lower(), int(item.source.local_id), str(item.kind))):
            parts.append(
                "|".join(
                    [
                        unit.source.dll_name.lower(),
                        str(int(unit.source.local_id)),
                        str(unit.kind),
                        unit.replacement_text,
                    ]
                )
            )
        digest = hashlib.sha1("\n".join(parts).encode("utf-8")).hexdigest()
        return digest

    @staticmethod
    def _build_dll_batches(units) -> list[tuple[Path, dict[str, dict[int, str]]]]:
        by_dll: dict[Path, dict[str, dict[int, str]]] = {}
        for unit in units:
            dll_path = unit.source.dll_path
            bucket = by_dll.setdefault(dll_path, {"strings": {}, "infos": {}})
            replacement_text = unit.replacement_text
            if unit.kind == ResourceKind.STRING:
                bucket["strings"][unit.source.local_id] = replacement_text
            else:
                bucket["infos"][unit.source.local_id] = replacement_text
        return sorted(by_dll.items(), key=lambda item: item[0].name.lower())

    @staticmethod
    def _preview_lines_for_bucket(bucket: dict[str, dict[int, str]]) -> list[str]:
        preview: list[str] = []
        for collection_name in ("strings", "infos"):
            for _local_id, text in sorted(bucket.get(collection_name, {}).items()):
                raw = str(text or "").replace("\r\n", "\n")
                for line in raw.split("\n"):
                    clean = " ".join(line.strip().split())
                    if not clean:
                        continue
                    preview.append(clean[:140])
                    if len(preview) >= 12:
                        return preview
        return preview

    def _write_resource_dll_entries(
        self,
        dll_path: Path,
        strings_by_local_id: dict[int, str],
        infos_by_local_id: dict[int, str] | None = None,
    ) -> tuple[bool, str]:
        cleaned = {
            int(key): str(value).strip()
            for key, value in strings_by_local_id.items()
            if int(key) >= 0 and str(value or "").strip()
        }
        info_cleaned = {
            int(key): str(value).strip()
            for key, value in dict(infos_by_local_id or {}).items()
            if int(key) > 0 and str(value or "").strip()
        }
        if not cleaned and not info_cleaned:
            return False, "no strings to write"
        if not self.is_windows():
            return self._write_resource_dll_entries_with_toolchain(dll_path, cleaned, info_cleaned)
        try:
            language_map, default_by_type = self._resource_language_map(dll_path)
            self._patch_existing_resource_dll(dll_path, cleaned, info_cleaned, language_map, default_by_type)
            return True, ""
        except Exception as exc:
            return False, str(exc)

    def _write_resource_dll_entries_with_toolchain(
        self,
        dll_path: Path,
        strings_by_local_id: dict[int, str],
        infos_by_local_id: dict[int, str] | None = None,
    ) -> tuple[bool, str]:
        toolchain = self._resource_toolchain_commands()
        if toolchain is None:
            return (
                False,
                "No supported resource toolchain found "
                "(need llvm-windres+lld-link, llvm-rc+lld-link, or rc.exe+link.exe)",
            )

        with tempfile.TemporaryDirectory(prefix="fllingo_ids_") as temp_dir:
            temp_root = Path(temp_dir)
            rc_path = temp_root / "resource.rc"
            res_path = temp_root / "resource.res"
            tmp_dll = temp_root / "resource.dll"
            rc_lines = ["#pragma code_page(65001)", ""]
            if strings_by_local_id:
                rc_lines.extend(["STRINGTABLE", "BEGIN"])
                for local_id in sorted(strings_by_local_id):
                    rc_lines.append(f"    {local_id} \"{self._rc_escape_toolchain(strings_by_local_id[local_id])}\"")
                rc_lines.extend(["END", ""])
            for local_id in sorted(dict(infos_by_local_id or {})):
                info_file = temp_root / f"ids_info_{local_id}.xml"
                info_file.write_text(str(infos_by_local_id[local_id]), encoding="utf-8")
                rc_lines.append(f'{local_id} 23 "{info_file.as_posix()}"')
            rc_lines.append("")
            rc_path.write_text("\n".join(rc_lines), encoding="utf-8-sig")
            try:
                compile_cmd, link_cmd = toolchain(str(rc_path), str(res_path), str(tmp_dll))
                subprocess.run(
                    compile_cmd,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                subprocess.run(
                    link_cmd,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
            except subprocess.CalledProcessError as exc:
                message = exc.stderr.strip() or exc.stdout.strip() or str(exc)
                return False, message
            try:
                dll_path.parent.mkdir(parents=True, exist_ok=True)
                last_error = None
                for _attempt in range(8):
                    try:
                        shutil.copy2(tmp_dll, dll_path)
                        last_error = None
                        break
                    except PermissionError as exc:
                        last_error = exc
                        time.sleep(0.15)
                    except OSError as exc:
                        last_error = exc
                        if getattr(exc, "winerror", None) in (5, 32, 33, 1224):
                            time.sleep(0.15)
                            continue
                        break
                if last_error is not None:
                    raise last_error
            except Exception as exc:
                return False, str(exc)
        return True, ""

    def _patch_existing_resource_dll(
        self,
        dll_path: Path,
        strings_by_local_id: dict[int, str],
        infos_by_local_id: dict[int, str],
        language_map: dict[tuple[int, int], int],
        default_by_type: dict[int, int],
    ) -> None:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        begin_update = kernel32.BeginUpdateResourceW
        begin_update.argtypes = [wintypes.LPCWSTR, wintypes.BOOL]
        begin_update.restype = wintypes.HANDLE
        end_update = kernel32.EndUpdateResourceW
        end_update.argtypes = [wintypes.HANDLE, wintypes.BOOL]
        end_update.restype = wintypes.BOOL
        update_resource = kernel32.UpdateResourceW
        update_resource.argtypes = [
            wintypes.HANDLE,
            ctypes.c_void_p,
            ctypes.c_void_p,
            wintypes.WORD,
            ctypes.c_void_p,
            wintypes.DWORD,
        ]
        update_resource.restype = wintypes.BOOL

        handle = begin_update(str(dll_path), False)
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())

        try:
            string_blocks = self._build_string_blocks(strings_by_local_id)
            for block_id, block_blob in sorted(string_blocks.items()):
                lang = int(language_map.get((6, block_id), default_by_type.get(6, 1033)))
                data_buffer = ctypes.create_string_buffer(block_blob)
                if not update_resource(
                    handle,
                    self._resource_id(6),
                    self._resource_id(block_id),
                    lang,
                    data_buffer,
                    len(block_blob),
                ):
                    raise ctypes.WinError(ctypes.get_last_error())

            for local_id, text in sorted(infos_by_local_id.items()):
                lang = int(language_map.get((23, int(local_id)), default_by_type.get(23, 1033)))
                blob = self._encode_html_resource(str(text))
                data_buffer = ctypes.create_string_buffer(blob)
                if not update_resource(
                    handle,
                    self._resource_id(23),
                    self._resource_id(int(local_id)),
                    lang,
                    data_buffer,
                    len(blob),
                ):
                    raise ctypes.WinError(ctypes.get_last_error())
        except Exception:
            end_update(handle, True)
            raise

        if not end_update(handle, False):
            raise ctypes.WinError(ctypes.get_last_error())

    @staticmethod
    def _build_string_blocks(strings_by_local_id: dict[int, str]) -> dict[int, bytes]:
        by_block: dict[int, dict[int, str]] = {}
        for local_id, text in strings_by_local_id.items():
            block_id = (int(local_id) // 16) + 1
            block_values = by_block.setdefault(block_id, {})
            block_values[int(local_id) % 16] = str(text or "")

        blocks: dict[int, bytes] = {}
        for block_id, values in by_block.items():
            parts = bytearray()
            for index in range(16):
                text = values.get(index, "")
                encoded = str(text).encode("utf-16le")
                char_count = len(encoded) // 2
                parts.extend(int(char_count).to_bytes(2, "little"))
                parts.extend(encoded)
            blocks[block_id] = bytes(parts)
        return blocks

    @staticmethod
    def _encode_html_resource(text: str) -> bytes:
        normalized = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
        return b"\xff\xfe" + normalized.encode("utf-16le")

    @staticmethod
    def _resource_language_map(dll_path: Path) -> tuple[dict[tuple[int, int], int], dict[int, int]]:
        try:
            import pefile  # type: ignore
        except Exception as exc:
            raise RuntimeError("pefile is required for resource patching.") from exc

        pe = pefile.PE(str(dll_path), fast_load=True)
        pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_RESOURCE"]])
        mapping: dict[tuple[int, int], int] = {}
        defaults: dict[int, int] = {}
        try:
            root = getattr(pe, "DIRECTORY_ENTRY_RESOURCE", None)
            if root is None:
                return mapping, defaults
            for type_entry in getattr(root, "entries", []):
                type_id = getattr(type_entry, "id", None)
                if not isinstance(type_id, int):
                    continue
                for name_entry in getattr(type_entry.directory, "entries", []):
                    name_id = getattr(name_entry, "id", None)
                    if not isinstance(name_id, int):
                        continue
                    lang_entries = list(getattr(name_entry.directory, "entries", []))
                    if not lang_entries:
                        continue
                    lang_id = int(getattr(lang_entries[0], "id", 0) or 0)
                    mapping[(type_id, name_id)] = lang_id
                    defaults.setdefault(type_id, lang_id)
        finally:
            pe.close()
        return mapping, defaults

    @staticmethod
    def _resource_id(value: int) -> ctypes.c_void_p:
        return ctypes.c_void_p(int(value))

    @staticmethod
    def _relative_install_path(install_dir: Path, file_path: Path) -> Path:
        install_dir = Path(install_dir)
        file_path = Path(file_path)
        try:
            return file_path.relative_to(install_dir)
        except ValueError:
            if file_path.suffix.lower() == ".dll":
                return Path("EXE") / file_path.name
            return Path(file_path.name)

    def _reference_audio_files(self, reference_install_dir: Path) -> list[Path]:
        reference_audio_root = Path(reference_install_dir) / self.AUDIO_DIALOGUE_ROOT
        if not reference_audio_root.is_dir():
            return []
        return sorted(path for path in reference_audio_root.rglob("*") if path.is_file())

    @staticmethod
    def _rc_escape(text: str) -> str:
        value = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
        pieces: list[str] = []
        for char in value:
            codepoint = ord(char)
            if char == "\"":
                pieces.append("\"\"")
            elif char == "\\":
                pieces.append("\\\\")
            elif char == "\n":
                pieces.append("\\n")
            elif char == "\t":
                pieces.append("\\t")
            elif codepoint < 32:
                pieces.append(f"\\x{codepoint:02X}")
            elif codepoint > 127:
                if codepoint <= 0xFFFF:
                    pieces.append(f"\\u{codepoint:04X}")
                else:
                    pieces.append(f"\\U{codepoint:08X}")
            else:
                pieces.append(char)
        return "".join(pieces)

    @staticmethod
    def _rc_escape_toolchain(text: str) -> str:
        value = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
        pieces: list[str] = []
        for char in value:
            codepoint = ord(char)
            if char == "\"":
                pieces.append("\"\"")
            elif char == "\\":
                pieces.append("\\\\")
            elif char == "\n":
                pieces.append("\\n")
            elif char == "\t":
                pieces.append("\\t")
            elif codepoint < 32:
                pieces.append(f"\\x{codepoint:02X}")
            elif codepoint > 127:
                try:
                    encoded = char.encode("cp1252")
                except UnicodeEncodeError:
                    pieces.append(char)
                else:
                    pieces.extend(f"\\x{byte:02X}" for byte in encoded)
            else:
                pieces.append(char)
        return "".join(pieces)

    @staticmethod
    def _resource_toolchain_commands():
        windres = ResourceWriter._resolve_tool_exe("llvm-windres")
        lld_link = ResourceWriter._resolve_tool_exe("lld-link")
        llvm_rc = ResourceWriter._resolve_tool_exe("llvm-rc")
        rc_exe = ResourceWriter._resolve_tool_exe("rc.exe") or ResourceWriter._resolve_tool_exe("rc")
        link_exe = ResourceWriter._resolve_tool_exe("link.exe") or ResourceWriter._resolve_tool_exe("link")

        if windres and lld_link:
            def _llvm_windres(rc_path: str, res_path: str, tmp_dll: str):
                return (
                    [windres, "--target=pe-i386", rc_path, res_path],
                    [lld_link, "/NOENTRY", "/DLL", "/MACHINE:X86", f"/OUT:{tmp_dll}", res_path],
                )
            return _llvm_windres

        if llvm_rc and lld_link:
            def _llvm_rc(rc_path: str, res_path: str, tmp_dll: str):
                return (
                    [llvm_rc, f"/fo{res_path}", rc_path],
                    [lld_link, "/NOENTRY", "/DLL", "/MACHINE:X86", f"/OUT:{tmp_dll}", res_path],
                )
            return _llvm_rc

        if rc_exe and link_exe:
            def _msvc(rc_path: str, res_path: str, tmp_dll: str):
                return (
                    [rc_exe, "/nologo", f"/fo{res_path}", rc_path],
                    [link_exe, "/NOLOGO", "/NOENTRY", "/DLL", "/MACHINE:X86", f"/OUT:{tmp_dll}", res_path],
                )
            return _msvc

        return None

    @staticmethod
    def _resolve_tool_exe(exe_name: str) -> str | None:
        hit = shutil.which(exe_name)
        if hit:
            return hit
        for directory in ResourceWriter._candidate_tool_dirs():
            candidates = [exe_name]
            if not exe_name.lower().endswith(".exe"):
                candidates.append(f"{exe_name}.exe")
            for name in candidates:
                path = directory / name
                if path.is_file():
                    return str(path)
        return None

    @staticmethod
    def _candidate_tool_dirs() -> list[Path]:
        directories: list[Path] = []
        env_dir = str(os.environ.get("FLATLAS_TOOLCHAIN_DIR", "") or "").strip()
        if env_dir:
            directories.append(Path(env_dir))

        project_root = Path(__file__).resolve().parent.parent.parent
        directories.extend(
            [
                project_root / "tools",
                project_root / "tools" / "bin",
                project_root / "tools" / "llvm" / "bin",
            ]
        )
        if sys.platform.startswith("win"):
            for env_name in ("ProgramFiles", "ProgramFiles(x86)"):
                raw = str(os.environ.get(env_name, "") or "").strip()
                if raw:
                    directories.append(Path(raw) / "LLVM" / "bin")

        if getattr(sys, "frozen", False):
            exe_dir = Path(sys.executable).resolve().parent
            directories.extend(
                [
                    exe_dir / "tools",
                    exe_dir / "tools" / "bin",
                    exe_dir / "tools" / "llvm" / "bin",
                    exe_dir / "_internal" / "tools",
                    exe_dir / "_internal" / "tools" / "bin",
                    exe_dir / "_internal" / "tools" / "llvm" / "bin",
                ]
            )

        result: list[Path] = []
        seen: set[str] = set()
        for directory in directories:
            key = str(directory.resolve()) if directory.exists() else str(directory)
            if key in seen:
                continue
            seen.add(key)
            result.append(directory)
        return result
