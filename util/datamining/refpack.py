"""
RefPack (QFS) decompression for EA's DBPF format.

RefPack is EA's proprietary compression used in The Sims series and other
EA games. It's a simple LZ-based scheme identified by the magic bytes 0x10FB
or 0x50FB at the start of compressed data.

Header format:
  - If first byte has bit 0x80 set: 4-byte big-endian decompressed size
    (after the 2-byte magic), otherwise 3-byte big-endian size.
  - Some variants prefix an additional 4-byte compressed size before the magic.

The compression uses variable-length control codes:
  - 0x00-0x7F: 2-byte code — short copy from output + literal bytes
  - 0x80-0xBF: 3-byte code — medium copy from output + literal bytes
  - 0xC0-0xDF: 4-byte code — long copy from output + literal bytes
  - 0xE0-0xFB: 1-byte code — literal bytes only
  - 0xFC-0xFF: stop codes
"""

import struct


def is_refpack(data):
    # type: (bytes) -> bool
    """Check if data is RefPack compressed."""
    if len(data) < 2:
        return False
    # Check for RefPack magic at offset 0 or after a 4-byte compressed size
    if len(data) >= 2 and data[0] in (0x10, 0x50) and data[1] == 0xFB:
        return True
    if len(data) >= 6 and data[4] in (0x10, 0x50) and data[5] == 0xFB:
        return True
    return False


def decompress(data):
    # type: (bytes) -> bytes
    """Decompress RefPack/QFS compressed data.

    Args:
        data: Raw compressed bytes (may include a 4-byte prefix before magic).

    Returns:
        Decompressed bytes.

    Raises:
        ValueError: If the data is not valid RefPack.
    """
    offset = 0

    # Skip optional 4-byte compressed size prefix
    if len(data) >= 6 and data[4] in (0x10, 0x50) and data[5] == 0xFB:
        offset = 4

    if len(data) < offset + 2:
        raise ValueError("Data too short for RefPack header")

    flags = data[offset]
    if data[offset + 1] != 0xFB:
        raise ValueError(
            "Invalid RefPack magic: 0x{:02X}{:02X}".format(
                data[offset], data[offset + 1]
            )
        )
    offset += 2

    # Read decompressed size
    if flags & 0x80:
        # 4-byte big-endian decompressed size
        if len(data) < offset + 4:
            raise ValueError("Data too short for 4-byte size")
        decompressed_size = struct.unpack_from(">I", data, offset)[0]
        offset += 4
    else:
        # 3-byte big-endian decompressed size
        if len(data) < offset + 3:
            raise ValueError("Data too short for 3-byte size")
        decompressed_size = (
            (data[offset] << 16) | (data[offset + 1] << 8) | data[offset + 2]
        )
        offset += 3

    output = bytearray()
    src = offset

    while src < len(data):
        code = data[src]

        if code <= 0x7F:
            # 2-byte control: short back-reference + literals
            if src + 1 >= len(data):
                break
            b1 = data[src + 1]
            num_literals = code & 0x03
            copy_length = ((code & 0x1C) >> 2) + 3
            copy_offset = ((code & 0x60) << 3) + b1 + 1
            src += 2

            # Append literal bytes
            output.extend(data[src:src + num_literals])
            src += num_literals

            # Copy from output history
            copy_src = len(output) - copy_offset
            for i in range(copy_length):
                output.append(output[copy_src + i])

        elif code <= 0xBF:
            # 3-byte control: medium back-reference + literals
            if src + 2 >= len(data):
                break
            b1 = data[src + 1]
            b2 = data[src + 2]
            num_literals = ((b1 & 0xC0) >> 6) & 0x03
            copy_length = (code & 0x3F) + 4
            copy_offset = ((b1 & 0x3F) << 8) + b2 + 1
            src += 3

            output.extend(data[src:src + num_literals])
            src += num_literals

            copy_src = len(output) - copy_offset
            for i in range(copy_length):
                output.append(output[copy_src + i])

        elif code <= 0xDF:
            # 4-byte control: long back-reference + literals
            if src + 3 >= len(data):
                break
            b1 = data[src + 1]
            b2 = data[src + 2]
            b3 = data[src + 3]
            num_literals = code & 0x03
            copy_length = ((code & 0x0C) << 6) + b3 + 5
            copy_offset = ((code & 0x10) << 12) + (b1 << 8) + b2 + 1
            src += 4

            output.extend(data[src:src + num_literals])
            src += num_literals

            copy_src = len(output) - copy_offset
            for i in range(copy_length):
                output.append(output[copy_src + i])

        elif code <= 0xFB:
            # 1-byte control: literal bytes only
            num_literals = ((code & 0x1F) << 2) + 4
            src += 1

            output.extend(data[src:src + num_literals])
            src += num_literals

        else:
            # 0xFC-0xFF: stop codes with 0-3 trailing literals
            num_literals = code & 0x03
            src += 1

            output.extend(data[src:src + num_literals])
            src += num_literals
            break

    return bytes(output[:decompressed_size])
