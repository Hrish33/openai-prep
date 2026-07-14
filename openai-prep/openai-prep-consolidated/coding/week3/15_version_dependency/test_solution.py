"""Tests for Version Dependency — earliest-supported-version variant.

Tests are organized by part. The harness in ``make_probe`` wraps a ground-
truth predicate and counts calls — Part 3 tests assert call budgets, not
just correctness.
"""

from typing import Callable

import pytest

from solution import (
    find_earliest_supported_version_v1,
    find_earliest_supported_version_v2,
    find_earliest_supported_version_v3,
    parse_version,
)


# ---------------------------------------------------------------------------
# Test harness: wraps a predicate and counts calls, so Part 3 tests can
# assert "this should take at most K calls" rather than just correctness.
# ---------------------------------------------------------------------------


class Probe:
    def __init__(self, predicate: Callable[[str], bool]) -> None:
        self.predicate = predicate
        self.calls = 0
        self.seen: list[str] = []

    def __call__(self, version: str) -> bool:
        self.calls += 1
        self.seen.append(version)
        return self.predicate(version)


def make_probe(predicate: Callable[[str], bool]) -> Probe:
    return Probe(predicate)


# Helpers for predicates ----------------------------------------------------


def supported_from(threshold: tuple[int, int, int]) -> Callable[[str], bool]:
    """Monotone: True iff parse_version(v) >= threshold."""
    return lambda v: parse_version(v) >= threshold


def supported_in_ranges(*ranges: tuple[tuple[int, int, int], tuple[int, int, int]]) -> Callable[[str], bool]:
    """Regressive: True iff parsed version lies in any of the given [lo, hi] ranges."""
    def predicate(v: str) -> bool:
        pv = parse_version(v)
        return any(lo <= pv <= hi for lo, hi in ranges)
    return predicate


# Lex-sorted (NOT numeric) sample input — exposes the "sort by raw string" trap.
LEX_SORTED = sorted([
    "1.0.0", "1.0.1", "1.0.10", "1.0.2",
    "1.1.0", "1.10.0", "1.2.0", "1.9.0",
    "2.0.0", "2.0.1", "10.0.0",
])


# ===========================================================================
# parse_version
# ===========================================================================


def test_parse_version_basic():
    assert parse_version("1.2.3") == (1, 2, 3)


def test_parse_version_strips_leading_zeros():
    assert parse_version("103.003.02") == (103, 3, 2)


def test_parse_version_numeric_not_lex():
    # If you sorted by string, "1.10.0" would come before "1.9.0".
    assert parse_version("1.10.0") > parse_version("1.9.0")


# ===========================================================================
# Part 1 — monotone
# ===========================================================================


def test_v1_returns_first_supported():
    probe = make_probe(supported_from((1, 2, 0)))
    assert find_earliest_supported_version_v1(LEX_SORTED, probe) == "1.2.0"


def test_v1_returns_none_when_no_support():
    probe = make_probe(lambda v: False)
    assert find_earliest_supported_version_v1(LEX_SORTED, probe) is None


def test_v1_empty_input():
    probe = make_probe(lambda v: True)
    assert find_earliest_supported_version_v1([], probe) is None
    assert probe.calls == 0


def test_v1_all_supported_returns_numeric_first():
    probe = make_probe(lambda v: True)
    # Numeric first is "1.0.0", NOT lex first ("1.0.0" happens to match here,
    # but the test is here to anchor the parse-first-then-sort discipline).
    assert find_earliest_supported_version_v1(LEX_SORTED, probe) == "1.0.0"


def test_v1_sort_by_parsed_not_raw_string():
    # Constructed input where lex order and numeric order disagree on the answer.
    versions = ["1.10.0", "1.2.0", "1.9.0"]
    # Numeric sorted: 1.2.0, 1.9.0, 1.10.0. Support starts at 1.9.0.
    probe = make_probe(supported_from((1, 9, 0)))
    assert find_earliest_supported_version_v1(versions, probe) == "1.9.0"


# ===========================================================================
# Part 2 — regressive
# ===========================================================================


def test_v2_regression_then_recovery():
    # Supported in [1.0.0, 1.0.10] and [2.0.0, 10.0.0]; gap in 1.1.x..1.10.x.
    predicate = supported_in_ranges(
        ((1, 0, 0), (1, 0, 10)),
        ((2, 0, 0), (10, 0, 0)),
    )
    probe = make_probe(predicate)
    assert find_earliest_supported_version_v2(LEX_SORTED, probe) == "1.0.0"


def test_v2_only_late_versions_supported():
    predicate = supported_in_ranges(((2, 0, 0), (10, 0, 0)))
    probe = make_probe(predicate)
    assert find_earliest_supported_version_v2(LEX_SORTED, probe) == "2.0.0"


def test_v2_no_support_returns_none():
    probe = make_probe(lambda v: False)
    assert find_earliest_supported_version_v2(LEX_SORTED, probe) is None


def test_v2_must_not_return_on_first_true():
    # If the implementation early-exits on first True it'd return whichever
    # True it hits first in iteration order — NOT the numeric-earliest True.
    # Construct an input where the input order disagrees with the numeric order.
    versions = ["1.10.0", "1.9.0", "1.2.0"]  # iteration encounters 1.10.0 first
    predicate = supported_in_ranges(((1, 2, 0), (1, 2, 0)), ((1, 10, 0), (1, 10, 0)))
    probe = make_probe(predicate)
    # Both 1.2.0 and 1.10.0 are True; numeric-earliest is 1.2.0.
    assert find_earliest_supported_version_v2(versions, probe) == "1.2.0"


def test_v2_single_version_supported():
    probe = make_probe(lambda v: parse_version(v) == (1, 9, 0))
    assert find_earliest_supported_version_v2(LEX_SORTED, probe) == "1.9.0"


# ===========================================================================
# Part 3 — rate-limited, hierarchical bisection
# ===========================================================================


def test_v3_correctness_matches_v2_on_monotone():
    probe = make_probe(supported_from((1, 2, 0)))
    assert find_earliest_supported_version_v3(LEX_SORTED, probe) == "1.2.0"


def test_v3_correctness_when_only_late_major_supports():
    # Suffix-monotone: True iff version >= 2.0.0. Earliest True = 2.0.0.
    # Major 1's latest (1.10.0) is False, so bisection skips major 1 correctly.
    probe = make_probe(supported_from((2, 0, 0)))
    assert find_earliest_supported_version_v3(LEX_SORTED, probe) == "2.0.0"


def test_v3_no_support_returns_none():
    probe = make_probe(lambda v: False)
    assert find_earliest_supported_version_v3(LEX_SORTED, probe) is None


def test_v3_empty_input():
    probe = make_probe(lambda v: True)
    assert find_earliest_supported_version_v3([], probe) is None
    assert probe.calls == 0


def test_v3_call_budget_is_logarithmic():
    # 11 versions, supported from 1.2.0 onward. A linear Part-2 scan would
    # take 11 calls; hierarchical bisection over (major=2, minor≤4, patch≤3)
    # should comfortably finish in < 11.
    probe = make_probe(supported_from((1, 2, 0)))
    result = find_earliest_supported_version_v3(LEX_SORTED, probe)
    assert result == "1.2.0"
    assert probe.calls < len(LEX_SORTED), f"used {probe.calls} calls, expected < {len(LEX_SORTED)}"


def test_v3_memoizes_duplicate_probes():
    # No two probes on the same version string should ever fire is_supported twice.
    probe = make_probe(supported_from((1, 2, 0)))
    find_earliest_supported_version_v3(LEX_SORTED, probe)
    assert len(probe.seen) == len(set(probe.seen)), \
        f"duplicate probes: {[v for v in probe.seen if probe.seen.count(v) > 1]}"


def test_v3_group_representative_is_latest_patch():
    # Support starts at 1.0.10 (suffix-monotone). Within the (1, 0) group, the
    # FIRST patch 1.0.0 is False but the LATEST 1.0.10 is True. A "first patch
    # as rep" impl would probe 1.0.0, get False, and skip the (1, 0) group —
    # missing the answer. "Latest patch as rep" probes 1.0.10 and recurses.
    probe = make_probe(supported_from((1, 0, 10)))
    assert find_earliest_supported_version_v3(LEX_SORTED, probe) == "1.0.10"


def test_v3_all_supported_finds_first_in_log_calls():
    probe = make_probe(lambda v: True)
    result = find_earliest_supported_version_v3(LEX_SORTED, probe)
    assert result == "1.0.0"
    # All-True is the easiest case — should finish in well under N calls.
    assert probe.calls < len(LEX_SORTED)


def test_v3_handles_sparse_groups():
    # Versions intentionally non-contiguous: major 2 jumps to major 10, no 3..9.
    # Implementation must build (major, minor) groups from input, not enumerate
    # all (X, Y) pairs.
    versions = ["1.0.0", "1.0.5", "2.0.0", "10.0.0"]
    predicate = supported_in_ranges(((2, 0, 0), (10, 0, 0)))
    probe = make_probe(predicate)
    assert find_earliest_supported_version_v3(versions, probe) == "2.0.0"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
