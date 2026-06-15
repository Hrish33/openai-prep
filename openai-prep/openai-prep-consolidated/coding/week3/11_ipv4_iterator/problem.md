# Problem 11: IPv4 / CIDR Iterator (5-part)

**Prereqs:** Skim `00_prereqs.md` if you haven't internalized the `__iter__`/`__next__` skeleton and the IP↔int helpers.

**Time budget:** 55 min total (the real OpenAI cap). Hard stop enforced.
**Source:** OpenAI phone screen, last seen 2026-05-15. Frequency: medium.
**Stage:** Phone screen. Throughput-optimized — see "Interview format" below.

## Interview format

Parts are revealed **one at a time**. The next part only unlocks when the previous part's tests fully pass. You don't get to see Part 2 until Part 1 is green.

**Throughput mode**: the interviewer has stated explicitly that engineering excellence does not matter for this question. No comments. No docstrings. No edge-case planning. Just make it work and debug fast.

This is unusual for OpenAI's bar — most of their questions reward edge-case discipline. This one rewards typing speed and tight feedback loops. Treat it as a different game.

---

## The progressive problem

You're building one class, `IPV4Iterator`, that gets extended across parts. The `__init__` signature grows but stays backwards-compatible (new params have defaults).

### Part 1 — Bare IPv4, forward iteration

```python
class IPV4Iterator:
    def __init__(self, ip_or_cidr: str) -> None: ...
    def __iter__(self) -> "IPV4Iterator": ...
    def __next__(self) -> str: ...
```

Given a bare dotted-quad IP string like `"192.168.0.5"`, iterate forward through every IP address up to and including `255.255.255.255`, then raise `StopIteration`.

```python
it = IPV4Iterator("192.168.0.254")
next(it)   # "192.168.0.254"
next(it)   # "192.168.0.255"
next(it)   # "192.168.1.0"        ← rollover into next /24
next(it)   # "192.168.1.1"
```

**Corner cases:**
- Start at `"0.0.0.0"` — first `next()` returns `"0.0.0.0"`, then advances.
- Start at `"255.255.255.255"` — first `next()` returns it, second `next()` raises `StopIteration`.
- Rollover `"192.168.0.255"` → `"192.168.1.0"` is one `+1` in int space.

---

### Part 2 — Reverse mode

```python
class IPV4Iterator:
    def __init__(self, ip_or_cidr: str, reverse: bool = False) -> None: ...
```

Add `reverse: bool = False`. When `True`, walk backwards down to `"0.0.0.0"` and then `StopIteration`.

```python
it = IPV4Iterator("192.168.1.1", reverse=True)
next(it)   # "192.168.1.1"
next(it)   # "192.168.1.0"
next(it)   # "192.168.0.255"     ← underflow into previous /24
```

**Corner cases:**
- Start at `"0.0.0.0"` with `reverse=True` — first `next()` returns it, second raises `StopIteration`.
- Start at `"255.255.255.255"` with `reverse=True` — walks down toward zero.
- Underflow `"192.168.1.0"` → `"192.168.0.255"` in reverse.

---

### Part 3 — CIDR form

```python
class IPV4Iterator:
    def __init__(self, ip_or_cidr: str, reverse: bool = False) -> None: ...
```

Same signature; the input string may now be `"a.b.c.d/prefix"`. When CIDR notation is given, restrict iteration to the block `[network, broadcast]` where:
- `network = seed & ~mask` (mask = `(1 << (32-prefix)) - 1`)
- `broadcast = seed | mask`

Iteration starts at the **supplied seed** (which need not equal the network address) and walks within the block. Forward stops at `broadcast` (inclusive); reverse stops at `network` (inclusive).

```python
it = IPV4Iterator("192.168.0.5/30")     # block = [192.168.0.4, 192.168.0.7]
list(it)
# ["192.168.0.5", "192.168.0.6", "192.168.0.7"]   ← starts at seed, not network

it = IPV4Iterator("192.168.0.5/30", reverse=True)
list(it)
# ["192.168.0.5", "192.168.0.4"]
```

**Corner cases:**
- `/32` — block is exactly one IP (the seed). `next()` returns it, then `StopIteration`.
- `/31` — block is exactly two IPs.
- `/0` — block is all 2^32 IPs.
- Seed != network — e.g., `"10.0.0.13/29"` → block is `[10.0.0.8, 10.0.0.15]`, iteration starts at `.13`.

---

### Part 4 — `step` and `next_batch`

```python
class IPV4Iterator:
    def __init__(
        self,
        ip_or_cidr: str,
        reverse: bool = False,
        step: int = 1,
    ) -> None: ...

    def next_batch(self, size: int) -> list[str]: ...
```

Two throughput knobs:

1. **`step`** is the integer advance per `__next__` call. Default `1` reproduces Parts 1-3. With `reverse=True`, walk `-step` per call. Raise `ValueError` if `step <= 0`.

2. **`next_batch(size)`** returns up to `size` IPs from the current cursor, stopping early at the same `StopIteration` boundary. Returns `[]` when the iterator is exhausted.

```python
it = IPV4Iterator("0.0.0.0", step=4)
next(it)   # "0.0.0.0"
next(it)   # "0.0.0.4"
next(it)   # "0.0.0.8"

it = IPV4Iterator("192.168.0.0/24", step=64)
it.next_batch(10)   # ["192.168.0.0", "192.168.0.64", "192.168.0.128", "192.168.0.192"]
                    # (stops early — only 4 IPs at step=64 in this /24)
```

**Corner cases:**
- `step <= 0` raises `ValueError`.
- `step` may exceed the block size (returns one IP then exhausts).
- `next_batch(0)` returns `[]`.
- `next_batch` after exhaustion returns `[]` (doesn't raise).

---

### Part 5 — branches (interviewer picks one)

Candidates have reported two distinct Part 5 reveals. Drill both; you don't know which you'll get.

#### Part 5A — Containment

```python
class IPV4Iterator:
    def contains(self, ip: str) -> bool: ...
```

Return `True` iff `ip` is within the iterator's configured **bounds** — i.e., `min_ip <= ip_int <= max_ip`. Direction-agnostic (forward and reverse share the same bounds).

- **Bare-IP**: bounds are `[0, 0xFFFFFFFF]` — every IPv4 address. Trivially True for any well-formed input. (The useful case is CIDR.)
- **CIDR**: bounds are `[network, broadcast]` — the configured block.

```python
it = IPV4Iterator("10.0.0.13/29")
it.contains("10.0.0.7")    # False — block is [10.0.0.8, 10.0.0.15]
it.contains("10.0.0.8")    # True (network is inclusive)
it.contains("10.0.0.15")   # True (broadcast is inclusive)
it.contains("10.0.0.16")   # False
```

The implementation is two lines once you've stored `min_ip` and `max_ip` correctly in Part 3 (the block bounds, not the emit cursor). The signal is whether you set those during `__init__`.

#### Part 5B — IP range → CIDR decomposition (LC 751)

```python
@staticmethod
def to_cidrs(start_ip: str, end_ip: str) -> list[str]:
    """Decompose the inclusive range [start_ip, end_ip] into the
    minimum list of CIDR blocks that exactly covers it."""
```

Given two IPs, return the **minimum-length list of CIDR blocks** whose union equals `[start_ip, end_ip]` exactly. This is LC 751 wearing different clothes.

```python
IPV4Iterator.to_cidrs("192.168.0.0", "192.168.0.9")
# ["192.168.0.0/29", "192.168.0.8/31"]
#  ↑ covers 0-7        ↑ covers 8-9
```

**The greedy:** at each step, emit the largest CIDR block that
1. starts at the current position (alignment constraint: `start & -start`)
2. doesn't overshoot the remaining range (size constraint: largest power of 2 ≤ remaining count)

Take the smaller, emit it, advance, repeat.

---

## Required API (final form after Part 4 or 5)

```python
class IPV4Iterator:
    def __init__(
        self,
        ip_or_cidr: str,
        reverse: bool = False,
        step: int = 1,
    ) -> None: ...

    def __iter__(self) -> "IPV4Iterator": ...
    def __next__(self) -> str: ...
    def next_batch(self, size: int) -> list[str]: ...

    # Part 5A:
    def contains(self, ip: str) -> bool: ...

    # Part 5B:
    @staticmethod
    def to_cidrs(start_ip: str, end_ip: str) -> list[str]: ...
```

---

## What an OpenAI interviewer is looking for (throughput edition)

**Different rubric than usual.** This problem optimizes for:

1. **Speed of skeleton.** First 90 seconds: you should have the class declared, `ip_to_int`/`int_to_ip` helpers written, and `__iter__` returning `self`. If you're still designing data structures at minute 5, you've lost the round.

2. **Working in int space, not string space.** The spec calls this out: string manipulation approaches get the rollover/underflow wrong. Convert once at the boundary, do arithmetic in int.

3. **Backwards-compatible signature evolution.** Each new part adds a parameter with a default. Adding `reverse: bool = False` in Part 2 must not break Part 1's tests. Same for `step` in Part 4.

4. **Tests-first debugging.** When a test fails, read the failure, fix the code, re-run. Don't reason from first principles about the spec when the test output is right there.

5. **CIDR boundary correctness.** Off-by-one on `broadcast = network + 2^(32-prefix) - 1` is the most common bug. The block is inclusive on both ends.

6. **`Seed != network` awareness** (Part 3). The iterator starts at the supplied IP, not the network address. Reported as a real candidate trap.

**What you do NOT get credit for in this format:**
- Docstrings, comments, or design discussion.
- Pre-computing edge case lists before coding.
- "Beautiful" code organization. One class, methods inline, ship it.

## Follow-ups (Part 5 candidates and beyond — don't peek until base works)

<details>
<summary>Click to expand</summary>

1. **Containment with overlap** (extension of Part 5A): `def overlaps(self, other: "IPV4Iterator") -> bool` — true iff the two configured ranges share any IP. Two-line int-interval check: `not (a.max_ip < b.min_ip or b.max_ip < a.min_ip)`.

2. **CIDR decomposition — multiple ranges** (extension of Part 5B): given a list of `[start, end]` ranges, return the minimum CIDRs covering their union. Sort + merge intervals first, then decompose each.

3. **`__len__` for CIDR iterators**: number of IPs remaining from current position to the boundary, honoring reverse and step. Useful for batch sizing without consuming.

4. **`peek()` method** that returns the next IP without advancing. Trivial — return `int_to_ip(self.current)` after the bounds check.

5. **Skip-ahead by N**: `def advance(self, n: int) -> None` — jump forward (or back, with reverse) without yielding. Useful for resuming an iterator from a checkpoint.

6. **IPv6 generalization**: same architecture, 128-bit integers instead of 32-bit. `int.from_bytes(..., 'big')` already handles this — but the dotted-quad string format changes to `xxxx:xxxx:...` colon-separated hex, with `::` zero-run compression. Mostly a parsing problem; the iteration is identical.

7. **Concurrency**: two threads call `next()` on the same iterator. Either add a `threading.Lock` around the `__next__` body (serializes), or document it as not thread-safe (the standard convention for Python iterators — `itertools` iterators are not thread-safe either).

8. **Generator-based alternative**: rewrite as a generator function instead of a class. Cleaner code but loses `next_batch` and `contains` — you'd need to wrap. Mention as a design alternative; don't switch mid-attempt.

9. **CIDR block aggregation**: given a list of CIDR blocks, merge any pair that's contiguous and aligned into a single larger block. E.g., `["10.0.0.0/25", "10.0.0.128/25"]` → `["10.0.0.0/24"]`. Inverse of Part 5B.

</details>

## Honest difficulty note

**Parts 1-4 are easy IF you've internalized the prereqs.** The class is ~30 lines. The hard part is *typing speed* and not getting tripped up by:
- The `+1`/`-1` direction in reverse mode (easy to flip)
- `current = seed` vs `current = network` in CIDR mode (off-by-one trap)
- The bounds check ordering in `__next__` (advance after, not before)
- `next_batch` calling `next(self)` and catching `StopIteration` (don't try to inline the bounds check — reuse `__next__`)

**Part 5 difficulty depends on the branch:**
- **5A (Containment)** is a 2-line method. ~5 minutes.
- **5B (Decomposition)** is LC 751. Hard if you haven't drilled `x & -x`. ~15-20 minutes if you have.

**A strong attempt covers:**
- Parts 1-3 cleared in <20 minutes total.
- Part 4 in <8 minutes.
- One of the Part 5 branches solid.
- ~10 minutes of buffer for the interviewer to probe with "what if N..." follow-ups on the last part.

**A failing attempt typically:**
- Stalls on string-space octet manipulation in Part 1.
- Gets the `seed != network` mistake in Part 3 and can't reconcile against the tests.
- Reaches Part 5 with <5 minutes remaining and panics.
