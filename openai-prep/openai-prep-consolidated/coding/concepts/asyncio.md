# asyncio — concept guide

For: Problem 4 (Resumable Iterator — async follow-up), Problem 8 (Multithreaded Crawler — async alt path), and the general "depth in Python internals" rubric axis.

How to read this: sections 1–4 are self-contained for the Problem 4 async follow-up. Sections 5–7 you need for Problem 8. Section 8+ is general depth.

---

## 1. The 30-second pitch

`asyncio` is **cooperative concurrency on a single thread**. You write functions that explicitly **yield control** at `await` points, and an event loop interleaves them. No OS threads, no preemption, no GIL contention — just one thread bouncing between paused coroutines.

The win: **thousands of concurrent I/O operations on one thread**. The cost: any blocking call (sync file I/O, `time.sleep`, CPU-bound work) freezes everything.

When to reach for it: many concurrent network/file/IPC operations that spend most of their time waiting. Not for CPU-bound work — use processes there.

---

## 2. Coroutines: the foundation

`async def` defines a **coroutine function**. Calling it returns a **coroutine object** — it does NOT execute the body.

```python
async def greet(name):
    print(f"hello {name}")

coro = greet("world")        # NOTHING printed yet
print(type(coro))            # <class 'coroutine'>
# RuntimeWarning if you never await it
```

To actually run it, an event loop must drive it. The simplest way:

```python
import asyncio
asyncio.run(greet("world"))   # now "hello world" prints
```

**`await`** suspends the current coroutine until the awaited thing completes, yielding control to the event loop.

```python
async def slow_work():
    await asyncio.sleep(1)           # suspends for 1s, doesn't block thread
    return 42

async def main():
    result = await slow_work()        # waits for slow_work
    print(result)

asyncio.run(main())
```

What `await` actually does at the protocol level: it drives the coroutine via `.send()` / `.__next__()` until it yields a Future, then registers a callback on that Future's completion and pauses. This is the same machinery as generator `.send()`. A coroutine is structurally a generator with sugar.

---

## 3. Running coroutines: `asyncio.run`

`asyncio.run(coro)` is the entry point:
- Creates a new event loop
- Runs `coro` to completion
- Closes the loop

**Use it once, at the top of your program.** Don't nest it. Inside `async` code, you don't call `asyncio.run` — you just `await`.

```python
async def main():
    await foo()
    await bar()

asyncio.run(main())          # only here, at the boundary
```

Rule of thumb: program-level code is sync (uses `asyncio.run`); everything inside the async tree uses `await`.

---

## 4. Async iterators — `__aiter__` / `__anext__` / `async for`

This is the protocol Problem 4's follow-up wants. **Memorize the table:**

| Sync | Async |
|---|---|
| `__iter__(self)` returns self | `__aiter__(self)` returns self (NOT async) |
| `def __next__(self)` | `async def __anext__(self)` |
| `raise StopIteration` | `raise StopAsyncIteration` |
| `for x in it:` | `async for x in it:` |
| `next(it)` | `await it.__anext__()` |

**Minimal example:**

```python
class AsyncCounter:
    def __init__(self, n):
        self.i = 0
        self.n = n

    def __aiter__(self):              # NOT async — just returns self
        return self

    async def __anext__(self):        # async — can await inside
        if self.i >= self.n:
            raise StopAsyncIteration  # the async-flavored sentinel
        val = self.i
        self.i += 1
        return val

async def main():
    async for x in AsyncCounter(3):
        print(x)                       # 0, 1, 2

asyncio.run(main())
```

**Three traps to internalize:**

1. **`__aiter__` is not async.** It's a regular method. `async def __aiter__` is wrong — the protocol expects it to return an async iterator synchronously.
2. **`StopIteration` cannot leak out of a coroutine.** Python explicitly raises `RuntimeError: generator raised StopIteration` if it does. The reason: `StopIteration` is how generators (which coroutines build on) signal return-value to their caller. Confusing the two would break the runtime. Always `StopAsyncIteration` in `__anext__`.
3. **The data source doesn't need to be async.** Items can come from sync lists. `async` is about the *iterator being suspendable*, not the data being async. Use async iterators when fetching/awaiting between items matters (network, paginated API, slow disk read), or when you want backpressure-aware iteration.

**Async generator (the syntactic sugar):**

```python
async def acounter(n):
    for i in range(n):
        await asyncio.sleep(0)        # yield control to loop
        yield i

async def main():
    async for x in acounter(3):
        print(x)
```

`async def` + `yield` = async generator. Python builds the `__aiter__` / `__anext__` / `StopAsyncIteration` plumbing for you. This is to async iterators what regular generators are to sync iterators.

---

## 5. Async context managers — `__aenter__` / `__aexit__` / `async with`

The async-flavored `with`. Useful for connection pools, async file handles, locks.

```python
class AsyncFileLock:
    def __init__(self, path):
        self.path = path

    async def __aenter__(self):
        await acquire_distributed_lock(self.path)  # awaits without blocking
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await release_distributed_lock(self.path)

async def main():
    async with AsyncFileLock("/tmp/foo"):
        await do_work()
```

Note both `__aenter__` and `__aexit__` are async (unlike `__aiter__`). They can `await`.

Convenience: `@asynccontextmanager` decorator from `contextlib` turns a generator into one.

---

## 6. Concurrent coroutines: `gather`, `create_task`

This is where async earns its keep — running many coroutines concurrently.

**`asyncio.gather(*coros)`** runs them concurrently and returns a list of results in order.

```python
async def fetch(url):
    await asyncio.sleep(1)            # simulate I/O
    return f"got {url}"

async def main():
    results = await asyncio.gather(
        fetch("a"), fetch("b"), fetch("c"),
    )
    print(results)                    # ['got a', 'got b', 'got c'] — ~1s total, not 3

asyncio.run(main())
```

3 fetches × 1s each = ~1 second total, not 3. That's the concurrency win.

**`asyncio.create_task(coro)`** schedules a coroutine in the background and returns a `Task` you can await later.

```python
async def main():
    t = asyncio.create_task(fetch("a"))    # starts running immediately
    do_other_work()                         # runs concurrently with fetch
    result = await t                        # collect when needed
```

**When to use which:**
- `gather` — fire N off, collect all results. Simple fan-out.
- `create_task` — kick off a background coroutine and continue. Useful when you want fire-and-forget, or to schedule before knowing when you'll await.

Both are how you'd implement the Problem 8 async crawler: each fetch is a coroutine, `asyncio.gather(*fetches)` runs them concurrently, the event loop interleaves them while they wait on network.

---

## 7. Cancellation and timeouts

`asyncio.wait_for(coro, timeout)` raises `asyncio.TimeoutError` if `coro` doesn't finish in time. Internally it cancels the coro.

```python
try:
    result = await asyncio.wait_for(slow_op(), timeout=2.0)
except asyncio.TimeoutError:
    print("gave up")
```

Cancellation propagates as `asyncio.CancelledError` raised inside the coroutine at its next `await`. Coroutines can catch it to clean up, but should re-raise — swallowing `CancelledError` is a bug.

```python
async def worker():
    try:
        await long_op()
    except asyncio.CancelledError:
        cleanup()
        raise                          # re-raise — don't swallow
```

---

## 8. How CPython implements it

Coroutines are **generators in disguise**. The CPython internals:
- `async def` compiles to a function whose `__code__.co_flags` includes `CO_COROUTINE`
- Calling it returns a `coroutine` object — same plumbing as a generator (`.send()`, `.throw()`, `.close()`)
- `await x` is desugared to roughly `yield from x.__await__()`
- The event loop drives coroutines by calling `.send(None)` until they yield a Future
- When the Future completes, the loop calls `.send(result)` to resume

That's it. There's no magic — `asyncio` is a generator-driving event loop plus a Future type. The protocol is small.

The event loop itself is single-threaded. It maintains a queue of ready callbacks and a `selectors`-based reactor for I/O readiness. Each iteration: drain ready callbacks, poll the reactor for I/O, schedule callbacks for ready events, repeat.

`uvloop` is a drop-in replacement event loop written in Cython on top of libuv — 2-4x faster, same API. Production async services use it.

---

## 9. Common mistakes

1. **Calling an async function without `await`.** Returns a coroutine object that never runs. Python warns with `RuntimeWarning: coroutine was never awaited`. Easy to miss in tests.

2. **Blocking calls inside `async` code.** `time.sleep(1)`, `requests.get(...)`, `open(...).read()` — all block the thread, freezing every other coroutine on the loop. Use `asyncio.sleep`, `httpx.AsyncClient`, `aiofiles`. If you must call sync code, wrap it: `await asyncio.to_thread(blocking_fn, arg)`.

3. **Calling `asyncio.run` from inside another coroutine.** `asyncio.run` creates a NEW loop. Nesting raises `RuntimeError: asyncio.run() cannot be called from a running event loop`. Inside async code, just `await`.

4. **Using `StopIteration` in `__anext__`.** Raises `RuntimeError` — Python explicitly forbids `StopIteration` leaking from coroutines.

5. **`async def __aiter__`.** It's NOT async. Just `def`. (See section 4.)

6. **Forgetting to consume Tasks.** `asyncio.create_task(coro)` without ever awaiting the task — the coro may run but exceptions vanish silently. Always either `await` the task or attach a done callback.

7. **CPU-bound work in `async`.** Async gives concurrency for *waiting*. A coroutine doing a 30-second NumPy crunch blocks every other coroutine for 30 seconds. Move CPU-bound work to processes (`run_in_executor` with `ProcessPoolExecutor`).

---

## 10. Exercises

### Exercise 1: convert your sync iterator to async

Take the `Counter` class from `week2/04_resumable_iterator/practice/01_counter.py` and write `AsyncCounter`. Drive it with `async for`.

<details>
<summary>Solution</summary>

```python
import asyncio

class AsyncCounter:
    def __init__(self, n):
        self.i = 0
        self.n = n

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.i >= self.n:
            raise StopAsyncIteration
        await asyncio.sleep(0)        # forces a suspension point
        val = self.i
        self.i += 1
        return val

async def main():
    async for x in AsyncCounter(5):
        print(x)

asyncio.run(main())
```

Why `await asyncio.sleep(0)`? It hands control back to the loop without delay — proves you understand a suspension point exists. In a real implementation, you'd `await` something that actually does I/O.
</details>

### Exercise 2: concurrent fetches

Write `async def fetch_all(urls)` that fakes 10 fetches (each `await asyncio.sleep(1)`) and returns when all are done. Compare time to the sequential version.

<details>
<summary>Solution</summary>

```python
import asyncio, time

async def fetch(url):
    await asyncio.sleep(1)
    return f"got {url}"

async def fetch_all(urls):
    return await asyncio.gather(*(fetch(u) for u in urls))

async def main():
    urls = [f"url-{i}" for i in range(10)]
    t0 = time.perf_counter()
    results = await fetch_all(urls)
    print(f"{time.perf_counter() - t0:.2f}s for {len(results)} fetches")
    # ~1.0s — all concurrent

asyncio.run(main())
```

Sequential (`for url in urls: await fetch(url)`) takes 10s. Gather takes ~1s. That's the win.
</details>

### Exercise 3: async generator

Write `async def acounter(n)` as an async generator (using `async def` + `yield`). Consume it with `async for`.

<details>
<summary>Solution</summary>

```python
async def acounter(n):
    for i in range(n):
        await asyncio.sleep(0)
        yield i

async def main():
    async for x in acounter(3):
        print(x)

asyncio.run(main())
```

Note: no `__aiter__` / `__anext__` to write. Python builds them for you.
</details>

### Exercise 4: bounded concurrency

`asyncio.gather` runs all coros simultaneously. What if you want at most K concurrent? Implement `bounded_gather(coros, k)` using `asyncio.Semaphore`.

<details>
<summary>Solution</summary>

```python
async def bounded_gather(coros, k):
    sem = asyncio.Semaphore(k)

    async def with_limit(coro):
        async with sem:
            return await coro

    return await asyncio.gather(*(with_limit(c) for c in coros))
```

This is exactly the pattern an OpenAI interviewer would ask for as a follow-up to Problem 8's async crawler: "what if I don't want to hammer the target site with 1000 concurrent fetches?" Answer: semaphore-bounded gather.
</details>

---

## 11. How this shows up in OpenAI interviews

**Problem 4 (Resumable Iterator) follow-up:** the reported variant is async. They'll ask you to implement `__aiter__` / `__anext__`. The state-design machinery from the sync base is unchanged — only the protocol is different. The follow-up question they'll probe: "what if `get_state` is called mid-`__anext__`?" Answer: snapshot policy — either disallow concurrent calls (document) or define atomic-at-entry semantics.

**Problem 8 (Multithreaded Crawler) async alt:** the threading version is the base. Async is the rung above. Each fetch is a coroutine, you use `asyncio.gather` to run K concurrently (with `asyncio.Semaphore` for bounding), and you handle cancellation/timeouts per fetch. The interview signal: "why async over threads?" Answer: I/O-bound, no GIL contention, scales to thousands of concurrent connections on one thread. "Why threads over async?" Answer: existing sync libraries (requests, urllib), simpler mental model, fine for hundreds not thousands.

**Depth probes you'll hit:**
- "What does `await` actually do?" — drives the coroutine via `.send()`, registers callback on awaited Future, suspends. (Section 8.)
- "Why can't `StopIteration` leak from a coroutine?" — because coroutines reuse generator machinery, and `StopIteration` is overloaded to mean return-value. (Section 4 trap 2.)
- "What happens if I call `time.sleep` in an async function?" — blocks the entire event loop. Wrong tool. (Section 9 mistake 2.)
- "How would you run CPU-bound work alongside async?" — `run_in_executor` with `ProcessPoolExecutor`. (Section 9 mistake 7.)

**The strong signal:** articulate the cooperative-concurrency mental model crisply. "One thread, explicit yield points at every `await`, the loop interleaves them. Great for I/O wait, terrible for CPU." If you can say that in one sentence and then reach for `gather` / `Semaphore` / `wait_for` fluently, you're at staff-level on Python async.
