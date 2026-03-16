"""Read Freelancer string-table and infocard resources from DLL files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

try:
    import pefile  # type: ignore
except Exception:  # pragma: no cover
    pefile = None


@dataclass(frozen=True, slots=True)
class StringTableEntry:
    resource_id: int
    text: str


@dataclass(frozen=True, slots=True)
class HtmlResourceEntry:
    resource_id: int
    text: str


class DllStringTableReader:
    """Load RT_STRING entries from a Windows resource DLL."""

    @property
    def available(self) -> bool:
        return pefile is not None

    def read_strings(self, dll_path: Path) -> dict[int, str]:
        if pefile is None:
            raise RuntimeError("pefile is not installed")

        pe = None
        try:
            pe = pefile.PE(str(dll_path), fast_load=True)
            pe.parse_data_directories(
                directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_RESOURCE"]]
            )
        except Exception as exc:
            raise RuntimeError(f"Failed to load DLL resources: {dll_path}") from exc

        strings: dict[int, str] = {}
        try:
            root = getattr(pe, "DIRECTORY_ENTRY_RESOURCE", None)
            if root is None:
                return strings

            for type_entry in getattr(root, "entries", []):
                if getattr(type_entry, "id", None) != 6:
                    continue
                for name_entry in getattr(type_entry.directory, "entries", []):
                    block_id = getattr(name_entry, "id", None)
                    if not isinstance(block_id, int):
                        continue
                    for lang_entry in getattr(name_entry.directory, "entries", []):
                        data_entry = getattr(lang_entry, "data", None)
                        if data_entry is None:
                            continue
                        rva = int(data_entry.struct.OffsetToData)
                        size = int(data_entry.struct.Size)
                        blob = pe.get_data(rva, size)
                        _decode_string_block(blob, block_id, strings)
        finally:
            if pe is not None:
                pe.close()

        return strings


class DllHtmlResourceReader:
    """Load RT_HTML entries from a Windows resource DLL."""

    @property
    def available(self) -> bool:
        return pefile is not None

    def read_html_resources(self, dll_path: Path) -> dict[int, str]:
        if pefile is None:
            raise RuntimeError("pefile is not installed")

        pe = None
        try:
            pe = pefile.PE(str(dll_path), fast_load=True)
            pe.parse_data_directories(
                directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_RESOURCE"]]
            )
        except Exception as exc:
            raise RuntimeError(f"Failed to load DLL resources: {dll_path}") from exc

        resources: dict[int, str] = {}
        try:
            root = getattr(pe, "DIRECTORY_ENTRY_RESOURCE", None)
            if root is None:
                return resources

            for type_entry in getattr(root, "entries", []):
                if getattr(type_entry, "id", None) != 23:
                    continue
                for name_entry in getattr(type_entry.directory, "entries", []):
                    local_id = getattr(name_entry, "id", None)
                    if not isinstance(local_id, int) or local_id <= 0:
                        continue
                    for lang_entry in getattr(name_entry.directory, "entries", []):
                        data_entry = getattr(lang_entry, "data", None)
                        if data_entry is None:
                            continue
                        rva = int(data_entry.struct.OffsetToData)
                        size = int(data_entry.struct.Size)
                        blob = pe.get_data(rva, size)
                        text = decode_resource_text_blob(blob)
                        if text:
                            resources[int(local_id)] = text
                        break
        finally:
            if pe is not None:
                pe.close()

        return resources


def _decode_string_block(blob: bytes, block_id: int, out: dict[int, str]) -> None:
    offset = 0
    base_id = (int(block_id) - 1) * 16
    for index in range(16):
        if offset + 2 > len(blob):
            break
        string_len = int.from_bytes(blob[offset:offset + 2], "little")
        offset += 2
        byte_len = string_len * 2
        if offset + byte_len > len(blob):
            break
        raw = blob[offset:offset + byte_len]
        offset += byte_len
        if string_len <= 0:
            continue
        text = raw.decode("utf-16le", errors="ignore").strip()
        if text:
            out[base_id + index] = text


def decode_resource_text_blob(blob: bytes) -> str:
    if not blob:
        return ""
    if blob.startswith(b"\xff\xfe") or blob.startswith(b"\xfe\xff"):
        try:
            return blob.decode("utf-16", errors="ignore").strip("\x00")
        except Exception:
            pass
    if b"\x00" in blob:
        try:
            return blob.decode("utf-16le", errors="ignore").replace("\x00", "").strip("\x00")
        except Exception:
            pass
    for encoding in ("utf-8", "cp1252", "latin-1"):
        try:
            return blob.decode(encoding, errors="ignore").strip("\x00")
        except Exception:
            continue
    return ""
