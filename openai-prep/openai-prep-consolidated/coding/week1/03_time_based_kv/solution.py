"""
Time-based key-value store.

Read 00_prereqs.md (the floor idiom + the out-of-order follow-up), then
problem.md. Sketch your data structure before coding.

Suggested structure (you don't have to follow this — design what makes
sense to you):
  - dict: key -> a list kept sorted by timestamp
  - per key, either two parallel lists (times[], values[]) or one list of
    (timestamp, value) tuples — know the trade-off (see interviewer_notes.md)
  - `set`: append (base case — timestamps strictly increasing per key)
  - `get`: bisect_right on the timestamps, minus 1, to find the floor

Reach for `bisect` from the stdlib. Do NOT linear-scan in `get`.
"""

import bisect
import collections


class TimeMap:
    def __init__(self) -> None:
        self._times = collections.defaultdict(list)
        self._values = collections.defaultdict(list)

    def set(self, key: str, value: str, timestamp: int) -> None:
        self._times[key].append(timestamp)
        self._values[key].append(value)

    def get(self, key: str, timestamp: int) -> str:
        times = self._times.get(key)
        if not times:
            return ""
        index = bisect.bisect_right(times, timestamp) - 1
        if index < 0:
            return ""
        return self._values[key][index]
