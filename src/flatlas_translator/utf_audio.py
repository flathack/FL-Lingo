"""Parse, write, and merge Freelancer UTF audio containers.

Freelancer stores voice lines in UTF container files under DATA/AUDIO/.
Each container holds audio entries keyed by hash-ID strings (e.g. '0xA2C39B07').
This module enables a 3-way merge: given a modded-EN, vanilla-EN, and vanilla-DE
installation, it replaces unmodified English voice lines with their German
counterparts while preserving any mod-specific audio.
"""

from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

HEADER_SIZE = 56
ENTRY_SIZE = 44
UTF_MAGIC = b"UTF "
UTF_VERSION = 0x0000_0101
DIR_FLAG = 0x10


@dataclass(frozen=True, slots=True)
class UtfEntry:
    """A single node (file leaf) inside a UTF container."""

    name: str
    data: bytes
    flags: int
    timestamps: tuple[int, int, int]


@dataclass(frozen=True, slots=True)
class UtfFile:
    """Parsed content of a UTF audio container."""

    version: int
    filetime: int
    entries: tuple[UtfEntry, ...]


@dataclass(frozen=True, slots=True)
class UtfMergeEntry:
    """Result for a single entry in a 3-way merge."""

    hash_id: str
    action: str  # "replaced" | "kept"
    source: str  # "de" | "mod"


@dataclass(frozen=True, slots=True)
class UtfMergeResult:
    """Report from merging a single UTF file."""

    filename: str
    total_entries: int
    replaced_count: int
    kept_count: int
    only_mod_count: int
    only_de_count: int
    entries: tuple[UtfMergeEntry, ...]


@dataclass(frozen=True, slots=True)
class UtfAudioMergeCandidate:
    """A UTF file that can be merged."""

    relative_path: Path
    mod_path: Path
    ref_en_path: Path
    ref_de_path: Path
    total_entries: int
    replaceable_count: int  # entries where mod == vanilla-EN → can be germanised


@dataclass(frozen=True, slots=True)
class UtfAudioMergeReport:
    """Summary of an entire UTF audio merge operation."""

    merged_files: tuple[UtfMergeResult, ...]
    backup_dir: Path | None
    total_replaced: int
    total_kept: int


# ---------------------------------------------------------------------------
# UTF parser
# ---------------------------------------------------------------------------

def read_utf(path: Path) -> UtfFile:
    """Read a Freelancer UTF container and return all leaf entries."""
    raw = Path(path).read_bytes()
    if len(raw) < HEADER_SIZE or raw[:4] != UTF_MAGIC:
        raise ValueError(f"Not a valid UTF file: {path}")

    (
        version,
        tree_offset,
        tree_size,
        _unused1,
        entry_size,
        name_offset,
        name_alloc,
        name_used,
        data_offset,
        _unused2,
        _unused3,
        filetime_lo,
        filetime_hi,
    ) = struct.unpack_from("<13I", raw, 4)

    filetime = (filetime_hi << 32) | filetime_lo

    name_block = raw[name_offset : name_offset + name_alloc]
    num_entries = tree_size // entry_size

    entries: list[UtfEntry] = []
    for i in range(num_entries):
        eoff = tree_offset + i * entry_size
        (
            _peer,
            noff,
            flags,
            _pad,
            child_or_doff,
            _alloc,
            _size1,
            size2,
            ts1,
            ts2,
            ts3,
        ) = struct.unpack_from("<iIIiiIIIIII", raw, eoff)

        # Read name
        nend = name_block.find(b"\x00", noff)
        name = name_block[noff:nend].decode("ascii", errors="replace") if nend > noff else ""

        is_dir = bool(flags & DIR_FLAG)
        if is_dir or not name or name == "\\":
            continue

        blob = raw[data_offset + child_or_doff : data_offset + child_or_doff + size2]
        entries.append(UtfEntry(name=name, data=blob, flags=flags, timestamps=(ts1, ts2, ts3)))

    return UtfFile(version=version, filetime=filetime, entries=tuple(entries))


# ---------------------------------------------------------------------------
# UTF writer
# ---------------------------------------------------------------------------

def write_utf(path: Path, utf: UtfFile) -> None:
    """Write a UtfFile back to disk as a valid Freelancer UTF container."""
    entries = utf.entries

    # --- Build name block ---
    # Name block: \x00 + \\ + \x00 + entry names (null-terminated each)
    name_parts = [b"\x00", b"\\", b"\x00"]
    entry_name_offsets: list[int] = []
    current_name_pos = 3  # after \x00 \\ \x00
    for entry in entries:
        entry_name_offsets.append(current_name_pos)
        encoded = entry.name.encode("ascii") + b"\x00"
        name_parts.append(encoded)
        current_name_pos += len(encoded)

    name_used = current_name_pos
    # Pad name block to multiple of 4
    name_alloc = (name_used + 3) & ~3
    name_block = b"".join(name_parts)
    name_block += b"\x00" * (name_alloc - len(name_block))

    # --- Build data block ---
    data_parts: list[bytes] = []
    entry_data_offsets: list[int] = []
    current_data_pos = 0
    for entry in entries:
        # Align to 4-byte boundary
        padding = (4 - (current_data_pos % 4)) % 4
        if padding:
            data_parts.append(b"\x00" * padding)
            current_data_pos += padding
        entry_data_offsets.append(current_data_pos)
        data_parts.append(entry.data)
        current_data_pos += len(entry.data)
    data_block = b"".join(data_parts)

    # --- Build tree ---
    num_tree_entries = 1 + len(entries)  # root + leaves
    tree_size = num_tree_entries * ENTRY_SIZE

    name_offset = HEADER_SIZE
    tree_offset = name_offset + name_alloc
    data_offset = tree_offset + tree_size
    file_size = data_offset + len(data_block)

    # Root entry
    root_name_off = 1  # offset of "\\" in name block
    root_child_off = ENTRY_SIZE  # first child is right after root in tree
    root_ts = entries[0].timestamps if entries else (0, 0, 0)
    root_entry = struct.pack(
        "<iIIiIIIIIII",
        0,              # peer (no sibling)
        root_name_off,  # name offset
        DIR_FLAG,       # flags (directory)
        0,              # padding
        root_child_off, # child offset (relative to tree start)
        file_size,      # alloc = file size
        file_size,      # size1
        file_size,      # size2
        root_ts[0],
        root_ts[1],
        root_ts[2],
    )

    tree_parts = [root_entry]
    for idx, entry in enumerate(entries):
        is_last = idx == len(entries) - 1
        peer_off = 0 if is_last else (idx + 2) * ENTRY_SIZE  # next sibling offset in tree
        leaf_entry = struct.pack(
            "<iIIiIIIIIII",
            peer_off,
            entry_name_offsets[idx],
            entry.flags,
            0,
            entry_data_offsets[idx],
            len(entry.data),   # alloc
            len(entry.data),   # size1
            len(entry.data),   # size2
            entry.timestamps[0],
            entry.timestamps[1],
            entry.timestamps[2],
        )
        tree_parts.append(leaf_entry)
    tree_block = b"".join(tree_parts)

    # --- Build header ---
    filetime_lo = utf.filetime & 0xFFFF_FFFF
    filetime_hi = (utf.filetime >> 32) & 0xFFFF_FFFF
    header = struct.pack(
        "<4s13I",
        UTF_MAGIC,
        utf.version,
        tree_offset,
        tree_size,
        0,             # unused
        ENTRY_SIZE,
        name_offset,
        name_alloc,
        name_used,
        data_offset,
        0,             # unused
        0,             # unused
        filetime_lo,
        filetime_hi,
    )

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(header + name_block + tree_block + data_block)


# ---------------------------------------------------------------------------
# 3-way merge
# ---------------------------------------------------------------------------

def _entry_hash(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def _entries_by_name(utf: UtfFile) -> dict[str, UtfEntry]:
    return {e.name: e for e in utf.entries}


def scan_utf_merge_candidate(
    mod_path: Path,
    ref_en_path: Path,
    ref_de_path: Path,
) -> UtfAudioMergeCandidate | None:
    """Check a single UTF file triple and return a merge candidate if useful."""
    mod_path = Path(mod_path)
    ref_en_path = Path(ref_en_path)
    ref_de_path = Path(ref_de_path)

    if not (mod_path.is_file() and ref_en_path.is_file() and ref_de_path.is_file()):
        return None

    try:
        mod_utf = read_utf(mod_path)
        ref_en_utf = read_utf(ref_en_path)
        ref_de_utf = read_utf(ref_de_path)
    except (ValueError, struct.error):
        return None

    mod_map = _entries_by_name(mod_utf)
    en_map = _entries_by_name(ref_en_utf)
    de_map = _entries_by_name(ref_de_utf)

    replaceable = 0
    for name, mod_entry in mod_map.items():
        en_entry = en_map.get(name)
        de_entry = de_map.get(name)
        if en_entry is not None and de_entry is not None:
            if _entry_hash(mod_entry.data) == _entry_hash(en_entry.data):
                replaceable += 1

    if replaceable == 0:
        return None

    return UtfAudioMergeCandidate(
        relative_path=Path(mod_path.name),
        mod_path=mod_path,
        ref_en_path=ref_en_path,
        ref_de_path=ref_de_path,
        total_entries=len(mod_map),
        replaceable_count=replaceable,
    )


def merge_utf_file(
    mod_path: Path,
    ref_en_path: Path,
    ref_de_path: Path,
    output_path: Path,
) -> UtfMergeResult:
    """Perform a 3-way merge of a single UTF audio file.

    For each entry in the mod file:
    - If it matches vanilla-EN → replace with the German version
    - If the mod changed it → keep the mod version
    - If it only exists in mod (no EN/DE counterpart) → keep as-is
    """
    mod_utf = read_utf(mod_path)
    ref_en_utf = read_utf(ref_en_path)
    ref_de_utf = read_utf(ref_de_path)

    en_map = _entries_by_name(ref_en_utf)
    de_map = _entries_by_name(ref_de_utf)

    merged_entries: list[UtfEntry] = []
    merge_log: list[UtfMergeEntry] = []
    replaced = 0
    kept = 0
    only_mod = 0
    only_de = 0

    for mod_entry in mod_utf.entries:
        en_entry = en_map.get(mod_entry.name)
        de_entry = de_map.get(mod_entry.name)

        if en_entry is not None and de_entry is not None:
            mod_hash = _entry_hash(mod_entry.data)
            en_hash = _entry_hash(en_entry.data)
            if mod_hash == en_hash:
                # Mod didn't change this entry → use German audio
                merged_entries.append(UtfEntry(
                    name=mod_entry.name,
                    data=de_entry.data,
                    flags=mod_entry.flags,
                    timestamps=mod_entry.timestamps,
                ))
                merge_log.append(UtfMergeEntry(hash_id=mod_entry.name, action="replaced", source="de"))
                replaced += 1
            else:
                # Mod changed this entry → keep mod version
                merged_entries.append(mod_entry)
                merge_log.append(UtfMergeEntry(hash_id=mod_entry.name, action="kept", source="mod"))
                kept += 1
        else:
            # Entry only in mod or missing from one reference
            merged_entries.append(mod_entry)
            merge_log.append(UtfMergeEntry(hash_id=mod_entry.name, action="kept", source="mod"))
            only_mod += 1

    # Check for entries only in DE (exist in DE but not in mod)
    mod_names = {e.name for e in mod_utf.entries}
    for de_entry in ref_de_utf.entries:
        if de_entry.name not in mod_names:
            only_de += 1

    merged_utf = UtfFile(
        version=mod_utf.version,
        filetime=mod_utf.filetime,
        entries=tuple(merged_entries),
    )
    write_utf(output_path, merged_utf)

    return UtfMergeResult(
        filename=Path(mod_path).name,
        total_entries=len(mod_utf.entries),
        replaced_count=replaced,
        kept_count=kept,
        only_mod_count=only_mod,
        only_de_count=only_de,
        entries=tuple(merge_log),
    )
