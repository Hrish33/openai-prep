# Prereqs — Time-Based Key-Value Store

**Estimated time: 1.5-2.5 hours.** This is lighter than problem 1. The base algorithm is a canonical LeetCode Medium you may already know cold. **Do not let that fool you** — at OpenAI level the entire test is the follow-up ladder (see `problem.md`). The prereqs below get you to a clean base; the follow-ups are where the round is won or lost.

There are really only two things to nail before the base, plus one preview you'll lean on for the hardest follow-up.

---

## Concept 1: Binary search and the *floor query*

**What you're learning:** finding "the largest element `<= target`" in a sorted list — the **floor**. This is the whole `get`. Everything else is bookkeeping.

The naive linear scan is O(n) per `get`. Binary search makes it O(log n). You will not hand-roll the binary search in the real solution — you'll use `bisect` — but you must be able to derive it, because the interviewer *will* ask "what's `bisect_right` actually doing here?"

**Mental model — the two `bisect` functions:**

```python
import bisect

times = [10, 20, 20, 30]
#         0   1   2   3   (indices)

bisect.bisect_left(times, 20)   # 1  -> leftmost slot where 20 could go
bisect.bisect_right(times, 20)  # 3  -> rightmost slot where 20 could go
```

- `bisect_left(a, x)` → index of the **first** element `>= x`.
- `bisect_right(a, x)` → index of the **first** element `> x`.

**The floor idiom — memorize this exact line:**

```python
idx = bisect.bisect_right(times, target) - 1
# idx == -1  -> nothing <= target (target is before all writes)
# else        -> times[idx] is the largest timestamp <= target
```

Why `bisect_right` and not `left`? Because of the **exact-match** case. If `target` equals a stored timestamp, you want to *include* it (the value written exactly at `target` is valid at `target`). `bisect_right` puts the cursor *after* all equal elements, so `- 1` lands you **on** the match. `bisect_left` would land you on the element *before* the match — an off-by-one that returns stale data on exact hits. This is the single most common bug in this problem, and a guaranteed probe.

**Three boundary cases to keep straight:**

| Query | `bisect_right - 1` gives | Correct? |
|-------|--------------------------|----------|
| `target` exactly equals a stored timestamp | the matching index | ✓ (you want the exact write) |
| `target` between two writes | the earlier one | ✓ (floor) |
| `target` before the first write | `-1` | ✓ (signal "no value" → return `""`) |

**Practice problems:**
- [LeetCode 704 — Binary Search](https://leetcode.com/problems/binary-search/) (Easy) — only if your hand-rolled binary search is rusty. Write it once with explicit `lo`/`hi` so you can reproduce `bisect` from scratch under questioning.
- [LeetCode 981 — Time Based Key-Value Store](https://leetcode.com/problems/time-based-key-value-store/) (Medium) — this **is** the base problem. Solve it with `bisect`. If you get it in under 15 minutes, you're ready for the base.

**Done when:** you can write the floor idiom (`bisect_right - 1` with the `-1`-means-not-found check) from a blank screen and explain why it's `right`, not `left`.

---

## Concept 2: The monotonic assumption — and `bisect.insort` for when it breaks

**What you're learning:** *why* `set` is O(1) in the base problem, and what it costs when that guarantee is removed. This is not optional polish — the out-of-order variant is a **documented, real interview follow-up** for this exact problem (a reported MongoDB variant where `PUT` timestamps arrive unordered). Bank on it.

**The base assumption (LeetCode 981 states it explicitly):** *"All timestamps for `set` operations are strictly increasing per key."* That guarantee is what lets `set` be a plain `append` — every new timestamp is larger than all existing ones, so the per-key list stays sorted for free.

```python
# Base case: timestamps strictly increasing -> append keeps it sorted, O(1)
self.store[key].append((timestamp, value))
```

**When the follow-up removes that guarantee**, `append` is a *bug* — the list is no longer sorted, so your `bisect` is reading garbage. You now must insert *in sorted position*:

```python
import bisect

# Out-of-order writes: insert so the list stays sorted, O(n) due to the shift
bisect.insort(self.store[key], (timestamp, value))
```

`bisect.insort(a, x)` finds the position with binary search (O(log n)) **then shifts** the tail to make room (O(n)). So the insert is O(n) overall — the binary search doesn't save you from the array shift. `insort` is **not a hack** — it's the correct, idiomatic O(n) answer. It's fine until out-of-order writes are frequent *and* per-key histories are large; only then do you escalate.

**The trap to avoid: "use a linked list so insert is O(1)."** You can't binary-search a linked list. Binary search is O(log n) *only because* an array gives O(1) random access to the midpoint; a linked list has no indexing, so reaching the midpoint is O(n) — the search collapses to O(n) and you've thrown away the whole point. Neither primitive gives you both operations cheaply:

| Structure | Floor search | Arbitrary insert | Why |
|-----------|--------------|------------------|-----|
| Dynamic array (`list` + `bisect`) | **O(log n)** ✓ | O(n) — shift the tail | random access yes, but contiguous memory must shift |
| Doubly linked list | O(n) — no random access | O(1) *splice*, but O(n) to *find* the spot | so insert is O(n) anyway, and search is also O(n) |

The array's O(n) is the *shift*; the linked list's O(n) is the *search*. You move the cost, you don't remove it — a plain DLL is strictly worse (loses fast reads, gains nothing).

To get **O(log n) for both search and insert**, the binary-search structure must be baked *into* the data structure, not borrowed from contiguous memory:
- **Balanced BST** (red-black / AVL) — floor query is a predecessor lookup, O(log n); insert O(log n). The textbook answer.
- **Skip list** — what the "linked list" instinct is actually reaching for: a linked list with multiple levels of express-lane pointers, so each level skips ~half the remaining nodes → O(log n) expected. (Redis sorted sets work this way.) A skip list *can* be searched in log n; a plain DLL cannot.
- **In Python, practically:** `sortedcontainers.SortedList` — O(log n) search, fast chunked inserts. This is what you'd actually reach for.

Be ready to say it out loud: *"`insort` is O(n) because of the shift. A linked list doesn't help — you can't binary-search it, so search degrades to O(n) too. For O(log n) on both I'd use a balanced BST, a skip list, or `sortedcontainers.SortedList`."*

**Concrete: the `sortedcontainers` version.** `SortedList(key=...)` returns a `SortedKeyList` that keeps elements ordered by a key function and gives ≈O(log n) `add` *and* binary search — exactly the "both operations cheap" structure the table above is missing. Store `(timestamp, value)` tuples keyed on the timestamp:

```python
import collections
from sortedcontainers import SortedKeyList   # NOT stdlib — pip install sortedcontainers

class TimeMap:
    def __init__(self):
        # each key -> a list kept sorted by timestamp (the tuple's [0])
        self._store = collections.defaultdict(
            lambda: SortedKeyList(key=lambda pair: pair[0])
        )

    def set(self, key, value, timestamp):
        self._store[key].add((timestamp, value))      # ≈O(log n), handles out-of-order

    def get(self, key, timestamp):
        history = self._store.get(key)                # .get -> no empty entry on miss
        if not history:
            return ""
        idx = history.bisect_key_right(timestamp) - 1  # floor BY KEY (timestamp only)
        if idx < 0:
            return ""
        return history[idx][1]                         # [1] is the value
```

What this buys over the `list` + `insort` version:
- **`add` is ≈O(log n)**, not O(n) — out-of-order writes no longer pay the array-shift cost.
- **`bisect_key_right(timestamp)` bisects by the key function**, so you compare against the bare timestamp and never trip the tuple-comparison gotcha (it never looks at `value`). That's why `SortedKeyList` is cleaner than a plain `SortedList` of tuples here.
- **Same-timestamp = last-write-wins** falls out for free: `add` places equal keys to the right (insertion order), so `bisect_key_right - 1` lands on the most recent write at that timestamp.

Two honest caveats for the interview:
- **`sortedcontainers` is third-party, not stdlib.** If the interviewer bars external imports, say "I'd use `sortedcontainers.SortedList` in real code; here I'll hand-roll with `bisect` on a `list` and accept O(n) inserts, or sketch a skip list." Naming the library *and* the fallback is the strong move.
- **"≈O(log n)" is the practical claim, not a literal balanced tree.** Internally it's a list-of-lists (chunked) structure; `add`/lookup are sub-linear and behave like log n in practice. Don't claim a strict O(log n) worst-case bound the way you would for a red-black tree.

> **Tuple ordering gotcha:** `(timestamp, value)` tuples compare lexicographically — timestamp first, which is what you want. But if two writes share a timestamp, the comparison falls through to comparing `value` strings, which can raise or misorder. Decide your same-timestamp policy (last-write-wins? reject?) deliberately; don't let tuple comparison decide it for you.

**No separate LeetCode problem for this** — it's a modification of 981. After you solve 981 the normal way, re-solve it assuming `set` can be called with *any* timestamp order. That single re-solve is the highest-value rep for this problem.

**Done when:** you can state why the base `set` is O(1), switch it to `bisect.insort` for out-of-order writes, and articulate the O(n) cost and the structure you'd escalate to.

---

## Concept 3 (preview): thread-safety — read this, don't drill it yet

**What you're learning:** *just enough* to not freeze when the interviewer says "now make it thread-safe." The real depth lives in **week 3 (`08_multithreaded_crawler`)** — that's where you actually build locks, lock striping, and reason about the GIL. Here, just hold the shape:

- **One global `threading.Lock` around `set` and `get`** is the correct *first* answer. Both need it: `get`'s `bisect` can read a list mid-`append`/`insort` and see a torn/reallocating structure. Say this; it shows you know the read path isn't automatically safe.
- **It's a bottleneck** because every key contends on one lock. The next step is **lock striping** — a lock *per key* (or per hash bucket), so writes to different keys don't block each other.
- **Reads vastly outnumber writes** in a time-series store, so the *right* answer is often a **reader-writer lock** (many concurrent readers, exclusive writer). Note that Python has **no stdlib `RWLock`** — you'd build one from a `threading.Condition`, or shard.

You do **not** need to write any of this now. You need to be able to *say the ladder*: global lock → per-key striping → reader/writer. If you've done the week-3 crawler, this will feel obvious. If you haven't, that's fine — flag it as "I'd reach for the patterns from my concurrency practice" and move on.

**Done when:** you can recite the three-rung concurrency ladder in two sentences. That's the bar for *this* problem; the actual implementation is week-3 work.

---

## Suggested schedule

| Day | What |
|-----|------|
| Day 1 | Read this doc. Solve LC 981 with `bisect`. Then re-solve it assuming out-of-order writes (`bisect.insort`). |
| Day 2 | Read `problem.md` — especially the follow-ups. Attempt `solution.py` cold on a 30-minute timer (base only). Run `test_solution.py`. |
| Day 3 | Read `interviewer_notes.md`. Then **pick one follow-up** (out-of-order writes is the highest-value) and actually implement it in a copy of your solution. |

This is deliberately short. The base is easy; spending three days grinding the base is wasted time. Spend the saved time on the follow-ups — that's the actual interview.

## When you're ready

When you can solve LC 981 in under 15 minutes **and** state the out-of-order and concurrency follow-up ladders without freezing, open `problem.md` and start a 30-minute timer on the base. The base is your floor (pun intended), not your ceiling.
