"""
Tests for the out-of-order variant.
Run: pytest coding/week1/03_time_based_kv/test_solution_unordered.py -v

All base-problem tests should ALSO pass — out-of-order is a strict
superset of strictly-increasing.
"""

import pytest
from solution_concurrent import TimeMap


# --- Base tests should still pass (in-order writes) ---

def test_base_inorder_writes_still_work():
    tm = TimeMap()
    tm.set("foo", "bar", 1)
    tm.set("foo", "baz", 4)
    assert tm.get("foo", 1) == "bar"
    assert tm.get("foo", 4) == "baz"
    assert tm.get("foo", 5) == "baz"
    assert tm.get("foo", 0) == ""


def test_get_missing_key_returns_empty():
    tm = TimeMap()
    assert tm.get("missing", 1) == ""


def test_get_before_first_write_returns_empty():
    tm = TimeMap()
    tm.set("k", "v", 10)
    assert tm.get("k", 5) == ""


# --- Out-of-order writes (the documented variant) ---

def test_reverse_order_writes():
    """Write t=10 then t=5 — get(7) must return the t=5 value."""
    tm = TimeMap()
    tm.set("k", "later", 10)
    tm.set("k", "earlier", 5)
    assert tm.get("k", 7) == "earlier"   # floor of 7 is t=5
    assert tm.get("k", 10) == "later"    # exact match on t=10
    assert tm.get("k", 4) == ""          # before all writes


def test_interleaved_out_of_order():
    """Write t=10, t=5, t=15, t=8. Floor queries at each boundary."""
    tm = TimeMap()
    tm.set("k", "v10", 10)
    tm.set("k", "v5", 5)
    tm.set("k", "v15", 15)
    tm.set("k", "v8", 8)
    assert tm.get("k", 4) == ""
    assert tm.get("k", 5) == "v5"
    assert tm.get("k", 6) == "v5"
    assert tm.get("k", 8) == "v8"
    assert tm.get("k", 9) == "v8"
    assert tm.get("k", 10) == "v10"
    assert tm.get("k", 11) == "v10"
    assert tm.get("k", 15) == "v15"
    assert tm.get("k", 100) == "v15"


def test_problem_md_out_of_order_example():
    """Write t=10 then t=8 then t=9 — the example in the prereqs doc."""
    tm = TimeMap()
    tm.set("k", "ten", 10)
    tm.set("k", "eight", 8)
    tm.set("k", "nine", 9)
    assert tm.get("k", 7) == ""
    assert tm.get("k", 8) == "eight"
    assert tm.get("k", 9) == "nine"
    assert tm.get("k", 10) == "ten"


# --- Same-timestamp policy: last-write-wins ---

def test_same_timestamp_last_write_wins():
    """Two writes at the same timestamp — the LATER call should win on floor query.
    With bisect_right insertion, the second write inserts AFTER the first,
    so bisect_right(t) - 1 lands on the later one."""
    tm = TimeMap()
    tm.set("k", "first", 5)
    tm.set("k", "second", 5)
    assert tm.get("k", 5) == "second"
    assert tm.get("k", 10) == "second"


def test_same_timestamp_out_of_order_with_others():
    """t=10, t=5, then t=5 again. Floor at 5 is the LATER t=5 write."""
    tm = TimeMap()
    tm.set("k", "ten", 10)
    tm.set("k", "five-first", 5)
    tm.set("k", "five-second", 5)
    assert tm.get("k", 5) == "five-second"
    assert tm.get("k", 9) == "five-second"
    assert tm.get("k", 10) == "ten"


# --- Independent keys still independent ---

def test_keys_independent_under_out_of_order():
    tm = TimeMap()
    tm.set("a", "a10", 10)
    tm.set("b", "b5", 5)
    tm.set("a", "a3", 3)
    assert tm.get("a", 4) == "a3"
    assert tm.get("a", 10) == "a10"
    assert tm.get("b", 5) == "b5"
    assert tm.get("b", 10) == "b5"


# --- Scale check (insort is O(n) — these should still complete fast for n in the thousands) ---

def test_many_out_of_order_writes():
    """1000 writes in reverse order. Should still be correct (slow is OK; correctness is the bar)."""
    tm = TimeMap()
    for t in range(1000, 0, -1):       # reverse: 1000, 999, ..., 1
        tm.set("k", f"v{t}", t)
    assert tm.get("k", 1) == "v1"
    assert tm.get("k", 500) == "v500"
    assert tm.get("k", 1000) == "v1000"
    assert tm.get("k", 1500) == "v1000"
    assert tm.get("k", 0) == ""
