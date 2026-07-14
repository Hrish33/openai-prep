"""
Social network / follow graph. Two API variants.

Read problem.md first. Sketch BEFORE coding:
  - For BOTH variants: write down the three exclusion clauses for recommend.
    (Not yourself. Not anyone you already follow. The rest get a Counter bump.)
  - Variant 1: what's the minimal per-edge state to answer check(A, B, t)?
  - Variant 2: at what depth do you copy the adjacency dict in create_snapshot?
    (One level: outer dict + new sets for values. Not deepcopy.)
  - Variant 2: when do you build the reverse index for get_followers?
    (Eagerly in the Snapshot constructor.)

Pick ONE variant per attempt. Don't do both in the same session.
"""
import collections
from collections import Counter, defaultdict
from operator import add
from typing import Optional


# ============================================================
# Variant 1 — Timestamped edges
# ============================================================


class FollowGraph:
    """Append-only follow graph with per-edge timestamps and temporal queries."""

    def __init__(self) -> None:
        self.graph = collections.defaultdict(dict)


    def update(self, A: str, B: str, t: int) -> None:
        """A starts following B at time t. No-op if A already follows B
        (earliest t wins)."""
        if B in self.graph[A]:
            return
        self.graph[A][B] = t

    def check(self, A: str, B: str, t: int) -> bool:
        """True iff A had an outgoing follow edge to B with start time <= t."""
        # your code here
        if A not in self.graph :
            return False
        if B not in self.graph[A]:
            return False
        return self.graph[A][B] <= t

    def recommend(self, A: str, k: int) -> list[str]:
        """Top-k 2-hop friend-of-friend suggestions.
        Rank by number of intermediaries (people in A's direct follows
        who also follow the candidate).
        Exclude A itself and anyone A already follows.
        Tie-break by lex order (or any reasonable deterministic tiebreak).
        """
        # your code here
        counter = Counter()
        friends = set(self.graph[A].keys())

        for friend in friends:
            for next_friend in self.graph[friend].keys():
                if next_friend in friends or next_friend == A :
                    continue
                counter[next_friend] += 1

        return [k for k, v in sorted(counter.items(), key = lambda kv : (-kv[1], kv[0]))[:k]]





# ============================================================
# Variant 2 — Snapshot-based
# ============================================================


class SocialNetwork:
    """Mutable follow graph that hands out immutable Snapshots on demand."""

    def __init__(self) -> None:
        # your code here
        self.graph = {}

    def add_user(self, user_id: str) -> None:
        """Raises ValueError if the user already exists."""
        # your code here
        if user_id in self.graph :
            raise ValueError
        self.graph[user_id] = set()

    def follow(self, follower: str, followee: str) -> None:
        """Raises ValueError if either user is missing.
        Self-follow is a no-op. Duplicate follow is a no-op."""
        if follower == followee:
            return
        if follower not in self.graph :
            raise ValueError
        if followee in self.graph[follower]:
            return
        self.graph[follower],add(followee)


    def create_snapshot(self) -> "Snapshot":
        """Returns an immutable view. Subsequent follow() calls must NOT
        affect this snapshot — one-level deep copy of the adjacency dict.
        Don't use copy.deepcopy; the `{u: set(fs) for u, fs in d.items()}`
        comprehension is the right depth and ~10x faster.
        """
        # your code here
        return Snapshot(self.graph)


class Snapshot:
    """Immutable read-only view of a SocialNetwork at a point in time."""

    def __init__(self, following: dict[str, set[str]]) -> None:
        """The caller (SocialNetwork.create_snapshot) is responsible for
        passing a freshly-copied adjacency dict. The Snapshot eagerly builds
        the reverse follower index here so get_followers is O(F)."""
        # your code here
        self.graph = {}
        for node, edges in following :
            self.graph[node] = set(edges)


    def is_following(self, follower: str, followee: str) -> bool:
        if follower == followee:
            return False
        if follower not in self.graph :
            raise ValueError
        return followee in self.graph[follower]


    def get_following(self, user_id: str) -> list[str]:
        # your code here
        return self.graph.get(user_id, [])

    def get_followers(self, user_id: str) -> list[str]:
        """Efficient (O(F)) via the eager reverse index built in __init__."""
        # your code here
        raise NotImplementedError

    def recommend(self, user_id: str, k: int) -> list[str]:
        """Same shape as FollowGraph.recommend. Three exclusion clauses."""
        # your code here
        raise NotImplementedError
