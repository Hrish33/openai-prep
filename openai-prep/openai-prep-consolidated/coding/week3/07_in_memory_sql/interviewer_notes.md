# Interviewer notes — In-Memory SQL

**Read after your attempt.** This is the reference solution, the design rationale, and a self-grading rubric.

## Reference solution

This implementation passes all 36 tests. Clean separation of tokenizer, parser, and executor — each stage is independently inspectable.

```python
import operator
from dataclasses import dataclass
from typing import Any, Optional


# ---- Tokens ----

@dataclass
class Token:
    type: str
    value: Any


KEYWORDS = {"CREATE", "TABLE", "INSERT", "INTO", "VALUES",
            "SELECT", "FROM", "WHERE", "INT", "TEXT"}


def tokenize(sql: str) -> list[Token]:
    tokens: list[Token] = []
    i = 0
    while i < len(sql):
        c = sql[i]
        if c.isspace():
            i += 1
        elif c == ',':
            tokens.append(Token("COMMA", ",")); i += 1
        elif c == '(':
            tokens.append(Token("LPAREN", "(")); i += 1
        elif c == ')':
            tokens.append(Token("RPAREN", ")")); i += 1
        elif c == '*':
            tokens.append(Token("STAR", "*")); i += 1
        elif sql[i:i+2] in ("!=", "<=", ">="):
            tokens.append(Token("OP", sql[i:i+2])); i += 2
        elif c in ("=", "<", ">"):
            tokens.append(Token("OP", c)); i += 1
        elif c == "'":
            j = i + 1
            while j < len(sql) and sql[j] != "'":
                j += 1
            if j >= len(sql):
                raise SyntaxError("unterminated string literal")
            tokens.append(Token("STRING", sql[i+1:j]))
            i = j + 1
        elif c.isdigit() or (c == '-' and i+1 < len(sql) and sql[i+1].isdigit()):
            j = i + 1
            while j < len(sql) and sql[j].isdigit():
                j += 1
            tokens.append(Token("INT", int(sql[i:j])))
            i = j
        elif c.isalpha() or c == '_':
            j = i + 1
            while j < len(sql) and (sql[j].isalnum() or sql[j] == '_'):
                j += 1
            word = sql[i:j]
            if word.upper() in KEYWORDS:
                tokens.append(Token("KEYWORD", word.upper()))
            else:
                tokens.append(Token("IDENT", word))
            i = j
        else:
            raise SyntaxError(f"unexpected character: {c!r}")
    return tokens


# ---- AST ----

@dataclass
class Column:
    name: str
    type: str


@dataclass
class CreateTable:
    name: str
    columns: list[Column]


@dataclass
class Insert:
    table: str
    values: list[Any]


@dataclass
class WhereClause:
    column: str
    op: str
    value: Any


@dataclass
class Select:
    columns: list[str]
    table: str
    where: Optional[WhereClause]


# ---- Parser (recursive descent) ----

class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    def _peek(self) -> Optional[Token]:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _consume(self, type_: Optional[str] = None,
                 value: Optional[str] = None) -> Token:
        if self.pos >= len(self.tokens):
            raise SyntaxError("unexpected end of input")
        tok = self.tokens[self.pos]
        if type_ and tok.type != type_:
            raise SyntaxError(f"expected {type_}, got {tok.type} ({tok.value!r})")
        if value is not None and tok.value != value:
            raise SyntaxError(f"expected {value!r}, got {tok.value!r}")
        self.pos += 1
        return tok

    def parse(self):
        kw = self._peek()
        if not kw or kw.type != "KEYWORD":
            raise SyntaxError("expected statement keyword")
        if kw.value == "CREATE":
            return self._parse_create()
        if kw.value == "INSERT":
            return self._parse_insert()
        if kw.value == "SELECT":
            return self._parse_select()
        raise SyntaxError(f"unknown statement: {kw.value}")

    def _parse_create(self) -> CreateTable:
        self._consume("KEYWORD", "CREATE")
        self._consume("KEYWORD", "TABLE")
        name = self._consume("IDENT").value
        self._consume("LPAREN")
        cols: list[Column] = []
        while True:
            col_name = self._consume("IDENT").value
            type_tok = self._consume("KEYWORD")
            if type_tok.value not in ("INT", "TEXT"):
                raise SyntaxError(f"unknown column type: {type_tok.value}")
            cols.append(Column(col_name, type_tok.value))
            if self._peek() and self._peek().type == "COMMA":
                self._consume("COMMA")
            else:
                break
        self._consume("RPAREN")
        return CreateTable(name, cols)

    def _parse_insert(self) -> Insert:
        self._consume("KEYWORD", "INSERT")
        self._consume("KEYWORD", "INTO")
        name = self._consume("IDENT").value
        self._consume("KEYWORD", "VALUES")
        self._consume("LPAREN")
        values: list[Any] = []
        while True:
            tok = self._consume()
            if tok.type not in ("INT", "STRING"):
                raise SyntaxError(f"expected literal in VALUES, got {tok.type}")
            values.append(tok.value)
            if self._peek() and self._peek().type == "COMMA":
                self._consume("COMMA")
            else:
                break
        self._consume("RPAREN")
        return Insert(name, values)

    def _parse_select(self) -> Select:
        self._consume("KEYWORD", "SELECT")
        cols: list[str] = []
        if self._peek() and self._peek().type == "STAR":
            self._consume("STAR")
            cols = ["*"]
        else:
            while True:
                cols.append(self._consume("IDENT").value)
                if self._peek() and self._peek().type == "COMMA":
                    self._consume("COMMA")
                else:
                    break
        self._consume("KEYWORD", "FROM")
        table = self._consume("IDENT").value
        where = None
        if self._peek() and self._peek().type == "KEYWORD" and self._peek().value == "WHERE":
            self._consume("KEYWORD", "WHERE")
            col = self._consume("IDENT").value
            op = self._consume("OP").value
            val_tok = self._consume()
            if val_tok.type not in ("INT", "STRING"):
                raise SyntaxError(f"WHERE value must be literal, got {val_tok.type}")
            where = WhereClause(col, op, val_tok.value)
        return Select(cols, table, where)


# ---- Executor ----

OP_FUNCS = {
    "=":  operator.eq,
    "!=": operator.ne,
    "<":  operator.lt,
    ">":  operator.gt,
    "<=": operator.le,
    ">=": operator.ge,
}


class Database:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict[str, Any]]] = {}
        self.schemas: dict[str, list[Column]] = {}

    def execute(self, sql: str) -> Optional[list[dict[str, Any]]]:
        tokens = tokenize(sql)
        ast = Parser(tokens).parse()
        return self._exec(ast)

    def _exec(self, ast):
        if isinstance(ast, CreateTable):
            self.tables[ast.name] = []
            self.schemas[ast.name] = ast.columns
            return None

        if isinstance(ast, Insert):
            if ast.table not in self.tables:
                raise KeyError(f"unknown table: {ast.table}")
            schema = self.schemas[ast.table]
            if len(ast.values) != len(schema):
                raise ValueError(f"expected {len(schema)} values, got {len(ast.values)}")
            row: dict[str, Any] = {}
            for col, val in zip(schema, ast.values):
                expected = int if col.type == "INT" else str
                if not isinstance(val, expected):
                    raise TypeError(
                        f"column {col.name} expects {col.type}, "
                        f"got {type(val).__name__}"
                    )
                row[col.name] = val
            self.tables[ast.table].append(row)
            return None

        if isinstance(ast, Select):
            if ast.table not in self.tables:
                raise KeyError(f"unknown table: {ast.table}")
            schema_cols = {c.name for c in self.schemas[ast.table]}

            if ast.columns == ["*"]:
                projected = [c.name for c in self.schemas[ast.table]]
            else:
                for c in ast.columns:
                    if c not in schema_cols:
                        raise KeyError(f"unknown column: {c}")
                projected = ast.columns

            if ast.where:
                if ast.where.column not in schema_cols:
                    raise KeyError(f"unknown column in WHERE: {ast.where.column}")
                op_fn = OP_FUNCS[ast.where.op]
                wcol, wval = ast.where.column, ast.where.value
                pred = lambda row: op_fn(row[wcol], wval)
            else:
                pred = lambda row: True

            return [
                {c: row[c] for c in projected}
                for row in self.tables[ast.table]
                if pred(row)
            ]

        raise NotImplementedError(f"unknown AST type: {type(ast).__name__}")
```

## Why this is the shape it is

**Three stages, three responsibilities, three places to put errors.**

- `tokenize` only handles character-level concerns: whitespace, multi-char operators, string termination, keyword classification. It doesn't know what a SELECT is.
- `Parser` only handles grammar: which tokens can follow which. It doesn't know what tables exist or what columns are valid.
- `Database._exec` is the only place that touches table data. It doesn't know about strings at all — it operates on AST nodes.

This separation is what an OpenAI interviewer is looking for. When they ask "add OR to WHERE," the answer should be: tokenize already handles OR (it'll be a keyword), parser needs precedence climbing in `_parse_where`, executor composes predicates with `or`. Three small changes in three predictable places, not one giant rewrite.

**Predicate-as-callable.** Instead of carrying the WHERE clause as data through execution, the executor compiles it once into a `lambda row: ...` and applies it during the scan. This is the natural Python equivalent of a query plan. It also makes the AND/OR follow-up trivial: predicates compose with `lambda r: left(r) and right(r)`.

**`operator` module instead of `if op == "=": ... elif op == "<":`.** Cleaner, and shows you know the stdlib. A reviewer should be able to find `OP_FUNCS` and see all supported operators at once.

**dataclasses for AST.** They give you a real type, free `__repr__` for debugging, free `__eq__` for testing the parser in isolation. Alternative is named tuples (more rigid) or plain classes (more boilerplate).

**`list[dict]` for tables.** Easiest to read in tests; easiest to talk about with an interviewer. Has obvious limits (O(N) scan) that you'd address in the indexes follow-up. Real DBs do not store rows as dicts — be ready to say so when asked "what would a real database do here?".

## Honest weaknesses to acknowledge

If you say nothing about these and the interviewer prods, you look unaware:

1. **No real type system.** Only `INT` and `TEXT`. No `NULL`, no `BOOL`, no `FLOAT`. Real SQL has a type hierarchy with implicit coercions and three-valued logic for NULL.
2. **No indexes.** Every SELECT is O(N). Stating this lets you naturally introduce indexes as the optimization.
3. **No transactions.** Two parallel `execute` calls would interleave rows. Mention it.
4. **No schema modification.** No `ALTER TABLE`, no `DROP TABLE`. Trivial to add but absent.
5. **Tokenizer doesn't handle escaped quotes** in strings (`'O''Brien'` would tokenize wrong). Mention this is a follow-up.
6. **Error class is overloaded** — using `KeyError`, `ValueError`, `TypeError`, `SyntaxError` based on what felt natural. A real DB would have a single `DatabaseError` hierarchy with subclasses. Defendable as "kept stdlib exceptions so the API is grep-able," but acknowledge the trade.
7. **No `print`/`repr` of query plan.** Real databases let you `EXPLAIN` queries. Adding a `plan(sql)` method that returns the AST would be a small, high-signal extension.

## Self-grading against the OpenAI rubric

| Axis | What this solution shows | What pushes it higher |
|---|---|---|
| **Practical problem-solving** | Pipeline shape over any clever trick. Iterates from CREATE → INSERT → SELECT → WHERE in obvious steps. | Walk through the staged build live: "first I get CREATE+INSERT+SELECT * working, then I add WHERE." |
| **Edge cases up front** | Empty result, no WHERE, SELECT *, unknown table/column, type mismatch, wrong arg count, unterminated string. | Enumerate these *before* writing the tokenizer, in a comment block. |
| **Layered optimization** | Base scan-all. Indexes are the natural next layer. | Have a concrete index plan ready: `dict[col_name, dict[value, list[row_idx]]]`, predicate-on-indexed-column uses the index. |
| **Python internals depth** | `operator` module, dataclasses, predicate-as-lambda. | Mention how you'd use `@dataclass(slots=True)` or `__slots__` for memory if rows scaled to millions. |
| **Targeted optimization under follow-up** | When asked "10M rows, queries on `id`?", proceed straight to the index. Don't talk about caching or threads. | Estimate the cost: index on INT column is ~40-80 bytes per row; for 10M rows that's ~500MB. Real number, not hand-waving. |
| **Test quality** | The provided tests cover happy path + projection + 6 ops + case sensitivity + 8 error conditions. | If you wrote your own tests first, mention the categories you targeted before looking at mine. |

## Follow-up sketches

### AND / OR in WHERE

```python
@dataclass
class And:
    left: Any   # WhereClause | And | Or
    right: Any

@dataclass
class Or:
    left: Any
    right: Any

def parse_where(parser):
    # OR has lower precedence than AND
    left = parse_and(parser)
    while peek_is_keyword(parser, "OR"):
        consume_keyword(parser, "OR")
        right = parse_and(parser)
        left = Or(left, right)
    return left

def parse_and(parser):
    left = parse_comparison(parser)
    while peek_is_keyword(parser, "AND"):
        consume_keyword(parser, "AND")
        right = parse_comparison(parser)
        left = And(left, right)
    return left

def make_pred(node):
    if isinstance(node, WhereClause):
        op = OP_FUNCS[node.op]
        return lambda r: op(r[node.column], node.value)
    if isinstance(node, And):
        l, r = make_pred(node.left), make_pred(node.right)
        return lambda row: l(row) and r(row)
    if isinstance(node, Or):
        l, r = make_pred(node.left), make_pred(node.right)
        return lambda row: l(row) or r(row)
```

### Indexes

```python
self.indexes: dict[str, dict[str, dict[Any, list[int]]]] = {}
# table_name -> column_name -> value -> list of row indices

def execute_select(self, ast):
    # ... if WHERE is `col = value` and an index exists on col:
    if ast.where and ast.where.op == "=" and ast.where.column in self.indexes.get(ast.table, {}):
        row_idxs = self.indexes[ast.table][ast.where.column].get(ast.where.value, [])
        rows = [self.tables[ast.table][i] for i in row_idxs]
    else:
        rows = [r for r in self.tables[ast.table] if pred(r)]
```

Key trade-off to articulate: **INSERT becomes slower** because every index must be updated. For write-heavy workloads, fewer indexes win. For read-heavy workloads, more indexes win. This is the textbook OLTP-vs-OLAP distinction.

### JOIN (nested-loop)

```python
@dataclass
class Join:
    left_table: str
    right_table: str
    left_col: str
    right_col: str

# In executor:
for l_row in left_table:
    for r_row in right_table:
        if l_row[left_col] == r_row[right_col]:
            yield {**l_row, **r_row}
```

`O(N * M)`. Mention hash join as the optimization: build a dict on the smaller side, scan the larger. `O(N + M)`.

### Concurrency

Per-table reader/writer lock is the natural answer. Multiple SELECTs can run concurrently; INSERT/DELETE/UPDATE need exclusive. MVCC (multi-version concurrency control — Postgres style) is what real databases do, but that's a 30-minute discussion, not a coding answer.

## Common mistakes interviewers see

1. **Using `eval()` or `exec()` for WHERE.** Disqualifying. The point of the problem is implementing SQL, not delegating to Python.
2. **Tokenizing with `sql.split()`.** Works for the example but breaks on `WHERE name='Alice'` (no space). Spend the 10 minutes on a real character-by-character tokenizer.
3. **Skipping the AST.** "I'll just parse and execute in one pass." Works for CREATE; falls apart when WHERE needs predicates composed. Reviewer will ask "how do you add AND?" and you have nowhere to put it.
4. **`if 'WHERE' in sql:` string matching.** Looks fine until `INSERT INTO users VALUES (1, 'WHEREwolf')` comes in. Tokenize first, then check.
5. **Returning tuples instead of dicts from SELECT.** Loses column names. The user has to remember positional order. dicts (or named tuples) keep the interface readable.
6. **No projection — returning all columns even on `SELECT name FROM users`.** Trivial bug, looks bad in review.
7. **Mutating shared state on error.** Adding the row to the table *before* checking the type means a failed INSERT leaves a half-committed row. Check first, then commit.
8. **Spending 30 minutes on the tokenizer.** Time-management failure. If tokenization is taking too long, fall back to a hacky one (split + special-case strings) and come back to it.

## What "passing" looks like in 75 minutes

- **30 min:** CREATE TABLE + INSERT + SELECT * working. No WHERE yet. Walk through your token list and AST shape with the interviewer.
- **50 min:** WHERE with one operator working. Add the other operators (mostly copy-paste in OP_FUNCS).
- **65 min:** Tests for error cases (unknown table, type mismatch). Articulate the index follow-up even if you don't code it.
- **75 min:** Wrap with "I'd add AND/OR next by extending the WHERE parser with precedence — here's the shape." Don't leave broken code on screen.

A clean base + articulated extensions beats a buggy attempt at JOINs every time.
