"""Mutation tests for the verifier itself.

A grader that passes a broken solution is a broken grader. Each mutation below
introduces one realistic defect into the reference solution; the verifier must
reject every one. If any mutation PASSES, the verifier has a blind spot.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REF = (ROOT / "solution" / "solve.py").read_text()

MUTATIONS = {
    "little-endian fixed length":
        ('int.from_bytes(view[i:i + 4], "big")', 'int.from_bytes(view[i:i + 4], "little")'),
    "checksum over whole buffer":
        ("zlib.crc32(data[:body_end])", "zlib.crc32(data)"),
    "off-by-one truncation bound":
        ("if i + length > len(view):", "if i + length > len(view) + 1:"),
    "truncated offset reports cursor not field start":
        ("raise Truncated(start)\n        if i - start >= 10", "raise Truncated(i)\n        if i - start >= 10"),
    "version check dropped":
        ("if data[4] != 1:", "if False:"),
    "reserved flags ignored":
        ("if flags & ~(LENGTHS_FIXED | HAS_CHECKSUM):", "if False:"),
    "checksum compared loosely":
        ("if expected != actual:", "if False:"),
    "varint shift not advanced":
        ("shift += 7", "shift += 0"),
    "magic check prefix-only":
        ('data[:4] != MAGIC', 'not data.startswith(b"R")'),
    "records dropped when count is zero-ish":
        ("for _ in range(count):", "for _ in range(max(0, count - 1)):"),
}


def run_with(source: str) -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "solution").mkdir()
        (d / "solution" / "solve.py").write_text(source)
        (d / "verify.py").write_text((ROOT / "verify.py").read_text())
        p = subprocess.run([sys.executable, "verify.py"], cwd=d,
                           capture_output=True, text=True, timeout=120)
        return p.returncode, (p.stdout + p.stderr).strip()


def main():
    rc, out = run_with(REF)
    if rc != 0:
        print("BROKEN: verifier rejects the reference solution")
        print(out)
        sys.exit(1)
    print("reference solution: PASS (as expected)\n")

    survivors = []
    for name, (old, new) in MUTATIONS.items():
        if old not in REF:
            print(f"  SKIP  {name}  (pattern not found — mutation is stale)")
            survivors.append(name + " [stale]")
            continue
        rc, out = run_with(REF.replace(old, new, 1))
        if rc == 0:
            print(f"  SURVIVED  {name}  <-- verifier blind spot")
            survivors.append(name)
        else:
            first = next((l.strip() for l in out.splitlines() if l.strip().startswith("-")), "")
            print(f"  killed    {name}  {first[:70]}")

    print()
    if survivors:
        print(f"FAIL: {len(survivors)} mutation(s) survived: {survivors}")
        sys.exit(1)
    print(f"PASS: all {len(MUTATIONS)} mutations killed. Verifier has no blind spot in this set.")
    sys.exit(0)


if __name__ == "__main__":
    main()
