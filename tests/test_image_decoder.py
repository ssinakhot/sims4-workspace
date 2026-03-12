"""Tests for util.datamining.image_decoder module."""

import struct
import pytest

from util.datamining.image_decoder import (
    _unshuffle_dst1,
    _unshuffle_dst5,
    decode_image,
    DDS_HEADER_SIZE,
    DDS_MAGIC,
    FOURCC_DXT1,
    FOURCC_DXT3,
    FOURCC_DXT5,
    FOURCC_DST1,
    FOURCC_DST3,
    FOURCC_DST5,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_dds_header(fourcc):
    # type: (bytes) -> bytes
    """Build a minimal 128-byte DDS header with the given FourCC at offset 84."""
    header = bytearray(DDS_HEADER_SIZE)
    header[0:4] = DDS_MAGIC
    header[84:88] = fourcc
    return bytes(header)


# ---------------------------------------------------------------------------
# _unshuffle_dst1
# ---------------------------------------------------------------------------

class TestUnshuffleDst1:
    """Tests for _unshuffle_dst1 (DST1 → DXT1 block reordering)."""

    def test_single_block(self):
        """One 8-byte block: [endpoints4][indices4] → interleaved."""
        endpoints = b'\x01\x02\x03\x04'
        indices = b'\x05\x06\x07\x08'
        shuffled = endpoints + indices  # 8 bytes total

        result = _unshuffle_dst1(shuffled)

        # Single block: output is same as input (endpoints then indices)
        assert result == b'\x01\x02\x03\x04\x05\x06\x07\x08'

    def test_two_blocks(self):
        """Two 8-byte blocks: endpoints are grouped, then indices grouped."""
        ep_a = b'\x01\x02\x03\x04'
        ep_b = b'\x11\x12\x13\x14'
        idx_a = b'\xA1\xA2\xA3\xA4'
        idx_b = b'\xB1\xB2\xB3\xB4'

        # Shuffled: [ep_a ep_b] [idx_a idx_b]
        shuffled = ep_a + ep_b + idx_a + idx_b  # 16 bytes

        result = _unshuffle_dst1(shuffled)

        # Interleaved: [ep_a idx_a] [ep_b idx_b]
        expected = ep_a + idx_a + ep_b + idx_b
        assert result == expected

    def test_empty_input(self):
        """Empty data produces empty result."""
        assert _unshuffle_dst1(b'') == b''

    def test_round_trip_identity_single_block(self):
        """For a single block, shuffled == unshuffled (no reordering needed)."""
        data = bytes(range(8))
        assert _unshuffle_dst1(data) == data


# ---------------------------------------------------------------------------
# _unshuffle_dst5
# ---------------------------------------------------------------------------

class TestUnshuffleDst5:
    """Tests for _unshuffle_dst5 (DST5/DST3 → DXT5/DXT3 block reordering)."""

    def test_single_block(self):
        """One 16-byte block with known regions."""
        # Region 0: alpha endpoints  2B
        alpha_ep = b'\xAA\xBB'
        # Region 2: color endpoints  4B
        color_ep = b'\x11\x22\x33\x44'
        # Region 1: alpha indices    6B
        alpha_idx = b'\x01\x02\x03\x04\x05\x06'
        # Region 3: color indices    4B
        color_idx = b'\xF1\xF2\xF3\xF4'

        # Shuffled layout: [region0][region2][region1][region3]
        shuffled = alpha_ep + color_ep + alpha_idx + color_idx

        result = _unshuffle_dst5(shuffled)

        # Standard DXT5: [alpha_ep][alpha_idx][color_ep][color_idx]
        expected = alpha_ep + alpha_idx + color_ep + color_idx
        assert result == expected

    def test_two_blocks(self):
        """Two 16-byte blocks: verify per-region grouping is correctly interleaved."""
        # Block A components
        a_alpha_ep = b'\xA0\xA1'
        a_color_ep = b'\xC0\xC1\xC2\xC3'
        a_alpha_idx = b'\x10\x11\x12\x13\x14\x15'
        a_color_idx = b'\xD0\xD1\xD2\xD3'

        # Block B components
        b_alpha_ep = b'\xB0\xB1'
        b_color_ep = b'\xE0\xE1\xE2\xE3'
        b_alpha_idx = b'\x20\x21\x22\x23\x24\x25'
        b_color_idx = b'\xF0\xF1\xF2\xF3'

        # Shuffled: all region0, all region2, all region1, all region3
        shuffled = (
            a_alpha_ep + b_alpha_ep +        # region 0: 2B * 2 blocks
            a_color_ep + b_color_ep +        # region 2: 4B * 2 blocks
            a_alpha_idx + b_alpha_idx +      # region 1: 6B * 2 blocks
            a_color_idx + b_color_idx        # region 3: 4B * 2 blocks
        )
        assert len(shuffled) == 32

        result = _unshuffle_dst5(shuffled)

        # Standard DXT5: per-block [alpha_ep, alpha_idx, color_ep, color_idx]
        expected = (
            a_alpha_ep + a_alpha_idx + a_color_ep + a_color_idx +
            b_alpha_ep + b_alpha_idx + b_color_ep + b_color_idx
        )
        assert result == expected

    def test_empty_input(self):
        """Empty data produces empty result."""
        assert _unshuffle_dst5(b'') == b''

    def test_output_length_matches_input(self):
        """Output length always equals input length."""
        data = bytes(48)  # 3 blocks * 16 bytes
        result = _unshuffle_dst5(data)
        assert len(result) == len(data)


# ---------------------------------------------------------------------------
# decode_image
# ---------------------------------------------------------------------------

class TestDecodeImage:
    """Tests for decode_image (DST→DXT conversion dispatcher)."""

    def test_short_data_returned_as_is(self):
        """Data shorter than DDS_HEADER_SIZE is returned unchanged."""
        short = b'\x00' * 64
        assert decode_image(short) is short

    def test_exactly_header_size_no_magic_returned_as_is(self):
        """128 bytes without DDS magic is returned unchanged."""
        data = b'\x00' * DDS_HEADER_SIZE
        assert decode_image(data) is data

    def test_no_dds_magic_returned_as_is(self):
        """Non-DDS data (e.g. PNG signature) is returned unchanged."""
        png_sig = b'\x89PNG\r\n\x1a\n'
        data = png_sig + b'\x00' * (DDS_HEADER_SIZE - len(png_sig) + 50)
        assert decode_image(data) is data

    def test_standard_dxt1_returned_as_is(self):
        """Standard DXT1 (not DST1) should not be modified."""
        header = _make_dds_header(FOURCC_DXT1)
        body = bytes(range(8)) * 4  # some block data
        data = header + body
        result = decode_image(data)
        assert result is data

    def test_standard_dxt5_returned_as_is(self):
        """Standard DXT5 should not be modified."""
        header = _make_dds_header(FOURCC_DXT5)
        body = b'\xFF' * 32
        data = header + body
        result = decode_image(data)
        assert result is data

    def test_standard_dxt3_returned_as_is(self):
        """Standard DXT3 should not be modified."""
        header = _make_dds_header(FOURCC_DXT3)
        body = b'\xAB' * 16
        data = header + body
        result = decode_image(data)
        assert result is data

    def test_dst5_converts_fourcc(self):
        """DST5 header FourCC is rewritten to DXT5."""
        # Build 1-block DST5 body (16 bytes shuffled)
        alpha_ep = b'\xAA\xBB'
        color_ep = b'\x11\x22\x33\x44'
        alpha_idx = b'\x01\x02\x03\x04\x05\x06'
        color_idx = b'\xF1\xF2\xF3\xF4'
        body = alpha_ep + color_ep + alpha_idx + color_idx

        data = _make_dds_header(FOURCC_DST5) + body
        result = decode_image(data)

        assert result[84:88] == FOURCC_DXT5

    def test_dst5_unshuffles_body(self):
        """DST5 body is unshuffled to standard DXT5 block order."""
        alpha_ep = b'\xAA\xBB'
        color_ep = b'\x11\x22\x33\x44'
        alpha_idx = b'\x01\x02\x03\x04\x05\x06'
        color_idx = b'\xF1\xF2\xF3\xF4'
        body = alpha_ep + color_ep + alpha_idx + color_idx

        data = _make_dds_header(FOURCC_DST5) + body
        result = decode_image(data)

        expected_body = alpha_ep + alpha_idx + color_ep + color_idx
        assert result[DDS_HEADER_SIZE:] == expected_body

    def test_dst5_preserves_header_except_fourcc(self):
        """DST5 conversion only changes bytes 84-88 of the header."""
        header = bytearray(DDS_HEADER_SIZE)
        header[0:4] = DDS_MAGIC
        header[84:88] = FOURCC_DST5
        # Put some recognizable data elsewhere in header
        header[4:8] = b'\xDE\xAD\xBE\xEF'
        header[12:16] = b'\xCA\xFE\xBA\xBE'

        body = bytes(16)  # 1 block, all zeros
        data = bytes(header) + body
        result = decode_image(data)

        # FourCC changed
        assert result[84:88] == FOURCC_DXT5
        # Other header bytes preserved
        assert result[4:8] == b'\xDE\xAD\xBE\xEF'
        assert result[12:16] == b'\xCA\xFE\xBA\xBE'

    def test_dst1_converts_fourcc(self):
        """DST1 header FourCC is rewritten to DXT1."""
        body = bytes(8)  # 1 block
        data = _make_dds_header(FOURCC_DST1) + body
        result = decode_image(data)
        assert result[84:88] == FOURCC_DXT1

    def test_dst1_unshuffles_body(self):
        """DST1 body is unshuffled to standard DXT1 block order."""
        ep_a = b'\x01\x02\x03\x04'
        ep_b = b'\x11\x12\x13\x14'
        idx_a = b'\xA1\xA2\xA3\xA4'
        idx_b = b'\xB1\xB2\xB3\xB4'

        # Shuffled: [all endpoints][all indices]
        body = ep_a + ep_b + idx_a + idx_b
        data = _make_dds_header(FOURCC_DST1) + body
        result = decode_image(data)

        expected_body = ep_a + idx_a + ep_b + idx_b
        assert result[DDS_HEADER_SIZE:] == expected_body

    def test_dst3_converts_fourcc(self):
        """DST3 header FourCC is rewritten to DXT3."""
        body = bytes(16)  # 1 block
        data = _make_dds_header(FOURCC_DST3) + body
        result = decode_image(data)
        assert result[84:88] == FOURCC_DXT3

    def test_dst3_uses_dst5_unshuffle(self):
        """DST3 uses the same unshuffle logic as DST5 (16-byte blocks)."""
        alpha_ep = b'\xAA\xBB'
        color_ep = b'\x11\x22\x33\x44'
        alpha_idx = b'\x01\x02\x03\x04\x05\x06'
        color_idx = b'\xF1\xF2\xF3\xF4'
        body = alpha_ep + color_ep + alpha_idx + color_idx

        data = _make_dds_header(FOURCC_DST3) + body
        result = decode_image(data)

        expected_body = alpha_ep + alpha_idx + color_ep + color_idx
        assert result[DDS_HEADER_SIZE:] == expected_body
        assert result[84:88] == FOURCC_DXT3

    def test_output_length_equals_input_length(self):
        """Conversion does not change total data length."""
        body = bytes(32)  # 2 blocks
        for fourcc in (FOURCC_DST1, FOURCC_DST5, FOURCC_DST3):
            if fourcc == FOURCC_DST1:
                block_body = bytes(16)  # 2 DXT1 blocks (8 bytes each)
            else:
                block_body = bytes(32)  # 2 DXT5/DXT3 blocks (16 bytes each)
            data = _make_dds_header(fourcc) + block_body
            result = decode_image(data)
            assert len(result) == len(data), "Length mismatch for {}".format(fourcc)

    def test_header_only_no_body(self):
        """DST5 with header but zero-length body still works."""
        data = _make_dds_header(FOURCC_DST5)
        result = decode_image(data)
        assert result[84:88] == FOURCC_DXT5
        assert len(result) == DDS_HEADER_SIZE

    def test_unknown_fourcc_returned_as_is(self):
        """Unknown FourCC in DDS header is returned unchanged."""
        header = _make_dds_header(b'BC7\x00')
        body = b'\x00' * 32
        data = header + body
        result = decode_image(data)
        assert result is data


# ---------------------------------------------------------------------------
# decode_image_to_png (only if Pillow available)
# ---------------------------------------------------------------------------

class TestDecodeImageToPng:
    """Tests for decode_image_to_png (requires Pillow)."""

    def test_png_passthrough(self):
        """A valid PNG passed to decode_image_to_png produces PNG output."""
        PIL = pytest.importorskip("PIL")
        from PIL import Image
        from util.datamining.image_decoder import decode_image_to_png

        # Create a tiny 1x1 RGBA PNG in memory
        import io
        img = Image.new("RGBA", (1, 1), (255, 0, 0, 255))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        png_bytes = buf.getvalue()

        result = decode_image_to_png(png_bytes)

        # Result should be valid PNG
        assert result[:8] == b'\x89PNG\r\n\x1a\n'

        # Should be decodable back to a 1x1 RGBA image
        out_img = Image.open(io.BytesIO(result))
        assert out_img.size == (1, 1)
        assert out_img.mode == "RGBA"
