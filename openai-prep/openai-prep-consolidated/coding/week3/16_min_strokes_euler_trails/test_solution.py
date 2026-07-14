"""
Tests for min_strokes. Run:
  pytest coding/week3/16_min_strokes_euler_trails/test_solution.py -v
"""

import pytest

from solution import min_strokes


# ---- The five provided samples ----

def test_sample1_path_two_odd():
    assert min_strokes(3, [(0, 1), (1, 2)]) == 1


def test_sample2_two_disconnected_edges():
    assert min_strokes(4, [(0, 1), (2, 3)]) == 2


def test_sample3_triangle_euler_circuit():
    assert min_strokes(4, [(0, 1), (1, 2), (2, 0)]) == 1


def test_sample4_long_path():
    assert min_strokes(5, [(0, 1), (1, 2), (2, 3), (3, 4)]) == 1


def test_sample5_star_four_odd():
    assert min_strokes(6, [(0, 1), (0, 2), (0, 3)]) == 2


# ---- Empty / degenerate ----

def test_no_edges():
    assert min_strokes(5, []) == 0


def test_single_vertex_no_edges():
    assert min_strokes(1, []) == 0


def test_single_edge():
    assert min_strokes(2, [(0, 1)]) == 1


# ---- Self-loops are ignored ----

def test_self_loop_ignored():
    # The only "edge" is a self-loop -> no real edges -> 0 strokes.
    assert min_strokes(3, [(0, 0)]) == 0


def test_self_loop_mixed_with_real_edge():
    # Self-loop ignored; remaining is one real edge.
    assert min_strokes(3, [(1, 1), (0, 1)]) == 1


# ---- Multi-edges count toward degree ----

def test_double_edge_makes_circuit():
    # Two parallel edges 0-1: deg 0=2, 1=2 -> 0 odd -> 1 stroke.
    assert min_strokes(2, [(0, 1), (0, 1)]) == 1


def test_triple_edge_two_odd():
    # Three parallel edges 0-1: deg 0=3, 1=3 -> 2 odd -> 1 stroke.
    assert min_strokes(2, [(0, 1), (0, 1), (0, 1)]) == 1


# ---- Component bucketing ----

def test_isolated_vertices_do_not_count():
    # Vertices 2,3,4 are isolated; only the 0-1 edge component counts.
    assert min_strokes(5, [(0, 1)]) == 1


def test_circuit_plus_path():
    # Component A: triangle 0-1-2 (Euler circuit -> 1).
    # Component B: path 3-4-5    (2 odd -> 1).
    edges = [(0, 1), (1, 2), (2, 0), (3, 4), (4, 5)]
    assert min_strokes(6, edges) == 2


def test_two_stars():
    # Two separate 4-odd stars -> 2 + 2 = 4.
    edges = [(0, 1), (0, 2), (0, 3), (4, 5), (4, 6), (4, 7)]
    assert min_strokes(8, edges) == 4


def test_square_with_one_diagonal():
    # 0-1-2-3-0 cycle plus diagonal 0-2.
    # deg: 0=3, 2=3, 1=2, 3=2 -> 2 odd -> 1 stroke.
    edges = [(0, 1), (1, 2), (2, 3), (3, 0), (0, 2)]
    assert min_strokes(4, edges) == 1


def test_complete_graph_k4():
    # K4: every vertex degree 3 -> 4 odd vertices -> 4/2 = 2 strokes.
    edges = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]
    assert min_strokes(4, edges) == 2


def test_complete_graph_k5_euler_circuit():
    # K5: every vertex degree 4 (even) -> 0 odd -> 1 stroke.
    edges = [(a, b) for a in range(5) for b in range(a + 1, 5)]
    assert min_strokes(5, edges) == 1


# ---- Scale smoke test ----

def test_long_path_scale():
    # A path of N vertices has exactly 2 odd ends -> 1 stroke, regardless of N.
    n = 100_000
    edges = [(i, i + 1) for i in range(n - 1)]
    assert min_strokes(n, edges) == 1
