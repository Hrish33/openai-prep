# Problem 10: Social Network / Follow Graph

**Status:** Scaffolded 2026-06-09 right after LC 355 (Design Twitter). Cold-attempt both variants when ready.

**One-liner:** Follow graph with two canonical API rotations — timestamped edges + temporal queries, or immutable snapshots + reverse index. Both end with **2-hop friend-of-friend recommendations**.

**Source:** Reported in OpenAI phone screens (last seen 2026-05-16). 60 min, medium. Frequency: high.

**Key concept:** graph storage + 2-hop traversal with `Counter` + (variant 1) temporal edges with `bisect` or (variant 2) snapshot immutability with reverse index.

**Likely prereqs:**
- LC 355 (Design Twitter) — done. Carries the `following: defaultdict(set)` storage and the rename-to-direction-you-traverse instinct.
- Concept: 2-hop BFS + `collections.Counter.most_common(k)`.
- Concept: per-edge timestamps + `bisect` for temporal queries (variant 1).
- Concept: `dict[k] -> set` shallow vs deep copy semantics + reverse-index construction (variant 2).

**When to do this:** week 3, after 09 (infection spread). Lighter algorithmically than 09. Heavier on **API hygiene** (the snapshot trap is a real signal).

**Honest framing:** despite the surface-level overlap with LC 355, your heap-merge tweet-feed skill **does not transfer** here. There are no tweets. The carry from LC 355 is graph storage + direction naming. The actual work is the 2-hop recommend and (per variant) the temporal layer or the snapshot semantics.
