# Interviewer notes — Multithreaded Web Crawler

**Read AFTER your attempt.** Reading first defeats the point.

This reference is **scrappy, not polished** — it's what a strong 45-60 minute attempt actually looks like. No clever helpers, no abstractions, no `WorkerPool` class wrapping `threading.Thread`. The point is something you could rebuild from scratch under interview pressure, not a code-golf showpiece.

## Reference solution (`threading.Thread` + `queue.Queue`)

```python
import queue
import threading
from typing import Protocol


class HtmlParser(Protocol):
    def get_urls(self, url: str) -> list[str]: ...


_SENTINEL = object()


class Crawler:
    def __init__(self, num_workers: int = 4) -> None:
        self._num_workers = num_workers

    def crawl(self, start_url: str, parser: HtmlParser) -> list[str]:
        host = self._hostname(start_url)
        visited: set[str] = {start_url}
        lock = threading.Lock()
        q: queue.Queue = queue.Queue()
        q.put(start_url)

        def worker() -> None:
            while True:
                url = q.get()
                if url is _SENTINEL:
                    q.task_done()
                    return
                try:
                    for link in parser.get_urls(url):
                        if self._hostname(link) != host:
                            continue
                        with lock:
                            if link in visited:
                                continue
                            visited.add(link)
                        q.put(link)
                finally:
                    q.task_done()

        threads = [
            threading.Thread(target=worker, daemon=False)
            for _ in range(self._num_workers)
        ]
        for t in threads:
            t.start()

        q.join()                              # all in-flight + queued work drained

        for _ in threads:
            q.put(_SENTINEL)                  # one poison pill per worker
        for t in threads:
            t.join()

        return list(visited)

    @staticmethod
    def _hostname(url: str) -> str:
        return url[len("http://"):].split("/", 1)[0]
```

## Walking through `crawl`

Six steps. Memorize the steps, not the syntax:

1. **Seed.** Compute host, mark `start_url` as visited, put it on the queue.
2. **Spin up workers.** N threads running the same `worker` loop.
3. **Each worker fetches a URL, filters by host, claims (lock + check-then-act), enqueues new URLs.**
4. **`q.join()`** waits until every put has had a matching `task_done`. This is your termination signal — no in-flight work, no queued work.
5. **Poison pills.** Workers are still blocked on `q.get()`; one sentinel per worker wakes them up to exit.
6. **`t.join()` each worker.** Clean shutdown — no leaked threads.

## Why the lock guards a *check-then-act*, not the fetch

The dangerous pattern:

```python
# WRONG — serializes all fetches behind one lock
with lock:
    if url not in visited:
        visited.add(url)
        for link in parser.get_urls(url):
            ...
```

The fetch is the slow thing. Holding the lock through it means your N-worker pool degenerates to a single worker. The visited-set test catches this implicitly (no duplicates, even with 50 racing children), but the speedup test catches it directly — with 5 workers and 10×50ms pages, a lock-during-fetch implementation takes ~500ms instead of ~100ms.

The right pattern (in the reference above):
- Acquire the lock just long enough to read+update the set.
- Release before doing I/O.

This is the load-bearing insight on the concurrency axis. If you didn't see it, that's the thing to internalize for next time.

## Why "mark visited at enqueue, not at dequeue"

Look at the reference: a URL is added to `visited` *before* it's put on the queue (in the parent worker), not when a worker picks it up. Why?

Because if you mark visited at dequeue time, two workers can both see "url X is not visited" at enqueue time, both put X on the queue, and both proceed to fetch it before the other marks it. Marking at enqueue closes the race — the lock around check-then-act ensures only one worker ever gets to put a given URL on the queue.

The start URL is added to `visited` before the queue is started for the same reason — symmetric with how children are claimed.

## Why `task_done`/`join`, not "wait until queue empty"

`q.empty()` can be `True` momentarily while a worker is mid-fetch and about to enqueue more. Polling on empty is a race.

`q.join()` waits on the `unfinished_tasks` counter, which is incremented by `put` and decremented by `task_done`. The counter is only zero when:
- nothing is queued, AND
- nothing is currently being processed.

That's exactly the termination predicate you want. Critical ordering inside the worker: `q.put(link)` happens **before** `q.task_done()` for the current URL. If you swapped them, you could hit a window where the counter briefly hits zero while there's about to be more work.

## Honest weaknesses to acknowledge in interview

- **The hostname parser** is hardcoded to `http://` with no port, query, or fragment handling. Real-world: use `urllib.parse.urlparse(url).hostname`. Mention it.
- **No error handling** in the worker. A parser that raises will leak a thread (sort of — `task_done` is in a `finally`, so it won't deadlock, but the exception is swallowed silently). For an interview, I'd handle it by `try/except` around `parser.get_urls` and continue.
- **`visited` is the result.** That's fine for a closed-world problem, but it means the result list size = the visited-set size. If you wanted to distinguish "visited" from "fetched successfully," you'd need a second set.
- **No backpressure.** If one page links to a million others, all million get enqueued at once. A bounded queue with `block=True` would push back; not needed at this scale.
- **One lock for the entire visited set.** Fine for 10k URLs. At 10M URLs the lock starts contending — you'd shard the set by hash or move to a lock-free structure.

## Grading yourself

| Axis | Passing |
|------|---------|
| Edge cases up front | Named: self-link, cycle, same-host filter, duplicate links on a page, parser errors |
| Concurrency primitive choice | `queue.Queue` + `Thread` + `Lock` — and can defend NOT using `multiprocessing` (GIL story) or rolling your own queue |
| Lock guards check-then-act, not the fetch | Lock acquired only around the visited-set update; released before I/O |
| Termination | `q.join()` + sentinels — NOT polling, NOT daemon threads |
| `task_done` discipline | Called in a `finally`, after the `q.put`s for the current URL |
| Code structure | Worker is < 20 lines; `crawl` reads as 6 named steps; host-parser is a one-liner |
| Follow-up readiness | "Now do it with asyncio" or "now cap connections" doesn't make you freeze |

## Follow-up sketches

### 1. `concurrent.futures.ThreadPoolExecutor`

Tempting, but recursion-into-the-pool is awkward. Each fetch submits new fetches; you end up tracking futures of unknown count.

```python
from concurrent.futures import ThreadPoolExecutor

def crawl(self, start_url, parser):
    host = self._hostname(start_url)
    visited = {start_url}
    lock = threading.Lock()

    with ThreadPoolExecutor(max_workers=self._num_workers) as pool:
        futures = {pool.submit(parser.get_urls, start_url)}
        while futures:
            done, futures = wait(futures, return_when=FIRST_COMPLETED)
            for fut in done:
                for link in fut.result():
                    if self._hostname(link) != host:
                        continue
                    with lock:
                        if link in visited:
                            continue
                        visited.add(link)
                    futures.add(pool.submit(parser.get_urls, link))
    return list(visited)
```

What got simpler: no explicit worker function, no sentinels, no `task_done`.
What got harder: `wait(...)` requires you to think about which futures to wait on; the recursion is visible in the outer loop.

Either is fine in an interview. The `Queue` version is what most people write under pressure.

### 2. Asyncio variant

```python
import asyncio

class AsyncCrawler:
    def __init__(self, num_workers: int = 4) -> None:
        self._num_workers = num_workers

    async def crawl(self, start_url, parser):
        host = self._hostname(start_url)
        visited = {start_url}
        q: asyncio.Queue = asyncio.Queue()
        await q.put(start_url)

        async def worker():
            while True:
                url = await q.get()
                if url is None:
                    q.task_done()
                    return
                try:
                    for link in await parser.get_urls(url):
                        if self._hostname(link) != host:
                            continue
                        if link in visited:    # no lock needed — no await between check and act
                            continue
                        visited.add(link)
                        await q.put(link)
                finally:
                    q.task_done()

        tasks = [asyncio.create_task(worker()) for _ in range(self._num_workers)]
        await q.join()
        for _ in tasks:
            await q.put(None)
        await asyncio.gather(*tasks)
        return list(visited)
```

Key differences:
- **No lock.** The check `if link in visited` and the `visited.add(link)` happen between `await` points, so no other task can interleave. This only holds because we don't `await` between them. Add an `await` in the middle and the lock is back.
- **`create_task` is cheap.** You'd typically run 100 "workers" not 4.
- **`parser.get_urls` must be `async def`** in this world. The threaded version doesn't care.

This is what an OpenAI interviewer means by "depth in Python internals" — knowing *why* the lock disappears, not just that it does.

### 3. Cap connections per host (`Semaphore`)

```python
sem = threading.Semaphore(10)        # at most 10 concurrent fetches

def worker():
    while True:
        url = q.get()
        ...
        with sem:
            links = parser.get_urls(url)
        ...
```

Mention: semaphore is the right primitive for "at most N holders" — distinct from a `Lock` (which is "exactly 1") and from a worker count (which caps total parallelism). A 50-worker pool with a 10-connection semaphore is a real configuration.

### 4. Parser raises

```python
try:
    links = parser.get_urls(url)
except Exception:
    links = []                       # or: track failures in a separate set
```

Inside the `try`, *outside* the lock. Don't swallow exceptions without leaving a trace; in production you'd record the failure. For an interview, mentioning the trade-off is enough.

### 5. 10M URLs — visited set won't fit

- **Bloom filter** for fast-path "definitely not visited." False positives mean you occasionally skip a URL you should have fetched, which may or may not be acceptable.
- **Sharded set across machines**, with the queue also sharded by hostname so dedup decisions are local to a shard.
- **Persistent visited set** in something like RocksDB if you need exact dedup at this scale.

## Common mistakes interviewers see

1. **Holding the lock during `parser.get_urls`.** Serializes the crawler. Caught by the speedup test in `test_solution.py`.
2. **Unlocked check-then-act on `visited`.** Two workers both put the same URL, both fetch it. Caught by `test_no_url_visited_more_than_once_under_concurrency` when latency is added.
3. **`task_done()` outside a `finally`.** A parser exception leaves the counter wrong forever; `q.join()` hangs. Always `finally`.
4. **Calling `q.put()` *after* `q.task_done()` for the same URL.** Briefly zero counter window — `q.join()` can return early.
5. **Marking visited at dequeue instead of enqueue.** The race window between "I popped URL X" and "I marked X visited" lets another worker re-pop X. Mark at enqueue.
6. **`time.sleep(1); break if q.empty()`** as a termination hack. Will get you bounced.
7. **Daemon threads + return when "looks done."** Tests will be flaky; interviewer will dig and find no real termination logic.
8. **Reaching for `multiprocessing`.** Wrong primitive for I/O-bound work. Pickling cost, no shared memory, slower than threads for the same workload. Mention the GIL story instead.
9. **`urlparse` for the hostname when the spec says scheme is always `http://`.** Not wrong, but you'll burn 2 minutes you don't need to.

## Want a Round 2?

After you've internalized the threaded version, do the async variant in a separate file (`solution_async.py`). Same shape, no lock, `asyncio.Queue` instead of `queue.Queue`. Comparing your two implementations side-by-side is the best way to actually understand why async eliminates the lock — and why that's a property of cooperative scheduling, not magic.
