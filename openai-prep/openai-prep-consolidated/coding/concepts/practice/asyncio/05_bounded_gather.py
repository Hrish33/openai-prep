"""
Bounded concurrency — at most K coroutines running at once.

GOAL: Same as drill 04, but cap concurrency at K. With 5 fetches of 1s
each at K=2, expect ~3s total (3 waves: 2 + 2 + 1).

When working, expect output:
  k=1: 5 fetches in ~5.0s   (effectively sequential)
  k=2: 5 fetches in ~3.0s   (3 waves)
  k=5: 5 fetches in ~1.0s   (all parallel — equivalent to plain gather)

Real-world use cases:
  - Rate-limited APIs: "at most 10 concurrent requests to host X"
  - The Problem 8 (multithreaded crawler) async alternative — bound
    concurrency to avoid hammering target sites.

Pattern to memorize:
  sem = asyncio.Semaphore(K)

  async def with_limit(coro):
      async with sem:           # acquires sem before running coro
          return await coro

  await asyncio.gather(*(with_limit(c) for c in coros))

Why it works: gather schedules all N coros at once, but each one blocks
on `async with sem` until at most K hold the semaphore. The loop happily
interleaves the suspended ones.
"""

import asyncio
import time


async def fetch(name: str) -> str:
    await asyncio.sleep(0.1)
    return "fetch " + name

async def bounded_gather(coros: list, k: int) -> list:
    sem = asyncio.Semaphore(k)
    async def with_limit(coro):
        async with sem:
            return await coro
    return await asyncio.gather(*[with_limit(c) for c in coros])

async def main() -> None:
    for k in (1, 2, 5):
        coros = [fetch(f"url-{i}") for i in range(5)]
        t0 = time.perf_counter()
        await bounded_gather(coros, k)
        print(f"k={k}: 5 fetches in ~{time.perf_counter() - t0:.1f}s")


if __name__ == "__main__":
    asyncio.run(main())
