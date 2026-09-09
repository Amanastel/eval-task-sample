# Task: implement an RTLV container parser

Implement `parse(data: bytes) -> list[tuple[int, bytes]]` in `solution/solve.py`.

Read `spec.md` for the format. Your parser must return the records in order as
`(tag, value)` pairs, and raise the exact exceptions the spec names.

Define the exceptions in `solution/solve.py` exactly as:

```python
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
```

Standard library only. No network access.

Success: `python verify.py` exits 0.
