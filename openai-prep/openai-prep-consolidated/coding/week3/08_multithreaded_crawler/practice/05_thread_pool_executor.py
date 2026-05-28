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
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED


# ---------------------------------------------------------------------------
# PART A — fixed batch of independent work
# ---------------------------------------------------------------------------

def slow_square(n: int) -> int:
    """Simulates an I/O-bound task (sleep releases the GIL)."""
    time.sleep(0.1)
    return n * n


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
    # TODO: implement (~6 lines). Return the collected results sorted.
    raise NotImplementedError


def part_a_map() -> list[int]:
    """
    Same work via ex.map(slow_square, range(10)).
    ex.map returns results in INPUT order (not completion order) and
    re-raises any exception when you iterate. Return list(...) of it.
    """
    # TODO: implement (~3 lines)
    raise NotImplementedError


# ---------------------------------------------------------------------------
# PART B — dynamic / recursive work (the crawler shape)
# ---------------------------------------------------------------------------

THRESHOLD = 1000


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

    The pattern:
        visited = {root}
        lock = threading.Lock()         # guards visited check-then-act
        with ThreadPoolExecutor(max_workers=4) as ex:
            in_flight = {ex.submit(fetch_children, root)}
            while in_flight:
                done, in_flight = wait(in_flight, return_when=FIRST_COMPLETED)
                for fut in done:
                    for child in fut.result():
                        with lock:                  # check-then-act, same as 03/04
                            if child in visited:
                                continue
                            visited.add(child)
                        in_flight.add(ex.submit(fetch_children, child))   # OUTSIDE lock
        return visited

    Note what replaced what:
      - queue.Queue      -> the in_flight set of futures
      - q.join()         -> `while in_flight:` (loop until none pending)
      - poison pills      -> nothing! `with` exit joins the pool for you
      - q.get()/task_done -> wait(..., FIRST_COMPLETED)
    """
    # TODO: implement (~12 lines) following the shape above.
    raise NotImplementedError


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
