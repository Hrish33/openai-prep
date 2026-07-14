# Prereqs — Problem 16: Minimum Strokes to Draw All Edges (Euler-trail decomposition)

This problem looks like graph traversal but the "minimum strokes" answer is a
**closed-form parity count** — you never actually build the trails. The whole
trick is recognizing the theorem. So the prereqs split into two buckets:

1. The plumbing you must be fluent in (components + degree counting).
2. The theory that gives you the formula (Euler paths / circuits).

---

## Concept 1 — Connected components (DSU or BFS/DFS)

The answer is computed **per connected component**, then summed. You need to
group vertices that are reachable through edges. Two standard tools:

- **Union-Find / DSU** — the cleaner fit here, because you're already iterating
  edges to count degrees. `union(u, v)` per edge, then bucket vertices by root.
- **BFS/DFS over an adjacency list** — also fine, but you build adjacency you
  don't otherwise need.

**Drill (do these until DSU is muscle memory):**
- LC 547 — Number of Provinces *(canonical DSU / components)*
- LC 323 — Number of Connected Components in an Undirected Graph *(if you have premium; otherwise 547 covers it)*
- LC 684 — Redundant Connection *(DSU with cycle detection — sharpens `find`/`union`)*

**When you can solve 547 with path-compression DSU in <8 min, move on.**

---

## Concept 2 — Degree counting & the handshake lemma

- The **degree** of a vertex = number of edge-endpoints touching it. Multi-edges
  each add to degree; a self-loop adds 2 (but this problem tells you to *ignore*
  self-loops entirely).
- **Handshake lemma:** the number of odd-degree vertices in any graph is always
  **even**. This is why `odd // 2` below is always a whole number — no rounding
  worries.

No LeetCode needed — just be certain you count degree by iterating edges and
incrementing both endpoints, *not* by `len(set(neighbors))` (that drops
multi-edges).

---

## Concept 3 — Euler paths & circuits (the theorem you're really tested on)

A **trail** is a walk that uses each edge at most once. A "stroke" in this
problem is exactly a trail. You want the **minimum number of trails** that
together cover every edge of a component.

The classic Euler results, for a **connected** component with ≥1 edge:

| Odd-degree vertices | What exists | Trails to cover all edges |
|---|---|---|
| 0 | Euler **circuit** (start = end) | **1** |
| 2 | Euler **path** (start ≠ end) | **1** |
| 2k (k ≥ 1) | neither | **k** = odd/2 |

So per component with edges: **`max(1, odd_degree_count // 2)`**.
(The `max(1, …)` handles the 0-odd circuit case, where `odd//2 == 0` but you
still need one stroke.) Sum over all components that contain at least one edge.
Edgeless components contribute 0.

**Why odd/2?** Each trail has exactly 2 endpoints (or 0, if it's a closed
circuit). Every odd-degree vertex *must* be the endpoint of some trail — you
can't pass through it cleanly because an odd number of edges leaves one stranded.
With 2k odd vertices you need k trails to absorb them as endpoints.

**Drill (to internalize Euler construction — Hierholzer's algorithm):**
- LC 332 — Reconstruct Itinerary *(the canonical Euler-path build; do this one)*
- LC 2097 — Valid Arrangement of Pairs *(Euler path on a directed graph; good stretch)*
- LC 753 — Cracking the Safe *(Euler circuit on a De Bruijn graph; hard, optional)*

You do **not** need Hierholzer to solve Problem 16 — the answer is pure parity
counting. But interviewers love the follow-up "now actually output one valid
stroke," and that *is* Hierholzer. Drill 332 so you're not caught flat.

---

## Suggested order & time budget

1. LC 547 (DSU components) — ~25 min
2. Re-derive the Euler table above from scratch on paper — ~15 min
3. LC 332 (Hierholzer, for the follow-up) — ~35 min
4. Then attempt `problem.md` cold.

**When you can (a) write path-compressed DSU from memory and (b) state the
`max(1, odd//2)` rule and explain *why* the odd vertices force endpoints,
attempt the problem.**
