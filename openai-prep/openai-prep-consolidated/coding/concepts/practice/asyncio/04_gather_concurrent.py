"""
asyncio.gather — concurrent execution of multiple coroutines.

GOAL: Run 5 simulated fetches (each ~1s of "I/O") concurrently. Observe
~1s total wall time, not 5s.

When working, expect output:
  sequential: 5 fetches in ~5.0s
  gather:     5 fetches in ~1.0s

The interview signal: feel the difference in your gut. If the gather run
ALSO takes ~5s, something is sync-blocking the event loop (you used
time.sleep instead of asyncio.sleep — see drill 06).

Two rules:
  1. asyncio.gather(*coros) runs coros concurrently and returns a list of
     results in INPUT order (not completion order).
  2. The "concurrent" is cooperative — coros must hit await points for the
     loop to interleave them. A coro that never awaits monopolizes the loop
     until it returns.
"""

import asyncio
import time


async def fetch(name: str) -> str:
    await asyncio.sleep(0.1)
    return "fetch " + name


async def sequential(names: list) -> list:
    results = []
    for n in names:
        results.append(await fetch(n))
    return results


async def concurrent(names: list) -> list:
    results = await asyncio.gather(*[fetch(name) for name in names])
    return results

async def main() -> None:
    names = [f"url-{i}" for i in range(5)]

    t0 = time.perf_counter()
    results = await sequential(names)
    print(results)
    print(f"sequential: 5 fetches in ~{time.perf_counter() - t0:.1f}s")

    t0 = time.perf_counter()
    await concurrent(names)
    print(f"gather:     5 fetches in ~{time.perf_counter() - t0:.1f}s")


if __name__ == "__main__":
    asyncio.run(main())
