"""Sanity tests for the dumb dep-graph reference."""

import pytest

from solution_dumb import (
    direct_dependencies,
    install_order,
    parse_catalog,
    parse_version,
    resolve,
    transitive_dependencies,
)


# ---------------------------------------------------------------------------
# Part 1 — parse
# ---------------------------------------------------------------------------


def test_parse_no_deps():
    cat = parse_catalog(["B 2.0.0"])
    assert cat == {"B": {(2, 0, 0): []}}


def test_parse_single_req():
    cat = parse_catalog(["A 1.0.0 requires B>=2.0.0"])
    assert cat == {"A": {(1, 0, 0): [("B", ">=", (2, 0, 0))]}}


def test_parse_multiple_reqs():
    cat = parse_catalog(["A 1.0.0 requires B>=2.0.0, C==1.5.0"])
    assert cat == {"A": {(1, 0, 0): [
        ("B", ">=", (2, 0, 0)),
        ("C", "==", (1, 5, 0)),
    ]}}


def test_parse_all_operators():
    cat = parse_catalog([
        "A 1.0.0 requires B>=1.0.0, C<=2.0.0, D==3.0.0, E!=4.0.0, F>5.0.0, G<6.0.0",
    ])
    reqs = cat["A"][(1, 0, 0)]
    ops = [op for _, op, _ in reqs]
    assert ops == [">=", "<=", "==", "!=", ">", "<"]


# ---------------------------------------------------------------------------
# Part 2 — queries
# ---------------------------------------------------------------------------


SAMPLE = parse_catalog([
    "A 1.0.0 requires B>=2.0.0, C==1.5.0",
    "B 2.0.0 requires D>=1.0.0",
    "B 2.1.0 requires D>=1.0.0",
    "C 1.5.0",
    "D 1.0.0",
    "D 1.1.0",
])


def test_direct_dependencies():
    assert direct_dependencies(SAMPLE, "A", (1, 0, 0)) == [
        ("B", ">=", (2, 0, 0)),
        ("C", "==", (1, 5, 0)),
    ]


def test_transitive_picks_latest_satisfying():
    # A → B>=2.0.0 (latest = 2.1.0) and C==1.5.0
    # B@2.1.0 → D>=1.0.0 (latest = 1.1.0)
    nodes = transitive_dependencies(SAMPLE, "A", (1, 0, 0))
    assert nodes == {
        ("A", (1, 0, 0)),
        ("B", (2, 1, 0)),
        ("C", (1, 5, 0)),
        ("D", (1, 1, 0)),
    }


def test_transitive_unsatisfiable_raises():
    cat = parse_catalog([
        "A 1.0.0 requires B>=9.9.9",
        "B 1.0.0",
    ])
    with pytest.raises(ValueError):
        transitive_dependencies(cat, "A", (1, 0, 0))


# ---------------------------------------------------------------------------
# Part 3 — install order
# ---------------------------------------------------------------------------


def test_install_order_topological():
    order = install_order(SAMPLE, "A", (1, 0, 0))
    assert order is not None
    pos = {node: i for i, node in enumerate(order)}
    # D installs before B; B and C before A.
    assert pos[("D", (1, 1, 0))] < pos[("B", (2, 1, 0))]
    assert pos[("B", (2, 1, 0))] < pos[("A", (1, 0, 0))]
    assert pos[("C", (1, 5, 0))] < pos[("A", (1, 0, 0))]
    assert set(order) == {
        ("A", (1, 0, 0)), ("B", (2, 1, 0)), ("C", (1, 5, 0)), ("D", (1, 1, 0)),
    }


def test_install_order_cycle_returns_none():
    cat = parse_catalog([
        "A 1.0.0 requires B>=1.0.0",
        "B 1.0.0 requires A>=1.0.0",
    ])
    assert install_order(cat, "A", (1, 0, 0)) is None


# ---------------------------------------------------------------------------
# Part 4 — resolver
# ---------------------------------------------------------------------------


def test_resolve_happy_path():
    # User wants A. Resolver picks latest version of A satisfying constraints (only 1.0.0),
    # then satisfies its deps with latest-compatible versions.
    sol = resolve(SAMPLE, [("A", ">=", (1, 0, 0))])
    assert sol == {"A": (1, 0, 0), "B": (2, 1, 0), "C": (1, 5, 0), "D": (1, 1, 0)}


def test_resolve_user_pins_older_version():
    # User pins B==2.0.0. Resolver must NOT pick the latest B; falls back to 2.0.0.
    sol = resolve(SAMPLE, [("A", ">=", (1, 0, 0)), ("B", "==", (2, 0, 0))])
    assert sol["A"] == (1, 0, 0)
    assert sol["B"] == (2, 0, 0)


def test_resolve_unsat_returns_none():
    # A 1.0.0 requires B>=2.0.0 but user pins B<2.0.0. UNSAT.
    sol = resolve(SAMPLE, [("A", ">=", (1, 0, 0)), ("B", "<", (2, 0, 0))])
    assert sol is None


def test_resolve_backtracks_on_conflict():
    # A 2.0.0 → C==1.0.0; A 1.0.0 → C==2.0.0. User pins C==2.0.0 and wants A.
    # Naïve "latest A first" picks A 2.0.0 → C==1.0.0 conflict → backtrack to A 1.0.0.
    cat = parse_catalog([
        "A 2.0.0 requires C==1.0.0",
        "A 1.0.0 requires C==2.0.0",
        "C 1.0.0",
        "C 2.0.0",
    ])
    sol = resolve(cat, [("A", ">=", (1, 0, 0)), ("C", "==", (2, 0, 0))])
    assert sol == {"A": (1, 0, 0), "C": (2, 0, 0)}


def test_resolve_unknown_package_returns_none():
    sol = resolve(SAMPLE, [("Z", "==", (1, 0, 0))])
    assert sol is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
