import struct
import pytest

from util.datamining.string_table import (
    StringTable,
    StringTableReader,
    STBL_MAGIC,
    STBL_HEADER_SIZE,
)


def build_stbl(entries):
    """Build a minimal STBL binary blob.

    entries: list of (key_hash, string) tuples
    """
    # Calculate string data length
    encoded = [(k, s.encode("utf-8")) for k, s in entries]
    string_data_len = sum(len(b) for _, b in encoded)

    # Header: magic(4) + version(2) + compressed(1) + num_entries(8) + reserved(2) + string_data_len(4)
    header = STBL_MAGIC
    header += struct.pack("<H", 5)           # version
    header += struct.pack("<B", 0)           # not compressed
    header += struct.pack("<Q", len(entries)) # num_entries
    header += struct.pack("<H", 0)           # reserved
    header += struct.pack("<I", string_data_len)

    assert len(header) == STBL_HEADER_SIZE

    # Entries
    body = b""
    for key_hash, string_bytes in encoded:
        body += struct.pack("<I", key_hash)      # key hash
        body += struct.pack("<B", 0)             # flags
        body += struct.pack("<H", len(string_bytes))  # string length
        body += string_bytes

    return header + body


class TestStringTable:
    def test_empty_table(self):
        table = StringTable()
        assert len(table) == 0
        assert 0x1234 not in table
        assert table.get(0x1234) is None

    def test_get_and_contains(self):
        table = StringTable()
        table.strings[0xABCD] = "Hello World"
        assert len(table) == 1
        assert 0xABCD in table
        assert table.get(0xABCD) == "Hello World"
        assert table[0xABCD] == "Hello World"

    def test_get_default(self):
        table = StringTable()
        assert table.get(0x1234, "fallback") == "fallback"

    def test_getitem_missing_raises(self):
        table = StringTable()
        with pytest.raises(KeyError):
            _ = table[0x9999]


class TestStringTableReader:
    def test_parse_empty(self):
        data = build_stbl([])
        table = StringTableReader.parse(data)
        assert len(table) == 0
        assert table.version == 5

    def test_parse_single_entry(self):
        data = build_stbl([(0x12345678, "Cooking")])
        table = StringTableReader.parse(data)
        assert len(table) == 1
        assert table[0x12345678] == "Cooking"

    def test_parse_multiple_entries(self):
        entries = [
            (0x0001, "Skill: Cooking"),
            (0x0002, "Master the culinary arts"),
            (0x0003, "Painting"),
        ]
        data = build_stbl(entries)
        table = StringTableReader.parse(data)
        assert len(table) == 3
        assert table[0x0001] == "Skill: Cooking"
        assert table[0x0002] == "Master the culinary arts"
        assert table[0x0003] == "Painting"

    def test_parse_unicode(self):
        data = build_stbl([(0xAAAA, "Peinture \u2014 l'art")])
        table = StringTableReader.parse(data)
        assert table[0xAAAA] == "Peinture \u2014 l'art"

    def test_invalid_magic(self):
        data = b"BAAD" + b"\x00" * 20
        with pytest.raises(ValueError, match="Invalid STBL magic"):
            StringTableReader.parse(data)

    def test_too_short(self):
        with pytest.raises(ValueError, match="STBL data too short"):
            StringTableReader.parse(b"STBL")

    def test_merge(self):
        t1 = StringTableReader.parse(build_stbl([(0x01, "alpha"), (0x02, "beta")]))
        t2 = StringTableReader.parse(build_stbl([(0x02, "BETA"), (0x03, "gamma")]))
        merged = StringTableReader.merge([t1, t2])
        assert len(merged) == 3
        assert merged[0x01] == "alpha"
        assert merged[0x02] == "BETA"  # t2 overrides t1
        assert merged[0x03] == "gamma"
