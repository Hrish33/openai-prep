"""
Variant: stdlib bisect over a list of tuples (no sortedcontainers,
no parallel arrays).

The trick: bisect uses tuple comparison, which is element-by-element.
So we don't need `key=` (which 3.9 lacks) — we just bisect with a
sentinel tuple that lands at the right boundary.

  bisect_right(records, (t, +inf, +inf))  ← first slot AFTER any (t, ?, ?)

The third element (a monotonic counter) is the tiebreaker for same-
timestamp last-write-wins. Without it, tuple comparison falls through
to comparing the VALUES (strings), which silently breaks LWW.

Cost is identical to the parallel-arrays variant:
  - set: O(log n) bisect + O(n) list.insert. Net O(n).
  - get: O(log n).

When you'd reach for this shape vs parallel arrays:
  - You'd ship parallel arrays in code. Cleaner.
  - You'd reach for this on a whiteboard if you forget about the 3.9
    bisect-key limitation and want to keep one list of tuples.
"""

import bisect
import collections


class TimeMap:
    def __init__(self) -> None:
        # records[key] = sorted list of (timestamp, seq, value)
        self._records = collections.defaultdict(list)
        self._seq = 0

    def set(self, key: str, value: str, timestamp: int) -> None:
        self._seq += 1
        entry = (timestamp, self._seq, value)
        records = self._records[key]
        idx = bisect.bisect_right(records, entry)
        records.insert(idx, entry)

    def get(self, key: str, timestamp: int) -> str:
        records = self._records.get(key)
        if not records:
            return ""
        # Sentinel that lands just after the largest entry with this timestamp.
        idx = bisect.bisect_right(records, (timestamp, float('inf'), '')) - 1
        if idx < 0:
            return ""
        return records[idx][2]
