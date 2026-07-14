# Interviewer notes — Problem 16 (read AFTER your attempt)

## Reference solution

```python
import sys


def min_strokes(n: int, edges: list[tuple[int, int]]) -> int:
    parent = list(range(n))

    def find(x: int) -> int:
        # Path-halving find — near-O(1) amortized.
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    deg = [0] * n
    for u, v in edges:
        if u == v:            # spec: ignore self-loops
            continue
        deg[u] += 1
        deg[v] += 1
        union(u, v)

    # Per component root: how many odd-degree vertices, and does it have edges.
    odd = {}
    has_edge = set()
    for x in range(n):
        if deg[x] > 0:
            r = find(x)
            has_edge.add(r)
            if deg[x] & 1:
                odd[r] = odd.get(r, 0) + 1

    total = 0
    for r in has_edge:
        total += max(1, odd.get(r, 0) // 2)
    return total
```

**Complexity:** O(n + m·α(n)) time, O(n) space. At n, m = 2e5 this is instant.

## Why this is the shape it is

- **DSU over BFS/DFS** because the edge loop is doing double duty: counting
  degrees *and* unioning. No adjacency list needed, so memory stays O(n).
- **The two collections (`odd`, `has_edge`)** separate two questions that are
  easy to conflate: "does this component need a stroke at all?" (has_edge) and
  "how many trails for it?" (odd-count). A component can have edges with *zero*
  odd vertices (a cycle) — that's exactly the case `max(1, 0)` rescues.
- **`deg[x] & 1`** instead of `% 2` — same thing, just the idiom you'll see in
  competitive code. `% 2` is equally fine; don't let anyone tell you it matters.

## The core theorem (be ready to justify, not just recite)

Minimum trails to cover all edges of a **connected** graph with `k` odd-degree
vertices:
- `k = 0`: Euler circuit exists → **1**.
- `k = 2`: Euler path exists → **1**.
- `k = 2j`: **j**.

**Live derivation if you blank:** every trail has exactly two endpoints (or zero,
if closed). An odd-degree vertex *cannot* be an interior pass-through point — each
time you pass through you use 2 of its edges, so an odd count always strands one
edge that must start or end a trail there. So every odd vertex is forced to be a
trail endpoint. With `2j` odd vertices and 2 endpoints per trail, you need at
least `j` trails — and `j` is achievable. Hence `max(1, k/2)`.

## Honest weaknesses to acknowledge

- The reference iterates all `n` vertices in the bucketing pass. If `n` is huge
  but `m` is tiny, you're scanning empty vertices. Easy fix: collect the set of
  touched vertices during the edge loop and iterate only those. Mention it; it's
  a micro-optimization, not a correctness issue.
- DSU here uses union-by-nothing (always `parent[ra] = rb`). Path-halving alone
  keeps it effectively flat, but union-by-rank/size is the textbook completion if
  the interviewer pushes on worst-case trees.

## Self-grading against the OpenAI rubric

| Axis | Strong attempt looks like |
|---|---|
| Practical problem-solving | States the parity theorem before coding; doesn't reach for Hierholzer |
| Edge-case discipline up front | Names self-loops, multi-edges, isolated vertices, and the `max(1,…)` cycle case *before* writing code |
| Layered optimization | Base O(n+m); offers the "iterate touched vertices only" refinement when n≫m |
| Python internals depth | Comfortable with DSU path-halving; can discuss why `dict.get` default beats `defaultdict` import here (or vice versa) |
| Targeted optimization under follow-up | Pivots to Hierholzer (LC 332) for "output a stroke"; names Chinese Postman for the weighted variant |
| Test quality | Tests cover cycle-vs-path, multi-edge, self-loop, disconnected mix, K4/K5 parity |

## Follow-up sketches

**"Output one valid stroke for a single-stroke component" → Hierholzer:**

```python
def euler_trail(adj: dict[int, list[int]], start: int) -> list[int]:
    # adj: vertex -> stack of neighbors (each undirected edge appears twice;
    # remove its twin when consumed in a real impl). Returns vertex sequence.
    stack, trail = [start], []
    while stack:
        v = stack[-1]
        if adj[v]:
            u = adj[v].pop()
            # (in a full impl, also remove v from adj[u] to mark edge used)
            stack.append(u)
        else:
            trail.append(stack.pop())
    return trail[::-1]
```

Start at an odd-degree vertex if one exists (Euler path), else any vertex (Euler
circuit). This is why LC 332 is the listed precursor.

**"Self-loops count" variant:** stop skipping `u == v`; add 2 to `deg[u]` and
mark the component has an edge. Parity is unaffected (loops add even degree), but
a lone-self-loop component now correctly costs 1 — already handled by `max(1,…)`.

## Common mistakes interviewers see

1. **Reporting 0 for a cycle/circuit** — forgot `max(1, …)`. The single most
   common failure.
2. **Deduping multi-edges** (`set(adj[v])`) → wrong parity → wrong answer.
3. **Counting isolated vertices** as components → over-count.
4. **Building full Hierholzer** for the count question → out of time, no payoff.
5. **Off-by-one in handshake reasoning** — trying `(k+1)//2` or `ceil(k/2)`;
   it's exactly `k//2` because `k` is always even.
