# Problem 16: Minimum Strokes to Draw All Edges (Min Trails)

**Prereqs:** See `00_prereqs.md`. You need DSU/components fluency and the Euler
path/circuit parity theorem. Do *not* peek at `interviewer_notes.md` first.

**Time budget:** 35 min. This is a "do you know the theorem" problem — if you
know it, it's 20 min; if you don't, no amount of coding saves you.
**Stage:** Phone screen / early onsite. Graph theory + clean component handling.

---

## Problem

You are given an **undirected** graph where vertices are points and edges are
line segments that must be drawn. A single **stroke** starts at any vertex and
continuously traverses edges to draw them, with the constraint that **each edge
must be drawn exactly once overall**. You may revisit vertices, but you may not
traverse (draw) an edge more than once.

Compute the **minimum number of strokes** required to draw all edges.

(In graph terms: partition all edges into the fewest possible **trails**.)

---

## Input (stdin)

```
First line:   two integers  n m   (number of vertices and edges)
Next m lines: two integers  u v   (0-indexed) — one undirected edge
```

## Output (stdout)

```
One integer: the minimum number of strokes.
```

## Required API

For local testing, implement:

```python
def min_strokes(n: int, edges: list[tuple[int, int]]) -> int: ...
```

…and wire `__main__` to read stdin / print the result (the harness format above).

---

## Constraints

- `1 <= n <= 2e5`
- `0 <= m <= 2e5`
- **Multi-edges may exist** — two vertices can be joined by several edges, and
  each is a distinct segment to draw.
- **Ignore self-loops** (`u == v`) if present.
- The graph **may be disconnected**.

---

## Sample tests

| Input | Output | Why |
|---|---|---|
| `3 2` / `0 1` / `1 2` | `1` | Path; 2 odd vertices → 1 trail |
| `4 2` / `0 1` / `2 3` | `2` | Two separate edges → 2 components → 2 |
| `4 3` / `0 1` / `1 2` / `2 0` | `1` | Triangle; all even → Euler circuit → 1 |
| `5 4` / `0 1` / `1 2` / `2 3` / `3 4` | `1` | Path of 5; 2 odd ends → 1 |
| `6 3` / `0 1` / `0 2` / `0 3` | `2` | Star; 4 odd vertices → 4/2 = 2 |

---

## The rule (this is the whole problem)

Process **per connected component**. A component with no edges needs **0**
strokes. For a component with at least one edge, let `k` = number of
odd-degree vertices in it. Then:

```
strokes(component) = max(1, k // 2)
```

- `k == 0` → an Euler **circuit** exists → 1 stroke.
- `k == 2` → an Euler **path** exists → 1 stroke.
- `k == 2j` (j ≥ 1) → j strokes.

Sum over all components that contain edges. (By the handshake lemma `k` is always
even, so `k // 2` is exact.)

---

## What an OpenAI interviewer is looking for

1. **Theorem recognition, stated up front.** Before coding, say: "minimum trails
   to cover a connected component = `max(1, odd_degree/2)`; sum over components."
   If you start writing Hierholzer to *build* the trails, you've over-engineered —
   you only need to count.
2. **Correct degree counting under multi-edges.** Increment both endpoints per
   edge. Do not dedupe neighbors.
3. **Self-loop handling.** Skip `u == v` cleanly and early.
4. **Component bucketing.** DSU is the tightest fit since you're already looping
   edges. Only count components that actually have edges — isolated vertices and
   edgeless components contribute 0.
5. **The `max(1, …)` subtlety.** The 0-odd (pure cycle) case still costs 1
   stroke even though `odd // 2 == 0`. Missing this is the #1 bug.
6. **Linear complexity.** O(n + m) with near-constant DSU. At n, m = 2e5 anything
   worse than near-linear is suspect.

---

## Follow-ups (don't peek until base passes)

<details>
<summary>Click to expand</summary>

1. **Output an actual stroke.** "Now print one valid sequence of edges for a
   single-stroke component." → **Hierholzer's algorithm** (LC 332). The counting
   answer tells you *how many* trails; Hierholzer constructs them.

2. **Output all the trails**, not just the count, for a multi-trail component.
   Pair up odd vertices, (conceptually) add virtual edges to make everything
   even, run Hierholzer, then cut at the virtual edges. Discuss; coding it is a
   20-min extension.

3. **Self-loops count instead of ignored.** A self-loop adds 2 to degree (even,
   so it never creates an endpoint) and forces the component to need ≥1 stroke.
   How does the formula change? (A lone self-loop component: 0 odd vertices but
   has an edge → 1 stroke. The `max(1, …)` already covers it once you stop
   skipping loops.)

4. **Weighted "ink" / Chinese Postman.** If you must traverse every edge but
   *may* repeat edges to return to start in a single stroke, minimizing total
   length, that's the **Route Inspection / Chinese Postman** problem — a
   different (matching-based) animal. Know the name and that it's where this
   family leads.

5. **Streaming edges / huge m.** Edges arrive one at a time and don't fit in
   memory. You can still maintain DSU + a degree-parity bit per vertex online,
   and recompute the sum at the end. What state is truly needed? (Per vertex: its
   DSU root and a single parity bit. Per root: whether it has any edge.)

6. **Dynamic edges (add/remove).** Adding edges: DSU + parity flips are easy
   (union-by + toggle two parity bits). Removal breaks DSU — discuss why
   (DSU has no efficient delete) and what you'd reach for (Euler-tour trees /
   link-cut trees) if pressed.

</details>

---

## Honest difficulty note

**This is a knowledge problem, not a coding problem.** The implementation is
~25 lines of DSU + a counting loop. The entire signal is whether you *know* the
Euler trail decomposition rule and can justify the `odd/2`.

Common ways it goes wrong:
- **Forgetting `max(1, …)`** → cycles and circuits report 0 strokes. (Most common.)
- **Counting edgeless/isolated vertices** as components → over-counts.
- **Deduping multi-edges** in degree calc → wrong parity.
- **Not skipping self-loops** → wrong degrees (and the spec explicitly says ignore).
- Over-engineering into Hierholzer when only the count is asked.

If you don't know the theorem, the right move in a real interview is to say so,
then reason it out from "each trail has 2 endpoints, odd vertices must be
endpoints" — interviewers reward deriving it live over a blank stare.
