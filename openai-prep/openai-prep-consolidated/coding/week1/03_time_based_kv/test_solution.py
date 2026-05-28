"""
Tests for the time-based key-value store.
Run: pytest coding/week1/03_time_based_kv/test_solution.py -v

If you wrote your own tests first (good!), compare against these afterward.
These cover the BASE problem only (strictly-increasing timestamps per key).
The follow-ups (out-of-order writes, concurrency, retention) get their own
tests when you implement them — see interviewer_notes.md.
"""

import pytest
from solution import TimeMap


# --- Basic set / get ---

def test_set_then_get_exact_timestamp():
    tm = TimeMap()
    tm.set("foo", "bar", 1)
    assert tm.get("foo", 1) == "bar"


def test_get_after_write_returns_floor():
    tm = TimeMap()
    tm.set("foo", "bar", 1)
    assert tm.get("foo", 3) == "bar"  # largest timestamp <= 3 is t=1


def test_get_picks_latest_at_or_before():
    tm = TimeMap()
    tm.set("foo", "bar", 1)
    tm.set("foo", "baz", 4)
    assert tm.get("foo", 4) == "baz"  # exact match on the later write
    assert tm.get("foo", 5) == "baz"  # floor of 5 is t=4
    assert tm.get("foo", 3) == "bar"  # floor of 3 is t=1


# --- Empty / missing cases (must return "") ---

def test_get_before_any_write_returns_empty():
    tm = TimeMap()
    tm.set("foo", "bar", 5)
    assert tm.get("foo", 4) == ""  # query is before the only write


def test_get_at_zero_returns_empty():
    tm = TimeMap()
    tm.set("foo", "bar", 1)
    assert tm.get("foo", 0) == ""


def test_get_missing_key_returns_empty():
    tm = TimeMap()
    assert tm.get("does_not_exist", 1) == ""


def test_get_missing_key_after_other_writes():
    tm = TimeMap()
    tm.set("foo", "bar", 1)
    assert tm.get("other", 10) == ""


# --- Exact-match boundary (the bisect_left vs bisect_right trap) ---

def test_exact_match_returns_that_write_not_the_previous():
    """If query t equals a stored timestamp, return THAT write."""
    tm = TimeMap()
    tm.set("k", "v1", 10)
    tm.set("k", "v2", 20)
    tm.set("k", "v3", 30)
    assert tm.get("k", 20) == "v2"   # exact hit, not v1
    assert tm.get("k", 10) == "v1"   # exact hit on the first
    assert tm.get("k", 30) == "v3"   # exact hit on the last


def test_query_between_writes():
    tm = TimeMap()
    tm.set("k", "v1", 10)
    tm.set("k", "v2", 30)
    assert tm.get("k", 20) == "v1"   # floor of 20 is t=10
    assert tm.get("k", 29) == "v1"
    assert tm.get("k", 31) == "v2"


# --- Multiple independent keys ---

def test_keys_are_independent():
    tm = TimeMap()
    tm.set("a", "a1", 1)
    tm.set("b", "b1", 1)
    tm.set("a", "a2", 5)
    assert tm.get("a", 5) == "a2"
    assert tm.get("b", 5) == "b1"   # b unaffected by a's writes
    assert tm.get("b", 1) == "b1"


def test_many_keys_many_versions():
    tm = TimeMap()
    for t in range(1, 101):
        tm.set("k", f"v{t}", t)
    assert tm.get("k", 1) == "v1"
    assert tm.get("k", 50) == "v50"
    assert tm.get("k", 100) == "v100"
    assert tm.get("k", 1000) == "v100"   # floor of a far-future query
    assert tm.get("k", 0) == ""


# --- Integration sequence (mirrors the problem.md example) ---

def test_problem_example_sequence():
    tm = TimeMap()
    tm.set("foo", "bar", 1)
    assert tm.get("foo", 1) == "bar"
    assert tm.get("foo", 3) == "bar"
    tm.set("foo", "baz", 4)
    assert tm.get("foo", 4) == "baz"
    assert tm.get("foo", 5) == "baz"
    assert tm.get("foo", 0) == ""
    assert tm.get("nope", 1) == ""


def test_repeated_reads_are_stable():
    """Reads don't mutate; the same query returns the same answer."""
    tm = TimeMap()
    tm.set("k", "v1", 1)
    tm.set("k", "v2", 10)
    for _ in range(5):
        assert tm.get("k", 5) == "v1"
        assert tm.get("k", 10) == "v2"


# --- Value semantics ---

def test_values_are_returned_verbatim():
    tm = TimeMap()
    tm.set("k", "complex value 123", 1)
    assert tm.get("k", 1) == "complex value 123"


def test_same_value_different_timestamps():
    tm = TimeMap()
    tm.set("k", "same", 1)
    tm.set("k", "same", 5)
    assert tm.get("k", 3) == "same"
    assert tm.get("k", 5) == "same"
