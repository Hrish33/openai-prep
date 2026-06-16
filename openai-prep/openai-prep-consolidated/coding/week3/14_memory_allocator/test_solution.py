"""Tests for the Memory Allocator. Run: pytest test_solution.py -v"""

from __future__ import annotations

from solution import Allocator


# ----- init ------------------------------------------------------------------


def test_init_with_positive_capacity() -> None:
    a = Allocator(10)
    assert a.allocate(10, 1) == 0


def test_init_with_zero_capacity_rejects_all_allocations() -> None:
    a = Allocator(0)
    assert a.allocate(1, 1) == -1


# ----- basic allocate --------------------------------------------------------


def test_allocate_returns_zero_for_first_block() -> None:
    a = Allocator(10)
    assert a.allocate(3, 1) == 0


def test_allocate_packs_leftmost() -> None:
    a = Allocator(10)
    assert a.allocate(2, 1) == 0
    assert a.allocate(3, 2) == 2
    assert a.allocate(1, 3) == 5


def test_allocate_returns_neg_one_when_no_fit() -> None:
    a = Allocator(5)
    assert a.allocate(3, 1) == 0
    assert a.allocate(3, 2) == -1  # only 2 bytes left


def test_allocate_returns_neg_one_when_request_exceeds_capacity() -> None:
    a = Allocator(5)
    assert a.allocate(10, 1) == -1


def test_allocate_exactly_fills_pool() -> None:
    a = Allocator(5)
    assert a.allocate(5, 1) == 0
    assert a.allocate(1, 2) == -1


def test_allocate_same_mid_stacks_multiple_blocks() -> None:
    a = Allocator(10)
    assert a.allocate(2, 1) == 0
    assert a.allocate(3, 1) == 2  # same mID, second block at 2
    assert a.freeMemory(1) == 5   # both blocks freed; total = 5


# ----- basic free ------------------------------------------------------------


def test_free_unknown_mid_returns_zero() -> None:
    a = Allocator(10)
    assert a.freeMemory(99) == 0


def test_free_returns_total_bytes_freed() -> None:
    a = Allocator(10)
    a.allocate(3, 1)
    a.allocate(2, 1)
    assert a.freeMemory(1) == 5


def test_double_free_returns_zero_the_second_time() -> None:
    a = Allocator(10)
    a.allocate(4, 7)
    assert a.freeMemory(7) == 4
    assert a.freeMemory(7) == 0


def test_free_then_realloc_reuses_address() -> None:
    a = Allocator(10)
    a.allocate(4, 1)
    a.freeMemory(1)
    assert a.allocate(4, 2) == 0  # leftmost-first puts it right back at 0


# ----- the four merge cases --------------------------------------------------


def test_merge_case_none_isolated_free_creates_new_gap() -> None:
    """free in the middle with used neighbours on both sides."""
    a = Allocator(10)
    a.allocate(3, 1)  # [0,3)
    a.allocate(3, 2)  # [3,6)
    a.allocate(3, 3)  # [6,9)
    a.freeMemory(2)   # free [3,6); neighbours are both allocated
    # now free regions are [3,6) and [9,10).
    assert a.allocate(3, 4) == 3   # leftmost fit is the new gap at 3
    assert a.allocate(1, 5) == 9   # the trailing 1 byte
    assert a.allocate(1, 6) == -1  # all packed


def test_merge_case_left_extends_left_gap_rightward() -> None:
    """free with a free gap immediately to the left."""
    a = Allocator(10)
    a.allocate(2, 1)  # [0,2)
    a.allocate(2, 2)  # [2,4)
    a.allocate(2, 3)  # [4,6)
    a.freeMemory(1)   # free [0,2); the [0,2) gap is now alone
    a.freeMemory(2)   # free [2,4); left-merge with [0,2) → [0,4)
    # now: free [0,4) and [6,10). Request 4 bytes → must fit at 0.
    assert a.allocate(4, 4) == 0


def test_merge_case_right_extends_freed_block_over_right_gap() -> None:
    """free with a free gap immediately to the right."""
    a = Allocator(10)
    a.allocate(2, 1)  # [0,2)
    a.allocate(2, 2)  # [2,4)
    a.allocate(2, 3)  # [4,6)
    a.freeMemory(3)   # free [4,6); the [4,10) gap (combined with original tail [6,10)) → [4,10)
    a.freeMemory(2)   # free [2,4); right-merge with [4,10) → [2,10)
    # now: free [2,10) and used [0,2). Request 8 bytes → must fit at 2.
    assert a.allocate(8, 4) == 2


def test_merge_case_both_collapses_three_into_one() -> None:
    """free in the middle with free gaps on BOTH sides."""
    a = Allocator(10)
    a.allocate(2, 1)  # [0,2)
    a.allocate(2, 2)  # [2,4)
    a.allocate(2, 3)  # [4,6)
    a.allocate(2, 4)  # [6,8)
    a.allocate(2, 5)  # [8,10)
    a.freeMemory(2)   # free [2,4)
    a.freeMemory(4)   # free [6,8)
    # now free: [2,4), [6,8). mID=3 block [4,6) is sandwiched between two free gaps.
    a.freeMemory(3)   # free [4,6); both-merge → [2,8)
    assert a.allocate(6, 6) == 2  # single contiguous 6-byte slot


# ----- fragmentation defeats first-fit ---------------------------------------


def test_fragmentation_blocks_alloc_even_when_total_free_is_enough() -> None:
    a = Allocator(10)
    a.allocate(1, 1)  # [0,1)
    a.allocate(1, 2)  # [1,2)
    a.allocate(1, 3)  # [2,3)
    a.allocate(1, 4)  # [3,4)
    a.allocate(1, 5)  # [4,5)
    a.allocate(1, 6)  # [5,6)
    a.allocate(1, 7)  # [6,7)
    a.allocate(1, 8)  # [7,8)
    a.allocate(1, 9)  # [8,9)
    a.allocate(1, 10) # [9,10)
    # free every other one — leaves five non-adjacent 1-byte gaps
    a.freeMemory(1)
    a.freeMemory(3)
    a.freeMemory(5)
    a.freeMemory(7)
    a.freeMemory(9)
    # 5 bytes free, no contiguous 2-byte run
    assert a.allocate(2, 11) == -1
    # 1-byte alloc takes the leftmost gap
    assert a.allocate(1, 12) == 0


# ----- mID reuse after full free ---------------------------------------------


def test_mid_can_be_reused_after_free() -> None:
    a = Allocator(10)
    assert a.allocate(5, 1) == 0
    assert a.freeMemory(1) == 5
    assert a.allocate(5, 1) == 0  # same mID, fresh allocation
    assert a.freeMemory(1) == 5


def test_full_free_returns_pool_to_one_gap() -> None:
    a = Allocator(10)
    a.allocate(2, 1)
    a.allocate(3, 2)
    a.allocate(1, 3)
    a.allocate(4, 4)
    a.freeMemory(1)
    a.freeMemory(2)
    a.freeMemory(3)
    a.freeMemory(4)
    # the whole pool should be one contiguous free block now
    assert a.allocate(10, 5) == 0


# ----- LC 2502 canonical example ---------------------------------------------


def test_lc_2502_canonical_sequence() -> None:
    """The example from the LeetCode problem statement, verbatim."""
    a = Allocator(10)
    assert a.allocate(1, 1) == 0
    assert a.allocate(1, 2) == 1
    assert a.allocate(1, 3) == 2
    assert a.freeMemory(2) == 1
    assert a.allocate(3, 4) == 3
    assert a.allocate(1, 1) == 1
    assert a.allocate(1, 1) == 6
    assert a.freeMemory(1) == 3
    assert a.allocate(10, 2) == -1


# ----- stress / integration --------------------------------------------------


def test_interleaved_alloc_free_stress() -> None:
    """A mid-sized churn: 50 ops with overlapping mIDs."""
    a = Allocator(100)
    addrs = {}
    addrs[1] = a.allocate(10, 1)
    addrs[2] = a.allocate(20, 2)
    addrs[3] = a.allocate(30, 3)
    addrs[4] = a.allocate(40, 4)  # pool full: 10+20+30+40 = 100
    assert a.allocate(1, 5) == -1

    a.freeMemory(2)  # free [10,30)
    a.freeMemory(4)  # free [60,100)
    # now free: [10,30) and [60,100) = 20 + 40 = 60 bytes
    assert a.allocate(40, 6) == 60  # leftmost-fit for 40 is the [60,100) gap
    assert a.allocate(20, 7) == 10  # then the [10,30) gap
    assert a.allocate(1, 8) == -1   # fully packed again
