"""
Follow-up #1: out-of-order writes (the documented variant).

The base `solution.py` exploits the guarantee that `set` is called with
strictly-increasing timestamps per key — so `append` keeps the list
sorted for free, in O(1). This guarantee is the very first thing a
real interviewer removes.

Now `set("foo", "old", 10)` then `set("foo", "older", 8)` must work,
and `get("foo", 9)` must return "older" — the floor of 9 is t=8.
Naive `append` is now a bug: the list is no longer sorted, and `bisect`
in `get` will read garbage.

The fix: insert in sorted position. `bisect.insort` is the stdolib tool.
For parallel arrays, that's bisect_right to find the position, then
.insert into BOTH arrays at the same index — keeps them aligned.

Things worth saying out loud (and saying in code comments):

  1. `bisect.insort` (and `list.insert`) is O(n). The binary search finds
     the position in O(log n) but doesn't save you from the array shift.
     Don't claim insort is "O(log n)" — interviewers will probe.

  2. If out-of-order writes are frequent and per-key histories are large,
     you'd switch to `sortedcontainers.SortedList` (≈O(log n) insert) or
     a balanced BST / skip list. Plain Python lists give O(1) append but
     O(n) arbitrary insert. State the ladder.

  3. Same-timestamp policy: with `bisect_right`, a re-write at an
     existing timestamp inserts AFTER the old one, so the floor query
     naturally returns the newer write (last-write-wins). Document it
     as a deliberate choice, not an accident.

  4. `get` is UNCHANGED from the base — the list is still sorted, just
     not by insertion order. Same bisect_right - 1 with the < 0 guard.
"""

import bisect  # noqa: F401
import collections  # noqa: F401

import sortedcontainers
from pygments.lexer import default
from sortedcontainers import SortedKeyList


class TimeMap:
    def __init__(self) -> None:
        # your code here
        self.store = collections.defaultdict(sortedcontainers.SortedKeyList(key = lambda x: x[0]))

    def set(self, key: str, value: str, timestamp: int) -> None:
        self.store[key].append((timestamp, value))


    def get(self, key: str, timestamp: int) -> str:

        if key not in self.store:
            return ""
        index = SortedKeyList.bisect_right(self.store[key], timestamp)
        return "" if index == 0 else self.store[key][index - 1][1]

