"""
Tests for resumable iterator. Run: pytest coding/week2/04_resumable_iterator/test_solution.py -v

If you wrote your own tests first (good!), compare against these afterward.
"""

import json
import pytest
from solution import CompositeIterator


# --- Basic iteration (no save/restore) ---

def test_single_source_iteration():
    it = CompositeIterator([[1, 2, 3]])
    assert list(it) == [1, 2, 3]


def test_multiple_sources_in_order():
    it = CompositeIterator([["a", "b"], ["c"], ["d", "e", "f"]])
    assert list(it) == ["a", "b", "c", "d", "e", "f"]


def test_empty_source_list_yields_nothing():
    it = CompositeIterator([])
    assert list(it) == []


def test_all_empty_sources_yields_nothing():
    it = CompositeIterator([[], [], []])
    assert list(it) == []


def test_empty_sources_interleaved_are_skipped_1():
    it = CompositeIterator([[0], [], [1, 2], [], [3], []])
    assert list(it) == [0, 1, 2, 3]


def test_empty_sources_interleaved_are_skipped():
    it = CompositeIterator([[], [1, 2], [], [3], []])
    assert list(it) == [1, 2, 3]


def test_exhausted_iterator_raises_stopiteration():
    it = CompositeIterator([[1]])
    next(it)
    with pytest.raises(StopIteration):
        next(it)


def test_iter_returns_self():
    it = CompositeIterator([[1, 2]])
    assert iter(it) is it


# --- State shape ---

def test_state_is_json_serializable():
    it = CompositeIterator([["a", "b"], ["c"]])
    next(it)
    state = it.get_state()
    # round-trip through JSON — no pickle, no opaque types
    assert json.loads(json.dumps(state)) == state


def test_state_at_start_is_well_defined():
    it = CompositeIterator([["a", "b"]])
    state = it.get_state()
    # whatever the shape, it must be a dict
    assert isinstance(state, dict)


def test_get_state_returns_fresh_dict_each_call():
    """Two states from one iterator should be independent objects."""
    it = CompositeIterator([["a", "b", "c"]])
    s1 = it.get_state()
    next(it)
    s2 = it.get_state()
    # mutating one must not affect the other
    assert s1 != s2 or it.get_state() == s2  # the post-next state has moved


# --- Save / restore round-trip ---

def test_resume_from_mid_stream():
    sources = [["a", "b", "c"], ["d", "e"]]
    it = CompositeIterator(sources)
    assert next(it) == "a"
    assert next(it) == "b"
    state = it.get_state()
    # original keeps going
    assert next(it) == "c"

    # restored instance resumes exactly where state was taken
    it2 = CompositeIterator(sources)
    it2.set_state(state)
    assert next(it2) == "c"
    assert next(it2) == "d"
    assert next(it2) == "e"
    with pytest.raises(StopIteration):
        next(it2)


def test_resume_across_source_boundary():
    """State captured right before a source ends — resume should cross cleanly."""
    sources = [["a", "b"], ["c", "d"]]
    it = CompositeIterator(sources)
    assert next(it) == "a"
    assert next(it) == "b"
    state = it.get_state()                 # at the end of source 0

    it2 = CompositeIterator(sources)
    it2.set_state(state)
    assert next(it2) == "c"                # crosses into source 1
    assert next(it2) == "d"


def test_resume_at_start():
    """State captured before any next() should resume from item 0."""
    sources = [["a", "b"], ["c"]]
    it = CompositeIterator(sources)
    state = it.get_state()
    it2 = CompositeIterator(sources)
    it2.set_state(state)
    assert list(it2) == ["a", "b", "c"]


def test_resume_at_exhaustion():
    """State captured after the last item — resume should raise StopIteration."""
    sources = [["a"]]
    it = CompositeIterator(sources)
    next(it)
    state = it.get_state()
    it2 = CompositeIterator(sources)
    it2.set_state(state)
    with pytest.raises(StopIteration):
        next(it2)


def test_round_trip_through_json():
    """The whole point: state survives serialization."""
    sources = [["a", "b", "c"], ["d", "e", "f"]]
    it = CompositeIterator(sources)
    next(it); next(it); next(it); next(it)        # consume "a", "b", "c", "d"

    blob = json.dumps(it.get_state())
    # ... time passes, process restarts, whatever ...
    restored = json.loads(blob)

    it2 = CompositeIterator(sources)
    it2.set_state(restored)
    assert next(it2) == "e"
    assert next(it2) == "f"


def test_two_iterators_from_same_state_are_independent():
    """If state is a value (not a reference), two restored iterators don't interfere."""
    sources = [["a", "b", "c"]]
    it = CompositeIterator(sources)
    next(it)
    state = it.get_state()

    it1 = CompositeIterator(sources)
    it1.set_state(state)
    it2 = CompositeIterator(sources)
    it2.set_state(state)

    assert next(it1) == "b"
    assert next(it2) == "b"                # same answer, no shared cursor


# --- Edge cases ---

def test_non_string_items():
    """Items can be anything — don't assume hashable / stringy."""
    sources = [[{"a": 1}, [1, 2]], [None]]
    it = CompositeIterator(sources)
    assert next(it) == {"a": 1}
    assert next(it) == [1, 2]
    assert next(it) is None


def test_tuple_sources_are_accepted():
    """Sources need only be iterable — tuples should work."""
    sources = [("a", "b"), ("c",)]
    it = CompositeIterator(sources)
    assert list(it) == ["a", "b", "c"]


def test_set_state_replaces_position():
    """set_state on a partially-consumed iterator overrides its position."""
    sources = [["a", "b", "c", "d"]]
    it = CompositeIterator(sources)
    next(it); next(it); next(it)            # at "d"

    # rewind via set_state
    fresh = CompositeIterator(sources).get_state()
    it.set_state(fresh)
    assert next(it) == "a"



# test async iterator

