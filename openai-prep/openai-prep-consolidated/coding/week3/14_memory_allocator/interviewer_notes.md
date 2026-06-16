# Interviewer notes — Memory Allocator

Read this **after** your attempt. Spoilers throughout.

---

## Reference solution — O(n) baseline (dump + sort + sweep)

The dumbest version that works. No bisect, no case analysis, no off-by-ones. The whole trick: when you free, dump the released blocks back into the free list and re-coalesce by **sorting + one-pass merge** (LC 56 Merge Intervals, verbatim).

```python
class Allocator:
    """Fixed-size allocator over `n` bytes, leftmost-first.

    Invariant after every op: `self.free` is sorted by start and coalesced
    (no two free blocks are address-adjacent).
    """

    def __init__(self, n: int) -> None:
        # (start, size) free blocks, sorted by start, coalesced.
        self.free = [(0, n)]
        # mID -> list of (start, size). One mID may own many blocks.
        self.alloc = {}

    def allocate(self, size: int, mID: int) -> int:
        # Scan free list left to right; carve from the first big-enough gap.
        # Either shrink the gap in place, or pop it entirely if it was an exact
        # fit. We never iterate past the mutation — the `return` exits first.
        for i, (start, gap) in enumerate(self.free):
            if gap >= size:
                if gap == size:
                    self.free.pop(i)
                else:
                    self.free[i] = (start + size, gap - size)
                if mID not in self.alloc:
                    self.alloc[mID] = []
                self.alloc[mID].append((start, size))
                return start
        return -1

    def freeMemory(self, mID: int) -> int:
        if mID not in self.alloc:
            return 0
        blocks = self.alloc.pop(mID)
        total = 0
        for _, size in blocks:
            total += size
        # Dump the released blocks back in, then re-coalesce in one sweep.
        self.free.extend(blocks)
        self.free.sort()
        merged = []
        for start, size in self.free:
            if merged and merged[-1][0] + merged[-1][1] == start:
                prev_start, prev_size = merged[-1]
                merged[-1] = (prev_start, prev_size + size)
            else:
                merged.append((start, size))
        self.free = merged
        return total
```

~30 lines, no helper, no case enumeration. Why this is the easiest:

- **No "four merge cases."** The sort + sweep handles all four implicitly. You can't get the merge logic wrong because there's no merge logic — just "are these two intervals back-to-back? combine them."
- **No `bisect_*` calls.** Stdlib `list.sort()` does the ordering work.
- **No insertion-point math.** No `while i < len(...) and ...`, no `i - 1` off-by-one.

Complexity: `allocate` is O(n) on the scan. `freeMemory` is O(n log n) on the sort. For an interview, that's fine — the optimization story is "let's get to O(log n) on free." Don't apologize for the sort.

> If you want to go **even dumber**, drop the free-block representation entirely and tag every byte with its owner: `self.mem = [0]*n`, where `0` means free. `allocate` scans for a run of `size` zeros and writes `mID` into those slots; `freeMemory` walks the array zeroing every cell that equals `mID`. No merge cases at all (free *is* zeroing), 20 lines total, O(n) per op. The interviewer will accept it as the brute force and immediately push you toward the free-block model — so prefer the sort+sweep version above as your real lead.

---

## Reference solution — O(log n) SortedDict-keyed-by-start

Swap the free container, keep everything else. The merge logic is identical in shape — only the neighbour-lookup primitive changes.

```python
from typing import Dict, List, Tuple
from sortedcontainers import SortedDict


class Allocator:
    def __init__(self, n: int) -> None:
        self.n = n
        self.free: SortedDict = SortedDict({0: n}) if n > 0 else SortedDict()
        self.alloc: Dict[int, List[Tuple[int, int]]] = {}

    def allocate(self, size: int, mID: int) -> int:
        if size <= 0:
            return -1
        # NOTE: still O(n) on the scan; see "Why is malloc still O(n)?" below.
        for start in list(self.free):
            gap = self.free[start]
            if gap >= size:
                del self.free[start]
                if gap > size:
                    self.free[start + size] = gap - size
                self.alloc.setdefault(mID, []).append((start, size))
                return start
        return -1

    def freeMemory(self, mID: int) -> int:
        blocks = self.alloc.pop(mID, [])
        total = 0
        for start, size in blocks:
            total += size
            self._insert_free(start, size)
        return total

    def _insert_free(self, start: int, size: int) -> None:
        end = start + size
        keys = self.free.keys()

        # Right neighbour: smallest free key >= start. If it equals `end`,
        # the freed block butts up against it — merge.
        ri = self.free.bisect_left(start)
        if ri < len(keys):
            right_start = keys[ri]
            if right_start == end:
                size += self.free.pop(right_start)

        # Left neighbour: largest free key < start. If left_start + left_size
        # equals `start`, they're adjacent — merge.
        li = self.free.bisect_left(start) - 1
        if li >= 0:
            left_start = keys[li]
            left_size = self.free[left_start]
            if left_start + left_size == start:
                start = left_start
                size += left_size
                del self.free[left_start]

        self.free[start] = size
```

Complexity (this version): `allocate` is still O(n) — the scan dominates. `free` is **O(log n)**: two `bisect_left` calls, two dict mutations. To make `allocate` O(log n) too, see the next section.

### Making `allocate` O(log n) — the size-index follow-up

Maintain a parallel `SortedList[(size, start)]`. Then `allocate(size)` becomes a `bisect_left((size, 0))` to find the smallest gap of ≥ size. The bookkeeping cost: every insert/delete to `self.free` now also touches the size index.

```python
from sortedcontainers import SortedDict, SortedList

class Allocator:
    def __init__(self, n: int) -> None:
        self.n = n
        self.free = SortedDict({0: n}) if n > 0 else SortedDict()
        # Mirror of self.free, indexed by (size, start) for best/first-fit.
        self.by_size: SortedList = SortedList([(n, 0)]) if n > 0 else SortedList()
        self.alloc = {}

    def _free_add(self, start, size):
        self.free[start] = size
        self.by_size.add((size, start))

    def _free_remove(self, start):
        size = self.free.pop(start)
        self.by_size.remove((size, start))
```

Now `allocate` is `O(log n)`: a `bisect_left((size, 0))` plus index removals. **Trade-off**: this gives you *best-fit* (smallest sufficient gap), not first-fit. LC 2502 specifies leftmost — strict first-fit. To preserve leftmost-fit with O(log n), you need a more involved structure (interval tree keyed by start, augmented with subtree max-size). This is usually the place where the interviewer says "good — sketch it but don't implement."

---

## Why this is the shape it is

### Why `dict[mID] -> list[block]` and not `dict[mID] -> block`?

LC 2502 says *"You may have several blocks with the same mID."* Same-mID stacking is what makes the canonical test case work:

```python
loc.allocate(1, 1) == 0   # mID=1 owns [0,1)
loc.allocate(1, 1) == 1   # mID=1 NOW owns [0,1) AND [1,2)
loc.freeMemory(1) == 3    # frees BOTH blocks (and a third from later)
```

A `dict[mID] -> tuple` would silently overwrite the first block's record, leak its bytes, and return the wrong count from `freeMemory`. The list is mandatory.

### Why coalesce eagerly?

Two reasons:

1. **Correctness of first-fit.** If you didn't coalesce, you could have free blocks `[(0,2), (2,3)]` and reject a request for 4 bytes — even though they're physically adjacent. The fragmentation test in the suite catches exactly this.
2. **Bounded structure size.** Without coalescing, the number of free blocks grows monotonically with allocate/free churn. Coalescing keeps the free-list size at most `O(live allocations)`.

The alternative — *lazy* coalescing, deferring merges until a request fails — exists in some production allocators (it amortizes nicely) but is harder to reason about and not what interviewers expect.

### Why is `malloc` still O(n) in the SortedDict version?

Because **leftmost-first** is what LC 2502 wants. SortedDict gives you O(log n) on keyed lookup — finding a specific address. It does *not* let you ask "give me the smallest key whose value is ≥ X" without scanning. To answer that in O(log n), you need a separate index keyed by value (size), or an augmented tree.

This is the natural follow-up the interviewer expects: "OK, free is O(log n). What about allocate? — Add a SortedList[(size, start)] mirror; best-fit becomes O(log n); preserving leftmost-first requires an interval tree."

### Why four merge cases, not "just merge whoever's adjacent"?

The four cases (none / left / right / both) aren't four code paths — they fall out of *two independent* checks:

```python
if right_neighbour_is_adjacent:
    merge_right
if left_neighbour_is_adjacent:
    merge_left
insert
```

That's it. Both checks fire independently → BOTH case. One check fires → LEFT or RIGHT. Neither fires → NONE. The "four cases" framing is for explaining the behaviour, not structuring the code.

Critically: do the **right merge before the left merge**, or do them in a way that doesn't change indices unexpectedly. The reference uses index `i` consistently and adjusts only after pops.

---

## Honest weaknesses to acknowledge

1. **`allocate` is still O(n) in the SortedDict version.** A real interviewer push gets you to the size-index. If you don't volunteer that, you'll be asked.
2. **`sortedcontainers` is third-party.** Acknowledge it. "In production I'd use a B-tree (e.g. `BTrees.OOBTree` if I'm in ZODB land) or write a custom skip list. For the interview this is the standard tool."
3. **Best-fit vs first-fit.** LC 2502 says leftmost (first-fit). Best-fit reduces fragmentation but biases toward many tiny holes. The buddy system trades both for trivial merging at the cost of internal fragmentation. Be ready to compare on the call.
4. **No thread safety.** Single-threaded by design. A single `threading.Lock` around `allocate`/`freeMemory` is correct but kills throughput. Per-size-class locks (segregated lists) are the production answer.
5. **No size validation in baseline.** `allocate(-5, ...)` silently returns `-1` in my impl. Defensible. Some shops want a raise. Ask.

---

## Self-grading vs OpenAI rubric

| Axis | Where you should land |
|---|---|
| 1. Practical problem-solving | Lead with the O(n) baseline. Optimize after it works. Don't reach for SortedDict on minute 2. |
| 2. Edge case discipline up front | Restate: `-1` on no fit, `0` on unknown mID, multi-block per mID, coalesce eagerly. Before coding. |
| 3. Layered optimization | Baseline → SortedDict for O(log n) free → size-index SortedList for O(log n) malloc. Three layers, each named. |
| 4. Python internals depth | Articulate why `sortedcontainers` is a B-tree; difference between `bisect_left` and `bisect_right`; why `dict` insertion-ordered iteration doesn't help here. |
| 5. Targeted optimization under follow-up | Best-fit vs first-fit. Buddy system. Boundary tags. Alignment. Realloc. Have a 30-second answer for each. |
| 6. Test quality | Suite must cover the four merge cases independently, fragmentation defeating first-fit, double-free, same-mID stacking, leftmost-fit ordering. |

---

## Follow-up sketches

### 1. Alignment

```python
def allocate(self, size: int, mID: int, align: int = 1) -> int:
    if size <= 0 or align <= 0:
        return -1
    for i, (start, gap) in enumerate(self.free):
        # First address in this gap that's a multiple of `align`.
        aligned = (start + align - 1) // align * align
        pad = aligned - start
        if gap - pad >= size:
            # Carve the gap into [start, aligned) + [aligned, aligned+size)
            # + [aligned+size, start+gap). Update self.free for the leftover
            # pieces; record (aligned, size) as the allocation.
            self.alloc.setdefault(mID, []).append((aligned, size))
            self.free.pop(i)
            if pad > 0:
                self.free.insert(i, (start, pad))
                i += 1
            tail_start = aligned + size
            tail_size = (start + gap) - tail_start
            if tail_size > 0:
                self.free.insert(i, (tail_start, tail_size))
            return aligned
    return -1
```

Note: the alignment slop on the left becomes a sub-gap. Coalescing-on-free handles it automatically.

### 2. Realloc

```python
def realloc(self, mID: int, new_size: int) -> int:
    # For simplicity, assume mID currently owns exactly one block.
    [(start, old_size)] = self.alloc[mID]
    if new_size == old_size:
        return start
    if new_size < old_size:
        # Shrink in place. Return the tail to the free list.
        self.alloc[mID] = [(start, new_size)]
        self._insert_free(start + new_size, old_size - new_size)
        return start
    # Grow: can we extend into the right neighbour free block?
    need = new_size - old_size
    for i, (fstart, fsize) in enumerate(self.free):
        if fstart == start + old_size and fsize >= need:
            self.alloc[mID] = [(start, new_size)]
            if fsize == need:
                self.free.pop(i)
            else:
                self.free[i] = (fstart + need, fsize - need)
            return start
    # Fallback: alloc new, copy (in a real allocator), free old.
    new_start = self.allocate(new_size, mID)
    if new_start == -1:
        return -1  # caller still owns the old block
    self.alloc[mID].remove((start, old_size))
    self._insert_free(start, old_size)
    return new_start
```

### 3. Thread safety

```python
import threading

class Allocator:
    def __init__(self, n: int) -> None:
        self._lock = threading.Lock()
        # ...

    def allocate(self, size: int, mID: int) -> int:
        with self._lock:
            # ...
```

Correct, simple, kills throughput. Production strategy: **segregated free lists per size class**, each with its own lock. `allocate(size)` rounds up to a size class, locks only that class's list. Contention drops by a factor of ~num-classes. The bookkeeping for cross-class coalescing is the hard part — most allocators just don't coalesce across classes (slab-style).

### 4. Double-free detection

```python
def __init__(self, n: int) -> None:
    # ...
    self._ever_allocated: set[int] = set()

def allocate(self, size: int, mID: int) -> int:
    # ...
    self._ever_allocated.add(mID)

def freeMemory(self, mID: int) -> int:
    if mID not in self._ever_allocated:
        raise ValueError(f'mID {mID} was never allocated')
    if mID not in self.alloc:
        raise ValueError(f'mID {mID} double-freed')
    # ...
```

For C-style use-after-free detection (caller still holds an address after free), you'd need to either zero freed memory + a canary, or use generational pointers (high bits = generation, increment on free).

---

## Common mistakes interviewers see

1. **`dict[mID] -> (start, size)`** (singular) — silently overwrites on repeat mID. Top-1 bug.
2. **Forgetting to coalesce** — tests that free blocks one at a time and then request a single large alloc will fail.
3. **Coalescing only in one direction** (right but not left, or vice versa). The `[ free | freed | free ]` case won't collapse to one block.
4. **Off-by-one on `bisect_left` vs `bisect_right`** when finding the left neighbour. The reference uses `bisect_left(start) - 1` — equivalent to "largest key strictly less than `start`."
5. **Sorting on every operation** instead of maintaining the sorted invariant. Turns the whole thing into O(n²).
6. **Returning `None` instead of `-1`** for no-fit, or raising on unknown mID instead of returning `0`. Read the spec.
7. **Using a min-heap by size for free blocks** and then needing to delete a specific block (when its neighbour is freed) — heaps don't support arbitrary delete without lazy tombstones, which adds bookkeeping and makes the "is this index still valid?" check ugly.

---

## What's worth saving to memory after this attempt

- **Whether the four-merge-cases sketch came out cleanly on first try** or whether you had to redraw it. (Tracks readiness for next time.)
- **Whether you reached for SortedDict on minute 2 vs after the baseline worked.** The pattern is "baseline first, optimize after" — building the habit matters more than the speed.
- **Which follow-up the interviewer would push hardest on** for your level. Likely alignment + thread safety for backend roles; realloc + buddy system for systems-leaning roles.
