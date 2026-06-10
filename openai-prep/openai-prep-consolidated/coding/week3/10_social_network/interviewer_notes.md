# Interviewer Notes — Social Network / Follow Graph

**Read this AFTER your timed attempts.** Reference implementations for both variants, the bugs to avoid, and how the OpenAI rubric scores each piece.

---

## Reference solutions

### Variant 1 — FollowGraph

```python
from collections import Counter, defaultdict


class FollowGraph:
    def __init__(self) -> None:
        # follower -> {followee: earliest_t}
        self.follow_t: dict[str, dict[str, int]] = defaultdict(dict)

    def update(self, A: str, B: str, t: int) -> None:
        # First call wins. Subsequent updates to the same edge are no-ops.
        if B not in self.follow_t[A]:
            self.follow_t[A][B] = t

    def check(self, A: str, B: str, t: int) -> bool:
        started = self.follow_t.get(A, {}).get(B)
        return started is not None and started <= t

    def recommend(self, A: str, k: int) -> list[str]:
        direct = set(self.follow_t.get(A, {}).keys())
        counts: Counter[str] = Counter()
        for mid in direct:
            for cand in self.follow_t.get(mid, {}):
                if cand == A or cand in direct:
                    continue
                counts[cand] += 1
        # most_common returns count-desc. Tiebreak by lex order via a stable sort.
        ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
        return [c for c, _ in ranked[:k]]
```

**Three things to defend:**
1. **`defaultdict(dict)`** — outer is a default-dict (no key-check on update), inner is a plain dict (so `get(B)` is None-safe).
2. **`first call wins`** for `update`. The spec says "A starts following B at time t" — once it's set, A has been following B since then. Subsequent calls don't change history. Either interpretation is defensible; pick one and stick with it.
3. **Lex tiebreak** in recommend so output is deterministic. `Counter.most_common(k)` is *not* lex-stable across ties; explicit `sorted` with a key tuple is.

### Variant 2 — SocialNetwork + Snapshot

```python
from collections import Counter, defaultdict


class SocialNetwork:
    def __init__(self) -> None:
        self.users: set[str] = set()
        self.following: dict[str, set[str]] = defaultdict(set)

    def add_user(self, user_id: str) -> None:
        if user_id in self.users:
            raise ValueError(f"user already exists: {user_id}")
        self.users.add(user_id)

    def follow(self, follower: str, followee: str) -> None:
        if follower not in self.users or followee not in self.users:
            raise ValueError(f"unknown user(s): {follower}, {followee}")
        if follower == followee:
            return    # self-follow no-op
        self.following[follower].add(followee)   # duplicate-follow is a set-add no-op

    def create_snapshot(self) -> "Snapshot":
        # One-level deep copy: outer dict + new sets for the values.
        # NOT copy.deepcopy (recurses unnecessarily, slower).
        # NOT dict(self.following) alone (aliases the sets — bug).
        following_copy = {u: set(fs) for u, fs in self.following.items()}
        return Snapshot(following_copy)


class Snapshot:
    def __init__(self, following: dict[str, set[str]]) -> None:
        # Caller is responsible for passing a freshly-copied adjacency dict.
        self.following = following
        # Eager reverse index — pay O(U+E) once so every get_followers is O(F).
        self.followers_idx: dict[str, set[str]] = defaultdict(set)
        for follower, followees in following.items():
            for followee in followees:
                self.followers_idx[followee].add(follower)

    def is_following(self, follower: str, followee: str) -> bool:
        return followee in self.following.get(follower, set())

    def get_following(self, user_id: str) -> list[str]:
        return list(self.following.get(user_id, set()))

    def get_followers(self, user_id: str) -> list[str]:
        return list(self.followers_idx.get(user_id, set()))

    def recommend(self, user_id: str, k: int) -> list[str]:
        direct = self.following.get(user_id, set())
        counts: Counter[str] = Counter()
        for mid in direct:
            for cand in self.following.get(mid, set()):
                if cand == user_id or cand in direct:
                    continue
                counts[cand] += 1
        ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
        return [c for c, _ in ranked[:k]]
```

**Four things to defend:**
1. **Why `{u: set(fs) for u, fs in d.items()}` and not `copy.deepcopy(d)`.** Same correctness for `dict[str, set[str]]` shape; the comprehension is ~10x faster because `deepcopy` recurses with cycle bookkeeping. If the value type ever becomes nested (e.g., `dict[str, dict[str, set]]`), `deepcopy` becomes worth the cost.
2. **Why `dict(self.following)` is a bug.** Outer dict is copied; values (sets) are aliased. Mutating `self.following[user]` after snapshot mutates the snapshot's set too. This is the classic shallow-copy trap.
3. **Why eager reverse index.** `get_followers` is called on the snapshot, possibly many times. Building lazily would mean every first call to `get_followers(x)` is O(U+E); the second is O(F). Inconsistent. Build it once at construction; every call is O(F).
4. **Why `self.users` separate from `self.following`.** A user with no follows still exists. `self.following[u]` would be an empty set in a defaultdict, but you need to distinguish "user exists with no follows" from "user doesn't exist" for the `raise` on `follow()`.

---

## The 2-hop recommend pattern — burn it into muscle memory

Both variants share this. If you can write it cold in 90 seconds, you'll never lose points on this problem.

```python
direct = following[user]
counts = Counter()
for mid in direct:
    for cand in following[mid]:
        if cand == user or cand in direct:
            continue
        counts[cand] += 1
return [c for c, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:k]]
```

**The three exclusion clauses (state them at the start of your attempt):**
1. Not yourself (`cand == user`).
2. Not anyone you already follow (`cand in direct`).
3. Anyone else with ≥1 intermediary becomes a candidate; Counter handles the rest.

**Why `most_common(k)` is fine but `sorted(..., key=(-count, name))` is better:**
- `Counter.most_common(k)` is `O(C log K)` and returns count-desc.
- It's NOT lex-stable across ties — two candidates with the same count come out in insertion order, which depends on dict iteration order, which depends on insertion order, which depends on test setup. Flaky tests.
- Explicit `sorted` with `key=(-count, name)` is `O(C log C)` but deterministic. For interview C sizes, the constant factor doesn't matter; deterministic output does.

---

## What the rubric scores

| Axis | What gets graded |
|------|------------------|
| **Practical problem-solving** | Did you reach for `Counter` immediately, or hand-roll a dict-of-int + manual sort? |
| **Edge case discipline up front** | Did you enumerate self-loop, direct-follow, unknown-user, empty-recommend BEFORE coding? |
| **Layered optimization** | `Counter.most_common` → "for very large C, min-heap of size K" → "Counter under a cardinality threshold, heap above it." |
| **Depth in Python internals** | Variant 2 is where the signal is. The shallow-vs-one-level-vs-deepcopy decision, articulated with the WHY, is exactly the Python-internals signal OpenAI grades. |
| **Targeted optimization under follow-up** | "Add unfollow" → interval list + bisect. "Snapshot at scale" → COW or edge-versioning. "3-hop" → weight by depth or shortest-path only. |
| **Test quality** | Does your test for snapshot immutability mutate the live graph AFTER taking the snapshot and assert the snapshot didn't see it? That's the killer test. |

**Strong hire** comes from:
- The shallow-copy bug named *before* implementing `create_snapshot`.
- Eager reverse index defended with "pay O(U+E) once, every read becomes O(F)."
- 2-hop recommend with three exclusion clauses called out at the start, not discovered via test failure.

**Lean hire** comes from:
- Working code on both variants, but the snapshot copy depth was wrong on first attempt and fixed after the immutability test failed.

---

## Common mistakes

1. **Shallow-copying the adjacency dict** (`dict(self.following)`). Snapshot becomes a live view. The killer test is exactly the "mutate after snapshot" assertion.

2. **`copy.deepcopy` of the adjacency dict.** Works but slow, and on senior bar it gets dinged. The one-level comprehension is the right depth for this shape.

3. **Forgetting `cand != user` in recommend.** A→B→A makes you recommend yourself. Embarrassing.

4. **Forgetting `cand not in direct` in recommend.** You recommend people you already follow.

5. **Raising on duplicate follow / self-follow.** Spec says these are no-ops. Raising is wrong API behavior.

6. **Raising on unknown user in `check`/`recommend`/`get_following`.** Spec says these return False/[]/[]. Raising is wrong.

7. **Lazy reverse index.** First call is O(U+E), subsequent O(F). Inconsistent latency. Build eagerly.

8. **Counter without lex tiebreak.** Tests pass locally, fail on CI when dict iteration order differs.

9. **Storing `set(self.users)` AND `dict[u, set]` redundantly.** Tempting but not required — a user with no follows is just not a key in the `following` dict. The reason to keep `self.users` separate is to distinguish "exists with no follows" from "doesn't exist" — needed for the `follow()` raise.

---

## Follow-up sketches

**"Add `unfollow(A, B, t)` and make `check` handle the gap."**

Store intervals per edge:
```python
self.intervals: dict[(str, str), list[tuple[int, Optional[int]]]] = defaultdict(list)
# (start_t, end_t_or_None) per follow/unfollow cycle

def update(self, A, B, t):
    self.intervals[(A, B)].append((t, None))   # None = still following

def unfollow(self, A, B, t):
    last_start, end = self.intervals[(A, B)][-1]
    self.intervals[(A, B)][-1] = (last_start, t)

def check(self, A, B, t):
    # bisect for the interval whose start <= t, then verify end > t
    intervals = self.intervals.get((A, B), [])
    if not intervals: return False
    # last interval starting <= t
    import bisect
    starts = [s for s, _ in intervals]
    idx = bisect.bisect_right(starts, t) - 1
    if idx < 0: return False
    start, end = intervals[idx]
    return end is None or t < end
```

**"Snapshot at scale (millions of users)."**

Two paths:

*Copy-on-Write*: each followee set is an immutable persistent structure (e.g., `frozenset` wrapped to allow "add" by returning a new frozenset). The snapshot shares the unchanged frozensets with the live graph; only mutated edges create new structures. Snapshot construction becomes O(1).

*Edge versioning*: each edge stores `[created_at, deleted_at_or_inf]`. Snapshots are just a timestamp; any historical state is reconstructed by filtering on edges where `created_at <= snapshot_t < deleted_at`. Storage scales linearly with edge events; queries get a `bisect` factor.

**"3-hop recommendations."**

BFS-3 with depth tracking. The exclusion clauses extend: not self, not direct (1-hop), not 2-hop already-recommended (depending on how you compose). Two semantics:
- Shortest-path: only count the shortest path's intermediary count.
- Weighted: `1/depth` per path.

Either is defensible; clarify which.

**"Concurrency."**

Reads on snapshots are inherently safe (immutable). Writes to the live graph need synchronization:
- Single global lock: simple, serializes all writes. Fine if write QPS is modest.
- Per-follower lock: parallelism within different followers. Deadlock-free as long as you only ever hold one at a time.
- Single writer thread + queue: full serialization but no lock contention, easy to reason about. Best for high write QPS.

For reads-during-writes, a `threading.Lock` around the write side is sufficient since snapshot construction reads the dict atomically (well, not quite — the dict comprehension iterates, so you need the lock for the duration of the comprehension to prevent torn reads).

---

## Honest weaknesses to acknowledge

- Variant 1's `update` with "earliest t wins" is an arbitrary choice. The spec is ambiguous about subsequent `update` calls — "starts following" could mean "first call sticks" or "every call moves the start". Pick a side and defend it.
- The `sorted` for recommend is O(C log C); for very large C, `heapq.nsmallest(k, items, key=lambda kv: (-kv[1], kv[0]))` is O(C log K). Mention the boundary if asked.
- One-level deep copy assumes the value type is `set[str]` — atomic immutable strings inside. If the value type ever becomes nested (e.g., `dict[str, dict[str, ...]]`), one-level isn't enough. State the dependency.

---

## Self-grading prompt

After your attempt, score 1-3 on each axis:

| Axis | 1 = missed | 2 = ok | 3 = strong |
|------|------------|--------|-----------|
| Three exclusion clauses for recommend stated up front | Discovered via test | Named one or two | Named all three before coding |
| Variant 1: justified "earliest t wins" for update | Took the path implicitly | Named the choice | Argued both interpretations briefly |
| Variant 2: stated the shallow-copy bug before writing create_snapshot | Hit the bug; fixed after test | Mentioned it once coded | Named the bug in the design discussion |
| Variant 2: justified eager (not lazy) reverse index | Lazy / didn't justify | Eager without justification | Eager with "pay O(U+E) once, reads O(F)" |
| Reached for `Counter` immediately | Hand-rolled dict + sort | Used Counter after a moment | First line was `from collections import Counter` |
| Lex-tiebreak for deterministic recommend output | `most_common(k)` only | Mentioned the issue | Used explicit `sorted` with key tuple |

12+ across both variants ≈ strong hire on this problem.
