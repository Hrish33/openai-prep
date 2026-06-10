# Interviewer notes — Unix `cd` with symlinks

**Read AFTER your attempt.** Reading first defeats the point.

This reference is **scrappy, not polished** — what a passing 45-minute attempt looks like. No dataclasses, no helper class for paths, no os.path. The goal is something you could rebuild from memory under pressure.

## Reference solution

```python
class Shell:
    def __init__(self):
        self._cwd = "/"
        self._symlinks = {}                              # link path -> target path

    def register_symlink(self, link_path, target):
        self._symlinks[link_path] = target

    def pwd(self):
        return self._cwd

    def cd(self, command):
        # 1. choose starting stack
        if command.startswith("/"):
            stack = []
        else:
            stack = self._split(self._cwd)

        # 2. walk command, resolving symlinks per-component
        for comp in command.split("/"):
            if comp == "" or comp == ".":
                continue
            if comp == "..":
                if stack:
                    stack.pop()
                continue
            stack.append(comp)
            stack = self._resolve(stack, visiting=set())

        # 3. commit (cwd is untouched until here — atomicity on cycle)
        new_cwd = "/" + "/".join(stack) if stack else "/"
        self._cwd = new_cwd
        return new_cwd

    # ---- helpers ----

    def _split(self, path):
        """'/a/b/c' -> ['a', 'b', 'c']. Used for seeding from cwd."""
        return [p for p in path.split("/") if p]

    def _resolve(self, stack, visiting):
        """If the path built from `stack` is a symlink, expand it (recursively)
        and return the new stack. Otherwise return stack unchanged.
        `visiting` is a set of paths currently mid-expansion — for cycle detection."""
        path = "/" + "/".join(stack)
        if path not in self._symlinks:
            return stack
        if path in visiting:
            raise ValueError(f"symlink cycle at {path}")
        visiting.add(path)

        target = self._symlinks[path]
        new_stack = []
        for comp in target.split("/"):
            if comp == "" or comp == ".":
                continue
            if comp == "..":
                if new_stack:
                    new_stack.pop()
                continue
            new_stack.append(comp)
            new_stack = self._resolve(new_stack, visiting)
        return new_stack
```

That's the whole problem. ~40 lines.

## Walking through `cd`

Three steps. Memorize the steps:

1. **Seed the stack.** Absolute → empty; relative → current cwd split into components.
2. **Walk the command.** For each component: skip empty/`.`, pop on `..`, push regular. *After pushing*, run `_resolve` to expand any symlink at the resulting full path.
3. **Commit.** Build the new cwd string and assign it. Until this line, `self._cwd` is untouched — that's how a cycle mid-walk leaves state unchanged.

The "atomicity" property is free: because we build a fresh stack and only assign to `self._cwd` at the end, a `ValueError` from inside `_resolve` propagates out before any mutation.

## Why one walker, not two

Both the user's `command` and a symlink's `target` are path strings needing the same logic: split on `/`, skip empty/`.`, pop on `..`, push regular, resolve symlinks at each push. Inlining the walk in two places is a smell — it'll diverge under follow-up edits. The reference has one inline walk in `cd` and a near-duplicate inside `_resolve` — that's the seam where a stronger refactor would extract a single `_walk(components, stack, visiting)` helper.

You can absolutely DRY it further. For the 45-minute attempt, the duplication is acceptable as long as you can *name* the seam if the interviewer asks.

## Why `visiting` is a set per top-level `cd`

A symlink that's been expanded *in this current chain* is what creates a cycle. The same symlink expanded again in a totally separate part of the same command's walk is fine.

But the simplest correct model — and the one in the reference — is **one `visiting` set per top-level `cd` call**: created at the top of `cd`'s loop body each iteration is fine too, but a single set across the whole call also works (and that's what `visiting=set()` inside the loop produces here — fresh per component push).

Wait, look at the code again: `stack = self._resolve(stack, visiting=set())` — the set is created fresh on *every iteration* of the component loop. That means symlink expansion for component A and component B have separate cycle universes. This is slightly more permissive than "one set per `cd` call" but doesn't allow real cycles through (a real cycle reveals itself within one component's `_resolve` call tree).

The two scopes both work. If asked which is "right," the answer is: **scoped to the recursive expansion that's currently unwinding** — i.e., the set that lives across the recursion of `_resolve` for a single component push. That's what the reference does.

## Why no `os.path` / `pathlib`

`os.path.realpath()` and `pathlib.Path.resolve()` would do this whole problem in one line. Reaching for them in this interview is the same as `eval()` in the spreadsheet — the question is *can you implement it*, not *can you find the stdlib answer*. If the interviewer asks "can you do it without `os.path`?", they're telling you they noticed and they want the implementation. Skip ahead.

## Honest weaknesses to acknowledge

- **No relative-target symlinks.** Real Unix supports `ln -s ../sibling link`. The reference assumes targets are absolute. The fix isn't deep — when expanding, the starting stack should be `dirname(link)` instead of `[]`. Mention this; don't volunteer to implement under time pressure.
- **No depth limit.** A non-cyclic chain of 10⁶ symlinks would blow Python's recursion limit. Linux caps at ~40 hops for exactly this reason. Mention `max_depth` as a guard.
- **`register_symlink` doesn't validate.** Self-loops, cycles between symlinks, dangling targets all register fine — the cycle only triggers on `cd`. You could validate at register time (BFS from the new link checking reachability); for base, it's fine to defer.
- **Recursive `_resolve` blows on deep chains.** Iterative version is ugly but possible if you push it.
- **Empty command is a no-op.** Some interviewers would prefer it to raise. Defensible either way; just be explicit about the choice.
- **No thread safety.** Concurrent `cd` and `register_symlink` will race. One `threading.Lock` around the public methods is the fix.

## Grading yourself

| Axis | Passing |
|------|---------|
| Edge cases up front | Named: empty, `/`, `/../..`, self-loop, two/three-link cycle, target with `..`, chained symlinks |
| Data structure choice | List stack + dict for symlinks; can explain why stack ≠ string |
| Per-component resolution | Symlink expansion fires on every regular component push, not just at the end |
| Cycle detection placement | Inside `_resolve`, scoped to the recursion, NOT instance state |
| Atomic semantics on cycle | `self._cwd` only mutated at end of `cd` — rejected calls leave state untouched |
| Code structure | One walker logic, used for both command and target; `cd` reads as 3 named steps |
| Follow-up readiness | Can sketch relative targets, depth limit, threading lock without freezing |

## Follow-up sketches

### 1. Relative symlink targets

Currently targets must be absolute. To support `register_symlink("/a/link", "../sibling")`:

```python
def _resolve(self, stack, visiting):
    path = "/" + "/".join(stack)
    if path not in self._symlinks:
        return stack
    if path in visiting:
        raise ValueError(...)
    visiting.add(path)

    target = self._symlinks[path]
    if target.startswith("/"):
        new_stack = []
    else:
        new_stack = stack[:-1]    # symlink resolves relative to its parent dir
    # ... (rest unchanged)
```

The single new line: `new_stack = stack[:-1]` — start from the link's parent.

### 2. Depth limit

Pass a counter through `_resolve`:

```python
def _resolve(self, stack, visiting, depth=0):
    if depth > 40:
        raise ValueError("symlink depth exceeded")
    # ... rest unchanged, pass depth+1 to recursive call
```

Why have this *and* cycle detection? Cycles are one failure mode; pathologically long non-cyclic chains are another. Defense in depth.

### 3. Thread safety

```python
import threading

class Shell:
    def __init__(self):
        self._cwd = "/"
        self._symlinks = {}
        self._lock = threading.Lock()

    def cd(self, command):
        with self._lock:
            # ... existing body ...

    def register_symlink(self, link, target):
        with self._lock:
            self._symlinks[link] = target

    def pwd(self):
        with self._lock:
            return self._cwd
```

Single lock around all public methods. Coarse but correct. Per-method reader/writer locks are a follow-up to the follow-up — be prepared if pushed but don't volunteer.

### 4. Persistence

Serialize `self._symlinks` to JSON on every `register_symlink`. Load on `__init__`. Cwd typically isn't persisted (a new shell starts at `/`). Trade-offs: durability vs throughput (every register = disk write); batch via a flush interval if write-heavy.

## Common mistakes interviewers see

1. **Resolving symlinks at the end.** Building the full path first, then looking up the full path in the symlinks dict. Misses every "link in the middle" case (`/usr/local/bin` when `/usr/local` is the link).
2. **Treating the symlink target as already-normalized.** Forgetting that the target itself can contain `..` or `//` and must run through the walker.
3. **`visited` set on `self`.** Cleared between calls → bug. Not cleared → next call hits false-positive cycle.
4. **Mutating `self._cwd` mid-walk.** Cycle raises → cwd is in a torn state. The reference avoids this by only assigning at the end.
5. **Using `os.path.realpath`.** Hard fail — the problem *is* implementing this.
6. **String concatenation for paths.** `current + "/" + command` then trying to split — gives you `//` to deal with everywhere. The stack-of-components abstraction makes the whole problem clean.
7. **Forgetting `..` at root is a no-op, not an error.** `cd /..` should return `/`, not raise.
8. **Trying to detect cycles at `register_symlink` time.** Tempting (validate before insert), but it's harder than detecting at use time — you'd have to BFS the whole symlink graph from the new edge. Defer it.

## Want a Round 2?

Try the **iterative version of `_resolve`** as a second pass (`solution_iterative.py`). Same tests should pass. The recursion is small here so the iterative version isn't a real win — but writing it is a good exercise in seeing how the visited set has to be threaded explicitly when you remove the call stack.

Or: implement **relative symlink targets** and add tests for them. That's a much more interview-shaped extension than the iterative rewrite.
