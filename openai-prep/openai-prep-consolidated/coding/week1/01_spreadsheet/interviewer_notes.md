# Interviewer notes — Spreadsheet

**Read AFTER your attempt.** Reading first defeats the point.

This reference is deliberately **scrappy, not polished** — it's what a passing-but-not-perfect attempt actually looks like in 45-60 minutes. No regex, no clever helpers, no `Cell` wrapper class. The point is something you could actually rebuild from scratch under pressure, not a code-golf showpiece.

## Reference solution (scrappy version)

```python
import collections
from typing import Union, Optional

CellValue = Union[int, float, str]


class Spreadsheet:
    def __init__(self):
        self._raw = {}                                    # cell -> raw int/float/formula string
        self._value = {}                                  # cell -> cached evaluated number (O(1) reads)
        self._depends_on = collections.defaultdict(set)   # cell -> cells it needs
        self._dependents = collections.defaultdict(set)   # cell -> cells that need it

    def set_cell(self, cell_id: str, value: CellValue) -> None:
        new_deps = self._parse_deps(value)

        # 1. cycle check BEFORE mutating any state
        if self._would_cycle(cell_id, new_deps):
            raise ValueError(f"cycle creating {cell_id}")

        # 2. remove old reverse edges
        for old in self._depends_on[cell_id]:
            self._dependents[old].discard(cell_id)

        # 3. install new state
        self._raw[cell_id] = value
        self._depends_on[cell_id] = new_deps
        for d in new_deps:
            self._dependents[d].add(cell_id)

        # 4. recompute cell_id and every transitive dependent, in topo order
        for c in self._topo_order(cell_id):
            self._value[c] = self._evaluate(c)

    def get_cell(self, cell_id: str) -> Optional[Union[int, float]]:
        return self._value.get(cell_id)

    # ---- helpers ----

    def _parse_deps(self, value):
        """Cell IDs referenced in a formula. Empty for non-formulas."""
        if not isinstance(value, str) or not value.startswith("="):
            return set()
        expr = value[1:]
        for op in "+-*/":
            expr = expr.replace(op, " ")
        deps = set()
        for tok in expr.split():
            if tok and tok[0].isalpha():
                deps.add(tok)
        return deps

    def _would_cycle(self, cell_id, new_deps):
        """Would adding cell_id -> new_deps create a cycle? Plain recursive DFS reachability."""
        seen = set()

        def reaches_cell_id(node):
            if node == cell_id:
                return True
            if node in seen:
                return False
            seen.add(node)
            for neighbor in self._depends_on[node]:
                if reaches_cell_id(neighbor):
                    return True
            return False

        for dep in new_deps:
            if reaches_cell_id(dep):
                return True
        return False

    def _topo_order(self, start):
        """[start + every transitive dependent] in evaluation order (deps before dependents)."""
        # find the affected subgraph by recursive DFS through dependents
        affected = set()

        def collect(node):
            if node in affected:
                return
            affected.add(node)
            for dependent in self._dependents[node]:
                collect(dependent)

        collect(start)

        # DFS post-order on depends_on (limited to affected set) = topological order
        order = []
        visited = set()

        def visit(node):
            if node in visited:
                return
            visited.add(node)
            for dep in self._depends_on[node]:
                if dep in affected:
                    visit(dep)
            order.append(node)

        for c in affected:
            visit(c)
        return order

    def _evaluate(self, cell_id):
        """Compute one cell's value from its raw input and currently-cached neighbors."""
        raw = self._raw.get(cell_id)
        if not isinstance(raw, str):
            return raw                                    # literal int/float
        expr = raw[1:]                                    # strip the '='
        for op in "+-*/":
            if op in expr:
                left, right = expr.split(op, 1)
                lv = self._operand(left)
                rv = self._operand(right)
                if op == "+":
                    return lv + rv
                if op == "-":
                    return lv - rv
                if op == "*":
                    return lv * rv
                if op == "/":
                    return lv / rv
        return self._operand(expr)                        # single ref or literal, no op

    def _operand(self, tok):
        """Resolve one operand: cell ref -> cached value (0 if unset), else parse as literal."""
        tok = tok.strip()
        if tok[0].isalpha():
            return self._value.get(tok, 0)                # unset cell = 0
        return float(tok) if "." in tok else int(tok)
```

## Walking through `set_cell`

The whole method has 4 steps. Memorize the steps, not the syntax:

1. **Parse new deps.** What cells does this new value reference?
2. **Cycle check on a HYPOTHETICAL graph.** Would adding `cell_id -> new_deps` create a back-path? If yes, raise — don't touch state.
3. **Commit edges.** Remove old reverse-edges, install new ones, store the raw value.
4. **Topo-sort the affected subgraph and re-evaluate.**

The whole reason this problem is hard is step 4. Steps 1-3 are bookkeeping; step 4 is the real algorithm. If you're stuck, focus your re-attempt on `_topo_order` and `_evaluate` — those are the two pieces that compose.

## Why two graph directions?

| Question | Direction needed |
|----|----|
| "When A1 changes, who needs to re-compute?" | dependents (reverse) — walk downstream from A1 |
| "When computing C1, what values do I need first?" | depends-on (forward) — used by topo sort to order evaluation |

You can technically store only one and re-derive the other by re-parsing raw formulas, but it makes the code uglier. Storing both is two `defaultdict(set)`s — cheap.

## Why topo sort, not just BFS down dependents?

Diamond/cross-edge graphs break naive BFS:

```
A1 → B1, D1 (D1 references A1 directly)
B1 → C1
C1 → D1 (D1 also references C1)
```

When A1 changes, BFS would enqueue B1 and D1 first, then process D1 before C1 has been recomputed → D1 reads stale C1.

Topological sort processes a cell only **after all its dependencies are done**. The DFS post-order on `depends_on` (within the affected subgraph) gives exactly that order.

## Honest weaknesses to acknowledge in interview

- **Parser breaks on multi-op formulas.** `=A1+B1*C1` would split wrong. Mention it as a known limit; offer regex tokenization as the fix.
- **No precedence, no parens, no functions** (`SUM`, etc.). Out of scope for base.
- **Eager re-eval on every set** means writes are O(D). Lazy eval (mark dirty, compute on read) trades writes for reads — viable alternative for write-heavy workloads.
- **Division by zero** propagates a raw `ZeroDivisionError`. Spec accepts this; some interviewers would want a custom error type.
- **Storing both edge directions** doubles memory vs storing one and re-deriving.

## Grading yourself

| Axis | Passing |
|------|---------|
| Edge cases up front | Named: direct cycle, indirect cycle, self-ref, unset ref, div-by-zero, parse errors |
| Data structure choice | Picked forward + reverse graph and can explain the two directions |
| Cycle detection on `set` | Caught BEFORE mutating state (no rollback needed) |
| Topological propagation | Not just re-evaluating in insertion order — actually topo-sorts affected subgraph |
| Code structure | Parser, graph, evaluator are visibly separable; no 60+ line `set_cell` |
| Follow-up readiness | "Make it thread-safe / lazy / handle ranges" doesn't make you freeze |

## Follow-up sketches

### 1. Thread safety
Wrap the public methods in a single `threading.Lock`. Both `set` and `get` need it — `get` returns a cached value but the cache can be mid-write. Per-cell locks introduce deadlock risk and require lock ordering. For better read concurrency: `RWLock` (readers can read in parallel, writers exclusive) — at the cost of `get` possibly seeing stale-but-consistent values during a propagation.

### 2. Lazy evaluation
Instead of re-evaluating in `set_cell`, mark every affected cell dirty. In `get_cell`, if dirty, recursively compute (and clean) on read.

```python
def set_cell(self, ...):
    # ... cycle check, install edges ...
    for c in self._affected(cell_id):
        self._dirty.add(c)

def get_cell(self, cell_id):
    if cell_id in self._dirty:
        self._compute(cell_id)            # recursively cleans deps too
    return self._value.get(cell_id)
```

Trade: writes become O(D) marks (fast), reads become O(formula depth) on first access after a change. Best for write-heavy workloads.

### 3. Ranges (`=SUM(A1:A10)`)
Parser needs range syntax. Dep set expands: `SUM(A1:A10)` depends on A1..A10. Watch out for: ranges that include the current cell (cycle), ranges where bounds are themselves formulas.

### 4. Async `set_cell`
Wrap propagation in `asyncio.create_task`. Ordering matters — back-to-back sets on overlapping cells can interleave incorrectly. Serialize via an `asyncio.Lock`, or queue updates into a single propagation task.

### 5. 10M cells, only 100 changing per second
Don't recompute everything. Affected subgraph is what `_topo_order` already isolates — make sure it stays small. Consider lazy + dirty marks (#2) so untouched cells cost nothing.

## Common mistakes interviewers see

1. **Using `eval()` on the formula string.** Hard fail — security hole, and shows you didn't think about parsing.
2. **Cycle check after mutating state, then trying to roll back.** Brittle. Check first on the hypothetical graph.
3. **Re-evaluating the entire sheet on every set.** Slow and obviously wrong at scale.
4. **Storing only forward edges.** Propagation becomes O(N) per set instead of O(D), because you have to scan every cell asking "do you depend on this?"
5. **Recursive evaluation in `get_cell` without caching.** Re-computes the whole formula tree on every read — `get_cell` is supposed to be O(1).
6. **String-replacing cell IDs into the formula** (e.g., `"=A1+B1".replace("A1", "5")`). Looks clever, breaks on substring collisions (`A1` vs `A11`), and is a slippery slope back to `eval()`.
7. **Walking dependents (downstream) for evaluation order.** Dependents direction gives you the *affected set*, but the *order* you evaluate in must come from the depends_on direction (deps before dependents). Easy to confuse.

## Want a Round 2?

After you've internalized the shape above, try the **lazy-eval variant** as a separate file (`solution_lazy.py`). Same tests should pass. Comparing your two implementations is the best way to see why the eager-vs-lazy choice matters.
