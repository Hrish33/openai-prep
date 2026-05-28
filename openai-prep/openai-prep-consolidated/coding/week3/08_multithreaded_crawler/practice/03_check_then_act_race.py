"""
Demonstrate the check-then-act race that the visited-set lock fixes.

GOAL:
  - run_unlocked() should LOSE increments — final value < 1,000,000
  - run_locked() should converge — final value == 1,000,000

IMPORTANT — making the race actually race:
  `counter += 1` in modern CPython is "accidentally" atomic enough that
  you may not see a lost-update bug. Force the race visible with an
  explicit read-then-write:

      tmp = counter
      # any tiny op or just the separate statement is enough to let the
      # interpreter give another thread a turn between read and write
      counter = tmp + 1

  This is the same shape as the crawler's `if url not in visited:
  visited.add(url)` — read state, decide, write state, two separable steps.

When working, expect output like:
  unlocked:   847,231 (expected 1,000,000) — lost 152,769 increments
  locked:   1,000,000 (expected 1,000,000) — OK
"""

import threading
import time

NUM_THREADS = 100
ITERATIONS = 10_000
EXPECTED = NUM_THREADS * ITERATIONS


def run_unlocked() -> int:
    """
    NUM_THREADS each increment a shared counter ITERATIONS times.
    Use an explicit read-modify-write (NOT `counter += 1`) so the race
    is observable.
    """
    counter = 0

    def worker() -> None:
        nonlocal counter
        for _ in range(ITERATIONS):
            tmp = counter
            time.sleep(0)
            counter = tmp + 1

    threads = [threading.Thread(target= worker) for _ in range(NUM_THREADS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return counter


def run_locked() -> int:
    """Same as run_unlocked but with a Lock around the read-modify-write."""
    counter = 0
    lock = threading.Lock()

    def worker() -> None:
        nonlocal counter
        with lock:
            for _ in range(ITERATIONS):
                # lock.acquire()
                tmp = counter
                time.sleep(0)
                counter = tmp + 1
                # lock.release()

    threads = [threading.Thread(target= worker) for _ in range(NUM_THREADS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    # TODO: spin up NUM_THREADS threads, join all
    return counter


def main() -> None:
    unlocked = run_unlocked()
    print(f"unlocked: {unlocked:>9,} (expected {EXPECTED:,}) "
          f"— lost {EXPECTED - unlocked:,} increments")

    locked = run_locked()
    print(f"locked:   {locked:>9,} (expected {EXPECTED:,}) "
          f"— {'OK' if locked == EXPECTED else 'BUG'}")

    print("\nTakeaway: `if url not in visited: visited.add(url)` is the")
    print("same two-step read-modify-write. Same race. Same fix.")


if __name__ == "__main__":
    main()
