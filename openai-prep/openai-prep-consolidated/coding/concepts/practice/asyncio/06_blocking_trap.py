"""
The blocking-call trap — what happens when sync code sneaks into async.

GOAL: Observe the difference between asyncio.sleep (cooperative) and
time.sleep (blocking the loop). Both "sleep 1 second" — but only one
allows the loop to interleave other coroutines.

When working, expect output:
  asyncio.sleep: 5 fetches in ~1.0s   (loop interleaves)
  time.sleep:    5 fetches in ~5.0s   (each fetch blocks the loop)

This is the #1 production-time async bug. A "harmless" `requests.get`,
`time.sleep`, or `open().read()` inside async code freezes EVERY coroutine
on the loop for the duration of the call. The loop is single-threaded
and cooperative — there is no preemption to save you.

The fix when blocking calls are unavoidable:
  await asyncio.to_thread(blocking_fn, arg)
  — runs blocking_fn on the default thread pool, frees the event loop.

When async alternatives exist, prefer them:
  - requests.get(url)          →  httpx.AsyncClient().get(url)
  - open(path).read()          →  aiofiles.open(path)
  - time.sleep(s)              →  asyncio.sleep(s)
  - subprocess.run(cmd)        →  asyncio.create_subprocess_exec(...)

Interview phrasing: "any function you call inside async code that itself
blocks the thread freezes the entire event loop. It must either be async
all the way down, or wrapped in asyncio.to_thread."
"""

import asyncio
import time


async def fetch_cooperative(name: str) -> str:
    await asyncio.sleep(1); return name


async def fetch_blocking(name: str) -> str:
    # TODO: time.sleep(1)        # SYNC — blocks the entire event loop
    # TODO: return name
    raise NotImplementedError


async def main() -> None:
    names = [f"url-{i}" for i in range(5)]

    t0 = time.perf_counter()
    await asyncio.gather(*(fetch_cooperative(n) for n in names))
    print(f"asyncio.sleep: 5 fetches in ~{time.perf_counter() - t0:.1f}s")

    t0 = time.perf_counter()
    await asyncio.gather(*(fetch_blocking(n) for n in names))
    print(f"time.sleep:    5 fetches in ~{time.perf_counter() - t0:.1f}s")


if __name__ == "__main__":
    asyncio.run(main())
