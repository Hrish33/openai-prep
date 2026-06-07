"""
Bare-bones (stdlib-only) variant of the out-of-order follow-up.

No sortedcontainers. Just `bisect` + parallel arrays.

Cost story to recite:
  - set: bisect_right is O(log n) to find the slot, BUT list.insert(idx, x)
    is O(n) because the tail of the array shifts right. Net: O(n) per set.
  - get: unchanged from the base, O(log n).

Same-timestamp last-write-wins:
  bisect_right inserts AFTER any equal element. So a second write at the
  same timestamp lands one slot to the right of the first — and
  `bisect_right(t) - 1` on the floor query lands on it. Free correctness.

Why parallel arrays instead of a list of (t, v) tuples?
  Python 3.9's bisect has NO `key=` parameter. To bisect a list of tuples
  by just timestamp, you'd need either (a) parallel arrays of bare ints
  (this file), or (b) construct a sentinel tuple at every bisect call site.
  (a) reads cleaner.
"""

import bisect
import collections


class TimeMap:
    def __init__(self) -> None:
        self._times = collections.defaultdict(list)
        self._values = collections.defaultdict(list)

    def set(self, key: str, value: str, timestamp: int) -> None:
        times = self._times[key]
        idx = bisect.bisect_right(times, timestamp)
        times.insert(idx, timestamp)
        self._values[key].insert(idx, value)

    def get(self, key: str, timestamp: int) -> str:
        times = self._times.get(key)
        if not times:
            return ""
        idx = bisect.bisect_right(times, timestamp) - 1
        if idx < 0:
            return ""
        return self._values[key][idx]
