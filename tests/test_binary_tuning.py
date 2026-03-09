"""Tests for util.datamining.binary_tuning module."""

import struct
import pytest

from util.datamining.binary_tuning import (
    BinaryDecoder,
    DataType,
    is_binary_combined_tuning,
    parse_binary_data,
    decode_combined_tuning,
    RELOFFSET_NULL,
)


class TestBinaryDecoder:
    def test_uint8(self):
        d = BinaryDecoder(b'\x42')
        assert d.uint8() == 0x42
        assert d.tell() == 1

    def test_int32(self):
        data = struct.pack('<i', -12345)
        d = BinaryDecoder(data)
        assert d.int32() == -12345

    def test_uint32(self):
        data = struct.pack('<I', 0xDEADBEEF)
        d = BinaryDecoder(data)
        assert d.uint32() == 0xDEADBEEF

    def test_uint64(self):
        data = struct.pack('<Q', 0x123456789ABCDEF0)
        d = BinaryDecoder(data)
        assert d.uint64() == 0x123456789ABCDEF0

    def test_float32(self):
        data = struct.pack('<f', 3.14)
        d = BinaryDecoder(data)
        assert abs(d.float32() - 3.14) < 0.001

    def test_string(self):
        d = BinaryDecoder(b'hello\x00world\x00')
        assert d.string() == 'hello'
        assert d.string() == 'world'

    def test_seek_and_tell(self):
        d = BinaryDecoder(b'\x00' * 20)
        d.seek(10)
        assert d.tell() == 10
        d.skip(5)
        assert d.tell() == 15

    def test_is_eof(self):
        d = BinaryDecoder(b'\x00\x01')
        assert not d.is_eof()
        d.skip(2)
        assert d.is_eof()

    def test_chars_utf8(self):
        d = BinaryDecoder(b'DATA')
        assert d.chars_utf8(4) == 'DATA'


class TestIsBinaryCombinedTuning:
    def test_valid_data(self):
        assert is_binary_combined_tuning(b'DATA\x01\x01\x00\x00')

    def test_xml(self):
        assert not is_binary_combined_tuning(b'<?xml version="1.0"?>')

    def test_too_short(self):
        assert not is_binary_combined_tuning(b'DA')

    def test_empty(self):
        assert not is_binary_combined_tuning(b'')


class TestDataType:
    def test_alignment_1byte(self):
        assert DataType.alignment(DataType.Boolean) == 1
        assert DataType.alignment(DataType.Character) == 1

    def test_alignment_2byte(self):
        assert DataType.alignment(DataType.Int16) == 2
        assert DataType.alignment(DataType.UInt16) == 2

    def test_alignment_4byte(self):
        assert DataType.alignment(DataType.Int32) == 4
        assert DataType.alignment(DataType.Float) == 4
        assert DataType.alignment(DataType.String) == 4

    def test_alignment_8byte(self):
        assert DataType.alignment(DataType.Int64) == 8
        assert DataType.alignment(DataType.ResourceKey) == 8


class TestParseHeader:
    def test_wrong_magic(self):
        data = b'NOTD' + b'\x00' * 100
        with pytest.raises(ValueError, match="Not a DATA file"):
            parse_binary_data(data)

    def test_bad_version(self):
        data = b'DATA' + struct.pack('<I', 0x200) + b'\x00' * 100
        with pytest.raises(ValueError, match="Unknown DATA version"):
            parse_binary_data(data)
