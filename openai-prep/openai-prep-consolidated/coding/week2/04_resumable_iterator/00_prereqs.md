# Prereqs — Resumable Iterator

**Estimated time: 2-3 hours.** Lighter than the crawler. The whole problem is *Python iterator protocol* + *state design*. There is no clever algorithm here — the entire signal is whether you understand `__iter__` / `__next__` / `StopIteration` deeply enough to design state that survives serialization.

**This is a Python-internals problem.** No LeetCode primer for the core idea (LC doesn't test custom iterators). Most of your prep happens in this doc plus the concept guide; the rest is two small LC warm-ups.

---

## Concept 1: The iterator protocol — what `for x in obj` actually does

**What you're learning:** the three-method contract (`__iter__`, `__next__`, `StopIteration`) and why the language wires them together this way. Every clever iterator you'll write — flatteners, paginators, this problem's resumer — is built on top of this.

**The 30-second story:**

`for x in obj:` is sugar for:

```python
it = iter(obj)          # calls obj.__iter__()
while True:
    try:
        x = next(it)    # calls it.__next__()
    except StopIteration:
        break
    # ... body ...
```

So an object is *iterable* if it has `__iter__`, and an *iterator* if it has `__next__`. The two are not the same — a `list` is iterable but not an iterator (you can `iter(my_list)` repeatedly and get fresh iterators); a generator is both (its `__iter__` returns itself).

**The minimal custom iterator:**

```python
class Counter:
    def __init__(self, n: int) -> None:
        self.n = n
        self.i = 0

    def __iter__(self):
        return self          # I AM the iterator

    def __next__(self):
        if self.i >= self.n:
            raise StopIteration
        x = self.i
        self.i += 1
        return x
```

Three rules to internalize:

1. **`__iter__` returns "something with `__next__`".** Often `self`. For a wrapper that wants multiple parallel passes, `__iter__` returns a *new* iterator object instead.
2. **`__next__` either returns the next item OR raises `StopIteration`.** `return None` is wrong — `None` is a valid value. The protocol is "raise to signal exhaustion."
3. **`StopIteration` is *the* terminator.** Catching it inside `__next__` and re-raising elsewhere is a bug class: you'll see "generator hangs" or "iteration silently stops mid-stream." Let it propagate.

**Mental model — three categories of object:**

| Category | Has `__iter__`? | Has `__next__`? | Example |
|----------|-----------------|-----------------|---------|
| Iterable (not iterator) | Yes — returns a fresh iterator | No | `list`, `dict`, `range` |
| Iterator (also iterable) | Yes — returns `self` | Yes | generators, `iter(some_list)` |
| Neither | No | No | `int`, `dict_keys` view's view, etc. |

The reason the same object is *often* both: convenience. Generators (`def f(): yield ...`) satisfy the iterator protocol with `__iter__` returning `self`, so `for x in gen()` and `for x in iter(gen())` behave identically.

**Practice:** write `Counter` above from scratch. Then write `Range(start, stop, step)` that exactly matches Python's built-in. Then write `ChunkedReader(text, chunk_size)` that yields fixed-size strings.

**Done when:** you can write a custom iterator from a blank screen — including the `StopIteration`-raising `__next__` — and explain why `return None` instead would be a bug.

---

## Concept 2: Iterable vs. iterator — the multi-pass distinction

**What you're learning:** the distinction between an *iterable* (something you can iterate over) and an *iterator* (an object actively walking through it). They look similar — both work in `for` loops, both have `__iter__` — but they behave differently in one critical way: whether you can iterate them more than once.

**The two categories:**

A *re-iterable* source — `list`, `tuple`, `dict`, `range`, `str` — can be iterated any number of times. Each `iter(obj)` call returns a *fresh* iterator starting at position 0:

```python
lst = [1, 2, 3]
list(lst)     # [1, 2, 3]
list(lst)     # [1, 2, 3]   <-- works again, fresh start each time
```

A *one-shot* source — generator, `iter(some_list)`, `map(...)`, `zip(...)`, `enumerate(...)` — can be iterated *only once*. Once consumed, it's done:

```python
gen = (x for x in [1, 2, 3])    # generator expression — an iterator
list(gen)     # [1, 2, 3]
list(gen)     # []              <-- exhausted; no way to rewind
```

**Why the asymmetry exists:** an iterable doesn't *hold* a position — it knows how to *produce* a fresh iterator on demand. An iterator IS a position; once it's walked past element N, there's no rewind button. Generators are iterators — they have a suspended frame at "wherever you left off," and Python provides no API to reset that frame to position 0.

**The duck-typed test:**

```python
hasattr(obj, "__iter__")   # True for both iterables AND iterators
hasattr(obj, "__next__")   # True ONLY for iterators
iter(obj) is obj           # True for iterators; False for re-iterables
```

A list passes the first test but fails the third — it's an iterable, not an iterator. A generator passes all three — it's both.

**The fix when you need multi-pass over a one-shot source:** materialize it. `data = list(source)` gives you a re-iterable list at O(N) memory. The other option is `itertools.tee(source, n)`, which produces N independent iterators by buffering items the slowest one hasn't seen yet — lazy but still O(N) in the worst case.

→ **Where this matters for the resumable iterator problem:**

You'll see in the problem statement that `set_state(state)` must restart iteration from a saved position. The most common implementation: re-`iter()` the source and skip forward N items. That requires the source to be *re-iterable* — list, tuple, file path, anything you can call `iter()` on more than once. A one-shot generator passed in would silently break `set_state`, because the generator is already past the save point and can't be rewound.

So the constraint on the problem's *input* is: sources must be re-iterable. Naming this constraint out loud — "I'm assuming the inputs are lists, tuples, or other re-iterables; a raw generator would break `set_state` because I can't rewind it" — is the kind of observation an interviewer rewards.

**Practice:** write a function `tee_safe(source, n)` that returns `n` independent iterators over `source`. If `source` is a generator, use `itertools.tee` (which memoizes); if it's already re-iterable, just `iter(source)` `n` times. The difference between those two branches IS the concept.

**Done when:** you can explain "single-shot iterator vs. re-iterable source" in two sentences and know how to detect which one you've been handed.

---

## Concept 3: State design — what's the minimum thing you need to save?

**What you're learning:** how to design *serializable state* for any object whose work happens incrementally — an iterator partway through a stream, a parser halfway through a file, a long-running job paused for a checkpoint. Across all these cases, three rules separate good state from bad.

**The three rules of resumable state:**

1. **Serializable** — represent state as primitives (dict, list, int, str), not as live language objects. A pickled iterator works in-process but fails the moment state crosses a process boundary or a language. JSON-compatible state survives both.

2. **Position-based, not snapshot-based** — store *where you are*, not *what's left*. A cursor (one integer) is O(1) space and survives source mutation; a copy of "remaining items" is O(N) and goes wrong if the source changes between save and restore.

3. **Minimal but sufficient** — enough to resume *exactly*. After restore, the next operation must produce the same value it would have produced without the round-trip. Anything more is dead weight you'll have to keep consistent; anything less can't disambiguate.

**A worked example: a resumable counter.**

```python
class Counter:
    def __init__(self, n): self.n = n; self.i = 0
    def __next__(self):
        if self.i >= self.n: raise StopIteration
        x = self.i; self.i += 1; return x
    def __iter__(self): return self

    def get_state(self) -> dict:
        return {"i": self.i}                     # ONE integer

    def set_state(self, state: dict) -> None:
        self.i = state["i"]
```

State is `{"i": cursor}` — one integer. Why not `{"n": self.n, "i": self.i}`? Because `n` is a constructor input; it doesn't change during iteration, so it isn't *state*. Two values that don't need to be saved would be two extra invariants for `set_state` to police.

**The wrong shapes — name these so you can defend the right one:**

| Wrong shape | Why it's wrong |
|-------------|----------------|
| `{"remaining": [items, not, yet, seen]}` | O(N) memory; breaks if source mutates between save and restore; defeats the point of streaming |
| `{"iterator": pickle.dumps(self._inner)}` | Not portable across processes / languages; ties you to CPython internals |
| `{"items_seen": 4}` when there are multiple sources | Loses which source you're in; can't resume across sources |
| `{"file_offset": 137}` (byte offset, not item count) | Only works for byte streams; fails for arbitrary iterables; couples state to text encoding |

→ **Where this matters for the resumable iterator problem:**

The problem iterates over a *list of sources*, so a single cursor isn't enough — you also need to know which source you're in. The minimum state is two integers:

```python
state = {
    "source_idx": 1,        # which source are we currently inside?
    "offset": 4,            # how many items into that source?
}
```

Restore is "open source 1, skip 4 items, you're caught up." That's it. Two ints, JSON-serializable.

**Per-source state for the async / multi-source variant:**

The fuller variant of the problem (see `problem.md`) maintains **independent state per source** — useful if multiple sources advance in parallel or if some need to be replayed independently. Generalize the two integers to:

```python
state = {
    "per_source": [
        {"offset": 5},      # source 0 has advanced 5 items
        {"offset": 0},      # source 1 hasn't been touched
        {"offset": 8},      # source 2 has advanced 8
    ],
    "current": 2,           # which source we're actively consuming
}
```

Same three rules, more sources. The structure tells the story: "how far each has gone, and which one is live."

**Done when:** you can articulate the three rules (serializable / position-based / minimal-sufficient) in your own words and apply them to a new object you've never seen — pick any LeetCode iterator problem and ask yourself "what's the minimum state I'd need to make this resumable?"

---

## Concept 4: `__getstate__` / `__setstate__` — the pickle hooks (preview)

**What you're learning:** the dunder methods that pickle invokes. You won't use them in the base solution (we'll use explicit `get_state` / `set_state` methods), but the interviewer will ask "could you make this work with `pickle`?" and you need to know the answer.

**The contract:**

- `obj.__getstate__()` — return a serializable representation (dict, tuple, anything pickle can handle). Pickle calls this when serializing.
- `obj.__setstate__(state)` — restore the object's state from that representation. Pickle calls this when deserializing (after creating an empty instance via `__new__`).

```python
class ResumableCounter:
    def __init__(self, n: int) -> None:
        self.n = n
        self.i = 0

    def __next__(self):
        if self.i >= self.n: raise StopIteration
        x = self.i; self.i += 1; return x

    def __iter__(self): return self

    def __getstate__(self):
        return {"n": self.n, "i": self.i}     # NOTE: includes n — see below

    def __setstate__(self, state):
        self.n = state["n"]
        self.i = state["i"]
```

Now `pickle.dumps(it)` / `pickle.loads(...)` Just Works.

**Wait — Concept 3 said `n` doesn't belong in state. Why is it here?**

Because **pickle bypasses `__init__`**. `pickle.loads(blob)` constructs the instance via `cls.__new__(cls)` (which produces a *bare* object with no attributes) and then calls `__setstate__(state)`. `__init__` never runs. So whatever attributes `__init__` would have set — including `n` — must come from the state, otherwise `__next__` will hit `AttributeError` on `self.n`.

Explicit `get_state` / `set_state` (Concept 3) doesn't have this problem because you call `it.set_state(state)` on an *already-constructed* object — `__init__` ran at construction time, `n` is already there, state only needs the cursor.

This asymmetry — *"pickle state must reconstruct the whole object; explicit state only restores what changed during iteration"* — is the cleanest argument for preferring the explicit pattern as the primary API. The state stays minimal; you don't pay to re-encode constructor args you already have.

**Why the explicit `get_state` / `set_state` is the better base answer:**

- It's **language-agnostic** — the state dict is just JSON. Survives cross-process, cross-language, cross-version.
- It's **testable** — you can inspect the state in tests; pickle blobs are opaque.
- It **forces you to design the state minimally** — `set_state` runs against an `__init__`-ed object, so only mutating state needs to be saved. Pickle's path forces you to bundle constructor args alongside, which doubles the surface area and the invariants `__setstate__` has to police.

Mention `__getstate__` / `__setstate__` as a *follow-up* — "and to make this pickle-able, here's the two-line addition" — not as the primary API.

**Done when:** you can explain when pickle is the right tool (in-process checkpoint) vs. when explicit state is (cross-process, durable storage).

---

## Concept 5 (preview): async iteration — `__aiter__` / `__anext__`

**What you're learning:** the async sibling of the iterator protocol. The full HelloInterview version of this problem uses `async next()`; you should know the shape even if your base solution is sync.

**The async iterator protocol mirrors the sync one:**

| Sync | Async |
|------|-------|
| `__iter__` | `__aiter__` |
| `__next__` | `__anext__` (a coroutine — must be `await`ed) |
| `StopIteration` | `StopAsyncIteration` |
| `for x in it:` | `async for x in it:` |

```python
class AsyncCounter:
    def __init__(self, n): self.n = n; self.i = 0
    def __aiter__(self): return self
    async def __anext__(self):
        if self.i >= self.n:
            raise StopAsyncIteration
        await asyncio.sleep(0)        # cooperate with the event loop
        x = self.i; self.i += 1
        return x
```

For the resumable iterator, the async variant has one additional concern: **state captured during `await` boundaries.** If `get_state()` runs while an `__anext__` is mid-`await`, what's the "current position"? Decide your policy (atomic at start of `__anext__`? atomic at first `await` point?) and document it.

**Don't drill async yet.** Get the sync version solid; bolt on `__aiter__` / `__anext__` as a follow-up. We'll generate `coding/concepts/asyncio.md` when you reach the crawler's async variant or a Problem 8 redo.

**Done when:** you can recite the sync→async name mapping and have the shape in your head for the follow-up.

---

## Hands-on drills (`practice/`)

Reading concepts is not enough. The `practice/` folder has scaffolds (TODO markers, not finished code) for each step of the prep arc above. Fill each in, run it, then delete and re-do the next day.

| Drill | Builds | Backing concept |
|-------|--------|-----------------|
| `01_counter.py` | the bare-minimum `__iter__` / `__next__` / `StopIteration` triangle | Concept 1 |
| `02_range.py` | sign-aware termination, zero-step rejection, multi-arg constructor | Concept 1 |
| `03_chunked_reader.py` | offset-cursor pattern over a string — the closest single-source analog of the real problem | Concept 1 (applied) |
| `04_one_shot_trap.py` | watch the iterable-vs-iterator distinction *fail* on a generator, then fix it with materialization | Concept 2 |
| `05_resumable_range.py` | `get_state` / `set_state` on a single-source iterator — the bridge to the assembled problem | Concept 3 |

**Readiness bar:** when you can write `02_range.py` from a blank screen in under 10 minutes AND `05_resumable_range.py` in under 15 minutes, attempt `solution.py`. Not before.

---

## LeetCode warm-ups (optional, 60 min total)

These two LC problems exercise iterator design without the resumability twist. Useful if Concept 1 felt rusty.

**[LC 251 — Flatten 2D Vector](https://leetcode.com/problems/flatten-2d-vector/) (Medium, premium)**

The exact "list of lists" structure of the resumable iterator's input. Has `next()` and `hasNext()` — not the resumable API, but the *same internal cursor pattern* (row index + col index). Solve it first; the resumable version is "this plus state design."

**[LC 341 — Flatten Nested List Iterator](https://leetcode.com/problems/flatten-nested-list-iterator/) (Medium)**

Stack-based iterator over arbitrarily-nested structure. Different shape (recursion in the data, not just one level deep), but excellent practice at deciding *where the cursor lives*. Skip if 251 was easy.

**Done when:** you can write LC 251 from blank in under 20 minutes.

---

## Generate the concept guide

The README in `coding/concepts/` points to `iterators.md` — which you should generate before attempting this problem. Ask Claude Code:

> generate the iterators concept guide

It'll write `coding/concepts/iterators.md` tuned to the prep arc above (protocol, multi-pass distinction, state design, pickle hooks, async preview). Read it after this doc; do the exercises in it; then attempt `problem.md`.

---

## Suggested schedule

| Day | What |
|-----|------|
| Day 1 | Read this doc. Generate and read the iterators concept guide. Write `Counter`, `Range`, `ChunkedReader` from blank. |
| Day 2 | LC 251 (Flatten 2D Vector). Then re-do `Range` from blank as warm-up the next morning. |
| Day 3 | **Attempt the resumable iterator** — open `problem.md`, work `solution.py`, run `test_solution.py`. 30-minute timer on the sync base. |
| Day 4 | Read `interviewer_notes.md`. Then pick one follow-up — the async variant or pickle integration — and implement it as `solution_async.py` / `solution_picklable.py`. |

This is deliberately compact. The base is small; the *interview* is the follow-up ladder.

## How to use Claude Code during this

Teacher-mode questions worth asking:
- "explain the iterator protocol — what does `for x in obj` actually do under the hood"
- "show me the difference between iterable and iterator with three examples"
- "what's the minimum state you'd save to make a flatten-iterator resumable?"
- "what changes if I bolt async on — what new edge cases appear?"

Don't ask Claude to solve LC 251 for you. The muscle is in writing the cursor advancement yourself.

## When you're ready

When you can write a list-of-lists flattener (sync, no resumability) from a blank screen in under 10 minutes, **then** open `problem.md` and start a 30-minute timer on the base. Not before.
