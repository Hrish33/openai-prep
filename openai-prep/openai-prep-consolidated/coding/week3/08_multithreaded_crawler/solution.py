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

from typing import Protocol


class HtmlParser(Protocol):
    def get_urls(self, url: str) -> list[str]:
        ...


class Crawler:
    def __init__(self, num_workers: int = 4) -> None:
        # your code here
        raise NotImplementedError

    def crawl(self, start_url: str, parser: HtmlParser) -> list[str]:
        # your code here
        raise NotImplementedError
