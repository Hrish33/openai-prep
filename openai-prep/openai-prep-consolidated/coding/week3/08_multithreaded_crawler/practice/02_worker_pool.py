"""
Wrap the four-phase lifecycle from 01 in a context manager.

GOAL: same behavior as 01, but the four phases collapse into a `with` block.
__enter__ does phase 1 (spin up). __exit__ does phases 3+4 (drain + shutdown).
The body of `with` does phase 2 (enqueue).

This is essentially what `concurrent.futures.ThreadPoolExecutor` is.
"""

import queue
import threading
import time
from typing import Callable, final


class WorkerPool:
    def __init__(self, num_workers: int, handler: Callable[[object], None]):
        self.num_workers = num_workers
        self.handler = handler
        self.q = queue.Queue()

    def submit(self, item: object) -> None:
        self.q.put(item)

    def _worker(self, work_item) -> None:
        while True:
            task = self.q.get()
            print(f"worker", work_item)
            try :
                if task is None:
                    return
                self.handler(task)
            finally:
                self.q.task_done()

    def __enter__(self) -> "WorkerPool":
        # TODO: create num_workers threads targeting _worker, start them
        self.threads = [threading.Thread(target = self._worker
                                         , args=(i,)) for i in range(self.num_workers)]
        for t in self.threads:
            print('create thread', t)
            t.start()
        #     returns the actual reference to the pool
        return self

    def __exit__(self, *exc) -> None:
        #do the work
        self.q.join()
        for i in self.threads:
            print('exit thread', i)
            self.q.put(None)
        for t in self.threads:
            print('wait for exit thread', t)
            t.join()

def handle(item: object) -> None:
    print(f"  handling {item}")
    time.sleep(0.1)


def main() -> None:
    start = time.perf_counter()
    with WorkerPool(num_workers=4, handler=handle) as pool:
        #enter gets called here and returns as pool
        for i in range(10):
            pool.submit(i)
        # leaving the `with` block runs __exit__: drain + shutdown
    elapsed = time.perf_counter() - start
    print(f"\nfinished in {elapsed:.2f}s")


if __name__ == "__main__":
    main()
