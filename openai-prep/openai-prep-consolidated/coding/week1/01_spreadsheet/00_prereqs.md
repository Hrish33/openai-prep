# Prereqs — Spreadsheet with formula dependencies

**Don't attempt the problem until you've worked through this.** Estimated time: 3-5 hours spread over 4-5 days.

The spreadsheet problem combines 4 skills. Each is its own LeetCode primer below. Do them in order — each builds on the previous.

---

## Concept 1: Graphs as adjacency dicts

**What you're learning:** representing a graph as `dict[Node, set[Neighbor]]` and traversing it with BFS or DFS. Almost every problem on this list will use this representation.

**Mental model:**
```python
# Directed graph: A -> B, A -> C, B -> D
graph: dict[str, set[str]] = {
    "A": {"B", "C"},
    "B": {"D"},
    "C": set(),
    "D": set(),
}
```

That's it. Most "graph problems" at companies like OpenAI use this structure, not fancy `Graph` classes.

**Practice problem:** [LeetCode 133 — Clone Graph](https://leetcode.com/problems/clone-graph/) (Medium)
- Why this one: forces you to traverse and reconstruct a graph; you'll write BFS or DFS with a visited set
- Time budget: 30 min
- After you solve it: re-solve from scratch the next day with the other traversal (if you used BFS, do DFS, and vice versa)

**Done when:** you can write BFS over an adjacency dict from memory without looking anything up.

---

## Concept 2: Cycle detection in a directed graph

**What you're learning:** detecting whether a directed graph contains a cycle. This is *the* core skill for the spreadsheet's `set_cell` — you must reject a formula that would create a cycle BEFORE installing it.

**Mental model — the three-color DFS:**

Each node has one of three states during the traversal:
- **WHITE** — not visited yet
- **GRAY** — currently being visited (on the active DFS path)
- **BLACK** — fully done, all descendants explored

A cycle exists iff you encounter a GRAY node during DFS. Reaching a BLACK node is fine (it's already explored, no cycle through it).

```python
WHITE, GRAY, BLACK = 0, 1, 2

def has_cycle(graph: dict[str, set[str]]) -> bool:
    color = {node: WHITE for node in graph}
    
    def dfs(node: str) -> bool:
        if color[node] == GRAY:
            return True  # found a back edge → cycle
        if color[node] == BLACK:
            return False  # already explored, no cycle through here
        color[node] = GRAY
        for neighbor in graph.get(node, set()):
            if dfs(neighbor):
                return True
        color[node] = BLACK
        return False
    
    return any(dfs(node) for node in graph if color[node] == WHITE)
```

**Why two states isn't enough:** A simple "visited" set tells you whether you've seen a node, but not whether it's on the *current* path. You need to distinguish "on path" (gray) from "fully done" (black). Otherwise you'll false-positive on diamond graphs (A→B, A→C, B→D, C→D — no cycle, but B and C both visit D).

**Iterative variant — for when recursion isn't enough**

Python's default recursion limit is ~1000 frames. A 10⁶-deep dependency chain (a real interview follow-up: *"what if numCourses is 10 million in one long line?"*) blows the recursive version. The fix: simulate the call stack with an explicit one, plus a flag indicating whether you're entering a node for the first time or finalizing it.

```python
def has_cycle(graph, n):
    WHITE, GRAY, BLACK = 0, 1, 2
    color = [WHITE] * n

    for start in range(n):
        if color[start] != WHITE:
            continue
        stack = [(start, False)]   # (node, is_processed)

        while stack:
            node, is_processed = stack.pop()

            if is_processed:
                color[node] = BLACK     # all descendants done
                continue
            if color[node] == GRAY:
                return True             # back edge → cycle
            if color[node] == BLACK:
                continue                # duplicate push, already finalized

            color[node] = GRAY
            stack.append((node, True))  # post-order marker BEFORE children

            for nei in graph[node]:
                if color[nei] != BLACK:
                    stack.append((nei, False))
    return False
```

**Why this is the cleanest formulation:**
- All state-machine logic lives in one place — right after `stack.pop()`. The four cases (`is_processed`, `GRAY`, `BLACK`, `WHITE`) are the entire decision tree.
- Pushing `(node, True)` *before* the children means LIFO ordering pops it after every descendant. That's your post-order hook — the moment you'd mark BLACK in the recursive version.
- Cycle detection happens at pop time, not push time. Safe because the `BLACK` check filters out duplicate pushes: a node pushed twice from different parents will only be GRAY on the second pop if it's actually on the current path.

The "iterator-based" idiom (peek the stack, advance `iter(graph[node])`) is a known alternative — same insight, slightly trickier to derive. The flag-based version above is what you should write under time pressure.

**Note:** for *pure* cycle detection without DFS-specific properties (pre/post-order, edge classification), **Kahn's algorithm (next section) is simpler still** — no colors, no flag, no stack of tuples. Reach for iterative DFS only when you need DFS semantics that Kahn's can't give you (post-order processing, finish-time-ordered topo sort, SCC).

**Practice problem:** [LeetCode 207 — Course Schedule](https://leetcode.com/problems/course-schedule/) (Medium)
- Solve it with recursive DFS + three colors first
- Re-solve iteratively using the pattern above (don't peek — derive it from "I need a post-order hook")
- Then re-solve with **Kahn's algorithm** (BFS with in-degree count) — you need all three in your toolkit
- Time budget: 60 min for all three approaches

**Done when:** you can implement three-color DFS cycle detection from a blank screen — recursive AND iterative.

---

## Interlude: Stack vs queue — why Kahn's (next) doesn't need the marker dance

The iterative DFS above needed an exit marker because of how stacks work. Kahn's algorithm (next section) won't, because of how queues work *and* because BFS doesn't have the same "come back later" problem as DFS. Internalize this contrast before moving on — it generalizes far beyond cycle detection.

**Data structure mechanics:**

| Structure | Push vs pop order | "Process after all children" item goes |
|-----------|-------------------|----------------------------------------|
| Stack (LIFO) | inverted | push **FIRST** → pops LAST |
| Queue (FIFO) | preserved | push **LAST** → pops LAST |

That's the surface-level rule. But the deeper reason Kahn's looks so much simpler is that **post-order is a DFS-specific concept** — Kahn's doesn't add such an item at all.

**Traversal shape determines bookkeeping:**

- **DFS (stack)** — *"Dive into a child, finish it completely, come back."* You need a marker because you have to *return to* the parent later to mark BLACK / emit it / whatever post-order processing requires.
- **Kahn's (queue)** — *"Process any node whose dependencies are already done."* You never return to a node. The pop order IS the topological order, because a node only enters the queue when its in-degree hits 0 — meaning every dependency has already been processed.

**The transferable principle:**

The choice between stack and queue isn't style — it determines whether your algorithm is depth-first or breadth-first, which determines whether you need post-order bookkeeping (DFS) or get the ordering naturally (BFS / Kahn's).

| Need | Use |
|------|-----|
| Post-order processing of a subtree | Stack + exit marker |
| Process in dependency order | Kahn's (BFS queue), no marker |
| Process in level / distance order | BFS queue, no marker |

The marker pattern is a **DFS-specific tax** you pay because depth-first means "go deep before going wide," which means you have to remember to come back. Queue-based algorithms don't go deep, so there's no "come back" to track.

---

## Concept 3: Topological sort

**What you're learning:** given a DAG, produce a linear order where every node comes after its dependencies. The spreadsheet uses this for propagation — when A1 changes, you must re-evaluate B1 before D1 if D1 depends on B1.

**Mental model — Kahn's algorithm (BFS with in-degree):**

```python
from collections import Counter, deque

def topological_sort(graph: dict[str, set[str]]) -> list[str]:
    # Counter("count occurrences as destinations") IS the in-degree.
    # Missing keys return 0, so source nodes (no in-edges) work naturally.
    in_degree = Counter(nei for neighbors in graph.values() for nei in neighbors)

    # Start with all nodes that have no dependencies
    queue = deque(node for node in graph if in_degree[node] == 0)
    result = []

    while queue:
        node = queue.popleft()
        result.append(node)
        for neighbor in graph.get(node, set()):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(result) != len(graph):
        raise ValueError("Cycle detected — no valid topological order")
    return result
```

**Why `Counter` here:** the in-degree of a node is literally "how many times it appears as a destination across all edges." Counter does exactly that, in one expression. The `in_degree[node] == 0` check at queue construction works because Counter returns 0 for missing keys (source nodes never appear as destinations and so aren't keys in the Counter).

This assumes the convention that `graph` keys are the full node set — every node appears as a key, even those with empty out-edge sets. With that convention, `len(graph)` is the correct denominator for the cycle-detection check.

**Alternative — DFS post-order:**
```python
def topological_sort_dfs(graph: dict[str, set[str]]) -> list[str]:
    visited = set()
    result = []
    
    def dfs(node: str) -> None:
        if node in visited:
            return
        visited.add(node)
        for neighbor in graph.get(node, set()):
            dfs(neighbor)
        result.append(node)  # add AFTER visiting all dependencies
    
    for node in graph:
        dfs(node)
    return result[::-1]  # reverse: dependencies should come first
```

**When to use which:**
- **Kahn's** when you want to detect cycles as a side effect (it raises naturally)
- **DFS post-order** when you only need the ordering and already know it's a DAG, or when you want to combine it with cycle detection in one pass

**Practice problem:** [LeetCode 210 — Course Schedule II](https://leetcode.com/problems/course-schedule-ii/) (Medium)
- Same setup as 207, but you return the actual order
- Solve with both Kahn's and DFS
- Time budget: 45 min

**Optional:** [LeetCode 269 — Alien Dictionary](https://leetcode.com/problems/alien-dictionary/) (Hard) — only the setup is hard; topo sort itself is identical to 210. Skip if short on time.

**Done when:** you can write Kahn's algorithm from memory and can explain why DFS post-order works.

---

## Decision matrix: which traversal for which problem?

You now have four cycle-detection variants and two topological sort variants. Here's how to decide under interview pressure. Memorize the *defaults*; the rest you can reason from.

### Cycle detection only (true / false answer)

| Situation | Tool |
|-----------|------|
| **Default** — clean code, no special constraints | **Kahn's BFS** (no recursion, no marker dance) |
| You also need DFS properties downstream (post-order, edge classification) | **Three-color recursive DFS** |
| Graph depth might exceed Python's ~1000 recursion limit | **Iterative three-color DFS** OR Kahn's |
| Throwaway scratch code, never extending | Two-set recursive DFS (works, doesn't generalize) |

### Topological sort (return the order)

| Situation | Tool |
|-----------|------|
| **Default** — any valid topological order | **Kahn's BFS** |
| Need DFS finish-time order (e.g., for Kosaraju's SCC) | DFS post-order, reversed |
| Need **lexicographically smallest** valid order | **Kahn's with a min-heap** (swap `deque` for `heapq`) |
| Need to know **how many parallel rounds** it takes | **Kahn's with level tracking** (LC 1136 pattern) |
| Dependencies change incrementally, need to re-sort cheaply | DAG with cached topo level per node (the spreadsheet pattern) |

### Other graph problems this toolkit solves

| Problem type | Use |
|--------------|-----|
| Build/execution order from dependencies | Kahn's |
| Detect cycle in dependency graph (build systems, package managers) | Three-color DFS or Kahn's |
| Feasibility of scheduling (Course Schedule, task DAG) | Kahn's |
| Critical path / longest path in a DAG | Topo sort + DP over the order |
| "Level" of each node (max distance from a source) | Kahn's with level tracking |
| Propagate updates outward (spreadsheet, reactive frameworks) | Kahn's, OR memoized DFS on dependents subtree |
| Find back edges (loop detection in compiler CFGs) | Three-color DFS + edge classification |
| Strongly Connected Components | Tarjan's or Kosaraju's (DFS-based; out of scope, but know it exists) |

### What about non-DAG graph problems?

The graph patterns in this doc only cover **directed acyclic** territory. For other shapes, reach for different tools:

- **Shortest path (unweighted)** → BFS with a queue
- **Shortest path (weighted, non-negative)** → Dijkstra (BFS with min-heap)
- **Connectivity / components in undirected graphs** → DFS or Union-Find
- **Bipartite check** → BFS with 2-coloring
- **Minimum spanning tree** → Kruskal (Union-Find) or Prim (heap)

If the problem says "find the shortest..." or "components" or "minimum cost," you're outside Kahn's territory — don't force it.

---

## Topological sort variants worth knowing

The base Kahn's you wrote handles ~80% of topo-sort problems. Two variants cover most of the rest.

### Variant 1: Lexicographically smallest topo order

When the problem says "if multiple valid orders exist, return the smallest one," swap the `deque` for a min-heap. Same algorithm, different "which ready node to pop next" tiebreaker.

```python
import heapq
from collections import Counter

def lex_topo_sort(graph: dict, n: int) -> list:
    in_degree = Counter(nei for neighbors in graph.values() for nei in neighbors)
    heap = [i for i in range(n) if in_degree[i] == 0]
    heapq.heapify(heap)
    result = []
    while heap:
        node = heapq.heappop(heap)
        result.append(node)
        for nei in graph[node]:
            in_degree[nei] -= 1
            if in_degree[nei] == 0:
                heapq.heappush(heap, nei)
    return result if len(result) == n else []   # [] signals cycle
```

**Practice:** [LC 1203 — Sort Items by Groups](https://leetcode.com/problems/sort-items-by-groups-respecting-dependencies/) (Hard) is the canonical version. Skip unless you have time.

### Variant 2: Level-tracked Kahn's (parallel scheduling)

When the problem asks "how many semesters minimum?" or "what's the longest dependency chain?", track depth alongside the BFS:

```python
from collections import deque, Counter

def min_semesters(graph: dict, n: int) -> int:
    in_degree = Counter(nei for neighbors in graph.values() for nei in neighbors)
    q = deque((i, 0) for i in range(n) if in_degree[i] == 0)
    ans = 0
    processed = 0
    while q:
        node, level = q.popleft()
        processed += 1
        ans = max(ans, level + 1)
        for nei in graph[node]:
            in_degree[nei] -= 1
            if in_degree[nei] == 0:
                q.append((nei, level + 1))
    return ans if processed == n else -1   # -1 signals cycle
```

**Why this gets the deepest path right** without explicitly tracking a max level per node: a node only hits `in_degree == 0` when ALL parents are processed. Since BFS processes lower-level nodes first (FIFO), the **last** parent to process is always the deepest. The level pushed with the node is automatically the longest path to it — the queue's ordering does the max() for you.

**Note on cycle detection:** you don't need a `result` list or visited set. The `processed` counter is enough — if Kahn's can't drain everyone, the final `processed == n` check signals a cycle. Kahn's enqueues each node exactly once by construction (in-degree only decrements), so no extra bookkeeping is needed.

**Alternative pattern — outer loop counts rounds, inner loop drains the level:**

```python
from collections import deque, Counter

def min_semesters_rounds(graph: dict, n: int) -> int:
    in_degree = Counter(nei for neighbors in graph.values() for nei in neighbors)
    current = deque(i for i in range(n) if in_degree[i] == 0)
    semesters = 0
    processed = 0
    while current:
        next_round = deque()
        semesters += 1
        while current:                          # drain entire level
            node = current.popleft()
            processed += 1
            for nei in graph[node]:
                in_degree[nei] -= 1
                if in_degree[nei] == 0:
                    next_round.append(nei)
        current = next_round
    return semesters if processed == n else -1
```

Use this shape when the problem is fundamentally "process in rounds" — multi-source BFS, simulation problems (rotting oranges), level-by-level reporting. Slightly more nested, but round boundaries are explicit. For "just give me the count" (LC 1136), the piggyback version above wins on concision.

**Practice:** [LC 1136 — Parallel Courses](https://leetcode.com/problems/parallel-courses/) (Medium) is exactly this. Listed as the integration problem in Concept 5 — do it before attempting the spreadsheet.

### How this connects to the spreadsheet problem

The spreadsheet combines **all three patterns** from this section:

- `set_cell` does **cycle detection** before installing a new formula (three-color DFS on the would-be graph, or "try Kahn's; if it can't drain, reject").
- After a valid `set_cell`, **propagation** walks the affected dependents in **topological order** (Kahn's restricted to the affected subtree).
- If you wanted bonus credit, you could expose **level-tracked propagation** — "this cell update kicked off 4 rounds of recomputation" — for diagnostics.

The hardest part isn't any single algorithm. It's **composing** them cleanly so the code reads as three named operations, not a 100-line `set_cell`.

---

## Concept 4: Expression parsing without `eval`

**What you're learning:** parsing a string like `"3+4*2"` into operands and operators, evaluating it correctly. You'll need this for the spreadsheet's formula evaluator.

**Why not `eval()`:** `eval()` is a security hole (executes arbitrary Python). In an interview, reaching for `eval()` on a formula string is a hard fail — interviewers will ask you to do it without.

**Mental model — the stack approach for one-pass calculator:**

```python
def calculate(s: str) -> int:
    stack = []
    num = 0
    op = "+"  # pretend there's a leading + so first num gets pushed
    
    for i, ch in enumerate(s):
        if ch.isdigit():
            num = num * 10 + int(ch)
        if ch in "+-*/" or i == len(s) - 1:
            if op == "+":
                stack.append(num)
            elif op == "-":
                stack.append(-num)
            elif op == "*":
                stack.append(stack.pop() * num)
            elif op == "/":
                stack.append(int(stack.pop() / num))  # truncate toward zero
            op = ch
            num = 0
    
    return sum(stack)
```

The trick: defer multiplication/division (apply when you see the next operator), accumulate addition/subtraction on a stack.

**For the spreadsheet, you may only need much simpler parsing** — just splitting `"=A1+B2"` into `["A1", "+", "B2"]`. If your formulas only support one binary operator (`OPERAND OP OPERAND`), a regex is enough. Reach for the calculator-style stack only when the follow-up adds precedence.

**Practice problem:** [LeetCode 227 — Basic Calculator II](https://leetcode.com/problems/basic-calculator-ii/) (Medium)
- This teaches the full pattern including precedence
- Skip [224 — Basic Calculator I](https://leetcode.com/problems/basic-calculator/) (parentheses) unless you want extra depth
- Time budget: 45-60 min

**Done when:** you can tokenize a string into numbers/operators and evaluate without `eval`, respecting operator precedence.

---

## Concept 5: Putting it together — dependency propagation

**What you're learning:** combining graph + topo sort + class design into a propagation system. This is essentially the spreadsheet without the formula stuff.

**Practice problem:** [LeetCode 1136 — Parallel Courses](https://leetcode.com/problems/parallel-courses/) (Medium)
- Topo sort + tracking "levels" (how many semesters minimum)
- Closest in shape to "propagate updates outward"
- Time budget: 45 min

**Done when:** you can write a `class` that holds an adjacency dict, supports add/remove of edges, and exposes a method that returns a topological order.

---

## Suggested schedule

| Day | What |
|-----|------|
| Day 1 | Read this whole doc. Solve LC 133 (Clone Graph). |
| Day 2 | LC 207 (Course Schedule) — both DFS-3-color and Kahn's. |
| Day 3 | LC 210 (Course Schedule II). Then re-solve LC 207 from scratch as warmup. |
| Day 4 | LC 227 (Basic Calculator II). |
| Day 5 | LC 1136 (Parallel Courses). |
| Day 6 | **Attempt the spreadsheet problem** — open `problem.md`, work it in `solution.py`, run `test_solution.py`. |
| Day 7 | Re-do the spreadsheet from scratch the next day. Compare attempt 2 to attempt 1 — what felt faster, what's still hard? |

This is 5-6 hours of LC work spread across 4-5 days, plus the 60-minute spreadsheet attempt. Don't compress it — the muscle has to actually form.

## How to use Claude Code during this

When you hit a concept that confuses you in any of the LC problems, ask Claude Code in **Teacher mode**:
- "explain three-color DFS cycle detection"
- "walk me through Kahn's algorithm"
- "teach me operator precedence parsing with stacks"

It'll teach the concept properly without solving the LC problem for you. That's the right division of labor: LeetCode for the reps, Claude Code for the *why*.

## When you're ready

When you can solve LC 1136 in under 45 minutes from a blank screen without looking things up, **then** open `problem.md` in this folder and start a 60-minute timer. Not before.
