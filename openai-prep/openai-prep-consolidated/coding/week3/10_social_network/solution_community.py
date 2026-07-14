"""
Communities via Union-Find — follow-up to Variant 1.

Reference solution. Read problem_community.md for the spec.

Design choices baked in:
  - Undirected union: update(A, B, t) unions regardless of direction.
  - Union-by-size + iterative two-pass path compression in _find.
  - max_size and num_components maintained INSIDE _union (and _ensure for
    the first-user singleton case) so largest_community_size() and
    num_communities() are O(1) — no scan over roots.
  - Lazy user registration via _ensure: users appear in the DSU the first
    time they show up in an update() call.
  - V1's check() is preserved on the directed graph; the DSU is a separate,
    parallel structure over the same node set.
"""

from collections import defaultdict


class CommunityGraph:
    """Append-only follow graph with weakly-connected-component queries via DSU."""

    def __init__(self) -> None:
        # Variant 1 directed-edge state (for check)
        self.graph: dict[str, dict[str, int]] = defaultdict(dict)

        # DSU forest
        self.parent: dict[str, str] = {}
        self.size: dict[str, int] = {}      # only meaningful at roots

        # O(1) global counters — maintained in _ensure / _union
        self.max_size: int = 0
        self.num_components: int = 0

    # ---- DSU primitives ----

    def _ensure(self, user: str) -> None:
        if user in self.parent:
            return
        self.parent[user] = user
        self.size[user] = 1
        self.num_components += 1
        if self.max_size < 1:
            self.max_size = 1

    def _find(self, user: str) -> str:
        root = user
        while self.parent[root] != root:
            root = self.parent[root]
        # two-pass path compression: point every node on the path at root
        while self.parent[user] != root:
            nxt = self.parent[user]
            self.parent[user] = root
            user = nxt
        return root

    def _union(self, a: str, b: str) -> None:
        ra, rb = self._find(a), self._find(b)
        if ra == rb:
            return
        # union by size: bigger root absorbs smaller
        if self.size[ra] < self.size[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        self.size[ra] += self.size[rb]
        if self.size[ra] > self.max_size:
            self.max_size = self.size[ra]
        self.num_components -= 1

    # ---- Variant 1 API ----

    def update(self, A: str, B: str, t: int) -> None:
        self._ensure(A)
        if A == B:
            return                          # self-follow: known user, no union, no edge
        self._ensure(B)
        if B not in self.graph[A]:
            self.graph[A][B] = t            # first-write wins (matches V1)
        self._union(A, B)                   # idempotent on already-merged pairs

    def check(self, A: str, B: str, t: int) -> bool:
        if A not in self.graph or B not in self.graph[A]:
            return False
        return self.graph[A][B] <= t

    # ---- Community queries ----

    def largest_community_size(self) -> int:
        return self.max_size

    def num_communities(self) -> int:
        return self.num_components

    def community_size(self, user: str) -> int:
        if user not in self.parent:
            return 0
        return self.size[self._find(user)]

    def same_community(self, A: str, B: str) -> bool:
        if A not in self.parent or B not in self.parent:
            return False
        return self._find(A) == self._find(B)
