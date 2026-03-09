"""
DBPF v2.0 .package file parser for The Sims 4.

Sims 4 .package files use the DBPF (Database Packed File) v2.0 format:
- 96-byte header containing magic bytes, version info, index entry count, and index position/size
- Resource entries identified by (type, group, instance) tuples
- Key resource type: 0x03B33DDF = Tuning XML
"""

import struct
import zlib
from dataclasses import dataclass, field
from typing import BinaryIO, List

from util.datamining.refpack import is_refpack, decompress as refpack_decompress
from util.datamining.resource_types import (
    TUNING_TYPE_ID,
    COMBINED_TUNING_TYPE_ID,
    STRING_TABLE_TYPE_ID,
    RESOURCE_TYPE_LABELS,
)

# Re-export for backwards compatibility
TUNING_TYPE_ID = TUNING_TYPE_ID

DBPF_MAGIC = b"DBPF"
DBPF_HEADER_SIZE = 96


@dataclass
class ResourceKey:
    """Identifies a resource within a .package file."""
    type_id: int
    group: int
    instance: int

    @property
    def is_tuning(self) -> bool:
        return self.type_id == TUNING_TYPE_ID

    def __str__(self) -> str:
        return f"{self.type_id:08X}!{self.group:08X}!{self.instance:016X}"


@dataclass
class IndexEntry:
    """A single resource entry from the package index."""
    key: ResourceKey
    offset: int
    file_size: int  # size in the file (possibly compressed)
    mem_size: int   # size when decompressed
    compressed: bool
    compression_type: int = 0

    @property
    def is_compressed(self) -> bool:
        return self.compressed and self.file_size != self.mem_size


@dataclass
class PackageHeader:
    """DBPF v2.0 package header."""
    magic: bytes = b""
    major_version: int = 0
    minor_version: int = 0
    index_entry_count: int = 0
    index_offset: int = 0
    index_size: int = 0


class PackageReader:
    """Reads and parses Sims 4 .package (DBPF v2.0) files."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.header = PackageHeader()
        self.entries: List[IndexEntry] = []
        self._flags: int = 0

    def read(self) -> None:
        """Read the package file, parsing header and index."""
        with open(self.filepath, "rb") as f:
            self._read_header(f)
            self._read_index(f)

    def _read_header(self, f: BinaryIO) -> None:
        """Parse the 96-byte DBPF header."""
        data = f.read(DBPF_HEADER_SIZE)
        if len(data) < DBPF_HEADER_SIZE:
            raise ValueError(f"File too small for DBPF header: {len(data)} bytes")

        magic = data[0:4]
        if magic != DBPF_MAGIC:
            raise ValueError(f"Invalid DBPF magic: {magic!r} (expected {DBPF_MAGIC!r})")

        self.header.magic = magic
        self.header.major_version = struct.unpack_from("<I", data, 4)[0]
        self.header.minor_version = struct.unpack_from("<I", data, 8)[0]

        # Index entry count at offset 36
        self.header.index_entry_count = struct.unpack_from("<I", data, 36)[0]

        # Index offset at offset 64, index size at offset 60
        self.header.index_size = struct.unpack_from("<I", data, 60)[0]
        self.header.index_offset = struct.unpack_from("<I", data, 64)[0]

    def _read_index(self, f: BinaryIO) -> None:
        """Parse the resource index."""
        f.seek(self.header.index_offset)

        # Read index flags (first 4 bytes of index)
        self._flags = struct.unpack_from("<I", f.read(4))[0]

        # Determine which fields are constant across all entries
        # Bits 0-3 of flags indicate which of type/group/instance_hi/instance_lo are constant
        const_type = 0
        const_group = 0
        const_instance_hi = 0
        const_instance_lo = 0

        if self._flags & 0x01:
            const_type = struct.unpack("<I", f.read(4))[0]
        if self._flags & 0x02:
            const_group = struct.unpack("<I", f.read(4))[0]
        if self._flags & 0x04:
            const_instance_hi = struct.unpack("<I", f.read(4))[0]
        if self._flags & 0x08:
            const_instance_lo = struct.unpack("<I", f.read(4))[0]

        self.entries = []
        for _ in range(self.header.index_entry_count):
            type_id = const_type if (self._flags & 0x01) else struct.unpack("<I", f.read(4))[0]
            group = const_group if (self._flags & 0x02) else struct.unpack("<I", f.read(4))[0]
            instance_hi = const_instance_hi if (self._flags & 0x04) else struct.unpack("<I", f.read(4))[0]
            instance_lo = const_instance_lo if (self._flags & 0x08) else struct.unpack("<I", f.read(4))[0]
            instance = (instance_hi << 32) | instance_lo

            offset, file_size = struct.unpack("<II", f.read(8))
            mem_size, compressed = struct.unpack("<IH", f.read(6))

            # Skip 2 bytes (padding/unknown)
            f.read(2)

            key = ResourceKey(type_id=type_id, group=group, instance=instance)
            entry = IndexEntry(
                key=key,
                offset=offset,
                file_size=file_size & 0x7FFFFFFF,  # mask off high bit
                mem_size=mem_size,
                compressed=(compressed != 0),
                compression_type=compressed,
            )
            self.entries.append(entry)

    def extract_resource(self, entry: IndexEntry) -> bytes:
        """Extract and decompress a single resource."""
        with open(self.filepath, "rb") as f:
            f.seek(entry.offset)
            data = f.read(entry.file_size)

        if entry.is_compressed:
            # Try RefPack (EA's proprietary compression) first
            if is_refpack(data):
                data = refpack_decompress(data)
            else:
                # Fall back to zlib (compression type 0x5A42)
                try:
                    data = zlib.decompress(data)
                except zlib.error:
                    # Some entries have a 4-byte compression header to skip
                    try:
                        data = zlib.decompress(data[4:])
                    except zlib.error:
                        raise ValueError(f"Failed to decompress resource {entry.key}")

        return data

    def extract_by_type(self, type_id: int) -> List[IndexEntry]:
        """Return all index entries matching a resource type ID."""
        return [e for e in self.entries if e.key.type_id == type_id]

    def extract_tuning_entries(self) -> List[IndexEntry]:
        """Return all index entries that are tuning XML resources."""
        return self.extract_by_type(TUNING_TYPE_ID)

    def extract_combined_tuning_entries(self) -> List[IndexEntry]:
        """Return all CombinedTuning XML entries."""
        return self.extract_by_type(COMBINED_TUNING_TYPE_ID)

    def extract_string_table_entries(self, locale_group: int = 0x00000000) -> List[IndexEntry]:
        """Return String Table entries, optionally filtered by locale group.

        Args:
            locale_group: Group ID for locale filtering (0x00000000 = English).
                Pass None to return all locales.
        """
        entries = self.extract_by_type(STRING_TABLE_TYPE_ID)
        if locale_group is not None:
            entries = [e for e in entries if e.key.group == locale_group]
        return entries

    def extract_tuning_xml(self, entry: IndexEntry) -> str:
        """Extract a tuning XML resource and return it as a string."""
        data = self.extract_resource(entry)
        return data.decode("utf-8")
