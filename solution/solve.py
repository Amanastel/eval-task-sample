"""Reference solution for the RTLV container format. Standard library only."""
import zlib


class RTLVError(Exception): pass
class BadMagic(RTLVError): pass
class BadVersion(RTLVError): pass
class ReservedFlag(RTLVError): pass


class Truncated(RTLVError):
    def __init__(self, offset: int):
        self.offset = offset
        super().__init__(f"truncated at {offset}")


class ChecksumMismatch(RTLVError):
    def __init__(self, expected: int, actual: int):
        self.expected, self.actual = expected, actual
        super().__init__(f"expected {expected:08x}, got {actual:08x}")


MAGIC = b"RTLV"
LENGTHS_FIXED = 0b01
HAS_CHECKSUM = 0b10


def _varint(data: bytes, i: int) -> tuple[int, int]:
    """Decode LEB128 at i. Returns (value, next_index). Raises Truncated(start)."""
    start, shift, out = i, 0, 0
    while True:
        if i >= len(data):
            raise Truncated(start)
        if i - start >= 10:
            raise Truncated(start)
        b = data[i]
        out |= (b & 0x7F) << shift
        i += 1
        if not (b & 0x80):
            return out, i
        shift += 7


def parse(data: bytes) -> list[tuple[int, bytes]]:
    if len(data) < 4 or data[:4] != MAGIC:
        raise BadMagic()
    if len(data) < 5:
        raise Truncated(4)
    if data[4] != 1:
        raise BadVersion()
    if len(data) < 6:
        raise Truncated(5)
    flags = data[5]
    if flags & ~(LENGTHS_FIXED | HAS_CHECKSUM):
        raise ReservedFlag()

    body_end = len(data)
    if flags & HAS_CHECKSUM:
        if len(data) < 10:
            raise Truncated(max(6, len(data) - 4))
        body_end = len(data) - 4
        expected = int.from_bytes(data[body_end:], "big")
        actual = zlib.crc32(data[:body_end]) & 0xFFFFFFFF
        if expected != actual:
            raise ChecksumMismatch(expected, actual)

    view = data[:body_end]
    count, i = _varint(view, 6)

    out: list[tuple[int, bytes]] = []
    for _ in range(count):
        tag, i = _varint(view, i)
        if flags & LENGTHS_FIXED:
            if i + 4 > len(view):
                raise Truncated(i)
            length = int.from_bytes(view[i:i + 4], "big")
            i += 4
        else:
            length, i = _varint(view, i)
        if i + length > len(view):
            raise Truncated(i)
        out.append((tag, bytes(view[i:i + length])))
        i += length
    return out
