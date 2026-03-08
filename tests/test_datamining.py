import struct
import zlib
import pytest

from datamining.package_reader import (
    PackageReader,
    ResourceKey,
    IndexEntry,
    DBPF_MAGIC,
    DBPF_HEADER_SIZE,
    TUNING_TYPE_ID,
)
from datamining.tuning_parser import TuningParser, TuningFile


# ---- Helper to build a minimal DBPF v2.0 file ----

def build_test_package(resources: list[tuple[int, int, int, bytes]]) -> bytes:
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
