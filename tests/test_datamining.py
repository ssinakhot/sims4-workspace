import struct
import zlib
from typing import List, Tuple
import pytest

from util.datamining.package_reader import (
    PackageReader,
    ResourceKey,
    IndexEntry,
    DBPF_MAGIC,
    DBPF_HEADER_SIZE,
    TUNING_TYPE_ID,
)
from util.datamining.resource_types import (
    COMBINED_TUNING_TYPE_ID,
    STRING_TABLE_TYPE_ID,
)
from util.datamining.tuning_parser import TuningParser, TuningFile


# ---- Helper to build a minimal DBPF v2.0 file ----

def build_test_package(resources: List[Tuple[int, int, int, bytes]]) -> bytes:
    """Build a minimal DBPF v2.0 .package file in memory.

    resources: list of (type_id, group, instance, data) tuples
    """
    # Build resource data blocks
    data_blocks = []
    data_offset = DBPF_HEADER_SIZE  # resource data starts right after the header
    entry_info = []  # (type, group, instance, offset, size)

    for type_id, group, instance, data in resources:
        entry_info.append((type_id, group, instance, data_offset, len(data)))
        data_blocks.append(data)
        data_offset += len(data)

    # Build index
    index_offset = data_offset
    # Index: 4 bytes flags + 24 bytes per entry (no constant fields, flags=0)
    index_flags = 0  # no constant fields
    index_data = struct.pack("<I", index_flags)

    for type_id, group, instance, offset, size in entry_info:
        instance_hi = (instance >> 32) & 0xFFFFFFFF
        instance_lo = instance & 0xFFFFFFFF
        # type, group, instance_hi, instance_lo, offset, file_size, mem_size, compressed, padding
        index_data += struct.pack("<IIIIIIIBB",
                                 type_id, group, instance_hi, instance_lo,
                                 offset, size, size, 0, 0)
        index_data += b'\x00\x00'  # 2 bytes padding (to make it 26 bytes per entry total... but let's match the reader)

    index_size = len(index_data)

    # Build header (96 bytes)
    header = bytearray(DBPF_HEADER_SIZE)
    header[0:4] = DBPF_MAGIC
    struct.pack_into("<I", header, 4, 2)    # major version
    struct.pack_into("<I", header, 8, 1)    # minor version
    struct.pack_into("<I", header, 36, len(resources))  # index entry count
    struct.pack_into("<I", header, 60, index_size)       # index size
    struct.pack_into("<I", header, 64, index_offset)     # index offset

    return bytes(header) + b"".join(data_blocks) + index_data


# ---- PackageReader Tests ----

class TestResourceKey:
    def test_is_tuning(self):
        key = ResourceKey(type_id=TUNING_TYPE_ID, group=0, instance=12345)
        assert key.is_tuning

    def test_not_tuning(self):
        key = ResourceKey(type_id=0x00000001, group=0, instance=12345)
        assert not key.is_tuning

    def test_str(self):
        key = ResourceKey(type_id=0x03B33DDF, group=0, instance=0x0D94E80BE40B3604)
        s = str(key)
        assert "03B33DDF" in s
        assert "0D94E80BE40B3604" in s


class TestPackageReader:
    def test_read_empty_package(self, tmp_path):
        pkg_data = build_test_package([])
        pkg_file = tmp_path / "empty.package"
        pkg_file.write_bytes(pkg_data)

        reader = PackageReader(str(pkg_file))
        reader.read()

        assert reader.header.major_version == 2
        assert reader.header.index_entry_count == 0
        assert len(reader.entries) == 0

    def test_invalid_magic(self, tmp_path):
        pkg_file = tmp_path / "bad.package"
        pkg_file.write_bytes(b"BAAD" + b"\x00" * 92)

        reader = PackageReader(str(pkg_file))
        with pytest.raises(ValueError, match="Invalid DBPF magic"):
            reader.read()

    def test_file_too_small(self, tmp_path):
        pkg_file = tmp_path / "tiny.package"
        pkg_file.write_bytes(b"DBPF")

        reader = PackageReader(str(pkg_file))
        with pytest.raises(ValueError, match="File too small"):
            reader.read()

    def test_extract_tuning_entries(self, tmp_path):
        tuning_xml = b'<I c="Buff" i="buff" n="buff_Test" s="12345"></I>'
        non_tuning = b"other data"

        pkg_data = build_test_package([
            (TUNING_TYPE_ID, 0, 100, tuning_xml),
            (0x00000001, 0, 200, non_tuning),
            (TUNING_TYPE_ID, 0, 300, tuning_xml),
        ])
        pkg_file = tmp_path / "test.package"
        pkg_file.write_bytes(pkg_data)

        reader = PackageReader(str(pkg_file))
        reader.read()

        tuning_entries = reader.extract_tuning_entries()
        assert len(tuning_entries) == 2
        assert all(e.key.is_tuning for e in tuning_entries)

    def test_extract_resource_uncompressed(self, tmp_path):
        raw_data = b"hello world resource data"
        pkg_data = build_test_package([
            (0x00000001, 0, 100, raw_data),
        ])
        pkg_file = tmp_path / "test.package"
        pkg_file.write_bytes(pkg_data)

        reader = PackageReader(str(pkg_file))
        reader.read()

        result = reader.extract_resource(reader.entries[0])
        assert result == raw_data

    def test_extract_resource_zlib_compressed(self, tmp_path):
        original_data = b"hello world uncompressed resource data" * 10
        compressed_data = zlib.compress(original_data)

        # Build the package manually with a compressed entry
        data_offset = DBPF_HEADER_SIZE
        index_offset = data_offset + len(compressed_data)

        # Index: 4-byte flags + 32-byte entry
        index_flags = 0
        index_data = struct.pack("<I", index_flags)
        instance = 100
        instance_hi = (instance >> 32) & 0xFFFFFFFF
        instance_lo = instance & 0xFFFFFFFF
        # compressed field = 1 (non-zero -> compressed), file_size = compressed, mem_size = original
        index_data += struct.pack("<IIIIIIIBB",
                                 0x00000001, 0, instance_hi, instance_lo,
                                 data_offset, len(compressed_data), len(original_data),
                                 1, 0)
        index_data += b'\x00\x00'
        index_size = len(index_data)

        header = bytearray(DBPF_HEADER_SIZE)
        header[0:4] = DBPF_MAGIC
        struct.pack_into("<I", header, 4, 2)
        struct.pack_into("<I", header, 8, 1)
        struct.pack_into("<I", header, 36, 1)         # 1 entry
        struct.pack_into("<I", header, 60, index_size)
        struct.pack_into("<I", header, 64, index_offset)

        pkg_data = bytes(header) + compressed_data + index_data
        pkg_file = tmp_path / "compressed.package"
        pkg_file.write_bytes(pkg_data)

        reader = PackageReader(str(pkg_file))
        reader.read()

        assert reader.entries[0].is_compressed
        result = reader.extract_resource(reader.entries[0])
        assert result == original_data

    def test_extract_combined_tuning_entries(self, tmp_path):
        combined_data = b'<combined><R><I c="Buff" i="buff" n="buff_Test" s="1"></I></R></combined>'
        other_data = b"other stuff"

        pkg_data = build_test_package([
            (COMBINED_TUNING_TYPE_ID, 0, 500, combined_data),
            (0x00000001, 0, 600, other_data),
            (COMBINED_TUNING_TYPE_ID, 0, 700, combined_data),
        ])
        pkg_file = tmp_path / "combined.package"
        pkg_file.write_bytes(pkg_data)

        reader = PackageReader(str(pkg_file))
        reader.read()

        entries = reader.extract_combined_tuning_entries()
        assert len(entries) == 2
        assert all(e.key.type_id == COMBINED_TUNING_TYPE_ID for e in entries)
        assert entries[0].key.instance == 500
        assert entries[1].key.instance == 700

    def test_extract_string_table_entries(self, tmp_path):
        stbl_data = b"STBL\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"

        pkg_data = build_test_package([
            (STRING_TABLE_TYPE_ID, 0x00000000, 100, stbl_data),  # English
            (STRING_TABLE_TYPE_ID, 0x00000002, 200, stbl_data),  # Other locale
            (STRING_TABLE_TYPE_ID, 0x00000000, 300, stbl_data),  # English
            (0x00000001, 0, 400, b"not a string table"),
        ])
        pkg_file = tmp_path / "strings.package"
        pkg_file.write_bytes(pkg_data)

        reader = PackageReader(str(pkg_file))
        reader.read()

        # Default: English locale (group 0x00000000)
        english_entries = reader.extract_string_table_entries()
        assert len(english_entries) == 2
        assert all(e.key.type_id == STRING_TABLE_TYPE_ID for e in english_entries)
        assert all(e.key.group == 0x00000000 for e in english_entries)

        # Specific locale
        other_entries = reader.extract_string_table_entries(locale_group=0x00000002)
        assert len(other_entries) == 1
        assert other_entries[0].key.instance == 200

        # All locales (None)
        all_entries = reader.extract_string_table_entries(locale_group=None)
        assert len(all_entries) == 3

    def test_extract_tuning_xml(self, tmp_path):
        xml_bytes = b'<I s="1" i="buff" n="buff_Test"></I>'
        pkg_data = build_test_package([
            (TUNING_TYPE_ID, 0, 100, xml_bytes),
        ])
        pkg_file = tmp_path / "test.package"
        pkg_file.write_bytes(pkg_data)

        reader = PackageReader(str(pkg_file))
        reader.read()

        tuning_entries = reader.extract_tuning_entries()
        xml_str = reader.extract_tuning_xml(tuning_entries[0])
        assert xml_str == xml_bytes.decode("utf-8")
        assert "buff_Test" in xml_str


class TestIndexEntry:
    def test_is_compressed_true(self):
        key = ResourceKey(type_id=1, group=0, instance=0)
        entry = IndexEntry(key=key, offset=0, file_size=50, mem_size=100, compressed=True)
        assert entry.is_compressed

    def test_is_compressed_false_when_flag_off(self):
        key = ResourceKey(type_id=1, group=0, instance=0)
        entry = IndexEntry(key=key, offset=0, file_size=50, mem_size=100, compressed=False)
        assert not entry.is_compressed

    def test_is_compressed_false_when_sizes_equal(self):
        key = ResourceKey(type_id=1, group=0, instance=0)
        entry = IndexEntry(key=key, offset=0, file_size=100, mem_size=100, compressed=True)
        assert not entry.is_compressed


# ---- TuningParser Tests ----

SAMPLE_TUNING_XML = """<?xml version="1.0" encoding="utf-8"?>
<I c="sims.sim_info_types.Trait" i="trait" m="traits.trait_Gloomy" n="trait_Gloomy" s="32427">
  <T n="display_name">0xABCDE</T>
  <T n="buff_reference">54321</T>
  <T n="some_text">not a number</T>
</I>"""


class TestTuningParser:
    def test_parse_basic(self):
        result = TuningParser.parse(SAMPLE_TUNING_XML)

        assert isinstance(result, TuningFile)
        assert result.instance_id == 32427
        assert result.tuning_type == "trait"
        assert result.name == "trait_Gloomy"
        assert result.cls == "sims.sim_info_types.Trait"

    def test_parse_references(self):
        result = TuningParser.parse(SAMPLE_TUNING_XML)
        assert 54321 in result.references

    def test_parse_minimal(self):
        xml = '<I s="999" i="interaction" n="si_Test"></I>'
        result = TuningParser.parse(xml)
        assert result.instance_id == 999
        assert result.tuning_type == "interaction"
        assert result.name == "si_Test"

    def test_parse_multiple(self):
        xml1 = '<I s="1" i="buff" n="buff_A"></I>'
        xml2 = '<I s="2" i="trait" n="trait_B"></I>'
        results = TuningParser.parse_multiple([xml1, xml2])
        assert len(results) == 2
        assert results[0].name == "buff_A"
        assert results[1].name == "trait_B"

    def test_parse_multiple_skips_invalid(self):
        good = '<I s="1" i="buff" n="buff_A"></I>'
        bad = "not xml at all <<<"
        results = TuningParser.parse_multiple([good, bad])
        assert len(results) == 1
