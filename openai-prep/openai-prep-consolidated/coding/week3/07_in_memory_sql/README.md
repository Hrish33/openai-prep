# Problem 7: In-Memory Database with SQL Operations

**Status:** Not yet scaffolded. Tell Claude Code "scaffold problem 7" when you're ready.

**One-liner:** Implement a subset of SQL in memory — tables, INSERTs, SELECTs with WHERE, possibly JOINs.

**Source:** [HelloInterview community question](https://www.hellointerview.com/community/questions/memory-database-sql/cmbsl00wk004v07adwuorveqo)

**Key concept:** parsing + execution + relational thinking

**Likely prereqs:**
- Problem 1 (spreadsheet) for the parsing experience — same shape, different syntax
- [LeetCode 1242 — basic concepts of SQL execution](https://leetcode.com/problemset/database/) — not a specific problem; just being comfortable with SQL semantics
- Read: how a real SQL parser tokenizes (e.g., look at the structure of SQLite's parser at a high level — don't read source, just understand the concept of tokens → AST → execution plan)
- Concept guide (to be generated when you reach this): `coding/concepts/parsing.md`

**When to do this:** week 3. **Largest problem in the set** — budget 75-90 min for first attempt. Don't tackle until you've done spreadsheet, since it has the same parser-graph-evaluator shape but bigger.
