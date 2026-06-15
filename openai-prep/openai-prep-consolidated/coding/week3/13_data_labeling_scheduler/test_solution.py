"""Tests for the Data Labeling Task Scheduler. Run: pytest test_solution.py -v"""

from __future__ import annotations

from collections import Counter
from typing import Iterable, List, Tuple

import pytest

from solution import (
    Assignment,
    build_balanced_schedule,
    build_basic_schedule,
)


# ----- verifier helpers -------------------------------------------------------


def _basic_invariants(
    schedule: List[Assignment],
    t: int,
    m: int,
    h: int,
    k: int,
) -> None:
    """Assert Part 1 invariants.

    - length is exactly h * k
    - every (task, model, human) lies in range
    - every human appears >= k times
    - (task, human) pairs are unique
    """
    assert len(schedule) == h * k
    for task, model, human in schedule:
        assert 0 <= task < t, f'task {task} out of range [0, {t})'
        assert 0 <= model < m, f'model {model} out of range [0, {m})'
        assert 0 <= human < h, f'human {human} out of range [0, {h})'

    human_count = Counter(human for _, _, human in schedule)
    for u in range(h):
        assert human_count[u] >= k, f'human {u} has only {human_count[u]} rows; needs >= {k}'

    task_human_pairs = [(task, human) for task, _, human in schedule]
    assert len(task_human_pairs) == len(set(task_human_pairs)), '(task, human) collision'


def _prefix_balanced(
    schedule: List[Assignment],
    t: int,
    m: int,
    h: int,
) -> None:
    """Assert Part 2 invariants: per-task model and human counts max-min <= 1 at every prefix.

    Tasks that haven't appeared in the prefix yet are vacuously balanced
    (all-zero counters).
    """
    # per-task model counts: task -> [count_model_0, ..., count_model_{m-1}]
    model_counts = [[0] * m for _ in range(t)]
    human_counts = [[0] * h for _ in range(t)]
    seen_tasks: set[int] = set()

    for i, (task, model, human) in enumerate(schedule):
        model_counts[task][model] += 1
        human_counts[task][human] += 1
        seen_tasks.add(task)

        for x in seen_tasks:
            mc = model_counts[x]
            assert max(mc) - min(mc) <= 1, (
                f'after row {i}: task {x} model counts {mc} violate balance'
            )
            hc = human_counts[x]
            assert max(hc) - min(hc) <= 1, (
                f'after row {i}: task {x} human counts {hc} violate balance'
            )


# ----- Part 1: build_basic_schedule ------------------------------------------


def test_basic_simple_shape():
    out = build_basic_schedule(t=4, m=2, h=3, k=2)
    _basic_invariants(out, t=4, m=2, h=3, k=2)


def test_basic_k_equals_t():
    out = build_basic_schedule(t=3, m=2, h=2, k=3)
    _basic_invariants(out, t=3, m=2, h=2, k=3)
    # Each human covers every task exactly once.
    for u in range(2):
        tasks_for_u = {task for task, _, human in out if human == u}
        assert tasks_for_u == {0, 1, 2}


def test_basic_each_human_quota_met():
    out = build_basic_schedule(t=5, m=3, h=4, k=3)
    _basic_invariants(out, t=5, m=3, h=4, k=3)
    counts = Counter(u for _, _, u in out)
    for u in range(4):
        assert counts[u] >= 3


def test_basic_task_human_uniqueness():
    out = build_basic_schedule(t=4, m=2, h=4, k=4)
    _basic_invariants(out, t=4, m=2, h=4, k=4)
    seen = set()
    for task, _, human in out:
        assert (task, human) not in seen
        seen.add((task, human))


def test_basic_k_zero_returns_empty_list():
    assert build_basic_schedule(t=3, m=2, h=2, k=0) == []


def test_basic_k_greater_than_t_returns_none():
    assert build_basic_schedule(t=2, m=2, h=3, k=3) is None


def test_basic_zero_tasks_returns_none():
    assert build_basic_schedule(t=0, m=2, h=2, k=1) is None


def test_basic_zero_models_returns_none():
    assert build_basic_schedule(t=3, m=0, h=2, k=1) is None


def test_basic_zero_humans_returns_none():
    assert build_basic_schedule(t=3, m=2, h=0, k=1) is None


def test_basic_single_human_single_round():
    out = build_basic_schedule(t=3, m=2, h=1, k=1)
    _basic_invariants(out, t=3, m=2, h=1, k=1)
    assert len(out) == 1


# ----- Part 2: build_balanced_schedule ---------------------------------------


def test_balanced_simple_shape():
    out = build_balanced_schedule(t=4, m=2, h=3, k=2)
    _basic_invariants(out, t=4, m=2, h=3, k=2)
    _prefix_balanced(out, t=4, m=2, h=3)


def test_balanced_k_equals_t():
    out = build_balanced_schedule(t=3, m=2, h=2, k=3)
    _basic_invariants(out, t=3, m=2, h=2, k=3)
    _prefix_balanced(out, t=3, m=2, h=2)


def test_balanced_m_equals_one_trivially_balanced():
    out = build_balanced_schedule(t=4, m=1, h=3, k=2)
    _basic_invariants(out, t=4, m=1, h=3, k=2)
    _prefix_balanced(out, t=4, m=1, h=3)
    assert all(model == 0 for _, model, _ in out)


def test_balanced_h_equals_one():
    out = build_balanced_schedule(t=4, m=3, h=1, k=3)
    _basic_invariants(out, t=4, m=3, h=1, k=3)
    _prefix_balanced(out, t=4, m=3, h=1)


def test_balanced_k_zero_returns_empty_list():
    assert build_balanced_schedule(t=3, m=2, h=2, k=0) == []


def test_balanced_k_greater_than_t_returns_none():
    assert build_balanced_schedule(t=2, m=2, h=3, k=3) is None


def test_balanced_zero_tasks_returns_none():
    assert build_balanced_schedule(t=0, m=2, h=2, k=1) is None


def test_balanced_zero_models_returns_none():
    assert build_balanced_schedule(t=3, m=0, h=2, k=1) is None


def test_balanced_zero_humans_returns_none():
    assert build_balanced_schedule(t=3, m=2, h=0, k=1) is None


def test_balanced_holds_at_every_prefix_random_size():
    out = build_balanced_schedule(t=5, m=3, h=4, k=4)
    _basic_invariants(out, t=5, m=3, h=4, k=4)
    _prefix_balanced(out, t=5, m=3, h=4)


def test_balanced_minimal_length():
    """Output is exactly h * k rows — no wasted assignments."""
    out = build_balanced_schedule(t=6, m=4, h=3, k=5)
    assert len(out) == 3 * 5


def test_balanced_many_models_few_appearances():
    """When a task is scheduled fewer than m times, all model counts are 0 or 1."""
    out = build_balanced_schedule(t=5, m=10, h=3, k=2)
    _basic_invariants(out, t=5, m=10, h=3, k=2)
    _prefix_balanced(out, t=5, m=10, h=3)
    # Per-task model count diff trivially <= 1.
    model_counts: dict[int, Counter] = {x: Counter() for x in range(5)}
    for task, model, _ in out:
        model_counts[task][model] += 1
    for x, mc in model_counts.items():
        if mc:
            assert max(mc.values()) - min(mc.values()) <= 1


# ----- combined / scenario ---------------------------------------------------


def test_spec_part_one_example():
    out = build_basic_schedule(t=4, m=2, h=3, k=2)
    assert len(out) == 6
    humans = [u for _, _, u in out]
    assert all(humans.count(u) >= 2 for u in range(3))
    assert len({(task, u) for task, _, u in out}) == 6  # all unique


def test_spec_part_two_small_trace():
    """Confirm the (t=2, m=2, h=2, k=2) trace from problem.md is balanced."""
    out = build_balanced_schedule(t=2, m=2, h=2, k=2)
    _basic_invariants(out, t=2, m=2, h=2, k=2)
    _prefix_balanced(out, t=2, m=2, h=2)
    assert len(out) == 4


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
