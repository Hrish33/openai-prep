"""
Minimum Strokes to Draw All Edges (Min Trails) — see problem.md.

This is a parity-counting problem, NOT a traversal problem. You do not build
the trails; you count them.

Sketch BEFORE coding:
  - Per connected component with >=1 edge: strokes = max(1, odd_degree // 2).
  - Sum over components that have edges. Edgeless/isolated vertices: 0.
  - Suggested tooling: DSU (you're already looping edges) + a degree array.
    1. For each edge (u, v): skip if u == v; else deg[u]+=1, deg[v]+=1, union(u, v).
    2. Bucket every vertex with deg > 0 by find(root): mark the root has an edge,
       and tally how many of its vertices have odd degree.
    3. For each root that has an edge: total += max(1, odd[root] // 2).
  - Watch the max(1, ...): a pure cycle has 0 odd vertices but still costs 1 stroke.
  - Multi-edges count (don't dedupe). Self-loops are ignored (spec).
"""

import sys


def min_strokes(n: int, edges: list[tuple[int, int]]) -> int:
    # Return the minimum number of strokes (trails) to draw every edge.
    raise NotImplementedError


def main() -> None:
    data = sys.stdin.buffer.read().split()
    if not data:
        return
    it = iter(data)
    n = int(next(it))
    m = int(next(it))
    edges = [(int(next(it)), int(next(it))) for _ in range(m)]
    print(min_strokes(n, edges))


if __name__ == "__main__":
    main()
