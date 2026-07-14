    # Problem 10: Social Network / Follow Graph

**Prereqs:** Skim `00_prereqs.md` if you haven't internalized the 2-hop recommend pattern and the snapshot deep-copy trap.

**Time budget:** 40-50 min per variant. Pick one per attempt.
**Source:** Reported in OpenAI phone screens (last seen 2026-05-16). Frequency: high.

## Problem

Build a social network's follow graph. Two API rotations circulate — drill both.

There are **no tweets** in this problem. Don't reach for your LC 355 heap-merge skill — it doesn't apply.

---

## Variant 1 — Timestamped edges

Each follow edge carries the time it was created. Queries are temporal.

```python
class FollowGraph:
    def update(self, A: str, B: str, t: int) -> None:
        """A starts following B at time t.
        If A already follows B, this is a no-op (earliest t wins)."""
        ...

    def check(self, A: str, B: str, t: int) -> bool:
        """At time t, was A following B?
        True iff A has an outgoing follow edge to B with start time <= t."""
        ...

    def recommend(self, A: str, k: int) -> list[str]:
        """Top-k 2-hop friend-of-friend suggestions for A.
        Rank by number of intermediaries (people in A's direct follows
        who also follow the candidate). Exclude A itself and anyone
        A already follows. Tie-break by anything reasonable (lex order is fine)."""
        ...
```

**Example:**

```python
g = FollowGraph()
g.update("A", "B", 1)
g.update("A", "M", 2)
g.update("B", "C", 3)
g.update("B", "D", 4)
g.update("M", "C", 5)

g.check("A", "B", 1)   # True  — A started following B at t=1
g.check("A", "B", 0)   # False — A wasn't following B yet at t=0
g.check("A", "X", 99)  # False — no such edge

g.recommend("A", 2)    # ["C", "D"] — C has 2 intermediaries (B, M); D has 1 (B)
```

### Requirements

- **Edges are append-only.** No `unfollow` in the stated spec. Storing earliest `t` per `(A, B)` pair is sufficient.
- **`check` is inclusive at `t`.** If A started following B at t=5, `check(A, B, 5)` returns True.
- **`recommend` uses current state.** No `t` parameter — recommendations are computed on the live graph.
- **Exclusion clauses for `recommend`:** not A itself, not anyone A already follows. State both clauses up front.
- **Unknown users:** `check` returns False, `recommend` returns `[]`. Don't raise.

---

## Variant 2 — Snapshot-based

Mutations happen on the live graph; reads happen on immutable snapshots that don't observe future writes.

```python
class SocialNetwork:
    def add_user(self, user_id: str) -> None:
        """Raises ValueError if the user already exists."""
        ...

    def follow(self, follower: str, followee: str) -> None:
        """Raises ValueError if either user is missing.
        Self-follow is a no-op. Duplicate follow is a no-op."""
        ...

    def create_snapshot(self) -> "Snapshot":
        """Returns an immutable view that does NOT observe subsequent follow() calls.
        Deep-copy each followee set; shallow copy of the outer dict is a bug."""
        ...


class Snapshot:
    def is_following(self, follower: str, followee: str) -> bool: ...

    def get_following(self, user_id: str) -> list[str]: ...

    def get_followers(self, user_id: str) -> list[str]:
        """Efficient (O(F)) because the snapshot eagerly built a reverse index
        at construction time."""
        ...

    def recommend(self, user_id: str, k: int) -> list[str]:
        """Top-k 2-hop suggestions. Same exclusion clauses as Variant 1."""
        ...
```

**Example:**

```python
net = SocialNetwork()
for u in ["A", "B", "M", "C", "D"]:
    net.add_user(u)
net.follow("A", "B")
net.follow("A", "M")
net.follow("B", "C")
net.follow("B", "D")
net.follow("M", "C")

snap = net.create_snapshot()

# Mutating the live graph after taking the snapshot:
net.follow("A", "C")

snap.is_following("A", "C")   # False — snapshot was taken before
snap.get_followers("C")       # ["B", "M"]  (order not specified)
snap.recommend("A", 2)        # ["C", "D"]   (same as Variant 1)
```

### Requirements

- **`add_user` raises** on duplicate.
- **`follow` raises** if either user is missing. Self-follow and duplicate follow are no-ops, NOT errors.
- **Snapshot immutability** is the load-bearing requirement. Mutating the live graph after `create_snapshot()` must not affect the snapshot. **One-level deep copy** of the adjacency dict is the right depth.
- **`get_followers` is O(F).** Eagerly build a reverse index in the `Snapshot` constructor. Not lazily — eagerly.
- **`recommend`:** same as Variant 1. Excludes self + direct follows.

---

## What an OpenAI interviewer is looking for

1. **State the three exclusion clauses for `recommend` up front.** "Exclude self, exclude direct follows, count intermediaries." Saying this *before* coding earns signal; finding them via test failure does not.

2. **Variant 1 — articulate why a single `t_started` is enough.** "Spec says follows are append-only. The earliest t is the answer to all temporal queries." If you reach for `bisect` without this justification, you've over-engineered.

3. **Variant 2 — articulate the deep-copy depth explicitly.** "One level: outer dict + new sets for the values. `copy.deepcopy` works but recurses unnecessarily; `dict.copy()` is too shallow and aliases the sets." Naming this trade-off is the senior signal.

4. **Variant 2 — eager reverse index.** "I'll build the followers index in the constructor so every `get_followers` call is O(F)." Lazy construction is a valid alternative; pick a side and defend it.

5. **`Counter.most_common(k)`** for ranking. Not a hand-rolled sort. Not a heap (unless asked).

6. **Edge cases enumerated up front.** Unknown user, empty recommend, no candidates, self-follow, duplicate follow, snapshot-before-vs-after-mutation.

## Follow-ups (don't peek until base works)

<details>
<summary>Click to expand</summary>

1. **Tiebreak `recommend` by recency.** Variant 1: store `t_followed` per edge; rank by `(count desc, max_intermediary_t desc)`. Variant 2: needs an extra timestamp argument on `follow()` and the snapshot has to copy those too.

2. **Add `unfollow` (Variant 1).** Now the edge has a lifecycle. Store `intervals: dict[(A, B), list[(start_t, end_t_or_inf)]]`. `check(A, B, t)` becomes a `bisect_right` on starts + a check that `t < end_t`. The simple "earliest t" model breaks.

3. **3-hop recommendations.** BFS-3 with depth tracking. Counter still works but candidates can be reached via multiple paths of different lengths — usually you weight by `1 / depth` or only count the shortest-path intermediaries. Spec gets fuzzy fast; clarify.

4. **Streaming snapshots (Variant 2 at scale).** Deep-copying the world per snapshot is O(U+E). For millions of users that's a lot. Two paths: (a) **Copy-on-Write** — represent each followee set as an immutable persistent structure; mutations create a new structure that shares unchanged parts with old snapshots; or (b) **edge-level versioning** — each edge stores `[created_at, deleted_at]`, and any historical state is reconstructed by filtering on `t`.

5. **Concurrency.** Two threads call `follow()` simultaneously. Either a global lock (simple, serializes writes), per-follower lock (more parallelism, deadlock risk if you ever need two), or a single writer thread fed by a queue. Snapshot reads can use a read-write lock to allow concurrent reads. Discuss the trade-off; don't implement unless asked.

6. **Recommend with mutual-friend visibility filter.** Only count intermediaries who haven't blocked the candidate. Adds a `blocked: dict[user, set[user]]` and a check in the inner loop.

7. **Top-K with very large C.** `Counter.most_common(k)` is O(C log C); a min-heap of size K (`heapq.nsmallest(k, candidates.items(), key=...)` or a manual size-K heap) is O(C log K). Mention the boundary: ~10x speedup once C is large.

</details>

## Honest difficulty note

Both variants are smaller than LC 355 by line count. ~80-100 lines each.

**Variant 1 is the easier one** if you've internalized the recommend pattern — the temporal `check` is a one-liner once you store earliest-t per edge.

**Variant 2 is where the API hygiene signal lives.** The deep-copy depth is the trap; the reverse-index decision is the trade-off; the `raise vs no-op` API surface is the polish. None of these are algorithmically hard — they're judgment calls that interviewers grade as senior vs not.

**A strong attempt covers:**
- 2-hop recommend with all three exclusion clauses called out up front (5 min think-time before coding).
- Variant 1: `update`/`check`/`recommend` (~30 min total).
- Variant 2: full snapshot semantics with the one-level deep copy, reverse index, and proper raises (~40 min).
- Articulated path to: unfollow follow-up (interval list), recency tiebreak, and snapshot-at-scale (COW or versioning).
