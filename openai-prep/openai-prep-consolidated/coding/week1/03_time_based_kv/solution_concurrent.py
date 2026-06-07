"""
Follow-up #2: thread safety.

`set` and `get` must be safe under concurrent calls from multiple threads.

The crucial insight to articulate BEFORE coding:

  This is a state-management problem, NOT a coordination problem.
  Unlike the crawler (problem 8) which has a work queue, termination
  protocol, and workers spawning work — here there's no orchestration.
  The whole job is mutual exclusion over shared mutable state.

  The depth lives in three places:
    (a) Granularity: state is partitioned by key → global lock can be
        replaced by per-key striping later, or RWLock if reads dominate.
    (b) The read path is NOT free. `get`'s `bisect + index lookup` is
        multiple bytecodes — the GIL does NOT make it atomic against a
        concurrent `append`. "Reads are safe because of the GIL" is
        WRONG. Say this out loud.
    (c) The critical section has no I/O. So the crawler's "never hold
        a lock during I/O" bug can't happen here.

The concurrency ladder, recited:

    Global lock          ← THIS file (simple, correct, every key contends)
    Per-key lock striping  ← next rung (dict[key] -> Lock; writes to
                              different keys proceed in parallel)
    Reader/writer lock   ← reads dominate time-series stores; allow many
                            concurrent readers, exclusive writer. Python
                            has no stdlib RWLock — build from Condition.

Implement the FIRST rung in this file. Just a `threading.Lock` around
both `set` and `get`. Both. The point of the exercise is to internalize
that `get` needs it too.

API is the same as the base. Tests stress it with many threads.
"""

import bisect  # noqa: F401
import collections  # noqa: F401
import itertools
import threading  # noqa: F401

class TimeMap:
    def __init__(self) -> None:
        # records[key] = sorted list of (timestamp, seq, value)
        self.BUCKETS = 16
        self.locks = [threading.Lock() for _ in range(self.BUCKETS)]
        self.times = collections.defaultdict(list)
        self.values = collections.defaultdict(list)

    def set(self, key: str, value: str, timestamp: int) -> None:
        lock = self.locks[key.__hash__() % self.BUCKETS]
        with lock:
            times = self.times[key]
            values = self.values[key]
            idx = bisect.bisect_right(self.times[key], timestamp)
            times.insert(idx, timestamp)
            values.insert(idx, value)

    def get(self, key: str, timestamp: int) -> str:
        lock = self.locks[key.__hash__() % self.BUCKETS]
        with lock:
            times = self.times.get(key)
            if not times:
                return ""
            idx = bisect.bisect_right(times, timestamp)
            if idx == 0:
                return ""
            return self.values[key][idx-1]