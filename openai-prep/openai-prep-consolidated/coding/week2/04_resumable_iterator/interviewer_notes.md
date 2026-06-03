# Interviewer notes — Resumable Iterator

**Read AFTER your attempt.** Reading first defeats the point.

This reference is the **scrappy, what-actually-works** version — not a code-golf showpiece. The goal is something you could rebuild from a blank screen in 20 minutes under interview pressure, with the state shape you'd actually defend out loud.

## Reference solution (sync base)

```python
from typing import Iterable, TypeVar

T = TypeVar("T")


class CompositeIterator:
    def __init__(self, sources: list[Iterable[T]]) -> None:
        self._sources = sources                 # keep originals for re-iter on set_state
        self._source_idx = 0
        self._offset = 0
        self._inner = None                      # the live iterator over current source; lazy

    def __iter__(self) -> "CompositeIterator":
        return self

    def __next__(self) -> T:
        while self._source_idx < len(self._sources):
            if self._inner is None:
                self._inner = iter(self._sources[self._source_idx])
                # fast-forward by self._offset items (set_state may have set this)
                for _ in range(self._offset):
                    next(self._inner)
            try:
                item = next(self._inner)
                self._offset += 1
                return item
            except StopIteration:
                self._source_idx += 1           # current source exhausted
                self._offset = 0
                self._inner = None              # next loop iteration opens the next source
        raise StopIteration

    def get_state(self) -> dict:
        return {"source_idx": self._source_idx, "offset": self._offset}

    def set_state(self, state: dict) -> None:
        self._source_idx = state["source_idx"]
        self._offset = state["offset"]
        self._inner = None                      # force lazy reopen on next __next__
```

That's ~25 lines. The state is two integers. That's the whole solution.

## Walking through the design

**The state shape: `{"source_idx": int, "offset": int}`.** Two integers, JSON-serializable. This is the single most-defended decision in the round. State your reasoning out loud in the interview:

> "I need just enough to seek to the exact next-element position. That's *which* source I'm in (`source_idx`) and *how many items into it* (`offset`). Anything more — like a copy of the remaining items — costs O(N) and breaks if the source mutates. Anything less can't disambiguate."

**Lazy reopen via `_inner = None`.** `__next__` opens the source on first use. `set_state` clears `_inner` so the next call re-opens against the restored cursor. The alternative — eagerly re-opening in `set_state` — works too but does I/O on a method that "should just be a setter." Lazy is the slightly-cleaner default. Either is defensible.

**The `while` loop crosses source boundaries.** A single `__next__` call may skip past empty sources or transition between sources. The loop body has two outcomes: yield an item (return) or exhaust the current source (advance and continue). Without the loop, you'd return `None` on an empty source — that's a `__next__` contract violation.

**`get_state` returns a *fresh* dict, not the internal one.** Otherwise two calls to `get_state` would share the same dict and mutating one would affect the other. Cheap insurance against subtle bugs the interviewer can trip you on.

## Why two graph integers and not three (or one)?

**Why not just `items_seen`?** With a single counter, you've lost which source you're in. Restoring "I've seen 7 items" requires you to count through all sources until you've consumed 7 — *and* you've assumed the source lengths are stable. If `sources[0]` was mutated between save and restore, the restore is silently wrong. Two cursors decouple "where" from "how far in."

**Why not also `total_consumed`?** Redundant. You can derive it (`sum(len(s) for s in sources[:source_idx]) + offset`). Adding it to the state dict means *two* fields that have to stay consistent — extra invariant, no extra information.

**Why not store the live iterator object?** Not portable. The whole point of `get_state` is "I can write this to a file." A live iterator is not serializable (or, if it is via pickle, only in the same Python process).

## Why sources must be re-iterable

`set_state(state)` may need to restart any source from item 0 (and skip forward to its offset). For that to work, the source has to be `iter()`-able multiple times. Lists, tuples, file paths — yes. Generators — no, once consumed.

This constraint belongs in the docstring and in the conversation:

> "I'm assuming sources are re-iterable. If they're one-shot generators, I'd need to materialize them first or keep a cache — both have O(N) memory cost. For the common case of lists or file paths this constraint is free."

Articulating the constraint without prompting is the senior move.

## Honest weaknesses to acknowledge

- **`set_state` advance is O(offset).** Re-opening a list and `next()`ing 1000 times is fine; doing it on a file with 10M lines hurts. For files, store a byte offset *in addition to* line offset and seek directly — but byte offsets are wrong for multi-byte UTF-8 unless you've designed for it.
- **No validation that `state` belongs to *these* sources.** Restoring `{"source_idx": 5}` against a 3-source iterator will silently misbehave on next access. Add `source_idx >= len(self._sources)` → treat as exhausted. Better: also include a hash of `[len(s) for s in sources]` and reject mismatches.
- **Not thread-safe.** Two threads calling `__next__` will race on `self._offset`. Lock around the body (the slow part is the user's source iteration, not your bookkeeping, so this is cheap).
- **Source exhaustion mid-restore is not gracefully reported.** If `set_state` says "advance 100 items" and source has 50, the `for _ in range(...)` raises `StopIteration` from inside `set_state`. Catch it, advance source_idx, retry — or simply do the advance lazily in `__next__` (cleaner — what the reference above does).

## Grading yourself

| Axis | Passing |
|------|---------|
| Edge cases up front | Named: empty sources interleaved, exhausted state, save-at-start, save-across-boundary |
| State design articulation | Said "two integers, JSON-serializable" *before* coding; can defend why not one, why not three |
| Iterable vs. iterator awareness | Flagged that sources must be re-iterable; named one-shot generators as the failure mode |
| `__next__` contract | Raises `StopIteration` correctly; doesn't return `None` on empty source; handles cross-source transition |
| Code structure | `__next__` is 8-15 lines; state methods are ~3 lines each; no clever bookkeeping object |
| Follow-up readiness | "Make it async / picklable / file-backed" doesn't make you freeze |

## Follow-up sketches

### 1. Async variant (the reported shape)

```python
class AsyncCompositeIterator:
    def __init__(self, sources):
        self._sources = sources
        self._source_idx = 0
        self._offset = 0
        self._inner = None

    def __aiter__(self):
        return self

    async def __anext__(self):
        while self._source_idx < len(self._sources):
            if self._inner is None:
                self._inner = aiter(self._sources[self._source_idx])    # async-iter the source
                for _ in range(self._offset):
                    await anext(self._inner)
            try:
                item = await anext(self._inner)
                self._offset += 1
                return item
            except StopAsyncIteration:
                self._source_idx += 1
                self._offset = 0
                self._inner = None
        raise StopAsyncIteration

    def get_state(self):  return {"source_idx": self._source_idx, "offset": self._offset}
    def set_state(self, s): self._source_idx, self._offset, self._inner = s["source_idx"], s["offset"], None
```

The state design is identical. The only real change is `__aiter__` / `__anext__` and `StopAsyncIteration`. Two things to call out:

- **Snapshot policy during `await`.** If `get_state` is called by another task while `__anext__` is suspended on `await anext(self._inner)`, the `_offset` it reads is "before the in-flight item." Document this — and consider: do you want a lock, or do you simply contract that `get_state` is called between `__anext__` calls?
- **Source iteration must itself be async.** If your sources are sync lists, wrap them: `async def aiter_list(lst): for x in lst: yield x`. Or use `aiter(...)` from `asyncio` helpers if your source is already an async iterable (e.g., `aiofiles`).

### 2. Pickle integration

```python
def __getstate__(self):
    # exclude the live iterator — it's not picklable and we can rebuild it
    return {"sources": self._sources, "source_idx": self._source_idx, "offset": self._offset}

def __setstate__(self, state):
    self._sources = state["sources"]
    self._source_idx = state["source_idx"]
    self._offset = state["offset"]
    self._inner = None
```

Two-method addition. But: pickle includes the *sources* in the blob — so the trade-off is "pickle is self-contained but big; `get_state` is small but requires the user to also hold onto the sources." Both have use cases. State the trade.

### 3. File-backed sources

```python
class CompositeIterator:
    def __init__(self, paths: list[str]) -> None:
        self._paths = paths
        self._source_idx = 0
        self._offset = 0
        self._file = None                  # open file handle for current source

    def __next__(self):
        while self._source_idx < len(self._paths):
            if self._file is None:
                self._file = open(self._paths[self._source_idx])
                for _ in range(self._offset):
                    next(self._file)
            line = self._file.readline()
            if line == "":                 # EOF
                self._file.close()
                self._file = None
                self._source_idx += 1
                self._offset = 0
                continue
            self._offset += 1
            return line.rstrip("\n")
        raise StopIteration

    def close(self):
        if self._file is not None:
            self._file.close()
            self._file = None
```

Now you also have to clean up the file handle. Add `__enter__` / `__exit__` to make `with CompositeIterator(paths) as it:` work. And mention the byte-offset alternative for fast seek — with the UTF-8 caveat.

### 4. Source mutation policy

```python
def __init__(self, sources):
    self._sources = sources
    self._initial_lens = [len(s) for s in sources if hasattr(s, "__len__")]
    ...

def __next__(self):
    # before each yield, check the current source hasn't been resized
    if hasattr(self._sources[self._source_idx], "__len__"):
        if len(self._sources[self._source_idx]) != self._initial_lens[self._source_idx]:
            raise RuntimeError("source modified during iteration")
    ...
```

Mimics `dict`'s policy. Cheap, predictable, surfaces bugs early. Alternative: snapshot the source at first touch — but that defeats the streaming property.

## Common mistakes interviewers see

1. **Storing the live iterator in state.** "Just pickle the iterator." Doesn't work cross-process; tightly couples the state shape to CPython internals.
2. **Storing remaining items.** `{"remaining": [...]}` — defeats the whole point of streaming. O(N) memory, breaks on source mutation.
3. **Returning `None` from `__next__` on an empty source instead of skipping.** Hard to spot in unit tests because the test sources never have an empty entry first. Edge case discipline catches this.
4. **`get_state` returns `self._cursor` directly** — a *reference*. Caller mutates their copy; iterator's internal state silently corrupts. Always return a fresh dict.
5. **`set_state` doesn't reset the inner iterator.** Cursor moves, but `_inner` still points at the old position. Next `__next__` reads from where the iterator already was. Symptom: "save after item 3, restore, get item 7 instead of 3."
6. **Forgetting that `iter([])` produces a valid (empty) iterator.** Some implementations special-case empties and break in surprising ways. The cleaner implementation lets `next(iter([]))` raise `StopIteration` naturally and handles it in the same path as cross-source transition.
7. **Mixing up "source is an iterable" with "source is an iterator."** Accepting `iter([1,2,3])` as a source works *once*, then `set_state` to a position before the current point breaks. Either accept only re-iterables and check, or materialize internally — but don't silently accept and silently corrupt.

## Want a Round 2?

After the sync base feels solid:

1. Re-implement as `solution_async.py` with `async __anext__`. Same tests should pass with `async for` and `await`.
2. Add `__getstate__` / `__setstate__` to a third variant; write a test that `pickle.loads(pickle.dumps(it))` resumes correctly.
3. Convert sources to file paths; verify the file-handle lifecycle (open lazily, close on exhaust, close on `__exit__`).

Three variants from one design is the test of whether your **state shape generalizes**. If you have to redesign state each time, the original wasn't well-factored.
