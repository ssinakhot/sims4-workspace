"""Tests for util/datamining/refpack.py — RefPack/QFS decompression."""

import struct
import pytest

from util.datamining.refpack import is_refpack, decompress


# ---------------------------------------------------------------------------
# Helper: build a minimal valid RefPack stream
# ---------------------------------------------------------------------------

def _make_literal_payload(literal_bytes, magic=b'\x10\xFB'):
    """Build a RefPack stream that encodes *literal_bytes* using a single
    literal-only control code (0xE0-0xFB range) followed by a 0xFC stop code.

    Only works for literal lengths where (length - 4) is divisible by 4 and
    the result fits in 5 bits (i.e. 4, 8, 12, ... up to 128 bytes).
    """
    n = len(literal_bytes)
    assert (n - 4) % 4 == 0 and 4 <= n <= 112
    code = 0xE0 | ((n - 4) // 4)

    # 3-byte big-endian decompressed size
    size_bytes = struct.pack(">I", n)[1:]  # last 3 bytes

    return magic + size_bytes + bytes([code]) + literal_bytes + b'\xFC'


# ===================================================================
# is_refpack tests
# ===================================================================

class TestIsRefpack:
    def test_magic_10fb(self):
        data = b'\x10\xFB' + b'\x00' * 10
        assert is_refpack(data) is True

    def test_magic_50fb(self):
        data = b'\x50\xFB' + b'\x00' * 10
        assert is_refpack(data) is True

    def test_magic_at_offset_4(self):
        # 4-byte compressed size prefix then magic
        data = b'\x00\x00\x00\x20' + b'\x10\xFB' + b'\x00' * 6
        assert is_refpack(data) is True

    def test_magic_50fb_at_offset_4(self):
        data = b'\xFF\xFF\xFF\xFF' + b'\x50\xFB' + b'\x00' * 6
        assert is_refpack(data) is True

    def test_non_refpack_data(self):
        assert is_refpack(b'\x00\x00\x00\x00\x00\x00') is False

    def test_wrong_second_byte(self):
        assert is_refpack(b'\x10\xFA\x00\x00') is False

    def test_wrong_first_byte(self):
        assert is_refpack(b'\x20\xFB\x00\x00') is False

    def test_shorter_than_2_bytes(self):
        assert is_refpack(b'\x10') is False

    def test_empty_bytes(self):
        assert is_refpack(b'') is False

    def test_exactly_2_bytes_valid(self):
        assert is_refpack(b'\x10\xFB') is True

    def test_exactly_2_bytes_invalid(self):
        assert is_refpack(b'\xAB\xCD') is False


# ===================================================================
# decompress — error cases
# ===================================================================

class TestDecompressErrors:
    def test_invalid_magic(self):
        with pytest.raises(ValueError, match="Invalid RefPack magic"):
            decompress(b'\x10\xAA\x00\x00\x00')

    def test_data_too_short(self):
        with pytest.raises(ValueError, match="Data too short"):
            decompress(b'\x10')

    def test_empty_data(self):
        with pytest.raises(ValueError, match="Data too short"):
            decompress(b'')

    def test_no_size_bytes_after_magic(self):
        # Magic present but no room for the 3-byte size
        with pytest.raises(ValueError, match="Data too short for 3-byte size"):
            decompress(b'\x10\xFB\x00')

    def test_no_size_bytes_4byte_header(self):
        # 0x80 flag means 4-byte size, but only 2 bytes follow
        with pytest.raises(ValueError, match="Data too short for 4-byte size"):
            decompress(b'\x90\xFB\x00\x00')


# ===================================================================
# decompress — literal-only payloads
# ===================================================================

class TestDecompressLiterals:
    def test_4_literal_bytes(self):
        """Smallest literal-only control: code 0xE0 → 4 literals."""
        payload = b'\xDE\xAD\xBE\xEF'
        stream = _make_literal_payload(payload)
        assert decompress(stream) == payload

    def test_8_literal_bytes(self):
        """code = 0xE1 → 8 literal bytes."""
        payload = b'\x01\x02\x03\x04\x05\x06\x07\x08'
        stream = _make_literal_payload(payload)
        assert decompress(stream) == payload

    def test_112_literal_bytes_max(self):
        """Maximum literal-only control: 0xFB → ((0x1B) << 2) + 4 = 112.
        (0xFB & 0x1F = 0x1B = 27; 27*4+4 = 112.)"""
        payload = bytes(range(112))
        stream = _make_literal_payload(payload)
        assert decompress(stream) == payload

    def test_stop_code_with_trailing_literals(self):
        """Stop codes 0xFD, 0xFE, 0xFF carry 1, 2, 3 trailing literals."""
        for num_trailing in range(4):
            stop_code = 0xFC + num_trailing
            trailing = bytes([0xAA + i for i in range(num_trailing)])
            size = num_trailing
            size_bytes = struct.pack(">I", size)[1:]
            stream = b'\x10\xFB' + size_bytes + bytes([stop_code]) + trailing
            assert decompress(stream) == trailing


# ===================================================================
# decompress — 3-byte vs 4-byte decompressed size header
# ===================================================================

class TestDecompressSizeHeaders:
    def test_3byte_size_header(self):
        """0x10FB → flags & 0x80 == 0 → 3-byte decompressed size."""
        payload = b'HELLO!!!'  # 8 bytes
        stream = _make_literal_payload(payload, magic=b'\x10\xFB')
        result = decompress(stream)
        assert result == payload

    def test_4byte_size_header(self):
        """0x90FB → flags & 0x80 != 0 → 4-byte decompressed size."""
        payload = b'TESTDATA'  # 8 bytes
        size_bytes = struct.pack(">I", 8)
        code = 0xE1  # 8 literals
        stream = b'\x90\xFB' + size_bytes + bytes([code]) + payload + b'\xFC'
        result = decompress(stream)
        assert result == payload


# ===================================================================
# decompress — 4-byte compressed size prefix variant
# ===================================================================

class TestDecompressCompressedSizePrefix:
    def test_4byte_prefix_before_magic(self):
        """Some variants have a 4-byte compressed size before the magic."""
        payload = b'PREFIXED'  # 8 bytes
        size_bytes = struct.pack(">I", 8)[1:]  # 3-byte decompressed size
        code = 0xE1  # 8 literals
        inner = b'\x10\xFB' + size_bytes + bytes([code]) + payload + b'\xFC'
        # Prepend 4-byte compressed size (value doesn't matter for decompression)
        prefix = struct.pack("<I", len(inner))
        stream = prefix + inner
        assert is_refpack(stream) is True
        assert decompress(stream) == payload


# ===================================================================
# decompress — output truncated to decompressed_size
# ===================================================================

class TestDecompressTruncation:
    def test_output_truncated_to_declared_size(self):
        """If control codes produce more output than decompressed_size, the
        result is truncated to decompressed_size."""
        payload = b'ABCDEFGH'  # 8 bytes of literal data
        # Declare decompressed size as only 5
        declared_size = 5
        size_bytes = struct.pack(">I", declared_size)[1:]
        code = 0xE1  # 8 literals
        stream = b'\x10\xFB' + size_bytes + bytes([code]) + payload + b'\xFC'
        result = decompress(stream)
        assert result == b'ABCDE'
        assert len(result) == declared_size


# ===================================================================
# decompress — back-reference (2-byte control code, 0x00-0x7F range)
# ===================================================================

class TestDecompressBackReference:
    def test_2byte_short_copy(self):
        """Write 8 literal bytes, then use a 2-byte control code to copy 3
        bytes from offset 8 (i.e. the beginning of output).

        2-byte code format (code <= 0x7F):
            num_literals = code & 0x03
            copy_length  = ((code & 0x1C) >> 2) + 3
            copy_offset  = ((code & 0x60) << 3) + b1 + 1

        We want: num_literals=0, copy_length=3, copy_offset=8
        - code & 0x03 = 0
        - ((code & 0x1C) >> 2) + 3 = 3  →  (code & 0x1C) >> 2 = 0  →  code & 0x1C = 0
        - ((code & 0x60) << 3) + b1 + 1 = 8  →  try code & 0x60 = 0, b1 = 7
        So code = 0x00, b1 = 0x07
        """
        literal_data = b'\x01\x02\x03\x04\x05\x06\x07\x08'
        expected = literal_data + b'\x01\x02\x03'
        decompressed_size = len(expected)  # 11
        size_bytes = struct.pack(">I", decompressed_size)[1:]

        # Literal-only control for 8 bytes: code = 0xE1
        lit_code = 0xE1
        # 2-byte back-ref: code=0x00, b1=0x07 → 0 literals, copy 3 from offset 8
        ref_code = bytes([0x00, 0x07])

        stream = (
            b'\x10\xFB'
            + size_bytes
            + bytes([lit_code])
            + literal_data
            + ref_code
            + b'\xFC'
        )
        result = decompress(stream)
        assert result == expected

    def test_2byte_copy_with_trailing_literals(self):
        """2-byte control with num_literals > 0: interleaved literals before
        the back-reference copy.

        We want: num_literals=2, copy_length=3, copy_offset=6
        After writing 4 initial literals via 0xE0, the output is 4 bytes.
        Then: 2 new literals are appended (output = 6 bytes),
              copy 3 bytes from offset 6 back (= beginning).

        code & 0x03 = 2
        ((code & 0x1C) >> 2) + 3 = 3  →  code & 0x1C = 0
        ((code & 0x60) << 3) + b1 + 1 = 6  →  code & 0x60 = 0, b1 = 5
        code = 0x02, b1 = 0x05
        """
        init_literals = b'\xAA\xBB\xCC\xDD'
        interleaved = b'\xEE\xFF'
        expected = init_literals + interleaved + b'\xAA\xBB\xCC'
        decompressed_size = len(expected)  # 9
        size_bytes = struct.pack(">I", decompressed_size)[1:]

        stream = (
            b'\x10\xFB'
            + size_bytes
            + bytes([0xE0])       # literal-only: 4 bytes
            + init_literals
            + bytes([0x02, 0x05]) # 2-byte code: 2 literals, copy 3 from offset 6
            + interleaved
            + b'\xFC'
        )
        result = decompress(stream)
        assert result == expected


# ===================================================================
# decompress — 3-byte control code (0x80-0xBF range) back-reference
# ===================================================================

class TestDecompress3ByteBackRef:
    def test_3byte_medium_copy(self):
        """3-byte control code: medium back-reference.

        Format (code in 0x80-0xBF):
            num_literals = ((b1 & 0xC0) >> 6) & 0x03
            copy_length  = (code & 0x3F) + 4
            copy_offset  = ((b1 & 0x3F) << 8) + b2 + 1

        We want: num_literals=0, copy_length=4, copy_offset=8
        - code & 0x3F = 0  →  code = 0x80
        - (b1 & 0xC0) >> 6 = 0, (b1 & 0x3F) << 8 + b2 + 1 = 8
          b1 = 0x00, b2 = 7
        """
        literal_data = b'ABCDEFGH'  # 8 bytes
        expected = literal_data + b'ABCD'
        decompressed_size = len(expected)  # 12
        size_bytes = struct.pack(">I", decompressed_size)[1:]

        stream = (
            b'\x10\xFB'
            + size_bytes
            + bytes([0xE1])              # 8 literals
            + literal_data
            + bytes([0x80, 0x00, 0x07])  # 3-byte code: copy 4 from offset 8
            + b'\xFC'
        )
        result = decompress(stream)
        assert result == expected


# ===================================================================
# decompress — 4-byte control code (0xC0-0xDF range) back-reference
# ===================================================================

class TestDecompress4ByteBackRef:
    def test_4byte_long_copy(self):
        """4-byte control code: long back-reference.

        Format (code in 0xC0-0xDF):
            num_literals = code & 0x03
            copy_length  = ((code & 0x0C) << 6) + b3 + 5
            copy_offset  = ((code & 0x10) << 12) + (b1 << 8) + b2 + 1

        We want: num_literals=0, copy_length=5, copy_offset=8
        - code & 0x03 = 0
        - ((code & 0x0C) << 6) + b3 + 5 = 5  →  code & 0x0C = 0, b3 = 0
        - ((code & 0x10) << 12) + (b1 << 8) + b2 + 1 = 8
          code & 0x10 = 0, b1 = 0, b2 = 7
        So code = 0xC0, b1 = 0x00, b2 = 0x07, b3 = 0x00
        """
        literal_data = b'ABCDEFGH'  # 8 bytes
        expected = literal_data + b'ABCDE'
        decompressed_size = len(expected)  # 13
        size_bytes = struct.pack(">I", decompressed_size)[1:]

        stream = (
            b'\x10\xFB'
            + size_bytes
            + bytes([0xE1])                        # 8 literals
            + literal_data
            + bytes([0xC0, 0x00, 0x07, 0x00])      # 4-byte code: copy 5 from offset 8
            + b'\xFC'
        )
        result = decompress(stream)
        assert result == expected


# ===================================================================
# decompress — overlapping back-reference (run-length style)
# ===================================================================

class TestDecompressOverlappingCopy:
    def test_overlapping_copy_repeats_bytes(self):
        """When copy_offset < copy_length, bytes are repeated (RLE-style).

        Write 4 literal bytes, then copy 6 from offset 2 — the copy source
        overlaps the destination, so earlier copied bytes feed later ones.

        Initial output: [A, B, C, D]
        copy_offset=2, so copy starts at index 2 (C, D)
        copy_length=6: C, D, C, D, C, D  (wraps around)
        Result: A B C D C D C D C D

        2-byte code: num_literals=0, copy_length=6, copy_offset=2
        - code & 0x03 = 0
        - ((code & 0x1C) >> 2) + 3 = 6  →  (code & 0x1C) >> 2 = 3  →  code & 0x1C = 0x0C
        - ((code & 0x60) << 3) + b1 + 1 = 2  →  code & 0x60 = 0, b1 = 1
        code = 0x0C, b1 = 0x01
        """
        init = b'ABCD'
        expected = b'ABCDCDCDCD'
        decompressed_size = len(expected)  # 10
        size_bytes = struct.pack(">I", decompressed_size)[1:]

        stream = (
            b'\x10\xFB'
            + size_bytes
            + bytes([0xE0])        # 4 literals
            + init
            + bytes([0x0C, 0x01]) # 2-byte: 0 lits, copy 6 from offset 2
            + b'\xFC'
        )
        result = decompress(stream)
        assert result == expected


# ===================================================================
# decompress — zero-length decompressed output
# ===================================================================

class TestDecompressZeroLength:
    def test_zero_decompressed_size(self):
        """Decompressed size = 0 should produce empty output."""
        stream = b'\x10\xFB\x00\x00\x00\xFC'
        result = decompress(stream)
        assert result == b''


# ===================================================================
# decompress — 0x50FB magic variant
# ===================================================================

class TestDecompress50FB:
    def test_50fb_magic(self):
        """0x50FB is an alternate RefPack magic (same decoding path)."""
        payload = b'TEST'
        stream = _make_literal_payload(payload, magic=b'\x50\xFB')
        result = decompress(stream)
        assert result == payload
