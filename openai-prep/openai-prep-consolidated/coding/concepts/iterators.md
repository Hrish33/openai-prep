# Iterators

This guide is the Python-internals view of the iterator protocol. The companion practice folder is `coding/week2/04_resumable_iterator/practice/` — read this guide, then drill there.

## 30-second pitch

An **iterator** is an object that produces values one at a time and signals "I'm done" by raising `StopIteration`. An **iterable** is anything you can ask "give me an iterator over you." `for x in obj` is sugar for "call `iter(obj)` to get an iterator, then call `next(it)` in a loop until `StopIteration`."

The protocol is exactly two methods:

| Method | Lives on | Does |
|--------|----------|------|
| `__iter__(self)` | iterable AND iterator | returns an iterator (often `self`) |
| `__next__(self)` | iterator only | returns the next value, or raises `StopIteration` |

That's it. Everything else — generators, comprehensions, `for` loops, `map`, `zip`, `itertools` — is built on these two methods.

## Minimal Python code

```python
class Counter:
    def __init__(self, n: int) -> None:
        self.n = n
        self.i = 0

    def __iter__(self):           # iterables MUST have this
        return self                #   here, the iterator IS the same object

    def __next__(self):           # iterators MUST have this
        if self.i >= self.n:
            raise StopIteration    #   the protocol's "done" signal
        x = self.i
        self.i += 1
        return x

for x in Counter(3):
    print(x)                       # 0, 1, 2
```

Six lines of logic and you've satisfied the entire `for` loop protocol. The reason `for` works on lists, dicts, files, generators, `range`, and your custom `Counter` is that they all expose these two methods (often via different code paths in CPython, but the contract is identical).

## How CPython implements it

The `for` statement compiles to bytecode that calls `iter()` once, then `next()` in a loop. The relevant bytecodes (Python 3.12+) are:

```
GET_ITER         # pops TOS, pushes iter(TOS)
FOR_ITER target  # calls next(TOS); if StopIteration, jumps to target
                 # else pushes the yielded value
```

So `for x in obj:` literally is:

```
       LOAD_NAME obj
       GET_ITER                  # stack: [iter(obj)]
loop:  FOR_ITER end               # stack: [iter(obj), x]  -- or jumps to end
       STORE_NAME x
       <body>
       JUMP loop
end:
```

`StopIteration` is special-cased in `FOR_ITER` — it's caught at the C level and translated into a jump. This is why a `for` loop never "sees" the exception; it's the protocol's terminator, not a real error.

**`iter()` and `next()` at the C level:**

- `iter(obj)` calls `tp_iter` on the object's type (`PyObject_GetIter` in `Objects/abstract.c`). Falls back to checking for `__getitem__` with sequential integer indices — that's the *legacy sequence protocol*, why some old code without `__iter__` still iterates.
- `next(obj)` calls `tp_iternext` (`PyIter_Next`). Sentinel: returns `NULL` and sets `StopIteration` to signal exhaustion. The Python-level `__next__` wraps this.

**Generators are iterators with state.** A `def f(): yield x` function returns a generator object — it has `tp_iter` returning `self` and `tp_iternext` driving the suspended frame. The `yield` keyword compiles to `YIELD_VALUE`, which suspends the frame and returns control. `next()` resumes it. This is why generators are iterators *and* iterables in one object: their `__iter__` returns `self` (standard for iterators), and their `__next__` resumes the suspended frame.

## Common patterns

### 1. The cursor pattern

When the data has a natural index, store the cursor as an integer and advance on each `__next__`. Used by `Range`, `ChunkedReader`, any flatten-iterator.

```python
class ChunkedReader:
    def __init__(self, text, size):
        self.text = text
        self.size = size
        self.cursor = 0

    def __iter__(self): return self
    def __next__(self):
        if self.cursor >= len(self.text):
            raise StopIteration
        chunk = self.text[self.cursor : self.cursor + self.size]
        self.cursor += self.size
        return chunk
```

### 2. The wrapped-iterator pattern

When you're transforming an existing iterable (filter, map, dedupe), hold its iterator as an instance attribute and delegate.

```python
class Dedupe:
    def __init__(self, source):
        self._inner = iter(source)            # get an iterator out of the iterable
        self._seen = set()

    def __iter__(self): return self
    def __next__(self):
        while True:                            # loop until a non-dup is found OR StopIteration propagates
            x = next(self._inner)              # if inner raises StopIteration, we propagate naturally
            if x not in self._seen:
                self._seen.add(x)
                return x
```

Two things to notice: `next(self._inner)` raising `StopIteration` is the *correct* termination — let it propagate, don't catch it. And the `while True` loop is the standard shape for filter-style iterators: keep pulling until you have something to yield.

### 3. The stateful generator pattern

When the protocol object's state would be more lines than the generator equivalent, just write a generator. Same contract, much less code:

```python
def chunked(text, size):
    cursor = 0
    while cursor < len(text):
        yield text[cursor : cursor + size]
        cursor += size
```

Generators win on **conciseness** and lose on **introspection**. With a class you can have other methods (`get_state`, `reset`), instance attributes (state you can inspect), and dunder hooks (`__len__`, `__repr__`). With a generator, you have a closure — opaque from the outside.

**The rule:** start with a generator. Promote to a class only when you need state methods or dunder hooks that generators can't give you. The resumable-iterator problem is exactly such a case — `get_state` / `set_state` don't fit naturally into a generator.

### 4. The composite/flatten pattern

Iterate across multiple sources in order. Hold the index of the current source plus the live iterator over it:

```python
class Flatten:
    def __init__(self, sources):
        self._sources = sources
        self._idx = 0
        self._inner = None

    def __iter__(self): return self
    def __next__(self):
        while self._idx < len(self._sources):
            if self._inner is None:
                self._inner = iter(self._sources[self._idx])
            try:
                return next(self._inner)
            except StopIteration:
                self._idx += 1
                self._inner = None
        raise StopIteration
```

This is the spine of the Problem 4 base solution. The `while` loop is critical: a single `__next__` call may cross any number of empty sources before finding (or failing to find) the next item.

### 5. The save/restore pattern (resumable)

Add `get_state` returning a serializable cursor snapshot, and `set_state` that replaces the cursor. The state must be a *value* (fresh dict), not a *reference* to internal storage:

```python
def get_state(self) -> dict:
    return {"idx": self._idx, "offset": self._offset}     # fresh dict

def set_state(self, state: dict) -> None:
    self._idx = state["idx"]
    self._offset = state["offset"]
    self._inner = None                                     # force lazy reopen
```

The "force lazy reopen" line is the subtle one. After `set_state`, the next `__next__` will see `_inner is None` and re-iter the current source. Without it, `_inner` would still point at the old position and you'd read from the wrong place.

## Common mistakes

1. **Returning `None` from `__next__` on exhaustion.** `None` is a *value*. The protocol is "raise to signal." A `for` loop reading `None` won't terminate — it'll pass `None` to the body. Symptom: infinite loop, or `NoneType` errors downstream.

2. **Catching `StopIteration` inside `__next__` and not re-raising.** If you wrap inner iteration in `try/except StopIteration`, you have to either return a real value or re-raise. Swallowing it silently makes the iterator never end.

3. **`__iter__` returning a new object every time (when it shouldn't).** For an *iterator*, `iter(it) is it` must be true — same object. Returning a new iterator each time means `for x in it` works once but `next(it)` in user code gets confused. Iterables (lists, dicts) DO return fresh iterators, but iterators themselves return `self`.

4. **Iterating a one-shot source twice.** `g = (x for x in [1,2,3]); list(g); list(g)` — second call returns `[]`. Generators are iterators (single-shot). Containers (`list`, `dict`, `range`) are iterables you can `iter()` repeatedly. Knowing which one you're holding determines whether `set_state` is even possible.

5. **Holding internal state by reference in `get_state`.** Returning `self._state_dict` means the caller can mutate the iterator's internals. Always `return dict(self._state)` or build a fresh dict.

6. **`isinstance(obj, Iterator)` to "check if it's an iterator."** The abstract base check works, but the duck-typed answer is `hasattr(obj, '__next__')`. The ABC check imports `collections.abc.Iterator` which is fine in app code; for raw checks in standard-library-style code, hasattr is the idiom.

7. **`for` loops on dict views during mutation.** `for k in d: del d[k]` raises `RuntimeError: dictionary changed size during iteration` at the next iteration. CPython's dict iterator checks the dict's version counter; if the dict was mutated, it bails. Same pattern shows up in `set` and `list` (the list one is more forgiving — it'll skip or repeat items rather than raising, which is arguably worse).

## Exercises

These mirror the drills in the practice folder. Solutions are collapsible — try first.

### 1. Implement `enumerate`

Without using the builtin, write a class `MyEnumerate` such that `MyEnumerate(["a","b","c"])` yields `(0,"a"), (1,"b"), (2,"c")`.

<details><summary>Solution</summary>

```python
class MyEnumerate:
    def __init__(self, source, start=0):
        self._inner = iter(source)
        self._i = start

    def __iter__(self): return self
    def __next__(self):
        x = next(self._inner)             # StopIteration propagates naturally
        i, self._i = self._i, self._i + 1
        return (i, x)
```

Note: increment the counter *after* `next(self._inner)` succeeds. If you increment before and inner exhausts, you've wasted a count.

</details>

### 2. Implement `zip` for two iterables

`MyZip([1,2,3], ["a","b"])` yields `(1,"a"), (2,"b")` — stops at the shortest.

<details><summary>Solution</summary>

```python
class MyZip:
    def __init__(self, a, b):
        self._a = iter(a)
        self._b = iter(b)

    def __iter__(self): return self
    def __next__(self):
        return (next(self._a), next(self._b))    # whichever raises StopIteration first wins
```

The right-hand `next` only runs if the left-hand succeeded. If `_a` is shorter, `_b` is left with one item unconsumed — that matches `zip`'s behavior (it's why `zip` "swallows" the next item from the longer iterable, a known footgun for resumable streams).

</details>

### 3. Implement a resumable `MyRange`

`r = MyRange(0, 10)`, consume 3, `s = r.get_state()`, build `r2 = MyRange(0, 10); r2.set_state(s)`, verify `list(r2) == [3,4,5,6,7,8,9]`.

<details><summary>Solution</summary>

```python
class MyRange:
    def __init__(self, start, stop, step=1):
        if step == 0: raise ValueError("step must be non-zero")
        self.start, self.stop, self.step = start, stop, step
        self.cursor = start

    def __iter__(self): return self
    def __next__(self):
        if (self.step > 0 and self.cursor >= self.stop) or \
           (self.step < 0 and self.cursor <= self.stop):
            raise StopIteration
        x = self.cursor
        self.cursor += self.step
        return x

    def get_state(self): return {"cursor": self.cursor}
    def set_state(self, s): self.cursor = s["cursor"]
```

The state is just the cursor. `start`, `stop`, `step` are constructor-time inputs, not state — they don't change during iteration, so they don't belong in `get_state`. This is the design discipline the resumable-iterator problem tests.

</details>

### 4. Implement `peekable`

Wrap an iterator so you can `peek()` at the next value without consuming it. `next()` still consumes.

<details><summary>Solution</summary>

```python
_SENTINEL = object()

class Peekable:
    def __init__(self, source):
        self._inner = iter(source)
        self._peeked = _SENTINEL              # _SENTINEL means "no value cached"

    def __iter__(self): return self
    def __next__(self):
        if self._peeked is not _SENTINEL:
            x, self._peeked = self._peeked, _SENTINEL
            return x
        return next(self._inner)              # propagates StopIteration

    def peek(self):
        if self._peeked is _SENTINEL:
            self._peeked = next(self._inner)  # may raise StopIteration
        return self._peeked
```

Why a sentinel object (not `None`)? Because the inner iterator might yield `None` legitimately — using `None` as "no cached value" would collide. The `object()` sentinel pattern is the idiomatic fix; it has a unique identity nothing else shares.

</details>

## How this shows up in OpenAI interviews

**Direct hits:**

- **Problem 4 (Resumable Iterator)** — the iterator protocol IS the interview. The whole signal is whether you can write `__iter__`/`__next__` from memory AND design `get_state`/`set_state` cleanly. See `coding/week2/04_resumable_iterator/`.

**Indirect hits — places where iterator depth shows up:**

- **Spreadsheet (Problem 1) follow-ups** — "expose a `__iter__` over cells in topological order." If your `__iter__` returns `self` while the topo state is mid-mutation, mutation during iteration is the bug class to anticipate. Use the dict-view "RuntimeError on concurrent modification" pattern.
- **Time-based KV (Problem 3) follow-ups** — "iterate a key's history" or "range scan returns a generator." Both are iterator-protocol design questions. The generator is the right choice; understand why (lazy, no buffer, propagates `StopIteration` naturally).
- **In-memory SQL (Problem 7)** — query results are iterators. A `SELECT *` over a million rows must NOT materialize the result list; it must be a streaming iterator. Same shape as `Flatten` above but per-row instead of per-source.

**The deeper signal — what an OpenAI interviewer is *actually* testing when iterators come up:**

1. **Do you reach for the cheapest abstraction?** Generator first, class only when you need state methods.
2. **Do you know the iterable/iterator distinction?** Naming this without prompting separates senior from junior candidates.
3. **Do you propagate `StopIteration` correctly?** Catching it is the #1 mistake; the fix is "don't."
4. **Do you handle mutation during iteration thoughtfully?** Dict's `RuntimeError` policy is one valid answer; snapshot is another; "undefined behavior, document it" is also defensible.
5. **Can you serialize iteration state when asked?** The base case is two integers (cursor + source index). The fact that this fits in a JSON dict is the whole reason the problem works.

If you can write a custom iterator in under 5 minutes, defend the iterable-vs-iterator distinction in one sentence, and articulate the minimum state design for a resumable variant — you're at the bar for Problem 4 and well-positioned to land iterator-related follow-ups across the rest of the loop.
