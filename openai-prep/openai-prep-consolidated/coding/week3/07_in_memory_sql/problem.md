# Problem 7: In-Memory Database with SQL Operations

**Prereqs:** Work through `00_prereqs.md` first. This problem will eat 90 minutes if you skip prep.

**Time budget:** 75–90 minutes
**Source:** Reported by multiple OpenAI candidates (HelloInterview community thread)

## Problem

Implement an in-memory database that accepts SQL-like statements as strings. Support `CREATE TABLE`, `INSERT INTO`, and `SELECT` with a single-condition `WHERE`. Tokenize, parse, and execute — no `eval()`.

```python
db = Database()

db.execute("CREATE TABLE users (id INT, name TEXT, age INT)")
db.execute("INSERT INTO users VALUES (1, 'Alice', 30)")
db.execute("INSERT INTO users VALUES (2, 'Bob', 25)")
db.execute("INSERT INTO users VALUES (3, 'Charlie', 35)")

db.execute("SELECT * FROM users")
# [{"id": 1, "name": "Alice", "age": 30},
#  {"id": 2, "name": "Bob", "age": 25},
#  {"id": 3, "name": "Charlie", "age": 35}]

db.execute("SELECT name, age FROM users WHERE age > 25")
# [{"name": "Alice", "age": 30},
#  {"name": "Charlie", "age": 35}]

db.execute("SELECT * FROM users WHERE name = 'Bob'")
# [{"id": 2, "name": "Bob", "age": 25}]
```

## Required API

- `Database()` — constructor, no args
- `execute(sql: str)` — returns:
  - `list[dict]` for `SELECT` (empty list if no rows match)
  - `None` for `CREATE TABLE` and `INSERT INTO`

## Required SQL subset

**CREATE TABLE:**
```sql
CREATE TABLE <name> (<col> <type>, <col> <type>, ...)
```
- Types: `INT`, `TEXT`
- Column names are case-sensitive; SQL keywords are case-insensitive

**INSERT INTO (positional):**
```sql
INSERT INTO <table> VALUES (<value>, <value>, ...)
```
- Number of values must match number of columns; type must match.
- Integer literals: `42`, `-7`.
- String literals: `'Alice'` (single quotes). No escape handling needed for base.

**SELECT:**
```sql
SELECT * FROM <table>
SELECT <col>, <col> FROM <table>
SELECT * FROM <table> WHERE <col> <op> <value>
```
- `<op>` ∈ `{=, !=, <, >, <=, >=}`
- Single WHERE condition for base. No AND/OR yet.

## Requirements

- **Tokenize → Parse → Execute** as distinct stages. The executor must not see raw strings.
- **No `eval()` or `exec()`.** WHERE evaluation must walk your AST.
- **Case-insensitive keywords, case-sensitive identifiers.** `select * from Users` works; `SELECT * FROM users` returns nothing if the table is `Users`.
- **Type checking on INSERT.** Inserting a string where an INT is declared raises an error before the row is added.
- **Unknown table / column raises an error** at execute time (not parse time — parser doesn't know about your tables).

## Error contract

Pick one error class and use it consistently for SQL errors. (Real DBs distinguish syntax errors from semantic errors; for the interview, one custom exception is fine — but be ready to defend the choice.)

| Condition | When detected | Error |
|---|---|---|
| Unterminated string literal | tokenize | raise |
| Unexpected/missing token | parse | raise |
| Unknown table | execute | raise |
| Unknown column | execute | raise |
| Type mismatch on INSERT | execute | raise |
| Wrong number of values on INSERT | execute | raise |

## What an OpenAI interviewer is looking for

1. **The pipeline is obvious from the code structure.** A reader should be able to find your tokenizer, parser, and executor in seconds.
2. **AST is real.** `Select(columns=['name'], table='users', where=Where('age', '>', 25))` — actual objects, not nested dicts.
3. **No `eval()`.** Show that you understand `eval()` defeats the purpose of writing the SQL implementation, and is a security hole on top.
4. **Edge cases enumerated up front:** empty result set, no WHERE clause, `SELECT *`, missing table/column, type mismatch. Mention these *before* you start coding.
5. **Layered optimization.** Base: scan-all on every SELECT. Follow-up: index on primary key, predicate on indexed column. Don't volunteer this until base works — but be ready when they ask.

## Follow-ups (don't peek until base works)

<details>
<summary>Click to expand</summary>

1. **AND / OR in WHERE.** `WHERE age > 25 AND name = 'Alice'`. Parser change: precedence (OR is lower than AND); executor change: predicates compose with `and`/`or`.

2. **DELETE / UPDATE.** `DELETE FROM users WHERE id = 1`; `UPDATE users SET age = 31 WHERE name = 'Alice'`. Same pipeline, two new statement types.

3. **Indexes.** `CREATE INDEX idx_age ON users (age)`. SELECT with predicate on indexed column uses the index instead of scanning. When does the index help, and when does it hurt?

4. **ORDER BY / LIMIT.** `SELECT * FROM users ORDER BY age DESC LIMIT 10`. Stable sort. What's the time complexity?

5. **JOIN.** `SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id`. Nested-loop join first; mention hash join as the optimization.

6. **Persistence.** Survive process restart. Serialize tables to JSON on every write? Use a write-ahead log? Discuss durability vs throughput.

7. **Concurrency.** Two threads call `execute` simultaneously. Reader/writer lock per table? MVCC? What guarantees do you provide?

8. **Aggregates.** `SELECT COUNT(*), AVG(age) FROM users`. Doesn't fit the "row dict" output shape — what changes?

9. **Subqueries.** `SELECT * FROM users WHERE id IN (SELECT user_id FROM orders)`. Now the parser needs recursive statement parsing. Big refactor or natural extension?

</details>

## Honest difficulty note

This is the **largest problem in the set.** Expect to spend the full 90 minutes on your first attempt and not finish all follow-ups. A passing performance is:

- CREATE + INSERT + SELECT-without-WHERE working end-to-end (~30 min)
- SELECT with single WHERE working (~50 min)
- Articulated path to AND/OR and DELETE, even if not implemented

Don't get stuck on the tokenizer for 30 minutes. If you're not done with tokenization in 15, fall back to a simpler approach (e.g., split on whitespace and special-case strings — it's hacky but ships).

The interviewer will care more about clean separation between stages than about supporting more SQL features.
