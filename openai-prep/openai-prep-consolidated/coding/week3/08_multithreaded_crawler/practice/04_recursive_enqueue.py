"""
The crawler's shape in miniature: workers themselves call q.put() to add
new work. This is what makes `q.join()` + sentinels (not a pre-counted
batch) the right termination idiom — you can't know up front how many
items will be processed.

Graph: each number n produces children [n*10+1, n*10+2] until value exceeds
THRESHOLD. Like a tiny tree of URLs.

GOAL: crawl the whole tree from root=1, no node visited twice, clean exit.

Key constraints to remember:
  - lock around the check-then-act on `visited` (same race as 03)
  - release the lock BEFORE q.put — don't hold it during "I/O"
  - q.put(child) MUST happen before q.task_done() for the current item,
    otherwise the unfinished_tasks counter can hit zero briefly with work
    about to be enqueued
  - mark visited at ENQUEUE time, not at dequeue time
"""

import queue
import threading
import time

THRESHOLD = 100000
visited: set[int] = set()
visited_lock = threading.Lock()


def worker(q: queue.Queue, worker_id: int) -> None:
    """
    Loop pulling values off q. For each n:
      - if n is None: exit
      - simulate I/O: time.sleep(0.001)
      - for each child in (n*10+1, n*10+2):
          if child > THRESHOLD: skip
          lock-guarded check-then-act on `visited`:
              if child in visited: skip
              else: add to visited
          q.put(child)   # OUTSIDE the lock
      - q.task_done() in a finally (runs for the None case too)
    """
    # TODO: implement (~15 lines)
    while True:
        try:

            task = q.get()
            if task is None:
                break
            time.sleep(0.001)
            for child in (task * 10 + 1, task * 10 + 2):
                if child > THRESHOLD:
                    continue
                with visited_lock:
                    if child in visited:
                        continue
                    visited.add(child)
                q.put(child)
        finally:
            q.task_done()


def main() -> None:
    NUM_WORKERS = 4
    q: queue.Queue = queue.Queue()

    # seed: mark root visited and enqueue it
    visited.add(1)
    q.put(1)

    # TODO: spin up NUM_WORKERS threads
    threads: list[threading.Thread] = [threading.Thread(target = worker, args = (q, i)) for i in range(NUM_WORKERS)]
    for t in threads:
        t.start()
    q.join()

    # TODO: q.join() to drain the whole tree

    print(f"crawled {len(visited)} nodes (didn't know this number upfront)")
    for _ in threads:
        q.put(None)
    for t in threads:
        t.join()
    # TODO: poison pills + t.join()
    print("clean shutdown")


if __name__ == "__main__":
    main()
