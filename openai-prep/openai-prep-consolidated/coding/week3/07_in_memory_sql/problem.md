# Problem 7: In-Memory SQL-Like Database (Method API)

**Prereqs:** Skim `00_prereqs.md`. Lighter than the full SQL-parsing version — no tokenizer, no parser.

**Time budget:** 45–60 minutes for base. 75–90 with follow-ups discussed.
**Source:** Reported by OpenAI candidates. This is the method-call variant of the "in-memory SQL" problem family. The SQL-string-parsing variant is a layered follow-up.

## Problem

Implement an in-memory database with table-creation, row-insertion, and row-selection. The API is **method calls, not parsed SQL strings.** This strips out the lexer/parser and lets you focus on storage design, predicate composition, and type checking.

```python
db = Database()

db.create_table("users", [("id", "INT"), ("name", "TEXT"), ("age", "INT")])

db.insert("users", {"id": 1, "name": "Alice", "age": 30})
db.insert("users", {"id": 2, "name": "Bob",   "age": 25})
db.insert("users", {"id": 3, "name": "Charlie", "age": 35})

db.select("users")
# [{"id": 1, "name": "Alice", "age": 30},
#  {"id": 2, "name": "Bob",   "age": 25},
#  {"id": 3, "name": "Charlie", "age": 35}]

db.select("users", columns=["name", "age"])
# [{"name": "Alice", "age": 30},
#  {"name": "Bob",   "age": 25},
#  {"name": "Charlie", "age": 35}]

db.select("users", where=lambda row: row["age"] > 25)
# [{"id": 1, "name": "Alice", "age": 30},
#  {"id": 3, "name": "Charlie", "age": 35}]

db.select("users", columns=["name"], where=lambda row: row["name"] == "Bob")
# [{"name": "Bob"}]
```

## Required API

- `Database()` — constructor, no args.
- `create_table(name: str, schema: list[tuple[str, str]])` — schema is `[(col_name, col_type), ...]`. Types: `"INT"` and `"TEXT"`. Returns `None`.
- `insert(table: str, row: dict[str, Any])` — row must have exactly the schema's columns (no missing, no extras), and each value must match its declared type. Returns `None`.
- `select(table: str, columns: list[str] | None = None, where: Callable[[dict], bool] | None = None)` — returns `list[dict]`. `columns=None` means all columns; `where=None` means all rows.

## Requirements

- **Storage layout is your call.** List-of-dicts is the recommended default. Be ready to defend it vs columnar.
- **Type checking on `insert`.** Inserting a string where an `INT` is declared raises. Inserting an int where a `TEXT` is declared raises.
- **Schema check on `insert`.** Missing column or extra column raises.
- **Column check on `select`.** Unknown column in `columns=[...]` raises.
- **Unknown table raises** on any operation.
- **Predicate is a callable.** The interviewer hands you the WHERE filter as a Python lambda. You apply it; you don't parse it. This is deliberate — the parsing layer is a follow-up.
- **`columns` controls projection order.** `columns=["c", "a"]` returns dicts with `c` before `a`.
- **Insertion order is preserved** in `select` (no implicit sorting).

## Error contract

| Condition | Detected during | Error |
|---|---|---|
| Unknown table | any op | raise |
| Insert with wrong column set | insert | raise |
| Insert with wrong type | insert | raise |
| Unknown column in projection | select | raise |

Pick one custom exception (e.g., `DatabaseError`) and use it consistently. Be ready to defend the choice — real DBs distinguish many error types; for the interview, one is fine.

## What an OpenAI interviewer is looking for

1. **Data-structure design is obvious.** Reader should see `tables: dict[str, list[dict]]` and `schemas: dict[str, list[Column]]` (or similar) and immediately understand the layout.
2. **Type check is real, not a `# TODO`.** Each `(col_name, col_type, value)` triple gets validated on insert, with a clean error.
3. **Predicate-as-callable.** The `where` lambda is just `[row for row in table if where(row)]`. No reinvention.
4. **Projection respects requested order.** `columns=["c", "a"]` — interviewers test this.
5. **Edge cases enumerated up front:** empty result, `where=None`, `columns=None`, missing table/column, type mismatch, insert with missing keys.
6. **Layered optimization.** Base: scan-all on every `select`. Follow-up: `create_index(table, column)` for equality lookups. Don't volunteer this until base works.

## Follow-ups (don't peek until base works)

<details>
<summary>Click to expand</summary>

1. **Predicate composition.** "Add AND / OR for WHERE." Since `where` is already a callable, compose them client-side: `where=lambda r: r["age"] > 25 and r["name"] == "Alice"`. The fact that *no API change is needed* is the lesson — this is the upside of the callable design.

2. **`delete` and `update`.** `db.delete("users", where=...)` and `db.update("users", {"age": 31}, where=...)`. Same predicate pattern.

3. **Indexes.** `db.create_index("users", "age")` builds `dict[value -> list[row_id]]`. The challenge: `select` with `where=lambda r: r["age"] == 30` has no way to know about the index — the lambda is opaque. So the follow-up forces a richer predicate API: `where={"age": ("=", 30)}` or a small AST. Discuss the trade-off; you don't have to implement it.

4. **`order_by` and `limit`.** `db.select("users", order_by="age", desc=True, limit=10)`. Stable sort. What's the time complexity?

5. **`join`.** `db.join("users", "orders", on=lambda u, o: u["id"] == o["user_id"])`. Nested-loop join first; mention hash join.

6. **Persistence.** Survive process restart. Serialize tables to JSON on every write? Use a write-ahead log? Discuss durability vs throughput.

7. **Concurrency.** Two threads call `insert` simultaneously. Single global `threading.Lock`? Per-table reader/writer lock? What guarantees do you provide? (You'll get asked this — be ready.)

8. **The SQL-string layer.** "Now accept SQL strings: `db.execute('SELECT * FROM users WHERE age > 25')`." This is the *full* parser variant. Sketch: tokenizer → recursive-descent parser → AST → translate WHERE-AST into a predicate lambda → call your existing `select`. The whole thing is a **wrapper around the method API you already built.** That framing is the key insight.

</details>

## Honest difficulty note

Base (CREATE + INSERT + SELECT with all three knobs) is genuinely **45–60 min** for someone with the prereq concepts loaded. If you're spending 40 min on storage layout, you've over-thought it — `dict[str, list[dict]]` and move on.

A strong attempt covers:
- All three methods working (~30 min)
- Type/schema checking on insert + column check on select (~10 min)
- Projection respects order (~5 min)
- Predicate works with combined `columns` + `where` (~5 min)
- Articulated path to: predicate composition (already free), index (with API trade-off), and the SQL-string layer as a wrapper

The interviewer cares more about clean separation between *storage*, *validation*, and *query* than about feature count.
