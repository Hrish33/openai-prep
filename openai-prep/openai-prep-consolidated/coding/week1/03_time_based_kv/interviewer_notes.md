# Interviewer notes — Time-Based Key-Value Store

**Read AFTER your attempt.** Reading first defeats the point.

The base here is small enough that the reference is almost trivial — which is exactly why **most of this doc is the follow-up sketches.** That's where your prep time should go. If you nailed the base in 15 minutes, good; now make sure you can write the out-of-order and thread-safe variants too.

## Reference solution (base — scrappy)

```python
import bisect
import collections


class TimeMap:
    def __init__(self):
        # Two parallel, index-aligned lists per key.
        #   _times[key][i]  <-> _values[key][i]
        # Parallel arrays let bisect work directly on the timestamps with no
        # key function and no tuple-comparison gotchas.
        self._times = collections.defaultdict(list)
        self._values = collections.defaultdict(list)

    def set(self, key, value, timestamp):
        # BASE GUARANTEE: timestamps strictly increasing per key.
        # So append keeps the list sorted for free -> O(1).
        self._times[key].append(timestamp)
        self._values[key].append(value)

    def get(self, key, timestamp):
        times = self._times.get(key)        # .get, NOT [], to avoid creating empty entries
        if not times:
            return ""                        # missing key, or no writes at all
        idx = bisect.bisect_right(times, timestamp) - 1
        if idx < 0:
            return ""                        # query is before the first write
        return self._values[key][idx]
```

That's the whole base. Memorize the `get` shape: **`bisect_right - 1`, then the `idx < 0` guard.**

## Why parallel arrays instead of a list of tuples?

Both work. The trade-off:

| Approach | `get` looks like | Notes |
|----------|------------------|-------|
| **Parallel arrays** (`times[]`, `values[]`) | `bisect_right(times, t) - 1` | bisect operates on bare ints — no key fn, no tuple-compare gotcha. Two lists to keep aligned. |
| **List of `(ts, value)` tuples** | needs `key=` (3.10+) or a sentinel | one list, but bisect compares tuples — if two share a `ts` it falls through to comparing `value`, which can raise. |

Parallel arrays are the cleaner default *because* they sidestep the tuple-comparison problem. Mention the tuple version exists and why you didn't pick it — that's the kind of micro-justification that reads as senior.

## The one bug that silently passes some tests

```python
idx = bisect.bisect_right(times, timestamp) - 1
return self._values[key][idx]        # BUG: no `idx < 0` guard
```

When the query is before all writes, `bisect_right` returns `0`, so `idx == -1`. In Python, `values[-1]` is **the last element** — so instead of returning `""`, you silently return the *latest* value. This passes happy-path tests and fails only the "query before first write" case. It's the classic floor-search bug. The `if idx < 0: return ""` line is not optional.

## Honest weaknesses to acknowledge in interview

- **`set` assumes strictly-increasing timestamps.** It's a bug the moment that guarantee is removed. Say so before they ask — see follow-up 1.
- **Two parallel lists must stay aligned.** A single list of tuples can't drift out of sync; parallel arrays can if you `append` to one and forget the other. A minor robustness cost for the bisect convenience.
- **Unbounded memory.** Every `set` grows the history forever. See follow-up 3.
- **Not thread-safe.** Concurrent `set`/`get` can tear. See follow-up 2.

## Grading yourself

| Axis | Passing |
|------|---------|
| Edge cases up front | Named: missing key, query-before-first-write (→ `""`), exact-match timestamp, far-future query |
| Floor boundary | `bisect_right - 1` with the `idx < 0` guard; can explain why `right` not `left` |
| Data structure choice | Sorted-per-key history + binary search; can justify parallel arrays vs tuples |
| Stated the assumption | Said "set is O(1) *because* timestamps are increasing" out loud |
| Follow-up readiness | Out-of-order, thread-safety, retention don't make you freeze — you can sketch each |
| `get` complexity | O(log n), not a linear scan |

A clean base alone is a **median** performance for this problem. The differentiation is the follow-ups below.

## Follow-up sketches

### 1. Out-of-order writes (the documented variant — bank on it)

`set` can be called with timestamps in any order. `append` no longer keeps the list sorted, so `bisect` reads garbage. Minimal fix — insert in sorted position into *both* aligned arrays:

```python
def set(self, key, value, timestamp):
    times, values = self._times[key], self._values[key]
    i = bisect.bisect_right(times, timestamp)   # where it belongs
    times.insert(i, timestamp)                  # O(n) shift
    values.insert(i, value)                     # same index keeps them aligned
# get() is UNCHANGED — the list is still sorted, so the floor query still works.
```

Say the cost out loud: **`list.insert` is O(n)** because of the shift; the binary search finds the spot in O(log n) but doesn't save the shift. If out-of-order writes are frequent and per-key histories are large:

> "I'd switch the per-key history to a structure with O(log n) insert — `sortedcontainers.SortedList`, or a balanced BST / skip list. Parallel Python lists give O(1) append but O(n) arbitrary insert."

**Same-timestamp policy:** with `bisect_right`, a re-write at an existing timestamp inserts *after* the old one, so the floor query naturally returns the newer write (last-write-wins). State that as a deliberate choice, not an accident.

### 2. Thread safety

**Frame it correctly first: this is a state-management problem, not a coordination problem.** Unlike the multithreaded crawler (a work queue, termination, workers spawning work), there's no orchestration here — no queue, no "when are we done." The whole job is mutual exclusion over shared mutable state. Saying that out loud shows you've classified the problem. The depth is then in three places: (a) *granularity* — the state is partitioned by key, so global lock → per-key striping → reader/writer; (b) the **read path is not free** — `get`'s bisect+index can tear on a concurrently-mutating list, so "reads are safe, the GIL covers me" is wrong; (c) the critical section is tiny and has **no I/O**, so the crawler's "never hold the lock during I/O" bug can't happen here.

**The insight that makes this problem easy to parallelize: the base case is append-only.** Strictly-increasing timestamps mean you only ever append; existing `(timestamp, value)` entries are never mutated. Immutable history ⇒ a reader on an old index is inherently safe; you only guard against a torn view *during* an append. This is why versioned stores lean on append-only + copy-on-write. Coupling to note: the **out-of-order variant breaks this** (`insort` mutates the middle), so it's strictly harder to make thread-safe than the base.

**What flips it back into coordination: multi-key atomic ops.** One key per operation = one lock = no deadlock. A transaction (or "copy A's history to B") must lock multiple keys atomically → lock ordering + deadlock avoidance. That's the bridge to the transactions follow-up.

First answer — one lock, on **both** methods:

```python
import threading

def __init__(self):
    ...
    self._lock = threading.Lock()

def set(self, key, value, timestamp):
    with self._lock:
        self._times[key].append(timestamp)
        self._values[key].append(value)

def get(self, key, timestamp):
    with self._lock:                 # YES, get needs it too
        times = self._times.get(key)
        ...
```

Why `get` needs the lock: a concurrent `append`/`insert` can reallocate the list or leave the two parallel arrays momentarily misaligned — a reader mid-`bisect` sees a torn structure. "Reads are safe because of the GIL" is **wrong** here: the GIL makes a single bytecode atomic, but your `bisect` + index is multiple bytecodes.

The ladder, recited:
- **Global lock** → simple, correct, but every key contends on one lock.
- **Lock striping** → a lock per key (or per hash bucket); writes to different keys proceed in parallel.
- **Reader/writer lock** → reads dominate a time-series store, so allow many concurrent readers, exclusive writer. Python has **no stdlib `RWLock`** — build one from `threading.Condition`, or shard. (Real implementation: week 3.)

### 3. Bounded memory / retention

Versions grow forever. Cap to the last N per key:

```python
def set(self, key, value, timestamp):
    times, values = self._times[key], self._values[key]
    times.append(timestamp)
    values.append(value)
    if len(times) > self._max_versions:
        # drop oldest. del [0] is O(n); for large N drop in batches,
        # or use a structure with O(1) front-pop. (But get needs random
        # access for bisect, so a plain deque won't do.)
        del times[0]
        del values[0]
```

Other retention strategies to name: **TTL/expiry** (drop versions older than `now - ttl`), **GC of cold keys** (keys never read), **compaction** (coalesce runs of identical values). The tension to articulate: `get` wants random access (favors arrays) but cheap front-eviction wants a deque — you can't have both for free.

### 4. Range query (`[t1, t2]`) as a generator

```python
def get_range(self, key, t1, t2):
    times = self._times.get(key, [])
    lo = bisect.bisect_left(times, t1)    # first >= t1
    hi = bisect.bisect_right(times, t2)   # first > t2
    for i in range(lo, hi):
        yield times[i], self._values[key][i]
```

Two bisects bound the slice; a **generator** streams it lazily instead of materializing a list (ties to the Python-internals axis — they like seeing `yield` used deliberately). Note `bisect_left` for the lower bound (inclusive of `t1`) vs `bisect_right` for the upper (inclusive of `t2`).

### 5. Doesn't fit in RAM

Now it's a storage-engine question, and they may steer you to system design. The shape:
- **In-memory index + on-disk append log.** Writes append to a log (sequential I/O, fast). An in-memory structure maps `key -> offset(s)`.
- **LSM-tree / SSTables.** Buffer recent writes in memory (a "memtable"), flush sorted runs to disk, merge/compact in the background. This is how real time-series and versioned stores (Cassandra, RocksDB, Bigtable) work.
- Reads check the memtable, then sorted on-disk runs newest-to-oldest until they find the floor.

You don't implement this — you name the shape and the trade-off (write throughput via sequential appends vs read amplification across runs, fixed by compaction).

## Common mistakes interviewers see

1. **`bisect_left` instead of `bisect_right`** → off-by-one that returns the *previous* write on an exact-timestamp match.
2. **Missing the `idx < 0` guard** → `values[-1]` silently returns the latest value instead of `""` for before-first-write queries. Passes happy-path tests; fails the boundary.
3. **Linear scan in `get`** → O(n). The sorted history + binary search is the entire point of the problem.
4. **`append` for out-of-order writes** → silently corrupts the sort order; `bisect` then reads wrong values with no error.
5. **No lock on `get`** under concurrency, justified by "the GIL makes reads safe" → wrong; the multi-step `bisect` + index isn't atomic.
6. **Storing `dict[timestamp] -> value` (unsorted)** and sorting on every `get` → O(n log n) reads. The history must be *maintained* sorted, not sorted on demand.

## Want a Round 2?

After the base, implement the **out-of-order variant** in a copy (`solution_unordered.py`) — the base tests should still pass, plus add a test that writes t=10 then t=8 then t=9 and reads each boundary. Then bolt on a single global lock and a `get_range` generator. Those three follow-ups, actually written (not just described), are what move this from "I've seen LC 981" to "I can build a versioned store."
