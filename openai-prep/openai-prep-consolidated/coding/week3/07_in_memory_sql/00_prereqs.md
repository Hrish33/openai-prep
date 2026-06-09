# Problem 7 prereqs — In-Memory SQL

This is the **biggest problem in the set.** Don't attempt cold — the failure mode is spending 30 minutes on the tokenizer and never getting to a working SELECT. The prereqs below front-load the design so the actual session is "translate the design to code," not "figure out what to do."

Time budget: 2–4 hours of prep, depending on how fresh parsing is for you. Then attempt the problem in 75–90 minutes.

---

## Concept 1: Tokenizer → Parser → Executor — the three-stage pipeline

**Why this matters:** SQL is a *language*. Any non-trivial language implementation has the same three-stage shape:
1. **Tokenizer (lexer):** raw string → list of tokens (`SELECT`, `*`, `FROM`, identifier `users`, etc.). Strips whitespace, recognizes keywords, classifies literals.
2. **Parser:** tokens → AST (abstract syntax tree). Validates grammar, produces a tree of objects like `SelectStatement(columns=..., table=..., where=...)`.
3. **Executor:** AST → result. Walks the table data structures, applies the WHERE predicate, projects the columns.

This separation **is the design decision** of the problem. If you write one big `execute(sql)` method that does everything, you've lost. Interviewer will say "now add OR to WHERE" and you'll be rewriting a 200-line monolith.

**Drill:** Write a calculator that supports `+`, `-`, `*`, `/`, parentheses. Use the three-stage pipeline. If you can do this cold, you're set for the SQL pipeline shape.

```python
# Target API:
class Calculator:
    def evaluate(self, expr: str) -> float: ...

calc = Calculator()
calc.evaluate("1 + 2 * 3")        # 7
calc.evaluate("(1 + 2) * 3")      # 9
calc.evaluate("10 / 2 - 1")       # 4
```

If you skip this and dive straight into SQL, the parser will eat your 90 minutes.

---

## Concept 2: Recursive descent parsing

For SQL with its limited grammar (no nested subqueries in our base), **recursive descent** is the right tool. Each grammar rule becomes a function:

```python
def parse_statement():       # CREATE | INSERT | SELECT
def parse_select():          # SELECT <cols> FROM <table> [WHERE <pred>]
def parse_columns():         # * | identifier (, identifier)*
def parse_where():           # column op value
def parse_value():           # int | string | identifier
```

Each function:
- Consumes tokens from a shared cursor
- Calls sub-rules for sub-expressions
- Returns an AST node
- Raises a parse error with the offending token if grammar fails

**Key trick:** the cursor (or token index) is shared state. Either pass it around or make it `self.pos` on a Parser class. Don't try to use generators for this — index-based is simpler and lets you peek ahead.

```python
class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
    
    def peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None
    
    def consume(self, expected=None):
        tok = self.tokens[self.pos]
        if expected and tok.type != expected:
            raise SyntaxError(f"expected {expected}, got {tok}")
        self.pos += 1
        return tok
```

**LeetCode warmups:**
- [LC 224 — Basic Calculator](https://leetcode.com/problems/basic-calculator/) — `+ - ( )`. Pure recursive descent.
- [LC 227 — Basic Calculator II](https://leetcode.com/problems/basic-calculator-ii/) — adds `* /`. Operator precedence.
- [LC 772 — Basic Calculator III](https://leetcode.com/problems/basic-calculator-iii/) (premium) — combines everything. If you can do this cold, you can parse SQL.

Do at least LC 224. You don't need precedence climbing for SQL WHERE in the base case (single condition), but you'll want it for the AND/OR follow-up.

---

## Concept 3: Tokens — what to recognize, what to skip

For a base SQL subset, your tokenizer needs to recognize:

| Token type | Examples |
|---|---|
| `KEYWORD` | `SELECT`, `FROM`, `WHERE`, `CREATE`, `TABLE`, `INSERT`, `INTO`, `VALUES`, `INT`, `TEXT` |
| `IDENTIFIER` | `users`, `name`, `age` (anything that isn't a keyword and matches `[a-zA-Z_][a-zA-Z0-9_]*`) |
| `INT_LITERAL` | `42`, `100` |
| `STRING_LITERAL` | `'Alice'`, `'hello world'` |
| `OPERATOR` | `=`, `!=`, `<`, `>`, `<=`, `>=` |
| `PUNCTUATION` | `(`, `)`, `,`, `*` |

**Things that trip people up:**

1. **Case-insensitive keywords.** `SELECT`, `select`, `Select` are all the SELECT keyword. But identifiers (table/column names) are typically case-sensitive. Decide your policy and stick to it. (For the interview, "keywords case-insensitive, identifiers case-sensitive" is the standard answer.)

2. **String literals with quotes.** `'O''Brien'` is "O'Brien" in real SQL (escaped quote). For the interview base, don't handle escaping — just `'Alice'`. Mention in the follow-up that you'd handle escapes.

3. **Multi-character operators.** `<=` must be one token, not `<` then `=`. Your tokenizer needs lookahead.

4. **Keyword vs identifier disambiguation.** Tokenize as identifier first, then if the lowercase form matches a keyword, reclassify. Or: maintain a `KEYWORDS = {"SELECT", "FROM", ...}` set and check after grabbing the identifier.

---

## Concept 4: Tables in memory — the data structure

Real databases use B-trees, page caches, write-ahead logs. For 90 minutes, you have two viable options:

**Option A: List of dicts**
```python
table = [
    {"id": 1, "name": "Alice", "age": 30},
    {"id": 2, "name": "Bob",   "age": 25},
]
```
- Pro: trivial INSERT (`table.append(row)`), trivial SELECT (filter + project on each dict).
- Pro: serializes to JSON if you need persistence later.
- Con: O(N) for every operation. No indexes.

**Option B: Columnar — dict of column → list**
```python
table = {
    "id":   [1, 2],
    "name": ["Alice", "Bob"],
    "age":  [30, 25],
}
```
- Pro: closer to how real analytical DBs (Snowflake, BigQuery) store data.
- Pro: nice for "SELECT one column from a wide table."
- Con: row-oriented operations (full-row INSERT, full-row SELECT) require more bookkeeping.

**For the interview, default to Option A.** It's the simplest, the executor code reads naturally, and it's easy to explain. Mention Option B in the follow-up when interviewer asks "what if rows are very wide and queries touch few columns?"

You'll also need a registry of tables and their schemas:

```python
class Database:
    def __init__(self):
        self.tables: dict[str, list[dict]] = {}      # name → rows
        self.schemas: dict[str, list[Column]] = {}   # name → column defs
```

The schema is what enforces type checks on INSERT and column existence on SELECT.

---

## Concept 5: The executor — WHERE as a predicate

The cleanest shape: parse WHERE into a *callable predicate*, then filter the rows with it.

```python
where_pred = parser.parse_where()         # returns lambda row: row["age"] > 25
matching = [row for row in table if where_pred(row)]
```

Mapping AST to predicate:
```python
def make_predicate(node):
    if node is None:
        return lambda row: True              # no WHERE clause matches everything
    col, op, value = node.column, node.op, node.value
    ops = {"=": eq, "!=": ne, "<": lt, ">": gt, "<=": le, ">=": ge}
    return lambda row: ops[op](row[col], value)
```

This is a clean separation: parser produces structure, executor turns structure into a callable. **Don't `eval()` user-supplied SQL strings to evaluate WHERE — that's the cardinal sin of this problem.** You're writing the SQL implementation; `eval()` is cheating *and* a security hole.

For AND/OR follow-up: predicates compose naturally.
```python
def make_and(left, right): return lambda row: left(row) and right(row)
def make_or(left, right):  return lambda row: left(row) or right(row)
```

---

## Concept 6: Errors and where they originate

A real SQL parser produces *good* error messages. For the interview, you don't need column-level pinpointing, but you should know **which stage** an error comes from:

| Error | Stage | Example |
|---|---|---|
| Unterminated string | Tokenizer | `SELECT * FROM users WHERE name = 'Alice` |
| Unexpected token | Parser | `SELECT FROM users` |
| Unknown table | Executor | `SELECT * FROM doesntexist` |
| Unknown column | Executor | `SELECT badcol FROM users` |
| Type mismatch | Executor | `INSERT INTO users (id) VALUES ('not_an_int')` |

The interviewer may push on this: "what error does `SELECT FROM users` produce?" The answer is a *SyntaxError at parse time*, not at execute time. Knowing where each error lives demonstrates that you actually built the pipeline rather than wrote a string-matching hack.

---

## Suggested order

1. **(30 min)** LC 224 (basic calculator) — get recursive descent into your hands.
2. **(15 min)** Sketch your token types and tokenizer on paper. What's the input → output for `SELECT * FROM users WHERE age > 25`?
3. **(15 min)** Sketch your AST classes: `CreateTable`, `Insert`, `Select`, `WhereClause`.
4. **(10 min)** Sketch the executor: how does `Select` AST become "filter rows + project columns"?
5. **Attempt the problem.** Aim for: CREATE + INSERT + SELECT-without-WHERE working in the first 30 minutes, then add WHERE.

**When you can:**
- Tokenize the example SQL above without ambiguity
- Sketch the AST shape for `SELECT name, age FROM users WHERE age > 25`
- Explain how the executor evaluates WHERE without `eval()`

…attempt the problem.

---

## What an interviewer at OpenAI specifically values for this problem

1. **Pipeline separation.** You should be able to point at the tokenizer, parser, and executor as distinct things. Not one 200-line method.
2. **No `eval()`.** It works, but it tells the interviewer you didn't understand the assignment. The whole point is *you implementing* SQL.
3. **AST is a real data structure.** Either dataclasses, classes, or named tuples — not nested dicts with magic string keys. The interviewer should be able to look at `Select(columns=['name'], table='users', where=WhereClause('age', '>', 25))` and read the program.
4. **Edge cases enumerated up front:** empty result, no WHERE, SELECT *, column doesn't exist, type mismatch on INSERT, unknown table.
5. **Layered optimization** (OpenAI rubric axis): base scan-all is fine; the follow-up is "add an index for primary key" or "WHERE on indexed column." Be ready.

Related concept guides you may want to generate as you go:
- [[concepts/parsing.md]] — recursive descent in depth (will be created when you reach this problem if not already)

Related problems in this repo:
- Problem 1 (spreadsheet) — same parse-then-evaluate shape, simpler grammar. If you nailed that, this is the bigger sibling.
