"""
ThreadPoolExecutor: the stdlib's worker pool. It replaces the manual
threading.Thread + queue.Queue + poison-pill dance from 01/02 — the pool
spins up workers, hands you a clean submit() API, and joins everything on
`with` exit. No sentinels, no t.join() by hand.

There are TWO cases, and the whole point of this drill is to feel the
difference:

  PART A — FIXED batch of independent work (the easy 90%).
    You know all the work up front. submit() each item or map() the list.
    This is what ThreadPoolExecutor is built for.

  PART B — DYNAMIC / recursive work (the crawler shape, the hard 10%).
    Workers discover MORE work as they run. You can't map() — you don't
    know the full list. You track in-flight futures and keep draining
    until none remain. This is the case the real crawler lives in.

Run as-is → NotImplementedError. Fill in the TODOs, then run.

Expected output when working:
  PART A
    as_completed results (any order): [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]
    map results (input order):        [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]
    elapsed ~0.3s  (10 items x 0.1s, 4 workers — NOT 1.0s)
  PART B
    crawled N nodes (didn't know N upfront)   # N == 7 with THRESHOLD=1000
"""

import time
import threading
from asyncio import ALL_COMPLETED
from concurrent import futures
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED
from random import randint


# ---------------------------------------------------------------------------
# PART A — fixed batch of independent work
# ---------------------------------------------------------------------------

def slow_square(n: int, m) -> int:
    """Simulates an I/O-bound task (sleep releases the GIL)."""
    time.sleep(0.1 * randint(1, 10))
    return n * m


def part_a_submit() -> list[int]:
    """
    Submit slow_square for n in range(10) using ex.submit(), then collect
    results with as_completed (results arrive as each finishes — order is
    NONDETERMINISTIC, so sort before returning so the test is stable).

    Shape:
        with ThreadPoolExecutor(max_workers=4) as ex:
            futures = [ex.submit(...) for ...]
            for fut in as_completed(futures):
                ... fut.result() ...
    """
    res = []
    with ThreadPoolExecutor(max_workers=4) as exec:
        futures = [exec.submit(slow_square, i, i + 1) for i in range(10)]
        for future in as_completed(futures):
            print(future.result())
            res.append(future.result())
    return res

def part_a_map() -> list[int]:
    """
    Same work via ex.map(slow_square, range(10)).
    ex.map returns results in INPUT order (not completion order) and
    re-raises any exception when you iterate. Return list(...) of it.
    """
    with ThreadPoolExecutor(max_workers=4) as exec:
        return list(exec.map(slow_square, range(10), range(1, 11)))
# ---------------------------------------------------------------------------
# PART B — dynamic / recursive work (the crawler shape)
# ---------------------------------------------------------------------------

THRESHOLD = 100000


def fetch_children(n: int) -> list[int]:
    """
    The 'I/O' call: given a node, return its children. Same toy tree as 04.
    In the real crawler this is htmlParser.getUrls(url).
    """
    time.sleep(0.001)
    return [c for c in (n * 10 + 1, n * 10 + 2) if c <= THRESHOLD]


def crawl_with_executor(root: int) -> set[int]:
    """
    Crawl the whole tree from `root`, no node visited twice.

    The KEY DIFFERENCE from Part A: you don't have the work list up front.
    Each fetch_children() call reveals new nodes to crawl. So you can't
    map() — you track in-flight futures and keep draining as new ones appear.

    Note what replaced what:
      - queue.Queue      -> the in_flight set of futures
      - q.join()         -> `while in_flight:` (loop until none pending)
      - poison pills      -> nothing! `with` exit joins the pool for you
      - q.get()/task_done -> wait(..., FIRST_COMPLETED)
    """
    visited = set()
    in_flight = set()
    lock = threading.Lock()
    with ThreadPoolExecutor(max_workers=5) as exec:
        visited.add(root)
        in_flight.add(exec.submit(fetch_children, root))
        while in_flight:
            done, in_flight = wait(in_flight, return_when=ALL_COMPLETED)
            for fut in done:
                for child in fut.result():
                    with lock:
                        if child in visited:
                            continue
                        visited.add(child)
                    in_flight.add(exec.submit(fetch_children, child))
    return visited



# ---------------------------------------------------------------------------

def main() -> None:
    print("PART A")
    start = time.perf_counter()
    print("  as_completed results (sorted):", part_a_submit())
    print("  map results (input order):    ", part_a_map())
    print(f"  elapsed {time.perf_counter() - start:.2f}s")

    print("\nPART B")
    visited = crawl_with_executor(1)
    print(f"  crawled {len(visited)} nodes (didn't know this number upfront)")


if __name__ == "__main__":
    main()
