# Problem 8: Multithreaded Web Crawler

**Prereqs:** Work through `00_prereqs.md` first. Don't attempt this cold.

**Time budget:** 60 minutes
**Source:** [HelloInterview community question](https://www.hellointerview.com/community/questions/multithreaded-web-crawler/cmbsl2nhd005107adsfu8ohme), mirrors [LeetCode 1242](https://leetcode.com/problems/web-crawler-multithreaded/)

## Problem

Given a starting URL and an HTML parser (injected — you don't make real network calls), crawl every reachable URL **on the same host** as the start URL, using multiple threads for concurrency. Return the deduplicated list of URLs visited.

```python
parser = MockHtmlParser({
    "http://news.yahoo.com/news/topics/": ["http://news.yahoo.com/news"],
    "http://news.yahoo.com/news":          ["http://news.yahoo.com/news/topics/",
                                            "http://news.yahoo.com/sports"],
    "http://news.yahoo.com/sports":        [],
    # other-host URL — must NOT be crawled:
    "http://sports.yahoo.com/anything":    ["http://sports.yahoo.com/more"],
})

crawler = Crawler(num_workers=4)
result = crawler.crawl("http://news.yahoo.com/news/topics/", parser)

# result (as a set) ==
# {"http://news.yahoo.com/news/topics/",
#  "http://news.yahoo.com/news",
#  "http://news.yahoo.com/sports"}
```

## Required API

```python
class HtmlParser:
    def get_urls(self, url: str) -> list[str]:
        """Return the list of URLs found on `url`. Injected — not real network."""
        ...

class Crawler:
    def __init__(self, num_workers: int = 4) -> None: ...

    def crawl(self, start_url: str, parser: HtmlParser) -> list[str]:
        """
        Crawl all URLs reachable from start_url that share its hostname.
        Return the deduplicated list of visited URLs (order not specified).
        Must use multiple threads. Must terminate.
        """
        ...
```

## Requirements

- **Same-host filter.** Only crawl URLs whose hostname matches `start_url`'s. Treat URLs as `http://<host>/<path>` — scheme is always `http://`, no `https`, no port, no query.
- **Dedup.** Each URL is visited (parser called) at most once across all threads.
- **Concurrent fetches.** Multiple threads call `parser.get_urls` in parallel. A correct serial solution will get docked on the rubric.
- **Terminates.** The function must return once the entire reachable set has been crawled. No daemon-thread leaks, no polling.
- **Thread-safe.** Two concurrent calls to `crawler.crawl(...)` on separate Crawler instances must be independent. (Same instance: not required, but be ready to discuss.)

## Constraints

- URL format: `http://<host>[/path]`. Hostname extraction is a one-liner; don't over-engineer with `urllib.parse`.
- The parser may have latency (the tests simulate this with `time.sleep`). Your solution shouldn't be measurably slower than `total_pages * page_latency / num_workers`.
- The parser is **idempotent and side-effect-free** for our purposes — but the rubric still says "call it at most once per URL."

## What an OpenAI interviewer is looking for

1. **Edge cases up front.** Enumerate before coding: empty parse result, self-link, cycle (A→B→A), other-host links, duplicate links on one page.
2. **Defendable concurrency primitives.** Almost certainly: `queue.Queue` + N `threading.Thread`s + a `threading.Lock`-guarded visited set. Be ready to explain why you didn't reach for `multiprocessing` (GIL story) or roll your own queue (`queue.Queue` already does the locking).
3. **Check-then-act on the visited set is locked.** This is the load-bearing race. If your `if url not in visited: visited.add(url)` is unlocked, that's a real bug, not a nit.
4. **Termination via `task_done`/`join`, not polling.** Workers loop forever; you exit them with a sentinel after `q.join()` returns.
5. **Lock released before I/O.** Holding the visited-set lock during `parser.get_urls(url)` serializes the entire crawler. Lock the bookkeeping, not the work.
6. **Clean separation.** Worker loop, claim/dedupe, host filter, and termination should each be readable in isolation. If your worker is 60 lines, you've lost.

## Follow-ups (don't peek until base works)

<details>
<summary>Click to expand</summary>

1. **Rewrite using `concurrent.futures.ThreadPoolExecutor`.** What gets simpler? What gets harder (hint: recursion-back-into-the-pool)?
2. **Rewrite using `asyncio`.** What primitives map 1:1, and what disappears (the lock, often)?
3. **Cap concurrent connections per host at K.** Now it's a `Semaphore`, not just a worker count.
4. **The parser fails on some URLs (raises).** Don't crash the crawler; mark the URL as visited-but-failed.
5. **Resume from a partial crawl.** Persist the visited set; on restart, re-seed the queue from the boundary.
6. **10M URLs.** The visited set no longer fits in memory. What now? (Bloom filter for fast-path "definitely not visited," fall back to disk for confirmation.)
7. **Politeness — never hit the same host more than 1 req/sec.** Where do you put that rate limit?
8. **Workers across machines, not threads.** What's the minimum set of changes? (Redis-backed queue, dedup by hostname-sharded set, idempotent enqueues.)

</details>

## Honest difficulty note

The algorithm is BFS. **The entire interview signal is on the concurrency.** A clean threaded solution is ~40-60 lines; an unclean one is 150. The hard parts are:

- Resisting the urge to hold the lock during the fetch.
- Getting termination right without `time.sleep` polling.
- Calling `task_done()` exactly once per `get()`, including in error paths.

If your first attempt deadlocks or hangs, that's expected on this problem. Read `interviewer_notes.md` after — termination is where most candidates lose points.
