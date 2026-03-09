"""
Image resource decoder for The Sims 4 .package files.

Handles EA's custom DST (shuffled DDS) formats:
- DST1: Shuffled DXT1 (no alpha, 8 bytes/block)
- DST3: Shuffled DXT3 (explicit alpha, 16 bytes/block)
- DST5: Shuffled DXT5 (interpolated alpha, 16 bytes/block)

The DST formats use standard DDS headers but rearrange the block data
so that like components are grouped together (all alpha endpoints, then
all color endpoints, etc.) instead of interleaved per-block.
"""

import io
import struct
from typing import Optional


# DDS FourCC values
FOURCC_DXT1 = b'DXT1'
FOURCC_DXT3 = b'DXT3'
FOURCC_DXT5 = b'DXT5'
FOURCC_DST1 = b'DST1'
FOURCC_DST3 = b'DST3'
FOURCC_DST5 = b'DST5'

DDS_HEADER_SIZE = 128
DDS_MAGIC = b'DDS '


def _unshuffle_dst1(data):
    # type: (bytes) -> bytes
    """Unshuffle DST1 block data to standard DXT1 layout.

    DST1 splits each 8-byte DXT1 block into two halves:
      [all 4-byte color endpoints] [all 4-byte color indices]
    """
    half = len(data) // 2
    result = bytearray()
    for i in range(half // 4):
        result.extend(data[i * 4:(i + 1) * 4])
        result.extend(data[half + i * 4:half + (i + 1) * 4])
    return bytes(result)


def _unshuffle_dst5(data):
    # type: (bytes) -> bytes
    """Unshuffle DST5 block data to standard DXT5 layout.

    DST5 stores block components in region order [0, 2, 1, 3]:
      Region 0: alpha endpoints (2 bytes/block)
      Region 2: color endpoints (4 bytes/block)
      Region 1: alpha indices  (6 bytes/block)
      Region 3: color indices  (4 bytes/block)

    Standard DXT5 block order is [0, 1, 2, 3]:
      alpha endpoints(2) + alpha indices(6) + color endpoints(4) + color indices(4)
    """
    size = len(data)
    num_blocks = size // 16

    # Region boundaries in shuffled order
    off0 = 0
    off2 = off0 + num_blocks * 2
    off1 = off2 + num_blocks * 4
    off3 = off1 + num_blocks * 6

    result = bytearray()
    o0, o1, o2, o3 = off0, off1, off2, off3
    for _ in range(num_blocks):
        result.extend(data[o0:o0 + 2])   # alpha endpoints
        result.extend(data[o1:o1 + 6])   # alpha indices
        result.extend(data[o2:o2 + 4])   # color endpoints
        result.extend(data[o3:o3 + 4])   # color indices
        o0 += 2
        o1 += 6
        o2 += 4
        o3 += 4

    return bytes(result)


def decode_image(data):
    # type: (bytes) -> bytes
    """Decode a Sims 4 image resource to standard DDS or PNG bytes.

    Handles DST1/DST3/DST5 by unshuffling to standard DXT format.
    Non-DST data (standard DDS, PNG, etc.) is returned as-is.

    Args:
        data: Raw decompressed image resource bytes.

    Returns:
        Image bytes suitable for opening with PIL/Pillow.
    """
    if len(data) < DDS_HEADER_SIZE:
        return data

    # Check for DDS magic
    if data[:4] != DDS_MAGIC:
        return data  # Not DDS — might be PNG or other format

    fourcc = data[84:88]

    if fourcc == FOURCC_DST5:
        header = bytearray(data[:DDS_HEADER_SIZE])
        header[84:88] = FOURCC_DXT5
        return bytes(header) + _unshuffle_dst5(data[DDS_HEADER_SIZE:])

    if fourcc == FOURCC_DST1:
        header = bytearray(data[:DDS_HEADER_SIZE])
        header[84:88] = FOURCC_DXT1
        return bytes(header) + _unshuffle_dst1(data[DDS_HEADER_SIZE:])

    if fourcc == FOURCC_DST3:
        # DST3 uses the same layout as DST5 for its 16-byte blocks
        header = bytearray(data[:DDS_HEADER_SIZE])
        header[84:88] = FOURCC_DXT3
        return bytes(header) + _unshuffle_dst5(data[DDS_HEADER_SIZE:])

    # Standard DDS — return as-is
    return data


def decode_image_to_png(data):
    # type: (bytes) -> bytes
    """Decode a Sims 4 image resource and convert to PNG bytes.

    Requires Pillow to be installed.

    Args:
        data: Raw decompressed image resource bytes.

    Returns:
        PNG image bytes.
    """
    from PIL import Image

    decoded = decode_image(data)
    img = Image.open(io.BytesIO(decoded))

    # Convert to RGBA if not already
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()
