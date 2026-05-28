"""
Raw producer-consumer with queue.Queue + threading.Thread.

GOAL: 4 workers process 10 items concurrently. Total wall time should be
~0.25s, not 1.0s (proves threads are actually overlapping I/O).

When you've filled this in correctly, running it should print 10 "worker N got X"
lines (interleaved), then "all work drained in ~0.3s", then 4 worker-exiting
lines, then "all threads reaped".

The four phases of every worker-pool lifecycle:
  1. spin up workers
  2. enqueue real work
  3. q.join() — wait for work to drain
  4. pills + t.join() — clean shutdown
"""

import queue
import threading
import time

def worker(q: queue.Queue, worker_id: int) -> None:
    """
    Loop forever:
    """
    while q:
        task = q.get()
        try:
            print(f"worker {worker_id} on task {task}")
            if task is None:
                break
            time.sleep(1)
        finally:
            q.task_done()

def main() -> None:
    NUM_WORKERS = 4
    NUM_ITEMS = 10

    q = queue.Queue()

    threads = [threading.Thread(target=worker, args = (q, i)) for i in range(NUM_WORKERS)]
    for t in threads:
        print('add thread', t)
        t.start()

    for i in range(NUM_ITEMS):
        print('add item', i)
        q.put(i)

    # wait for work to finish
    print('wait for work to finish')
    q.join()

    print('add sentinel to end execution')
    for t in threads:
        q.put(None)
    print('wait for execution to end for each threads')
    for t in threads:
        t.join()

if __name__ == "__main__":
    main()
