"""
Tests for get_range — the generator-shaped follow-up.
Run: pytest coding/week1/03_time_based_kv/test_solution_range.py -v
"""

import types
import pytest
from solution_range import TimeMap


def _make(items):
    """Helper: build a TimeMap from a list of (key, value, timestamp)."""
    tm = TimeMap()
    for k, v, t in items:
        tm.set(k, v, t)
    return tm


# --- Base set/get still works (must not break the existing API) ---

def test_base_set_get_still_work():
    tm = TimeMap()
    tm.set("k", "v1", 1)
    tm.set("k", "v2", 5)
    assert tm.get("k", 1) == "v1"
    assert tm.get("k", 5) == "v2"
    assert tm.get("k", 0) == ""


# --- get_range basics ---

def test_get_range_returns_generator_not_list():
    """The whole point of this follow-up. Must be lazy."""
    tm = _make([("k", "v1", 1), ("k", "v2", 5)])
    result = tm.get_range("k", 0, 10)
    assert isinstance(result, types.GeneratorType)


def test_get_range_empty_when_no_matches():
    tm = _make([("k", "v1", 10), ("k", "v2", 20)])
    assert list(tm.get_range("k", 0, 5)) == []      # all writes after t2
    assert list(tm.get_range("k", 30, 50)) == []    # all writes before t1


def test_get_range_missing_key_yields_nothing():
    tm = TimeMap()
    assert list(tm.get_range("missing", 0, 100)) == []


def test_get_range_returns_ascending_order():
    tm = _make([("k", "v1", 1), ("k", "v2", 5), ("k", "v3", 10)])
    assert list(tm.get_range("k", 0, 100)) == [(1, "v1"), (5, "v2"), (10, "v3")]


# --- Inclusive-bounds boundary (the bisect_left vs bisect_right trap) ---

def test_get_range_lower_bound_is_inclusive():
    """t1 = 5, and there's a write at exactly t=5. It must be included."""
    tm = _make([("k", "v1", 1), ("k", "v5", 5), ("k", "v10", 10)])
    assert list(tm.get_range("k", 5, 10)) == [(5, "v5"), (10, "v10")]


def test_get_range_upper_bound_is_inclusive():
    """t2 = 10, and there's a write at exactly t=10. It must be included."""
    tm = _make([("k", "v1", 1), ("k", "v5", 5), ("k", "v10", 10)])
    assert list(tm.get_range("k", 1, 10)) == [(1, "v1"), (5, "v5"), (10, "v10")]


def test_get_range_both_bounds_exact_matches():
    tm = _make([("k", "v1", 1), ("k", "v5", 5), ("k", "v10", 10)])
    assert list(tm.get_range("k", 1, 10)) == [(1, "v1"), (5, "v5"), (10, "v10")]


def test_get_range_single_point():
    """t1 == t2 — only the exact-match write."""
    tm = _make([("k", "v1", 1), ("k", "v5", 5), ("k", "v10", 10)])
    assert list(tm.get_range("k", 5, 5)) == [(5, "v5")]


def test_get_range_single_point_no_match():
    """t1 == t2 but no write at that timestamp."""
    tm = _make([("k", "v1", 1), ("k", "v5", 5)])
    assert list(tm.get_range("k", 3, 3)) == []


# --- Lazy consumption (generator semantics) ---

def test_get_range_can_be_consumed_one_at_a_time():
    """next() should yield one value without exhausting the generator."""
    tm = _make([("k", f"v{i}", i) for i in range(100)])
    gen = tm.get_range("k", 0, 100)
    first = next(gen)
    assert first == (0, "v0")
    # second next should give (1, "v1") — generator state preserved
    second = next(gen)
    assert second == (1, "v1")


def test_get_range_break_early_doesnt_iterate_rest():
    """A consumer that breaks early should not pay for the rest.
    We can't directly measure this without internals, but we can verify
    the for-break pattern works."""
    tm = _make([("k", f"v{i}", i) for i in range(1000)])
    found = None
    for ts, value in tm.get_range("k", 0, 1000):
        if value == "v42":
            found = (ts, value)
            break
    assert found == (42, "v42")


# --- Independent keys ---

def test_get_range_only_for_requested_key():
    tm = TimeMap()
    tm.set("a", "a1", 1)
    tm.set("a", "a2", 5)
    tm.set("b", "b1", 1)
    tm.set("b", "b2", 5)
    assert list(tm.get_range("a", 0, 10)) == [(1, "a1"), (5, "a2")]
    assert list(tm.get_range("b", 0, 10)) == [(1, "b1"), (5, "b2")]
