"""Deterministic verifier for the RTLV task.

Vectors are generated from a seed at verification time, so a solution cannot
pass by hardcoding outputs. Checks happy paths, error types, and error payloads.

Exit 0 = pass. Any non-zero exit = fail, with the first failure printed.
"""
import importlib.util
import random
import sys
import zlib
from pathlib import Path

SEED = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 20260908
LENGTHS_FIXED, HAS_CHECKSUM = 0b01, 0b10


def load(path="solution/solve.py"):
    spec = importlib.util.spec_from_file_location("sol", Path(__file__).parent / path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def leb(n: int) -> bytes:
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        out.append(b | (0x80 if n else 0))
        if not n:
            return bytes(out)


def build(records, *, fixed=False, checksum=False, version=1, flags=None, magic=b"RTLV"):
    f = (LENGTHS_FIXED if fixed else 0) | (HAS_CHECKSUM if checksum else 0)
    if flags is not None:
        f = flags
    body = bytearray(magic + bytes([version, f]) + leb(len(records)))
    for tag, val in records:
        body += leb(tag)
        body += len(val).to_bytes(4, "big") if fixed else leb(len(val))
        body += val
    if checksum:
        body += (zlib.crc32(bytes(body)) & 0xFFFFFFFF).to_bytes(4, "big")
    return bytes(body)


def gen_records(rng, n):
    out = []
    for _ in range(n):
        tag = rng.choice([0, 1, 127, 128, 300, 16384, rng.randrange(0, 2**21)])
        ln = rng.choice([0, 1, 2, 5, 130, rng.randrange(0, 300)])
        out.append((tag, bytes(rng.randrange(256) for _ in range(ln))))
    return out


FAILS = []


def check(name, cond, detail=""):
    if not cond:
        FAILS.append(f"{name}: {detail}")


def expect_raises(name, mod, data, exc_name, **attrs):
    exc = getattr(mod, exc_name)
    try:
        mod.parse(data)
    except Exception as e:
        if not isinstance(e, exc):
            FAILS.append(f"{name}: expected {exc_name}, got {type(e).__name__}")
            return
        for k, v in attrs.items():
            got = getattr(e, k, None)
            if got != v:
                FAILS.append(f"{name}: {exc_name}.{k} expected {v}, got {got}")
        return
    FAILS.append(f"{name}: expected {exc_name}, nothing raised")


def main():
    mod = load()
    rng = random.Random(SEED)

    # --- happy paths, both length encodings, with and without checksum -------
    for fixed in (False, True):
        for csum in (False, True):
            for trial in range(6):
                recs = gen_records(rng, rng.randrange(0, 7))
                data = build(recs, fixed=fixed, checksum=csum)
                try:
                    got = mod.parse(data)
                except Exception as e:
                    FAILS.append(f"happy(fixed={fixed},csum={csum},t={trial}): raised {type(e).__name__}: {e}")
                    continue
                check(f"happy(fixed={fixed},csum={csum},t={trial})", got == recs,
                      f"expected {recs!r}, got {got!r}")

    # --- header errors, and their precedence --------------------------------
    expect_raises("bad magic", mod, b"XTLV\x01\x00\x00", "BadMagic")
    expect_raises("bad magic, same first byte", mod, b"RTLX\x01\x00\x00", "BadMagic")
    expect_raises("bad magic, last byte only", mod, b"RTLW\x01\x00\x00", "BadMagic")
    expect_raises("bad magic wins over checksum", mod,
                  b"XTLV" + build([(1, b"a")], checksum=True)[4:], "BadMagic")
    expect_raises("bad version", mod, build([], version=2), "BadVersion")
    expect_raises("reserved flag", mod, build([], flags=0b100), "ReservedFlag")
    expect_raises("reserved high flag", mod, build([], flags=0b10000000), "ReservedFlag")

    # --- checksum -----------------------------------------------------------
    good = bytearray(build([(7, b"payload")], checksum=True))
    good[-1] ^= 0xFF
    bad = bytes(good)
    expected = int.from_bytes(bad[-4:], "big")
    actual = zlib.crc32(bad[:-4]) & 0xFFFFFFFF
    expect_raises("checksum mismatch", mod, bad, "ChecksumMismatch",
                  expected=expected, actual=actual)

    # --- truncation: the discriminating cases -------------------------------
    # LEB128 length runs off the end -> offset at the varint start
    d = build([(1, b"abcd")])
    body = d[:8] + b"\x80"          # tag then a continuation byte with no follow-up
    expect_raises("truncated varint length", mod, body, "Truncated", offset=8)

    # fixed-width length truncated -> offset where the 4-byte field began
    d = build([(1, b"abcd")], fixed=True)
    expect_raises("truncated fixed length", mod, d[:9], "Truncated", offset=8)

    # value shorter than declared, fixed-width
    d = build([(1, b"abcdefgh")], fixed=True)
    expect_raises("truncated fixed value", mod, d[:-3], "Truncated", offset=12)

    # value shorter than declared, LEB128
    d = build([(1, b"abcdefgh")])
    expect_raises("truncated leb value", mod, d[:-3], "Truncated", offset=9)

    # off-by-one: value short by exactly one byte
    expect_raises("truncated by one byte", mod, d[:-1], "Truncated", offset=9)
    d = build([(1, b"abcdefgh")], fixed=True)
    expect_raises("truncated fixed by one byte", mod, d[:-1], "Truncated", offset=12)

    # header cut before flags
    expect_raises("truncated header", mod, b"RTLV\x01", "Truncated", offset=5)

    # --- structural edges ---------------------------------------------------
    check("zero-length value", mod.parse(build([(3, b"")])) == [(3, b"")])
    check("duplicate tags preserved",
          mod.parse(build([(5, b"a"), (5, b"b")])) == [(5, b"a"), (5, b"b")])
    check("empty container", mod.parse(build([])) == [])
    big = [(300, b"x" * 200)]
    check("multibyte tag and length", mod.parse(build(big)) == big)

    if FAILS:
        print(f"FAIL ({len(FAILS)} of many checks)")
        for f in FAILS[:12]:
            print("  -", f)
        sys.exit(1)
    print("PASS  seed=%d" % SEED)
    sys.exit(0)


if __name__ == "__main__":
    main()
