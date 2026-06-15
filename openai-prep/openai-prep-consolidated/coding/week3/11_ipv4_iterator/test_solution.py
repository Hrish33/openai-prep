"""
Tests for IPV4Iterator. Run:
  pytest coding/week3/11_ipv4_iterator/test_solution.py -v

Tests are grouped by part to mirror the progressive reveal in the real interview.
Use -k to scope to one part at a time:
  pytest ... -k "part1"
  pytest ... -k "part2"
  pytest ... -k "part3"
  pytest ... -k "part4"
  pytest ... -k "part5a"   # containment branch
  pytest ... -k "part5b"   # to_cidrs branch

Part 5 has two reported branches; you may only see one in a real interview.
Pick one to drill per session.
"""

import pytest

from solution import IPV4Iterator


# ============================================================
# Part 1 — Bare IPv4, forward iteration
# ============================================================


def test_part1_iter_returns_self():
    it = IPV4Iterator("0.0.0.0")
    assert iter(it) is it


def test_part1_starts_at_supplied_ip():
    it = IPV4Iterator("10.0.0.5")
    assert next(it) == "10.0.0.5"


def test_part1_advances_by_one():
    it = IPV4Iterator("10.0.0.5")
    assert next(it) == "10.0.0.5"
    assert next(it) == "10.0.0.6"
    assert next(it) == "10.0.0.7"


def test_part1_starts_at_zero():
    it = IPV4Iterator("0.0.0.0")
    assert next(it) == "0.0.0.0"
    assert next(it) == "0.0.0.1"


def test_part1_rollover_within_octet():
    it = IPV4Iterator("192.168.0.255")
    assert next(it) == "192.168.0.255"
    assert next(it) == "192.168.1.0"


def test_part1_rollover_multi_octet():
    it = IPV4Iterator("10.0.255.255")
    assert next(it) == "10.0.255.255"
    assert next(it) == "10.1.0.0"


def test_part1_max_ip_yields_then_stops():
    it = IPV4Iterator("255.255.255.255")
    assert next(it) == "255.255.255.255"
    with pytest.raises(StopIteration):
        next(it)


def test_part1_for_loop_consumes_finite_range():
    # Manually stop after a few iterations — full iteration is 2^32 calls.
    it = IPV4Iterator("255.255.255.250")
    collected = list(it)
    assert collected == [
        "255.255.255.250",
        "255.255.255.251",
        "255.255.255.252",
        "255.255.255.253",
        "255.255.255.254",
        "255.255.255.255",
    ]


# ============================================================
# Part 2 — Reverse mode
# ============================================================


def test_part2_reverse_default_false_matches_part1():
    it = IPV4Iterator("10.0.0.5", reverse=False)
    assert next(it) == "10.0.0.5"
    assert next(it) == "10.0.0.6"


def test_part2_reverse_walks_down():
    it = IPV4Iterator("10.0.0.5", reverse=True)
    assert next(it) == "10.0.0.5"
    assert next(it) == "10.0.0.4"
    assert next(it) == "10.0.0.3"


def test_part2_reverse_underflow_across_subnet():
    it = IPV4Iterator("192.168.1.0", reverse=True)
    assert next(it) == "192.168.1.0"
    assert next(it) == "192.168.0.255"


def test_part2_reverse_underflow_multi_octet():
    it = IPV4Iterator("10.1.0.0", reverse=True)
    assert next(it) == "10.1.0.0"
    assert next(it) == "10.0.255.255"


def test_part2_reverse_at_zero_yields_then_stops():
    it = IPV4Iterator("0.0.0.0", reverse=True)
    assert next(it) == "0.0.0.0"
    with pytest.raises(StopIteration):
        next(it)


def test_part2_reverse_from_max():
    it = IPV4Iterator("255.255.255.255", reverse=True)
    assert next(it) == "255.255.255.255"
    assert next(it) == "255.255.255.254"


def test_part2_reverse_collects_finite_range():
    it = IPV4Iterator("0.0.0.5", reverse=True)
    assert list(it) == [
        "0.0.0.5",
        "0.0.0.4",
        "0.0.0.3",
        "0.0.0.2",
        "0.0.0.1",
        "0.0.0.0",
    ]


# ============================================================
# Part 3 — CIDR form
# ============================================================


def test_part3_slash_32_yields_one_ip():
    it = IPV4Iterator("192.168.0.5/32")
    assert list(it) == ["192.168.0.5"]


def test_part3_slash_31_from_broadcast_yields_one():
    # /31 block at seed=5: network=4, broadcast=5. Iteration starts at seed=5,
    # forward — so only the broadcast IP is in [seed, broadcast].
    it = IPV4Iterator("192.168.0.5/31")
    assert list(it) == ["192.168.0.5"]


def test_part3_slash_31_from_network_address():
    # Same /31 block, but seed is the network address now.
    it = IPV4Iterator("192.168.0.4/31")
    assert list(it) == ["192.168.0.4", "192.168.0.5"]


def test_part3_slash_30_forward_from_seed():
    # /30 block at seed=5: network=4, broadcast=7. Forward yields 5, 6, 7.
    it = IPV4Iterator("192.168.0.5/30")
    assert list(it) == ["192.168.0.5", "192.168.0.6", "192.168.0.7"]


def test_part3_slash_30_reverse_from_seed():
    # Same block, reverse: yields 5, 4 (stops at network).
    it = IPV4Iterator("192.168.0.5/30", reverse=True)
    assert list(it) == ["192.168.0.5", "192.168.0.4"]


def test_part3_seed_not_network_address():
    # 10.0.0.13/29 → block [10.0.0.8, 10.0.0.15]. Forward from .13 yields .13-.15.
    it = IPV4Iterator("10.0.0.13/29")
    assert list(it) == ["10.0.0.13", "10.0.0.14", "10.0.0.15"]


def test_part3_seed_not_network_reverse():
    # Same block, reverse from .13: yields .13, .12, .11, .10, .9, .8.
    it = IPV4Iterator("10.0.0.13/29", reverse=True)
    assert list(it) == [
        "10.0.0.13",
        "10.0.0.12",
        "10.0.0.11",
        "10.0.0.10",
        "10.0.0.9",
        "10.0.0.8",
    ]


def test_part3_slash_24_full_block_forward():
    it = IPV4Iterator("192.168.5.0/24")
    collected = list(it)
    assert len(collected) == 256
    assert collected[0] == "192.168.5.0"
    assert collected[-1] == "192.168.5.255"


def test_part3_slash_24_seed_mid_block():
    it = IPV4Iterator("192.168.5.100/24")
    collected = list(it)
    assert collected[0] == "192.168.5.100"
    assert collected[-1] == "192.168.5.255"
    assert len(collected) == 156   # 255 - 100 + 1


def test_part3_forward_stops_at_broadcast():
    it = IPV4Iterator("10.0.0.14/29")   # broadcast = 10.0.0.15
    assert next(it) == "10.0.0.14"
    assert next(it) == "10.0.0.15"
    with pytest.raises(StopIteration):
        next(it)


def test_part3_reverse_stops_at_network():
    it = IPV4Iterator("10.0.0.9/29", reverse=True)   # network = 10.0.0.8
    assert next(it) == "10.0.0.9"
    assert next(it) == "10.0.0.8"
    with pytest.raises(StopIteration):
        next(it)


# ============================================================
# Part 4 — step and next_batch
# ============================================================


def test_part4_step_default_one():
    it = IPV4Iterator("10.0.0.0", step=1)
    assert next(it) == "10.0.0.0"
    assert next(it) == "10.0.0.1"


def test_part4_step_two_skips():
    it = IPV4Iterator("10.0.0.0", step=2)
    assert next(it) == "10.0.0.0"
    assert next(it) == "10.0.0.2"
    assert next(it) == "10.0.0.4"


def test_part4_step_four_across_octet():
    it = IPV4Iterator("10.0.0.252", step=4)
    assert next(it) == "10.0.0.252"
    assert next(it) == "10.0.1.0"


def test_part4_step_in_reverse():
    it = IPV4Iterator("10.0.0.10", reverse=True, step=3)
    assert next(it) == "10.0.0.10"
    assert next(it) == "10.0.0.7"
    assert next(it) == "10.0.0.4"


def test_part4_step_zero_raises_valueerror():
    with pytest.raises(ValueError):
        IPV4Iterator("10.0.0.0", step=0)


def test_part4_step_negative_raises_valueerror():
    with pytest.raises(ValueError):
        IPV4Iterator("10.0.0.0", step=-1)


def test_part4_step_in_cidr_block():
    it = IPV4Iterator("192.168.0.0/24", step=64)
    assert list(it) == [
        "192.168.0.0",
        "192.168.0.64",
        "192.168.0.128",
        "192.168.0.192",
    ]


def test_part4_step_overshoots_block_yields_one():
    # /29 block has 8 IPs. step=100 yields only the seed, then stops.
    it = IPV4Iterator("10.0.0.8/29", step=100)
    assert list(it) == ["10.0.0.8"]


def test_part4_next_batch_returns_requested_size():
    it = IPV4Iterator("10.0.0.0")
    assert it.next_batch(3) == ["10.0.0.0", "10.0.0.1", "10.0.0.2"]


def test_part4_next_batch_continues_from_cursor():
    it = IPV4Iterator("10.0.0.0")
    assert next(it) == "10.0.0.0"
    assert it.next_batch(2) == ["10.0.0.1", "10.0.0.2"]


def test_part4_next_batch_stops_at_boundary():
    it = IPV4Iterator("10.0.0.5/30")   # block = [.4, .7], from seed: .5, .6, .7
    assert it.next_batch(10) == ["10.0.0.5", "10.0.0.6", "10.0.0.7"]


def test_part4_next_batch_zero_returns_empty():
    it = IPV4Iterator("10.0.0.0")
    assert it.next_batch(0) == []


def test_part4_next_batch_after_exhausted():
    it = IPV4Iterator("0.0.0.0", reverse=True)
    assert it.next_batch(5) == ["0.0.0.0"]
    assert it.next_batch(5) == []   # already exhausted, no raise


def test_part4_next_batch_with_step():
    it = IPV4Iterator("10.0.0.0/24", step=50)
    assert it.next_batch(10) == [
        "10.0.0.0",
        "10.0.0.50",
        "10.0.0.100",
        "10.0.0.150",
        "10.0.0.200",
        "10.0.0.250",
    ]


# ============================================================
# Part 5A — contains  (block bounds, direction-agnostic)
# ============================================================


def test_part5a_contains_within_cidr_block():
    # /29 at seed=5: host_bits=3, mask=7, network=0, broadcast=7.
    # Block = [10.0.0.0, 10.0.0.7].
    it = IPV4Iterator("10.0.0.5/29")
    assert it.contains("10.0.0.0") is True
    assert it.contains("10.0.0.5") is True
    assert it.contains("10.0.0.7") is True


def test_part5a_contains_outside_block_false():
    it = IPV4Iterator("10.0.0.13/29")    # block = [10.0.0.8, 10.0.0.15]
    assert it.contains("10.0.0.7") is False
    assert it.contains("10.0.0.16") is False


def test_part5a_contains_at_boundaries_inclusive():
    it = IPV4Iterator("10.0.0.13/29")    # block = [10.0.0.8, 10.0.0.15]
    assert it.contains("10.0.0.8") is True
    assert it.contains("10.0.0.15") is True


def test_part5a_contains_slash_32_only_self():
    it = IPV4Iterator("192.168.0.5/32")
    assert it.contains("192.168.0.5") is True
    assert it.contains("192.168.0.4") is False
    assert it.contains("192.168.0.6") is False


def test_part5a_contains_direction_agnostic():
    # Same /29 block in forward and reverse — contains is identical.
    fwd = IPV4Iterator("10.0.0.13/29")
    rev = IPV4Iterator("10.0.0.13/29", reverse=True)
    for ip in ("10.0.0.8", "10.0.0.10", "10.0.0.15"):
        assert fwd.contains(ip) == rev.contains(ip) is True
    for ip in ("10.0.0.7", "10.0.0.16"):
        assert fwd.contains(ip) == rev.contains(ip) is False


def test_part5a_contains_bare_ip_full_space():
    # Bare-IP: bounds are [0, 0xFFFFFFFF]. Any well-formed IPv4 is in range.
    it = IPV4Iterator("10.0.0.100")
    assert it.contains("0.0.0.0") is True
    assert it.contains("10.0.0.100") is True
    assert it.contains("255.255.255.255") is True


# ============================================================
# Part 5B — to_cidrs (LC 751 wrapped)
# ============================================================


def test_part5b_single_ip_range():
    assert IPV4Iterator.to_cidrs("10.0.0.5", "10.0.0.5") == ["10.0.0.5/32"]


def test_part5b_aligned_pair_yields_slash_31():
    assert IPV4Iterator.to_cidrs("10.0.0.4", "10.0.0.5") == ["10.0.0.4/31"]


def test_part5b_aligned_full_slash_29():
    # /29 starting at .8 covers .8-.15 exactly.
    assert IPV4Iterator.to_cidrs("10.0.0.8", "10.0.0.15") == ["10.0.0.8/29"]


def test_part5b_unaligned_start():
    # [.5, .9] = .5/32, .6/31, .8/31
    assert IPV4Iterator.to_cidrs("10.0.0.5", "10.0.0.9") == [
        "10.0.0.5/32",
        "10.0.0.6/31",
        "10.0.0.8/31",
    ]


def test_part5b_lc751_example():
    # ip=255.0.0.7, n=10  →  255.0.0.7/32, 255.0.0.8/29, 255.0.0.16/32
    assert IPV4Iterator.to_cidrs("255.0.0.7", "255.0.0.16") == [
        "255.0.0.7/32",
        "255.0.0.8/29",
        "255.0.0.16/32",
    ]


def test_part5b_full_slash_24():
    # [10.0.0.0, 10.0.0.255] is exactly /24.
    assert IPV4Iterator.to_cidrs("10.0.0.0", "10.0.0.255") == ["10.0.0.0/24"]


def test_part5b_crosses_octet_boundary():
    # [10.0.0.250, 10.0.1.5] — decomposition crossing the .255 → .0 boundary.
    # Hand-traced greedy:
    #   .250/31 (.250-.251), .252/30 (.252-.255),
    #   10.0.1.0/30 (.0-.3),  10.0.1.4/31 (.4-.5).
    assert IPV4Iterator.to_cidrs("10.0.0.250", "10.0.1.5") == [
        "10.0.0.250/31",
        "10.0.0.252/30",
        "10.0.1.0/30",
        "10.0.1.4/31",
    ]
