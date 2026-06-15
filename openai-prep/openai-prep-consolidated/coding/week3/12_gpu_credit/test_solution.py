"""Tests for the GPU credit system. Run: pytest test_solution.py -v"""

from __future__ import annotations

import pytest

from solution import GPUCredit


# ----- happy path -------------------------------------------------------------


def test_single_grant_balance_returns_full_amount():
    gpu = GPUCredit()
    gpu.add_credit('a', 10, 0, 100)
    assert gpu.get_balance(50) == 10


def test_balance_before_grant_starts_returns_none():
    gpu = GPUCredit()
    gpu.add_credit('a', 10, 100, 50)
    assert gpu.get_balance(50) is None


def test_balance_after_grant_expires_returns_none():
    gpu = GPUCredit()
    gpu.add_credit('a', 10, 0, 50)
    # valid 0..50 inclusive; t=51 is past
    assert gpu.get_balance(51) is None


def test_balance_at_inclusive_expiration_boundary():
    gpu = GPUCredit()
    gpu.add_credit('a', 10, 0, 50)
    assert gpu.get_balance(50) == 10  # still valid


def test_subtract_reduces_balance():
    gpu = GPUCredit()
    gpu.add_credit('a', 10, 0, 100)
    gpu.subtract(3, 10)
    assert gpu.get_balance(20) == 7


# ----- earliest-expiring-first drain -----------------------------------------


def test_subtract_burns_soonest_expiring_grant_first():
    gpu = GPUCredit()
    gpu.add_credit('a', 4, 20, 40)  # expires at 60
    gpu.add_credit('b', 3, 30, 10)  # expires at 40 (sooner)
    gpu.subtract(2, 30)
    assert gpu.get_balance(30) == 5  # b has 1 left, a has 4


def test_subtract_spans_multiple_grants():
    gpu = GPUCredit()
    gpu.add_credit('a', 4, 20, 40)  # expires at 60
    gpu.add_credit('b', 3, 30, 10)  # expires at 40
    gpu.subtract(5, 30)  # drains all of b (3) plus 2 from a
    assert gpu.get_balance(30) == 2  # a has 2 left


def test_after_short_grant_expires_long_grant_still_visible():
    gpu = GPUCredit()
    gpu.add_credit('a', 4, 20, 40)  # expires at 60
    gpu.add_credit('b', 3, 30, 10)  # expires at 40
    gpu.subtract(2, 30)
    assert gpu.get_balance(41) == 4  # b expired, only a remains


# ----- the None vs 0 discipline -----------------------------------------------


def test_exact_zero_with_active_grant_returns_zero_not_none():
    gpu = GPUCredit()
    gpu.add_credit('a', 10, 0, 100)
    gpu.subtract(10, 50)
    assert gpu.get_balance(60) == 0  # exact zero with active grant → 0


def test_negative_balance_returns_none():
    gpu = GPUCredit()
    gpu.add_credit('a', 10, 10, 30)
    gpu.subtract(100, 20)
    assert gpu.get_balance(20) is None  # balance is -90 → None


def test_balance_before_subtract_unaffected():
    gpu = GPUCredit()
    gpu.add_credit('a', 10, 10, 30)
    gpu.subtract(100, 20)
    assert gpu.get_balance(10) == 10  # subtract is in the future at t=10


# ----- out-of-order arrival --------------------------------------------------


def test_subtract_arrives_before_add_credit():
    gpu = GPUCredit()
    gpu.subtract(4, 30)              # arrives first
    gpu.add_credit('a', 4, 20, 30)   # valid 20..50
    assert gpu.get_balance(20) == 4  # at t=20, subtract hasn't happened yet
    assert gpu.get_balance(30) == 0  # 4 added, 4 used → 0 (active grant present)
    assert gpu.get_balance(50) == 0  # still valid, still 0


def test_add_credit_arrives_after_subtract_negative_then_topup():
    gpu = GPUCredit()
    gpu.subtract(10, 50)
    gpu.add_credit('a', 5, 0, 100)
    # at t=50: 5 added, 10 subtracted → balance -5 → None
    assert gpu.get_balance(50) is None
    gpu.add_credit('b', 20, 60, 100)
    # at t=60: 5 + 20 added, 10 subtracted → balance 15
    assert gpu.get_balance(60) == 15


def test_query_before_any_grant_returns_none():
    gpu = GPUCredit()
    gpu.subtract(4, 30)
    gpu.add_credit('a', 4, 20, 30)
    assert gpu.get_balance(0) is None  # no grant active at t=0


# ----- edge cases ------------------------------------------------------------


def test_two_grants_same_expiration_either_order_acceptable():
    """Tie-breaker on expiration is implementation-defined; just verify totals."""
    gpu = GPUCredit()
    gpu.add_credit('a', 5, 0, 50)  # expires at 50
    gpu.add_credit('b', 5, 0, 50)  # expires at 50
    gpu.subtract(3, 10)
    assert gpu.get_balance(20) == 7


def test_subtract_only_touches_grants_active_at_its_timestamp():
    gpu = GPUCredit()
    gpu.add_credit('expired', 10, 0, 10)   # valid 0..10
    gpu.add_credit('live', 10, 20, 50)     # valid 20..70
    gpu.subtract(5, 30)
    # 'expired' grant must not be drained — it wasn't active at t=30
    assert gpu.get_balance(30) == 5
    # 'expired' grant still gone by t=30 anyway, but the point is:
    # at t=5 (during 'expired'), nothing was subtracted from it
    assert gpu.get_balance(5) == 10


def test_subtract_exceeds_available_in_active_grants_goes_negative():
    gpu = GPUCredit()
    gpu.add_credit('a', 5, 0, 100)
    gpu.subtract(8, 10)
    assert gpu.get_balance(20) is None  # balance -3 → None


def test_multiple_subtracts_accumulate():
    gpu = GPUCredit()
    gpu.add_credit('a', 10, 0, 100)
    gpu.subtract(2, 10)
    gpu.subtract(3, 20)
    gpu.subtract(1, 30)
    assert gpu.get_balance(40) == 4


def test_grant_zero_amount_treated_as_active():
    gpu = GPUCredit()
    gpu.add_credit('a', 0, 0, 100)
    assert gpu.get_balance(50) == 0  # active grant, balance 0 → 0


# ----- combined / scenario ---------------------------------------------------


def test_spec_example_burn_soonest_full_trace():
    gpu = GPUCredit()
    gpu.add_credit('a', 4, 20, 40)
    gpu.add_credit('b', 3, 30, 10)
    gpu.subtract(2, 30)
    assert gpu.get_balance(30) == 5
    assert gpu.get_balance(40) == 5
    assert gpu.get_balance(41) == 4


def test_spec_example_out_of_order_full_trace():
    gpu = GPUCredit()
    gpu.subtract(4, 30)
    gpu.add_credit('a', 4, 20, 30)
    assert gpu.get_balance(20) == 4
    assert gpu.get_balance(30) == 0
    assert gpu.get_balance(50) == 0


def test_spec_example_negative_balance_full_trace():
    gpu = GPUCredit()
    gpu.add_credit('openai', 10, 10, 30)
    gpu.subtract(100, 20)
    assert gpu.get_balance(10) == 10
    assert gpu.get_balance(20) is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
