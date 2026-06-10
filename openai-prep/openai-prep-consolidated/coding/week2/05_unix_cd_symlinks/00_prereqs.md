# Prereqs — Unix `cd` with symlink resolution

**Don't attempt the problem until you've worked through this.** Estimated time: 1.5–2.5 hours, spread over 2–3 sessions.

This problem looks easy ("just split on `/`") and then gets you in two places:
1. **Per-component symlink resolution.** Not "resolve at the end" — resolve every time a new component lands.
2. **Cycle detection across recursive symlink expansion.** Reuses the visited-set muscle from problem 1, but the graph is implicit.

If you've done LC 71 cleanly and remember the visited-set pattern, you're 70% of the way there. The remaining 30% is the per-component re-entry.

---

## Concept 1: Path normalization with a stack

**What you're learning:** the canonical "split on `/`, push regular components, pop on `..`, ignore `.` and empty" stack pattern. This is the substrate the symlink logic plugs into.

**Mental model:**
```python
def simplify(path: str) -> str:
    stack: list[str] = []
    for comp in path.split("/"):
        if comp == "" or comp == ".":
            continue
        if comp == "..":
            if stack:
                stack.pop()
            continue
        stack.append(comp)
    return "/" + "/".join(stack)
```

Five rules. Memorize them, not the syntax:
1. Split on `/`.
2. Empty component (from leading slash, trailing slash, or `//`) → skip.
3. `.` → skip.
4. `..` → pop one (but not past root — `if stack` guard).
5. Anything else → push.

The output is always absolute (`"/" + "/".join(...)`). Edge case: empty stack at the end → `"/"`.

**Practice problem:** [LeetCode 71 — Simplify Path](https://leetcode.com/problems/simplify-path/) (Medium)
- Time budget: 15–20 min, this is a warm-up
- Don't move on until your solution handles `///`, trailing `/`, and `/../../` (all should yield `/`)

**Done when:** you can write `simplify("/a/./b/../../c/")` → `"/c"` from a blank screen in under 5 minutes.

---

## Concept 2: How Unix actually resolves symlinks — the per-component model

**What you're learning:** the *moment* a symlink gets expanded. Most candidates get this wrong by resolving symlinks "at the end," which silently mishandles every interesting case.

**The rule:** path resolution walks left-to-right. Every time you finish constructing a new component's absolute path, you check if that exact path is a symlink. If yes, replace it with the target *and keep walking the rest of the input*.

```
symlinks = {"/usr/local": "/usr"}
cd("/", "/usr/local/bin")

walk components: "usr", "local", "bin"

after "usr":   stack = ["usr"]            full path = "/usr"        not a link
after "local": stack = ["usr", "local"]   full path = "/usr/local"  is a link → "/usr"
                                          stack ← ["usr"]
after "bin":   stack = ["usr", "bin"]     full path = "/usr/bin"    not a link

final: /usr/bin
```

Why per-component matters: if you waited until the end and looked up `/usr/local/bin`, you'd miss the link — `/usr/local/bin` itself isn't in the symlinks table, only `/usr/local` is. The link applies *to the prefix*, and the suffix walks on from wherever the prefix lands.

**The subtle one — symlink target with `..`:**
```
symlinks = {"/a/b": "/x/y/.."}
cd("/", "/a/b/c")

after "a":  stack = ["a"]                full = "/a"        not a link
after "b":  stack = ["a", "b"]           full = "/a/b"      is a link → "/x/y/.."
                                         resolve target: stack ← ["x"]
after "c":  stack = ["x", "c"]           full = "/x/c"      not a link

final: /x/c
```

The symlink target is itself a path that needs the same `.` / `..` / `//` normalization. **Don't shortcut this** — recursively run the target through the same walker.

**Another subtle case — chained symlinks:**
```
symlinks = {"/a": "/b", "/b": "/c"}
cd("/", "/a/file")

after "a":  full = "/a"   → "/b"   → "/c"
            stack ← ["c"]
after "file": stack = ["c", "file"]

final: /c/file
```

Resolving `/a` lands on `/b`, but `/b` is *also* a symlink — keep resolving until you hit something that isn't. This is where cycle detection enters (Concept 3).

**No LeetCode for this one** — it's conceptual. The right exercise: trace by hand the following four cases on paper before writing code.

| symlinks | cd input | expected |
|---|---|---|
| `{}` | `cd("/", "/a/b/../c")` | `/a/c` |
| `{"/a": "/x"}` | `cd("/", "/a/b")` | `/x/b` |
| `{"/a": "/x/..", "/x": "/y"}` | `cd("/", "/a/b")` | `/b` |
| `{"/a": "/b", "/b": "/a"}` | `cd("/", "/a")` | cycle error |

If you can't do these four by hand without code, the implementation will go sideways.

**Done when:** you can verbally explain "I resolve a symlink at the moment I finish pushing a component, and the target gets fed through the same walker recursively."

---

## Concept 3: Cycle detection during symlink expansion

**What you're learning:** the visited-set pattern, applied to an implicit graph where nodes are paths and edges are symlink mappings.

**Mental model — the graph is implicit:**
```
{"/a": "/b", "/b": "/c", "/c": "/a"}
```
…is exactly:
```
/a ──→ /b ──→ /c
 ↑              │
 └──────────────┘
```

When we land on `/a`, we follow to `/b`, follow to `/c`, follow to `/a` again → cycle. Standard DFS cycle detection.

**The pattern:**
```python
def resolve(path: str, visiting: set[str]) -> str:
    if path not in self._symlinks:
        return path
    if path in visiting:
        raise ValueError(f"symlink cycle at {path}")
    visiting.add(path)
    return resolve(self._symlinks[path], visiting)
```

**Two things to get right:**

1. **The visited set is scoped to one `cd` call**, not to the lifetime of the Shell. A symlink that's safe in one cd call (because nothing else triggered it) is still safe in the next. Don't make it `self._visited` and forget to clear.

2. **Each component starts fresh.** Within one `cd("/", "/a/b")` call, resolving `/a` and resolving `/a/b` have separate cycle universes. If `/a` → `/x` and `/a/b` resolves through `/x/b` → `/a/b`, that's a *different* chain. A single `visiting` set spanning the whole `cd` is fine because real cycles still trip it; per-component sets also work. The simplest model is one set per top-level `cd`.

**Where the muscle comes from:** problem 1 (spreadsheet) used a `seen` set in `_would_cycle` for the same reason — preventing infinite recursion on a graph traversal where edges might loop. Same idea, simpler graph.

**Practice problem (optional refresher):** [LeetCode 207 — Course Schedule](https://leetcode.com/problems/course-schedule/) (Medium)
- Only if it's been a few weeks since problem 1. If the muscle is fresh, skip.
- Time budget: 20 min if you do it.

**Done when:** you can explain "the visited set has to be scoped to *this resolution attempt*, not to the Shell."

---

## Concept 4: Putting the pieces together — the per-component loop

This is the integration concept. Read it carefully — it's the shape of `cd`.

```python
def cd(self, command: str) -> str:
    # 1. Choose starting stack: absolute → fresh, relative → copy of cwd
    if command.startswith("/"):
        stack: list[str] = []
    else:
        stack = self._split(self._cwd)

    # 2. Walk the command's components
    for comp in command.split("/"):
        if comp in ("", "."):
            continue
        if comp == "..":
            if stack:
                stack.pop()
            continue
        # regular component: push, then resolve symlinks at this exact path
        stack.append(comp)
        stack = self._resolve(stack, visiting=set())

    # 3. Commit
    new_cwd = "/" + "/".join(stack) if stack else "/"
    self._cwd = new_cwd
    return new_cwd
```

The `_resolve` helper does symlink expansion:
- Build the full path from the stack
- If not in `symlinks`, return the stack unchanged
- If in `symlinks`, expand: feed the target through the same component walker (recursively), with the cycle-detection set

```python
def _resolve(self, stack: list[str], visiting: set[str]) -> list[str]:
    path = "/" + "/".join(stack)
    if path not in self._symlinks:
        return stack
    if path in visiting:
        raise ValueError(f"symlink cycle at {path}")
    visiting.add(path)
    target = self._symlinks[path]

    new_stack: list[str] = []
    for comp in target.split("/"):
        if comp in ("", "."):
            continue
        if comp == "..":
            if new_stack:
                new_stack.pop()
            continue
        new_stack.append(comp)
        new_stack = self._resolve(new_stack, visiting)
    return new_stack
```

That's the whole problem. About 30 lines. The two non-obvious choices:
- **`_resolve` is recursive, not iterative.** Iterative is possible but the bookkeeping is uglier. Recursion depth is bounded by symlink chain length, which is small in practice.
- **`visiting` is mutated in place across recursion.** A new `_resolve` call inherits its caller's set — that's how a `/a → /b → /c → /a` chain gets caught even though no single call sees the full loop.

---

## Suggested schedule

| Day | What |
|---|---|
| Day 1 | Read this doc. Solve LC 71 (Simplify Path). |
| Day 2 | Trace the 4 hand-cases from Concept 2 on paper. No code. |
| Day 3 | (Optional) LC 207 refresher if cycle muscle is rusty. |
| Day 4 | **Attempt the problem.** 45-minute timer. |

If you blow past 45 minutes, stop, read `interviewer_notes.md`, and re-attempt from scratch tomorrow.

---

## What an OpenAI interviewer specifically values here

1. **You enumerated edge cases up front** — empty command, `/../..`, self-loop symlink, two-link cycle, symlink target with `..`, chained symlinks. Naming them before coding is the signal.
2. **You wrote one walker, not two.** Both the input command and the symlink target are paths; both go through the same component logic. Candidates who write two parallel split/walk loops have a worse design.
3. **Cycle check sits in the right place.** Not in `cd`. Not on every component. In `_resolve`, exactly when a symlink is about to be expanded.
4. **You don't use `os.path.realpath` or `pathlib.Path.resolve`.** The whole point is implementing it. Reaching for the stdlib answer is the same hard-fail as `eval()` in the spreadsheet problem.

---

## When you're ready

When you can:
- Solve LC 71 in 10 minutes
- Hand-trace the 4 cases in Concept 2 without mistakes
- Explain per-component resolution and where the visited set lives

…open `problem.md` and start a 45-minute timer.

Related problems in this repo:
- Problem 1 (spreadsheet) — same `visited` set pattern in `_would_cycle`. If that's fresh, this is the cheaper sibling.
