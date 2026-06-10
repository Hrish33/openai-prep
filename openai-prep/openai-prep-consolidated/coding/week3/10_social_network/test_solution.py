"""
Tests for social network / follow graph. Run:
  pytest coding/week3/10_social_network/test_solution.py -v

Grouped by variant:
  Variant 1 (FollowGraph) -> Variant 2 (SocialNetwork + Snapshot).

If you're attempting one variant at a time, deselect the other:
  pytest ... -k "variant1"
  pytest ... -k "variant2"
"""

import pytest
from solution import FollowGraph, SocialNetwork, Snapshot


# ============================================================
# Variant 1 — FollowGraph (timestamped edges)
# ============================================================


# ---- update / check ----


def test_variant1_check_returns_false_for_unknown_users():
    g = FollowGraph()
    assert g.check("A", "B", 100) is False


def test_variant1_check_true_at_follow_time():
    g = FollowGraph()
    g.update("A", "B", 5)
    assert g.check("A", "B", 5) is True   # inclusive at t


def test_variant1_check_true_after_follow_time():
    g = FollowGraph()
    g.update("A", "B", 5)
    assert g.check("A", "B", 100) is True


def test_variant1_check_false_before_follow_time():
    g = FollowGraph()
    g.update("A", "B", 5)
    assert g.check("A", "B", 4) is False


def test_variant1_check_false_for_nonexistent_edge():
    g = FollowGraph()
    g.update("A", "B", 5)
    assert g.check("A", "C", 100) is False


def test_variant1_update_is_idempotent_earliest_t_wins():
    g = FollowGraph()
    g.update("A", "B", 10)
    g.update("A", "B", 5)        # earlier — should this update?
    g.update("A", "B", 20)       # later — should not move the clock
    # Spec: "earliest t wins" — once you start following, you've been following
    # since that earliest t. Either interpretation is defensible; pick one and
    # stick with it. We test "first call wins" here (simpler).
    assert g.check("A", "B", 9) is False   # first update was at t=10
    assert g.check("A", "B", 10) is True


def test_variant1_multiple_followers_independent():
    g = FollowGraph()
    g.update("A", "X", 1)
    g.update("B", "X", 5)
    assert g.check("A", "X", 1) is True
    assert g.check("B", "X", 1) is False
    assert g.check("B", "X", 5) is True


# ---- recommend ----


def test_variant1_recommend_basic_from_spec():
    """A → B → C, A → B → D, A → M → C — recommend(A) should rank C above D."""
    g = FollowGraph()
    g.update("A", "B", 1)
    g.update("A", "M", 1)
    g.update("B", "C", 1)
    g.update("B", "D", 1)
    g.update("M", "C", 1)
    result = g.recommend("A", 2)
    assert result == ["C", "D"]    # C has 2 intermediaries, D has 1


def test_variant1_recommend_excludes_self():
    """A → B → A: A should not recommend itself even though B follows it back."""
    g = FollowGraph()
    g.update("A", "B", 1)
    g.update("B", "A", 2)
    assert "A" not in g.recommend("A", 10)


def test_variant1_recommend_excludes_direct_follows():
    """A already follows C — recommend should not include C."""
    g = FollowGraph()
    g.update("A", "B", 1)
    g.update("A", "C", 1)
    g.update("B", "C", 1)
    assert "C" not in g.recommend("A", 10)


def test_variant1_recommend_top_k_limit():
    g = FollowGraph()
    g.update("A", "B", 1)
    # B follows X1..X5
    for x in ["X1", "X2", "X3", "X4", "X5"]:
        g.update("B", x, 1)
    result = g.recommend("A", 3)
    assert len(result) == 3
    assert all(x in {"X1", "X2", "X3", "X4", "X5"} for x in result)


def test_variant1_recommend_empty_for_isolated_user():
    g = FollowGraph()
    g.update("solo", "alone", 1)
    # solo's only followee (alone) follows nobody — no 2-hop candidates
    assert g.recommend("solo", 5) == []


def test_variant1_recommend_unknown_user_returns_empty():
    g = FollowGraph()
    assert g.recommend("ghost", 5) == []


def test_variant1_recommend_orders_by_intermediary_count():
    """Three candidates with different counts — they come back in count-desc order."""
    g = FollowGraph()
    # A follows B, M, N (three direct followees)
    g.update("A", "B", 1)
    g.update("A", "M", 1)
    g.update("A", "N", 1)
    # X is followed by all three (count 3)
    g.update("B", "X", 1)
    g.update("M", "X", 1)
    g.update("N", "X", 1)
    # Y is followed by two (count 2)
    g.update("B", "Y", 1)
    g.update("M", "Y", 1)
    # Z is followed by one (count 1)
    g.update("N", "Z", 1)
    result = g.recommend("A", 3)
    assert result == ["X", "Y", "Z"]


# ============================================================
# Variant 2 — SocialNetwork + Snapshot
# ============================================================


# ---- add_user / follow ----


def test_variant2_add_duplicate_user_raises():
    net = SocialNetwork()
    net.add_user("A")
    with pytest.raises(ValueError):
        net.add_user("A")


def test_variant2_follow_unknown_follower_raises():
    net = SocialNetwork()
    net.add_user("A")
    with pytest.raises(ValueError):
        net.follow("ghost", "A")


def test_variant2_follow_unknown_followee_raises():
    net = SocialNetwork()
    net.add_user("A")
    with pytest.raises(ValueError):
        net.follow("A", "ghost")


def test_variant2_self_follow_is_noop():
    net = SocialNetwork()
    net.add_user("A")
    net.follow("A", "A")
    snap = net.create_snapshot()
    assert snap.is_following("A", "A") is False


def test_variant2_duplicate_follow_is_noop():
    net = SocialNetwork()
    net.add_user("A")
    net.add_user("B")
    net.follow("A", "B")
    net.follow("A", "B")    # second call should not raise, should not duplicate
    snap = net.create_snapshot()
    assert snap.get_following("A") == ["B"]


# ---- snapshot immutability ----


def test_variant2_snapshot_immune_to_subsequent_follow():
    """The load-bearing requirement: live mutations don't bleed into snapshots."""
    net = SocialNetwork()
    for u in ["A", "B", "C"]:
        net.add_user(u)
    net.follow("A", "B")
    snap = net.create_snapshot()

    # Mutate the live graph AFTER snapshot:
    net.follow("A", "C")

    assert snap.is_following("A", "B") is True
    assert snap.is_following("A", "C") is False     # not reflected in snapshot
    assert sorted(snap.get_following("A")) == ["B"]


def test_variant2_two_snapshots_are_independent():
    net = SocialNetwork()
    for u in ["A", "B", "C", "D"]:
        net.add_user(u)
    net.follow("A", "B")
    snap1 = net.create_snapshot()

    net.follow("A", "C")
    snap2 = net.create_snapshot()

    net.follow("A", "D")

    assert sorted(snap1.get_following("A")) == ["B"]
    assert sorted(snap2.get_following("A")) == ["B", "C"]


def test_variant2_snapshot_is_following_basic():
    net = SocialNetwork()
    for u in ["A", "B", "C"]:
        net.add_user(u)
    net.follow("A", "B")
    snap = net.create_snapshot()
    assert snap.is_following("A", "B") is True
    assert snap.is_following("A", "C") is False
    assert snap.is_following("ghost", "B") is False


# ---- get_followers (reverse index) ----


def test_variant2_get_followers_basic():
    net = SocialNetwork()
    for u in ["A", "B", "C", "X"]:
        net.add_user(u)
    net.follow("A", "X")
    net.follow("B", "X")
    net.follow("C", "X")
    snap = net.create_snapshot()
    assert sorted(snap.get_followers("X")) == ["A", "B", "C"]


def test_variant2_get_followers_empty_for_isolated_user():
    net = SocialNetwork()
    net.add_user("hermit")
    snap = net.create_snapshot()
    assert snap.get_followers("hermit") == []


def test_variant2_get_followers_unknown_user_returns_empty():
    net = SocialNetwork()
    snap = net.create_snapshot()
    assert snap.get_followers("ghost") == []


# ---- recommend ----


def test_variant2_recommend_basic_from_spec():
    """A → B → C, A → B → D, A → M → C — recommend(A, 2) returns [C, D]."""
    net = SocialNetwork()
    for u in ["A", "B", "M", "C", "D"]:
        net.add_user(u)
    net.follow("A", "B")
    net.follow("A", "M")
    net.follow("B", "C")
    net.follow("B", "D")
    net.follow("M", "C")
    snap = net.create_snapshot()
    assert snap.recommend("A", 2) == ["C", "D"]


def test_variant2_recommend_excludes_self_and_direct_follows():
    net = SocialNetwork()
    for u in ["A", "B", "C"]:
        net.add_user(u)
    net.follow("A", "B")
    net.follow("A", "C")
    net.follow("B", "A")    # would-be self recommendation
    net.follow("B", "C")    # would-be direct-follow recommendation
    snap = net.create_snapshot()
    result = snap.recommend("A", 10)
    assert "A" not in result
    assert "C" not in result


def test_variant2_recommend_empty_when_no_candidates():
    net = SocialNetwork()
    for u in ["A", "B"]:
        net.add_user(u)
    net.follow("A", "B")
    snap = net.create_snapshot()
    # B follows nobody — no 2-hop candidates for A
    assert snap.recommend("A", 5) == []


def test_variant2_recommend_top_k_limit():
    net = SocialNetwork()
    for u in ["A", "B"] + [f"X{i}" for i in range(5)]:
        net.add_user(u)
    net.follow("A", "B")
    for i in range(5):
        net.follow("B", f"X{i}")
    snap = net.create_snapshot()
    result = snap.recommend("A", 3)
    assert len(result) == 3
