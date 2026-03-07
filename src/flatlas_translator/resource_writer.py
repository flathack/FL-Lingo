"""Write Freelancer resource DLLs for relocalization output."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
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


class ResourceWriter:
    def __init__(
        self,
        *,
        string_reader: DllStringTableReader | None = None,
        html_reader: DllHtmlResourceReader | None = None,
    ) -> None:
        self._string_reader = string_reader or DllStringTableReader()
        self._html_reader = html_reader or DllHtmlResourceReader()

    def has_toolchain(self) -> bool:
        return self._resource_toolchain_commands() is not None

    @staticmethod
    def backup_root(install_dir: Path) -> Path:
        return Path(install_dir) / "FLAtlas-Translator-Backups"

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
        for dll_path in backup_dir.glob("*.dll"):
            target_path = install_dir / "EXE" / dll_path.name
            if not target_path.parent.is_dir():
                target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dll_path, target_path)
            written_files.append(target_path)
        if not written_files:
            raise RuntimeError("Backup does not contain any DLL files.")
        return tuple(written_files)

    def apply_german_relocalization(
        self,
        catalog: ResourceCatalog,
        *,
        units=None,
        dll_plans: list[DllRelocalizationPlan] | None = None,
        backup_root: Path | None = None,
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

        backup_dir = self._make_backup_dir(catalog.install_dir, backup_root)
        by_dll: dict[Path, dict[str, dict[int, str]]] = {}
        for unit in apply_units:
            dll_path = unit.source.dll_path
            bucket = by_dll.setdefault(dll_path, {"strings": {}, "infos": {}})
            replacement_text = unit.replacement_text
            if unit.kind == ResourceKind.STRING:
                bucket["strings"][unit.source.local_id] = replacement_text
            else:
                bucket["infos"][unit.source.local_id] = replacement_text

        written_files: list[Path] = []
        plan_by_name = {plan.dll_name: plan for plan in list(dll_plans or [])}
        for dll_path, bucket in by_dll.items():
            dll_name = dll_path.name
            plan = plan_by_name.get(dll_name)
            current_strings = self._string_reader.read_strings(dll_path)
            current_infos = self._html_reader.read_html_resources(dll_path)
            current_strings.update(bucket["strings"])
            current_infos.update(bucket["infos"])

            backup_path = backup_dir / dll_path.name
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dll_path, backup_path)

            if (
                plan is not None
                and plan.strategy == DllStrategy.FULL_REPLACE_SAFE
                and plan.target_dll_path is not None
                and plan.target_dll_path.is_file()
            ):
                shutil.copy2(plan.target_dll_path, dll_path)
                written_files.append(dll_path)
                continue

            ok, error = self._write_resource_dll_entries(dll_path, current_strings, current_infos)
            if not ok:
                shutil.copy2(backup_path, dll_path)
                raise RuntimeError(f"Failed to write {dll_path.name}: {error}")
            written_files.append(dll_path)

        return ApplyReport(
            backup_dir=backup_dir,
            written_files=tuple(written_files),
            replaced_units=len(apply_units),
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
        script_path = next((path for path in ResourceWriter.install_script_candidates() if path.name == "install_ids_toolchain_windows.cmd"), None)
        if script_path is None:
            raise FileNotFoundError("Toolchain installer script not found.")
        subprocess.Popen(["cmd.exe", "/c", str(script_path)], cwd=str(script_path.parent))
        return script_path

    @staticmethod
    def install_file_association() -> Path:
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

    def _write_resource_dll_entries(
        self,
        dll_path: Path,
        strings_by_local_id: dict[int, str],
        infos_by_local_id: dict[int, str] | None = None,
    ) -> tuple[bool, str]:
        toolchain = self._resource_toolchain_commands()
        if toolchain is None:
            return False, "No supported resource toolchain found."

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

        with tempfile.TemporaryDirectory(prefix="flatlas_translator_") as temp_dir:
            temp_path = Path(temp_dir)
            rc_path = temp_path / "resource.rc"
            res_path = temp_path / "resource.res"
            tmp_dll = temp_path / "resource.dll"

            rc_lines: list[str] = []
            if cleaned:
                rc_lines.extend(["STRINGTABLE", "BEGIN"])
                for local_id in sorted(cleaned):
                    rc_lines.append(f'    {local_id} "{self._rc_escape(cleaned[local_id])}"')
                rc_lines.extend(["END", ""])
            for local_id in sorted(info_cleaned):
                info_file = temp_path / f"ids_info_{local_id}.xml"
                info_file.write_text(info_cleaned[local_id], encoding="utf-8")
                rc_lines.append(f'{local_id} 23 "{info_file.as_posix()}"')
            rc_lines.append("")
            rc_path.write_text("\n".join(rc_lines), encoding="utf-8")

            try:
                compile_cmd, link_cmd = toolchain(str(rc_path), str(res_path), str(tmp_dll))
                subprocess.run(compile_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                subprocess.run(link_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            except subprocess.CalledProcessError as exc:
                return False, exc.stderr.strip() or exc.stdout.strip() or str(exc)

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

    @staticmethod
    def _rc_escape(text: str) -> str:
        return (
            str(text or "")
            .replace("\\", "\\\\")
            .replace("\"", "\\\"")
            .replace("\r\n", "\\n")
            .replace("\n", "\\n")
        )

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
