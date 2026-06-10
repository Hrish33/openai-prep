# Prereqs — Social Network / Follow Graph

**Don't attempt until you've internalized the three patterns below.** Estimated time: 1-1.5 hours, mostly because graph storage is reused from LC 355.

You've done LC 355 (Design Twitter). That gave you the `following: defaultdict(set)` storage and the rename instinct (`following`, not `followers`, because you traverse in the direction "what does *this user* pull from"). That part carries.

**What's NEW vs LC 355:**

1. **2-hop traversal with `Counter`.** Friend-of-friend recommendation with three exclusion clauses.
2. **Per-edge timestamps + `bisect`** (Variant 1). `check(A, B, t)` — was A following B *at time t*?
3. **Snapshot semantics — deep-ish copy + reverse index** (Variant 2). The shallow-copy trap is the killer.

Internalize these and both variants are 35-45 min each.

---

## Concept 1: 2-hop recommendation with `collections.Counter`

**What you're learning:** the canonical pattern for "people you may know" — count how many of *user's* followees follow each candidate, exclude the obvious ones, rank by count.

**The pattern:**

```python
from collections import Counter

def recommend(self, user: str, k: int) -> list[str]:
    direct = self.following.get(user, set())
    candidates: Counter[str] = Counter()
    for mid in direct:                          # 1-hop neighbors
        for cand in self.following.get(mid, set()):    # 2-hop neighbors
            if cand == user:                    # exclusion 1: not yourself
                continue
            if cand in direct:                  # exclusion 2: not someone you already follow
                continue
            candidates[cand] += 1               # +1 intermediary

    return [c for c, _ in candidates.most_common(k)]
```

**Three exclusion clauses — name them at the start of your attempt:**
1. **Not yourself.** A→B→A is a degenerate case if B follows A back. Without this, you'd recommend yourself.
2. **Not anyone you already follow.** A→B→C and A→C means C is already in your direct set.
3. **(Implicit) Not someone who has zero intermediaries.** Handled naturally by Counter — they never get incremented.

**Why `Counter.most_common(k)` and not a heap:**
- For typical interview sizes, `Counter.most_common(k)` is O(C log C) — fine.
- For very large C, a min-heap of size K is O(C log K). Mention as a follow-up; don't lead with it.
- `most_common(k)` returns sorted desc; if you want tiebreak by something else (e.g., recency), use `sorted(candidates.items(), key=...)` instead.

**Tiebreaking by recency** (variant 1, optional follow-up): if you store edge timestamps, break ties on candidates with equal count by the maximum intermediary-edge-timestamp:
```python
ranked = sorted(
    candidates.items(),
    key=lambda kv: (-kv[1], -max_intermediary_t[kv[0]]),
)[:k]
```
Don't volunteer this until the interviewer asks.

**Done when:** you can write the pattern from a blank screen in under 4 minutes, and state the three exclusion clauses without referencing the code.

---

## Concept 2: Per-edge timestamps + `bisect` for temporal queries (Variant 1)

**What you're learning:** how to model "A started following B at time t" so that `check(A, B, t)` is fast.

**The data shape:**

```python
# A starts following B at time t. Once you start, you don't unfollow (per spec).
# So storing the EARLIEST t per (A, B) edge is sufficient.
self.follow_t: dict[str, dict[str, int]] = defaultdict(dict)
#                ^ follower      ^ followee  ^ time they started

def update(self, A: str, B: str, t: int) -> None:
    if B not in self.follow_t[A]:
        self.follow_t[A][B] = t            # only set on first follow

def check(self, A: str, B: str, t: int) -> bool:
    t_started = self.follow_t.get(A, {}).get(B)
    return t_started is not None and t_started <= t
```

That's the whole pattern. No `bisect` needed when you're storing per-edge "earliest follow" — it's a single comparison.

**When does `bisect` come in?**

Only if the problem allows **unfollow + re-follow**, which makes the membership-at-time-t question harder. Then you'd store a list of intervals per edge:
```python
self.intervals: dict[(A, B)] -> list[(start_t, end_t_or_inf)]
```
And `check(A, B, t)` becomes a binary search through the intervals.

**The current OpenAI spec does NOT mention unfollow.** Stick to the simple "earliest t" model. Mention the interval-list approach as a follow-up if the interviewer asks "what if they can unfollow?"

**Done when:** you can write the `update`/`check` pair in under 2 minutes and articulate why a single `t_started` is sufficient under the stated spec.

---

## Concept 3: Snapshot immutability — the deep-copy trap (Variant 2)

**What you're learning:** how to take a snapshot of a graph that does NOT observe future mutations, without doing a slow `copy.deepcopy` of the whole world.

**The trap:**

```python
# WRONG — shallow copy of the OUTER dict only.
def create_snapshot(self):
    return Snapshot(following=dict(self.following))
```

`dict(self.following)` copies the dict but the *values are aliased* — each `Snapshot`'s set still points to the SAME set as the live graph. Subsequent `follow()` calls mutate that set, and the snapshot sees the change. **Snapshot immutability broken.**

**The fix — one-level deep copy:**

```python
def create_snapshot(self):
    following_copy = {user: set(followees) for user, followees in self.following.items()}
    return Snapshot(following_copy)
```

`set(followees)` builds a new set from the existing one. Now the snapshot's set is independent.

**Why not `copy.deepcopy`:**
- `deepcopy` works but is slower — it recurses through arbitrary structure with bookkeeping for cycles.
- For `dict[str, set[str]]`, the dict comprehension above is the right depth and ~10x faster.
- Mention this trade-off if the interviewer probes — it's a real Python-internals signal.

**The reverse index — what makes `get_followers` O(F) instead of O(U+E):**

```python
class Snapshot:
    def __init__(self, following: dict[str, set[str]]):
        self.following = following
        # Build reverse index ONCE at construction time.
        self.followers_idx: dict[str, set[str]] = defaultdict(set)
        for follower, followees in following.items():
            for followee in followees:
                self.followers_idx[followee].add(follower)

    def get_followers(self, user: str) -> list[str]:
        return list(self.followers_idx.get(user, set()))
```

Cost: snapshot construction goes from O(U+E) (one-level copy) to O(U+E) (copy) + O(U+E) (reverse-index build) = still O(U+E). But each `get_followers` call becomes O(F) (the size of that user's follower set) instead of O(U+E) (scanning every edge).

The trade-off in one sentence: **pay O(U+E) once at snapshot-construction time to make every reverse-lookup O(F).** Worth it because snapshots are typically read many times after construction.

**Done when:** you can articulate the shallow-copy bug in 30 seconds, write the one-level deep copy from memory, and explain why the reverse index is eager (constructor) and not lazy (first-call).

---

## Recall templates — type these from a blank screen

If you can type these three cold, both variants are derivable.

**1. 2-hop recommend** (both variants):
```python
direct = following[user]
counts = Counter()
for mid in direct:
    for cand in following[mid]:
        if cand != user and cand not in direct:
            counts[cand] += 1
return [c for c, _ in counts.most_common(k)]
```

**2. Temporal edge + check** (variant 1):
```python
def update(self, A, B, t):
    if B not in self.follow_t[A]:
        self.follow_t[A][B] = t

def check(self, A, B, t):
    started = self.follow_t.get(A, {}).get(B)
    return started is not None and started <= t
```

**3. Snapshot constructor with reverse index** (variant 2):
```python
class Snapshot:
    def __init__(self, following):
        self.following = {u: set(fs) for u, fs in following.items()}
        self.followers_idx = defaultdict(set)
        for u, fs in self.following.items():
            for f in fs:
                self.followers_idx[f].add(u)
```

---

## Suggested schedule

| Session | What |
|---------|------|
| Session 1 (30 min) | Read this doc. Type the three recall templates from a blank screen. |
| Session 2 (40 min) | Cold attempt Variant 1 against the `FollowGraph` tests. |
| Session 3 (50 min) | Cold attempt Variant 2 against the `SocialNetwork` + `Snapshot` tests. |
| Session 4 (20 min) | Read `interviewer_notes.md`. Re-do the recommend function from scratch. |

## How to use Claude Code during this

- "explain Counter.most_common vs heapq.nlargest — when do I reach for each?"
- "show me the shallow-vs-deep copy bug with a 5-line example"
- "what's the bug in this recommend?" — paste your code

Don't ask Claude to write the recommend function for you. The muscle is in the three exclusion clauses.

## When you're ready

When you can type the three recall templates cold, set a 40-min timer and open `problem.md`. Pick a variant per attempt; don't try both in one session.
