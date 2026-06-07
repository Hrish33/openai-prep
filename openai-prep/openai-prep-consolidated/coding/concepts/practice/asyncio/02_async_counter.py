"""
Async iterator protocol — the minimal class form.

GOAL: AsyncCounter(n) yields 0, 1, ..., n-1 via `async for`.

When working, expect output:
  0
  1
  2
  3
  4
  exhausted as expected

THREE rules — burn these in:
  1. __aiter__ is NOT async. Plain `def`, returns self.
     (`async def __aiter__` is wrong — the protocol expects it sync.)
  2. __anext__ IS async (`async def`). Can await inside.
  3. Exhaustion raises StopAsyncIteration, NOT StopIteration.
     StopIteration leaking from a coroutine raises RuntimeError — Python
     explicitly forbids it because coroutines reuse generator machinery
     where StopIteration overloads as "return value".
"""

import asyncio

from concurrent.futures import thread

class AsyncCounter:
    def __init__(self, n: int) -> None:
        self.i = 0
        self.n = n

    def __aiter__(self) -> "AsyncCounter":
        # TODO: return self   (NOT async — plain def)
        return self

    async def __anext__(self) -> int:
        if self.i >= self.n: raise StopAsyncIteration
        # await thread.sleep(0)     # any suspension point
        await asyncio.sleep(0)     # any suspension point
        val = self.i
        self.i += 1
        return val


async def main() -> None:
    async for x in AsyncCounter(5):
        print(x)

    # Verify exhaustion via manual __anext__
    it = AsyncCounter(0)
    try:
        await it.__anext__()
        print("BUG — should have raised StopAsyncIteration")
    except StopAsyncIteration:
        print("exhausted as expected")


if __name__ == "__main__":
    asyncio.run(main())
