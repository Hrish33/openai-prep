"""
Tests for in-memory SQL database. Run:
  pytest coding/week3/07_in_memory_sql/test_solution.py -v

If you wrote your own tests first (good!), compare against these afterward.
The tests are structured by capability so you can see your progress as you
implement each piece (CREATE -> INSERT -> SELECT -> WHERE -> errors).
"""

import pytest
from solution import Database


# ---- CREATE TABLE ----

def test_create_empty_table_then_select_returns_empty():
    db = Database()
    db.execute("CREATE TABLE users (id INT, name TEXT)")
    assert db.execute("SELECT * FROM users") == []


def test_create_returns_none():
    db = Database()
    result = db.execute("CREATE TABLE users (id INT, name TEXT)")
    assert result is None


def test_create_with_multiple_columns():
    db = Database()
    db.execute("CREATE TABLE x (a INT, b TEXT, c INT, d TEXT)")
    db.execute("INSERT INTO x VALUES (1, 'two', 3, 'four')")
    assert db.execute("SELECT * FROM x") == [
        {"a": 1, "b": "two", "c": 3, "d": "four"}
    ]


# ---- INSERT ----

def test_insert_single_row():
    db = Database()
    db.execute("CREATE TABLE users (id INT, name TEXT)")
    db.execute("INSERT INTO users VALUES (1, 'Alice')")
    assert db.execute("SELECT * FROM users") == [{"id": 1, "name": "Alice"}]


def test_insert_returns_none():
    db = Database()
    db.execute("CREATE TABLE users (id INT, name TEXT)")
    assert db.execute("INSERT INTO users VALUES (1, 'Alice')") is None


def test_insert_multiple_rows_preserves_order():
    db = Database()
    db.execute("CREATE TABLE users (id INT, name TEXT)")
    db.execute("INSERT INTO users VALUES (1, 'Alice')")
    db.execute("INSERT INTO users VALUES (2, 'Bob')")
    db.execute("INSERT INTO users VALUES (3, 'Charlie')")
    rows = db.execute("SELECT * FROM users")
    assert rows == [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
        {"id": 3, "name": "Charlie"},
    ]


def test_insert_negative_integer():
    db = Database()
    db.execute("CREATE TABLE x (n INT)")
    db.execute("INSERT INTO x VALUES (-5)")
    assert db.execute("SELECT * FROM x") == [{"n": -5}]


def test_insert_string_with_spaces():
    db = Database()
    db.execute("CREATE TABLE x (name TEXT)")
    db.execute("INSERT INTO x VALUES ('hello world')")
    assert db.execute("SELECT * FROM x") == [{"name": "hello world"}]


# ---- SELECT * (no WHERE) ----

def test_select_star_returns_all_columns():
    db = Database()
    db.execute("CREATE TABLE users (id INT, name TEXT, age INT)")
    db.execute("INSERT INTO users VALUES (1, 'Alice', 30)")
    assert db.execute("SELECT * FROM users") == [
        {"id": 1, "name": "Alice", "age": 30}
    ]


def test_select_projected_columns():
    db = Database()
    db.execute("CREATE TABLE users (id INT, name TEXT, age INT)")
    db.execute("INSERT INTO users VALUES (1, 'Alice', 30)")
    db.execute("INSERT INTO users VALUES (2, 'Bob', 25)")
    rows = db.execute("SELECT name, age FROM users")
    assert rows == [
        {"name": "Alice", "age": 30},
        {"name": "Bob", "age": 25},
    ]


def test_select_one_column():
    db = Database()
    db.execute("CREATE TABLE users (id INT, name TEXT)")
    db.execute("INSERT INTO users VALUES (1, 'Alice')")
    db.execute("INSERT INTO users VALUES (2, 'Bob')")
    assert db.execute("SELECT name FROM users") == [
        {"name": "Alice"}, {"name": "Bob"}
    ]


def test_select_column_order_in_projection():
    """Projected columns should appear in the order they were requested."""
    db = Database()
    db.execute("CREATE TABLE x (a INT, b INT, c INT)")
    db.execute("INSERT INTO x VALUES (1, 2, 3)")
    rows = db.execute("SELECT c, a FROM x")
    assert rows == [{"c": 3, "a": 1}]


def test_select_from_empty_table():
    db = Database()
    db.execute("CREATE TABLE users (id INT, name TEXT)")
    assert db.execute("SELECT * FROM users") == []


# ---- SELECT with WHERE ----

def test_where_equality_on_int():
    db = Database()
    db.execute("CREATE TABLE users (id INT, name TEXT)")
    db.execute("INSERT INTO users VALUES (1, 'Alice')")
    db.execute("INSERT INTO users VALUES (2, 'Bob')")
    rows = db.execute("SELECT * FROM users WHERE id = 1")
    assert rows == [{"id": 1, "name": "Alice"}]


def test_where_equality_on_string():
    db = Database()
    db.execute("CREATE TABLE users (id INT, name TEXT)")
    db.execute("INSERT INTO users VALUES (1, 'Alice')")
    db.execute("INSERT INTO users VALUES (2, 'Bob')")
    rows = db.execute("SELECT * FROM users WHERE name = 'Bob'")
    assert rows == [{"id": 2, "name": "Bob"}]


def test_where_inequality():
    db = Database()
    db.execute("CREATE TABLE x (n INT)")
    db.execute("INSERT INTO x VALUES (1)")
    db.execute("INSERT INTO x VALUES (2)")
    db.execute("INSERT INTO x VALUES (3)")
    rows = db.execute("SELECT * FROM x WHERE n != 2")
    assert rows == [{"n": 1}, {"n": 3}]


def test_where_less_than():
    db = Database()
    db.execute("CREATE TABLE x (age INT)")
    for v in [10, 20, 30, 40]:
        db.execute(f"INSERT INTO x VALUES ({v})")
    assert db.execute("SELECT * FROM x WHERE age < 30") == [{"age": 10}, {"age": 20}]


def test_where_greater_than():
    db = Database()
    db.execute("CREATE TABLE x (age INT)")
    for v in [10, 20, 30, 40]:
        db.execute(f"INSERT INTO x VALUES ({v})")
    assert db.execute("SELECT * FROM x WHERE age > 25") == [{"age": 30}, {"age": 40}]


def test_where_less_than_or_equal():
    db = Database()
    db.execute("CREATE TABLE x (n INT)")
    for v in [1, 2, 3]:
        db.execute(f"INSERT INTO x VALUES ({v})")
    assert db.execute("SELECT * FROM x WHERE n <= 2") == [{"n": 1}, {"n": 2}]


def test_where_greater_than_or_equal():
    db = Database()
    db.execute("CREATE TABLE x (n INT)")
    for v in [1, 2, 3]:
        db.execute(f"INSERT INTO x VALUES ({v})")
    assert db.execute("SELECT * FROM x WHERE n >= 2") == [{"n": 2}, {"n": 3}]


def test_where_no_match_returns_empty():
    db = Database()
    db.execute("CREATE TABLE x (n INT)")
    db.execute("INSERT INTO x VALUES (1)")
    assert db.execute("SELECT * FROM x WHERE n > 100") == []


def test_where_combined_with_projection():
    db = Database()
    db.execute("CREATE TABLE users (id INT, name TEXT, age INT)")
    db.execute("INSERT INTO users VALUES (1, 'Alice', 30)")
    db.execute("INSERT INTO users VALUES (2, 'Bob', 25)")
    db.execute("INSERT INTO users VALUES (3, 'Charlie', 35)")
    rows = db.execute("SELECT name FROM users WHERE age > 25")
    assert rows == [{"name": "Alice"}, {"name": "Charlie"}]


# ---- Case sensitivity ----

def test_keywords_are_case_insensitive():
    db = Database()
    db.execute("create table users (id int, name text)")
    db.execute("insert into users values (1, 'Alice')")
    assert db.execute("select * from users") == [{"id": 1, "name": "Alice"}]


def test_mixed_case_keywords():
    db = Database()
    db.execute("Create Table users (id Int, name Text)")
    db.execute("Insert Into users Values (1, 'Alice')")
    assert db.execute("Select * From users Where id = 1") == [
        {"id": 1, "name": "Alice"}
    ]


def test_identifiers_are_case_sensitive():
    """Table 'users' and table 'Users' would be different (if both existed).
    Here we just check that the lookup respects case."""
    db = Database()
    db.execute("CREATE TABLE users (id INT)")
    db.execute("INSERT INTO users VALUES (1)")
    # 'Users' (capital U) is a different identifier — should error.
    with pytest.raises(Exception):
        db.execute("SELECT * FROM Users")


# ---- Errors ----

def test_select_from_unknown_table_raises():
    db = Database()
    with pytest.raises(Exception):
        db.execute("SELECT * FROM ghost")


def test_insert_into_unknown_table_raises():
    db = Database()
    with pytest.raises(Exception):
        db.execute("INSERT INTO ghost VALUES (1)")


def test_select_unknown_column_raises():
    db = Database()
    db.execute("CREATE TABLE users (id INT, name TEXT)")
    db.execute("INSERT INTO users VALUES (1, 'Alice')")
    with pytest.raises(Exception):
        db.execute("SELECT badcol FROM users")


def test_where_on_unknown_column_raises():
    db = Database()
    db.execute("CREATE TABLE users (id INT, name TEXT)")
    db.execute("INSERT INTO users VALUES (1, 'Alice')")
    with pytest.raises(Exception):
        db.execute("SELECT * FROM users WHERE badcol = 1")


def test_insert_wrong_number_of_values_raises():
    db = Database()
    db.execute("CREATE TABLE users (id INT, name TEXT)")
    with pytest.raises(Exception):
        db.execute("INSERT INTO users VALUES (1)")


def test_insert_type_mismatch_raises():
    """Inserting a string where INT is declared."""
    db = Database()
    db.execute("CREATE TABLE users (id INT, name TEXT)")
    with pytest.raises(Exception):
        db.execute("INSERT INTO users VALUES ('not_an_int', 'Alice')")


def test_unterminated_string_raises():
    db = Database()
    db.execute("CREATE TABLE x (s TEXT)")
    with pytest.raises(Exception):
        db.execute("INSERT INTO x VALUES ('unterminated")


def test_malformed_sql_raises():
    db = Database()
    with pytest.raises(Exception):
        db.execute("SELECT FROM users")    # missing column list


def test_malformed_create_raises():
    db = Database()
    with pytest.raises(Exception):
        db.execute("CREATE TABLE users id INT")    # missing parens


# ---- Integration / sequence ----

def test_multiple_tables_independent():
    db = Database()
    db.execute("CREATE TABLE a (x INT)")
    db.execute("CREATE TABLE b (y TEXT)")
    db.execute("INSERT INTO a VALUES (1)")
    db.execute("INSERT INTO b VALUES ('hello')")
    assert db.execute("SELECT * FROM a") == [{"x": 1}]
    assert db.execute("SELECT * FROM b") == [{"y": "hello"}]


def test_realistic_session():
    """End-to-end: walk through the example from problem.md."""
    db = Database()
    db.execute("CREATE TABLE users (id INT, name TEXT, age INT)")
    db.execute("INSERT INTO users VALUES (1, 'Alice', 30)")
    db.execute("INSERT INTO users VALUES (2, 'Bob', 25)")
    db.execute("INSERT INTO users VALUES (3, 'Charlie', 35)")

    assert db.execute("SELECT * FROM users") == [
        {"id": 1, "name": "Alice", "age": 30},
        {"id": 2, "name": "Bob", "age": 25},
        {"id": 3, "name": "Charlie", "age": 35},
    ]

    assert db.execute("SELECT name, age FROM users WHERE age > 25") == [
        {"name": "Alice", "age": 30},
        {"name": "Charlie", "age": 35},
    ]

    assert db.execute("SELECT * FROM users WHERE name = 'Bob'") == [
        {"id": 2, "name": "Bob", "age": 25},
    ]
