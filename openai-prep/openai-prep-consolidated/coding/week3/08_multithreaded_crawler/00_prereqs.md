# Prereqs — Multithreaded Web Crawler

**Don't attempt the problem until you've worked through this.** Estimated time: 4-6 hours spread over 4-5 days.

This is a **Python-internals problem first, algorithm problem second**. The graph traversal underneath is just BFS — the entire interview signal is on the concurrency primitives. If you walk in thinking "I'll write BFS and sprinkle threads on top" you will get torn apart in follow-ups.

You need four things solid before attempting:
1. Why threads (not async, not multiprocessing) for I/O-bound work — the GIL story
2. The `queue.Queue` API and its termination idiom (`task_done` + `join`)
3. The check-then-act race on shared state and how `threading.Lock` fixes it
4. How to know "everyone's done" without polling

If you can't write a 4-worker URL-fetcher from a blank screen in 20 minutes, you're not ready for the problem.

---

## Concept 1: The GIL and "when do threads actually help?"

**What you're learning:** when threading buys you something in Python, and when it doesn't. This is the first thing an OpenAI interviewer will probe.

**The 30-second story:**

CPython has a Global Interpreter Lock — one thread executes Python bytecode at a time. So two threads doing pure CPU work do not run in parallel; they take turns. This makes threads useless for CPU-bound work.

**But** the GIL is released around blocking I/O calls — `socket.recv`, `time.sleep`, `requests.get`, file reads, etc. While one thread is blocked waiting on a syscall, other threads run freely. This makes threads great for I/O-bound work where most time is spent waiting.

**Mental model:**

| Work shape | Threads help? | Why |
|------------|---------------|-----|
| HTTP fetches, DB queries, file I/O | **Yes** | GIL releases during the syscall; threads overlap waiting |
| Number crunching, parsing in pure Python | **No** | GIL serializes them; you'd want `multiprocessing` or C extensions |
| Numpy/SciPy numerics | **Yes** | Numpy releases the GIL around its C kernels |

**Web crawling is I/O-bound** — `htmlParser.getUrls(url)` simulates a network round-trip. Threads are the right primitive. You should be able to say this in one sentence in the interview.

**Done when:** you can articulate, without hedging, why a CPU-bound matrix-multiply gets no speedup from threads but a 50-URL crawler does.

**Optional reading:** David Beazley's "Understanding the Python GIL" talk. 30 minutes, worth it.

---

## Concept 2: `queue.Queue` and its termination idiom

**What you're learning:** the producer-consumer pattern in Python without writing your own lock dance.

**The minimal program:**

```python
import queue, threading, time

q: queue.Queue = queue.Queue()

def worker():
    while True:
        item = q.get()
        if item is None:           # poison pill — sentinel to exit
            q.task_done()
            break
        print(f"got {item}")
        time.sleep(0.1)            # simulated work
        q.task_done()              # MUST call after every get()

threads = [threading.Thread(target=worker) for _ in range(4)]
for t in threads:
    t.start()

for i in range(10):
    q.put(i)

q.join()                           # block until task_done called for every put

for _ in threads:
    q.put(None)                    # one poison pill per worker
for t in threads:
    t.join()
```

Three rules. Internalize them:

1. **Every `q.get()` must be matched by a `q.task_done()`.** No exceptions, including in error paths. Use try/finally.
2. **`q.join()` waits until the unfinished-tasks counter hits zero.** That's the "all work done" signal — much cleaner than polling thread liveness.
3. **Workers that loop forever need an explicit exit signal.** Either a sentinel ("poison pill"), or you make them daemon threads and let the process kill them. Daemon threads are seductive but make tests flaky — prefer the sentinel.

**Why not a plain `list` + a `Lock`:**
- `Queue` already does the lock for you.
- `Queue` blocks on `get()` when empty — you get backpressure for free.
- `Queue` has the `task_done`/`join` accounting which is exactly the termination signal you need.

A common interview anti-pattern is rolling your own with `list` + `Lock` + `Condition`. It works, it's slower to write, it has more bugs. Reach for `queue.Queue` first; only justify a custom structure if you need something `Queue` can't give you.

### Variant: wrap the setup/teardown in a context manager

Once you've written the raw version a few times, you'll see the four phases are rigid enough to wrap. The lifecycle is **construct → use → destruct**, same as RAII in C++ or `defer` in Go:

```python
import queue, threading

class WorkerPool:
    def __init__(self, num_workers: int, handler):
        self._num_workers = num_workers
        self._handler = handler              # function: item -> None
        self._q: queue.Queue = queue.Queue()
        self._threads: list[threading.Thread] = []

    def submit(self, item) -> None:
        self._q.put(item)

    def _worker(self) -> None:
        while True:
            item = self._q.get()
            try:
                if item is None:
                    return
                self._handler(item)
            finally:
                self._q.task_done()

    def __enter__(self) -> "WorkerPool":
        self._threads = [
            threading.Thread(target=self._worker)
            for _ in range(self._num_workers)
        ]
        for t in self._threads:
            t.start()
        return self

    def __exit__(self, *exc) -> None:
        self._q.join()                       # drain real work
        for _ in self._threads:
            self._q.put(None)                # poison pills
        for t in self._threads:
            t.join()                         # reap threads
```

Usage:

```python
def handle(x):
    print(f"got {x}")

with WorkerPool(num_workers=4, handler=handle) as pool:
    for i in range(10):
        pool.submit(i)
# __exit__ runs the drain → signal → reap dance automatically
```

**This is exactly what `concurrent.futures.ThreadPoolExecutor` is** — its `__exit__` does this same dance, but with futures instead of a raw queue. So you should think of `ThreadPoolExecutor` as "WorkerPool with a nicer API for getting results back."

**Why the raw version still matters for the crawler:** workers in a crawler *produce more work* — each fetched page enqueues new URLs. `ThreadPoolExecutor.submit()` from inside a submitted task means tracking a set of in-flight futures and `wait()`-ing on them in a loop. With a raw `queue.Queue`, you just call `self._q.put(new_url)` inside the worker. That recursive-enqueue ergonomics is why the raw queue is often the cleaner reach. Both work — drill `practice/05_thread_pool_executor.py` walks through the futures-tracking loop side-by-side so you can feel the trade-off.

**Practice:** write the snippet above from memory. Then change the worker to enqueue new items based on what it pulled (this is the crawler's recursion).

**Done when:** you can write the producer-consumer template from a blank screen and explain why `task_done` exists.

---

## Concept 3: Shared mutable state and the check-then-act race

**What you're learning:** the actual bug pattern that the visited-set introduces, and the smallest fix.

**The bug:**

```python
visited: set[str] = set()

def worker(url):
    if url not in visited:          # CHECK
        visited.add(url)            # ACT
        # ... fetch and recurse ...
```

Two workers can both pass the `if url not in visited` check before either does `add`. Both fetch. You crawl the URL twice, and depending on what "fetch" means (cost, side effects), that's a correctness bug or a performance bug.

**The fix is a lock around the WHOLE check-then-act pair:**

```python
visited: set[str] = set()
visited_lock = threading.Lock()

def worker(url):
    with visited_lock:
        if url in visited:
            return                  # someone else already claimed this one
        visited.add(url)
    # ... fetch OUTSIDE the lock ...
```

Why this shape:
- The lock guards an *invariant* ("at most one worker enters the fetch path per URL"), not just a data structure.
- Releasing the lock before the slow operation (fetch) is essential — otherwise you've serialized all I/O behind the lock and your worker pool is moot.
- `set.add` on its own is atomic in CPython, but `if x not in s: s.add(x)` is not. Two operations. Two race windows.

**Variants you should know:**

| Construct | What it gives you |
|-----------|-------------------|
| `threading.Lock` | Plain mutex. Default choice. |
| `threading.RLock` | Reentrant — same thread can acquire twice. Use only if your code calls back into itself while holding the lock; otherwise prefer plain `Lock`. |
| `threading.Semaphore(n)` | "At most N holders." Use to cap concurrent HTTP connections, not for mutual exclusion. |
| `threading.Event` | One-shot "go" signal across many waiters. |
| `threading.Condition` | Wait-until-predicate. Rare in modern code — `Queue` covers most use cases. |

**Practice:** write a thread-safe counter and break it on purpose first (no lock) by spinning up 100 threads each incrementing 10000 times. Watch the result come out less than 1,000,000. Then add the lock and watch it converge.

**Done when:** you can identify a check-then-act race in code review and explain the fix without invoking magic words like "atomic."

---

## Concept 4: Knowing when "everyone's done"

**What you're learning:** termination is the part candidates routinely screw up. You need a single, defensible answer.

The crawler has a producer-consumer loop where workers *also produce* — each fetched URL can enqueue more URLs. That's the tricky part: you can't say "done when the queue is empty" because empty doesn't mean nothing's coming. A worker might be mid-fetch about to enqueue 30 more.

**The right primitive: `Queue.task_done` + `Queue.join`.**

Internally, `Queue` keeps an `unfinished_tasks` counter:
- `put()` increments it
- `task_done()` decrements it
- `join()` blocks until it hits zero

So as long as every fetched URL calls `task_done()` exactly once after fetching (which means: after any new URLs from that page are `put` onto the queue), `q.join()` returns precisely when there is no in-flight work and no queued work. That's your termination signal.

**The ordering inside a worker matters:**

```python
def worker():
    while True:
        url = q.get()
        if url is None:
            q.task_done()
            break
        try:
            for new_url in fetch_and_extract(url):
                if claim(new_url):       # lock + check-then-act
                    q.put(new_url)       # increments counter BEFORE we're done with current
        finally:
            q.task_done()                # AFTER all puts for this URL
```

If you call `task_done()` before the `q.put`s, you can hit a window where `unfinished_tasks` is briefly zero and `q.join()` returns even though more work is about to be enqueued. Put-then-done. Always.

**Alternative idioms (know the names; don't use them by default):**

| Idiom | When |
|-------|------|
| `ThreadPoolExecutor` + futures-tracking loop | Works for recursive crawls too: hold in-flight futures in a set, `wait(..., FIRST_COMPLETED)`, submit children as they surface, loop until the set empties. Termination is `while in_flight:` and the `with` exit reaps the pool — no poison pills. More moving parts than `queue.join`, but a legitimate answer. Drill it in `practice/05`. |
| Outer "active workers" counter + Condition | DIY equivalent of `task_done`/`join`. Easy to get wrong. |
| Daemon threads + sleep until queue empty for K seconds | Polling. Brittle. Don't. |

**Done when:** you can defend `task_done`/`join` against "why not just count threads?" in 30 seconds.

---

## Concept 5: Same-host filter (the algorithmic gotcha)

**What you're learning:** the only non-concurrency wrinkle in this problem. Easy to get wrong by overthinking the URL parsing.

The problem restricts crawling to URLs with the same hostname as the start URL. So given `startUrl = "http://news.yahoo.com/news/topics/"`, you crawl `http://news.yahoo.com/...` but not `http://sports.yahoo.com/...`.

The interview-grade parser is **two lines**, not `urllib.parse`:

```python
def hostname(url: str) -> str:
    # url is "http://<host>/<rest>"; strip the scheme, split off the path
    return url[len("http://"):].split("/", 1)[0]
```

`urllib.parse.urlparse(url).hostname` is correct, but it's overkill for a problem that defines the URL format strictly. Use the simple version; mention the library version exists if the interviewer presses on URL formats.

**Done when:** you can read the LC 1242 problem statement and immediately know the host-extraction is a one-liner, not a digression.

---

## Concept 6: `ThreadPoolExecutor` — the pool you don't hand-build

**What you're learning:** the standard library's worker pool, and the two ways to drive it. This is the "could you do it *without* managing threads by hand?" follow-up an interviewer asks the moment your queue+pills solution works. A strong answer needs both regimes below.

**The 30-second story:**

`concurrent.futures.ThreadPoolExecutor` is Concepts 2 + 4 wrapped in a library. It owns the threads, hands you a `submit()`/`map()` API, returns a `Future` per task, and its `__exit__` joins everything. The manual dance — spin up N threads, drop poison pills, `t.join()` each — disappears. In exchange you learn exactly one new object: the **Future**.

**The Future — the only new idea here:**

A `Future` is a handle to a result that may not exist yet. `submit()` returns one *immediately* (it does NOT block); the work runs on a pool thread, and the Future is how you later ask "are you done? what did you produce? did you blow up?"

```python
fut = ex.submit(fn, arg)   # returns now; fn runs on a worker thread
```

**The lifecycle — a Future is a tiny state machine.** It moves through these states, one direction only, and never goes backward:

```
            ex.submit(fn)
                 │
                 ▼
            ┌─────────┐   a worker picks it up    ┌─────────┐   fn returns / raises   ┌──────────┐
            │ PENDING │ ───────────────────────▶ │ RUNNING │ ──────────────────────▶ │ FINISHED │
            └─────────┘                           └─────────┘                          └──────────┘
                 │                                                                      (has a result
                 │  fut.cancel()  — only works while still PENDING                       OR an exception)
                 ▼
            ┌───────────┐
            │ CANCELLED │   never ran
            └───────────┘
```

The one rule worth memorizing: **you can only cancel a task that hasn't started.** Once a worker has picked it up (RUNNING), `cancel()` returns `False` and the task runs to completion — there is no preemption, no "kill the thread." FINISHED covers both success and failure; "the function raised" is a *normal* terminal state, and the exception sits inside the Future waiting for you to ask.

**The methods — what each one does and whether it blocks:**

| Method | Blocks? | Returns / does | When you reach for it |
|--------|---------|----------------|------------------------|
| `fut.result(timeout=None)` | **YES** until FINISHED | the return value, or **RE-RAISES** the task's exception | the main one — get the answer |
| `fut.exception(timeout=None)` | **YES** until FINISHED | the exception object, or `None` if it succeeded | inspect failure *without* raising |
| `fut.done()` | no | `True` if FINISHED or CANCELLED | poll without committing to a block |
| `fut.running()` | no | `True` if a worker is currently executing it | rarely; introspection |
| `fut.cancelled()` | no | `True` if it was cancelled before running | confirm a cancel took |
| `fut.cancel()` | no | tries to cancel; `True` only if still PENDING | abandon not-yet-started work |
| `fut.add_done_callback(fn)` | no | calls `fn(fut)` when it reaches FINISHED/CANCELLED | event-driven; callback runs on the worker's thread |

Note `result()` and `exception()` take an optional `timeout` — pass one and they raise `TimeoutError` instead of blocking forever, which is how you avoid a hang when a task wedges.

The property that bites people: **`.result()` re-raises, and if you never call it the exception is swallowed.** A fire-and-forget task that throws fails *silently* — the traceback is trapped inside the Future (FINISHED-with-exception) until someone calls `.result()` or `.exception()`. If you submit work and never inspect the futures, you are blind to failures. That's the #1 executor footgun. (`as_completed`/`map` save you here because iterating them forces you through each result.)

**Minimal program — Regime A, fixed batch:**

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

with ThreadPoolExecutor(max_workers=4) as ex:
    futures = [ex.submit(fetch, url) for url in urls]
    for fut in as_completed(futures):   # yields each as it finishes
        page = fut.result()             # re-raises if THAT fetch failed
        ...
# leaving `with` waits for all tasks, then tears the threads down
```

Three ways to collect results — know when each fits:

| API | Result order | Use when |
|-----|--------------|----------|
| `as_completed(futures)` | completion (fastest first) | react to each result ASAP |
| `ex.map(fn, iterable)` | **input** order | you want results aligned to inputs; re-raises on iteration |
| `fut.result()` on a saved list | your list order | you need one specific future's result at a specific time |

**The two regimes — this distinction *is* the concept:**

*Regime A — fixed batch (the easy 90%).* You know every task up front. `submit` them all, or `map` the iterable, collect. This is what the executor is built for.

*Regime B — dynamic / recursive (the crawler).* Tasks discover MORE tasks as they run. You can't `map` — you don't have the list. The idiom tracks in-flight futures and drains:

```python
from concurrent.futures import wait, FIRST_COMPLETED

with ThreadPoolExecutor(max_workers=N) as ex:
    inflight = {ex.submit(fetch, root)}
    while inflight:
        done, inflight = wait(inflight, return_when=FIRST_COMPLETED)
        for fut in done:
            for child in fut.result():
                with lock:                       # still need it — see below
                    if child in seen: continue
                    seen.add(child)
                inflight.add(ex.submit(fetch, child))
```

`wait(set, return_when=FIRST_COMPLETED)` returns `(done, not_done)`. Re-bind `inflight` to `not_done`, process the `done` ones (which may submit new futures), loop. Termination is `while inflight:` — when the set empties, all reachable work is finished. No poison pills; the `with` exit reaps the pool.

**Why the lock does NOT go away:** the executor manages *threads*, not *your shared state*. `visited`/`seen` still races exactly as in Concept 3. The executor saves you the pool plumbing — it does nothing for correctness on shared data. Candidates who think "I used the safe library pool, so I don't need a lock" ship the double-fetch bug.

**The deadlock to never write:** don't block on a Future (`.result()`) from *inside* a task running in the same bounded pool, when the thing you're waiting on itself needs a free worker. All workers can end up blocked waiting for tasks that can't be scheduled because all workers are blocked. The crawler is safe because you submit-and-return (you never `.result()` inside a task) — but know the trap, it's a classic follow-up.

**Sizing `max_workers`:** for I/O-bound work, more than the CPU count is fine and usually wanted — you're overlapping *waits*, not computing. The default (`min(32, os.cpu_count() + 4)`) is sensible. Dozens is normal for a crawler; don't reach for hundreds without a reason (thread stacks and context-switch cost are real).

**`map` vs `submit` in one line:** `map` when the work is a clean function over a list and you want input-ordered results; `submit` when you need the Futures themselves (to `as_completed`, to track in a set, to cancel, or because the work is dynamic).

**Done when:** you can take your queue+pills crawler and rewrite it with `ThreadPoolExecutor` + the `wait` loop, and articulate what got simpler (no pills, no manual join, no `task_done`) and what did NOT (the `visited` lock is still mandatory).

---

## Recall templates — type these from a blank screen

Everything above is commentary on these four. If you can type all four cold, you can derive the rest. Memorize the **shape** and the **one gotcha** attached to each.

**1. Raw queue pool** — gotcha: `task_done` in `finally`; pills *after* `join`.
```python
q = queue.Queue()
def worker():
    while True:
        item = q.get()
        try:
            if item is None:        # poison pill → exit
                return
            handle(item)            # may q.put() more work
        finally:
            q.task_done()           # ALWAYS, pill included

# start N threads targeting worker
# ... enqueue work ...
q.join()                           # drain
for _ in threads: q.put(None)      # pills
for t in threads: t.join()         # reap
```

**2. Check-then-act** — gotcha: the slow work goes *outside* the lock.
```python
with lock:
    if x in seen:
        return                     # or continue
    seen.add(x)
fetch(x)                           # outside — never hold the lock during I/O
```

**3. ThreadPoolExecutor, fixed batch** — gotcha: `.result()` re-raises the task's exception.
```python
with ThreadPoolExecutor(max_workers=N) as ex:
    futures = [ex.submit(fn, x) for x in items]
    for f in as_completed(futures):    # completion order
        use(f.result())
    # or, input order, one line:
    results = list(ex.map(fn, items))
```

**4. ThreadPoolExecutor, dynamic/recursive** — gotcha: loop until the in-flight set empties.
```python
seen = {root}
lock = threading.Lock()
with ThreadPoolExecutor(max_workers=N) as ex:
    inflight = {ex.submit(fetch, root)}
    while inflight:
        done, inflight = wait(inflight, return_when=FIRST_COMPLETED)
        for f in done:
            for child in f.result():
                with lock:
                    if child in seen:
                        continue
                    seen.add(child)
                inflight.add(ex.submit(fetch, child))   # outside the lock
```

**The mapping to hold in your head** — template 1 → template 4:

| Raw queue (1) | Executor (4) |
|---------------|--------------|
| `queue.Queue` | set of in-flight futures |
| `q.join()` | `while inflight:` |
| poison pills | nothing — `with` exit reaps |
| `q.get` / `task_done` | `wait(..., FIRST_COMPLETED)` |

---

## Hands-on drills (`practice/`)

Reading the concepts above is not enough — the signal is in your fingers, not your head. The `practice/` folder has scaffolds (TODO markers, not finished code) that isolate each primitive so you build muscle memory before assembling the real crawler. Fill them in, run them, then delete and re-do.

| Drill | Builds | Backing concept |
|-------|--------|-----------------|
| `01_producer_consumer.py` | raw `queue.Queue` + `threading.Thread`, the four-phase lifecycle (spin up → enqueue → `q.join()` → pills + reap) | Concept 2 |
| `02_worker_pool.py` | same lifecycle wrapped in a context manager (`__enter__`/`__exit__`) | Concept 2 (variant) |
| `03_check_then_act_race.py` | break a counter with no lock, watch it lose increments, then fix it | Concept 3 |
| `04_recursive_enqueue.py` | workers that `q.put()` more work — the crawler's shape in miniature | Concept 4 + 3 |
| `05_thread_pool_executor.py` | `submit`/`result`/`as_completed`/`map` for a fixed batch, then the futures-tracking loop for recursive work | Concept 2 (variant) + 4 |

**Readiness bar:** when you can write `01` from a blank screen in under 5 minutes, attempt `solution.py`. Not before.

---

## LeetCode primer

**[LeetCode 1242 — Web Crawler Multithreaded](https://leetcode.com/problems/web-crawler-multithreaded/) (Medium, premium)**

This is almost literally the problem you'll get. Solve it twice:

1. **Pass 1:** with `threading` + `queue.Queue`. Aim for ~50 lines of code.
2. **Pass 2:** with `concurrent.futures.ThreadPoolExecutor`. Notice what gets easier and what gets harder.

Time budget: 60 min for both.

If you don't have premium, the problem statement is in `problem.md` here — it's the same shape, just adapted.

**[LeetCode 1114 — Print in Order](https://leetcode.com/problems/print-in-order/) (Easy)**

Tiny but forces you to use a synchronization primitive correctly (Event, Semaphore, or Condition). Skip if Concept 3's counter-experiment was easy.

---

## Decision matrix: which concurrency primitive for which sub-problem?

You'll be quizzed on this verbally even if your code is clean.

| Sub-problem | Primitive |
|-------------|-----------|
| Worker pool over a stream of work items | `queue.Queue` + N `threading.Thread`s |
| "Have I seen this URL?" | `set` + `threading.Lock` around check-then-act |
| Cap concurrent HTTP connections (sub-pool) | `threading.Semaphore(n)` |
| "All work done" signal | `Queue.task_done` + `Queue.join` |
| Workers that loop forever need to exit | Sentinel ("poison pill") put on the queue |
| Shared counter (URLs fetched, bytes downloaded) | `threading.Lock` around update, OR a single owner thread reading from a results queue |
| Cross-process parallelism (CPU-bound parsing) | `multiprocessing.Pool` — different beast, mention but don't use here |

---

## Async variant — preview only

OpenAI may ask the same problem with `asyncio` instead of threads. Defer this until you've nailed the threaded version, but know it's coming. The shape changes:

- `queue.Queue` → `asyncio.Queue`
- `threading.Lock` → not needed for simple check-then-act inside a single event loop (cooperative scheduling means no preemption between non-await points). You *do* need it if your "check" and "act" straddle an `await`.
- `threading.Thread(target=worker)` → `asyncio.create_task(worker())`
- `q.task_done` / `q.join` → same API, exists on `asyncio.Queue`
- Number of "workers" → number of tasks, often higher than thread count (cheap)

We'll generate `coding/concepts/asyncio.md` when you reach this — for now, focus on the threaded version. Knowing both is the difference between "passing" and "strong hire" on the concurrency axis.

---

## Suggested schedule

| Day | What |
|-----|------|
| Day 1 | Read this whole doc. Run the producer-consumer snippet from Concept 2. Break and fix the counter from Concept 3. |
| Day 2 | LC 1242 with `threading.Thread` + `queue.Queue`. Aim for 60 min. |
| Day 3 | Re-solve LC 1242 with `ThreadPoolExecutor`. Compare line counts and termination logic. |
| Day 4 | **Attempt the crawler problem** — open `problem.md`, work in `solution.py`, run `test_solution.py`. |
| Day 5 | Read `interviewer_notes.md`. Re-do the problem from scratch the next day. |
| Day 6 (optional) | Once asyncio guide is generated: write the async variant. |

## How to use Claude Code during this

Teacher mode questions worth asking:
- "explain the GIL and what it means for I/O-bound vs CPU-bound work"
- "walk me through queue.Queue's task_done/join machinery"
- "show me a check-then-act race in 5 lines"
- "what's the difference between Lock, RLock, and Semaphore"

Don't ask Claude to solve LC 1242 for you. The muscle is in writing it yourself.

## When you're ready

When you can write a 4-worker queue-driven URL-fetcher from a blank screen in under 20 minutes, **then** open `problem.md` and start a 60-minute timer. Not before.
