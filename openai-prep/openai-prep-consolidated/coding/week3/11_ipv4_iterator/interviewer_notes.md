# Interviewer Notes — IPv4 / CIDR Iterator

**Read this AFTER your timed attempt(s).** Reference solution, the bugs you'll hit, and how the (modified) OpenAI rubric scores throughput-mode work.

This problem's rubric is different from most OpenAI problems — see `## Rubric self-grade` below.

---

## Reference solution (full, both Part 5 branches)

```python
def ip_to_int(s: str) -> int:
    return int.from_bytes(bytes(int(o) for o in s.split('.')), 'big')


def int_to_ip(x: int) -> str:
    return '.'.join(str(b) for b in x.to_bytes(4, 'big'))


class IPV4Iterator:
    def __init__(
        self,
        ip_or_cidr: str,
        reverse: bool = False,
        step: int = 1,
    ) -> None:
        if step <= 0:
            raise ValueError("step must be positive")
        if '/' in ip_or_cidr:
            ip_str, prefix_str = ip_or_cidr.split('/')
            seed = ip_to_int(ip_str)
            host_bits = 32 - int(prefix_str)
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

    def __iter__(self) -> "IPV4Iterator":
        return self

    def __next__(self) -> str:
        if self.reverse:
            if self.current < self.min_ip:
                raise StopIteration
            result = int_to_ip(self.current)
            self.current -= self.step
        else:
            if self.current > self.max_ip:
                raise StopIteration
            result = int_to_ip(self.current)
            self.current += self.step
        return result

    def next_batch(self, size: int) -> list[str]:
        out = []
        for _ in range(size):
            try:
                out.append(next(self))
            except StopIteration:
                break
        return out

    # ---- Part 5A ----
    def contains(self, ip: str) -> bool:
        return self.min_ip <= ip_to_int(ip) <= self.max_ip

    # ---- Part 5B ----
    @staticmethod
    def to_cidrs(start_ip: str, end_ip: str) -> list[str]:
        start, end = ip_to_int(start_ip), ip_to_int(end_ip)
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

That's the complete class — ~50 lines including helpers. Total typing time at full muscle memory: **~6 minutes**.

---

## Why this is the shape it is

**1. Two helpers at the top.** `ip_to_int` and `int_to_ip` are not methods — they're module-level. Two reasons: (a) they're used in `to_cidrs` which is a `@staticmethod`, so it can't reach `self.ip_to_int`; (b) they're conceptually free-standing conversions, not iterator state.

**2. `__init__` branches on `'/'`, not on `isinstance` or regex.** Fastest to type, no false positives. If the spec ever broadened to accept IPv6 or hostnames, this would need rework — but the spec is IPv4 only, so the brittle parse is correct here.

**3. `current = seed` always.** Both the CIDR and bare branches set `self.current = ip_to_int(seed_string)`. This is the seed-IP rule the spec calls out. Don't reset to `min_ip` or `max_ip` based on direction — the spec says iteration starts at the *supplied* IP and walks toward the boundary.

**4. `min_ip` / `max_ip` are the iteration boundaries, NOT the emit cursor.** They're set once in `__init__` and never touched again. Direction is encoded in the `__next__` branch + the step sign, not in the bounds.

**5. `__next__` ordering: check → capture → advance.** Off-by-one is the #1 bug. The first call must return the *seed* (not seed ± step). So you capture `int_to_ip(self.current)` BEFORE advancing.

**6. `next_batch` reuses `__next__`.** Don't duplicate the bounds-check logic. The `try/except StopIteration` pattern is the canonical Python way to "consume up to N values from an iterator." Memorize it.

**7. `to_cidrs` is `@staticmethod`, not a free function.** The spec says it's on the class. Mechanically: it takes two string IPs, returns a list. No iterator state needed. Don't even instantiate an iterator inside it — pure int arithmetic.

---

## Common bugs (graded by how often candidates report them)

### Bug 1 — Off-by-one on broadcast (severity: high)

```python
self.max_ip = seed | mask
# WRONG: self.max_ip = seed | mask - 1     # excludes broadcast
# WRONG: self.max_ip = seed + (1 << host_bits)    # off by one (exclusive end)
```

The broadcast address is *inclusive*. Block size is `mask + 1 = 2^host_bits`, and the block spans `[network, broadcast]` both ends included.

Verify against /32: `mask=0`, network=broadcast=seed, block size 1. ✓
Verify against /31: `mask=1`, broadcast = network + 1, block size 2. ✓

### Bug 2 — Seed treated as network (severity: high, reported by spec)

```python
self.current = self.min_ip       # WRONG
self.current = seed              # CORRECT
```

`IPV4Iterator("10.0.0.13/29")` should yield `["10.0.0.13", "10.0.0.14", "10.0.0.15"]`, NOT `["10.0.0.8", ..., "10.0.0.15"]`.

The seed is wherever you "drop in" to the block. The iterator walks from there.

### Bug 3 — Advance before capture (severity: medium)

```python
def __next__(self):
    if self.current > self.max_ip:
        raise StopIteration
    self.current += self.step                 # WRONG: advances first
    return int_to_ip(self.current)            # WRONG: returns wrong value

# CORRECT:
def __next__(self):
    if self.current > self.max_ip:
        raise StopIteration
    result = int_to_ip(self.current)
    self.current += self.step
    return result
```

First call to `next(IPV4Iterator("10.0.0.5"))` must return `"10.0.0.5"`, not `"10.0.0.6"`.

### Bug 4 — Reverse bounds check uses `> max_ip` (severity: medium)

```python
def __next__(self):
    if self.current > self.max_ip:        # WRONG for reverse
        raise StopIteration
    ...
```

Reverse walks DOWN. It should stop when `current < min_ip`, not when `current > max_ip`. Easy slip if you copy-paste from the forward branch and forget to flip the comparison.

### Bug 5 — String-space octet arithmetic (severity: high, reported by spec)

```python
# WRONG — manipulating octet strings:
def next_ip(ip_str):
    a, b, c, d = ip_str.split('.')
    d = str(int(d) + 1)
    if int(d) > 255:
        d = '0'
        c = str(int(c) + 1)
        if int(c) > 255:
            c = '0'
            b = str(int(b) + 1)
            ...   # forgets one of the cases
    return '.'.join([a, b, c, d])
```

Every candidate who tries this gets at least one carry wrong. **Convert to int, do `+1`, convert back.** It's literally one line each direction.

### Bug 6 — `to_cidrs` misses `start == 0` (severity: low, only Part 5B)

```python
align = start & -start            # WRONG when start == 0: gives 0
align = start & -start if start > 0 else (1 << 32)   # CORRECT
```

`0 & -0 == 0`, but the alignment ceiling at IP 0 is the full 2^32. Without this guard, the loop infinite-loops on inputs starting at 0.0.0.0.

### Bug 7 — `next_batch` raises instead of returning empty (severity: low)

```python
def next_batch(self, size):
    return [next(self) for _ in range(size)]    # WRONG: raises on boundary
```

Spec says: "Empty list means the iterator is exhausted." Don't let `StopIteration` propagate out — catch it and stop early.

---

## Rubric self-grade — throughput edition

This problem's rubric is unusual. The interviewer note is explicit: *"engineering excellence doesn't matter — comments, edge case planning, all of it is wasted time."*

| Axis | What earns signal | What loses signal |
|------|------------------|-------------------|
| **Skeleton speed** | Class + iter/next + ip↔int helpers in <3 minutes. | Still designing data structures at minute 8. |
| **Int-space discipline** | Convert at the boundary, arithmetic in int. | Octet-string manipulation; rollover bugs. |
| **API evolution** | `step: int = 1` added with default — old tests still pass. | Breaks Part 1 tests when Part 2 lands. |
| **Tests-first debug** | Reads failure output, fixes, reruns. <2 min per bug. | Re-derives spec from scratch each time. |
| **CIDR math** | `mask = (1 << host_bits) - 1`, broadcast inclusive, seed != network. | Off-by-one on broadcast; seed=network mistake. |
| **Part 5 throughput** | Either branch done in <15 min once revealed. | Stalls on `x & -x` or interval logic. |

**What this rubric does NOT reward:**
- Docstrings, type hints beyond the signature, comments.
- Explaining trade-offs out loud during the round.
- Edge-case planning before writing code.
- Pretty code organization.

**A passing attempt** clears Parts 1-4 with time to spare for Part 5. A great attempt also lands Part 5 with the interviewer asking "what if we added IPv6?" or a similar follow-up.

---

## Honest weaknesses to acknowledge

After your attempt, look over the reference and your code. Likely gaps:

1. **You probably typed the `__next__` body twice** — once for forward, once for reverse. The reference does this too. Don't try to deduplicate during the interview; the if/else branch is faster to type than a clever helper.

2. **You may have used bit shifts** (`(a << 24) | (b << 16) | ...`) instead of `int.from_bytes`. Both work. The `from_bytes` version is harder to typo. Pick one and never switch.

3. **You probably didn't handle `step=0` or `step<0`** until a test failed. That's fine in throughput mode — adding the `ValueError` is 3 lines.

4. **For Part 5B, you may have written `range_to_cidrs` as a free function** and not made it a `@staticmethod`. The tests catch this, but it's worth knowing the convention: methods that don't need `self` go in `@staticmethod`, especially when the spec puts them on the class.

5. **You may have computed prefix from `int(math.log2(size))`.** Works, but adds a `math` import. `33 - size.bit_length()` is one line shorter and avoids float roundoff.

---

## Follow-up sketches with code

Picking the most likely interview follow-ups after Parts 1-5:

### Follow-up A — `overlaps`

```python
def overlaps(self, other: "IPV4Iterator") -> bool:
    return not (self.max_ip < other.min_ip or other.max_ip < self.min_ip)
```

Two-line interval overlap. State the formula: "two intervals overlap iff neither is strictly to the left of the other."

### Follow-up B — Iterator-as-generator

```python
def iter_ips(ip_or_cidr: str, reverse=False, step=1):
    if step <= 0:
        raise ValueError
    # ... same __init__ logic to get min_ip, max_ip, current
    while min_ip <= current <= max_ip:
        yield int_to_ip(current)
        current += -step if reverse else step
```

Mention this as an alternative design. Don't switch in the middle of an attempt — the class form is what the spec asks for, and `next_batch` is easier to attach to a class than a generator.

### Follow-up C — IPv6 generalization

Change the integer width:
- `0xFFFFFFFF` → `(1 << 128) - 1`
- `to_bytes(4, 'big')` → `to_bytes(16, 'big')`
- Parsing the hex-with-`::`-compression is the main new work.

The iteration logic is identical. State this as a "the algorithm is unchanged, only the parser changes" answer.

### Follow-up D — Skip-ahead

```python
def advance(self, n: int) -> None:
    delta = n * self.step * (-1 if self.reverse else 1)
    self.current += delta
```

One line. Useful for checkpoint/resume.

### Follow-up E — Length without consuming

```python
def remaining(self) -> int:
    if self.reverse:
        if self.current < self.min_ip:
            return 0
        return (self.current - self.min_ip) // self.step + 1
    if self.current > self.max_ip:
        return 0
    return (self.max_ip - self.current) // self.step + 1
```

Integer arithmetic on the bounds. The `// step + 1` handles the inclusive-endpoint count.

---

## Common mistakes interviewers see (collected from candidate reports)

1. **Stalling on the iterator protocol.** Candidates without recent Python practice forget that `__iter__` returns `self` and that `__next__` raises `StopIteration` (not returns `None`). Drill this until automatic.

2. **Mis-parsing the CIDR string.** `split('/')` and `int(prefix_str)` are the whole story. Don't reach for `re`.

3. **Hand-rolling `next_batch` with explicit bounds checks** instead of delegating to `next(self)`. Doubles the code surface and introduces drift.

4. **Asking for hints.** In a throughput-mode interview, asking "should `next_batch` raise or return empty?" wastes 30 seconds you don't have. Pick the most reasonable answer (return empty) and move on. The tests will tell you if you guessed wrong.

5. **Reading every test before coding.** The progressive reveal means you only see Part N's tests when Part N-1 passes. Don't over-prepare; read the current part, code, run, iterate.

---

## When to use this problem in practice

This is an interview problem — but the patterns (iterator class, int-space arithmetic, CIDR math) are real production patterns. If you ever build:

- A network scanning tool — iterate over a CIDR block.
- A firewall rule engine — interval overlap and containment.
- An IP allocator — `to_cidrs` for "carve up a range into CIDR blocks."

These exact functions show up. The throughput interview style is artificial, but the algorithms aren't.
