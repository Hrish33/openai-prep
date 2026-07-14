# Follow-up: Communities via Union-Find

**Bolt-on for Variant 1 (`FollowGraph`).** Same `update` semantics; add four new query methods that answer connectivity questions.

This is a textbook DSU drill. The right data structure is **Union-Find / Disjoint Set Union**. If you reach for BFS, you've under-tooled.

---

## The decision you state up front

> "Follow edges are directed, but communities are **undirected** connectivity. I treat each `update(A, B, t)` as an undirected union — A and B are now in the same community regardless of who followed whom."

Say this before coding. It's the design call an interviewer grades.

(Strongly connected components — mutual follows only — is a different problem requiring Tarjan/Kosaraju. Don't conflate.)

---

## Required API

```python
class CommunityGraph:
    # --- inherited shape from Variant 1, kept for context ---
    def update(self, A: str, B: str, t: int) -> None:
        """A starts following B at time t. Idempotent (earliest t wins).
        Also unions A and B in the community DSU."""
        ...

    def check(self, A: str, B: str, t: int) -> bool:
        """Same as Variant 1. Temporal directed-edge check."""
        ...

    # --- new community queries ---

    def largest_community_size(self) -> int:
        """Member count of the biggest community. 0 if no users seen."""
        ...

    def num_communities(self) -> int:
        """Number of distinct communities. Counts singletons too if any."""
        ...

    def community_size(self, user: str) -> int:
        """Size of the community containing `user`. 0 if user unknown."""
        ...

    def same_community(self, A: str, B: str) -> bool:
        """True iff A and B are in the same community.
        False if either is unknown. A and A are trivially in the same community
        ONLY if A has been seen at least once."""
        ...
```

## Example

```python
g = CommunityGraph()
g.update("A", "B", 1)    # {A,B}                    -> 1 community of size 2
g.update("C", "D", 2)    # {A,B}, {C,D}             -> 2 communities of size 2
g.update("E", "F", 3)    # {A,B}, {C,D}, {E,F}      -> 3 communities of size 2
g.update("B", "C", 4)    # {A,B,C,D}, {E,F}         -> 2 communities; largest = 4

g.largest_community_size()   # 4
g.num_communities()          # 2
g.community_size("A")        # 4
g.community_size("E")        # 2
g.community_size("Z")        # 0  (unknown user)
g.same_community("A", "D")   # True
g.same_community("A", "F")   # False
g.same_community("A", "Z")   # False (unknown user)
```

## Requirements

- **Undirected union.** `update(A, B, t)` unions A and B regardless of direction.
- **Self-follow** (`update("A", "A", t)`) is a no-op for the graph AND a no-op for the union — but A becomes a known user (size 1).
- **Idempotent updates.** Re-following the same pair must not break component counts or sizes. `union(A, B)` when they're already in the same set is a no-op.
- **Unknown user** → `community_size` returns 0, `same_community` returns False. Don't raise.
- **`largest_community_size()` and `num_communities()` must be O(1).** Track `max_size` and `num_components` incrementally during `union()`. Don't scan all roots on every query.
- **`community_size(user)` and `same_community(A, B)` must be amortized O(α(n)).** That's `size[find(x)]` and `find(a) == find(b)`. Use path compression.

---

## What an OpenAI interviewer is looking for

1. **Name the structure.** "I'll use union-find with path compression and union-by-size. The communities are weakly connected components." Say this before writing the class.

2. **Maintain `num_components` and `max_size` incrementally.** This is the senior signal. Scanning `set(find(x) for x in users)` on every `num_communities()` call is correct but graded as junior — they're looking for "I update these counters inside `union()` so the queries are O(1)."

3. **Union-by-size vs union-by-rank.** Either is fine; pick one and justify. Size is more natural here because you need `size[root]` for `community_size()` anyway — single field doing double duty.

4. **Path compression flavor.** Two-pass (iterative) or one-pass (recursive with assignment). Either is fine. Avoid the `find(x.parent)` recursion in Python without a `sys.setrecursionlimit` bump — flag it as a concern.

5. **Edge cases enumerated up front.** Self-follow, duplicate update, unknown user, empty graph.

## Follow-ups (don't peek until base works)

<details>
<summary>Click to expand</summary>

1. **Return the actual member list of the largest community.** Now you need `members: dict[root, list[str]]` updated inside `union()` (extend the smaller list into the larger; clear the absorbed one). `largest_community()` returns the list at `members[root_with_max_size]`. The size-only tracking isn't enough.

2. **Add `unfollow` / `disconnect`.** DSU does not support efficient deletion. Options: (a) **Offline rebuild** — recompute components from the edge list lazily on the next read; (b) **Link-Cut Trees** — supports both link and cut in O(log n) but is famously hard to write; (c) **Euler-tour trees** — same complexity, also hard. In an interview: say "this is the boundary where DSU stops; for dynamic connectivity I'd reach for offline rebuild or punt to a different structure" — don't try to live-code link-cut.

3. **Top-K largest communities.** Maintain a `Counter[root] = size` and call `most_common(k)`. Updating it inside `union()` is a delete + insert. Or: skip the maintenance and just `Counter(size[r] for r in roots).most_common(k)` at query time — O(R log R). Pick based on read/write ratio.

4. **Temporal communities.** "What did the communities look like at time t?" DSU cannot answer this on its own — it's a forward-only structure. You'd need to replay updates up to time t into a fresh DSU, or use a **persistent DSU** (rollback DSU via union-by-size without path compression: O(log n) per op, supports undo). Mention rollback DSU; don't live-code it.

5. **Concurrent updates.** Standard fix: a global lock around `update()`. DSU operations are not naturally lock-free because find can mutate (path compression). Lock-free DSU exists but is research-grade.

</details>

## Honest difficulty note

If you've done LC 547 (Friend Circles) or LC 684 (Redundant Connection), this is ~20 minutes of work. If DSU is new to you, expect 40 minutes — the bookkeeping for `num_components` and `max_size` inside `union()` is where bugs hide.

The trap people fall into: scanning `len({find(x) for x in self.parent})` on every `num_communities()` call. It works. It passes tests. It's not what the interviewer wants. **Counters maintained in `union()`** is the answer.
