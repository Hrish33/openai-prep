# Prereqs — Memory Allocator (LC 2502 "Design Memory Allocator")

Estimated prep time: **60-90 min**. This problem has a hard floor (the O(n) interval-scan baseline) and a high ceiling (O(log m) free-block index). The interview *expects* you to get to the ceiling — the O(n) version explicitly gets rejected. Plan for two passes.

Four things to internalize before you attempt:

1. **The four merge-on-free cases** — none / left / right / both. Draw them.
2. **The free-block representation choice** — sorted interval list vs SortedDict vs heap-by-size. What you give up with each.
3. **`sortedcontainers.SortedDict` API** — `bisect_*`, `irange`, `peekitem`, `popitem`. The two operations you actually need.
4. **Allocated-block bookkeeping** — `free(mID)` takes only the mID, so the allocator must remember `(start, size)` for every live block keyed by mID.

---

## Concept 1: The four merge-on-free cases

`free(mID)` releases one allocated block and **must coalesce with adjacent free space.** There are exactly four cases. Draw them once and you'll never confuse them again.

```
Layout: [ ... free | freed block | free ... ]   ← case BOTH:  collapse 3 → 1
        [ ... free | freed block | used ... ]   ← case LEFT:  extend left gap rightward
        [ ... used | freed block | free ... ]   ← case RIGHT: extend freed block over right gap
        [ ... used | freed block | used ... ]   ← case NONE:  insert a new gap
```

In a sorted-by-start representation (interval list or `SortedDict[start] = size`), "adjacent" is decided by address arithmetic:

```python
prev_end   = prev_start + prev_size   # is this == freed_start?  → LEFT
freed_end  = freed_start + freed_size # is this == next_start?   → RIGHT
```

The **trap**: you must check the neighbours that exist in the *free* structure, not the previous/next allocated block. In a SortedDict of free blocks keyed by start, `irange(maximum=freed_start, reverse=True)` peeks the candidate left neighbour; `irange(minimum=freed_start)` peeks the candidate right neighbour. Then you do the adjacency check.

**Done when:** you can list the four cases and the address arithmetic for each from a blank screen in 30 seconds.

---

## Concept 2: Free-block representation — three options, three trade-offs

| Representation | `malloc` | `free` | Why pick it |
|---|---|---|---|
| Sorted interval list (e.g. `list[(start, size)]`) | **O(n)** scan for first-fit | **O(n)** to find neighbours by linear walk | Baseline. Trivial to write. Easy to argue correctness. Use as the lead solution if you have <20 min. |
| `SortedDict[start] = size` (free blocks keyed by start) | **O(n)** scan first-fit, or **O(log n)** with a size index | **O(log n)** to find left/right neighbours | The expected O(log m) answer for OpenAI. Single structure does adjacency lookup. |
| Heap-by-size + interval list | **O(log n)** best-fit pop from heap | Hard — heap doesn't support delete; need lazy deletion | Tempting but messy. Avoid unless asked for best-fit specifically. |

**The pivot from interview:** Start with the interval list, get all tests passing, *then* swap the free-block container for a SortedDict to get O(log n). The bookkeeping (allocated blocks dict, merge cases) is unchanged — you're only replacing the linear scan.

**Done when:** you can name the three representations and articulate why SortedDict wins for this specific API.

---

## Concept 3: `sortedcontainers.SortedDict` — the four operations you need

```python
from sortedcontainers import SortedDict

free = SortedDict()        # start_address -> size
free[100] = 50             # gap of 50 bytes starting at 100
free[200] = 30             # gap of 30 bytes starting at 200

# (1) Iterate free blocks in address order — for malloc first-fit scan
for start, size in free.items():
    if size >= want:
        ...

# (2) Find the gap to the LEFT of a given address — for merge on free
#     "largest key <= freed_start" via bisect_right then back up by 1
idx = free.bisect_right(freed_start) - 1
if idx >= 0:
    left_start = free.keys()[idx]
    left_size  = free[left_start]
    if left_start + left_size == freed_start:
        # adjacent — merge!

# (3) Find the gap to the RIGHT of a given address
idx = free.bisect_left(freed_start)
if idx < len(free):
    right_start = free.keys()[idx]
    # if freed_start + freed_size == right_start → adjacent

# (4) Insert / delete a gap — O(log n)
del free[old_start]
free[new_start] = new_size
```

That's all of it. Don't reach for `irange` unless you actually need a range slice — `bisect_*` + index lookup is cleaner for "single neighbour."

**Done when:** you can write the "find left neighbour, check adjacency, merge or insert" block from a blank screen.

---

## Concept 4: Allocated-block bookkeeping

LC 2502's `free(mID)` takes only an `int` — no size, no address. The allocator therefore *must* remember:

```python
allocated: dict[int, list[tuple[int, int]]]   # mID -> [(start, size), ...]
```

A single `mID` can have **multiple** allocations (every `malloc(size, mID)` with the same mID stacks up). `free(mID)` frees them all and returns the total bytes freed. The dict-of-lists shape handles this naturally.

**The trap:** candidates default to `dict[mID] -> (start, size)` (singular) and silently overwrite the second allocation. Read the LC spec once carefully — *"You may have several blocks with the same mID."*

---

## What to clarify on the call

Five open questions in 90 seconds before you write code:

1. **Does `free(mID)` free all blocks with that mID, or just one?** (LC 2502: all of them.)
2. **Can `malloc` reuse a freed `mID`?** (Yes — mID is just a label, not an identity.)
3. **What's the return contract for `malloc` when no fit exists?** (`-1`.)
4. **What's the return for `free` when the mID doesn't exist?** (`0` — total bytes freed.)
5. **Complexity expectation — what's the n in O(log n)?** (Number of free blocks / live allocations, not total bytes.)

Pin these down. The "all blocks with mID" point alone eliminates 40% of buggy attempts.

---

## Recall template — type this from a blank screen

If you can get the **interval-list baseline** down in <8 minutes and the **SortedDict version** in <15, you're ready.

### Baseline — O(n) dump + sort + sweep

```python
class Allocator:
    def __init__(self, n: int) -> None:
        # Free blocks as (start, size), sorted by start, coalesced.
        self.free = [(0, n)]
        # mID -> list of (start, size). Multiple blocks per mID is legal.
        self.alloc = {}

    def allocate(self, size: int, mID: int) -> int:
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
        # Re-coalesce by dumping back + sorting + one-pass merge (LC 56).
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

No bisect, no left/right case analysis, no merge helper. The sort + sweep handles all four merge cases implicitly. **This is the version to type from blank.**

### Optimized — O(log n) SortedDict

```python
from typing import Dict, List, Tuple
from sortedcontainers import SortedDict


class Allocator:
    def __init__(self, n: int) -> None:
        self.n = n
        self.free: SortedDict = SortedDict({0: n})     # start -> size
        self.alloc: Dict[int, List[Tuple[int, int]]] = {}

    def allocate(self, size: int, mID: int) -> int:
        # First-fit by address still requires linear scan. To hit O(log n),
        # also maintain a size-keyed index — but the interview usually
        # accepts O(n) here and O(log n) on free, since malloc is the
        # logically harder optimization (best-fit / segregated lists).
        for start, gap in self.free.items():
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

        # RIGHT neighbour: smallest key >= start.
        ri = self.free.bisect_left(start)
        if ri < len(keys):
            right_start = keys[ri]
            if right_start == end:
                size += self.free.pop(right_start)

        # LEFT neighbour: largest key < start.
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

**Honest note on the SortedDict version:** strict O(log n) for *both* malloc and free requires a second index keyed by size (e.g. `SortedList[(size, start)]`) so first-fit/best-fit doesn't scan. Most interviewers accept O(log n) on free + linear malloc, and use the malloc optimization as the follow-up. If they push, sketch the size-index second structure.

---

## Recommended warmup problems

| Problem | Why |
|---|---|
| **LC 56 — Merge Intervals** | The "insert one interval, merge with neighbours" mechanic is the same as `_insert_free`. Drill it in 10 min. |
| **LC 57 — Insert Interval** | Even closer — single-insert variant. The bisect-and-merge pattern *is* the free path. |
| **LC 2502 — Design Memory Allocator** | The exact problem. Solve it in O(n) first, then refactor to SortedDict. |
| **LC 855 — Exam Room** | SortedList drill in the same shape: maintain sorted set of occupied seats, find largest gap, insert/remove. |

---

## Suggested schedule

| Session | What |
|---------|------|
| Session 1 (25 min) | Read this doc + `problem.md`. Solve LC 56 + LC 57 if rusty. Draw the four merge cases on paper. |
| Session 2 (45 min) | Cold attempt of the O(n) baseline under timer. `timer started, 45 min`. Aim: all tests green. |
| Session 3 (30 min) | Refactor to SortedDict. Time it: <15 min for the swap. |
| Session 4 (20 min) | `review mode`. Walk through `interviewer_notes.md` — focus on follow-ups (alignment, realloc, thread safety). |

When you can write the baseline `_insert_free` block (the bisect + left/right merge) from blank in under 5 minutes, set a **45-min timer** and open `problem.md`.
