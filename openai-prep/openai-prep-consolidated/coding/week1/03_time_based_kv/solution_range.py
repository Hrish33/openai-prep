"""
Follow-up #3: range query as a generator.

Adds one new method:

    get_range(key, t1, t2) -> Iterator[tuple[int, str]]

Returns all (timestamp, value) pairs for `key` where `t1 <= timestamp <= t2`,
in ascending timestamp order. Both bounds INCLUSIVE.

The whole point of this follow-up is the GENERATOR shape — you don't
materialize a list, you `yield` each pair one at a time. Connects
directly to the streaming pattern from problem 2.

Two implementation insights worth saying out loud:

  1. TWO bisects bound the slice.
       lo = bisect_left(times, t1)    # first index where times[i] >= t1
       hi = bisect_right(times, t2)   # first index where times[i] > t2
     The slice [lo, hi) is exactly the matching range. O(log n) to find,
     O(k) to iterate (where k = number of results).

  2. Why bisect_LEFT for the lower bound and bisect_RIGHT for the upper?
     Because both bounds are INCLUSIVE. bisect_left lands you on (or
     before) an exact match of t1; bisect_right lands you *after* an
     exact match of t2. The slice [lo, hi) then includes both.
     Get this wrong and exact-match queries silently drop the boundary
     value — a classic off-by-one.

  3. Generator vs list: don't materialize. The caller can consume one
     pair at a time, break early, compose with other generators.
     This is the same idiom as problem 2's deserialize_stream.

Keep `set` and `get` the same as the base. Just add `get_range`.
"""

import bisect  # noqa: F401
import collections  # noqa: F401
from typing import Iterator, Tuple


class TimeMap:
    def __init__(self) -> None:
        # your code here — same parallel arrays as the base
        self.times = collections.defaultdict(list)
        self.values = collections.defaultdict(list)


    def set(self, key: str, value: str, timestamp: int) -> None:
        # your code here — same as base
        self.times[key].append(timestamp)
        self.values[key].append(value)

    def get(self, key: str, timestamp: int) -> str:
        times = self.times.get(key)
        if not times:
            return ""
        index = bisect.bisect_right(times, timestamp)
        if index == 0:
            return ""
        return self.values[key][index - 1]

    def get_range(self, key: str, t1: int, t2: int) -> Iterator[Tuple[int, str]]:
        if t1 > t2:
            t1, t2 = t2, t1

        times = self.times.get(key)
        if not times:
            return

        left = bisect.bisect_left(times, t1)
        right = bisect.bisect_right(times, t2)

        values = self.values[key]
        for i in range(left, right):
            yield times[i], values[i]