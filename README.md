# Eval task sample: RTLV container parser

A self-contained evaluation task for coding agents, in the shape I build them:
a pinned container, a written spec, and a deterministic verifier that decides
pass or fail without a model in the loop.

**This task is written from scratch for public sharing.** It is not adapted from
any task authored under a benchmark programme.

## What this task tests

Binary-format parsing against a written spec, with the difficulty concentrated
where agents actually fail:

- **Variable-length integer decoding** (LEB128) with multi-byte continuation
- **A format branch** that changes the encoding of every length field
- **Error discrimination** — five distinct failure modes that must raise five
  distinct exceptions, not one generic error
- **Truncation handling** at four different offsets
- **Checksum validation** over a byte range the spec defines precisely

The spec is complete and unambiguous. An agent that fails does so because it
missed a branch, not because the problem was vague.

## Why a frontier agent should fail it

The bar I hold tasks to: a frontier coding agent should fail more often than it
passes, and fail for a legitimate reason.

The intended failure is the interaction between the `LENGTHS_FIXED` flag and
truncation detection. When lengths are fixed-width, a truncated record is
detectable before reading the payload; when they are LEB128, it is not detectable
until the varint itself runs off the end. Most implementations handle one and
raise the wrong exception for the other.

## Why the verifier cannot be gamed

- Test vectors are **generated at verification time from a seed**, not shipped.
  Hardcoding outputs fails.
- The verifier checks **exception type and offset**, not just the happy path.
- A reference solution is included, and the verifier is **mutation-tested against
  deliberately broken variants** of it (`tests/test_verifier.py`). A verifier that
  passes a broken solution is a broken verifier.

## Layout

```
task.md                 the prompt as an agent receives it
spec.md                 the format specification
Dockerfile              pinned environment
verify.py               deterministic verifier
solution/solve.py       reference solution
tests/test_verifier.py  mutation tests for the verifier itself
```

## Running it

```bash
docker build -t rtlv-task .
docker run --rm rtlv-task            # verifies the reference solution
docker run --rm rtlv-task mutations  # runs the verifier's own mutation tests
```

Or directly, standard library only, no dependencies:

```bash
python verify.py              # PASS  seed=20260908
python tests/test_verifier.py # PASS: all 10 mutations killed
```

## What the mutation tests actually caught

Writing this sample, the first version of the verifier let **two** mutations through:

- `off-by-one truncation bound` — a value short by exactly one byte passed, because
  every truncation test cut three bytes
- `magic check prefix-only` — a parser checking only the first byte passed, because
  the bad-magic vector was `XTLV`, which differs at byte 0

Both are the kind of gap that makes a task look solved when it is not. They were
found by testing the grader, not the solution. The fix added `RTLX` and `RTLW`
vectors and one-byte truncation cases. All 10 mutations are now killed.

That sequence is the point of this sample.

## The verifier-first habit

Roughly 2.5 lines of verifier code per line of reference solution, which is
typical for tasks of this shape. The verifier is written before the solution and
tested against broken solutions before it is trusted. If a grader still passes a
deliberately broken implementation, the grader is the bug.
