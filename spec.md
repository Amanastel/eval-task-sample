# RTLV container format v1

All multi-byte fixed-width integers are **big-endian**.

## Header

| Offset | Size | Field | Notes |
|---|---|---|---|
| 0 | 4 | magic | exactly `RTLV` |
| 4 | 1 | version | must be `1` |
| 5 | 1 | flags | bit 0 `LENGTHS_FIXED`, bit 1 `HAS_CHECKSUM`, bits 2-7 must be 0 |
| 6 | varint | record_count | LEB128, always, regardless of flags |

## Records

`record_count` records follow, each:

| Field | Encoding |
|---|---|
| tag | LEB128 varint |
| length | LEB128 varint, OR 4-byte big-endian if `LENGTHS_FIXED` |
| value | exactly `length` bytes |

Zero-length values are legal. Duplicate tags are legal and preserved in order.

## Checksum

If `HAS_CHECKSUM`, the final 4 bytes are a big-endian CRC-32 (IEEE) computed over
**every byte from offset 0 up to but not including the checksum itself**.

## LEB128

Unsigned, little-endian base-128. Each byte carries 7 bits; the high bit means
"more bytes follow". A varint longer than 10 bytes is invalid.

## Errors

The parser must raise these exact exceptions, defined in the task:

| Exception | Condition |
|---|---|
| `BadMagic` | first 4 bytes are not `RTLV` |
| `BadVersion` | version byte is not 1 |
| `ReservedFlag` | any of bits 2-7 set in flags |
| `Truncated(offset)` | input ends mid-field; `offset` = index where the incomplete field began |
| `ChecksumMismatch(expected, actual)` | `HAS_CHECKSUM` set and CRC does not match |

Checks occur in that order. A file with bad magic and a bad checksum raises
`BadMagic`.
