"""
Multithreaded web crawler.

Read 00_prereqs.md, then problem.md. Sketch your data structures and
concurrency primitives BEFORE coding. In particular, decide:
  - what's the queue of work, and what does an item look like?
  - what state is shared, and what guards it?
  - how do workers know when to exit?

Suggested structure (you don't have to follow this — design what makes
sense to you):
  - queue.Queue of URLs to fetch
  - threading.Thread pool of `num_workers` workers
  - visited: set[str], guarded by a threading.Lock
  - sentinel ("poison pill") to tell workers to exit after q.join()
"""
import asyncio
import threading
from asyncio import ALL_COMPLETED
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from queue import Queue
from threading import Thread
from typing import Protocol


class HtmlParser(Protocol):
    def get_urls(self, url: str) -> list[str]:
        ...


class Crawler:
    def __init__(self, num_workers: int = 4) -> None:
        # your code here
        self.num_workers = num_workers

    def crawl(self, start_url: str, parser: HtmlParser) -> list[str]:
        return self.crawl_executor(start_url, parser)

    def crawl_bfs(self, start_url: str, parser: HtmlParser) -> list[str]:

        def parseHostName(url):
            return url.split("/")[2]

        target_host = parseHostName(start_url)
        visited = set()

        with ThreadPoolExecutor(max_workers = self.num_workers) as exec:
            visited.add(start_url)
            inflight = {exec.submit(parser.get_urls, start_url)}
            while inflight :
                done_futures, inflight = wait(inflight, return_when=ALL_COMPLETED)
                for done_future in done_futures:
                    for link in done_future.result():
                        if link in visited:
                            continue
                        if parseHostName(link) == target_host:
                            visited.add(link)
                            inflight.add(exec.submit(parser.get_urls, link))
        return list(visited)


    def crawl_dfs(self, start_url: str, parser: HtmlParser) -> list[str]:
        def parseHostName(url):
            return url.split("/")[2]
        target_host = parseHostName(start_url)
        q = Queue()
        state_lock = threading.Lock()
        visited = {start_url}

        def worker():
            while True:
                url = q.get()
                try:
                    if url is None:
                        return
                    for next_url in parser.get_urls(url):
                        if parseHostName(next_url) == target_host :
                            with state_lock:
                                if next_url in visited:
                                    continue
                                visited.add(next_url)
                            q.put(next_url)
                finally:
                    q.task_done()

        threads = [threading.Thread(target=worker, ) for _ in range(self.num_workers)]

        q.put(start_url)

        for t in threads:
            t.start()


        q.join()

        for t in threads:
            q.put(None)

        for t in threads:
            t.join()

        return list(visited)

    def crawl_executor(self, start_url: str, parser: HtmlParser) -> list[str]:
        """
        Same continuous-workers shape as crawl_dfs, but with ThreadPoolExecutor
        instead of raw threads + Queue + poison pills.

        Key differences from crawl_dfs:
          - No worker function, no Queue, no poison pills. Executor manages
            the thread pool and shutdown via the `with` block.
          - return_when=FIRST_COMPLETED makes this non-level (vs crawl_bfs which
            uses ALL_COMPLETED and idles workers at level boundaries).
          - visited is touched only by THIS thread (main), so no lock needed —
            workers just call parser.get_urls and return. The visited check
            and child submission happen here as we reap each completed future.
        """
        def host(url): return url.split("/")[2]
        target_host = host(start_url)
        visited = {start_url}

        with ThreadPoolExecutor(max_workers=self.num_workers) as exec:
            inflight = {exec.submit(parser.get_urls, start_url)}
            while inflight:
                done, inflight = wait(inflight, return_when=FIRST_COMPLETED)
                for fut in done:
                    for link in fut.result():
                        if host(link) == target_host and link not in visited:
                            visited.add(link)
                            inflight.add(exec.submit(parser.get_urls, link))
        return list(visited)