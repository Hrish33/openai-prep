# Problem 1: Spreadsheet with Formula Dependencies

**Prereqs:** Work through `00_prereqs.md` first. Don't attempt this cold.

**Time budget:** 60 minutes
**Source:** Reported by multiple OpenAI candidates (HelloInterview, Exponent)

## Problem

Implement a spreadsheet where cells can hold either literal values or formulas that reference other cells. Updating a cell propagates to all cells that depend on it.

```python
sheet = Spreadsheet()
sheet.set_cell("A1", 5)
sheet.set_cell("B1", 10)
sheet.set_cell("C1", "=A1+B1")
sheet.get_cell("C1")          # returns 15

sheet.set_cell("A1", 20)
sheet.get_cell("C1")          # returns 30

sheet.set_cell("D1", "=C1*2")
sheet.get_cell("D1")          # returns 60

sheet.set_cell("A1", 1)
sheet.get_cell("D1")          # returns 22 (propagated through C1)
```

## Required API

- `set_cell(cell_id: str, value)` — value is int, float, or formula string starting with `=`
- `get_cell(cell_id: str)` — returns evaluated value, or `None` if unset

Formula syntax: `=A1+B2` with binary operators `+`, `-`, `*`, `/`. Operands are cell refs or numeric literals. Single binary operation is enough for the base.

## Requirements

- **Updates propagate.** Changing a cell updates all its transitive dependents.
- **Cycle detection.** Reject cycles (direct and indirect) — raise `ValueError`. State must remain unchanged on rejection.
- **`get_cell` is O(1)** — don't re-evaluate the formula tree on every read.
- **`set_cell` can be O(D)** where D = number of transitive dependents.

## Constraints

- Cell IDs: opaque strings, no grid layout assumed
- Values: int, float, or formula string
- Division by zero: raise `ZeroDivisionError`
- Unset cell referenced in a formula: pick a behavior (0 or raise), be consistent, defend it

## What an OpenAI interviewer is looking for

1. **Edge cases up front.** Enumerate before coding: cycles (direct, indirect, self), unset refs, division by zero, parse errors.
2. **Defendable data structure choice.** Almost certainly: dependency graph + cached evaluated values. Be ready to explain why, and what lazy-on-read trades off against it.
3. **Cycle detection on `set_cell`, not on `get_cell`.** Catching at set time avoids infinite loops at evaluation time.
4. **Topological propagation order.** D1 depends on C1 — must update C1 first.
5. **Clean separation.** Parser, graph, evaluator should be separable. If `set_cell` is 80 lines, you've lost.

## Follow-ups (don't peek until base works)

<details>
<summary>Click to expand</summary>

1. Add ranges and aggregates: `=SUM(A1:A10)`
2. Make it thread-safe — what lock, where, contention cost?
3. Cache eval results — when do you invalidate?
4. 10M cells, only 100 changing per second — avoid recomputing everything?
5. Make `set_cell` async — what changes about propagation?
6. Persist to disk so it survives restarts
7. Two users edit different cells concurrently — consistency model?

</details>

## Honest difficulty note

This is harder than it looks. Expect to use most of the 60 minutes on your first attempt. Don't panic if you only get the base working without follow-ups — that's a passing performance, as long as the base is clean and you can articulate extensions.
