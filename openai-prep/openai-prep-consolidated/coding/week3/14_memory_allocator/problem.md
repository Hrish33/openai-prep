# Problem 14: Memory Allocator (LC 2502 "Design Memory Allocator")

**Prereqs:** Skim `00_prereqs.md` if the four merge-on-free cases aren't second nature, or if `sortedcontainers.SortedDict.bisect_left` doesn't immediately mean "find the index where this key would slot in."

**Time budget:** 60-75 min (onsite coding); 30-40 min for the O(n) baseline alone (phone screen).
**Source:** OpenAI phone screen + onsite, last seen 2026-06-11. Frequency: medium. Common arc: "implement first-fit in ~25 min, then optimize."
**Stage:** Phone screen (baseline) → onsite (baseline + log-time optimization + 1-2 follow-ups).

---

## The problem

You're implementing a memory allocator backing a fixed pool of `n` bytes. Clients call `allocate(size, mID)` to reserve a contiguous range and `freeMemory(mID)` to release everything they've reserved under that ID. The allocator must coalesce adjacent free space so future allocations can use it.

This is a classic systems-coding problem masquerading as a data-structure problem. The first attempt is always an O(n) linear scan. **The interviewer will reject it and ask for better.** Have the O(log n) version ready.

---

## Required API

```python
class Allocator:
    def __init__(self, n: int) -> None:
        """Initialize an allocator backed by `n` contiguous bytes, all free."""
        ...

    def allocate(self, size: int, mID: int) -> int:
        """
        Find the LEFTMOST free block of >= size bytes. Carve `size` bytes from
        the start of it and return the starting address. Multiple allocations
        may share the same mID — each is tracked independently.

        Returns -1 if no contiguous free block of `size` bytes exists.
        """
        ...

    def freeMemory(self, mID: int) -> int:
        """
        Free EVERY block currently allocated under `mID`. Coalesce each
        released block with adjacent free space (left, right, both, or
        neither).

        Returns the total bytes freed (0 if mID has no live blocks).
        """
        ...
```

### Return contracts to nail

- `allocate(size, mID)` → starting address `s ∈ [0, n - size]` on success, **`-1`** on no-fit. Even on success, mID is recorded; multiple allocates with the same mID stack.
- `freeMemory(mID)` → total bytes freed (sum of all sizes). **`0`** when mID is unknown or already fully freed. Idempotent on unknown mIDs — never raises.
- After every operation, the allocator's free-block representation is **coalesced** — no two free blocks are adjacent in address space.

---

## Example (LC 2502 sample)

```python
loc = Allocator(10)        # 10 bytes, all free
assert loc.allocate(1, 1) == 0    # gives [0,1); free = [1,10)
assert loc.allocate(1, 2) == 1    # gives [1,2); free = [2,10)
assert loc.allocate(1, 3) == 2    # gives [2,3); free = [3,10)
assert loc.freeMemory(2) == 1     # frees [1,2); free = [1,2) and [3,10)
assert loc.allocate(3, 4) == 3    # leftmost gap of >=3 is [3,10); gives [3,6)
assert loc.allocate(1, 1) == 1    # leftmost gap of >=1 is [1,2); gives [1,2)
                                  # mID=1 now owns BOTH [0,1) and [1,2)
assert loc.allocate(1, 1) == 6    # gives [6,7); mID=1 owns [0,1), [1,2), [6,7)
assert loc.freeMemory(1) == 3     # frees all three of mID=1's blocks (1+1+1=3)
assert loc.allocate(10, 2) == -1  # 4 bytes free, request 10 → no fit
```

Walk through this once by hand before you code — the "same mID allocated multiple times" wrinkle is the easiest thing to get wrong.

---

## Edge cases to nail

- **Empty pool size (`n == 0`)**: every `allocate` returns `-1`. Don't crash on init.
- **`allocate(size > n, ...)`**: return `-1`. (Captured by the general no-fit path.)
- **`freeMemory` of unknown mID**: return `0`. No error.
- **Double-free**: after `freeMemory(7)` succeeds, a second `freeMemory(7)` returns `0` — the mID was popped from the allocated map.
- **Re-allocate after full free**: after freeing everything, the next `allocate(n, ...)` returns `0` — the entire pool coalesced back to a single free block.
- **Allocate exactly fills a gap**: don't leave a zero-size free block. Remove the gap entirely.
- **Fragmentation that defeats first-fit**: if free blocks are `[(0,1), (3,1), (6,1)]` and you request 2 bytes, return `-1` even though *total* free bytes ≥ 2. The "contiguous" word in the spec is load-bearing.
- **mID collision after free**: `allocate(5, 1) → free(1) → allocate(5, 1)` should succeed and mID=1 now owns one block, not two.
- **Coalesce all four ways**: free a block with (a) no free neighbours, (b) free left, (c) free right, (d) free both. Test each.

---

## What an OpenAI interviewer is looking for

1. **Clarify the API before coding.** "Does `free(mID)` free *all* blocks with that mID, or just one?" "What's the return on no-fit?" "What's the n in O(log n) — bytes or blocks?" Asking these in the first 90 seconds buys you 10 minutes later when an edge case bites.

2. **Lead with the baseline, then optimize.** Write the O(n) interval-list version end-to-end, get tests green, **then** introduce the SortedDict-based O(log n) version. Strong candidates make this pivot explicit ("the current version is O(n) on free for the neighbour walk; let me swap the free-list for a SortedDict to get O(log n)").

3. **Draw the four merge cases out loud.** None / left / right / both. The bug rate on coalescing is proportional to how clearly you've enumerated the cases before writing the code.

4. **Coalesced invariant.** State it explicitly: "after every op, no two free blocks are adjacent." Then design the merge logic so the invariant holds. Don't leave it implicit and hope.

5. **Test quality.** Tests should cover: each merge case in isolation, fragmentation defeats first-fit, double-free returns 0, re-allocation reuses freed space, same-mID multi-allocation. If your suite is missing the four merge cases, it's a yellow flag.

6. **Complexity follow-up.** Be ready to articulate: "malloc is O(n) on the free-list scan; free is O(log n) via SortedDict bisect. To make malloc O(log n) too, I'd add a second index keyed by size — a SortedList of `(size, start)` — so first-fit/best-fit becomes a bisect rather than a scan." The interviewer wants to hear you reach for the second structure unprompted.

7. **Honesty about Python.** "`sortedcontainers` isn't stdlib but is interview-canonical for this. In production I'd use a B-tree or a treap. In a real C/C++ allocator I'd reach for boundary tags + a segregated free list per size class."

---

## Follow-ups (don't peek until both baseline + SortedDict are working)

<details>
<summary>Click to expand</summary>

1. **Alignment.** Modify `allocate(size, mID, align=8)` so every returned address is a multiple of `align`. Sketch: when scanning a free gap `[start, start+gap)`, the first aligned address is `((start + align - 1) // align) * align`. If `aligned + size > start + gap`, skip. The leftover slice on the left becomes a sub-gap.

2. **Realloc.** `realloc(mID, new_size)` resizes an existing allocation in place if possible (right-neighbour is a free gap of sufficient size), otherwise allocates fresh + frees old. Returns new address. Discuss copying semantics — for a real allocator you'd `memcpy`; for this exercise just track the bookkeeping.

3. **Thread safety.** What's your locking strategy? A single global mutex is correct but kills throughput. Sketch: per-size-class locks (segregated free lists), or RCU-style read-mostly with copy-on-write of the free-block index. Bring up `threading.Lock` vs `RLock` (re-entrancy in free-of-self), and the GIL's role.

4. **Double-free detection.** Currently `free(mID)` of an unknown mID returns `0` silently. Add detection that distinguishes "never allocated" from "previously allocated, now freed." Sketch: keep a `seen_mIDs` set; or version-tag mIDs with a generation counter.

5. **Best-fit instead of first-fit.** Swap the malloc strategy: find the *smallest* free block of `>= size`. Reduces fragmentation. Implementation: second index, `SortedList[(size, start)]`. Trade-off: best-fit can leave many tiny unusable fragments; first-fit is faster but biases toward leaving big holes at the start.

6. **Buddy allocator.** Power-of-2 size classes; allocate by rounding up; free always merges with its "buddy" of equal size. Trivial merging in exchange for internal fragmentation. Sketch: bitmap per size class.

7. **Compare to the OS allocator.** glibc `ptmalloc` uses bins (segregated free lists by size class), each protected by its own arena lock. Linux MMU operates on 4KB pages. Your allocator is a userland slab over a flat byte array — closer to a slab allocator than to `malloc(3)`.

8. **Compaction.** Given a fragmented allocator, write a `compact()` that moves live blocks to the start of the pool, coalescing all free space into one trailing gap. Issue: returned addresses are now stale; need a pointer-rewrite or a handle-based API.

</details>

---

## Honest difficulty note

**The problem is harder than it looks because of bookkeeping, not algorithms.**

- The O(n) baseline is ~40 lines if you're careful. Most candidates write it in 20 minutes — but lose 10 of those minutes on the merge cases.
- The SortedDict pivot is conceptually simple (swap the container, neighbour lookup goes from linear walk to `bisect_left`) but easy to botch the off-by-ones on `bisect_right` vs `bisect_left`.
- The "same mID, multiple allocations" wrinkle catches the LC 2502 spec-skimmers — it's `dict[mID] -> list[block]`, not `dict[mID] -> block`.
- The interviewer *will* push you off the baseline. If you can't articulate the SortedDict version in the last 20 minutes, the round is a no-hire.

**A strong attempt covers:**
- Restates the API and contracts before coding (allocate returns address or -1; free returns total bytes; free of unknown mID returns 0; same mID can stack).
- Lists the four merge cases out loud or sketches them on the whiteboard.
- Writes the baseline with the coalescing invariant in <25 minutes.
- Pivots to SortedDict unprompted, articulates "O(log n) on free, malloc still O(n) without a size index."
- Names alignment / realloc / thread safety as obvious follow-ups before being asked.

**A failing attempt typically:**
- Uses a plain `dict[start] -> size` and re-sorts on every operation.
- Forgets to coalesce, so the allocator leaks fragmentation across operations.
- Models `dict[mID] -> (start, size)` (singular) and silently loses repeat allocations.
- Crashes on `freeMemory` of an unknown mID instead of returning 0.
- Spends 45 minutes on the baseline and never gets to the optimization.
- Reaches for a heap-by-size and then can't handle "delete arbitrary element."
