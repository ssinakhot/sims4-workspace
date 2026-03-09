"""
String Table (STBL) parser for The Sims 4.

String Tables (resource type 0x220557DA) store localized strings as a binary
format mapping uint32 hash keys to UTF-8 string values.

Binary format:
  Header (21 bytes):
    - 4 bytes: magic "STBL"
    - 2 bytes: version (uint16 LE)
    - 1 byte:  compressed flag
    - 8 bytes: num_entries (uint64 LE)
    - 2 bytes: reserved
    - 4 bytes: string data length (uint32 LE)
  Entries (repeated num_entries times):
    - 4 bytes: key hash (uint32 LE)
    - 1 byte:  flags
    - 2 bytes: string length (uint16 LE)
    - N bytes: UTF-8 string data

Locale is determined by the group field of the resource key in the DBPF index:
  0x00000000 = English (US)
  0x00000001 = Chinese (Simplified)
  0x00000002 = Chinese (Traditional)
  ...etc.
"""

import struct
from typing import Dict, Optional

STBL_MAGIC = b"STBL"
STBL_HEADER_SIZE = 21

# Locale group IDs
LOCALE_ENGLISH = 0x00000000


class StringTable:
    """Parsed string table mapping hash keys to string values."""

    def __init__(self):
        # type: () -> None
        self.version = 0       # type: int
        self.strings = {}      # type: Dict[int, str]

    def __len__(self):
        # type: () -> int
        return len(self.strings)

    def __contains__(self, key):
        # type: (int) -> bool
        return key in self.strings

    def get(self, key, default=None):
        # type: (int, Optional[str]) -> Optional[str]
        """Look up a string by its hash key."""
        return self.strings.get(key, default)

    def __getitem__(self, key):
        # type: (int) -> str
        return self.strings[key]


class StringTableReader:
    """Reads STBL binary data into a StringTable."""

    @staticmethod
    def parse(data):
        # type: (bytes) -> StringTable
        """Parse a raw STBL binary resource into a StringTable.

        Args:
            data: Raw bytes of a STBL resource (already decompressed).

        Returns:
            A StringTable with all entries.

        Raises:
            ValueError: If the data is too short or has an invalid magic.
        """
        if len(data) < STBL_HEADER_SIZE:
            raise ValueError(
                "STBL data too short: {} bytes (need at least {})".format(
                    len(data), STBL_HEADER_SIZE
                )
            )

        magic = data[0:4]
        if magic != STBL_MAGIC:
            raise ValueError(
                "Invalid STBL magic: {!r} (expected {!r})".format(magic, STBL_MAGIC)
            )

        table = StringTable()
        table.version = struct.unpack_from("<H", data, 4)[0]

        num_entries = struct.unpack_from("<Q", data, 7)[0]

        offset = STBL_HEADER_SIZE
        for _ in range(num_entries):
            if offset + 7 > len(data):
                break

            key_hash = struct.unpack_from("<I", data, offset)[0]
            offset += 4

            # flags byte
            offset += 1

            str_len = struct.unpack_from("<H", data, offset)[0]
            offset += 2

            string_data = data[offset:offset + str_len]
            offset += str_len

            table.strings[key_hash] = string_data.decode("utf-8", errors="replace")

        return table

    @staticmethod
    def merge(tables):
        # type: (list) -> StringTable
        """Merge multiple StringTables into one.

        Later tables override earlier ones for duplicate keys.
        """
        merged = StringTable()
        for table in tables:
            merged.strings.update(table.strings)
        return merged
