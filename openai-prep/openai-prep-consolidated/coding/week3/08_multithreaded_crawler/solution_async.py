"""
Asyncio variant of the web crawler.

Same problem, different concurrency model. Read problem.md for the spec.
The interesting design questions are different from the threading version:

  Threading:    queue.Queue + N worker threads + threading.Lock on visited
                Termination: queue.join() + poison pills
                Workers BLOCK on q.get() — real OS threads, real wall-clock idle

  Asyncio:      asyncio.Queue + N worker COROUTINES + asyncio.Lock on visited
                Termination: queue.join() + worker cancellation
                Workers AWAIT q.get() — same event loop, scheduler resumes them

Key design choices to call out BEFORE coding:

  1. The parser is async. `await parser.get_urls(url)` is the I/O suspension
     point. The whole point of asyncio is to interleave many such awaits.

  2. visited needs a lock — OR — you can rely on the single-event-loop
     scheduling to avoid races, IF you structure the "check-then-act"
     (visited check + visited add) as ONE non-awaiting block. The cleanest
     answer is still an asyncio.Lock around the check-then-act. Don't
     hand-wave "asyncio is single-threaded so no lock needed" — the race
     is in the AWAIT BETWEEN check and add, not at the bytecode level.

  3. Termination — `asyncio.Queue.join()` mirrors `queue.Queue.join()`:
     blocks until every put has been matched by a task_done(). When join
     returns, cancel the worker tasks (which are sitting in q.get()).

  4. Backpressure — asyncio.Queue can have a maxsize. For a crawler with
     bounded fanout, unbounded is fine. For an unbounded link graph (or
     adversarial input), bound it.

  5. NUM_WORKERS in asyncio is a *concurrency limit*, not a CPU count.
     Even 1000 worker coroutines are cheap. The bound exists to limit
     in-flight requests against the parser (politeness / rate-limiting).

API: identical to the threading version, but `crawl` is async.

    crawler = AsyncCrawler(num_workers=8)
    result = await crawler.crawl(start_url, parser)
"""
import asyncio
from asyncio import tasks
from typing import Protocol


class AsyncHtmlParser(Protocol):
    async def get_urls(self, url: str) -> list[str]:
        ...


class AsyncCrawler:
    def __init__(self, num_workers: int = 8) -> None:
        # your code here
        self.num_workers = num_workers
    async def crawl(self, start_url: str, parser: AsyncHtmlParser) -> list[str]:
        return await self.crawl_2(start_url, parser)

    async def crawl_1(self, start_url: str, parser: AsyncHtmlParser) -> list[str]:
        """
        Level-by-level BFS via asyncio.gather. Mirrors crawl_bfs (ALL_COMPLETED).
        Semaphore caps in-flight requests to num_workers — without it, gather
        fires the entire level at once, which is fine for small graphs but
        rude to the parser when a level has thousands of URLs.
        """
        def parseHostName(url):
            return url.split("/")[2]

        sem = asyncio.Semaphore(self.num_workers)

        async def fetch(url: str) -> list[str]:
            async with sem:
                return await parser.get_urls(url)

        target_host = parseHostName(start_url)
        visited = {start_url}
        layer = [start_url]

        while layer:
            results = await asyncio.gather(*(fetch(url) for url in layer))
            next_layer = []
            for res in results:
                for link in res:
                    if parseHostName(link) == target_host and link not in visited:
                        visited.add(link)
                        next_layer.append(link)
            layer = next_layer

        return list(visited)

    async def crawl_2(self, start_url: str, parser: AsyncHtmlParser) -> list[str]:
        """
        Non-level continuous crawl via asyncio.wait + FIRST_COMPLETED. Mirrors
        crawl_executor. Semaphore caps in-flight requests to num_workers — the
        wait-set itself doesn't bound concurrency, it just reaps completions.
        """
        def parseHostName(url):
            return url.split("/")[2]

        sem = asyncio.Semaphore(self.num_workers)

        async def fetch(url: str) -> list[str]:
            async with sem:
                return await parser.get_urls(url)

        target_host = parseHostName(start_url)
        visited = {start_url}
        inflight = {asyncio.create_task(fetch(start_url))}

        while inflight:
            done, inflight = await asyncio.wait(inflight, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                for link in task.result():
                    if parseHostName(link) == target_host and link not in visited:
                        visited.add(link)
                        inflight.add(asyncio.create_task(fetch(link)))
        return list(visited)
