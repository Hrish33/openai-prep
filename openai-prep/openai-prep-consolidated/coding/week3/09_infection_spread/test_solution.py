"""
Tests for infection spread / cellular automata. Run:
  pytest coding/week3/09_infection_spread/test_solution.py -v

Grouped by part:
  Part 1 -> Part 2 -> Part 3 -> Part 4A (light coverage).

Encoding: 0 = healthy, 1 = infected, 2 = immune (Parts 2+).

Note: tests mutate copies of grids defensively. If your solution mutates
the input, that's fine — but expect to defend that choice in code review.
"""

import copy
import pytest
from solution import (
    time_to_full_infection,
    time_to_full_infection_with_immunity,
    time_to_stable_state,
    time_to_full_infection_threshold,
)


def g(grid):
    """Deep-copy helper so tests are independent of in-place mutation."""
    return copy.deepcopy(grid)


# ============================================================
# Part 1 — basic multi-source BFS
# ============================================================


def test_p1_single_source_2x2():
    grid = [[1, 0],
            [0, 0]]
    # day 1: (0,0) infects (0,1) and (1,0); day 2: those infect (1,1)
    assert time_to_full_infection(g(grid)) == 2


def test_p1_all_already_infected_returns_zero():
    grid = [[1, 1],
            [1, 1]]
    assert time_to_full_infection(g(grid)) == 0


def test_p1_no_sources_returns_minus_one():
    grid = [[0, 0],
            [0, 0]]
    assert time_to_full_infection(g(grid)) == -1


def test_p1_multiple_sources_spread_in_parallel():
    grid = [[1, 0, 0, 0, 1]]
    # day 1: (0,1) and (0,3); day 2: (0,2)
    assert time_to_full_infection(g(grid)) == 2


def test_p1_single_cell_infected_returns_zero():
    assert time_to_full_infection([[1]]) == 0


def test_p1_single_cell_healthy_returns_minus_one():
    assert time_to_full_infection([[0]]) == -1


def test_p1_row_spread():
    grid = [[1, 0, 0, 0, 0]]
    # Manhattan distance from (0,0) to (0,4) is 4
    assert time_to_full_infection(g(grid)) == 4


def test_p1_corner_to_opposite_corner():
    grid = [[1, 0, 0],
            [0, 0, 0],
            [0, 0, 0]]
    # Manhattan (0,0) -> (2,2) = 4
    assert time_to_full_infection(g(grid)) == 4


def test_p1_dense_sources_finish_in_one_day():
    grid = [[1, 0, 1],
            [0, 0, 0],
            [1, 0, 1]]
    # day 1: every 0 has a corner-adjacent... wait, corners are diagonals.
    # (0,1): neighbors (0,0)=1, (0,2)=1 -> infected day 1
    # (1,0): neighbors (0,0)=1, (2,0)=1 -> infected day 1
    # (1,2): neighbors (0,2)=1, (2,2)=1 -> infected day 1
    # (2,1): neighbors (2,0)=1, (2,2)=1 -> infected day 1
    # (1,1): no infected 4-neighbors initially -> infected day 2
    assert time_to_full_infection(g(grid)) == 2


# ============================================================
# Part 2 — immune cells (value 2)
# ============================================================


def test_p2_immune_blocks_spread_returns_minus_one():
    grid = [[1, 2, 0]]
    # (0,2) is walled off by immune at (0,1)
    assert time_to_full_infection_with_immunity(g(grid)) == -1


def test_p2_all_immune_returns_zero():
    grid = [[2, 2],
            [2, 2]]
    assert time_to_full_infection_with_immunity(g(grid)) == 0


def test_p2_immune_not_counted_as_target():
    grid = [[1, 2, 2, 2, 2]]
    # (0,0) infected, rest immune. No healthy cells exist. Return 0.
    assert time_to_full_infection_with_immunity(g(grid)) == 0


def test_p2_route_around_immune():
    grid = [[1, 2, 0],
            [0, 2, 0],
            [0, 0, 0]]
    # Path: (0,0) -> (1,0) -> (2,0) -> (2,1) -> (2,2) -> (1,2) -> (0,2)
    # That's 6 hops, so 6 days for the last cell.
    assert time_to_full_infection_with_immunity(g(grid)) == 6


def test_p2_no_sources_returns_minus_one():
    grid = [[0, 2, 0]]
    assert time_to_full_infection_with_immunity(g(grid)) == -1


def test_p2_no_sources_all_immune_returns_zero():
    grid = [[2, 2, 2]]
    assert time_to_full_infection_with_immunity(g(grid)) == 0


# ============================================================
# Part 3 — recovery -> immunity after D days
# ============================================================


def test_p3_d1_recovers_immediately_no_spread():
    grid = [[1, 0]]
    # D=1: day 1 tick, recover check: 1-0=1, >=1 yes. (0,0) becomes immune.
    # active is now empty. Return 1. (0,1) survives forever.
    assert time_to_stable_state(g(grid), D=1) == 1


def test_p3_d2_spreads_once_then_recovers():
    grid = [[1, 0]]
    # day 1: recover check 1-0>=2? no. spread (0,0)->(0,1). infection_day[(0,1)]=1.
    # day 2: recover (0,0) (2-0>=2). active={(0,1)}. spread: no healthy neighbors.
    # day 3: recover (0,1) (3-1>=2). active={}. Return 3.
    assert time_to_stable_state(g(grid), D=2) == 3


def test_p3_isolated_source_recovers_immediately():
    assert time_to_stable_state([[1]], D=1) == 1


def test_p3_no_initial_infection_returns_zero():
    grid = [[0, 0],
            [0, 0]]
    assert time_to_stable_state(g(grid), D=3) == 0


def test_p3_all_immune_returns_zero():
    grid = [[2, 2],
            [2, 2]]
    assert time_to_stable_state(g(grid), D=3) == 0


def test_p3_d_large_enough_to_cover_full_spread_then_all_recover():
    grid = [[1, 0, 0],
            [0, 0, 0],
            [0, 0, 0]]
    # D=10: nothing recovers during the spread phase.
    # Full infection completes at day 4 (Manhattan to (2,2)).
    # Last cell (2,2) infected on day 4, recovers on day 14 (14-4=10>=10).
    assert time_to_stable_state(g(grid), D=10) == 14


def test_p3_d3_basic_spread_then_recover():
    grid = [[1, 0, 0]]
    # day 1: spread (0,0)->(0,1), infection_day[(0,1)]=1
    # day 2: spread (0,0),(0,1)->(0,2), infection_day[(0,2)]=2. recover none (1-0<3, 2-0<3, no spread checks needed).
    #   actually recover check on day 2: (0,0) 2-0=2 <3 no. Spread proceeds.
    # day 3: recover (0,0) (3-0>=3). active={(0,1),(0,2)}. spread: no targets.
    # day 4: recover (0,1) (4-1>=3). active={(0,2)}.
    # day 5: recover (0,2) (5-2>=3). active={}.
    # Return 5.
    assert time_to_stable_state(g(grid), D=3) == 5


# ============================================================
# Part 4A — threshold spread (light coverage)
# ============================================================


def test_p4a_threshold_1_acts_like_part_1():
    grid = [[1, 0],
            [0, 0]]
    assert time_to_full_infection_threshold(g(grid), K=1) == 2


def test_p4a_threshold_2_requires_two_neighbors():
    grid = [[1, 0, 1],
            [0, 0, 0],
            [1, 0, 1]]
    # day 1 snapshot: each edge-midpoint has exactly 2 infected corner-neighbors.
    # day 2: (1,1) now has 4 infected neighbors, threshold met.
    assert time_to_full_infection_threshold(g(grid), K=2) == 2


def test_p4a_threshold_too_high_returns_minus_one():
    grid = [[1, 0, 1]]
    # (0,1) has 2 infected 4-neighbors. K=3 -> never reaches threshold.
    assert time_to_full_infection_threshold(g(grid), K=3) == -1


def test_p4a_no_sources_returns_minus_one():
    grid = [[0, 0, 0]]
    assert time_to_full_infection_threshold(g(grid), K=1) == -1


def test_p4a_all_infected_returns_zero():
    grid = [[1, 1, 1]]
    assert time_to_full_infection_threshold(g(grid), K=2) == 0
