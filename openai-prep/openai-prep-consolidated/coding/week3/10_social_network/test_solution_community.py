"""
Tests for CommunityGraph (union-find follow-up). Run:
  pytest coding/week3/10_social_network/test_solution_community.py -v

Tests are grouped:
  - empty / single-user state
  - basic unions and counters
  - duplicate / self-follow idempotency
  - same_community semantics
  - O(1) counter invariants
  - the example from problem_community.md
"""

import pytest
from solution_community import CommunityGraph


# ============================================================
# Empty / single-user state
# ============================================================


def test_empty_largest_community_size_is_zero():
    g = CommunityGraph()
    assert g.largest_community_size() == 0


def test_empty_num_communities_is_zero():
    g = CommunityGraph()
    assert g.num_communities() == 0


def test_unknown_user_community_size_is_zero():
    g = CommunityGraph()
    g.update("A", "B", 1)
    assert g.community_size("Z") == 0


def test_unknown_user_same_community_is_false():
    g = CommunityGraph()
    g.update("A", "B", 1)
    assert g.same_community("A", "Z") is False
    assert g.same_community("Z", "A") is False
    assert g.same_community("Y", "Z") is False


# ============================================================
# Basic unions and counters
# ============================================================


def test_single_edge_creates_one_community_of_two():
    g = CommunityGraph()
    g.update("A", "B", 1)
    assert g.num_communities() == 1
    assert g.largest_community_size() == 2
    assert g.community_size("A") == 2
    assert g.community_size("B") == 2


def test_disjoint_edges_create_separate_communities():
    g = CommunityGraph()
    g.update("A", "B", 1)
    g.update("C", "D", 2)
    g.update("E", "F", 3)
    assert g.num_communities() == 3
    assert g.largest_community_size() == 2


def test_chain_merges_into_one_community():
    g = CommunityGraph()
    g.update("A", "B", 1)
    g.update("B", "C", 2)
    g.update("C", "D", 3)
    assert g.num_communities() == 1
    assert g.largest_community_size() == 4
    assert g.community_size("A") == 4
    assert g.community_size("D") == 4


def test_merge_two_groups_via_bridge():
    g = CommunityGraph()
    # Group 1
    g.update("A", "B", 1)
    g.update("B", "C", 2)
    # Group 2
    g.update("X", "Y", 3)
    g.update("Y", "Z", 4)
    assert g.num_communities() == 2
    assert g.largest_community_size() == 3

    # bridge
    g.update("C", "X", 5)
    assert g.num_communities() == 1
    assert g.largest_community_size() == 6
    assert g.community_size("A") == 6
    assert g.community_size("Z") == 6


# ============================================================
# Direction is irrelevant for communities
# ============================================================


def test_direction_does_not_matter_for_community():
    g = CommunityGraph()
    g.update("A", "B", 1)   # A -> B
    g.update("C", "B", 2)   # C -> B  (not B -> C)
    # All three should be in the same weakly connected component
    assert g.num_communities() == 1
    assert g.largest_community_size() == 3


# ============================================================
# Idempotency: duplicate update, self-follow
# ============================================================


def test_duplicate_update_does_not_change_counters():
    g = CommunityGraph()
    g.update("A", "B", 1)
    before_num = g.num_communities()
    before_max = g.largest_community_size()
    g.update("A", "B", 2)   # duplicate
    g.update("A", "B", 3)   # duplicate
    assert g.num_communities() == before_num
    assert g.largest_community_size() == before_max


def test_redundant_edge_within_same_component_does_not_change_counters():
    g = CommunityGraph()
    g.update("A", "B", 1)
    g.update("B", "C", 2)
    # A, B, C already in same community; adding A->C is a no-op for DSU counters
    g.update("A", "C", 3)
    assert g.num_communities() == 1
    assert g.largest_community_size() == 3


def test_self_follow_makes_user_known_but_no_union():
    g = CommunityGraph()
    g.update("A", "A", 1)
    assert g.community_size("A") == 1
    assert g.num_communities() == 1
    assert g.largest_community_size() == 1


# ============================================================
# same_community semantics
# ============================================================


def test_same_community_true_for_directly_connected():
    g = CommunityGraph()
    g.update("A", "B", 1)
    assert g.same_community("A", "B") is True
    assert g.same_community("B", "A") is True


def test_same_community_true_for_transitively_connected():
    g = CommunityGraph()
    g.update("A", "B", 1)
    g.update("B", "C", 2)
    g.update("C", "D", 3)
    assert g.same_community("A", "D") is True


def test_same_community_false_for_disjoint():
    g = CommunityGraph()
    g.update("A", "B", 1)
    g.update("C", "D", 2)
    assert g.same_community("A", "C") is False
    assert g.same_community("B", "D") is False


def test_user_is_in_same_community_as_self_if_known():
    g = CommunityGraph()
    g.update("A", "B", 1)
    assert g.same_community("A", "A") is True


# ============================================================
# Mixed with Variant 1 check() — directed edges still work
# ============================================================


def test_check_still_works_on_directed_edges():
    g = CommunityGraph()
    g.update("A", "B", 5)
    assert g.check("A", "B", 5) is True
    assert g.check("A", "B", 4) is False
    assert g.check("B", "A", 100) is False   # direction matters for check


# ============================================================
# O(1) invariant — counters maintained, not scanned
# ============================================================


def test_num_communities_decreases_only_on_real_merge():
    g = CommunityGraph()
    g.update("A", "B", 1)   # 1
    assert g.num_communities() == 1
    g.update("C", "D", 2)   # 2
    assert g.num_communities() == 2
    g.update("A", "B", 3)   # duplicate, still 2
    assert g.num_communities() == 2
    g.update("B", "C", 4)   # merges -> 1
    assert g.num_communities() == 1
    g.update("A", "D", 5)   # already same component -> 1
    assert g.num_communities() == 1


def test_largest_community_size_is_monotone_nondecreasing():
    g = CommunityGraph()
    sizes_seen = []
    edges = [("A", "B", 1), ("C", "D", 2), ("E", "F", 3), ("B", "C", 4), ("D", "E", 5)]
    for a, b, t in edges:
        g.update(a, b, t)
        sizes_seen.append(g.largest_community_size())
    assert sizes_seen == sorted(sizes_seen)   # never decreases


# ============================================================
# Example from problem_community.md
# ============================================================


def test_problem_md_example():
    g = CommunityGraph()
    g.update("A", "B", 1)
    g.update("C", "D", 2)
    g.update("E", "F", 3)
    g.update("B", "C", 4)

    assert g.largest_community_size() == 4
    assert g.num_communities() == 2
    assert g.community_size("A") == 4
    assert g.community_size("E") == 2
    assert g.community_size("Z") == 0
    assert g.same_community("A", "D") is True
    assert g.same_community("A", "F") is False
    assert g.same_community("A", "Z") is False
