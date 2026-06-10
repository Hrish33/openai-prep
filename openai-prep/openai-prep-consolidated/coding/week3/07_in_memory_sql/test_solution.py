"""
Tests for the in-memory SQL-like database (method-call API). Run:
  pytest coding/week3/07_in_memory_sql/test_solution.py -v

Tests are grouped by capability so you can watch progress as you implement:
CREATE -> INSERT -> SELECT all -> SELECT projection -> SELECT where -> errors.
"""

import pytest
from solution import Database


# ---- create_table ----

def test_create_then_select_returns_empty():
    db = Database()
    db.create_table("users", [("id", "INT"), ("name", "TEXT")])
    assert db.select("users") == []


def test_create_returns_none():
    db = Database()
    result = db.create_table("users", [("id", "INT")])
    assert result is None


def test_create_multiple_independent_tables():
    db = Database()
    db.create_table("a", [("x", "INT")])
    db.create_table("b", [("y", "TEXT")])
    db.insert("a", {"x": 1})
    db.insert("b", {"y": "hello"})
    assert db.select("a") == [{"x": 1}]
    assert db.select("b") == [{"y": "hello"}]


# ---- insert ----

def test_insert_single_row():
    db = Database()
    db.create_table("users", [("id", "INT"), ("name", "TEXT")])
    db.insert("users", {"id": 1, "name": "Alice"})
    assert db.select("users") == [{"id": 1, "name": "Alice"}]


def test_insert_returns_none():
    db = Database()
    db.create_table("users", [("id", "INT")])
    assert db.insert("users", {"id": 1}) is None


def test_insert_preserves_order():
    db = Database()
    db.create_table("users", [("id", "INT"), ("name", "TEXT")])
    db.insert("users", {"id": 1, "name": "Alice"})
    db.insert("users", {"id": 2, "name": "Bob"})
    db.insert("users", {"id": 3, "name": "Charlie"})
    assert db.select("users") == [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
        {"id": 3, "name": "Charlie"},
    ]


def test_insert_negative_integer():
    db = Database()
    db.create_table("x", [("n", "INT")])
    db.insert("x", {"n": -5})
    assert db.select("x") == [{"n": -5}]


def test_insert_string_with_spaces():
    db = Database()
    db.create_table("x", [("name", "TEXT")])
    db.insert("x", {"name": "hello world"})
    assert db.select("x") == [{"name": "hello world"}]


# ---- select all rows ----

def test_select_returns_all_columns_by_default():
    db = Database()
    db.create_table("u", [("id", "INT"), ("name", "TEXT"), ("age", "INT")])
    db.insert("u", {"id": 1, "name": "Alice", "age": 30})
    assert db.select("u") == [{"id": 1, "name": "Alice", "age": 30}]


def test_select_from_empty_table():
    db = Database()
    db.create_table("u", [("id", "INT")])
    assert db.select("u") == []


# ---- select with projection ----

def test_select_subset_of_columns():
    db = Database()
    db.create_table("u", [("id", "INT"), ("name", "TEXT"), ("age", "INT")])
    db.insert("u", {"id": 1, "name": "Alice", "age": 30})
    db.insert("u", {"id": 2, "name": "Bob", "age": 25})
    assert db.select("u", columns=["name", "age"]) == [
        {"name": "Alice", "age": 30},
        {"name": "Bob", "age": 25},
    ]


def test_select_one_column():
    db = Database()
    db.create_table("u", [("id", "INT"), ("name", "TEXT")])
    db.insert("u", {"id": 1, "name": "Alice"})
    db.insert("u", {"id": 2, "name": "Bob"})
    assert db.select("u", columns=["name"]) == [
        {"name": "Alice"}, {"name": "Bob"}
    ]


def test_projection_respects_column_order():
    """columns=['c', 'a'] should return dicts with c before a."""
    db = Database()
    db.create_table("x", [("a", "INT"), ("b", "INT"), ("c", "INT")])
    db.insert("x", {"a": 1, "b": 2, "c": 3})
    rows = db.select("x", columns=["c", "a"])
    assert rows == [{"c": 3, "a": 1}]
    # confirm key order in the actual dict
    assert list(rows[0].keys()) == ["c", "a"]


# ---- select with where ----

def test_where_equality_on_int():
    db = Database()
    db.create_table("u", [("id", "INT"), ("name", "TEXT")])
    db.insert("u", {"id": 1, "name": "Alice"})
    db.insert("u", {"id": 2, "name": "Bob"})
    assert db.select("u", where=lambda r: r["id"] == 1) == [
        {"id": 1, "name": "Alice"}
    ]


def test_where_equality_on_string():
    db = Database()
    db.create_table("u", [("id", "INT"), ("name", "TEXT")])
    db.insert("u", {"id": 1, "name": "Alice"})
    db.insert("u", {"id": 2, "name": "Bob"})
    assert db.select("u", where=lambda r: r["name"] == "Bob") == [
        {"id": 2, "name": "Bob"}
    ]


def test_where_inequality():
    db = Database()
    db.create_table("x", [("n", "INT")])
    for v in [1, 2, 3]:
        db.insert("x", {"n": v})
    assert db.select("x", where=lambda r: r["n"] != 2) == [{"n": 1}, {"n": 3}]


def test_where_range():
    db = Database()
    db.create_table("x", [("age", "INT")])
    for v in [10, 20, 30, 40]:
        db.insert("x", {"age": v})
    assert db.select("x", where=lambda r: r["age"] >= 20 and r["age"] < 40) == [
        {"age": 20}, {"age": 30}
    ]


def test_where_composed_and():
    """The AND/OR follow-up is free with callable predicates."""
    db = Database()
    db.create_table("u", [("name", "TEXT"), ("age", "INT")])
    db.insert("u", {"name": "Alice", "age": 30})
    db.insert("u", {"name": "Bob", "age": 25})
    db.insert("u", {"name": "Carol", "age": 30})
    rows = db.select("u", where=lambda r: r["age"] == 30 and r["name"] != "Carol")
    assert rows == [{"name": "Alice", "age": 30}]


def test_where_no_match_returns_empty():
    db = Database()
    db.create_table("x", [("n", "INT")])
    db.insert("x", {"n": 1})
    assert db.select("x", where=lambda r: r["n"] > 100) == []


def test_where_combined_with_projection():
    db = Database()
    db.create_table("u", [("id", "INT"), ("name", "TEXT"), ("age", "INT")])
    db.insert("u", {"id": 1, "name": "Alice", "age": 30})
    db.insert("u", {"id": 2, "name": "Bob", "age": 25})
    db.insert("u", {"id": 3, "name": "Charlie", "age": 35})
    rows = db.select("u", columns=["name"], where=lambda r: r["age"] > 25)
    assert rows == [{"name": "Alice"}, {"name": "Charlie"}]


# ---- Errors ----

def test_select_unknown_table_raises():
    db = Database()
    with pytest.raises(Exception):
        db.select("ghost")


def test_insert_unknown_table_raises():
    db = Database()
    with pytest.raises(Exception):
        db.insert("ghost", {"x": 1})


def test_select_unknown_column_raises():
    db = Database()
    db.create_table("u", [("id", "INT")])
    db.insert("u", {"id": 1})
    with pytest.raises(Exception):
        db.select("u", columns=["badcol"])


def test_insert_missing_column_raises():
    db = Database()
    db.create_table("u", [("id", "INT"), ("name", "TEXT")])
    with pytest.raises(Exception):
        db.insert("u", {"id": 1})    # missing 'name'


def test_insert_extra_column_raises():
    db = Database()
    db.create_table("u", [("id", "INT")])
    with pytest.raises(Exception):
        db.insert("u", {"id": 1, "extra": "oops"})


def test_insert_wrong_type_int_for_text_raises():
    db = Database()
    db.create_table("u", [("name", "TEXT")])
    with pytest.raises(Exception):
        db.insert("u", {"name": 42})


def test_insert_wrong_type_string_for_int_raises():
    db = Database()
    db.create_table("u", [("id", "INT")])
    with pytest.raises(Exception):
        db.insert("u", {"id": "not_an_int"})


# ---- Integration ----

def test_realistic_session():
    """Walk through the example from problem.md end-to-end."""
    db = Database()
    db.create_table("users", [("id", "INT"), ("name", "TEXT"), ("age", "INT")])
    db.insert("users", {"id": 1, "name": "Alice", "age": 30})
    db.insert("users", {"id": 2, "name": "Bob", "age": 25})
    db.insert("users", {"id": 3, "name": "Charlie", "age": 35})

    assert db.select("users") == [
        {"id": 1, "name": "Alice", "age": 30},
        {"id": 2, "name": "Bob", "age": 25},
        {"id": 3, "name": "Charlie", "age": 35},
    ]

    assert db.select("users", columns=["name", "age"], where=lambda r: r["age"] > 25) == [
        {"name": "Alice", "age": 30},
        {"name": "Charlie", "age": 35},
    ]

    assert db.select("users", where=lambda r: r["name"] == "Bob") == [
        {"id": 2, "name": "Bob", "age": 25}
    ]
