# Prereqs — IPv4 / CIDR Iterator

**This is a throughput interview.** The note attached to the problem is explicit: *"engineering excellence doesn't matter — comments, edge case planning, all of it is wasted time. Make the code work + debug fast."* 55 min, 5 parts revealed one at a time. The next part only unlocks when the previous one passes its tests.

That changes how you prep. The bar is **muscle memory on the skeleton**, not architectural taste. If you stop to think about the iterator protocol mid-attempt, you've already lost.

Estimated prep time: 45-60 min if you've already done LC 751. The math is identical; what's new is the iterator class wrapper and the throughput cadence.

**Two things to internalize before you attempt:**
1. The `__iter__` / `__next__` skeleton, with all four parts wrapped around it.
2. The two-line `ip_to_int` / `int_to_ip` pair — typed without thinking.

---

## Concept 1: The iterator protocol in CPython

**What you're learning:** the exact bytes Python expects from an "iterator," so you can write a class that works with `for x in obj` and `next(obj)`.

**The protocol — two methods, that's it:**

```python
class Foo:
    def __iter__(self):
        return self          # iterators return themselves

    def __next__(self):
        if <done>:
            raise StopIteration
        # compute next value, advance state, return value
```

That's the whole spec. CPython's `for` loop is:
```python
it = iter(obj)               # calls obj.__iter__()
while True:
    try:
        x = next(it)         # calls it.__next__()
    except StopIteration:
        break
    # body
```

**Iterable vs iterator** — both can show up:
- **Iterable**: has `__iter__` that returns a *fresh* iterator each call. Lists are iterables (`iter([1,2,3])` returns a new iterator every call).
- **Iterator**: has `__iter__` that returns `self`, and `__next__` that advances. One-shot — exhaust it and it's done.

For this problem you want an **iterator** (state lives on the object; one-shot is fine). The signatures in the spec confirm this — `__iter__` returns `'IPV4Iterator'`, i.e., self.

**`__next__` ordering — burn this in:**

```python
def __next__(self):
    if <out of bounds>:           # 1. check FIRST
        raise StopIteration
    result = int_to_ip(self.current)   # 2. capture current value
    self.current += self.step          # 3. advance AFTER
    return result
```

Off-by-one bugs come from advancing first. The first call should return the *starting* IP, then advance — not advance, then return.

**Done when:** you can type the 6-line skeleton from a blank screen in under 30 seconds.

---

## Concept 2: IP ↔ int conversion (drill the one-liner)

**What you're learning:** convert dotted-quad strings to/from 32-bit integers using `int.from_bytes` / `int.to_bytes`. Memorize these two lines — they're your first two lines on every IP problem.

```python
def ip_to_int(s: str) -> int:
    return int.from_bytes(bytes(int(o) for o in s.split('.')), 'big')

def int_to_ip(x: int) -> str:
    return '.'.join(str(b) for b in x.to_bytes(4, 'big'))
```

**Why these, not bit shifts:**

Bit shifts work and many references use them:
```python
def ip_to_int(s):
    a, b, c, d = map(int, s.split('.'))
    return (a << 24) | (b << 16) | (c << 8) | d
```

Both are correct. The `to_bytes` / `from_bytes` versions are slightly less to type and harder to typo (no operator-precedence mistakes). Pick one and drill it. Don't context-switch mid-interview.

**Why integer space, not string manipulation:**

The #1 reported bug on this problem is the **carry/rollover error**. When you add 1 to `192.168.0.255`, the .255 octet rolls to .0 and carries into the .0 octet → `192.168.1.0`. Doing this in string space requires four nested checks. In integer space it's literally `+1` — the carry happens for free.

```python
ip_to_int("192.168.0.255") + 1 == ip_to_int("192.168.1.0")   # True
```

Whenever you're tempted to manipulate octets as strings: stop. Convert to int, do the arithmetic, convert back.

**Done when:** you can type both helpers in under 20 seconds, and you instinctively reach for them on any IP problem.

---

## Concept 3: CIDR math (the mask formula)

**What you're learning:** how to compute the bounds of a CIDR block from `a.b.c.d/prefix`.

**The four-line ritual:**

```python
host_bits = 32 - prefix              # number of variable bits
mask = (1 << host_bits) - 1          # low host_bits set, rest zero
network = seed_ip & ~mask            # zero out the host bits
broadcast = seed_ip | mask           # set all host bits to 1
```

Block size = `mask + 1 = 2 ** host_bits`. Block = `[network, broadcast]`, inclusive both ends.

**Sanity check it against /32 and /31:**

| prefix | host_bits | mask | block size | example for seed=192.168.0.5 |
|--------|-----------|------|------------|------------------------------|
| /32    | 0         | 0    | 1          | [192.168.0.5, 192.168.0.5]   |
| /31    | 1         | 1    | 2          | [192.168.0.4, 192.168.0.5]   |
| /30    | 2         | 3    | 4          | [192.168.0.4, 192.168.0.7]   |
| /24    | 8         | 255  | 256        | [192.168.0.0, 192.168.0.255] |
| /0     | 32        | 2^32-1 | 2^32     | [0.0.0.0, 255.255.255.255]   |

Notice /31 with seed=192.168.0.5: the network is .4, not .5. **The seed is NOT necessarily the network address** — the spec calls this out, and the test cases will hit it.

**The seed-IP trap (Part 3):**

```python
# In Part 3, `current` starts at the SEED, not the network.
self.current = seed                  # ← NOT self.min_ip
self.min_ip = seed & ~mask
self.max_ip = seed | mask
```

Iteration walks from the seed outward (forward to broadcast; reverse to network). Setting `current = min_ip` is a real mistake reported in the spec.

**Python signed-int gotcha:**

`~mask` in Python is signed. For `mask = 0`, `~mask = -1` (all bits set in 2's-complement, ad infinitum). When you AND with a 32-bit value, this is fine — the high bits get masked off. If you ever need a clean 32-bit value (e.g., to compare to `0xFFFFFFFF`), do `& 0xFFFFFFFF`.

```python
~mask & 0xFFFFFFFF    # explicit 32-bit
```

Not strictly required for this problem, but if you see `-1` show up in a debug print, this is why.

**Done when:** you can write `mask`, `network`, `broadcast` from memory and verify the four /32, /31, /30, /24 cases without running code.

---

## Concept 4: Lowbit (`x & -x`) — for Part 5 only

**What you're learning:** isolating the lowest set bit of an integer. Pulled in if Part 5 is the IP-range-to-CIDR decomposition (LC 751 territory).

```python
x & -x   # power-of-2 value of the lowest set bit
```

Why it works: in two's-complement, `-x = ~x + 1`. The `+1` flips all the trailing zeros and the lowest 1 of `x`; everywhere else, `x` and `-x` disagree. So `x & -x` retains exactly that one bit.

```
x      = 0b...01011000
-x     = 0b...10101000
x & -x = 0b...00001000   ← lowest set bit
```

**Why it matters for CIDR**: the lowest set bit of an IP tells you the **largest aligned CIDR block size that can start at that IP**. An IP ending in `...1000` (binary) can start any block up to size 8 (/29). An IP ending in `...0001` can only start a /32.

**The IP-range → CIDR decomposition** (Part 5 candidate):

Given `[start, end]`, emit the minimum list of CIDR blocks:
```python
def range_to_cidrs(start: int, end: int) -> list[str]:
    out = []
    while start <= end:
        max_aligned = start & -start if start > 0 else (1 << 32)
        max_fits = 1 << ((end - start + 1).bit_length() - 1)
        size = min(max_aligned, max_fits)
        prefix = 32 - size.bit_length() + 1   # log2(size) → suffix
        out.append(f"{int_to_ip(start)}/{prefix}")
        start += size
    return out
```

The two constraints:
- `start & -start` — alignment (largest block that can START at `start`).
- `largest pow2 ≤ remaining` — don't overshoot the range.

Take the smaller. Emit. Advance. Repeat. Greedy is provably optimal here because emitting the largest block at each step monotonically improves both alignment (start gets more trailing zeros) and remaining count.

**The `start == 0` edge case**: `0 & -0 == 0`, but the alignment at IP 0 allows any block size. Handle this explicitly (cap at `1 << 32`).

**Done when:** you can articulate "lowbit = alignment ceiling" and write the decomposition loop from a 1-line hint.

---

## Concept 5: The throughput mindset (this is unique to this problem)

The interviewer note for this problem reads: *"engineering excellence doesn't matter — comments, edge case planning, all of it is wasted time. Make the code work + debug fast."*

This is **not** the OpenAI Applied-Foundations bar that other problems test. This particular question is a high-pressure phone screen optimizing for **raw typing throughput and tight feedback loops**. The signal is: can you absorb a new requirement, extend a working class, and pass the new tests in 8-12 minutes?

**What this means for prep:**

| Normal mode | Throughput mode |
|-------------|-----------------|
| State edge cases up front | Skip — the tests will reveal them |
| Docstrings for each method | None |
| Helper functions for clarity | Inline if it's <5 lines |
| Type hints | Keep the ones in the signature; don't add internals |
| Comments explaining intent | None |
| Plan the data structures | Write the skeleton from muscle memory |

**What to STILL do:**
- Get `__init__` parameters right the first time. The spec says signatures stay backwards-compatible across parts. Adding `step: int = 1` in Part 4 is fine — it has a default.
- Read the test file before coding each part. The tests tell you the exact corner cases. Don't guess.
- Run tests after every part. Don't write all 4 parts then test — that's a debugging nightmare.

**Cadence target:**
- Part 1: 5 min
- Part 2: 3 min (it's a flag + branch)
- Part 3: 8 min (CIDR parsing + bounds)
- Part 4: 5 min (step + batch helper)
- Part 5: 15-20 min (whichever branch — containment is easy, decomposition is the lowbit drill)

That leaves ~10 min of debug margin across all 5 parts. Realistic if the skeleton is automatic.

---

## Recall templates — type these from a blank screen

If you can type these three cold in <2 minutes total, you're ready.

**1. IP ↔ int** (always lines 1-2):
```python
def ip_to_int(s): return int.from_bytes(bytes(int(o) for o in s.split('.')), 'big')
def int_to_ip(x): return '.'.join(str(b) for b in x.to_bytes(4, 'big'))
```

**2. Iterator skeleton:**
```python
class IPV4Iterator:
    def __init__(self, ip_or_cidr, reverse=False, step=1):
        if step <= 0:
            raise ValueError("step must be positive")
        if '/' in ip_or_cidr:
            ip_str, p = ip_or_cidr.split('/')
            seed = ip_to_int(ip_str)
            host_bits = 32 - int(p)
            mask = (1 << host_bits) - 1
            self.min_ip = seed & ~mask
            self.max_ip = seed | mask
            self.current = seed
        else:
            self.current = ip_to_int(ip_or_cidr)
            self.min_ip = 0
            self.max_ip = 0xFFFFFFFF
        self.reverse = reverse
        self.step = step

    def __iter__(self):
        return self

    def __next__(self):
        if self.reverse:
            if self.current < self.min_ip:
                raise StopIteration
            r = int_to_ip(self.current)
            self.current -= self.step
        else:
            if self.current > self.max_ip:
                raise StopIteration
            r = int_to_ip(self.current)
            self.current += self.step
        return r

    def next_batch(self, size):
        out = []
        for _ in range(size):
            try:
                out.append(next(self))
            except StopIteration:
                break
        return out
```

**3. CIDR decomposition (Part 5 contingency):**
```python
def range_to_cidrs(start, end):
    out = []
    while start <= end:
        align = start & -start if start > 0 else (1 << 32)
        fits = 1 << ((end - start + 1).bit_length() - 1)
        size = min(align, fits)
        prefix = 33 - size.bit_length()
        out.append(f"{int_to_ip(start)}/{prefix}")
        start += size
    return out
```

---

## Suggested schedule

| Session | What |
|---------|------|
| Session 1 (30 min) | Read this doc. Type templates 1 & 2 from a blank screen 3x. |
| Session 2 (45 min) | Cold attempt Parts 1-3 under timer. Run tests after each part. |
| Session 3 (30 min) | Cold attempt Part 4. Then attempt Part 5 *containment* branch. |
| Session 4 (30 min) | Cold attempt Part 5 *decomposition* branch (LC 751 wrapped in the class). |
| Session 5 (20 min) | Read `interviewer_notes.md`. Re-type the full class once from scratch. |

## How to use Claude Code during this

- "type the iterator skeleton, I want to compare" — only after your own attempt.
- "what's the bug in my __next__?" — paste your code.
- "explain why `x & -x` gives the lowest set bit" — if you're shaky on the bit trick.
- "drill me on /31 vs /32 vs /30 edge cases" — for the CIDR math.

Don't ask Claude to write the full class for you before your first attempt. The muscle is in typing the skeleton from memory under time pressure.

## When you're ready

When you can type templates 1 and 2 from a blank screen in under 2 minutes, set a **40-min timer** and open `problem.md`. Aim to clear Parts 1-3 in that window. Then `review mode` and post-mortem.
